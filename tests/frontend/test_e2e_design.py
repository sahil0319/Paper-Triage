"""Real-browser checks of the v4 Carbon look (T069): fonts, shell, nav, buttons and the query field.

Computed-style assertions against the live mock server; every case runs through `offline_page`,
which fails the test on any non-local request.
"""

import os
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

PRIMARY = "rgb(15, 98, 254)"
BORDER_STRONG = "rgb(141, 141, 141)"


def _css(page, selector, prop):
    return page.locator(selector).evaluate("(e, p) => getComputedStyle(e)[p]", prop)


def _box(page, selector):
    return page.locator(selector).bounding_box()


@pytest.fixture
def desktop(offline_page, live_server):
    live_server.set_triage_delay(0)
    offline_page.set_viewport_size({"width": 1440, "height": 900})
    offline_page.goto("/")
    expect(offline_page.locator("#submit")).to_be_visible()
    return offline_page


def test_body_uses_plex_sans_and_the_font_loads(desktop):
    page = desktop
    assert _css(page, "body", "fontFamily").startswith('"IBM Plex Sans"')
    loaded = page.evaluate(
        "document.fonts.ready.then(() => document.fonts.check('16px \"IBM Plex Sans\"'))"
    )
    assert loaded is True


def test_nav_is_48px_with_current_view_marked_by_weight_and_primary_rule(desktop):
    page = desktop
    assert abs(_box(page, ".global-nav")["height"] - 48) < 0.5
    current = 'nav a[data-view="triage"][aria-current="page"]'
    assert _css(page, current, "fontWeight") == "600"
    assert _css(page, current, "borderBottomWidth") == "2px"
    assert _css(page, current, "borderBottomColor") == PRIMARY
    other = 'nav a[data-view="library"]'
    assert _css(page, other, "fontWeight") == "400"
    assert _css(page, other, "color") == "rgb(82, 82, 82)"  # ink-muted
    assert _css(page, ".brand", "fontWeight") == "600"


def test_mock_badge_is_a_pill_with_an_info_outline(desktop):
    page = desktop
    expect(page.locator(".badge")).to_be_visible()
    assert _css(page, ".badge", "borderTopColor") == PRIMARY
    assert _css(page, ".badge", "color") == PRIMARY
    assert _css(page, ".badge", "borderTopLeftRadius") != "0px"
    assert _css(page, ".badge", "fontSize") == "12px"


def test_submit_is_a_square_48px_primary_button(desktop):
    page = desktop
    assert _css(page, "#submit", "backgroundColor") == PRIMARY
    assert _css(page, "#submit", "borderTopLeftRadius") == "0px"
    assert abs(_box(page, "#submit")["height"] - 48) < 0.5


def test_submit_goes_full_width_on_mobile(desktop):
    page = desktop
    page.set_viewport_size({"width": 390, "height": 844})
    submit = _box(page, "#submit")
    form = _box(page, "#triage-form")
    assert abs(submit["width"] - form["width"]) < 1
    assert abs(submit["height"] - 48) < 0.5


def test_query_is_a_carbon_field(desktop):
    page = desktop
    assert abs(_box(page, "#query")["height"] - 48) < 0.5
    assert _css(page, "#query", "borderBottomWidth") == "1px"
    assert _css(page, "#query", "borderBottomColor") == BORDER_STRONG
    assert _css(page, "#query", "borderTopWidth") == "0px"
    assert _css(page, "#query", "borderLeftWidth") == "0px"
    assert _css(page, "#query", "backgroundColor") == "rgb(244, 244, 244)"  # surface-1
    assert _css(page, "#query", "borderTopLeftRadius") == "0px"


def test_focus_ring_on_query_is_an_inset_2px_blue_outline(desktop):
    page = desktop
    page.focus("#query")
    page.keyboard.press("Shift+Tab")
    page.keyboard.press("Tab")
    assert _css(page, "#query", "outlineStyle") == "solid"
    assert _css(page, "#query", "outlineWidth") == "2px"
    assert _css(page, "#query", "outlineColor") == PRIMARY
    assert _css(page, "#query", "outlineOffset") == "-2px"


def test_buttons_follow_the_variant_table(desktop, live_server):
    page = desktop
    page.fill("#query", "diffusion distillation")
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(10, timeout=15_000)
    # Outline: Save is a 32px square outline button.
    save = "#paper-list li.paper >> nth=0 >> button.save"
    assert abs(_box(page, save)["height"] - 32) < 0.5
    assert _css(page, save, "borderTopLeftRadius") == "0px"
    assert _css(page, save, "borderTopColor") == BORDER_STRONG
    # Secondary (charcoal): Load 5 more.
    load_more = "#load-more"
    expect(page.locator(load_more)).to_be_visible()
    assert _css(page, load_more, "backgroundColor") == "rgb(57, 57, 57)"
    assert _css(page, load_more, "color") == "rgb(255, 255, 255)"
    assert abs(_box(page, load_more)["height"] - 40) < 0.5
    # Ghost: the external links are link-coloured with no fill.
    ext = "#paper-list li.paper >> nth=0 >> a.ext-link >> nth=0"
    assert _css(page, ext, "color") == PRIMARY
    assert _css(page, ext, "backgroundColor") == "rgba(0, 0, 0, 0)"


# ---- T070: result rows and results chat ----

TOPIC = "diffusion distillation"
MONO = '"IBM Plex Mono"'


def _search(page, query=TOPIC, rows=10):
    page.fill("#query", query)
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(rows, timeout=15_000)
    expect(page.locator("#submit")).to_be_enabled()


def _ask(page, question):
    count = page.locator("#chat-log li.turn").count()
    page.fill("#question", question)
    page.click("#ask")
    expect(page.locator("#chat-log li.turn")).to_have_count(count + 1)
    expect(page.locator("#ask")).to_be_enabled(timeout=10_000)
    return page.locator("#chat-log li.turn").last


