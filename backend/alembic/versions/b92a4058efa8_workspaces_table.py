"""workspaces table

Revision ID: b92a4058efa8
Revises: b2c4f7e8a1d3
Create Date: 2026-05-05 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "b92a4058efa8"
down_revision: Union[str, None] = "b2c4f7e8a1d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "primary_domain", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("onboarding_state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
        sa.UniqueConstraint(
            "primary_domain", name=op.f("uq_workspaces_primary_domain")
        ),
    )
    op.create_index(
        op.f("ix_workspaces_customer_id"), "workspaces", ["customer_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workspaces_customer_id"), table_name="workspaces")
    op.drop_table("workspaces")
