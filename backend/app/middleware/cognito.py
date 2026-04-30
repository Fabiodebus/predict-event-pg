"""Cognito JWT validator with JWKS caching.

Limitations (acceptable for now, revisit when traffic warrants):
- JWKS cache never expires; on key rotation the process must restart. Cognito
  rotates keys rarely.
- No lock around `_fetch_jwks()`; concurrent first-fetch may double-fetch.
  JWKS responses are idempotent so this is benign.
- `validate()` is synchronous; callers must `await load_jwks()` once at startup
  (see app.main lifespan in Task 5).
"""

import httpx
from jose import jwt as jose_jwt


class InvalidTokenError(Exception):
    pass


class CognitoTokenValidator:
    def __init__(
        self,
        user_pool_id: str,
        client_id: str,
        region: str,
        token_use: str = "id",
    ) -> None:
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self.token_use = token_use
        self._jwks_cache: dict | None = None

    @property
    def issuer(self) -> str:
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"

    async def _fetch_jwks(self) -> dict:
        if self._jwks_cache is not None:
            return self._jwks_cache

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            jwks = response.json()

        self._jwks_cache = jwks
        return jwks

    def _select_key(self, jwks: dict, kid: str) -> dict:
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
        raise InvalidTokenError("Unknown signing key")

    def validate(self, token: str) -> dict:
        if self._jwks_cache is None:
            # Programmer error — load_jwks() must be awaited once at startup.
            # Don't surface this as a token-shaped 401 to clients.
            raise InvalidTokenError("Token validator not initialized")

        try:
            header = jose_jwt.get_unverified_header(token)
            kid = header["kid"]
            key = self._select_key(self._jwks_cache, kid)
            claims = jose_jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
            )
        except InvalidTokenError:
            raise
        except Exception as exc:
            raise InvalidTokenError("Invalid token") from exc

        # Cognito issues both id and access tokens with the same signing keys.
        # Refuse access tokens when we want id tokens (and vice versa).
        if claims.get("token_use") != self.token_use:
            raise InvalidTokenError("Invalid token")

        return claims

    async def load_jwks(self) -> None:
        await self._fetch_jwks()
