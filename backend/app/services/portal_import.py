"""Bounded public HTML/RSS/API readers; no login or application submission."""
import asyncio
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import feedparser
from bs4 import BeautifulSoup

from app.models.enums import JobSource
from app.schemas.job import JobListingCreate
from app.services.rss_import import _fetch_feed, _entry_to_job
from app.services.sitprace_import import build_search_url, fetch_sitprace, _job_text
from app.services.places import nearby_centres, slug

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
        link = urlsplit(urljoin(url, a["href"]))
        canonical = urlunsplit((link.scheme, link.netloc, link.path, "", ""))
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
    base, path = ("https://www.jobs.cz", "prace") if key == "jobs" else ("https://www.prace.cz", "nabidky")
    for city in nearby_centres(home, config.radius_km):
        # Public municipality landing pages include local surroundings. The
        # final radius is always applied to the real workplace on our server.
        url = f"{base}/{path}/{slug(city)}/?{urlencode({'page': page})}"
        try:
            items.extend(parse_portal(await _fetch_feed(url), url))
        except Exception as exc:
            errors.append(f"{city}: {str(exc)[:180]}")
        await asyncio.sleep(0.3)
    if not items and errors:
        raise ValueError("; ".join(errors))
    return items, errors
