from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password
from app.models.profile import ProfessionalProfile
from app.models.user import User

DEFAULT_PROFILE = {
    "summary": (
        "Dlouholeté zkušenosti s technickou podporou L1/L2, zákaznickou komunikací, "
        "řešením problémů a praktickou správou linuxových serverů. Vyučení bez maturity."
    ),
    "skills": [
        "Linux",
        "DNS",
        "webhosting",
        "technická podpora",
        "zákaznická podpora",
        "incident management",
        "ticketing",
        "SSH",
        "Apache/Nginx",
        "e-mail servery",
    ],
    "experience": [
        {
            "role": "Technická podpora / správa serverů",
            "years": "10+",
            "highlights": ["L1/L2 podpora", "Linux", "hosting"],
        }
    ],
    "education": [{"level": "Vyučení", "field": "IT / technické"}],
    "preferences": {
        "regions": ["Jihočeský kraj", "remote", "home office", "hybrid"],
        "roles": [
            "IT podpora",
            "technická podpora",
            "zákaznická podpora",
            "správce serverů",
            "hosting",
            "provoz",
        ],
        "min_score_suggest": 60,
    },
    "cv_versions": [{"name": "Technická podpora", "description": "Zdůraznění Linux/hosting"}],
}


async def ensure_admin_user(db: AsyncSession) -> None:
    settings = get_settings()
    result = await db.execute(select(User).where(User.email == settings.admin_email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
        )
        db.add(user)
        await db.flush()
        db.add(
            ProfessionalProfile(
                user_id=user.id,
                summary=DEFAULT_PROFILE["summary"],
                skills=DEFAULT_PROFILE["skills"],
                experience=DEFAULT_PROFILE["experience"],
                education=DEFAULT_PROFILE["education"],
                preferences=DEFAULT_PROFILE["preferences"],
                cv_versions=DEFAULT_PROFILE["cv_versions"],
            )
        )
    else:
        result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
        if not result.scalar_one_or_none():
            db.add(
                ProfessionalProfile(
                    user_id=user.id,
                    **DEFAULT_PROFILE,
                )
            )
    await db.commit()
