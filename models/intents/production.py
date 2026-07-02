"""Production module intent parameter models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProductYieldParams(BaseModel):
    line_id: str
    product_code: str
    start_date: datetime
    end_date: datetime


class ProductYieldResult(BaseModel):
    line_id: str
    product_code: str
    total_qty: float
    breakdown: list[dict[str, Any]] = Field(default_factory=list)


class DeviceRateParams(BaseModel):
    device_sn: Optional[str] = None
    line_id: Optional[str] = None
    start_date: datetime
    end_date: datetime


class DeviceRateResult(BaseModel):
    devices: list[dict[str, Any]] = Field(default_factory=list)


class StandardTimeAchievementParams(BaseModel):
    line_id: str
    model_code: str
    start_date: datetime
    end_date: datetime


class StandardTimeAchievementResult(BaseModel):
    line_id: str
    model_code: str
    achievement_pct: float
    actual_qty: float
    standard_time: float
    elapsed_hours: float


class RootCauseParams(BaseModel):
    line_id: str
    start_date: datetime
    end_date: datetime
    yield_type: str = "equipment"


class RootCauseResult(BaseModel):
    line_id: str
    probable_causes: list[dict[str, Any]] = Field(default_factory=list)


class SchedulingParams(BaseModel):
    line_id: str
    horizon_days: int = 7


class SchedulingResult(BaseModel):
    line_id: str
    adjusted_schedule: list[dict[str, Any]] = Field(default_factory=list)


class CapacityForecastParams(BaseModel):
    line_id: Optional[str] = None
    forecast_days: int = 14


class CapacityForecastResult(BaseModel):
    line_id: Optional[str] = None
    capacity_utilization: float
    overtime_hours_estimate: float
    personnel_gap: int
