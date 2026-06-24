"""
F0.3 — LLM Orchestrator (Intent Router).

Pipeline: parse_intent → RAG enrichment → MCP dispatch → synthesis report.
"""

from __future__ import annotations

from typing import Any, Optional

from core.logging import get_logger
from core.rag.retriever import retrieve_context
from mcp_tools.base import MCPToolResult
from models.intents.system import CrossModuleParams
from models.schemas import IntentType, MCPContext, OrchestratorResponse
from orchestrator.cross_module import run_cross_module_analysis
from orchestrator.intent_utils import RAG_INTENTS, parse_intent
from orchestrator.param_mappers import PARAM_MAPPERS
from orchestrator.param_validation import validate_intent_params
from orchestrator.report_generator import COMPANION_GREETING, _fallback_markdown_report, generate_ai_analysis
from orchestrator.tool_registry import get_tool_for_intent, register_all_tools

logger = get_logger(__name__)

register_all_tools(PARAM_MAPPERS)

# Intents that return guidance only — skip second-pass synthesis
_NO_SYNTHESIS_INTENTS = frozenset(
    {
        IntentType.UNKNOWN,
        IntentType.EXPORT_REPORT,
    }
)


async def _synthesize_message(
    query: str,
    db_result: dict[str, Any],
    rag_context: Optional[str],
) -> str:
    """Run second-pass LLM synthesis with formatted fallback on any failure."""
    try:
        return await generate_ai_analysis(query, db_result, rag_context)
    except Exception:
        logger.exception("Synthesis pipeline failed unexpectedly")
        return _fallback_markdown_report(query, db_result, reason="synthesis pipeline error")


async def _run_tool(
    query: str,
    intent_schema,
    tool,
    params,
    context: MCPContext,
    metadata: dict | None = None,
) -> OrchestratorResponse:
    tool_result: MCPToolResult = await tool.run(params, context)
    meta = metadata or {}
    rag_context = meta.get("rag_context")

    if not tool_result.success:
        return OrchestratorResponse(
            intent=intent_schema,
            tool_name=tool.name,
            result=None,
            message=tool_result.error or "MCP tool execution failed",
            metadata=meta,
        )

    report = await _synthesize_message(
        query,
        tool_result.data,
        rag_context,
    )

    return OrchestratorResponse(
        intent=intent_schema,
        tool_name=tool.name,
        result=tool_result.data,
        message=report,
        metadata=meta,
    )


async def route_and_execute(
    query: str,
    context: MCPContext,
    enrich_response: bool = True,
) -> OrchestratorResponse:
    intent = await parse_intent(query, context)
    logger.info(
        "Parsed intent=%s line=%s",
        intent.intent,
        intent.line_id,
    )

    metadata: dict = {}
    if enrich_response and intent.intent in RAG_INTENTS:
        rag_context = await retrieve_context(query, top_k=5)
        if rag_context:
            metadata["rag_context"] = rag_context

    if intent.intent == IntentType.CROSS_MODULE_ANALYSIS:
        validation = validate_intent_params(intent)
        if not validation.ok:
            return OrchestratorResponse(
                intent=intent,
                tool_name="cross_module_analysis",
                result=None,
                message=validation.message,
                metadata=metadata,
            )
        params = CrossModuleParams(line_id=intent.line_id.strip(), raw_query=query)
        cross_result = await run_cross_module_analysis(params, context)
        result_dict = cross_result.model_dump(mode="json")
        report = await _synthesize_message(
            query,
            result_dict,
            metadata.get("rag_context"),
        )
        return OrchestratorResponse(
            intent=intent,
            tool_name="cross_module_analysis",
            result=result_dict,
            message=report,
            metadata=metadata,
        )

    if intent.intent in _NO_SYNTHESIS_INTENTS:
        if intent.intent == IntentType.EXPORT_REPORT:
            return OrchestratorResponse(
                intent=intent,
                tool_name=None,
                result={"export_format": intent.export_format or "xlsx", "hint": "POST /api/v1/export"},
                message="Use POST /api/v1/export with the orchestrator result payload.",
                metadata=metadata,
            )
        return OrchestratorResponse(
            intent=intent,
            tool_name=None,
            result=None,
            message=COMPANION_GREETING,
            metadata=metadata,
        )

    entry = get_tool_for_intent(intent.intent)
    if not entry:
        return OrchestratorResponse(
            intent=intent,
            tool_name=None,
            result=None,
            message=f"No tool registered for intent: {intent.intent.value}",
            metadata=metadata,
        )

    tool, mapper, _ = entry

    validation = validate_intent_params(intent)
    if not validation.ok:
        return OrchestratorResponse(
            intent=intent,
            tool_name=tool.name,
            result=None,
            message=validation.message,
            metadata=metadata,
        )

    params = mapper(intent)
    return await _run_tool(query, intent, tool, params, context, metadata)
