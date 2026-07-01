#!/usr/bin/env python3
"""Prewarm dashboard snapshots in local SQLite cache."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_settings
from core.dashboard_cache import store
from core.dashboard_cache.service import refresh_all_dashboards, refresh_dashboard_module
from core.db import close_db, init_db
from models.schemas import MCPContext


async def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh assistant dashboard cache")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="Lookback window passed to dashboard builders (default: 7)",
    )
    parser.add_argument(
        "--locale",
        action="append",
        dest="locales",
        help="Locale to refresh (repeatable). Default: zh-CN and en-US",
    )
    parser.add_argument(
        "--module",
        choices=[
            "production",
            "warehouse",
            "quality",
            "equipment",
            "procurement",
        ],
        help="Refresh a single module only",
    )
    args = parser.parse_args()

    settings = get_settings()
    locales = args.locales or ["zh-CN", "en-US"]
    context = MCPContext(workshop_id=settings.default_workshop_id)

    await init_db()
    try:
        if args.module:
            for locale in locales:
                if args.module in ("production", "quality", "equipment"):
                    await refresh_dashboard_module(
                        args.module,
                        line_id=settings.default_line_id,
                        locale=locale,
                        lookback_days=args.lookback_days,
                        context=context,
                    )
                else:
                    await refresh_dashboard_module(
                        args.module,
                        wh_code=settings.default_wh_code,
                        locale=locale,
                        lookback_days=args.lookback_days,
                        context=context,
                    )
            refreshed = [args.module]
        else:
            refreshed = await refresh_all_dashboards(
                lookback_days=args.lookback_days,
                locales=locales,
                context=context,
            )

        rows = await asyncio.to_thread(store.list_snapshots_sync)
        print(f"Refreshed {len(refreshed)} dashboard snapshot(s).")
        print(f"Cache DB: {settings.dashboard_cache_db_path} ({len(rows)} row(s))")
        for row in rows:
            print(
                f"  - {row['module']} | {row['scope_key']} | {row['locale']} | "
                f"lookback={row['lookback_days']} | {row['generated_at']}"
            )
    finally:
        await close_db()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
