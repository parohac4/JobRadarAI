import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.schemas.job import (
    JobDismissIn,
    JobImportEmail,
    JobImportUrl,
    JobListingCreate,
    JobListingDetail,
    JobListingOut,
    JobSnoozeIn,
)
from app.schemas.response import GeneratedResponseOut
from app.services import audit
from app.services import jobs as job_service
from app.services.ai import evaluate_job, generate_response_text
from app.services.job_import import UnsafeUrlError, fetch_job_from_url, parse_job_email

logger = logging.getLogger("jobradar.jobs")

router = APIRouter()


async def _get_owned_job(db: AsyncSession, user: User, job_id: int) -> JobListing:
    result = await db.execute(select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Nabídka nenalezena")
    return job


async def _get_profile(db: AsyncSession, user: User) -> ProfessionalProfile:
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=409, detail="Nejdříve vyplňte profesní profil")
    return profile


async def _store_job(db: AsyncSession, user: User, data: JobListingCreate, action: str) -> dict:
    job, _dup = await job_service.create_job(db, user.id, data)
    await audit.log_audit(db, user_id=user.id, action=action, entity_type="job", entity_id=str(job.id))
    await db.commit()
    return await job_service.get_job_detail(db, user.id, job.id)


async def _get_profile_optional(db: AsyncSession, user: User) -> ProfessionalProfile | None:
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    return result.scalar_one_or_none()


@router.get("", response_model=list[JobListingOut])
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    min_score: int | None = Query(None, ge=0, le=100),
    sort: str = Query("imported", pattern="^(imported|score|distance)$"),
    max_km: int | None = Query(None, ge=1, le=500),
    include_remote: bool = Query(True),
    include_unknown: bool = Query(True),
    inbox: str = Query("active", pattern="^(active|snoozed|dismissed)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile_optional(db, user)
    prefs = (profile.preferences or {}) if profile else {}
    home = prefs.get("home") if isinstance(prefs.get("home"), dict) else None
    effective_max = max_km if max_km is not None else prefs.get("max_distance_km")
    if effective_max is not None:
        try:
            effective_max = int(effective_max)
        except (TypeError, ValueError):
            effective_max = None
    if (sort == "distance" or effective_max is not None) and not home:
        raise HTTPException(
            status_code=400,
            detail="Pro filtr nebo řazení podle vzdálenosti nastavte domovské město v profilu.",
        )
    return await job_service.list_jobs(
        db,
        user.id,
        skip=skip,
        limit=limit,
        min_score=min_score,
        sort=sort,
        home=home,
        max_km=effective_max,
        include_remote=include_remote,
        include_unknown=include_unknown,
        inbox=inbox,
    )


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
    return await _store_job(db, user, data, "job.create")


@router.post("/import/url", response_model=JobListingOut)
async def import_url(
    body: JobImportUrl,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        extracted = await fetch_job_from_url(body.url)
    except UnsafeUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Stránka vrátila chybu HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("Import URL selhal: %s", exc)
        raise HTTPException(status_code=502, detail="Stránku se nepodařilo načíst") from exc
    return await _store_job(db, user, JobListingCreate(**extracted), "job.import_url")


@router.post("/import/email", response_model=JobListingOut)
async def import_email(
    body: JobImportEmail,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    extracted = parse_job_email(body.subject, body.email_body)
    return await _store_job(db, user, JobListingCreate(**extracted), "job.import_email")


@router.post("/{job_id}/snooze", response_model=JobListingOut)
async def snooze_job(
    job_id: int,
    body: JobSnoozeIn,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _get_owned_job(db, user, job_id)
    await job_service.snooze_job(db, job, note=body.note, days=body.days)
    await audit.log_audit(
        db,
        user_id=user.id,
        action="job.snooze",
        entity_type="job",
        entity_id=str(job.id),
        payload={"days": body.days},
    )
    await db.commit()
    detail = await job_service.get_job_detail(db, user.id, job.id)
    return detail


@router.post("/{job_id}/dismiss", response_model=JobListingOut)
async def dismiss_job(
    job_id: int,
    body: JobDismissIn,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _get_owned_job(db, user, job_id)
    await job_service.dismiss_job(db, job, note=body.note)
    await audit.log_audit(db, user_id=user.id, action="job.dismiss", entity_type="job", entity_id=str(job.id))
    await db.commit()
    detail = await job_service.get_job_detail(db, user.id, job.id)
    return detail


@router.post("/{job_id}/restore-inbox", response_model=JobListingOut)
async def restore_job_inbox(
    job_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _get_owned_job(db, user, job_id)
    await job_service.restore_job_inbox(db, job)
    await audit.log_audit(db, user_id=user.id, action="job.restore_inbox", entity_type="job", entity_id=str(job.id))
    await db.commit()
    detail = await job_service.get_job_detail(db, user.id, job.id)
    return detail


@router.post("/{job_id}/evaluate", response_model=EvaluationOut)
async def evaluate(
    job_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _get_owned_job(db, user, job_id)
    profile = await _get_profile(db, user)
    ev = await evaluate_job(profile, title=job.title, location=job.location, raw_text=job.raw_text)
    row = AiEvaluation(job_listing_id=job.id, **ev)
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
    await _get_owned_job(db, user, job_id)
    result = await db.execute(
        select(AiEvaluation).where(AiEvaluation.job_listing_id == job_id).order_by(AiEvaluation.id.desc())
    )
    return list(result.scalars().all())


@router.post("/{job_id}/generate-response", response_model=GeneratedResponseOut)
async def generate_response(
    job_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await _get_owned_job(db, user, job_id)
    profile = await _get_profile(db, user)
    gen = await generate_response_text(profile, title=job.title, company=job.company, raw_text=job.raw_text)
    row = GeneratedResponse(job_listing_id=job.id, **gen)
    db.add(row)
    await audit.log_audit(
        db, user_id=user.id, action="job.generate_response", entity_type="job", entity_id=str(job.id)
    )
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/{job_id}/responses", response_model=list[GeneratedResponseOut])
async def list_responses(
    job_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_job(db, user, job_id)
    result = await db.execute(
        select(GeneratedResponse)
        .where(GeneratedResponse.job_listing_id == job_id)
        .order_by(GeneratedResponse.id.desc())
    )
    return list(result.scalars().all())
