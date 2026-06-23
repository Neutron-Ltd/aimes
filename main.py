"""
NEUTRON MES AI Assistant — FastAPI entry point (Phase 1).

Bootstraps core orchestration, MCP data bridge, and RBAC middleware.
Use Swagger UI at /docs for API-first testing until the Vue.js frontend is ready.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from api.routes import router
from core.config import get_settings
from core.db import close_db, init_db
from core.logging import setup_logging
from core.security import RBACMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Enterprise MES AI Assistant backend. "
            "Intent routing via LLM → structured MCP tool dispatch. "
            "No Text-to-SQL."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Feature 13.1 — inject workshop_id / permission context on every request
    app.add_middleware(RBACMiddleware)

    app.include_router(router)

    return app


app = create_app()
