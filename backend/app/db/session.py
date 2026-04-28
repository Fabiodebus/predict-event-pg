from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import engine

# Module-level singleton — DATABASE_URL is read at import time via settings.
# Tests must have DATABASE_URL set before importing this module.
_async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session() as session:
        yield session
