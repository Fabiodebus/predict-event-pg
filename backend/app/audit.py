from typing import Any, Literal, get_args
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

EventType = Literal[
    "state_transition", "send_action", "approval_change", "evidence_mutation"
]
_VALID_EVENT_TYPES: frozenset[str] = frozenset(get_args(EventType))


async def write_audit_log(
    db: AsyncSession,
    event_type: EventType,
    actor_id: UUID,
    resource_id: UUID,
    resource_type: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> None:
    """Insert an audit row and flush.

    The row is added to the session and flushed so DB-level errors (FK,
    NOT NULL, etc.) surface immediately — but the transaction is NOT
    committed. The caller MUST commit in the same transaction as the
    domain change so the audit row and the change land atomically. If
    the caller's transaction rolls back, the audit row rolls back too.

    Immutability is by convention — there is no DB-level guard against
    UPDATE or DELETE on this table. A follow-up should grant
    INSERT-only privileges to the application role.
    """
    if event_type not in _VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type!r}")
    entry = AuditLog(
        event_type=event_type,
        actor_id=actor_id,
        resource_id=resource_id,
        resource_type=resource_type,
        before=before,
        after=after,
    )
    db.add(entry)
    await db.flush()
