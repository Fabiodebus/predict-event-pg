"""workflow_runs and job idempotency

Revision ID: b2c4f7e8a1d3
Revises: a1b2c3d4e5f6
Create Date: 2026-05-04 08:54:28.713499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "b2c4f7e8a1d3"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "IN_PROGRESS", "AWAITING_APPROVAL",
                "ESCALATED", "COMPLETED", "FAILED",
                name="workflowrunstatus",
            ),
            nullable=False,
        ),
        sa.Column("current_node", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("iteration_count", sa.Integer(), nullable=False),
        sa.Column("max_iteration_count", sa.Integer(), nullable=False),
        sa.Column("acceptance_threshold", sa.Float(), nullable=False),
        sa.Column("escalated", sa.Boolean(), nullable=False),
        sa.Column("escalation_reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("error", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_runs_workspace_id"),
        "workflow_runs",
        ["workspace_id"],
        unique=False,
    )

    op.add_column(
        "jobs",
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "idempotency_key",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
    )
    op.add_column(
        "jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("jobs", "attempt_count", server_default=None)

    op.create_foreign_key(
        "fk_jobs_workflow_run_id",
        "jobs",
        "workflow_runs",
        ["workflow_run_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_jobs_workflow_run_id"), "jobs", ["workflow_run_id"], unique=False
    )
    op.create_index(
        op.f("ix_jobs_idempotency_key"),
        "jobs",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_idempotency_key"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_workflow_run_id"), table_name="jobs")
    op.drop_constraint("fk_jobs_workflow_run_id", "jobs", type_="foreignkey")
    op.drop_column("jobs", "attempt_count")
    op.drop_column("jobs", "idempotency_key")
    op.drop_column("jobs", "workflow_run_id")

    op.drop_index(op.f("ix_workflow_runs_workspace_id"), table_name="workflow_runs")
    op.drop_table("workflow_runs")
    sa.Enum(name="workflowrunstatus").drop(op.get_bind(), checkfirst=False)
