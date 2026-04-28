import pytest
from sqlalchemy.ext.asyncio import AsyncSession


async def test_get_db_yields_async_session():
    from app.db.session import get_db
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break


async def test_get_db_session_closes_after_use():
    from app.db.session import get_db
    sessions = []
    async for session in get_db():
        sessions.append(session)
    assert sessions[0].is_active is False
