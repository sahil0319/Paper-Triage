"""Offline guard for the static UI: no external URLs, required element ids present."""

import re
from html.parser import HTMLParser
from pathlib import Path

STATIC = Path(__file__).resolve().parents[2] / "src" / "paper_triage" / "static"

# Hooks the UI tests and other lanes rely on. Later FE tasks extend this list.
REQUIRED_IDS = [
    "query",
    "submit",
    "paper-list",
    "question",
    "ask",
    "chat-scope",
    "results-count",
    "chat-log",
    "status",
    "alert",
    "working",
]


class _Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.urls = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids[a["id"]] = a
        for key in ("src", "href"):
            if a.get(key):
                self.urls.append((tag, key, a[key]))


def _html():
    p = _Collect()
    p.feed((STATIC / "index.html").read_text(encoding="utf-8"))
    return p


def test_files_exist():
    for name in ("index.html", "app.css", "app.js"):
        assert (STATIC / name).is_file(), name


def test_html_has_no_external_urls():
    for tag, key, url in _html().urls:
        assert not re.match(r"(?i)(https?:)?//", url), f"<{tag} {key}={url}> is external"


def test_css_has_no_external_resources():
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert "@import" not in css
    assert "@font-face" not in css
    assert not re.search(r"url\(\s*['\"]?\s*(https?:)?//", css, re.IGNORECASE)


def test_js_loads_nothing_external():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"""fetch\(\s*['"]\s*https?://""", js)
    assert not re.search(r"""import\s*\(|importScripts|XMLHttpRequest""", js)
    # Only same-origin API paths are fetched; link hosts (arxiv.org) are navigation, not loads.
    assert not re.search(r"""\.src\s*=\s*['"]https?://""", js)


def test_required_ids_present():
    ids = _html().ids
    missing = [i for i in REQUIRED_IDS if i not in ids]
    assert not missing, f"missing ids: {missing}"


def test_status_is_polite_live_region():
    a = _html().ids["status"]
    assert a.get("role") == "status"
    assert a.get("aria-live") == "polite"


def test_alert_has_role_alert():
    assert _html().ids["alert"].get("role") == "alert"



def test_working_indicator_contract():
    a = _html().ids["working"]
    assert a.get("role") == "group"
    assert a.get("aria-label") == "Triage in progress"
    assert "hidden" in a


def test_css_has_reduced_motion_rules():
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: reduce" in css
    assert "@keyframes ray" in css and "@keyframes breathe" in css
