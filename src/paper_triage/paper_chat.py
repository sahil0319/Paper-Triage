"""Paper chat runtime agent: grounded Q&A over ONE saved paper's own PDF text.

Lazy: page text is extracted on the first question for a paper with a ready PDF (and only then).
Nothing about the chat is stored. Highlights and notes are never part of the context.
"""

import re
import sqlite3
import threading
from pathlib import Path

from . import db
from .config import Settings
from .extract import ExtractError, extract_pages
from .llm import SENTINEL, LLMClient
from .models import PaperChatAnswer
from .prompting import load_prompt

NOT_READY_TEXT = "Chat needs the PDF text. It is not ready yet."
NO_TEXT_TEXT = "This PDF has no extractable text."
REFUSAL_TEXT = "I can only answer from this paper, and it does not cover that."
_CITE = re.compile(r"\[p\.(\d+)\]")


class NotSaved(LookupError):
    """The paper is not in the Library (HTTP 404)."""


def build_context(pages: list[str], cap: int) -> str:
    """`<page n="N">` blocks for the paper text, cut off once `cap` characters are used."""
    blocks, used = [], 0
    for n, text in enumerate(pages, start=1):
        text = text.strip()
        room = cap - used
        if room <= 0:
            break
        text = text[:room]
        blocks.append(f'<page n="{n}">\n{text}\n</page>')
        used += len(text)
    return "\n".join(blocks)


def _history(turns: list[dict]) -> str:
    if not turns:
        return ""
    body = "\n".join(
        f"<turn><q>{t['question']}</q><a>{t['answer']}</a></turn>" for t in turns
    )
    return f"<history>\n{body}\n</history>\n"


def _refused(text: str, dropped: list[int] | None = None) -> PaperChatAnswer:
    return PaperChatAnswer(answer=text, refused=True, dropped_pages=dropped or [])


def _load_pages(
    paper_id: str, conn: sqlite3.Connection, lock: threading.Lock
) -> list[str] | None:
    """Stored page text, extracting it from the PDF on first use. None when the PDF is not ready."""
    with lock:
        if db.get_saved(conn, paper_id) is None:
            raise NotSaved(paper_id)
        f = db.get_file(conn, paper_id)
        if f is None or f["status"] != "ready" or not f["path"]:
            return None
        pages = db.get_pages(conn, paper_id)
    if pages:
        return pages
    try:
        pages = extract_pages(Path(f["path"]).read_bytes())
    except (ExtractError, OSError):
        return None
    with lock:
        if db.get_saved(conn, paper_id) is None:
            raise NotSaved(paper_id)
        db.put_pages(conn, paper_id, pages)
    return pages


def answer(
    paper_id: str,
    question: str,
    history: list[dict],
    conn: sqlite3.Connection,
    client: LLMClient,
    lock: threading.Lock,
    settings: Settings,
) -> PaperChatAnswer:
    """Answer from the paper's pages only. Raises NotSaved, or LLMError from the model call."""
    pages = _load_pages(paper_id, conn, lock)
    if pages is None:
        return _refused(NOT_READY_TEXT)
    if not any(p.strip() for p in pages):
        return _refused(NO_TEXT_TEXT)
    turns = history[-settings.paper_chat_history :]
    user = (
        f"{build_context(pages, settings.paper_chat_cap)}\n{_history(turns)}"
        f"<question>\n{question}\n</question>"
    )
    text = client.text(load_prompt("paper_chat"), user).strip()  # no lock held during the call

    cited: list[int] = []
    dropped: list[int] = []
    for m in _CITE.findall(text):
        n = int(m)
        bucket = cited if 1 <= n <= len(pages) else dropped
        if n not in bucket:
            bucket.append(n)

    if SENTINEL in text or not cited:
        cleaned = text.replace(SENTINEL, "").strip(" :-\n") if SENTINEL in text else ""
        reply = cleaned if cleaned and not _CITE.search(cleaned) else REFUSAL_TEXT
        return _refused(reply, dropped)
    return PaperChatAnswer(answer=text, pages=cited, refused=False, dropped_pages=dropped)
