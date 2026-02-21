from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """Default wall-clock implementation."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)
