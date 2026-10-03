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
