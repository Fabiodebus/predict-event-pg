from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.job import Job, JobStatus
from app.repositories.job import JobRepository

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.database_url, echo=False)
_default_factory = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def _open_session() -> AsyncIterator[AsyncSession]:
    """Module-level session opener so tests can monkeypatch it.

    Production: yields a fresh session from the engine bound to settings.database_url.
    Tests: monkeypatched to yield the savepoint-bound test session.
    """
    async with _default_factory() as session:
        yield session


class IdempotentTask(Task):
    """Celery base class that mirrors task lifecycle into the `jobs` table.

    Subclassed via:  @celery_app.task(bind=True, base=IdempotentTask, name=...)

    Lifecycle:
        dispatch()   -> writes Job(status=pending, idempotency_key=?, celery_task_id=?)
        before_start -> Job.status = in_progress, attempt_count += 1
        on_success   -> Job.status = completed
        on_failure   -> Job.status = failed, Job.error = repr(exc)

    The task return value is NOT written to Job.result. Per blueprint,
    results are validated and persisted by the API layer.

    Note: dispatch() creates the Job row and returns it with a pre-allocated
    celery_task_id. The caller is responsible for firing apply_async() with
    that task_id so the worker can resolve the Job row without a race.

    Same-process / test mode
    ------------------------
    When the dispatch and the task execution happen in the same process (eager
    mode in tests), dispatch() stores the Job reference in `self._jobs`.  The
    sync lifecycle hooks (before_start, on_success, on_failure) modify that
    in-memory object directly — no async I/O, no futures, no event-loop
    interaction.  SQLAlchemy records the attribute changes as dirty.  The
    test's subsequent `await db.refresh(job)` triggers an autoflush that
    issues the UPDATE before re-reading from the DB, so the assertions see the
    correct state.

    Production mode
    ---------------
    In a real Celery worker the process is different from the one that called
    dispatch(), so `self._jobs` is empty.  The hooks use asyncio.run() (safe
    because no event loop is running inside a Celery worker thread) to open a
    fresh session, look up the Job by celery_task_id, persist the new state,
    and commit.
    """

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 60
    retry_jitter = True
    max_retries = 3

    # Per-task-instance cache populated by dispatch().
    # Keyed by celery_task_id (str); values are Job ORM objects bound to
    # whatever AsyncSession was passed to dispatch().
    _jobs: dict[str, Job]

    def __init__(self) -> None:
        super().__init__()
        self._jobs = {}

    @classmethod
    async def dispatch(
        cls,
        task: Task,
        *,
        workspace_id: UUID,
        task_type: str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        workflow_run_id: UUID | None = None,
        db: AsyncSession,
    ) -> Job:
        """Create a Job row in pending state and return it.

        If idempotency_key is provided and a Job with that key already exists,
        returns the existing job without creating a duplicate.

        The caller should follow up with:
            task.apply_async(args=args, kwargs=kwargs or {}, task_id=job.celery_task_id)
        so that the worker can resolve the Job by celery_task_id.
        """
        repo = JobRepository(db)

        if idempotency_key is not None:
            existing = await repo.get_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        celery_task_id = str(uuid4())
        job = Job(
            workspace_id=workspace_id,
            task_type=task_type,
            celery_task_id=celery_task_id,
            idempotency_key=idempotency_key,
            workflow_run_id=workflow_run_id,
            status=JobStatus.PENDING,
        )
        await repo.create(job)

        # Cache on the task instance so in-process hooks can update it
        # without a DB lookup.
        if hasattr(task, '_jobs'):
            task._jobs[celery_task_id] = job  # type: ignore[union-attr]

        return job

    # ------------------------------------------------------------------
    # Celery lifecycle hooks
    # ------------------------------------------------------------------

    def before_start(self, task_id: str, args, kwargs) -> None:  # type: ignore[override]
        if self._try_in_memory_update(task_id, status=JobStatus.IN_PROGRESS, bump_attempt=True):
            return
        asyncio.run(self._mutate_job_db(task_id, status=JobStatus.IN_PROGRESS, bump_attempt=True))

    def on_success(self, retval, task_id, args, kwargs) -> None:  # type: ignore[override]
        if self._try_in_memory_update(task_id, status=JobStatus.COMPLETED):
            return
        asyncio.run(self._mutate_job_db(task_id, status=JobStatus.COMPLETED))

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:  # type: ignore[override]
        error = f"{type(exc).__name__}: {exc}"
        if self._try_in_memory_update(task_id, status=JobStatus.FAILED, error=error):
            return
        asyncio.run(self._mutate_job_db(task_id, status=JobStatus.FAILED, error=error))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_in_memory_update(
        self,
        celery_task_id: str,
        *,
        status: JobStatus,
        error: str | None = None,
        bump_attempt: bool = False,
    ) -> bool:
        """Attempt to update the job state purely in-memory.

        Returns True if the job was found in the local cache and updated.
        Returns False if the job is not in the cache (production / cross-process
        case) and the caller should fall back to a DB update.

        The SQLAlchemy session tracks the attribute change as dirty.  The next
        flush (e.g., triggered by `await db.refresh(job)` autoflush) will issue
        the UPDATE and make the new state visible.
        """
        job = self._jobs.get(celery_task_id)
        if job is None:
            return False
        job.status = status
        if error is not None:
            job.error = error
        if bump_attempt:
            job.attempt_count += 1
        return True

    async def _mutate_job_db(
        self,
        celery_task_id: str,
        *,
        status: JobStatus,
        error: str | None = None,
        bump_attempt: bool = False,
    ) -> None:
        """Persist a job state transition to the database.

        Used in production (cross-process) where the job is not in the local
        cache.  Opens a session via _open_session(), looks up the job, updates
        it, and commits.
        """
        async with _open_session() as session:
            repo = JobRepository(session)
            job = await repo.get_by_celery_task_id(celery_task_id)
            if job is None:
                return
            job.status = status
            if error is not None:
                job.error = error
            if bump_attempt:
                job.attempt_count += 1
            await repo.update(job)
            await session.commit()
