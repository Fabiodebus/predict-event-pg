from sqlalchemy.ext.asyncio import AsyncSession


async def test_get_db_yields_async_session():
    from app.db.session import get_db
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        break


async def test_get_db_returns_new_session_each_call():
    """Each call to get_db() should produce an independent session object."""
    from app.db.session import get_db
    first_id = None
    second_id = None
    async for session in get_db():
        first_id = id(session)
    async for session in get_db():
        second_id = id(session)
    assert first_id != second_id
