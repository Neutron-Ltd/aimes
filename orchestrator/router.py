"""
F0.3 — LLM Orchestrator (Intent Router).

Pipeline: parse_intent → RAG enrichment → tool registry dispatch.
"""

from __future__ import annotations

from core.config import get_settings
from core.logging import get_logger
from core.rag.retriever import retrieve_context
from mcp_tools.base import MCPToolResult
from models.intents.system import CrossModuleParams
from models.schemas import IntentType, MCPContext, OrchestratorResponse
from orchestrator.cross_module import run_cross_module_analysis
from orchestrator.intent_utils import RAG_INTENTS, parse_intent
from orchestrator.param_mappers import PARAM_MAPPERS
from orchestrator.param_validation import validate_intent_params
from orchestrator.tool_registry import get_tool_for_intent, register_all_tools

logger = get_logger(__name__)

register_all_tools(PARAM_MAPPERS)


async def _run_tool(
    intent_schema,
    tool,
    params,
    context: MCPContext,
    success_message: str,
    metadata: dict | None = None,
) -> OrchestratorResponse:
    tool_result: MCPToolResult = await tool.run(params, context)
    meta = metadata or {}

    if not tool_result.success:
        return OrchestratorResponse(
            intent=intent_schema,
            tool_name=tool.name,
            result=None,
            message=tool_result.error or "MCP tool execution failed",
            metadata=meta,
        )

    return OrchestratorResponse(
        intent=intent_schema,
        tool_name=tool.name,
        result=tool_result.data,
        message=success_message,
        metadata=meta,
    )


async def route_and_execute(
    query: str,
    context: MCPContext,
    enrich_response: bool = True,
) -> OrchestratorResponse:
    intent = await parse_intent(query, context)
    logger.info(
        "Parsed intent=%s line=%s workshop=%s",
        intent.intent,
        intent.line_id,
        context.workshop_id,
    )

    metadata: dict = {}
    if enrich_response and intent.intent in RAG_INTENTS:
        rag_context = await retrieve_context(query, context.workshop_id, top_k=5)
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
        result = await run_cross_module_analysis(params, context)
        return OrchestratorResponse(
            intent=intent,
            tool_name="cross_module_analysis",
            result=result.model_dump(mode="json"),
            message=result.summary,
            metadata=metadata,
        )

    if intent.intent == IntentType.EXPORT_REPORT:
        return OrchestratorResponse(
            intent=intent,
            tool_name=None,
            result={"export_format": intent.export_format or "xlsx", "hint": "POST /api/v1/export"},
            message="Use POST /api/v1/export with the orchestrator result payload.",
            metadata=metadata,
        )

    if intent.intent == IntentType.UNKNOWN:
        return OrchestratorResponse(
            intent=intent,
            tool_name=None,
            result=None,
            message="Could not determine intent. Please rephrase your MES question.",
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

    tool, mapper, success_message = entry

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
    return await _run_tool(intent, tool, params, context, success_message, metadata)
