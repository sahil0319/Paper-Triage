import json

import pytest
from fastapi.testclient import TestClient

from paper_triage.app import create_app


@pytest.fixture
def client(tmp_db, monkeypatch):
    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)
    with TestClient(create_app()) as c:
        yield c


def test_status_mock(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["mock"] is True and body["model"] and body["paper_count"] == 0
    assert body["provider"] == "anthropic"


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


def test_triage_topic_returns_five_ranked(client):
    r = client.post("/api/triage", json={"query": "diffusion distillation", "max_results": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["topic"] == "diffusion distillation" and body["errors"] == []
    ranks = [x["rank"] for x in body["results"]]
    assert len(ranks) == 5 and ranks == sorted(ranks, reverse=True)
    assert client.get("/api/status").json()["paper_count"] == 5


def test_triage_max_results(client):
    r = client.post("/api/triage", json={"query": "diffusion", "max_results": 2})
    assert len(r.json()["results"]) == 2


def test_triage_ids_with_unknown(client):
    r = client.post("/api/triage", json={"query": "2401.00001 9999.99999"})
    body = r.json()
    assert [x["paper_id"] for x in body["results"]] == ["2401.00001"]
    assert body["errors"] == [{"input": "9999.99999", "reason": "not found"}]


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},
        {"query": "   "},
        {},
        {"query": "x", "max_results": 0},
        {"query": "x", "max_results": 21},
        {"query": "x", "max_results": "many"},
    ],
)
def test_triage_422_plain_detail(client, payload):
    r = client.post("/api/triage", json=payload)
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str) and r.json()["detail"]


def test_papers_empty_then_latest_topic(client):
    assert client.get("/api/papers").json() == {"topic": "", "results": []}
    client.post("/api/triage", json={"query": "first topic", "max_results": 2})
    client.post("/api/triage", json={"query": "second topic", "max_results": 3})
    latest = client.get("/api/papers").json()
    assert latest["topic"] == "second topic" and len(latest["results"]) == 3
    first = client.get("/api/papers", params={"topic": "first topic"}).json()
    assert len(first["results"]) == 2
    assert client.get("/api/papers", params={"topic": "nope"}).json()["results"] == []


def test_papers_same_shape_and_order_as_triage(client):
    t = client.post("/api/triage", json={"query": "diffusion"}).json()
    p = client.get("/api/papers", params={"topic": "diffusion"}).json()
    assert p["results"] == t["results"]


def test_index_has_page_landmarks(client):
    html = client.get("/").text
    for needle in ('<main id="main"', 'id="triage-form"', 'id="paper-list"', 'id="chat"',
                   'id="mock-label"', 'href="app.css"'):
        assert needle in html


def test_static_css_served(client):
    r = client.get("/app.css")
    assert r.status_code == 200 and "text/css" in r.headers["content-type"]
    assert "http://" not in r.text and "https://" not in r.text  # no CDN, no external fonts


# --- T019: POST /api/chat ---


def _turns(client):
    return client.app.state.conn.execute("SELECT * FROM chat_turns ORDER BY id").fetchall()


def test_chat_empty_set_refused_and_persisted(client):
    r = client.post("/api/chat", json={"question": "what is stored?", "paper_ids": []})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "citations", "refused", "dropped_citations"}
    assert body["refused"] is True and body["citations"] == []
    assert body["answer"].startswith("No search results to ask about yet")
    turns = _turns(client)
    assert len(turns) == 1 and turns[0]["refused"] == 1 and turns[0]["question"] == "what is stored?"


def test_chat_in_scope_cites_set_ids_only(client):
    ids = [
        r["paper_id"]
        for r in client.post("/api/triage", json={"query": "diffusion", "max_results": 3}).json()[
            "results"
        ]
    ]
    body = client.post(
        "/api/chat", json={"question": "what is progressive about?", "paper_ids": ids}
    ).json()
    assert body["refused"] is False and body["citations"]
    assert set(body["citations"]) <= set(ids)
    assert "[" in body["answer"]
    turn = _turns(client)[-1]
    assert turn["refused"] == 0 and turn["answer"] == body["answer"]
    assert json.loads(turn["citations"]) == body["citations"]


def test_chat_unrelated_question_refused(client):
    ids = [
        r["paper_id"]
        for r in client.post("/api/triage", json={"query": "diffusion", "max_results": 2}).json()[
            "results"
        ]
    ]
    body = client.post(
        "/api/chat", json={"question": "What is the capital of France?", "paper_ids": ids}
    ).json()
    assert body["refused"] is True and body["citations"] == []
    assert len(_turns(client)) == 1


def test_chat_earlier_search_paper_outside_set_refused(client):
    client.post("/api/triage", json={"query": "diffusion", "max_results": 10})
    client.post("/api/triage", json={"query": "2401.00001"})
    body = client.post(
        "/api/chat", json={"question": "consistency?", "paper_ids": ["2401.00001"]}
    ).json()
    assert body["refused"] is True and body["citations"] == []
    assert len(_turns(client)) == 1
    again = client.post(
        "/api/chat",
        json={"question": "consistency?", "paper_ids": ["2401.00001", "2401.00002"]},
    ).json()
    assert again["refused"] is False and again["citations"] == ["2401.00002"]


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "", "paper_ids": []},
        {"question": "   ", "paper_ids": []},
        {"paper_ids": []},
        {"question": 5, "paper_ids": []},
        {"question": "hi"},
        {"question": "hi", "paper_ids": "2401.00001"},
    ],
)
def test_chat_422_plain_detail_and_not_persisted(client, payload):
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and r.json()["detail"]
    assert _turns(client) == []


