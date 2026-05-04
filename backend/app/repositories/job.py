from sqlalchemy import select

from app.models.job import Job
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    async def get_by_celery_task_id(self, celery_task_id: str) -> Job | None:
        stmt = select(self.model).where(self.model.celery_task_id == celery_task_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Job | None:
        stmt = select(self.model).where(self.model.idempotency_key == idempotency_key)
        result = await self.db.execute(stmt)
        return result.scalars().first()
