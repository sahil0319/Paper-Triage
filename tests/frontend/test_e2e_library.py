"""Real-browser specs for the v3 shell, Library routes and Preview (stubbed Library API).

Static files are the real app; `/api/library*` is stubbed per contracts/api.md (ptstubs).
Every case runs through `offline_page`: any non-local request fails the test.
"""

from urllib.parse import quote

import pytest
from playwright.sync_api import expect
from ptstubs import LibraryStub, lib_item

pytestmark = pytest.mark.e2e

TOPIC = "diffusion distillation"


@pytest.fixture
def app(offline_page, live_server):
    live_server.set_triage_delay(0)
    return offline_page


def _count_requests(page):
    seen = {"triage": 0, "papers": 0}

    def on_request(req):
        if req.url.endswith("/api/triage"):
            seen["triage"] += 1
        if "/api/papers" in req.url:
            seen["papers"] += 1

    page.on("request", on_request)
    return seen


def test_nav_has_view_links_and_library_count(app):
    page = app
    LibraryStub(page, [lib_item(n) for n in range(1, 4)])
    page.goto("/")
    nav = page.locator("nav.views")
    expect(nav.locator('a[data-view="triage"]')).to_have_attribute("aria-current", "page")
    expect(nav.locator('a[data-view="library"]')).not_to_have_attribute("aria-current", "page")
    expect(nav.locator(".views__count")).to_have_text("3")
    expect(page.locator("#library")).to_be_hidden()
    expect(page.locator("#preview")).to_be_hidden()
    expect(page).to_have_title("Paper Triage")


def test_library_count_hidden_when_empty(app):
    page = app
    LibraryStub(page, [])
    page.goto("/")
    expect(page.locator("nav.views a[data-view='library']")).to_be_visible()
    expect(page.locator(".views__count")).to_be_hidden()


def test_library_route_toggles_views_title_focus_and_announces(app):
    page = app
    LibraryStub(page, [lib_item(1)])
    page.goto("/")
    page.click('nav.views a[data-view="library"]')
    expect(page.locator("#library")).to_be_visible()
    expect(page.locator("#main")).to_be_hidden()
    expect(page.locator("#triage-intro")).to_be_hidden()
    expect(page.locator('nav.views a[data-view="library"]')).to_have_attribute(
        "aria-current", "page"
    )
    expect(page.locator('nav.views a[data-view="triage"]')).not_to_have_attribute(
        "aria-current", "page"
    )
    expect(page).to_have_title("Library · Paper Triage")
    expect(page.locator("#library-heading")).to_be_focused()
    expect(page.locator("#status")).to_contain_text("Library")
    # Mock badge stays in the nav in every view.
    expect(page.locator("#mock-label")).to_be_visible()
    page.click('nav.views a[data-view="triage"]')
    expect(page.locator("#main")).to_be_visible()
    expect(page.locator("#intro-heading")).to_be_focused()
    expect(page).to_have_title("Paper Triage")


def test_skip_links_follow_the_view(app):
    page = app
    LibraryStub(page, [])
    page.goto("/")
    expect(page.locator("a.skip:not([hidden])")).to_have_count(2)
    expect(page.locator("a.skip:not([hidden])").first).to_have_text("Skip to results")
    page.goto("/#/library")
    expect(page.locator("a.skip:not([hidden])")).to_have_count(1)
    expect(page.locator("a.skip:not([hidden])")).to_have_text("Skip to saved papers")
    # Activating a skip link moves focus and keeps the route.
    page.focus('a.skip[data-skip="library"]')
    page.keyboard.press("Enter")
    expect(page.locator("#library")).to_be_visible()
    assert page.evaluate("location.hash") == "#/library"


def test_back_forward_switch_views_without_refetching_triage(app):
    page = app
    LibraryStub(page, [lib_item(1)])
    seen = _count_requests(page)
    page.goto("/")
    page.fill("#query", TOPIC)
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(10, timeout=15_000)
    expect(page.locator("#submit")).to_be_enabled()
    before = dict(seen)
    assert before["triage"] == 1

    page.click('nav.views a[data-view="library"]')
    expect(page.locator("#library")).to_be_visible()
    page.go_back()
    expect(page.locator("#main")).to_be_visible()
    expect(page.locator("#library")).to_be_hidden()
    expect(page.locator("#paper-list li.paper")).to_have_count(10)
    expect(page.locator("#results-heading")).to_contain_text(TOPIC)
    page.go_forward()
    expect(page.locator("#library")).to_be_visible()
    page.go_back()
    expect(page.locator("#paper-list li.paper")).to_have_count(10)
    assert seen == before, f"triage data was re-fetched: {before} -> {seen}"


def test_cite_hash_does_not_switch_views(app):
    page = app
    LibraryStub(page, [])
    page.goto("/")
    page.fill("#query", "2401.00001")
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(1, timeout=15_000)
    page.evaluate("location.hash = '#paper-2401.00001'")
    page.wait_for_timeout(100)
    expect(page.locator("#main")).to_be_visible()
    expect(page.locator("#library")).to_be_hidden()


def _open_buttons(page):
    return page.locator("#library-list li.paper .open-preview")


def test_preview_back_restores_filters_scroll_and_focus(app):
    page = app
    items = [lib_item(n) for n in range(1, 41)]
    LibraryStub(page, items)
    hash_ = "#/library?dir=network&tags=diffusion%20models,video&q=attn"
    page.set_viewport_size({"width": 1100, "height": 700})
    page.goto("/" + hash_)
    expect(_open_buttons(page)).to_have_count(40)
    target = items[29]
    btn = page.locator(
        f'#library-list li.paper[data-paper-id="{target["paper_id"]}"] .open-preview'
    )
    btn.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    y_before = page.evaluate("window.scrollY")
    assert y_before > 300
    btn.click()
    expect(page.locator("#preview")).to_be_visible()
    expect(page.locator("#library")).to_be_hidden()
    assert page.evaluate("location.hash") == "#/library/paper/" + quote(target["paper_id"], safe="")
    expect(page).to_have_title(f"{target['title']} · Paper Triage")
    expect(page.locator("#preview-heading")).to_be_focused()

    page.click("#pv-back")
    expect(page.locator("#library")).to_be_visible()
    assert page.evaluate("location.hash") == hash_
    expect(btn).to_be_focused()
    assert abs(page.evaluate("window.scrollY") - y_before) < 40


def test_browser_back_from_preview_also_restores(app):
    page = app
    items = [lib_item(n) for n in range(1, 41)]
    LibraryStub(page, items)
    page.set_viewport_size({"width": 1100, "height": 700})
    page.goto("/#/library?q=saved")
    expect(_open_buttons(page)).to_have_count(40)
    btn = _open_buttons(page).nth(25)
    btn.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    y_before = page.evaluate("window.scrollY")
    btn.click()
    expect(page.locator("#preview")).to_be_visible()
    page.go_back()
    expect(page.locator("#library")).to_be_visible()
    assert page.evaluate("location.hash") == "#/library?q=saved"
    expect(btn).to_be_focused()
    assert abs(page.evaluate("window.scrollY") - y_before) < 40


def test_deep_link_to_preview_loads_the_library_first(app):
    page = app
    item = lib_item(7, paper_id="math.GT/0107001", title="Old style id paper")
    LibraryStub(page, [item])
    page.goto("/#/library/paper/" + quote("math.GT/0107001", safe=""))
    expect(page.locator("#preview")).to_be_visible()
    expect(page.locator("#preview-heading")).to_have_text("Old style id paper")
    expect(page).to_have_title("Old style id paper · Paper Triage")
