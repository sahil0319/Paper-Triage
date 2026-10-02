"""Playwright stubs for the v3 Library API, shaped per specs/001-paper-triage/contracts/api.md.

The FE lane tests run against the real static files but stub `/api/library*` so they do not depend
on the backend lane. Unstubbed requests fall through to the next handler (the offline guard).
"""

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SAMPLE_PDF = (
    Path(__file__).resolve().parents[2] / "src" / "paper_triage" / "fixtures" / "sample.pdf"
)

LIB_PATHS = re.compile(r".*/api/(library|annotations|directories)(/.*)?(\?.*)?$")


def lib_item(n, **kw):
    """A library item per `GET /api/library`; `n` makes id and title unique."""
    item = {
        "paper_id": f"2401.{n:05d}",
        "title": f"Saved paper {n}: stubbed title",
        "authors": ["A. Author", "B. Author"],
        "source": "arxiv",
        "published": "2024-01-01",
        "abstract": "Stub abstract.",
        "basis": "fulltext",
        "rank": 8,
        "rank_reason": "Stub reason.",
        "summary": None,
        "critique": None,
        "abs_url": f"https://arxiv.org/abs/2401.{n:05d}",
        "pdf_url": f"https://arxiv.org/pdf/2401.{n:05d}",
        "topic": "diffusion models",
        "tags": ["diffusion", "models"],
        "directory_id": None,
        "saved_at": "2026-10-03T10:00:00+00:00",
        "pdf": {"status": "ready", "error": None, "pages": 3},
        "highlight_count": 0,
    }
    item.update(kw)
    return item


def _json(route, body, status=200):
    route.fulfill(status=status, content_type="application/json", body=json.dumps(body))


class LibraryStub:
    """In-memory stand-in for the Library endpoints. `calls` lists (METHOD, path, query, body)."""

    def __init__(self, page, items=None, pdf=True):
        self.page = page
        self.items = list(items or [])
        self.directories = []
        self.calls = []
        self.pdf = pdf
        self.fail = {}  # (METHOD, path) -> (status, detail): next matching call fails once
        self.delay_ms = 0
        page.route(LIB_PATHS, self._handle)

    # -- helpers --
    def listing(self):
        return {
            "papers": self.items,
            "directories": self.directories,
            "unsorted_count": sum(1 for i in self.items if i["directory_id"] is None),
            "total": len(self.items),
        }

    def calls_to(self, method, path):
        return [c for c in self.calls if c[0] == method and c[1] == path]

    def _handle(self, route):
        req = route.request
        u = urlparse(req.url)
        query = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            body = req.post_data_json if req.post_data else None
        except (ValueError, TypeError):
            body = None
        key = (req.method, u.path)
        self.calls.append((req.method, u.path, query, body))
        if key in self.fail:
            status, detail = self.fail.pop(key)
            return _json(route, {"detail": detail}, status)
        if key == ("GET", "/api/library"):
            return _json(route, self.listing())
        if key == ("POST", "/api/library"):
            return self._save(route, body)
        if key == ("DELETE", "/api/library"):
            return self._unsave(route, query.get("paper_id"))
        if key == ("GET", "/api/library/pdf"):
            if self.pdf and SAMPLE_PDF.exists():
                return route.fulfill(
                    status=200,
                    content_type="application/pdf",
                    body=SAMPLE_PDF.read_bytes(),
                    headers={"Content-Disposition": "inline"},
                )
            return _json(route, {"detail": "not found"}, 404)
        return route.fallback()

    def _save(self, route, body):
        pid = body["paper_id"]
        for it in self.items:
            if it["paper_id"] == pid:
                return _json(route, {"created": False, "paper": it})
        n = int(pid.split(".")[-1]) if pid.split(".")[-1].isdigit() else len(self.items) + 100
        item = lib_item(n, paper_id=pid, topic=body.get("topic", ""))
        item["pdf"] = {"status": "pending", "error": None, "pages": None}
        self.items.insert(0, item)
        return _json(route, {"created": True, "paper": item}, 201)

    def _unsave(self, route, pid):
        for it in self.items:
            if it["paper_id"] == pid:
                self.items.remove(it)
                return _json(route, {"deleted": True, "annotations": it["highlight_count"]})
        return _json(route, {"detail": "not saved"}, 404)
