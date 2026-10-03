"""Real-browser specs for the v3 shell, Library routes and Preview (stubbed Library API).

Static files are the real app; `/api/library*` is stubbed per contracts/api.md (ptstubs).
Every case runs through `offline_page`: any non-local request fails the test.
"""

import json
import os
import re
import time
from pathlib import Path
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
    items = [
        lib_item(n, title=f"Attn paper {n}", tags=["diffusion models", "video"], directory_id=1)
        for n in range(1, 41)
    ]
    stub = LibraryStub(page, items)
    stub.directories = [{"id": 1, "name": "network", "count": 40}]
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


# ---- T055: viewer shell (stubbed PDF = fixtures/sample.pdf) ----


def preview(page, items, hash_=None, **stub_kw):
    stub = LibraryStub(page, items, **stub_kw)
    page.add_init_script("window.__PT_POLL_MS = 300")
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("/" + (hash_ or "#/library/paper/" + quote(items[0]["paper_id"], safe="")))
    return stub


def page_width(page, n=1):
    return page.locator(f'.pdf-page[data-page="{n}"]').evaluate(
        "e => e.getBoundingClientRect().width"
    )


def test_viewer_renders_pages_text_layer_and_stays_local(app):
    page = app
    urls = []
    page.on("request", lambda r: urls.append(r.url))
    preview(page, [lib_item(1)])
    expect(page.locator("#preview-heading")).to_have_text("Saved paper 1: stubbed title")
    expect(page.locator(".pdf-page")).to_have_count(3)
    expect(page.locator("#pv-pages canvas").first).to_be_attached()
    expect(page.locator('.pdf-page[data-page="1"].is-drawn')).to_have_count(1, timeout=10_000)
    expect(page.locator('.pdf-page[data-page="1"] .textLayer')).to_contain_text("Distillation")
    expect(page.locator("#pv-pages")).to_have_attribute("role", "region")
    expect(page.locator("#pv-pages")).to_have_attribute("aria-label", "PDF pages")
    expect(page.locator('.pdf-page[data-page="2"]')).to_have_attribute("aria-label", "Page 2")
    expect(page.locator("#pv-page-of")).to_have_text("of 3")
    expect(page.locator("#pv-zoom")).to_have_value("fit-width")
    ext = page.locator("#pv-external")
    expect(ext).to_have_attribute("href", "/api/library/pdf?paper_id=2401.00001")
    expect(ext).to_have_attribute("target", "_blank")
    assert any(u.endswith("/vendor/pdfjs/pdf.worker.min.mjs") for u in urls)
    assert all(u.startswith(("http://127.0.0.1", "blob:", "data:")) for u in urls), urls


def test_viewer_page_navigation_clamps_and_tracks_scroll(app):
    page = app
    preview(page, [lib_item(1)])
    expect(page.locator(".pdf-page")).to_have_count(3)
    inp = page.locator("#pv-page-input")
    expect(inp).to_have_value("1")
    expect(page.locator("#pv-prev")).to_have_attribute("aria-disabled", "true")
    page.click("#pv-next")
    expect(inp).to_have_value("2")
    expect(page.locator("#pv-prev")).not_to_have_attribute("aria-disabled", "true")
    top2 = page.locator('.pdf-page[data-page="2"]').evaluate("e => e.getBoundingClientRect().top")
    well_top = page.locator("#pv-pages").evaluate("e => e.getBoundingClientRect().top")
    assert abs(top2 - well_top) < 40
    inp.fill("99")
    inp.press("Enter")
    expect(inp).to_have_value("3")
    expect(page.locator("#pv-next")).to_have_attribute("aria-disabled", "true")
    inp.fill("0")
    inp.press("Enter")
    expect(inp).to_have_value("1")
    # Scrolling by hand updates the page number.
    page.locator("#pv-pages").evaluate(
        "w => { w.scrollTop = w.querySelector('[data-page=\"3\"]').offsetTop }"
    )
    expect(inp).to_have_value("3")


def test_viewer_zoom_changes_page_width(app):
    page = app
    preview(page, [lib_item(1)])
    expect(page.locator('.pdf-page[data-page="1"].is-drawn')).to_have_count(1, timeout=10_000)
    fit = page_width(page)
    page.select_option("#pv-zoom", "50")
    page.wait_for_function(
        "document.querySelector('.pdf-page').getBoundingClientRect().width < 450"
    )
    assert abs(page_width(page) - 612 * 96 / 72 * 0.5) < 3
    page.select_option("#pv-zoom", "200")
    page.wait_for_function(
        "document.querySelector('.pdf-page').getBoundingClientRect().width > 1500"
    )
    page.click("#pv-zoom-out")
    expect(page.locator("#pv-zoom")).to_have_value("150")
    page.click("#pv-zoom-in")
    expect(page.locator("#pv-zoom")).to_have_value("200")
    expect(page.locator("#pv-zoom-in")).to_have_attribute("aria-disabled", "true")
    page.select_option("#pv-zoom", "fit-width")
    page.wait_for_function(
        f"Math.abs(document.querySelector('.pdf-page').getBoundingClientRect().width - {fit}) < 2"
    )
    page.select_option("#pv-zoom", "fit-page")
    page.wait_for_function(
        f"document.querySelector('.pdf-page').getBoundingClientRect().width < {fit} - 50"
    )


def test_viewer_keys_work_in_the_pages_region_only(app):
    page = app
    preview(page, [lib_item(1)])
    expect(page.locator(".pdf-page")).to_have_count(3)
    fit = page_width(page)
    # Not focused in the region: keys do nothing.
    page.locator("#pv-prev").focus()
    page.keyboard.press("+")
    page.keyboard.press("n")
    assert abs(page_width(page) - fit) < 2
    expect(page.locator("#pv-page-input")).to_have_value("1")
    page.locator("#pv-pages").focus()
    page.keyboard.press("+")
    page.wait_for_function(
        f"Math.abs(document.querySelector('.pdf-page').getBoundingClientRect().width - {fit}) > 2"
    )
    page.keyboard.press("0")
    expect(page.locator("#pv-zoom")).to_have_value("fit-width")
    page.keyboard.press("n")
    expect(page.locator("#pv-page-input")).to_have_value("2")
    page.keyboard.press("p")
    expect(page.locator("#pv-page-input")).to_have_value("1")
    page.keyboard.press("-")
    expect(page.locator("#pv-zoom")).not_to_have_value("fit-width")
    for sel, key in (
        ("#pv-zoom-in", "+"),
        ("#pv-zoom-out", "-"),
        ("#pv-next", "n"),
        ("#pv-prev", "p"),
    ):
        assert page.locator(sel).get_attribute("aria-keyshortcuts") == key


def test_viewer_downloading_state_polls_until_ready(app):
    page = app
    stub = preview(
        page,
        [
            lib_item(
                1,
                pdf={"status": "pending", "error": None, "pages": None},
                critique={
                    "basis": "fulltext",
                    "weak_claims": [],
                    "overclaims": [],
                    "missing_baselines": ["No teacher-free baseline"],
                },
            )
        ],
    )
    working = page.locator("#pv-stage .working")
    expect(working).to_contain_text("Downloading the PDF…")
    expect(working).to_contain_text("You can read the critique below while you wait.")
    expect(page.locator("#pv-stage .critique")).to_contain_text("No teacher-free baseline")
    expect(page.locator("#pv-pages")).to_be_hidden()
    stub.items[0]["pdf"] = {"status": "ready", "error": None, "pages": 3}
    expect(page.locator(".pdf-page")).to_have_count(3, timeout=10_000)
    expect(page.locator("#pv-stage .working")).to_have_count(0)
    expect(page.locator("#status")).to_have_text("PDF ready.")


def test_viewer_unavailable_state_retry(app):
    page = app
    stub = preview(
        page, [lib_item(1, pdf={"status": "failed", "error": "Not a PDF.", "pages": None})]
    )
    alert = page.locator("#pv-stage .alert")
    expect(alert).to_contain_text("This PDF could not be downloaded.")
    expect(alert).to_contain_text("Not a PDF.")
    expect(alert.get_by_role("link", name="Open the source page")).to_have_attribute(
        "href", "https://arxiv.org/abs/2401.00001"
    )
    expect(page.locator("#pv-controls")).to_be_hidden()
    alert.get_by_role("button", name="Try again").click()
    expect(page.locator("#pv-stage .working")).to_be_visible()
    assert [c[3] for c in stub.calls_to("POST", "/api/library/retry")] == [
        {"paper_id": "2401.00001"}
    ]
    stub.items[0]["pdf"] = {"status": "ready", "error": None, "pages": 3}
    expect(page.locator(".pdf-page")).to_have_count(3, timeout=10_000)


def test_viewer_render_failed_state(app):
    page = app
    preview(page, [lib_item(1)], pdf="garbage")
    alert = page.locator("#pv-stage .alert")
    expect(alert).to_contain_text("This PDF could not be displayed.", timeout=10_000)
    expect(alert).to_contain_text(
        "The file may be damaged or use features the viewer does not support."
    )
    expect(alert.get_by_role("link", name="Open PDF in new tab")).to_have_attribute(
        "href", "/api/library/pdf?paper_id=2401.00001"
    )


def test_viewer_not_saved_state(app):
    page = app
    preview(page, [lib_item(1)], hash_="#/library/paper/9999.99999")
    expect(page.locator("#pv-stage")).to_contain_text("This paper is not in your Library.")
    expect(page.locator("#pv-stage").get_by_role("link", name="Go to Library")).to_be_visible()
    expect(page.locator("#pv-controls")).to_be_hidden()
    expect(page.locator("#pv-pages")).to_be_hidden()


def test_open_from_library_then_back_closes_viewer(app):
    page = app
    stub = LibraryStub(page, [lib_item(1)])
    page.goto("/#/library")
    page.click(".open-preview")
    expect(page.locator(".pdf-page")).to_have_count(3)
    page.click("#pv-back")
    expect(page.locator("#library")).to_be_visible()
    expect(page.locator("#pv-pages .pdf-page")).to_have_count(0)
    page.click(".open-preview")
    expect(page.locator(".pdf-page")).to_have_count(3)
    assert len(stub.calls_to("GET", "/api/library/pdf")) >= 1


def test_real_api_save_then_open_preview_renders_pdf(app, live_server):
    """No stubs: save through the UI, open the Library item, see real pages (BE T047-T050)."""
    page = app
    page.goto("/")
    try:
        page.fill("#query", "2401.00001")
        page.click("#submit")
        expect(page.locator("#paper-list li.paper")).to_have_count(1, timeout=15_000)
        save_btn(page, 1).click()
        expect(save_btn(page, 1)).to_have_text("Saved", timeout=10_000)
        expect(page.locator(".views__count")).to_have_text("1")
        page.click('nav.views a[data-view="library"]')
        page.locator(".open-preview").first.click()
        expect(page.locator(".pdf-page")).to_have_count(3, timeout=20_000)
        expect(page.locator('.pdf-page[data-page="1"] .textLayer')).to_contain_text(
            "Distillation", timeout=10_000
        )
    finally:
        page.request.delete(f"{live_server.url}/api/library?paper_id=2401.00001")


# ---- T056: find in paper ----


def open_find(page):
    expect(page.locator(".pdf-page")).to_have_count(3)
    page.click("#pv-find-btn")
    expect(page.locator("#pv-find")).to_be_visible()
    expect(page.locator("#pv-find-input")).to_be_focused()


def find(page, text):
    page.fill("#pv-find-input", text)
    page.press("#pv-find-input", "Enter")


