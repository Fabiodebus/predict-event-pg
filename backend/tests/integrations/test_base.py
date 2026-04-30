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
