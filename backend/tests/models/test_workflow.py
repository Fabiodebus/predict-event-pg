from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowRun, WorkflowRunStatus


async def test_workflow_run_defaults(db: AsyncSession) -> None:
    wr = WorkflowRun(
        workspace_id=uuid4(),
        workflow_type="gtm_thesis",
        max_iteration_count=2,
        acceptance_threshold=0.8,
    )
    db.add(wr)
    await db.flush()
    await db.refresh(wr)

    assert wr.status == WorkflowRunStatus.PENDING
    assert wr.iteration_count == 0
    assert wr.escalated is False
    assert wr.current_node is None
    assert wr.escalation_reason is None
    assert wr.id is not None


async def test_workflow_run_status_transitions(db: AsyncSession) -> None:
    wr = WorkflowRun(
        workspace_id=uuid4(),
        workflow_type="enrichment",
        max_iteration_count=2,
        acceptance_threshold=0.7,
    )
    db.add(wr)
    await db.flush()
    wr.status = WorkflowRunStatus.IN_PROGRESS
    wr.current_node = "research_sources"
    await db.flush()
    await db.refresh(wr)

    assert wr.status == WorkflowRunStatus.IN_PROGRESS
    assert wr.current_node == "research_sources"
