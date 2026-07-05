"""
Phase 2 — Production Data MCP Tool Arsenal (Token-Optimized).

Three flexible tools cover standard aggregation, anomaly detection, and
period comparison. The LLM passes structured parameters only; SQL is
predefined and table-routed — never LLM-generated.

Table routing:
  equipment → n2admin.t_smt_program_consumption_record via area_sn or device_sn
  reported  → n2admin.t_wip_detail JOIN t_co_area (line.area_sn / area_name = line_id)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.line_scope import equipment_scope_filter, reported_line_filter
from core.logging import get_logger
from core.math_safeguard import period_over_period_growth_rate, population_std_dev
from mcp_tools.base import BaseMCPTool, optional_session
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
    scope: Literal["line", "plant", "all_lines"] = "line"
    refinement_suggested: bool = False
    line_breakdown: list[dict[str, Any]] = Field(default_factory=list)


class FactoryMetadataParams(BaseModel):
    """No required inputs — returns structural master data."""


class FactoryMetadataResult(BaseModel):
    line_count: int
    lines: list[dict[str, str]] = Field(default_factory=list)


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
    period_1_total: float
    period_2_total: float
    growth_rate: Optional[float] = None


# ---------------------------------------------------------------------------
# SQL routing helpers
# ---------------------------------------------------------------------------


def build_yield_from_clause(yield_type: YieldType) -> str:
    """
    Route yield_type to the correct table(s).

    equipment: consumption records — scoped by device_sn or eq.area_sn
               (Chinese line names resolved via t_co_area.area_name).
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


def _is_all_lines(line_id: Optional[str]) -> bool:
    return str(line_id or "").strip().lower() == "all"


def _equipment_scope_filter(line_id: Optional[str], device_sn: Optional[str]) -> str:
    if _is_all_lines(line_id):
        return "1=1"
    return equipment_scope_filter(line_id, device_sn, alias="eq")


def _line_filter(
    yield_type: YieldType,
    line_id: Optional[str] = None,
    device_sn: Optional[str] = None,
) -> str:
    if _is_all_lines(line_id):
        return "1=1"
    if yield_type == YieldType.EQUIPMENT:
        return _equipment_scope_filter(line_id, device_sn)
    if line_id:
        return reported_line_filter(alias="line")
    return "1=1"


def _time_column(yield_type: YieldType) -> str:
    if yield_type == YieldType.EQUIPMENT:
        return "eq.create_time"
    return "COALESCE(wd.in_time, wd.create_time)"


