from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.persona import Persona
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


async def test_persona_defaults_and_jsonb_roundtrip(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    p = Persona(
        workspace_id=ws.id,
        name="VP Engineering",
        priority_rank=1,
        job_title_patterns=["VP Eng*", "Head of Engineering"],
        event_context_behavior={
            "open_topics": ["scaling", "hiring"],
            "meeting_type": "30min_intro",
        },
    )
    db.add(p)
    await db.flush()
    await db.refresh(p)

    assert p.is_active is True
    assert p.is_ai_suggested is False
    assert p.job_title_patterns == ["VP Eng*", "Head of Engineering"]
    assert p.event_context_behavior["meeting_type"] == "30min_intro"


async def test_persona_workspace_fk_required(db: AsyncSession) -> None:
    p = Persona(
        workspace_id=uuid4(),  # nonexistent workspace
        name="X",
        priority_rank=1,
    )
    db.add(p)
    with pytest.raises(IntegrityError):
        await db.flush()
