from pathlib import Path

import pytest

from paper_triage.extract import ExtractError, extract_text, prepare_for_llm

SAMPLE = Path(__file__).parent.parent / "src/paper_triage/fixtures/sample.pdf"


def test_extract_sample_pdf():
    text = extract_text(SAMPLE.read_bytes())
    assert len(text) > 500
    assert "distillation" in text.lower()


def test_extract_invalid_bytes():
    with pytest.raises(ExtractError):
        extract_text(b"this is not a pdf")


def test_extract_empty_bytes():
    with pytest.raises(ExtractError):
        extract_text(b"")


def test_extract_too_short(monkeypatch):
    class P:
        def extract_text(self):
            return "tiny"

    class R:
        def __init__(self, *_a, **_k):
            self.pages = [P()]

    monkeypatch.setattr("paper_triage.extract.PdfReader", R)
    with pytest.raises(ExtractError):
        extract_text(b"%PDF-whatever")


def test_prepare_drops_trailing_references():
    body = "Intro line.\n" * 50
    text = body + "References\n[1] Foo et al.\n[2] Bar et al.\n"
    out = prepare_for_llm(text, 40000)
    assert "Foo et al" not in out
    assert out.startswith("Intro line.")


def test_prepare_references_case_insensitive_and_padded():
    text = "Body text here.\n" * 50 + "  REFERENCES  \n[1] Foo\n"
    assert "Foo" not in prepare_for_llm(text, 40000)


def test_prepare_ignores_early_references_heading():
    # a table-of-contents style heading in the first half must not truncate the paper
    text = "References\n" + "Real content line.\n" * 100
    out = prepare_for_llm(text, 40000)
    assert out.count("Real content line.") == 100


def test_prepare_no_references_unchanged():
    text = "Just text.\n" * 10
    assert prepare_for_llm(text, 40000) == text


def test_prepare_caps_length():
    assert len(prepare_for_llm("x" * 1000, 100)) == 100
