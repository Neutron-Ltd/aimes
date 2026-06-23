"""
Feature 13.1 — RBAC Context Injector (Middleware Prep).

Simulates integration with the existing MES permission system by reading
identity/scope headers and injecting workshop context into each request.

Production flow: validate JWT/session → resolve MES roles → set workshop_id.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.config import get_settings
from core.logging import get_logger
from models.schemas import MCPContext

logger = get_logger(__name__)

# Header names aligned with future MES gateway integration
HEADER_WORKSHOP_ID = "X-MES-Workshop-Id"
HEADER_USER_ID = "X-MES-User-Id"
HEADER_PERMISSION_LEVEL = "X-MES-Permission-Level"


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Injects MES RBAC context into request.state before route handlers run.

    Swagger UI testers can pass headers manually to simulate different
    permission scopes without a full auth stack.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()

        workshop_id = request.headers.get(HEADER_WORKSHOP_ID, settings.default_workshop_id)
        user_id = request.headers.get(HEADER_USER_ID)
        permission_level = request.headers.get(HEADER_PERMISSION_LEVEL, "operator")

        request.state.mes_context = MCPContext(
            workshop_id=workshop_id,
            user_id=user_id,
            permission_level=permission_level,
        )

        logger.debug(
            "RBAC context injected: workshop=%s user=%s level=%s",
            workshop_id,
            user_id,
            permission_level,
        )

        return await call_next(request)


def get_mes_context(request: Request) -> MCPContext:
    """FastAPI dependency — retrieve RBAC context from request state."""
    ctx: Optional[MCPContext] = getattr(request.state, "mes_context", None)
    if ctx is None:
        settings = get_settings()
        return MCPContext(workshop_id=settings.default_workshop_id)
    return ctx


def get_mes_context_from_headers(
    x_mes_workshop_id: Optional[str] = Header(None, alias=HEADER_WORKSHOP_ID),
    x_mes_user_id: Optional[str] = Header(None, alias=HEADER_USER_ID),
    x_mes_permission_level: Optional[str] = Header(
        None, alias=HEADER_PERMISSION_LEVEL
    ),
) -> MCPContext:
    """
    Alternative dependency for endpoints that need explicit header docs in Swagger.

    Prefer get_mes_context(request) in route handlers; middleware already
    populates request.state.
    """
    settings = get_settings()
    return MCPContext(
        workshop_id=x_mes_workshop_id or settings.default_workshop_id,
        user_id=x_mes_user_id,
        permission_level=x_mes_permission_level or "operator",
    )


# Type alias for cleaner route signatures
MESContextDep = Depends(get_mes_context)
