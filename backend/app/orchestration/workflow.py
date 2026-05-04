from __future__ import annotations

import abc
from typing import Any
from uuid import UUID

from app.orchestration.policy import EscalationPolicy


class WorkflowOrchestrator(abc.ABC):
    """Contract for stateful, multi-step workflows.

    LangGraph is one implementation. Simple Celery tasks may bypass this
    interface entirely when state and branching are not required.
    """

    @abc.abstractmethod
    async def start(
        self,
        *,
        workspace_id: UUID,
        workflow_type: str,
        initial_state: dict[str, Any],
        policy: EscalationPolicy,
    ) -> UUID:
        """Begin a workflow. Returns the WorkflowRun.id (used as thread_id)."""

    @abc.abstractmethod
    async def resume(self, *, workflow_run_id: UUID, decision: dict[str, Any]) -> None:
        """Resume a paused workflow with a human-in-the-loop decision."""

    @abc.abstractmethod
    async def get_state(self, *, workflow_run_id: UUID) -> dict[str, Any]:
        """Return the latest checkpointed state for the workflow."""
