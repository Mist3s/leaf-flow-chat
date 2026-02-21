from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response | None:
        cid = request.headers.get(HEADER) or uuid.uuid4().hex
        token = correlation_id_ctx.set(cid)
        try:
            response = await call_next(request)
            response.headers[HEADER] = cid
            return response
        finally:
            correlation_id_ctx.reset(token)
