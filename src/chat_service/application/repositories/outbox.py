from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol


class OutboxWriter(Protocol):
    async def add(self, event_type: str, payload: dict[str, Any]) -> None: ...

    async def fetch_pending(self, batch_size: int) -> list[OutboxRecord]: ...

    async def mark_sent(self, ids: list[int]) -> None: ...

    async def mark_failed(self, record_id: int, next_retry_at: datetime) -> None: ...


class OutboxRecord:
    """Lightweight read-model for the outbox worker."""

    __slots__ = ("id", "event_type", "payload", "attempts")

    def __init__(
        self,
        id: int,
        event_type: str,
        payload: dict[str, Any],
        attempts: int,
    ) -> None:
        self.id = id
        self.event_type = event_type
        self.payload = payload
        self.attempts = attempts
