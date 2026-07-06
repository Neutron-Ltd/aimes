"""Pre-dispatch validation — block MCP execution when required entities are missing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from models.schemas import IntentSchema, IntentType

Validator = Callable[[IntentSchema], Optional[str]]

_SUPPORTED_LOCALES = frozenset({"zh-CN", "en-US"})

_MESSAGES: dict[str, dict[str, str]] = {
    "line_required": {
        "zh-CN": (
            "无法执行分析：请在问题中指明产线编号（如 FDQ-SMT-3）或车间区域。"
        ),
        "en-US": (
            "Could not execute analysis: Please specify a valid production line ID "
            "(e.g. FDQ-SMT-3) or workshop area in your query."
        ),
    },
    "line_and_product": {
        "zh-CN": (
            "无法执行分析：请同时指定产线与产品或型号编码。"
        ),
        "en-US": (
            "Could not execute analysis: Please specify a product or model code "
            "along with the production line in your query."
        ),
    },
    "line_and_model": {
        "zh-CN": (
            "无法执行分析：请同时指定产线与型号或产品编码。"
        ),
        "en-US": (
            "Could not execute analysis: Please specify a model or product code "
            "along with the production line in your query."
        ),
    },
    "device_or_line": {
        "zh-CN": (
            "无法执行分析：请在问题中指明设备序列号或产线编号。"
        ),
        "en-US": (
            "Could not execute analysis: Please specify either a device serial number "
            "or a production line ID in your query."
        ),
    },
    "process_code_required": {
        "zh-CN": "无法执行分析：请在问题中指明工序或检验步骤编码。",
        "en-US": (
            "Could not execute analysis: Please specify a process or inspection step "
            "code in your query."
        ),
    },
    "milestone_date_required": {
        "zh-CN": "无法执行分析：请在问题中指明里程碑日期（如纠正措施实施日期）。",
        "en-US": (
            "Could not execute analysis: Please specify the milestone date "
            "(e.g. when the corrective action was implemented) in your query."
        ),
    },
    "warehouse_inbound_wh": {
        "zh-CN": "无法执行分析：请在问题中指明仓库编码（wh_code）。",
        "en-US": (
            "Could not execute analysis: Please specify a warehouse code (wh_code) "
            "in your query."
        ),
    },
    "warehouse_inbound_item": {
        "zh-CN": "无法执行分析：请为出入库操作指定物料或产品编码。",
        "en-US": (
            "Could not execute analysis: Please specify an item or product code "
            "for the inbound/outbound operation."
        ),
    },
    "material_batch_required": {
        "zh-CN": "无法执行分析：请指定物料批次或 lot 号以进行正向追溯。",
        "en-US": (
            "Could not execute analysis: Please specify a material batch or lot number "
            "to trace forward."
        ),
    },
    "finished_lot_required": {
        "zh-CN": "无法执行分析：请指定成品 lot 号以进行反向追溯。",
        "en-US": (
            "Could not execute analysis: Please specify a finished product lot number "
            "to trace in reverse."
        ),
    },
    "plan_achievement_scope": {
        "zh-CN": (
            "无法执行计划达成率分析：请指定日期范围，并至少提供产线、工单号或产品型号之一。"
        ),
        "en-US": (
            "Could not execute plan attainment analysis: Please specify a date range "
            "and at least one of line, work order (MO), or product code."
        ),
    },
    "achievement_rate_deprecated": {
        "zh-CN": (
            "设备日志达成率已停用。计划达成率请询问「计划达成率」或指定产线/工单/产品的达成情况。"
        ),
        "en-US": (
            "Equipment-log achievement rate is deprecated. For plan attainment, ask "
            "about plan achievement rate with a line, work order, or product."
        ),
    },
}


def _normalize_locale(locale: str) -> str:
    return locale if locale in _SUPPORTED_LOCALES else "zh-CN"


def _msg(key: str, locale: str) -> str:
    locale = _normalize_locale(locale)
    return _MESSAGES[key][locale]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    message: str = ""


def _missing(value: Optional[str]) -> bool:
    return value is None or not str(value).strip()


def _is_all_lines(line_id: Optional[str]) -> bool:
    return str(line_id or "").strip().lower() == "all"


def _first_present(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if not _missing(value):
            return str(value).strip()
    return None


def _line_required(intent: IntentSchema, locale: str) -> Optional[str]:
    if _missing(intent.line_id):
        return _msg("line_required", locale)
    return None


def _line_and_product(intent: IntentSchema, locale: str) -> Optional[str]:
    if err := _line_required(intent, locale):
        return err
    if not _first_present(intent.product_code, intent.model_code):
        return _msg("line_and_product", locale)
    return None


def _line_and_model(intent: IntentSchema, locale: str) -> Optional[str]:
    if err := _line_required(intent, locale):
        return err
    if not _first_present(intent.model_code, intent.product_code):
        return _msg("line_and_model", locale)
    return None


def _device_or_line(intent: IntentSchema, locale: str) -> Optional[str]:
    if _missing(intent.device_sn) and _missing(intent.line_id):
        return _msg("device_or_line", locale)
    return None


def _process_code_required(intent: IntentSchema, locale: str) -> Optional[str]:
    if _missing(intent.process_code):
        return _msg("process_code_required", locale)
    return None


def _milestone_date_required(intent: IntentSchema, locale: str) -> Optional[str]:
    if intent.start_date is None:
        return _msg("milestone_date_required", locale)
    return None


def _warehouse_inbound(intent: IntentSchema, locale: str) -> Optional[str]:
    if _missing(intent.wh_code):
        return _msg("warehouse_inbound_wh", locale)
    if not _first_present(intent.item_code, intent.product_code):
        return _msg("warehouse_inbound_item", locale)
    return None


def _material_batch_required(intent: IntentSchema, locale: str) -> Optional[str]:
    if not _first_present(intent.material_batch, intent.batch_lot):
        return _msg("material_batch_required", locale)
    return None


def _finished_lot_required(intent: IntentSchema, locale: str) -> Optional[str]:
    if not _first_present(intent.finished_lot, intent.batch_lot):
        return _msg("finished_lot_required", locale)
    return None


def _yield_scope_required(intent: IntentSchema, locale: str) -> Optional[str]:
    """Reported yield needs line_id; equipment yield accepts line_id OR device_sn."""
    if _is_all_lines(intent.line_id):
        return None
    if intent.yield_type == "reported":
        return _line_required(intent, locale)
    return _device_or_line(intent, locale)


def _yield_aggregation_allowed(intent: IntentSchema, locale: str) -> Optional[str]:
    """Plant-wide and all-line aggregation allowed without entity constraints."""
    if intent.metric == "achievement_rate":
        return _msg("achievement_rate_deprecated", locale)
    return None


def _plan_achievement_allowed(_intent: IntentSchema, _locale: str) -> Optional[str]:
    """Plant-wide plan attainment allowed; dates default via mapper."""
    return None


INTENT_VALIDATORS: dict[IntentType, Callable[[IntentSchema, str], Optional[str]]] = {
    IntentType.YIELD_AGGREGATION: _yield_aggregation_allowed,
    IntentType.YIELD_ANOMALIES: _yield_scope_required,
    IntentType.YIELD_COMPARISON: _yield_scope_required,
    IntentType.PRODUCTION_PRODUCT_YIELD: _line_and_product,
    IntentType.PRODUCTION_STANDARD_TIME: _line_and_model,
    IntentType.PRODUCTION_DEVICE_RATE: _device_or_line,
    IntentType.PRODUCTION_ROOT_CAUSE: _line_required,
    IntentType.PRODUCTION_SCHEDULING_OPT: _line_required,
    IntentType.PRODUCTION_CAPACITY_FORECAST: _line_required,
    IntentType.PRODUCTION_PLAN_ACHIEVEMENT: _plan_achievement_allowed,
    IntentType.QUALITY_ERROR_PREVENTION: _process_code_required,
    IntentType.QUALITY_EFFECTIVENESS_VERIFY: _milestone_date_required,
    IntentType.WAREHOUSE_INBOUND_OUTBOUND: _warehouse_inbound,
    IntentType.WAREHOUSE_TRACE_FORWARD: _material_batch_required,
    IntentType.WAREHOUSE_TRACE_REVERSE: _finished_lot_required,
    IntentType.CROSS_MODULE_ANALYSIS: _line_required,
}


def validate_intent_params(
    intent: IntentSchema,
    locale: str = "zh-CN",
) -> ValidationResult:
    """
    Return ValidationResult(ok=False) when required entity fields are absent.

    Intents without an entry (e.g. workshop-scoped inventory monitor) pass through.
    Date defaults are handled in param mappers; entity identifiers may be null for
    plant-wide yield aggregation.
    """
    validator = INTENT_VALIDATORS.get(intent.intent)
    if validator is None:
        return ValidationResult(ok=True)

    message = validator(intent, locale)
    if message:
        return ValidationResult(ok=False, message=message)
    return ValidationResult(ok=True)
