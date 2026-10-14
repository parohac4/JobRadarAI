import logging
from datetime import UTC, datetime

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobSource
from app.models.feed_source import FeedSource
from app.models.user import User
from app.schemas.job import JobListingCreate
from app.services import jobs as job_service
from app.services.job_import import UnsafeUrlError, assert_public_url
from app.services.sitprace_import import import_from_url as sitprace_import_from_url

logger = logging.getLogger("jobradar.rss")
MAX_FEED_BYTES = 2_000_000


async def _fetch_feed(url: str) -> str:
    await assert_public_url(url)
    async with httpx.AsyncClient(follow_redirects=False, timeout=30.0) as client:
        current = url
        for _ in range(5):
            resp = await client.get(
                current,
                headers={"User-Agent": "JobRadarAI/0.3 (+https://github.com/parohac4/JobRadarAI)"},
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                if not loc:
                    break
                await assert_public_url(loc)
                current = loc
                continue
            resp.raise_for_status()
            if len(resp.content) > MAX_FEED_BYTES:
                raise ValueError("RSS feed je příliš velký")
            return resp.text
    raise ValueError("Příliš mnoho přesměrování")


def _entry_to_job(entry: feedparser.FeedParserDict) -> JobListingCreate:
    title = (entry.get("title") or "Pozice z RSS").strip()[:500]
    link = (entry.get("link") or "").strip()[:2000]
    summary = entry.get("summary") or entry.get("description") or ""
    if hasattr(summary, "value"):
        summary = summary.value
    raw = str(summary)[:50000]
    company = ""
    if entry.get("author"):
        company = str(entry.author)[:300]
    return JobListingCreate(
        title=title,
        company=company,
        location="",
        url=link,
        raw_text=raw or title,
        source=JobSource.rss,
    )


async def sync_rss_for_user(db: AsyncSession, user: User) -> dict:
    result = await db.execute(
        select(FeedSource).where(FeedSource.user_id == user.id, FeedSource.enabled.is_(True))
    )
    feeds = list(result.scalars().all())
    if not feeds:
        return {"feeds": 0, "created": 0, "duplicates": 0}

    total_created = 0
    total_dup = 0
    new_job_ids: list[int] = []
    errors: list[str] = []

    for feed in feeds:
        try:
            if "sitprace.cz/api/public/jobs" in feed.url:
                created, dup, new_ids = await sitprace_import_from_url(db, user, feed.url)
                feed.last_fetched_at = datetime.now(UTC)
                feed.last_error = ""
                total_created += created
                total_dup += dup
                new_job_ids.extend(new_ids)
                continue
            body = await _fetch_feed(feed.url)
            parsed = feedparser.parse(body)
            if parsed.bozo and not parsed.entries:
                raise ValueError(str(parsed.bozo_exception)[:200])
            created = dup = 0
            for entry in parsed.entries[:50]:
                try:
                    data = _entry_to_job(entry)
                    if data.url:
                        await assert_public_url(data.url)
                    job, duplicate = await job_service.create_job(db, user.id, data)
                    if duplicate:
                        dup += 1
                    else:
                        created += 1
                        new_job_ids.append(job.id)
                except (UnsafeUrlError, ValueError) as e:
                    logger.debug("RSS položka přeskočena: %s", e)
            feed.last_fetched_at = datetime.now(UTC)
            feed.last_error = ""
            total_created += created
            total_dup += dup
        except Exception as e:
            logger.exception("RSS feed %s", feed.url)
            feed.last_error = str(e)[:500]
            errors.append(f"{feed.title or feed.url}: {e}")

    await db.commit()
    return {
        "feeds": len(feeds),
        "created": total_created,
        "duplicates": total_dup,
        "errors": errors,
        "new_job_ids": new_job_ids,
    }
