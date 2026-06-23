"""HTTP endpoints for the NEUTRON MES AI Assistant."""

from fastapi import APIRouter, Request

from core.security import get_mes_context
from models.schemas import MCPContext, OrchestratorRequest, OrchestratorResponse
from orchestrator.router import route_and_execute

router = APIRouter(prefix="/api/v1", tags=["orchestrator"])


@router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "neutron-mes-ai"}


@router.post(
    "/query",
    response_model=OrchestratorResponse,
    summary="Route natural-language query through intent orchestrator",
    description=(
        "Submit a natural-language MES question. The orchestrator extracts "
        "structured parameters (no SQL) and dispatches to the appropriate MCP tool. "
        "Set **X-MES-Workshop-Id** header to simulate RBAC scope in Swagger UI."
    ),
)
async def query_orchestrator(
    body: OrchestratorRequest,
    request: Request,
) -> OrchestratorResponse:
    context: MCPContext = get_mes_context(request)
    return await route_and_execute(body.query, context)
