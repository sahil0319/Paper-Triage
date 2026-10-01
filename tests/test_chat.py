import pytest

from paper_triage import db
from paper_triage.chat import REFUSAL_TEXT, answer
from paper_triage.llm import SENTINEL, MockClient
from paper_triage.models import ChatAnswer, Critique, Summary


class Spy:
    def __init__(self, reply="x"):
        self.reply, self.calls = reply, []

    def parse(self, system, user, schema):  # pragma: no cover
        raise AssertionError("parse not expected")

    def text(self, system, user):
        self.calls.append((system, user))
        return self.reply


@pytest.fixture
def conn(tmp_db):
    c = db.connect(tmp_db)
    db.init_schema(c)
    yield c
    c.close()


def _paper(conn, pid, title="T", rank=5):
    db.upsert_paper(
        conn,
        {"id": pid, "source": "arxiv", "title": title, "authors": [], "abstract": f"abs {pid}",
         "basis": "abstract"},
    )
    db.save_result(
        conn, pid, "t", status="ok",
        summary=Summary(summary=f"sum {pid}", contributions=["c"]),
        critique=Critique(weak_claims=[{"claim": f"wc {pid}", "why": "w"}], basis="abstract"),
        rank=rank, rank_reason="r",
    )


def test_empty_store_refuses_without_llm_call(conn):
    spy = Spy()
    out = answer("anything?", conn, spy)
    assert isinstance(out, ChatAnswer)
    assert out.refused is True and out.citations == [] and out.answer
    assert spy.calls == []


def test_in_scope_cites_stored_id(conn):
    _paper(conn, "2401.00001")
    out = answer("what is this about?", conn, MockClient())
    assert out.refused is False and out.citations == ["2401.00001"]
    assert out.dropped_citations == []


def test_out_of_scope_sentinel_refuses(conn):
    _paper(conn, "2401.00001")
    out = answer("out of scope question", conn, MockClient())
    assert out.refused is True and out.citations == []
    assert SENTINEL not in out.answer


def test_unknown_ids_dropped_known_kept(conn):
    _paper(conn, "2401.00001")
    spy = Spy("A [2401.00001] and B [9999.99999] and again [2401.00001].")
    out = answer("q", conn, spy)
    assert out.citations == ["2401.00001"]
    assert out.dropped_citations == ["9999.99999"]
    assert out.refused is False


def test_only_unknown_citations_refuses(conn):
    _paper(conn, "2401.00001")
    out = answer("q", conn, Spy("Claim [9999.99999]."))
    assert out.refused is True and out.citations == []
    assert out.dropped_citations == ["9999.99999"]
    assert out.answer == REFUSAL_TEXT


def test_no_citations_refuses(conn):
    _paper(conn, "2401.00001")
    out = answer("q", conn, Spy("Plain uncited claim."))
    assert out.refused is True and out.citations == []


def test_pdf_and_old_style_ids_validate(conn):
    _paper(conn, "pdf:abc123def456")
    _paper(conn, "math.GT/0107001")
    out = answer("q", conn, Spy("[pdf:abc123def456] [math.GT/0107001]"))
    assert out.citations == ["pdf:abc123def456", "math.GT/0107001"]


def test_context_has_tagged_papers_summary_critique_and_question(conn):
    _paper(conn, "2401.00001", title='A "quoted" title')
    spy = Spy("[2401.00001]")
    answer("my question here", conn, spy)
    system, user = spy.calls[0]
    assert "NOT_IN_STORED_PAPERS" in system
    assert '<paper id="2401.00001"' in user
    assert "abs 2401.00001" in user and "sum 2401.00001" in user and "wc 2401.00001" in user
    assert "my question here" in user


def test_context_limited_to_top_k_by_rank(conn, monkeypatch):
    for i, rk in enumerate([1, 9, 5]):
        _paper(conn, f"2401.0000{i}", rank=rk)
    monkeypatch.setattr("paper_triage.chat.get_settings", lambda: type("S", (), {"chat_top_k": 2})())
    spy = Spy("[2401.00001]")
    answer("q", conn, spy)
    user = spy.calls[0][1]
    assert "2401.00001" in user and "2401.00002" in user and "2401.00000" not in user
