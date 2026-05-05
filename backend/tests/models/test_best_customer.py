from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.best_customer import BestCustomer, EnrichmentStatus
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


async def test_best_customer_defaults(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id, company_name="Acme")
    db.add(bc)
    await db.flush()
    await db.refresh(bc)

    assert bc.enrichment_status == EnrichmentStatus.PENDING
    assert bc.is_confirmed is False
    assert bc.industry is None
    assert bc.employee_count is None


async def test_best_customer_status_transitions(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id, domain="acme.example")
    db.add(bc)
    await db.flush()

    bc.enrichment_status = EnrichmentStatus.ENRICHED
    bc.industry = "SaaS"
    bc.employee_count = 250
    bc.hq_country = "US"
    await db.flush()
    await db.refresh(bc)
    assert bc.enrichment_status == EnrichmentStatus.ENRICHED
    assert bc.industry == "SaaS"


async def test_best_customer_workspace_fk_required(db: AsyncSession) -> None:
    bc = BestCustomer(workspace_id=uuid4(), company_name="Orphan")
    db.add(bc)
    with pytest.raises(IntegrityError):
        await db.flush()
