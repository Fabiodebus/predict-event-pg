import time
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from jose.utils import long_to_base64

from app.dependencies import (
    UserContext,
    get_current_user,
    get_token_validator,
    require_gtm_engineer,
    require_role,
)
from app.middleware.cognito import CognitoTokenValidator


@pytest.fixture
def rsa_keypair() -> tuple[str, dict]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_numbers = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test-kid",
        "use": "sig",
        "alg": "RS256",
        "n": long_to_base64(public_numbers.n).decode("ascii"),
        "e": long_to_base64(public_numbers.e).decode("ascii"),
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


def test_valid_token_yields_user_context(rsa_keypair: tuple[str, dict]) -> None:
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
    response = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {_token(private_pem, claims)}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["workspace_id"] == str(workspace_id)
    assert body["email"] == "user@example.com"
    assert body["role"] == "customer"


def test_missing_authorization_returns_401(rsa_keypair: tuple[str, dict]) -> None:
    _, jwk = rsa_keypair
    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get("/whoami")
    assert response.status_code == 401


def test_invalid_token_returns_401(rsa_keypair: tuple[str, dict]) -> None:
    _, jwk = rsa_keypair
    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get("/whoami", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_token_with_invalid_role_returns_401(rsa_keypair: tuple[str, dict]) -> None:
    """Cognito role outside the allowed Literal must produce 401, not 500."""
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
        "custom:workspace_id": str(uuid4()),
        "custom:role": "admin",  # not in Literal["customer", "gtm_engineer"]
    }

    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {_token(private_pem, claims)}"},
    )
    assert response.status_code == 401


def _make_role_guarded_app(
    actor_role: str, guard: object, route: str = "/guarded"
) -> FastAPI:
    """Build an app that overrides get_current_user with a fixed role and exposes a guarded route."""
    app = FastAPI()
    fake_user = UserContext(
        user_id=uuid4(),
        workspace_id=uuid4(),
        email="user@example.com",
        role=actor_role,  # type: ignore[arg-type]
    )

    async def _override_user() -> UserContext:
        return fake_user

    app.dependency_overrides[get_current_user] = _override_user

    @app.get(route)
    async def _route(user: UserContext = Depends(guard)) -> dict:
        return {"role": user.role}

    return app


def test_require_role_allows_matching_role() -> None:
    guard = require_role("gtm_engineer")
    client = TestClient(_make_role_guarded_app("gtm_engineer", guard))
    response = client.get("/guarded")
    assert response.status_code == 200
    assert response.json() == {"role": "gtm_engineer"}


def test_require_role_rejects_non_matching_role() -> None:
    guard = require_role("gtm_engineer")
    client = TestClient(_make_role_guarded_app("customer", guard))
    response = client.get("/guarded")
    assert response.status_code == 403
    assert "customer" in response.json()["detail"]


def test_require_role_accepts_any_listed_role() -> None:
    guard = require_role("customer", "gtm_engineer")
    client = TestClient(_make_role_guarded_app("customer", guard))
    response = client.get("/guarded")
    assert response.status_code == 200


def test_require_gtm_engineer_blocks_customer() -> None:
    client = TestClient(_make_role_guarded_app("customer", require_gtm_engineer))
    response = client.get("/guarded")
    assert response.status_code == 403


def test_require_gtm_engineer_allows_gtm_engineer() -> None:
    client = TestClient(_make_role_guarded_app("gtm_engineer", require_gtm_engineer))
    response = client.get("/guarded")
    assert response.status_code == 200


def test_token_missing_workspace_id_returns_401(rsa_keypair: tuple[str, dict]) -> None:
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
        "custom:role": "gtm_engineer",
    }

    validator = CognitoTokenValidator("us-east-1_TESTPOOL", "test-client-id", "us-east-1")
    validator._jwks_cache = {"keys": [jwk]}

    client = TestClient(_make_app(validator))
    response = client.get(
        "/whoami",
        headers={"Authorization": f"Bearer {_token(private_pem, claims)}"},
    )
    assert response.status_code == 401