def test_rank_numeral_and_meter(desktop):
    page = desktop
    _search(page)
    first = "#paper-list li.paper >> nth=0"
    assert _css(page, f"{first} >> .rank__n", "fontSize") == "32px"
    assert _css(page, f"{first} >> .rank__meter", "height") == "4px"
    assert _css(page, f"{first} >> .rank__meter", "borderTopLeftRadius") == "0px"
    assert _css(page, f"{first} >> .rank__of", "color") == "rgb(111, 111, 111)"  # ink-subtle
    assert _css(page, f"{first} >> .paper__title", "fontWeight") == "600"
    assert _css(page, f"{first} >> .paper__reason", "fontSize") == "16px"
    assert _css(page, f"{first} >> .paper__id", "fontFamily").startswith(MONO)
    page.set_viewport_size({"width": 390, "height": 844})
    assert _css(page, f"{first} >> .rank__n", "fontSize") == "24px"
    assert abs(_box(page, f"{first} >> .rank__meter")["width"] - 32) < 0.5


def test_rows_are_separated_by_a_subtle_top_rule(desktop):
    page = desktop
    _search(page)
    second = "#paper-list li.paper >> nth=1"
    assert _css(page, second, "borderTopWidth") == "1px"
    assert _css(page, second, "borderTopColor") == "rgb(224, 224, 224)"
    assert _css(page, "#paper-list li.paper >> nth=0", "borderTopWidth") == "0px"
    assert _css(page, second, "paddingTop") == "24px"
    assert _css(page, second, "gridTemplateColumns").split(" ")[0] == "72px"
    page.set_viewport_size({"width": 390, "height": 844})
    assert _css(page, second, "paddingTop") == "16px"
    assert _css(page, second, "gridTemplateColumns").split(" ")[0] == "56px"


def test_critique_panel_is_a_square_layer(desktop):
    page = desktop
    _search(page)
    row = "#paper-list li.paper >> nth=0"
    page.locator(f"{row} >> .disclosure summary").click()
    assert _css(page, f"{row} >> .critique", "backgroundColor") == "rgb(244, 244, 244)"
    assert _css(page, f"{row} >> .critique", "borderTopLeftRadius") == "0px"
    assert _css(page, f"{row} >> .disclosure summary", "fontWeight") == "600"


def test_saved_row_uses_a_grey_fill_without_border(offline_page, live_server):
    from ptstubs import LibraryStub

    live_server.set_triage_delay(0)
    page = offline_page
    LibraryStub(page, [])
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto("/")
    _search(page)
    saved = page.locator('[id="paper-2401.00001"] button.save')
    saved.click()
    expect(saved).to_have_attribute("aria-pressed", "true")
    page.mouse.move(0, 0)  # leave the hover state; transitions are 110ms
    expect(saved).to_have_css("background-color", "rgb(224, 224, 224)")
    expect(saved).to_have_css("border-top-color", "rgba(0, 0, 0, 0)")
    unsaved = page.locator('button.save[aria-pressed="false"]').first
    assert abs(unsaved.bounding_box()["height"] - 32) < 0.5


def test_cite_chip_is_mono_on_a_grey_chip(desktop):
    page = desktop
    _search(page)
    title = page.locator('[id="paper-2401.00002"] .paper__title').inner_text()
    import re

    word = next(w for w in re.findall(r"[A-Za-z]+", title) if len(w) >= 6)
    turn = _ask(page, f"{word}?")
    cite = turn.locator("a.cite").first
    expect(cite).to_be_visible()
    assert cite.evaluate("e => getComputedStyle(e).fontFamily").startswith(MONO)
    assert cite.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(224, 224, 224)"
    assert cite.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "2px"


def test_refusal_is_an_info_notification(desktop):
    page = desktop
    _search(page)
    turn = _ask(page, "What is the capital of France?")
    refused = turn.locator(".turn__a--refused")
    expect(refused).to_be_visible()
    assert refused.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(237, 245, 255)"
    assert refused.evaluate("e => getComputedStyle(e).borderLeftWidth") == "3px"
    assert refused.evaluate("e => getComputedStyle(e).borderLeftColor") == PRIMARY
    assert refused.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"


def test_chat_panel_is_a_square_layer_with_canvas_field(desktop):
    page = desktop
    _search(page)
    assert _css(page, ".chat", "backgroundColor") == "rgb(244, 244, 244)"
    assert _css(page, ".chat", "borderTopLeftRadius") == "0px"
    assert _css(page, ".chat", "borderTopWidth") == "0px"
    assert _css(page, ".chat h2", "fontSize") == "20px"
    assert _css(page, "#question", "backgroundColor") == "rgb(255, 255, 255)"
    assert abs(_box(page, "#ask")["height"] - 40) < 0.5


# ---- T071: Library view ----


@pytest.fixture
def library(offline_page, live_server):
    from ptstubs import LibraryStub, lib_item

    live_server.set_triage_delay(0)
    page = offline_page
    LibraryStub(page, [lib_item(1), lib_item(2)])
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto("/#/library")
    expect(page.locator(".lib-row")).to_have_count(2)
    return page


def test_current_rail_item_is_selected_with_a_primary_bar(library):
    page = library
    item = '#dir-rail .rail__item[aria-current="true"]'
    assert _css(page, item, "fontWeight") == "600"
    shadow = _css(page, item, "boxShadow")
    assert PRIMARY in shadow and "3px 0px 0px 0px inset" in shadow
    assert _css(page, item, "backgroundColor") == "rgb(224, 224, 224)"  # surface-selected
    assert abs(_box(page, item)["height"] - 32) < 0.5


