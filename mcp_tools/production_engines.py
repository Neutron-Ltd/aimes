"""Production analytics MCP tools — root cause, scheduling, capacity."""

from __future__ import annotations

from core.analytics.capacity import forecast_capacity
from core.analytics.root_cause import analyze_root_cause
from core.analytics.scheduling import optimize_schedule
from mcp_tools.base import BaseMCPTool
from models.intents.production import (
    CapacityForecastParams,
    CapacityForecastResult,
    RootCauseParams,
    RootCauseResult,
    SchedulingParams,
    SchedulingResult,
)
from models.schemas import MCPContext


class GetProductionRootCauseTool(BaseMCPTool[RootCauseParams, RootCauseResult]):
    name = "get_production_root_cause"
    description = "Rank probable root causes for production yield dips."

    async def execute(self, params: RootCauseParams, context: MCPContext) -> RootCauseResult:
        causes = await analyze_root_cause(params)
        return RootCauseResult(
            line_id=params.line_id,
            probable_causes=causes,
        )


class OptimizeProductionScheduleTool(BaseMCPTool[SchedulingParams, SchedulingResult]):
    name = "optimize_production_schedule"
    description = "Heuristic schedule optimization with priority scores."

    async def execute(self, params: SchedulingParams, context: MCPContext) -> SchedulingResult:
        schedule = await optimize_schedule(params)
        return SchedulingResult(
            line_id=params.line_id,
            adjusted_schedule=schedule,
        )


class ForecastCapacityHrTool(BaseMCPTool[CapacityForecastParams, CapacityForecastResult]):
    name = "forecast_capacity_hr"
    description = "Forecast capacity utilization and personnel gaps."

    async def execute(
        self, params: CapacityForecastParams, context: MCPContext
    ) -> CapacityForecastResult:
        forecast = await forecast_capacity(params)
        return CapacityForecastResult(
            line_id=params.line_id,
            capacity_utilization=float(forecast["capacity_utilization"]),
            overtime_hours_estimate=float(forecast["overtime_hours_estimate"]),
            personnel_gap=int(forecast["personnel_gap"]),
        )


get_production_root_cause_tool = GetProductionRootCauseTool()
optimize_production_schedule_tool = OptimizeProductionScheduleTool()
forecast_capacity_hr_tool = ForecastCapacityHrTool()
