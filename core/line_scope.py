"""Shared SQL predicates for production line scoping (equipment + reported)."""

from __future__ import annotations

from typing import Optional


def equipment_scope_filter(
    line_id: Optional[str],
    device_sn: Optional[str],
    *,
    alias: str = "eq",
) -> str:
    """
    Scope equipment consumption rows by device or line.

    Line codes (e.g. FDQ-SMT-6) match area_sn directly; Chinese names
    (e.g. 防盗器贴片六线) resolve via t_co_area.area_name.
    """
    if device_sn:
        return f"{alias}.device_sn = :device_sn"
    if line_id:
        return f"""(
            {alias}.area_sn = :line_id
            OR {alias}.area_sn IN (
                SELECT a.area_sn FROM n2admin.t_co_area a
                WHERE a.area_sn = :line_id OR a.area_name = :line_id
            )
        )"""
    return "1=1"


def equipment_line_area_sn_subquery() -> str:
    """Subquery returning canonical area_sn values for a :line_id bind param."""
    return """(
        SELECT a.area_sn FROM n2admin.t_co_area a
        WHERE a.area_sn = :line_id OR a.area_name = :line_id
    )"""


def reported_line_filter(*, alias: str = "line") -> str:
    """Filter reported WIP rows joined to a line node (code or Chinese name)."""
    return f"({alias}.area_sn = :line_id OR {alias}.area_name = :line_id)"
