from uuid import uuid4

from app.models.job import Job, JobStatus
from app.repositories.base import BaseRepository


class JobBaseRepo(BaseRepository[Job]):
    model = Job


async def test_create_and_get(db):
    repo = JobBaseRepo(db)
    workspace_id = uuid4()
    job = Job(workspace_id=workspace_id, task_type="test")

    created = await repo.create(job)
    assert created.id is not None
    assert created.task_type == "test"

    fetched = await repo.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_returns_none_for_missing_id(db):
    repo = JobBaseRepo(db)
    result = await repo.get(uuid4())
    assert result is None


async def test_list_is_workspace_scoped(db):
    repo = JobBaseRepo(db)
    ws_a = uuid4()
    ws_b = uuid4()

    await repo.create(Job(workspace_id=ws_a, task_type="gtm_thesis"))
    await repo.create(Job(workspace_id=ws_a, task_type="enrichment"))
    await repo.create(Job(workspace_id=ws_b, task_type="gtm_thesis"))

    results_a = await repo.list(workspace_id=ws_a)
    assert len(results_a) == 2
    assert all(j.workspace_id == ws_a for j in results_a)

    results_b = await repo.list(workspace_id=ws_b)
    assert len(results_b) == 1


async def test_list_with_filter(db):
    repo = JobBaseRepo(db)
    ws = uuid4()
    await repo.create(Job(workspace_id=ws, task_type="gtm_thesis"))
    await repo.create(Job(workspace_id=ws, task_type="enrichment"))

    results = await repo.list(workspace_id=ws, task_type="gtm_thesis")
    assert len(results) == 1
    assert results[0].task_type == "gtm_thesis"


async def test_update(db):
    repo = JobBaseRepo(db)
    ws = uuid4()
    job = await repo.create(Job(workspace_id=ws, task_type="test"))

    job.task_type = "updated"
    updated = await repo.update(job)
    assert updated.task_type == "updated"

    fetched = await repo.get(job.id)
    assert fetched.task_type == "updated"


async def test_delete(db):
    repo = JobBaseRepo(db)
    ws = uuid4()
    job = await repo.create(Job(workspace_id=ws, task_type="test"))

    await repo.delete(job.id)
    assert await repo.get(job.id) is None


async def test_delete_nonexistent_does_not_raise(db):
    repo = JobBaseRepo(db)
    await repo.delete(uuid4())
