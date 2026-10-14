from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobAvailability
from app.models.evaluation import AiEvaluation
from app.models.job import JobListing
from app.schemas.job import JobListingCreate
from app.services import dedup
from app.services.geo import job_distance


async def create_job(
    db: AsyncSession,
    user_id: int,
    data: JobListingCreate,
) -> tuple[JobListing, JobListing | None]:
    dup = await dedup.find_duplicate(
        db,
        user_id,
        title=data.title,
        company=data.company,
        location=data.location,
        url=data.url,
    )
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
        duplicate_of_id=dup.id if dup else None,
        availability=JobAvailability.open,
    )
    db.add(job)
    await db.flush()
    return job, dup


def latest_score_subquery():
    latest_id = (
        select(AiEvaluation.job_listing_id, func.max(AiEvaluation.id).label("eval_id"))
        .group_by(AiEvaluation.job_listing_id)
        .subquery()
    )
    return (
        select(latest_id.c.job_listing_id, AiEvaluation.score.label("latest_score"))
        .join(AiEvaluation, AiEvaluation.id == latest_id.c.eval_id)
        .subquery()
    )


def _job_dict(
    job: JobListing,
    latest_score: int | None,
    *,
    full_text: bool,
    distance_km: float | None = None,
    location_remote: bool = False,
    location_unknown: bool = False,
) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "url": job.url,
        "source": job.source,
        "raw_text": job.raw_text if full_text else (job.raw_text or "")[:500],
        "availability": job.availability,
        "duplicate_of_id": job.duplicate_of_id,
        "imported_at": job.imported_at,
        "latest_score": latest_score,
        "distance_km": distance_km,
        "location_remote": location_remote,
        "location_unknown": location_unknown,
    }


async def list_jobs(
    db: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
    min_score: int | None = None,
    sort: str = "imported",
    home: dict | None = None,
    max_km: int | None = None,
    include_remote: bool = True,
    include_unknown: bool = True,
) -> list[dict]:
    scores = latest_score_subquery()
    query = (
        select(JobListing, scores.c.latest_score)
        .outerjoin(scores, JobListing.id == scores.c.job_listing_id)
        .where(JobListing.user_id == user_id)
    )
    if min_score is not None:
        query = query.where(scores.c.latest_score >= min_score)

    filter_by_distance = home and max_km is not None
    sort_by_distance = home and sort == "distance"
    needs_post_process = filter_by_distance or sort_by_distance
    fetch_limit = 500 if needs_post_process else limit
    fetch_skip = 0 if needs_post_process else skip

    if sort == "score" and not needs_post_process:
        query = query.order_by(desc(scores.c.latest_score).nulls_last(), desc(JobListing.id))
    elif not needs_post_process:
        query = query.order_by(desc(JobListing.imported_at), desc(JobListing.id))

    result = await db.execute(query.offset(fetch_skip).limit(fetch_limit))
    rows: list[dict] = []
    for job, score in result.all():
        dist_km: float | None = None
        remote = False
        unknown = False
        if home:
            info = job_distance(home, job.location or "", job.raw_text or "")
            dist_km = info.distance_km
            remote = info.remote
            unknown = info.unknown
        rows.append(
            _job_dict(
                job,
                score,
                full_text=False,
                distance_km=dist_km,
                location_remote=remote,
                location_unknown=unknown,
            )
        )

    if needs_post_process:
        filtered: list[dict] = []
        for row in rows:
            if filter_by_distance:
                if row["location_remote"] and not include_remote:
                    continue
                if row["location_unknown"] and not include_unknown:
                    continue
                if row["distance_km"] is not None and row["distance_km"] > max_km:
                    continue
                if row["distance_km"] is None and not row["location_remote"] and not include_unknown:
                    continue
            filtered.append(row)
        rows = filtered

        if sort_by_distance:
            rows.sort(
                key=lambda r: (
                    r["distance_km"] is None,
                    r["distance_km"] if r["distance_km"] is not None else 1e9,
                    -(r["imported_at"].timestamp() if r["imported_at"] else 0),
                )
            )
        elif sort == "score":
            rows.sort(key=lambda r: (-(r["latest_score"] or -1), r["distance_km"] or 1e9))
        else:
            rows.sort(key=lambda r: r["imported_at"], reverse=True)

        rows = rows[skip : skip + limit]

    return rows


async def get_job_detail(db: AsyncSession, user_id: int, job_id: int) -> dict | None:
    scores = latest_score_subquery()
    result = await db.execute(
        select(JobListing, scores.c.latest_score)
        .outerjoin(scores, JobListing.id == scores.c.job_listing_id)
        .where(JobListing.id == job_id, JobListing.user_id == user_id)
    )
    row = result.first()
    if not row:
        return None
    job, score = row
    count = await db.scalar(
        select(func.count()).select_from(AiEvaluation).where(AiEvaluation.job_listing_id == job.id)
    )
    return {
        **_job_dict(job, score, full_text=True),
        "requirements_text": job.requirements_text,
        "evaluations_count": count or 0,
    }
