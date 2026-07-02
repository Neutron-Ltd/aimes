"""Capacity forecasting — utilization, overtime, personnel gap estimates."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.intents.production import CapacityForecastParams
from core.line_scope import equipment_scope_filter
from mcp_tools.base import optional_session


async def forecast_capacity(
    params: CapacityForecastParams,
    *,
    session: Optional[AsyncSession] = None,
) -> dict[str, float | int]:
    async with optional_session(session) as db:
        end = datetime.now()
        start = end - timedelta(days=30)
        if params.line_id:
            line_predicate = equipment_scope_filter(params.line_id, None, alias="eq")
            sql = text(
                f"""
                SELECT SUM(COALESCE(eq.finish_qty, 0)) AS total_qty,
                       COUNT(DISTINCT date_trunc('day', eq.create_time)) AS active_days
                FROM n2admin.t_smt_program_consumption_record eq
                WHERE {line_predicate}
                  AND eq.create_time BETWEEN :start_date AND :end_date
                """
            )
            bind = {
                "line_id": params.line_id,
                "start_date": start,
                "end_date": end,
            }
        else:
            sql = text(
                """
                SELECT SUM(COALESCE(eq.finish_qty, 0)) AS total_qty,
                       COUNT(DISTINCT date_trunc('day', eq.create_time)) AS active_days
                FROM n2admin.t_smt_program_consumption_record eq
                WHERE eq.create_time BETWEEN :start_date AND :end_date
                """
            )
            bind = {
                "start_date": start,
                "end_date": end,
            }
        result = await db.execute(sql, bind)
        row = result.mappings().first() or {}

    total_qty = float(row.get("total_qty") or 0)
    active_days = max(int(row.get("active_days") or 1), 1)
    daily_avg = total_qty / active_days
    forecast_demand = daily_avg * params.forecast_days
    assumed_capacity = daily_avg * 1.1 * params.forecast_days
    utilization = min((forecast_demand / assumed_capacity) * 100.0, 150.0) if assumed_capacity else 0.0
    overtime = max(0.0, (utilization - 100.0) * 0.4)
    personnel_gap = max(0, int((utilization - 95.0) / 10.0))

    return {
        "capacity_utilization": round(utilization, 4),
        "overtime_hours_estimate": round(overtime, 4),
        "personnel_gap": personnel_gap,
    }
