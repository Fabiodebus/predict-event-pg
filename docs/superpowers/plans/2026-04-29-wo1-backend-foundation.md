# WO-1: Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI application surface — health, correlation IDs, error handling, Cognito auth, the job-status endpoint, audit log, and HTTP integration clients — on top of the WO-3 data layer.

**Architecture:** A single FastAPI app composed via an app factory in `app/main.py` mounting an `/api/v1` router tree. Cross-cutting concerns (CORS, correlation ID middleware, exception handlers) live alongside the factory. Auth is a dependency-injected `get_current_user` that validates JWTs against Cognito's JWKS. External APIs go through a shared `BaseIntegrationClient` with tenacity retries.

**Tech Stack:** FastAPI 0.115, SQLModel + SQLAlchemy 2.x async, Pydantic v2, pydantic-settings, python-jose (JWT verification), httpx, tenacity, respx (test mocks), pytest-asyncio (session-scoped loop, savepoint rollback).

---

## File Structure

```
backend/
  app/
    main.py                     # FastAPI app factory, CORS, middleware, exception handlers, router include
    dependencies.py             # UserContext model + get_current_user
    errors.py                   # ErrorResponse + register_exception_handlers
    audit.py                    # write_audit_log()
    middleware/
      __init__.py
      correlation.py            # CorrelationIDMiddleware (assigns X-Correlation-ID)
      cognito.py                # JWKS fetcher + JWT validator
    api/
      __init__.py
      v1/
        __init__.py
        router.py               # Mounts domain routers under /api/v1
        common/
          __init__.py
          router.py             # GET /health
        agents/
          __init__.py
          router.py             # GET /agents/jobs/{job_id}
    models/
      audit.py                  # AuditLog SQLModel
    integrations/
      __init__.py
      base.py                   # BaseIntegrationClient (httpx + tenacity)
      crustdata.py
      browser_use.py
      unipile.py
  tests/
    test_main.py                # CORS + correlation ID end-to-end
    test_health.py
    test_errors.py
    test_dependencies.py        # UserContext + get_current_user
    middleware/
      __init__.py
      test_correlation.py
      test_cognito.py
    api/
      __init__.py
      v1/
        __init__.py
        agents/
          __init__.py
          test_router.py        # job status endpoint
    test_audit.py
    integrations/
      __init__.py
      test_base.py
      test_crustdata.py
      test_browser_use.py
      test_unipile.py
  alembic/versions/
    <new>_add_audit_log_table.py
```

**Already in place from WO-3** (do not modify):
- `app/config.py` — `allowed_origins: list[str]`, all Cognito/integration secrets exposed
- `app/db/base.py`, `app/db/session.py` — async engine + `get_db`
- `app/models/job.py`, `app/models/__init__.py`
- `app/repositories/base.py`, `app/repositories/job.py`
- `tests/conftest.py` — `engine` (session) and `db` (per-test savepoint) fixtures

---

## Test Conventions

All HTTP tests use FastAPI's `TestClient` via the synchronous `httpx.Client`. For tests that hit the database, use the existing `db` fixture and override `get_db` like this (defined once in `tests/conftest.py` or the per-module conftest as needed — the fixture pattern is repeated in plan tasks where it's first introduced):

```python
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db

async def _override_get_db(db):
    async def _gen():
        yield db
    return _gen

# In each test that needs DB:
app.dependency_overrides[get_db] = _override_get_db_factory(db_fixture)
client = TestClient(app)
# ... assert ...
app.dependency_overrides.clear()
```

For tests that mock outbound HTTP, use `respx`:

```python
import respx, httpx
@respx.mock
async def test_something():
    respx.get("https://api.example.com/x").mock(return_value=httpx.Response(200, json={"ok": True}))
    ...
```

---

### Task 1: FastAPI App Factory + Health Endpoint

**Files:**
- Create: `backend/app/api/__init__.py` (empty)
- Create: `backend/app/api/v1/__init__.py` (empty)
- Create: `backend/app/api/v1/common/__init__.py` (empty)
- Create: `backend/app/api/v1/common/router.py`
- Create: `backend/app/api/v1/router.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && poetry run pytest tests/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Create the common router**

Create `backend/app/api/v1/common/router.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 4: Create the v1 aggregate router**

Create `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1.common.router import router as common_router

router = APIRouter(prefix="/api/v1")
router.include_router(common_router, tags=["common"])
```

- [ ] **Step 5: Create the FastAPI app factory**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="PREDICT Event API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)
    return app


