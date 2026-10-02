"""Real-browser specs for the v3 shell, Library routes and Preview (stubbed Library API).

Static files are the real app; `/api/library*` is stubbed per contracts/api.md (ptstubs).
Every case runs through `offline_page`: any non-local request fails the test.
"""

import json
import re
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
