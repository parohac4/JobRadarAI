from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync import SyncRun


async def start_run(db: AsyncSession, user_id: int, source: str) -> SyncRun:
    run = SyncRun(user_id=user_id, source=source, status="running", message="")
    db.add(run)
    await db.flush()
    return run


async def finish_run(
    db: AsyncSession,
    run: SyncRun,
    *,
    status: str,
    message: str,
    details: dict | None = None,
) -> None:
    run.status = status
    run.message = message[:5000]
    if details is not None:
        run.details = details
    run.finished_at = datetime.now(UTC)
