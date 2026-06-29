"""HTTP endpoints for the NEUTRON MES AI Assistant (v0.3)."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from core.dashboard.production import production_dashboard_builder
from core.dashboard.warehouse import warehouse_dashboard_builder
from core.config import get_settings
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

DASHBOARD_BUILDERS = {
    "production": production_dashboard_builder,
    "warehouse": warehouse_dashboard_builder,
}


def _require_workshop_id(context: MCPContext) -> str:
    workshop_id = (context.workshop_id or "").strip()
    if not workshop_id:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required header: {HEADER_WORKSHOP_ID}",
        )
    return workshop_id


@router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    from core.config import get_settings

    settings = get_settings()
    return {"status": "ok", "service": "neutron-mes-ai", "version": settings.app_version}


@router.get(
    "/assistants/{module}/dashboard",
    response_model=AssistantDashboardResponse,
    summary="Pre-built dashboard snapshot for an assistant module",
    description=(
        "Returns KPI and chart slot data for the assistant UI. "
        "Calls MCP tools directly (no NL parsing). "
        "Implemented modules: production, warehouse."
    ),
)
async def get_assistant_dashboard(
    module: str,
    request: Request,
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

    settings = get_settings()
    context: MCPContext = get_mes_context(request)

    if module == "production":
        resolved_line = (line_id or settings.default_line_id).strip()
        if not resolved_line:
            raise HTTPException(status_code=400, detail="line_id is required")
        return await builder.build(
            line_id=resolved_line,
            locale=locale,
            lookback_days=lookback_days,
            context=context,
        )

    resolved_wh = wh_code if wh_code is not None else settings.default_wh_code
    if resolved_wh is not None:
        resolved_wh = resolved_wh.strip() or None
    return await builder.build(
        wh_code=resolved_wh,
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
