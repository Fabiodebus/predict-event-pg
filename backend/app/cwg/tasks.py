"""CWG (Customer Workspace & GTM Thesis) Celery tasks.

Auto-discovered by app.celery_app via celery_app.autodiscover_tasks(["app.cwg"]).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import Task

from app.celery_app import celery_app
from app.config import settings
from app.integrations.crustdata import CrustdataClient
from app.models.best_customer import BestCustomer, EnrichmentStatus
from app.tasks.base import IdempotentTask, _open_session

logger = logging.getLogger(__name__)


# Task-level retries are disabled because BaseIntegrationClient already retries
# transient 5xx via tenacity, and the BC.enrichment_status field is the source
# of truth for business-level success/failure (orthogonal to Job lifecycle).
@celery_app.task(
    bind=True,
    base=IdempotentTask,
    name="app.cwg.enrich_best_customer",
    autoretry_for=(),
    max_retries=0,
)
def enrich_best_customer(self: Task, *, best_customer_id: str) -> dict[str, Any]:
    """Enrich a single BestCustomer entry via Crustdata.

    Reads the BestCustomer, picks the best identifier (LinkedIn URL > domain >
    company_name), calls Crustdata's screener, and writes industry /
    employee_count / hq_country back. Sets enrichment_status to enriched on
    success, failed on any of: no identifier present, no Crustdata match,
    Crustdata error after retries.
    """
    return asyncio.run(_run_enrich_best_customer(UUID(best_customer_id)))


def _select_identifier(bc: BestCustomer) -> tuple[str, str] | None:
    """Identifier preference: LinkedIn URL > domain > company_name.

    Returns (kwarg_name_for_screener_company, identifier_value) or None.
    """
    if bc.linkedin_url:
        return ("company_linkedin_urls", bc.linkedin_url)
    if bc.domain:
        return ("company_domains", bc.domain)
    if bc.company_name:
        return ("company_names", bc.company_name)
    return None


def _extract_industry(profile: dict[str, Any]) -> str | None:
    industries = profile.get("linkedin_industries") or []
    if isinstance(industries, list) and industries:
        return industries[0]
    # Fallback: some Crustdata responses use the `industry` field directly.
    industry = profile.get("industry")
    return industry if isinstance(industry, str) else None


def _extract_employee_count(profile: dict[str, Any]) -> int | None:
    headcount = profile.get("headcount")
    if isinstance(headcount, dict):
        latest = headcount.get("latest_count")
        if isinstance(latest, int):
            return latest
    return None


async def _run_enrich_best_customer(best_customer_id: UUID) -> dict[str, Any]:
    async with _open_session() as session:
        bc = await session.get(BestCustomer, best_customer_id)
        if bc is None:
            return {"status": "skipped", "reason": "best_customer_not_found"}

        identifier = _select_identifier(bc)
        if identifier is None:
            bc.enrichment_status = EnrichmentStatus.FAILED
            await session.commit()
            return {"status": "failed", "reason": "no_identifier"}

        client = CrustdataClient(api_key=settings.crustdata_api_key)
        kwarg_name, value = identifier
        try:
            profiles = await client.screener_company(**{kwarg_name: [value]})
        except Exception as exc:
            bc.enrichment_status = EnrichmentStatus.FAILED
            await session.commit()
            logger.exception(
                "crustdata enrichment failed for best_customer_id=%s",
                best_customer_id,
            )
            return {"status": "failed", "reason": f"crustdata_error: {type(exc).__name__}"}

        profile = profiles[0] if profiles else None
        if profile is None:
            bc.enrichment_status = EnrichmentStatus.FAILED
            await session.commit()
            return {"status": "failed", "reason": "no_match"}

        bc.industry = _extract_industry(profile)
        bc.employee_count = _extract_employee_count(profile)
        bc.hq_country = profile.get("hq_country")
        bc.enrichment_status = EnrichmentStatus.ENRICHED
        await session.commit()
        return {"status": "ok"}
