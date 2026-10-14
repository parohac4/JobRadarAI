from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_write_access
from app.database import get_db
from app.models.profile import ProfessionalProfile
from app.models.user import User
from app.schemas.profile import ProfileOut, ProfileUpdate
from app.services import audit
from app.services.cv_extract import extract_cv_text
from app.services.geo import enrich_location_preferences

MAX_CV_BYTES = 5_000_000

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
    payload = data.model_dump()
    try:
        payload["preferences"] = enrich_location_preferences(payload.get("preferences") or {})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    for field, value in payload.items():
        setattr(profile, field, value)
    await audit.log_audit(db, user_id=user.id, action="profile.update")
    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/cv", response_model=ProfileOut)
async def upload_cv(
    file: UploadFile = File(...),
    _: None = Depends(require_write_access),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Soubor bez názvu")
    data = await file.read()
    if len(data) > MAX_CV_BYTES:
        raise HTTPException(status_code=400, detail="Soubor je příliš velký (max 5 MB)")
    try:
        text = extract_cv_text(file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil nenalezen")
    profile.summary = text[:5000]
    versions = list(profile.cv_versions or [])
    versions.insert(0, {"name": file.filename, "imported_at": "auto", "chars": len(text)})
    profile.cv_versions = versions[:20]
    await audit.log_audit(db, user_id=user.id, action="profile.cv_import")
    await db.commit()
    await db.refresh(profile)
    return profile
