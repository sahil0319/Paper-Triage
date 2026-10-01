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
