from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gtm_thesis import (
    GTMThesis,
    GTMThesisSection,
    GTMThesisVersion,
    ThesisStatus,
)
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


async def _make_thesis(db: AsyncSession) -> GTMThesis:
    ws = await _make_workspace(db)
    t = GTMThesis(workspace_id=ws.id)
    db.add(t)
    await db.flush()
    return t


async def test_gtm_thesis_defaults(db: AsyncSession) -> None:
    t = await _make_thesis(db)
    assert t.status == ThesisStatus.DRAFT
    assert t.active_version_id is None
    assert t.generation_job_id is None


async def test_one_thesis_per_workspace(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    t1 = GTMThesis(workspace_id=ws.id)
    db.add(t1)
    await db.flush()

    t2 = GTMThesis(workspace_id=ws.id)
    db.add(t2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_active_version_id_circular_fk_resolves(db: AsyncSession) -> None:
    """Approval flow: create thesis → snapshot a version → point active_version_id at it."""
    t = await _make_thesis(db)
    v = GTMThesisVersion(
        thesis_id=t.id,
        version_number=1,
        sections={"icp_best_fit_profile": {"text": "..."}},
    )
    db.add(v)
    await db.flush()

    t.active_version_id = v.id
    t.status = ThesisStatus.APPROVED
    await db.flush()
    await db.refresh(t)
    assert t.active_version_id == v.id
    assert t.status == ThesisStatus.APPROVED


async def test_version_number_unique_per_thesis(db: AsyncSession) -> None:
    t = await _make_thesis(db)
    v1 = GTMThesisVersion(thesis_id=t.id, version_number=1, sections={})
    db.add(v1)
    await db.flush()

    v2 = GTMThesisVersion(thesis_id=t.id, version_number=1, sections={})
    db.add(v2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_two_theses_can_share_version_number(db: AsyncSession) -> None:
    """Composite unique is on (thesis_id, version_number), not version_number alone."""
    t1 = await _make_thesis(db)
    t2 = await _make_thesis(db)
    db.add(GTMThesisVersion(thesis_id=t1.id, version_number=1, sections={}))
    db.add(GTMThesisVersion(thesis_id=t2.id, version_number=1, sections={}))
    await db.flush()  # no IntegrityError


async def test_section_key_unique_per_thesis(db: AsyncSession) -> None:
    t = await _make_thesis(db)
    s1 = GTMThesisSection(
        thesis_id=t.id, section_key="icp_best_fit_profile", content={"v": 1}
    )
    db.add(s1)
    await db.flush()

    s2 = GTMThesisSection(
        thesis_id=t.id, section_key="icp_best_fit_profile", content={"v": 2}
    )
    db.add(s2)
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_section_defaults(db: AsyncSession) -> None:
    t = await _make_thesis(db)
    s = GTMThesisSection(
        thesis_id=t.id, section_key="personas", content={"items": []}
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)

    assert s.is_ai_generated is True
    assert s.is_flagged_incomplete is False
    assert s.accepted_at is None
    assert s.last_edited_at is None


async def test_version_sections_jsonb_roundtrip(db: AsyncSession) -> None:
    """The version snapshot is a complete JSONB blob of all sections."""
    t = await _make_thesis(db)
    snapshot = {
        "icp_best_fit_profile": {"summary": "B2B SaaS, 50-500 employees"},
        "personas": [{"name": "VP Eng"}, {"name": "Head of Data"}],
        "messaging_style_and_guardrails": {"tone": "direct"},
    }
    v = GTMThesisVersion(thesis_id=t.id, version_number=1, sections=snapshot)
    db.add(v)
    await db.flush()
    await db.refresh(v)
    assert v.sections == snapshot
