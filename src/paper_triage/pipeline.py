"""Triage orchestration: parse -> fetch -> summarize/critique/rank per paper -> persist.

Owns the single retry for LLMError/LLMRefusal/pydantic ValidationError (agents let them propagate).
"""

import sqlite3

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


def _process(conn: sqlite3.Connection, paper: dict, topic: str, llm: LLMClient) -> None:
    """Run the three agents for one paper and store the result (ok, or failed with partials)."""
    pid = paper["id"]
    step, summary, crit = "summarizer", None, None
    try:
        summary = _retry(lambda: summarize(paper, llm))
        step = "critic"
        crit = _retry(lambda: critique(paper, llm))
        step = "ranker"
        rk = _retry(lambda: rank(paper, summary, topic, llm))
    except _RETRY_ON as e:
        db.save_result(
            conn, pid, topic, status="failed", summary=summary, critique=crit,
            error=_reason(step, e),
        )
        return
    db.save_result(
        conn, pid, topic, status="ok", summary=summary, critique=crit, rank=rk.rank,
        rank_reason=rk.rank_reason,
    )


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
    results = []
    for paper in papers:
        existing = db.get_result(conn, paper["id"], topic)
        if existing is None or existing["status"] != "ok":
            _process(conn, paper, topic, llm)
        row = db.get_result(conn, paper["id"], topic)
        results.append(
            to_out({**row, "title": paper["title"], "authors": paper["authors"],
                    "source": paper["source"], "basis": paper["basis"]})
        )
    return {"topic": topic, "results": sort_results(results), "errors": errors}
