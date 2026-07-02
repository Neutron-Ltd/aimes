"""Heuristic production scheduling optimizer."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from mcp_tools.base import optional_session
from models.intents.production import SchedulingParams

logger = get_logger(__name__)


async def optimize_schedule(
    params: SchedulingParams,
    *,
    session: Optional[AsyncSession] = None,
) -> list[dict[str, Any]]:
    orders: list[dict[str, Any]] = []
    async with optional_session(session) as db:
        sql = text(
            """
            SELECT mo.mo_number, mo.plan_qty, mo.plan_start_time, mo.plan_end_time
            FROM n2admin.t_aps_plan_mo_info mo
            WHERE mo.plan_start_time >= NOW()
            ORDER BY mo.plan_start_time
            LIMIT 50
            """
        )
        try:
            result = await db.execute(sql)
            orders = [dict(r) for r in result.mappings().all()]
        except Exception:
            logger.exception(
                "optimize_production_schedule query failed for line=%s",
                params.line_id,
            )
            orders = []

    if not orders:
        return []

    schedule: list[dict[str, Any]] = []
    for i, order in enumerate(orders):
        qty = float(order.get("plan_qty") or 0)
        urgency = 1.0 - (i * 0.05)
        score = round(min(urgency + (qty / 10000.0), 1.0), 4)
        schedule.append(
            {
                "mo_number": order.get("mo_number"),
                "priority_score": score,
                "plan_start": str(order.get("plan_start_time")),
                "plan_qty": qty,
            }
        )
    return sorted(schedule, key=lambda x: x["priority_score"], reverse=True)
