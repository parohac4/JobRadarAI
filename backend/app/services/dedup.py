import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobListing

FUZZY_TITLE_THRESHOLD = 90
FUZZY_COMPANY_THRESHOLD = 88

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


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower().strip())


def _normalize_company(company: str) -> str:
    c = _normalize(company)
    c = re.sub(r"\b(a\.?\s*s\.?|s\.?\s*r\.?\s*o\.?|spol\.\s*s\s*r\.?\s*o\.?)\b", "", c)
    return re.sub(r"\s+", " ", c).strip()


def content_hash(title: str, company: str, location: str) -> str:
    key = "|".join([_normalize(title), _normalize(company), _normalize(location)])
    return hashlib.sha256(key.encode()).hexdigest()


def title_company_hash(title: str, company: str) -> str:
    """Stejná pozice u jiného portálu (jiná URL, jiná lokalita v textu)."""
    key = "|".join([_normalize(title), _normalize_company(company)])
    if key == "|" or not _normalize(title):
        return ""
    return hashlib.sha256(key.encode()).hexdigest()


def is_similar_title(a: str, b: str) -> bool:
    return fuzz.token_sort_ratio(_normalize(a), _normalize(b)) >= FUZZY_TITLE_THRESHOLD


def is_similar_company(a: str, b: str) -> bool:
    na, nb = _normalize_company(a), _normalize_company(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return fuzz.token_sort_ratio(na, nb) >= FUZZY_COMPANY_THRESHOLD


def _locations_overlap(a: str, b: str) -> bool:
    la, lb = _normalize(a), _normalize(b)
    if not la or not lb:
        return True
    if la == lb:
        return True
    return la in lb or lb in la


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

    tc = title_company_hash(title, company)
    if tc:
        result = await db.execute(
            select(JobListing).where(
                JobListing.user_id == user_id,
                JobListing.title_company_hash == tc,
                JobListing.duplicate_of_id.is_(None),
            )
        )
        found = result.scalars().first()
        if found:
            return found

    result = await db.execute(
        select(JobListing).where(
            JobListing.user_id == user_id,
            JobListing.duplicate_of_id.is_(None),
        )
    )
    for job in result.scalars().all():
        if not is_similar_title(title, job.title):
            continue
        if is_similar_company(company, job.company):
            return job
        if _locations_overlap(location, job.location) and (
            not _normalize_company(company) or not _normalize_company(job.company)
        ):
            return job
    return None
