from __future__ import annotations

import abc
from typing import Any


class AgentOrchestrator(abc.ABC):
    """Hook surface for external agent orchestrators (e.g. Hermes).

    Adapters register a `name` and implement `dispatch()`. The workflow
    layer resolves orchestrators from the registry without knowing their
    concrete identity.
    """

    name: str

    @abc.abstractmethod
    async def dispatch(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Hand a task spec to the underlying orchestrator and return its result."""


class AgentRegistry:
    def __init__(self) -> None:
        self._orchestrators: dict[str, AgentOrchestrator] = {}

    def register(self, orchestrator: AgentOrchestrator) -> None:
        if orchestrator.name in self._orchestrators:
            raise ValueError(f"orchestrator {orchestrator.name!r} already registered")
        self._orchestrators[orchestrator.name] = orchestrator

    def get(self, name: str) -> AgentOrchestrator:
        try:
            return self._orchestrators[name]
        except KeyError as exc:
            raise KeyError(f"unknown orchestrator: {name!r}") from exc
