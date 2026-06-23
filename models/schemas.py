"""Pydantic schemas for intent routing, MCP tool I/O, and API payloads."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TimeFrame(str, Enum):
    """Supported aggregation windows for production queries."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    SHIFT = "shift"


class IntentType(str, Enum):
    """Known intents the orchestrator can route to MCP tools."""

    PRODUCTION_DATA = "production_data"
    UNKNOWN = "unknown"


class IntentSchema(BaseModel):
    """
    Structured output from the LLM intent router.

    The orchestrator maps natural language to this schema; no raw SQL is
    generated — only typed parameters consumed by predefined MCP tools.
    """

    intent: IntentType = IntentType.UNKNOWN
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    time_frame: Optional[TimeFrame] = None
    model_code: Optional[str] = None
    line_id: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_query: str = ""


class MCPContext(BaseModel):
    """
    RBAC context injected by middleware and forwarded to every MCP tool call.

    workshop_id scopes data access to the caller's MES permission boundary.
    """

    workshop_id: str
    user_id: Optional[str] = None
    permission_level: str = "operator"


class ProductionDataParams(BaseModel):
    """Input parameters for the Production Data MCP tool."""

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    time_frame: Optional[TimeFrame] = None
    model_code: Optional[str] = None
    line_id: Optional[str] = None
    workshop_id: str


class ProductionDataResult(BaseModel):
    """Aggregated production metrics returned by the Production Data MCP tool."""

    workshop_id: str
    line_id: Optional[str] = None
    model_code: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    time_frame: Optional[str] = None
    total_reported: int = 0
    total_equipment: int = 0
    yield_rate: float = Field(description="Equipment yield as a percentage (0–100)")
    defect_count: int = 0
    aggregated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestratorRequest(BaseModel):
    """API request body for the intent-routing endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        examples=[
            "Calculate the total reported/equipment yield of the corresponding "
            "products on line L-03 for the current day"
        ],
    )


class OrchestratorResponse(BaseModel):
    """Full pipeline response: parsed intent + MCP tool result."""

    intent: IntentSchema
    tool_name: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    message: str = ""
