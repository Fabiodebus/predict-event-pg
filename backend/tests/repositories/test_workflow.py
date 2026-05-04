from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowRun, WorkflowRunStatus
from app.repositories.workflow import WorkflowRunRepository


async def test_workflow_run_create_and_get(db: AsyncSession) -> None:
    repo = WorkflowRunRepository(db)
    wr = WorkflowRun(
        workspace_id=uuid4(),
        workflow_type="gtm_thesis",
        max_iteration_count=2,
        acceptance_threshold=0.8,
    )
    created = await repo.create(wr)
    created_id = created.id
    db.expire_all()

    fetched = await repo.get(created_id)
    assert fetched is not None
    assert fetched.workflow_type == "gtm_thesis"
    assert fetched.status == WorkflowRunStatus.PENDING


async def test_workflow_run_list_workspace_scoped(db: AsyncSession) -> None:
    repo = WorkflowRunRepository(db)
    ws1 = uuid4()
    ws2 = uuid4()

    a = await repo.create(
        WorkflowRun(
            workspace_id=ws1, workflow_type="x",
            max_iteration_count=2, acceptance_threshold=0.5,
        )
    )
    await repo.create(
        WorkflowRun(
            workspace_id=ws2, workflow_type="x",
            max_iteration_count=2, acceptance_threshold=0.5,
        )
    )

    results = await repo.list(workspace_id=ws1)
    assert [r.id for r in results] == [a.id]
