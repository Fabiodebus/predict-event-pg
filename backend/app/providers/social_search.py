from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SocialSearchProvider(Protocol):
    """LinkedIn (or similar) post search by keyword/filter."""

    async def search_posts(
        self,
        *,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        ...
