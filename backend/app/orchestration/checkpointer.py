"""Lazy lifetime-scoped AsyncPostgresSaver for LangGraph workflow checkpoints.

The checkpointer holds a long-lived psycopg connection. Construction is
expensive and must run schema setup() once per database. We instantiate
once per process (Celery worker, API server) and reuse for every workflow.

`from_conn_string` is an async context manager (an asynccontextmanager-decorated
async generator). To keep the connection open across many tasks we enter the
context once via an AsyncExitStack and never exit until shutdown.
"""

from __future__ import annotations

import asyncio
import contextlib

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings

_lock = asyncio.Lock()
_stack: contextlib.AsyncExitStack | None = None
_checkpointer: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """Return a process-singleton AsyncPostgresSaver.

    First call enters from_conn_string's context, runs setup() to create
    LangGraph's checkpoint tables (idempotent), and caches the instance.
    Subsequent calls return the cached instance directly.
    """
    global _stack, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    async with _lock:
        # Re-check inside the lock; another coroutine may have initialized.
        if _checkpointer is not None:
            return _checkpointer

        stack = contextlib.AsyncExitStack()
        try:
            saver = await stack.enter_async_context(
                AsyncPostgresSaver.from_conn_string(settings.langgraph_checkpoint_dsn)
            )
            await saver.setup()
        except Exception:
            await stack.aclose()
            raise

        _stack = stack
        _checkpointer = saver
        return _checkpointer


async def shutdown_checkpointer() -> None:
    """Close the underlying connection and clear caches.

    Optional — process exit will reclaim the connection anyway. Useful for
    test isolation and graceful worker shutdown.
    """
    global _stack, _checkpointer
    async with _lock:
        if _stack is not None:
            await _stack.aclose()
        _stack = None
        _checkpointer = None
