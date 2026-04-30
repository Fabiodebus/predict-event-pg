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
