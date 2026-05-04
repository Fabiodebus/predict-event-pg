from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CompanyDiscoveryProvider(Protocol):
    async def discover_companies(
        self,
        *,
        criteria: dict[str, Any],
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        ...
