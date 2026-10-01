import hashlib
from pathlib import Path

import httpx
import pytest

from paper_triage import db
from paper_triage.fetcher import Fetcher, FetchError, parse_feed
from paper_triage.net import make_http


class CountingThrottle:
    def __init__(self):
        self.waits = 0

    def wait(self):
        self.waits += 1


@pytest.fixture
def env(tmp_db):
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    client, _ = make_http(True)
    requests = []
    client.event_hooks["request"].append(lambda r: requests.append(r))
    th = CountingThrottle()
    return Fetcher(conn, client, th), requests, th, conn


# ---- search ----


def test_search_returns_normalized_papers(env):
    f, _, _, _ = env
    papers, total = f.search("diffusion distillation", 5)
    assert len(papers) == 5 and total == 15
    p = papers[0]
    assert p["id"] == "2401.00001"
    assert p["version"] == "v1"
    assert p["source"] == "arxiv"
    assert p["title"] == "Progressive Distillation for Fast Sampling of Diffusion Models"
    assert p["authors"] == ["Ada Lovelace", "Alan Turing"]
    assert p["published"] == "2024-01-02"
    assert p["pdf_url"] == "http://arxiv.org/pdf/2401.00001v1"
    assert p["abstract"].startswith("We distill")
    assert p["basis"] == "abstract"
    assert p["full_text"] is None
    assert papers[1]["version"] == "v2"


def test_search_respects_n_and_query_params(env):
    f, requests, _, _ = env
    assert len(f.search("diffusion distillation", 3)[0]) == 3
    q = requests[0].url.params
    assert q["search_query"] == "all:diffusion AND all:distillation"
    assert q["max_results"] == "3"
    assert q["sortBy"] == "relevance"


def test_search_throttled_and_cached(env):
    f, requests, th, conn = env
    a = f.search("Diffusion  Distillation", 5)
    b = f.search("diffusion distillation", 5)  # same normalized key
    assert a == b
    assert len(requests) == 1
    assert th.waits == 1
    assert db.cache_get(conn, "q:diffusion distillation:5:0") is not None
    f.search("diffusion distillation", 4)  # different n -> new request
    assert len(requests) == 2


def test_search_http_failure_raises(tmp_db):
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    with pytest.raises(FetchError):
        Fetcher(conn, client, CountingThrottle()).search("x", 5)


# ---- by_ids ----


def test_by_ids_found_and_not_found(env):
    f, _, _, _ = env
    papers, errors = f.by_ids(["2401.00002", "9999.99999"])
    assert [p["id"] for p in papers] == ["2401.00002"]
    assert errors == [{"input": "9999.99999", "reason": "not found"}]


def test_by_ids_preserves_input_order(env):
    f, _, _, _ = env
    papers, errors = f.by_ids(["2401.00003", "2401.00001"])
    assert [p["id"] for p in papers] == ["2401.00003", "2401.00001"]
    assert errors == []


def test_by_ids_cached(env):
    f, requests, th, conn = env
    f.by_ids(["2401.00002", "2401.00001"])
    f.by_ids(["2401.00001", "2401.00002"])
    assert len(requests) == 1
    assert th.waits == 1
    assert db.cache_get(conn, "ids:2401.00001,2401.00002") is not None


def test_by_ids_empty_makes_no_request(env):
    f, requests, _, _ = env
    assert f.by_ids([]) == ([], [])
    assert requests == []


def test_by_ids_http_failure_reports_each_id(tmp_db):
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    papers, errors = Fetcher(conn, client, CountingThrottle()).by_ids(["2401.00001"])
    assert papers == []
    assert errors[0]["input"] == "2401.00001"
    assert errors[0]["reason"]


# ---- parse_feed ----


def test_parse_feed_skips_arxiv_error_entry():
    xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/api/errors#incorrect_id_format_for_1234</id>
  <title>Error</title><summary>incorrect id format</summary></entry>
