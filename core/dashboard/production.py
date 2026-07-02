"""Production assistant dashboard snapshot — direct MCP tool calls."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
from models.dashboard import (
    AssistantDashboardResponse,
    DashboardChartSlot,
    DashboardKpiSlot,
    DataSource,
)
from models.intents.production import CapacityForecastParams, DeviceRateParams
from models.schemas import MCPContext
from mcp_tools.production_engines import forecast_capacity_hr_tool
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

DEFECT_CHART_MONTHS = 6


def _month_window(months: int) -> tuple[datetime, datetime]:
    settings = get_settings()
    ref_end = settings.dashboard_reference_date
    end_day = min(date.today(), ref_end)
    end = datetime.combine(end_day, datetime.max.time()).replace(microsecond=0)
    year, month = end.year, end.month
    start_month = month - (months - 1)
    start_year = year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start = datetime.combine(date(start_year, start_month, 1), datetime.min.time())
    return start, end


def _month_bucket_label(bucket: Any, locale: str) -> str:
    if bucket is None:
        return ""
    if isinstance(bucket, datetime):
        dt = bucket
    else:
        text_val = str(bucket)
        try:
            dt = datetime.fromisoformat(text_val.replace("Z", "+00:00"))
        except ValueError:
            return text_val[:7]
    if locale.startswith("zh"):
        return f"{dt.month}月"
    return dt.strftime("%b")


def _line_area_filter(line_id: Optional[str]) -> tuple[str, dict[str, Any]]:
    if not line_id:
        return "", {}
    return " AND line.area_sn = :line_id", {"line_id": line_id}


async def _fetch_monthly_defect_counts(
    session: AsyncSession,
    line_id: Optional[str],
    locale: str,
    months: int = DEFECT_CHART_MONTHS,
) -> tuple[list[str], list[float]]:
    start, end = _month_window(months)
    line_sql, line_bind = _line_area_filter(line_id)
    sql = text(
        f"""
        SELECT date_trunc('month', COALESCE(wd.in_time, wd.create_time)) AS bucket,
               SUM(COALESCE(wd.ng_qty, 0) + COALESCE(wd.scrap_qty, 0)) AS defect_qty
        FROM n2admin.t_wip_detail wd
        JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
        JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
        WHERE COALESCE(wd.in_time, wd.create_time) BETWEEN :start_date AND :end_date
        {line_sql}
        GROUP BY date_trunc('month', COALESCE(wd.in_time, wd.create_time))
        ORDER BY bucket
        """
    )
    rows = (
        await session.execute(
            sql,
            {"start_date": start, "end_date": end, **line_bind},
        )
    ).mappings().all()

    labels: list[str] = []
    series: list[float] = []
    for row in rows:
        qty = float(row.get("defect_qty") or 0)
        if qty <= 0:
            continue
        labels.append(_month_bucket_label(row.get("bucket"), locale))
        series.append(round(qty, 1))
    return labels, series


class ProductionDashboardBuilder:
    async def build(
        self,
        line_id: Optional[str],
        locale: str,
        lookback_days: int,
        context: MCPContext,
        *,
        session: AsyncSession,
    ) -> AssistantDashboardResponse:
        start, end = resolve_date_range(lookback_days)
        prev_start, prev_end = previous_period(start, end)

        achievement_total = await get_yield_aggregation_tool.run(
            YieldAggregationParams(
                yield_type=YieldType.EQUIPMENT,
                line_id=line_id,
                start_date=start,
                end_date=end,
                group_by=GroupBy.TOTAL,
                metric=Metric.ACHIEVEMENT_RATE,
            ),
            context,
            session=session,
        )
        achievement_daily = await get_yield_aggregation_tool.run(
            YieldAggregationParams(
                yield_type=YieldType.EQUIPMENT,
                line_id=line_id,
                start_date=start,
                end_date=end,
                group_by=GroupBy.DAILY,
                metric=Metric.ACHIEVEMENT_RATE,
            ),
            context,
            session=session,
        )
        achievement_prev = await compare_yield_periods_tool.run(
            CompareYieldPeriodsParams(
                yield_type=YieldType.EQUIPMENT,
                line_id=line_id,
                period_1_start=prev_start,
                period_1_end=prev_end,
                period_2_start=start,
                period_2_end=end,
            ),
            context,
            session=session,
        )
        device_rates = await get_device_production_rate_tool.run(
            DeviceRateParams(
                line_id=line_id,
                start_date=start,
                end_date=end,
            ),
            context,
            session=session,
        )
        capacity = await forecast_capacity_hr_tool.run(
            CapacityForecastParams(line_id=line_id, forecast_days=14),
            context,
            session=session,
        )
        anomalies = await get_yield_anomalies_tool.run(
            YieldAnomaliesParams(
                yield_type=YieldType.EQUIPMENT,
                line_id=line_id,
                start_date=start,
                end_date=end,
                analysis_type=AnalysisType.BELOW_STANDARD,
            ),
            context,
            session=session,
        )
        monthly_defects = await _fetch_monthly_defect_counts(session, line_id, locale)

        defect_labels, defect_series = monthly_defects

        kpis = self._build_kpis(
            achievement_total, achievement_prev, device_rates, locale
        )
        charts = self._build_charts(
            achievement_daily,
            device_rates,
            capacity,
            anomalies,
            defect_labels,
            defect_series,
            locale,
        )
        partial = any(
            slot.source == DataSource.FALLBACK for slot in (*kpis, *charts)
        )
        insight = self._build_insight(kpis, charts, line_id, locale)

        return AssistantDashboardResponse(
            module="production",
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
        device_rates: Any,
        locale: str,
    ) -> list[DashboardKpiSlot]:
        kpis: list[DashboardKpiSlot] = []

        ach_data = tool_data(achievement_total)
        prev_data = tool_data(achievement_prev)
        if ach_data and ach_data.get("value") is not None:
            rate = float(ach_data["value"])
            if rate <= 1.0:
                rate *= 100.0
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

        dev_data = tool_data(device_rates)
        devices = (dev_data or {}).get("devices") or []
        if devices:
            avg_rate = sum(float(d.get("avg_rate") or 0) for d in devices) / len(
                devices
            )
            kpis.append(
                DashboardKpiSlot(
                    index=1,
                    value=f"{round(avg_rate, 1)}",
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(1))

        # No MCP tool for WIP orders — always fallback placeholder
        kpis.append(fallback_kpi(2))
        return kpis

    def _build_charts(
        self,
        achievement_daily: Any,
        device_rates: Any,
        capacity: Any,
        anomalies: Any,
        defect_labels: list[str],
        defect_series: list[float],
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

        # Work order status — no direct tool
        charts.append(fallback_chart(1, "bar"))

        cap_data = tool_data(capacity)
        if cap_data and cap_data.get("capacity_utilization") is not None:
            util = float(cap_data["capacity_utilization"])
            if util > 0:
                charts.append(
                    DashboardChartSlot(
                        index=2,
                        chart_type="gauge",
                        gauge_value=min(max(util, 0), 150),
                        source=DataSource.LIVE,
                    )
                )
            else:
                charts.append(fallback_chart(2, "gauge"))
        else:
            charts.append(fallback_chart(2, "gauge"))

        dev_data = tool_data(device_rates)
        devices = (dev_data or {}).get("devices") or []
        if devices:
            charts.append(
                DashboardChartSlot(
                    index=3,
                    chart_type="bar",
                    x_data=[
                        str(d.get("device_name") or d.get("device_sn") or "")[:12]
                        for d in devices
                    ],
                    series=[float(d.get("avg_rate") or 0) for d in devices],
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(3, "bar"))

        if defect_series:
            charts.append(
                DashboardChartSlot(
                    index=4,
                    chart_type="line",
                    x_data=defect_labels,
                    series=defect_series,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(4, "line"))

        anom_data = tool_data(anomalies)
        nested = (anom_data or {}).get("result") or {}
        flagged = nested.get("flagged_buckets") or []
        if flagged:
            charts.append(
                DashboardChartSlot(
                    index=5,
                    chart_type="bar",
                    x_data=[
                        bucket_label(row.get("bucket"), locale) for row in flagged
                    ],
                    series=[
                        float(row.get("achievement_rate") or 0) * 100
                        if float(row.get("achievement_rate") or 0) <= 1
                        else float(row.get("achievement_rate") or 0)
                        for row in flagged
                    ],
                    source=DataSource.LIVE,
                )
            )
        elif nested.get("below_standard_count"):
            count = int(nested["below_standard_count"])
            charts.append(
                DashboardChartSlot(
                    index=5,
                    chart_type="bar",
                    x_data=["Below standard"] if not locale.startswith("zh") else ["未达标"],
                    series=[float(count)],
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(5, "bar"))

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
                return f"{scope} 产线数据暂不可用，请稍后重试或通过 AI 助手提问。"
            return f"Live data for {scope} is unavailable. Try again or ask the AI assistant."

        kpi0 = next((k for k in kpis if k.index == 0), None)
        cap = next(
            (c for c in charts if c.index == 2 and c.source == DataSource.LIVE),
            None,
        )
        if locale.startswith("zh"):
            parts = [f"产线 {scope} 最新扫描完成。"]
            if kpi0:
                parts.append(f"计划达成率 {kpi0.value}。")
            if cap and cap.gauge_value is not None:
                parts.append(f"产能负荷约 {round(cap.gauge_value, 1)}%。")
            parts.append("可通过右侧 AI 助手深入分析排程、瓶颈与异常。")
            return " ".join(parts)

        parts = [f"Latest scan for {scope} is ready."]
        if kpi0:
            parts.append(f"Plan attainment is {kpi0.value}.")
        if cap and cap.gauge_value is not None:
            parts.append(f"Capacity load is about {round(cap.gauge_value, 1)}%.")
        parts.append("Use the AI assistant for scheduling, bottlenecks, and anomalies.")
        return " ".join(parts)


production_dashboard_builder = ProductionDashboardBuilder()
