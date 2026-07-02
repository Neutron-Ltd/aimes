"""Quality assistant dashboard snapshot — MCP tools + QM SQL aggregations."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.dashboard.base import (
    bucket_label,
    fallback_chart,
    fallback_kpi,
    format_percent,
    resolve_date_range,
    tool_data,
)
from models.dashboard import (
    AssistantDashboardResponse,
    DashboardChartSlot,
    DashboardKpiSlot,
    DataSource,
)
from models.intents.quality import DefectAggregationParams, QualityRootCauseParams
from models.schemas import MCPContext
from mcp_tools.quality_tools import (
    analyze_defect_root_cause_tool,
    get_quality_defect_aggregation_tool,
)


def _area_filter(line_id: Optional[str], alias: str = "qi") -> tuple[str, dict[str, Any]]:
    if not line_id:
        return "", {}
    return f" AND {alias}.area_sn = :line_id", {"line_id": line_id}


async def _fetch_daily_defect_rates(
    session: AsyncSession,
    line_id: Optional[str],
    start: datetime,
    end: datetime,
) -> tuple[list[str], list[float]]:
    area_sql, area_bind = _area_filter(line_id, "qi")
    sql = text(
        f"""
        SELECT DATE(qi.test_start_time) AS bucket,
               SUM(COALESCE(qi.real_qty, 0)) AS inspected,
               SUM(COALESCE(qi.error_qty, 0)) AS defects
        FROM n2admin.t_qm_inspect_info qi
        WHERE qi.test_start_time BETWEEN :start_date AND :end_date
        {area_sql}
        GROUP BY DATE(qi.test_start_time)
        ORDER BY bucket
        """
    )
    bind = {"start_date": start, "end_date": end, **area_bind}
    rows = (await session.execute(sql, bind)).mappings().all()

    labels: list[str] = []
    series: list[float] = []
    for row in rows:
        inspected = float(row.get("inspected") or 0)
        defects = float(row.get("defects") or 0)
        if inspected <= 0:
            continue
        labels.append(str(row.get("bucket") or "")[:10])
        series.append(round((defects / inspected) * 100.0, 2))
    return labels, series


async def _fetch_problem_summary(
    session: AsyncSession,
    line_id: Optional[str],
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    sql = text(
        """
        SELECT close_time
        FROM n2admin.t_qm_problem_report pr
        WHERE pr.create_time BETWEEN :start_date AND :end_date
        """
    )
    bind = {"start_date": start, "end_date": end}
    rows = (await session.execute(sql, bind)).mappings().all()

    total = len(rows)
    closed = sum(1 for row in rows if row.get("close_time") is not None)
    closure_rate = (closed / total * 100.0) if total else None
    return {
        "abnormal_count": total,
        "closed_count": closed,
        "closure_rate": closure_rate,
    }


class QualityDashboardBuilder:
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

        defect_params = DefectAggregationParams(
            line_id=line_id,
            start_date=start,
            end_date=end,
        )
        root_cause_params = QualityRootCauseParams(
            start_date=start,
            end_date=end,
        )

        defect_result = await get_quality_defect_aggregation_tool.run(
            defect_params, context, session=session
        )
        root_cause_result = await analyze_defect_root_cause_tool.run(
            root_cause_params, context, session=session
        )
        daily_result = await _fetch_daily_defect_rates(session, line_id, start, end)
        problem_summary = await _fetch_problem_summary(session, line_id, start, end)

        daily_labels, daily_rates = daily_result

        defect_data = tool_data(defect_result) or {}
        root_cause_data = tool_data(root_cause_result) or {}

        kpis = self._build_kpis(defect_data, problem_summary)
        charts = self._build_charts(
            defect_data,
            root_cause_data,
            daily_labels,
            daily_rates,
            daily_labels,
            daily_rates,
            locale,
        )
        partial = any(
            slot.source == DataSource.FALLBACK for slot in (*kpis, *charts)
        )
        insight = self._build_insight(kpis, defect_data, problem_summary, line_id, locale)

        return AssistantDashboardResponse(
            module="quality",
            line_id=line_id,
            kpis=kpis,
            charts=charts,
            insight=insight,
            partial=partial,
            generated_at=datetime.utcnow(),
        )

    def _build_kpis(
        self,
        defect_data: dict[str, Any],
        problem_summary: dict[str, Any],
    ) -> list[DashboardKpiSlot]:
        kpis: list[DashboardKpiSlot] = []

        defect_rate = float(defect_data.get("defect_rate") or 0)
        if defect_data.get("total_inspected", 0) > 0 and defect_rate >= 0:
            fpy = max(100.0 - defect_rate, 0.0)
            kpis.append(
                DashboardKpiSlot(
                    index=0,
                    value=format_percent(fpy),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(0))

        abnormal = int(problem_summary.get("abnormal_count") or 0)
        if problem_summary.get("abnormal_count") is not None:
            kpis.append(
                DashboardKpiSlot(
                    index=1,
                    value=str(abnormal),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(1))

        closure_rate = problem_summary.get("closure_rate")
        if closure_rate is not None and problem_summary.get("abnormal_count", 0) > 0:
            kpis.append(
                DashboardKpiSlot(
                    index=2,
                    value=format_percent(float(closure_rate)),
                    trend=None,
                    source=DataSource.LIVE,
                )
            )
        else:
            kpis.append(fallback_kpi(2))

        return kpis

    def _build_charts(
        self,
        defect_data: dict[str, Any],
        root_cause_data: dict[str, Any],
        daily_labels: list[str],
        daily_rates: list[float],
        rework_labels: list[str],
        rework_rates: list[float],
        locale: str,
    ) -> list[DashboardChartSlot]:
        charts: list[DashboardChartSlot] = []

        if daily_rates:
            charts.append(
                DashboardChartSlot(
                    index=0,
                    chart_type="line",
                    x_data=[
                        bucket_label(label, locale) for label in daily_labels
                    ],
                    series=daily_rates,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(0, "line"))

        hypotheses = root_cause_data.get("hypotheses") or []
        if hypotheses:
            counter: Counter[str] = Counter()
            for item in hypotheses:
                label = (item.get("reason") or item.get("problem") or "").strip()
                if not label:
                    continue
                counter[label[:16]] += int(float(item.get("score") or 1) * 10) or 1
            top = counter.most_common()
            if top:
                charts.append(
                    DashboardChartSlot(
                        index=1,
                        chart_type="bar",
                        x_data=[name for name, _ in top],
                        series=[float(count) for _, count in top],
                        source=DataSource.LIVE,
                    )
                )
            else:
                charts.append(fallback_chart(1, "bar"))
        else:
            charts.append(fallback_chart(1, "bar"))

        defect_rate = float(defect_data.get("defect_rate") or 0)
        if defect_data.get("total_inspected", 0) > 0:
            health = max(100.0 - defect_rate, 0.0)
            if health > 0:
                charts.append(
                    DashboardChartSlot(
                        index=2,
                        chart_type="gauge",
                        gauge_value=health,
                        source=DataSource.LIVE,
                    )
                )
            else:
                charts.append(fallback_chart(2, "gauge"))
        else:
            charts.append(fallback_chart(2, "gauge"))

        if rework_rates:
            charts.append(
                DashboardChartSlot(
                    index=3,
                    chart_type="line",
                    x_data=[
                        bucket_label(label, locale) for label in rework_labels
                    ],
                    series=rework_rates,
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(3, "line"))

        breakdown = defect_data.get("breakdown") or []
        if breakdown:
            charts.append(
                DashboardChartSlot(
                    index=4,
                    chart_type="bar",
                    x_data=[
                        str(item.get("process_code") or f"P{i + 1}")
                        for i, item in enumerate(breakdown)
                    ],
                    series=[
                        max(100.0 - float(item.get("defect_rate") or 0), 0.0)
                        for item in breakdown
                    ],
                    source=DataSource.LIVE,
                )
            )
        else:
            charts.append(fallback_chart(4, "bar"))

        charts.append(fallback_chart(5, "gauge"))

        return charts

    def _build_insight(
        self,
        kpis: list[DashboardKpiSlot],
        defect_data: dict[str, Any],
        problem_summary: dict[str, Any],
        line_id: Optional[str],
        locale: str,
    ) -> str:
        scope = line_id or ("全部产线" if locale.startswith("zh") else "all lines")
        kpi0 = next((k for k in kpis if k.index == 0 and k.source == DataSource.LIVE), None)
        abnormal = int(problem_summary.get("abnormal_count") or 0)
        defect_rate = float(defect_data.get("defect_rate") or 0)

        if locale.startswith("zh"):
            parts = [f"质量域 {scope} 最新扫描完成。"]
            if kpi0:
                parts.append(f"一次合格率 {kpi0.value}。")
            if defect_rate > 0:
                parts.append(f"不良率 {round(defect_rate, 1)}%。")
            if abnormal:
                parts.append(f"异常批次 {abnormal} 项。")
            parts.append("可通过右侧 AI 助手深入分析缺陷根因与改善措施。")
            return " ".join(parts)

        parts = [f"Quality scan for {scope} is ready."]
        if kpi0:
            parts.append(f"First pass yield is {kpi0.value}.")
        if defect_rate > 0:
            parts.append(f"Defect rate is {round(defect_rate, 1)}%.")
        if abnormal:
            parts.append(f"{abnormal} abnormal lots recorded.")
        parts.append("Use the AI assistant for root-cause and improvement analysis.")
        return " ".join(parts)


quality_dashboard_builder = QualityDashboardBuilder()
