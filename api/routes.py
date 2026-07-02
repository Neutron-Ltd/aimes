"""HTTP endpoints for the NEUTRON MES AI Assistant (v0.3)."""

import asyncio
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from core.dashboard.production import production_dashboard_builder
from core.dashboard.warehouse import warehouse_dashboard_builder
from core.dashboard.quality import quality_dashboard_builder
from core.dashboard.equipment import equipment_dashboard_builder
from core.dashboard.procurement import procurement_dashboard_builder
from core.bailian import bailian_config_status
from core.config import get_settings
from core.db import check_db_connectivity
from core.dashboard_cache.service import (
    CacheStatus,
    build_dashboard_response,
    build_scope_key,
    get_cached_dashboard,
    put_cached_dashboard,
    refresh_dashboard_module,
)
from core.chat_store import append_message, clear_history, list_messages
from core.export.excel import export_to_excel
from core.export.pdf import export_to_pdf
from core.rag.ingest import ingest_document
from core.security import HEADER_WORKSHOP_ID, get_mes_context
from core.voice.transcribe import transcribe_audio
from models.dashboard import AssistantDashboardResponse
from models.schemas import (
    ChatHistoryResponse,
    ChatMessageCreate,
    ChatMessageRecord,
    ExportRequest,
    MCPContext,
    OrchestratorRequest,
    OrchestratorResponse,
    RagIngestRequest,
    RagIngestResponse,
)
from orchestrator.router import route_and_execute

router = APIRouter(prefix="/api/v1", tags=["orchestrator"])

_REVALIDATION_TASKS: dict[str, asyncio.Task[None]] = {}

DASHBOARD_BUILDERS = {
    "production": production_dashboard_builder,
    "warehouse": warehouse_dashboard_builder,
    "quality": quality_dashboard_builder,
    "equipment": equipment_dashboard_builder,
    "procurement": procurement_dashboard_builder,
}


def _require_workshop_id(context: MCPContext) -> str:
    workshop_id = (context.workshop_id or "").strip()
    if not workshop_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {HEADER_WORKSHOP_ID}",
        )
    return workshop_id


def _resolve_dashboard_params(
    module: str,
    line_id: str | None,
    wh_code: str | None,
) -> tuple[Optional[str], Optional[str], str]:
    settings = get_settings()

    if module in ("production", "quality", "equipment"):
        resolved_line = (line_id or "").strip() or None
        return resolved_line, None, build_scope_key(module, line_id=resolved_line)

    resolved_wh = wh_code if wh_code is not None else settings.default_wh_code
    if resolved_wh is not None:
        resolved_wh = resolved_wh.strip() or None
    return None, resolved_wh, build_scope_key(module, wh_code=resolved_wh)


async def _build_and_cache_dashboard(
    module: str,
    *,
    line_id: Optional[str],
    wh_code: Optional[str],
    scope_key: str,
    locale: str,
    lookback_days: int,
    context: MCPContext,
) -> AssistantDashboardResponse:
    response = await build_dashboard_response(
        module,
        line_id=line_id,
        wh_code=wh_code,
        locale=locale,
        lookback_days=lookback_days,
        context=context,
    )
    await put_cached_dashboard(module, scope_key, locale, lookback_days, response)
    return response


def _revalidation_key(
    module: str,
    line_id: Optional[str],
    wh_code: Optional[str],
    locale: str,
    lookback_days: int,
) -> str:
    scope_key = build_scope_key(module, line_id=line_id, wh_code=wh_code)
    return f"{module}:{scope_key}:{locale}:{lookback_days}"


def _schedule_dashboard_revalidation(
    module: str,
    *,
    line_id: Optional[str],
    wh_code: Optional[str],
    locale: str,
    lookback_days: int,
    context: MCPContext,
) -> None:
    key = _revalidation_key(module, line_id, wh_code, locale, lookback_days)
    existing = _REVALIDATION_TASKS.get(key)
    if existing is not None and not existing.done():
        return

    async def _revalidate() -> None:
        try:
            await refresh_dashboard_module(
                module,
                line_id=line_id,
                wh_code=wh_code,
                locale=locale,
                lookback_days=lookback_days,
                context=context,
            )
        except Exception:
            from core.logging import get_logger

            get_logger(__name__).exception(
                "Background dashboard revalidation failed for %s", module
            )
        finally:
            _REVALIDATION_TASKS.pop(key, None)

    _REVALIDATION_TASKS[key] = asyncio.create_task(_revalidate())


@router.get("/health", summary="Health check", response_model=None)
async def health():
    settings = get_settings()
    body = {
        "status": "ok",
        "service": "neutron-mes-ai",
        "version": settings.app_version,
        "database": "ok",
        "bailian": bailian_config_status(settings),
    }
    if not await check_db_connectivity():
        return JSONResponse(
            status_code=503,
            content={
                **body,
                "status": "degraded",
                "database": "unavailable",
            },
        )
    if body["bailian"] != "ok":
        body["status"] = "degraded"
    return body


