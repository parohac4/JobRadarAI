"""Doplňující DDL pro existující DB (create_all nepřidává sloupce)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def patch_applications_snooze(conn: AsyncConnection) -> None:
    await conn.execute(
        text(
            """
            ALTER TABLE applications
                ADD COLUMN IF NOT EXISTS snooze_note TEXT NOT NULL DEFAULT '';
            """
        )
    )


async def patch_job_listings_inbox(conn: AsyncConnection) -> None:
    await conn.execute(
        text(
            """
            ALTER TABLE job_listings
                ADD COLUMN IF NOT EXISTS inbox_status VARCHAR(20) NOT NULL DEFAULT 'active',
                ADD COLUMN IF NOT EXISTS snoozed_until TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS snooze_note TEXT NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS dismissed_at TIMESTAMPTZ,
                ADD COLUMN IF NOT EXISTS dismissed_note TEXT NOT NULL DEFAULT '';
            """
        )
    )
