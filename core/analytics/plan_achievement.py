"""Plan-based attainment SQL builders and row fetchers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.math_safeguard import plan_achievement_rate

DataSource = Literal["mo_base", "project_base"]
GroupBy = Literal["daily", "weekly", "monthly", "total"]

_MO_DATE_COL = (
    "COALESCE(mb.actual_start_time, mb.actual_online_time, mb.create_time)"
)
_PB_DATE_COL = "COALESCE(pb.actual_start_time, pb.plan_start_time, pb.create_time)"

_ONLINE_FILTER_MB = """
(
  EXISTS (SELECT 1 FROM n2admin.t_pm_mo_online o WHERE o.mo_number = mb.mo_number)
  OR EXISTS (
    SELECT 1 FROM n2admin.t_pm_mo_online_log ol
    WHERE ol.mo_number = mb.mo_number
      AND ol.online_time <= :end_date
      AND COALESCE(ol.offline_time, TIMESTAMP '2099-12-31') >= :start_date
  )
)
"""

_ONLINE_FILTER_PB = """
(
  EXISTS (
    SELECT 1 FROM n2admin.t_pm_mo_online o
    WHERE o.project_id = pb.id
       OR o.mo_number IN (
         SELECT mb2.mo_number FROM n2admin.t_pm_mo_base mb2
         WHERE mb2.project_no = pb.project_no
       )
  )
  OR EXISTS (
    SELECT 1 FROM n2admin.t_pm_mo_online_log ol
    WHERE ol.project_no = pb.project_no
      AND ol.online_time <= :end_date
      AND COALESCE(ol.offline_time, TIMESTAMP '2099-12-31') >= :start_date
  )
)
"""


def _is_all_lines(line_id: Optional[str]) -> bool:
    return str(line_id or "").strip().lower() == "all"


def _line_filter(alias: str) -> str:
    return f"""(
        {alias}.area_sn = :line_id
        OR {alias}.area_sn IN (
            SELECT a.area_sn FROM n2admin.t_co_area a
            WHERE a.area_sn = :line_id OR a.area_name = :line_id
        )
    )"""


def _time_bucket_expr(date_col: str, group_by: GroupBy) -> Optional[str]:
    if group_by == "total":
        return None
    trunc = {"daily": "day", "weekly": "week", "monthly": "month"}[group_by]
    return f"date_trunc('{trunc}', {date_col})"


def _build_mo_base_sql(
    *,
    group_by: GroupBy,
    line_id: Optional[str],
    all_lines_matrix: bool,
    with_product: bool,
    with_mo: bool,
) -> str:
    bucket_expr = _time_bucket_expr(_MO_DATE_COL, group_by)
    selects = [
        "SUM(COALESCE(mb.output_qty, 0)) AS actual_qty",
        "SUM(COALESCE(mb.plan_qty, 0)) AS planned_qty",
    ]
    group_parts: list[str] = []

    if bucket_expr:
        selects.append(f"{bucket_expr} AS bucket")
        group_parts.append(bucket_expr)

    if all_lines_matrix:
        selects.extend(["mb.area_sn AS area_sn", "MAX(a.area_name) AS area_name"])
        group_parts.extend(["mb.area_sn"])

    where = [
        f"{_MO_DATE_COL} BETWEEN :start_date AND :end_date",
        _ONLINE_FILTER_MB,
    ]
    if line_id and not all_lines_matrix and not _is_all_lines(line_id):
        where.append(_line_filter("mb"))
    if with_product:
        where.append("mb.model_code = :product_code")
    if with_mo:
        where.append("(mb.mo_number = :mo_number OR mb.project_no = :mo_number)")
    if all_lines_matrix:
        where.append("mb.area_sn LIKE '%-SMT-%'")

    joins = ""
    if all_lines_matrix:
        joins = " LEFT JOIN n2admin.t_co_area a ON a.area_sn = mb.area_sn"

    sql = f"""
        SELECT {", ".join(selects)}
        FROM n2admin.t_pm_mo_base mb
        {joins}
        WHERE {" AND ".join(where)}
    """
    if group_parts:
        sql += f" GROUP BY {', '.join(group_parts)}"
        if bucket_expr:
            sql += " ORDER BY bucket"
        else:
            sql += " ORDER BY area_sn"
    return sql


def _build_project_base_sql(
    *,
    group_by: GroupBy,
    line_id: Optional[str],
    with_product: bool,
) -> str:
    bucket_expr = _time_bucket_expr(_PB_DATE_COL, group_by)
    selects = [
        "SUM(COALESCE(pb.output_qty, 0)) AS actual_qty",
        "SUM(COALESCE(pb.plan_qty, 0)) AS planned_qty",
    ]
    group_parts: list[str] = []

    if bucket_expr:
        selects.append(f"{bucket_expr} AS bucket")
        group_parts.append(bucket_expr)

    where = [
        f"{_PB_DATE_COL} BETWEEN :start_date AND :end_date",
        _ONLINE_FILTER_PB,
        "(pb.project_no = :mo_number OR pb.id::text = :mo_number)",
    ]
    if with_product:
        where.append("pb.model_code = :product_code")
    if line_id:
        where.append(
            f"""(
            {_line_filter("pb")}
            OR EXISTS (
              SELECT 1 FROM n2admin.t_pm_mo_online_log ol
              WHERE ol.project_no = pb.project_no AND {_line_filter("ol")}
            )
            OR EXISTS (
              SELECT 1 FROM n2admin.t_pm_mo_base mb3
              WHERE mb3.project_no = pb.project_no AND {_line_filter("mb3")}
            )
        )"""
        )

    sql = f"""
        SELECT {", ".join(selects)}
        FROM n2admin.t_pm_project_base pb
        WHERE {" AND ".join(where)}
    """
    if group_parts:
        sql += f" GROUP BY {', '.join(group_parts)} ORDER BY bucket"
    return sql


def _row_rate(row: dict[str, Any]) -> float:
    actual = float(row.get("actual_qty") or 0)
    planned = float(row.get("planned_qty") or 0)
    return round(plan_achievement_rate(actual, planned), 4)


async def fetch_plan_achievement_rows(
    session: AsyncSession,
    *,
    mo_number: Optional[str],
    line_id: Optional[str],
    product_code: Optional[str],
    start_date: datetime,
    end_date: datetime,
    group_by: GroupBy,
) -> tuple[list[dict[str, Any]], DataSource]:
    all_lines = _is_all_lines(line_id)
    use_project = bool(mo_number and mo_number.strip())
    single_day = start_date.date() == end_date.date()
    all_lines_matrix = all_lines and not use_project and (
        group_by == "total" or single_day
    )

    if use_project:
        sql = text(
            _build_project_base_sql(
                group_by=group_by,
                line_id=None if all_lines else line_id,
                with_product=bool(product_code),
            )
        )
        data_source: DataSource = "project_base"
    else:
        sql = text(
            _build_mo_base_sql(
                group_by=group_by,
                line_id=line_id,
                all_lines_matrix=all_lines_matrix,
                with_product=bool(product_code),
                with_mo=False,
            )
        )
        data_source = "mo_base"

    bind: dict[str, Any] = {
        "start_date": start_date,
        "end_date": end_date,
    }
    if line_id and not all_lines:
        bind["line_id"] = line_id
    if product_code:
        bind["product_code"] = product_code
    if use_project:
        bind["mo_number"] = mo_number.strip()

    result = await session.execute(sql, bind)
    return [dict(row) for row in result.mappings().all()], data_source


def aggregate_plan_achievement(
    rows: list[dict[str, Any]],
    group_by: GroupBy,
) -> tuple[float, float, float, list[dict[str, Any]]]:
    """Return headline rate, actual, planned, and time breakdown."""
    breakdown: list[dict[str, Any]] = []
    if group_by != "total":
        for row in rows:
            bucket = row.get("bucket")
            breakdown.append(
                {
                    "bucket": bucket.isoformat() if bucket else None,
                    "achievement_rate": _row_rate(row),
                    "actual_qty": float(row.get("actual_qty") or 0),
                    "planned_qty": float(row.get("planned_qty") or 0),
                }
            )

    if not rows:
        return 0.0, 0.0, 0.0, breakdown

    if group_by == "total" and "area_sn" not in rows[0]:
        actual = float(rows[0].get("actual_qty") or 0)
        planned = float(rows[0].get("planned_qty") or 0)
        return round(plan_achievement_rate(actual, planned), 4), actual, planned, breakdown

    total_actual = sum(float(r.get("actual_qty") or 0) for r in rows)
    total_planned = sum(float(r.get("planned_qty") or 0) for r in rows)
    rate = round(plan_achievement_rate(total_actual, total_planned), 4)
    return rate, total_actual, total_planned, breakdown


def build_line_breakdown(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "area_sn": row.get("area_sn"),
            "area_name": row.get("area_name"),
            "achievement_rate": _row_rate(row),
            "actual_qty": float(row.get("actual_qty") or 0),
            "planned_qty": float(row.get("planned_qty") or 0),
        }
        for row in rows
    ]
