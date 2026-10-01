"""SQLite storage (stdlib sqlite3). Schema per specs/001-paper-triage/data-model.md."""

import json
import sqlite3
from datetime import UTC, datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL CHECK (source IN ('arxiv','pdf')),
  version TEXT,
  title TEXT NOT NULL,
  authors TEXT NOT NULL DEFAULT '[]',
  abstract TEXT NOT NULL DEFAULT '',
  published TEXT,
  pdf_url TEXT,
  full_text TEXT,
  basis TEXT NOT NULL CHECK (basis IN ('fulltext','abstract')),
  fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS arxiv_cache (
  key TEXT PRIMARY KEY,
  body TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
  paper_id TEXT NOT NULL REFERENCES papers(id),
  topic TEXT NOT NULL,
  summary TEXT,
  critique TEXT,
  rank INTEGER,
  rank_reason TEXT,
  status TEXT NOT NULL CHECK (status IN ('ok','failed')),
  error TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (paper_id, topic)
);
CREATE TABLE IF NOT EXISTS chat_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  citations TEXT NOT NULL DEFAULT '[]',
  refused INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _dump(obj) -> str | None:
    if obj is None:
        return None
    if hasattr(obj, "model_dump_json"):
        return obj.model_dump_json()
    return json.dumps(obj)


def _load(s: str | None):
    return None if s is None else json.loads(s)


def _paper_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["authors"] = json.loads(d["authors"])
    return d


def upsert_paper(conn: sqlite3.Connection, p: dict) -> None:
    conn.execute(
        """INSERT INTO papers (id, source, version, title, authors, abstract, published, pdf_url,
                               full_text, basis, fetched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET source=excluded.source, version=excluded.version,
             title=excluded.title, authors=excluded.authors, abstract=excluded.abstract,
             published=excluded.published, pdf_url=excluded.pdf_url,
             full_text=excluded.full_text, basis=excluded.basis, fetched_at=excluded.fetched_at""",
        (
            p["id"], p["source"], p.get("version"), p["title"], json.dumps(p.get("authors") or []),
            p.get("abstract") or "", p.get("published"), p.get("pdf_url"), p.get("full_text"),
            p["basis"], _now(),
        ),
    )
    conn.commit()


def get_paper(conn: sqlite3.Connection, paper_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()
    return _paper_dict(row) if row else None


def paper_ids(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT id FROM papers ORDER BY id")]


def cache_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT body FROM arxiv_cache WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def cache_put(conn: sqlite3.Connection, key: str, body: str) -> None:
    conn.execute(
        "INSERT INTO arxiv_cache (key, body, fetched_at) VALUES (?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET body=excluded.body, fetched_at=excluded.fetched_at",
        (key, body, _now()),
    )
    conn.commit()


def save_result(
    conn: sqlite3.Connection,
    paper_id: str,
    topic: str,
    *,
    status: str,
    summary=None,
    critique=None,
    rank: int | None = None,
    rank_reason: str | None = None,
    error: str | None = None,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO results (paper_id, topic, summary, critique, rank, rank_reason, "
        "status, error, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (paper_id, topic, _dump(summary), _dump(critique), rank, rank_reason, status, error,
         _now()),
    )
    conn.commit()


def _result_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    for k in ("summary", "critique", "authors"):
        if k in d and d[k] is not None:
            d[k] = json.loads(d[k])
    return d


def get_result(conn: sqlite3.Connection, paper_id: str, topic: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM results WHERE paper_id=? AND topic=?", (paper_id, topic)
    ).fetchone()
    return _result_dict(row) if row else None


def list_results(conn: sqlite3.Connection, topic: str) -> list[dict]:
    """Results for a topic joined with paper fields: rank desc, failed last."""
    rows = conn.execute(
        """SELECT r.*, p.title, p.authors, p.source, p.basis, p.pdf_url
           FROM results r JOIN papers p ON p.id = r.paper_id
           WHERE r.topic = ?
           ORDER BY r.status = 'failed', r.rank DESC, r.rowid""",
        (topic,),
    ).fetchall()
    return [_result_dict(r) for r in rows]


def latest_topic(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT topic FROM results ORDER BY created_at DESC, rowid DESC").fetchone()
    return row[0] if row else None


def top_papers(conn: sqlite3.Connection, k: int) -> list[dict]:
    """Stored papers by best ok rank desc (unranked last), with that result's summary/critique."""
    rows = conn.execute(
        """SELECT p.*, r.summary, r.critique, MAX(r.rank) AS rank
           FROM papers p LEFT JOIN results r ON r.paper_id = p.id AND r.status = 'ok'
           GROUP BY p.id
           ORDER BY rank IS NULL, rank DESC, p.id
           LIMIT ?""",
        (k,),
    ).fetchall()
    return [_result_dict(r) for r in rows]


def save_chat_turn(
    conn: sqlite3.Connection, question: str, answer: str, citations: list[str], refused: bool
) -> int:
    cur = conn.execute(
        "INSERT INTO chat_turns (question, answer, citations, refused, created_at) "
        "VALUES (?,?,?,?,?)",
        (question, answer, json.dumps(citations), int(refused), _now()),
    )
    conn.commit()
    return cur.lastrowid