def test_pressed_tag_is_inverse(library):
    page = library
    tag = page.locator("#lib-tags button.tag").first
    tag.click()
    page.mouse.move(0, 0)
    expect(tag).to_have_attribute("aria-pressed", "true")
    expect(tag).to_have_css("background-color", "rgb(22, 22, 22)")
    expect(tag).to_have_css("color", "rgb(255, 255, 255)")
    assert abs(tag.bounding_box()["height"] - 32) < 0.5
    assert tag.evaluate("e => getComputedStyle(e).borderTopLeftRadius") != "0px"


def test_row_select_is_a_32px_carbon_select(library):
    page = library
    select = page.locator('.lib-row select[data-act="move"]').first
    assert abs(select.bounding_box()["height"] - 32) < 0.5
    assert select.evaluate("e => getComputedStyle(e).appearance") == "none"
    assert select.evaluate("e => getComputedStyle(e).backgroundImage").startswith("url(")
    assert select.evaluate("e => getComputedStyle(e).borderTopWidth") == "0px"
    assert select.evaluate("e => getComputedStyle(e).borderBottomWidth") == "1px"


def test_row_removal_does_not_transition_height(library):
    page = library
    prop = _css(page, ".lib-row >> nth=0", "transitionProperty")
    assert "height" not in prop


def test_library_filter_field_is_carbon(library):
    page = library
    field = page.locator("#lib-title-filter, .lib-filter input[type=search]").first
    assert abs(field.bounding_box()["height"] - 40) < 0.5
    assert field.evaluate("e => getComputedStyle(e).borderTopWidth") == "0px"
    assert field.evaluate("e => getComputedStyle(e).borderBottomColor") == BORDER_STRONG


# ---- T072: Preview toolbar, well, highlights and popover ----

HL_FILLS = {
    "yellow": "rgb(255, 222, 102)",
    "mint": "rgb(159, 224, 192)",
    "peach": "rgb(255, 194, 158)",
}


@pytest.fixture
def pv(offline_page, live_server):
    from test_e2e_library import hl_preview

    live_server.set_triage_delay(0)
    hl_preview(offline_page)
    return offline_page


def test_toolbar_controls_are_40px_and_square(pv):
    page = pv
    controls = page.locator("#pv-controls button, #pv-controls select, #pv-controls input")
    seen = 0
    for i in range(controls.count()):
        c = controls.nth(i)
        if not c.is_visible():
            continue
        seen += 1
        assert abs(c.bounding_box()["height"] - 40) < 1, c.get_attribute("id")
        assert c.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"
    assert seen >= 8
    # Row 1 actions are controls too (F-022), at desktop and mobile widths.
    for width in (1440, 820, 390):
        page.set_viewport_size({"width": width, "height": 900})
        for sel in ("#pv-export", "#pv-external"):
            box = page.locator(sel).bounding_box()
            assert abs(box["height"] - 40) < 1, (width, sel, box["height"])
    page.set_viewport_size({"width": 1440, "height": 900})
    title = page.locator("#preview-heading")
    assert title.evaluate("e => getComputedStyle(e).fontWeight") == "600"
    assert title.evaluate("e => getComputedStyle(e).fontSize") == "16px"


def test_highlight_button_and_color_select_share_one_edge(pv):
    page = pv
    btn = page.locator("#pv-hl-btn").bounding_box()
    sel = page.locator("#pv-hl-color").bounding_box()
    assert abs((btn["x"] + btn["width"]) - sel["x"]) <= 1.5
    assert page.locator("#pv-hl-color").evaluate("e => getComputedStyle(e).appearance") == "none"


@pytest.mark.parametrize("color", ["yellow", "mint", "peach"])
def test_highlights_are_opaque_fills_with_multiply(pv, color):
    from test_e2e_library import drag_select, hls

    page = pv
    drag_select(page, "Abstract")
    page.locator(f'#pv-popover button.swatch[aria-label="Highlight {color}"]').click()
    # The optimistic node (tmp-N) is swapped for the persisted one: wait for the saved id, then
    # measure that node (F-012, F-023).
    expect(hls(page).first).to_have_attribute("data-annotation-id", re.compile(r"^\d+$"))
    hl = hls(page).first
    expect(hl).to_have_css("background-color", HL_FILLS[color])
    assert hl.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "2px"
    layer = page.locator('.pdf-page[data-page="1"] .hl-layer')
    assert layer.evaluate("e => getComputedStyle(e).mixBlendMode") == "multiply"
    item = page.locator("#pv-hl-list li.hl-item[data-annotation-id]").first
    expect(item.locator(".hl-item__kind")).to_have_text(color.capitalize())  # SC-019: named
    assert (
        item.locator(".hl-item__quote").evaluate("e => getComputedStyle(e).borderLeftWidth")
        == "3px"
    )
    assert (
        item.locator(".hl-item__quote").evaluate("e => getComputedStyle(e).borderLeftColor")
        == HL_FILLS[color]
    )
    dot = item.locator(".dot")
    assert dot.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "50%"


def test_pdf_pages_have_a_page_edge_and_no_shadow(pv):
    page = pv
    p1 = page.locator("section.pdf-page").first
    for side in ("Top", "Right", "Bottom", "Left"):
        assert p1.evaluate(f"e => getComputedStyle(e).border{side}Width") == "1px"
        assert p1.evaluate(f"e => getComputedStyle(e).border{side}Color") == "rgb(198, 198, 198)"
    assert p1.evaluate("e => getComputedStyle(e).boxShadow") == "none"
    assert page.locator("#pv-pages").evaluate("e => getComputedStyle(e).backgroundColor") == (
        "rgb(224, 224, 224)"
    )


def test_popover_is_a_square_overlay_with_round_swatches(pv):
    from test_e2e_library import drag_select

    page = pv
    drag_select(page, "Abstract")
    pop = page.locator("#pv-popover")
    expect(pop).to_be_visible()
    assert pop.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"
    assert pop.evaluate("e => getComputedStyle(e).boxShadow") != "none"
    assert pop.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
    for sw in pop.locator("button.swatch").all():
        assert sw.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "50%"


