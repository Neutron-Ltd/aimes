"""SQLite persistence for dashboard snapshot responses."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS dashboard_snapshots (
    module TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    locale TEXT NOT NULL,
    lookback_days INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    PRIMARY KEY (module, scope_key, locale, lookback_days)
);
"""


def _db_path() -> Path:
    settings = get_settings()
    path = Path(settings.dashboard_cache_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_CREATE_TABLE_SQL)
    return conn


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_snapshot_sync(
    module: str,
    scope_key: str,
    locale: str,
    lookback_days: int,
) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT module, scope_key, locale, lookback_days, payload_json, generated_at
            FROM dashboard_snapshots
            WHERE module = ? AND scope_key = ? AND locale = ? AND lookback_days = ?
            """,
            (module, scope_key, locale, lookback_days),
        ).fetchone()
        if row is None:
            return None
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError:
            logger.warning(
                "Invalid dashboard cache JSON for %s/%s", module, scope_key
            )
            return None
        return {
            "module": row["module"],
            "scope_key": row["scope_key"],
            "locale": row["locale"],
            "lookback_days": row["lookback_days"],
            "payload": payload,
            "generated_at": row["generated_at"],
        }
    finally:
        conn.close()


def put_snapshot_sync(
    module: str,
    scope_key: str,
    locale: str,
    lookback_days: int,
    payload: dict[str, Any],
) -> str:
    generated_at = _utc_now_iso()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO dashboard_snapshots
                (module, scope_key, locale, lookback_days, payload_json, generated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(module, scope_key, locale, lookback_days) DO UPDATE SET
                payload_json = excluded.payload_json,
                generated_at = excluded.generated_at
            """,
            (
                module,
                scope_key,
                locale,
                lookback_days,
                json.dumps(payload, default=str),
                generated_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return generated_at


def list_snapshots_sync() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT module, scope_key, locale, lookback_days, generated_at
            FROM dashboard_snapshots
            ORDER BY module, scope_key, locale
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
