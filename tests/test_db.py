import sqlite3

import pytest

from paper_triage import db
from paper_triage.models import Critique, Summary


def paper(pid="2401.00001", **kw):
    return {
        "id": pid, "source": "arxiv", "version": "v1", "title": f"Title {pid}",
        "authors": ["A", "B"], "abstract": "abs", "published": "2024-01-01",
        "pdf_url": "http://x/pdf", "full_text": None, "basis": "abstract", **kw,
    }


@pytest.fixture
def conn(tmp_db):
    c = db.connect(tmp_db)
    db.init_schema(c)
    yield c
    c.close()


def test_init_schema_idempotent_and_tables(conn):
    db.init_schema(conn)
    names = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {"papers", "arxiv_cache", "results", "chat_turns"} <= names


def test_upsert_get_paper(conn):
    assert db.get_paper(conn, "2401.00001") is None
    db.upsert_paper(conn, paper())
    p = db.get_paper(conn, "2401.00001")
    assert p["title"] == "Title 2401.00001" and p["authors"] == ["A", "B"]
    assert p["fetched_at"]
    db.upsert_paper(conn, paper(title="New", full_text="body", basis="fulltext"))
    p = db.get_paper(conn, "2401.00001")
    assert (p["title"], p["full_text"], p["basis"]) == ("New", "body", "fulltext")
    assert db.paper_ids(conn) == ["2401.00001"]


def test_paper_basis_check(conn):
    with pytest.raises(sqlite3.IntegrityError):
        db.upsert_paper(conn, paper(basis="bogus"))


def test_cache(conn):
    assert db.cache_get(conn, "q:x:5") is None
    db.cache_put(conn, "q:x:5", "<feed/>")
    assert db.cache_get(conn, "q:x:5") == "<feed/>"
    db.cache_put(conn, "q:x:5", "<feed2/>")
    assert db.cache_get(conn, "q:x:5") == "<feed2/>"


def save_ok(conn, pid, topic, rank):
    db.save_result(
        conn, pid, topic,
        summary=Summary(summary="s", contributions=["c"]),
        critique=Critique(basis="abstract"), rank=rank, rank_reason="r", status="ok",
    )


def test_save_get_result_roundtrip(conn):
    db.upsert_paper(conn, paper())
    assert db.get_result(conn, "2401.00001", "t") is None
    save_ok(conn, "2401.00001", "t", 7)
    r = db.get_result(conn, "2401.00001", "t")
    assert r["rank"] == 7 and r["status"] == "ok" and r["error"] is None
    assert r["summary"]["contributions"] == ["c"]
    assert r["critique"]["basis"] == "abstract"
    # same key replaces, not duplicates
    save_ok(conn, "2401.00001", "t", 3)
    assert db.get_result(conn, "2401.00001", "t")["rank"] == 3
    assert len(db.list_results(conn, "t")) == 1


def test_list_results_order_rank_desc_failed_last(conn):
    for pid in ("a", "b", "c", "d"):
        db.upsert_paper(conn, paper(pid))
    save_ok(conn, "a", "t", 2)
    db.save_result(conn, "b", "t", status="failed", error="boom")
    save_ok(conn, "c", "t", 9)
    save_ok(conn, "d", "other", 10)
    rows = db.list_results(conn, "t")
    assert [r["paper_id"] for r in rows] == ["c", "a", "b"]
    assert rows[0]["title"] == "Title c" and rows[0]["source"] == "arxiv"
    assert rows[0]["authors"] == ["A", "B"] and rows[0]["basis"] == "abstract"
    assert rows[2]["status"] == "failed" and rows[2]["error"] == "boom" and rows[2]["rank"] is None


def test_latest_topic(conn):
    assert db.latest_topic(conn) is None
    db.upsert_paper(conn, paper("a"))
    save_ok(conn, "a", "first", 1)
    save_ok(conn, "a", "second", 1)
    assert db.latest_topic(conn) == "second"
    save_ok(conn, "a", "", 1)
    assert db.latest_topic(conn) == ""


