from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.profile import ProfessionalProfile
from app.models.user import User

DEFAULT_PROFILE = {
    "summary": (
        "Zkušenosti s technickou podporou L1/L2, zákaznickou komunikací, "
        "řešením problémů a praktickou správou linuxových serverů. Vyučení bez maturity. "
        "(Upravte shrnutí a data zkušeností podle skutečnosti.)"
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
            "from": "2010",
            "to": "2020",
            "highlights": ["L1/L2 podpora", "Linux", "hosting"],
        }
    ],
    "education": [{"level": "Vyučení", "field": "IT / technické"}],
    "preferences": {
        "home_city": "Strakonice",
        "home": {"city": "Strakonice", "lat": 49.2614, "lon": 13.9024},
        "max_distance_km": None,
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
    """Jeden tenant: účet v DB se synchronizuje s ADMIN_EMAIL / ADMIN_PASSWORD z .env."""
    settings = get_settings()
    admin_email = settings.admin_email.strip().lower()
    total = await db.scalar(select(func.count()).select_from(User)) or 0

    result = await db.execute(select(User).where(User.email == admin_email))
    user = result.scalar_one_or_none()

    if user is None and total == 1:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one()

    if user is None:
        user = User(
            email=admin_email,
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
        user.email = admin_email
        if not verify_password(settings.admin_password, user.hashed_password):
            user.hashed_password = hash_password(settings.admin_password)
        user.is_active = True
        result = await db.execute(select(ProfessionalProfile).where(ProfessionalProfile.user_id == user.id))
        if not result.scalar_one_or_none():
            db.add(
                ProfessionalProfile(
                    user_id=user.id,
                    **DEFAULT_PROFILE,
                )
            )
    await db.commit()
