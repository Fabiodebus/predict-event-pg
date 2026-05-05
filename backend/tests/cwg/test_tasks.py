from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
import respx
from sqlalchemy.ext.asyncio import AsyncSession

import app.tasks.base as task_base
from app.cwg.tasks import _run_enrich_best_customer
from app.models.best_customer import BestCustomer, EnrichmentStatus
from app.models.workspace import Workspace


@pytest.fixture(autouse=True)
def _stub_session_factory(monkeypatch, db: AsyncSession):
    @asynccontextmanager
    async def _ctx():
        yield db

    monkeypatch.setattr(task_base, "_open_session", _ctx)
    # The task body imports _open_session directly from task_base, so the
    # patch above propagates.

    _orig_refresh = db.refresh

    async def _refresh_with_flush(instance, **kwargs):
        await db.flush()
        return await _orig_refresh(instance, **kwargs)

    monkeypatch.setattr(db, "refresh", _refresh_with_flush)


async def _make_workspace(db: AsyncSession) -> Workspace:
    ws = Workspace(
        customer_id=uuid4(),
        company_name="Co",
        primary_domain=f"{uuid4().hex}.example",
    )
    db.add(ws)
    await db.flush()
    return ws


def _crustdata_profile(**overrides) -> dict:
    return {
        "company_name": "Acme",
        "company_website_domain": "acme.example",
        "hq_country": "United States",
        "linkedin_industries": ["Computer Software"],
        "headcount": {"latest_count": 250},
        **overrides,
    }


@respx.mock
async def test_enrich_writes_industry_employee_count_country(db: AsyncSession):
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id, domain="acme.example")
    db.add(bc)
    await db.flush()

    respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[_crustdata_profile()])
    )

    result = await _run_enrich_best_customer(bc.id)
    await db.refresh(bc)

    assert result["status"] == "ok"
    assert bc.enrichment_status == EnrichmentStatus.ENRICHED
    assert bc.industry == "Computer Software"
    assert bc.employee_count == 250
    assert bc.hq_country == "United States"


@respx.mock
async def test_enrich_marks_failed_on_no_match(db: AsyncSession):
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id, domain="ghost.example")
    db.add(bc)
    await db.flush()

    respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[])
    )

    result = await _run_enrich_best_customer(bc.id)
    await db.refresh(bc)
    assert result["status"] == "failed"
    assert result["reason"] == "no_match"
    assert bc.enrichment_status == EnrichmentStatus.FAILED


async def test_enrich_marks_failed_when_no_identifier(db: AsyncSession):
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id)  # no domain, no LinkedIn, no name
    db.add(bc)
    await db.flush()

    result = await _run_enrich_best_customer(bc.id)
    await db.refresh(bc)
    assert result["status"] == "failed"
    assert result["reason"] == "no_identifier"
    assert bc.enrichment_status == EnrichmentStatus.FAILED


@respx.mock
async def test_enrich_marks_failed_on_crustdata_5xx(db: AsyncSession):
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id, domain="bad.example")
    db.add(bc)
    await db.flush()

    # All retry attempts return 503; tenacity inside the client gives up,
    # the task body catches and marks the BC failed without re-raising.
    respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(503)
    )

    result = await _run_enrich_best_customer(bc.id)
    await db.refresh(bc)
    assert result["status"] == "failed"
    assert "crustdata_error" in result["reason"]
    assert bc.enrichment_status == EnrichmentStatus.FAILED


@respx.mock
async def test_enrich_prefers_linkedin_url_over_domain(db: AsyncSession):
    ws = await _make_workspace(db)
    bc = BestCustomer(
        workspace_id=ws.id,
        domain="acme.example",
        linkedin_url="https://linkedin.com/company/acme",
    )
    db.add(bc)
    await db.flush()

    route = respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[_crustdata_profile()])
    )

    await _run_enrich_best_customer(bc.id)

    request = route.calls.last.request
    assert "company_linkedin_url" in request.url.params
    assert "company_domain" not in request.url.params


