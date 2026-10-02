"""Saved-PDF storage: download one PDF to disk, record its status, and clean up (R14).

Network work happens outside the shared lock; status writes take it. The module never extracts
page text (that is lazy, in paper chat).
"""

import hashlib
import os
import sqlite3
import threading
from pathlib import Path

import httpx

from . import db
from .config import Settings
from .extract import ExtractError, page_count

TIMEOUT = httpx.Timeout(60.0, connect=10.0)
HEADERS = {"User-Agent": "paper-triage (personal research tool)"}
CHUNK = 64 * 1024
TOO_BIG = "PDF is larger than 50 MB."


class _Failed(Exception):
    """Download failed; the message is the plain reason stored in paper_files.error."""


def file_name(paper_id: str) -> str:
    """Safe on-disk name: derived from a hash, never from the id text (ids may hold '/')."""
    return hashlib.sha256(paper_id.encode()).hexdigest() + ".pdf"


class _HttpError(Exception):
    def __init__(self, status: int):
        super().__init__(status)
        self.status = status


def _urls(paper: dict) -> list[tuple[str, bool]]:
    """(url, uses_arxiv_throttle) candidates in order."""
    if paper["source"] == "arxiv":
        pid = paper["id"]
        return [
            (f"https://export.arxiv.org/pdf/{pid}", True),
            (f"https://arxiv.org/pdf/{pid}", True),
        ]
    return [(paper["pdf_url"], False)]


def _stream_to(client: httpx.Client, url: str, tmp: Path, cap: int) -> tuple[int, str]:
    """Stream url into tmp. Returns (bytes, sha256). Raises _Failed, or _HttpError on an HTTP error status."""
    try:
        with client.stream("GET", url, headers=HEADERS, timeout=TIMEOUT) as r:
            if r.status_code >= 400:
                raise _HttpError(r.status_code)
            declared = r.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > cap:
                raise _Failed(TOO_BIG)
            digest, size = hashlib.sha256(), 0
            with open(tmp, "wb") as out:
                for chunk in r.iter_bytes(CHUNK):
                    if size == 0 and not chunk.startswith(b"%PDF-"):
                        raise _Failed("Not a PDF.")
                    size += len(chunk)
                    if size > cap:
                        raise _Failed(TOO_BIG)
                    digest.update(chunk)
                    out.write(chunk)
    except httpx.TimeoutException as e:
        raise _Failed("Download timed out.") from e
    except httpx.HTTPError as e:
        raise _Failed("Could not reach the server.") from e
    if size == 0:
        raise _Failed("Not a PDF.")
    return size, digest.hexdigest()


def _fetch(paper: dict, http, tmp: Path, cap: int) -> tuple[str, int, str]:
    """Try the candidate URLs. Returns (url_used, bytes, sha256) or raises _Failed."""
    client, throttle = http
    urls = _urls(paper)
    for i, (url, throttled) in enumerate(urls):
        if throttled:
            throttle.wait()
        try:
            size, digest = _stream_to(client, url, tmp, cap)
            return url, size, digest
        except _HttpError as e:
            retry = (e.status == 404 or e.status >= 500) and i + 1 < len(urls)
            if not retry:
                raise _Failed(f"Download failed (HTTP {e.status}).") from e
    raise _Failed("Download failed.")  # unreachable: every path above returns or raises


def download(
    paper_id: str, conn: sqlite3.Connection, http, lock: threading.Lock, settings: Settings
) -> None:
    """Download a saved paper's PDF and set paper_files to ready or failed. Never raises."""
    with lock:
        saved, paper = db.get_saved(conn, paper_id), db.get_paper(conn, paper_id)
    if saved is None or paper is None:
        return
    pdfs = Path(settings.data_dir).resolve() / "pdfs"
    dest = pdfs / file_name(paper_id)
    tmp = dest.with_suffix(".part")
    url = None
    try:
        pdfs.mkdir(parents=True, exist_ok=True)
        url, size, digest = _fetch(paper, http, tmp, settings.pdf_max_bytes)
        try:
            pages = page_count(tmp.read_bytes())
        except ExtractError as e:
            raise _Failed("PDF could not be read.") from e
        os.replace(tmp, dest)
    except _Failed as e:
        _discard(tmp)
        _record(conn, lock, paper_id, "failed", error=str(e), path=None, bytes=None, sha256=None,
                pages=None)
        return
    except OSError:
        _discard(tmp)
        _record(conn, lock, paper_id, "failed", error="Could not save the PDF.", path=None,
                bytes=None, sha256=None, pages=None)
        return
    if not _record(conn, lock, paper_id, "ready", source_url=url, error=None, path=str(dest),
                   bytes=size, sha256=digest, pages=pages):
        _discard(dest)  # unsaved while downloading: leave nothing behind


def _record(conn, lock, paper_id: str, status: str, **fields) -> bool:
    """Write the status if the paper is still saved. False when it was unsaved meanwhile."""
    with lock:
        if db.get_saved(conn, paper_id) is None:
            return False
        db.set_file_status(conn, paper_id, status, **fields)
        return True


def _discard(path: Path) -> None:
    path.unlink(missing_ok=True)


def sweep_pending(conn: sqlite3.Connection) -> int:
    """At startup: downloads cut short by a restart become failed. Returns how many."""
    ids = db.pending_files(conn)
    for pid in ids:
        db.set_file_status(conn, pid, "failed", error="Download interrupted. Try again.")
    return len(ids)


def delete_file(path: str | None) -> None:
    """Remove a stored PDF (and any leftover partial); missing files are fine."""
    if path:
        p = Path(path)
        _discard(p)
        _discard(p.with_suffix(".part"))
