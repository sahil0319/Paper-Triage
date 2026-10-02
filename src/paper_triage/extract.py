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


def extract_pages(pdf_bytes: bytes) -> list[str]:
    """Text of each page in order (1 entry per page; empty string when a page has no text)."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        raise ExtractError(f"cannot read PDF: {e}") from e


def page_count(pdf_bytes: bytes) -> int:
    """Number of pages, without extracting any text."""
    try:
        return len(PdfReader(io.BytesIO(pdf_bytes)).pages)
    except Exception as e:
        raise ExtractError(f"cannot read PDF: {e}") from e


def prepare_for_llm(text: str, cap: int) -> str:
    """Drop a trailing References section (heading in the second half), then cap length."""
    for m in _REFERENCES.finditer(text):
        if m.start() >= len(text) / 2:
            text = text[: m.start()]
            break
    return text[:cap]


def pdf_title(pdf_bytes: bytes) -> str | None:
    """PDF /Title metadata, or None."""
    try:
        title = PdfReader(io.BytesIO(pdf_bytes)).metadata.title
    except Exception:  # noqa: BLE001 - any parse failure just means no title
        return None
    return " ".join(title.split()) if title and title.strip() else None
