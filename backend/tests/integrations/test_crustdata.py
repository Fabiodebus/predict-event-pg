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
