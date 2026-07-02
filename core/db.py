"""
F0.4 — Async SQLAlchemy Database Bridge (MES Data Bridge).

Provides a non-blocking PostgreSQL connection pool for time-series
aggregations. MCP tools receive sessions via get_db() or async_session_factory.

IMPORTANT: The AI orchestrator NEVER generates SQL. MCP tools execute
predefined, parameterized queries via sqlalchemy.text() only.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None
_pg_work_sem: asyncio.Semaphore | None = None


def _get_pg_work_sem() -> asyncio.Semaphore:
    global _pg_work_sem
    if _pg_work_sem is None:
        settings = get_settings()
        _pg_work_sem = asyncio.Semaphore(settings.db_pg_work_concurrency)
    return _pg_work_sem


@asynccontextmanager
async def pg_work_slot() -> AsyncIterator[None]:
    """Limit concurrent dashboard-style PG builds across scheduler and HTTP paths."""
    async with _get_pg_work_sem():
        yield


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": settings.debug,
    }
    if settings.db_pool_size == 0:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
    return create_async_engine(settings.database_url, **engine_kwargs)


async def init_db() -> None:
    """Initialize engine and verify connectivity (SELECT 1)."""
    global engine, async_session_factory

    if engine is not None:
        return

    try:
        engine = _build_engine()
    except ValueError as exc:
        logger.error(
            "Invalid DATABASE_URL — check .env (port must be numeric, not a placeholder): %s",
            exc,
        )
        raise

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connectivity check failed")
        await close_db()
        raise

    pool_mode = "NullPool" if get_settings().db_pool_size == 0 else "QueuePool"
    logger.info("Database connection pool initialized (%s)", pool_mode)


async def close_db() -> None:
    """Dispose engine and release pool connections."""
    global engine, async_session_factory

    if engine is not None:
        await engine.dispose()
        logger.info("Database connection pool shut down")

    engine = None
    async_session_factory = None


async def check_db_connectivity() -> bool:
    """Return True if PostgreSQL responds to SELECT 1."""
    if engine is None:
        return False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency — yields an async session per request.

    Inject into route handlers or MCP tool execution via Depends(get_db).
    """
    if async_session_factory is None:
        await init_db()

    assert async_session_factory is not None

    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_session() -> AsyncSession:
    """Acquire a standalone session for MCP tool execution outside HTTP deps."""
    if async_session_factory is None:
        await init_db()

    assert async_session_factory is not None
    return async_session_factory()
