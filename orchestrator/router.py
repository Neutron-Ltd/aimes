"""
F0.2 — LLM Orchestrator (Intent Router).

Pipeline:
  1. User natural-language query arrives via FastAPI.
  2. parse_intent() calls Bailian (DashScope) to extract IntentSchema params.
  3. route_and_execute() maps intent → Phase 2 MCP tool and invokes it with RBAC context.

The orchestrator NEVER prompts an LLM to write SQL. It only extracts typed
parameters and dispatches to predefined MCP tools.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import date, datetime, time, timedelta
from http import HTTPStatus
from typing import Any, Optional

import dashscope
from pydantic import ValidationError

from core.config import get_settings
from core.logging import get_logger
from mcp_tools.base import BaseMCPTool, MCPToolResult
from mcp_tools.production_tools import (
    AnalysisType,
    CompareYieldPeriodsParams,
    GroupBy,
    Metric,
    YieldAggregationParams,
    YieldAnomaliesParams,
    YieldType,
    compare_yield_periods_tool,
    get_yield_aggregation_tool,
    get_yield_anomalies_tool,
)
from models.schemas import (
    BailianIntentExtraction,
    IntentSchema,
    IntentType,
    MCPContext,
    OrchestratorResponse,
)

logger = get_logger(__name__)

DEFAULT_LINE_ID = "L-01"

_VALID_GROUP_BY = {e.value for e in GroupBy}
_VALID_METRICS = {e.value for e in Metric}
_VALID_ANALYSIS_TYPES = {e.value for e in AnalysisType}

_INTENT_MAP: dict[str, IntentType] = {
    "YIELD_AGGREGATION": IntentType.YIELD_AGGREGATION,
    "YIELD_ANOMALIES": IntentType.YIELD_ANOMALIES,
    "YIELD_COMPARISON": IntentType.YIELD_COMPARISON,
    "UNKNOWN": IntentType.UNKNOWN,
    "yield_aggregation": IntentType.YIELD_AGGREGATION,
    "yield_anomalies": IntentType.YIELD_ANOMALIES,
    "yield_comparison": IntentType.YIELD_COMPARISON,
    "unknown": IntentType.UNKNOWN,
}

_MARKDOWN_JSON_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _end_of_day(d: date) -> datetime:
    return datetime.combine(d, time.max)


def _fallback_intent(query: str, reason: str) -> IntentSchema:
    logger.warning("Intent extraction failed: %s", reason)
    return IntentSchema(intent=IntentType.UNKNOWN, raw_query=query, confidence=0.0)


def _strip_markdown_json(text: str) -> str:
    """Remove Markdown code fences that LLMs often wrap around JSON."""
    text = text.strip()
    match = _MARKDOWN_JSON_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _normalize_intent(raw: str) -> IntentType:
    key = raw.strip()
    if key in _INTENT_MAP:
        return _INTENT_MAP[key]
    upper = key.upper()
    if upper in _INTENT_MAP:
        return _INTENT_MAP[upper]
    lower = key.lower()
    if lower in _INTENT_MAP:
        return _INTENT_MAP[lower]
    return IntentType.UNKNOWN


def _parse_date_field(value: Any) -> Optional[date]:
    """Parse ISO datetime/date strings from AI output into date objects."""
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


def _safe_group_by(value: Optional[str]) -> str:
    if value and value in _VALID_GROUP_BY:
        return value
    return GroupBy.DAILY.value


def _safe_metric(value: Optional[str]) -> str:
    if value and value in _VALID_METRICS:
        return value
    return Metric.SUM.value


def _safe_analysis_type(value: Optional[str]) -> str:
    if value and value in _VALID_ANALYSIS_TYPES:
        return value
    return AnalysisType.VOLATILITY.value


def _build_intent_prompt(query: str, context: MCPContext) -> str:
    """Construct the Bailian Application prompt for structured intent extraction."""
    now = datetime.now().isoformat()
    intent_types = " | ".join(
        [
            "YIELD_AGGREGATION",
            "YIELD_ANOMALIES",
            "YIELD_COMPARISON",
            "UNKNOWN",
        ]
    )
    return f"""You are a strict Intent Extraction Router for an MES Production system.
