from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.application import Application
from app.models.enums import JobAvailability
from app.models.evaluation import AiEvaluation
from app.models.job import JobListing
from app.schemas.job import JobListingCreate
from app.services import dedup


async def create_job(
    db: AsyncSession,
    user_id: int,
    data: JobListingCreate,
    *,
    mark_duplicate: bool = True,
) -> tuple[JobListing, JobListing | None]:
    dup: JobListing | None = None
    duplicate_of_id = None
    if mark_duplicate:
        dup = await dedup.find_duplicate(
            db,
            user_id,
            title=data.title,
            company=data.company,
            location=data.location,
            url=data.url,
        )
        if dup:
            duplicate_of_id = dup.id

    job = JobListing(
        user_id=user_id,
        title=data.title,
        company=data.company,
        location=data.location,
        url=data.url,
        source=data.source,
        raw_text=data.raw_text,
        requirements_text=data.requirements_text,
        content_hash=dedup.content_hash(data.title, data.company, data.location),
        url_hash=dedup.url_hash(data.url) if data.url else "",
        duplicate_of_id=duplicate_of_id,
        availability=JobAvailability.open,
    )
    db.add(job)
    await db.flush()
    return job, dup


async def list_jobs(db: AsyncSession, user_id: int, *, skip: int = 0, limit: int = 50) -> list[dict]:
    subq = (
        select(
            AiEvaluation.job_listing_id,
            func.max(AiEvaluation.score).label("latest_score"),
        )
        .group_by(AiEvaluation.job_listing_id)
        .subquery()
    )
    result = await db.execute(
        select(JobListing, subq.c.latest_score)
        .outerjoin(subq, JobListing.id == subq.c.job_listing_id)
        .where(JobListing.user_id == user_id)
        .order_by(desc(JobListing.imported_at))
        .offset(skip)
        .limit(limit)
    )
    rows = []
    for job, score in result.all():
        rows.append({**_job_dict(job), "latest_score": score})
    return rows


def _job_dict(job: JobListing) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "source": job.source,
        "raw_text": job.raw_text[:500] if job.raw_text else "",
        "availability": job.availability,
        "duplicate_of_id": job.duplicate_of_id,
        "imported_at": job.imported_at,
    }


async def get_job_detail(db: AsyncSession, user_id: int, job_id: int) -> dict | None:
    result = await db.execute(
        select(JobListing)
        .options(selectinload(JobListing.evaluations))
        .where(JobListing.id == job_id, JobListing.user_id == user_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None
    latest = max((e.score for e in job.evaluations), default=None)
    return {
        **_job_dict(job),
        "raw_text": job.raw_text,
        "requirements_text": job.requirements_text,
        "evaluations_count": len(job.evaluations),
        "latest_score": latest,
    }
