import pytest

from app.core.rate_limit import FailureLimiter
from app.services.job_import import UnsafeUrlError, assert_public_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/api",
        "http://localhost/",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data",
        "ftp://example.com/file",
        "file:///etc/passwd",
    ],
)
async def test_import_rejects_internal_urls(url):
    with pytest.raises(UnsafeUrlError):
        await assert_public_url(url)


def test_failure_limiter_blocks_after_threshold():
    limiter = FailureLimiter(max_failures=3, window_seconds=60)
    for _ in range(3):
        assert not limiter.is_blocked("email:a")
        limiter.record_failure("email:a", "ip:1")
    assert limiter.is_blocked("email:a")
    assert limiter.is_blocked("ip:1")
    limiter.reset("email:a", "ip:1")
    assert not limiter.is_blocked("email:a")
