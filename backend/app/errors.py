import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    correlation_id: str
    detail: dict[str, Any] | None = None


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # exc.detail can be Any — only treat strings as user-facing messages,
    # otherwise stash the structured payload under detail and use a generic message.
    if isinstance(exc.detail, str):
        message = exc.detail
        detail: dict[str, Any] | None = None
    else:
        message = "HTTP error"
        detail = {"detail": exc.detail}

    body = ErrorResponse(
        error_code="HTTP_ERROR",
        message=message,
        correlation_id=_correlation_id(request),
        detail=detail,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    body = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        correlation_id=_correlation_id(request),
        detail={"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception", extra={"correlation_id": _correlation_id(request)}
    )
    body = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="Internal server error",
        correlation_id=_correlation_id(request),
    )
    return JSONResponse(status_code=500, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    """Register the three global exception handlers.

    Starlette dispatches by exact-class lookup (not MRO walk), so registration
    order doesn't affect which handler runs — but we keep specific-first for
    readability.
    """
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
