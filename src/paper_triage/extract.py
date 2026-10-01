"""PDF text extraction (pypdf). Single swap point for another extractor."""

import io
import re

from pypdf import PdfReader

MIN_CHARS = 500
_REFERENCES = re.compile(r"^\s*references\s*$", re.IGNORECASE | re.MULTILINE)


class ExtractError(Exception):
    pass


def extract_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise ExtractError(f"cannot read PDF: {e}") from e
    if len(text.strip()) < MIN_CHARS:
        raise ExtractError("too little text extracted")
    return text


def prepare_for_llm(text: str, cap: int) -> str:
    """Drop a trailing References section (heading in the second half), then cap length."""
    for m in _REFERENCES.finditer(text):
        if m.start() >= len(text) / 2:
            text = text[: m.start()]
            break
    return text[:cap]
