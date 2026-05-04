from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import WorkflowRun, WorkflowRunStatus
from app.orchestration.policy import EscalationPolicy
from app.orchestration.workflow import WorkflowOrchestrator
from app.repositories.workflow import WorkflowRunRepository

GraphBuilder = Callable[[], StateGraph]
SessionFactory = Callable[[], AsyncSession]


class LangGraphOrchestrator(WorkflowOrchestrator):
    """LangGraph implementation of WorkflowOrchestrator.

    Each `start()` creates a WorkflowRun, compiles the graph with the supplied
    checkpointer, and runs to completion (or to a human-in-the-loop interrupt).
    Escalation is enforced when the final state's `score` (0..1) is below the
    policy's threshold and iteration_count has hit max.
    """

    def __init__(
        self,
        *,
        graph_builder: GraphBuilder,
        checkpointer: BaseCheckpointSaver,
        session_factory: SessionFactory,
    ) -> None:
        self._builder = graph_builder
        self._checkpointer = checkpointer
        self._session_factory = session_factory

    async def start(
        self,
        *,
        workspace_id: UUID,
        workflow_type: str,
        initial_state: dict[str, Any],
        policy: EscalationPolicy,
    ) -> UUID:
        session = self._session_factory()
        repo = WorkflowRunRepository(session)
        wr = await repo.create(
            WorkflowRun(
                workspace_id=workspace_id,
                workflow_type=workflow_type,
                status=WorkflowRunStatus.IN_PROGRESS,
                max_iteration_count=policy.max_iteration_count,
                acceptance_threshold=policy.acceptance_threshold,
            )
        )

        graph = self._builder().compile(checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": str(wr.id)}}
        try:
            final_state = await graph.ainvoke(initial_state, config=config)
        except Exception as exc:
            wr.status = WorkflowRunStatus.FAILED
            wr.error = f"{type(exc).__name__}: {exc}"
            await repo.update(wr)
            raise

        final_dict = dict(final_state)
        wr.iteration_count += 1
        wr.state = final_dict
        wr.current_node = None  # graph ran to END; no pause point
        score = float(final_dict.get("score", 0.0))
        if policy.should_escalate(iteration_count=wr.iteration_count, score=score):
            wr.escalated = True
            wr.status = WorkflowRunStatus.ESCALATED
            wr.escalation_reason = (
                f"score {score} below threshold {policy.acceptance_threshold} "
                f"after {wr.iteration_count} iteration(s)"
            )
        else:
            wr.status = WorkflowRunStatus.COMPLETED
        await repo.update(wr)
        return wr.id

    async def resume(self, *, workflow_run_id: UUID, decision: dict[str, Any]) -> None:
        graph = self._builder().compile(checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": str(workflow_run_id)}}
        await graph.ainvoke(decision, config=config)

    async def get_state(self, *, workflow_run_id: UUID) -> dict[str, Any]:
        graph = self._builder().compile(checkpointer=self._checkpointer)
        config = {"configurable": {"thread_id": str(workflow_run_id)}}
        snapshot = await graph.aget_state(config)
        return dict(snapshot.values)
