"""Cursor-based pagination helpers.

Cursor format: base64("<iso-timestamp>|<uuid>")
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from uuid import UUID


def encode_cursor(ts: datetime | None, uid: UUID) -> str:
    ts_str = (ts or datetime.min.replace(tzinfo=timezone.utc)).isoformat()
    raw = f"{ts_str}|{uid}"
    cursor = base64.urlsafe_b64encode(raw.encode()).decode()
    return cursor.rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    # Restore base64 padding if it was stripped
    cursor += "=" * ((4 - len(cursor) % 4) % 4)
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, uid_str = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), UUID(uid_str)
