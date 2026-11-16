from unittest.mock import AsyncMock

import httpx
import pytest

from app.schemas.aggregator import SearchSettings
from app.services import portal_import as portals
from app.services.places import resolve_place

EMPTY_PAGE = "<h1>Žádné nabídky</h1>"


def http_error(url, status, headers=None):
    return httpx.HTTPStatusError("Technical details must stay in logs", request=httpx.Request("GET", url),
        response=httpx.Response(status, headers=headers, request=httpx.Request("GET", url)))


@pytest.fixture(autouse=True)
def clear_routes():
    portals._ROUTE_CACHE.clear()
    yield
    portals._ROUTE_CACHE.clear()


@pytest.mark.parametrize("city,region", [("Sušice", "plzensky"), ("Vimperk", "jihocesky")])
async def test_missing_locality_uses_regional_route_and_remembers_it(monkeypatch, city, region):
    place = resolve_place(city)
    primary, fallback = portals.locality_routes("jobs", place)
    assert f"/{region}/" in fallback
    calls = []
    async def read(url):
        calls.append(url)
        if url.startswith(primary):
            raise http_error(url, 404)
        return EMPTY_PAGE
    monkeypatch.setattr(portals, "_fetch_feed", read)
    assert await portals.fetch_locality("jobs", place, 1) == []
    assert calls == [primary + "?page=1", fallback + "?page=1"]
    calls.clear()
    await portals.fetch_locality("jobs", place, 2)
    assert calls == [fallback + "?page=2"]


async def test_cached_address_is_replaced_if_it_disappears(monkeypatch):
    place = resolve_place("Vimperk")
    primary, fallback = portals.locality_routes("jobs", place)
    import time
    portals._ROUTE_CACHE[("jobs", place["label"])] = (fallback, time.monotonic() + 60)
    calls = []
    async def read(url):
        calls.append(url)
        if url.startswith(fallback):
            raise http_error(url, 410)
        return EMPTY_PAGE
    monkeypatch.setattr(portals, "_fetch_feed", read)
    await portals.fetch_locality("jobs", place, 1)
    assert calls == [fallback + "?page=1", primary + "?page=1"]
    assert portals._ROUTE_CACHE[("jobs", place["label"])][0] == primary


async def test_temporary_failure_is_retried_once(monkeypatch):
    read = AsyncMock(side_effect=[http_error("https://www.jobs.cz/prace/", 503), EMPTY_PAGE])
    pause = AsyncMock()
    monkeypatch.setattr(portals, "_fetch_feed", read)
    monkeypatch.setattr(portals.asyncio, "sleep", pause)
    assert await portals._read_with_retry("https://www.jobs.cz/prace/") == EMPTY_PAGE
    assert read.await_count == 2
    pause.assert_awaited_once_with(2)


async def test_long_rate_limit_stops_remaining_localities(monkeypatch):
    read = AsyncMock(side_effect=http_error("https://www.jobs.cz/prace/", 429, {"Retry-After": "120"}))
    monkeypatch.setattr(portals, "_fetch_feed", read)
    with pytest.raises(ValueError) as caught:
        await portals.fetch_source("jobs", SearchSettings(), resolve_place("Strakonice"))
    assert read.await_count == 1
    assert "omezil počet požadavků" in str(caught.value)
    assert "Zbývající lokality" in str(caught.value)
    assert "developer.mozilla" not in str(caught.value)


async def test_unavailable_city_keeps_other_city_results(monkeypatch):
    home = resolve_place("Strakonice")
    other = resolve_place("Vimperk")
    monkeypatch.setattr(portals, "nearby_places", lambda *args: [other, home])
    body = '''<article><a data-jobad-id="1" href="https://www.jobs.cz/rpd/1/">Technik</a>
              <li data-test="serp-locality">Strakonice</li></article>'''
    async def read(url):
        if "vimperk" in url:
            raise http_error(url, 404)
        return body
    monkeypatch.setattr(portals, "_fetch_feed", read)
    monkeypatch.setattr(portals.asyncio, "sleep", AsyncMock())
    jobs, errors = await portals.fetch_source("jobs", SearchSettings(), home)
    assert len(jobs) == 1 and jobs[0].title == "Technik"
    assert len(errors) == 1 and errors[0].startswith("Vimperk:")
    assert "náhradní adrese" in errors[0]
    assert "Technical details" not in errors[0]


async def test_forbidden_access_does_not_trigger_other_routes(monkeypatch):
    read = AsyncMock(side_effect=http_error("https://www.jobs.cz/prace/", 403))
    monkeypatch.setattr(portals, "_fetch_feed", read)
    with pytest.raises(httpx.HTTPStatusError):
        await portals.fetch_locality("jobs", resolve_place("Vimperk"), 1)
    read.assert_awaited_once()
