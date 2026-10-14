"""Výchozí zdroje nabídek – Síť práce (API) a veřejné RSS (Kariera.cz, …)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feed_source import FeedSource
from app.models.user import User
from app.services.sitprace_import import build_search_url

KARIERA_RSS = "https://www.kariera.cz/prace/?format=rss"
KARIERA_JC = "https://www.kariera.cz/prace/cesko/jihocesky-kraj/?format=rss"
KARIERA_HW = "https://www.kariera.cz/prace/hardware/?format=rss"
KARIERA_JC_HW = "https://www.kariera.cz/prace/cesko/jihocesky-kraj/hardware/?format=rss"
AKTUALNI_NABIDKY_RSS = "https://www.aktualninabidkyprace.cz/rss/detail/"
PRACE_PRO_OZP_RSS = "https://www.praceproozp.cz/rss/detail/"

# Přizpůsobeno profilu: IT podpora, Linux, Jihočeský kraj (+ dojezd)
DEFAULT_FEEDS: list[tuple[str, str]] = [
    (
        "Kariera.cz – vše (ČR)",
        KARIERA_RSS,
    ),
    (
        "Kariera.cz – Jihočeský kraj",
        KARIERA_JC,
    ),
    (
        "Kariera.cz – hardware (ČR)",
        KARIERA_HW,
    ),
    (
        "Kariera.cz – hardware (Jihočeský kraj)",
        KARIERA_JC_HW,
    ),
    (
        "Aktuální nabídky práce (RSS)",
        AKTUALNI_NABIDKY_RSS,
    ),
    (
        "Práce pro OZP (RSS)",
        PRACE_PRO_OZP_RSS,
    ),
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


async def ensure_default_feeds(db: AsyncSession, user: User) -> int:
    """Doplní výchozí zdroje podle URL – i když už má uživatel jiné feedy."""
    result = await db.execute(select(FeedSource.url).where(FeedSource.user_id == user.id))
    existing = set(result.scalars().all())
    added = 0
    for title, url in DEFAULT_FEEDS:
        if url in existing:
            continue
        db.add(FeedSource(user_id=user.id, title=title, url=url, enabled=True))
        added += 1
    if added:
        await db.commit()
    return added


# zpětná kompatibilita
async def seed_default_feeds_if_empty(db: AsyncSession, user: User) -> int:
    return await ensure_default_feeds(db, user)
