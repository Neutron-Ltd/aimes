"""System-level intent parameter models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CrossModuleParams(BaseModel):
    line_id: str
    raw_query: str = ""


class CrossModuleResult(BaseModel):
    workshop_id: str
    modules: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
