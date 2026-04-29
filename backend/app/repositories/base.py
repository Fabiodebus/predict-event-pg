from typing import Any, ClassVar, Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    model: ClassVar[type]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, id: UUID) -> T | None:
        return await self.db.get(self.model, id)

    async def list(self, workspace_id: UUID, **filters: Any) -> list[T]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            *[getattr(self.model, k) == v for k, v in filters.items()],
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: T) -> T:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, id: UUID) -> None:
        obj = await self.get(id)
        if obj is not None:
            await self.db.delete(obj)
            await self.db.flush()
