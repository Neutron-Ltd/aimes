"""Quality module intent parameter models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DefectAggregationParams(BaseModel):
    line_id: Optional[str] = None
    process_code: Optional[str] = None
    start_date: datetime
    end_date: datetime


class DefectAggregationResult(BaseModel):
    workshop_id: str
    defect_rate: float
    total_inspected: int
    total_defects: int
    breakdown: list[dict[str, Any]] = Field(default_factory=list)


class QualityRootCauseParams(BaseModel):
    process_code: Optional[str] = None
    batch_lot: Optional[str] = None
    start_date: datetime
    end_date: datetime


class QualityRootCauseResult(BaseModel):
    workshop_id: str
    hypotheses: list[dict[str, Any]] = Field(default_factory=list)


class ErrorPreventionParams(BaseModel):
    process_code: str
    model_code: Optional[str] = None


class ErrorPreventionResult(BaseModel):
    workshop_id: str
    process_code: str
    omissions: list[str] = Field(default_factory=list)
    checklist_items: list[dict[str, Any]] = Field(default_factory=list)


class EffectivenessVerifyParams(BaseModel):
    process_code: Optional[str] = None
    milestone_date: datetime
    comparison_days: int = 30


class EffectivenessVerifyResult(BaseModel):
    workshop_id: str
    before_defect_rate: float
    after_defect_rate: float
    growth_rate: Optional[float] = None
