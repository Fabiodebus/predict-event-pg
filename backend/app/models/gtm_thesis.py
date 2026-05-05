import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import JSON, Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, SQLModel


class ThesisStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"


class GTMThesis(SQLModel, table=True):
    __tablename__ = "gtm_theses"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", unique=True)
    status: ThesisStatus = ThesisStatus.DRAFT
    # Circular FK: gtm_thesis_versions.thesis_id → gtm_theses.id and
    # gtm_theses.active_version_id → gtm_thesis_versions.id. use_alter defers
    # the constraint to a post-create ALTER TABLE so both tables can exist
    # before either FK is enforced.
    active_version_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            sa.Uuid(),
            ForeignKey(
                "gtm_thesis_versions.id",
                use_alter=True,
                name="fk_gtm_theses_active_version_id_gtm_thesis_versions",
            ),
            nullable=True,
        ),
    )
    generation_job_id: UUID | None = Field(
        default=None, foreign_key="jobs.id", nullable=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class GTMThesisVersion(SQLModel, table=True):
    __tablename__ = "gtm_thesis_versions"
    __table_args__ = (
        UniqueConstraint(
            "thesis_id",
            "version_number",
            name="uq_gtm_thesis_versions_thesis_id_version_number",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    thesis_id: UUID = Field(foreign_key="gtm_theses.id", index=True)
    version_number: int
    # Immutable snapshot of all sections at approval time.
    sections: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    approved_at: datetime | None = None
    # approved_by is the Cognito sub of the approving user. No DB FK
    # (no users table — see app.models.workspace.Workspace.customer_id).
    approved_by: UUID | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class GTMThesisSection(SQLModel, table=True):
    __tablename__ = "gtm_thesis_sections"
    __table_args__ = (
        UniqueConstraint(
            "thesis_id",
            "section_key",
            name="uq_gtm_thesis_sections_thesis_id_section_key",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    thesis_id: UUID = Field(foreign_key="gtm_theses.id", index=True)
    section_key: str
    content: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    is_ai_generated: bool = True
    is_flagged_incomplete: bool = False
    accepted_at: datetime | None = None
    last_edited_at: datetime | None = None
