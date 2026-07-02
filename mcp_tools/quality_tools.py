"""Quality module MCP tools — defect analysis, root cause, prevention, effectiveness."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.math_safeguard import period_over_period_growth_rate
from mcp_tools.base import BaseMCPTool, optional_session
from models.intents.quality import (
    DefectAggregationParams,
    DefectAggregationResult,
    EffectivenessVerifyParams,
    EffectivenessVerifyResult,
    ErrorPreventionParams,
    ErrorPreventionResult,
    QualityRootCauseParams,
    QualityRootCauseResult,
)
from models.schemas import MCPContext


class GetQualityDefectAggregationTool(
    BaseMCPTool[DefectAggregationParams, DefectAggregationResult]
):
    name = "get_quality_defect_aggregation"
    description = "Defect rate aggregation from t_qm_inspect_info."

    async def execute(
        self,
        params: DefectAggregationParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> DefectAggregationResult:
        async with optional_session(session) as db:
            filters = ["qi.test_start_time BETWEEN :start_date AND :end_date"]
            bind: dict[str, Any] = {
                "start_date": params.start_date,
                "end_date": params.end_date,
            }
            if params.process_code:
                filters.append("qi.test_step = :process_code")
                bind["process_code"] = params.process_code

            sql = text(
                f"""
                SELECT qi.test_step AS process_code,
                       SUM(COALESCE(qi.real_qty, 0)) AS inspected,
                       SUM(COALESCE(qi.error_qty, 0)) AS defects
                FROM n2admin.t_qm_inspect_info qi
                WHERE {" AND ".join(filters)}
                GROUP BY qi.test_step
                """
            )
            result = await db.execute(sql, bind)
            rows = [dict(r) for r in result.mappings().all()]

        total_inspected = sum(int(r.get("inspected") or 0) for r in rows)
        total_defects = sum(int(r.get("defects") or 0) for r in rows)
        rate = (total_defects / total_inspected * 100.0) if total_inspected else 0.0
        breakdown = [
            {
                "process_code": r.get("process_code"),
                "inspected": int(r.get("inspected") or 0),
                "defects": int(r.get("defects") or 0),
                "defect_rate": round(
                    (int(r.get("defects") or 0) / int(r.get("inspected") or 1)) * 100.0, 4
                ),
            }
            for r in rows
        ]
        return DefectAggregationResult(
            defect_rate=round(rate, 4),
            total_inspected=total_inspected,
            total_defects=total_defects,
            breakdown=breakdown,
        )


class AnalyzeDefectRootCauseTool(
    BaseMCPTool[QualityRootCauseParams, QualityRootCauseResult]
):
    name = "analyze_defect_root_cause"
    description = "Ranked root cause hypotheses from QM problem tables."

    async def execute(
        self,
        params: QualityRootCauseParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> QualityRootCauseResult:
        async with optional_session(session) as db:
            sql = text(
                """
                SELECT pr.problem_desc, prr.cause_desc, COUNT(*) AS cnt
                FROM n2admin.t_qm_problem_report pr
                LEFT JOIN n2admin.t_qm_problem_reason prr ON pr.id = prr.doc_id
                WHERE pr.create_time BETWEEN :start_date AND :end_date
                GROUP BY pr.problem_desc, prr.cause_desc
                ORDER BY cnt DESC
                LIMIT 10
                """
            )
            result = await db.execute(
                sql,
                {
                    "start_date": params.start_date,
                    "end_date": params.end_date,
                },
            )
            rows = result.mappings().all()

        hypotheses = [
            {
                "problem": r.get("problem_desc"),
                "reason": r.get("cause_desc"),
                "score": round(float(r.get("cnt") or 0) / 10.0, 4),
            }
            for r in rows
        ]
        return QualityRootCauseResult(hypotheses=hypotheses)


class CheckErrorPreventionTool(BaseMCPTool[ErrorPreventionParams, ErrorPreventionResult]):
    name = "check_error_prevention"
    description = "Validate IPQC checklist vs inspection scheme."

    async def execute(
        self,
        params: ErrorPreventionParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> ErrorPreventionResult:
        async with optional_session(session) as db:
            scheme_sql = text(
                """
                SELECT scheme_name, inspect_item
                FROM n2admin.t_qm_inspect_scheme_info
                WHERE test_step = :process_code
                LIMIT 20
                """
            )
            doc_sql = text(
                """
                SELECT doc_no, inspect_item
                FROM n2admin.t_qm_ipqc_doc
                WHERE test_step = :process_code
                LIMIT 20
                """
            )
            bind = {"process_code": params.process_code}
            scheme_rows = (await db.execute(scheme_sql, bind)).mappings().all()
            doc_rows = (await db.execute(doc_sql, bind)).mappings().all()

        scheme_items = {r.get("inspect_item") for r in scheme_rows if r.get("inspect_item")}
        doc_items = {r.get("inspect_item") for r in doc_rows if r.get("inspect_item")}
        omissions = sorted(scheme_items - doc_items)
        checklist = [{"item": item, "in_scheme": True, "in_ipqc": item in doc_items} for item in scheme_items]

        return ErrorPreventionResult(
            process_code=params.process_code,
            omissions=omissions,
            checklist_items=checklist,
        )


class VerifyQualityEffectivenessTool(
    BaseMCPTool[EffectivenessVerifyParams, EffectivenessVerifyResult]
):
    name = "verify_quality_effectiveness"
    description = "Before/after defect rate comparison around a milestone."

    async def execute(
        self,
        params: EffectivenessVerifyParams,
        context: MCPContext,
        *,
        session: AsyncSession | None = None,
    ) -> EffectivenessVerifyResult:
        milestone = params.milestone_date
        before_start = milestone - timedelta(days=params.comparison_days)
        after_end = milestone + timedelta(days=params.comparison_days)

        async with optional_session(session) as db:
            async def _rate(start: datetime, end: datetime) -> float:
                sql = text(
                    """
                    SELECT SUM(COALESCE(real_qty, 0)) AS inspected,
                           SUM(COALESCE(error_qty, 0)) AS defects
                    FROM n2admin.t_qm_inspect_info
                    WHERE test_start_time BETWEEN :start_date AND :end_date
                    """
                )
                result = await db.execute(
                    sql,
                    {"start_date": start, "end_date": end},
                )
                row = result.mappings().first() or {}
                inspected = float(row.get("inspected") or 0)
                defects = float(row.get("defects") or 0)
                return (defects / inspected * 100.0) if inspected else 0.0

            before_rate = await _rate(before_start, milestone)
            after_rate = await _rate(milestone, after_end)

        growth = period_over_period_growth_rate(after_rate, before_rate)
        return EffectivenessVerifyResult(
            before_defect_rate=round(before_rate, 4),
            after_defect_rate=round(after_rate, 4),
            growth_rate=round(growth, 4) if growth is not None else None,
        )


get_quality_defect_aggregation_tool = GetQualityDefectAggregationTool()
analyze_defect_root_cause_tool = AnalyzeDefectRootCauseTool()
check_error_prevention_tool = CheckErrorPreventionTool()
verify_quality_effectiveness_tool = VerifyQualityEffectivenessTool()
