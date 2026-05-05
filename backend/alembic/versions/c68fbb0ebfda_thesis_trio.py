"""gtm_theses + gtm_thesis_versions + gtm_thesis_sections (with circular FK)

Revision ID: c68fbb0ebfda
Revises: 79d93bd1105b
Create Date: 2026-05-05 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "c68fbb0ebfda"
down_revision: Union[str, None] = "79d93bd1105b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Circular FK requires use_alter: gtm_theses.active_version_id ->
# gtm_thesis_versions.id, while gtm_thesis_versions.thesis_id ->
# gtm_theses.id. The active_version_id FK is added via a separate
# ALTER TABLE after both tables exist. The matching SQLModel uses
# use_alter=True so SQLModel.metadata.create_all (used by tests)
# follows the same pattern.
ACTIVE_VERSION_FK = "fk_gtm_theses_active_version_id_gtm_thesis_versions"


def upgrade() -> None:
    op.create_table(
        "gtm_theses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "IN_REVIEW", "APPROVED", name="thesisstatus"),
            nullable=False,
        ),
        sa.Column("active_version_id", sa.Uuid(), nullable=True),
        sa.Column("generation_job_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_gtm_theses_workspace_id_workspaces"),
        ),
        sa.ForeignKeyConstraint(
            ["generation_job_id"],
            ["jobs.id"],
            name=op.f("fk_gtm_theses_generation_job_id_jobs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gtm_theses")),
        sa.UniqueConstraint(
            "workspace_id", name=op.f("uq_gtm_theses_workspace_id")
        ),
    )

    op.create_table(
        "gtm_thesis_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thesis_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["thesis_id"],
            ["gtm_theses.id"],
            name=op.f("fk_gtm_thesis_versions_thesis_id_gtm_theses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gtm_thesis_versions")),
        sa.UniqueConstraint(
            "thesis_id",
            "version_number",
            # Hand-named because env.py convention uses column_0_name only,
            # which doesn't disambiguate composite uniques.
            name="uq_gtm_thesis_versions_thesis_id_version_number",
        ),
    )
    op.create_index(
        op.f("ix_gtm_thesis_versions_thesis_id"),
        "gtm_thesis_versions",
        ["thesis_id"],
        unique=False,
    )

    # Now that gtm_thesis_versions exists, add the deferred FK on gtm_theses.
    op.create_foreign_key(
        ACTIVE_VERSION_FK,
        "gtm_theses",
        "gtm_thesis_versions",
        ["active_version_id"],
        ["id"],
    )

    op.create_table(
        "gtm_thesis_sections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("thesis_id", sa.Uuid(), nullable=False),
        sa.Column(
            "section_key", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False),
        sa.Column("is_flagged_incomplete", sa.Boolean(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("last_edited_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["thesis_id"],
            ["gtm_theses.id"],
            name=op.f("fk_gtm_thesis_sections_thesis_id_gtm_theses"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gtm_thesis_sections")),
        sa.UniqueConstraint(
            "thesis_id",
            "section_key",
            name="uq_gtm_thesis_sections_thesis_id_section_key",
        ),
    )
    op.create_index(
        op.f("ix_gtm_thesis_sections_thesis_id"),
        "gtm_thesis_sections",
        ["thesis_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_gtm_thesis_sections_thesis_id"),
        table_name="gtm_thesis_sections",
    )
    op.drop_table("gtm_thesis_sections")

    # Break the cycle before dropping versions.
    op.drop_constraint(ACTIVE_VERSION_FK, "gtm_theses", type_="foreignkey")

    op.drop_index(
        op.f("ix_gtm_thesis_versions_thesis_id"),
        table_name="gtm_thesis_versions",
    )
    op.drop_table("gtm_thesis_versions")

    op.drop_table("gtm_theses")

    sa.Enum(name="thesisstatus").drop(op.get_bind(), checkfirst=False)
