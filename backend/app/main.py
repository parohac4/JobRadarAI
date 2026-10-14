import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.router import api_router
from app.config import get_settings
from app.middleware.cloudflare import CloudflareOnlyMiddleware
from app.database import AsyncSessionLocal, Base, engine
from app.database_migrations import patch_applications_snooze, patch_job_listings_inbox
from app.services.bootstrap import ensure_admin_user
from app.services.default_feeds import ensure_default_feeds
from app.services.demo_seed import seed_demo_if_empty
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

DEV_ORIGINS = ["http://localhost:5173", "http://localhost:8080", "http://127.0.0.1:5173", "http://127.0.0.1:8080"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await patch_job_listings_inbox(conn)
        await patch_applications_snooze(conn)
    async with AsyncSessionLocal() as session:
        await ensure_admin_user(session)
        user = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if user:
            await ensure_default_feeds(session, user)
        if get_settings().demo_mode:
            await seed_demo_if_empty(session)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="JobRadar AI",
        version="0.3.0",
        description="Automatizace hledání zaměstnání s AI hodnocením",
        lifespan=lifespan,
        root_path=settings.root_path,
        docs_url="/api/v1/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json" if settings.docs_enabled else None,
    )
    if not settings.is_production:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=DEV_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(CloudflareOnlyMiddleware)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
