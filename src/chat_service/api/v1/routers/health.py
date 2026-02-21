from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from chat_service.infrastructure.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    errors: list[str] = []

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"postgres: {exc}")

    try:
        redis = request.app.state.redis
        await redis.ping()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"redis: {exc}")

    if errors:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "errors": errors},
        )
    return JSONResponse(content={"status": "ready"})