</feed>"""
    assert parse_feed(xml) == []


def test_parse_feed_old_style_id_and_missing_pdf_link():
    xml = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/abs/math.GT/0107001v3</id>
  <published>2001-07-01T00:00:00Z</published>
  <title>Some\n   Old  Paper</title><summary>  An abstract.\n</summary>
  </entry>
</feed>"""
    (p,) = parse_feed(xml)
    assert p["id"] == "math.GT/0107001"
    assert p["version"] == "v3"
    assert p["title"] == "Some Old Paper"
    assert p["abstract"] == "An abstract."
    assert p["authors"] == []
    assert p["pdf_url"] == "https://arxiv.org/pdf/math.GT/0107001v3"


# ---- part 2: PDFs, full text, orchestration ----

SAMPLE = (Path(__file__).parent.parent / "src/paper_triage/fixtures/sample.pdf").read_bytes()


def test_fetch_topic_fulltext_and_abstract_fallback(env):
    f, _, th, conn = env
    papers, errors, _ = f.fetch("diffusion distillation", [], 5)
    assert errors == []
    by_id = {p["id"]: p for p in papers}
    assert len(papers) == 5
    for pid in ("2401.00001", "2401.00002", "2401.00003", "2401.00004"):
        assert by_id[pid]["basis"] == "fulltext"
        assert len(by_id[pid]["full_text"]) > 500
    assert by_id["2401.00005"]["basis"] == "abstract"
    assert by_id["2401.00005"]["full_text"] is None
    assert th.waits == 6  # 1 search + 5 arxiv PDF downloads
    stored = db.get_paper(conn, "2401.00001")
    assert stored["basis"] == "fulltext" and stored["full_text"]
    assert db.get_paper(conn, "2401.00005")["basis"] == "abstract"


def test_fetch_full_text_capped(env):
    f, _, _, _ = env
    papers, _, _ = f.fetch("", [("arxiv", "2401.00001")], 10)
    assert len(papers[0]["full_text"]) <= 200_000


def test_fetch_ids_unknown_reported_others_continue(env):
    f, _, _, _ = env
    papers, errors, _ = f.fetch("", [("arxiv", "2401.00002"), ("arxiv", "9999.99999")], 10)
    assert [p["id"] for p in papers] == ["2401.00002"]
    assert errors == [{"input": "9999.99999", "reason": "not found"}]


def test_fetch_pdf_url(env):
    f, _, th, conn = env
    url = "https://example.org/papers/x.pdf"
    papers, errors, _ = f.fetch("", [("pdf", url)], 10)
    assert errors == []
    (p,) = papers
    assert p["id"] == "pdf:" + hashlib.sha256(url.encode()).hexdigest()[:12]
    assert p["source"] == "pdf"
    assert p["basis"] == "fulltext"
    assert p["title"] == "Sample Paper on Diffusion Distillation"
    assert p["pdf_url"] == url
    assert 0 < len(p["abstract"]) <= 1500
    assert p["abstract"].startswith("Sample Paper on Diffusion Distillation")
    assert len(p["full_text"]) > 500
    assert th.waits == 0  # non-arXiv hosts are not arXiv-throttled
    assert db.get_paper(conn, p["id"])["title"] == p["title"]


def test_fetch_pdf_title_falls_back_to_url_basename(tmp_db):
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    pdf = SAMPLE.replace(b" /Info 6 0 R", b"")
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=pdf)))
    (p,), _, _ = Fetcher(conn, client, CountingThrottle()).fetch(
        "", [("pdf", "https://example.org/dir/my-paper.pdf")], 10
    )
    assert p["title"] == "my-paper.pdf"


def test_fetch_unreachable_url_is_error_others_continue(env):
    f, _, _, _ = env
    good = "https://example.org/a.pdf"
    bad = "https://down.invalid/x.pdf"
    papers, errors, _ = f.fetch("", [("pdf", bad), ("pdf", good)], 10)
    assert [p["source"] for p in papers] == ["pdf"]
    assert errors == [{"input": bad, "reason": errors[0]["reason"]}]
    assert errors[0]["reason"]


