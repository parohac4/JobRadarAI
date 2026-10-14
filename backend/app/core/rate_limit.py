import time
from collections import defaultdict, deque

from fastapi import Request


class FailureLimiter:
    """Počítá neúspěšné pokusy v klouzavém okně. Stav je v paměti procesu (jeden worker)."""

    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._failures[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        return bucket

    def is_blocked(self, *keys: str) -> bool:
        now = time.monotonic()
        return any(len(self._prune(k, now)) >= self.max_failures for k in keys)

    def record_failure(self, *keys: str) -> None:
        now = time.monotonic()
        for k in keys:
            self._prune(k, now).append(now)

    def reset(self, *keys: str) -> None:
        for k in keys:
            self._failures.pop(k, None)


def client_ip(request: Request) -> str:
    # Za Cloudflare je skutečná IP v CF-Connecting-IP; hlavičku lze podvrhnout při přímém
    # přístupu na origin, proto limit platí zároveň i pro cílový e-mail.
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
