"""Procurement assistant dashboard snapshot — WMS receive/supplier SQL + inventory MCP."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from core.dashboard.base import (
    bucket_label,
    fallback_chart,
    fallback_kpi,
    format_percent,
    format_trend,
    previous_period,
    resolve_date_range,
    tool_data,
)
from core.db import get_session
from models.dashboard import (
    AssistantDashboardResponse,
    DashboardChartSlot,
    DashboardKpiSlot,
    DataSource,
)
from models.intents.warehouse import InventoryStatusParams
from models.schemas import MCPContext
from mcp_tools.warehouse_tools import get_inventory_status_tool

RISK_OTD_THRESHOLD = 85.0


def _wh_filter(wh_code: Optional[str], alias: str = "rd") -> tuple[str, dict[str, Any]]:
    if not wh_code:
        return "", {}
    return f" AND {alias}.wh_code = :wh_code", {"wh_code": wh_code}


async def _fetch_receive_docs(
    wh_code: Optional[str], start: datetime, end: datetime
) -> list[dict[str, Any]]:
    session = await get_session()
    try:
        wh_sql, wh_bind = _wh_filter(wh_code, "rd")
        sql = text(
            f"""
            SELECT rd.supplier_code, rd.plan_receive_date, rd.receive_date
            FROM n2admin.t_wms_receive_doc rd
            WHERE rd.receive_date BETWEEN :start_date AND :end_date
              AND rd.plan_receive_date IS NOT NULL
              AND rd.receive_date IS NOT NULL
              AND rd.supplier_code IS NOT NULL
            {wh_sql}
            """
        )
        bind = {"start_date": start, "end_date": end, **wh_bind}
        rows = (await session.execute(sql, bind)).mappings().all()
    finally:
        await session.close()
    return [dict(r) for r in rows]


def _summarize_receive_docs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    on_time = 0
    supplier_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "on_time": 0}
    )

    for row in rows:
        supplier = str(row.get("supplier_code") or "").strip()
        plan = row.get("plan_receive_date")
        received = row.get("receive_date")
        if not plan or not received:
            continue
        is_on_time = received <= plan
        if is_on_time:
            on_time += 1
        if supplier:
            supplier_stats[supplier]["total"] += 1
            if is_on_time:
                supplier_stats[supplier]["on_time"] += 1

    otd_rate = (on_time / total * 100.0) if total else None
    risk_count = 0
    for stats in supplier_stats.values():
        if stats["total"] < 2:
            continue
        supplier_otd = stats["on_time"] / stats["total"] * 100.0
        if supplier_otd < RISK_OTD_THRESHOLD:
            risk_count += 1

    return {
        "total": total,
        "on_time": on_time,
        "otd_rate": otd_rate,
        "risk_suppliers": risk_count,
        "supplier_stats": dict(supplier_stats),
    }


def _stability_from_receive_docs(rows: list[dict[str, Any]]) -> Optional[float]:
    if len(rows) < 2:
        return None

    late_flags: list[float] = []
    for row in rows:
        plan = row.get("plan_receive_date")
        received = row.get("receive_date")
        if not plan or not received:
            continue
        late_flags.append(0.0 if received <= plan else 1.0)

    if not late_flags:
        return None

    late_rate = sum(late_flags) / len(late_flags)
    return round(max(100.0 - late_rate * 100.0, 0.0), 1)


async def _fetch_receive_summary(
    wh_code: Optional[str], start: datetime, end: datetime
) -> dict[str, Any]:
    rows = await _fetch_receive_docs(wh_code, start, end)
    return _summarize_receive_docs(rows)


async def _fetch_spend_totals(
    wh_code: Optional[str], start: datetime, end: datetime
) -> float:
    session = await get_session()
    try:
        wh_sql, wh_bind = _wh_filter(wh_code, "rd")
        sql = text(
            f"""
            SELECT COALESCE(
                SUM(COALESCE(ri.receive_qty, 0) * COALESCE(ci.single_price, 0)),
                0
            ) AS spend
            FROM n2admin.t_wms_receive_item ri
            JOIN n2admin.t_wms_receive_doc rd ON ri.doc_no = rd.doc_no
            LEFT JOIN n2admin.t_co_item ci ON ri.item_code = ci.item_code
            WHERE rd.receive_date BETWEEN :start_date AND :end_date
            {wh_sql}
            """
        )
        bind = {"start_date": start, "end_date": end, **wh_bind}
        row = (await session.execute(sql, bind)).mappings().first()
    finally:
        await session.close()
    return float(row.get("spend") or 0) if row else 0.0


async def _fetch_spend_comparison(
    wh_code: Optional[str],
    start: datetime,
    end: datetime,
    prev_start: datetime,
    prev_end: datetime,
) -> dict[str, Any]:
    current, previous = await asyncio.gather(
        _fetch_spend_totals(wh_code, start, end),
        _fetch_spend_totals(wh_code, prev_start, prev_end),
    )
    savings_pct = None
    if previous > 0:
        savings_pct = ((previous - current) / previous) * 100.0
    growth = None
    if previous > 0:
        growth = ((current - previous) / previous) * 100.0
    return {
        "current_spend": current,
        "previous_spend": previous,
        "savings_pct": savings_pct,
        "spend_growth": growth,
    }


async def _fetch_daily_spend(
    wh_code: Optional[str], start: datetime, end: datetime
) -> tuple[list[str], list[float]]:
    session = await get_session()
    try:
        wh_sql, wh_bind = _wh_filter(wh_code, "rd")
        sql = text(
            f"""
            SELECT DATE(rd.receive_date) AS bucket,
                   COALESCE(
                       SUM(COALESCE(ri.receive_qty, 0) * COALESCE(ci.single_price, 0)),
                       0
                   ) AS spend
            FROM n2admin.t_wms_receive_item ri
            JOIN n2admin.t_wms_receive_doc rd ON ri.doc_no = rd.doc_no
            LEFT JOIN n2admin.t_co_item ci ON ri.item_code = ci.item_code
            WHERE rd.receive_date BETWEEN :start_date AND :end_date
            {wh_sql}
            GROUP BY DATE(rd.receive_date)
            ORDER BY bucket
            """
        )
        bind = {"start_date": start, "end_date": end, **wh_bind}
        rows = (await session.execute(sql, bind)).mappings().all()
    finally:
        await session.close()

    labels: list[str] = []
    series: list[float] = []
    for row in rows:
        spend = float(row.get("spend") or 0)
        if spend <= 0:
            continue
        labels.append(str(row.get("bucket") or "")[:10])
        series.append(round(spend / 10000.0, 2))
    return labels, series


async def _fetch_supplier_scores(
    supplier_stats: dict[str, dict[str, int]],
) -> tuple[list[str], list[float]]:
    if not supplier_stats:
        return [], []

    session = await get_session()
    try:
        codes = list(supplier_stats.keys())[:20]
        placeholders = ", ".join(f":s{i}" for i in range(len(codes)))
        bind = {f"s{i}": code for i, code in enumerate(codes)}
        name_map: dict[str, str] = {}
        if codes:
            sql = text(
                f"""
                SELECT supplier_code, supplier_name, supplier_shortname
                FROM n2admin.t_co_supplier
                WHERE supplier_code IN ({placeholders})
                """
            )
            rows = (await session.execute(sql, bind)).mappings().all()
            for row in rows:
                code = str(row.get("supplier_code") or "")
                name = (
                    row.get("supplier_shortname")
                    or row.get("supplier_name")
                    or code
                )
                name_map[code] = str(name)[:12]
    finally:
        await session.close()

    scored: list[tuple[str, float, int]] = []
    for code, data in supplier_stats.items():
        total = int(data.get("total") or 0)
        if total < 1:
            continue
        otd = int(data.get("on_time") or 0) / total * 100.0
        scored.append((code, round(otd, 1), total))

    scored.sort(key=lambda x: x[2], reverse=True)
    top = scored[:5]
    labels = [name_map.get(code, code[:12]) for code, _, _ in top]
    series = [score for _, score, _ in top]
    return labels, series


async def _fetch_lead_time_by_abc(
    wh_code: Optional[str], start: datetime, end: datetime, locale: str
) -> tuple[list[str], list[float]]:
    session = await get_session()
    try:
        wh_sql, wh_bind = _wh_filter(wh_code, "rd")
        sql = text(
            f"""
            SELECT ci.abc_type,
                   AVG(EXTRACT(EPOCH FROM (rd.receive_date - rd.plan_receive_date)) / 86400.0)
                       AS avg_lead_days
            FROM n2admin.t_wms_receive_doc rd
            JOIN n2admin.t_wms_receive_item ri ON ri.doc_no = rd.doc_no
            LEFT JOIN n2admin.t_co_item ci ON ri.item_code = ci.item_code
            WHERE rd.receive_date BETWEEN :start_date AND :end_date
              AND rd.plan_receive_date IS NOT NULL
              AND rd.receive_date IS NOT NULL
              AND ci.abc_type IS NOT NULL
            {wh_sql}
            GROUP BY ci.abc_type
            ORDER BY ci.abc_type
            """
        )
        bind = {"start_date": start, "end_date": end, **wh_bind}
        rows = (await session.execute(sql, bind)).mappings().all()
    finally:
        await session.close()

    zh = locale.startswith("zh")
    labels: list[str] = []
    series: list[float] = []
    for row in rows:
        abc = str(row.get("abc_type") or "").strip()
        if not abc:
            continue
        days = float(row.get("avg_lead_days") or 0)
        if days < 0:
            days = abs(days)
        labels.append(f"{abc}类" if zh else f"Cat {abc}")
        series.append(round(days, 1))
    return labels, series


async def _fetch_kit_rate(wh_code: Optional[str]) -> Optional[float]:
    session = await get_session()
    try:
        filters = ["ci.min_stock > 0"]
        bind: dict[str, Any] = {}
        if wh_code:
            filters.append("s.wh_code = :wh_code")
            bind["wh_code"] = wh_code

        sql = text(
            f"""
            SELECT s.item_code,
                   SUM(COALESCE(s.item_qty, 0)) AS stock_qty,
                   MAX(COALESCE(ci.min_stock, 0)) AS min_stock
            FROM n2admin.t_wms_stock_info s
            JOIN n2admin.t_co_item ci ON s.item_code = ci.item_code
            WHERE {" AND ".join(filters)}
            GROUP BY s.item_code
            """
        )
        rows = (await session.execute(sql, bind)).mappings().all()
    finally:
        await session.close()

    if not rows:
        return None

    covered = 0
    for row in rows:
        stock = float(row.get("stock_qty") or 0)
        minimum = float(row.get("min_stock") or 0)
        if minimum > 0 and stock >= minimum:
            covered += 1

    return round((covered / len(rows)) * 100.0, 1) if rows else None


class ProcurementDashboardBuilder:
    async def build(
        self,
        wh_code: Optional[str],
        locale: str,
        lookback_days: int,
        context: MCPContext,
    ) -> AssistantDashboardResponse:
        start, end = resolve_date_range(lookback_days)
        prev_start, prev_end = previous_period(start, end)

        receive_rows = await _fetch_receive_docs(wh_code, start, end)
        receive_summary = _summarize_receive_docs(receive_rows)
        stability = _stability_from_receive_docs(receive_rows)

        (
            spend_comparison,
            daily_spend,
            supplier_scores,
            lead_time_abc,
            kit_rate,
            inventory_result,
        ) = await asyncio.gather(
            _fetch_spend_comparison(wh_code, start, end, prev_start, prev_end),
            _fetch_daily_spend(wh_code, start, end),
            _fetch_supplier_scores(receive_summary.get("supplier_stats") or {}),
            _fetch_lead_time_by_abc(wh_code, start, end, locale),
            _fetch_kit_rate(wh_code),
            get_inventory_status_tool.run(
                InventoryStatusParams(wh_code=wh_code), context
            ),
        )

        daily_labels, daily_series = daily_spend
        supplier_labels, supplier_series = supplier_scores
        abc_labels, abc_series = lead_time_abc

        inv_data = tool_data(inventory_result) or {}
        low_stock_count = len(inv_data.get("low_stock") or [])

        kpis = self._build_kpis(receive_summary, spend_comparison)
        charts = self._build_charts(
            daily_labels,
            daily_series,
            supplier_labels,
            supplier_series,
            stability,
            abc_labels,
            abc_series,
            kit_rate,
            locale,
        )
        partial = any(
            slot.source == DataSource.FALLBACK for slot in (*kpis, *charts)
        )
        insight = self._build_insight(
            kpis, wh_code, locale, receive_summary, low_stock_count
        )

        return AssistantDashboardResponse(
            module="procurement",
            wh_code=wh_code,
            kpis=kpis,
            charts=charts,
            insight=insight,
            partial=partial,
            generated_at=datetime.utcnow(),
        )

    def _build_kpis(
        self,
        receive_summary: dict[str, Any],
        spend_comparison: dict[str, Any],
    ) -> list[DashboardKpiSlot]:
        kpis: list[DashboardKpiSlot] = []

        savings = spend_comparison.get("savings_pct")
        if savings is not None and spend_comparison.get("previous_spend", 0) > 0:
            trend = format_trend(spend_comparison.get("spend_growth"))
            kpis.append(
                DashboardKpiSlot(
                    index=0,
                    value=format_percent(float(savings)),
                    trend=trend,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(0))

        otd = receive_summary.get("otd_rate")
        if otd is not None and receive_summary.get("total", 0) > 0:
            kpis.append(
                DashboardKpiSlot(
                    index=1,
                    value=format_percent(float(otd)),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(1))

        risk = receive_summary.get("risk_suppliers")
        if risk is not None and receive_summary.get("total", 0) > 0:
            kpis.append(
                DashboardKpiSlot(
                    index=2,
                    value=str(int(risk)),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(2))

        return kpis

    def _build_charts(
        self,
        daily_labels: list[str],
        daily_series: list[float],
        supplier_labels: list[str],
        supplier_series: list[float],
        stability: Optional[float],
        abc_labels: list[str],
        abc_series: list[float],
        kit_rate: Optional[float],
        locale: str,
    ) -> list[DashboardChartSlot]:
        charts: list[DashboardChartSlot] = []

        if daily_series:
            charts.append(
                DashboardChartSlot(
                    index=0,
                    chart_type="line",
                    x_data=[
                        bucket_label(label, locale) for label in daily_labels
                    ],
                    series=daily_series,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(0, "line"))

        if supplier_series:
            charts.append(
                DashboardChartSlot(
                    index=1,
                    chart_type="bar",
                    x_data=supplier_labels,
                    series=supplier_series,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(1, "bar"))

        if stability is not None and stability > 0:
            charts.append(
                DashboardChartSlot(
                    index=2,
                    chart_type="gauge",
                    gauge_value=min(stability, 100.0),
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(2, "gauge"))

        if abc_series:
            charts.append(
                DashboardChartSlot(
                    index=3,
                    chart_type="bar",
                    x_data=abc_labels,
                    series=abc_series,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(3, "bar"))

        charts.append(fallback_chart(4, "line"))

        if kit_rate is not None and kit_rate > 0:
            charts.append(
                DashboardChartSlot(
                    index=5,
                    chart_type="gauge",
                    gauge_value=kit_rate,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(5, "gauge"))

        return charts

    def _build_insight(
        self,
        kpis: list[DashboardKpiSlot],
        wh_code: Optional[str],
        locale: str,
        receive_summary: dict[str, Any],
        low_stock_count: int,
    ) -> str:
        scope = wh_code or ("全部仓库" if locale.startswith("zh") else "all warehouses")
        live_kpis = [k for k in kpis if k.source == DataSource.LIVE]
        if not live_kpis:
            if locale.startswith("zh"):
                return f"采购域 {scope} 数据暂不可用，请稍后重试或通过 AI 助手提问。"
            return f"Procurement data for {scope} is unavailable. Try again or ask the AI assistant."

        kpi0 = next((k for k in kpis if k.index == 0 and k.source == DataSource.LIVE), None)
        kpi1 = next((k for k in kpis if k.index == 1 and k.source == DataSource.LIVE), None)
        risk = int(receive_summary.get("risk_suppliers") or 0)

        if locale.startswith("zh"):
            parts = [f"采购域 {scope} 最新扫描完成。"]
            if kpi0:
                parts.append(f"采购节省率 {kpi0.value}。")
            if kpi1:
                parts.append(f"准交率 {kpi1.value}。")
            if risk:
                parts.append(f"风险供应商 {risk} 家。")
            if low_stock_count:
                parts.append(f"低库存物料 {low_stock_count} 项需补货。")
            parts.append("可通过右侧 AI 助手分析供应商表现与补货建议。")
            return " ".join(parts)

        parts = [f"Procurement scan for {scope} is ready."]
        if kpi0:
            parts.append(f"Savings rate is {kpi0.value}.")
        if kpi1:
            parts.append(f"On-time delivery is {kpi1.value}.")
        if risk:
            parts.append(f"{risk} at-risk suppliers.")
        if low_stock_count:
            parts.append(f"{low_stock_count} low-stock items need replenishment.")
        parts.append("Use the AI assistant for supplier and replenishment analysis.")
        return " ".join(parts)


procurement_dashboard_builder = ProcurementDashboardBuilder()
