import pytest
from fastapi.testclient import TestClient

from paper_triage import db
from paper_triage.app import create_app
from paper_triage.tags import keywords


@pytest.fixture
def client(tmp_db, tmp_path, monkeypatch):
    monkeypatch.setenv("PAPER_TRIAGE_DB", tmp_db)
    monkeypatch.setenv("PAPER_TRIAGE_DATA_DIR", str(tmp_path / "data"))
    with TestClient(create_app()) as c:
        yield c


def search(client, topic="diffusion models", n=3):
    r = client.post("/api/triage", json={"query": topic, "max_results": n})
    assert r.status_code == 200
    return r.json()


def save(client, paper_id, topic):
    return client.post("/api/library", json={"paper_id": paper_id, "topic": topic})


ITEM_KEYS = {
    "paper_id", "title", "authors", "source", "published", "abstract", "basis", "rank",
    "rank_reason", "summary", "critique", "abs_url", "pdf_url", "topic", "tags", "directory_id",
    "saved_at", "pdf", "highlight_count",
}


def test_save_new_returns_201_with_snapshot_and_tags(client):
    body = search(client, "Diffusion models, for VIDEO generation")
    top = body["results"][0]
    r = save(client, top["paper_id"], body["topic"])
    assert r.status_code == 201
    out = r.json()
    assert out["created"] is True
    item = out["paper"]
    assert set(item) == ITEM_KEYS
    assert item["paper_id"] == top["paper_id"]
    assert item["title"] == top["title"] and item["rank"] == top["rank"]
    assert item["rank_reason"] == top["rank_reason"] and item["basis"] == top["basis"]
    assert item["summary"] == top["summary"] and item["critique"] == top["critique"]
    assert item["abs_url"] == top["abs_url"] and item["pdf_url"] == top["pdf_url"]
    assert item["abstract"] and item["published"]
    assert item["topic"] == body["topic"]
    assert item["tags"] == keywords("Diffusion models, for VIDEO generation")
    assert item["directory_id"] is None and item["saved_at"] and item["highlight_count"] == 0
    assert set(item["pdf"]) == {"status", "error", "pages"}


def test_save_again_other_topic_merges_tags_keeps_original(client):
    first = search(client, "diffusion models")
    pid = first["results"][0]["paper_id"]
    created = save(client, pid, "diffusion models").json()["paper"]
    second = search(client, "video generation")
    assert pid in {x["paper_id"] for x in second["results"]}
    r = save(client, pid, "video generation")
    assert r.status_code == 200
    out = r.json()
    assert out["created"] is False
    item = out["paper"]
    assert item["saved_at"] == created["saved_at"] and item["rank"] == created["rank"]
    assert item["topic"] == "diffusion models"
    assert item["tags"] == ["diffusion", "models", "video", "generation"]


def test_item_query_topic_empty_gives_no_tags(client):
    body = search(client, "2401.00001")
    assert body["topic"] == ""
    r = save(client, "2401.00001", "")
    assert r.status_code == 201 and r.json()["paper"]["tags"] == []


def test_unknown_pair_404(client):
    search(client, "diffusion models")
    r = save(client, "2401.00001", "never searched")
    assert r.status_code == 404
    assert r.json() == {"detail": "no stored result for this paper"}
    assert save(client, "9999.99999", "diffusion models").status_code == 404


def test_failed_result_409(client):
    body = search(client, "diffusion models")
    pid = body["results"][0]["paper_id"]
    db.save_result(client.app.state.conn, pid, "diffusion models", status="failed", error="boom")
    r = save(client, pid, "diffusion models")
    assert r.status_code == 409
    assert r.json() == {"detail": "only completed results can be saved"}


def test_missing_fields_422(client):
    assert client.post("/api/library", json={"topic": "x"}).status_code == 422


