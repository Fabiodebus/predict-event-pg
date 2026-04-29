"""Correlation ID middleware: stamps every request/response with X-Correlation-ID.

Reads the incoming `X-Correlation-ID` header if present, otherwise generates a
UUIDv4. Stores the value on `request.state.correlation_id` so dependencies and
exception handlers (see app/errors.py) can include it in error responses.
"""

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        cid = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = cid

        response = await call_next(request)
        response.headers[CORRELATION_HEADER] = cid
        return response
