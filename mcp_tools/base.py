"""
Base class for all MCP tools in the NEUTRON MES AI Assistant.

Each tool is a self-contained, typed function that the LLM orchestrator
invokes with structured parameters — never free-form SQL.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_session
from core.logging import get_logger
from models.schemas import MCPContext

logger = get_logger(__name__)

TParams = TypeVar("TParams", bound=BaseModel)
TResult = TypeVar("TResult", bound=BaseModel)


@asynccontextmanager
async def optional_session(
    session: AsyncSession | None = None,
) -> AsyncIterator[AsyncSession]:
    """Yield an existing session or acquire and close a standalone one."""
    if session is not None:
        yield session
        return
    owned = await get_session()
    try:
        yield owned
    finally:
        await owned.close()


class MCPToolResult(BaseModel):
    """Standard envelope returned by every MCP tool execution."""

    tool_name: str
    success: bool = True
    data: dict[str, Any]
    error: str | None = None


class BaseMCPTool(ABC, Generic[TParams, TResult]):
    """
    Abstract MCP tool contract.

    Subclasses declare:
      - name: unique tool identifier used by the orchestrator router
      - description: human-readable purpose (for future LLM tool-calling)
      - params_model / result_model: Pydantic types for I/O validation
    """

    name: str
    description: str

    @abstractmethod
    async def execute(
        self,
        params: TParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> TResult:
        """Run the tool with validated parameters."""
        ...

    async def run(
        self,
        params: TParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> MCPToolResult:
        """
        Public entry point — validates, executes, and wraps the result.

        The orchestrator calls run() after mapping IntentSchema → tool params.
        Dashboard builders may pass a shared session to cap connection use.
        """
        try:
            result = await self.execute(params, context, session=session)
            logger.info("MCP tool '%s' completed", self.name)
            return MCPToolResult(
                tool_name=self.name,
                success=True,
                data=result.model_dump(mode="json"),
            )
        except Exception as exc:
            logger.exception("MCP tool '%s' failed", self.name)
            return MCPToolResult(
                tool_name=self.name,
                success=False,
                data={},
                error=str(exc),
            )
