"""Background periodic dashboard cache refresh."""

from __future__ import annotations

import asyncio
from typing import Optional

from core.config import get_settings
from core.dashboard_cache.service import refresh_all_dashboards
from core.logging import get_logger

logger = get_logger(__name__)

_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


async def _refresh_loop() -> None:
    settings = get_settings()
    assert _stop_event is not None
    while not _stop_event.is_set():
        try:
            await refresh_all_dashboards()
        except Exception:
            logger.exception("Scheduled dashboard cache refresh failed")
        try:
            await asyncio.wait_for(
                _stop_event.wait(),
                timeout=settings.dashboard_cache_refresh_interval_seconds,
            )
        except asyncio.TimeoutError:
            continue


def start_dashboard_cache_scheduler() -> None:
    global _task, _stop_event
    settings = get_settings()
    if not settings.dashboard_cache_enabled:
        return
    if _task is not None and not _task.done():
        return
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_refresh_loop())
    logger.info(
        "Dashboard cache scheduler started (interval=%ss)",
        settings.dashboard_cache_refresh_interval_seconds,
    )


async def stop_dashboard_cache_scheduler() -> None:
    global _task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _task is not None:
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None
    _stop_event = None
