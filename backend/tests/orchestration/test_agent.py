import pytest

from app.orchestration.agent import AgentOrchestrator, AgentRegistry


class _FakeOrchestrator(AgentOrchestrator):
    name = "fake"

    async def dispatch(self, spec):  # type: ignore[no-untyped-def]
        return {"echoed": spec}


def test_register_and_resolve():
    registry = AgentRegistry()
    fake = _FakeOrchestrator()
    registry.register(fake)
    assert registry.get("fake") is fake


def test_register_duplicate_raises():
    registry = AgentRegistry()
    registry.register(_FakeOrchestrator())
    with pytest.raises(ValueError):
        registry.register(_FakeOrchestrator())


def test_get_unknown_raises():
    registry = AgentRegistry()
    with pytest.raises(KeyError):
        registry.get("unknown")
