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
    assert (await client.get("/api/v1/jobs")).status_code == 401


async def test_full_job_flow(client: AsyncClient):
    auth = await _token(client)
    payload = {
        "title": f"IT podpora {uuid.uuid4().hex[:8]}",
        "company": "TestCo",
        "location": "Remote",
        "raw_text": "Požadujeme Linux a DNS. Technická podpora zákazníků.",
        "source": "manual",
    }

    job = await client.post("/api/v1/jobs", headers=auth, json=payload)
    assert job.status_code == 200, job.text
    job_id = job.json()["id"]
    assert job.json()["duplicate_of_id"] is None

    dup = await client.post("/api/v1/jobs", headers=auth, json=payload)
    assert dup.json()["duplicate_of_id"] == job_id

    ev = await client.post(f"/api/v1/jobs/{job_id}/evaluate", headers=auth)
    assert ev.status_code == 200, ev.text
    assert 0 <= ev.json()["score"] <= 100
    assert ev.json()["reasons"]

    detail = await client.get(f"/api/v1/jobs/{job_id}", headers=auth)
    assert detail.json()["latest_score"] == ev.json()["score"]

    resp = await client.post(f"/api/v1/jobs/{job_id}/generate-response", headers=auth)
    assert resp.status_code == 200
    drafts = await client.get(f"/api/v1/jobs/{job_id}/responses", headers=auth)
    assert drafts.json()[0]["content"] == resp.json()["content"]

    app_row = await client.post(f"/api/v1/applications/from-job/{job_id}", headers=auth)
    assert app_row.status_code == 200, app_row.text
    app_id = app_row.json()["id"]
    again = await client.post(f"/api/v1/applications/from-job/{job_id}", headers=auth)
    assert again.status_code == 409

    upd = await client.patch(
        f"/api/v1/applications/{app_id}/status", headers=auth, json={"status": "sent", "note": "Odesláno"}
    )
    assert upd.json()["status"] == "sent"
    hist = await client.get(f"/api/v1/applications/{app_id}/history", headers=auth)
    assert [h["to_status"] for h in hist.json()] == ["sent", "new_offer"]

    await client.post(f"/api/v1/applications/{app_id}/notes", headers=auth, json={"body": "Zavolat v pátek"})
    notes = await client.get(f"/api/v1/applications/{app_id}/notes", headers=auth)
    assert notes.json()[0]["body"] == "Zavolat v pátek"


async def test_import_url_blocks_internal_address(client: AsyncClient):
    auth = await _token(client)
    resp = await client.post("/api/v1/jobs/import/url", headers=auth, json={"url": "http://127.0.0.1:8000/"})
    assert resp.status_code == 400


async def test_login_rate_limit(client: AsyncClient):
    from app.api.v1.auth import login_limiter

    email = f"nobody-{uuid.uuid4().hex[:6]}@test.local"
    codes = []
    for _ in range(login_limiter.max_failures + 1):
        r = await client.post("/api/v1/auth/login", data={"username": email, "password": "x"})
        codes.append(r.status_code)
    assert codes[-1] == 429
    login_limiter.reset(f"email:{email}", "ip:127.0.0.1")
