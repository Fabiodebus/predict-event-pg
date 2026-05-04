from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from app.models.workflow import WorkflowRunStatus
from app.orchestration.langgraph_orchestrator import LangGraphOrchestrator
from app.orchestration.policy import EscalationPolicy
from app.repositories.workflow import WorkflowRunRepository


class _State(TypedDict):
    value: int
    score: float


def _double(state: _State) -> _State:
    return {"value": state["value"] * 2, "score": state["score"]}


def _build_graph() -> StateGraph:
    g = StateGraph(_State)
    g.add_node("double", _double)
    g.add_edge(START, "double")
    g.add_edge("double", END)
    return g


async def test_start_creates_workflow_run_and_runs_to_completion(db: AsyncSession) -> None:
    workspace_id = uuid4()
    saver = InMemorySaver()
    orch = LangGraphOrchestrator(
        graph_builder=_build_graph,
        checkpointer=saver,
        session_factory=lambda: db,
    )

    run_id = await orch.start(
        workspace_id=workspace_id,
        workflow_type="test_double",
        initial_state={"value": 5, "score": 0.95},
        policy=EscalationPolicy(max_iteration_count=2, acceptance_threshold=0.9),
    )

    fetched = await WorkflowRunRepository(db).get(run_id)
    assert fetched is not None
    assert fetched.workflow_type == "test_double"
    assert fetched.status == WorkflowRunStatus.COMPLETED
    state = await orch.get_state(workflow_run_id=run_id)
    assert state["value"] == 10


def _boom(state: _State) -> _State:
    raise RuntimeError("graph_failure")


def _build_failing_graph() -> StateGraph:
    g = StateGraph(_State)
    g.add_node("boom", _boom)
    g.add_edge(START, "boom")
    g.add_edge("boom", END)
    return g


async def test_failure_marks_workflow_run_failed(db: AsyncSession) -> None:
    workspace_id = uuid4()
    saver = InMemorySaver()
    orch = LangGraphOrchestrator(
        graph_builder=_build_failing_graph,
        checkpointer=saver,
        session_factory=lambda: db,
    )

    with pytest.raises(RuntimeError, match="graph_failure"):
        await orch.start(
            workspace_id=workspace_id,
            workflow_type="test_failure",
            initial_state={"value": 1, "score": 1.0},
            policy=EscalationPolicy(max_iteration_count=2, acceptance_threshold=0.5),
        )

    runs = await WorkflowRunRepository(db).list(workspace_id=workspace_id)
    assert len(runs) == 1
    failed = runs[0]
    assert failed.status == WorkflowRunStatus.FAILED
    assert "graph_failure" in (failed.error or "")


async def test_escalation_when_threshold_not_met(db: AsyncSession) -> None:
    workspace_id = uuid4()
    saver = InMemorySaver()
    orch = LangGraphOrchestrator(
        graph_builder=_build_graph,
        checkpointer=saver,
        session_factory=lambda: db,
    )

    run_id = await orch.start(
        workspace_id=workspace_id,
        workflow_type="test_double",
        initial_state={"value": 1, "score": 0.1},
        policy=EscalationPolicy(max_iteration_count=1, acceptance_threshold=0.9),
    )

    fetched = await WorkflowRunRepository(db).get(run_id)
    assert fetched is not None
    assert fetched.escalated is True
    assert fetched.status == WorkflowRunStatus.ESCALATED
    assert fetched.escalation_reason is not None
