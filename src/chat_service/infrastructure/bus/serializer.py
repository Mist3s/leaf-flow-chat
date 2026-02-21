from __future__ import annotations

import json
from typing import Any
from uuid import UUID
from datetime import datetime


class _Encoder(json.JSONEncoder):
    def default(self, o: object) -> Any:
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def serialize_event(event_type: str, payload: dict[str, Any]) -> str:
    envelope = {"event": event_type, "data": payload}
    return json.dumps(envelope, cls=_Encoder)


def deserialize_event(raw: str | bytes) -> tuple[str, dict[str, Any]]:
    data = json.loads(raw)
    return data["event"], data["data"]
