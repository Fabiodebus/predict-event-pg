from uuid import uuid4

import pytest
from sqlalchemy import select

from app.audit import write_audit_log
from app.models.audit import AuditLog


async def test_write_audit_log_creates_row(db):
    actor = uuid4()
    resource = uuid4()
    await write_audit_log(
        db=db,
        event_type="state_transition",
        actor_id=actor,
        resource_id=resource,
        resource_type="job",
        before={"status": "pending"},
        after={"status": "in_progress"},
    )
    await db.flush()

    rows = (await db.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.event_type == "state_transition"
    assert row.actor_id == actor
    assert row.resource_id == resource
    assert row.resource_type == "job"
    assert row.before == {"status": "pending"}
    assert row.after == {"status": "in_progress"}
    assert row.created_at is not None


async def test_write_audit_log_accepts_null_before(db):
    await write_audit_log(
        db=db,
        event_type="evidence_mutation",
        actor_id=uuid4(),
        resource_id=uuid4(),
        resource_type="evidence",
        before=None,
        after={"value": "new"},
    )
    await db.flush()
    rows = (await db.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].before is None


async def test_write_audit_log_rejects_invalid_event_type(db):
    with pytest.raises(ValueError):
        await write_audit_log(
            db=db,
            event_type="bogus_event",  # type: ignore[arg-type]
            actor_id=uuid4(),
            resource_id=uuid4(),
            resource_type="job",
            before=None,
            after=None,
        )
