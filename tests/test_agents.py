import pytest

from paper_triage.critic import critique
from paper_triage.llm import MockClient
from paper_triage.models import Critique, Rank, Summary
from paper_triage.ranker import rank
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


# ---- critic ----


def test_critic_returns_critique_with_mock():
    out = critique(PAPER, MockClient())
    assert isinstance(out, Critique)
    assert out.basis == "fulltext"


def test_critic_prompt_skeptical_and_supported_only():
    spy = Spy(Critique(basis="fulltext"))
    critique(PAPER, spy)
    system, user, schema = spy.calls[0]
    assert schema is Critique
    assert '<paper id="2401.00001" basis="fulltext">' in user and "BODY" in user
    low = system.lower()
    assert "skeptical" in low and "not stated" in low
    assert "weak_claims" in low and "overclaims" in low and "missing_baselines" in low


def test_critic_basis_comes_from_paper_not_llm():
    spy = Spy(Critique(basis="fulltext", missing_baselines=["X"]))
    out = critique(ABSTRACT_ONLY, spy)
    assert out.basis == "abstract"
    assert out.missing_baselines == ["X"]
    assert 'basis="abstract"' in spy.calls[0][1] and "BODY" not in spy.calls[0][1]
    assert critique(PAPER, Spy(Critique(basis="abstract"))).basis == "fulltext"


# ---- ranker ----

SUMMARY = Summary(summary="Distills samplers fast.", contributions=["2-step sampler"])


def test_ranker_returns_rank_with_mock_in_range():
    out = rank(PAPER, SUMMARY, "diffusion", MockClient())
    assert isinstance(out, Rank) and 0 <= out.rank <= 10 and out.rank_reason


def test_ranker_prompt_has_topic_summary_no_full_text_and_anchors():
    spy = Spy(Rank(rank=7, rank_reason="r"))
    rank(PAPER, SUMMARY, "diffusion distillation", spy)
    system, user, schema = spy.calls[0]
    assert schema is Rank
    assert '<paper id="2401.00001" basis="fulltext">' in user
    assert "diffusion distillation" in user and "Distills samplers fast." in user
    assert "BODY" not in user
    for anchor in ("0-2", "3-5", "6-8", "9-10"):
        assert anchor in system


def test_ranker_empty_topic_uses_overall_priority_wording():
    spy = Spy(Rank(rank=5, rank_reason="r"))
    rank(PAPER, SUMMARY, "  ", spy)
    user = spy.calls[0][1]
    assert "overall reading priority" in user.lower()
    assert "Topic:" not in user


def test_ranker_clamps_out_of_range():
    assert rank(PAPER, SUMMARY, "t", Spy(Rank(rank=99, rank_reason="r"))).rank == 10
    assert rank(PAPER, SUMMARY, "t", Spy(Rank(rank=-4, rank_reason="r"))).rank == 0
