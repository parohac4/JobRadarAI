from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.sync import SyncRun
from app.models.user import User
from app.schemas.system import HealthOut, SyncRunOut
from app.services.demo_seed import seed_demo_data

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health():
    settings = get_settings()
    return HealthOut(status="ok", demo_mode=settings.demo_mode)


@router.get("/sync-runs", response_model=list[SyncRunOut])
async def sync_runs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SyncRun).where(SyncRun.user_id == user.id).order_by(SyncRun.started_at.desc()).limit(50)
    )
    return list(result.scalars().all())


@router.post("/demo/reset")
async def demo_reset(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if not settings.demo_mode:
        return {"ok": False, "message": "Pouze v DEMO_MODE=true"}
    summary = await seed_demo_data(db, user)
    return {"ok": True, **summary}
