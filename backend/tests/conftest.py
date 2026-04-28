import os

from dotenv import load_dotenv

load_dotenv()  # loads backend/.env into os.environ

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

import app.models  # noqa: F401 - registers Job and all future models with SQLModel.metadata

DATABASE_URL = os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine():
    _engine = create_async_engine(DATABASE_URL, echo=False)
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
