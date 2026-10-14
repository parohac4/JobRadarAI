from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_write_access
from app.database import get_db
from app.models.profile import ProfessionalProfile
from app.models.user import User
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services import audit

router = APIRouter()


@router.get("", response_model=ProfileOut)
async def get_profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil nenalezen")
    return profile


@router.put("", response_model=ProfileOut)
async def update_profile(
    data: ProfileUpdate,
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil nenalezen")
    for field, value in data.model_dump().items():
        setattr(profile, field, value)
    await audit.log_audit(db, user_id=user.id, action="profile.update")
    await db.commit()
    await db.refresh(profile)
    return profile
