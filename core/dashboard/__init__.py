"""Assistant dashboard snapshot builders."""

from core.dashboard.production import ProductionDashboardBuilder, production_dashboard_builder
from core.dashboard.equipment import EquipmentDashboardBuilder, equipment_dashboard_builder
from core.dashboard.quality import QualityDashboardBuilder, quality_dashboard_builder
from core.dashboard.warehouse import WarehouseDashboardBuilder, warehouse_dashboard_builder

__all__ = [
    "ProductionDashboardBuilder",
    "production_dashboard_builder",
    "EquipmentDashboardBuilder",
    "equipment_dashboard_builder",
    "WarehouseDashboardBuilder",
    "warehouse_dashboard_builder",
    "QualityDashboardBuilder",
    "quality_dashboard_builder",
]
