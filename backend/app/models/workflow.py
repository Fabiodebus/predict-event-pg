import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class WorkflowRunStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRun(SQLModel, table=True):
    __tablename__ = "workflow_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(index=True)
    workflow_type: str  # e.g. "gtm_thesis", "event_research", "enrichment", "outreach"
    status: WorkflowRunStatus = WorkflowRunStatus.PENDING
    current_node: str | None = None
    iteration_count: int = 0
    max_iteration_count: int  # required, per-workflow override of escalation policy
    acceptance_threshold: float  # required, per-workflow override
    escalated: bool = False
    escalation_reason: str | None = None
    error: str | None = None
    state: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
