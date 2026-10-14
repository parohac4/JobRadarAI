"""Výchozí zdroje nabídek – Síť práce (veřejné API, bez klíče). Jobs.cz / Prace.cz nemají veřejné RSS."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feed_source import FeedSource
from app.models.user import User
from app.services.sitprace_import import build_search_url

# Přizpůsobeno profilu: IT podpora, Linux, Jihočeský kraj (+ dojezd)
DEFAULT_FEEDS: list[tuple[str, str]] = [
    (
        "Síť práce – IT podpora (České Budějovice, 80 km)",
        build_search_url(query="linux", city="České Budějovice", radius_km=80, category="it-podpora", limit=50),
    ),
    (
        "Síť práce – technická podpora Linux",
        build_search_url(
            query="technická podpora linux",
            city="České Budějovice",
            radius_km=100,
            limit=50,
        ),
    ),
    (
        "Síť práce – správce sítí (Tábor, 80 km)",
        build_search_url(query="správce sítí", city="Tábor", radius_km=80, limit=50),
    ),
    (
        "Síť práce – hosting / servery / DNS",
        build_search_url(
            query="hosting server DNS",
            city="České Budějovice",
            radius_km=120,
            limit=40,
        ),
    ),
    (
        "Síť práce – nejnovější nabídky (celá ČR, AI filtr)",
        "https://sitprace.cz/api/public/jobs/latest.json",
    ),
]


async def seed_default_feeds_if_empty(db: AsyncSession, user: User) -> int:
    existing = (await db.execute(select(FeedSource.id).where(FeedSource.user_id == user.id).limit(1))).first()
    if existing:
        return 0
    for title, url in DEFAULT_FEEDS:
        db.add(FeedSource(user_id=user.id, title=title, url=url, enabled=True))
    await db.commit()
    return len(DEFAULT_FEEDS)
