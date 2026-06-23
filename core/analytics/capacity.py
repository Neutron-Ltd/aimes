"""Capacity forecasting — utilization, overtime, personnel gap estimates."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text

from core.db import get_session
from models.intents.production import CapacityForecastParams


async def forecast_capacity(params: CapacityForecastParams) -> dict[str, float | int]:
    session = await get_session()
    try:
        end = datetime.now()
        start = end - timedelta(days=30)
        sql = text(
            """
            SELECT SUM(COALESCE(eq.finish_qty, 0)) AS total_qty,
                   COUNT(DISTINCT date_trunc('day', eq.create_time)) AS active_days
            FROM n2admin.t_smt_program_consumption_record eq
            WHERE eq.device_sn IN (
                SELECT device_sn FROM n2admin.t_co_device
                WHERE cd_location = :line_id
            )
              AND eq.create_time BETWEEN :start_date AND :end_date
            """
        )
        result = await session.execute(
            sql,
            {
                "line_id": params.line_id,
                "start_date": start,
                "end_date": end,
            },
        )
        row = result.mappings().first() or {}
    finally:
        await session.close()

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
