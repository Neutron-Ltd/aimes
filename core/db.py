"""
F0.4 — Mock Database Connection Manager (MES Data Bridge).

This module simulates a secure, read-only connection pool to the MES
relational database. In production it will wrap asyncpg/SQLAlchemy with
connection pooling, credential rotation, and query timeouts.

IMPORTANT: The AI orchestrator NEVER generates SQL. MCP tools call
predefined repository methods that execute vetted queries server-side.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MockConnection:
    """Simulated database connection handle."""

    dsn: str
    is_connected: bool = True
    _query_log: list[str] = field(default_factory=list)

    async def execute(self, query_name: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """
        Execute a named, pre-approved query stub.

        Real implementation will map query_name → parameterized SQL via
        a query registry; LLMs have no access to this layer.
        """
        self._query_log.append(query_name)
        logger.debug("Mock DB execute: %s params=%s", query_name, params)
        return []

    async def close(self) -> None:
        self.is_connected = False


class DatabaseManager:
    """
    Singleton-style manager for MES database connections.

    Provides async context-managed connections for MCP tool execution.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._dsn = (
            f"postgresql://{settings.db_user}@{settings.db_host}:"
            f"{settings.db_port}/{settings.db_name}"
        )
        self._pool: list[MockConnection] = []
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return
        settings = get_settings()
        for _ in range(settings.db_pool_size):
            self._pool.append(MockConnection(dsn=self._dsn))
        self._initialized = True
        logger.info("Mock database pool initialized (%d connections)", len(self._pool))

    async def shutdown(self) -> None:
        for conn in self._pool:
            await conn.close()
        self._pool.clear()
        self._initialized = False
        logger.info("Mock database pool shut down")

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[MockConnection]:
        if not self._initialized:
            await self.initialize()
        conn = self._pool[0] if self._pool else MockConnection(dsn=self._dsn)
        try:
            yield conn
        finally:
            pass  # Return connection to pool (no-op for mock)


# Module-level singleton used by MCP tools
db_manager = DatabaseManager()
