"""Real-browser specs for the v3 shell, Library routes and Preview (stubbed Library API).

Static files are the real app; `/api/library*` is stubbed per contracts/api.md (ptstubs).
Every case runs through `offline_page`: any non-local request fails the test.
"""

import json
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


# ---- T054: save toggle on result rows ----


def triage_item(n, **kw):
    item = {
        "paper_id": f"2401.{n:05d}",
        "title": f"Result paper {n}",
        "authors": ["A. Author"],
        "source": "arxiv",
        "basis": "fulltext",
        "rank": 10 - n,
        "rank_reason": "Stub reason.",
        "summary": None,
        "critique": None,
        "status": "ok",
        "error": None,
        "abs_url": f"https://arxiv.org/abs/2401.{n:05d}",
        "pdf_url": f"https://arxiv.org/pdf/2401.{n:05d}",
        "saved": False,
    }
    item.update(kw)
    return item


def stub_triage(page, results, topic="diffusion models"):
    body = {
        "topic": topic,
        "results": results,
        "errors": [],
        "offset": 0,
        "next_offset": None,
        "has_more": False,
    }
    page.route(
        lambda url: url.endswith("/api/triage"),
        lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(body)
        ),
    )


def run_search(page, rows):
    page.fill("#query", "diffusion models")
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(rows, timeout=15_000)
    expect(page.locator("#submit")).to_be_enabled()


def save_btn(page, n):
    return page.locator(f'[id="paper-2401.{n:05d}"] button.save')


def test_save_button_states_and_failed_rows(app):
    page = app
    LibraryStub(page, [lib_item(2)])
    stub_triage(
        page,
        [
            triage_item(1),
            triage_item(2, saved=True),
            triage_item(3, status="failed", rank=0, error="Could not fetch."),
        ],
    )
    page.goto("/")
    run_search(page, 3)
    expect(save_btn(page, 1)).to_have_text("Save")
    expect(save_btn(page, 1)).to_have_attribute("aria-pressed", "false")
    expect(save_btn(page, 2)).to_have_text("Saved")
    expect(save_btn(page, 2)).to_have_attribute("aria-pressed", "true")
    expect(page.locator('[id="paper-2401.00003"] button.save')).to_have_count(0)
    # Button accessible description is the row title.
    title_id = page.locator('[id="paper-2401.00001"] .paper__title').get_attribute("id")
    assert save_btn(page, 1).get_attribute("aria-describedby") == title_id


def test_save_posts_topic_updates_count_and_announces(app):
    page = app
    stub = LibraryStub(page, [lib_item(9)])
    stub_triage(page, [triage_item(1), triage_item(2)])
    page.goto("/")
    expect(page.locator(".views__count")).to_have_text("1")
    run_search(page, 2)
    hold = []
    page.route(
        lambda url: url.endswith("/api/library"),
        lambda route: hold.append(route) if route.request.method == "POST" else route.fallback(),
    )
    save_btn(page, 1).click()
    expect(save_btn(page, 1)).to_have_text("Saving…")
    expect(save_btn(page, 1)).to_have_attribute("aria-disabled", "true")
    expect(save_btn(page, 1)).to_have_attribute("aria-busy", "true")
    hold[0].fallback()
    expect(save_btn(page, 1)).to_have_text("Saved")
    expect(save_btn(page, 1)).to_have_attribute("aria-pressed", "true")
    expect(page.locator(".views__count")).to_have_text("2")
    expect(page.locator("#status")).to_have_text("Saved to Library.")
    posts = stub.calls_to("POST", "/api/library")
    assert [c[3] for c in posts] == [{"paper_id": "2401.00001", "topic": "diffusion models"}]


