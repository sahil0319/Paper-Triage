import pytest

from paper_triage.llm import MockClient
from paper_triage.models import Summary
from paper_triage.summarizer import summarize

PAPER = {
    "id": "2401.00001",
    "title": "Progressive Distillation",
    "abstract": "We distill diffusion samplers.",
    "full_text": "BODY " * 10,
    "basis": "fulltext",
}
ABSTRACT_ONLY = {**PAPER, "full_text": None, "basis": "abstract"}


class Spy:
    """LLMClient that records calls and returns a fixed object."""

    def __init__(self, out):
        self.out = out
        self.calls = []

    def parse(self, system, user, schema):
        self.calls.append((system, user, schema))
        return self.out

    def text(self, system, user):  # pragma: no cover
        raise AssertionError("text() not expected")


# ---- summarizer ----


def test_summarizer_returns_summary_with_mock():
    out = summarize(PAPER, MockClient())
    assert isinstance(out, Summary)
    assert out.summary and 1 <= len(out.contributions) <= 5


def test_summarizer_prompt_wraps_paper_tag_and_rules():
    spy = Spy(Summary(summary="s", contributions=["c"]))
    summarize(PAPER, spy)
    system, user, schema = spy.calls[0]
    assert schema is Summary
    assert '<paper id="2401.00001" basis="fulltext">' in user
    assert "Progressive Distillation" in user and "BODY" in user
    assert "120 words" in system and "not stated" in system.lower()


def test_summarizer_abstract_basis_omits_text():
    spy = Spy(Summary(summary="s", contributions=["c"]))
    summarize(ABSTRACT_ONLY, spy)
    user = spy.calls[0][1]
    assert 'basis="abstract"' in user and "We distill diffusion samplers." in user
    assert "BODY" not in user


def test_summarizer_caps_full_text():
    spy = Spy(Summary(summary="s", contributions=["c"]))
    summarize({**PAPER, "full_text": "x" * 100_000}, spy)
    assert len(spy.calls[0][1]) < 41_000


def test_summarizer_propagates_llm_error():
    from paper_triage.llm import LLMError

    class Boom:
        def parse(self, *a):
            raise LLMError("x")

    with pytest.raises(LLMError):
        summarize(PAPER, Boom())
