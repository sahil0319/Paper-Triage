import time

import httpx
import pytest


def test_live_server_status_is_mock(live_server):
    body = httpx.get(f"{live_server.url}/api/status").json()
    assert body["mock"] is True and body["paper_count"] >= 0


def test_triage_delay_applies_to_triage_only(live_server):
    live_server.set_triage_delay(1)
    try:
        t0 = time.monotonic()
        r = httpx.post(
            f"{live_server.url}/api/triage", json={"query": "diffusion", "max_results": 2},
            timeout=10,
        )
        assert r.status_code == 200 and time.monotonic() - t0 >= 1
        t0 = time.monotonic()
        httpx.get(f"{live_server.url}/api/status")
        assert time.monotonic() - t0 < 1
    finally:
        live_server.set_triage_delay(0)


@pytest.mark.e2e
def test_index_loads_offline(live_server, offline_page):
    offline_page.goto("/")
    assert offline_page.title() == "Paper Triage"
