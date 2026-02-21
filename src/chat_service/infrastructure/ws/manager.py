"""In-process WebSocket connection manager."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from chat_service.infrastructure.ws.protocol import WsOutbound

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Tracks WebSocket connections per principal and conversation subscriptions."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._subscriptions: dict[UUID, set[str]] = {}

    async def connect(self, ws: WebSocket, principal_key: str) -> None:
        await ws.accept()
        self._connections.setdefault(principal_key, set()).add(ws)
        logger.debug("WS connected: %s (total=%d)", principal_key, len(self._connections))

    def disconnect(self, ws: WebSocket, principal_key: str) -> None:
        conns = self._connections.get(principal_key)
        if conns:
            conns.discard(ws)
            if not conns:
                del self._connections[principal_key]
        for subs in self._subscriptions.values():
            subs.discard(principal_key)
        logger.debug("WS disconnected: %s", principal_key)

    def subscribe(self, principal_key: str, conversation_id: UUID) -> None:
        self._subscriptions.setdefault(conversation_id, set()).add(principal_key)

    def unsubscribe(self, principal_key: str, conversation_id: UUID) -> None:
        subs = self._subscriptions.get(conversation_id)
        if subs:
            subs.discard(principal_key)

    async def broadcast_to_conversation(
        self,
        conversation_id: UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send a WS message to all principals subscribed to a conversation."""
        subs = self._subscriptions.get(conversation_id, set())
        payload = WsOutbound(type=event_type, data=data)
        raw = payload.model_dump_json()
        dead: list[tuple[str, WebSocket]] = []
        for pkey in subs:
            for ws in self._connections.get(pkey, set()):
                try:
                    await ws.send_text(raw)
                except Exception:
                    dead.append((pkey, ws))
        for pkey, ws in dead:
            self.disconnect(ws, pkey)

    async def send_to_principal(
        self,
        principal_key: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Send a WS message to a specific principal."""
        payload = WsOutbound(type=event_type, data=data)
        raw = payload.model_dump_json()
        dead: list[WebSocket] = []
        for ws in self._connections.get(principal_key, set()):
            try:
                await ws.send_text(raw)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, principal_key)