def test_chat_paper_ids_limit_50(client):
    ok = client.post(
        "/api/chat", json={"question": "hi", "paper_ids": [f"x{i}" for i in range(50)]}
    )
    assert ok.status_code == 200
    r = client.post(
        "/api/chat", json={"question": "hi", "paper_ids": [f"x{i}" for i in range(51)]}
    )
    assert r.status_code == 422 and r.json() == {"detail": "paper_ids: at most 50 ids"}
    dup = client.post("/api/chat", json={"question": "hi", "paper_ids": ["x"] * 60})
    assert dup.status_code == 200  # duplicates ignored


def test_chat_llm_failure_is_502_plain_detail(client):
    from paper_triage.llm import LLMError

    class Boom:
        def text(self, system, user):
            raise LLMError("down")

    client.post("/api/triage", json={"query": "diffusion", "max_results": 2})
    client.app.state.llm = Boom()
    r = client.post("/api/chat", json={"question": "hi", "paper_ids": ["2401.00001", "2401.00002"]})
    assert r.status_code == 502 and "down" in r.json()["detail"]
    assert _turns(client) == []


# --- T021 (api): revisit earlier results on a fresh app over the same db ---


def test_new_app_instance_same_db_returns_same_results_without_fetch(tmp_db, monkeypatch):
    import httpx

    from paper_triage.net import Throttle

    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)
    with TestClient(create_app()) as c1:
        first = c1.post(
            "/api/triage", json={"query": "diffusion distillation", "max_results": 5}
        ).json()
    assert len(first["results"]) == 5

    def no_network(request):
        raise AssertionError(f"unexpected fetch: {request.url}")

    with TestClient(create_app()) as c2:
        c2.app.state.http = (httpx.Client(transport=httpx.MockTransport(no_network)), Throttle(0))
        status = c2.get("/api/status").json()
        assert status["mock"] is True and status["paper_count"] == 5
        stored = c2.get("/api/papers").json()
        assert stored == {"topic": "diffusion distillation", "results": first["results"]}
        again = c2.post(
            "/api/triage", json={"query": "diffusion distillation", "max_results": 5}
        ).json()
        assert again["results"] == first["results"]


def test_source_links_on_triage_and_papers(client):
    body = client.post("/api/triage", json={"query": "2401.00001 https://example.org/a.pdf"}).json()
    again = client.get("/api/papers", params={"topic": ""}).json()["results"]
    for results in (body["results"], again):
        by_src = {r["source"]: r for r in results}
        assert by_src["arxiv"]["abs_url"] == "https://arxiv.org/abs/2401.00001"
        assert by_src["arxiv"]["pdf_url"] == "https://arxiv.org/pdf/2401.00001"
        assert by_src["pdf"]["abs_url"] is None
        assert by_src["pdf"]["pdf_url"] == "https://example.org/a.pdf"


def test_triage_paging_fields_and_load_more(client):
    a = client.post("/api/triage", json={"query": "diffusion", "max_results": 10}).json()
    assert (a["offset"], a["next_offset"], a["has_more"]) == (0, 10, True)
    assert len(a["results"]) == 10
    b = client.post(
        "/api/triage", json={"query": "diffusion", "max_results": 5, "offset": 10}
    ).json()
    assert {r["paper_id"] for r in b["results"]} == {f"2401.{i:05d}" for i in range(11, 16)}
    assert (b["offset"], b["next_offset"], b["has_more"]) == (10, 15, False)


@pytest.mark.parametrize("offset", [-1, 1001])
def test_triage_offset_range_422(client, offset):
    r = client.post("/api/triage", json={"query": "diffusion", "offset": offset})
    assert r.status_code == 422


def test_triage_items_with_offset_422(client):
    r = client.post("/api/triage", json={"query": "2401.00001", "offset": 5})
    assert r.status_code == 422
    assert r.json() == {"detail": "offset only applies to topic searches"}
    ok = client.post("/api/triage", json={"query": "2401.00001"}).json()
    assert (ok["offset"], ok["next_offset"], ok["has_more"]) == (0, None, False)


def test_triage_fetch_error_has_more_false(client):
    import httpx

    from paper_triage.net import Throttle

    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    client.app.state.http = (bad, Throttle(0))
    body = client.post("/api/triage", json={"query": "diffusion"}).json()
    assert body["results"] == [] and body["has_more"] is False and body["next_offset"] is None


# ---- T066: woff2 MIME type ----


def test_woff2_mime_type_registered(client):
    import mimetypes

    assert mimetypes.guess_type("a.woff2")[0] == "font/woff2"


def test_woff2_served_as_font_woff2(client):
    from pathlib import Path

    import paper_triage

    font = Path(paper_triage.__file__).parent / "static/vendor/fonts/plex-sans-latin-400.woff2"
    if not font.exists():
        pytest.skip("fonts not vendored yet (T067)")
    r = client.get("/vendor/fonts/plex-sans-latin-400.woff2")
    assert r.status_code == 200
    assert r.headers["content-type"] == "font/woff2"
