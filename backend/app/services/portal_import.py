"""Bounded public HTML/RSS/API readers; no login or application submission."""
import asyncio
import logging
import time
from urllib.parse import urlencode, urljoin, urlsplit

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.models.enums import JobSource
from app.schemas.job import JobListingCreate
from app.services.rss_import import _fetch_feed, _entry_to_job
from app.services.sitprace_import import build_search_url, fetch_sitprace, _job_text
from app.services.places import nearby_places, slug
from app.services.portal_urls import original_offer_url

logger = logging.getLogger("jobradar.portals")

# GeoNames admin1 codes -> region segments used by the public portal pages.
REGION_SLUGS = {
    "52": "praha", "78": "jihomoravsky", "79": "jihocesky", "80": "vysocina",
    "81": "karlovarsky", "82": "kralovehradecky", "83": "liberecky", "84": "olomoucky",
    "85": "moravskoslezsky", "86": "pardubicky", "87": "plzensky", "88": "stredocesky",
    "89": "ustecky", "90": "zlinsky",
}
_ROUTE_CACHE: dict[tuple, tuple[str, float]] = {}
ROUTE_TTL = 24 * 60 * 60


def locality_routes(key: str, place: dict) -> list[str]:
    city_slug = slug(place["name"])
    region = REGION_SLUGS.get(place.get("region"))
    if key == "jobs":
        routes = [f"https://www.jobs.cz/prace/{city_slug}/"]
        if region:
            routes.append(f"https://beta.jobs.cz/prace/{region}/{city_slug}/")
    else:
        routes = [f"https://www.prace.cz/nabidky/{city_slug}/"]
        if region:
            routes.append(f"https://www.prace.cz/nabidky/{region}/{city_slug}/")
    return routes


async def _read_with_retry(url: str) -> str:
    for attempt in range(2):
        try:
            return await _fetch_feed(url)
        except httpx.HTTPStatusError as exc:
            if attempt or exc.response.status_code not in (429, 500, 502, 503, 504):
                raise
            try:
                delay = max(2, int(exc.response.headers.get("Retry-After", "2")))
            except ValueError:
                # A date-based Retry-After is left to the next scheduled run.
                raise exc
            if delay > 5:
                raise
        except httpx.TransportError:
            if attempt:
                raise
            delay = 2
        await asyncio.sleep(delay)
    raise RuntimeError("Nedokončené načtení portálu")


async def fetch_locality(key: str, place: dict, page: int) -> list[JobListingCreate]:
    cache_key = (key, place["label"])
    routes = locality_routes(key, place)
    cached = _ROUTE_CACHE.get(cache_key)
    if cached and cached[1] > time.monotonic() and cached[0] in routes:
        routes.remove(cached[0])
        routes.insert(0, cached[0])
    last_error = None
    for route in routes:
        url = f"{route}?{urlencode({'page': page})}"
        try:
            body = await _read_with_retry(url)
            items = parse_portal(body, url)
            if len(_ROUTE_CACHE) >= 512 and cache_key not in _ROUTE_CACHE:
                _ROUTE_CACHE.pop(next(iter(_ROUTE_CACHE)))
            _ROUTE_CACHE[cache_key] = (route, time.monotonic() + ROUTE_TTL)
            return items
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in (404, 410):
                raise
            # Missing routes require another address, not repeated retries.
            if _ROUTE_CACHE.get(cache_key, (None,))[0] == route:
                _ROUTE_CACHE.pop(cache_key, None)
            logger.info("Missing %s locality route: %s", key, url)
    raise last_error or ValueError("Pro lokalitu není dostupná adresa portálu.")


def source_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (404, 410):
            return "Stránka lokality není dostupná ani na náhradní adrese. Další pokus proběhne při příští kontrole."
        if status == 429:
            return "Portál dočasně omezil počet požadavků. Sběr se zopakuje při příští kontrole."
        if status in (401, 403):
            return "Portál nepovolil automatické načtení. Ostatní zdroje se dál sledují."
        return f"Portál je dočasně nedostupný (HTTP {status}). Sběr se zopakuje při příští kontrole."
    if isinstance(exc, httpx.TransportError):
        return "Spojení s portálem se nepodařilo ani při opakovaném pokusu. Další pokus proběhne při příští kontrole."
    if isinstance(exc, ValueError):
        return str(exc)[:200]
    return "Zdroj se nepodařilo zpracovat. Další pokus proběhne při příští kontrole."

CATALOG = [
    {"id": "jobs", "name": "Jobs.cz", "description": "Odborné, kancelářské a technické pozice", "url": "https://www.jobs.cz/prace/"},
    {"id": "prace", "name": "Prace.cz", "description": "Regionální nabídky, provoz, služby a řemesla", "url": "https://www.prace.cz/nabidky/"},
    {"id": "sitprace", "name": "Síť práce / Úřad práce", "description": "Veřejné API, vlastní nabídky i data MPSV", "url": "https://sitprace.cz/pro-vyvojare"},
    {"id": "kariera", "name": "Kariera.cz", "description": "Doplňkový celostátní RSS zdroj", "url": "https://www.kariera.cz/prace/?format=rss"},
]
PORTAL_HOSTS = {"jobs.cz": "jobs", "prace.cz": "prace", "sitprace.cz": "sitprace", "kariera.cz": "kariera"}


