import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.enums import JobSource


def extract_from_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    company = ""
    host = urlparse(url).netloc.replace("www.", "")
    if host:
        company = host.split(".")[0].capitalize()

    return {
        "title": title or "Neznámá pozice",
        "company": company,
        "location": "",
        "raw_text": text[:50000],
        "url": url,
        "source": JobSource.url,
    }


async def fetch_job_from_url(url: str) -> dict:
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        resp = await client.get(
            url,
            headers={
                "User-Agent": "JobRadarAI/1.0 (+https://github.com/jobradar-ai; job search assistant)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        resp.raise_for_status()
    return extract_from_html(resp.text, url)


def parse_job_email(subject: str, body: str) -> dict:
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    title = subject.strip() or "Pozice z e-mailu"
    url = ""
    for line in lines:
        m = re.search(r"https?://[^\s<>\"']+", line)
        if m:
            url = m.group(0).rstrip(").,]")
            break
    company = ""
    for line in lines[:15]:
        if re.search(r"(společnost|firma|company)\s*[:]", line, re.I):
            company = re.split(r"[:]", line, maxsplit=1)[-1].strip()
            break
    location = ""
    for line in lines[:20]:
        if re.search(r"(lokace|místo|location)\s*[:]", line, re.I):
            location = re.split(r"[:]", line, maxsplit=1)[-1].strip()
            break
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "raw_text": body[:50000],
        "source": JobSource.email,
    }
