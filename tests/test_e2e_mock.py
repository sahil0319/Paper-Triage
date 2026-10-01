"""E2E smoke through the HTTP API in mock mode: no key, no network, fast (SC-001)."""

import socket
import time

import pytest
from fastapi.testclient import TestClient

from paper_triage.app import create_app


@pytest.fixture
def client(tmp_db, monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)

    def no_connect(self, *a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", no_connect)
    with TestClient(create_app()) as c:
        yield c


def _stored_ids(client):
    return {r[0] for r in client.app.state.conn.execute("SELECT id FROM papers")}


def test_status_is_mock(client):
    assert client.get("/api/status").json()["mock"] is True


def test_triage_topic_five_ranked_under_five_seconds(client):
    t0 = time.monotonic()
    r = client.post("/api/triage", json={"query": "diffusion distillation", "max_results": 5})
    assert time.monotonic() - t0 < 5
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 5
    ranks = [x["rank"] for x in results]
    assert ranks == sorted(ranks, reverse=True)
    assert all(x["status"] == "ok" or x["error"] for x in results)
    assert any(x["basis"] == "abstract" for x in results)


def test_mixed_ids_and_url_input(client):
    r = client.post("/api/triage", json={"query": "2401.00001 https://example.org/a.pdf"})
    assert r.status_code == 200
    ids = [x["paper_id"] for x in r.json()["results"]]
    assert "2401.00001" in ids and any(i.startswith("pdf:") for i in ids)
    assert client.get("/api/status").json()["paper_count"] == len(ids)


def test_chat_in_scope_cites_only_stored_ids(client):
    client.post("/api/triage", json={"query": "diffusion distillation"})
    body = client.post("/api/chat", json={"question": "Which paper is strongest?"}).json()
    assert body["refused"] is False
    assert body["citations"] and set(body["citations"]) <= _stored_ids(client)
    assert body["dropped_citations"] == []


def test_chat_out_of_scope_refused(client):
    client.post("/api/triage", json={"query": "diffusion distillation"})
    body = client.post("/api/chat", json={"question": "out of scope: who won the 2018 World Cup?"})
    assert body.json()["refused"] is True and body.json()["citations"] == []


def test_chat_before_any_triage_refused(client):
    body = client.post("/api/chat", json={"question": "anything"}).json()
    assert body["refused"] is True and body["citations"] == []
