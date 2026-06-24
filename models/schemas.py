"""Pydantic schemas for intent routing, MCP tool I/O, and API payloads."""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TimeFrame(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    SHIFT = "shift"


class IntentType(str, Enum):
    """Routing paths for v0.3 MCP tools."""

    # Production (Phase 2)
    YIELD_AGGREGATION = "yield_aggregation"
    YIELD_ANOMALIES = "yield_anomalies"
    YIELD_COMPARISON = "yield_comparison"
    PRODUCTION_ROOT_CAUSE = "production_root_cause"
    PRODUCTION_SCHEDULING_OPT = "production_scheduling_opt"
    PRODUCTION_CAPACITY_FORECAST = "production_capacity_forecast"
    PRODUCTION_PRODUCT_YIELD = "production_product_yield"
    PRODUCTION_DEVICE_RATE = "production_device_rate"
    PRODUCTION_STANDARD_TIME = "production_standard_time"

    # Quality (Phase 3)
    QUALITY_DEFECT_ANALYSIS = "quality_defect_analysis"
    QUALITY_ROOT_CAUSE = "quality_root_cause"
    QUALITY_ERROR_PREVENTION = "quality_error_prevention"
    QUALITY_EFFECTIVENESS_VERIFY = "quality_effectiveness_verify"

    # Warehouse (Phase 4)
    WAREHOUSE_INVENTORY_MONITOR = "warehouse_inventory_monitor"
    WAREHOUSE_INBOUND_OUTBOUND = "warehouse_inbound_outbound"
    WAREHOUSE_OBSOLETE_PROFILE = "warehouse_obsolete_profile"
    WAREHOUSE_TRACE_FORWARD = "warehouse_trace_forward"
    WAREHOUSE_TRACE_REVERSE = "warehouse_trace_reverse"

    # System (Phase 5)
    EXPORT_REPORT = "export_report"
    CROSS_MODULE_ANALYSIS = "cross_module_analysis"
    VOICE_QUERY = "voice_query"

    UNKNOWN = "unknown"


class IntentSchema(BaseModel):
    """Structured output from the LLM intent router."""

    intent: IntentType = IntentType.UNKNOWN
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    time_frame: Optional[TimeFrame] = None
    model_code: Optional[str] = None
    product_code: Optional[str] = None
    device_sn: Optional[str] = None
    batch_lot: Optional[str] = None
    material_batch: Optional[str] = None
    finished_lot: Optional[str] = None
    process_code: Optional[str] = None
    line_id: Optional[str] = None
    yield_type: Optional[str] = Field(
        default=None,
        description="equipment or reported — null when not stated by user",
    )
    group_by: Optional[str] = None
    metric: Optional[str] = None
    analysis_type: Optional[str] = None
    threshold_percentage: Optional[float] = None
    period_1_start: Optional[date] = None
    period_1_end: Optional[date] = None
    period_2_start: Optional[date] = None
    period_2_end: Optional[date] = None
    export_format: Optional[str] = Field(default=None, description="xlsx | pdf")
    doc_type: Optional[str] = Field(default=None, description="sop | anomaly | solution")
    wh_code: Optional[str] = None
    item_code: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_query: str = ""


class BailianIntentExtraction(BaseModel):
    """Strict schema for raw Bailian JSON before mapping to IntentSchema."""

    intent: str
    yield_type: Optional[str] = None
    line_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    group_by: Optional[str] = None
    metric: Optional[str] = None
    analysis_type: Optional[str] = None
    threshold_percentage: Optional[float] = None
    period_1_start: Optional[str] = None
    period_1_end: Optional[str] = None
    period_2_start: Optional[str] = None
    period_2_end: Optional[str] = None
    product_code: Optional[str] = None
    model_code: Optional[str] = None
    device_sn: Optional[str] = None
    batch_lot: Optional[str] = None
    material_batch: Optional[str] = None
    finished_lot: Optional[str] = None
    process_code: Optional[str] = None
    export_format: Optional[str] = None
    doc_type: Optional[str] = None
    wh_code: Optional[str] = None
    item_code: Optional[str] = None


class MCPContext(BaseModel):
    """Request context placeholder — no workshop scoping is applied to queries."""

    workshop_id: Optional[str] = None
    user_id: Optional[str] = None
    permission_level: str = "operator"


class OrchestratorRequest(BaseModel):
    query: str = Field(..., min_length=1)
    enrich_response: bool = Field(
        default=True,
        description="When true, attach RAG context to response metadata",
    )
    locale: str = Field(
        default="zh-CN",
        pattern="^(zh-CN|en-US)$",
        description="Locale for synthesized Markdown report (zh-CN or en-US)",
    )


class ChatMessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|error)$")
    content: str = Field(..., min_length=1)
    response_json: Optional[dict[str, Any]] = None


class ChatMessageRecord(BaseModel):
    id: str
    workshop_id: str
    role: str
    content: str
    response_json: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    workshop_id: str
    messages: list[ChatMessageRecord]


class OrchestratorResponse(BaseModel):
    """API response: structured MCP payload plus human-readable Markdown narrative."""

    intent: IntentSchema
    tool_name: Optional[str] = None
    result: Optional[dict[str, Any]] = Field(
        default=None,
        description="Raw structured JSON from the MCP tool (for widgets, export, debugging)",
    )
    message: str = Field(
        default="",
        description="Primary user-facing Markdown report synthesized from result data",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    transcript: Optional[str] = None


class RagIngestRequest(BaseModel):
    doc_type: str = Field(..., description="sop | anomaly | solution")
    text: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagIngestResponse(BaseModel):
    success: bool
    chunk_id: Optional[str] = None
    backend: str
    message: str = ""


class ExportRequest(BaseModel):
    result: dict[str, Any]
    format: str = Field(..., pattern="^(xlsx|pdf)$")
