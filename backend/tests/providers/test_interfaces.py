from typing import get_type_hints

from app.providers.company_discovery import CompanyDiscoveryProvider
from app.providers.company_enrichment import CompanyEnrichmentProvider
from app.providers.person_enrichment import PersonEnrichmentProvider
from app.providers.social_search import SocialSearchProvider
from app.providers.web_extraction import WebExtractionProvider


def test_web_extraction_protocol_has_extract():
    assert hasattr(WebExtractionProvider, "extract")


def test_social_search_protocol_has_search_posts():
    assert hasattr(SocialSearchProvider, "search_posts")


def test_company_enrichment_protocol_has_enrich():
    assert hasattr(CompanyEnrichmentProvider, "enrich_company")


def test_person_enrichment_protocol_has_enrich_person():
    assert hasattr(PersonEnrichmentProvider, "enrich_person")


def test_company_discovery_protocol_has_discover():
    assert hasattr(CompanyDiscoveryProvider, "discover_companies")


def test_runtime_checkable_via_duck_typing():
    class _DuckExtractor:
        async def extract(self, *, url: str, schema: dict) -> dict:
            return {}

    assert isinstance(_DuckExtractor(), WebExtractionProvider)