def test_find_field_is_carbon_and_hover_fill_is_surface_hover(pv):
    page = pv
    page.click("#pv-find-btn")
    field = page.locator("#pv-find-input")
    expect(field).to_be_visible()
    assert abs(field.bounding_box()["height"] - 40) < 1
    assert field.evaluate("e => getComputedStyle(e).borderTopWidth") == "0px"
    assert field.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(244, 244, 244)"


# ---- T073: Preview side panel, notes, Ask this paper and the bottom sheet ----


def _open_preview(page, width, height=900, wait_pages=True, **item_kw):
    from ptstubs import lib_item
    from test_e2e_library import preview

    chat_calls = []
    page.on(
        "request",
        lambda r: chat_calls.append(r.url) if r.url.endswith("/api/paper-chat") else None,
    )
    preview(page, [lib_item(item_kw.pop("n", 1), **item_kw)])
    page.set_viewport_size({"width": width, "height": height})
    if wait_pages:
        expect(page.locator(".pdf-page")).to_have_count(3)
    else:
        expect(page.locator("#pv-panel")).to_be_visible()
    return chat_calls


def test_selected_tab_is_ask_this_paper_with_primary_rule_and_no_chat_request(
    offline_page, live_server
):
    live_server.set_triage_delay(0)
    page = offline_page
    calls = _open_preview(page, 1440)
    tab = page.locator('#pv-panel [role="tab"][aria-selected="true"]')
    expect(tab).to_have_text("Ask this paper")
    assert tab.evaluate("e => getComputedStyle(e).fontWeight") == "600"
    assert tab.evaluate("e => getComputedStyle(e).borderBottomWidth") == "2px"
    assert tab.evaluate("e => getComputedStyle(e).borderBottomColor") == PRIMARY
    assert abs(tab.bounding_box()["height"] - 40) < 1.5
    panel = page.locator("#pv-panel")
    assert panel.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(244, 244, 244)"
    assert panel.evaluate("e => getComputedStyle(e).borderLeftColor") == "rgb(198, 198, 198)"
    page.wait_for_timeout(300)
    assert calls == []


def test_notes_field_is_canvas_on_the_panel(offline_page, live_server):
    from test_e2e_library import hl_tab

    live_server.set_triage_delay(0)
    page = offline_page
    _open_preview(page, 1440)
    hl_tab(page)
    page.click("#pv-note-add")
    area = page.locator(".note-editor textarea").first
    expect(area).to_be_visible()
    assert area.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
    assert area.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"
    assert area.evaluate("e => getComputedStyle(e).borderTopWidth") == "0px"
    assert area.evaluate("e => getComputedStyle(e).borderBottomColor") == BORDER_STRONG


def test_sheet_is_square_overlay_opening_on_ask_this_paper(offline_page, live_server):
    live_server.set_triage_delay(0)
    page = offline_page
    calls = _open_preview(page, 390, 844)
    page.click("#pv-sheet-open")
    sheet = page.locator("#pv-sheet")
    expect(sheet).to_be_visible()
    expect(sheet.locator('[role="tab"][aria-selected="true"]')).to_have_text("Ask this paper")
    assert sheet.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"
    assert sheet.evaluate("e => getComputedStyle(e).boxShadow") != "none"
    assert sheet.evaluate("e => getComputedStyle(e, '::backdrop').backgroundColor") == (
        "rgba(22, 22, 22, 0.5)"
    )
    assert sheet.evaluate("e => getComputedStyle(e).animationTimingFunction") == (
        "cubic-bezier(0, 0, 0.38, 0.9)"
    )
    assert calls == []


def test_no_pdf_note_is_an_info_notification(offline_page, live_server):
    live_server.set_triage_delay(0)
    page = offline_page
    _open_preview(
        page,
        1440,
        wait_pages=False,
        n=5,
        pdf={"status": "failed", "error": "Not a PDF.", "pages": None},
    )
    note = page.locator("#pv-chat-nopdf")
    expect(note).to_be_visible()
    assert note.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(237, 245, 255)"
    assert note.evaluate("e => getComputedStyle(e).borderLeftWidth") == "3px"
    assert note.evaluate("e => getComputedStyle(e).borderLeftColor") == PRIMARY
    assert note.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"


# ---- T074: states (working card, notes, alert, empty), previous results, flashes ----


def test_previous_results_stay_at_full_opacity_and_clickable_during_a_second_search(
    offline_page, live_server
):
    from ptstubs import LibraryStub

    LibraryStub(offline_page, [])
    page = offline_page
    live_server.set_triage_delay(0)
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto("/")
    _search(page)
    held = []
    page.route("**/api/triage", lambda route: held.append(route))
    page.fill("#query", "2401.00001")
    page.click("#submit")
    expect(page.locator("#working")).to_be_visible(timeout=3_000)
    rows = page.locator("#paper-list li.paper")
    assert rows.count() == 10
    for i in range(rows.count()):
        assert rows.nth(i).evaluate("e => getComputedStyle(e).opacity") == "1"
    first = rows.first
    first.locator('a[data-link="abs"]').click(trial=True)
    first.locator("button.save").click()
    expect(first.locator("button.save")).to_have_attribute("aria-pressed", "true")
    # Release so the server-side request completes cleanly.
    held[0].continue_()
    expect(page.locator("#paper-list li.paper")).to_have_count(1, timeout=15_000)


