from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select

from app.config import get_settings
from app.core.deps import get_current_user, require_write_access
from app.database import AsyncSessionLocal, get_db
from app.models.job import JobListing
from app.schemas.aggregator import SearchSettings
from app.services import aggregator as service
from app.services.job_import import assert_public_url, UnsafeUrlError
from app.services.places import resolve_place, suggestions
from app.services.portal_import import CATALOG

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
               sort: str | None = Query(None, pattern="^(newest|match|distance)$"),
               source: str | None = Query(None, max_length=30), q: str = Query("", max_length=300),
               user=Depends(get_current_user), db=Depends(get_db)):
    return await service.offers(db, user.id, skip=skip, limit=limit, sort=sort, source=source, query=q)


@router.get("/jobs/{job_id}")
async def detail(job_id: int, user=Depends(get_current_user), db=Depends(get_db)):
    job = (await db.execute(select(JobListing).where(JobListing.id == job_id, JobListing.user_id == user.id))).scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Nabídka nenalezena")
    return {"id": job.id, "title": job.title, "company": job.company, "location": job.location,
            "url": job.url, "raw_text": service.plain_text(job.raw_text)}
