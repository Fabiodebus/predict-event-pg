from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales_material import (
    ContentType,
    ExtractionStatus,
    SalesMarketingMaterial,
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


async def test_sales_material_defaults(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    m = SalesMarketingMaterial(
        workspace_id=ws.id,
        file_name="deck.pdf",
        s3_key="workspaces/x/deck.pdf",
        content_type=ContentType.PDF,
    )
    db.add(m)
    await db.flush()
    await db.refresh(m)

    assert m.extraction_status == ExtractionStatus.PENDING
    assert m.raw_text is None
    assert m.extracted_content is None


async def test_sales_material_text_content(db: AsyncSession) -> None:
    ws = await _make_workspace(db)
    m = SalesMarketingMaterial(
        workspace_id=ws.id,
        content_type=ContentType.TEXT,
        raw_text="We help B2B companies streamline outreach...",
    )
    db.add(m)
    await db.flush()

    m.extraction_status = ExtractionStatus.EXTRACTED
    m.extracted_content = {
        "solution": "outreach automation",
        "proof_points": ["20% conversion lift"],
    }
    await db.flush()
    await db.refresh(m)
    assert m.extraction_status == ExtractionStatus.EXTRACTED
    assert m.extracted_content["solution"] == "outreach automation"


async def test_sales_material_workspace_fk_required(db: AsyncSession) -> None:
    m = SalesMarketingMaterial(
        workspace_id=uuid4(),
        content_type=ContentType.TEXT,
        raw_text="orphan",
    )
    db.add(m)
    with pytest.raises(IntegrityError):
        await db.flush()
