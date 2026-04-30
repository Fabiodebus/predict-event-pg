from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import UserContext, get_current_user
from app.models.job import JobStatus
from app.repositories.job import JobRepository

router = APIRouter()


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    task_type: str
    result: dict | None
    error: str | None
    created_at: datetime
    updated_at: datetime


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
) -> JobStatusResponse:
    repo = JobRepository(db)
    job = await repo.get(job_id)
    if job is None or job.workspace_id != user.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        task_type=job.task_type,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
