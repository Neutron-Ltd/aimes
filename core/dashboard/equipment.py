"""Equipment assistant dashboard snapshot — production MCP tools + t_co_device SQL."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from core.config import get_settings
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
from models.intents.production import DeviceRateParams
from models.schemas import MCPContext
from mcp_tools.production_tools import (
    AnalysisType,
    CompareYieldPeriodsParams,
    GroupBy,
    Metric,
    YieldAggregationParams,
    YieldAnomaliesParams,
    YieldType,
    compare_yield_periods_tool,
    get_device_production_rate_tool,
    get_yield_aggregation_tool,
    get_yield_anomalies_tool,
)

DOWNTIME_PROXY_SCALE = 4.0


def _line_filter(line_id: Optional[str]) -> tuple[str, dict[str, Any]]:
    if not line_id:
        return "", {}
    return " AND cd_location = :line_id", {"line_id": line_id}


async def _fetch_device_registry_summary(
    line_id: Optional[str],
) -> dict[str, Any]:
    settings = get_settings()
    ref_date = settings.dashboard_reference_date
    session = await get_session()
    try:
        line_sql, line_bind = _line_filter(line_id)
        sql = text(
            f"""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (
                       WHERE expire_date IS NULL OR expire_date >= :ref_date
                   ) AS valid
            FROM n2admin.t_co_device
            WHERE 1=1
            {line_sql}
            """
        )
        bind = {"ref_date": ref_date, **line_bind}
        row = (await session.execute(sql, bind)).mappings().first()
    finally:
        await session.close()

    total = int(row.get("total") or 0) if row else 0
    valid = int(row.get("valid") or 0) if row else 0
    maintenance_rate = (valid / total * 100.0) if total else None
    return {
        "total": total,
        "valid": valid,
        "maintenance_rate": maintenance_rate,
    }


async def _fetch_active_device_ratio(
    line_id: Optional[str], start: datetime, end: datetime
) -> dict[str, Any]:
    session = await get_session()
    try:
        line_sql, line_bind = _line_filter(line_id)
        sql = text(
            f"""
            WITH registered AS (
                SELECT device_sn
                FROM n2admin.t_co_device
                WHERE 1=1
                {line_sql}
            ),
            active AS (
                SELECT DISTINCT eq.device_sn
                FROM n2admin.t_smt_program_consumption_record eq
                WHERE eq.create_time BETWEEN :start_date AND :end_date
                  AND eq.device_sn IN (SELECT device_sn FROM registered)
            )
            SELECT
                (SELECT COUNT(*) FROM registered) AS total,
                (SELECT COUNT(*) FROM active) AS active
            """
        )
        bind = {"start_date": start, "end_date": end, **line_bind}
        row = (await session.execute(sql, bind)).mappings().first()
    finally:
        await session.close()

    total = int(row.get("total") or 0) if row else 0
    active = int(row.get("active") or 0) if row else 0
    inspection_rate = (active / total * 100.0) if total else None
    return {
        "total": total,
        "active": active,
        "inspection_rate": inspection_rate,
    }


class EquipmentDashboardBuilder:
    async def build(
        self,
        line_id: Optional[str],
        locale: str,
        lookback_days: int,
        context: MCPContext,
    ) -> AssistantDashboardResponse:
        start, end = resolve_date_range(lookback_days)
        prev_start, prev_end = previous_period(start, end)

        (
            achievement_total,
            achievement_daily,
            achievement_prev,
            device_rates,
            anomalies,
            registry_summary,
            active_ratio,
        ) = await asyncio.gather(
            get_yield_aggregation_tool.run(
                YieldAggregationParams(
                    yield_type=YieldType.EQUIPMENT,
                    line_id=line_id,
                    start_date=start,
                    end_date=end,
                    group_by=GroupBy.TOTAL,
                    metric=Metric.ACHIEVEMENT_RATE,
                ),
                context,
            ),
            get_yield_aggregation_tool.run(
                YieldAggregationParams(
                    yield_type=YieldType.EQUIPMENT,
                    line_id=line_id,
                    start_date=start,
                    end_date=end,
                    group_by=GroupBy.DAILY,
                    metric=Metric.ACHIEVEMENT_RATE,
                ),
                context,
            ),
            compare_yield_periods_tool.run(
                CompareYieldPeriodsParams(
                    yield_type=YieldType.EQUIPMENT,
                    line_id=line_id,
                    period_1_start=prev_start,
                    period_1_end=prev_end,
                    period_2_start=start,
                    period_2_end=end,
                ),
                context,
            ),
            get_device_production_rate_tool.run(
                DeviceRateParams(
                    line_id=line_id,
                    start_date=start,
                    end_date=end,
                ),
                context,
            ),
            get_yield_anomalies_tool.run(
                YieldAnomaliesParams(
                    yield_type=YieldType.EQUIPMENT,
                    line_id=line_id,
                    start_date=start,
                    end_date=end,
                    analysis_type=AnalysisType.BELOW_STANDARD,
                ),
                context,
            ),
            _fetch_device_registry_summary(line_id),
            _fetch_active_device_ratio(line_id, start, end),
        )

        kpis = self._build_kpis(achievement_total, achievement_prev, anomalies)
        charts = self._build_charts(
            achievement_daily,
            device_rates,
            registry_summary,
            active_ratio,
            locale,
        )
        partial = any(
            slot.source == DataSource.FALLBACK for slot in (*kpis, *charts)
        )
        insight = self._build_insight(kpis, charts, line_id, locale)

        return AssistantDashboardResponse(
            module="equipment",
            line_id=line_id,
            kpis=kpis,
            charts=charts,
            insight=insight,
            partial=partial,
            generated_at=datetime.utcnow(),
        )

    def _build_kpis(
        self,
        achievement_total: Any,
        achievement_prev: Any,
        anomalies: Any,
    ) -> list[DashboardKpiSlot]:
        kpis: list[DashboardKpiSlot] = []

        ach_data = tool_data(achievement_total)
        prev_data = tool_data(achievement_prev)
        if ach_data and ach_data.get("value") is not None:
            rate = self._normalize_rate(float(ach_data["value"]))
            trend = None
            if prev_data and prev_data.get("growth_rate") is not None:
                trend = format_trend(float(prev_data["growth_rate"]))
            if rate > 0:
                kpis.append(
                    DashboardKpiSlot(
                        index=0,
                        value=format_percent(rate),
                        trend=trend,
                        source=DataSource.LIVE,
                    )
                )
            else:
                kpis.append(fallback_kpi(0))
        else:
            kpis.append(fallback_kpi(0))

        anom_data = tool_data(anomalies)
        nested = (anom_data or {}).get("result") or {}
        alert_count = nested.get("below_standard_count")
        if alert_count is None:
            flagged = nested.get("flagged_buckets") or []
            alert_count = len(flagged) if flagged else None
        if alert_count is not None and int(alert_count) >= 0:
            kpis.append(
                DashboardKpiSlot(
                    index=1,
                    value=str(int(alert_count)),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(1))

        kpis.append(fallback_kpi(2))
        return kpis

    def _build_charts(
        self,
        achievement_daily: Any,
        device_rates: Any,
        registry_summary: dict[str, Any],
        active_ratio: dict[str, Any],
        locale: str,
    ) -> list[DashboardChartSlot]:
        charts: list[DashboardChartSlot] = []

        daily_data = tool_data(achievement_daily)
        breakdown = (daily_data or {}).get("breakdown") or []
        if breakdown:
            charts.append(
                DashboardChartSlot(
                    index=0,
                    chart_type="line",
                    x_data=[
                        bucket_label(row.get("bucket"), locale) for row in breakdown
                    ],
                    series=[
                        self._normalize_rate(float(row.get("value") or 0))
                        for row in breakdown
                    ],
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(0, "line"))

        charts.append(fallback_chart(1, "bar"))

        maintenance_rate = registry_summary.get("maintenance_rate")
        if maintenance_rate is not None and registry_summary.get("total", 0) > 0:
            charts.append(
                DashboardChartSlot(
                    index=2,
                    chart_type="gauge",
                    gauge_value=round(float(maintenance_rate), 1),
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(2, "gauge"))

        dev_data = tool_data(device_rates)
        devices = (dev_data or {}).get("devices") or []
        if devices:
            rates = [float(d.get("avg_rate") or 0) for d in devices]
            max_rate = max(rates) if rates else 0.0
            top = devices[:5]
            if max_rate > 0:
                charts.append(
                    DashboardChartSlot(
                        index=3,
                        chart_type="bar",
                        x_data=[
                            str(d.get("device_name") or d.get("device_sn") or "")[:12]
                            for d in top
                        ],
                        series=[
                            round(
                                (max_rate - float(d.get("avg_rate") or 0))
                                / max_rate
                                * DOWNTIME_PROXY_SCALE,
                                1,
                            )
                            for d in top
                        ],
                        source=DataSource.LIVE,
                    )
                )
            else:
                charts.append(fallback_chart(3, "bar"))
        else:
            charts.append(fallback_chart(3, "bar"))

        charts.append(fallback_chart(4, "line"))

        inspection_rate = active_ratio.get("inspection_rate")
        if inspection_rate is not None and active_ratio.get("total", 0) > 0:
            charts.append(
                DashboardChartSlot(
                    index=5,
                    chart_type="gauge",
                    gauge_value=round(float(inspection_rate), 1),
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(5, "gauge"))

        return charts

    @staticmethod
    def _normalize_rate(value: float) -> float:
        if value <= 1.0:
            return round(value * 100, 2)
        return round(value, 2)

    def _build_insight(
        self,
        kpis: list[DashboardKpiSlot],
        charts: list[DashboardChartSlot],
        line_id: Optional[str],
        locale: str,
    ) -> str:
        scope = line_id or ("全部产线" if locale.startswith("zh") else "all lines")
        live_kpis = [k for k in kpis if k.source == DataSource.LIVE]
        if not live_kpis:
            if locale.startswith("zh"):
                return f"设备域 {scope} 数据暂不可用，请稍后重试或通过 AI 助手提问。"
            return f"Equipment data for {scope} is unavailable. Try again or ask the AI assistant."

        kpi0 = next((k for k in kpis if k.index == 0 and k.source == DataSource.LIVE), None)
        kpi1 = next((k for k in kpis if k.index == 1 and k.source == DataSource.LIVE), None)
        maint = next(
            (c for c in charts if c.index == 2 and c.source == DataSource.LIVE),
            None,
        )

        if locale.startswith("zh"):
            parts = [f"设备域 {scope} 最新扫描完成。"]
            if kpi0:
                parts.append(f"设备健康度 {kpi0.value}。")
            if kpi1:
                parts.append(f"预测告警 {kpi1.value} 项。")
            if maint and maint.gauge_value is not None:
                parts.append(f"维护完成率约 {round(maint.gauge_value, 1)}%。")
            parts.append("可通过右侧 AI 助手深入分析设备异常与维护建议。")
            return " ".join(parts)

        parts = [f"Equipment scan for {scope} is ready."]
        if kpi0:
            parts.append(f"Equipment health is {kpi0.value}.")
        if kpi1:
            parts.append(f"{kpi1.value} predicted alerts.")
        if maint and maint.gauge_value is not None:
            parts.append(f"Maintenance completion is about {round(maint.gauge_value, 1)}%.")
        parts.append("Use the AI assistant for anomaly and maintenance analysis.")
        return " ".join(parts)


equipment_dashboard_builder = EquipmentDashboardBuilder()
