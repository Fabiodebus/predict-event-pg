from typing import Any, Iterable

from app.integrations.base import BaseIntegrationClient


# Crustdata's `GET /screener/company` accepts up to 25 identifiers per request.
MAX_IDENTIFIERS_PER_REQUEST = 25


class CrustdataClient(BaseIntegrationClient):
    """Crustdata Screener API client.

    Auth: `Authorization: Token <api_key>`. Base URL: https://api.crustdata.com.
    The Screener endpoint accepts up to 25 identifiers per request and returns
    a comprehensive firmographic profile per match.
    """

    base_url = "https://api.crustdata.com"
    auth_header_format = "Token {api_key}"

    async def screener_company(
        self,
        *,
        company_domains: Iterable[str] | None = None,
        company_names: Iterable[str] | None = None,
        company_linkedin_urls: Iterable[str] | None = None,
        fields: Iterable[str] | None = None,
        enrich_realtime: bool = False,
    ) -> list[dict[str, Any]]:
        """Call `GET /screener/company` and return a list of company profiles.

        At least one identifier source must be provided. Combined identifier
        count must not exceed MAX_IDENTIFIERS_PER_REQUEST.
        """
        domains = list(company_domains) if company_domains else []
        names = list(company_names) if company_names else []
        linkedin_urls = list(company_linkedin_urls) if company_linkedin_urls else []

        total = len(domains) + len(names) + len(linkedin_urls)
        if total == 0:
            raise ValueError(
                "screener_company requires at least one identifier "
                "(company_domains, company_names, or company_linkedin_urls)"
            )
        if total > MAX_IDENTIFIERS_PER_REQUEST:
            raise ValueError(
                f"screener_company accepts at most {MAX_IDENTIFIERS_PER_REQUEST} "
                f"identifiers per request; got {total}"
            )

        params: dict[str, Any] = {}
        if domains:
            params["company_domain"] = ",".join(domains)
        if names:
            params["company_name"] = ",".join(names)
        if linkedin_urls:
            params["company_linkedin_url"] = ",".join(linkedin_urls)
        if fields:
            params["fields"] = ",".join(fields)
        if enrich_realtime:
            params["enrich_realtime"] = "true"

        result: Any = await self.get("/screener/company", params=params)
        # Crustdata returns either a single object or a list depending on
        # identifier count. Normalize to a list.
        if isinstance(result, list):
            return result
        return [result]
