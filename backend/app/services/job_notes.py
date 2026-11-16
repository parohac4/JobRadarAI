from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.job_note import JobNote


async def save_note(db, user_id: int, job_id: int, text: str) -> dict:
    if not text.strip():
        await db.execute(delete(JobNote).where(JobNote.user_id == user_id, JobNote.job_id == job_id))
        await db.commit()
        return {"text": "", "updated_at": None}
    updated_at = datetime.now(UTC)
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    statement = insert(JobNote).values(user_id=user_id, job_id=job_id, text=text, updated_at=updated_at)
    statement = statement.on_conflict_do_update(
        index_elements=[JobNote.user_id, JobNote.job_id], set_={"text": text, "updated_at": updated_at})
    await db.execute(statement)
    await db.commit()
    return {"text": text, "updated_at": updated_at}