def test_working_card_is_a_square_grey_layer_in_normal_flow(offline_page, live_server):
    page = offline_page
    live_server.set_triage_delay(1.5)
    try:
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto("/")
        page.fill("#query", TOPIC)
        page.click("#submit")
        expect(page.locator("#working")).to_be_visible(timeout=3_000)
        assert _css(page, "#working", "backgroundColor") == "rgb(244, 244, 244)"
        assert _css(page, "#working", "borderTopLeftRadius") == "0px"
        assert _css(page, "#working", "paddingTop") == "24px"
        assert _css(page, "#working", "position") == "static"
        assert _css(page, "#working .working__verb", "fontWeight") == "600"
        expect(page.locator("#working")).to_be_hidden(timeout=10_000)
    finally:
        live_server.set_triage_delay(0)


def test_a_failed_load_shows_a_light_error_notification(desktop):
    page = desktop
    page.route(
        "**/api/triage",
        lambda route: route.fulfill(
            status=502, content_type="application/json", body='{"detail": "upstream down"}'
        ),
    )
    page.fill("#query", TOPIC)
    page.click("#submit")
    alert = page.locator("#alert")
    expect(alert).to_be_visible(timeout=5_000)
    assert _css(page, "#alert", "backgroundColor") == "rgb(255, 241, 241)"
    assert _css(page, "#alert", "borderLeftColor") == "rgb(218, 30, 40)"
    assert _css(page, "#alert", "borderLeftWidth") == "3px"
    assert _css(page, "#alert .alert__title", "color") == "rgb(22, 22, 22)"
    retry = alert.locator("button.btn")
    expect(retry).to_be_visible()
    assert _css(page, "#alert button.btn", "backgroundColor") == "rgb(57, 57, 57)"
    for link in alert.locator(".ext-link").all():
        assert link.evaluate("e => getComputedStyle(e).backgroundColor") == "rgba(0, 0, 0, 0)"
        assert link.evaluate("e => getComputedStyle(e).color") == PRIMARY


def test_empty_state_title_body_and_chips(offline_page, live_server):
    page = offline_page
    live_server.set_triage_delay(0)
    # The shared server may hold papers from earlier tests: serve an empty store for this page.
    page.route(
        "**/api/papers",
        lambda route: route.fulfill(
            status=200, content_type="application/json", body='{"results": [], "notes": []}'
        ),
    )
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto("/")
    expect(page.locator("#empty")).to_be_visible()
    assert _css(page, ".empty__title", "fontWeight") == "600"
    assert _css(page, ".empty__title", "fontSize") == "16px"
    assert _css(page, ".empty__body", "color") == "rgb(82, 82, 82)"
    assert _css(page, ".empty__body", "fontSize") == "16px"
    chip = page.locator("#empty .chips button").first
    assert abs(chip.bounding_box()["height"] - 32) < 0.5
    assert chip.evaluate("e => getComputedStyle(e).borderTopColor") == BORDER_STRONG


def _cite_and_load_more(page):
    """Cite click -> .paper--cited, then Load 5 more -> .paper--new rows."""
    _search(page)
    turn = _ask(page, "Which paper is about diffusion?")
    cite = turn.locator("a.cite:not(.cite--off), button.cite:not(.cite--off)").first
    expect(cite).to_be_visible()
    cite.click()
    expect(page.locator("#paper-list li.paper.paper--cited")).to_have_count(1)
    page.click("#load-more")
    expect(page.locator("#paper-list li.paper.paper--new").first).to_be_visible(timeout=15_000)


def test_cited_and_new_rows_fade_info_surface_over_the_flash_token(desktop):
    page = desktop
    _cite_and_load_more(page)
    cited = page.locator("#paper-list li.paper--cited").first
    new = page.locator("#paper-list li.paper--new").first
    for row, name in ((cited, "cited-flash"), (new, "new-flash")):
        assert row.evaluate("e => getComputedStyle(e).animationName") == name
        assert row.evaluate("e => getComputedStyle(e).animationDuration") == "1.6s"


def test_reduced_motion_replaces_flashes_with_static_markers(offline_page, live_server):
    page = offline_page
    live_server.set_triage_delay(0)
    page.emulate_media(reduced_motion="reduce")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto("/")
    _cite_and_load_more(page)
    cited = page.locator("#paper-list li.paper--cited").first
    new = page.locator("#paper-list li.paper--new").first
    assert cited.evaluate("e => getComputedStyle(e).animationName") == "none"
    assert cited.evaluate("e => getComputedStyle(e).outlineStyle") == "solid"
    assert cited.evaluate("e => getComputedStyle(e).outlineWidth") == "2px"
    assert cited.evaluate("e => getComputedStyle(e).outlineColor") == PRIMARY
    assert new.evaluate("e => getComputedStyle(e).animationName") == "none"
    assert new.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(237, 245, 255)"
    # No running animation anywhere in the results list.
    assert (
        page.evaluate("document.querySelector('#paper-list').getAnimations({subtree: true}).length")
        == 0
    )
    # Chevron does not rotate over time: disclosure open has no transition.
    chev = page.locator("#paper-list summary .chev").first
    assert chev.evaluate("e => getComputedStyle(e).transitionDuration") in ("0s", "0s, 0s")


def test_reduced_motion_working_glyph_is_static_with_full_opacity_rays(offline_page, live_server):
    page = offline_page
    live_server.set_triage_delay(1.5)
    try:
        page.emulate_media(reduced_motion="reduce")
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto("/")
        page.fill("#query", TOPIC)
        page.click("#submit")
        expect(page.locator("#working")).to_be_visible(timeout=3_000)
        assert (
            page.evaluate(
                "document.querySelector('#working').getAnimations({subtree: true}).length"
            )
            == 0
        )
        assert _css(page, "#working .ray >> nth=0", "opacity") == "1"
        expect(page.locator("#working")).to_be_hidden(timeout=10_000)
    finally:
        live_server.set_triage_delay(0)


