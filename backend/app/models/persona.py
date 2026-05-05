from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Persona(SQLModel, table=True):
    __tablename__ = "personas"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    name: str
    job_title_patterns: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    function: str | None = None
    seniority_level: str | None = None
    description: str | None = None
    priority_rank: int
    event_context_behavior: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    is_ai_suggested: bool = False
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
