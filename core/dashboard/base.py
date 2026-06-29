"""Shared helpers for assistant dashboard builders."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Optional, Protocol

from core.config import get_settings
from models.dashboard import (
    AssistantDashboardResponse,
    DashboardChartSlot,
    DashboardKpiSlot,
    DataSource,
)
from models.schemas import MCPContext
from mcp_tools.base import MCPToolResult


class DashboardBuilder(Protocol):
    async def build(
        self,
        line_id: str,
        locale: str,
        lookback_days: int,
        context: MCPContext,
    ) -> AssistantDashboardResponse:
        ...


def resolve_date_range(lookback_days: int) -> tuple[datetime, datetime]:
    """Return [start, end] datetimes for the lookback window."""
    settings = get_settings()
    ref_end = settings.dashboard_reference_date
    end_day = min(date.today(), ref_end)
    end = datetime.combine(end_day, datetime.max.time()).replace(microsecond=0)
    start = datetime.combine(
        end_day - timedelta(days=max(lookback_days - 1, 0)),
        datetime.min.time(),
    )
    return start, end


def previous_period(
    start: datetime, end: datetime
) -> tuple[datetime, datetime]:
    """Mirror window immediately before [start, end]."""
    span = end - start
    prev_end = start - timedelta(seconds=1)
    prev_start = prev_end - span
    return prev_start, prev_end


def tool_data(result: MCPToolResult) -> Optional[dict[str, Any]]:
    if not result.success or not result.data:
        return None
    return result.data


def format_percent(value: float, decimals: int = 1) -> str:
    return f"{round(value, decimals)}%"


def format_trend(growth_rate: Optional[float], suffix: str = "%") -> Optional[str]:
    if growth_rate is None:
        return None
    sign = "+" if growth_rate >= 0 else ""
    return f"{sign}{round(growth_rate, 1)}{suffix}"


def fallback_kpi(index: int, value: str = "—", trend: str = "—") -> DashboardKpiSlot:
    return DashboardKpiSlot(
        index=index, value=value, trend=trend, source=DataSource.FALLBACK
    )


def fallback_chart(
    index: int, chart_type: str = "line"
) -> DashboardChartSlot:
    return DashboardChartSlot(
        index=index,
        chart_type=chart_type,  # type: ignore[arg-type]
        source=DataSource.FALLBACK,
    )


def bucket_label(bucket: Any, locale: str) -> str:
    if bucket is None:
        return ""
    text = str(bucket)
    if "T" in text:
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if locale.startswith("zh"):
                return f"{dt.month}月{dt.day}日"
            return dt.strftime("%m/%d")
        except ValueError:
            return text[:10]
    return text[:10]