def test_forced_colours_keep_borders_on_controls_notifications_and_chips(offline_page, live_server):
    page = offline_page
    live_server.set_triage_delay(0)
    page.emulate_media(forced_colors="active")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto("/")
    assert _css(page, "#submit", "borderTopStyle") == "solid"
    assert _css(page, "#submit", "borderTopWidth") == "1px"
    assert _css(page, "#query", "borderTopStyle") == "solid"
    _search(page)
    turn = _ask(page, "Which paper is about diffusion?")
    cite = turn.locator(".cite").first
    assert cite.evaluate("e => getComputedStyle(e).borderTopStyle") == "solid"
    assert cite.evaluate("e => getComputedStyle(e).borderTopWidth") == "1px"
    meter = page.locator(".rank__meter span").first
    assert meter.evaluate("e => getComputedStyle(e).backgroundColor") != "rgba(0, 0, 0, 0)"
    refused = _ask(page, "What is the capital of France?")
    note = page.locator(".turn__a--refused").first
    expect(note).to_be_visible()
    assert note.evaluate("e => getComputedStyle(e).borderTopStyle") == "solid"
    assert refused


def test_reduced_motion_sheet_opens_without_sliding(offline_page, live_server):
    live_server.set_triage_delay(0)
    page = offline_page
    page.emulate_media(reduced_motion="reduce")
    _open_preview(page, 390, 844)
    page.click("#pv-sheet-open")
    sheet = page.locator("#pv-sheet")
    expect(sheet).to_be_visible()
    assert sheet.evaluate("e => getComputedStyle(e).animationName") == "none"
    assert sheet.evaluate("e => e.getAnimations().length") == 0


def test_forced_colours_sheet_popover_and_highlights_keep_edges(offline_page, live_server):
    live_server.set_triage_delay(0)
    page = offline_page
    page.emulate_media(forced_colors="active")
    _open_preview(page, 390, 844)
    page.click("#pv-sheet-open")
    sheet = page.locator("#pv-sheet")
    expect(sheet).to_be_visible()
    assert sheet.evaluate("e => getComputedStyle(e).borderTopStyle") == "solid"
    assert sheet.evaluate("e => getComputedStyle(e).borderTopWidth") == "1px"


# ---- T076: design sweep at 390, 820 and 1440 (SC-017..SC-022) ----
#
# F-016 (drag selection keeps popover and the new .hl covers the selected words) is covered by the
# "F-016" block in test_e2e_library.py, F-017 by test_old_results_stay_interactive_during_a_new_search
# (test_e2e_browser.py) and the previous-results test above, F-019 by the selected-tab and sheet
# tests above. `pytest -m e2e` runs them together with this sweep.

WIDTHS = (390, 820, 1440)
HEIGHTS = {390: 844, 820: 1100, 1440: 900}


@pytest.fixture(scope="session")
def shots_dir(tmp_path_factory):
    env = os.environ.get("V4_SHOTS_DIR")
    path = Path(env) if env else tmp_path_factory.mktemp("v4-shots")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _size(page, width):
    page.set_viewport_size({"width": width, "height": HEIGHTS[width]})


def _triage(page, live_server, width):
    from ptstubs import LibraryStub, lib_item

    live_server.set_triage_delay(0)
    LibraryStub(page, [lib_item(1), lib_item(2)])
    _size(page, width)
    page.goto("/")
    expect(page.locator("#submit")).to_be_visible()


def _triage_with_chat(page, live_server, width):
    _triage(page, live_server, width)
    _search(page)
    _ask(page, "Which paper is about diffusion?")
    _ask(page, "What is the capital of France?")
    expect(page.locator(".turn__a--refused")).to_have_count(1)


def _library(page, live_server, width):
    from ptstubs import LibraryStub, lib_item

    live_server.set_triage_delay(0)
    LibraryStub(page, [lib_item(1), lib_item(2)])
    _size(page, width)
    page.goto("/#/library")
    expect(page.locator(".lib-row")).to_have_count(2)


def _preview_open(page, live_server, width):
    live_server.set_triage_delay(0)
    _open_preview(page, width, HEIGHTS[width])
    if width < 1024:
        page.click("#pv-sheet-open")
        sheet = page.locator("#pv-sheet")
        expect(sheet).to_be_visible()
        sheet.evaluate("e => Promise.all(e.getAnimations().map(a => a.finished))")


def _all_fonts_ready(page, spec='12px "IBM Plex Mono"'):
    page.wait_for_function(
        "spec => document.fonts.ready.then(() => document.fonts.check(spec))", arg=spec
    )


CONTRAST_JS = """
({selector, kind}) => {
  const parse = (c) => {
    let m = c.match(/^rgba?\\(([^)]+)\\)/);
    if (m) {
      const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
      return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
    }
    m = c.match(/^color\\(srgb ([^)]+)\\)/);
    if (m) {
      const p = m[1].split(/[ /]+/).filter(Boolean).map(Number);
      return [p[0] * 255, p[1] * 255, p[2] * 255, p.length > 3 ? p[3] : 1];
    }
    return [0, 0, 0, 0];
  };
  const over = (top, bottom) => {
    const a = top[3];
    return [0, 1, 2].map((i) => top[i] * a + bottom[i] * (1 - a)).concat([1]);
  };
  const backdrop = (el) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c[3] > 0) layers.push(c);
      if (c[3] >= 1) break;
    }
    let acc = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc);
    return acc;
  };
  const lum = (c) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  const out = [];
  for (const el of document.querySelectorAll(selector)) {
    if (!el.getClientRects().length) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden') continue;
    if (kind === 'text') {
      const bg = backdrop(el);
      out.push(ratio(over(parse(cs.color), bg), bg));
    } else {
      const bg = backdrop(el.parentElement);
      const edge = parse(kind === 'edge-bottom' ? cs.borderBottomColor : cs.borderTopColor);
      out.push(ratio(over(edge, bg), bg));
    }
  }
  return out;
}
"""


def _contrast(page, selector, kind="text"):
    return page.evaluate(CONTRAST_JS, {"selector": selector, "kind": kind})