def test_top_papers(conn):
    for pid in ("a", "b", "c"):
        db.upsert_paper(conn, paper(pid))
    save_ok(conn, "a", "t", 4)
    save_ok(conn, "b", "t", 9)
    save_ok(conn, "b", "u", 2)
    top = db.top_papers(conn, 2)
    assert [p["id"] for p in top] == ["b", "a"]
    assert top[0]["rank"] == 9 and top[0]["summary"]["summary"] == "s"
    assert top[0]["critique"]["basis"] == "abstract"
    assert [p["id"] for p in db.top_papers(conn, 10)] == ["b", "a", "c"]
    assert db.top_papers(conn, 10)[2]["summary"] is None


def test_chat_turn(conn):
    tid = db.save_chat_turn(conn, "q?", "a [x]", ["x"], False)
    row = conn.execute("select * from chat_turns where id=?", (tid,)).fetchone()
    assert row["question"] == "q?" and row["refused"] == 0 and row["created_at"]
    assert row["citations"] == '["x"]'


def test_persistence_across_reconnect(tmp_db):
    c = db.connect(tmp_db)
    db.init_schema(c)
    db.upsert_paper(c, paper())
    save_ok(c, "2401.00001", "t", 6)
    db.cache_put(c, "k", "body")
    db.save_chat_turn(c, "q", "a", [], True)
    c.close()
    c2 = db.connect(tmp_db)
    db.init_schema(c2)
    assert db.get_paper(c2, "2401.00001")["title"]
    assert db.get_result(c2, "2401.00001", "t")["rank"] == 6
    assert db.cache_get(c2, "k") == "body"
    assert c2.execute("select count(*) from chat_turns").fetchone()[0] == 1
    c2.close()


def test_papers_by_ids_input_order_unknown_skipped_latest_result(conn):
    for pid in ("a", "b", "c"):
        db.upsert_paper(conn, paper(pid))
    save_ok(conn, "a", "t", 4)
    save_ok(conn, "b", "t", 9)
    got = db.papers_by_ids(conn, ["c", "zzz", "b", "a"])
    assert [p["id"] for p in got] == ["c", "b", "a"]
    assert got[0]["summary"] is None and got[0]["abstract"] is not None
    assert got[1]["summary"]["summary"] == "s" and got[1]["critique"]["basis"] == "abstract"
    assert got[1]["authors"] == paper("b")["authors"]
    assert db.papers_by_ids(conn, []) == []


def test_touch_results_refreshes_latest_topic_only_for_given_papers(conn):
    for pid in ("a", "b"):
        db.upsert_paper(conn, paper(pid))
    save_ok(conn, "a", "first", 1)
    save_ok(conn, "b", "second", 1)
    assert db.latest_topic(conn) == "second"
    db.touch_results(conn, "first", ["a", "missing"])
    assert db.latest_topic(conn) == "first"
    assert db.get_result(conn, "b", "second")["rank"] == 1


# ---- v3: Library (T045) ---------------------------------------------------------------------

SNAP = {"title": "T", "authors": ["A"], "rank": 8, "rank_reason": "why", "abstract": "abs"}


def saved_conn(conn, pid="2401.00001"):
    db.upsert_paper(conn, paper(pid))
    return conn


def test_v3_tables_exist(conn):
    names = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {"directories", "saved_papers", "saved_tags"} <= names


def test_save_paper_creates_and_lists(conn):
    saved_conn(conn)
    assert db.get_saved(conn, "2401.00001") is None
    assert db.save_paper(conn, "2401.00001", SNAP, "diffusion models", ["diffusion", "models"])
    s = db.get_saved(conn, "2401.00001")
    assert s["snapshot"] == SNAP and s["topic"] == "diffusion models"
    assert s["tags"] == ["diffusion", "models"] and s["directory_id"] is None and s["saved_at"]
    assert db.saved_ids(conn, ["2401.00001", "x"]) == {"2401.00001"}
    assert db.saved_ids(conn, []) == set()


def test_save_paper_idempotent_keeps_snapshot_and_saved_at_merges_tags(conn):
    saved_conn(conn)
    db.save_paper(conn, "2401.00001", SNAP, "a topic", ["topic"])
    first = db.get_saved(conn, "2401.00001")
    created = db.save_paper(conn, "2401.00001", {**SNAP, "rank": 1}, "other", ["topic", "other"])
    assert created is False
    again = db.get_saved(conn, "2401.00001")
    assert again["snapshot"] == SNAP and again["topic"] == "a topic"
    assert again["saved_at"] == first["saved_at"]
    assert again["tags"] == ["topic", "other"]
    db.merge_tags(conn, "2401.00001", ["zeta", "topic"])
    assert db.get_saved(conn, "2401.00001")["tags"] == ["topic", "other", "zeta"]


