from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.target_market import ProximityPreference, TargetMarket
from app.models.workspace import Workspace


async def _make_workspace(db: AsyncSession) -> Workspace:
    ws = Workspace(
        customer_id=uuid4(),
        company_name="Co",
        primary_domain=f"{uuid4().hex}.example",
    )
    db.add(ws)
    await db.flush()
    return ws


async def test_target_market_defaults_with_jsonb_lists(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    tm = TargetMarket(
        workspace_id=ws.id,
        target_industries=["SaaS", "FinTech"],
        company_size_ranges=["50-250", "250-1000"],
        target_regions=["NA", "EU"],
        excluded_company_types=["Government"],
    )
    db.add(tm)
    await db.flush()
    await db.refresh(tm)

    assert tm.default_proximity_preference == ProximityPreference.SAME_REGION
    assert tm.default_radius_km is None
    assert tm.target_industries == ["SaaS", "FinTech"]
    assert tm.excluded_company_types == ["Government"]


async def test_target_market_one_per_workspace(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    tm1 = TargetMarket(workspace_id=ws.id)
    db.add(tm1)
    await db.flush()

    tm2 = TargetMarket(workspace_id=ws.id)
    db.add(tm2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_target_market_radius_preference(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    tm = TargetMarket(
        workspace_id=ws.id,
        default_proximity_preference=ProximityPreference.RADIUS,
        default_radius_km=200,
    )
    db.add(tm)
    await db.flush()
    await db.refresh(tm)
    assert tm.default_proximity_preference == ProximityPreference.RADIUS
    assert tm.default_radius_km == 200


async def test_target_market_workspace_fk_required(db: AsyncSession) -> None:
    tm = TargetMarket(workspace_id=uuid4())
    db.add(tm)
    with pytest.raises(IntegrityError):
        await db.flush()
