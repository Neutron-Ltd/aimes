"""
Phase 2 — Production Data MCP Tool Arsenal (Token-Optimized).

Three flexible tools cover standard aggregation, anomaly detection, and
period comparison. The LLM passes structured parameters only; SQL is
predefined and table-routed — never LLM-generated.

Table routing:
  equipment → n2admin.t_smt_program_consumption_record via t_co_device.cd_location or device_sn
  reported  → n2admin.t_wip_detail JOIN t_co_area (line.area_sn = line_id)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.logging import get_logger
from core.math_safeguard import period_over_period_growth_rate, population_std_dev
from mcp_tools.base import BaseMCPTool
from models.schemas import MCPContext

logger = get_logger(__name__)

DEFAULT_BELOW_STANDARD_THRESHOLD = 90.0


# ---------------------------------------------------------------------------
# Enums & Pydantic schemas (LLM-facing tool parameters)
# ---------------------------------------------------------------------------


class YieldType(str, Enum):
    EQUIPMENT = "equipment"
    REPORTED = "reported"


class GroupBy(str, Enum):
    DAILY = "daily"
    HOURLY = "hourly"
    TOTAL = "total"


class Metric(str, Enum):
    SUM = "sum"
    AVERAGE = "average"
    ACHIEVEMENT_RATE = "achievement_rate"


class AnalysisType(str, Enum):
    VOLATILITY = "volatility"
    BELOW_STANDARD = "below_standard"
    PEAK_HOURLY = "peak_hourly"


class YieldAggregationParams(BaseModel):
    yield_type: YieldType
    line_id: Optional[str] = None
    device_sn: Optional[str] = None
    start_date: datetime
    end_date: datetime
    group_by: GroupBy
    metric: Metric


class YieldAggregationResult(BaseModel):
    yield_type: str
    line_id: Optional[str] = None
    device_sn: Optional[str] = None
    metric: str
    group_by: str
    value: float
    breakdown: list[dict[str, Any]] = Field(default_factory=list)
    workshop_id: str


class YieldAnomaliesParams(BaseModel):
    yield_type: YieldType
    line_id: Optional[str] = None
    device_sn: Optional[str] = None
    start_date: datetime
    end_date: datetime
    analysis_type: AnalysisType
    threshold_percentage: Optional[float] = None


class YieldAnomaliesResult(BaseModel):
    yield_type: str
    line_id: Optional[str] = None
    device_sn: Optional[str] = None
    analysis_type: str
    workshop_id: str
    result: dict[str, Any]


class CompareYieldPeriodsParams(BaseModel):
    yield_type: YieldType
    line_id: Optional[str] = None
    device_sn: Optional[str] = None
    period_1_start: datetime
    period_1_end: datetime
    period_2_start: datetime
    period_2_end: datetime


class CompareYieldPeriodsResult(BaseModel):
    yield_type: str
    line_id: Optional[str] = None
    device_sn: Optional[str] = None
    workshop_id: str
    period_1_total: float
    period_2_total: float
    growth_rate: Optional[float] = None


# ---------------------------------------------------------------------------
# SQL routing helpers
# ---------------------------------------------------------------------------


def build_yield_from_clause(yield_type: YieldType) -> str:
    """
    Route yield_type to the correct table(s).

    equipment: consumption records — scoped by device_sn / t_co_device.cd_location
               (area_sn on eq is often NULL in raw machine logs).
    reported:  join wip workstation records up to the parent line node
               in t_co_area — never filter t_wip_detail by line directly.
    """
    if yield_type == YieldType.EQUIPMENT:
        return "n2admin.t_smt_program_consumption_record eq"
    return """
        n2admin.t_wip_detail wd
        JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
        JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
    """


def _equipment_scope_filter(line_id: Optional[str], device_sn: Optional[str]) -> str:
    """
    Filter equipment consumption rows without using eq.area_sn (often NULL).

    Prefer direct device_sn; otherwise resolve devices registered at cd_location = line_id.
    """
    if device_sn:
        return "eq.device_sn = :device_sn"
    if line_id:
        return """eq.device_sn IN (
            SELECT device_sn FROM n2admin.t_co_device
            WHERE cd_location = :line_id
              AND data_auth = :workshop_id
        )"""
    return "1=0"


def _line_filter(
    yield_type: YieldType,
    line_id: Optional[str] = None,
    device_sn: Optional[str] = None,
) -> str:
    if yield_type == YieldType.EQUIPMENT:
        return _equipment_scope_filter(line_id, device_sn)
    return "line.area_sn = :line_id"


def _rbac_filter(yield_type: YieldType) -> str:
    if yield_type == YieldType.EQUIPMENT:
        return "eq.data_auth = :workshop_id"
    return "wd.data_auth = :workshop_id"


def _time_column(yield_type: YieldType) -> str:
    if yield_type == YieldType.EQUIPMENT:
        return "eq.create_time"
    return "COALESCE(wd.in_time, wd.create_time)"


def _build_aggregation_sql(
    yield_type: YieldType,
    group_by: GroupBy,
    *,
    line_id: Optional[str] = None,
    device_sn: Optional[str] = None,
) -> str:
    """
    Build a parameterized SELECT that fetches raw numeric rows for Python
    safeguard computation. group_by controls date_trunc bucketing.
    """
    from_clause = build_yield_from_clause(yield_type)
    time_col = _time_column(yield_type)
    scope_filter = _line_filter(yield_type, line_id=line_id, device_sn=device_sn)
    rbac_filter = _rbac_filter(yield_type)

    if yield_type == YieldType.EQUIPMENT:
        qty_expr = "COALESCE(eq.finish_qty, 0)"
        denom_expr = "COALESCE(eq.mount_sheet_qty, 0)"
        time_range = f"{time_col} BETWEEN :start_date AND :end_date"
    else:
        qty_expr = "COALESCE(wd.pro_qty, 0)"
        good_expr = (
            "COALESCE(wd.pro_qty, 0) - COALESCE(wd.ng_qty, 0) - COALESCE(wd.scrap_qty, 0)"
        )
        denom_expr = "COALESCE(wd.pro_qty, 0)"
        time_range = f"{time_col} BETWEEN :start_date AND :end_date"

    if group_by == GroupBy.TOTAL:
        if yield_type == YieldType.EQUIPMENT:
            select_cols = f"""
                SUM({qty_expr}) AS qty,
                SUM({denom_expr}) AS denom
            """
        else:
            select_cols = f"""
                SUM({good_expr}) AS good_qty,
                SUM({denom_expr}) AS denom
            """
        return f"""
            SELECT {select_cols}
            FROM {from_clause}
            WHERE {scope_filter}
              AND {rbac_filter}
              AND {time_range}
        """

    trunc_unit = "day" if group_by == GroupBy.DAILY else "hour"
    bucket = f"date_trunc('{trunc_unit}', {time_col})"

    if yield_type == YieldType.EQUIPMENT:
        select_cols = f"""
            {bucket} AS bucket,
            SUM({qty_expr}) AS qty,
            SUM({denom_expr}) AS denom
        """
    else:
        select_cols = f"""
            {bucket} AS bucket,
            SUM({good_expr}) AS good_qty,
            SUM({denom_expr}) AS denom
        """

    return f"""
        SELECT {select_cols}
        FROM {from_clause}
        WHERE {scope_filter}
          AND {rbac_filter}
          AND {time_range}
        GROUP BY {bucket}
        ORDER BY {bucket}
    """


async def _fetch_aggregation_rows(
    session: AsyncSession,
    *,
    yield_type: YieldType,
    line_id: Optional[str],
    device_sn: Optional[str],
    workshop_id: str,
    start_date: datetime,
    end_date: datetime,
    group_by: GroupBy,
) -> list[dict[str, Any]]:
    sql = text(
        _build_aggregation_sql(
            yield_type, group_by, line_id=line_id, device_sn=device_sn
        )
    )
    bind: dict[str, Any] = {
        "workshop_id": workshop_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    if line_id:
        bind["line_id"] = line_id
    if device_sn:
        bind["device_sn"] = device_sn
    result = await session.execute(sql, bind)
    return [dict(row) for row in result.mappings().all()]


def _row_qty(row: dict[str, Any], yield_type: YieldType) -> float:
    if yield_type == YieldType.EQUIPMENT:
        return float(row.get("qty") or 0)
    return float(row.get("good_qty") or 0)


def _row_achievement_rate(row: dict[str, Any], yield_type: YieldType) -> float:
    if yield_type == YieldType.EQUIPMENT:
        qty = float(row.get("qty") or 0)
        denom = float(row.get("denom") or 0)
    else:
        qty = float(row.get("good_qty") or 0)
        denom = float(row.get("denom") or 0)
    if denom == 0:
        return 0.0
    return (qty / denom) * 100.0


def _compute_metric(
    rows: list[dict[str, Any]],
    yield_type: YieldType,
    metric: Metric,
    group_by: GroupBy,
) -> tuple[float, list[dict[str, Any]]]:
    """Python safeguard — all aggregate math happens here, not in the LLM."""
    breakdown: list[dict[str, Any]] = []

    if group_by != GroupBy.TOTAL:
        for row in rows:
            bucket = row.get("bucket")
            entry: dict[str, Any] = {"bucket": bucket.isoformat() if bucket else None}
            if metric == Metric.ACHIEVEMENT_RATE:
                entry["value"] = round(_row_achievement_rate(row, yield_type), 4)
            else:
                entry["value"] = _row_qty(row, yield_type)
            breakdown.append(entry)

    if not rows:
        return 0.0, breakdown

    if metric == Metric.SUM:
        if group_by == GroupBy.TOTAL:
            return _row_qty(rows[0], yield_type), breakdown
        return sum(_row_qty(r, yield_type) for r in rows), breakdown

    if metric == Metric.AVERAGE:
        if group_by == GroupBy.TOTAL:
            return _row_qty(rows[0], yield_type), breakdown
        values = [_row_qty(r, yield_type) for r in rows]
        return sum(values) / len(values) if values else 0.0, breakdown

    # achievement_rate — computed from period totals
    if group_by == GroupBy.TOTAL:
        rate = _row_achievement_rate(rows[0], yield_type)
    else:
        total_good = sum(
            float(r.get("good_qty") or r.get("qty") or 0) for r in rows
        )
        total_denom = sum(float(r.get("denom") or 0) for r in rows)
        rate = (total_good / total_denom * 100.0) if total_denom else 0.0

    return round(rate, 4), breakdown


async def _fetch_period_total(
    session: AsyncSession,
    *,
    yield_type: YieldType,
    line_id: Optional[str],
    device_sn: Optional[str],
    workshop_id: str,
    start_date: datetime,
    end_date: datetime,
) -> float:
    rows = await _fetch_aggregation_rows(
        session,
        yield_type=yield_type,
        line_id=line_id,
        device_sn=device_sn,
        workshop_id=workshop_id,
        start_date=start_date,
        end_date=end_date,
        group_by=GroupBy.TOTAL,
    )
    value, _ = _compute_metric(rows, yield_type, Metric.SUM, GroupBy.TOTAL)
    return value


# ---------------------------------------------------------------------------
# Tool 1: get_yield_aggregation
# ---------------------------------------------------------------------------


class GetYieldAggregationTool(BaseMCPTool[YieldAggregationParams, YieldAggregationResult]):
    name = "get_yield_aggregation"
    description = (
        "Standard production yield queries: totals, averages, and achievement rates "
        "grouped by day, hour, or as a single total."
    )

    async def execute(
        self, params: YieldAggregationParams, context: MCPContext
    ) -> YieldAggregationResult:
        session = await get_session()
        try:
            rows = await _fetch_aggregation_rows(
                session,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
                workshop_id=context.workshop_id,
                start_date=params.start_date,
                end_date=params.end_date,
                group_by=params.group_by,
            )
            value, breakdown = _compute_metric(
                rows, params.yield_type, params.metric, params.group_by
            )
            return YieldAggregationResult(
                yield_type=params.yield_type.value,
                line_id=params.line_id,
                device_sn=params.device_sn,
                metric=params.metric.value,
                group_by=params.group_by.value,
                value=round(value, 4),
                breakdown=breakdown,
                workshop_id=context.workshop_id,
            )
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tool 2: get_yield_anomalies_and_peaks
# ---------------------------------------------------------------------------


class GetYieldAnomaliesAndPeaksTool(
    BaseMCPTool[YieldAnomaliesParams, YieldAnomaliesResult]
):
    name = "get_yield_anomalies_and_peaks"
    description = (
        "Statistical outlier detection: volatility (std dev), below-standard "
        "buckets, and peak hourly throughput."
    )

    async def execute(
        self, params: YieldAnomaliesParams, context: MCPContext
    ) -> YieldAnomaliesResult:
        session = await get_session()
        try:
            # Hourly series for anomaly analysis
            rows = await _fetch_aggregation_rows(
                session,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
                workshop_id=context.workshop_id,
                start_date=params.start_date,
                end_date=params.end_date,
                group_by=GroupBy.HOURLY,
            )

            series = [_row_qty(r, params.yield_type) for r in rows]
            result: dict[str, Any] = {}

            if params.analysis_type == AnalysisType.VOLATILITY:
                # Feature 5.2 — population std dev computed in Python
                result = {
                    "volatility_std_dev": round(population_std_dev(series), 4),
                    "bucket_count": len(series),
                    "mean": round(sum(series) / len(series), 4) if series else 0.0,
                }

            elif params.analysis_type == AnalysisType.BELOW_STANDARD:
                threshold = (
                    params.threshold_percentage or DEFAULT_BELOW_STANDARD_THRESHOLD
                )
                # Compare each hourly bucket's achievement rate to threshold
                daily_rows = await _fetch_aggregation_rows(
                    session,
                    yield_type=params.yield_type,
                    line_id=params.line_id,
                    device_sn=params.device_sn,
                    workshop_id=context.workshop_id,
                    start_date=params.start_date,
                    end_date=params.end_date,
                    group_by=GroupBy.HOURLY,
                )
                flagged = []
                for row in daily_rows:
                    rate = _row_achievement_rate(row, params.yield_type)
                    if rate < threshold:
                        bucket = row.get("bucket")
                        flagged.append(
                            {
                                "bucket": bucket.isoformat() if bucket else None,
                                "achievement_rate": round(rate, 4),
                                "threshold": threshold,
                            }
                        )
                result = {
                    "threshold_percentage": threshold,
                    "below_standard_count": len(flagged),
                    "flagged_buckets": flagged,
                }

            elif params.analysis_type == AnalysisType.PEAK_HOURLY:
                if not rows:
                    result = {"peak_hour": None, "peak_value": 0.0}
                else:
                    peak_row = max(rows, key=lambda r: _row_qty(r, params.yield_type))
                    bucket = peak_row.get("bucket")
                    result = {
                        "peak_hour": bucket.isoformat() if bucket else None,
                        "peak_value": round(
                            _row_qty(peak_row, params.yield_type), 4
                        ),
                    }

            return YieldAnomaliesResult(
                yield_type=params.yield_type.value,
                line_id=params.line_id,
                device_sn=params.device_sn,
                analysis_type=params.analysis_type.value,
                workshop_id=context.workshop_id,
                result=result,
            )
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tool 3: compare_yield_periods
# ---------------------------------------------------------------------------


class CompareYieldPeriodsTool(
    BaseMCPTool[CompareYieldPeriodsParams, CompareYieldPeriodsResult]
):
    name = "compare_yield_periods"
    description = (
        "Period-over-period yield comparison with server-side growth rate calculation."
    )

    async def execute(
        self, params: CompareYieldPeriodsParams, context: MCPContext
    ) -> CompareYieldPeriodsResult:
        session = await get_session()
        try:
            period_1_total = await _fetch_period_total(
                session,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
                workshop_id=context.workshop_id,
                start_date=params.period_1_start,
                end_date=params.period_1_end,
            )
            period_2_total = await _fetch_period_total(
                session,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
                workshop_id=context.workshop_id,
                start_date=params.period_2_start,
                end_date=params.period_2_end,
            )

            # Feature 5.2 — growth rate computed in Python, not by LLM
            growth = period_over_period_growth_rate(period_2_total, period_1_total)

            return CompareYieldPeriodsResult(
                yield_type=params.yield_type.value,
                line_id=params.line_id,
                device_sn=params.device_sn,
                workshop_id=context.workshop_id,
                period_1_total=round(period_1_total, 4),
                period_2_total=round(period_2_total, 4),
                growth_rate=round(growth, 4) if growth is not None else None,
            )
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tool 4: get_product_yield (t_co_item join)
# ---------------------------------------------------------------------------


class GetProductYieldTool(BaseMCPTool):
    name = "get_product_yield"
    description = "Product-specific reported yield per line with t_co_item metadata."

    async def execute(self, params, context: MCPContext):
        from models.intents.production import ProductYieldParams, ProductYieldResult

        session = await get_session()
        try:
            sql = text(
                """
                SELECT date_trunc('day', COALESCE(wd.in_time, wd.create_time)) AS bucket,
                       SUM(COALESCE(wd.pro_qty, 0) - COALESCE(wd.ng_qty, 0)
                           - COALESCE(wd.scrap_qty, 0)) AS good_qty,
                       ci.item_name
                FROM n2admin.t_wip_detail wd
                JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
                JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
                JOIN n2admin.t_co_item ci ON wd.model_code = ci.item_code
                WHERE line.area_sn = :line_id
                  AND wd.model_code = :product_code
                  AND wd.data_auth = :workshop_id
                  AND COALESCE(wd.in_time, wd.create_time)
                      BETWEEN :start_date AND :end_date
                GROUP BY bucket, ci.item_name
                ORDER BY bucket
                """
            )
            result = await session.execute(
                sql,
                {
                    "line_id": params.line_id,
                    "product_code": params.product_code,
                    "workshop_id": context.workshop_id,
                    "start_date": params.start_date,
                    "end_date": params.end_date,
                },
            )
            rows = [dict(r) for r in result.mappings().all()]
            total = sum(float(r.get("good_qty") or 0) for r in rows)
            breakdown = [
                {
                    "bucket": r["bucket"].isoformat() if r.get("bucket") else None,
                    "good_qty": float(r.get("good_qty") or 0),
                    "item_name": r.get("item_name"),
                }
                for r in rows
            ]
            return ProductYieldResult(
                line_id=params.line_id,
                product_code=params.product_code,
                workshop_id=context.workshop_id,
                total_qty=round(total, 4),
                breakdown=breakdown,
            )
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tool 5: get_device_production_rate (t_co_device join)
# ---------------------------------------------------------------------------


class GetDeviceProductionRateTool(BaseMCPTool):
    name = "get_device_production_rate"
    description = "Average equipment production rate joined with t_co_device."

    async def execute(self, params, context: MCPContext):
        from models.intents.production import DeviceRateParams, DeviceRateResult

        session = await get_session()
        try:
            filters = ["eq.data_auth = :workshop_id", "eq.create_time BETWEEN :start_date AND :end_date"]
            bind: dict[str, Any] = {
                "workshop_id": context.workshop_id,
                "start_date": params.start_date,
                "end_date": params.end_date,
            }
            if params.device_sn:
                filters.append("eq.device_sn = :device_sn")
                bind["device_sn"] = params.device_sn
            elif params.line_id:
                filters.append(
                    """eq.device_sn IN (
                        SELECT device_sn FROM n2admin.t_co_device
                        WHERE cd_location = :line_id AND data_auth = :workshop_id
                    )"""
                )
                bind["line_id"] = params.line_id

            where = " AND ".join(filters)
            sql = text(
                f"""
                SELECT eq.device_sn, d.device_name,
                       AVG(COALESCE(eq.finish_qty, 0)) AS avg_rate,
                       SUM(COALESCE(eq.finish_qty, 0)) AS total_qty
                FROM n2admin.t_smt_program_consumption_record eq
                JOIN n2admin.t_co_device d ON eq.device_sn = d.device_sn
                WHERE {where}
                GROUP BY eq.device_sn, d.device_name
                ORDER BY avg_rate DESC
                """
            )
            result = await session.execute(sql, bind)
            devices = [
                {
                    "device_sn": r["device_sn"],
                    "device_name": r.get("device_name"),
                    "avg_rate": round(float(r.get("avg_rate") or 0), 4),
                    "total_qty": round(float(r.get("total_qty") or 0), 4),
                }
                for r in result.mappings().all()
            ]
            return DeviceRateResult(workshop_id=context.workshop_id, devices=devices)
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Tool 6: get_standard_time_achievement (t_co_standard_time join)
# ---------------------------------------------------------------------------


class GetStandardTimeAchievementTool(BaseMCPTool):
    name = "get_standard_time_achievement"
    description = "Actual output vs standard_time goal percentage."

    async def execute(self, params, context: MCPContext):
        from models.intents.production import (
            StandardTimeAchievementParams,
            StandardTimeAchievementResult,
        )

        session = await get_session()
        try:
            sql = text(
                """
                SELECT SUM(COALESCE(eq.finish_qty, 0)) AS actual_qty,
                       MAX(st.standard_time) AS standard_time,
                       EXTRACT(EPOCH FROM (MAX(eq.create_time) - MIN(eq.create_time))) / 3600.0
                           AS elapsed_hours
                FROM n2admin.t_smt_program_consumption_record eq
                JOIN n2admin.t_co_standard_time st
                  ON eq.area_sn = st.area_sn AND eq.model_code = st.model_code
                WHERE eq.area_sn = :line_id
                  AND eq.model_code = :model_code
                  AND eq.data_auth = :workshop_id
                  AND eq.create_time BETWEEN :start_date AND :end_date
                """
            )
            result = await session.execute(
                sql,
                {
                    "line_id": params.line_id,
                    "model_code": params.model_code,
                    "workshop_id": context.workshop_id,
                    "start_date": params.start_date,
                    "end_date": params.end_date,
                },
            )
            row = result.mappings().first() or {}
            actual = float(row.get("actual_qty") or 0)
            std_time = float(row.get("standard_time") or 1)
            elapsed = max(float(row.get("elapsed_hours") or 1), 0.01)
            achievement = (actual / (std_time * elapsed)) * 100.0

            return StandardTimeAchievementResult(
                line_id=params.line_id,
                model_code=params.model_code,
                workshop_id=context.workshop_id,
                achievement_pct=round(achievement, 4),
                actual_qty=round(actual, 4),
                standard_time=round(std_time, 4),
                elapsed_hours=round(elapsed, 4),
            )
        finally:
            await session.close()


# Singleton instances for orchestrator registration
get_yield_aggregation_tool = GetYieldAggregationTool()
get_yield_anomalies_tool = GetYieldAnomaliesAndPeaksTool()
compare_yield_periods_tool = CompareYieldPeriodsTool()
get_product_yield_tool = GetProductYieldTool()
get_device_production_rate_tool = GetDeviceProductionRateTool()
get_standard_time_achievement_tool = GetStandardTimeAchievementTool()
