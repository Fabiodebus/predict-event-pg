from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel  # noqa: F401

from app.config import settings

engine: AsyncEngine = create_async_engine(settings.database_url, echo=False)
