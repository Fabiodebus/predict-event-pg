import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from app.middleware.cognito import CognitoTokenValidator, InvalidTokenError


def _b64url_uint(value: int) -> str:
    byte_length = max(1, (value.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode("ascii")


@pytest.fixture
def rsa_keypair() -> tuple[str, dict, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_numbers = private_key.public_key().public_numbers()
    kid = "test-kid"

    jwk = {
        "kty": "RSA",
        "kid": kid,
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_uint(public_numbers.n),
        "e": _b64url_uint(public_numbers.e),
    }

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    return private_pem, jwk, kid


@pytest.fixture
def validator() -> CognitoTokenValidator:
    return CognitoTokenValidator(
        user_pool_id="us-test-1_ABC123",
        client_id="test-client-id",
        region="us-test-1",
    )


def _claims(
    validator: CognitoTokenValidator,
    exp: datetime,
    aud: str | None = None,
    token_use: str | None = None,
) -> dict:
    return {
        "sub": "user-123",
        "aud": aud or validator.client_id,
        "iss": validator.issuer,
        "exp": int(exp.timestamp()),
        "token_use": token_use or validator.token_use,
    }


def test_valid_token_returns_claims(
    rsa_keypair: tuple[str, dict, str],
    validator: CognitoTokenValidator,
) -> None:
    private_pem, jwk, kid = rsa_keypair
    validator._jwks_cache = {"keys": [jwk]}

    payload = _claims(validator, datetime.now(timezone.utc) + timedelta(minutes=5))
    token = jose_jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})

    decoded = validator.validate(token)

    assert decoded["sub"] == payload["sub"]
    assert decoded["aud"] == payload["aud"]
    assert decoded["iss"] == payload["iss"]


def test_expired_token_raises(
    rsa_keypair: tuple[str, dict, str],
    validator: CognitoTokenValidator,
) -> None:
    private_pem, jwk, kid = rsa_keypair
    validator._jwks_cache = {"keys": [jwk]}

    payload = _claims(validator, datetime.now(timezone.utc) - timedelta(minutes=5))
    token = jose_jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})

    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_wrong_audience_raises(
    rsa_keypair: tuple[str, dict, str],
    validator: CognitoTokenValidator,
) -> None:
    private_pem, jwk, kid = rsa_keypair
    validator._jwks_cache = {"keys": [jwk]}

    payload = _claims(
        validator,
        datetime.now(timezone.utc) + timedelta(minutes=5),
        aud="wrong-client-id",
    )
    token = jose_jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})

    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_unknown_kid_raises(
    rsa_keypair: tuple[str, dict, str],
    validator: CognitoTokenValidator,
) -> None:
    private_pem, jwk, kid = rsa_keypair
    validator._jwks_cache = {"keys": [{**jwk, "kid": "different-kid"}]}

    payload = _claims(validator, datetime.now(timezone.utc) + timedelta(minutes=5))
    token = jose_jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})

    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_wrong_token_use_raises(
    rsa_keypair: tuple[str, dict, str],
    validator: CognitoTokenValidator,
) -> None:
    """An access token presented to an id-token endpoint must be rejected,
    even though it has a valid signature, audience, and issuer."""
    private_pem, jwk, kid = rsa_keypair
    validator._jwks_cache = {"keys": [jwk]}

    payload = _claims(
        validator,
        datetime.now(timezone.utc) + timedelta(minutes=5),
        token_use="access",
    )
    token = jose_jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid})

    with pytest.raises(InvalidTokenError):
        validator.validate(token)


def test_validate_without_loaded_jwks_raises(
    validator: CognitoTokenValidator,
) -> None:
    """validate() before load_jwks() is a programmer error, not a token error."""
    with pytest.raises(InvalidTokenError):
        validator.validate("any.token.here")
