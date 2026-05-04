from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CompanyEnrichmentProvider(Protocol):
    async def enrich_company(self, *, identifier: str) -> dict[str, Any]:
        ...
