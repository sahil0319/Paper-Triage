"""Triage orchestration: parse -> fetch -> summarize/critique/rank per paper -> persist.

Owns the single retry for LLMError/LLMRefusal/pydantic ValidationError (agents let them propagate).
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError

from . import db
from .config import get_settings
from .critic import critique
from .fetcher import Fetcher, FetchError
from .input_parse import parse_query
from .llm import LLMClient, LLMError
from .ranker import rank
from .summarizer import summarize
from .tags import keywords

_RETRY_ON = (LLMError, ValidationError)  # LLMRefusal is an LLMError
_OUT_KEYS = (
    "paper_id", "title", "authors", "source", "basis", "rank", "rank_reason", "summary",
    "critique", "status", "error", "abs_url", "pdf_url", "saved",
)


def _retry(fn):
    """Call fn; on a model failure retry once, then let the second failure propagate."""
    try:
        return fn()
    except _RETRY_ON:
        return fn()


def source_urls(paper_id: str, source: str, pdf_url: str | None) -> tuple[str | None, str | None]:
    """(abs_url, pdf_url) for a result item: arXiv links derive from the id, a PDF keeps its URL."""
    if source == "arxiv":
        return f"https://arxiv.org/abs/{paper_id}", f"https://arxiv.org/pdf/{paper_id}"
    return None, pdf_url


def to_out(row: dict) -> dict:
    """db.list_results row -> API result item (contracts/api.md)."""
    row = dict(row)
    row["abs_url"], row["pdf_url"] = source_urls(row["paper_id"], row["source"], row.get("pdf_url"))
    row.setdefault("saved", False)
    return {k: row.get(k) for k in _OUT_KEYS}


def mark_saved(conn: sqlite3.Connection, items: list[dict], topic: str | None = None) -> None:
    """Set `saved` on result items. With a topic, also merge its keywords into saved papers' tags."""
    saved = db.saved_ids(conn, [i["paper_id"] for i in items])
    tags = keywords(topic) if topic else []
    for item in items:
        item["saved"] = item["paper_id"] in saved
        if item["saved"] and tags:
            db.merge_tags(conn, item["paper_id"], tags)


class NoStoredResult(LookupError):
    """No stored (paper, topic) result to save (HTTP 404)."""


class ResultFailed(ValueError):
    """The stored result failed, so it cannot be saved (HTTP 409)."""


def build_snapshot(conn: sqlite3.Connection, paper_id: str, topic: str) -> dict:
    """Frozen card data for a saved paper, built from stored data only (never from the client)."""
    paper = db.get_paper(conn, paper_id)
    result = db.get_result(conn, paper_id, topic) if paper else None
    if paper is None or result is None:
        raise NoStoredResult(paper_id)
    if result["status"] != "ok":
        raise ResultFailed(paper_id)
    abs_url, pdf_url = source_urls(paper_id, paper["source"], paper.get("pdf_url"))
    return {
        "title": paper["title"], "authors": paper["authors"], "source": paper["source"],
        "published": paper.get("published"), "abstract": paper.get("abstract") or "",
        "basis": paper["basis"], "rank": result["rank"], "rank_reason": result["rank_reason"],
        "summary": result["summary"], "critique": result["critique"],
        "abs_url": abs_url, "pdf_url": pdf_url,
    }


def library_item(conn: sqlite3.Connection, saved: dict) -> dict:
    """db.get_saved row -> API library item (contracts/api.md)."""
    f = db.get_file(conn, saved["paper_id"]) or {}
    return {
        **saved["snapshot"],
        "paper_id": saved["paper_id"], "topic": saved["topic"], "tags": saved["tags"],
        "directory_id": saved["directory_id"], "saved_at": saved["saved_at"],
        "pdf": {
            "status": f.get("status", "pending"), "error": f.get("error"), "pages": f.get("pages"),
        },
        "highlight_count": db.annotation_count(conn, saved["paper_id"], "highlight"),
    }


def sort_results(items: list[dict]) -> list[dict]:
    """Rank desc, failed last; stable for ties."""
    return sorted(items, key=lambda r: (r["status"] == "failed", -(r["rank"] or 0)))


def _reason(step: str, e: Exception) -> str:
    return f"{step}: {type(e).__name__}: {' '.join(str(e).split())[:200]}"


