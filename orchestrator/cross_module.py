"""Cross-module analysis — gather results from multiple MCP tools."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from mcp_tools.production_tools import (
    AnalysisType,
    GroupBy,
    Metric,
    YieldAnomaliesParams,
    YieldType,
    get_yield_anomalies_tool,
)
from mcp_tools.quality_tools import get_quality_defect_aggregation_tool
from mcp_tools.warehouse_tools import get_inventory_status_tool
from models.intents.quality import DefectAggregationParams
from models.intents.system import CrossModuleParams, CrossModuleResult
from models.intents.warehouse import InventoryStatusParams
from models.schemas import MCPContext
from orchestrator.param_mappers import _end_of_day, _start_of_day


async def run_cross_module_analysis(
    params: CrossModuleParams, context: MCPContext
) -> CrossModuleResult:
    today = date.today()
    start = _start_of_day(today - timedelta(days=7))
    end = _end_of_day(today)

    yield_params = YieldAnomaliesParams(
        yield_type=YieldType.EQUIPMENT,
        line_id=params.line_id,
        start_date=start,
        end_date=end,
        analysis_type=AnalysisType.BELOW_STANDARD,
        threshold_percentage=90.0,
    )
    defect_params = DefectAggregationParams(
        start_date=start,
        end_date=end,
    )
    inventory_params = InventoryStatusParams()

    results = await asyncio.gather(
        get_yield_anomalies_tool.run(yield_params, context),
        get_quality_defect_aggregation_tool.run(defect_params, context),
        get_inventory_status_tool.run(inventory_params, context),
        return_exceptions=True,
    )

    modules: dict = {}
    labels = ["production_anomalies", "quality_defects", "warehouse_inventory"]
    for label, result in zip(labels, results):
        if isinstance(result, Exception):
            modules[label] = {"success": False, "error": str(result)}
        else:
            modules[label] = {"success": result.success, "data": result.data}

    summary_parts = []
    prod = modules.get("production_anomalies", {})
    if prod.get("success"):
        flagged = prod.get("data", {}).get("result", {}).get("below_standard_count", 0)
        summary_parts.append(f"Production: {flagged} below-standard hourly buckets.")
    qual = modules.get("quality_defects", {})
    if qual.get("success"):
        rate = qual.get("data", {}).get("defect_rate", 0)
        summary_parts.append(f"Quality: {rate}% defect rate (7d).")
    wh = modules.get("warehouse_inventory", {})
    if wh.get("success"):
        low = len(wh.get("data", {}).get("low_stock", []))
        summary_parts.append(f"Warehouse: {low} low-stock items.")

    return CrossModuleResult(
        workshop_id=context.workshop_id,
        modules=modules,
        summary=" ".join(summary_parts) or "Cross-module analysis completed.",
    )
