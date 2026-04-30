from app.config import settings
from app.integrations.base import BaseIntegrationClient


class UnipileClient(BaseIntegrationClient):
    def __init__(self, api_key: str) -> None:
        self.base_url = settings.unipile_base_url  # type: ignore[misc]
        super().__init__(api_key=api_key)
