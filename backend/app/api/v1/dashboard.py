from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.enums import ApplicationStatus, JobAvailability
from app.models.evaluation import AiEvaluation
from app.models.job import JobListing
from app.models.user import User
from app.schemas.system import DashboardStats

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def stats(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = await db.scalar(
        select(func.count()).select_from(JobListing).where(JobListing.user_id == user.id)
    )
    open_jobs = await db.scalar(
        select(func.count())
        .select_from(JobListing)
        .where(JobListing.user_id == user.id, JobListing.availability == JobAvailability.open)
    )
    apps = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(
            Application.user_id == user.id,
            Application.status.not_in([ApplicationStatus.archived, ApplicationStatus.rejected]),
        )
    )
    rec = await db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.user_id == user.id, Application.status == ApplicationStatus.recommended)
    )
    avg = await db.scalar(
        select(func.avg(AiEvaluation.score))
        .select_from(AiEvaluation)
        .join(JobListing, AiEvaluation.job_listing_id == JobListing.id)
        .where(JobListing.user_id == user.id)
    )
    return DashboardStats(
        total_jobs=total or 0,
        open_jobs=open_jobs or 0,
        applications_active=apps or 0,
        recommended_count=rec or 0,
        avg_score=float(avg) if avg is not None else None,
    )
