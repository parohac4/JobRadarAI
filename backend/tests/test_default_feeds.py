from app.services.default_feeds import DEFAULT_FEEDS, KARIERA_JC, KARIERA_RSS


def test_default_feeds_include_kariera_rss():
    urls = [url for _, url in DEFAULT_FEEDS]
    assert KARIERA_RSS in urls
    assert KARIERA_JC in urls
    assert any("aktualninabidkyprace.cz" in u for u in urls)
    assert any("praceproozp.cz" in u for u in urls)
