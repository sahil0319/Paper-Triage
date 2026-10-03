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
        self.annotations = []
        self._ann_id = 0
        self.after_retry = None  # pdf dict a retried item takes on the first GET after the retry
        self._flip = None
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
            if self._flip:
                pid, pdf = self._flip
                self._flip = None
                for it in self.items:
                    if it["paper_id"] == pid:
                        it["pdf"] = pdf
            return _json(route, self.listing())
        if key == ("POST", "/api/library"):
            return self._save(route, body)
        if key == ("DELETE", "/api/library"):
            return self._unsave(route, query.get("paper_id"))
        if u.path == "/api/annotations" or u.path.startswith("/api/annotations/"):
            return self._annotations(route, req.method, u.path, query, body)
        if key == ("POST", "/api/library/retry"):
            return self._retry(route, body)
        if key == ("GET", "/api/library/pdf"):
            if isinstance(self.pdf, bytes):
                return route.fulfill(status=200, content_type="application/pdf", body=self.pdf)
            if self.pdf == "garbage":
                return route.fulfill(
                    status=200, content_type="application/pdf", body=b"%PDF-1.4 not really"
                )
            if self.pdf and SAMPLE_PDF.exists():
                return route.fulfill(
                    status=200,
                    content_type="application/pdf",
                    body=SAMPLE_PDF.read_bytes(),
                    headers={"Content-Disposition": "inline"},
                )
            return _json(route, {"detail": "not found"}, 404)
        return route.fallback()

    def _annotations(self, route, method, path, query, body):
        now = "2026-10-03T10:00:00+00:00"
        if path == "/api/annotations" and method == "GET":
            rows = [a for a in self.annotations if a["paper_id"] == query.get("paper_id")]
            rows.sort(
                key=lambda a: (a["page"], min((r[1] for r in a["rects"]), default=0), a["id"])
            )
            return _json(route, {"annotations": rows})
        if path == "/api/annotations" and method == "POST":
            self._ann_id += 1
            ann = {
                "id": self._ann_id,
                "paper_id": body["paper_id"],
                "page": body["page"],
                "kind": body.get("kind", "highlight"),
                "color": body.get("color", "yellow"),
                "rects": body.get("rects", []),
                "quote": body.get("quote", ""),
                "prefix": body.get("prefix", ""),
                "suffix": body.get("suffix", ""),
                "note": body.get("note", ""),
                "created_at": now,
                "updated_at": now,
            }
            self.annotations.append(ann)
            for it in self.items:
                if it["paper_id"] == ann["paper_id"]:
                    it["highlight_count"] = sum(
                        1
                        for a in self.annotations
                        if a["paper_id"] == it["paper_id"] and a["kind"] == "highlight"
                    )
            return _json(route, ann, 201)
        ann_id = int(path.rsplit("/", 1)[1])
        ann = next((a for a in self.annotations if a["id"] == ann_id), None)
        if ann is None:
            return _json(route, {"detail": "not found"}, 404)
        if method == "PATCH":
            for k in ("color", "note"):
                if k in body:
                    ann[k] = body[k]
            return _json(route, ann)
        if method == "DELETE":
            self.annotations.remove(ann)
            return route.fulfill(status=204, body="")
        return route.fallback()

    def _retry(self, route, body):
        for it in self.items:
            if it["paper_id"] == body["paper_id"]:
                if it["pdf"]["status"] != "failed":
                    return _json(route, {"detail": "PDF is not in a failed state"}, 409)
                it["pdf"] = {"status": "pending", "error": None, "pages": None}
                if self.after_retry:
                    self._flip = (it["paper_id"], self.after_retry)
                return _json(route, {"pdf": it["pdf"]}, 202)
        return _json(route, {"detail": "not in the library"}, 404)

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


COLUMN_LEFT = [
    "Left column line one about sampling",
    "Left column line two about distillation",
    "Left column line three about students",
    "Left column line four about teachers",
]
COLUMN_RIGHT = [
    "Right column line one about latents",
    "Right column line two about filters",
    "Right column line three about stages",
    "Right column line four about schedules",
]


def two_column_pdf():
    """A 1-page, two-column PDF (stdlib, raw objects): 4 short lines per column, a wide gutter."""

    def col(x, lines):
        body = f"BT /F1 11 Tf 14 TL {x} 700 Td\n"
        body += "".join(f"({t}) Tj T*\n" for t in lines)
        return body + "ET\n"

    content = (col(50, COLUMN_LEFT) + col(330, COLUMN_RIGHT)).encode("latin-1")
    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        4: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (num, objs[num])
    xref = len(out)
    out += b"xref\n0 6\n0000000000 65535 f \n"
    for num in range(1, 6):
        out += b"%010d 00000 n \n" % offsets[num]
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % xref
    return bytes(out)
