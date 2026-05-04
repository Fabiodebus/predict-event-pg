from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WebExtractionProvider(Protocol):
    """Browser/web extraction. Returns structured JSON conforming to `schema`."""

    async def extract(self, *, url: str, schema: dict[str, Any]) -> dict[str, Any]:
        ...
