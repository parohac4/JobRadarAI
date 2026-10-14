import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User
from app.services import imap_import, rss_import
from app.services.post_import import maybe_evaluate_and_notify
from app.services.sync_run import finish_run, start_run

logger = logging.getLogger("jobradar.sync")


async def _single_user(db: AsyncSession) -> User | None:
    return (await db.execute(select(User).limit(1))).scalar_one_or_none()


async def run_imap_sync(db: AsyncSession) -> dict:
    user = await _single_user(db)
    if not user:
        return {"error": "no_user"}
    run = await start_run(db, user.id, "imap")
    await db.commit()
    summary = await imap_import.sync_imap_for_user(db, user)
    if summary.get("error"):
        await finish_run(db, run, status="error", message=summary["error"], details=summary)
    elif summary.get("skipped"):
        await finish_run(db, run, status="skipped", message=summary.get("reason", ""), details=summary)
    else:
        for job_id in summary.get("new_job_ids") or []:
            try:
                await maybe_evaluate_and_notify(db, user, job_id)
            except Exception:
                logger.exception("post-import job_id=%s", job_id)
        await db.commit()
        await finish_run(
            db,
            run,
            status="ok",
            message=f"Nové: {summary.get('created', 0)}, duplicity: {summary.get('duplicates', 0)}",
            details=summary,
        )
    await db.commit()
    return summary


async def run_rss_sync(db: AsyncSession) -> dict:
    user = await _single_user(db)
    if not user:
        return {"error": "no_user"}
    run = await start_run(db, user.id, "rss")
    await db.commit()
    summary = await rss_import.sync_rss_for_user(db, user)
    for job_id in summary.get("new_job_ids") or []:
        try:
            await maybe_evaluate_and_notify(db, user, job_id)
        except Exception:
            logger.exception("post-import job_id=%s", job_id)
    await db.commit()
    await finish_run(
        db,
        run,
        status="ok" if not summary.get("errors") else "partial",
        message=f"Nové: {summary.get('created', 0)}, feedů: {summary.get('feeds', 0)}",
        details=summary,
    )
    await db.commit()
    return summary


async def run_all_syncs(db: AsyncSession) -> dict:
    settings = get_settings()
    out: dict = {}
    if settings.imap_configured:
        out["imap"] = await run_imap_sync(db)
    out["rss"] = await run_rss_sync(db)
    return out
