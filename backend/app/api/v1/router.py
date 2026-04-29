from fastapi import APIRouter

from app.api.v1.common.router import router as common_router

router = APIRouter(prefix="/api/v1")
router.include_router(common_router, tags=["common"])
