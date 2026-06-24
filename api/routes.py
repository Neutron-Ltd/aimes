"""HTTP endpoints for the NEUTRON MES AI Assistant (v0.3)."""

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from core.chat_store import append_message, clear_history, list_messages
from core.export.excel import export_to_excel
from core.export.pdf import export_to_pdf
from core.rag.ingest import ingest_document
from core.security import HEADER_WORKSHOP_ID, get_mes_context
from core.voice.transcribe import transcribe_audio
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
