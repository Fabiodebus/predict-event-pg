import enum
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class ContentType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TEXT = "text"


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    FAILED = "failed"


class SalesMarketingMaterial(SQLModel, table=True):
    __tablename__ = "sales_marketing_materials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    file_name: str | None = None
    s3_key: str | None = None
    content_type: ContentType
    raw_text: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    extracted_content: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
