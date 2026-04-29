import os

from dotenv import load_dotenv

load_dotenv()  # loads backend/.env into os.environ

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

import app.models  # noqa: F401 - registers Job and all future models with SQLModel.metadata


def _get_test_database_url() -> str:
    # Use TEST_DATABASE_URL if set, otherwise fall back to DATABASE_URL.
    # A dedicated test DB is strongly recommended — the session fixture calls drop_all on teardown.
    url = os.environ.get("TEST_DATABASE_URL") or os.environ["DATABASE_URL"]
    assert "localhost" in url or "_test" in url or "127.0.0.1" in url, (
        f"Refusing to run destructive test fixtures against a non-local / non-test database.\n"
        f"Set TEST_DATABASE_URL to a dedicated test database URL.\nGot: {url!r}"
    )
    return url


@pytest_asyncio.fixture(scope="session")
async def engine():
    _engine = create_async_engine(_get_test_database_url(), echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncSession:
    """Each test gets an isolated session. All writes are rolled back after the test."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(conn, join_transaction_mode="create_savepoint")
        yield session
        await session.close()
        await transaction.rollback()
