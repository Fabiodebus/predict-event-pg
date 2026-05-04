import inspect

import pytest

from app.orchestration.workflow import WorkflowOrchestrator


def test_workflow_orchestrator_is_abstract():
    with pytest.raises(TypeError):
        WorkflowOrchestrator()  # type: ignore[abstract]


def test_workflow_orchestrator_required_methods():
    methods = {
        name for name, m in inspect.getmembers(WorkflowOrchestrator)
        if getattr(m, "__isabstractmethod__", False)
    }
    assert methods == {"start", "resume", "get_state"}
