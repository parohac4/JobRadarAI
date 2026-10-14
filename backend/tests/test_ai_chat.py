from app.services.ai import _model_supports_temperature, normalize_cover_letter_content


def test_gpt5_no_custom_temperature():
    assert not _model_supports_temperature("gpt-5")
    assert not _model_supports_temperature("gpt-5-mini")


def test_gpt4_supports_temperature():
    assert _model_supports_temperature("gpt-4o-mini")


def test_normalize_cover_letter_from_json():
    raw = '{"cover_letter":"Dobrý den,\\n\\nreaguji na pozici."}'
    assert normalize_cover_letter_content(raw) == "Dobrý den,\n\nreaguji na pozici."


def test_normalize_cover_letter_plain_text():
    assert normalize_cover_letter_content("Dobrý den.") == "Dobrý den."
