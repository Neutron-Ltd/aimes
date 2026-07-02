"""Bailian / DashScope configuration helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import Settings

_PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "your_dashscope_api_key",
        "your_bailian_application_id",
    }
)


def _clean(value: str) -> str:
    return value.strip()


def bailian_credentials_configured(settings: Settings) -> bool:
    """Return True when non-placeholder DashScope credentials are present."""
    key = _clean(settings.dashscope_api_key)
    app_id = _clean(settings.bailian_app_id)
    return bool(
        key
        and app_id
        and key.lower() not in _PLACEHOLDER_VALUES
        and app_id.lower() not in _PLACEHOLDER_VALUES
    )


def bailian_config_status(settings: Settings) -> str:
    """Return ok | not_configured for health checks."""
    return "ok" if bailian_credentials_configured(settings) else "not_configured"
