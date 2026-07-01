"""
NEUTRON MES AI Assistant — FastAPI entry point (Phase 1).

Bootstraps core orchestration, MCP data bridge, and RBAC middleware.
Use Swagger UI at /docs for API-first testing until the Vue.js frontend is ready.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from api.routes import router
from core.config import get_settings
from core.db import close_db, init_db
from core.dashboard_cache.scheduler import (
    start_dashboard_cache_scheduler,
    stop_dashboard_cache_scheduler,
)
from core.logging import setup_logging
from core.security import RBACMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    await init_db()
    start_dashboard_cache_scheduler()
    yield
    await stop_dashboard_cache_scheduler()
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

    # Request context middleware (no workshop scoping)
    app.add_middleware(RBACMiddleware)

    # Allow the Vite dev server (and other local frontends) to call the API from the browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """Browser-friendly entry point → Swagger UI."""
        return RedirectResponse(url="/docs")

    return app


app = create_app()
