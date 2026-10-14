import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobListing

FUZZY_TITLE_THRESHOLD = 90


TRACKING_PARAMS = {"fbclid", "gclid", "ref", "source", "rps"}


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    params = sorted(
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    )
    query = f"?{urlencode(params)}" if params else ""
    return f"{host}{path}{query}"


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def content_hash(title: str, company: str, location: str) -> str:
    key = "|".join([_normalize(title), _normalize(company), _normalize(location)])
    return hashlib.sha256(key.encode()).hexdigest()


async def find_duplicate(
    db: AsyncSession,
    user_id: int,
    *,
    title: str,
    company: str,
    location: str,
    url: str,
) -> JobListing | None:
    if url:
        uh = url_hash(url)
        result = await db.execute(
            select(JobListing).where(
                JobListing.user_id == user_id,
                JobListing.url_hash == uh,
                JobListing.duplicate_of_id.is_(None),
            )
        )
        found = result.scalars().first()
        if found:
            return found

    ch = content_hash(title, company, location)
    result = await db.execute(
        select(JobListing).where(
            JobListing.user_id == user_id,
            JobListing.content_hash == ch,
            JobListing.duplicate_of_id.is_(None),
        )
    )
    found = result.scalars().first()
    if found:
        return found

    company_key = _normalize(company)
    if not company_key:
        return None
    result = await db.execute(
        select(JobListing).where(
            JobListing.user_id == user_id,
            JobListing.duplicate_of_id.is_(None),
        )
    )
    for job in result.scalars().all():
        if _normalize(job.company) == company_key and is_similar_title(title, job.title):
            return job
    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower().strip())


def is_similar_title(a: str, b: str) -> bool:
    return fuzz.token_sort_ratio(_normalize(a), _normalize(b)) >= FUZZY_TITLE_THRESHOLD