app = create_app()
```

- [ ] **Step 6: Create empty `__init__.py` files for the new packages**

```bash
touch backend/app/api/__init__.py backend/app/api/v1/__init__.py backend/app/api/v1/common/__init__.py
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd backend && poetry run pytest tests/test_health.py -v
```

Expected: `1 passed`

- [ ] **Step 8: Commit**

```bash
git add backend/app/main.py backend/app/api backend/tests/test_health.py
git commit -m "feat(wo-1): FastAPI app factory with health endpoint and CORS"
```

---

### Task 2: Correlation ID Middleware

**Files:**
- Create: `backend/app/middleware/__init__.py` (empty)
- Create: `backend/app/middleware/correlation.py`
- Modify: `backend/app/main.py` (register middleware)
- Test: `backend/tests/middleware/__init__.py` (empty)
- Test: `backend/tests/middleware/test_correlation.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/middleware/__init__.py` (empty) and `backend/tests/middleware/test_correlation.py`:

```python
import uuid
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_correlation_id_header_added_when_missing():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    cid = response.headers.get("X-Correlation-ID")
    assert cid is not None
    # Must be a valid UUID
    uuid.UUID(cid)


def test_correlation_id_header_is_unique_per_request():
    r1 = client.get("/api/v1/health")
    r2 = client.get("/api/v1/health")
    assert r1.headers["X-Correlation-ID"] != r2.headers["X-Correlation-ID"]


def test_correlation_id_header_is_propagated_when_provided():
    cid = str(uuid.uuid4())
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": cid})
    assert response.headers["X-Correlation-ID"] == cid
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/middleware/test_correlation.py -v
```

Expected: FAIL — `X-Correlation-ID` is not in response headers.

- [ ] **Step 3: Implement the middleware**

Create `backend/app/middleware/correlation.py`:

```python
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
```

- [ ] **Step 4: Register the middleware in `main.py`**

Edit `backend/app/main.py` — add the import and middleware registration *before* `include_router`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.middleware.correlation import CorrelationIDMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="PREDICT Event API", version="0.1.0")

    app.add_middleware(CorrelationIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router)
    return app


app = create_app()
```

- [ ] **Step 5: Create empty `app/middleware/__init__.py`**

```bash
touch backend/app/middleware/__init__.py
```

- [ ] **Step 6: Run tests**

```bash
cd backend && poetry run pytest tests/middleware/test_correlation.py -v
```

Expected: `3 passed`

- [ ] **Step 7: Re-run health test to make sure CORS/middleware order didn't break it**

```bash
cd backend && poetry run pytest tests/test_health.py -v
```

Expected: `1 passed`

- [ ] **Step 8: Commit**

```bash
git add backend/app/middleware backend/tests/middleware backend/app/main.py
git commit -m "feat(wo-1): correlation ID middleware (X-Correlation-ID header)"
```

---

### Task 3: ErrorResponse + Global Exception Handlers

**Files:**
- Create: `backend/app/errors.py`
- Modify: `backend/app/main.py` (register handlers)
- Test: `backend/tests/test_errors.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_errors.py`:

```python
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


def test_unhandled_exception_returns_500_error_response():
    client = TestClient(_build_app(), raise_server_exceptions=False)
    response = client.get("/raise-unhandled")
    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "INTERNAL_ERROR"
    assert body["message"] == "Internal server error"
    uuid.UUID(body["correlation_id"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/test_errors.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.errors'`

- [ ] **Step 3: Implement errors module**

Create `backend/app/errors.py`:

```python
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    correlation_id: str
    detail: dict[str, Any] | None = None


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "")


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    body = ErrorResponse(
        error_code="HTTP_ERROR",
        message=str(exc.detail),
        correlation_id=_correlation_id(request),
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


async def _validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    body = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        correlation_id=_correlation_id(request),
        detail={"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content=body.model_dump())


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    body = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="Internal server error",
        correlation_id=_correlation_id(request),
    )
    return JSONResponse(status_code=500, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
```

- [ ] **Step 4: Wire handlers into main.py**

