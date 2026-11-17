import pytest

from app.services.portal_import import parse_portal
from app.services.portal_urls import original_offer_url

UUID = "1d9d8c01-ca63-4989-822d-09b5d786e141"


@pytest.mark.parametrize("path", [f"/nabidka/{UUID}/", f"/firma/xa5wss-firma/nabidka/{UUID}/"])
def test_repairs_modern_jobs_links_stored_on_legacy_host(path):
    assert original_offer_url(f"https://www.jobs.cz{path}?id=123#detail") == f"https://beta.jobs.cz{path}?id=123#detail"


@pytest.mark.parametrize("url", [
    "https://www.jobs.cz/rpd/2001499885/?rps=1",
    "https://mmreality.jobs.cz/detail-pozice?r=detail&id=2001499885",
    f"https://www.prace.cz/nabidka/{UUID}/",
    f"https://beta.jobs.cz/nabidka/{UUID}/",
    "https://jobs.cz.example.test/nabidka/anything/",
    "https://www.jobs.cz/prace/strakonice/",
    "http://[invalid",
])
def test_keeps_other_valid_routes_and_parameters(url):
    assert original_offer_url(url) == url


def test_listing_redirect_uses_canonical_host_for_relative_offer():
    html = f'''<link rel="canonical" href="https://beta.jobs.cz/prace/strakonice/">
    <article><a data-testid="advert-link" href="/nabidka/{UUID}/?originJobAdUuid={UUID}&rps=2233">Obchodník</a></article>'''
    job = parse_portal(html, "https://www.jobs.cz/prace/strakonice/")[0]
    assert job.url == f"https://beta.jobs.cz/nabidka/{UUID}/?originJobAdUuid={UUID}&rps=2233"


def test_preserves_employer_detail_query_and_ignores_external_canonical():
    html = '''<link rel="canonical" href="https://unrelated.example/prace/">
    <article><a data-jobad-id="1" href="https://mmreality.jobs.cz/detail-pozice?r=detail&amp;id=2001499885">Makléř</a></article>'''
    assert parse_portal(html, "https://www.jobs.cz/prace/")[0].url == "https://mmreality.jobs.cz/detail-pozice?r=detail&id=2001499885"


def test_relative_prace_offer_does_not_switch_to_jobs():
    html = f'<article><a data-testid="advert-link" href="/nabidka/{UUID}/?id=123">Technik</a></article>'
    assert parse_portal(html, "https://www.prace.cz/nabidky/")[0].url == f"https://www.prace.cz/nabidka/{UUID}/?id=123"
