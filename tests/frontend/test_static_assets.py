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
    "load-more",
    "library",
    "library-heading",
    "library-list",
    "preview",
    "preview-heading",
    "pv-back",
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


# ---- v3 (T052): scan every own file except static/vendor/, vendored pdf.js checks ----

VENDOR = STATIC / "vendor"
PDFJS = VENDOR / "pdfjs"
PDFJS_VERSION = "6.3.289"


def _own_files(*suffixes):
    return [
        p
        for p in sorted(STATIC.rglob("*"))
        if p.is_file() and VENDOR not in p.parents and p.suffix in suffixes
    ]


def test_own_scripts_load_nothing_external():
    scripts = _own_files(".js", ".mjs")
    assert scripts, "no own scripts found"
    for p in scripts:
        js = p.read_text(encoding="utf-8")
        assert not re.search(r"""importScripts|XMLHttpRequest""", js), p.name
        assert not re.search(r"""fetch\(\s*['"]\s*https?://""", js), p.name
        assert not re.search(r"""\.src\s*=\s*['"]https?://""", js), p.name
        # Static `import ... from "./x.mjs"` is allowed (viewer.js); dynamic import() is not.
        assert not re.search(r"""\bimport\s*\(""", js), f"{p.name} uses dynamic import()"
        for m in re.finditer(r"""\bimport\b[^;]*?\bfrom\s*['"]([^'"]+)['"]""", js):
            assert not re.match(r"(?i)(https?:)?//", m.group(1)), f"{p.name} imports {m.group(1)}"


def test_own_css_has_no_external_resources():
    for p in _own_files(".css"):
        css = p.read_text(encoding="utf-8")
        assert "@import" not in css, p.name
        assert "@font-face" not in css, p.name
        assert not re.search(r"url\(\s*['\"]?\s*(https?:)?//", css, re.IGNORECASE), p.name


def test_own_html_has_no_external_urls():
    for p in _own_files(".html"):
        c = _Collect()
        c.feed(p.read_text(encoding="utf-8"))
        for tag, key, url in c.urls:
            assert not re.match(r"(?i)(https?:)?//", url), f"{p.name}: <{tag} {key}={url}>"


def test_vendored_pdfjs_present():
    for name in ("pdf.min.mjs", "pdf.worker.min.mjs", "LICENSE", "VERSION"):
        f = PDFJS / name
        assert f.is_file() and f.stat().st_size > 0, f"vendor/pdfjs/{name} missing"


def test_vendored_pdfjs_version_pinned():
    version = (PDFJS / "VERSION").read_text(encoding="utf-8")
    assert f"pdfjs-dist {PDFJS_VERSION}" in version
    assert "modern" in version.lower() or "build/" in version
    assert "legacy" not in version.lower()
    for name in ("pdf.min.mjs", "pdf.worker.min.mjs"):
        head = (PDFJS / name).read_text(encoding="utf-8", errors="replace")
        assert PDFJS_VERSION in head, f"{name} does not contain {PDFJS_VERSION}"


def test_vendored_pdfjs_license_is_apache():
    assert "Apache License" in (PDFJS / "LICENSE").read_text(encoding="utf-8")


def test_nav_has_view_links_and_per_view_regions():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert '<nav class="views"' in html
    assert 'data-view="triage"' in html and 'data-view="library"' in html
    assert "views__count" in html
    for view in ("triage", "library", "preview"):
        assert f'data-route="{view}"' in html
        assert f'data-skip="{view}"' in html
    assert 'type="module" src="viewer.js"' in html
