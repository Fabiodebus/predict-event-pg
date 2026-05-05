from fastapi import APIRouter

from app.api.v1.agents.router import router as agents_router
from app.api.v1.common.router import router as common_router
from app.api.v1.enrichment.router import router as enrichment_router
from app.api.v1.events.router import router as events_router
from app.api.v1.outreach.router import router as outreach_router
from app.api.v1.workspace.router import router as workspace_router

router = APIRouter(prefix="/api/v1")
router.include_router(common_router, tags=["common"])
router.include_router(agents_router, prefix="/agents", tags=["agents"])
router.include_router(workspace_router, prefix="/workspace", tags=["workspace"])
router.include_router(events_router, prefix="/events", tags=["events"])
router.include_router(enrichment_router, prefix="/enrichment", tags=["enrichment"])
router.include_router(outreach_router, prefix="/outreach", tags=["outreach"])
