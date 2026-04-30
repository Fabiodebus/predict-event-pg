import uuid

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.errors import ErrorResponse, register_exception_handlers
from app.middleware.correlation import CorrelationIDMiddleware


def _build_app() -> FastAPI:
    """Minimal app for testing handlers in isolation."""
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)
    register_exception_handlers(app)

    @app.get("/raise-http")
    async def raise_http():
        raise HTTPException(status_code=404, detail="not found")

    @app.get("/raise-validation")
    async def raise_validation(must_be_int: int):
        return {"value": must_be_int}

    @app.get("/raise-unhandled")
    async def raise_unhandled():
        raise RuntimeError("boom")

    @app.get("/raise-http-dict")
    async def raise_http_dict():
        raise HTTPException(status_code=400, detail={"reason": "bad", "field": "x"})

    return app


def test_error_response_schema_has_required_fields():
    payload = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="bad input",
        correlation_id=str(uuid.uuid4()),
    )
    assert payload.detail is None


def test_http_exception_returns_error_response_with_correlation_id():
    client = TestClient(_build_app())
    response = client.get("/raise-http")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "HTTP_ERROR"
    assert body["message"] == "not found"
    uuid.UUID(body["correlation_id"])
    assert body["correlation_id"] == response.headers["X-Correlation-ID"]


def test_validation_error_returns_422_error_response():
    client = TestClient(_build_app())
    response = client.get("/raise-validation?must_be_int=not-a-number")
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "detail" in body and body["detail"] is not None


def test_http_exception_with_dict_detail_uses_generic_message_and_structured_detail():
    """HTTPException(detail={...}) should not str() the dict into message —
    it should put the structured payload under detail and use a generic message."""
    client = TestClient(_build_app())
    response = client.get("/raise-http-dict")
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "HTTP_ERROR"
    assert body["message"] == "HTTP error"
    assert body["detail"] == {"detail": {"reason": "bad", "field": "x"}}


def test_unhandled_exception_returns_500_error_response():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    response = client.get("/raise-unhandled")
    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "INTERNAL_ERROR"
    assert body["message"] == "Internal server error"
    uuid.UUID(body["correlation_id"])
