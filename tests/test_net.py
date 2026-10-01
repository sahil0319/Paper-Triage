import httpx
from pypdf import PdfReader

from paper_triage.net import Throttle, make_http

API = "http://export.arxiv.org/api/query"


class FakeTime:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s


def test_throttle_spaces_calls():
    t = FakeTime()
    th = Throttle(min_interval=3.0, clock=t.clock, sleep=t.sleep)
    stamps = []
    for _ in range(3):
        th.wait()
        stamps.append(t.now)
    assert stamps[1] - stamps[0] >= 3.0
    assert stamps[2] - stamps[1] >= 3.0
    assert t.sleeps == [3.0, 3.0]  # first call free


def test_throttle_skips_sleep_when_already_elapsed():
    t = FakeTime()
    th = Throttle(min_interval=3.0, clock=t.clock, sleep=t.sleep)
    th.wait()
    t.now += 10
    th.wait()
    assert t.sleeps == []


def test_throttle_zero_never_sleeps():
    t = FakeTime()
    th = Throttle(min_interval=0, clock=t.clock, sleep=t.sleep)
    for _ in range(3):
        th.wait()
    assert t.sleeps == []


def test_make_http_real_config_no_network():
    client, th = make_http(False)
    assert isinstance(client, httpx.Client)
    assert client.follow_redirects is True
    assert client.timeout.read == 20
    assert th.min_interval == 3.0
    client.close()


def test_mock_search_returns_five_entries():
    client, th = make_http(True)
    assert th.min_interval == 0
    r = client.get(API, params={"search_query": "all:diffusion", "max_results": 10})
    assert r.status_code == 200
    assert r.text.count("<entry>") == 5


def test_mock_id_list_known_and_unknown():
    client, _ = make_http(True)
    r = client.get(API, params={"id_list": "2401.00002"})
    assert r.text.count("<entry>") == 1
    assert "Consistency Models" in r.text
    r = client.get(API, params={"id_list": "9999.99999"})
    assert r.status_code == 200
    assert "<entry>" not in r.text


def test_mock_pdfs_four_valid_one_invalid(tmp_path):
    client, _ = make_http(True)
    valid = 0
    invalid = 0
    for n in range(1, 6):
        r = client.get(f"http://arxiv.org/pdf/2401.0000{n}v1")
        assert r.status_code == 200
        if r.content.startswith(b"%PDF"):
            p = tmp_path / f"{n}.pdf"
            p.write_bytes(r.content)
            text = "".join(pg.extract_text() for pg in PdfReader(str(p)).pages)
            assert len(text) > 500
            valid += 1
        else:
            invalid += 1
    assert (valid, invalid) == (4, 1)


def test_mock_other_urls():
    client, _ = make_http(True)
    assert client.get("https://example.org/papers/x.pdf").content.startswith(b"%PDF")
    assert client.get("https://down.invalid/x.pdf").status_code == 404
