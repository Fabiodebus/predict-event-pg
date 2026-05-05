from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace


async def test_workspace_defaults(db: AsyncSession) -> None:
    ws = Workspace(
        customer_id=uuid4(),
        company_name="Acme Corp",
        primary_domain="acme.example",
    )
    db.add(ws)
    await db.flush()
    await db.refresh(ws)

    assert ws.id is not None
    assert ws.onboarding_state is None
    assert ws.created_at is not None
    assert ws.updated_at is not None


async def test_workspace_primary_domain_is_unique(db: AsyncSession) -> None:
    ws1 = Workspace(
        customer_id=uuid4(),
        company_name="Acme",
        primary_domain="dup.example",
    )
    db.add(ws1)
    await db.flush()

    ws2 = Workspace(
        customer_id=uuid4(),
        company_name="Other",
        primary_domain="dup.example",
    )
    db.add(ws2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_workspace_onboarding_state_jsonb_roundtrip(db: AsyncSession) -> None:
    state = {
        "currentStep": "best_customers",
        "completedSteps": ["company_setup"],
        "canGenerate": False,
    }
    ws = Workspace(
        customer_id=uuid4(),
        company_name="JSON Co",
        primary_domain="json.example",
        onboarding_state=state,
    )
    db.add(ws)
    await db.flush()
    await db.refresh(ws)

    assert ws.onboarding_state == state


async def test_workspace_onboarding_state_replace_semantics(db: AsyncSession) -> None:
    """PATCH /onboarding-state replaces (no merge). Verify the ORM stores by reference."""
    ws = Workspace(
        customer_id=uuid4(),
        company_name="Replace Co",
        primary_domain="replace.example",
        onboarding_state={"currentStep": "company_setup", "completedSteps": []},
    )
    db.add(ws)
    await db.flush()

    ws.onboarding_state = {"currentStep": "personas", "completedSteps": ["a", "b"]}
    await db.flush()
    await db.refresh(ws)
    assert ws.onboarding_state == {
        "currentStep": "personas",
        "completedSteps": ["a", "b"],
    }


async def test_workspace_customer_id_indexed_but_not_unique(db: AsyncSession) -> None:
    """Customer can have multiple workspaces (no unique on customer_id)."""
    cid = uuid4()
    ws1 = Workspace(
        customer_id=cid, company_name="W1", primary_domain="w1.example"
    )
    ws2 = Workspace(
        customer_id=cid, company_name="W2", primary_domain="w2.example"
    )
    db.add(ws1)
    db.add(ws2)
    await db.flush()
