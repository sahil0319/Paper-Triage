"""Real-browser checks of the v4 Carbon look (T069): fonts, shell, nav, buttons and the query field.

Computed-style assertions against the live mock server; every case runs through `offline_page`,
which fails the test on any non-local request.
"""

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
    hl = hls(page).first
    expect(hl).to_be_attached()
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
