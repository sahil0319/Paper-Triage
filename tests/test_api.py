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


def test_index_served(client):
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]


def test_triage_topic_returns_five_ranked(client):
    r = client.post("/api/triage", json={"query": "diffusion distillation"})
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


def test_chat_empty_store_refused_and_persisted(client):
    r = client.post("/api/chat", json={"question": "what is stored?"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "citations", "refused", "dropped_citations"}
    assert body["refused"] is True and body["citations"] == []
    turns = _turns(client)
    assert len(turns) == 1 and turns[0]["refused"] == 1 and turns[0]["question"] == "what is stored?"


def test_chat_in_scope_cites_stored_ids_only(client):
    client.post("/api/triage", json={"query": "diffusion", "max_results": 3})
    stored = {r[0] for r in client.app.state.conn.execute("SELECT id FROM papers")}
    body = client.post("/api/chat", json={"question": "what do they find?"}).json()
    assert body["refused"] is False and body["citations"]
    assert set(body["citations"]) <= stored
    assert "[" in body["answer"]
    turn = _turns(client)[-1]
    assert turn["refused"] == 0 and turn["answer"] == body["answer"]
    assert json.loads(turn["citations"]) == body["citations"]


def test_chat_out_of_scope_refused(client):
    client.post("/api/triage", json={"query": "diffusion", "max_results": 2})
    body = client.post("/api/chat", json={"question": "out of scope: capital of France"}).json()
    assert body["refused"] is True and body["citations"] == []
    assert len(_turns(client)) == 1


@pytest.mark.parametrize("payload", [{"question": ""}, {"question": "   "}, {}, {"question": 5}])
def test_chat_422_plain_detail_and_not_persisted(client, payload):
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and r.json()["detail"]
    assert _turns(client) == []


def test_chat_llm_failure_is_502_plain_detail(client):
    from paper_triage.llm import LLMError

    class Boom:
        def text(self, system, user):
            raise LLMError("down")

    client.post("/api/triage", json={"query": "diffusion", "max_results": 2})
    client.app.state.llm = Boom()
    r = client.post("/api/chat", json={"question": "hi"})
    assert r.status_code == 502 and "down" in r.json()["detail"]
    assert _turns(client) == []
