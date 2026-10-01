"""Chat runtime agent: grounded Q&A over stored papers. Validates citations against the store."""

import re
import sqlite3

from . import db
from .config import get_settings
from .llm import SENTINEL, LLMClient
from .models import ChatAnswer
from .prompting import load_prompt

REFUSAL_TEXT = "I can only answer from the stored papers, and they do not cover that."
EMPTY_STORE_TEXT = "No papers are stored yet. Run a triage first, then ask about the results."
_CITE = re.compile(r"\[([^\[\]\s]+)\]")


def _attr(s: str) -> str:
    return " ".join(s.split()).replace('"', "'")


def _context(papers: list[dict]) -> str:
    blocks = []
    for p in papers:
        lines = [f"Abstract: {p.get('abstract') or ''}"]
        s, c = p.get("summary"), p.get("critique")
        if s:
            lines.append(f"Summary: {s['summary']}")
            lines.append("Contributions: " + "; ".join(s["contributions"]))
        if c:
            lines.append("Weak claims: " + "; ".join(f"{w['claim']} ({w['why']})"
                                                     for w in c["weak_claims"]))
            lines.append("Overclaims: " + "; ".join(f"{o['claim']} ({o['evidence_gap']})"
                                                    for o in c["overclaims"]))
            lines.append("Missing baselines: " + "; ".join(c["missing_baselines"]))
        body = "\n".join(lines)
        blocks.append(f'<paper id="{p["id"]}" title="{_attr(p["title"])}">\n{body}\n</paper>')
    return "\n".join(blocks)


def answer(question: str, conn: sqlite3.Connection, client: LLMClient) -> ChatAnswer:
    stored = set(db.paper_ids(conn))
    if not stored:
        return ChatAnswer(answer=EMPTY_STORE_TEXT, refused=True)
    papers = db.top_papers(conn, get_settings().chat_top_k)
    user = f"{_context(papers)}\n<question>\n{question}\n</question>"
    text = client.text(load_prompt("chat"), user).strip()

    cited: list[str] = []
    dropped: list[str] = []
    for cid in _CITE.findall(text):
        bucket = cited if cid in stored else dropped
        if cid not in bucket:
            bucket.append(cid)

    if SENTINEL in text or not cited:
        cleaned = text.replace(SENTINEL, "").strip(" :-\n") if SENTINEL in text else ""
        reply = cleaned if cleaned and not _CITE.search(cleaned) else REFUSAL_TEXT
        return ChatAnswer(answer=reply, refused=True, dropped_citations=dropped)
    return ChatAnswer(answer=text, citations=cited, refused=False, dropped_citations=dropped)
