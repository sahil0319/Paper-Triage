import threading
import time

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


class Slow:
    """MockClient wrapper: sleeps per call; tracks peak concurrent calls; optional per-id failure."""

    def __init__(self, delay=0.05, fail_id=None, fail_schema=Summary):
        self.inner = MockClient()
        self.delay, self.fail_id, self.fail_schema = delay, fail_id, fail_schema
        self.lock = threading.Lock()
        self.active = self.peak = 0
        self.threads = set()

    def parse(self, system, user, schema):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            self.threads.add(threading.get_ident())
        try:
            time.sleep(self.delay)
            if self.fail_id and self.fail_id in user and schema is self.fail_schema:
                raise LLMRefusal("no")
            return self.inner.parse(system, user, schema)
        finally:
            with self.lock:
                self.active -= 1

    def text(self, system, user):  # pragma: no cover
        raise AssertionError("text() not expected")


IDS = "2401.00001 2401.00002 2401.00003 2401.00004 2401.00005"


def _timed(env, monkeypatch, conc, llm, topic=IDS):
    conn, http = env
    monkeypatch.setenv("TRIAGE_CONCURRENCY", str(conc))
    t = time.perf_counter()
    out = triage(topic, 10, conn, http, llm)
    return out, time.perf_counter() - t


def test_concurrent_faster_than_sequential_same_results(env, monkeypatch, tmp_path):
    seq_llm, par_llm = Slow(), Slow()
    seq, t_seq = _timed(env, monkeypatch, 1, seq_llm)
    assert seq_llm.peak == 1
    conn2 = db.connect(str(tmp_path / "b.db"))
    db.init_schema(conn2)
    par, t_par = _timed((conn2, env[1]), monkeypatch, 4, par_llm)
    assert par_llm.peak > 1
    assert t_par < t_seq * 0.7
    assert par == seq  # same order + content as sequential


def test_concurrent_failure_isolated(env, monkeypatch):
    llm = Slow(delay=0.01, fail_id="2401.00002")
    out, _ = _timed(env, monkeypatch, 4, llm)
    by_id = {r["paper_id"]: r for r in out["results"]}
    assert by_id["2401.00002"]["status"] == "failed"
    assert "summar" in by_id["2401.00002"]["error"].lower()
    assert all(r["status"] == "ok" for i, r in by_id.items() if i != "2401.00002")
    assert out["results"][-1]["paper_id"] == "2401.00002"
    assert db.get_result(env[0], "2401.00002", "")["status"] == "failed"


def test_concurrent_retry_once_semantics(env, monkeypatch):
    llm = Slow(delay=0.01, fail_id="2401.00003")
    _timed(env, monkeypatch, 4, llm)
    # second attempt happens: failing paper hit twice (initial + one retry), not more
    calls = []
    orig = llm.parse

    def spy(system, user, schema):
        if schema is Summary and "2401.00003" in user:
            calls.append(1)
        return orig(system, user, schema)

    llm.parse = spy
    triage(IDS, 10, env[0], env[1], llm)  # failed row is recomputed
    assert len(calls) == 2


def test_summarizer_and_critic_run_concurrently_within_paper(env, monkeypatch):
    llm = Slow(delay=0.1)
    out, t = _timed(env, monkeypatch, 2, llm, "2401.00001")
    assert out["results"][0]["status"] == "ok"
    assert llm.peak == 2 and len(llm.threads) >= 2
    assert t < 0.27  # summ||crit then rank = 2 delays (0.2s), vs 0.3s sequential


def test_db_only_touched_on_calling_thread(env, monkeypatch):
    seen = set()
    for name in ("save_result", "get_result"):
        orig = getattr(db, name)

        def wrap(*a, _orig=orig, **k):
            seen.add(threading.get_ident())
            return _orig(*a, **k)

        monkeypatch.setattr(db, name, wrap)
    llm = Slow(delay=0.01)
    out, _ = _timed(env, monkeypatch, 4, llm)
    assert len(out["results"]) == 5
    assert seen == {threading.get_ident()}
    assert threading.get_ident() in llm.threads or len(llm.threads) > 1


def test_concurrency_setting_default_min_and_invalid(monkeypatch):
    from paper_triage.config import get_settings

    monkeypatch.delenv("TRIAGE_CONCURRENCY", raising=False)
    assert get_settings().concurrency == 4
    monkeypatch.setenv("TRIAGE_CONCURRENCY", "0")
    assert get_settings().concurrency == 1
    monkeypatch.setenv("TRIAGE_CONCURRENCY", "-3")
    assert get_settings().concurrency == 1
    monkeypatch.setenv("TRIAGE_CONCURRENCY", "8")
    assert get_settings().concurrency == 8
    monkeypatch.setenv("TRIAGE_CONCURRENCY", "abc")
    assert get_settings().concurrency == 4


def test_source_urls():
    from paper_triage.pipeline import source_urls

    assert source_urls("2401.00001", "arxiv", "https://arxiv.org/pdf/2401.00001v2") == (
        "https://arxiv.org/abs/2401.00001", "https://arxiv.org/pdf/2401.00001")
    assert source_urls("math.GT/0107001", "arxiv", None) == (
        "https://arxiv.org/abs/math.GT/0107001", "https://arxiv.org/pdf/math.GT/0107001")
    assert source_urls("pdf:abc", "pdf", "https://example.org/a.pdf") == (
        None, "https://example.org/a.pdf")


def test_triage_results_carry_source_links(env):
    conn, http = env
    out = triage("2401.00001 https://example.org/a.pdf", 10, conn, http, MockClient())
    by_src = {r["source"]: r for r in out["results"]}
    assert by_src["arxiv"]["abs_url"] == "https://arxiv.org/abs/2401.00001"
    assert by_src["arxiv"]["pdf_url"] == "https://arxiv.org/pdf/2401.00001"
    assert by_src["pdf"]["abs_url"] is None
    assert by_src["pdf"]["pdf_url"] == "https://example.org/a.pdf"
