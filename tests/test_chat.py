import pytest

from paper_triage import db
from paper_triage.chat import NO_SET_TEXT, REFUSAL_TEXT, answer
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


def test_empty_set_refuses_without_llm_call(conn):
    _paper(conn, "2401.00001")
    spy = Spy()
    out = answer("anything?", [], conn, spy)
    assert isinstance(out, ChatAnswer)
    assert out.refused is True and out.citations == [] and out.answer == NO_SET_TEXT
    assert spy.calls == []


def test_ids_none_stored_refuses_without_llm_call(conn):
    _paper(conn, "2401.00001")
    spy = Spy()
    out = answer("anything?", ["9999.99999", "8888.88888"], conn, spy)
    assert out.refused is True and out.answer == NO_SET_TEXT
    assert spy.calls == []


def test_in_scope_cites_stored_id(conn):
    _paper(conn, "2401.00001", title="Basalt Study")
    out = answer("what is basalt about?", ["2401.00001"], conn, MockClient())
    assert out.refused is False and out.citations == ["2401.00001"]
    assert out.dropped_citations == []


def test_unrelated_question_sentinel_refuses(conn):
    _paper(conn, "2401.00001", title="Basalt Study")
    out = answer("What is the capital of France?", ["2401.00001"], conn, MockClient())
    assert out.refused is True and out.citations == []
    assert SENTINEL not in out.answer


def test_stored_paper_outside_set_not_in_prompt_and_citation_dropped(conn):
    _paper(conn, "2401.00001", title="Basalt Study")
    _paper(conn, "2401.00002", title="Cobalt Study")
    spy = Spy("Both [2401.00001] and [2401.00002].")
    out = answer("compare", ["2401.00001"], conn, spy)
    user = spy.calls[0][1]
    assert "2401.00001" in user and "2401.00002" not in user and "Cobalt" not in user
    assert out.citations == ["2401.00001"] and out.dropped_citations == ["2401.00002"]
    assert out.refused is False


def test_only_outside_set_citation_refuses(conn):
    _paper(conn, "2401.00001")
    _paper(conn, "2401.00002")
    out = answer("q", ["2401.00001"], conn, Spy("Claim [2401.00002]."))
    assert out.refused is True and out.citations == []
    assert out.dropped_citations == ["2401.00002"] and out.answer == REFUSAL_TEXT


def test_load_more_id_in_set_can_be_cited(conn):
    for i in (1, 2):
        _paper(conn, f"2401.0000{i}")
    out = answer("q", ["2401.00001", "2401.00002"], conn, Spy("[2401.00002]"))
    assert out.citations == ["2401.00002"] and out.dropped_citations == []


def test_context_in_sent_order_and_duplicates_ignored(conn):
    for i in (1, 2, 3):
        _paper(conn, f"2401.0000{i}")
    spy = Spy("[2401.00003]")
    answer("q", ["2401.00003", "2401.00001", "2401.00003", "nope"], conn, spy)
    user = spy.calls[0][1]
    assert user.count("<paper ") == 2
    assert user.index("2401.00003") < user.index("2401.00001")


def test_unknown_ids_dropped_known_kept(conn):
    _paper(conn, "2401.00001")
    spy = Spy("A [2401.00001] and B [9999.99999] and again [2401.00001].")
    out = answer("q", ["2401.00001"], conn, spy)
    assert out.citations == ["2401.00001"]
    assert out.dropped_citations == ["9999.99999"]
    assert out.refused is False


def test_no_citations_refuses(conn):
    _paper(conn, "2401.00001")
    out = answer("q", ["2401.00001"], conn, Spy("Plain uncited claim."))
    assert out.refused is True and out.citations == []


def test_pdf_and_old_style_ids_validate(conn):
    _paper(conn, "pdf:abc123def456")
    _paper(conn, "math.GT/0107001")
    ids = ["pdf:abc123def456", "math.GT/0107001"]
    out = answer("q", ids, conn, Spy("[pdf:abc123def456] [math.GT/0107001]"))
    assert out.citations == ids


def test_context_has_tagged_papers_summary_critique_and_question(conn):
    _paper(conn, "2401.00001", title='A "quoted" title')
    spy = Spy("[2401.00001]")
    answer("my question here", ["2401.00001"], conn, spy)
    system, user = spy.calls[0]
    assert "NOT_IN_STORED_PAPERS" in system
    assert '<paper id="2401.00001"' in user
    assert "abs 2401.00001" in user and "sum 2401.00001" in user and "wc 2401.00001" in user
    assert "my question here" in user
