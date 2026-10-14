import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.sync import SyncRun
from app.models.user import User
from app.schemas.system import AuditEventOut, HealthOut, SyncRunOut
from app.services.demo_seed import seed_demo_data

logger = logging.getLogger("jobradar.system")

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check: databáze nedostupná")
        return JSONResponse(status_code=503, content={"status": "db_error", "demo_mode": settings.demo_mode})
    return HealthOut(status="ok", demo_mode=settings.demo_mode)


@router.get("/sync-runs", response_model=list[SyncRunOut])
async def sync_runs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SyncRun).where(SyncRun.user_id == user.id).order_by(SyncRun.started_at.desc()).limit(50)
    )
    return list(result.scalars().all())


@router.get("/audit", response_model=list[AuditEventOut])
async def audit_log(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditEvent)
        .where((AuditEvent.user_id == user.id) | (AuditEvent.user_id.is_(None)))
        .order_by(AuditEvent.id.desc())
        .limit(100)
    )
    return list(result.scalars().all())


@router.post("/demo/reset")
async def demo_reset(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not get_settings().demo_mode:
        raise HTTPException(status_code=403, detail="Reset dat je dostupný jen v demo režimu (DEMO_MODE=true)")
    summary = await seed_demo_data(db, user)
    return {"ok": True, **summary}
