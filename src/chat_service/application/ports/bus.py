from __future__ import annotations

from typing import Any, Protocol


class EventPublisher(Protocol):
    async def publish(self, channel: str, payload: dict[str, Any]) -> None: ...
