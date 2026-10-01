"""HTTP client factory: real httpx + arXiv throttle, or MockTransport serving fixtures."""

import re
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

FIXTURES = Path(__file__).parent / "fixtures"
TIMEOUT = 20.0
INVALID_PDF_ID = "2401.00005"
_ENTRY = re.compile(r"  <entry>.*?</entry>\n", re.DOTALL)


class Throttle:
    """Ensures >= min_interval seconds between wait() returns (process-wide when shared)."""

    def __init__(self, min_interval=3.0, clock=time.monotonic, sleep=time.sleep):
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last: float | None = None

    def wait(self) -> None:
        with self._lock:
            if self._last is not None:
                remaining = self.min_interval - (self._clock() - self._last)
                if remaining > 0:
                    self._sleep(remaining)
            self._last = self._clock()


def _norm_id(s: str) -> str:
    return re.sub(r"v\d+$", "", s.strip())


def _feed(ids: list[str] | None, n: int | None) -> str:
    xml = (FIXTURES / "arxiv_search.xml").read_text()
    entries = _ENTRY.findall(xml)
    head = xml[: xml.index(entries[0])]
    if ids is not None:
        wanted = {_norm_id(i) for i in ids}
        entries = [
            e for e in entries if _norm_id(re.search(r"/abs/([^<]+)<", e).group(1)) in wanted
        ]
    elif n is not None:
        entries = entries[:n]
    return head + "".join(entries) + "</feed>\n"


def _mock_handler(request: httpx.Request) -> httpx.Response:
    url = request.url
    if url.host.endswith("arxiv.org"):
        if url.path == "/api/query":
            q = parse_qs(url.query.decode())
            ids = q["id_list"][0].split(",") if "id_list" in q else None
            n = int(q["max_results"][0]) if "max_results" in q else None
            return httpx.Response(
                200, text=_feed(ids, n), headers={"content-type": "application/atom+xml"}
            )
        if url.path.startswith("/pdf/"):
            if _norm_id(url.path.removeprefix("/pdf/")) == INVALID_PDF_ID:
                return httpx.Response(200, content=b"this is not a pdf")
            return httpx.Response(200, content=(FIXTURES / "sample.pdf").read_bytes())
        return httpx.Response(404)
    if urlparse(str(url)).path.endswith(".pdf") and not url.host.endswith(".invalid"):
        return httpx.Response(200, content=(FIXTURES / "sample.pdf").read_bytes())
    return httpx.Response(404)


def make_http(mock: bool) -> tuple[httpx.Client, Throttle]:
    if mock:
        client = httpx.Client(transport=httpx.MockTransport(_mock_handler), follow_redirects=True)
        return client, Throttle(min_interval=0)
    client = httpx.Client(timeout=TIMEOUT, follow_redirects=True)
    return client, Throttle(min_interval=3.0)
