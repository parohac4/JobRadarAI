import io
import re

from docx import Document
from pypdf import PdfReader


def extract_text_from_pdf(data: bytes, max_chars: int = 50000) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts: list[str] = []
    for page in reader.pages[:40]:
        text = page.extract_text() or ""
        parts.append(text)
        if sum(len(p) for p in parts) > max_chars:
            break
    return _clean("\n".join(parts)[:max_chars])


def extract_text_from_docx(data: bytes, max_chars: int = 50000) -> str:
    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    return _clean("\n".join(parts)[:max_chars])


def _clean(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_cv_text(filename: str, data: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(data)
    if lower.endswith(".docx"):
        return extract_text_from_docx(data)
    raise ValueError("Podporované formáty: PDF, DOCX")
