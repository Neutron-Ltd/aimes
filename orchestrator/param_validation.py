"""Pre-dispatch validation — block MCP execution when required entities are missing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from models.schemas import IntentSchema, IntentType

Validator = Callable[[IntentSchema], Optional[str]]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    message: str = ""


def _missing(value: Optional[str]) -> bool:
    return value is None or not str(value).strip()


def _first_present(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if not _missing(value):
            return str(value).strip()
    return None


def _line_required(intent: IntentSchema) -> Optional[str]:
    if _missing(intent.line_id):
        return (
            "Could not execute analysis: Please specify a valid production line ID "
            "(e.g. L-01, L-03) or workshop area in your query."
        )
    return None


def _line_and_product(intent: IntentSchema) -> Optional[str]:
    if err := _line_required(intent):
        return err
    if not _first_present(intent.product_code, intent.model_code):
        return (
            "Could not execute analysis: Please specify a product or model code "
            "along with the production line in your query."
        )
    return None


def _line_and_model(intent: IntentSchema) -> Optional[str]:
    if err := _line_required(intent):
        return err
    if not _first_present(intent.model_code, intent.product_code):
        return (
            "Could not execute analysis: Please specify a model or product code "
            "along with the production line in your query."
        )
    return None


def _device_or_line(intent: IntentSchema) -> Optional[str]:
    if _missing(intent.device_sn) and _missing(intent.line_id):
        return (
            "Could not execute analysis: Please specify either a device serial number "
            "or a production line ID in your query."
        )
    return None


def _process_code_required(intent: IntentSchema) -> Optional[str]:
    if _missing(intent.process_code):
        return (
            "Could not execute analysis: Please specify a process or inspection step "
            "code in your query."
        )
    return None


def _milestone_date_required(intent: IntentSchema) -> Optional[str]:
    if intent.start_date is None:
        return (
            "Could not execute analysis: Please specify the milestone date "
            "(e.g. when the corrective action was implemented) in your query."
        )
    return None


def _warehouse_inbound(intent: IntentSchema) -> Optional[str]:
    if _missing(intent.wh_code):
        return (
            "Could not execute analysis: Please specify a warehouse code (wh_code) "
            "in your query."
        )
    if not _first_present(intent.item_code, intent.product_code):
        return (
            "Could not execute analysis: Please specify an item or product code "
            "for the inbound/outbound operation."
        )
    return None


def _material_batch_required(intent: IntentSchema) -> Optional[str]:
    if not _first_present(intent.material_batch, intent.batch_lot):
        return (
            "Could not execute analysis: Please specify a material batch or lot number "
            "to trace forward."
        )
    return None


def _finished_lot_required(intent: IntentSchema) -> Optional[str]:
    if not _first_present(intent.finished_lot, intent.batch_lot):
        return (
            "Could not execute analysis: Please specify a finished product lot number "
            "to trace in reverse."
        )
    return None


INTENT_VALIDATORS: dict[IntentType, Validator] = {
    IntentType.YIELD_AGGREGATION: _line_required,
    IntentType.YIELD_ANOMALIES: _line_required,
    IntentType.YIELD_COMPARISON: _line_required,
    IntentType.PRODUCTION_PRODUCT_YIELD: _line_and_product,
    IntentType.PRODUCTION_STANDARD_TIME: _line_and_model,
    IntentType.PRODUCTION_DEVICE_RATE: _device_or_line,
    IntentType.PRODUCTION_ROOT_CAUSE: _line_required,
    IntentType.PRODUCTION_SCHEDULING_OPT: _line_required,
    IntentType.PRODUCTION_CAPACITY_FORECAST: _line_required,
    IntentType.QUALITY_ERROR_PREVENTION: _process_code_required,
    IntentType.QUALITY_EFFECTIVENESS_VERIFY: _milestone_date_required,
    IntentType.WAREHOUSE_INBOUND_OUTBOUND: _warehouse_inbound,
    IntentType.WAREHOUSE_TRACE_FORWARD: _material_batch_required,
    IntentType.WAREHOUSE_TRACE_REVERSE: _finished_lot_required,
    IntentType.CROSS_MODULE_ANALYSIS: _line_required,
}


def validate_intent_params(intent: IntentSchema) -> ValidationResult:
    """
    Return ValidationResult(ok=False) when required entity fields are absent.

    Intents without an entry (e.g. workshop-scoped inventory monitor) pass through.
  Date defaults are handled in param mappers; entity identifiers must come from the user.
    """
    validator = INTENT_VALIDATORS.get(intent.intent)
    if validator is None:
        return ValidationResult(ok=True)

    message = validator(intent)
    if message:
        return ValidationResult(ok=False, message=message)
    return ValidationResult(ok=True)
