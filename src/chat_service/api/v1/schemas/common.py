from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class CursorPaginationParams(BaseModel):
    cursor: str | None = None
    limit: int = 20


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]  # type: ignore[type-var]
    next_cursor: str | None = None
