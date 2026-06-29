"""Shared dashboard API schemas for assistant module snapshots."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DataSource(str, Enum):
    LIVE = "live"
    FALLBACK = "fallback"


class DashboardKpiSlot(BaseModel):
    index: int = Field(..., ge=0, description="KPI card index matching frontend layout")
    value: str
    trend: Optional[str] = None
    source: DataSource = DataSource.LIVE


class DashboardChartSlot(BaseModel):
    index: int = Field(..., ge=0, description="Chart mosaic index matching frontend layout")
    chart_type: Literal["line", "bar", "gauge"]
    x_data: list[str] = Field(default_factory=list)
    series: list[float] = Field(default_factory=list)
    gauge_value: Optional[float] = None
    source: DataSource = DataSource.LIVE


class AssistantDashboardResponse(BaseModel):
    module: str
    line_id: str
    kpis: list[DashboardKpiSlot]
    charts: list[DashboardChartSlot]
    insight: Optional[str] = None
    partial: bool = Field(
        default=False,
        description="True when one or more slots use fallback data",
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)
