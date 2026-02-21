"""FastAPI dependency injection helpers."""
from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chat_service.application.dto.principal import Principal
from chat_service.application.ports.auth import TokenVerifier
from chat_service.config import settings
from chat_service.domain.value_objects.enums import ParticipantKind
from chat_service.infrastructure.auth.hs256_verifier import HS256Verifier
from chat_service.infrastructure.auth.jwks_verifier import JWKSVerifier
from chat_service.infrastructure.db.session import AsyncSessionLocal
from chat_service.infrastructure.db.uow import SqlAlchemyUoW

_bearer_scheme = HTTPBearer()


async def get_uow() -> AsyncIterator[SqlAlchemyUoW]:
    async with AsyncSessionLocal() as session:
        uow = SqlAlchemyUoW(session)
        try:
            yield uow
        finally:
            await session.close()


UoWDep = Annotated[SqlAlchemyUoW, Depends(get_uow)]


def _get_verifier() -> TokenVerifier:
    if settings.JWT_VERIFY_MODE == "jwks":
        assert settings.JWKS_URL, "JWKS_URL must be set when JWT_VERIFY_MODE=jwks"
        return JWKSVerifier(settings.JWKS_URL)
    return HS256Verifier(settings.JWT_SECRET, settings.JWT_ALGORITHM)


_verifier: TokenVerifier | None = None


def get_verifier() -> TokenVerifier:
    global _verifier  # noqa: PLW0603
    if _verifier is None:
        _verifier = _get_verifier()
    return _verifier


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> Principal:
    verifier = get_verifier()
    try:
        return await verifier.verify(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]


async def get_current_admin(principal: CurrentPrincipal) -> Principal:
    if principal.kind != ParticipantKind.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return principal


CurrentAdmin = Annotated[Principal, Depends(get_current_admin)]
