"""workspace children: personas, best_customers, sales_marketing_materials, target_markets

Revision ID: 79d93bd1105b
Revises: b92a4058efa8
Create Date: 2026-05-05 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = "79d93bd1105b"
down_revision: Union[str, None] = "b92a4058efa8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "personas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("job_title_patterns", sa.JSON(), nullable=False),
        sa.Column("function", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "seniority_level", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("priority_rank", sa.Integer(), nullable=False),
        sa.Column("event_context_behavior", sa.JSON(), nullable=False),
        sa.Column("is_ai_suggested", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_personas_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_personas")),
    )
    op.create_index(
        op.f("ix_personas_workspace_id"), "personas", ["workspace_id"], unique=False
    )

    op.create_table(
        "best_customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column(
            "company_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("domain", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("linkedin_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("industry", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("employee_count", sa.Integer(), nullable=True),
        sa.Column("hq_country", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "enrichment_status",
            sa.Enum("PENDING", "ENRICHED", "FAILED", name="enrichmentstatus"),
            nullable=False,
        ),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_best_customers_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_best_customers")),
    )
    op.create_index(
        op.f("ix_best_customers_workspace_id"),
        "best_customers",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "sales_marketing_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("s3_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "content_type",
            sa.Enum("PDF", "DOCX", "PPTX", "TEXT", name="contenttype"),
            nullable=False,
        ),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_content", sa.JSON(), nullable=True),
        sa.Column(
            "extraction_status",
            sa.Enum("PENDING", "EXTRACTED", "FAILED", name="extractionstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_sales_marketing_materials_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sales_marketing_materials")),
    )
    op.create_index(
        op.f("ix_sales_marketing_materials_workspace_id"),
        "sales_marketing_materials",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "target_markets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("target_industries", sa.JSON(), nullable=False),
        sa.Column("company_size_ranges", sa.JSON(), nullable=False),
        sa.Column("target_regions", sa.JSON(), nullable=False),
        sa.Column("excluded_company_types", sa.JSON(), nullable=False),
        sa.Column(
            "default_proximity_preference",
            sa.Enum(
                "SAME_CITY",
                "SAME_REGION",
                "SAME_COUNTRY",
                "RADIUS",
                name="proximitypreference",
            ),
            nullable=False,
        ),
        sa.Column("default_radius_km", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_target_markets_workspace_id_workspaces"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_target_markets")),
        sa.UniqueConstraint(
            "workspace_id", name=op.f("uq_target_markets_workspace_id")
        ),
    )


def downgrade() -> None:
    op.drop_table("target_markets")

    op.drop_index(
        op.f("ix_sales_marketing_materials_workspace_id"),
        table_name="sales_marketing_materials",
    )
    op.drop_table("sales_marketing_materials")

    op.drop_index(
        op.f("ix_best_customers_workspace_id"), table_name="best_customers"
    )
    op.drop_table("best_customers")

    op.drop_index(op.f("ix_personas_workspace_id"), table_name="personas")
    op.drop_table("personas")

    bind = op.get_bind()
    sa.Enum(name="proximitypreference").drop(bind, checkfirst=False)
    sa.Enum(name="extractionstatus").drop(bind, checkfirst=False)
    sa.Enum(name="contenttype").drop(bind, checkfirst=False)
    sa.Enum(name="enrichmentstatus").drop(bind, checkfirst=False)
