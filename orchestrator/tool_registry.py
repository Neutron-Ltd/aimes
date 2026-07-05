"""Intent → MCP tool registry (v0.3)."""

from __future__ import annotations

from typing import Any, Callable, Optional

from mcp_tools.base import BaseMCPTool
from mcp_tools.production_engines import (
    forecast_capacity_hr_tool,
    get_production_root_cause_tool,
    optimize_production_schedule_tool,
)
from mcp_tools.production_tools import (
    compare_yield_periods_tool,
    FactoryMetadataParams,
    get_device_production_rate_tool,
    get_factory_structure_metadata_tool,
    get_product_yield_tool,
    get_standard_time_achievement_tool,
    get_yield_aggregation_tool,
    get_yield_anomalies_tool,
)
from mcp_tools.quality_tools import (
    analyze_defect_root_cause_tool,
    check_error_prevention_tool,
    get_quality_defect_aggregation_tool,
    verify_quality_effectiveness_tool,
)
from mcp_tools.warehouse_tools import (
    get_inventory_status_tool,
    guide_inbound_outbound_tool,
    profile_obsolete_inventory_tool,
    trace_material_forward_tool,
    trace_product_reverse_tool,
)
from models.schemas import IntentType

ParamMapper = Callable[[Any], Any]

INTENT_TOOL_MAP: dict[IntentType, tuple[BaseMCPTool, ParamMapper, str]] = {}


def _register(
    intent: IntentType,
    tool: BaseMCPTool,
    mapper: ParamMapper,
    success_message: str,
) -> None:
    INTENT_TOOL_MAP[intent] = (tool, mapper, success_message)


def get_tool_for_intent(intent: IntentType) -> Optional[tuple[BaseMCPTool, ParamMapper, str]]:
    return INTENT_TOOL_MAP.get(intent)


def register_all_tools(mappers: dict[IntentType, ParamMapper]) -> None:
    """Bind param mappers to tools — called at module load."""
    _register(
        IntentType.YIELD_AGGREGATION,
        get_yield_aggregation_tool,
        mappers[IntentType.YIELD_AGGREGATION],
        "Yield aggregation retrieved successfully",
    )
    _register(
        IntentType.YIELD_ANOMALIES,
        get_yield_anomalies_tool,
        mappers[IntentType.YIELD_ANOMALIES],
        "Yield anomaly analysis completed successfully",
    )
    _register(
        IntentType.YIELD_COMPARISON,
        compare_yield_periods_tool,
        mappers[IntentType.YIELD_COMPARISON],
        "Yield period comparison completed successfully",
    )
    _register(
        IntentType.PRODUCTION_PRODUCT_YIELD,
        get_product_yield_tool,
        mappers[IntentType.PRODUCTION_PRODUCT_YIELD],
        "Product yield retrieved successfully",
    )
    _register(
        IntentType.PRODUCTION_DEVICE_RATE,
        get_device_production_rate_tool,
        mappers[IntentType.PRODUCTION_DEVICE_RATE],
        "Device production rate retrieved successfully",
    )
    _register(
        IntentType.PRODUCTION_STANDARD_TIME,
        get_standard_time_achievement_tool,
        mappers[IntentType.PRODUCTION_STANDARD_TIME],
        "Standard time achievement retrieved successfully",
    )
    _register(
        IntentType.PRODUCTION_ROOT_CAUSE,
        get_production_root_cause_tool,
        mappers[IntentType.PRODUCTION_ROOT_CAUSE],
        "Production root cause analysis completed",
    )
    _register(
        IntentType.PRODUCTION_SCHEDULING_OPT,
        optimize_production_schedule_tool,
        mappers[IntentType.PRODUCTION_SCHEDULING_OPT],
        "Production schedule optimized",
    )
    _register(
        IntentType.PRODUCTION_CAPACITY_FORECAST,
        forecast_capacity_hr_tool,
        mappers[IntentType.PRODUCTION_CAPACITY_FORECAST],
        "Capacity forecast generated",
    )
    _register(
        IntentType.FACTORY_METADATA_LOOKUP,
        get_factory_structure_metadata_tool,
        mappers[IntentType.FACTORY_METADATA_LOOKUP],
        "Factory structure metadata retrieved",
    )
    _register(
        IntentType.QUALITY_DEFECT_ANALYSIS,
        get_quality_defect_aggregation_tool,
        mappers[IntentType.QUALITY_DEFECT_ANALYSIS],
        "Quality defect aggregation completed",
    )
    _register(
        IntentType.QUALITY_ROOT_CAUSE,
        analyze_defect_root_cause_tool,
        mappers[IntentType.QUALITY_ROOT_CAUSE],
        "Quality root cause analysis completed",
    )
    _register(
        IntentType.QUALITY_ERROR_PREVENTION,
        check_error_prevention_tool,
        mappers[IntentType.QUALITY_ERROR_PREVENTION],
        "Error prevention check completed",
    )
    _register(
        IntentType.QUALITY_EFFECTIVENESS_VERIFY,
        verify_quality_effectiveness_tool,
        mappers[IntentType.QUALITY_EFFECTIVENESS_VERIFY],
        "Quality effectiveness verification completed",
    )
    _register(
        IntentType.WAREHOUSE_INVENTORY_MONITOR,
        get_inventory_status_tool,
        mappers[IntentType.WAREHOUSE_INVENTORY_MONITOR],
        "Inventory status retrieved",
    )
    _register(
        IntentType.WAREHOUSE_INBOUND_OUTBOUND,
        guide_inbound_outbound_tool,
        mappers[IntentType.WAREHOUSE_INBOUND_OUTBOUND],
        "Inbound/outbound guidance generated",
    )
    _register(
        IntentType.WAREHOUSE_OBSOLETE_PROFILE,
        profile_obsolete_inventory_tool,
        mappers[IntentType.WAREHOUSE_OBSOLETE_PROFILE],
        "Obsolete inventory profile generated",
    )
    _register(
        IntentType.WAREHOUSE_TRACE_FORWARD,
        trace_material_forward_tool,
        mappers[IntentType.WAREHOUSE_TRACE_FORWARD],
        "Forward material trace completed",
    )
    _register(
        IntentType.WAREHOUSE_TRACE_REVERSE,
        trace_product_reverse_tool,
        mappers[IntentType.WAREHOUSE_TRACE_REVERSE],
        "Reverse product trace completed",
    )
