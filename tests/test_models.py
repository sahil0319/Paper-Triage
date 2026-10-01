import pytest
from pydantic import ValidationError

from paper_triage.models import (
    ChatAnswer,
    Critique,
    Overclaim,
    PaperOut,
    Rank,
    Summary,
    WeakClaim,
)


def test_summary_trims_to_120_words():
    s = Summary(summary=" ".join(["w"] * 200), contributions=["a"])
    assert len(s.summary.split()) == 120


def test_summary_contributions_bounds():
    with pytest.raises(ValidationError):
        Summary(summary="x", contributions=[])
    with pytest.raises(ValidationError):
        Summary(summary="x", contributions=list("abcdef"))


def test_critique_defaults_and_basis():
    c = Critique(basis="abstract")
    assert c.weak_claims == [] and c.overclaims == [] and c.missing_baselines == []
    with pytest.raises(ValidationError):
        Critique(basis="guess")


def test_critique_nested():
    c = Critique(
        weak_claims=[WeakClaim(claim="a", why="b")],
        overclaims=[Overclaim(claim="c", evidence_gap="d")],
        missing_baselines=["x"],
        basis="fulltext",
    )
    assert c.weak_claims[0].why == "b"
    assert c.overclaims[0].evidence_gap == "d"


@pytest.mark.parametrize("raw,want", [(-3, 0), (0, 0), (7, 7), (10, 10), (99, 10)])
def test_rank_clamped(raw, want):
    assert Rank(rank=raw, rank_reason="r").rank == want


def test_chat_answer_defaults():
    a = ChatAnswer(answer="x", refused=True)
    assert a.citations == [] and a.dropped_citations == []


def test_paper_out_shape():
    p = PaperOut(
        paper_id="2401.01234", title="T", authors=["A"], source="arxiv", basis="fulltext",
        rank=8, rank_reason="r", summary=Summary(summary="s", contributions=["c"]),
        critique=Critique(basis="fulltext"), status="ok", error=None,
    )
    d = p.model_dump()
    assert d["paper_id"] == "2401.01234" and d["status"] == "ok" and d["error"] is None
    failed = PaperOut(paper_id="p", title="T", source="pdf", basis="abstract", status="failed",
                      error="boom")
    assert failed.rank is None and failed.summary is None and failed.authors == []
