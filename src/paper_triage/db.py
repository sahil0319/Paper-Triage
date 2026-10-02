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
CREATE TABLE IF NOT EXISTS directories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  name_key TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_papers (
  paper_id TEXT PRIMARY KEY REFERENCES papers(id),
  snapshot TEXT NOT NULL,
  topic TEXT NOT NULL DEFAULT '',
  directory_id INTEGER REFERENCES directories(id) ON DELETE SET NULL,
  saved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_tags (
  paper_id TEXT NOT NULL REFERENCES saved_papers(paper_id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  added_at TEXT NOT NULL,
  PRIMARY KEY (paper_id, tag)
);
CREATE TABLE IF NOT EXISTS paper_files (
  paper_id TEXT PRIMARY KEY REFERENCES saved_papers(paper_id) ON DELETE CASCADE,
  source_url TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending','ready','failed')),
  error TEXT,
  path TEXT,
  bytes INTEGER,
  sha256 TEXT,
  pages INTEGER,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_pages (
  paper_id TEXT NOT NULL REFERENCES saved_papers(paper_id) ON DELETE CASCADE,
  page INTEGER NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY (paper_id, page)
);
CREATE TABLE IF NOT EXISTS annotations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  paper_id TEXT NOT NULL REFERENCES saved_papers(paper_id) ON DELETE CASCADE,
  page INTEGER NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('highlight','note')),
  color TEXT NOT NULL DEFAULT 'yellow',
  rects TEXT NOT NULL DEFAULT '[]',
  top REAL NOT NULL DEFAULT 0,
  quote TEXT NOT NULL DEFAULT '',
  prefix TEXT NOT NULL DEFAULT '',
  suffix TEXT NOT NULL DEFAULT '',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
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


def touch_results(conn: sqlite3.Connection, topic: str, paper_ids: list[str]) -> None:
    """Mark existing results as just used so `latest_topic` reflects the most recent run."""
    conn.executemany(
        "UPDATE results SET created_at=? WHERE topic=? AND paper_id=?",
        [(_now(), topic, pid) for pid in paper_ids],
    )
    conn.commit()


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


def papers_by_ids(conn: sqlite3.Connection, ids: list[str]) -> list[dict]:
    """Each stored paper with its latest result's summary/critique, in input order.

    Unknown ids are skipped; repeated ids yield one entry.
    """
    out, seen = [], set()
    for pid in ids:
        if pid in seen:
            continue
        seen.add(pid)
        row = conn.execute(
            """SELECT p.*, r.summary, r.critique
               FROM papers p LEFT JOIN results r ON r.paper_id = p.id
               WHERE p.id = ?
               ORDER BY r.created_at DESC, r.rowid DESC LIMIT 1""",
            (pid,),
        ).fetchone()
        if row:
            out.append(_result_dict(row))
    return out


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


# ---- v3 Library: saved papers, tags, directories -------------------------------------------

RESERVED_DIR_NAMES = frozenset({"unsorted", "all saved"})
DIR_NAME_MAX = 40


class DuplicateName(ValueError):
    """A directory name collides with another directory or a reserved name (HTTP 409)."""


def _saved_dict(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    d = dict(row)
    d["snapshot"] = json.loads(d["snapshot"])
    d["tags"] = [
        r[0]
        for r in conn.execute(
            "SELECT tag FROM saved_tags WHERE paper_id=? ORDER BY added_at, rowid",
            (d["paper_id"],),
        )
    ]
    return d


def merge_tags(conn: sqlite3.Connection, paper_id: str, tags: list[str]) -> None:
    """Add tags to a saved paper; tags it already has are left alone (INSERT OR IGNORE)."""
    now = _now()
    conn.executemany(
        "INSERT OR IGNORE INTO saved_tags (paper_id, tag, added_at) VALUES (?,?,?)",
        [(paper_id, t, now) for t in tags],
    )
    conn.commit()


def save_paper(
    conn: sqlite3.Connection, paper_id: str, snapshot: dict, topic: str, tags: list[str]
) -> bool:
    """Save a paper once. True when newly saved; if already saved only merge tags (False)."""
    created = (
        conn.execute(
            "INSERT OR IGNORE INTO saved_papers (paper_id, snapshot, topic, saved_at) "
            "VALUES (?,?,?,?)",
            (paper_id, json.dumps(snapshot), topic, _now()),
        ).rowcount
        == 1
    )
    merge_tags(conn, paper_id, tags)
    return created


def get_saved(conn: sqlite3.Connection, paper_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM saved_papers WHERE paper_id=?", (paper_id,)).fetchone()
    return _saved_dict(conn, row) if row else None


def list_saved(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM saved_papers ORDER BY saved_at DESC, rowid DESC").fetchall()
    return [_saved_dict(conn, r) for r in rows]


def saved_ids(conn: sqlite3.Connection, ids: list[str]) -> set[str]:
    if not ids:
        return set()
    marks = ",".join("?" * len(ids))
    rows = conn.execute(f"SELECT paper_id FROM saved_papers WHERE paper_id IN ({marks})", ids)
    return {r[0] for r in rows}


def delete_saved(conn: sqlite3.Connection, paper_id: str) -> bool:
    """Unsave; tags, file row, page text and annotations go with it (ON DELETE CASCADE)."""
    n = conn.execute("DELETE FROM saved_papers WHERE paper_id=?", (paper_id,)).rowcount
    conn.commit()
    return n == 1


def _clean_dir_name(name: str) -> tuple[str, str]:
    name = name.strip()
    if not name:
        raise ValueError("Enter a name.")
    if len(name) > DIR_NAME_MAX:
        raise ValueError(f"Names can be up to {DIR_NAME_MAX} characters.")
    return name, name.casefold()


def _dir_count(conn: sqlite3.Connection, directory_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM saved_papers WHERE directory_id=?", (directory_id,)
    ).fetchone()[0]


def get_directory(conn: sqlite3.Connection, directory_id: int) -> dict | None:
    row = conn.execute("SELECT id, name FROM directories WHERE id=?", (directory_id,)).fetchone()
    return {"id": row["id"], "name": row["name"], "count": _dir_count(conn, row["id"])} if row else None


def create_directory(conn: sqlite3.Connection, name: str) -> dict:
    name, key = _clean_dir_name(name)
    if key in RESERVED_DIR_NAMES:
        raise DuplicateName(f'"{name}" already exists.')
    try:
        cur = conn.execute(
            "INSERT INTO directories (name, name_key, created_at) VALUES (?,?,?)",
            (name, key, _now()),
        )
    except sqlite3.IntegrityError as e:
        raise DuplicateName(f'"{name}" already exists.') from e
    conn.commit()
    return {"id": cur.lastrowid, "name": name, "count": 0}


def rename_directory(conn: sqlite3.Connection, directory_id: int, name: str) -> dict | None:
    name, key = _clean_dir_name(name)
    if key in RESERVED_DIR_NAMES:
        raise DuplicateName(f'"{name}" already exists.')
    if get_directory(conn, directory_id) is None:
        return None
    try:
        conn.execute(
            "UPDATE directories SET name=?, name_key=? WHERE id=?", (name, key, directory_id)
        )
    except sqlite3.IntegrityError as e:
        raise DuplicateName(f'"{name}" already exists.') from e
    conn.commit()
    return get_directory(conn, directory_id)


def delete_directory(conn: sqlite3.Connection, directory_id: int) -> int | None:
    """Delete a directory; its papers become Unsorted. Returns how many moved, None if unknown."""
    if get_directory(conn, directory_id) is None:
        return None
    moved = _dir_count(conn, directory_id)
    conn.execute("DELETE FROM directories WHERE id=?", (directory_id,))
    conn.commit()
    return moved


def list_directories(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """SELECT d.id, d.name, COUNT(s.paper_id) AS count
           FROM directories d LEFT JOIN saved_papers s ON s.directory_id = d.id
           GROUP BY d.id ORDER BY d.name_key"""
    ).fetchall()
    return [dict(r) for r in rows]


def move_paper(conn: sqlite3.Connection, paper_id: str, directory_id: int | None) -> bool:
    """Move a saved paper to a directory (None = Unsorted). False for unknown paper/directory."""
    if directory_id is not None and get_directory(conn, directory_id) is None:
        return False
    n = conn.execute(
        "UPDATE saved_papers SET directory_id=? WHERE paper_id=?", (directory_id, paper_id)
    ).rowcount
    conn.commit()
    return n == 1


# ---- v3: PDF files, page text, annotations ------------------------------------------------

FILE_STATUSES = ("pending", "ready", "failed")
_FILE_FIELDS = ("source_url", "error", "path", "bytes", "sha256", "pages")
ANNOTATION_COLORS = ("yellow", "mint", "peach")


def set_file_status(conn: sqlite3.Connection, paper_id: str, status: str, **fields) -> None:
    """Upsert the paper_files row. Only the given fields change; others keep their value."""
    if status not in FILE_STATUSES:
        raise ValueError(f"bad file status: {status}")
    bad = set(fields) - set(_FILE_FIELDS)
    if bad:
        raise ValueError(f"unknown file fields: {sorted(bad)}")
    cols = ["paper_id", "status", "updated_at", *fields]
    marks = ",".join("?" * len(cols))
    sets = ", ".join(f"{c}=excluded.{c}" for c in cols[1:])
    conn.execute(
        f"INSERT INTO paper_files ({', '.join(cols)}) VALUES ({marks}) "
        f"ON CONFLICT(paper_id) DO UPDATE SET {sets}",
        (paper_id, status, _now(), *fields.values()),
    )
    conn.commit()


def get_file(conn: sqlite3.Connection, paper_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM paper_files WHERE paper_id=?", (paper_id,)).fetchone()
    return dict(row) if row else None


def pending_files(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT paper_id FROM paper_files WHERE status='pending' ORDER BY rowid")
    return [r[0] for r in rows]


def put_pages(conn: sqlite3.Connection, paper_id: str, texts: list[str]) -> None:
    conn.execute("DELETE FROM paper_pages WHERE paper_id=?", (paper_id,))
    conn.executemany(
        "INSERT INTO paper_pages (paper_id, page, text) VALUES (?,?,?)",
        [(paper_id, i, t) for i, t in enumerate(texts, start=1)],
    )
    conn.commit()


def get_pages(conn: sqlite3.Connection, paper_id: str) -> list[str]:
    rows = conn.execute("SELECT text FROM paper_pages WHERE paper_id=? ORDER BY page", (paper_id,))
    return [r[0] for r in rows]


def _annotation_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["rects"] = json.loads(d["rects"])
    return d


def get_annotation(conn: sqlite3.Connection, annotation_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM annotations WHERE id=?", (annotation_id,)).fetchone()
    return _annotation_dict(row) if row else None


def create_annotation(
    conn: sqlite3.Connection,
    paper_id: str,
    page: int,
    kind: str,
    color: str,
    rects: list[list[float]],
    quote: str,
    prefix: str,
    suffix: str,
    note: str,
) -> dict:
    now = _now()
    top = min((r[1] for r in rects), default=0)
    cur = conn.execute(
        "INSERT INTO annotations (paper_id, page, kind, color, rects, top, quote, prefix, suffix, "
        "note, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (paper_id, page, kind, color, json.dumps(rects), top, quote, prefix, suffix, note, now,
         now),
    )
    conn.commit()
    return get_annotation(conn, cur.lastrowid)


def update_annotation(
    conn: sqlite3.Connection, annotation_id: int, color: str | None = None, note: str | None = None
) -> dict | None:
    if get_annotation(conn, annotation_id) is None:
        return None
    if color is not None:
        conn.execute("UPDATE annotations SET color=? WHERE id=?", (color, annotation_id))
    if note is not None:
        conn.execute("UPDATE annotations SET note=? WHERE id=?", (note, annotation_id))
    conn.execute("UPDATE annotations SET updated_at=? WHERE id=?", (_now(), annotation_id))
    conn.commit()
    return get_annotation(conn, annotation_id)


def delete_annotation(conn: sqlite3.Connection, annotation_id: int) -> bool:
    n = conn.execute("DELETE FROM annotations WHERE id=?", (annotation_id,)).rowcount
    conn.commit()
    return n == 1


def list_annotations(conn: sqlite3.Connection, paper_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM annotations WHERE paper_id=? ORDER BY page, top, id", (paper_id,)
    ).fetchall()
    return [_annotation_dict(r) for r in rows]


def annotation_count(conn: sqlite3.Connection, paper_id: str, kind: str | None = None) -> int:
    if kind is None:
        q, args = "SELECT COUNT(*) FROM annotations WHERE paper_id=?", (paper_id,)
    else:
        q, args = "SELECT COUNT(*) FROM annotations WHERE paper_id=? AND kind=?", (paper_id, kind)
    return conn.execute(q, args).fetchone()[0]