def test_list_saved_newest_first(conn):
    for pid in ("2401.00001", "2401.00002", "2401.00003"):
        saved_conn(conn, pid)
        db.save_paper(conn, pid, SNAP, "", [])
    assert [s["paper_id"] for s in db.list_saved(conn)] == [
        "2401.00003", "2401.00002", "2401.00001",
    ]
    assert db.get_saved(conn, "2401.00001")["tags"] == []


def test_delete_saved_keeps_papers_and_results(conn):
    saved_conn(conn)
    db.save_result(conn, "2401.00001", "t", status="ok", rank=5, rank_reason="r")
    db.save_paper(conn, "2401.00001", SNAP, "t", ["tt"])
    assert db.delete_saved(conn, "2401.00001") is True
    assert db.delete_saved(conn, "2401.00001") is False
    assert db.get_saved(conn, "2401.00001") is None
    assert conn.execute("select count(*) from saved_tags").fetchone()[0] == 0
    assert db.get_paper(conn, "2401.00001") and db.get_result(conn, "2401.00001", "t")


def test_directory_crud_and_unique_casefold(conn):
    d = db.create_directory(conn, "  Network  ")
    assert d == {"id": d["id"], "name": "Network", "count": 0}
    with pytest.raises(db.DuplicateName, match='"network" already exists.'):
        db.create_directory(conn, "network")
    with pytest.raises(db.DuplicateName):
        db.create_directory(conn, "Unsorted")
    with pytest.raises(db.DuplicateName):
        db.create_directory(conn, "all SAVED")
    with pytest.raises(ValueError, match="Enter a name."):
        db.create_directory(conn, "   ")
    with pytest.raises(ValueError, match="Names can be up to 40 characters."):
        db.create_directory(conn, "x" * 41)
    assert db.create_directory(conn, "x" * 40)["name"] == "x" * 40
    db.create_directory(conn, "alpha")
    assert [x["name"] for x in db.list_directories(conn)] == ["alpha", "Network", "x" * 40]
    renamed = db.rename_directory(conn, d["id"], "Graphs")
    assert renamed["name"] == "Graphs"
    assert db.rename_directory(conn, d["id"], "GRAPHS")["name"] == "GRAPHS"  # same row, new case
    assert db.rename_directory(conn, 999, "zzz") is None
    with pytest.raises(db.DuplicateName):
        db.rename_directory(conn, d["id"], "ALPHA")


def test_move_paper_counts_and_delete_directory_moves_members_to_null(conn):
    d = db.create_directory(conn, "net")
    for pid in ("2401.00001", "2401.00002"):
        saved_conn(conn, pid)
        db.save_paper(conn, pid, SNAP, "", [])
    assert db.move_paper(conn, "2401.00001", d["id"]) is True
    assert db.move_paper(conn, "2401.00002", d["id"]) is True
    assert db.move_paper(conn, "nope", d["id"]) is False
    assert db.move_paper(conn, "2401.00001", 999) is False
    assert db.list_directories(conn)[0]["count"] == 2
    assert db.move_paper(conn, "2401.00002", None) is True
    assert db.list_directories(conn)[0]["count"] == 1
    assert db.delete_directory(conn, d["id"]) == 1
    assert db.get_saved(conn, "2401.00001")["directory_id"] is None
    assert db.delete_directory(conn, d["id"]) is None
    assert db.list_directories(conn) == []


def test_rename_keeps_members(conn):
    d = db.create_directory(conn, "net")
    saved_conn(conn)
    db.save_paper(conn, "2401.00001", SNAP, "", [])
    db.move_paper(conn, "2401.00001", d["id"])
    db.rename_directory(conn, d["id"], "graphs")
    assert db.get_saved(conn, "2401.00001")["directory_id"] == d["id"]
    assert db.list_directories(conn)[0] == {"id": d["id"], "name": "graphs", "count": 1}


# ---- v3: files, pages, annotations (T046) ---------------------------------------------------


