from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.tasks.base as task_base
from app.celery_app import celery_app
from app.models.job import JobStatus
from app.tasks.base import IdempotentTask


@celery_app.task(bind=True, base=IdempotentTask, name="tests.echo")
def echo_task(self, value: str) -> str:
    return value


@celery_app.task(bind=True, base=IdempotentTask, name="tests.boom", max_retries=2)
def boom_task(self) -> None:
    raise RuntimeError("boom")


@pytest.fixture(autouse=True)
def _stub_session_factory(monkeypatch, db: AsyncSession):
    """Route IdempotentTask writes into the test's savepoint-bound session
    so assertions see them and the outer transaction rolls them back.

    Also patches db.refresh to flush pending changes before reloading.
    Celery lifecycle hooks modify job attributes in-memory (synchronously,
    to avoid event-loop re-entrance).  Those dirty changes must be flushed
    to the DB within the savepoint before refresh issues its SELECT,
    otherwise Session.refresh's _expire_state() discards them first.
    """

    @asynccontextmanager
    async def _ctx():
        # Don't close the session — the test fixture owns its lifecycle.
        yield db

    monkeypatch.setattr(task_base, "_open_session", _ctx)

    # Wrap db.refresh so it flushes dirty in-memory state first.
    _orig_refresh = db.refresh

    async def _refresh_with_flush(instance, **kwargs):  # type: ignore[return]
        await db.flush()
        return await _orig_refresh(instance, **kwargs)

    monkeypatch.setattr(db, "refresh", _refresh_with_flush)


async def test_dispatches_job_pending_then_completed(db: AsyncSession) -> None:
    workspace_id = uuid4()
    job = await IdempotentTask.dispatch(
        echo_task,
        workspace_id=workspace_id,
        task_type="echo",
        args=("hello",),
        db=db,
    )
    assert job.status == JobStatus.PENDING
    # Eager mode runs the task inline; reading the job from the same session
    # should reflect the completed state.
    result = echo_task.apply(args=("hello",), task_id=job.celery_task_id)
    await db.refresh(job)
    assert result.result == "hello"
    assert job.status == JobStatus.COMPLETED
    assert job.attempt_count == 1
    assert job.error is None
    # Result column is intentionally NOT populated by the base class.
    assert job.result is None


async def test_idempotency_key_short_circuits(db: AsyncSession) -> None:
    workspace_id = uuid4()
    first = await IdempotentTask.dispatch(
        echo_task,
        workspace_id=workspace_id,
        task_type="echo",
        args=("first",),
        idempotency_key="echo:abc",
        db=db,
    )
    second = await IdempotentTask.dispatch(
        echo_task,
        workspace_id=workspace_id,
        task_type="echo",
        args=("second",),
        idempotency_key="echo:abc",
        db=db,
    )
    assert first.id == second.id


async def test_failure_records_error_and_increments_attempts(db: AsyncSession) -> None:
    workspace_id = uuid4()
    job = await IdempotentTask.dispatch(
        boom_task,
        workspace_id=workspace_id,
        task_type="boom",
        args=(),
        db=db,
    )
    result = boom_task.apply(args=(), task_id=job.celery_task_id)
    assert result.failed()
    await db.refresh(job)
    assert job.status == JobStatus.FAILED
    assert "boom" in (job.error or "")
    # max_retries=2 means up to 3 total attempts.
    assert job.attempt_count >= 1
