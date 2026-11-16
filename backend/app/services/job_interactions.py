from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.job_interaction import JobInteraction


async def update_interaction(db, user_id: int, job_id: int, *, seen=None, marked=None) -> dict:
    """Atomic updates preserve a bookmark when recording a simultaneous click."""
    now = datetime.now(UTC)
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    changes = {}
    if seen is not None:
        changes["seen_at"] = func.coalesce(JobInteraction.seen_at, now) if seen else None
    if marked is not None:
        changes["marked"] = marked
        changes["marked_at"] = func.coalesce(JobInteraction.marked_at, now) if marked else None
    if not changes:
        raise ValueError("Vyberte označení nebo stav zobrazení.")
    statement = insert(JobInteraction).values(
        user_id=user_id, job_id=job_id, seen_at=now if seen else None,
        marked=bool(marked), marked_at=now if marked else None,
    ).on_conflict_do_update(index_elements=[JobInteraction.user_id, JobInteraction.job_id], set_=changes)
    result = await db.execute(statement.returning(JobInteraction.seen_at, JobInteraction.marked, JobInteraction.marked_at))
    row = result.one()
    await db.commit()
    return {"id": job_id, "seen_at": row.seen_at, "marked": row.marked, "marked_at": row.marked_at}