def test_v3_file_tables_exist(conn):
    names = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {"paper_files", "paper_pages", "annotations"} <= names


def test_file_status_lifecycle(conn):
    saved_conn(conn)
    db.save_paper(conn, "2401.00001", SNAP, "", [])
    assert db.get_file(conn, "2401.00001") is None
    db.set_file_status(conn, "2401.00001", "pending", source_url="https://x/pdf")
    assert db.get_file(conn, "2401.00001")["status"] == "pending"
    assert db.pending_files(conn) == ["2401.00001"]
    db.set_file_status(
        conn, "2401.00001", "ready", path="/d/a.pdf", bytes=10, sha256="ab", pages=3, error=None
    )
    f = db.get_file(conn, "2401.00001")
    assert (f["status"], f["path"], f["bytes"], f["sha256"], f["pages"]) == (
        "ready", "/d/a.pdf", 10, "ab", 3,
    )
    assert f["source_url"] == "https://x/pdf" and f["updated_at"]
    assert db.pending_files(conn) == []
    db.set_file_status(conn, "2401.00001", "failed", error="Not a PDF.", path=None, pages=None)
    f = db.get_file(conn, "2401.00001")
    assert (f["status"], f["error"], f["path"], f["pages"]) == ("failed", "Not a PDF.", None, None)
    with pytest.raises(ValueError):
        db.set_file_status(conn, "2401.00001", "weird")


def test_pages_replace_and_read(conn):
    saved_conn(conn)
    db.save_paper(conn, "2401.00001", SNAP, "", [])
    assert db.get_pages(conn, "2401.00001") == []
    db.put_pages(conn, "2401.00001", ["one", "", "three"])
    assert db.get_pages(conn, "2401.00001") == ["one", "", "three"]
    db.put_pages(conn, "2401.00001", ["only"])
    assert db.get_pages(conn, "2401.00001") == ["only"]


def test_annotation_crud_order_and_top(conn):
    saved_conn(conn)
    db.save_paper(conn, "2401.00001", SNAP, "", [])
    a = db.create_annotation(
        conn, "2401.00001", 2, "highlight", "mint", [[0.1, 0.5, 0.2, 0.02], [0.1, 0.3, 0.2, 0.02]],
        "quote", "pre", "suf", "",
    )
    assert a["top"] == 0.3 and a["rects"] == [[0.1, 0.5, 0.2, 0.02], [0.1, 0.3, 0.2, 0.02]]
    n = db.create_annotation(conn, "2401.00001", 1, "note", "yellow", [], "", "", "", "page note")
    assert n["top"] == 0 and n["rects"] == [] and n["created_at"] == n["updated_at"]
    b = db.create_annotation(
        conn, "2401.00001", 2, "highlight", "yellow", [[0.1, 0.1, 0.2, 0.02]], "q2", "", "", ""
    )
    assert [x["id"] for x in db.list_annotations(conn, "2401.00001")] == [n["id"], b["id"], a["id"]]
    assert db.annotation_count(conn, "2401.00001") == 3
    assert db.get_annotation(conn, a["id"])["quote"] == "quote"
    u = db.update_annotation(conn, a["id"], color="peach", note="hello")
    assert (u["color"], u["note"]) == ("peach", "hello")
    assert db.update_annotation(conn, a["id"], note="")["note"] == ""
    assert db.update_annotation(conn, 999, note="x") is None
    assert db.delete_annotation(conn, a["id"]) is True
    assert db.delete_annotation(conn, a["id"]) is False
    assert db.annotation_count(conn, "2401.00001") == 2


def test_unsave_cascades_file_pages_and_annotations(conn):
    saved_conn(conn)
    db.save_paper(conn, "2401.00001", SNAP, "t", ["tt"])
    db.set_file_status(conn, "2401.00001", "ready", pages=3)
    db.put_pages(conn, "2401.00001", ["a", "b", "c"])
    db.create_annotation(conn, "2401.00001", 1, "note", "yellow", [], "", "", "", "n")
    db.delete_saved(conn, "2401.00001")
    for table in ("paper_files", "paper_pages", "annotations", "saved_tags"):
        assert conn.execute(f"select count(*) from {table}").fetchone()[0] == 0, table
