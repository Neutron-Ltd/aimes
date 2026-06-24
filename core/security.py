"""
Request context middleware (RBAC disabled).

Workshop / permission headers are ignored; no row-level scope is injected.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from models.schemas import MCPContext

# Header names retained for API compatibility; values are not used for data scoping.
HEADER_WORKSHOP_ID = "X-MES-Workshop-Id"
HEADER_USER_ID = "X-MES-User-Id"
HEADER_PERMISSION_LEVEL = "X-MES-Permission-Level"


class RBACMiddleware(BaseHTTPMiddleware):
    """Injects MCP context from headers — no row-level data scoping enforced."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.mes_context = MCPContext(
            workshop_id=request.headers.get(HEADER_WORKSHOP_ID),
            user_id=request.headers.get(HEADER_USER_ID),
            permission_level=request.headers.get(HEADER_PERMISSION_LEVEL) or "operator",
        )
        return await call_next(request)


def get_mes_context(request: Request) -> MCPContext:
    """FastAPI dependency — retrieve request context (no RBAC scope)."""
    ctx: Optional[MCPContext] = getattr(request.state, "mes_context", None)
    if ctx is None:
        return MCPContext()
    return ctx


def get_mes_context_from_headers(
    x_mes_workshop_id: Optional[str] = None,
    x_mes_user_id: Optional[str] = None,
    x_mes_permission_level: Optional[str] = None,
) -> MCPContext:
    """Swagger-compatible dependency; headers are accepted but not enforced."""
    return MCPContext(
        workshop_id=x_mes_workshop_id,
        user_id=x_mes_user_id,
        permission_level=x_mes_permission_level or "operator",
    )


MESContextDep = Depends(get_mes_context)
