from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_write_access
from app.database import get_db
from app.models.application import Application, ApplicationHistory, ApplicationNote
from app.models.job import JobListing
from app.models.user import User
from app.schemas.application import (
    ApplicationHistoryOut,
    ApplicationNoteCreate,
    ApplicationNoteOut,
    ApplicationOut,
    ApplicationSnoozeIn,
    ApplicationStatusUpdate,
)
from app.services import audit
from app.services.applications import application_inbox_clause, clear_application_snooze, snooze_application

router = APIRouter()


def _out(app: Application, job: JobListing) -> ApplicationOut:
    return ApplicationOut(
        id=app.id,
        job_listing_id=app.job_listing_id,
        status=app.status,
        updated_at=app.updated_at,
        next_action_at=app.next_action_at,
        snooze_note=app.snooze_note or "",
        job_title=job.title,
        company=job.company,
    )


async def _get_owned(db: AsyncSession, user: User, app_id: int) -> tuple[Application, JobListing]:
    result = await db.execute(
        select(Application, JobListing)
        .join(JobListing, Application.job_listing_id == JobListing.id)
        .where(Application.id == app_id, Application.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Žádost nenalezena")
    return row[0], row[1]


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    inbox: str = Query("active", pattern="^(active|snoozed)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Application, JobListing)
        .join(JobListing, Application.job_listing_id == JobListing.id)
        .where(Application.user_id == user.id, application_inbox_clause(inbox))
        .order_by(Application.updated_at.desc())
    )
    return [_out(app, job) for app, job in result.all()]


@router.get("/by-job/{job_id}", response_model=ApplicationOut | None)
async def get_by_job(job_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Application, JobListing)
        .join(JobListing, Application.job_listing_id == JobListing.id)
        .where(Application.job_listing_id == job_id, Application.user_id == user.id)
    )
    row = result.first()
    return _out(row[0], row[1]) if row else None


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
    result = await db.execute(select(Application.id).where(Application.job_listing_id == job_id))
    if result.first():
        raise HTTPException(status_code=409, detail="Žádost k této nabídce už existuje")
    app = Application(user_id=user.id, job_listing_id=job_id)
    db.add(app)
    await db.flush()
    db.add(ApplicationHistory(application_id=app.id, from_status=None, to_status=app.status, note="Vytvořeno"))
    await audit.log_audit(db, user_id=user.id, action="application.create", entity_type="application", entity_id=str(app.id))
    await db.commit()
    await db.refresh(app)
    return _out(app, job)


@router.post("/{app_id}/snooze", response_model=ApplicationOut)
async def snooze_application_endpoint(
    app_id: int,
    body: ApplicationSnoozeIn,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app, job = await _get_owned(db, user, app_id)
    snooze_application(app, note=body.note, days=body.days)
    until = app.next_action_at
    db.add(
        ApplicationHistory(
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            note=f"Odloženo do {until.isoformat() if until else '?'}: {body.note.strip()}",
        )
    )
    await audit.log_audit(
        db,
        user_id=user.id,
        action="application.snooze",
        entity_type="application",
        entity_id=str(app.id),
        payload={"days": body.days},
    )
    await db.commit()
    await db.refresh(app)
    return _out(app, job)


@router.post("/{app_id}/restore-snooze", response_model=ApplicationOut)
async def restore_application_snooze(
    app_id: int,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app, job = await _get_owned(db, user, app_id)
    clear_application_snooze(app)
    db.add(
        ApplicationHistory(
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            note="Odložení zrušeno – žádost je znovu aktivní.",
        )
    )
    await audit.log_audit(
        db, user_id=user.id, action="application.restore_snooze", entity_type="application", entity_id=str(app.id)
    )
    await db.commit()
    await db.refresh(app)
    return _out(app, job)


@router.patch("/{app_id}/status", response_model=ApplicationOut)
async def update_status(
    app_id: int,
    body: ApplicationStatusUpdate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    app, job = await _get_owned(db, user, app_id)
    old = app.status
    if old != body.status or body.note:
        app.status = body.status
        db.add(ApplicationHistory(application_id=app.id, from_status=old, to_status=body.status, note=body.note))
        await audit.log_audit(
            db,
            user_id=user.id,
            action="application.status",
            entity_type="application",
            entity_id=str(app.id),
            payload={"from": old.value, "to": body.status.value},
        )
        await db.commit()
        await db.refresh(app)
    return _out(app, job)


@router.get("/{app_id}/history", response_model=list[ApplicationHistoryOut])
async def history(app_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_owned(db, user, app_id)
    result = await db.execute(
        select(ApplicationHistory)
        .where(ApplicationHistory.application_id == app_id)
        .order_by(ApplicationHistory.id.desc())
    )
    return list(result.scalars().all())


@router.get("/{app_id}/notes", response_model=list[ApplicationNoteOut])
async def list_notes(app_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _get_owned(db, user, app_id)
    result = await db.execute(
        select(ApplicationNote).where(ApplicationNote.application_id == app_id).order_by(ApplicationNote.id.desc())
    )
    return list(result.scalars().all())


@router.post("/{app_id}/notes", response_model=ApplicationNoteOut)
async def add_note(
    app_id: int,
    body: ApplicationNoteCreate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned(db, user, app_id)
    note = ApplicationNote(application_id=app_id, body=body.body)
    db.add(note)
    await audit.log_audit(
        db, user_id=user.id, action="application.note", entity_type="application", entity_id=str(app_id)
    )
    await db.commit()
    await db.refresh(note)
    return note