@respx.mock
async def test_enrich_falls_back_to_company_name(db: AsyncSession):
    ws = await _make_workspace(db)
    bc = BestCustomer(workspace_id=ws.id, company_name="Acme Corp")
    db.add(bc)
    await db.flush()

    route = respx.get("https://api.crustdata.com/screener/company").mock(
        return_value=httpx.Response(200, json=[_crustdata_profile()])
    )

    await _run_enrich_best_customer(bc.id)
    request = route.calls.last.request
    assert request.url.params["company_name"] == "Acme Corp"


async def test_enrich_skips_when_bc_not_found(db: AsyncSession):
    result = await _run_enrich_best_customer(uuid4())
    assert result["status"] == "skipped"


# ---------------------------------------------------------------------------
# Material extraction
# ---------------------------------------------------------------------------


from app.cwg.tasks import (  # noqa: E402
    ExtractedContent,
    _run_extract_material,
)
from app.models.sales_material import (  # noqa: E402
    ContentType,
    ExtractionStatus,
    SalesMarketingMaterial,
)


def _stub_extract_via_llm(monkeypatch, payload: ExtractedContent):
    """Replace the LLM call so the test asserts our wiring, not vendor behaviour."""

    async def _fake(text: str) -> ExtractedContent:
        return payload

    import app.cwg.tasks as cwg_tasks

    monkeypatch.setattr(cwg_tasks, "_extract_via_llm", _fake)


async def test_extract_text_material_persists_extracted_content(
    db: AsyncSession, monkeypatch
):
    ws = await _make_workspace(db)
    m = SalesMarketingMaterial(
        workspace_id=ws.id,
        content_type=ContentType.TEXT,
        raw_text="We help mid-market SaaS teams ship faster. 42% conversion lift at Acme.",
    )
    db.add(m)
    await db.flush()

    payload = ExtractedContent(
        solution_description="Outreach automation for mid-market SaaS",
        proof_points=["42% conversion lift at Acme"],
        use_cases=["B2B sales outbound"],
        customer_references=["Acme"],
        communication_style_indicators=["direct", "metric-led"],
    )
    _stub_extract_via_llm(monkeypatch, payload)

    result = await _run_extract_material(m.id)
    await db.refresh(m)

    assert result["status"] == "ok"
    assert m.extraction_status == ExtractionStatus.EXTRACTED
    assert m.extracted_content == payload.model_dump()


async def test_extract_marks_failed_on_empty_content(db: AsyncSession):
    ws = await _make_workspace(db)
    m = SalesMarketingMaterial(
        workspace_id=ws.id, content_type=ContentType.TEXT, raw_text=""
    )
    db.add(m)
    await db.flush()

    result = await _run_extract_material(m.id)
    await db.refresh(m)
    assert result["status"] == "failed"
    assert result["reason"] == "empty_content"
    assert m.extraction_status == ExtractionStatus.FAILED


async def test_extract_marks_failed_on_llm_invalid_output(
    db: AsyncSession, monkeypatch
):
    ws = await _make_workspace(db)
    m = SalesMarketingMaterial(
        workspace_id=ws.id, content_type=ContentType.TEXT, raw_text="some content"
    )
    db.add(m)
    await db.flush()

    async def _bad(_: str) -> ExtractedContent:
        # Mimic a Pydantic validation failure surfacing from the LLM call.
        from pydantic import ValidationError
        raise ValidationError.from_exception_data(
            "ExtractedContent", line_errors=[]
        )

    import app.cwg.tasks as cwg_tasks

    monkeypatch.setattr(cwg_tasks, "_extract_via_llm", _bad)

    result = await _run_extract_material(m.id)
    await db.refresh(m)
    assert result["status"] == "failed"
    assert result["reason"] == "llm_output_invalid"
    assert m.extraction_status == ExtractionStatus.FAILED


async def test_extract_skips_when_material_not_found():
    result = await _run_extract_material(uuid4())
    assert result["status"] == "skipped"


async def test_extract_marks_failed_on_non_text_without_s3_key(db: AsyncSession):
    ws = await _make_workspace(db)
    m = SalesMarketingMaterial(
        workspace_id=ws.id, content_type=ContentType.PDF, s3_key=None
    )
    db.add(m)
    await db.flush()

    result = await _run_extract_material(m.id)
    await db.refresh(m)
    assert result["status"] == "failed"
    assert "load_error" in result["reason"]
    assert m.extraction_status == ExtractionStatus.FAILED


