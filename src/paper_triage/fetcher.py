"""Fetcher runtime agent (LLM-free): arXiv metadata via throttled, cached API calls."""

import hashlib
import re
import sqlite3
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

from . import db
from .extract import ExtractError, extract_text, pdf_title

API_URL = "https://export.arxiv.org/api/query"
_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "os": "http://a9.com/-/spec/opensearch/1.1/",
}
FULL_TEXT_CAP = 200_000
ABSTRACT_CHARS = 1500
_ABS = re.compile(r"^https?://arxiv\.org/abs/(.+?)(?:v(\d+))?$")


class FetchError(Exception):
    pass


def _clean(s: str | None) -> str:
    return " ".join((s or "").split())


def parse_feed(xml: str) -> list[dict]:
    """Atom feed -> paper dicts (metadata only). Non-paper entries (arXiv errors) are skipped."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise FetchError(f"bad arXiv response: {e}") from e
    papers = []
    for e in root.findall("a:entry", _NS):
        m = _ABS.match(_clean(e.findtext("a:id", namespaces=_NS)))
        if not m:
            continue
        pid, ver = m.group(1), (f"v{m.group(2)}" if m.group(2) else None)
        pdf_url = next(
            (
                lk.get("href")
                for lk in e.findall("a:link", _NS)
                if lk.get("title") == "pdf" and lk.get("href")
            ),
            f"https://arxiv.org/pdf/{pid}{ver or ''}",
        )
        papers.append(
            {
                "id": pid,
                "source": "arxiv",
                "version": ver,
                "title": _clean(e.findtext("a:title", namespaces=_NS)) or pid,
                "authors": [
                    _clean(n.text) for n in e.findall("a:author/a:name", _NS) if _clean(n.text)
                ],
                "abstract": _clean(e.findtext("a:summary", namespaces=_NS)),
                "published": _clean(e.findtext("a:published", namespaces=_NS))[:10] or None,
                "pdf_url": pdf_url,
                "full_text": None,
                "basis": "abstract",
            }
        )
    return papers


def parse_total(xml: str) -> int | None:
    """`opensearch:totalResults` of an Atom body, or None when absent or not a number."""
    try:
        text = ET.fromstring(xml).findtext("os:totalResults", namespaces=_NS)
        return int(text.strip()) if text else None
    except (ET.ParseError, ValueError):
        return None


class Fetcher:
    def __init__(self, conn: sqlite3.Connection, client: httpx.Client, throttle):
        self.conn = conn
        self.client = client
        self.throttle = throttle

    def _api(self, key: str, params: dict) -> tuple[list[dict], int | None]:
        """Read-through cache of the raw Atom body; throttled on network use.

        Returns (papers, reported total or None).
        """
        body = db.cache_get(self.conn, key)
        if body is None:
            self.throttle.wait()
            try:
                r = self.client.get(API_URL, params=params)
                r.raise_for_status()
            except httpx.HTTPError as e:
                raise FetchError(f"arXiv request failed: {e}") from e
            body = r.text
            papers = parse_feed(body)
            if papers:  # never cache empty results (may be a transient miss)
                db.cache_put(self.conn, key, body)
            return papers, parse_total(body)
        return parse_feed(body), parse_total(body)

    def search(self, topic: str, n: int, offset: int = 0) -> tuple[list[dict], int | None]:
        """One page of a topic search: (papers, source-reported total or None)."""
        words = topic.lower().split()
        if not words:
            return [], 0
        key = f"q:{' '.join(words)}:{n}:{offset}"
        params = {
            "search_query": " AND ".join(f"all:{w}" for w in words),
            "start": offset,
            "max_results": n,
            "sortBy": "relevance",
        }
        return self._api(key, params)

    def by_ids(self, ids: list[str]) -> tuple[list[dict], list[dict]]:
        """Returns (papers in input order, error entries {"input", "reason"})."""
        if not ids:
            return [], []
        key = "ids:" + ",".join(sorted(ids))
        params = {"id_list": ",".join(ids), "max_results": len(ids)}
        try:
            found = {p["id"]: p for p in self._api(key, params)[0]}
        except FetchError as e:
            return [], [{"input": i, "reason": str(e)} for i in ids]
        papers = [found[i] for i in ids if i in found]
        errors = [{"input": i, "reason": "not found"} for i in ids if i not in found]
        return papers, errors

    # ---- PDFs and orchestration ----

    def _download(self, url: str, throttled: bool) -> bytes:
        if throttled:
            self.throttle.wait()
        try:
            r = self.client.get(url)
            r.raise_for_status()
        except (httpx.HTTPError, httpx.InvalidURL, ValueError) as e:  # ValueError: host-less URL
            raise FetchError(f"download failed: {e}") from e
        return r.content

    def _add_fulltext(self, paper: dict) -> dict:
        """arXiv paper: try the PDF; any failure keeps the abstract basis."""
        try:
            text = extract_text(self._download(paper["pdf_url"], throttled=True))
        except (FetchError, ExtractError):
            return paper
        return {**paper, "full_text": text[:FULL_TEXT_CAP], "basis": "fulltext"}

    def _pdf_paper(self, url: str) -> dict:
        """Direct (non-arXiv) PDF URL -> paper dict; raises FetchError/ExtractError."""
        data = self._download(url, throttled=(urlparse(url).hostname or "").endswith("arxiv.org"))
        text = extract_text(data)
        basename = urlparse(url).path.rsplit("/", 1)[-1]
        return {
            "id": _pdf_id(url),
            "source": "pdf",
            "version": None,
            "title": pdf_title(data) or basename or url,
            "authors": [],
            "abstract": _clean(text)[:ABSTRACT_CHARS],
            "published": None,
            "pdf_url": url,
            "full_text": text[:FULL_TEXT_CAP],
            "basis": "fulltext",
        }

    def fetch(
        self, topic: str, items: list, n: int, offset: int = 0
    ) -> tuple[list[dict], list[dict], dict]:
        """Resolve a parsed query into stored papers.

        items: (kind, value) pairs, kind "arxiv" (id) or "pdf" (URL); with no items, search topic
        from `offset`. Returns (papers, errors, page); page = {"next_offset", "has_more"}
        (item searches: None / False). One bad item never stops the others. Stored papers are
        reused without network.
        """
        if not items:
            found, total = self.search(topic, n, offset)
            candidates = [self._stored(p) or self._add_fulltext(p) for p in found]
            next_offset = offset + len(found)
            has_more = bool(found) and (
                total > next_offset if total is not None else len(found) >= n
            )
            page = {"next_offset": next_offset, "has_more": has_more}
            return [self._save(p) for p in candidates], [], page
        items = items[:n]
        missing = [v for k, v in items if k == "arxiv" and not db.get_paper(self.conn, v)]
        fetched, fetch_errors = self.by_ids(missing)
        meta = {p["id"]: p for p in fetched}
        err = {e["input"]: e for e in fetch_errors}
        papers, errors = [], []
        for kind, value in items:
            pid = value if kind == "arxiv" else _pdf_id(value)
            paper = db.get_paper(self.conn, pid) or meta.get(pid)
            try:
                if paper is None and kind == "pdf":
                    paper = self._pdf_paper(value)
                elif paper is None:
                    raise FetchError(err[value]["reason"])
                elif kind == "arxiv" and pid in meta:
                    paper = self._add_fulltext(paper)
            except (FetchError, ExtractError) as e:
                errors.append({"input": value, "reason": str(e)})
                continue
            papers.append(self._save(paper))
        return papers, errors, {"next_offset": None, "has_more": False}

    def _stored(self, paper: dict) -> dict | None:
        return db.get_paper(self.conn, paper["id"])

    def _save(self, paper: dict) -> dict:
        if not db.get_paper(self.conn, paper["id"]):
            db.upsert_paper(self.conn, paper)
        return paper


def _pdf_id(url: str) -> str:
    return "pdf:" + hashlib.sha256(url.encode()).hexdigest()[:12]