def test_fetch_non_pdf_bytes_url_is_error(tmp_db):
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    html = httpx.MockTransport(lambda r: httpx.Response(200, content=b"<html>"))
    client = httpx.Client(transport=html)
    papers, errors, _ = Fetcher(conn, client, CountingThrottle()).fetch(
        "", [("pdf", "https://example.org/page")], 10
    )
    assert papers == []
    assert errors[0]["input"] == "https://example.org/page"


def test_fetch_mixed_items_keep_input_order(env):
    f, _, _, _ = env
    url = "https://example.org/a.pdf"
    papers, _, _ = f.fetch("", [("pdf", url), ("arxiv", "2401.00003"), ("arxiv", "2401.00001")], 10)
    assert [p["id"] for p in papers][1:] == ["2401.00003", "2401.00001"]
    assert papers[0]["source"] == "pdf"


def test_fetch_reuses_stored_papers_without_network(env):
    f, requests, _, _ = env
    url = "https://example.org/a.pdf"
    f.fetch("", [("pdf", url), ("arxiv", "2401.00001")], 10)
    n = len(requests)
    papers, errors, _ = f.fetch("", [("pdf", url), ("arxiv", "2401.00001")], 10)
    assert len(papers) == 2 and errors == []
    assert len(requests) == n


def test_fetch_caps_items_at_n(env):
    f, _, _, _ = env
    papers, _, _ = f.fetch("", [("arxiv", f"2401.0000{i}") for i in (1, 2, 3, 4)], 2)
    assert len(papers) == 2


def test_fetch_hostless_url_is_error_others_continue(env):
    f, _, _, _ = env
    papers, errors, _ = f.fetch("", [("pdf", "http://"), ("arxiv", "2401.00001")], 10)
    assert [p["id"] for p in papers] == ["2401.00001"]
    assert errors[0]["input"] == "http://"
    assert errors[0]["reason"]


# ---- v2 paging ----


def test_search_offset_sends_start_and_keys_cache(env):
    f, requests, _, conn = env
    papers, total = f.search("diffusion distillation", 5, 10)
    assert [p["id"] for p in papers] == [f"2401.{i:05d}" for i in range(11, 16)]
    assert total == 15
    assert requests[0].url.params["start"] == "10"
    assert db.cache_get(conn, "q:diffusion distillation:5:10") is not None
    f.search("diffusion distillation", 5, 10)
    assert len(requests) == 1
    f.search("diffusion distillation", 5)  # offset 0 is a different key
    assert len(requests) == 2


def test_search_missing_total_is_none(tmp_db):
    xml = (Path(__file__).parent.parent / "src/paper_triage/fixtures/arxiv_search.xml").read_text()
    xml = xml.replace("<opensearch:totalResults>15</opensearch:totalResults>", "")
    conn = db.connect(tmp_db)
    db.init_schema(conn)
    db.cache_put(conn, "q:x:5:0", xml)
    client, _ = make_http(True)
    papers, total = Fetcher(conn, client, CountingThrottle()).search("x", 5)
    assert len(papers) == 15 and total is None


def test_fetch_topic_page_info(env):
    f, _, _, _ = env
    _, _, page = f.fetch("diffusion distillation", [], 10)
    assert page == {"next_offset": 10, "has_more": True}
    _, _, page = f.fetch("diffusion distillation", [], 5, 10)
    assert page == {"next_offset": 15, "has_more": False}
    _, _, page = f.fetch("diffusion distillation", [], 5, 15)
    assert page == {"next_offset": 15, "has_more": False}


def test_fetch_page_fallback_without_total(env, monkeypatch):
    f, _, _, _ = env
    monkeypatch.setattr(f, "search", lambda t, n, o=0: (f.__class__.search(f, t, n, o)[0], None))
    _, _, page = f.fetch("diffusion", [], 5)
    assert page == {"next_offset": 5, "has_more": True}  # full page -> assume more
    _, _, page = f.fetch("diffusion", [], 20)
    assert page["has_more"] is False  # only 15 returned < 20


def test_fetch_items_have_no_paging(env):
    f, _, _, _ = env
    _, _, page = f.fetch("", [("arxiv", "2401.00001")], 10)
    assert page == {"next_offset": None, "has_more": False}
