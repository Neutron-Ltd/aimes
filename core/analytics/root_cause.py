"""Root cause analysis engine — correlates yield dips with batch/operator/device."""

from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import text

from core.db import get_session
from models.intents.production import RootCauseParams


async def analyze_root_cause(params: RootCauseParams) -> list[dict[str, Any]]:
    session = await get_session()
    try:
        sql = text(
            """
            SELECT wd.pro_lot, wd.operator, eq.device_sn,
                   date_trunc('hour', COALESCE(wd.in_time, wd.create_time)) AS bucket,
                   SUM(COALESCE(wd.pro_qty, 0) - COALESCE(wd.ng_qty, 0)
                       - COALESCE(wd.scrap_qty, 0)) AS good_qty
            FROM n2admin.t_wip_detail wd
            JOIN n2admin.t_co_area ws ON wd.work_stationsn = ws.area_sn
            JOIN n2admin.t_co_area line ON ws.parent_sn = line.area_sn
            LEFT JOIN n2admin.t_smt_program_consumption_record eq
              ON eq.device_sn IN (
                  SELECT device_sn FROM n2admin.t_co_device
                  WHERE cd_location = :line_id
              )
             AND eq.create_time BETWEEN :start_date AND :end_date
            WHERE line.area_sn = :line_id
              AND COALESCE(wd.in_time, wd.create_time) BETWEEN :start_date AND :end_date
            GROUP BY wd.pro_lot, wd.operator, eq.device_sn, bucket
            ORDER BY bucket
            """
        )
        result = await session.execute(
            sql,
            {
                "line_id": params.line_id,
                "start_date": params.start_date,
                "end_date": params.end_date,
            },
        )
        rows = [dict(r) for r in result.mappings().all()]
    finally:
        await session.close()

    if not rows:
        return [{"cause": "insufficient_data", "score": 0.0}]

    qtys = [float(r.get("good_qty") or 0) for r in rows]
    mean_qty = sum(qtys) / len(qtys) if qtys else 0
    dip_rows = [r for r in rows if float(r.get("good_qty") or 0) < mean_qty * 0.85]

    lot_counts = Counter(r.get("pro_lot") for r in dip_rows if r.get("pro_lot"))
    user_counts = Counter(r.get("operator") for r in dip_rows if r.get("operator"))
    device_counts = Counter(r.get("device_sn") for r in dip_rows if r.get("device_sn"))

    causes: list[dict[str, Any]] = []
    if lot_counts:
        lot, count = lot_counts.most_common(1)[0]
        causes.append({"cause": "batch_lot", "value": lot, "score": round(count / max(len(dip_rows), 1), 4)})
    if device_counts:
        dev, count = device_counts.most_common(1)[0]
        causes.append({"cause": "device_sn", "value": dev, "score": round(count / max(len(dip_rows), 1), 4)})
    if user_counts:
        user, count = user_counts.most_common(1)[0]
        causes.append({"cause": "operator", "value": user, "score": round(count / max(len(dip_rows), 1), 4)})

    return sorted(causes, key=lambda c: c["score"], reverse=True)
