"""Keep original advertisement URLs functional across the Jobs.cz migration."""
import re
from urllib.parse import urlsplit, urlunsplit

_UUID = r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}"
_MODERN_JOBS_PATH = re.compile(rf"/(?:firma/[^/]+/)?nabidka/{_UUID}/?", re.IGNORECASE)


def original_offer_url(url: str) -> str:
    """Repair previously stored new-format paths on the legacy Jobs.cz host.

    Numeric /rpd/ links, employer subdomains and other portals stay intact.
    Query parameters may identify the advertisement and must be preserved.
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        return url
    if (parsed.scheme in ("http", "https") and parsed.hostname in ("jobs.cz", "www.jobs.cz")
            and _MODERN_JOBS_PATH.fullmatch(parsed.path)):
        return urlunsplit(("https", "beta.jobs.cz", parsed.path, parsed.query, parsed.fragment))
    return url