def test_triage_and_papers_items_carry_saved(client):
    body = search(client, "diffusion models")
    assert all(x["saved"] is False for x in body["results"])
    pid = body["results"][0]["paper_id"]
    save(client, pid, "diffusion models")
    again = search(client, "diffusion models")
    flags = {x["paper_id"]: x["saved"] for x in again["results"]}
    assert flags[pid] is True and sum(flags.values()) == 1
    got = client.get("/api/papers", params={"topic": "diffusion models"}).json()
    assert {x["paper_id"]: x["saved"] for x in got["results"]} == flags


def test_topic_search_merges_tags_for_saved_paper(client):
    body = search(client, "diffusion models")
    pid = body["results"][0]["paper_id"]
    save(client, pid, "diffusion models")
    search(client, "video generation")  # same mock papers, other topic
    lib = client.get("/api/library").json()
    tags = next(p for p in lib["papers"] if p["paper_id"] == pid)["tags"]
    assert tags == ["diffusion", "models", "video", "generation"]


def test_item_search_does_not_change_tags(client):
    body = search(client, "diffusion models")
    pid = body["results"][0]["paper_id"]
    save(client, pid, "diffusion models")
    search(client, pid)
    lib = client.get("/api/library").json()
    assert lib["papers"][0]["tags"] == ["diffusion", "models"]


def test_get_library_lists_newest_first_with_counts(client):
    body = search(client, "diffusion models", 3)
    ids = [x["paper_id"] for x in body["results"]]
    for pid in ids:
        save(client, pid, "diffusion models")
    lib = client.get("/api/library").json()
    assert [p["paper_id"] for p in lib["papers"]] == ids[::-1]
    assert (lib["total"], lib["unsorted_count"], lib["directories"]) == (3, 3, [])
    assert set(lib["papers"][0]) == ITEM_KEYS


def test_get_library_empty(client):
    assert client.get("/api/library").json() == {
        "papers": [], "directories": [], "unsorted_count": 0, "total": 0,
    }


def test_pdf_state_pending_after_save_until_download_wired(client):
    body = search(client, "diffusion models")
    item = save(client, body["results"][0]["paper_id"], "diffusion models").json()["paper"]
    assert item["pdf"]["status"] in ("pending", "ready")


def test_delete_unsave_returns_annotation_count_then_404(client):
    body = search(client, "diffusion models")
    pid = body["results"][0]["paper_id"]
    save(client, pid, "diffusion models")
    r = client.delete("/api/library", params={"paper_id": pid})
    assert r.status_code == 200 and r.json() == {"deleted": True, "annotations": 0}
    assert client.delete("/api/library", params={"paper_id": pid}).status_code == 404
    conn = client.app.state.conn
    assert db.get_paper(conn, pid) and db.get_result(conn, pid, "diffusion models")
    assert db.get_saved(conn, pid) is None
    assert client.get("/api/library").json()["total"] == 0
    assert all(x["saved"] is False for x in search(client, "diffusion models")["results"])


def test_delete_counts_annotations(client):
    body = search(client, "diffusion models")
    pid = body["results"][0]["paper_id"]
    save(client, pid, "diffusion models")
    conn = client.app.state.conn
    db.create_annotation(conn, pid, 1, "note", "yellow", [], "", "", "", "n")
    db.create_annotation(conn, pid, 1, "highlight", "mint", [[0, 0.1, 0.2, 0.1]], "q", "", "", "")
    r = client.delete("/api/library", params={"paper_id": pid})
    assert r.json() == {"deleted": True, "annotations": 2}


def test_delete_requires_paper_id(client):
    assert client.delete("/api/library").status_code == 422


# ---- directories + move (T048) ---------------------------------------------------------------


def mk_dir(client, name):
    return client.post("/api/directories", json={"name": name})


def saved_ids(client, n=3):
    body = search(client, "diffusion models", n)
    ids = [x["paper_id"] for x in body["results"]]
    for pid in ids:
        save(client, pid, "diffusion models")
    return ids


def test_create_directory_201(client):
    r = mk_dir(client, "  network  ")
    assert r.status_code == 201
    assert r.json() == {"id": r.json()["id"], "name": "network", "count": 0}


