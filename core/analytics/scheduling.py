"""Heuristic production scheduling optimizer."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from core.db import get_session
from core.logging import get_logger
from models.intents.production import SchedulingParams

logger = get_logger(__name__)


async def optimize_schedule(params: SchedulingParams, workshop_id: str) -> list[dict[str, Any]]:
    session = await get_session()
    try:
        sql = text(
            """
            SELECT mo.mo_number, mo.plan_qty, mo.plan_start_time, mo.plan_end_time
            FROM n2admin.t_aps_plan_mo_info mo
            WHERE mo.data_auth = :workshop_id
              AND mo.plan_start_time >= NOW()
            ORDER BY mo.plan_start_time
            LIMIT 50
            """
        )
        try:
            result = await session.execute(sql, {"workshop_id": workshop_id})
            orders = [dict(r) for r in result.mappings().all()]
        except Exception:
            logger.exception(
                "optimize_production_schedule query failed for workshop=%s line=%s",
                workshop_id,
                params.line_id,
            )
            orders = []
    finally:
        await session.close()

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