Your ONLY job is to classify the user query and extract structured parameters.
DO NOT output conversational text. DO NOT generate SQL.
DO NOT include workshop_id or any RBAC fields in your output.
Output ONLY a valid JSON object matching this exact schema:
{{
  "intent": "{intent_types}",
  "yield_type": "equipment" | "reported",
  "line_id": "string (e.g., L-01, L-03)",
  "start_date": "YYYY-MM-DDTHH:MM:SS",
  "end_date": "YYYY-MM-DDTHH:MM:SS",
  "group_by": "daily" | "hourly" | "total",
  "metric": "sum" | "average" | "achievement_rate",
  "analysis_type": "volatility" | "below_standard" | "peak_hourly",
  "threshold_percentage": 90.0,
  "period_1_start": "YYYY-MM-DDTHH:MM:SS",
  "period_1_end": "YYYY-MM-DDTHH:MM:SS",
  "period_2_start": "YYYY-MM-DDTHH:MM:SS",
  "period_2_end": "YYYY-MM-DDTHH:MM:SS"
}}
Intent definitions:
  YIELD_AGGREGATION — totals, averages, achievement rates
  YIELD_ANOMALIES — volatility, below-standard, peak hourly analysis
  YIELD_COMPARISON — period-over-period growth or decline
  UNKNOWN — query is not a production data question
Use the current date/time if 'today' or 'current' is mentioned.
Current datetime: {now}
Workshop context (reference only — do NOT include in JSON output): {context.workshop_id}

