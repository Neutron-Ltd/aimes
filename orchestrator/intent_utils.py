"""Bailian intent parsing utilities."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import date, datetime
from http import HTTPStatus
from typing import Any, Optional

import dashscope
from pydantic import ValidationError

from core.config import get_settings
from core.logging import get_logger
from models.schemas import BailianIntentExtraction, IntentSchema, IntentType, MCPContext
from orchestrator.intent_prompt import build_intent_prompt
from orchestrator.param_mappers import DEFAULT_LINE_ID

logger = get_logger(__name__)

_INTENT_MAP: dict[str, IntentType] = {e.name: e for e in IntentType}
_INTENT_MAP.update({e.value: e for e in IntentType})
_INTENT_MAP.update({e.name.lower(): e for e in IntentType})

_MARKDOWN_JSON_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

RAG_INTENTS = {
    IntentType.YIELD_ANOMALIES,
    IntentType.QUALITY_DEFECT_ANALYSIS,
    IntentType.PRODUCTION_ROOT_CAUSE,
    IntentType.QUALITY_ROOT_CAUSE,
    IntentType.WAREHOUSE_OBSOLETE_PROFILE,
}


def fallback_intent(query: str, reason: str) -> IntentSchema:
    logger.warning("Intent extraction failed: %s", reason)
    return IntentSchema(intent=IntentType.UNKNOWN, raw_query=query, confidence=0.0)


def strip_markdown_json(text: str) -> str:
    text = text.strip()
    match = _MARKDOWN_JSON_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def normalize_intent(raw: str) -> IntentType:
    key = raw.strip()
    for variant in (key, key.upper(), key.lower()):
        if variant in _INTENT_MAP:
            return _INTENT_MAP[variant]
    return IntentType.UNKNOWN


def parse_date_field(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
        except ValueError:
            return date.fromisoformat(cleaned[:10])
    return None


def map_extraction_to_intent_schema(
    extracted: BailianIntentExtraction, raw_query: str
) -> IntentSchema:
    yield_type = extracted.yield_type.lower()
    if yield_type not in ("equipment", "reported"):
        yield_type = "equipment"

    return IntentSchema(
        intent=normalize_intent(extracted.intent),
        start_date=parse_date_field(extracted.start_date),
        end_date=parse_date_field(extracted.end_date),
        line_id=extracted.line_id or DEFAULT_LINE_ID,
        yield_type=yield_type,
        group_by=extracted.group_by,
        metric=extracted.metric,
        analysis_type=extracted.analysis_type,
        threshold_percentage=extracted.threshold_percentage,
        period_1_start=parse_date_field(extracted.period_1_start),
        period_1_end=parse_date_field(extracted.period_1_end),
        period_2_start=parse_date_field(extracted.period_2_start),
        period_2_end=parse_date_field(extracted.period_2_end),
        product_code=extracted.product_code,
        model_code=extracted.model_code,
        device_sn=extracted.device_sn,
        batch_lot=extracted.batch_lot,
        material_batch=extracted.material_batch,
        finished_lot=extracted.finished_lot,
        process_code=extracted.process_code,
        export_format=extracted.export_format,
        doc_type=extracted.doc_type,
        wh_code=extracted.wh_code,
        item_code=extracted.item_code,
        confidence=0.9,
        raw_query=raw_query,
    )


async def parse_intent(query: str, context: MCPContext) -> IntentSchema:
    normalized = query.strip()
    settings = get_settings()

    if not settings.dashscope_api_key or not settings.bailian_app_id:
        return fallback_intent(
            normalized,
            "DASHSCOPE_API_KEY or BAILIAN_APP_ID not configured",
        )

    prompt_text = build_intent_prompt(normalized, context)

    try:
        response = await asyncio.to_thread(
            dashscope.Application.call,
            app_id=settings.bailian_app_id,
            prompt=prompt_text,
            api_key=settings.dashscope_api_key,
        )

        if response.status_code != HTTPStatus.OK:
            message = getattr(response, "message", "Unknown Bailian API error")
            return fallback_intent(normalized, f"Bailian API error: {message}")

        output_text = response.output.text
        if not output_text:
            return fallback_intent(normalized, "Empty response from Bailian")

        if settings.debug:
            logger.debug("Bailian raw response: %s", output_text)

        sanitized = strip_markdown_json(output_text)
        payload = json.loads(sanitized)
        extracted = BailianIntentExtraction.model_validate(payload)
        return map_extraction_to_intent_schema(extracted, normalized)

    except json.JSONDecodeError as exc:
        return fallback_intent(normalized, f"Invalid JSON from Bailian: {exc}")
    except ValidationError as exc:
        return fallback_intent(normalized, f"Intent schema validation failed: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error during Bailian intent extraction")
        return fallback_intent(normalized, f"Unexpected error: {exc}")
