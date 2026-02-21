"""WebSocket message envelope models."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WsInbound(BaseModel):
    """Client → Server."""

    type: str  # message.send | mark_read | ping
    data: dict[str, Any] = {}


class WsOutbound(BaseModel):
    """Server → Client."""

    type: str  # message.created | conversation.updated | error | pong
    data: dict[str, Any] = {}
