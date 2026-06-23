"""
F0.2 — LLM Orchestrator (Intent Router).

Pipeline:
  1. User natural-language query arrives via FastAPI.
  2. parse_intent() mocks an LLM call and returns IntentSchema (structured params).
  3. route_and_execute() maps intent → MCP tool and invokes it with RBAC context.

The orchestrator NEVER prompts an LLM to write SQL. It only extracts typed
parameters and dispatches to predefined MCP tools.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core.logging import get_logger
from mcp_tools.base import MCPToolResult
from mcp_tools.production_data import production_data_tool
from models.schemas import (
    IntentSchema,
    IntentType,
    MCPContext,
    OrchestratorResponse,
    ProductionDataParams,
    TimeFrame,
)

logger = get_logger(__name__)

# Keywords that signal production/yield intents (mock LLM classification)
_PRODUCTION_KEYWORDS = (
    "yield",
    "production",
    "reported",
    "equipment",
    "throughput",
    "output",
    "defect",
    "line",
)

_LINE_PATTERN = re.compile(r"\b(?:line\s+)?([Ll]-?\d{1,2})\b")
_MODEL_PATTERN = re.compile(r"\b(?:model\s+)?(MDL-[\w-]+)\b", re.IGNORECASE)
_DATE_TODAY = re.compile(r"\b(current\s+day|today|this\s+day)\b", re.IGNORECASE)


def parse_intent(query: str) -> IntentSchema:
    """
    Mock LLM intent extraction.

    Production replacement: call an LLM with a structured-output schema
    (IntentSchema JSON mode / function calling) — still NO SQL generation.
    """
    normalized = query.strip()
    lower = normalized.lower()

    intent = IntentType.UNKNOWN
    confidence = 0.3

    if any(kw in lower for kw in _PRODUCTION_KEYWORDS):
        intent = IntentType.PRODUCTION_DATA
        confidence = 0.85

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    time_frame: Optional[TimeFrame] = None
    line_id: Optional[str] = None
    model_code: Optional[str] = None

    if _DATE_TODAY.search(lower):
        start_date = date.today()
        end_date = date.today()
        time_frame = TimeFrame.DAY
        confidence = min(confidence + 0.1, 1.0)

    line_match = _LINE_PATTERN.search(normalized)
    if line_match:
        token = line_match.group(1).upper().replace(" ", "")
        line_id = token if token.startswith("L-") else f"L-{token.lstrip('L').lstrip('-')}"
        confidence = min(confidence + 0.05, 1.0)

    model_match = _MODEL_PATTERN.search(normalized)
    if model_match:
        model_code = model_match.group(1).upper()

    if "week" in lower:
        time_frame = TimeFrame.WEEK
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
    elif "month" in lower:
        time_frame = TimeFrame.MONTH
        end_date = date.today()
        start_date = end_date - timedelta(days=29)

    return IntentSchema(
        intent=intent,
        start_date=start_date,
        end_date=end_date,
        time_frame=time_frame,
        model_code=model_code,
        line_id=line_id,
        confidence=confidence,
        raw_query=normalized,
    )


def _intent_to_production_params(
    intent: IntentSchema, context: MCPContext
) -> ProductionDataParams:
    """
    Map parsed intent fields → Production Data MCP tool input model.

    workshop_id always comes from RBAC context, never from user free text.
    """
    return ProductionDataParams(
        start_date=intent.start_date,
        end_date=intent.end_date,
        time_frame=intent.time_frame,
        model_code=intent.model_code,
        line_id=intent.line_id,
        workshop_id=context.workshop_id,
    )


async def route_and_execute(
    query: str, context: MCPContext
) -> OrchestratorResponse:
    """
    End-to-end orchestration: NL query → intent → MCP tool → response.

    This is the central connection point between the LLM router and MCP tools:
      parse_intent() produces IntentSchema
      match intent type to registered tool
      tool.run(params, context) executes with RBAC-scoped workshop_id
    """
    intent = parse_intent(query)
    logger.info(
        "Parsed intent=%s confidence=%.2f workshop=%s",
        intent.intent,
        intent.confidence,
        context.workshop_id,
    )

    if intent.intent == IntentType.PRODUCTION_DATA:
        # --- Orchestrator → MCP Tool dispatch ---
        params = _intent_to_production_params(intent, context)
        tool_result: MCPToolResult = await production_data_tool.run(params, context)

        if not tool_result.success:
            return OrchestratorResponse(
                intent=intent,
                tool_name=production_data_tool.name,
                result=None,
                message=tool_result.error or "MCP tool execution failed",
            )

        return OrchestratorResponse(
            intent=intent,
            tool_name=production_data_tool.name,
            result=tool_result.data,
            message="Production data retrieved successfully",
        )

    return OrchestratorResponse(
        intent=intent,
        tool_name=None,
        result=None,
        message=(
            "Could not route query to a known MCP tool. "
            "Refine your question to include production/yield/line context."
        ),
    )