def _assert_contrast(page, checks):
    """checks: (selector, minimum[, kind]). Every visible match must meet the minimum, and one must exist."""
    for check in checks:
        selector, minimum, *rest = check
        ratios = _contrast(page, selector, rest[0] if rest else "text")
        assert ratios, f"no visible element for {selector}"
        assert min(ratios) >= minimum, (selector, minimum, sorted(ratios)[:3])


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("view", ["triage", "library", "preview"])
def test_views_make_no_remote_requests_and_serve_woff2(offline_page, live_server, view, width):
    page = offline_page
    fonts = []
    page.on(
        "response",
        lambda r: (
            fonts.append((r.url, r.headers.get("content-type", "")))
            if "/vendor/fonts/" in r.url and r.url.endswith(".woff2")
            else None
        ),
    )
    if view == "triage":
        _triage(page, live_server, width)
        _search(page)
        expect(page.locator(".paper__id").first).to_be_visible()
    elif view == "library":
        _library(page, live_server, width)
    else:
        _preview_open(page, live_server, width)
    _all_fonts_ready(page)
    assert page.evaluate("document.fonts.check('16px \"IBM Plex Sans\"')") is True
    assert fonts, "expected at least one vendored woff2 response"
    for url, ctype in fonts:
        assert ctype == "font/woff2", (url, ctype)
    # offline_page itself fails the test on any non-local request.


@pytest.mark.parametrize("width", WIDTHS)
def test_triage_text_contrast_and_control_edges(offline_page, live_server, width):
    page = offline_page
    _triage_with_chat(page, live_server, width)
    _assert_contrast(
        page,
        [
            (".paper__title", 4.5),
            (".paper__reason", 4.5),
            (".paper__authors", 4.5),
            (".rank__of", 4.5),
            (".paper__id", 4.5),
            ("a[data-link]", 4.5),
            (".views a[aria-current='page']", 4.5),
            (".views a:not([aria-current])", 4.5),
            (".turn__a", 4.5),
            (".turn__a--refused", 4.5),
            ("a.cite", 4.5),
            (".views__count", 4.5),
            (".rank__n", 3),
            ("#query", 3, "edge-bottom"),
            ("button.save", 3, "edge"),
        ],
    )


@pytest.mark.parametrize("width", WIDTHS)
def test_error_notification_text_contrast(offline_page, live_server, width):
    page = offline_page
    _triage(page, live_server, width)
    page.route(
        "**/api/triage",
        lambda route: route.fulfill(
            status=502, content_type="application/json", body='{"detail": "upstream down"}'
        ),
    )
    page.fill("#query", TOPIC)
    page.click("#submit")
    expect(page.locator("#alert")).to_be_visible(timeout=5_000)
    _assert_contrast(page, [(".alert", 4.5), (".alert__title", 4.5), (".alert__detail", 4.5)])


@pytest.mark.parametrize("width", WIDTHS)
def test_library_text_contrast_and_tag_edge(offline_page, live_server, width):
    page = offline_page
    _library(page, live_server, width)
    _assert_contrast(
        page,
        [
            (".lib-saved", 4.5),
            (".views__count", 4.5),
            (".views a[aria-current='page']", 4.5),
            (".tag", 4.5),
            (".tag", 3, "edge"),
        ],
    )


@pytest.mark.parametrize("width", WIDTHS)
def test_preview_tabs_contrast(offline_page, live_server, width):
    page = offline_page
    _preview_open(page, live_server, width)
    _assert_contrast(page, [(".pv-tab", 4.5)])
    # Selected and unselected tabs are both measured.
    assert page.locator('.pv-tab[aria-selected="true"]:visible').count() == 1
    assert page.locator('.pv-tab[aria-selected="false"]:visible').count() >= 1


@pytest.mark.parametrize("width", WIDTHS)
def test_tab_to_submit_shows_a_2px_blue_focus_ring(offline_page, live_server, width):
    page = offline_page
    _triage(page, live_server, width)
    page.focus("#query")
    page.keyboard.press("Tab")
    expect(page.locator("#submit")).to_be_focused()
    assert _css(page, "#submit", "outlineWidth") == "2px"
    assert _css(page, "#submit", "outlineStyle") == "solid"
    assert _css(page, "#submit", "outlineColor") == PRIMARY


ANIMATED_JS = """
sel => document.getAnimations().filter(a => {
  const t = a.effect && a.effect.target;
  return t && t.closest && t.closest(sel);
}).length
"""
MOTION_TARGETS = ".paper--cited, .paper--new, #paper-list details.disclosure, #pv-sheet"


@pytest.mark.parametrize("width", WIDTHS)
def test_reduced_motion_leaves_no_animations_and_keeps_static_markers(
    offline_page, live_server, width
):
    page = offline_page
    live_server.set_triage_delay(0)
    page.emulate_media(reduced_motion="reduce")
    _size(page, width)
    page.goto("/")
    _cite_and_load_more(page)
    first = page.locator("#paper-list li.paper").first
    first.locator("details.disclosure summary").click()
    expect(first.locator("details.disclosure")).to_have_attribute("open", "")
    assert page.evaluate(ANIMATED_JS, MOTION_TARGETS) == 0
    cited = page.locator("#paper-list li.paper--cited").first
    new = page.locator("#paper-list li.paper--new").first
    assert cited.evaluate("e => getComputedStyle(e).outlineWidth") == "2px"
    assert cited.evaluate("e => getComputedStyle(e).outlineColor") == PRIMARY
    assert new.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(237, 245, 255)"


@pytest.mark.parametrize("width", (390, 820))
def test_reduced_motion_sheet_has_no_animations(offline_page, live_server, width):
    page = offline_page
    live_server.set_triage_delay(0)
    page.emulate_media(reduced_motion="reduce")
    _open_preview(page, width, HEIGHTS[width])
    page.click("#pv-sheet-open")
    expect(page.locator("#pv-sheet")).to_be_visible()
    assert page.evaluate(ANIMATED_JS, MOTION_TARGETS) == 0


