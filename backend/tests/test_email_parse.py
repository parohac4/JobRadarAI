from app.services.job_import import parse_job_email


def test_parse_email_extracts_url_and_company():
    body = """
    Nová pozice pro vás
    Společnost: HostMaster s.r.o.
    Lokace: České Budějovice
    Detail: https://jobs.cz/nabidka/12345
    """
    data = parse_job_email("IT podpora L2", body)
    assert "HostMaster" in data["company"]
    assert "jobs.cz" in data["url"]
    assert data["title"] == "IT podpora L2"
