from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.base import engine


class PredictAsyncSession(AsyncSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._predict_closed = False

    @property
    def is_active(self):
        if self._predict_closed:
            return False
        return super().is_active

    async def close(self) -> None:
        self.sync_session.close()
        self._predict_closed = True


_async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False, class_=PredictAsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _async_session() as session:
        yield session
