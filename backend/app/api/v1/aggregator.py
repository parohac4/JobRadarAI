from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select

from app.config import get_settings
from app.core.deps import get_current_user, require_write_access
from app.database import AsyncSessionLocal, get_db
from app.models.job import JobListing
from app.models.job_interaction import JobInteraction
from app.models.job_note import JobNote
from app.schemas.aggregator import InteractionUpdate, NoteUpdate, SearchSettings
from app.services import aggregator as service
from app.services.job_import import assert_public_url, UnsafeUrlError
from app.services.places import resolve_place, suggestions
from app.services.portal_import import CATALOG
from app.services.job_interactions import update_interaction
from app.services.job_notes import save_note

router = APIRouter()


@router.get("/settings")
async def settings(user=Depends(get_current_user), db=Depends(get_db)):
    config = service.config_for(await service.profile_for(db, user.id))
    s = get_settings()
    return {"settings": config, "sources": CATALOG, "ai_available": s.ai_provider == "openai" and bool(s.openai_api_key),
            "worker_enabled": s.worker_enabled, "ai_daily_limit": s.ai_daily_max_calls}


@router.put("/settings")
async def save_settings(config: SearchSettings, _=Depends(require_write_access), user=Depends(get_current_user), db=Depends(get_db)):
    place = resolve_place(config.city)
    if not place:
        raise HTTPException(400, "Vyberte konkrétní obec z našeptávače; stejnojmenné obce mají uvedené souřadnice.")
    config.city = place["label"]
    if config.ai_enabled and not config.ai_preferences.strip():
        raise HTTPException(400, "Napište, jakou práci má AI hledat, nebo AI preference vypněte.")
    for feed in config.custom_feeds:
        try:
            await assert_public_url(str(feed.url))
        except UnsafeUrlError as exc:
            raise HTTPException(400, str(exc)) from exc
    profile = await service.profile_for(db, user.id)
    profile.preferences = {**(profile.preferences or {}), "aggregator": config.model_dump(mode="json")}
    await db.commit()
    return {"settings": config}


@router.get("/places")
async def places(q: str = Query("", max_length=150), user=Depends(get_current_user)):
    return {"items": suggestions(q)}


@router.get("/status")
async def status(user=Depends(get_current_user), db=Depends(get_db)):
    config = service.config_for(await service.profile_for(db, user.id))
    run = await service.latest_run(db, user.id)
    return {"monitoring_enabled": config.monitoring_enabled, "interval_minutes": config.interval_minutes,
            "settings_current": bool(run and (run.details or {}).get("config_hash") == service.fingerprint(config)),
            "last_run": {"id": run.id, "status": run.status, "started_at": run.started_at,
                         "finished_at": run.finished_at, "message": run.message, "details": run.details} if run else None}


async def _collect(user):
    async with AsyncSessionLocal() as db:
        await service.monitor(db, user, force=True)


@router.post("/sync", status_code=202)
async def sync(tasks: BackgroundTasks, _=Depends(require_write_access), user=Depends(get_current_user)):
    tasks.add_task(_collect, user)
    return {"status": "queued"}


@router.get("/jobs")
async def jobs(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
               sort: str | None = Query(None, pattern="^(newest|oldest|match|distance)$"),
               source: str | None = Query(None, max_length=30), q: str = Query("", max_length=300),
               seen: str = Query("all", pattern="^(all|unseen|seen)$"), marked_only: bool = False,
               user=Depends(get_current_user), db=Depends(get_db)):
    return await service.offers(db, user.id, skip=skip, limit=limit, sort=sort, source=source, query=q,
                                seen=seen, marked_only=marked_only)


@router.patch("/jobs/{job_id}/interaction")
async def interaction(job_id: int, data: InteractionUpdate, _=Depends(require_write_access),
                      user=Depends(get_current_user), db=Depends(get_db)):
    owned = await db.scalar(select(JobListing.id).where(JobListing.id == job_id, JobListing.user_id == user.id))
    if owned is None:
        raise HTTPException(404, "Nabídka nenalezena")
    try:
        return await update_interaction(db, user.id, job_id, seen=data.seen, marked=data.marked)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs/{job_id}")
async def detail(job_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    job = (await db.execute(select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Nabídka nenalezena")
    state = (await db.execute(select(JobInteraction.seen_at, JobInteraction.marked, JobInteraction.marked_at)
        .where(JobInteraction.user_id == user.id, JobInteraction.job_id == job_id))).one_or_none()
    note = (await db.execute(select(JobNote.text, JobNote.updated_at)
        .where(JobNote.user_id == user.id, JobNote.job_id == job_id))).one_or_none()
    return {"id": job.id, "title": job.title, "company": job.company, "location": job.location,
            "url": job.url, "raw_text": service.plain_text(job.raw_text), "seen_at": state.seen_at if state else None,
            "marked": state.marked if state else False, "marked_at": state.marked_at if state else None,
            "note": {"text": note.text, "updated_at": note.updated_at} if note else {"text": "", "updated_at": None}}


async def _require_owned_job(db, user_id: int, job_id: int):
    if await db.scalar(select(JobListing.id).where(JobListing.id == job_id, JobListing.user_id == user_id)) is None:
        raise HTTPException(404, "Nabídka nenalezena")


@router.put("/jobs/{job_id}/note")
async def update_note(job_id: int, data: NoteUpdate, _=Depends(require_write_access),
                      user=Depends(get_current_user), db=Depends(get_db)):
    await _require_owned_job(db, user.id, job_id)
    return await save_note(db, user.id, job_id, data.text)


@router.delete("/jobs/{job_id}/note")
async def delete_note(job_id: int, _=Depends(require_write_access), user=Depends(get_current_user), db=Depends(get_db)):
    await _require_owned_job(db, user.id, job_id)
    return await save_note(db, user.id, job_id, "")
