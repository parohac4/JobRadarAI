from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_write_access
from app.database import get_db
from app.models.evaluation import AiEvaluation
from app.models.job import JobListing
from app.models.profile import ProfessionalProfile
from app.models.response import GeneratedResponse
from app.models.user import User
from app.schemas.evaluation import EvaluationOut
from app.schemas.job import JobImportEmail, JobImportUrl, JobListingCreate, JobListingDetail, JobListingOut
from app.schemas.response import GeneratedResponseOut
from app.services import audit, jobs as job_service
from app.services.ai import evaluate_job, generate_response_text
from app.services.job_import import fetch_job_from_url, parse_job_email
from app.schemas.job import JobListingCreate as JobCreate

router = APIRouter()


@router.get("", response_model=list[JobListingOut])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await job_service.list_jobs(db, user.id, skip=skip, limit=limit)


@router.get("/{job_id}", response_model=JobListingDetail)
async def get_job(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    detail = await job_service.get_job_detail(db, user.id, job_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Nabídka nenalezena")
    return detail


@router.post("", response_model=JobListingOut)
async def create_job(
    data: JobListingCreate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job, dup = await job_service.create_job(db, user.id, data)
    await audit.log_audit(db, user_id=user.id, action="job.create", entity_type="job", entity_id=str(job.id))
    await db.commit()
    await db.refresh(job)
    out = await job_service.get_job_detail(db, user.id, job.id)
    return out


@router.post("/import/url", response_model=JobListingOut)
async def import_url(
    body: JobImportUrl,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        extracted = await fetch_job_from_url(body.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Nepodařilo se načíst URL: {exc}") from exc
    data = JobCreate(
        title=extracted["title"],
        company=extracted["company"],
        location=extracted["location"],
        url=extracted["url"],
        raw_text=extracted["raw_text"],
        source=extracted["source"],
    )
    job, dup = await job_service.create_job(db, user.id, data)
    await audit.log_audit(db, user_id=user.id, action="job.import_url", entity_type="job", entity_id=str(job.id))
    await db.commit()
    detail = await job_service.get_job_detail(db, user.id, job.id)
    if dup:
        detail["duplicate_of_id"] = dup.id
    return detail


@router.post("/import/email", response_model=JobListingOut)
async def import_email(
    body: JobImportEmail,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    extracted = parse_job_email(body.subject, body.email_body)
    data = JobCreate(
        title=extracted["title"],
        company=extracted["company"],
        location=extracted["location"],
        url=extracted["url"],
        raw_text=extracted["raw_text"],
        source=extracted["source"],
    )
    job, _ = await job_service.create_job(db, user.id, data)
    await audit.log_audit(db, user_id=user.id, action="job.import_email", entity_type="job", entity_id=str(job.id))
    await db.commit()
    return await job_service.get_job_detail(db, user.id, job.id)


@router.post("/{job_id}/evaluate", response_model=EvaluationOut)
async def evaluate(
    job_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Nabídka nenalezena")
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one()
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
        provider=ev.get("provider", "mock"),
    )
    db.add(row)
    await audit.log_audit(db, user_id=user.id, action="job.evaluate", entity_type="job", entity_id=str(job.id))
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{job_id}/evaluations", response_model=list[EvaluationOut])
async def list_evaluations(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Nabídka nenalezena")
    result = await db.execute(
        select(AiEvaluation).where(AiEvaluation.job_listing_id == job_id).order_by(AiEvaluation.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{job_id}/generate-response", response_model=GeneratedResponseOut)
async def generate_response(
    job_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Nabídka nenalezena")
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one()
    gen = await generate_response_text(
        profile, title=job.title, company=job.company, raw_text=job.raw_text
    )
    row = GeneratedResponse(
        job_listing_id=job.id,
        content=gen["content"],
        recommended_cv_version=gen["recommended_cv_version"],
        provider=gen["provider"],
    )
    db.add(row)
    await audit.log_audit(db, user_id=user.id, action="job.generate_response", entity_type="job", entity_id=str(job.id))
    await db.commit()
    await db.refresh(row)
    return row
