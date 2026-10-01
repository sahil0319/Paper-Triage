"""Fetcher runtime agent (LLM-free): arXiv metadata via throttled, cached API calls."""

import re
import sqlite3
import xml.etree.ElementTree as ET

import httpx

from . import db

API_URL = "https://export.arxiv.org/api/query"
_NS = {"a": "http://www.w3.org/2005/Atom"}
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


class Fetcher:
    def __init__(self, conn: sqlite3.Connection, client: httpx.Client, throttle):
        self.conn = conn
        self.client = client
        self.throttle = throttle

    def _api(self, key: str, params: dict) -> list[dict]:
        """Read-through cache of the raw Atom body; throttled on network use."""
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
            return papers
        return parse_feed(body)

    def search(self, topic: str, n: int) -> list[dict]:
        words = topic.lower().split()
        if not words:
            return []
        key = f"q:{' '.join(words)}:{n}"
        params = {
            "search_query": " AND ".join(f"all:{w}" for w in words),
            "start": 0,
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
            found = {p["id"]: p for p in self._api(key, params)}
        except FetchError as e:
            return [], [{"input": i, "reason": str(e)} for i in ids]
        papers = [found[i] for i in ids if i in found]
        errors = [{"input": i, "reason": "not found"} for i in ids if i not in found]
        return papers, errors