def test_find_lists_matches_and_jumps_with_outline(app):
    page = app
    preview(page, [lib_item(1)])
    btn = page.locator("#pv-find-btn")
    expect(btn).to_have_attribute("aria-label", "Find in paper")
    expect(btn).to_have_attribute("aria-keyshortcuts", "f")
    open_find(page)
    expect(page.locator("#pv-find-input")).to_have_attribute("placeholder", "Find text")
    find(page, "distillation")
    count = page.locator("#pv-find-count")
    expect(count).to_have_text(re.compile(r"^\d+ matches on 1 page$"))
    hits = page.locator("#pv-find-results .find-hit")
    assert hits.count() >= 2
    for i in range(hits.count()):
        assert hits.nth(i).inner_text().startswith("Page 1: ")
    expect(page.locator("#pv-find-results .find-match").first).to_have_text(
        re.compile("^distillation$", re.IGNORECASE)
    )
    expect(page.locator("#status")).to_contain_text("matches on 1 page")
    # A word that only appears on page 2.
    find(page, "Quartzite")
    expect(count).to_have_text(re.compile(r"^\d+ match(es)? on 1 page$"))
    hit = page.locator("#pv-find-results .find-hit").first
    assert hit.inner_text().startswith("Page 2: ")
    hit.click()
    expect(page.locator("#pv-page-input")).to_have_value("2")
    expect(page.locator('.pdf-page[data-page="2"]')).to_have_class(re.compile("is-flash"))
    top2 = page.locator('.pdf-page[data-page="2"]').evaluate("e => e.getBoundingClientRect().top")
    well_top = page.locator("#pv-pages").evaluate("e => e.getBoundingClientRect().top")
    assert abs(top2 - well_top) < 40
    find(page, "Obsidian")
    assert page.locator("#pv-find-results .find-hit").first.inner_text().startswith("Page 3: ")


def test_find_spans_pages_and_singular_copy(app):
    page = app
    preview(page, [lib_item(1)])
    open_find(page)
    find(page, "the")
    expect(page.locator("#pv-find-count")).to_have_text(re.compile(r"^\d+ matches on [23] pages$"))
    pages = {b.get_attribute("data-page") for b in page.locator("#pv-find-results .find-hit").all()}
    assert len(pages) >= 2


def test_find_no_matches(app):
    page = app
    preview(page, [lib_item(1)])
    open_find(page)
    find(page, "zzzxqjnonsense")
    expect(page.locator("#pv-find-count")).to_have_text("No matches.")
    expect(page.locator("#pv-find-results .find-hit")).to_have_count(0)
    expect(page.locator("#status")).to_have_text("No matches.")


def test_find_escape_closes_and_returns_focus(app):
    page = app
    preview(page, [lib_item(1)])
    open_find(page)
    find(page, "Quartzite")
    expect(page.locator("#pv-find-results .find-hit").first).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#pv-find")).to_be_hidden()
    expect(page.locator("#pv-find-btn")).to_be_focused()
    expect(page.locator("#pv-find-btn")).to_have_attribute("aria-expanded", "false")
    page.click("#pv-find-btn")
    page.click("#pv-find-close")
    expect(page.locator("#pv-find")).to_be_hidden()
    expect(page.locator("#pv-find-btn")).to_be_focused()


def test_find_key_f_opens_inside_pages_region_only(app):
    page = app
    preview(page, [lib_item(1)])
    expect(page.locator(".pdf-page")).to_have_count(3)
    page.locator("#pv-prev").focus()
    page.keyboard.press("f")
    expect(page.locator("#pv-find")).to_be_hidden()
    page.locator("#pv-pages").focus()
    page.keyboard.press("f")
    expect(page.locator("#pv-find")).to_be_visible()
    expect(page.locator("#pv-find-input")).to_be_focused()


def test_find_is_reset_when_the_preview_closes(app):
    page = app
    preview(page, [lib_item(1), lib_item(2)], hash_="#/library")
    page.locator(".open-preview").first.click()
    open_find(page)
    find(page, "Quartzite")
    expect(page.locator("#pv-find-results .find-hit").first).to_be_visible()
    page.click("#pv-back")
    page.locator(".open-preview").first.click()
    expect(page.locator(".pdf-page")).to_have_count(3)
    expect(page.locator("#pv-find")).to_be_hidden()
    expect(page.locator("#pv-find-input")).to_have_value("")


# ---- T060: Library list, filters, tags, states, polling ----


def rows(page):
    return page.locator("#library-list li.lib-row")


def row_ids(page):
    return rows(page).evaluate_all("els => els.map(e => e.dataset.paperId)")


def tag_chip(page, name):
    return page.locator(f'#lib-tags button.tag[data-tag="{name}"]')


def lib_page(app, items, hash_="#/library", **kw):
    stub = LibraryStub(app, items, **kw)
    app.add_init_script("window.__PT_POLL_MS = 300")
    app.set_viewport_size({"width": 1280, "height": 900})
    app.goto("/" + hash_)
    return stub


def tagged(n, tags, **kw):
    return lib_item(n, tags=tags, **kw)


def test_library_row_content(app):
    page = app
    lib_page(
        page,
        [
            lib_item(
                1,
                tags=["diffusion", "video"],
                topic="diffusion video",
                highlight_count=3,
                saved_at="2026-10-03T10:00:00+00:00",
                summary={"summary": "S.", "contributions": []},
                critique={
                    "basis": "fulltext",
                    "weak_claims": [],
                    "overclaims": [],
                    "missing_baselines": [],
                },
            )
        ],
    )
    li = rows(page).first
    expect(li).to_have_attribute("data-paper-id", "2401.00001")
    expect(li.locator(".paper__title")).to_have_text("Saved paper 1: stubbed title")
    expect(li.locator(".paper__authors").first).to_have_text("A. Author, B. Author")
    expect(li.locator(".lib-tagline")).to_have_text("Tags: diffusion, video")
    expect(li.locator(".rank__for")).to_have_text('for "diffusion video"')
    expect(li.locator(".lib-saved")).to_have_text("Saved 3 Oct")
    expect(li.locator("[data-pdf-status]")).to_have_text("PDF ready")
    expect(li.locator("[data-pdf-status]")).to_have_attribute("data-pdf-status", "ready")
    expect(li.locator(".lib-hl")).to_have_text("3 highlights")
    expect(li.locator('a[data-link="abs"]')).to_have_count(1)
    expect(li.locator("details.disclosure")).to_have_count(1)
    expect(li.locator("button.open-preview")).to_have_text("Open preview")
    expect(page.locator("#library-count")).to_have_text("1 of 1 saved paper")
    expect(page.locator("#library-heading")).to_have_text("Library")


def test_library_row_omits_tags_topic_and_zero_highlights(app):
    page = app
    lib_page(page, [lib_item(1, tags=[], topic="", highlight_count=0)])
    li = rows(page).first
    expect(li.locator(".lib-tagline")).to_have_count(0)
    expect(li.locator(".rank__for")).to_have_count(0)
    expect(li.locator(".lib-hl")).to_have_count(0)


def test_open_preview_button_opens_preview_route(app):
    page = app
    lib_page(page, [lib_item(1)])
    rows(page).first.locator("button.open-preview").click()
    assert page.evaluate("location.hash") == "#/library/paper/2401.00001"


def test_tag_filter_is_and_and_chips_sorted(app):
    page = app
    items = [
        tagged(1, ["diffusion", "video"]),
        tagged(2, ["diffusion", "video", "rag"]),
        tagged(3, ["diffusion"]),
        tagged(4, ["rag"]),
    ]
    lib_page(page, items)
    chips = page.locator("#lib-tags button.tag")
    assert [c.get_attribute("data-tag") for c in chips.all()] == ["diffusion", "rag", "video"]
    expect(tag_chip(page, "diffusion")).to_contain_text("3")
    expect(tag_chip(page, "diffusion")).to_have_attribute("aria-pressed", "false")
    tag_chip(page, "diffusion").click()
    assert row_ids(page) == ["2401.00001", "2401.00002", "2401.00003"]
    expect(tag_chip(page, "diffusion")).to_have_attribute("aria-pressed", "true")
    expect(tag_chip(page, "diffusion").locator("svg.tag__check")).to_have_count(1)
    tag_chip(page, "video").click()
    assert row_ids(page) == ["2401.00001", "2401.00002"]
    expect(page.locator("#lib-tags-summary")).to_have_text(
        "Showing papers tagged diffusion and video."
    )
    expect(page.locator("#library-count")).to_have_text("2 of 4 saved papers")
    assert page.evaluate("location.hash") == "#/library?tags=diffusion,video"
    tag_chip(page, "rag").click()
    assert row_ids(page) == ["2401.00002"]
    # Unpress: filter widens again.
    tag_chip(page, "rag").click()
    tag_chip(page, "video").click()
    assert row_ids(page) == ["2401.00001", "2401.00002", "2401.00003"]
    # Pressed chips sort first: video (2) now precedes rag (2) only because it is pressed.
    tag_chip(page, "diffusion").click()
    tag_chip(page, "video").click()
    chips = page.locator("#lib-tags button.tag")
    assert [c.get_attribute("data-tag") for c in chips.all()] == ["video", "diffusion", "rag"]


def test_title_filter_and_chip_text_rules(app):
    page = app
    items = [
        tagged(1, ["diffusion"], title="Quartz attention"),
        tagged(2, ["diffusion", "guidance"], title="Basalt steering"),
        tagged(3, ["guidance"], title="Marble sampling"),
    ]
    lib_page(page, items)
    flt = page.locator("#lib-filter")
    flt.fill("QUARTZ")
    expect(rows(page)).to_have_count(1)
    assert row_ids(page) == ["2401.00001"]
    assert page.evaluate("location.hash") == "#/library?q=QUARTZ"
    # Text narrows the chips too: only tags containing the text.
    flt.fill("guid")
    expect(page.locator("#lib-tags button.tag")).to_have_count(1)
    expect(tag_chip(page, "guidance")).to_be_visible()
    expect(rows(page)).to_have_count(0)
    # Selecting a chip clears the text and filters by the tag.
    tag_chip(page, "guidance").click()
    expect(flt).to_have_value("")
    assert row_ids(page) == ["2401.00002", "2401.00003"]
    # Title text and a tag combine with AND; selected chips never disappear.
    flt.fill("marble")
    expect(rows(page)).to_have_count(1)
    assert row_ids(page) == ["2401.00003"]
    expect(tag_chip(page, "guidance")).to_be_visible()
    expect(page.locator("#lib-tags button.tag")).to_have_count(1)


def test_clear_filters_and_escape(app):
    page = app
    lib_page(page, [tagged(1, ["a1"]), tagged(2, ["b2"])], hash_="#/library?tags=a1&q=saved")
    expect(page.locator("#lib-filter")).to_have_value("saved")
    expect(tag_chip(page, "a1")).to_have_attribute("aria-pressed", "true")
    assert row_ids(page) == ["2401.00001"]
    clear = page.locator("#lib-clear")
    expect(clear).to_be_visible()
    clear.click()
    assert row_ids(page) == ["2401.00001", "2401.00002"]
    expect(page.locator("#lib-filter")).to_be_focused()
    expect(clear).to_be_hidden()
    expect(page.locator("#status")).to_have_text("Filters cleared. 2 saved papers.")
    assert page.evaluate("location.hash") == "#/library"
    page.locator("#lib-filter").fill("paper 2")
    expect(rows(page)).to_have_count(1)
    assert row_ids(page) == ["2401.00002"]
    page.locator("#lib-filter").press("Escape")
    expect(page.locator("#lib-filter")).to_have_value("")
    assert row_ids(page) == ["2401.00001", "2401.00002"]


def test_slash_focuses_filter_in_library(app):
    page = app
    lib_page(page, [lib_item(1)])
    expect(rows(page)).to_have_count(1)
    page.locator("#library-heading").focus()
    page.keyboard.press("/")
    expect(page.locator("#lib-filter")).to_be_focused()


def test_no_matches_state_offers_clear(app):
    page = app
    lib_page(page, [lib_item(1)], hash_="#/library?q=zzzz")
    expect(page.locator("#library-empty .empty__title")).to_have_text("No saved papers match.")
    expect(page.locator("#library-empty .empty__body")).to_have_text(
        "Try fewer tags or a shorter filter."
    )
    expect(rows(page)).to_have_count(0)
    page.locator("#library-empty").get_by_role("button", name="Clear filters").click()
    expect(rows(page)).to_have_count(1)


