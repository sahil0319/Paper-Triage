import pytest
from fastapi.testclient import TestClient

from paper_triage import db
from paper_triage.app import create_app

PID = "2401.00001"
ANN_KEYS = {
    "id", "paper_id", "page", "kind", "color", "rects", "quote", "prefix", "suffix", "note",
    "created_at", "updated_at",
}


@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)
    monkeypatch.setenv("PAPER_TRIAGE_DATA_DIR", str(tmp_path / "data"))
    with TestClient(create_app()) as c:
        yield c


def save_ready(client, pid=PID):
    client.post("/api/triage", json={"query": "diffusion models", "max_results": 5})
    r = client.post("/api/library", json={"paper_id": pid, "topic": "diffusion models"})
    assert r.status_code == 201
    return pid


def highlight(**kw):
    body = {
        "paper_id": PID, "page": 1, "kind": "highlight",
        "rects": [[0.1, 0.2, 0.3, 0.02]], "quote": "distillation of diffusion",
    }
    return {**body, **kw}


def note(**kw):
    return {"paper_id": PID, "page": 2, "kind": "note", "note": "check this", **kw}


def post(client, body):
    return client.post("/api/annotations", json=body)


def test_create_highlight_defaults(client):
    save_ready(client)
    r = post(client, highlight(prefix="we study ", suffix=" into few"))
    assert r.status_code == 201
    a = r.json()
    assert set(a) == ANN_KEYS
    assert (a["paper_id"], a["page"], a["kind"], a["color"]) == (PID, 1, "highlight", "yellow")
    assert a["rects"] == [[0.1, 0.2, 0.3, 0.02]] and a["quote"] == "distillation of diffusion"
    assert (a["prefix"], a["suffix"], a["note"]) == ("we study ", " into few", "")
    assert a["created_at"] == a["updated_at"] and isinstance(a["id"], int)


def test_create_highlight_with_color_and_note(client):
    save_ready(client)
    a = post(client, highlight(color="mint", note="key idea")).json()
    assert (a["color"], a["note"]) == ("mint", "key idea")


@pytest.mark.parametrize("color", ["red", "", "Yellow", "pink"])
def test_color_outside_palette_422(client, color):
    save_ready(client)
    assert post(client, highlight(color=color)).status_code == 422


@pytest.mark.parametrize(
    "rects",
    [[[1.2, 0.1, 0.1, 0.1]], [[-0.1, 0.1, 0.1, 0.1]], [[0.1, 0.1, 0.1]], [[0.1, 0.1, 0.1, 0.1, 0.1]],
     [], [[0.1, 0.1, 0.1, 0.1]] * 51],
)
def test_bad_rects_422(client, rects):
    save_ready(client)
    assert post(client, highlight(rects=rects)).status_code == 422


def test_fifty_rects_ok(client):
    save_ready(client)
    assert post(client, highlight(rects=[[0.1, 0.1, 0.1, 0.1]] * 50)).status_code == 201


def test_quote_limits(client):
    save_ready(client)
    assert post(client, highlight(quote="")).status_code == 422
    assert post(client, highlight(quote="q" * 501)).status_code == 422
    assert post(client, highlight(quote="q" * 500)).status_code == 201
    assert post(client, highlight(prefix="p" * 65)).status_code == 422
    assert post(client, highlight(suffix="s" * 65)).status_code == 422
    assert post(client, highlight(note="n" * 501)).status_code == 422


def test_page_range_against_pdf_pages(client):
    save_ready(client)
    assert post(client, highlight(page=3)).status_code == 201
    assert post(client, highlight(page=4)).status_code == 422
    assert post(client, highlight(page=0)).status_code == 422


def test_pdf_not_ready_409(client):
    save_ready(client)
    db.set_file_status(client.app.state.conn, PID, "failed", error="x")
    assert post(client, highlight()).status_code == 409
    db.set_file_status(client.app.state.conn, PID, "pending")
    assert post(client, note()).status_code == 409


def test_unsaved_paper_404(client):
    assert post(client, highlight()).status_code == 404
    assert client.get("/api/annotations", params={"paper_id": PID}).status_code == 404


def test_page_note(client):
    save_ready(client)
    r = post(client, note())
    assert r.status_code == 201
    a = r.json()
    assert (a["kind"], a["rects"], a["quote"], a["note"]) == ("note", [], "", "check this")