def test_unsave_always_confirms_keep_and_escape(app):
    page = app
    stub = LibraryStub(page, [lib_item(1, highlight_count=3)])
    stub_triage(page, [triage_item(1, saved=True)])
    page.goto("/")
    run_search(page, 1)
    save_btn(page, 1).click()
    group = page.locator('[data-confirm="unsave"]')
    expect(group).to_be_visible()
    expect(group).to_have_attribute("role", "group")
    expect(group).to_have_attribute("aria-label", "Confirm removal")
    expect(group).to_contain_text(
        "Remove from Library? This deletes the saved PDF and 3 highlights with their notes."
    )
    expect(group.get_by_role("button", name="Keep")).to_be_focused()
    page.keyboard.press("Escape")
    expect(group).to_have_count(0)
    expect(save_btn(page, 1)).to_be_focused()
    expect(save_btn(page, 1)).to_have_text("Saved")
    save_btn(page, 1).click()
    page.get_by_role("button", name="Keep").click()
    expect(group).to_have_count(0)
    assert stub.calls_to("DELETE", "/api/library") == []


def test_unsave_remove_deletes_and_updates(app):
    page = app
    stub = LibraryStub(page, [lib_item(1), lib_item(8)])
    stub_triage(page, [triage_item(1, saved=True)])
    page.goto("/")
    run_search(page, 1)
    expect(page.locator(".views__count")).to_have_text("2")
    save_btn(page, 1).click()
    expect(page.locator('[data-confirm="unsave"]')).to_contain_text(
        "Remove from Library? This deletes the saved PDF."
    )
    expect(page.locator('[data-confirm="unsave"]')).not_to_contain_text("highlight")
    page.get_by_role("button", name="Remove", exact=True).click()
    expect(save_btn(page, 1)).to_have_text("Save")
    expect(save_btn(page, 1)).to_have_attribute("aria-pressed", "false")
    expect(save_btn(page, 1)).to_be_focused()
    expect(page.locator(".views__count")).to_have_text("1")
    expect(page.locator("#status")).to_have_text("Removed from Library.")
    deletes = stub.calls_to("DELETE", "/api/library")
    assert [c[2] for c in deletes] == [{"paper_id": "2401.00001"}]


def test_save_error_shows_row_alert_and_keeps_state(app):
    page = app
    stub = LibraryStub(page, [])
    stub_triage(page, [triage_item(1)])
    page.goto("/")
    run_search(page, 1)
    stub.fail[("POST", "/api/library")] = (500, "disk full")
    save_btn(page, 1).click()
    err = page.locator('[id="paper-2401.00001"] .row-error')
    expect(err).to_have_text("Could not save. disk full")
    expect(err).to_have_attribute("role", "alert")
    expect(save_btn(page, 1)).to_have_text("Save")
    # Next attempt clears the line.
    save_btn(page, 1).click()
    expect(save_btn(page, 1)).to_have_text("Saved")
    expect(err).to_have_count(0)


def test_unsave_error_keeps_saved_state(app):
    page = app
    stub = LibraryStub(page, [lib_item(1)])
    stub_triage(page, [triage_item(1, saved=True)])
    page.goto("/")
    run_search(page, 1)
    stub.fail[("DELETE", "/api/library")] = (500, "locked")
    save_btn(page, 1).click()
    page.get_by_role("button", name="Remove", exact=True).click()
    expect(page.locator('[id="paper-2401.00001"] .row-error')).to_have_text(
        "Could not remove from Library. locked"
    )
    expect(save_btn(page, 1)).to_have_text("Saved")
    expect(save_btn(page, 1)).to_have_attribute("aria-pressed", "true")


def test_saved_state_follows_library_after_view_switch(app):
    page = app
    stub = LibraryStub(page, [lib_item(1)])
    stub_triage(page, [triage_item(1, saved=True)])
    page.goto("/")
    run_search(page, 1)
    page.click('nav.views a[data-view="library"]')
    expect(page.locator("#library")).to_be_visible()
    stub.items.clear()  # removed elsewhere (e.g. the Library view)
    page.evaluate("PT.libraryRemove('2401.00001')")
    page.click('nav.views a[data-view="triage"]')
    expect(save_btn(page, 1)).to_have_text("Save")
