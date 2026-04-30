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