User Query: {query}
"""


def _map_extraction_to_intent_schema(
    extracted: BailianIntentExtraction, raw_query: str
) -> IntentSchema:
    """Map validated Bailian extraction into IntentSchema with enum-safe defaults."""
    yield_type = extracted.yield_type.lower()
    if yield_type not in ("equipment", "reported"):
        yield_type = "equipment"

    return IntentSchema(
        intent=_normalize_intent(extracted.intent),
        start_date=_parse_date_field(extracted.start_date),
        end_date=_parse_date_field(extracted.end_date),
        line_id=extracted.line_id or DEFAULT_LINE_ID,
        yield_type=yield_type,
        group_by=_safe_group_by(extracted.group_by),
        metric=_safe_metric(extracted.metric),
        analysis_type=_safe_analysis_type(extracted.analysis_type),
        threshold_percentage=extracted.threshold_percentage,
        period_1_start=_parse_date_field(extracted.period_1_start),
        period_1_end=_parse_date_field(extracted.period_1_end),
        period_2_start=_parse_date_field(extracted.period_2_start),
        period_2_end=_parse_date_field(extracted.period_2_end),
        confidence=0.9,
        raw_query=raw_query,
    )


async def parse_intent(query: str, context: MCPContext) -> IntentSchema:
    """
    Extract structured intent parameters via Alibaba Cloud Bailian (DashScope).

    Uses asyncio.to_thread so the synchronous dashscope SDK does not block
    the FastAPI event loop. Falls back to UNKNOWN on any API or parse failure.
    """
    normalized = query.strip()
    settings = get_settings()

    if not settings.dashscope_api_key or not settings.bailian_app_id:
        return _fallback_intent(
            normalized,
            "DASHSCOPE_API_KEY or BAILIAN_APP_ID not configured",
        )

    prompt_text = _build_intent_prompt(normalized, context)

    try:
        response = await asyncio.to_thread(
            dashscope.Application.call,
            app_id=settings.bailian_app_id,
            prompt=prompt_text,
            api_key=settings.dashscope_api_key,
        )

        if response.status_code != HTTPStatus.OK:
            message = getattr(response, "message", "Unknown Bailian API error")
            request_id = getattr(response, "request_id", None)
            logger.error(
                "Bailian API error status=%s message=%s request_id=%s",
                response.status_code,
                message,
                request_id,
            )
            return _fallback_intent(normalized, f"Bailian API error: {message}")

        output_text = response.output.text
        if not output_text:
            return _fallback_intent(normalized, "Empty response from Bailian")

        if settings.debug:
            logger.debug("Bailian raw response: %s", output_text)

        sanitized = _strip_markdown_json(output_text)
        logger.debug("Bailian sanitized JSON: %s", sanitized)

        payload = json.loads(sanitized)
        extracted = BailianIntentExtraction.model_validate(payload)
        intent_schema = _map_extraction_to_intent_schema(extracted, normalized)

        logger.debug("Mapped IntentSchema: %s", intent_schema.model_dump(mode="json"))
        return intent_schema

    except json.JSONDecodeError as exc:
        return _fallback_intent(normalized, f"Invalid JSON from Bailian: {exc}")
    except ValidationError as exc:
        return _fallback_intent(normalized, f"Intent schema validation failed: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _fallback_intent(normalized, f"Intent mapping failed: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error during Bailian intent extraction")
        return _fallback_intent(normalized, f"Unexpected error: {exc}")


def _resolve_yield_type(intent: IntentSchema) -> YieldType:
    return YieldType.REPORTED if intent.yield_type == "reported" else YieldType.EQUIPMENT


def _intent_to_aggregation_params(intent: IntentSchema) -> YieldAggregationParams:
    if not intent.start_date or not intent.end_date:
        today = date.today()
        start, end = today, today
    else:
        start, end = intent.start_date, intent.end_date

    return YieldAggregationParams(
        yield_type=_resolve_yield_type(intent),
        line_id=intent.line_id or DEFAULT_LINE_ID,
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
        group_by=GroupBy(_safe_group_by(intent.group_by)),
        metric=Metric(_safe_metric(intent.metric)),
    )


def _intent_to_anomalies_params(intent: IntentSchema) -> YieldAnomaliesParams:
    if not intent.start_date or not intent.end_date:
        today = date.today()
        start, end = today, today
    else:
        start, end = intent.start_date, intent.end_date

    return YieldAnomaliesParams(
        yield_type=_resolve_yield_type(intent),
        line_id=intent.line_id or DEFAULT_LINE_ID,
        start_date=_start_of_day(start),
        end_date=_end_of_day(end),
        analysis_type=AnalysisType(_safe_analysis_type(intent.analysis_type)),
        threshold_percentage=intent.threshold_percentage,
    )


def _intent_to_comparison_params(intent: IntentSchema) -> CompareYieldPeriodsParams:
    today = date.today()
    p1s = intent.period_1_start or (today - timedelta(days=13))
    p1e = intent.period_1_end or (today - timedelta(days=7))
    p2s = intent.period_2_start or (today - timedelta(days=6))
    p2e = intent.period_2_end or today

    return CompareYieldPeriodsParams(
        yield_type=_resolve_yield_type(intent),
        line_id=intent.line_id or DEFAULT_LINE_ID,
        period_1_start=_start_of_day(p1s),
        period_1_end=_end_of_day(p1e),
        period_2_start=_start_of_day(p2s),
        period_2_end=_end_of_day(p2e),
    )


async def _run_tool(
    intent: IntentSchema,
    tool: BaseMCPTool,
    params: YieldAggregationParams | YieldAnomaliesParams | CompareYieldPeriodsParams,
    context: MCPContext,
    success_message: str,
) -> OrchestratorResponse:
    """Execute an MCP tool and wrap the result in OrchestratorResponse."""
    tool_result: MCPToolResult = await tool.run(params, context)

    logger.info(
        "Tool '%s' success=%s workshop=%s",
        tool.name,
        tool_result.success,
        context.workshop_id,
    )
    settings = get_settings()
    if settings.debug:
        logger.debug("Tool result data: %s", tool_result.data)

    if not tool_result.success:
        return OrchestratorResponse(
            intent=intent,
            tool_name=tool.name,
            result=None,
            message=tool_result.error or "MCP tool execution failed",
        )

    response = OrchestratorResponse(
        intent=intent,
        tool_name=tool.name,
        result=tool_result.data,
        message=success_message,
    )
    if settings.debug:
        logger.debug("OrchestratorResponse: %s", response.model_dump(mode="json"))
    return response


async def route_and_execute(query: str, context: MCPContext) -> OrchestratorResponse:
    """
    End-to-end orchestration: NL query → Bailian intent → Phase 2 MCP tool → response.

    Dynamic switch on IntentType:
      YIELD_AGGREGATION  → get_yield_aggregation_tool
      YIELD_ANOMALIES    → get_yield_anomalies_tool
      YIELD_COMPARISON   → compare_yield_periods_tool
      UNKNOWN            → error response (no tool dispatched)

    workshop_id is always taken from RBAC context (middleware), never user text.
    """
    intent = await parse_intent(query, context)
    logger.info(
        "Parsed intent=%s confidence=%.2f line=%s workshop=%s",
        intent.intent,
        intent.confidence,
        intent.line_id,
        context.workshop_id,
    )

    if intent.intent == IntentType.YIELD_AGGREGATION:
        params = _intent_to_aggregation_params(intent)
        return await _run_tool(
            intent,
            get_yield_aggregation_tool,
            params,
            context,
            "Yield aggregation retrieved successfully",
        )

    if intent.intent == IntentType.YIELD_ANOMALIES:
        params = _intent_to_anomalies_params(intent)
        return await _run_tool(
            intent,
            get_yield_anomalies_tool,
            params,
            context,
            "Yield anomaly analysis completed successfully",
        )

    if intent.intent == IntentType.YIELD_COMPARISON:
        params = _intent_to_comparison_params(intent)
        return await _run_tool(
            intent,
            compare_yield_periods_tool,
            params,
            context,
            "Yield period comparison completed successfully",
        )

    return OrchestratorResponse(
        intent=intent,
        tool_name=None,
        result=None,
        message=(
            "Could not determine intent from your query. "
            "Please rephrase your production data question."
        ),
    )
