from pathlib import Path
from urllib.parse import urlparse

import pytest

LOCAL_HOSTS = {"127.0.0.1", "localhost"}
CHROMIUM_MISSING = "chromium not installed: run `uv run playwright install chromium`"


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


def _chromium_installed() -> bool:
    try:
        from playwright.sync_api import Error, sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except (ImportError, Error):
        return False


def pytest_collection_modifyitems(config, items):
    """Skip e2e (real-browser) tests when chromium is not installed."""
    e2e = [i for i in items if i.get_closest_marker("e2e")]
    if e2e and not _chromium_installed():
        skip = pytest.mark.skip(reason=CHROMIUM_MISSING)
        for item in e2e:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    from e2e_harness import LiveServer

    server = LiveServer(str(tmp_path_factory.mktemp("e2e") / "e2e.db"))
    server.start()
    yield server
    server.stop()


@pytest.fixture(scope="session")
def base_url(live_server):
    return live_server.url


@pytest.fixture
def offline_page(page):
    """Playwright page that aborts and records any non-local request; fails the test if any."""
    blocked: list[str] = []

    def guard(route):
        url = route.request.url
        parsed = urlparse(url)
        if parsed.scheme in ("http", "https", "ws", "wss") and parsed.hostname not in LOCAL_HOSTS:
            blocked.append(url)
            route.abort()
        else:
            route.continue_()

    page.route("**/*", guard)
    yield page
    assert blocked == [], f"non-local requests made: {blocked}"
