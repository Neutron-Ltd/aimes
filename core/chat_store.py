"""Server-side chat message persistence scoped by workshop ID and assistant module (local SQLite)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY,
    workshop_id TEXT NOT NULL,
    assistant_module TEXT NOT NULL DEFAULT 'production',
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'error')),
    content TEXT NOT NULL,
    response_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_workshop_module_created
    ON chat_messages (workshop_id, assistant_module, created_at);
"""


def _db_path() -> Path:
    settings = get_settings()
    path = Path(getattr(settings, "chat_db_path", "./data/chat_history.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _migrate_schema(conn: sqlite3.Connection) -> None:
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
    }
    if columns and "assistant_module" not in columns:
        conn.execute(
            """
            ALTER TABLE chat_messages
            ADD COLUMN assistant_module TEXT NOT NULL DEFAULT 'production'
            """
        )
        conn.commit()
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_workshop_module_created
        ON chat_messages (workshop_id, assistant_module, created_at)
        """
    )


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(_CREATE_TABLE_SQL)
    _migrate_schema(conn)
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    response_json = row["response_json"]
    parsed: Optional[dict[str, Any]] = None
    if response_json:
        try:
            parsed = json.loads(response_json)
        except json.JSONDecodeError:
            parsed = None
    return {
        "id": row["id"],
        "workshop_id": row["workshop_id"],
        "assistant_module": row["assistant_module"],
        "role": row["role"],
        "content": row["content"],
        "response_json": parsed,
        "created_at": row["created_at"],
    }


def _list_messages_sync(workshop_id: str, assistant_module: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, workshop_id, assistant_module, role, content, response_json, created_at
            FROM chat_messages
            WHERE workshop_id = ? AND assistant_module = ?
            ORDER BY created_at ASC
            """,
            (workshop_id, assistant_module),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def _append_message_sync(
    workshop_id: str,
    assistant_module: str,
    role: str,
    content: str,
    response_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    conn = _connect()
    try:
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(response_json) if response_json is not None else None
        conn.execute(
            """
            INSERT INTO chat_messages (
                id, workshop_id, assistant_module, role, content, response_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (msg_id, workshop_id, assistant_module, role, content, payload, now),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT id, workshop_id, assistant_module, role, content, response_json, created_at
            FROM chat_messages WHERE id = ?
            """,
            (msg_id,),
        ).fetchone()
        return _row_to_dict(row) if row else {}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _clear_history_sync(workshop_id: str, assistant_module: str) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            """
            DELETE FROM chat_messages
            WHERE workshop_id = ? AND assistant_module = ?
            """,
            (workshop_id, assistant_module),
        )
        conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


async def list_messages(workshop_id: str, assistant_module: str) -> list[dict[str, Any]]:
    try:
        return await asyncio.to_thread(
            _list_messages_sync, workshop_id, assistant_module
        )
    except Exception:
        logger.exception(
            "Failed to list chat messages for workshop=%s module=%s",
            workshop_id,
            assistant_module,
        )
        raise


async def append_message(
    workshop_id: str,
    assistant_module: str,
    role: str,
    content: str,
    response_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            _append_message_sync,
            workshop_id,
            assistant_module,
            role,
            content,
            response_json,
        )
    except Exception:
        logger.exception(
            "Failed to append chat message for workshop=%s module=%s",
            workshop_id,
            assistant_module,
        )
        raise


async def clear_history(workshop_id: str, assistant_module: str) -> int:
    try:
        return await asyncio.to_thread(
            _clear_history_sync, workshop_id, assistant_module
        )
    except Exception:
        logger.exception(
            "Failed to clear chat history for workshop=%s module=%s",
            workshop_id,
            assistant_module,
        )
        raise