Edit `backend/app/main.py` — add the import and call `register_exception_handlers(app)` after middleware registration:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.errors import register_exception_handlers
from app.middleware.correlation import CorrelationIDMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="PREDICT Event API", version="0.1.0")

    app.add_middleware(CorrelationIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run tests**

```bash
cd backend && poetry run pytest tests/test_errors.py tests/test_health.py tests/middleware -v
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/app/errors.py backend/app/main.py backend/tests/test_errors.py
git commit -m "feat(wo-1): ErrorResponse schema and global exception handlers"
```

---

### Task 4: Cognito JWKS Fetcher + JWT Validator

**Files:**
- Create: `backend/app/middleware/cognito.py`
- Test: `backend/tests/middleware/test_cognito.py`

This task delivers a *pure* JWT validator. Wiring it into a FastAPI dependency happens in Task 5.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/middleware/test_cognito.py`:

```python
import time
from unittest.mock import patch

import pytest
from jose import jwt
from jose.utils import long_to_base64

from app.middleware.cognito import CognitoTokenValidator, InvalidTokenError


@pytest.fixture
def rsa_keypair():
    """Generate a fresh RSA keypair and matching JWKS entry for each test."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_numbers = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-kid",
        "use": "sig",
        "alg": "RS256",
        "n": long_to_base64(public_numbers.n).decode(),
        "e": long_to_base64(public_numbers.e).decode(),
    }
    return private_pem, jwk


def _make_token(private_pem: str, claims: dict, kid: str = "test-kid") -> str:
    return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": kid})


def _validator(jwks: dict) -> CognitoTokenValidator:
    """Construct validator with JWKS pre-cached so no network call happens."""
    v = CognitoTokenValidator(
        user_pool_id="us-east-1_TESTPOOL",
        client_id="test-client-id",
        region="us-east-1",
    )
    v._jwks_cache = jwks  # bypass network fetch in tests
    return v


def test_valid_token_returns_claims(rsa_keypair):
    private_pem, jwk = rsa_keypair
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "aud": "test-client-id",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "iat": now,
        "exp": now + 3600,
        "token_use": "id",
        "email": "user@example.com",
    }
    token = _make_token(private_pem, claims)
    validator = _validator({"keys": [jwk]})
    decoded = validator.validate(token)
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "user@example.com"


def test_expired_token_raises(rsa_keypair):
    private_pem, jwk = rsa_keypair
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "aud": "test-client-id",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "iat": now - 7200,
        "exp": now - 3600,
        "token_use": "id",
    }
    token = _make_token(private_pem, claims)
    validator = _validator({"keys": [jwk]})
    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_wrong_audience_raises(rsa_keypair):
    private_pem, jwk = rsa_keypair
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "aud": "wrong-audience",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "iat": now,
        "exp": now + 3600,
        "token_use": "id",
    }
    token = _make_token(private_pem, claims)
    validator = _validator({"keys": [jwk]})
    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_unknown_kid_raises(rsa_keypair):
    private_pem, jwk = rsa_keypair
    now = int(time.time())
    claims = {
        "sub": "user-123",
        "aud": "test-client-id",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "iat": now,
        "exp": now + 3600,
        "token_use": "id",
    }
    token = _make_token(private_pem, claims, kid="nonexistent-kid")
    validator = _validator({"keys": [jwk]})
    with pytest.raises(InvalidTokenError):
        validator.validate(token)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/middleware/test_cognito.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.middleware.cognito'`

- [ ] **Step 3: Add the `cryptography` test dependency**

```bash
cd backend && poetry add --group dev cryptography
```

(`python-jose[cryptography]` is already a runtime dep, but we need the `cryptography` lib directly to generate test keys.)

- [ ] **Step 4: Implement the validator**

Create `backend/app/middleware/cognito.py`:

```python
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError


class InvalidTokenError(Exception):
    """Raised when a JWT fails Cognito validation."""


class CognitoTokenValidator:
    def __init__(self, user_pool_id: str, client_id: str, region: str) -> None:
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self._jwks_cache: dict[str, Any] | None = None

    @property
    def issuer(self) -> str:
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    async def _fetch_jwks(self) -> dict[str, Any]:
        if self._jwks_cache is not None:
            return self._jwks_cache
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            self._jwks_cache = response.json()
        return self._jwks_cache

    def _select_key(self, jwks: dict[str, Any], kid: str) -> dict[str, Any]:
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        raise InvalidTokenError(f"No JWKS key matches kid={kid!r}")

    def validate(self, token: str) -> dict[str, Any]:
        """Synchronous validation. JWKS must already be loaded via load_jwks() or
        cached from a prior call."""
        if self._jwks_cache is None:
            raise InvalidTokenError("JWKS not loaded; call load_jwks() first")
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise InvalidTokenError(f"Malformed token header: {e}") from e

        kid = unverified_header.get("kid")
        if not kid:
            raise InvalidTokenError("Token header missing kid")

        key = self._select_key(self._jwks_cache, kid)

        try:
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )
        except ExpiredSignatureError as e:
            raise InvalidTokenError("Token is expired") from e
        except JWTClaimsError as e:
            raise InvalidTokenError(f"Invalid claims: {e}") from e
        except JWTError as e:
            raise InvalidTokenError(f"Token validation failed: {e}") from e

    async def load_jwks(self) -> None:
        """Pre-load JWKS so subsequent validate() calls are sync."""
        await self._fetch_jwks()
```

- [ ] **Step 5: Run tests**

```bash
cd backend && poetry run pytest tests/middleware/test_cognito.py -v
```

Expected: `4 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/middleware/cognito.py backend/tests/middleware/test_cognito.py backend/pyproject.toml backend/poetry.lock
git commit -m "feat(wo-1): Cognito JWKS-backed JWT validator with kid/aud/exp checks"
```

---

### Task 5: UserContext + get_current_user Dependency

**Files:**
- Create: `backend/app/dependencies.py`
- Modify: `backend/app/main.py` (load JWKS on startup)
- Test: `backend/tests/test_dependencies.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_dependencies.py`:

```python
import time
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from jose.utils import long_to_base64

from app.dependencies import UserContext, get_current_user, get_token_validator
from app.middleware.cognito import CognitoTokenValidator


@pytest.fixture
def rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_numbers = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-kid",
        "use": "sig",
        "alg": "RS256",
        "n": long_to_base64(public_numbers.n).decode(),
        "e": long_to_base64(public_numbers.e).decode(),
    }
    return private_pem, jwk


def _make_app(validator: CognitoTokenValidator) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_token_validator] = lambda: validator

    @app.get("/whoami")
    async def whoami(user: UserContext = Depends(get_current_user)) -> dict:
        return user.model_dump(mode="json")

    return app


def _token(private_pem: str, claims: dict) -> str:
    return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": "test-kid"})


def test_valid_token_yields_user_context(rsa_keypair):
    private_pem, jwk = rsa_keypair
    user_id = uuid4()
    workspace_id = uuid4()
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "aud": "test-client-id",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "iat": now,
        "exp": now + 3600,
        "token_use": "id",
        "email": "user@example.com",
        "custom:workspace_id": str(workspace_id),
        "custom:role": "customer",
    }

    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get("/whoami", headers={"Authorization": f"Bearer {_token(private_pem, claims)}"})
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["workspace_id"] == str(workspace_id)
    assert body["email"] == "user@example.com"
    assert body["role"] == "customer"


def test_missing_authorization_returns_401(rsa_keypair):
    _, jwk = rsa_keypair
    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get("/whoami")
    assert response.status_code == 401


def test_invalid_token_returns_401(rsa_keypair):
    _, jwk = rsa_keypair
    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get("/whoami", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_token_missing_workspace_id_returns_401(rsa_keypair):
    private_pem, jwk = rsa_keypair
    now = int(time.time())
    claims = {
        "sub": str(uuid4()),
        "aud": "test-client-id",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "iat": now,
        "exp": now + 3600,
        "token_use": "id",
        "email": "user@example.com",
        # no custom:workspace_id
        "custom:role": "customer",
    }

    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get("/whoami", headers={"Authorization": f"Bearer {_token(private_pem, claims)}"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/test_dependencies.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.dependencies'`

- [ ] **Step 3: Implement dependencies module**

Create `backend/app/dependencies.py`:

```python
from functools import lru_cache
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr

from app.config import settings
from app.middleware.cognito import CognitoTokenValidator, InvalidTokenError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=True)


class UserContext(BaseModel):
    user_id: UUID
    workspace_id: UUID
    email: EmailStr
    role: Literal["customer", "gtm_engineer"]


@lru_cache(maxsize=1)
def get_token_validator() -> CognitoTokenValidator:
    return CognitoTokenValidator(
        user_pool_id=settings.cognito_user_pool_id,
        client_id=settings.cognito_client_id,
        region=settings.cognito_region,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    validator: CognitoTokenValidator = Depends(get_token_validator),
) -> UserContext:
    try:
        claims = validator.validate(token)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    try:
        return UserContext(
            user_id=UUID(claims["sub"]),
            workspace_id=UUID(claims["custom:workspace_id"]),
            email=claims["email"],
            role=claims["custom:role"],
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token claims missing or invalid: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
```

- [ ] **Step 4: Add startup hook in main.py to load JWKS**

Edit `backend/app/main.py` — add a startup event to pre-warm JWKS:

```python
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.dependencies import get_token_validator
from app.errors import register_exception_handlers
from app.middleware.correlation import CorrelationIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    validator = get_token_validator()
    await validator.load_jwks()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PREDICT Event API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(CorrelationIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run tests**

```bash
cd backend && poetry run pytest tests/test_dependencies.py -v
```

Expected: `4 passed`

- [ ] **Step 6: Run all tests to confirm no regressions**

```bash
export TEST_DATABASE_URL="$(grep DATABASE_URL .env | cut -d= -f2- | sed 's|/predict$|/predict_test|')"
cd backend && poetry run pytest -v
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/dependencies.py backend/app/main.py backend/tests/test_dependencies.py
git commit -m "feat(wo-1): UserContext + get_current_user FastAPI dependency"
```

---

### Task 6: Audit Log Model + Migration + write_audit_log

**Files:**
- Create: `backend/app/models/audit.py`
- Modify: `backend/app/models/__init__.py` (re-export AuditLog)
- Create: `backend/alembic/versions/<hash>_add_audit_log_table.py` (autogenerated)
- Create: `backend/app/audit.py`
- Test: `backend/tests/test_audit.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_audit.py`:

```python
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.audit import write_audit_log
from app.models.audit import AuditLog


async def test_write_audit_log_creates_immutable_row(db):
    actor = uuid4()
    resource = uuid4()
    await write_audit_log(
        db=db,
        event_type="state_transition",
        actor_id=actor,
        resource_id=resource,
        resource_type="job",
        before={"status": "pending"},
        after={"status": "in_progress"},
    )
    await db.flush()

    rows = (await db.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.event_type == "state_transition"
    assert row.actor_id == actor
    assert row.resource_id == resource
    assert row.resource_type == "job"
    assert row.before == {"status": "pending"}
    assert row.after == {"status": "in_progress"}
    assert row.created_at is not None


async def test_write_audit_log_accepts_null_before(db):
    await write_audit_log(
        db=db,
        event_type="evidence_mutation",
        actor_id=uuid4(),
        resource_id=uuid4(),
        resource_type="evidence",
        before=None,
        after={"value": "new"},
    )
    await db.flush()
    rows = (await db.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].before is None


async def test_write_audit_log_rejects_invalid_event_type(db):
    with pytest.raises(ValueError):
        await write_audit_log(
            db=db,
            event_type="bogus_event",  # type: ignore[arg-type]
            actor_id=uuid4(),
            resource_id=uuid4(),
            resource_type="job",
            before=None,
            after=None,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/test_audit.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.audit'`

- [ ] **Step 3: Create the AuditLog model**

Create `backend/app/models/audit.py`:

```python
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_type: str = Field(index=True)
    actor_id: UUID = Field(index=True)
    resource_id: UUID = Field(index=True)
    resource_type: str = Field(index=True)
    before: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    after: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
```

- [ ] **Step 4: Re-export AuditLog from app.models**

Edit `backend/app/models/__init__.py` (read it first, then add a line):

```python
from app.models.audit import AuditLog  # noqa: F401
from app.models.job import Job, JobStatus  # noqa: F401
```

(Adjust to the existing pattern — just ensure `AuditLog` is imported so SQLModel.metadata picks it up.)

- [ ] **Step 5: Generate the Alembic migration**

```bash
cd backend && poetry run alembic revision --autogenerate -m "add_audit_log_table"
```

This creates `backend/alembic/versions/<hash>_add_audit_log_table.py`. Open it and:
- **Verify** it contains `op.create_table('audit_logs', ...)` with all 8 columns plus the 4 indexes.
- **Add** `import sqlmodel` at the top if AutoString columns appear (this is the known autogenerate gotcha from WO-3).

- [ ] **Step 6: Apply the migration to the test DB**

```bash
cd backend
export TEST_DATABASE_URL="$(grep DATABASE_URL .env | cut -d= -f2- | sed 's|/predict$|/predict_test|')"
DATABASE_URL="$TEST_DATABASE_URL" poetry run alembic upgrade head
```

Expected: `audit_logs` table created. The session-scoped `engine` fixture uses `metadata.create_all`, so the test DB will pick it up automatically — but applying the migration here verifies the migration file works.

- [ ] **Step 7: Implement write_audit_log**

Create `backend/app/audit.py`:

```python
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

_VALID_EVENT_TYPES = {
    "state_transition",
    "send_action",
    "approval_change",
    "evidence_mutation",
}

EventType = Literal[
    "state_transition", "send_action", "approval_change", "evidence_mutation"
]


async def write_audit_log(
    db: AsyncSession,
    event_type: EventType,
    actor_id: UUID,
    resource_id: UUID,
    resource_type: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    if event_type not in _VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type!r}")
    entry = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        resource_id=resource_id,
        resource_type=resource_type,
        before=before,
        after=after,
    )
    db.add(entry)
    await db.flush()
```

- [ ] **Step 8: Run tests**

```bash
cd backend && poetry run pytest tests/test_audit.py -v
```

Expected: `3 passed`

- [ ] **Step 9: Run full suite**

```bash
cd backend && poetry run pytest -v
```

Expected: all green.

- [ ] **Step 10: Commit**

```bash
git add backend/app/audit.py backend/app/models/audit.py backend/app/models/__init__.py backend/alembic/versions backend/tests/test_audit.py
git commit -m "feat(wo-1): immutable audit_logs table + write_audit_log()"
```

---

### Task 7: Job Status Endpoint

**Files:**
- Create: `backend/app/api/v1/agents/__init__.py` (empty)
- Create: `backend/app/api/v1/agents/router.py`
- Modify: `backend/app/api/v1/router.py` (mount agents router)
- Test: `backend/tests/api/__init__.py` (empty)
- Test: `backend/tests/api/v1/__init__.py` (empty)
- Test: `backend/tests/api/v1/agents/__init__.py` (empty)
- Test: `backend/tests/api/v1/agents/test_router.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/api/v1/agents/test_router.py`:

```python
from uuid import uuid4

import pytest_asyncio
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.dependencies import UserContext, get_current_user
from app.main import app
from app.models.job import Job, JobStatus


def _override_user() -> UserContext:
    return UserContext(
        user_id=uuid4(),
        workspace_id=uuid4(),
        email="user@example.com",
        role="customer",
    )


@pytest_asyncio.fixture
async def client(db):
    async def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _override_user
    yield TestClient(app)
    app.dependency_overrides.clear()


async def test_get_job_status_returns_job(client, db):
    job = Job(workspace_id=uuid4(), task_type="gtm_thesis", status=JobStatus.IN_PROGRESS)
    db.add(job)
    await db.flush()
    job_id = job.id

    response = client.get(f"/api/v1/agents/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["status"] == "in_progress"
    assert body["task_type"] == "gtm_thesis"
    assert body["result"] is None
    assert body["error"] is None
    assert "created_at" in body
    assert "updated_at" in body


async def test_get_job_status_404_for_missing(client):
    response = client.get(f"/api/v1/agents/jobs/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "HTTP_ERROR"


async def test_get_job_status_invalid_uuid_returns_422(client):
    response = client.get("/api/v1/agents/jobs/not-a-uuid")
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/api/v1/agents/test_router.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement the router**

Create `backend/app/api/v1/agents/router.py`:

```python
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import UserContext, get_current_user
from app.models.job import JobStatus
from app.repositories.job import JobRepository

router = APIRouter()


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    task_type: str
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> JobStatusResponse:
    repo = JobRepository(db)
    job = await repo.get(job_id)
    if job is None or job.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        task_type=job.task_type,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
```

- [ ] **Step 4: Mount the router**

Edit `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1.agents.router import router as agents_router
from app.api.v1.common.router import router as common_router

router = APIRouter(prefix="/api/v1")
router.include_router(common_router, tags=["common"])
router.include_router(agents_router, prefix="/agents", tags=["agents"])
```

- [ ] **Step 5: Update test to match workspace scoping**

The `_override_user` returns a fresh `workspace_id` each call. Update `test_get_job_status_returns_job` to put the job in the same workspace as the override:

Edit `backend/tests/api/v1/agents/test_router.py` — change the fixture to share a workspace:

```python
import uuid as _uuid

_TEST_WORKSPACE_ID = _uuid.uuid4()


def _override_user() -> UserContext:
    return UserContext(
        user_id=uuid4(),
        workspace_id=_TEST_WORKSPACE_ID,
        email="user@example.com",
        role="customer",
    )


# ...and in test_get_job_status_returns_job, replace `workspace_id=uuid4()` with
# `workspace_id=_TEST_WORKSPACE_ID`.
```

- [ ] **Step 6: Add empty `__init__.py` files**

```bash
touch backend/tests/api/__init__.py backend/tests/api/v1/__init__.py backend/tests/api/v1/agents/__init__.py backend/app/api/v1/agents/__init__.py
```

- [ ] **Step 7: Run tests**

```bash
cd backend
export TEST_DATABASE_URL="$(grep DATABASE_URL .env | cut -d= -f2- | sed 's|/predict$|/predict_test|')"
poetry run pytest tests/api/v1/agents/test_router.py -v
```

Expected: `3 passed`

- [ ] **Step 8: Run full suite**

```bash
cd backend && poetry run pytest -v
```

Expected: all green.

- [ ] **Step 9: Commit**

```bash
git add backend/app/api/v1/agents backend/app/api/v1/router.py backend/tests/api
git commit -m "feat(wo-1): GET /api/v1/agents/jobs/{id} job status endpoint"
```

---

### Task 8: BaseIntegrationClient (httpx + tenacity)

**Files:**
- Create: `backend/app/integrations/__init__.py` (empty)
- Create: `backend/app/integrations/base.py`
- Test: `backend/tests/integrations/__init__.py` (empty)
- Test: `backend/tests/integrations/test_base.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/integrations/test_base.py`:

```python
import httpx
import pytest
import respx

from app.integrations.base import BaseIntegrationClient


class _Client(BaseIntegrationClient):
    base_url = "https://api.example.com"

    def __init__(self, api_key: str = "key123"):
        super().__init__(api_key=api_key)


@pytest.fixture
def client():
    return _Client()


@respx.mock
async def test_get_returns_json_on_2xx(client):
    respx.get("https://api.example.com/widgets").mock(
        return_value=httpx.Response(200, json={"items": [1, 2, 3]})
    )
    result = await client.get("/widgets")
    assert result == {"items": [1, 2, 3]}


@respx.mock
async def test_attaches_auth_header(client):
    route = respx.get("https://api.example.com/widgets").mock(
        return_value=httpx.Response(200, json={})
    )
    await client.get("/widgets")
    assert route.calls[0].request.headers["Authorization"] == "Bearer key123"


@respx.mock
async def test_retries_on_5xx_then_succeeds(client):
    route = respx.get("https://api.example.com/widgets").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(503),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    result = await client.get("/widgets")
    assert result == {"ok": True}
    assert route.call_count == 3


@respx.mock
async def test_gives_up_after_three_attempts(client):
    respx.get("https://api.example.com/widgets").mock(
        return_value=httpx.Response(503)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.get("/widgets")


@respx.mock
async def test_does_not_retry_on_4xx(client):
    route = respx.get("https://api.example.com/widgets").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(httpx.HTTPStatusError):
        await client.get("/widgets")
    assert route.call_count == 1


@respx.mock
async def test_post_sends_json_body(client):
    route = respx.post("https://api.example.com/widgets").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    result = await client.post("/widgets", json={"name": "thing"})
    assert result == {"id": 1}
    assert route.calls[0].request.content == b'{"name":"thing"}'
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/integrations/test_base.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement BaseIntegrationClient**

Create `backend/app/integrations/base.py`:

```python
from typing import Any, ClassVar

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


class BaseIntegrationClient:
    """Base class for outbound HTTP clients.

    Subclasses must set `base_url` and may override `auth_header_name`."""

    base_url: ClassVar[str] = ""
    auth_header_name: ClassVar[str] = "Authorization"
    auth_header_format: ClassVar[str] = "Bearer {api_key}"
    timeout_seconds: ClassVar[float] = 10.0

    def __init__(self, api_key: str) -> None:
        if not self.base_url:
            raise ValueError(f"{type(self).__name__}.base_url must be set")
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {self.auth_header_name: self.auth_header_format.format(api_key=self._api_key)}

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, max=1.0),
        reraise=True,
    )
    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(
                method, url, headers=self._headers(), json=json, params=params
            )
            response.raise_for_status()
            return response.json()

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, *, json: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", path, json=json)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && poetry run pytest tests/integrations/test_base.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/base.py backend/tests/integrations
git commit -m "feat(wo-1): BaseIntegrationClient with tenacity retry on 5xx + transport errors"
```

---

### Task 9: Crustdata, Browser Use, Unipile Clients

**Files:**
- Create: `backend/app/integrations/crustdata.py`
- Create: `backend/app/integrations/browser_use.py`
- Create: `backend/app/integrations/unipile.py`
- Test: `backend/tests/integrations/test_crustdata.py`
- Test: `backend/tests/integrations/test_browser_use.py`
- Test: `backend/tests/integrations/test_unipile.py`

These are minimal scaffolds — they only verify subclassing and base_url plumbing. Real endpoints will be added when those integrations are needed.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/integrations/test_crustdata.py`:

```python
import httpx
import respx

from app.integrations.crustdata import CrustdataClient


@respx.mock
async def test_crustdata_client_sends_request_to_configured_base_url():
    client = CrustdataClient(api_key="cd-key")
    route = respx.get("https://api.crustdata.com/v1/ping").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = await client.get("/v1/ping")
    assert result == {"ok": True}
    assert route.calls[0].request.headers["Authorization"] == "Bearer cd-key"
```

Create `backend/tests/integrations/test_browser_use.py`:

```python
import httpx
import respx

from app.integrations.browser_use import BrowserUseClient


@respx.mock
async def test_browser_use_client_sends_request_to_configured_base_url():
    client = BrowserUseClient(api_key="bu-key")
    route = respx.get("https://api.browser-use.com/v1/ping").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = await client.get("/v1/ping")
    assert result == {"ok": True}
    assert route.calls[0].request.headers["Authorization"] == "Bearer bu-key"
```

Create `backend/tests/integrations/test_unipile.py`:

```python
import httpx
import respx

from app.config import settings
from app.integrations.unipile import UnipileClient


@respx.mock
async def test_unipile_client_uses_settings_base_url(monkeypatch):
    monkeypatch.setattr(settings, "unipile_base_url", "https://api.unipile.test")
    client = UnipileClient(api_key="up-key")
    route = respx.get("https://api.unipile.test/v1/ping").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    result = await client.get("/v1/ping")
    assert result == {"ok": True}
    assert route.calls[0].request.headers["Authorization"] == "Bearer up-key"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && poetry run pytest tests/integrations/test_crustdata.py tests/integrations/test_browser_use.py tests/integrations/test_unipile.py -v
```

Expected: FAIL — modules not found.

- [ ] **Step 3: Implement clients**

Create `backend/app/integrations/crustdata.py`:

```python
from app.integrations.base import BaseIntegrationClient


class CrustdataClient(BaseIntegrationClient):
    base_url = "https://api.crustdata.com"
```

Create `backend/app/integrations/browser_use.py`:

```python
from app.integrations.base import BaseIntegrationClient


class BrowserUseClient(BaseIntegrationClient):
    base_url = "https://api.browser-use.com"
```

Create `backend/app/integrations/unipile.py` (Unipile's URL is configurable via settings — set `base_url` as an instance attribute *before* calling `super().__init__`, which checks `self.base_url`):

```python
from app.config import settings
from app.integrations.base import BaseIntegrationClient


class UnipileClient(BaseIntegrationClient):
    def __init__(self, api_key: str) -> None:
        self.base_url = settings.unipile_base_url  # type: ignore[misc]
        super().__init__(api_key=api_key)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && poetry run pytest tests/integrations -v
```

Expected: `3 new tests pass`, plus the 6 existing base tests still pass = `9 passed`.

- [ ] **Step 5: Run full suite**

```bash
cd backend
export TEST_DATABASE_URL="$(grep DATABASE_URL .env | cut -d= -f2- | sed 's|/predict$|/predict_test|')"
poetry run pytest -v
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/app/integrations/crustdata.py backend/app/integrations/browser_use.py backend/app/integrations/unipile.py backend/tests/integrations/test_crustdata.py backend/tests/integrations/test_browser_use.py backend/tests/integrations/test_unipile.py
git commit -m "feat(wo-1): Crustdata, Browser Use, Unipile integration clients"
```

---

## Phase 1 (WO-1) Acceptance

After all 9 tasks:

- [ ] `cd backend && poetry run pytest -v` — all tests green
- [ ] `GET /api/v1/health` returns `{"status": "ok"}` with `X-Correlation-ID` header
- [ ] `GET /api/v1/agents/jobs/{job_id}` returns `JobStatusResponse` for jobs the user's workspace owns; 404 otherwise
- [ ] CORS preflight from `http://localhost:5173` succeeds
- [ ] Cognito JWT validation rejects expired / wrong-aud / unknown-kid tokens
- [ ] `audit_logs` table exists in Aurora and `write_audit_log()` writes a row
- [ ] BaseIntegrationClient retries 3× on 5xx, attaches Bearer token, does not retry 4xx
