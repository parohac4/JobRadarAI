import hashlib
import re
from urllib.parse import urlparse

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobListing


def normalize_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip().lower())
    host = parsed.netloc.replace("www.", "")
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def content_hash(title: str, company: str, location: str) -> str:
    key = "|".join(
        [
            re.sub(r"\s+", " ", (title or "").lower().strip()),
            re.sub(r"\s+", " ", (company or "").lower().strip()),
            re.sub(r"\s+", " ", (location or "").lower().strip()),
        ]
    )
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
        found = result.scalar_one_or_none()
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
    found = result.scalar_one_or_none()
    if found:
        return found

    result = await db.execute(
        select(JobListing).where(
            JobListing.user_id == user_id,
            JobListing.duplicate_of_id.is_(None),
        )
    )
    for job in result.scalars().all():
        score = fuzz.token_set_ratio(
            f"{title} {company}",
            f"{job.title} {job.company}",
        )
        if score >= 92:
            return job
    return None
