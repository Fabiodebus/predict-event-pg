import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_correlation_id_header_added_when_missing():
    client = TestClient(app)

    response = client.get("/api/v1/health")

    correlation_id = response.headers.get("X-Correlation-ID")
    assert correlation_id is not None
    assert uuid.UUID(correlation_id).version == 4


def test_correlation_id_header_is_unique_per_request():
    client = TestClient(app)

    first_response = client.get("/api/v1/health")
    second_response = client.get("/api/v1/health")

    first_correlation_id = first_response.headers.get("X-Correlation-ID")
    second_correlation_id = second_response.headers.get("X-Correlation-ID")

    assert first_correlation_id is not None
    assert second_correlation_id is not None
    assert first_correlation_id != second_correlation_id


def test_correlation_id_header_is_propagated_when_provided():
    client = TestClient(app)
    provided = str(uuid.uuid4())

    response = client.get(
        "/api/v1/health",
        headers={"X-Correlation-ID": provided},
    )

    assert response.headers.get("X-Correlation-ID") == provided


def test_correlation_id_header_present_on_cors_preflight():
    """CorrelationIDMiddleware must wrap CORS so preflight responses also
    carry the correlation ID, otherwise browsers can't correlate failed
    preflights."""
    client = TestClient(app)

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("X-Correlation-ID") is not None


def test_correlation_id_exposed_via_cors():
    """Browsers can only read response headers when listed in
    Access-Control-Expose-Headers."""
    client = TestClient(app)

    response = client.get(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5173"},
    )

    expose = response.headers.get("Access-Control-Expose-Headers", "")
    assert "X-Correlation-ID" in expose
