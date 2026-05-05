import enum
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class ProximityPreference(str, enum.Enum):
    SAME_CITY = "same_city"
    SAME_REGION = "same_region"
    SAME_COUNTRY = "same_country"
    RADIUS = "radius"


class TargetMarket(SQLModel, table=True):
    __tablename__ = "target_markets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", unique=True)
    target_industries: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    company_size_ranges: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    target_regions: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    excluded_company_types: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    default_proximity_preference: ProximityPreference = ProximityPreference.SAME_REGION
    default_radius_km: int | None = None
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
