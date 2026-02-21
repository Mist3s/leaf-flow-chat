from __future__ import annotations

from typing import Protocol

from chat_service.application.dto.principal import Principal


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> Principal: ...
