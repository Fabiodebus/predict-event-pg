import uuid as _uuid
from uuid import uuid4

import httpx
import pytest_asyncio
from httpx import ASGITransport

from app.db.session import get_db
from app.dependencies import UserContext, get_current_user
from app.main import app
from app.models.job import Job, JobStatus

_TEST_WORKSPACE_ID = _uuid.uuid4()


def _override_user() -> UserContext:
    return UserContext(
        user_id=uuid4(),
        workspace_id=_TEST_WORKSPACE_ID,
        email="user@example.com",
        role="customer",
    )


@pytest_asyncio.fixture
async def client(db):
    """Async HTTP client. We use httpx.AsyncClient + ASGITransport instead of
    fastapi.TestClient because TestClient uses anyio's portal which spins up
    its own event loop — that mismatches with the asyncpg connection backing
    the `db` fixture, producing 'Future attached to a different loop' errors.
    """

    async def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def test_get_job_status_returns_job(client, db):
    job = Job(workspace_id=_TEST_WORKSPACE_ID, task_type="gtm_thesis", status=JobStatus.IN_PROGRESS)
    db.add(job)
    await db.flush()
    job_id = job.id

    response = await client.get(f"/api/v1/agents/jobs/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == str(job_id)
    assert body["status"] == "in_progress"
    assert body["task_type"] == "gtm_thesis"
    assert body["result"] is None
    assert body["error"] is None
    assert "created_at" in body
    assert "updated_at" in body


async def test_get_job_status_404_for_missing(client):
    response = await client.get(f"/api/v1/agents/jobs/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "HTTP_ERROR"


async def test_get_job_status_404_when_workspace_does_not_match(client, db):
    """Even if the job exists, a user in a different workspace gets 404."""
    other_workspace = _uuid.uuid4()
    job = Job(workspace_id=other_workspace, task_type="gtm_thesis")
    db.add(job)
    await db.flush()
    job_id = job.id

    response = await client.get(f"/api/v1/agents/jobs/{job_id}")
    assert response.status_code == 404


async def test_get_job_status_invalid_uuid_returns_422(client):
    response = await client.get("/api/v1/agents/jobs/not-a-uuid")
    assert response.status_code == 422


async def test_get_job_status_requires_auth(db):
    """Without an Authorization header the endpoint must reject with 401 —
    locks in that get_current_user is actually wired. (No get_current_user
    override here, only get_db.)"""

    async def _get_db_override():
        yield db

    app.dependency_overrides[get_db] = _get_db_override
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/agents/jobs/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
