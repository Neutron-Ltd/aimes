"""Warehouse assistant dashboard snapshot — MCP tools + WMS SQL aggregations."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text

from core.config import get_settings
from core.dashboard.base import (
    fallback_chart,
    fallback_kpi,
    format_percent,
    tool_data,
)
from core.db import get_session
from models.dashboard import (
    AssistantDashboardResponse,
    DashboardChartSlot,
    DashboardKpiSlot,
    DataSource,
)
from models.intents.warehouse import InventoryStatusParams, ObsoleteProfileParams
from models.schemas import MCPContext
from mcp_tools.warehouse_tools import (
    get_inventory_status_tool,
    profile_obsolete_inventory_tool,
)

AGE_BUCKET_LABELS_ZH = ["0-30天", "31-60天", "61-90天", "91-180天", "180天+"]
AGE_BUCKET_LABELS_EN = ["0-30d", "31-60d", "61-90d", "91-180d", "180d+"]


def _reference_datetime() -> datetime:
    settings = get_settings()
    ref_end = settings.dashboard_reference_date
    end_day = min(date.today(), ref_end)
    return datetime.combine(end_day, datetime.max.time()).replace(microsecond=0)


async def _fetch_stock_summary(
    wh_code: Optional[str], ref_date: datetime
) -> dict[str, Any]:
    session = await get_session()
    expiring_cutoff = ref_date + timedelta(days=30)
    try:
        filters = ["s.item_qty > 0"]
        bind: dict[str, Any] = {
            "ref_date": ref_date,
            "expiring_cutoff": expiring_cutoff,
        }
        if wh_code:
            filters.append("s.wh_code = :wh_code")
            bind["wh_code"] = wh_code

        sql = text(
            f"""
            SELECT COUNT(*) AS total,
                   SUM(
                       CASE
                           WHEN COALESCE(ci.min_stock, 0) > 0
                                AND s.item_qty < ci.min_stock
                           THEN 1 ELSE 0
                       END
                   ) AS low_stock,
                   SUM(
                       CASE
                           WHEN s.invalid_date IS NOT NULL
                                AND s.invalid_date <= :expiring_cutoff
                           THEN 1 ELSE 0
                       END
                   ) AS expiring,
                   AVG(
                       CASE
                           WHEN s.instock_time IS NOT NULL
                           THEN EXTRACT(
                               EPOCH FROM (:ref_date - s.instock_time)
                           ) / 86400.0
                           ELSE NULL
                       END
                   ) AS avg_turnover_days
            FROM n2admin.t_wms_stock_info s
            LEFT JOIN n2admin.t_co_item ci ON s.item_code = ci.item_code
            WHERE {" AND ".join(filters)}
            """
        )
        row = (await session.execute(sql, bind)).mappings().first()
    finally:
        await session.close()

    total = int(row.get("total") or 0) if row else 0
    low_stock = int(row.get("low_stock") or 0) if row else 0
    expiring = int(row.get("expiring") or 0) if row else 0
    avg_turnover = row.get("avg_turnover_days") if row else None
    healthy = max(total - low_stock - expiring, 0)
    accuracy = ((healthy / total) * 100.0) if total else None

    return {
        "total": total,
        "low_stock": low_stock,
        "expiring": expiring,
        "healthy": healthy,
        "avg_turnover_days": float(avg_turnover) if avg_turnover is not None else None,
        "accuracy_pct": accuracy,
    }


async def _fetch_age_buckets(
    wh_code: Optional[str], ref_date: datetime
) -> list[int]:
    session = await get_session()
    try:
        filters = ["s.item_qty > 0", "s.instock_time IS NOT NULL"]
        bind: dict[str, Any] = {"ref_date": ref_date}
        if wh_code:
            filters.append("s.wh_code = :wh_code")
            bind["wh_code"] = wh_code

        sql = text(
            f"""
            SELECT
                SUM(
                    CASE
                        WHEN (DATE(:ref_date) - DATE(s.instock_time)) <= 30 THEN 1
                        ELSE 0
                    END
                ) AS bucket_0,
                SUM(
                    CASE
                        WHEN (DATE(:ref_date) - DATE(s.instock_time)) > 30
                             AND (DATE(:ref_date) - DATE(s.instock_time)) <= 60
                        THEN 1 ELSE 0
                    END
                ) AS bucket_1,
                SUM(
                    CASE
                        WHEN (DATE(:ref_date) - DATE(s.instock_time)) > 60
                             AND (DATE(:ref_date) - DATE(s.instock_time)) <= 90
                        THEN 1 ELSE 0
                    END
                ) AS bucket_2,
                SUM(
                    CASE
                        WHEN (DATE(:ref_date) - DATE(s.instock_time)) > 90
                             AND (DATE(:ref_date) - DATE(s.instock_time)) <= 180
                        THEN 1 ELSE 0
                    END
                ) AS bucket_3,
                SUM(
                    CASE
                        WHEN (DATE(:ref_date) - DATE(s.instock_time)) > 180 THEN 1
                        ELSE 0
                    END
                ) AS bucket_4
            FROM n2admin.t_wms_stock_info s
            WHERE {" AND ".join(filters)}
            """
        )
        row = (await session.execute(sql, bind)).mappings().first()
    finally:
        await session.close()

    if not row:
        return [0, 0, 0, 0, 0]
    return [
        int(row.get("bucket_0") or 0),
        int(row.get("bucket_1") or 0),
        int(row.get("bucket_2") or 0),
        int(row.get("bucket_3") or 0),
        int(row.get("bucket_4") or 0),
    ]


async def _fetch_bin_utilization(wh_code: Optional[str]) -> Optional[float]:
    session = await get_session()
    try:
        area_sql = text(
            """
            SELECT COUNT(DISTINCT area_sn) AS total_bins
            FROM n2admin.t_wms_area
            """
        )
        stock_bind: dict[str, Any] = {}
        stock_filter = "WHERE item_qty > 0 AND storage_code IS NOT NULL"
        if wh_code:
            stock_filter += " AND wh_code = :wh_code"
            stock_bind["wh_code"] = wh_code

        stock_sql = text(
            f"""
            SELECT COUNT(DISTINCT storage_code) AS occupied_bins
            FROM n2admin.t_wms_stock_info
            {stock_filter}
            """
        )
        area_row = (await session.execute(area_sql)).mappings().first()
        stock_row = (await session.execute(stock_sql, stock_bind)).mappings().first()
    finally:
        await session.close()

    total_bins = int(area_row.get("total_bins") or 0) if area_row else 0
    occupied = int(stock_row.get("occupied_bins") or 0) if stock_row else 0
    if total_bins <= 0:
        return None
    return round((occupied / total_bins) * 100.0, 1)


class WarehouseDashboardBuilder:
    async def build(
        self,
        wh_code: Optional[str],
        locale: str,
        lookback_days: int,
        context: MCPContext,
    ) -> AssistantDashboardResponse:
        ref_date = _reference_datetime()
        inv_params = InventoryStatusParams(wh_code=wh_code)
        obs_params = ObsoleteProfileParams(wh_code=wh_code, dull_days_threshold=90)

        inventory_result, obsolete_result, summary, age_buckets, bin_util = (
            await asyncio.gather(
                get_inventory_status_tool.run(inv_params, context),
                profile_obsolete_inventory_tool.run(obs_params, context),
                _fetch_stock_summary(wh_code, ref_date),
                _fetch_age_buckets(wh_code, ref_date),
                _fetch_bin_utilization(wh_code),
            )
        )

        inv_data = tool_data(inventory_result) or {}
        low_stock_items = inv_data.get("low_stock") or []

        kpis = self._build_kpis(summary, len(low_stock_items), locale)
        charts = self._build_charts(summary, age_buckets, bin_util, locale)
        partial = any(
            slot.source == DataSource.FALLBACK for slot in (*kpis, *charts)
        )
        insight = self._build_insight(kpis, charts, wh_code, locale, summary)

        return AssistantDashboardResponse(
            module="warehouse",
            wh_code=wh_code,
            kpis=kpis,
            charts=charts,
            insight=insight,
            partial=partial,
            generated_at=datetime.utcnow(),
        )

    def _build_kpis(
        self,
        summary: dict[str, Any],
        pick_tasks: int,
        locale: str,
    ) -> list[DashboardKpiSlot]:
        kpis: list[DashboardKpiSlot] = []

        accuracy = summary.get("accuracy_pct")
        if accuracy is not None and summary.get("total", 0) > 0:
            kpis.append(
                DashboardKpiSlot(
                    index=0,
                    value=format_percent(float(accuracy)),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(0))

        avg_turnover = summary.get("avg_turnover_days")
        if avg_turnover is not None and avg_turnover > 0:
            kpis.append(
                DashboardKpiSlot(
                    index=1,
                    value=f"{round(float(avg_turnover), 1)}",
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(1))

        if summary.get("total", 0) >= 0:
            kpis.append(
                DashboardKpiSlot(
                    index=2,
                    value=str(pick_tasks),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(2))

        return kpis

    def _build_charts(
        self,
        summary: dict[str, Any],
        age_buckets: list[int],
        bin_util: Optional[float],
        locale: str,
    ) -> list[DashboardChartSlot]:
        charts: list[DashboardChartSlot] = []
        zh = locale.startswith("zh")

        charts.append(fallback_chart(0, "bar"))

        healthy = summary.get("healthy", 0)
        low_stock = summary.get("low_stock", 0)
        expiring = summary.get("expiring", 0)
        if summary.get("total", 0) > 0:
            charts.append(
                DashboardChartSlot(
                    index=1,
                    chart_type="bar",
                    x_data=(
                        ["正常", "低库存", "临期"]
                        if zh
                        else ["Healthy", "Low stock", "Expiring"]
                    ),
                    series=[float(healthy), float(low_stock), float(expiring)],
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(1, "bar"))

        if bin_util is not None and bin_util > 0:
            charts.append(
                DashboardChartSlot(
                    index=2,
                    chart_type="gauge",
                    gauge_value=min(max(bin_util, 0), 100),
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(2, "gauge"))

        if any(age_buckets):
            charts.append(
                DashboardChartSlot(
                    index=3,
                    chart_type="bar",
                    x_data=AGE_BUCKET_LABELS_ZH if zh else AGE_BUCKET_LABELS_EN,
                    series=[float(v) for v in age_buckets],
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(3, "bar"))

        charts.append(fallback_chart(4, "line"))
        charts.append(fallback_chart(5, "gauge"))

        return charts

    def _build_insight(
        self,
        kpis: list[DashboardKpiSlot],
        charts: list[DashboardChartSlot],
        wh_code: Optional[str],
        locale: str,
        summary: dict[str, Any],
    ) -> str:
        scope = wh_code or ("全部仓库" if locale.startswith("zh") else "all warehouses")
        kpi0 = next((k for k in kpis if k.index == 0 and k.source == DataSource.LIVE), None)
        kpi1 = next((k for k in kpis if k.index == 1 and k.source == DataSource.LIVE), None)
        low = summary.get("low_stock", 0)

        if locale.startswith("zh"):
            parts = [f"仓库 {scope} 库存扫描完成。"]
            if kpi0:
                parts.append(f"库存准确率约 {kpi0.value}。")
            if kpi1:
                parts.append(f"平均周转 {kpi1.value} 天。")
            if low:
                parts.append(f"低库存物料 {low} 项需关注。")
            parts.append("可通过右侧 AI 助手查询补货、呆滞与出入库建议。")
            return " ".join(parts)

        parts = [f"Inventory scan for {scope} is ready."]
        if kpi0:
            parts.append(f"Accuracy is about {kpi0.value}.")
        if kpi1:
            parts.append(f"Average turnover is {kpi1.value} days.")
        if low:
            parts.append(f"{low} low-stock items need attention.")
        parts.append("Use the AI assistant for replenishment and obsolete stock analysis.")
        return " ".join(parts)


warehouse_dashboard_builder = WarehouseDashboardBuilder()
