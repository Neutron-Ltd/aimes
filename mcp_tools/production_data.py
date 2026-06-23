"""
Production Data MCP Tool — aggregated yield and throughput metrics.

Accepts structured date/line/model filters plus RBAC workshop_id.
Returns mock aggregated JSON; production version will call db_manager
with pre-approved named queries (no LLM-generated SQL).
"""

from __future__ import annotations

from datetime import date, timedelta

from core.logging import get_logger
from mcp_tools.base import BaseMCPTool
from models.schemas import MCPContext, ProductionDataParams, ProductionDataResult, TimeFrame

logger = get_logger(__name__)

# Deterministic mock seed offsets per line for repeatable Swagger tests
_LINE_SEEDS: dict[str, int] = {
    "L-01": 1200,
    "L-02": 980,
    "L-03": 1450,
    "L-04": 870,
}


class ProductionDataTool(BaseMCPTool[ProductionDataParams, ProductionDataResult]):
    name = "production_data"
    description = (
        "Retrieve aggregated production yield, reported count, and equipment "
        "metrics for a given line, model, and date range within a workshop."
    )

    async def execute(
        self, params: ProductionDataParams, context: MCPContext
    ) -> ProductionDataResult:
        # RBAC: workshop_id from middleware scopes all data access
        workshop_id = params.workshop_id or context.workshop_id

        period_start = params.start_date or date.today()
        period_end = params.end_date or period_start
        time_frame = (params.time_frame or TimeFrame.DAY).value
        line_id = params.line_id or "L-01"
        model_code = params.model_code or "MDL-UNKNOWN"

        return self._build_mock_aggregate(
            workshop_id=workshop_id,
            line_id=line_id,
            model_code=model_code,
            period_start=period_start,
            period_end=period_end,
            time_frame=time_frame,
        )

    def _build_mock_aggregate(
        self,
        *,
        workshop_id: str,
        line_id: str,
        model_code: str,
        period_start: date,
        period_end: date,
        time_frame: str,
    ) -> ProductionDataResult:
        """Generate realistic mock aggregates for API/Swagger testing."""
        base = _LINE_SEEDS.get(line_id, 1000)
        day_span = max((period_end - period_start).days + 1, 1)
        multiplier = day_span if time_frame == TimeFrame.DAY.value else day_span * 3

        total_reported = base * multiplier
        yield_pct = 92.5 + (hash(line_id) % 50) / 10.0  # 92.5 – 97.4
        total_equipment = int(total_reported * yield_pct / 100)
        defect_count = total_reported - total_equipment

        return ProductionDataResult(
            workshop_id=workshop_id,
            line_id=line_id,
            model_code=model_code,
            period_start=period_start,
            period_end=period_end,
            time_frame=time_frame,
            total_reported=total_reported,
            total_equipment=total_equipment,
            yield_rate=round(yield_pct, 2),
            defect_count=defect_count,
            metadata={
                "source": "mock",
                "query": "agg_production_yield",
                "note": "Replace with real aggregation once DB bridge is live",
            },
        )


# Singleton instance registered by the orchestrator
production_data_tool = ProductionDataTool()