def source_id(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return next((key for domain, key in PORTAL_HOSTS.items() if host == domain or host.endswith("." + domain)), "custom")


def parse_portal(body: str, url: str) -> list[JobListingCreate]:
    soup = BeautifulSoup(body, "html.parser")
    # A legacy listing URL can redirect to beta.jobs.cz, where relative links
    # belong to a different host. The listing advertises its effective base.
    base = url
    canonical_tag = soup.select_one('link[rel="canonical"][href]')
    if canonical_tag:
        candidate = urljoin(url, canonical_tag["href"])
        parsed_base = urlsplit(candidate)
        if (parsed_base.scheme in ("https", "http")
                and parsed_base.hostname in ("jobs.cz", "www.jobs.cz", "beta.jobs.cz", "prace.cz", "www.prace.cz")
                and source_id(candidate) == source_id(url)):
            base = candidate
    items = []
    for a in soup.select('a[data-jobad-id], a[data-testid="advert-link"]'):
        card = a.find_parent("article")
        if not card:
            continue
        loc = card.select_one('[data-test="serp-locality"]')
        company = card.select_one('.SearchResultCard__footerItem span[translate="no"]')
        location = loc.get_text(" ", strip=True) if loc else ""
        company_text = company.get_text(" ", strip=True) if company else ""
        for hidden in card.select("span.accessibility-hidden"):
            label = hidden.get_text(" ", strip=True).rstrip(" :")
            if label in ("Lokalita", "Název firmy"):
                value = hidden.find_next_sibling("span")
                if value:
                    if label == "Lokalita":
                        location = value.get_text(" ", strip=True)
                    else:
                        company_text = value.get_text(" ", strip=True)
        canonical = original_offer_url(urljoin(base, a["href"]))
        if source_id(canonical) != source_id(url):
            continue
        items.append(JobListingCreate(title=a.get_text(" ", strip=True)[:500], company=company_text[:300],
            location=location[:300], url=canonical[:2000], raw_text=card.get_text(" ", strip=True)[:50000], source=JobSource.api))
    if not items and not any(marker in soup.get_text(" ", strip=True).lower() for marker in
                             ("nenašli", "žádné nabídky", "žádná nabídka", "0 nabídek", "0 nabídk")):
        raise ValueError("Portál nevrátil rozpoznatelný seznam nabídek (změna stránky nebo ochrana přístupu).")
    return items


async def fetch_source(key: str, config, home: dict, *, page: int = 1) -> tuple[list[JobListingCreate], list[str]]:
    items, errors = [], []
    if key == "sitprace":
        url = build_search_url(query=config.keywords, city=home["name"], radius_km=config.radius_km)
        for j in await fetch_sitprace(url):
            items.append(JobListingCreate(title=(j.get("title") or "Nabídka")[:500], company=(j.get("company") or "")[:300],
                location=(j.get("city") or "")[:300], url=(j.get("url") or "")[:2000], raw_text=_job_text(j), source=JobSource.api))
        return items, errors
    if key == "kariera" or key.startswith("custom:"):
        url = "https://www.kariera.cz/prace/?format=rss" if key == "kariera" else key.removeprefix("custom:")
        parsed = feedparser.parse(await _fetch_feed(url))
        if not parsed.entries:
            raise ValueError("Zdroj nevrátil položky RSS/Atom.")
        for e in parsed.entries[:100]:
            job = _entry_to_job(e)
            job.raw_text = BeautifulSoup(job.raw_text, "html.parser").get_text(" ", strip=True)
            job.location = str(e.get("location") or e.get("job_location") or "")[:300]
            if not job.location:
                # RSS often puts the locality in the title: 'Role - City'.
                job.location = job.title.rsplit(" - ", 1)[-1] if " - " in job.title else ""
            items.append(job)
        return items, errors
    for place in nearby_places(home, config.radius_km):
        # Public municipality landing pages include local surroundings. The
        # final radius is always applied to the real workplace on our server.
        try:
            items.extend(await fetch_locality(key, place, page))
        except Exception as exc:
            logger.warning("Locality import failed: %s / %s", key, place["label"], exc_info=True)
            errors.append(f"{place['name']}: {source_error(exc)}")
            if isinstance(exc, httpx.TransportError) or (
                isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (401, 403, 429, 503)
            ):
                errors.append("Zbývající lokality tohoto portálu zkusím při příští kontrole.")
                break
        await asyncio.sleep(0.3)
    if not items and errors:
        raise ValueError("; ".join(errors))
    return items, errors
