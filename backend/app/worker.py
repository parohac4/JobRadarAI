"""Plánovaný worker – IMAP a RSS synchronizace."""

import asyncio
import logging

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.services.sync_orchestrator import run_all_syncs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("jobradar.worker")


async def tick() -> None:
    async with AsyncSessionLocal() as db:
        result = await run_all_syncs(db)
        logger.info("Sync dokončen: %s", result)


async def main() -> None:
    settings = get_settings()
    if not settings.worker_enabled:
        logger.info("WORKER_ENABLED=false, ukončuji")
        return
    interval = max(60, settings.sync_interval_seconds)
    logger.info("Worker běží, interval %s s", interval)
    while True:
        try:
            await tick()
        except Exception:
            logger.exception("Sync cyklus selhal")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
