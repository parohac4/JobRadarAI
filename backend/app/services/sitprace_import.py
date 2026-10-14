import logging
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobSource
from app.models.user import User
from app.schemas.job import JobListingCreate
from app.services import jobs as job_service
from app.services.job_import import assert_public_url

logger = logging.getLogger("jobradar.sitprace")

SITPRACE_BASE = "https://sitprace.cz/api/public/jobs"


def _job_text(job: dict) -> str:
    parts = [
        job.get("title") or "",
        f"Firma: {job.get('company') or 'neuvedeno'}",
        f"Lokalita: {job.get('city') or ''} {job.get('region') or ''}".strip(),
    ]
    sal_min, sal_max = job.get("salary_min"), job.get("salary_max")
    if sal_min or sal_max:
        parts.append(f"Plat: {sal_min or '?'}-{sal_max or '?'} {job.get('salary_currency') or 'CZK'}")
    if job.get("job_type"):
        parts.append(f"Typ: {job['job_type']}")
    if job.get("location_type"):
        parts.append(f"Místo práce: {job['location_type']}")
    parts.append(f"Zdroj: sitprace.cz · {job.get('url') or ''}")
    parts.append(
        "\n(Podrobný popis pozice je na odkazu – v JobRadaru můžete spustit import z URL pro celý text inzerátu.)"
    )
    return "\n".join(parts)[:50000]


async def fetch_sitprace(url: str) -> list[dict]:
    await assert_public_url(url)
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        resp = await client.get(
            url,
            headers={"User-Agent": "JobRadarAI/0.3 (+https://github.com/parohac4/JobRadarAI)", "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
    if "jobs" in data:
        return list(data["jobs"])
    if url.rstrip("/").endswith("latest.json"):
        return list(data.get("jobs") or [])
    return []


async def import_from_url(db: AsyncSession, user: User, url: str) -> tuple[int, int, list[int]]:
    created = dup = 0
    new_ids: list[int] = []
    try:
        items = await fetch_sitprace(url)
    except Exception:
        logger.exception("Sitprace fetch %s", url)
        raise
    for job in items:
        link = (job.get("url") or "").strip()
        if link:
            try:
                await assert_public_url(link)
            except Exception:
                continue
        location = ", ".join(filter(None, [job.get("city"), job.get("region")]))
        data = JobListingCreate(
            title=(job.get("title") or "Pozice ze Sítě práce")[:500],
            company=(job.get("company") or "")[:300],
            location=location[:300],
            url=link[:2000],
            raw_text=_job_text(job),
            source=JobSource.api,
        )
        row, duplicate = await job_service.create_job(db, user.id, data)
        if duplicate:
            dup += 1
        else:
            created += 1
            new_ids.append(row.id)
    return created, dup, new_ids


def build_search_url(
    *,
    query: str,
    city: str = "",
    radius_km: int = 80,
    category: str = "",
    limit: int = 50,
) -> str:
    params: dict[str, str | int] = {"query": query, "limit": limit}
    if city:
        params["city"] = city
        params["radius_km"] = radius_km
    if category:
        params["category"] = category
    return f"{SITPRACE_BASE}/search.json?{urlencode(params)}"
