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

_RETRY_ON = (LLMError, ValidationError)  # LLMRefusal is an LLMError
_OUT_KEYS = (
    "paper_id", "title", "authors", "source", "basis", "rank", "rank_reason", "summary",
    "critique", "status", "error",
)


def _retry(fn):
    """Call fn; on a model failure retry once, then let the second failure propagate."""
    try:
        return fn()
    except _RETRY_ON:
        return fn()


def to_out(row: dict) -> dict:
    """db.list_results row -> API result item (contracts/api.md)."""
    return {k: row.get(k) for k in _OUT_KEYS}


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


def triage(query: str, n: int, conn: sqlite3.Connection, http, llm: LLMClient) -> dict:
    """Run a triage. http = (httpx.Client, Throttle) from net.make_http.

    Returns {"topic", "results", "errors"}; raises ValueError on an empty query.
    """
    topic, items = parse_query(query)
    n = max(1, min(int(n), get_settings().max_papers))
    client, throttle = http
    try:
        papers, errors = Fetcher(conn, client, throttle).fetch(topic, items, n)
    except FetchError as e:
        return {"topic": topic, "results": [], "errors": [{"input": topic, "reason": str(e)}]}
    todo = []
    for paper in papers:
        existing = db.get_result(conn, paper["id"], topic)
        if existing is None or existing["status"] != "ok":
            todo.append(paper)
    _process_all(conn, todo, topic, llm)
    results = []
    for paper in papers:
        row = db.get_result(conn, paper["id"], topic)
        results.append(
            to_out({**row, "title": paper["title"], "authors": paper["authors"],
                    "source": paper["source"], "basis": paper["basis"]})
        )
    return {"topic": topic, "results": sort_results(results), "errors": errors}
