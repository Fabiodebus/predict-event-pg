import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(index=True)
    workflow_run_id: UUID | None = Field(
        default=None, foreign_key="workflow_runs.id", index=True
    )
    task_type: str
    celery_task_id: str | None = None
    idempotency_key: str | None = Field(default=None, unique=True, index=True)
    attempt_count: int = 0
    status: JobStatus = JobStatus.PENDING
    error: str | None = None
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
