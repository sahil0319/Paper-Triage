import pytest
from pydantic import ValidationError

from paper_triage import db
from paper_triage.llm import LLMError, LLMRefusal, MockClient
from paper_triage.models import Rank, Summary
from paper_triage.net import make_http
from paper_triage.pipeline import triage


@pytest.fixture
def env(tmp_db):
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    return conn, make_http(True)


class Flaky:
    """MockClient wrapper: fails the first `fails` parse calls for `schema` with `exc`."""

    def __init__(self, schema=None, exc=None, fails=0, only_id=None):
        self.inner = MockClient()
        self.schema, self.exc, self.fails, self.only_id = schema, exc, fails, only_id
        self.calls = []

    def parse(self, system, user, schema):
        self.calls.append(schema)
        hit = schema is self.schema and (self.only_id is None or self.only_id in user)
        if hit and self.fails > 0:
            self.fails -= 1
            raise self.exc
        return self.inner.parse(system, user, schema)

    def text(self, system, user):  # pragma: no cover
        raise AssertionError("text() not expected")


def _validation_error():
    try:
        Rank.model_validate({"rank": "x"})
    except ValidationError as e:
        return e


def test_triage_topic_five_ranked_results(env):
    conn, http = env
    out = triage("diffusion distillation", 10, conn, http, MockClient())
    assert out["topic"] == "diffusion distillation"
    assert out["errors"] == []
    rs = out["results"]
    assert len(rs) == 5
    assert all(r["status"] == "ok" and r["error"] is None for r in rs)
    ranks = [r["rank"] for r in rs]
    assert ranks == sorted(ranks, reverse=True)
    r = rs[0]
    assert {"paper_id", "title", "authors", "source", "basis", "rank", "rank_reason",
            "summary", "critique", "status", "error"} <= set(r)
    assert r["summary"]["contributions"] and "weak_claims" in r["critique"]
    assert any(x["basis"] == "abstract" for x in rs)
    assert any(x["basis"] == "fulltext" for x in rs)


def test_triage_persists_results(env):
    conn, http = env
    out = triage("diffusion", 3, conn, http, MockClient())
    stored = db.list_results(conn, "diffusion")
    assert [r["paper_id"] for r in stored] == [r["paper_id"] for r in out["results"]]


def test_triage_n_limits_and_caps_at_20(env):
    conn, http = env
    assert len(triage("diffusion", 2, conn, http, MockClient())["results"]) == 2
    # n above 20 is capped, not an error (feed only has 5)
    assert len(triage("other topic", 99, conn, http, MockClient())["results"]) == 5


def test_triage_ids_only_topic_empty_and_unknown_id_error(env):
    conn, http = env
    out = triage("2401.00001 2401.00002 9999.99999", 10, conn, http, MockClient())
    assert out["topic"] == ""
    assert {r["paper_id"] for r in out["results"]} == {"2401.00001", "2401.00002"}
    assert out["errors"] == [{"input": "9999.99999", "reason": "not found"}]


def test_triage_mixed_ids_and_pdf_url(env):
    conn, http = env
    out = triage("2401.00001 https://example.org/a.pdf", 10, conn, http, MockClient())
    ids = {r["paper_id"] for r in out["results"]}
    assert len(ids) == 2 and "2401.00001" in ids
    assert any(i.startswith("pdf:") for i in ids)


def test_triage_empty_query_raises(env):
    conn, http = env
    with pytest.raises(ValueError):
        triage("   ", 10, conn, http, MockClient())


def test_triage_zero_found(env):
    conn, http = env
    out = triage("9999.99999", 10, conn, http, MockClient())
    assert out["results"] == []
    assert out["errors"]


def test_triage_search_failure_is_reported_not_raised(tmp_db):
    import httpx

    conn = db.connect(tmp_db)
    db.init_schema(conn)
    from paper_triage.net import Throttle

    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    out = triage("diffusion", 5, conn, (bad, Throttle(0)), MockClient())
    assert out["results"] == []
    assert out["errors"][0]["input"] == "diffusion"


def test_validation_error_retried_once_then_ok(env):
    conn, http = env
    llm = Flaky(Summary, _validation_error(), fails=1)
    out = triage("2401.00001", 10, conn, http, llm)
    assert out["results"][0]["status"] == "ok"
    assert llm.calls.count(Summary) == 2


@pytest.mark.parametrize("exc", [LLMError("boom"), LLMRefusal("no")])
def test_llm_errors_retried_once(env, exc):
    conn, http = env
    llm = Flaky(Rank, exc, fails=1)
    out = triage("2401.00001", 10, conn, http, llm)
    assert out["results"][0]["status"] == "ok"
    assert llm.calls.count(Rank) == 2


def test_persistent_failure_marks_failed_others_continue(env):
    conn, http = env
    llm = Flaky(Summary, LLMRefusal("no"), fails=99, only_id="2401.00002")
    out = triage("2401.00001 2401.00002 2401.00003", 10, conn, http, llm)
    by_id = {r["paper_id"]: r for r in out["results"]}
    assert by_id["2401.00002"]["status"] == "failed"
    assert "summar" in by_id["2401.00002"]["error"].lower()
    assert by_id["2401.00001"]["status"] == "ok" and by_id["2401.00003"]["status"] == "ok"
    assert out["results"][-1]["paper_id"] == "2401.00002"  # failed sorted last
    assert llm.calls.count(Summary) == 4  # 2 ok + 2 attempts on failing one
    stored = db.get_result(conn, "2401.00002", "")
    assert stored["status"] == "failed" and stored["error"]


def test_partial_fields_kept_on_late_failure(env):
    conn, http = env
    llm = Flaky(Rank, _validation_error(), fails=99)
    r = triage("2401.00001", 10, conn, http, llm)["results"][0]
    assert r["status"] == "failed" and r["rank"] is None
    assert r["summary"] is not None and r["critique"] is not None


def test_existing_ok_result_reused_without_llm(env):
    conn, http = env
    triage("2401.00001", 10, conn, http, MockClient())
    llm = Flaky()
    out = triage("2401.00001", 10, conn, http, llm)
    assert llm.calls == []
    assert out["results"][0]["status"] == "ok"


def test_failed_result_recomputed(env):
    conn, http = env
    triage("2401.00001", 10, conn, http, Flaky(Rank, LLMError("x"), fails=99))
    out = triage("2401.00001", 10, conn, http, MockClient())
    assert out["results"][0]["status"] == "ok"


def test_same_paper_new_topic_gets_own_result(env):
    conn, http = env
    triage("2401.00001", 10, conn, http, MockClient())
    llm = Flaky()
    triage("2401.00001 distillation", 10, conn, http, llm)
    assert llm.calls.count(Rank) == 1