@router.get(
    "/assistants/{module}/dashboard",
    response_model=AssistantDashboardResponse,
    summary="Pre-built dashboard snapshot for an assistant module",
    description=(
        "Returns KPI and chart slot data for the assistant UI. "
        "Calls MCP tools directly (no NL parsing). "
        "Implemented modules: production, warehouse, quality, equipment, procurement."
    ),
)
async def get_assistant_dashboard(
    module: str,
    request: Request,
    response: Response,
    line_id: str | None = None,
    wh_code: str | None = None,
    locale: str = "zh-CN",
    lookback_days: int = 7,
) -> AssistantDashboardResponse:
    builder = DASHBOARD_BUILDERS.get(module)
    if builder is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dashboard not implemented for module '{module}'",
        )
    if locale not in ("zh-CN", "en-US"):
        raise HTTPException(status_code=400, detail="locale must be zh-CN or en-US")
    if lookback_days < 1 or lookback_days > 90:
        raise HTTPException(status_code=400, detail="lookback_days must be 1–90")

    context: MCPContext = get_mes_context(request)
    resolved_line, resolved_wh, scope_key = _resolve_dashboard_params(
        module, line_id, wh_code
    )

    cached, cache_status = await get_cached_dashboard(
        module, scope_key, locale, lookback_days
    )
    if cached is not None and cache_status == CacheStatus.HIT:
        response.headers["X-Dashboard-Cache"] = "hit"
        return cached

    if cached is not None and cache_status == CacheStatus.STALE:
        response.headers["X-Dashboard-Cache"] = "stale"
        _schedule_dashboard_revalidation(
            module,
            line_id=resolved_line,
            wh_code=resolved_wh,
            locale=locale,
            lookback_days=lookback_days,
            context=context,
        )
        return cached

    response.headers["X-Dashboard-Cache"] = "miss"
    return await _build_and_cache_dashboard(
        module,
        line_id=resolved_line,
        wh_code=resolved_wh,
        scope_key=scope_key,
        locale=locale,
        lookback_days=lookback_days,
        context=context,
    )


@router.post(
    "/query",
    response_model=OrchestratorResponse,
    summary="Route natural-language query through intent orchestrator",
    description=(
        "Two-pass pipeline: (1) intent extraction + MCP SQL execution, "
        "(2) Bailian synthesis of a Markdown analysis report in `message`. "
        "Raw tool output remains in `result`."
    ),
)
async def query_orchestrator(
    body: OrchestratorRequest,
    request: Request,
) -> OrchestratorResponse:
    context: MCPContext = get_mes_context(request)
    return await route_and_execute(
        body.query,
        context,
        enrich_response=body.enrich_response,
        locale=body.locale,
        assistant_module=body.assistant_module,
    )


@router.post(
    "/query/voice",
    response_model=OrchestratorResponse,
    summary="Voice query — transcribe audio then route through orchestrator",
    description="Same two-pass synthesis as `/query`; `transcript` holds the speech-to-text input.",
)
async def query_voice(
    request: Request,
    audio: UploadFile = File(..., description="wav/mp3/m4a audio file"),
    locale: str = Form(default="zh-CN"),
) -> OrchestratorResponse:
    context: MCPContext = get_mes_context(request)
    audio_bytes = await audio.read()
    transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.wav")
    response = await route_and_execute(transcript, context, locale=locale)
    response.transcript = transcript
    return response


@router.get(
    "/chat/history",
    response_model=ChatHistoryResponse,
    summary="Load chat history for the current workshop",
)
async def get_chat_history(request: Request) -> ChatHistoryResponse:
    context: MCPContext = get_mes_context(request)
    workshop_id = _require_workshop_id(context)
    rows = await list_messages(workshop_id)
    messages = [ChatMessageRecord(**row) for row in rows]
    return ChatHistoryResponse(workshop_id=workshop_id, messages=messages)


@router.post(
    "/chat/messages",
    response_model=ChatMessageRecord,
    summary="Append a chat message for the current workshop",
)
async def post_chat_message(
    body: ChatMessageCreate,
    request: Request,
) -> ChatMessageRecord:
    context: MCPContext = get_mes_context(request)
    workshop_id = _require_workshop_id(context)
    row = await append_message(
        workshop_id,
        body.role,
        body.content,
        body.response_json,
    )
    return ChatMessageRecord(**row)


@router.delete(
    "/chat/history",
    summary="Clear chat history for the current workshop",
)
async def delete_chat_history(request: Request) -> dict[str, int | str]:
    context: MCPContext = get_mes_context(request)
    workshop_id = _require_workshop_id(context)
    deleted = await clear_history(workshop_id)
    return {"workshop_id": workshop_id, "deleted": deleted}


@router.post(
    "/rag/ingest",
    response_model=RagIngestResponse,
    summary="Ingest SOP/anomaly/solution document into RAG vector store",
)
async def rag_ingest(body: RagIngestRequest, request: Request) -> RagIngestResponse:
    if body.doc_type not in ("sop", "anomaly", "solution"):
        return RagIngestResponse(
            success=False,
            backend="",
            message="doc_type must be sop, anomaly, or solution",
        )
    success, chunk_id, backend = await ingest_document(
        body.doc_type, body.text, body.metadata
    )
    return RagIngestResponse(
        success=success,
        chunk_id=chunk_id,
        backend=backend,
        message="Document ingested successfully" if success else "Ingestion failed",
    )


@router.post("/export", summary="Export orchestrator result as xlsx or pdf")
async def export_report(body: ExportRequest) -> StreamingResponse:
    if body.format == "xlsx":
        content = export_to_excel(body.result)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "neutron_report.xlsx"
    else:
        content = export_to_pdf(body.result)
        media_type = "application/pdf"
        filename = "neutron_report.pdf"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
