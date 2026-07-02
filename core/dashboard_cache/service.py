"""Dashboard cache read/write with freshness checks."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from core.config import get_settings
from core.dashboard.equipment import equipment_dashboard_builder
from core.dashboard.procurement import procurement_dashboard_builder
from core.dashboard.production import production_dashboard_builder
from core.dashboard.quality import quality_dashboard_builder
from core.dashboard.warehouse import warehouse_dashboard_builder
from core.dashboard_cache import store
from core.db import get_session
from core.logging import get_logger
from models.dashboard import AssistantDashboardResponse
from models.schemas import MCPContext

logger = get_logger(__name__)

GLOBAL_SCOPE = "__all__"

BUILDERS = {
    "production": production_dashboard_builder,
    "warehouse": warehouse_dashboard_builder,
    "quality": quality_dashboard_builder,
    "equipment": equipment_dashboard_builder,
    "procurement": procurement_dashboard_builder,
}


class CacheStatus(str, Enum):
    HIT = "hit"
    STALE = "stale"
    MISS = "miss"


def build_scope_key(
    module: str,
    *,
    line_id: Optional[str] = None,
    wh_code: Optional[str] = None,
) -> str:
    if module in ("production", "quality", "equipment"):
        return (line_id or GLOBAL_SCOPE).strip()
    return (wh_code or GLOBAL_SCOPE).strip()


def _parse_generated_at(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_fresh(generated_at: str) -> bool:
    settings = get_settings()
    age = datetime.now(timezone.utc) - _parse_generated_at(generated_at)
    return age.total_seconds() <= settings.dashboard_cache_ttl_seconds


async def get_cached_dashboard(
    module: str,
    scope_key: str,
    locale: str,
    lookback_days: int,
) -> tuple[Optional[AssistantDashboardResponse], CacheStatus]:
    settings = get_settings()
    if not settings.dashboard_cache_enabled:
        return None, CacheStatus.MISS

    row = await asyncio.to_thread(
        store.get_snapshot_sync, module, scope_key, locale, lookback_days
    )
    if row is None:
        return None, CacheStatus.MISS

    try:
        response = AssistantDashboardResponse.model_validate(row["payload"])
    except Exception:
        logger.exception("Failed to parse cached dashboard for %s", module)
        return None, CacheStatus.MISS

    if is_fresh(row["generated_at"]):
        return response, CacheStatus.HIT
    if settings.dashboard_cache_stale_ok:
        return response, CacheStatus.STALE
    return None, CacheStatus.MISS


async def put_cached_dashboard(
    module: str,
    scope_key: str,
    locale: str,
    lookback_days: int,
    response: AssistantDashboardResponse,
) -> None:
    settings = get_settings()
    if not settings.dashboard_cache_enabled:
        return
    payload = response.model_dump(mode="json")
    await asyncio.to_thread(
        store.put_snapshot_sync,
        module,
        scope_key,
        locale,
        lookback_days,
        payload,
    )


async def build_dashboard_response(
    module: str,
    *,
    line_id: Optional[str],
    wh_code: Optional[str],
    locale: str,
    lookback_days: int,
    context: MCPContext,
) -> AssistantDashboardResponse:
    builder = BUILDERS[module]
    session = await get_session()
    try:
        if module == "production":
            return await builder.build(
                line_id=line_id,
                locale=locale,
                lookback_days=lookback_days,
                context=context,
                session=session,
            )
        if module in ("quality", "equipment"):
            return await builder.build(
                line_id=line_id,
                locale=locale,
                lookback_days=lookback_days,
                context=context,
                session=session,
            )
        return await builder.build(
            wh_code=wh_code,
            locale=locale,
            lookback_days=lookback_days,
            context=context,
            session=session,
        )
    finally:
        await session.close()


async def refresh_dashboard_module(
    module: str,
    *,
    line_id: Optional[str] = None,
    wh_code: Optional[str] = None,
    locale: str = "zh-CN",
    lookback_days: int = 7,
    context: Optional[MCPContext] = None,
) -> AssistantDashboardResponse:
    settings = get_settings()
    ctx = context or MCPContext(workshop_id=settings.default_workshop_id)
    scope_key = build_scope_key(module, line_id=line_id, wh_code=wh_code)

    if module == "production":
        response = await build_dashboard_response(
            module,
            line_id=line_id,
            wh_code=None,
            locale=locale,
            lookback_days=lookback_days,
            context=ctx,
        )
    elif module in ("quality", "equipment"):
        response = await build_dashboard_response(
            module,
            line_id=line_id,
            wh_code=None,
            locale=locale,
            lookback_days=lookback_days,
            context=ctx,
        )
    else:
        resolved_wh = wh_code if wh_code is not None else settings.default_wh_code
        if resolved_wh is not None:
            resolved_wh = resolved_wh.strip() or None
        response = await build_dashboard_response(
            module,
            line_id=None,
            wh_code=resolved_wh,
            locale=locale,
            lookback_days=lookback_days,
            context=ctx,
        )

    await put_cached_dashboard(module, scope_key, locale, lookback_days, response)
    logger.info("Dashboard cache refreshed: %s/%s (%s)", module, scope_key, locale)
    return response


async def refresh_all_dashboards(
    *,
    lookback_days: int = 7,
    locales: Optional[list[str]] = None,
    context: Optional[MCPContext] = None,
) -> list[str]:
    settings = get_settings()
    locale_list = locales or ["zh-CN", "en-US"]
    refreshed: list[str] = []

    line_modules = ["production", "quality", "equipment"]
    wh_modules = ["warehouse", "procurement"]

    for locale in locale_list:
        for module in line_modules:
            await refresh_dashboard_module(
                module,
                line_id=None,
                locale=locale,
                lookback_days=lookback_days,
                context=context,
            )
            refreshed.append(f"{module}:{GLOBAL_SCOPE}:{locale}")

        for module in wh_modules:
            await refresh_dashboard_module(
                module,
                wh_code=settings.default_wh_code,
                locale=locale,
                lookback_days=lookback_days,
                context=context,
            )
            scope = settings.default_wh_code or GLOBAL_SCOPE
            refreshed.append(f"{module}:{scope}:{locale}")

    return refreshed
