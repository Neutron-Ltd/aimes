"""HTTP endpoints for the NEUTRON MES AI Assistant (v0.3)."""

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import StreamingResponse

from core.export.excel import export_to_excel
from core.export.pdf import export_to_pdf
from core.rag.ingest import ingest_document
from core.security import get_mes_context
from core.voice.transcribe import transcribe_audio
from models.schemas import (
    ExportRequest,
    MCPContext,
    OrchestratorRequest,
    OrchestratorResponse,
    RagIngestRequest,
    RagIngestResponse,
)
from orchestrator.router import route_and_execute

router = APIRouter(prefix="/api/v1", tags=["orchestrator"])


@router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    from core.config import get_settings

    settings = get_settings()
    return {"status": "ok", "service": "neutron-mes-ai", "version": settings.app_version}


@router.post(
    "/query",
    response_model=OrchestratorResponse,
    summary="Route natural-language query through intent orchestrator",
)
async def query_orchestrator(
    body: OrchestratorRequest,
    request: Request,
) -> OrchestratorResponse:
    context: MCPContext = get_mes_context(request)
    return await route_and_execute(body.query, context, enrich_response=body.enrich_response)


@router.post(
    "/query/voice",
    response_model=OrchestratorResponse,
    summary="Voice query — transcribe audio then route through orchestrator",
)
async def query_voice(
    request: Request,
    audio: UploadFile = File(..., description="wav/mp3/m4a audio file"),
) -> OrchestratorResponse:
    context: MCPContext = get_mes_context(request)
    audio_bytes = await audio.read()
    transcript = await transcribe_audio(audio_bytes, audio.filename or "audio.wav")
    response = await route_and_execute(transcript, context)
    response.transcript = transcript
    return response


@router.post(
    "/rag/ingest",
    response_model=RagIngestResponse,
    summary="Ingest SOP/anomaly/solution document into RAG vector store",
)
async def rag_ingest(body: RagIngestRequest, request: Request) -> RagIngestResponse:
    context: MCPContext = get_mes_context(request)
    if body.doc_type not in ("sop", "anomaly", "solution"):
        return RagIngestResponse(
            success=False,
            backend="",
            message="doc_type must be sop, anomaly, or solution",
        )
    success, chunk_id, backend = await ingest_document(
        body.doc_type, body.text, body.metadata, context.workshop_id
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