@pytest.mark.parametrize(
    ("name", "code", "detail"),
    [
        ("", 422, "Enter a name."),
        ("   ", 422, "Enter a name."),
        ("x" * 41, 422, "Names can be up to 40 characters."),
    ],
)
def test_directory_name_validation(client, name, code, detail):
    r = mk_dir(client, name)
    assert (r.status_code, r.json()) == (code, {"detail": detail})


def test_directory_name_conflicts_409(client):
    mk_dir(client, "Network")
    for name in ("network", "NETWORK", "Unsorted", "all saved"):
        r = mk_dir(client, name)
        assert r.status_code == 409, name
        assert r.json() == {"detail": f'"{name}" already exists.'}
    assert mk_dir(client, "x" * 40).status_code == 201


def test_missing_name_422(client):
    assert client.post("/api/directories", json={}).status_code == 422


def test_rename_keeps_members_and_conflicts(client):
    ids = saved_ids(client, 2)
    d = mk_dir(client, "net").json()
    other = mk_dir(client, "other").json()
    client.post("/api/library/move", json={"paper_id": ids[0], "directory_id": d["id"]})
    r = client.patch(f"/api/directories/{d['id']}", json={"name": "graphs"})
    assert r.status_code == 200 and r.json() == {"id": d["id"], "name": "graphs", "count": 1}
    lib = client.get("/api/library").json()
    member = next(p for p in lib["papers"] if p["paper_id"] == ids[0])
    assert member["directory_id"] == d["id"]
    assert client.patch(f"/api/directories/{d['id']}", json={"name": "OTHER"}).status_code == 409
    assert client.patch(f"/api/directories/{d['id']}", json={"name": "Unsorted"}).status_code == 409
    assert client.patch(f"/api/directories/{d['id']}", json={"name": " "}).status_code == 422
    assert client.patch(f"/api/directories/{other['id'] + 50}", json={"name": "z"}).status_code == 404


def test_delete_directory_moves_members_to_unsorted(client):
    ids = saved_ids(client, 3)
    d = mk_dir(client, "net").json()
    for pid in ids[:2]:
        client.post("/api/library/move", json={"paper_id": pid, "directory_id": d["id"]})
    r = client.delete(f"/api/directories/{d['id']}")
    assert r.status_code == 200 and r.json() == {"deleted": True, "moved": 2}
    lib = client.get("/api/library").json()
    assert all(p["directory_id"] is None for p in lib["papers"])
    assert (lib["directories"], lib["unsorted_count"], lib["total"]) == ([], 3, 3)
    assert client.delete(f"/api/directories/{d['id']}").status_code == 404


def test_move_paper_and_counts(client):
    ids = saved_ids(client, 3)
    b = mk_dir(client, "b").json()
    a = mk_dir(client, "A").json()
    r = client.post("/api/library/move", json={"paper_id": ids[0], "directory_id": b["id"]})
    assert r.status_code == 200 and r.json() == {"paper_id": ids[0], "directory_id": b["id"]}
    client.post("/api/library/move", json={"paper_id": ids[1], "directory_id": b["id"]})
    lib = client.get("/api/library").json()
    assert lib["directories"] == [
        {"id": a["id"], "name": "A", "count": 0}, {"id": b["id"], "name": "b", "count": 2},
    ]
    assert (lib["unsorted_count"], lib["total"]) == (1, 3)
    r = client.post("/api/library/move", json={"paper_id": ids[0], "directory_id": None})
    assert r.status_code == 200 and r.json()["directory_id"] is None
    assert client.get("/api/library").json()["unsorted_count"] == 2


def test_move_unknown_404(client):
    ids = saved_ids(client, 1)
    r = client.post("/api/library/move", json={"paper_id": ids[0], "directory_id": 999})
    assert r.status_code == 404
    d = mk_dir(client, "net").json()
    r = client.post("/api/library/move", json={"paper_id": "nope", "directory_id": d["id"]})
    assert r.status_code == 404
