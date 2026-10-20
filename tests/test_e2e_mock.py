"""E2E smoke through the HTTP API in mock mode: no key, no network, fast (SC-001)."""

import socket
import time

import pytest
from fastapi.testclient import TestClient

from paper_triage.app import create_app


@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("PAPER_TRIAGE_DATA_DIR", str(tmp_path / "data"))
    for k in (
        "LLM_PROVIDER",
        "AGENT_API_KEY",
        "AGENT_MODEL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_MODEL",
        "OPENAI_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)
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


def _triage_ids(client, query="diffusion distillation", **kw):
    r = client.post("/api/triage", json={"query": query, **kw})
    return [x["paper_id"] for x in r.json()["results"]]


def test_chat_in_scope_cites_only_stored_ids(client):
    ids = _triage_ids(client, max_results=5)
    body = client.post(
        "/api/chat", json={"question": "Which paper is progressive?", "paper_ids": ids}
    ).json()
    assert body["refused"] is False
    assert body["citations"] and set(body["citations"]) <= _stored_ids(client)
    assert body["dropped_citations"] == []


def test_chat_out_of_scope_refused(client):
    ids = _triage_ids(client, max_results=5)
    body = client.post(
        "/api/chat", json={"question": "What is the capital of France?", "paper_ids": ids}
    )
    assert body.json()["refused"] is True and body.json()["citations"] == []


def test_chat_before_any_triage_refused(client):
    body = client.post("/api/chat", json={"question": "anything", "paper_ids": []}).json()
    assert body["refused"] is True and body["citations"] == []


# ---- v2 smoke: links, paging, set-scoped chat (SC-001, SC-002, SC-003, SC-008 API half) ----


def test_v2_search_load_more_and_scoped_chat(client):
    t0 = time.monotonic()
    first = client.post("/api/triage", json={"query": "diffusion", "max_results": 10}).json()
    assert time.monotonic() - t0 < 5  # SC-001
    assert len(first["results"]) == 10
    for r in first["results"]:
        assert r["abs_url"] == f"https://arxiv.org/abs/{r['paper_id']}"
        assert r["pdf_url"] == f"https://arxiv.org/pdf/{r['paper_id']}"
    assert first["has_more"] is True and first["next_offset"] == 10

    more = client.post(
        "/api/triage", json={"query": "diffusion", "max_results": 5, "offset": 10}
    ).json()
    first_ids = {r["paper_id"] for r in first["results"]}
    more_ids = [r["paper_id"] for r in more["results"]]
    assert len(more_ids) == 5 and not first_ids & set(more_ids)  # SC-008 API half
    assert more["has_more"] is False and more["next_offset"] == 15

    ids = [r["paper_id"] for r in first["results"]] + more_ids
    assert len(ids) == 15
    # SC-002: marker word of a load-more paper (2401.00015 "Pumice") cites only set ids
    body = client.post("/api/chat", json={"question": "Pumice?", "paper_ids": ids}).json()
    assert body["refused"] is False and body["citations"] == ["2401.00015"]
    assert set(body["citations"]) <= set(ids) and body["dropped_citations"] == []
    refused = client.post(
        "/api/chat", json={"question": "What is the capital of France?", "paper_ids": ids}
    ).json()
    assert refused["refused"] is True and refused["citations"] == []


def test_v2_id_only_set_refuses_question_about_other_stored_paper(client):
    client.post("/api/triage", json={"query": "diffusion", "max_results": 10})
    client.post("/api/triage", json={"query": "2401.00001"})
    # SC-003: 2401.00002 ("Consistency") is stored but not in the current set
    body = client.post(
        "/api/chat", json={"question": "Consistency?", "paper_ids": ["2401.00001"]}
    ).json()
    assert body["refused"] is True and body["citations"] == []
    assert _stored_ids(client) >= {"2401.00001", "2401.00002"}


def test_v2_pdf_url_item_links(client):
    r = client.post("/api/triage", json={"query": "https://example.org/a.pdf"}).json()
    (item,) = r["results"]
    assert item["abs_url"] is None and item["pdf_url"] == "https://example.org/a.pdf"
    assert r["has_more"] is False and r["next_offset"] is None


def test_v3_library_flow_offline(client, tmp_path):
    """search -> save -> ready -> pdf -> highlight -> paper chat -> directories -> unsave."""
    topic = "diffusion distillation"
    results = client.post("/api/triage", json={"query": topic, "max_results": 5}).json()["results"]
    pid = "2401.00001"
    assert pid in {r["paper_id"] for r in results}

    saved = client.post("/api/library", json={"paper_id": pid, "topic": topic})
    assert saved.status_code == 201 and saved.json()["paper"]["tags"] == ["diffusion", "distillation"]
    item = client.get("/api/library").json()["papers"][0]
    assert item["pdf"] == {"status": "ready", "error": None, "pages": 3}

    pdf = client.get("/api/library/pdf", params={"paper_id": pid})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    files = list((tmp_path / "data" / "pdfs").glob("*.pdf"))
    assert len(files) == 1

    hl = client.post("/api/annotations", json={
        "paper_id": pid, "page": 2, "kind": "highlight", "rects": [[0.1, 0.2, 0.3, 0.02]],
        "quote": "Quartzite filters",
    })
    assert hl.status_code == 201
    assert client.get("/api/library").json()["papers"][0]["highlight_count"] == 1

    chat = client.post("/api/paper-chat", json={"paper_id": pid, "question": "Where is Quartzite?"})
    assert chat.status_code == 200
    body = chat.json()
    assert body["refused"] is False and body["pages"] == [2] and "[p.2]" in body["answer"]

    d = client.post("/api/directories", json={"name": "Filters"}).json()
    moved = client.post("/api/library/move", json={"paper_id": pid, "directory_id": d["id"]})
    assert moved.status_code == 200
    lib = client.get("/api/library").json()
    assert lib["directories"] == [{"id": d["id"], "name": "Filters", "count": 1}]
    assert client.delete(f"/api/directories/{d['id']}").json() == {"deleted": True, "moved": 1}
    assert client.get("/api/library").json()["unsorted_count"] == 1

    gone = client.delete("/api/library", params={"paper_id": pid})
    assert gone.json() == {"deleted": True, "annotations": 1}
    assert list((tmp_path / "data" / "pdfs").glob("*")) == []
    assert client.get("/api/library/pdf", params={"paper_id": pid}).status_code == 404
    assert client.get("/api/library").json()["total"] == 0
    assert _stored_ids(client)  # papers and results survive an unsave