def test_tag_bar_overflow_show_all_and_no_tags_note(app):
    page = app
    many = [f"topicword{n:02d}" for n in range(30)]
    lib_page(page, [tagged(1, many)])
    more = page.locator("#lib-tags-more")
    expect(more).to_have_text("Show all 30 tags")
    expect(more).to_have_attribute("aria-expanded", "false")
    tags_h = page.locator("#lib-tags").evaluate("e => e.clientHeight")
    assert tags_h <= 80
    more.click()
    expect(more).to_have_text("Show fewer tags")
    expect(more).to_have_attribute("aria-expanded", "true")
    assert page.locator("#lib-tags").evaluate("e => e.clientHeight") > tags_h
    more.click()
    expect(more).to_have_text("Show all 30 tags")


def test_no_tags_note(app):
    page = app
    lib_page(page, [tagged(1, [])])
    expect(page.locator("#lib-tags-none")).to_have_text(
        "No tags yet. Tags are the search keywords that found each paper."
    )
    expect(page.locator("#lib-tags")).to_be_hidden()


def test_library_states_empty_error_loading(app):
    page = app
    LibraryStub(page, [])
    page.goto("/#/library")
    expect(page.locator("#library-empty-all .empty__title")).to_have_text("Nothing saved yet.")
    expect(page.locator("#library-empty-all")).to_contain_text("Each saved paper keeps its rank")
    page.locator("#library-empty-all").get_by_role("link", name="Go to Triage").click()
    expect(page.locator("#main")).to_be_visible()


def test_library_load_error_then_try_again(app):
    page = app
    stub = LibraryStub(page, [lib_item(1)])
    stub.fail[("GET", "/api/library")] = (500, "db locked")
    page.goto("/#/library")
    expect(page.locator("#library-alert")).to_contain_text("Could not load your library.")
    expect(page.locator("#library-alert")).to_contain_text("db locked")
    expect(page.locator("#library-list")).to_be_hidden()
    page.locator("#library-alert").get_by_role("button", name="Try again").click()
    expect(rows(page)).to_have_count(1)
    expect(page.locator("#library-alert")).to_be_hidden()


def test_library_loading_caption_after_delay(app):
    page = app
    held = []
    LibraryStub(page, [lib_item(1)])
    page.route(
        lambda url: url.endswith("/api/library"),
        lambda route: held.append(route) if not held else route.fallback(),
    )
    page.goto("/#/library")
    expect(page.locator("#library-loading")).to_have_text("Loading your library…")
    held[0].fallback()
    expect(rows(page)).to_have_count(1)
    expect(page.locator("#library-loading")).to_be_hidden()


def test_status_polls_until_ready_then_stops(app):
    page = app
    stub = lib_page(page, [lib_item(1, pdf={"status": "pending", "error": None, "pages": None})])
    li = rows(page).first
    expect(li.locator("[data-pdf-status]")).to_have_text("Downloading PDF…")
    expect(li.locator("[data-pdf-status]")).to_have_attribute("data-pdf-status", "pending")
    stub.items[0]["pdf"] = {"status": "ready", "error": None, "pages": 3}
    expect(li.locator("[data-pdf-status]")).to_have_text("PDF ready", timeout=5_000)
    n = len(stub.calls_to("GET", "/api/library"))
    page.wait_for_timeout(1000)
    assert len(stub.calls_to("GET", "/api/library")) == n, "polling did not stop"


def test_no_polling_when_nothing_pending(app):
    page = app
    stub = lib_page(page, [lib_item(1), lib_item(2)])
    expect(rows(page)).to_have_count(2)
    n = len(stub.calls_to("GET", "/api/library"))
    page.wait_for_timeout(1000)
    assert len(stub.calls_to("GET", "/api/library")) == n


def test_failed_status_try_again_posts_retry(app):
    page = app
    stub = lib_page(
        page, [lib_item(1, pdf={"status": "failed", "error": "Not a PDF.", "pages": None})]
    )
    li = rows(page).first
    expect(li.locator("[data-pdf-status]")).to_contain_text("PDF unavailable")
    li.get_by_role("button", name="Try again").click()
    expect(li.locator("[data-pdf-status]")).to_have_attribute("data-pdf-status", "pending")
    assert [c[3] for c in stub.calls_to("POST", "/api/library/retry")] == [
        {"paper_id": "2401.00001"}
    ]
    stub.items[0]["pdf"] = {"status": "ready", "error": None, "pages": 3}
    expect(li.locator("[data-pdf-status]")).to_have_text("PDF ready", timeout=5_000)


# Real harness (BE T047-T050): tags from topics, filters give exact rows, status reaches ready.


@pytest.fixture
def real_library(app, live_server):
    api = app.request

    def wipe():
        data = api.get(f"{live_server.url}/api/library").json()
        for p in data["papers"]:
            api.delete(f"{live_server.url}/api/library?paper_id={p['paper_id']}")
        for d in data["directories"]:
            api.delete(f"{live_server.url}/api/directories/{d['id']}")

    wipe()
    yield live_server.url
    wipe()


def _triage(page, base, query):
    r = page.request.post(f"{base}/api/triage", data={"query": query})
    assert r.ok, r.text()
    return r.json()["topic"]


def _save(page, base, topic, paper_id):
    s = page.request.post(f"{base}/api/library", data={"paper_id": paper_id, "topic": topic})
    assert s.ok, s.text()


def test_real_tag_and_title_filters_give_exact_rows(app, real_library):
    page, base = app, real_library
    # Triage first: a later topic search that returns a saved paper merges its tags into it.
    t1 = _triage(page, base, "diffusion distillation")
    t2 = _triage(page, base, "diffusion guidance")
    _save(page, base, t1, "2401.00001")
    _save(page, base, t1, "2401.00002")
    _save(page, base, t2, "2401.00003")
    page.goto("/#/library")
    expect(rows(page)).to_have_count(3)
    assert sorted(row_ids(page)) == ["2401.00001", "2401.00002", "2401.00003"]
    expect(page.locator("#lib-tags button.tag").first).to_have_attribute("data-tag", "diffusion")
    tag_chip(page, "distillation").click()
    assert sorted(row_ids(page)) == ["2401.00001", "2401.00002"]
    tag_chip(page, "guidance").click()
    expect(page.locator("#library-empty .empty__title")).to_have_text("No saved papers match.")
    tag_chip(page, "guidance").click()
    tag_chip(page, "distillation").click()
    tag_chip(page, "guidance").click()
    assert row_ids(page) == ["2401.00003"]
    page.locator("#lib-clear").click()
    title = rows(page).nth(0).locator(".paper__title").inner_text()
    word = next(w for w in re.findall(r"[A-Za-z]{6,}", title))
    expected = [
        i
        for i, t in zip(
            row_ids(page),
            rows(page).evaluate_all(
                "els => els.map(e => e.querySelector('.paper__title').textContent)"
            ),
        )
        if word.lower() in t.lower()
    ]
    page.locator("#lib-filter").fill(word)
    expect(rows(page)).to_have_count(len(expected))
    assert row_ids(page) == expected


def test_real_status_reaches_pdf_ready(app, real_library):
    page, base = app, real_library
    _save(page, base, _triage(page, base, "diffusion distillation"), "2401.00001")
    page.goto("/#/library")
    expect(rows(page).first.locator("[data-pdf-status]")).to_have_text("PDF ready", timeout=5_000)


def test_real_unavailable_pdf_offers_retry(app, real_library):
    page, base = app, real_library
    _save(page, base, _triage(page, base, "2401.00005"), "2401.00005")
    page.goto("/#/library")
    st = rows(page).first.locator("[data-pdf-status]")
    expect(st).to_contain_text("PDF unavailable", timeout=5_000)
    rows(page).first.get_by_role("button", name="Try again").click()
    expect(st).to_contain_text("PDF unavailable", timeout=5_000)


# ---- T061: directories and row actions (real harness) ----


def dir_item(page, name):
    return page.locator(f'#dir-list button.rail__item[data-dir="{name}"]')


def two_saved(page, base):
    topic = _triage(page, base, "diffusion distillation")
    _save(page, base, topic, "2401.00001")
    _save(page, base, topic, "2401.00002")


def make_dir(page, name):
    page.click("#dir-new")
    page.fill("#dir-new-slot input", name)
    page.press("#dir-new-slot input", "Enter")
    expect(dir_item(page, name)).to_have_attribute("aria-current", "true")


