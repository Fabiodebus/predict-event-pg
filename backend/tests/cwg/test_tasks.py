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
