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