def test_rail_lists_all_unsorted_and_counts(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    expect(rows(page)).to_have_count(2)
    expect(page.locator("#dir-rail")).to_be_visible()
    items = page.locator("#dir-list button.rail__item")
    assert [i.get_attribute("data-dir") for i in items.all()] == ["", "Unsorted"]
    expect(items.nth(0)).to_contain_text("All saved")
    expect(items.nth(0)).to_contain_text("2")
    expect(items.nth(0)).to_have_attribute("aria-current", "true")
    expect(items.nth(1)).to_contain_text("Unsorted")
    expect(page.locator("#dir-new")).to_have_text("New directory")
    expect(page.locator("#dir-rail h2.rail__label")).to_have_text("Directories")
    items.nth(1).click()
    expect(items.nth(1)).to_have_attribute("aria-current", "true")
    assert page.evaluate("location.hash") == "#/library?dir=Unsorted"
    expect(page.locator("#library-count")).to_have_text("2 of 2 saved papers · Unsorted")


def test_create_directory_validation_and_select(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    expect(rows(page)).to_have_count(2)
    page.click("#dir-new")
    inp = page.locator("#dir-new-slot input")
    expect(inp).to_be_focused()
    expect(inp).to_have_attribute("placeholder", "e.g. final year thesis")
    expect(inp).to_have_attribute("maxlength", "40")
    inp.press("Enter")
    err = page.locator("#dir-new-slot .field-error")
    expect(err).to_have_text("Enter a name.")
    expect(inp).to_have_attribute("aria-invalid", "true")
    inp.fill("Unsorted")
    inp.press("Enter")
    expect(err).to_have_text('"Unsorted" already exists.')
    inp.fill("network")
    inp.press("Enter")
    expect(dir_item(page, "network")).to_have_attribute("aria-current", "true")
    expect(page.locator("#library-heading")).to_have_text("network")
    expect(page.locator("#status")).to_have_text('Directory "network" created.')
    assert page.evaluate("location.hash") == "#/library?dir=network"
    expect(page.locator("#library-empty .empty__title")).to_have_text("No papers in network.")
    expect(page.locator("#library-empty .empty__body")).to_have_text(
        "Move a saved paper here with its Directory menu."
    )
    # Duplicate, case-insensitive (server rule).
    page.click("#dir-new")
    inp = page.locator("#dir-new-slot input")
    inp.fill("NETWORK")
    inp.press("Enter")
    expect(page.locator("#dir-new-slot .field-error")).to_have_text('"NETWORK" already exists.')
    # Escape cancels and returns focus.
    inp.press("Escape")
    expect(page.locator("#dir-new")).to_be_focused()
    expect(page.locator("#dir-new-slot form")).to_have_count(0)


def test_move_paper_between_directories_with_collapse(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    expect(rows(page)).to_have_count(2)
    make_dir(page, "network")
    page.click('#dir-list button[data-dir=""]')
    expect(rows(page)).to_have_count(2)
    sel = rows(page).first.locator('select[data-act="move"]')
    first_id = row_ids(page)[0]
    sel.select_option(label="network")
    expect(page.locator("#status")).to_have_text("Moved to network.")
    expect(rows(page)).to_have_count(2)  # still in All saved
    expect(dir_item(page, "network")).to_contain_text("1")
    expect(dir_item(page, "Unsorted")).to_contain_text("1")
    # In network: moving back to Unsorted collapses the row out.
    dir_item(page, "network").click()
    expect(rows(page)).to_have_count(1)
    assert row_ids(page) == [first_id]
    rows(page).first.locator('select[data-act="move"]').select_option(label="Unsorted")
    expect(rows(page)).to_have_count(0)
    expect(page.locator("#status")).to_have_text("Moved to Unsorted.")
    expect(page.locator("#library-empty .empty__title")).to_have_text("No papers in network.")
    expect(page.locator("#library-heading")).to_be_focused()
    data = page.request.get(f"{base}/api/library").json()
    assert all(p["directory_id"] is None for p in data["papers"])


def test_move_error_reverts_select(app):
    page = app
    stub = lib_page(page, [lib_item(1)])
    stub.directories = [{"id": 1, "name": "network", "count": 0}]
    page.reload()
    sel = rows(page).first.locator('select[data-act="move"]')
    stub.fail[("POST", "/api/library/move")] = (404, "unknown directory")
    sel.select_option(label="network")
    expect(rows(page).first.locator(".row-error")).to_have_text("Could not move. unknown directory")
    expect(sel).to_have_value("")
    expect(sel).to_be_enabled()


def test_rename_directory(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    make_dir(page, "network")
    make_dir(page, "vision")
    expect(page.locator("#dir-actions")).to_be_visible()
    page.click('#dir-actions [data-act="rename"]')
    inp = page.locator("#dir-rename-slot input")
    expect(inp).to_be_focused()
    expect(inp).to_have_value("vision")
    expect(page.locator("#library-heading")).to_be_hidden()
    inp.fill("network")
    inp.press("Enter")
    expect(page.locator("#dir-rename-slot .field-error")).to_have_text('"network" already exists.')
    inp.fill("computer vision")
    page.click("#dir-rename-slot button[type=submit]")
    expect(page.locator("#library-heading")).to_have_text("computer vision")
    assert page.evaluate("location.hash") == "#/library?dir=computer%20vision"
    expect(dir_item(page, "computer vision")).to_have_attribute("aria-current", "true")
    expect(dir_item(page, "vision")).to_have_count(0)
    # Escape cancels.
    page.click('#dir-actions [data-act="rename"]')
    page.locator("#dir-rename-slot input").press("Escape")
    expect(page.locator("#library-heading")).to_be_visible()
    expect(page.locator('#dir-actions [data-act="rename"]')).to_be_focused()


def test_all_saved_and_unsorted_have_no_rename_or_delete(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    expect(rows(page)).to_have_count(2)
    expect(page.locator("#dir-actions")).to_be_hidden()
    dir_item(page, "Unsorted").click()
    expect(page.locator("#dir-actions")).to_be_hidden()


def test_delete_directory_moves_papers_to_unsorted(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    make_dir(page, "network")
    page.click('#dir-list button[data-dir=""]')
    for i in range(2):
        rows(page).nth(i).locator('select[data-act="move"]').select_option(label="network")
        expect(page.locator("#status")).to_have_text("Moved to network.")
        page.evaluate("document.getElementById('status').textContent = ''")
    dir_item(page, "network").click()
    expect(rows(page)).to_have_count(2)
    page.click('#dir-actions [data-act="delete"]')
    group = page.locator("#dir-confirm [role=group]")
    expect(group).to_contain_text('Delete "network"? Its 2 papers move to Unsorted.')
    expect(group.get_by_role("button", name="Keep")).to_be_focused()
    page.keyboard.press("Escape")
    expect(group).to_have_count(0)
    expect(page.locator('#dir-actions [data-act="delete"]')).to_be_focused()
    page.click('#dir-actions [data-act="delete"]')
    group.get_by_role("button", name="Delete", exact=True).click()
    expect(dir_item(page, "Unsorted")).to_have_attribute("aria-current", "true")
    expect(page.locator("#status")).to_have_text("Directory deleted. 2 papers moved to Unsorted.")
    expect(rows(page)).to_have_count(2)
    expect(dir_item(page, "network")).to_have_count(0)
    data = page.request.get(f"{base}/api/library").json()
    assert data["total"] == 2 and data["directories"] == [] and data["unsorted_count"] == 2


def test_remove_from_library_always_confirms(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.goto("/#/library")
    expect(rows(page)).to_have_count(2)
    expect(page.locator(".views__count")).to_have_text("2")
    gone = row_ids(page)[0]
    keep_id = row_ids(page)[1]
    rows(page).first.get_by_role("button", name="Remove from Library").click()
    group = rows(page).first.locator("[data-confirm=unsave]")
    expect(group).to_contain_text("Remove from Library? This deletes the saved PDF.")
    expect(group.get_by_role("button", name="Keep")).to_be_focused()
    page.keyboard.press("Escape")
    expect(group).to_have_count(0)
    expect(rows(page).first.get_by_role("button", name="Remove from Library")).to_be_focused()
    assert [c for c in page.request.get(f"{base}/api/library").json()["papers"]]
    rows(page).first.get_by_role("button", name="Remove from Library").click()
    rows(page).first.get_by_role("button", name="Remove", exact=True).click()
    expect(rows(page)).to_have_count(1)
    assert row_ids(page) == [keep_id]
    expect(page.locator("#status")).to_have_text("Removed from Library.")
    expect(page.locator(".views__count")).to_have_text("1")
    expect(rows(page).first.locator(".open-preview")).to_be_focused()
    ids = [p["paper_id"] for p in page.request.get(f"{base}/api/library").json()["papers"]]
    assert gone not in ids


def test_small_screen_uses_select_and_manage_panel(app, real_library):
    page, base = app, real_library
    two_saved(page, base)
    page.set_viewport_size({"width": 800, "height": 900})
    page.goto("/#/library")
    expect(rows(page)).to_have_count(2)
    expect(page.locator("#dir-rail")).to_be_hidden()
    sel = page.locator("#dir-select")
    expect(sel).to_be_visible()
    expect(page.locator("label[for=dir-select]")).to_have_text("Directory")
    assert [o.inner_text() for o in sel.locator("option").all()] == [
        "All saved (2)",
        "Unsorted (2)",
    ]
    manage = page.locator("#dir-manage")
    expect(manage).to_have_attribute("aria-expanded", "false")
    manage.click()
    expect(manage).to_have_attribute("aria-expanded", "true")
    expect(page.locator("#dir-manage-panel")).to_be_visible()
    page.click("#dir-manage-panel .dir-new")
    inp = page.locator("#dir-new-slot-m input")
    inp.fill("network")
    inp.press("Enter")
    expect(page.locator("#library-heading")).to_have_text("network")
    expect(sel).to_have_value("network")
    # Per-item rename and delete live in the panel.
    expect(page.locator("#dir-manage-list .dir-manage__item")).to_have_count(1)
    page.get_by_role("button", name="Delete directory network").click()
    expect(page.locator("#dir-manage-list [role=group]")).to_contain_text('Delete "network"?')
    page.locator("#dir-manage-list").get_by_role("button", name="Delete", exact=True).click()
    expect(page.locator("#status")).to_contain_text("Directory deleted.")
    expect(sel).to_have_value("Unsorted")
    sel.select_option("")
    expect(rows(page)).to_have_count(2)


# ---- F-009 / F-011 regressions ----


def test_viewer_retry_that_fails_again_ends_in_unavailable_not_stuck(app):
    page = app
    failed = {"status": "failed", "error": "Not a PDF.", "pages": None}
    stub = preview(page, [lib_item(1, pdf=dict(failed))])
    stub.after_retry = dict(failed)
    alert = page.locator("#pv-stage .alert")
    expect(alert).to_contain_text("This PDF could not be downloaded.")
    alert.get_by_role("button", name="Try again").click()
    expect(page.locator("#pv-stage .working")).to_be_visible()
    # The server already failed again: the next poll must replace "Downloading" with the failure.
    expect(page.locator("#pv-stage .alert")).to_contain_text(
        "This PDF could not be downloaded.", timeout=5_000
    )
    expect(page.locator("#pv-stage .working")).to_have_count(0)
    # And a second retry that succeeds renders the pages.
    stub.after_retry = {"status": "ready", "error": None, "pages": 3}
    page.locator("#pv-stage .alert").get_by_role("button", name="Try again").click()
    expect(page.locator(".pdf-page")).to_have_count(3, timeout=10_000)


def test_library_retry_that_fails_again_ends_in_unavailable(app):
    page = app
    failed = {"status": "failed", "error": "Not a PDF.", "pages": None}
    stub = lib_page(page, [lib_item(1, pdf=dict(failed))])
    stub.after_retry = dict(failed)
    li = rows(page).first
    li.get_by_role("button", name="Try again").click()
    expect(li.locator("[data-pdf-status]")).to_have_attribute("data-pdf-status", "pending")
    expect(li.locator("[data-pdf-status]")).to_have_attribute(
        "data-pdf-status", "failed", timeout=5_000
    )
    expect(li.get_by_role("button", name="Try again")).to_be_visible()


def test_find_result_moves_focus_to_the_viewer_region(app):
    page = app
    preview(page, [lib_item(1)])
    open_find(page)
    find(page, "Quartzite")
    page.locator("#pv-find-results .find-hit").first.click()
    expect(page.locator("#pv-pages")).to_be_focused()


# ---- T062: highlights, notes, panel list, export ----


def hl_preview(page, items=None, hash_=None, **kw):
    page.add_init_script("window.__PT_UNDO_MS = 800")
    stub = preview(page, items or [lib_item(1)], hash_=hash_, **kw)
    expect(page.locator(".pdf-page")).to_have_count(3)
    expect(page.locator('.pdf-page[data-page="1"].has-text')).to_have_count(1, timeout=10_000)
    expect(page.locator("#pv-panel")).to_be_visible()
    return stub


def line(page, text, n=1):
    return page.locator(f'.pdf-page[data-page="{n}"] .textLayer span', has_text=text).first


def drag_select(page, text, n=1):
    box = line(page, text, n).bounding_box()
    y = box["y"] + box["height"] / 2
    page.mouse.move(box["x"] + 2, y)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] - 2, y, steps=8)
    page.mouse.up()


def hls(page, n=1):
    return page.locator(f'.pdf-page[data-page="{n}"] .hl')


def items(page):
    return page.locator("#pv-hl-list li.hl-item[data-annotation-id]")


def test_highlight_via_toolbar_draws_lists_and_saves_fractions(app):
    page = app
    stub = hl_preview(page)
    btn = page.locator("#pv-hl-btn")
    expect(btn).to_have_attribute("aria-disabled", "true")
    expect(page.locator("#pv-hl-empty .pv-empty__title")).to_have_text("No highlights yet.")
    line(page, "Abstract").select_text()
    expect(btn).not_to_have_attribute("aria-disabled", "true")
    btn.click()
    expect(hls(page).first).to_be_attached()
    expect(hls(page).first).to_have_class(re.compile("hl--yellow"))
    expect(items(page)).to_have_count(1)
    expect(page.locator("#pv-hl-count")).to_have_text("1")
    expect(page.locator("#pv-tab-hl")).to_contain_text("Highlights")
    expect(page.locator("#status")).to_have_text("Yellow highlight added on page 1.")
    expect(items(page).first.locator(".hl-item__kind")).to_have_text("Yellow")
    expect(items(page).first.locator(".hl-item__page")).to_have_text("Page 1")
    assert "Abstract" in items(page).first.locator(".hl-item__quote").inner_text()
    ann = stub.annotations[0]
    assert ann["kind"] == "highlight" and ann["color"] == "yellow" and ann["page"] == 1
    assert 1 <= len(ann["rects"]) <= 50
    for x, y, w, h in ann["rects"]:
        assert 0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1
        assert x + w <= 1.0001 and y + h <= 1.0001
    assert "Abstract" in ann["quote"]
    # Selection is cleared and the button is disabled again.
    expect(btn).to_have_attribute("aria-disabled", "true")


def test_selection_popover_swatches_colors_and_last_used(app):
    page = app
    stub = hl_preview(page)
    drag_select(page, "Abstract")
    pop = page.locator("#pv-popover")
    expect(pop).to_be_visible()
    swatches = pop.locator("button.swatch")
    assert [s.get_attribute("aria-label") for s in swatches.all()] == [
        "Highlight yellow",
        "Highlight mint",
        "Highlight peach",
    ]
    expect(pop.get_by_role("button", name="Add note")).to_be_visible()
    box = swatches.first.bounding_box()
    assert abs(box["width"] - 32) < 1 and abs(box["height"] - 32) < 1
    swatches.nth(1).click()
    expect(pop).to_be_hidden()
    expect(hls(page).first).to_have_class(re.compile("hl--mint"))
    assert stub.annotations[0]["color"] == "mint"
    expect(page.locator("#status")).to_have_text("Mint highlight added on page 1.")
    expect(page.locator("#pv-hl-color")).to_have_value("mint")
    # The last-used color carries the ring and is what the toolbar button applies.
    drag_select(page, "Our method")
    expect(page.locator("#pv-popover button.swatch.is-last")).to_have_attribute(
        "aria-label", "Highlight mint"
    )
    page.keyboard.press("Escape")
    expect(pop).to_be_hidden()
    expect(page.locator("#pv-pages")).to_be_focused()


def test_popover_add_note_opens_editor_in_panel(app):
    page = app
    stub = hl_preview(page)
    drag_select(page, "Abstract")
    page.locator("#pv-popover").get_by_role("button", name="Add note").click()
    ta = page.locator("#pv-hl-list textarea")
    expect(ta).to_be_focused()
    ta.fill("check this claim")
    ta.press("Control+Enter")
    expect(items(page).first.locator(".hl-item__note")).to_have_text("check this claim")
    assert stub.annotations[0]["note"] == "check this claim"
    expect(items(page).first.get_by_role("button", name="Edit note")).to_be_focused()


def test_note_editor_counter_max_cancel_and_empty_removes_note(app):
    page = app
    stub = hl_preview(page)
    line(page, "Abstract").select_text()
    page.click("#pv-hl-btn")
    expect(items(page)).to_have_count(1)
    it = items(page).first
    it.get_by_role("button", name="Add note").first.click()
    ta = it.locator("textarea")
    expect(it.locator("label")).to_contain_text("Note")
    expect(ta).to_have_attribute("maxlength", "500")
    expect(ta).to_have_attribute("rows", "3")
    counter = it.locator(".note-counter")
    ta.fill("x" * 399)
    expect(counter).to_be_hidden()
    ta.fill("x" * 420)
    expect(counter).to_have_text("420/500")
    ta.fill("y" * 600)
    expect(counter).to_have_text("500/500")
    expect(counter).to_have_class(re.compile("is-max"))
    ta.press("Escape")
    expect(it.locator("textarea")).to_have_count(0)
    assert stub.annotations[0]["note"] == ""
    it.get_by_role("button", name="Add note").first.click()
    it.locator("textarea").fill("short note")
    it.get_by_role("button", name="Save note").click()
    assert stub.annotations[0]["note"] == "short note"
    # Empty save deletes the note, not the highlight.
    it.get_by_role("button", name="Edit note").click()
    it.locator("textarea").fill("   ")
    it.locator("textarea").press("Control+Enter")
    expect(it.locator(".hl-item__note")).to_have_count(0)
    assert stub.annotations[0]["note"] == "" and len(stub.annotations) == 1
    expect(hls(page).first).to_be_attached()


def test_change_color_updates_page_and_api(app):
    page = app
    stub = hl_preview(page)
    line(page, "Abstract").select_text()
    page.click("#pv-hl-btn")
    sel = items(page).first.locator('select[data-act="color"]')
    expect(sel).to_have_value("yellow")
    sel.select_option("peach")
    expect(hls(page).first).to_have_class(re.compile("hl--peach"))
    assert stub.annotations[0]["color"] == "peach"
    expect(items(page).first.locator(".hl-item__kind")).to_have_text("Peach")


def test_delete_with_undo_and_expiry(app):
    page = app
    stub = hl_preview(page)
    line(page, "Abstract").select_text()
    page.click("#pv-hl-btn")
    expect(items(page)).to_have_count(1)
    items(page).first.get_by_role("button", name="Add note").first.click()
    items(page).first.locator("textarea").fill("keep me")
    items(page).first.locator("textarea").press("Control+Enter")
    items(page).first.get_by_role("button", name="Delete").click()
    tomb = page.locator("#pv-hl-list li.hl-item--deleted")
    expect(tomb).to_contain_text("Highlight deleted.")
    expect(tomb.get_by_role("button", name="Undo")).to_be_focused()
    expect(hls(page)).to_have_count(0)
    assert stub.annotations == []
    tomb.get_by_role("button", name="Undo").click()
    expect(items(page)).to_have_count(1)
    expect(hls(page).first).to_be_attached()
    assert len(stub.annotations) == 1 and stub.annotations[0]["note"] == "keep me"
    # Without Undo the row disappears after the window.
    items(page).first.get_by_role("button", name="Delete").click()
    expect(tomb).to_have_count(1)
    expect(tomb).to_have_count(0, timeout=5_000)
    expect(page.locator("#pv-hl-empty .pv-empty__title")).to_be_visible()


def test_page_note_add_edit_and_delete(app):
    page = app
    stub = hl_preview(page)
    page.click("#pv-note-add")
    li = page.locator("#pv-hl-list li[data-draft]")
    expect(li).to_contain_text("Page note")
    expect(li).to_contain_text("Page 1")
    li.locator("textarea").fill("overall unclear on baselines")
    li.get_by_role("button", name="Save note").click()
    note = page.locator('#pv-hl-list li[data-kind="note"][data-annotation-id]')
    expect(note.locator(".hl-item__note")).to_have_text("overall unclear on baselines")
    expect(note.locator('select[data-act="color"]')).to_have_count(0)
    assert stub.annotations[0]["kind"] == "note" and stub.annotations[0]["rects"] == []
    expect(page.locator("#pv-hl-count")).to_have_text("0")  # the tab counts highlights
    note.get_by_role("button", name="Delete").click()
    expect(page.locator("#pv-hl-list li.hl-item--deleted")).to_contain_text("Note deleted.")
    assert stub.annotations == []


def test_go_to_scrolls_to_quarter_and_flashes(app):
    page = app
    hl_preview(page)
    page.locator("#pv-pages").evaluate(
        "w => { w.scrollTop = w.querySelector('[data-page=\"2\"]').offsetTop }"
    )
    expect(page.locator('.pdf-page[data-page="2"].has-text')).to_have_count(1, timeout=10_000)
    line(page, "Quartzite", 2).select_text()
    page.click("#pv-hl-btn")
    expect(items(page)).to_have_count(1)
    page.locator("#pv-pages").evaluate("w => { w.scrollTop = 0 }")
    expect(page.locator("#pv-page-input")).to_have_value("1")
    go = items(page).first.get_by_role("button", name="Go to highlight on page 2")
    go.click()
    expect(page.locator("#pv-page-input")).to_have_value("2")
    expect(hls(page, 2).first).to_have_class(re.compile("is-flash"))
    expect(page.locator("#pv-pages")).to_be_focused()
    well = page.locator("#pv-pages").bounding_box()
    hl = hls(page, 2).first.bounding_box()
    frac = (hl["y"] - well["y"]) / well["height"]
    assert 0.1 < frac < 0.4, frac


def test_cross_page_selection_highlights_only_the_start_page(app):
    page = app
    stub = hl_preview(page)
    page.locator("#pv-pages").evaluate(
        "w => { w.scrollTop = w.querySelector('[data-page=\"2\"]').offsetTop - 300 }"
    )
    expect(page.locator('.pdf-page[data-page="2"].has-text')).to_have_count(1, timeout=10_000)
    page.evaluate(
        """() => {
          const a = [...document.querySelectorAll('[data-page="1"] .textLayer span')].find(s => s.textContent.includes('Abstract'));
          const b = [...document.querySelectorAll('[data-page="2"] .textLayer span')].find(s => s.textContent.includes('Quartzite'));
          getSelection().setBaseAndExtent(a.firstChild, 0, b.firstChild, 5);
        }"""
    )
    expect(page.locator("#pv-hl-btn")).not_to_have_attribute("aria-disabled", "true")
    page.click("#pv-hl-btn")
    expect(page.locator("#status")).to_have_text(
        "Highlighted the part on page 1. Select across pages one page at a time."
    )
    assert len(stub.annotations) == 1 and stub.annotations[0]["page"] == 1


def test_highlight_save_failure_keeps_dashed_mark_and_retries(app):
    page = app
    stub = hl_preview(page)
    stub.fail[("POST", "/api/annotations")] = (500, "disk full")
    line(page, "Abstract").select_text()
    page.click("#pv-hl-btn")
    it = items(page).first
    expect(it.locator(".row-error")).to_contain_text("Could not save. disk full")
    expect(hls(page).first).to_have_class(re.compile("hl--failed"))
    it.get_by_role("button", name="Try again").click()
    expect(items(page).first.locator(".row-error")).to_have_count(0)
    expect(hls(page).first).not_to_have_class(re.compile("hl--failed"))
    assert len(stub.annotations) == 1


def test_export_notes_downloads_markdown(app):
    page = app
    hl_preview(page)
    export = page.locator("#pv-export")
    expect(export).to_have_attribute("aria-disabled", "true")
    expect(export).to_have_text("Export notes")
    line(page, "Abstract").select_text()
    page.click("#pv-hl-btn")
    expect(export).not_to_have_attribute("aria-disabled", "true")
    items(page).first.get_by_role("button", name="Add note").first.click()
    items(page).first.locator("textarea").fill("weak baseline")
    items(page).first.locator("textarea").press("Control+Enter")
    with page.expect_download() as dl:
        export.click()
    d = dl.value
    assert d.suggested_filename == "2401.00001-notes.md"
    text = Path(d.path()).read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "# Saved paper 1: stubbed title"
    assert lines[1].startswith("2401.00001 · https://arxiv.org/abs/2401.00001")
    assert lines[2] == ""
    assert lines[3].startswith("> ") and lines[3].endswith("(p.1)") and "Abstract" in lines[3]
    assert lines[4] == "weak baseline"
    expect(page.locator("#status")).to_have_text("Notes exported.")


def _blank_pdf():
    import io

    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def test_scanned_page_shows_message_and_still_takes_page_notes(app):
    page = app
    page.add_init_script("window.__PT_UNDO_MS = 800")
    stub = preview(
        page, [lib_item(1, pdf={"status": "ready", "error": None, "pages": 1})], pdf=_blank_pdf()
    )
    expect(page.locator(".pdf-page")).to_have_count(1)
    msg = page.locator(".pdf-page__notext")
    expect(msg).to_contain_text("No selectable text on this page.", timeout=10_000)
    page.click("#pv-note-add")
    page.locator("#pv-hl-list li[data-draft] textarea").fill("scanned appendix")
    page.get_by_role("button", name="Save note").click()
    expect(page.locator('#pv-hl-list li[data-kind="note"]')).to_contain_text("scanned appendix")
    assert stub.annotations[0]["kind"] == "note"


def test_panel_states_when_pdf_not_ready(app):
    page = app
    preview(page, [lib_item(1, pdf={"status": "pending", "error": None, "pages": None})])
    expect(page.locator("#pv-panel")).to_be_visible()
    expect(page.locator("#pv-hl-msg")).to_have_text(
        "Highlights are available once the PDF is ready."
    )
    expect(page.locator("#pv-hl-list")).to_be_hidden()
    expect(page.locator("#pv-hl-btn")).to_be_hidden()
    expect(page.locator("#pv-export")).to_be_hidden()


def test_panel_is_a_separate_column_on_wide_screens(app):
    page = app
    hl_preview(page)
    panel = page.locator("#pv-panel").bounding_box()
    well = page.locator("#pv-pages").bounding_box()
    assert abs(panel["width"] - 384) < 2
    assert well["x"] + well["width"] <= panel["x"] + 1
    expect(page.locator("a.skip[data-skip=preview]")).to_have_count(2)
    expect(page.locator("a.skip:not([hidden])")).to_have_count(2)


# Real harness (BE T051): highlight and note persist; zoom keeps the mark proportional.


def _real_preview(app, base):
    page = app
    topic = _triage(page, base, "diffusion distillation")
    _save(page, base, topic, "2401.00001")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto("/#/library/paper/2401.00001")
    expect(page.locator(".pdf-page")).to_have_count(3, timeout=20_000)
    expect(page.locator('.pdf-page[data-page="1"].has-text')).to_have_count(1, timeout=10_000)
    return page


def test_real_highlight_persists_and_scales_with_zoom(app, real_library):
    page = _real_preview(app, real_library)
    line(page, "Abstract").select_text()
    page.click("#pv-hl-btn")
    # The optimistic node (tmp-N) is replaced by the persisted one: wait for the saved id (F-012).
    expect(hls(page).first).to_have_attribute("data-annotation-id", re.compile(r"^\d+$"))
    ratio_fit = hls(page).first.evaluate(
        "e => e.getBoundingClientRect().width / e.closest('.pdf-page').clientWidth"
    )
    page.select_option("#pv-zoom", "200")
    page.wait_for_function(
        "document.querySelector('.pdf-page').getBoundingClientRect().width > 1500"
    )
    ratio_zoom = hls(page).first.evaluate(
        "e => e.getBoundingClientRect().width / e.closest('.pdf-page').clientWidth"
    )
    assert abs(ratio_fit - ratio_zoom) < 0.005
    page.select_option("#pv-zoom", "50")
    page.wait_for_function(
        "document.querySelector('.pdf-page').getBoundingClientRect().width < 450"
    )
    ratio_small = hls(page).first.evaluate(
        "e => e.getBoundingClientRect().width / e.closest('.pdf-page').clientWidth"
    )
    assert abs(ratio_fit - ratio_small) < 0.005
    api = page.request.get(f"{real_library}/api/annotations?paper_id=2401.00001").json()[
        "annotations"
    ]
    assert len(api) == 1 and 0 < api[0]["rects"][0][2] <= 1
    # Add a note, reload: both persist.
    items(page).first.get_by_role("button", name="Add note").first.click()
    items(page).first.locator("textarea").fill("real note")
    items(page).first.locator("textarea").press("Control+Enter")
    page.reload()
    expect(page.locator(".pdf-page")).to_have_count(3, timeout=20_000)
    expect(items(page)).to_have_count(1, timeout=10_000)
    expect(items(page).first.locator(".hl-item__note")).to_have_text("real note")
    expect(hls(page).first).to_be_attached()
    expect(page.locator("#pv-hl-count")).to_have_text("1")
    # The Library row and nav reflect the highlight count.
    page.goto("/#/library")
    expect(page.locator(".lib-row .lib-hl")).to_have_text("1 highlight")


def test_real_go_to_jumps_to_the_page(app, real_library):
    page = _real_preview(app, real_library)
    page.locator("#pv-pages").evaluate(
        "w => { w.scrollTop = w.querySelector('[data-page=\"2\"]').offsetTop }"
    )
    expect(page.locator('.pdf-page[data-page="2"].has-text')).to_have_count(1, timeout=10_000)
    line(page, "Quartzite", 2).select_text()
    page.click("#pv-hl-btn")
    expect(items(page)).to_have_count(1)
    page.select_option("#pv-zoom", "fit-page")
    page.locator("#pv-pages").evaluate("w => { w.scrollTop = 0 }")
    items(page).first.get_by_role("button", name=re.compile("Go to highlight on page 2")).click()
    expect(page.locator("#pv-page-input")).to_have_value("2")


# ---- T063: Ask this paper panel and sheet ----


def chat_requests(page):
    reqs = []
    page.on(
        "request",
        lambda r: reqs.append(r.post_data_json) if r.url.endswith("/api/paper-chat") else None,
    )
    return reqs


def stub_chat(page, responder):
    """Stub POST /api/paper-chat; `responder(body)` returns (status, json)."""

    def handle(route):
        status, data = responder(route.request.post_data_json)
        route.fulfill(status=status, content_type="application/json", body=json.dumps(data))

    page.route(lambda url: url.endswith("/api/paper-chat"), handle)


def ask_tab(page):
    page.click("#pv-tab-chat")
    expect(page.locator("#pv-tabpanel-chat")).to_be_visible()


def ask(page, q):
    page.fill("#pv-chat-question", q)
    page.click("#pv-chat-ask")


def chat_turns(page):
    return page.locator("#pv-chat-log li.turn")


def test_chat_is_lazy_no_request_until_first_question(app):
    page = app
    reqs = chat_requests(page)
    hl_preview(page)
    ask_tab(page)
    expect(page.locator("#pv-chat-idle")).to_be_visible()
    expect(page.locator("#pv-chat-idle .pv-empty__title")).to_have_text(
        "Chat is off until you ask."
    )
    expect(page.locator("#pv-chat-idle .pv-empty__body")).to_have_text(
        "Your first question reads this paper, so it takes longer than the rest."
    )
    starters = page.locator("#pv-chat-starters button")
    assert starters.all_inner_texts() == [
        "What is the main claim?",
        "What baselines are compared?",
        "What are the stated limitations?",
    ]
    expect(page.locator("#pv-chat-scope")).to_have_text(
        "Answers use only this paper. Citations point to pages. Not saved: closing or reloading clears this chat."
    )
    expect(page.locator("label[for=pv-chat-question]")).to_have_text("Question about this paper")
    expect(page.locator("#pv-chat-question")).to_have_attribute(
        "placeholder", "Ask about this paper"
    )
    expect(page.locator("#pv-chat-ask")).to_have_class(re.compile("btn--primary"))
    expect(page.locator("#pv-chat-log")).to_have_attribute("role", "log")
    expect(page.locator("#pv-chat-log")).to_have_attribute(
        "aria-label", "Conversation about this paper"
    )
    page.click("#pv-tab-hl")
    page.click("#pv-tab-chat")
    page.wait_for_timeout(300)
    assert reqs == [], "chat must not call the server before the first question"


def test_chat_starter_sends_first_question(app):
    page = app
    reqs = chat_requests(page)
    stub_chat(
        page,
        lambda b: (
            200,
            {"answer": "Fine [p.1].", "pages": [1], "refused": False, "dropped_pages": []},
        ),
    )
    hl_preview(page)
    ask_tab(page)
    page.get_by_role("button", name="What baselines are compared?").click()
    expect(chat_turns(page)).to_have_count(1)
    expect(chat_turns(page).first.locator(".turn__q")).to_contain_text(
        "What baselines are compared?"
    )
    expect(chat_turns(page).first.locator(".cite")).to_have_count(2)  # inline marker and Pages line
    assert reqs == [
        {"paper_id": "2401.00001", "question": "What baselines are compared?", "history": []}
    ]
    expect(page.locator("#pv-chat-idle")).to_be_hidden()
    expect(page.locator("#pv-chat-reset")).to_have_text(
        "This chat clears when you close the preview or reload."
    )


def test_chat_pending_copy_first_slow_and_later(app):
    page = app
    page.add_init_script("window.__PT_CHAT_SLOW_MS = 400")
    held = []
    page.route(
        lambda url: url.endswith("/api/paper-chat"),
        lambda route: held.append(route),
    )
    hl_preview(page)
    ask_tab(page)
    ask(page, "first question")
    pending = page.locator("#pv-chat-log .turn__pending")
    expect(pending).to_have_text("Reading this paper. The first answer takes longer.")
    expect(page.locator("#pv-chat-ask")).to_be_disabled()
    expect(page.locator("#pv-chat-question")).to_be_enabled()
    expect(pending).to_have_text("Still reading. Long papers take up to a minute.")
    held[0].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            {"answer": "ok [p.1]", "pages": [1], "refused": False, "dropped_pages": []}
        ),
    )
    expect(page.locator("#pv-chat-ask")).to_be_enabled()
    ask(page, "second question")
    expect(page.locator("#pv-chat-log .turn__pending")).to_have_text("Reading this paper…")
    held[1].abort()


def test_chat_history_is_last_six_turns(app):
    page = app
    reqs = chat_requests(page)
    stub_chat(
        page,
        lambda b: (
            200,
            {
                "answer": f"A for {b['question']} [p.1]",
                "pages": [1],
                "refused": False,
                "dropped_pages": [],
            },
        ),
    )
    hl_preview(page)
    ask_tab(page)
    for i in range(8):
        ask(page, f"q{i}")
        expect(chat_turns(page)).to_have_count(i + 1)
        expect(page.locator("#pv-chat-ask")).to_be_enabled()
    assert reqs[0]["history"] == []
    assert reqs[1]["history"] == [{"question": "q0", "answer": "A for q0 [p.1]"}]
    assert len(reqs[7]["history"]) == 6
    assert reqs[7]["history"][0]["question"] == "q1" and reqs[7]["history"][-1]["question"] == "q6"


def test_chat_cite_chip_jumps_to_page_and_flashes(app):
    page = app
    stub_chat(
        page,
        lambda b: (
            200,
            {
                "answer": "See [p.3] and [p.99].",
                "pages": [3],
                "refused": False,
                "dropped_pages": [99],
            },
        ),
    )
    hl_preview(page)
    ask_tab(page)
    ask(page, "where?")
    cite = chat_turns(page).first.locator('.turn__a button.cite[data-page="3"]').first
    expect(cite).to_have_text("p. 3")
    expect(cite).to_have_attribute("aria-label", "Go to page 3")
    expect(chat_turns(page).first.locator(".turn__a")).not_to_contain_text("99")
    expect(chat_turns(page).first.locator(".sources")).to_contain_text("Pages: p. 3")
    cite.click()
    expect(page.locator("#pv-page-input")).to_have_value("3")
    expect(page.locator('.pdf-page[data-page="3"]')).to_have_class(re.compile("is-flash"))
    expect(page.locator("#pv-pages")).to_be_focused()


def test_chat_arxiv_tokens_are_plain_chips(app):
    page = app
    stub_chat(
        page,
        lambda b: (
            200,
            {
                "answer": "Per [arXiv:2401.00001] [p.1].",
                "pages": [1],
                "refused": False,
                "dropped_pages": [],
            },
        ),
    )
    hl_preview(page)
    ask_tab(page)
    ask(page, "x")
    chip = chat_turns(page).first.locator("span.cite")
    expect(chip).to_have_text("arXiv:2401.00001")
    expect(chip).not_to_have_attribute("role", "button")


def test_chat_refusal_component(app):
    page = app
    stub_chat(
        page,
        lambda b: (
            200,
            {"answer": "That is not covered.", "pages": [], "refused": True, "dropped_pages": []},
        ),
    )
    hl_preview(page)
    ask_tab(page)
    ask(page, "capital of France?")
    r = chat_turns(page).first.locator(".turn__a--refused")
    expect(r.locator(".turn__refused-title")).to_have_text("Not in this paper")
    expect(r.locator(".turn__refused-body")).to_have_text("That is not covered.")
    expect(r.locator(".turn__refused-hint")).to_have_text("Ask about something this paper covers.")
    expect(chat_turns(page).first.locator("button.cite")).to_have_count(0)


def test_chat_first_question_error_returns_to_idle_and_restores_input(app):
    page = app
    stub_chat(page, lambda b: (502, {"detail": "model call failed: boom"}))
    hl_preview(page)
    ask_tab(page)
    ask(page, "my first question")
    err = page.locator("#pv-chat-error")
    expect(err).to_have_text("Could not answer. model call failed: boom")
    expect(err).to_have_attribute("role", "alert")
    expect(page.locator("#pv-chat-idle")).to_be_visible()
    expect(chat_turns(page)).to_have_count(0)
    expect(page.locator("#pv-chat-question")).to_have_value("my first question")


def test_chat_later_error_offers_ask_again(app):
    page = app
    calls = []

    def responder(b):
        calls.append(b["question"])
        if len(calls) == 2:
            return 502, {"detail": "model call failed: boom"}
        return 200, {"answer": "ok [p.1]", "pages": [1], "refused": False, "dropped_pages": []}

    stub_chat(page, responder)
    hl_preview(page)
    ask_tab(page)
    ask(page, "one")
    expect(chat_turns(page)).to_have_count(1)
    ask(page, "two")
    err = chat_turns(page).nth(1).locator(".turn__err")
    expect(err).to_contain_text("Could not answer. model call failed: boom")
    err.get_by_role("button", name="Ask again").click()
    expect(chat_turns(page).nth(1).locator(".turn__a")).to_be_visible()
    assert calls == ["one", "two", "two"]


def test_chat_disabled_without_ready_pdf(app):
    page = app
    reqs = chat_requests(page)
    stub = preview(page, [lib_item(1, pdf={"status": "pending", "error": None, "pages": None})])
    ask_tab(page)
    expect(page.locator("#pv-chat-nopdf")).to_have_text(
        "Chat needs the PDF text. It is not ready yet."
    )
    expect(page.locator("#pv-chat-question")).to_be_disabled()
    expect(page.locator("#pv-chat-ask")).to_be_disabled()
    expect(page.locator("#pv-chat-idle")).to_be_hidden()
    stub.items[0]["pdf"] = {"status": "ready", "error": None, "pages": 3}
    expect(page.locator("#pv-chat-question")).to_be_enabled(timeout=10_000)
    expect(page.locator("#pv-chat-nopdf")).to_be_hidden()
    assert reqs == []


def test_chat_unavailable_pdf_copy(app):
    page = app
    preview(page, [lib_item(1, pdf={"status": "failed", "error": "Not a PDF.", "pages": None})])
    ask_tab(page)
    expect(page.locator("#pv-chat-nopdf")).to_have_text(
        "Chat needs the PDF text, and this PDF is unavailable."
    )
    expect(page.locator("#pv-chat-question")).to_be_disabled()


def test_chat_transcript_clears_on_close_and_reload(app):
    page = app
    stub_chat(
        page,
        lambda b: (
            200,
            {"answer": "ok [p.1]", "pages": [1], "refused": False, "dropped_pages": []},
        ),
    )
    page.add_init_script("window.__PT_UNDO_MS = 800")
    preview(page, [lib_item(1)], hash_="#/library")
    page.locator(".open-preview").first.click()
    expect(page.locator(".pdf-page")).to_have_count(3)
    ask_tab(page)
    ask(page, "hello")
    expect(chat_turns(page)).to_have_count(1)
    page.click("#pv-back")
    page.locator(".open-preview").first.click()
    expect(page.locator(".pdf-page")).to_have_count(3)
    ask_tab(page)
    expect(chat_turns(page)).to_have_count(0)
    expect(page.locator("#pv-chat-idle")).to_be_visible()
    ask(page, "again")
    expect(chat_turns(page)).to_have_count(1)
    page.reload()
    expect(page.locator(".pdf-page")).to_have_count(3)
    ask_tab(page)
    expect(chat_turns(page)).to_have_count(0)


def test_tabs_keyboard_roving_arrows_home_end(app):
    page = app
    hl_preview(page)
    tabs = page.locator("#pv-tabs [role=tab]")
    assert [t.inner_text().strip() for t in tabs.all()][1] == "Ask this paper"
    expect(page.locator("#pv-tabs")).to_have_attribute("role", "tablist")
    hl, chat = page.locator("#pv-tab-hl"), page.locator("#pv-tab-chat")
    expect(hl).to_have_attribute("aria-controls", "pv-tabpanel-hl")
    expect(chat).to_have_attribute("aria-controls", "pv-tabpanel-chat")
    hl.focus()
    page.keyboard.press("ArrowRight")
    expect(chat).to_be_focused()
    expect(chat).to_have_attribute("aria-selected", "true")
    expect(hl).to_have_attribute("aria-selected", "false")
    expect(page.locator("#pv-tabpanel-chat")).to_be_visible()
    expect(page.locator("#pv-tabpanel-hl")).to_be_hidden()
    page.keyboard.press("Home")
    expect(hl).to_be_focused()
    page.keyboard.press("End")
    expect(chat).to_be_focused()
    page.keyboard.press("ArrowRight")
    expect(hl).to_be_focused()


def test_slash_focuses_chat_input_in_preview(app):
    page = app
    hl_preview(page)
    ask_tab(page)
    page.locator("#pv-pages").focus()
    page.keyboard.press("/")
    expect(page.locator("#pv-chat-question")).to_be_focused()


def test_sheet_below_1024_opens_modal_with_tabs_and_returns_focus(app):
    page = app
    page.set_viewport_size({"width": 800, "height": 900})
    stub_chat(
        page,
        lambda b: (
            200,
            {"answer": "ok [p.2]", "pages": [2], "refused": False, "dropped_pages": []},
        ),
    )
    page.add_init_script("window.__PT_UNDO_MS = 800")
    preview(page, [lib_item(1)])
    page.set_viewport_size({"width": 800, "height": 900})
    expect(page.locator(".pdf-page")).to_have_count(3)
    expect(page.locator("#pv-panel")).to_be_hidden()
    btn = page.locator("#pv-sheet-open")
    expect(btn).to_have_text("Highlights and chat")
    expect(page.locator("#pv-sheet")).not_to_have_attribute("open", "")
    btn.click()
    sheet = page.locator("#pv-sheet")
    expect(sheet).to_be_visible()
    assert sheet.evaluate("e => e.open && e.matches(':modal')")
    expect(sheet.locator("#pv-tabs")).to_be_visible()
    sheet.locator("#pv-tab-chat").click()
    ask(page, "where")
    expect(sheet.locator("#pv-chat-log li.turn")).to_have_count(1)
    # Esc closes and returns focus to the toolbar button.
    page.keyboard.press("Escape")
    expect(sheet).not_to_have_attribute("open", "")
    expect(btn).to_be_focused()
    # Close button does the same.
    btn.click()
    sheet.locator("#pv-sheet-close").click()
    expect(btn).to_be_focused()
    # A cite chip closes the sheet first, then jumps.
    btn.click()
    sheet.locator("#pv-tab-chat").click()
    sheet.locator("button.cite").first.click()
    expect(sheet).not_to_have_attribute("open", "")
    expect(page.locator("#pv-page-input")).to_have_value("2")
    expect(page.locator("#pv-pages")).to_be_focused()


def test_sheet_opens_for_note_from_popover_and_closes_when_wide(app):
    page = app
    page.set_viewport_size({"width": 800, "height": 900})
    stub = preview(page, [lib_item(1)])
    page.set_viewport_size({"width": 800, "height": 900})
    expect(page.locator('.pdf-page[data-page="1"].has-text')).to_have_count(1, timeout=10_000)
    drag_select(page, "Abstract")
    page.locator("#pv-popover").get_by_role("button", name="Add note").click()
    expect(page.locator("#pv-sheet")).to_be_visible()
    expect(page.locator("#pv-sheet textarea")).to_be_focused()
    page.locator("#pv-sheet textarea").fill("from the sheet")
    page.locator("#pv-sheet textarea").press("Control+Enter")
    assert stub.annotations[0]["note"] == "from the sheet"
    page.set_viewport_size({"width": 1280, "height": 900})
    expect(page.locator("#pv-sheet")).not_to_have_attribute("open", "")
    expect(page.locator("#pv-panel")).to_be_visible()
    expect(items(page)).to_have_count(1)


# Real harness (BE T057-T058): grounded answer with a page cite, refusal, no early request.


def test_real_paper_chat_cites_page_2_and_jumps(app, real_library):
    page = _real_preview(app, real_library)
    reqs = chat_requests(page)
    ask_tab(page)
    page.wait_for_timeout(300)
    assert reqs == []
    ask(page, "Where is Quartzite discussed?")
    expect(chat_turns(page)).to_have_count(1)
    cite = chat_turns(page).first.locator('button.cite[data-page="2"]').first
    expect(cite).to_have_text("p. 2", timeout=20_000)
    assert reqs[0]["paper_id"] == "2401.00001" and reqs[0]["history"] == []
    cite.click()
    expect(page.locator("#pv-page-input")).to_have_value("2")


def test_real_paper_chat_refuses_outside_the_paper(app, real_library):
    page = _real_preview(app, real_library)
    ask_tab(page)
    ask(page, "What is the capital of France?")
    expect(chat_turns(page).first.locator(".turn__a--refused")).to_be_visible(timeout=20_000)
    expect(chat_turns(page).first.locator("button.cite")).to_have_count(0)
    expect(chat_turns(page).first.locator(".turn__refused-title")).to_have_text("Not in this paper")


# ---- v3 audit fixes: Library ----


def test_audit_rail_items_stay_inside_the_rail(app):
    page = app
    stub = lib_page(page, [lib_item(1, directory_id=1)])
    stub.directories = [
        {"id": 1, "name": "final year thesis with a really very long name indeed", "count": 1}
    ]
    page.reload()
    expect(rows(page)).to_have_count(1)
    rail = page.locator("#dir-rail").bounding_box()
    right = rail["x"] + rail["width"]
    for item in page.locator("#dir-list button.rail__item").all():
        b = item.bounding_box()
        assert b["x"] + b["width"] <= right + 0.5, (item.inner_text(), b, right)
    long = page.locator("#dir-list button.rail__item").nth(2)
    expect(long).to_have_attribute("title", "final year thesis with a really very long name indeed")
    assert long.locator(".rail__name").evaluate("e => e.scrollWidth > e.clientWidth")


def test_audit_new_directory_form_in_rail_keeps_a_wide_input(app):
    page = app
    lib_page(page, [lib_item(1)])
    page.click("#dir-new")
    box = page.locator("#dir-new-slot input").bounding_box()
    assert box["width"] > 180, box
    for b in page.locator("#dir-new-slot button").all():
        assert b.bounding_box()["y"] > box["y"]


def test_audit_rank_caption_is_one_line_under_authors_at_every_width(app):
    page = app
    lib_page(page, [lib_item(1, topic="diffusion models video")])
    li = rows(page).first
    expect(li.locator(".rank__for")).to_be_hidden()
    expect(li.locator(".lib-for")).to_have_text('Ranked for "diffusion models video"')
    expect(li.locator(".lib-for")).to_be_visible()


def test_audit_no_horizontal_overflow_with_long_directory_on_mobile(app):
    page = app
    stub = LibraryStub(page, [lib_item(1, directory_id=1)])
    stub.directories = [
        {"id": 1, "name": "final year thesis with a really very long name indeed", "count": 1}
    ]
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto("/#/library")
    expect(rows(page)).to_have_count(1)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390


def test_audit_mobile_title_gets_the_full_row(app):
    page = app
    lib_page(
        page,
        [
            lib_item(
                1, title="A fairly long saved paper title that needs room to breathe on a phone"
            )
        ],
    )
    page.set_viewport_size({"width": 390, "height": 844})
    title = rows(page).first.locator(".paper__title").bounding_box()
    btn = rows(page).first.locator("button.open-preview").bounding_box()
    assert btn["y"] > title["y"] + title["height"] - 1
    assert title["width"] > 250


def test_audit_empty_directory_hides_filters_and_tag_note(app):
    page = app
    stub = lib_page(page, [lib_item(1, tags=["diffusion"])], hash_="#/library?dir=network")
    stub.directories = [{"id": 1, "name": "network", "count": 0}]
    page.reload()
    expect(page.locator("#library-empty .empty__title")).to_have_text("No papers in network.")
    expect(page.locator(".lib-filters")).to_be_hidden()
    expect(page.locator("#lib-tags-none")).to_be_hidden()


def test_audit_tag_note_only_when_library_has_no_tags(app):
    page = app
    stub = lib_page(page, [tagged(1, ["a1"], directory_id=None), tagged(2, [], directory_id=1)])
    stub.directories = [{"id": 1, "name": "network", "count": 1}]
    page.goto("/#/library?dir=network")
    page.reload()
    expect(rows(page)).to_have_count(1)
    expect(page.locator("#lib-tags-none")).to_be_hidden()


# ---- v3 audit fixes: Preview ----


def vp(page, w, h=900):
    page.set_viewport_size({"width": w, "height": h})


def test_audit_mobile_toolbar_is_compact_with_two_line_title(app):
    page = app
    preview(
        page,
        [lib_item(1, title="Progressive Distillation for Fast Sampling of Diffusion Models")],
    )
    vp(page, 390, 844)
    expect(page.locator(".pdf-page")).to_have_count(3)
    h = page.locator(".pv-toolbar").evaluate("e => e.getBoundingClientRect().height")
    assert h < 260, h
    title = page.locator("#preview-heading").bounding_box()
    assert title["width"] > 180 and title["height"] > 30  # two lines, not 9 characters
    expect(page.locator("#pv-zoom-in")).to_be_hidden()
    expect(page.locator("#pv-zoom-out")).to_be_hidden()
    expect(page.locator("#pv-zoom")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    # Rows: back + title, page nav, highlight + sheet button, links.
    ys = {
        n: page.locator(sel).bounding_box()["y"]
        for n, sel in {
            "back": "#pv-back",
            "pager": "#pv-prev",
            "hl": "#pv-hl-btn",
            "export": "#pv-export",
        }.items()
    }
    assert ys["back"] < ys["pager"] < ys["hl"] < ys["export"]


def test_audit_tablet_title_keeps_room_and_sheet_button_joins_controls(app):
    page = app
    preview(
        page, [lib_item(1, title="Progressive Distillation for Fast Sampling of Diffusion Models")]
    )
    vp(page, 820, 1100)
    expect(page.locator(".pdf-page")).to_have_count(3)
    title = page.locator("#preview-heading").bounding_box()
    assert title["width"] > 380, title
    sheet = page.locator("#pv-sheet-open").bounding_box()
    find = page.locator("#pv-find-btn").bounding_box()
    assert abs(sheet["y"] - find["y"]) < 20  # same row as the controls
    assert sheet["x"] > find["x"]


def test_audit_toolbar_controls_share_one_height_and_highlight_is_split(app):
    page = app
    hl_preview(page)
    for sel in (
        "#pv-prev",
        "#pv-page-input",
        "#pv-zoom",
        "#pv-zoom-in",
        "#pv-find-btn",
        "#pv-hl-btn",
        "#pv-hl-color",
    ):
        b = page.locator(sel).bounding_box()
        assert abs(b["height"] - 40) < 1, (sel, b)
    btn = page.locator("#pv-hl-btn").bounding_box()
    sel = page.locator("#pv-hl-color").bounding_box()
    assert abs((btn["x"] + btn["width"]) - sel["x"]) <= 1.5  # shared edge, no gap


def test_audit_disabled_text_button_looks_disabled(app):
    page = app
    hl_preview(page)
    muted = page.locator("#pv-export").evaluate("e => getComputedStyle(e).color")
    live = page.locator("#pv-note-add").evaluate("e => getComputedStyle(e).color")
    assert muted != live
    assert muted == "rgb(65, 69, 77)"


def test_audit_popover_never_covers_the_toolbar(app):
    page = app
    hl_preview(page)
    drag_select(page, "Sample Paper")  # first line: nearest the well's top edge
    pop = page.locator("#pv-popover")
    expect(pop).to_be_visible()
    well = page.locator("#pv-pages").bounding_box()
    assert pop.bounding_box()["y"] >= well["y"] - 0.5


def test_audit_new_paper_opens_on_highlights_tab(app):
    page = app
    LibraryStub(page, [lib_item(1), lib_item(2)])
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto("/#/library/paper/2401.00001")
    expect(page.locator(".pdf-page")).to_have_count(3)
    ask_tab(page)
    expect(page.locator("#pv-tab-chat")).to_have_attribute("aria-selected", "true")
    page.goto("/#/library/paper/2401.00002")
    expect(page.locator("#pv-tab-hl")).to_have_attribute("aria-selected", "true")
    expect(page.locator("#pv-tabpanel-hl")).to_be_visible()
    expect(page.locator("#pv-tabpanel-chat")).to_be_hidden()


def test_audit_sheet_header_is_one_row_on_canvas(app):
    page = app
    vp(page, 800, 900)
    preview(page, [lib_item(1)])
    vp(page, 800, 900)
    expect(page.locator(".pdf-page")).to_have_count(3)
    page.click("#pv-sheet-open")
    sheet = page.locator("#pv-sheet")
    expect(sheet).to_be_visible()
    tabs = sheet.locator("#pv-tab-hl").bounding_box()
    close = sheet.locator("#pv-sheet-close").bounding_box()
    assert abs((tabs["y"] + tabs["height"] / 2) - (close["y"] + close["height"] / 2)) < 12
    assert abs(close["height"] - 40) < 1
    assert sheet.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
    page.keyboard.press("Escape")
    expect(sheet.locator("#pv-sheet-close")).to_have_count(0)
    expect(page.locator("#pv-sheet-close")).to_be_hidden()


# ---- T064: v3 end-to-end on the real harness (SC-011 .. SC-016) ----


def _triage_ui(page, query, rows_expected):
    page.fill("#query", query)
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(rows_expected, timeout=15_000)
    expect(page.locator("#submit")).to_be_enabled()


def test_e2e_card_to_pdf_in_three_actions_with_time_budgets(app, real_library):
    """SC-011 (first page within 2 s), SC-016 (card to PDF in 3 actions), PDF ready within 5 s."""
    page = app
    reqs = chat_requests(page)
    page.goto("/")
    _triage_ui(page, "2401.00001", 1)
    # Action 1: Save on the card.
    save_btn(page, 1).click()
    expect(save_btn(page, 1)).to_have_text("Saved", timeout=10_000)
    # Action 2: open the Library; the row reaches "PDF ready" within 5 s.
    t0 = time.monotonic()
    page.click('nav.views a[data-view="library"]')
    status = rows(page).first.locator("[data-pdf-status]")
    expect(status).to_have_text("PDF ready", timeout=5_000)
    assert time.monotonic() - t0 < 5.0
    # Action 3: Open preview; page 1 renders within 2 s.
    t1 = time.monotonic()
    rows(page).first.locator("button.open-preview").click()
    expect(page.locator('.pdf-page[data-page="1"].is-drawn')).to_have_count(1, timeout=2_000)
    assert time.monotonic() - t1 < 2.0
    expect(page.locator('.pdf-page[data-page="1"] .textLayer')).to_contain_text(
        "Distillation", timeout=5_000
    )
    # SC-014: opening the preview made no paper-chat request.
    assert reqs == []


def test_e2e_chat_cites_page_refuses_and_is_lazy(app, real_library):
    """SC-014: nothing before the first question; Quartzite cites p. 2 and jumps; France refused."""
    page = _real_preview(app, real_library)
    reqs = chat_requests(page)
    ask_tab(page)
    expect(page.locator("#pv-chat-idle")).to_be_visible()
    page.wait_for_timeout(500)
    assert reqs == []
    ask(page, "Where is Quartzite discussed?")
    cite = chat_turns(page).first.locator('button.cite[data-page="2"]').first
    expect(cite).to_have_text("p. 2", timeout=20_000)
    assert len(reqs) == 1
    cite.click()
    expect(page.locator("#pv-page-input")).to_have_value("2")
    expect(page.locator('.pdf-page[data-page="2"]')).to_have_class(re.compile("is-flash"))
    ask(page, "What is the capital of France?")
    refused = chat_turns(page).nth(1).locator(".turn__a--refused")
    expect(refused).to_be_visible(timeout=20_000)
    expect(refused.locator(".turn__refused-title")).to_have_text("Not in this paper")
    expect(chat_turns(page).nth(1).locator("button.cite")).to_have_count(0)
    assert reqs[1]["history"] and reqs[1]["history"][0]["question"].startswith("Where is Quartzite")


def test_e2e_unsave_from_the_card_confirms_and_removes_everything(app, real_library):
    """SC-015: unsave with confirm removes the row, the PDF and the annotations."""
    page, base = app, real_library
    page.goto("/")
    _triage_ui(page, "2401.00001", 1)
    save_btn(page, 1).click()
    expect(save_btn(page, 1)).to_have_text("Saved", timeout=10_000)
    expect(page.locator(".views__count")).to_have_text("1")
    # A highlight exists, so the confirm names it.
    page.request.post(
        f"{base}/api/annotations",
        data={
            "paper_id": "2401.00001",
            "page": 1,
            "kind": "note",
            "note": "n",
            "rects": [],
            "quote": "",
        },
    )
    expect(page.locator(".views__count")).to_have_text("1")
    pdf_before = page.request.get(f"{base}/api/library/pdf?paper_id=2401.00001")
    assert pdf_before.status == 200
    save_btn(page, 1).click()
    group = page.locator('[data-confirm="unsave"]')
    expect(group).to_be_visible()
    page.get_by_role("button", name="Remove", exact=True).click()
    expect(save_btn(page, 1)).to_have_text("Save", timeout=10_000)
    expect(page.locator(".views__count")).to_be_hidden()
    page.click('nav.views a[data-view="library"]')
    expect(page.locator("#library-empty-all .empty__title")).to_have_text("Nothing saved yet.")
    assert page.request.get(f"{base}/api/library/pdf?paper_id=2401.00001").status == 404
    assert page.request.get(f"{base}/api/annotations?paper_id=2401.00001").status == 404


def test_e2e_unavailable_pdf_shows_status_and_disabled_chat(app, real_library):
    page = app
    page.goto("/")
    _triage_ui(page, "2401.00005", 1)
    save_btn(page, 5).click()
    expect(save_btn(page, 5)).to_have_text("Saved", timeout=10_000)
    page.click('nav.views a[data-view="library"]')
    expect(rows(page).first.locator("[data-pdf-status]")).to_contain_text(
        "PDF unavailable", timeout=5_000
    )
    rows(page).first.locator("button.open-preview").click()
    expect(page.locator("#pv-stage .alert")).to_contain_text("This PDF could not be downloaded.")
    ask_tab(page)
    expect(page.locator("#pv-chat-nopdf")).to_have_text(
        "Chat needs the PDF text, and this PDF is unavailable."
    )
    expect(page.locator("#pv-chat-question")).to_be_disabled()
    expect(page.locator("#pv-chat-ask")).to_be_disabled()


def test_e2e_highlight_and_note_survive_a_server_restart(offline_page, tmp_path, monkeypatch):
    """SC-013: stored highlight and note are back after the server restarts on the same data."""
    import tempfile

    from e2e_harness import LiveServer

    page = offline_page
    port = int(os.environ.get("E2E_PORT", "8766")) + 30
    db = str(tmp_path / "restart.db")
    data = tmp_path / "data"
    data.mkdir()

    def boot():
        srv = LiveServer(db, port=port)
        monkeypatch.setattr(tempfile, "mkdtemp", lambda **kw: str(data))
        srv.start()
        monkeypatch.undo()
        return srv

    srv = boot()
    try:
        base = srv.url
        topic = page.request.post(f"{base}/api/triage", data={"query": "2401.00001"}).json()[
            "topic"
        ]
        assert page.request.post(
            f"{base}/api/library", data={"paper_id": "2401.00001", "topic": topic}
        ).ok
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(f"{base}/#/library/paper/2401.00001")
        expect(page.locator(".pdf-page")).to_have_count(3, timeout=20_000)
        expect(page.locator('.pdf-page[data-page="1"].has-text')).to_have_count(1, timeout=10_000)
        line(page, "Abstract").select_text()
        page.click("#pv-hl-btn")
        expect(hls(page).first).to_have_attribute("data-annotation-id", re.compile(r"^\d+$"))
        items(page).first.get_by_role("button", name="Add note").first.click()
        items(page).first.locator("textarea").fill("survives restart")
        items(page).first.locator("textarea").press("Control+Enter")
        expect(items(page).first.locator(".hl-item__note")).to_have_text("survives restart")
    finally:
        srv.data_dir = None  # keep the saved PDF for the second boot
        srv.stop()
    srv2 = boot()
    try:
        page.goto(f"{srv2.url}/#/library/paper/2401.00001")
        page.reload()
        expect(page.locator(".pdf-page")).to_have_count(3, timeout=20_000)
        expect(items(page)).to_have_count(1, timeout=10_000)
        expect(items(page).first.locator(".hl-item__note")).to_have_text("survives restart")
        expect(hls(page).first).to_be_attached()
    finally:
        srv2.data_dir = None
        srv2.stop()


def test_e2e_every_v3_view_makes_only_local_requests(app, real_library):
    """Zero non-local requests across triage, Library and Preview (offline_page asserts it)."""
    page = app
    page.goto("/")
    _triage_ui(page, "2401.00001", 1)
    save_btn(page, 1).click()
    expect(save_btn(page, 1)).to_have_text("Saved", timeout=10_000)
    page.click('nav.views a[data-view="library"]')
    rows(page).first.locator("button.open-preview").click()
    expect(page.locator(".pdf-page")).to_have_count(3, timeout=20_000)
    page.click("#pv-find-btn")
    find(page, "Quartzite")
    expect(page.locator("#pv-find-results .find-hit").first).to_be_visible()
