"""Unit tests for the checkpointer lifetime singleton.

We don't run a real Postgres in CI; instead we stub
AsyncPostgresSaver.from_conn_string with a fake async context manager that
yields a stub object. The tests verify the module's caching, lock-protected
init, and shutdown semantics — not the underlying psycopg connection.
"""

from __future__ import annotations

import asyncio
import contextlib

import pytest

import app.orchestration.checkpointer as checkpointer_module


class _StubSaver:
    def __init__(self, name: str = "stub") -> None:
        self.name = name
        self.setup_calls = 0

    async def setup(self) -> None:
        self.setup_calls += 1


@pytest.fixture
def stub_saver(monkeypatch):
    """Replace AsyncPostgresSaver.from_conn_string with a stubbed async CM."""
    saver = _StubSaver()
    instances: list[_StubSaver] = []

    @contextlib.asynccontextmanager
    async def _fake_from_conn_string(_dsn: str):
        instances.append(saver)
        yield saver

    monkeypatch.setattr(
        checkpointer_module.AsyncPostgresSaver,
        "from_conn_string",
        _fake_from_conn_string,
    )

    return saver, instances


@pytest.fixture(autouse=True)
async def _reset_module_state():
    yield
    # Always clean up the module singleton between tests so ordering doesn't
    # leak state.
    await checkpointer_module.shutdown_checkpointer()


async def test_get_checkpointer_returns_singleton_after_setup(stub_saver):
    saver, instances = stub_saver
    first = await checkpointer_module.get_checkpointer()
    second = await checkpointer_module.get_checkpointer()

    assert first is saver
    assert second is saver
    assert saver.setup_calls == 1
    assert len(instances) == 1


async def test_concurrent_first_calls_only_setup_once(stub_saver):
    saver, _ = stub_saver
    results = await asyncio.gather(
        checkpointer_module.get_checkpointer(),
        checkpointer_module.get_checkpointer(),
        checkpointer_module.get_checkpointer(),
    )
    assert all(r is saver for r in results)
    assert saver.setup_calls == 1


async def test_shutdown_clears_singleton(stub_saver):
    saver, _ = stub_saver
    await checkpointer_module.get_checkpointer()
    await checkpointer_module.shutdown_checkpointer()
    # Internal globals must be cleared so the next get_checkpointer reinits.
    assert checkpointer_module._checkpointer is None
    assert checkpointer_module._stack is None

    new = await checkpointer_module.get_checkpointer()
    assert new is saver
    # setup_calls is on the *same* stub instance — ran once before shutdown,
    # once again after. Total: 2.
    assert saver.setup_calls == 2


async def test_setup_failure_does_not_cache(monkeypatch):
    @contextlib.asynccontextmanager
    async def _fake(_dsn: str):
        raise RuntimeError("connection refused")
        yield  # unreachable; satisfies generator contract

    monkeypatch.setattr(
        checkpointer_module.AsyncPostgresSaver, "from_conn_string", _fake
    )

    with pytest.raises(RuntimeError, match="connection refused"):
        await checkpointer_module.get_checkpointer()

    # Failure must not leave a half-initialised stack/saver behind.
    assert checkpointer_module._checkpointer is None
    assert checkpointer_module._stack is None
