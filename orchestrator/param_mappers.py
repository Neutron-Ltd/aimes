"""Map IntentSchema → MCP tool parameter models.

Entity identifiers are passed through as extracted — no dummy defaults.
Temporal defaults (e.g. today for date ranges) are applied only where noted.
Required-entity checks run in orchestrator.param_validation before dispatch.

Line identifiers may be canonical codes (FDQ-SMT-6) or Chinese names
(防盗器贴片六线); SQL resolves them to area_sn at execution time.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from core.reference_date import get_reference_today

from mcp_tools.production_tools import (
    AnalysisType,
    CompareYieldPeriodsParams,
    FactoryMetadataParams,
    GroupBy,
    Metric,
    YieldAggregationParams,
    YieldAnomaliesParams,
    YieldType,
)
from models.intents.production import (
    CapacityForecastParams,
    DeviceRateParams,
    PlanAchievementParams,
    ProductYieldParams,
    RootCauseParams,
    SchedulingParams,
    StandardTimeAchievementParams,
)
from models.intents.quality import (
    DefectAggregationParams,
    EffectivenessVerifyParams,
    ErrorPreventionParams,
    QualityRootCauseParams,
)
from models.intents.warehouse import (
    InboundOutboundParams,
    InventoryStatusParams,
    ObsoleteProfileParams,
    TraceForwardParams,
    TraceReverseParams,
)
from models.schemas import IntentSchema, IntentType, TimeFrame


def _start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _end_of_day(d: date) -> datetime:
    return datetime.combine(d, time.max)


def _resolve_yield_type(intent: IntentSchema) -> YieldType:
    if intent.yield_type == "reported":
        return YieldType.REPORTED
    return YieldType.EQUIPMENT


def _date_range(intent: IntentSchema) -> tuple[date, date]:
    if intent.start_date and intent.end_date:
        return intent.start_date, intent.end_date
    today = get_reference_today()
    return today, today


def _strip(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _first_present(*values: Optional[str]) -> str:
    for value in values:
        cleaned = _strip(value)
        if cleaned:
            return cleaned
    raise ValueError("Required identifier missing — validation should have caught this")


def _line_id(intent: IntentSchema) -> str:
    return _first_present(intent.line_id)


def _line_scope(intent: IntentSchema) -> Optional[str]:
    cleaned = _strip(intent.line_id)
    if cleaned and cleaned.lower() == "all":
        return "all"
    return cleaned


def _plan_group_by(intent: IntentSchema) -> str:
    if intent.group_by in ("daily", "weekly", "monthly", "total"):
        return intent.group_by
    if intent.time_frame == TimeFrame.DAY:
        return "daily"
    if intent.time_frame == TimeFrame.WEEK:
        return "weekly"
    if intent.time_frame == TimeFrame.MONTH:
        return "monthly"
    return "total"


def intent_to_plan_achievement_params(intent: IntentSchema) -> PlanAchievementParams:
    start, end = _date_range(intent)
    return PlanAchievementParams(
        line_id=_line_scope(intent),
        mo_number=_strip(intent.mo_number),
        product_code=_strip(intent.product_code) or _strip(intent.model_code),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
        group_by=_plan_group_by(intent),
    )


def intent_to_factory_metadata_params(_intent: IntentSchema) -> FactoryMetadataParams:
    return FactoryMetadataParams()


def intent_to_aggregation_params(intent: IntentSchema) -> YieldAggregationParams:
    start, end = _date_range(intent)
    return YieldAggregationParams(
        yield_type=_resolve_yield_type(intent),
        line_id=_line_scope(intent),
        device_sn=_strip(intent.device_sn),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
        group_by=GroupBy(intent.group_by or GroupBy.DAILY.value),
        metric=Metric(intent.metric or Metric.SUM.value),
    )


def intent_to_anomalies_params(intent: IntentSchema) -> YieldAnomaliesParams:
    start, end = _date_range(intent)
    return YieldAnomaliesParams(
        yield_type=_resolve_yield_type(intent),
        line_id=_line_scope(intent),
        device_sn=_strip(intent.device_sn),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
        analysis_type=AnalysisType(intent.analysis_type or AnalysisType.VOLATILITY.value),
        threshold_percentage=intent.threshold_percentage,
    )


def intent_to_comparison_params(intent: IntentSchema) -> CompareYieldPeriodsParams:
    today = get_reference_today()
    p1s = intent.period_1_start or (today - timedelta(days=13))
    p1e = intent.period_1_end or (today - timedelta(days=7))
    p2s = intent.period_2_start or (today - timedelta(days=6))
    p2e = intent.period_2_end or today
    return CompareYieldPeriodsParams(
        yield_type=_resolve_yield_type(intent),
        line_id=_line_scope(intent),
        device_sn=_strip(intent.device_sn),
        period_1_start=_start_of_day(p1s),
        period_1_end=_end_of_day(p1e),
        period_2_start=_start_of_day(p2s),
        period_2_end=_end_of_day(p2e),
    )


def intent_to_product_yield_params(intent: IntentSchema) -> ProductYieldParams:
    start, end = _date_range(intent)
    return ProductYieldParams(
        line_id=_line_scope(intent),
        product_code=_strip(intent.product_code) or _strip(intent.model_code),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
    )


def intent_to_device_rate_params(intent: IntentSchema) -> DeviceRateParams:
    start, end = _date_range(intent)
    return DeviceRateParams(
        device_sn=_strip(intent.device_sn),
        line_id=_line_scope(intent),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
    )


def intent_to_standard_time_params(intent: IntentSchema) -> StandardTimeAchievementParams:
    start, end = _date_range(intent)
    return StandardTimeAchievementParams(
        line_id=_line_id(intent),
        model_code=_first_present(intent.model_code, intent.product_code),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
    )


def intent_to_root_cause_params(intent: IntentSchema) -> RootCauseParams:
    start, end = _date_range(intent)
    return RootCauseParams(
        line_id=_line_id(intent),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
        yield_type=intent.yield_type or "equipment",
    )


def intent_to_scheduling_params(intent: IntentSchema) -> SchedulingParams:
    return SchedulingParams(line_id=_line_id(intent))


def intent_to_capacity_params(intent: IntentSchema) -> CapacityForecastParams:
    return CapacityForecastParams(line_id=_line_id(intent))


def intent_to_defect_params(intent: IntentSchema) -> DefectAggregationParams:
    start, end = _date_range(intent)
    return DefectAggregationParams(
        line_id=_strip(intent.line_id),
        process_code=_strip(intent.process_code),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
    )


def intent_to_quality_root_cause_params(intent: IntentSchema) -> QualityRootCauseParams:
    start, end = _date_range(intent)
    return QualityRootCauseParams(
        process_code=_strip(intent.process_code),
        batch_lot=_strip(intent.batch_lot),
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
    )


def intent_to_error_prevention_params(intent: IntentSchema) -> ErrorPreventionParams:
    return ErrorPreventionParams(
        process_code=_first_present(intent.process_code),
        model_code=_strip(intent.model_code),
    )


def intent_to_effectiveness_params(intent: IntentSchema) -> EffectivenessVerifyParams:
    assert intent.start_date is not None
    return EffectivenessVerifyParams(
        process_code=_strip(intent.process_code),
        milestone_date=_start_of_day(intent.start_date),
    )


def intent_to_inventory_params(intent: IntentSchema) -> InventoryStatusParams:
    return InventoryStatusParams(
        wh_code=_strip(intent.wh_code),
        item_code=_strip(intent.item_code),
    )


def intent_to_inbound_outbound_params(intent: IntentSchema) -> InboundOutboundParams:
    return InboundOutboundParams(
        wh_code=_first_present(intent.wh_code),
        item_code=_first_present(intent.item_code, intent.product_code),
    )


def intent_to_obsolete_params(intent: IntentSchema) -> ObsoleteProfileParams:
    return ObsoleteProfileParams(wh_code=_strip(intent.wh_code))


def intent_to_trace_forward_params(intent: IntentSchema) -> TraceForwardParams:
    return TraceForwardParams(
        material_batch=_first_present(intent.material_batch, intent.batch_lot),
    )


def intent_to_trace_reverse_params(intent: IntentSchema) -> TraceReverseParams:
    return TraceReverseParams(
        finished_lot=_first_present(intent.finished_lot, intent.batch_lot),
    )


PARAM_MAPPERS = {
    IntentType.YIELD_AGGREGATION: intent_to_aggregation_params,
    IntentType.YIELD_ANOMALIES: intent_to_anomalies_params,
    IntentType.YIELD_COMPARISON: intent_to_comparison_params,
    IntentType.PRODUCTION_PRODUCT_YIELD: intent_to_product_yield_params,
    IntentType.PRODUCTION_DEVICE_RATE: intent_to_device_rate_params,
    IntentType.PRODUCTION_STANDARD_TIME: intent_to_standard_time_params,
    IntentType.PRODUCTION_ROOT_CAUSE: intent_to_root_cause_params,
    IntentType.PRODUCTION_SCHEDULING_OPT: intent_to_scheduling_params,
    IntentType.PRODUCTION_CAPACITY_FORECAST: intent_to_capacity_params,
    IntentType.PRODUCTION_PLAN_ACHIEVEMENT: intent_to_plan_achievement_params,
    IntentType.FACTORY_METADATA_LOOKUP: intent_to_factory_metadata_params,
    IntentType.QUALITY_DEFECT_ANALYSIS: intent_to_defect_params,
    IntentType.QUALITY_ROOT_CAUSE: intent_to_quality_root_cause_params,
    IntentType.QUALITY_ERROR_PREVENTION: intent_to_error_prevention_params,
    IntentType.QUALITY_EFFECTIVENESS_VERIFY: intent_to_effectiveness_params,
    IntentType.WAREHOUSE_INVENTORY_MONITOR: intent_to_inventory_params,
    IntentType.WAREHOUSE_INBOUND_OUTBOUND: intent_to_inbound_outbound_params,
    IntentType.WAREHOUSE_OBSOLETE_PROFILE: intent_to_obsolete_params,
    IntentType.WAREHOUSE_TRACE_FORWARD: intent_to_trace_forward_params,
    IntentType.WAREHOUSE_TRACE_REVERSE: intent_to_trace_reverse_params,
}
