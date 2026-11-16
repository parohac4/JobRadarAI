"""Plánovaný worker – IMAP a RSS synchronizace."""

import asyncio
import logging

from app.config import get_settings
from app.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.user import User
from app.services.aggregator import monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("jobradar.worker")


async def tick() -> None:
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
        for user in users:
            try:
                result = await monitor(db, user)
                await db.commit()
                logger.info("Sběr user=%s: %s", user.id, result.get("status"))
            except Exception:
                await db.rollback()
                logger.exception("Sběr user=%s selhal", user.id)


async def main() -> None:
    settings = get_settings()
    if not settings.worker_enabled:
        logger.info("WORKER_ENABLED=false, ukončuji")
        return
    interval = 60  # Each user's saved interval is checked by monitor().
    logger.info("Worker běží, interval %s s", interval)
    while True:
        try:
            await tick()
        except Exception:
            logger.exception("Sync cyklus selhal")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
