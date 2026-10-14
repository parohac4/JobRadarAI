import asyncio
import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.models.enums import JobSource

USER_AGENT = "JobRadarAI/0.1 (+https://github.com/parohac4/JobRadarAI; osobni asistent hledani prace)"
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5


class UnsafeUrlError(ValueError):
    pass


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return ip.is_global and not ip.is_multicast


async def assert_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError("Povoleny jsou jen adresy http:// a https://")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("Adresa neobsahuje hostitele")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Doménu {host} nelze přeložit") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses or not all(_is_public_ip(a) for a in addresses):
        raise UnsafeUrlError("Adresa míří do interní nebo neveřejné sítě")


def extract_from_html(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = ""
    h1 = soup.find("h1")
    og = soup.find("meta", property="og:title")
    if h1 and h1.get_text(strip=True):
        title = h1.get_text(strip=True)
    elif og and og.get("content"):
        title = og["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return {
        "title": title[:500] or "Neznámá pozice",
        "company": "",
        "location": "",
        "raw_text": text[:50000],
        "url": url,
        "source": JobSource.url,
    }


async def fetch_job_from_url(url: str) -> dict:
    current = url.strip()
    async with httpx.AsyncClient(follow_redirects=False, timeout=20.0) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await assert_public_url(current)
            async with client.stream(
                "GET",
                current,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            ) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        raise UnsafeUrlError("Přesměrování bez cílové adresy")
                    current = urljoin(current, location)
                    continue
                resp.raise_for_status()
                body = bytearray()
                async for chunk in resp.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise UnsafeUrlError("Stránka je příliš velká")
                html = body.decode(resp.encoding or "utf-8", errors="replace")
                return extract_from_html(html, current)
    raise UnsafeUrlError("Příliš mnoho přesměrování")


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
        if re.search(r"(společnost|firma|zaměstnavatel|company)\s*:", line, re.I):
            company = line.split(":", 1)[-1].strip()
            break
    location = ""
    for line in lines[:20]:
        if re.search(r"(lokace|lokalita|místo|location)\s*:", line, re.I):
            location = line.split(":", 1)[-1].strip()
            break
    return {
        "title": title[:500],
        "company": company[:300],
        "location": location[:300],
        "url": url[:2000],
        "raw_text": body[:50000],
        "source": JobSource.email,
    }
