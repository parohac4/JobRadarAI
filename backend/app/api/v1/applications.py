from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, require_write_access
from app.database import get_db
from app.models.application import Application, ApplicationHistory, ApplicationNote
from app.models.job import JobListing
from app.models.user import User
from app.schemas.application import (
    ApplicationHistoryOut,
    ApplicationNoteCreate,
    ApplicationOut,
    ApplicationStatusUpdate,
)
from app.services import audit

router = APIRouter()


@router.get("", response_model=list[ApplicationOut])
async def list_applications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application, JobListing)
        .join(JobListing, Application.job_listing_id == JobListing.id)
        .where(Application.user_id == user.id)
        .order_by(Application.updated_at.desc())
    )
    out = []
    for app, job in result.all():
        out.append(
            ApplicationOut(
                id=app.id,
                job_listing_id=app.job_listing_id,
                status=app.status,
                updated_at=app.updated_at,
                job_title=job.title,
                company=job.company,
            )
        )
    return out


@router.post("/from-job/{job_id}", response_model=ApplicationOut)
async def create_from_job(
    job_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Nabídka nenalezena")
    result = await db.execute(select(Application).where(Application.job_listing_id == job_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Žádost již existuje")
    app = Application(user_id=user.id, job_listing_id=job_id)
    db.add(app)
    await db.flush()
    db.add(ApplicationHistory(application_id=app.id, from_status=None, to_status=app.status, note="Vytvořeno"))
    await audit.log_audit(db, user_id=user.id, action="application.create", entity_id=str(app.id))
    await db.commit()
    return ApplicationOut(
        id=app.id,
        job_listing_id=app.job_listing_id,
        status=app.status,
        updated_at=app.updated_at,
        job_title=job.title,
        company=job.company,
    )


@router.patch("/{app_id}/status", response_model=ApplicationOut)
async def update_status(
    app_id: int,
    body: ApplicationStatusUpdate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.job_listing))
        .where(Application.id == app_id, Application.user_id == user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Žádost nenalezena")
    old = app.status
    app.status = body.status
    db.add(
        ApplicationHistory(
            application_id=app.id,
            from_status=old,
            to_status=body.status,
            note=body.note,
        )
    )
    await audit.log_audit(db, user_id=user.id, action="application.status", entity_id=str(app.id))
    await db.commit()
    await db.refresh(app)
    job = app.job_listing
    return ApplicationOut(
        id=app.id,
        job_listing_id=app.job_listing_id,
        status=app.status,
        updated_at=app.updated_at,
        job_title=job.title if job else None,
        company=job.company if job else None,
    )


@router.get("/{app_id}/history", response_model=list[ApplicationHistoryOut])
async def history(
    app_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Application).where(Application.id == app_id, Application.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Žádost nenalezena")
    result = await db.execute(
        select(ApplicationHistory)
        .where(ApplicationHistory.application_id == app_id)
        .order_by(ApplicationHistory.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{app_id}/notes")
async def add_note(
    app_id: int,
    body: ApplicationNoteCreate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Application).where(Application.id == app_id, Application.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Žádost nenalezena")
    db.add(ApplicationNote(application_id=app_id, body=body.body))
    await db.commit()
    return {"ok": True}