@pytest.mark.parametrize("width", WIDTHS)
def test_forced_colours_show_borders_on_submit_and_cites(offline_page, live_server, width):
    page = offline_page
    live_server.set_triage_delay(0)
    page.emulate_media(forced_colors="active")
    _triage(page, live_server, width)
    _search(page)
    _ask(page, "Which paper is about diffusion?")
    for sel in ("#submit", ".cite"):
        style = page.locator(sel).first.evaluate(
            "e => { const s = getComputedStyle(e); return [s.borderTopColor, s.borderTopWidth, s.borderTopStyle]; }"
        )
        assert style[0] != "rgba(0, 0, 0, 0)", (sel, style)
        assert style[1] != "0px" and style[2] != "none", (sel, style)


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("view", ["triage", "library", "preview"])
def test_screenshots_of_triage_library_and_preview(
    offline_page, live_server, shots_dir, view, width
):
    page = offline_page
    if view == "triage":
        _triage(page, live_server, width)
        _search(page)
        _ask(page, "Which paper is about diffusion?")
        _all_fonts_ready(page)
        page.screenshot(path=str(shots_dir / f"triage-{width}.png"), full_page=True)
    elif view == "library":
        _library(page, live_server, width)
        _all_fonts_ready(page, '16px "IBM Plex Sans"')
        page.screenshot(path=str(shots_dir / f"library-{width}.png"), full_page=True)
    else:
        _preview_open(page, live_server, width)  # panel at 1440, bottom sheet below 1024
        _all_fonts_ready(page, '16px "IBM Plex Sans"')
        page.screenshot(path=str(shots_dir / f"preview-{width}.png"))
    shot = shots_dir / f"{view}-{width}.png"
    assert shot.exists() and shot.stat().st_size > 5_000


def test_sheet_notes_field_is_a_surface_1_field(offline_page, live_server):
    from test_e2e_library import drag_select

    live_server.set_triage_delay(0)
    page = offline_page
    _open_preview(page, 800, 900)
    expect(page.locator('.pdf-page[data-page="1"].has-text')).to_have_count(1, timeout=10_000)
    drag_select(page, "Abstract")
    page.locator("#pv-popover").get_by_role("button", name="Add note").click()
    area = page.locator("#pv-sheet textarea")
    expect(area).to_be_focused()
    assert area.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(244, 244, 244)"
    assert area.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"
    assert area.evaluate("e => getComputedStyle(e).borderBottomColor") == BORDER_STRONG


def test_no_text_page_note_is_an_info_notification(offline_page, live_server):
    from ptstubs import lib_item
    from test_e2e_library import _blank_pdf, preview

    live_server.set_triage_delay(0)
    page = offline_page
    preview(
        page, [lib_item(1, pdf={"status": "ready", "error": None, "pages": 1})], pdf=_blank_pdf()
    )
    note = page.locator(".pdf-page__notext")
    expect(note).to_contain_text("No selectable text on this page.", timeout=10_000)
    assert note.evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(237, 245, 255)"
    assert note.evaluate("e => getComputedStyle(e).borderLeftColor") == PRIMARY
    assert note.evaluate("e => getComputedStyle(e).borderLeftWidth") == "3px"
    assert note.evaluate("e => getComputedStyle(e).borderTopLeftRadius") == "0px"


# ---- v4 audit fixes ----


@pytest.mark.parametrize("hover", [False, True])
def test_rail_count_meets_aa_on_current_and_hovered_items(offline_page, live_server, hover):
    page = offline_page
    _library(page, live_server, 1440)
    _assert_contrast(page, [("#dir-rail .rail__item[aria-current='true'] .rail__count", 4.5)])
    if hover:
        page.locator("#dir-rail .rail__item:not([aria-current='true'])").first.hover()
        _assert_contrast(page, [("#dir-rail .rail__item:hover .rail__count", 4.5)])


def test_forced_colours_underline_only_the_current_nav_link_and_tab(offline_page, live_server):
    page = offline_page
    live_server.set_triage_delay(0)
    page.emulate_media(forced_colors="active")
    _triage(page, live_server, 1440)

    def edge(selector):
        return page.locator(selector).first.evaluate(
            "e => [getComputedStyle(e).borderBottomColor, getComputedStyle(e.parentElement).backgroundColor]"
        )

    other, _ = edge(".views a:not([aria-current])")
    current, _ = edge(".views a[aria-current='page']")
    canvas = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert other == canvas, (other, canvas)
    assert current != canvas, (current, canvas)
    _open_preview(page, 1440)
    other = page.locator('.pv-tab[aria-selected="false"]').first.evaluate(
        "e => getComputedStyle(e).borderBottomColor"
    )
    current = page.locator('.pv-tab[aria-selected="true"]').first.evaluate(
        "e => getComputedStyle(e).borderBottomColor"
    )
    canvas = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert other == canvas, (other, canvas)
    assert current != canvas, (current, canvas)


def test_preview_back_button_is_a_ghost_with_a_chevron(pv):
    page = pv
    back = page.locator("#pv-back")
    assert back.evaluate("e => getComputedStyle(e).backgroundColor") == "rgba(0, 0, 0, 0)"
    assert back.evaluate("e => getComputedStyle(e).borderTopColor") == "rgba(0, 0, 0, 0)"
    assert back.evaluate("e => getComputedStyle(e).color") == PRIMARY
    assert abs(back.bounding_box()["height"] - 40) < 1
    assert back.evaluate("e => getComputedStyle(e, '::before').content") != "none"
    back.hover()
    expect(back).to_have_css("background-color", "rgb(232, 232, 232)")
    expect(back).to_have_css("color", "rgb(0, 67, 206)")
