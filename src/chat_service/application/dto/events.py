from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OutboxEventDTO:
    event_type: str
    payload: dict[str, Any]
