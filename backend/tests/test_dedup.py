from app.services.dedup import content_hash, normalize_url, url_hash


def test_url_normalization():
    assert normalize_url("https://www.jobs.cz/offer/123/") == normalize_url("https://jobs.cz/offer/123")


def test_hashes_stable():
    h1 = content_hash("IT podpora", "Firma", "České Budějovice")
    h2 = content_hash("it   podpora", "firma", "české budějovice")
    assert h1 == h2
    assert url_hash("https://example.com/a") == url_hash("https://www.example.com/a/")
