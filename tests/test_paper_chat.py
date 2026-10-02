import pytest
from fastapi.testclient import TestClient

from paper_triage import db, paper_chat
from paper_triage.app import create_app
from paper_triage.llm import SENTINEL, LLMError, MockClient

PID = "2401.00001"
NOT_READY = "Chat needs the PDF text. It is not ready yet."


class Spy(MockClient):
    def __init__(self, reply=None, error=None):
        self.calls = []
        self.reply = reply
        self.error = error

    def text(self, system, user):
        self.calls.append((system, user))
        if self.error:
            raise self.error
        return self.reply if self.reply is not None else super().text(system, user)


@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)
    monkeypatch.setenv("PAPER_TRIAGE_DATA_DIR", str(tmp_path / "data"))
    with TestClient(create_app()) as c:
        c.app.state.llm = Spy()
        yield c


def save(client, pid=PID):
    client.post("/api/triage", json={"query": "diffusion models", "max_results": 5})
    assert client.post("/api/library", json={"paper_id": pid, "topic": "diffusion models"}
                       ).status_code == 201
    return pid


def ask(client, question, history=None, pid=PID):
    body = {"paper_id": pid, "question": question}
    if history is not None:
        body["history"] = history
    return client.post("/api/paper-chat", json=body)


def pages_rows(client):
    return client.app.state.conn.execute("select count(*) from paper_pages").fetchone()[0]


def test_nothing_extracts_or_calls_llm_before_first_question(client):
    save(client)
    client.get("/api/library")
    client.get("/api/library/pdf", params={"paper_id": PID})
    client.post("/api/annotations", json={
        "paper_id": PID, "page": 1, "kind": "highlight", "rects": [[0.1, 0.1, 0.2, 0.02]],
        "quote": "distillation",
    })
    client.get("/api/annotations", params={"paper_id": PID})
    assert pages_rows(client) == 0 and client.app.state.llm.calls == []


def test_first_question_extracts_and_cites_page(client):
    save(client)
    r = ask(client, "Where is Quartzite used?")
    assert r.status_code == 200
    assert r.json() == {
        "answer": "Mock answer from this paper [p.2].", "pages": [2], "refused": False,
        "dropped_pages": [],
    }
    assert pages_rows(client) == 3
    assert len(client.app.state.llm.calls) == 1
    ask(client, "Tell me about obsidian")
    assert pages_rows(client) == 3  # extracted once, then reused


def test_prompt_has_page_blocks_history_and_question_only(client):
    save(client)
    client.post("/api/annotations", json={
        "paper_id": PID, "page": 2, "kind": "highlight", "rects": [[0.1, 0.1, 0.2, 0.02]],
        "quote": "UNIQUEQUOTE", "note": "UNIQUENOTE",
    })
    client.post("/api/annotations", json={
        "paper_id": PID, "page": 1, "kind": "note", "note": "PAGENOTETEXT",
    })
    hist = [{"question": "earlier q", "answer": "earlier a"}]
    ask(client, "Where is Quartzite used?", hist)
    system, user = client.app.state.llm.calls[0]
    assert "NOT_IN_STORED_PAPERS" in system and "[p.N]" in system
    assert '<page n="1">' in user and '<page n="3">' in user and "Quartzite" in user
    assert "earlier q" in user and "earlier a" in user
    assert user.rstrip().endswith("</question>")
    for hidden in ("UNIQUEQUOTE", "UNIQUENOTE", "PAGENOTETEXT"):
        assert hidden not in user


def test_unrelated_question_refused(client):
    save(client)
    r = ask(client, "What is the capital of France?").json()
    assert r["refused"] is True and r["pages"] == [] and r["answer"]
    assert SENTINEL not in r["answer"]


def test_dropped_page_when_model_cites_outside_range(client):
    save(client)
    client.app.state.llm.reply = "It matters [p.9] and [p.2] and [p.2] and [p.0]."
    r = ask(client, "anything").json()
    assert (r["refused"], r["pages"], r["dropped_pages"]) == (False, [2], [9, 0])


def test_refused_when_no_valid_page_cited(client):
    save(client)
    spy = client.app.state.llm
    spy.reply = "Sure, see [p.9]."
    r = ask(client, "anything").json()
    assert (r["refused"], r["pages"], r["dropped_pages"]) == (True, [], [9])
    assert "[p." not in r["answer"]
    spy.reply = "No citation at all."
    r = ask(client, "anything").json()
    assert r["refused"] is True and r["pages"] == []


def test_sentinel_with_reason_keeps_plain_sentence(client):
    save(client)
    client.app.state.llm.reply = f"{SENTINEL} The paper does not mention that."
    r = ask(client, "anything").json()
    assert r == {"answer": "The paper does not mention that.", "pages": [], "refused": True,
                 "dropped_pages": []}


@pytest.mark.parametrize("status", ["pending", "failed"])
def test_pdf_not_ready_refused_without_llm_or_extraction(client, status):
    save(client)
    db.set_file_status(client.app.state.conn, PID, status, error="x")
    r = ask(client, "Where is Quartzite used?")
    assert r.status_code == 200
    assert r.json() == {"answer": NOT_READY, "pages": [], "refused": True, "dropped_pages": []}
    assert client.app.state.llm.calls == [] and pages_rows(client) == 0


def test_all_empty_pages_refused_no_llm(client, monkeypatch):
    save(client)
    monkeypatch.setattr(paper_chat, "extract_pages", lambda b: ["", " ", "\n"])
    r = ask(client, "Where is Quartzite used?").json()
    assert r["refused"] is True and r["answer"] == "This PDF has no extractable text."
    assert client.app.state.llm.calls == []


def test_history_over_six_422(client):
    save(client)
    turns = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(7)]
    r = ask(client, "Quartzite?", turns)
    assert r.status_code == 422 and "history" in r.json()["detail"]
    assert ask(client, "Quartzite?", turns[:6]).status_code == 200
    assert client.app.state.llm.calls and "q0" in client.app.state.llm.calls[-1][1]


def test_unsaved_404_and_bad_bodies_422(client):
    assert ask(client, "Quartzite?").status_code == 404
    save(client)
    assert ask(client, "   ").status_code == 422
    assert client.post("/api/paper-chat", json={"question": "x"}).status_code == 422
    assert client.post("/api/paper-chat", json={"paper_id": PID}).status_code == 422


def test_llm_error_502(client):
    save(client)
    client.app.state.llm.error = LLMError("boom")
    r = ask(client, "Quartzite?")
    assert r.status_code == 502 and r.json() == {"detail": "model call failed: boom"}


def test_unsave_removes_page_text(client):
    save(client)
    ask(client, "Quartzite?")
    assert pages_rows(client) == 3
    client.delete("/api/library", params={"paper_id": PID})
    assert pages_rows(client) == 0


def test_build_context_cap_and_blocks():
    out = paper_chat.build_context(["aaaa", "bbbb", "cccc"], cap=6)
    assert '<page n="1">\naaaa\n</page>' in out and '<page n="2">\nbb\n</page>' in out
    assert "cccc" not in out
    assert paper_chat.build_context([], cap=10) == ""
