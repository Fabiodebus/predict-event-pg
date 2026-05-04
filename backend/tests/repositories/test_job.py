from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus
from app.repositories.job import JobRepository


async def test_job_create_and_get(db: AsyncSession) -> None:
    repo = JobRepository(db)
    job = Job(workspace_id=uuid4(), task_type="gtm_thesis")

    created = await repo.create(job)
    created_id = created.id
    db.expire_all()

    fetched = await repo.get(created_id)
    assert fetched is not None
    assert fetched.task_type == "gtm_thesis"


async def test_job_list_workspace_scoped(db: AsyncSession) -> None:
    repo = JobRepository(db)
    ws1 = uuid4()
    ws2 = uuid4()

    job_ws1 = await repo.create(Job(workspace_id=ws1, task_type="gtm_thesis"))
    await repo.create(Job(workspace_id=ws2, task_type="gtm_thesis"))

    results = await repo.list(workspace_id=ws1)
    assert [j.id for j in results] == [job_ws1.id]


async def test_get_by_celery_task_id_found(db: AsyncSession) -> None:
    repo = JobRepository(db)
    await repo.create(
        Job(
            workspace_id=uuid4(),
            task_type="gtm_thesis",
            celery_task_id="task-abc-123",
        )
    )
    db.expire_all()

    found = await repo.get_by_celery_task_id("task-abc-123")
    assert found is not None
    assert found.celery_task_id == "task-abc-123"


async def test_get_by_celery_task_id_not_found(db: AsyncSession) -> None:
    repo = JobRepository(db)
    result = await repo.get_by_celery_task_id("nonexistent-id")
    assert result is None


async def test_job_update_status(db: AsyncSession) -> None:
    repo = JobRepository(db)
    created = await repo.create(Job(workspace_id=uuid4(), task_type="gtm_thesis"))
    created_id = created.id
    db.expire_all()

    job_obj = await repo.get(created_id)
    assert job_obj is not None
    job_obj.status = JobStatus.IN_PROGRESS
    await repo.update(job_obj)
    db.expire_all()

    refreshed = await repo.get(created_id)
    assert refreshed is not None
    assert refreshed.status == JobStatus.IN_PROGRESS


async def test_job_delete(db: AsyncSession) -> None:
    repo = JobRepository(db)
    created = await repo.create(Job(workspace_id=uuid4(), task_type="gtm_thesis"))
    created_id = created.id
    db.expire_all()

    await repo.delete(created_id)
    result = await repo.get(created_id)
    assert result is None


async def test_get_by_idempotency_key_found(db: AsyncSession) -> None:
    repo = JobRepository(db)
    await repo.create(
        Job(workspace_id=uuid4(), task_type="enrichment", idempotency_key="enrich:account-1")
    )
    db.expire_all()

    found = await repo.get_by_idempotency_key("enrich:account-1")
    assert found is not None
    assert found.idempotency_key == "enrich:account-1"


async def test_get_by_idempotency_key_not_found(db: AsyncSession) -> None:
    repo = JobRepository(db)
    assert await repo.get_by_idempotency_key("never-seen") is None
