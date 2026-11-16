import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

DATABASE_URL = os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    "postgresql" not in DATABASE_URL, reason="Vyžaduje běžící PostgreSQL (DATABASE_URL)"
)


@pytest.fixture
async def client():
    from app.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def _token(client: AsyncClient) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_health(client: AsyncClient):
    resp = await client.get("/api/v1/system/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_requires_auth(client: AsyncClient):
    assert (await client.get("/api/v1/aggregate/jobs")).status_code == 401


async def test_saved_search_and_offers(client: AsyncClient):
    auth = await _token(client)
    original = (await client.get("/api/v1/aggregate/settings", headers=auth)).json()["settings"]
    config = {**original, "city": "Strakonice", "radius_km": 30, "ai_enabled": False,
              "sources": ["jobs", "prace", "sitprace"], "custom_feeds": []}
    try:
        response = await client.put("/api/v1/aggregate/settings", headers=auth, json=config)
        assert response.status_code == 200, response.text
        listing = await client.get("/api/v1/aggregate/jobs?sort=distance&limit=10", headers=auth)
        assert listing.status_code == 200, listing.text
        assert "items" in listing.json() and "total" in listing.json()
        places = await client.get("/api/v1/aggregate/places?q=Volyn", headers=auth)
        assert places.status_code == 200 and places.json()["items"]
        assert (await client.post("/api/v1/applications/from-job/1", headers=auth)).status_code == 404
        assert (await client.post("/api/v1/jobs/1/generate-response", headers=auth)).status_code == 404
    finally:
        restored = await client.put("/api/v1/aggregate/settings", headers=auth, json=original)
        assert restored.status_code == 200


async def test_custom_feed_blocks_internal_address(client: AsyncClient):
    auth = await _token(client)
    config = (await client.get("/api/v1/aggregate/settings", headers=auth)).json()["settings"]
    config["custom_feeds"] = [{"title": "Internal", "url": "http://127.0.0.1:8000/rss", "enabled": True}]
    response = await client.put("/api/v1/aggregate/settings", headers=auth, json=config)
    assert response.status_code == 400


async def test_login_rate_limit(client: AsyncClient):
    from app.api.v1.auth import login_limiter

    email = f"nobody-{uuid.uuid4().hex[:6]}@test.local"
    codes = []
    for _ in range(login_limiter.max_failures + 1):
        r = await client.post("/api/v1/auth/login", data={"username": email, "password": "x"})
        codes.append(r.status_code)
    assert codes[-1] == 429
    login_limiter.reset(f"email:{email}", "ip:127.0.0.1")


async def test_interaction_persists_in_postgresql(client: AsyncClient):
    from sqlalchemy import delete, select
    from app.database import AsyncSessionLocal
    from app.models.job import JobListing
    from app.models.user import User
    from app.schemas.job import JobListingCreate
    from app.services.jobs import create_job

    auth = await _token(client)
    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == os.environ['ADMIN_EMAIL']))).scalar_one()
        job, _ = await create_job(db, user.id, JobListingCreate(
            title=f'Test označení {uuid.uuid4().hex}', company='Test', location='Strakonice',
            url=f'https://www.jobs.cz/rpd/test-{uuid.uuid4().hex}/', raw_text='Testovací nabídka', source='api'))
        await db.commit()
        job_id = job.id
    try:
        path = f'/api/v1/aggregate/jobs/{job_id}/interaction'
        marked = await client.patch(path, headers=auth, json={'marked': True})
        assert marked.status_code == 200 and marked.json()['marked']
        viewed = await client.patch(path, headers=auth, json={'seen': True})
        assert viewed.status_code == 200 and viewed.json()['seen_at'] and viewed.json()['marked']
        again = await client.patch(path, headers=auth, json={'seen': True})
        assert again.json()['seen_at'] == viewed.json()['seen_at']
        detail = await client.get(f'/api/v1/aggregate/jobs/{job_id}', headers=auth)
        assert detail.json()['marked'] and detail.json()['seen_at']
        unseen = await client.patch(path, headers=auth, json={'seen': False})
        assert unseen.json()['seen_at'] is None and unseen.json()['marked']
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(JobListing).where(JobListing.id == job_id))
            await db.commit()
