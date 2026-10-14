from types import SimpleNamespace

from app.services.ai import (
    _mock_evaluate,
    _profile_context,
    _template_letter,
    classify_skills,
    enrich_experience_for_ai,
    normalize_evaluation,
)


def _profile(**kw):
    base = {
        "summary": "Technická podpora. Vyučení bez maturity.",
        "skills": ["Linux", "DNS", "Apache/Nginx"],
        "experience": [],
        "education": [],
        "preferences": {"regions": ["Jihočeský kraj", "remote"], "roles": ["technická podpora"]},
        "cv_versions": [],
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_classify_required_vs_preferred():
    text = "Požadujeme Linux a DNS. Znalost Apache/Nginx výhodou."
    required, preferred = classify_skills(text, ["Linux", "DNS", "Apache/Nginx", "Windows"])
    assert required == ["Linux", "DNS"]
    assert preferred == ["Apache/Nginx"]


def test_mock_does_not_invent_job_requirements():
    ev = _mock_evaluate(_profile(), "Hledáme skladníka.", "Skladník", "Brno")
    assert ev["required_skills"] == []
    assert ev["preferred_skills"] == []


def test_mock_recognizes_south_bohemia_city_and_maturita_risk():
    ev = _mock_evaluate(_profile(), "Linux servery. Požadujeme maturitu.", "Správce", "Tábor")
    assert any("Lokalita" in r for r in ev["reasons"])
    assert any("maturita" in r.lower() for r in ev["risks"])


def test_normalize_evaluation_handles_incomplete_llm_output():
    ev = normalize_evaluation({"score": "150", "reasons": "není seznam"}, provider="openai")
    assert ev["score"] == 100
    assert ev["reasons"] == []
    assert ev["risks"] == []


def test_template_letter_uses_only_profile_data():
    letter = _template_letter(_profile(summary="", skills=["Excel"]), "Asistent", "Firma")
    assert "Excel" in letter
    assert "Linux" not in letter


def test_enrich_experience_adds_tenure_note_for_from_to():
    enriched = enrich_experience_for_ai(
        [{"role": "Podpora", "from": "2010", "to": "2020", "highlights": []}]
    )
    assert enriched[0]["_tenure_note"]
    assert "2020" in enriched[0]["_tenure_note"]
    assert "skončila" in enriched[0]["_tenure_note"]


def test_profile_context_includes_tenure_notes():
    ctx = _profile_context(
        _profile(experience=[{"role": "Podpora", "from": "2010", "to": "2020"}])
    )
    assert "_tenure_note" in ctx
    assert "2010" in ctx and "2020" in ctx