def _build_all_lines_sql(
    yield_type: YieldType,
    metric: Metric,
) -> str:
    """Per-line comparative aggregation — GROUP BY area_sn on transactional tables."""
    time_col = _time_column(yield_type)
    time_range = f"{time_col} BETWEEN :start_date AND :end_date"

    if yield_type == YieldType.EQUIPMENT:
        qty_expr = "COALESCE(eq.finish_qty, 0)"
        denom_expr = "COALESCE(eq.mount_sheet_qty, 0)"
        return f"""
            SELECT eq.area_sn,
                   COALESCE(a.area_name, eq.area_sn) AS area_name,
                   SUM({qty_expr}) AS qty,
                   SUM({denom_expr}) AS denom
            FROM n2admin.t_smt_program_consumption_record eq
            LEFT JOIN n2admin.t_co_area a ON eq.area_sn = a.area_sn
            WHERE eq.area_sn IS NOT NULL
              AND {time_range}
            GROUP BY eq.area_sn, COALESCE(a.area_name, eq.area_sn)
            ORDER BY qty DESC
        """

    good_expr = (
        "COALESCE(wd.pro_qty, 0) - COALESCE(wd.ng_qty, 0) - COALESCE(wd.scrap_qty, 0)"
    )
    denom_expr = "COALESCE(wd.pro_qty, 0)"
    return f"""
        SELECT line.area_sn,
               COALESCE(line.area_name, line.area_sn) AS area_name,
               SUM({good_expr}) AS good_qty,
               SUM({denom_expr}) AS denom
        FROM n2admin.t_wip_detail wd
        JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
        JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
        WHERE {time_range}
        GROUP BY line.area_sn, COALESCE(line.area_name, line.area_sn)
        ORDER BY good_qty DESC
    """


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
          AND {time_range}
        GROUP BY {bucket}
        ORDER BY {bucket}
    """


async def _fetch_all_lines_rows(
    session: AsyncSession,
    *,
    yield_type: YieldType,
    start_date: datetime,
    end_date: datetime,
) -> list[dict[str, Any]]:
    sql = text(_build_all_lines_sql(yield_type, Metric.SUM))
    result = await session.execute(
        sql,
        {"start_date": start_date, "end_date": end_date},
    )
    return [dict(row) for row in result.mappings().all()]


def _build_line_breakdown(
    rows: list[dict[str, Any]],
    yield_type: YieldType,
    metric: Metric,
) -> tuple[list[dict[str, Any]], float]:
    """Build per-line matrix and plant total from all-lines query rows."""
    line_breakdown: list[dict[str, Any]] = []
    plant_total = 0.0

    for row in rows:
        if metric == Metric.ACHIEVEMENT_RATE:
            value = round(_row_achievement_rate(row, yield_type), 4)
        else:
            value = round(_row_qty(row, yield_type), 4)
        plant_total += _row_qty(row, yield_type)
        line_breakdown.append(
            {
                "area_sn": row.get("area_sn"),
                "area_name": row.get("area_name"),
                "value": value,
            }
        )

    if metric == Metric.ACHIEVEMENT_RATE:
        total_good = sum(_row_qty(r, yield_type) for r in rows)
        total_denom = sum(float(r.get("denom") or 0) for r in rows)
        plant_total = (
            round((total_good / total_denom * 100.0), 4) if total_denom else 0.0
        )
    else:
        plant_total = round(plant_total, 4)

    return line_breakdown, plant_total


async def _fetch_aggregation_rows(
    session: AsyncSession,
    *,
    yield_type: YieldType,
    line_id: Optional[str],
    device_sn: Optional[str],
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
        "start_date": start_date,
        "end_date": end_date,
    }
    if line_id and not _is_all_lines(line_id):
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
    start_date: datetime,
    end_date: datetime,
) -> float:
    rows = await _fetch_aggregation_rows(
        session,
        yield_type=yield_type,
        line_id=line_id,
        device_sn=device_sn,
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
        self,
        params: YieldAggregationParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> YieldAggregationResult:
        async with optional_session(session) as db:
            scope: Literal["line", "plant", "all_lines"] = "line"
            refinement_suggested = False
            line_breakdown: list[dict[str, Any]] = []

            if _is_all_lines(params.line_id):
                scope = "all_lines"
                rows = await _fetch_all_lines_rows(
                    db,
                    yield_type=params.yield_type,
                    start_date=params.start_date,
                    end_date=params.end_date,
                )
                line_breakdown, value = _build_line_breakdown(
                    rows, params.yield_type, params.metric
                )
                breakdown: list[dict[str, Any]] = []
            else:
                rows = await _fetch_aggregation_rows(
                    db,
                    yield_type=params.yield_type,
                    line_id=params.line_id,
                    device_sn=params.device_sn,
                    start_date=params.start_date,
                    end_date=params.end_date,
                    group_by=params.group_by,
                )
                value, breakdown = _compute_metric(
                    rows, params.yield_type, params.metric, params.group_by
                )
                if (
                    params.line_id is None
                    and params.device_sn is None
                    and params.group_by == GroupBy.TOTAL
                ):
                    scope = "plant"
                    refinement_suggested = value > 0

            return YieldAggregationResult(
                yield_type=params.yield_type.value,
                line_id=params.line_id,
                device_sn=params.device_sn,
                metric=params.metric.value,
                group_by=params.group_by.value,
                value=round(value, 4),
                breakdown=breakdown,
                scope=scope,
                refinement_suggested=refinement_suggested,
                line_breakdown=line_breakdown,
            )


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
        self,
        params: YieldAnomaliesParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> YieldAnomaliesResult:
        async with optional_session(session) as db:
            # Hourly series for anomaly analysis
            rows = await _fetch_aggregation_rows(
                db,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
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
                    db,
                    yield_type=params.yield_type,
                    line_id=params.line_id,
                    device_sn=params.device_sn,
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
                result=result,
            )


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
        self,
        params: CompareYieldPeriodsParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> CompareYieldPeriodsResult:
        async with optional_session(session) as db:
            period_1_total = await _fetch_period_total(
                db,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
                start_date=params.period_1_start,
                end_date=params.period_1_end,
            )
            period_2_total = await _fetch_period_total(
                db,
                yield_type=params.yield_type,
                line_id=params.line_id,
                device_sn=params.device_sn,
                start_date=params.period_2_start,
                end_date=params.period_2_end,
            )

            # Feature 5.2 — growth rate computed in Python, not by LLM
            growth = period_over_period_growth_rate(period_2_total, period_1_total)

            return CompareYieldPeriodsResult(
                yield_type=params.yield_type.value,
                line_id=params.line_id,
                device_sn=params.device_sn,
                period_1_total=round(period_1_total, 4),
                period_2_total=round(period_2_total, 4),
                growth_rate=round(growth, 4) if growth is not None else None,
            )


# ---------------------------------------------------------------------------
# Tool 4: get_product_yield (t_co_item join)
# ---------------------------------------------------------------------------


class GetProductYieldTool(BaseMCPTool):
    name = "get_product_yield"
    description = "Product-specific reported yield per line with t_co_item metadata."

    async def execute(self, params, context: MCPContext, *, session: AsyncSession | None = None):
        from models.intents.production import ProductYieldParams, ProductYieldResult

        async with optional_session(session) as db:
            line_predicate = reported_line_filter(alias="line")
            sql = text(
                f"""
                SELECT date_trunc('day', COALESCE(wd.in_time, wd.create_time)) AS bucket,
                       SUM(COALESCE(wd.pro_qty, 0) - COALESCE(wd.ng_qty, 0)
                           - COALESCE(wd.scrap_qty, 0)) AS good_qty,
                       ci.item_name
                FROM n2admin.t_wip_detail wd
                JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
                JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
                JOIN n2admin.t_co_item ci ON wd.model_code = ci.item_code
                WHERE {line_predicate}
                  AND wd.model_code = :product_code
                  AND COALESCE(wd.in_time, wd.create_time)
                      BETWEEN :start_date AND :end_date
                GROUP BY bucket, ci.item_name
                ORDER BY bucket
                """
            )
            result = await db.execute(
                sql,
                {
                    "line_id": params.line_id,
                    "product_code": params.product_code,
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
                total_qty=round(total, 4),
                breakdown=breakdown,
            )


# ---------------------------------------------------------------------------
# Tool 5: get_device_production_rate (t_co_device join)
# ---------------------------------------------------------------------------


class GetDeviceProductionRateTool(BaseMCPTool):
    name = "get_device_production_rate"
    description = "Average equipment production rate joined with t_co_device."

    async def execute(self, params, context: MCPContext, *, session: AsyncSession | None = None):
        from models.intents.production import DeviceRateParams, DeviceRateResult

        async with optional_session(session) as db:
            filters = ["eq.create_time BETWEEN :start_date AND :end_date"]
            bind: dict[str, Any] = {
                "start_date": params.start_date,
                "end_date": params.end_date,
            }
            if params.device_sn:
                filters.append("eq.device_sn = :device_sn")
                bind["device_sn"] = params.device_sn
            elif params.line_id:
                filters.append(equipment_scope_filter(params.line_id, None, alias="eq"))
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
            result = await db.execute(sql, bind)
            devices = [
                {
                    "device_sn": r["device_sn"],
                    "device_name": r.get("device_name"),
                    "avg_rate": round(float(r.get("avg_rate") or 0), 4),
                    "total_qty": round(float(r.get("total_qty") or 0), 4),
                }
                for r in result.mappings().all()
            ]
            return DeviceRateResult(devices=devices)


# ---------------------------------------------------------------------------
# Tool 6: get_standard_time_achievement (t_co_standard_time join)
# ---------------------------------------------------------------------------


class GetStandardTimeAchievementTool(BaseMCPTool):
    name = "get_standard_time_achievement"
    description = "Actual output vs standard_time goal percentage."

    async def execute(self, params, context: MCPContext, *, session: AsyncSession | None = None):
        from models.intents.production import (
            StandardTimeAchievementParams,
            StandardTimeAchievementResult,
        )

        async with optional_session(session) as db:
            line_predicate = equipment_scope_filter(params.line_id, None, alias="eq")
            sql = text(
                f"""
                SELECT SUM(COALESCE(eq.finish_qty, 0)) AS actual_qty,
                       MAX(st.standard_time) AS standard_time,
                       EXTRACT(EPOCH FROM (MAX(eq.create_time) - MIN(eq.create_time))) / 3600.0
                           AS elapsed_hours
                FROM n2admin.t_smt_program_consumption_record eq
                JOIN n2admin.t_co_standard_time st
                  ON eq.area_sn = st.area_sn AND eq.model_code = st.model_code
                WHERE {line_predicate}
                  AND eq.model_code = :model_code
                  AND eq.create_time BETWEEN :start_date AND :end_date
                """
            )
            result = await db.execute(
                sql,
                {
                    "line_id": params.line_id,
                    "model_code": params.model_code,
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
                achievement_pct=round(achievement, 4),
                actual_qty=round(actual, 4),
                standard_time=round(std_time, 4),
                elapsed_hours=round(elapsed, 4),
            )


# ---------------------------------------------------------------------------
# Tool 7: get_factory_structure_metadata
# ---------------------------------------------------------------------------


class GetFactoryStructureMetadataTool(
    BaseMCPTool[FactoryMetadataParams, FactoryMetadataResult]
):
    name = "get_factory_structure_metadata"
    description = (
        "Lightweight lookup of production line structure from t_co_area master data."
    )

    async def execute(
        self,
        params: FactoryMetadataParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> FactoryMetadataResult:
        _ = params, context
        async with optional_session(session) as db:
            sql = text(
                """
                SELECT DISTINCT area_sn, area_name
                FROM n2admin.t_co_area
                WHERE area_sn IS NOT NULL
                ORDER BY area_sn
                """
            )
            result = await db.execute(sql)
            lines = [
                {
                    "area_sn": str(row["area_sn"]),
                    "area_name": str(row.get("area_name") or row["area_sn"]),
                }
                for row in result.mappings().all()
            ]
            return FactoryMetadataResult(line_count=len(lines), lines=lines)


# Singleton instances for orchestrator registration
get_yield_aggregation_tool = GetYieldAggregationTool()
get_yield_anomalies_tool = GetYieldAnomaliesAndPeaksTool()
compare_yield_periods_tool = CompareYieldPeriodsTool()
get_product_yield_tool = GetProductYieldTool()
get_device_production_rate_tool = GetDeviceProductionRateTool()
get_standard_time_achievement_tool = GetStandardTimeAchievementTool()
get_factory_structure_metadata_tool = GetFactoryStructureMetadataTool()
