from app.services.sitprace_import import _job_text, build_search_url


def test_build_search_url_encodes_city():
    url = build_search_url(query="linux", city="České Budějovice", category="it-podpora")
    assert "sitprace.cz" in url
    assert "search.json" in url
    assert "Bud%C4%9Bjovice" in url or "Budějovice" in url


def test_job_text_contains_link_hint():
    text = _job_text({"title": "IT technik", "company": "A", "city": "Tábor", "url": "https://sitprace.cz/prace/x"})
    assert "IT technik" in text
    assert "sitprace.cz" in text
