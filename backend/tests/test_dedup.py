from app.services.dedup import content_hash, is_similar_title, normalize_url, url_hash


def test_url_normalization():
    assert normalize_url("https://www.jobs.cz/offer/123/") == normalize_url("https://jobs.cz/offer/123")


def test_url_keeps_identifying_query_and_drops_tracking():
    assert url_hash("https://example.com/job?id=1") != url_hash("https://example.com/job?id=2")
    assert url_hash("https://example.com/job?id=1&utm_source=mail") == url_hash("https://example.com/job?id=1")


def test_hashes_stable():
    h1 = content_hash("IT podpora", "Firma", "České Budějovice")
    h2 = content_hash("it   podpora", "firma", "české budějovice")
    assert h1 == h2
    assert url_hash("https://example.com/a") == url_hash("https://www.example.com/a/")


def test_similar_title_does_not_match_subset():
    assert not is_similar_title("Technik", "Technik IT podpory L2")
    assert is_similar_title("Technik IT podpory L2", "Technik IT podpory - L2")
