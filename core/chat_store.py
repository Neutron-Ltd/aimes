"""Server-side chat message persistence scoped by workshop ID."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text

from core.db import get_session
from core.logging import get_logger

logger = get_logger(__name__)

_LIST_SQL = text("""
    SELECT id, workshop_id, role, content, response_json, created_at
    FROM n2admin.chat_messages
    WHERE workshop_id = :workshop_id
    ORDER BY created_at ASC
""")

_INSERT_SQL = text("""
    INSERT INTO n2admin.chat_messages (id, workshop_id, role, content, response_json, created_at)
    VALUES (:id, :workshop_id, :role, :content, :response_json, :created_at)
    RETURNING id, workshop_id, role, content, response_json, created_at
""")

_DELETE_SQL = text("""
    DELETE FROM n2admin.chat_messages
    WHERE workshop_id = :workshop_id
""")


def _row_to_dict(row: Any) -> dict[str, Any]:
    response_json = row.get("response_json")
    if isinstance(response_json, str):
        try:
            response_json = json.loads(response_json)
        except json.JSONDecodeError:
            response_json = None
    return {
        "id": str(row["id"]),
        "workshop_id": row["workshop_id"],
        "role": row["role"],
        "content": row["content"],
        "response_json": response_json,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


async def list_messages(workshop_id: str) -> list[dict[str, Any]]:
    session = await get_session()
    try:
        result = await session.execute(_LIST_SQL, {"workshop_id": workshop_id})
        rows = result.mappings().all()
        return [_row_to_dict(dict(r)) for r in rows]
    except Exception:
        logger.exception("Failed to list chat messages for workshop=%s", workshop_id)
        raise
    finally:
        await session.close()


async def append_message(
    workshop_id: str,
    role: str,
    content: str,
    response_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    session = await get_session()
    try:
        msg_id = str(uuid.uuid4())
        now = datetime.utcnow()
        payload = json.dumps(response_json) if response_json is not None else None
        result = await session.execute(
            _INSERT_SQL,
            {
                "id": msg_id,
                "workshop_id": workshop_id,
                "role": role,
                "content": content,
                "response_json": payload,
                "created_at": now,
            },
        )
        await session.commit()
        row = result.mappings().first()
        return _row_to_dict(dict(row)) if row else {}
    except Exception:
        await session.rollback()
        logger.exception("Failed to append chat message for workshop=%s", workshop_id)
        raise
    finally:
        await session.close()


async def clear_history(workshop_id: str) -> int:
    session = await get_session()
    try:
        result = await session.execute(_DELETE_SQL, {"workshop_id": workshop_id})
        await session.commit()
        return result.rowcount or 0
    except Exception:
        await session.rollback()
        logger.exception("Failed to clear chat history for workshop=%s", workshop_id)
        raise
    finally:
        await session.close()
