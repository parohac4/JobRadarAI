import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.evaluation import AiEvaluation
from app.models.job import JobListing
from app.models.profile import ProfessionalProfile
from app.models.user import User
from app.services.ai import evaluate_job
from app.services.notifications import notify_job_match

logger = logging.getLogger("jobradar.import")


async def ai_calls_today(db: AsyncSession, user_id: int) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.scalar(
        select(func.count(AiEvaluation.id))
        .join(JobListing, AiEvaluation.job_listing_id == JobListing.id)
        .where(JobListing.user_id == user_id, AiEvaluation.created_at >= start, AiEvaluation.provider == "openai")
    )
    return int(result or 0)


async def maybe_evaluate_and_notify(db: AsyncSession, user: User, job_id: int) -> None:
    settings = get_settings()
    if not settings.auto_evaluate_on_import:
        return

    result = await db.execute(select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job or job.duplicate_of_id:
        return

    if settings.ai_provider == "openai" and settings.openai_api_key:
        if await ai_calls_today(db, user.id) >= settings.ai_daily_max_calls:
            logger.warning("Denní limit AI volání dosažen, přeskočeno job_id=%s", job_id)
            return

    prof = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = prof.scalar_one_or_none()
    if not profile:
        return

    ev = await evaluate_job(profile, title=job.title, location=job.location, raw_text=job.raw_text)
    row = AiEvaluation(
        job_listing_id=job.id,
        score=ev["score"],
        summary=ev["summary"],
        reasons=ev["reasons"],
        required_skills=ev["required_skills"],
        preferred_skills=ev["preferred_skills"],
        pros=ev["pros"],
        cons=ev["cons"],
        risks=ev["risks"],
        provider=ev["provider"],
    )
    db.add(row)
    await db.flush()
    await notify_job_match(db, user, job, ev["score"])
