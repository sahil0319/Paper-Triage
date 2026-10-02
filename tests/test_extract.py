from pathlib import Path

import pytest

from paper_triage.extract import (
    ExtractError,
    extract_pages,
    extract_text,
    page_count,
    pdf_title,
    prepare_for_llm,
)

SAMPLE = Path(__file__).parent.parent / "src/paper_triage/fixtures/sample.pdf"


def test_extract_sample_pdf():
    text = extract_text(SAMPLE.read_bytes())
    assert len(text) > 500
    assert "distillation" in text.lower()


def test_sample_pdf_has_three_pages_with_markers():
    pages = extract_pages(SAMPLE.read_bytes())
    assert len(pages) == 3
    assert "distillation" in pages[0].lower()
    assert "Quartzite" in pages[1] and "Quartzite" not in pages[0] + pages[2]
    assert "Obsidian" in pages[2] and "Obsidian" not in pages[0] + pages[1]
    assert SAMPLE.stat().st_size < 50_000
    xml = (SAMPLE.parent / "arxiv_search.xml").read_text()
    assert "Quartzite" not in xml


def test_sample_pdf_page_one_text_unchanged():
    page1 = extract_pages(SAMPLE.read_bytes())[0]
    assert page1.splitlines()[0] == "Sample Paper on Diffusion Distillation"
    assert page1.splitlines()[-1] == "[1] Ho et al. Denoising diffusion probabilistic models."
    assert len(page1.splitlines()) == 18


def test_sample_pdf_matches_generator():
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_sample_pdf", SAMPLE.with_name("make_sample_pdf.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.build() == SAMPLE.read_bytes()


def test_extract_pages_invalid_bytes():
    with pytest.raises(ExtractError):
        extract_pages(b"not a pdf")


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


def test_pdf_title():
    assert pdf_title(SAMPLE.read_bytes()) == "Sample Paper on Diffusion Distillation"
    assert pdf_title(SAMPLE.read_bytes().replace(b" /Info 6 0 R", b"")) is None
    assert pdf_title(b"junk") is None


def test_page_count():
    assert page_count(SAMPLE.read_bytes()) == 3
    with pytest.raises(ExtractError):
        page_count(b"nope")