def test_page_note_rules(client):
    save_ready(client)
    assert post(client, note(note="")).status_code == 422
    assert post(client, {k: v for k, v in note().items() if k != "note"}).status_code == 422
    assert post(client, note(note="n" * 501)).status_code == 422
    assert post(client, note(note="n" * 500)).status_code == 201
    assert post(client, note(rects=[[0.1, 0.1, 0.1, 0.1]])).status_code == 422
    assert post(client, note(quote="text")).status_code == 422


def test_bad_kind_and_missing_fields_422(client):
    save_ready(client)
    assert post(client, highlight(kind="ink")).status_code == 422
    assert post(client, {"paper_id": PID, "page": 1}).status_code == 422
    assert post(client, {"page": 1, "kind": "note", "note": "x"}).status_code == 422


def test_patch_color_and_note(client):
    save_ready(client)
    a = post(client, highlight()).json()
    r = client.patch(f"/api/annotations/{a['id']}", json={"color": "peach", "note": "later"})
    assert r.status_code == 200
    out = r.json()
    assert set(out) == ANN_KEYS and (out["color"], out["note"]) == ("peach", "later")
    assert out["created_at"] == a["created_at"] and out["updated_at"] >= a["updated_at"]
    r = client.patch(f"/api/annotations/{a['id']}", json={"note": ""})
    assert r.status_code == 200 and r.json()["note"] == "" and r.json()["color"] == "peach"


def test_patch_rules(client):
    save_ready(client)
    h = post(client, highlight()).json()
    n = post(client, note()).json()
    assert client.patch(f"/api/annotations/{h['id']}", json={"color": "red"}).status_code == 422
    assert client.patch(f"/api/annotations/{h['id']}", json={"note": "n" * 501}).status_code == 422
    assert client.patch(f"/api/annotations/{n['id']}", json={"note": ""}).status_code == 422
    assert client.patch(f"/api/annotations/{n['id']}", json={"note": "new"}).json()["note"] == "new"
    assert client.patch(f"/api/annotations/{n['id']}", json={"color": "mint"}).status_code == 200
    assert client.patch("/api/annotations/9999", json={"note": "x"}).status_code == 404


def test_delete_then_404(client):
    save_ready(client)
    a = post(client, highlight()).json()
    r = client.delete(f"/api/annotations/{a['id']}")
    assert r.status_code == 204 and r.content == b""
    assert client.delete(f"/api/annotations/{a['id']}").status_code == 404


def test_list_ordered_page_top_id(client):
    save_ready(client)
    low = post(client, highlight(page=2, rects=[[0.1, 0.6, 0.1, 0.02]])).json()
    high = post(client, highlight(page=2, rects=[[0.1, 0.1, 0.1, 0.02], [0.1, 0.9, 0.1, 0.02]])).json()
    first = post(client, note(page=1)).json()
    same_top = post(client, highlight(page=2, rects=[[0.5, 0.1, 0.1, 0.02]])).json()
    r = client.get("/api/annotations", params={"paper_id": PID})
    assert r.status_code == 200
    ids = [a["id"] for a in r.json()["annotations"]]
    assert ids == [first["id"], high["id"], same_top["id"], low["id"]]
    assert all(set(a) == ANN_KEYS for a in r.json()["annotations"])
    assert client.get("/api/annotations").status_code == 422


def test_highlight_count_in_library(client):
    save_ready(client)
    post(client, highlight())
    post(client, highlight(page=2))
    post(client, note())
    item = client.get("/api/library").json()["papers"][0]
    assert item["highlight_count"] == 2  # page notes are not highlights
    r = client.delete("/api/library", params={"paper_id": PID})
    assert r.json() == {"deleted": True, "annotations": 3}


def test_persists_across_app_restart(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)
    monkeypatch.setenv("PAPER_TRIAGE_DATA_DIR", str(tmp_path / "data"))
    with TestClient(create_app()) as c:
        save_ready(c)
        made = post(c, highlight(color="peach", note="keep")).json()
    with TestClient(create_app()) as c2:
        got = c2.get("/api/annotations", params={"paper_id": PID}).json()["annotations"]
        assert got == [made]
        assert c2.get("/api/library").json()["papers"][0]["highlight_count"] == 1


def test_unsave_removes_annotations(client):
    save_ready(client)
    post(client, highlight())
    client.delete("/api/library", params={"paper_id": PID})
    assert db.annotation_count(client.app.state.conn, PID) == 0


def test_annotation_calls_never_extract_page_text(client):
    save_ready(client)
    a = post(client, highlight()).json()
    client.get("/api/annotations", params={"paper_id": PID})
    client.patch(f"/api/annotations/{a['id']}", json={"note": "x"})
    assert db.get_pages(client.app.state.conn, PID) == []
