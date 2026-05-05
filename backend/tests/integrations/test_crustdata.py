import httpx
import pytest
import respx

from app.integrations.crustdata import (
    MAX_IDENTIFIERS_PER_REQUEST,
    CrustdataClient,
)


@respx.mock
async def test_uses_token_auth_header() -> None:
    """Crustdata auth is `Authorization: Token <key>`, not `Bearer`."""
    route = respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[])
    )
    client = CrustdataClient(api_key="cd-key")
    await client.screener_company(company_domains=["acme.example"])
    assert route.calls.last.request.headers["Authorization"] == "Token cd-key"


@respx.mock
async def test_screener_company_by_domain() -> None:
    profile = {
        "company_name": "Hubspot",
        "company_website_domain": "hubspot.com",
        "hq_country": "United States",
    }
    route = respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[profile]),
    )
    client = CrustdataClient(api_key="k")
    result = await client.screener_company(company_domains=["hubspot.com"])

    assert result == [profile]
    assert route.calls.last.request.url.params["company_domain"] == "hubspot.com"


@respx.mock
async def test_screener_company_by_linkedin_and_domain_combined() -> None:
    respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[]),
    )
    client = CrustdataClient(api_key="k")
    await client.screener_company(
        company_domains=["a.example", "b.example"],
        company_linkedin_urls=["https://linkedin.com/company/c"],
    )

    request = respx.calls.last.request
    assert request.url.params["company_domain"] == "a.example,b.example"
    assert (
        request.url.params["company_linkedin_url"]
        == "https://linkedin.com/company/c"
    )


@respx.mock
async def test_screener_company_supports_enrich_realtime_and_fields() -> None:
    respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[]),
    )
    client = CrustdataClient(api_key="k")
    await client.screener_company(
        company_domains=["x.example"],
        fields=["headcount", "taxonomy"],
        enrich_realtime=True,
    )

    request = respx.calls.last.request
    assert request.url.params["fields"] == "headcount,taxonomy"
    assert request.url.params["enrich_realtime"] == "true"


@respx.mock
async def test_screener_company_normalizes_single_object_to_list() -> None:
    """Crustdata may return a single profile object instead of a list."""
    profile = {"company_name": "Acme", "hq_country": "US"}
    respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=profile),
    )
    client = CrustdataClient(api_key="k")
    result = await client.screener_company(company_domains=["acme.example"])
    assert result == [profile]


async def test_screener_company_requires_at_least_one_identifier() -> None:
    client = CrustdataClient(api_key="k")
    with pytest.raises(ValueError, match="at least one identifier"):
        await client.screener_company()


async def test_screener_company_caps_at_25_identifiers() -> None:
    client = CrustdataClient(api_key="k")
    too_many = [f"co-{i}.example" for i in range(MAX_IDENTIFIERS_PER_REQUEST + 1)]
    with pytest.raises(ValueError, match="at most"):
        await client.screener_company(company_domains=too_many)
