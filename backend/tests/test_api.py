import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio

DATABASE_URL = os.getenv("DATABASE_URL", "")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.skipif("postgresql" not in DATABASE_URL, reason="Vyžaduje běžící PostgreSQL (DATABASE_URL)")
async def test_health_and_login_flow(client: AsyncClient):
    health = await client.get("/api/v1/system/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    email = os.getenv("ADMIN_EMAIL", "admin@localhost")
    password = os.getenv("ADMIN_PASSWORD", "change-me")
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    job = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test IT podpora",
            "company": "TestCo",
            "location": "Remote",
            "raw_text": "Linux, DNS, technická podpora",
            "source": "manual",
        },
    )
    assert job.status_code == 200
    job_id = job.json()["id"]

    dup = await client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Test IT podpora",
            "company": "TestCo",
            "location": "Remote",
            "raw_text": "Linux, DNS, technická podpora",
            "source": "manual",
        },
    )
    assert dup.status_code == 200
    assert dup.json()["duplicate_of_id"] == job_id

    ev = await client.post(
        f"/api/v1/jobs/{job_id}/evaluate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ev.status_code == 200
    assert 0 <= ev.json()["score"] <= 100

    resp = await client.post(
        f"/api/v1/jobs/{job_id}/generate-response",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["content"]) > 20

    app_row = await client.post(
        f"/api/v1/applications/from-job/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert app_row.status_code == 200