def _compute(paper: dict, topic: str, llm: LLMClient, crit_pool: ThreadPoolExecutor | None) -> dict:
    """LLM work for one paper; never touches the DB (safe in a worker thread).

    Returns {"summary", "critique", "rank", "rank_reason", "error"}. With crit_pool the critic runs
    alongside the summarizer; without it the order is the original sequential one.
    """
    out = {"summary": None, "critique": None, "rank": None, "rank_reason": None, "error": None}
    step = "summarizer"
    try:
        if crit_pool is None:
            out["summary"] = _retry(lambda: summarize(paper, llm))
            step = "critic"
            out["critique"] = _retry(lambda: critique(paper, llm))
        else:
            fut = crit_pool.submit(_retry, lambda: critique(paper, llm))
            errs = {}
            try:
                out["summary"] = _retry(lambda: summarize(paper, llm))
            except _RETRY_ON as e:
                errs["summarizer"] = e
            try:
                out["critique"] = fut.result()
            except _RETRY_ON as e:
                errs["critic"] = e
            for step, e in errs.items():  # summarizer first, like the sequential order
                raise e
        step = "ranker"
        rk = _retry(lambda: rank(paper, out["summary"], topic, llm))
        out["rank"], out["rank_reason"] = rk.rank, rk.rank_reason
    except _RETRY_ON as e:
        out["error"] = _reason(step, e)
    return out


def _save(conn: sqlite3.Connection, pid: str, topic: str, r: dict) -> None:
    if r["error"]:
        db.save_result(
            conn, pid, topic, status="failed", summary=r["summary"], critique=r["critique"],
            error=r["error"],
        )
    else:
        db.save_result(
            conn, pid, topic, status="ok", summary=r["summary"], critique=r["critique"],
            rank=r["rank"], rank_reason=r["rank_reason"],
        )


def _process_all(conn: sqlite3.Connection, todo: list[dict], topic: str, llm: LLMClient) -> None:
    """Compute (concurrently when TRIAGE_CONCURRENCY > 1), then store in paper order on this thread."""
    workers = get_settings().concurrency
    if workers <= 1 or not todo:
        for paper in todo:
            _save(conn, paper["id"], topic, _compute(paper, topic, llm, None))
        return
    with ThreadPoolExecutor(workers) as pool, ThreadPoolExecutor(workers) as crit_pool:
        futs = [pool.submit(_compute, p, topic, llm, crit_pool) for p in todo]
        for paper, fut in zip(todo, futs, strict=True):
            _save(conn, paper["id"], topic, fut.result())


def triage(
    query: str, n: int, conn: sqlite3.Connection, http, llm: LLMClient, offset: int = 0
) -> dict:
    """Run a triage. http = (httpx.Client, Throttle) from net.make_http.

    Returns {"topic", "results", "errors", "offset", "next_offset", "has_more"}; raises ValueError
    on an empty query, or on offset > 0 for a query with items (paging is for topic searches).
    """
    topic, items = parse_query(query)
    if items and offset > 0:
        raise ValueError("offset only applies to topic searches")
    n = max(1, min(int(n), get_settings().max_papers))
    client, throttle = http
    try:
        papers, errors, page = Fetcher(conn, client, throttle).fetch(topic, items, n, offset)
    except FetchError as e:
        return {
            "topic": topic, "results": [], "errors": [{"input": topic, "reason": str(e)}],
            "offset": offset, "next_offset": None, "has_more": False,
        }
    todo = []
    for paper in papers:
        existing = db.get_result(conn, paper["id"], topic)
        if existing is None or existing["status"] != "ok":
            todo.append(paper)
    _process_all(conn, todo, topic, llm)
    db.touch_results(conn, topic, [p["id"] for p in papers if p not in todo])
    results = []
    for paper in papers:
        row = db.get_result(conn, paper["id"], topic)
        results.append(
            to_out({**row, "title": paper["title"], "authors": paper["authors"],
                    "source": paper["source"], "basis": paper["basis"],
                    "pdf_url": paper.get("pdf_url")})
        )
    results = sort_results(results)
    mark_saved(conn, results, topic)
    return {"topic": topic, "results": results, "errors": errors, "offset": offset, **page}
