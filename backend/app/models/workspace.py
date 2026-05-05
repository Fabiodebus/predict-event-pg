from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # customer_id is the Cognito `sub` claim. No DB FK — there is no users
    # table in this codebase; identity lives in Cognito. Add an FK if/when a
    # users table is introduced.
    customer_id: UUID = Field(index=True)
    company_name: str
    primary_domain: str = Field(unique=True)
    # Wizard state persisted by the frontend for resume-after-close UX.
    # Schema is opaque to the backend; PATCH replaces the whole object.
    onboarding_state: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
