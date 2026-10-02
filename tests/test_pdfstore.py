import hashlib
import threading
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from paper_triage import db, pdfstore
from paper_triage.config import get_settings
from paper_triage.net import Throttle, _mock_handler, make_http

SAMPLE = Path(__file__).parent.parent / "src/paper_triage/fixtures/sample.pdf"


class SpyThrottle(Throttle):
    def __init__(self):
        super().__init__(min_interval=0)
        self.waits = 0

    def wait(self):
        self.waits += 1


@pytest.fixture
def conn(tmp_db):
    c = db.connect(tmp_db)
    db.init_schema(c)
    yield c
    c.close()


@pytest.fixture
def settings(tmp_path):
    return replace(get_settings(), data_dir=str(tmp_path / "data"))


def add(conn, pid, source="arxiv", pdf_url=None):
    db.upsert_paper(
        conn,
        {"id": pid, "source": source, "version": None, "title": "T", "authors": [],
         "abstract": "a", "published": None, "pdf_url": pdf_url, "full_text": None,
         "basis": "abstract"},
    )
    db.save_paper(conn, pid, {"title": "T"}, "", [])
    db.set_file_status(conn, pid, "pending")


def http_from(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True), SpyThrottle()


def mock_http():
    client, _ = make_http(True)
    return client, SpyThrottle()


def run(conn, pid, http, settings):
    pdfstore.download(pid, conn, http, threading.Lock(), settings)
    return db.get_file(conn, pid)


def test_arxiv_download_ready(conn, settings):
    add(conn, "2401.00001")
    http = mock_http()
    f = run(conn, "2401.00001", http, settings)
    name = hashlib.sha256(b"2401.00001").hexdigest() + ".pdf"
    assert f["status"] == "ready" and f["error"] is None
    assert f["path"] == str(Path(settings.data_dir).resolve() / "pdfs" / name)
    assert Path(f["path"]).read_bytes() == SAMPLE.read_bytes()
    assert f["bytes"] == SAMPLE.stat().st_size
    assert f["sha256"] == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    assert f["pages"] == 3
    assert f["source_url"] == "https://export.arxiv.org/pdf/2401.00001"
    assert http[1].waits == 1
    assert db.get_pages(conn, "2401.00001") == []  # text is extracted lazily, never here
    assert [p.name for p in (Path(settings.data_dir) / "pdfs").iterdir()] == [name]


def test_not_a_pdf_fails(conn, settings):
    add(conn, "2401.00005")
    f = run(conn, "2401.00005", mock_http(), settings)
    assert (f["status"], f["error"], f["path"]) == ("failed", "Not a PDF.", None)
    assert list((Path(settings.data_dir) / "pdfs").iterdir()) == []


def test_too_big_fails_and_leaves_no_file(conn, settings):
    add(conn, "2401.00001")
    f = run(conn, "2401.00001", mock_http(), replace(settings, pdf_max_bytes=100))
    assert (f["status"], f["error"]) == ("failed", "PDF is larger than 50 MB.")
    assert f["path"] is None and f["bytes"] is None
    assert list((Path(settings.data_dir) / "pdfs").iterdir()) == []


def test_content_length_over_cap_fails_early(conn, settings):
    def handler(request):
        return httpx.Response(200, content=b"%PDF-" + b"x" * 10, headers={"content-length": "999"})

    add(conn, "2401.00001")
    f = run(conn, "2401.00001", http_from(handler), replace(settings, pdf_max_bytes=100))
    assert f["error"] == "PDF is larger than 50 MB."


def test_export_404_falls_back_to_arxiv_host(conn, settings):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.host == "export.arxiv.org":
            return httpx.Response(404)
        return _mock_handler(request)

    add(conn, "2401.00001")
    http = http_from(handler)
    f = run(conn, "2401.00001", http, settings)
    assert f["status"] == "ready" and f["source_url"] == "https://arxiv.org/pdf/2401.00001"
    assert seen == ["https://export.arxiv.org/pdf/2401.00001", "https://arxiv.org/pdf/2401.00001"]
    assert http[1].waits == 2


def test_export_5xx_falls_back_both_fail(conn, settings):
    add(conn, "2401.00001")
    f = run(conn, "2401.00001", http_from(lambda r: httpx.Response(503)), settings)
    assert f["status"] == "failed" and "503" in f["error"]


def test_direct_pdf_uses_pdf_url_and_skips_throttle(conn, settings):
    pid = "pdf:abc123def456"
    add(conn, pid, "pdf", "https://example.org/papers/x.pdf")
    http = mock_http()
    f = run(conn, pid, http, settings)
    assert f["status"] == "ready" and f["pages"] == 3
    assert f["source_url"] == "https://example.org/papers/x.pdf"
    assert http[1].waits == 0
    name = Path(f["path"]).name
    assert name == hashlib.sha256(pid.encode()).hexdigest() + ".pdf"


def test_invalid_host_fails(conn, settings):
    pid = "pdf:000000000000"
    add(conn, pid, "pdf", "https://down.invalid/x.pdf")
    f = run(conn, pid, mock_http(), settings)
    assert f["status"] == "failed" and "404" in f["error"] and f["path"] is None


def test_old_style_id_makes_safe_file_name(conn, settings):
    add(conn, "math.GT/0107001")
    f = run(conn, "math.GT/0107001", mock_http(), settings)
    assert f["status"] == "ready"
    p = Path(f["path"])
    assert p.parent == (Path(settings.data_dir) / "pdfs").resolve() and p.suffix == ".pdf"
    assert "/" not in p.name and "." not in p.stem
    assert f["source_url"] == "https://export.arxiv.org/pdf/math.GT/0107001"


def test_unreadable_pdf_fails(conn, settings):
    def handler(request):
        return httpx.Response(200, content=b"%PDF-1.4\ngarbage with no objects at all")

    add(conn, "2401.00001")
    f = run(conn, "2401.00001", http_from(handler), settings)
    assert (f["status"], f["error"]) == ("failed", "PDF could not be read.")
    assert list((Path(settings.data_dir) / "pdfs").iterdir()) == []


def test_timeout_and_network_errors_fail(conn, settings):
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def broken(request):
        raise httpx.ConnectError("down", request=request)

    add(conn, "2401.00001")
    assert run(conn, "2401.00001", http_from(timeout), settings)["error"] == "Download timed out."
    f = run(conn, "2401.00001", http_from(broken), settings)
    assert f["status"] == "failed" and f["error"] == "Could not reach the server."


def test_unsaved_during_download_leaves_nothing(conn, settings):
    def handler(request):
        db.delete_saved(conn, "2401.00001")  # user unsaves while the download runs
        return _mock_handler(request)

    add(conn, "2401.00001")
    pdfstore.download("2401.00001", conn, http_from(handler), threading.Lock(), settings)
    assert db.get_file(conn, "2401.00001") is None
    assert list((Path(settings.data_dir) / "pdfs").iterdir()) == []


def test_sweep_pending_marks_failed(conn):
    add(conn, "2401.00001")
    add(conn, "2401.00002")
    db.set_file_status(conn, "2401.00002", "ready", pages=3)
    assert pdfstore.sweep_pending(conn) == 1
    f = db.get_file(conn, "2401.00001")
    assert (f["status"], f["error"]) == ("failed", "Download interrupted. Try again.")
    assert db.get_file(conn, "2401.00002")["status"] == "ready"
    assert pdfstore.sweep_pending(conn) == 0


def test_delete_file(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"x")
    pdfstore.delete_file(str(f))
    assert not f.exists()
    pdfstore.delete_file(str(f))  # already gone: no error
    pdfstore.delete_file(None)
