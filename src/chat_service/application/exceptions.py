from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    pass


class ForbiddenError(AppError):
    pass


class ConflictError(AppError):
    pass


class ValidationError(AppError):
    pass
