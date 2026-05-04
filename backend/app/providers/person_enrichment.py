from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PersonEnrichmentProvider(Protocol):
    async def enrich_person(self, *, identifier: str) -> dict[str, Any]:
        ...
