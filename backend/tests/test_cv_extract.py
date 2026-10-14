from app.services.cv_extract import extract_text_from_docx


def test_docx_extract_plain():
    from docx import Document
    import io

    doc = Document()
    doc.add_paragraph("Linux administrátor")
    buf = io.BytesIO()
    doc.save(buf)
    text = extract_text_from_docx(buf.getvalue())
    assert "Linux" in text
