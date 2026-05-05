import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class EnrichmentStatus(str, enum.Enum):
    PENDING = "pending"
    ENRICHED = "enriched"
    FAILED = "failed"


class BestCustomer(SQLModel, table=True):
    __tablename__ = "best_customers"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    company_name: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    hq_country: str | None = None
    enrichment_status: EnrichmentStatus = EnrichmentStatus.PENDING
    is_confirmed: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
