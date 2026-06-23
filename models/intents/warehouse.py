"""Warehouse module intent parameter models."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class InventoryStatusParams(BaseModel):
    wh_code: Optional[str] = None
    item_code: Optional[str] = None


class InventoryStatusResult(BaseModel):
    workshop_id: str
    low_stock: list[dict[str, Any]] = Field(default_factory=list)
    expiring: list[dict[str, Any]] = Field(default_factory=list)


class InboundOutboundParams(BaseModel):
    wh_code: str
    item_code: str
    direction: str = Field(default="outbound", description="inbound | outbound")


class InboundOutboundResult(BaseModel):
    workshop_id: str
    recommended_bay: Optional[str] = None
    fifo_lots: list[dict[str, Any]] = Field(default_factory=list)


class ObsoleteProfileParams(BaseModel):
    wh_code: Optional[str] = None
    dull_days_threshold: int = 90


class ObsoleteProfileResult(BaseModel):
    workshop_id: str
    stagnant_items: list[dict[str, Any]] = Field(default_factory=list)


class TraceForwardParams(BaseModel):
    material_batch: str


class TraceForwardResult(BaseModel):
    workshop_id: str
    chain: list[dict[str, Any]] = Field(default_factory=list)


class TraceReverseParams(BaseModel):
    finished_lot: str


class TraceReverseResult(BaseModel):
    workshop_id: str
    chain: list[dict[str, Any]] = Field(default_factory=list)
