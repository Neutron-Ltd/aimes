"""
F0.3 — LLM Orchestrator (Intent Router).

Pipeline: parse_intent → RAG enrichment → MCP dispatch → synthesis report.

Chat queries (POST /api/v1/query) always execute live MCP tools against
PostgreSQL. They must never read from the SQLite dashboard cache in
core/dashboard_cache/.
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
from orchestrator.module_personas import resolve_module, strip_domain_prefix
from orchestrator.param_mappers import PARAM_MAPPERS
from orchestrator.param_validation import validate_intent_params
from orchestrator.report_generator import _fallback_markdown_report, generate_ai_analysis, get_companion_greeting
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


def _resolve_assistant_module(
    query: str, assistant_module: Optional[str]
) -> tuple[str, str, str]:
    """Return (cleaned_query, resolved_module, original_query)."""
    cleaned, prefix_module = strip_domain_prefix(query)
    module = resolve_module(assistant_module or prefix_module)
    return cleaned, module, query


async def _synthesize_message(
    query: str,
    db_result: dict[str, Any],
    rag_context: Optional[str],
    locale: str = "zh-CN",
    module: Optional[str] = None,
) -> str:
    """Run second-pass LLM synthesis with formatted fallback on any failure."""
    try:
        return await generate_ai_analysis(
            query, db_result, rag_context, locale, module=module
        )
    except Exception:
        logger.exception("Synthesis pipeline failed unexpectedly")
        return _fallback_markdown_report(
            query,
            db_result,
            reason="synthesis pipeline error",
            locale=locale,
            module=module,
        )


async def _run_tool(
    query: str,
    intent_schema,
    tool,
    params,
    context: MCPContext,
    metadata: dict | None = None,
    locale: str = "zh-CN",
    module: Optional[str] = None,
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
        locale,
        module,
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
    locale: str = "zh-CN",
    assistant_module: Optional[str] = None,
) -> OrchestratorResponse:
    cleaned_query, module, _original_query = _resolve_assistant_module(
        query, assistant_module
    )

    intent = await parse_intent(cleaned_query, context, locale)
    logger.info(
        "Parsed intent=%s line=%s module=%s",
        intent.intent,
        intent.line_id,
        module,
    )

    metadata: dict = {"assistant_module": module}
    if enrich_response and intent.intent in RAG_INTENTS:
        rag_context = await retrieve_context(cleaned_query, top_k=5)
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
        params = CrossModuleParams(line_id=intent.line_id.strip(), raw_query=cleaned_query)
        cross_result = await run_cross_module_analysis(params, context)
        result_dict = cross_result.model_dump(mode="json")
        report = await _synthesize_message(
            cleaned_query,
            result_dict,
            metadata.get("rag_context"),
            locale,
            module,
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
            message=get_companion_greeting(locale, module),
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
    return await _run_tool(
        cleaned_query,
        intent,
        tool,
        params,
        context,
        metadata,
        locale,
        module,
    )
