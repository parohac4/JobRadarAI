"""Doplní title_company_hash u starších záznamů (pro lepší slučování při importu)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import JobListing
from app.services.dedup import title_company_hash


async def backfill_title_company_hashes(db: AsyncSession, *, limit: int = 2000) -> int:
    result = await db.execute(
        select(JobListing).where(JobListing.title_company_hash == "").limit(limit)
    )
    updated = 0
    for job in result.scalars().all():
        tc = title_company_hash(job.title, job.company)
        if tc:
            job.title_company_hash = tc
            updated += 1
    if updated:
        await db.commit()
    return updated
