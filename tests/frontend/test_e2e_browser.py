"""Real-browser specs against the live mock server (fixtures from tests/conftest.py).

Selectors come only from the UI test hooks in plan.md. Every case runs through `offline_page`,
which fails the test on any non-local request (SC-004).
"""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.e2e

TOPIC = "diffusion distillation"
NEW_IDS = {f"2401.{n:05d}" for n in range(11, 16)}


def _ids(page):
    return [i[len("paper-"):] for i in page.eval_on_selector_all(
        "#paper-list li.paper", "els => els.map(e => e.id)")]


def search(page, query, rows):
    """Submit a search and wait until `rows` papers are listed and the run is over."""
    page.fill("#query", query)
    page.click("#submit")
    expect(page.locator("#paper-list li.paper")).to_have_count(rows, timeout=15_000)
    expect(page.locator("#submit")).to_be_enabled()


@pytest.fixture
def home(offline_page, live_server):
    live_server.set_triage_delay(0)
    offline_page.goto("/")
    return offline_page


def test_indicator_visible_during_search_then_gone(home, live_server):
    page = home
    live_server.set_triage_delay(1.5)
    try:
        page.fill("#query", TOPIC)
        page.click("#submit")
        expect(page.locator("#working")).to_be_visible(timeout=3_000)
        expect(page.locator("#empty")).to_be_hidden()
        expect(page.locator("#working")).to_be_hidden(timeout=10_000)
        expect(page.locator("#paper-list li.paper")).to_have_count(10)
    finally:
        live_server.set_triage_delay(0)


def test_every_arxiv_row_links_to_abs_and_pdf(home):
    page = home
    search(page, TOPIC, 10)
    rows = page.locator("#paper-list li.paper")
    for i in range(rows.count()):
        row = rows.nth(i)
        pid = row.get_attribute("id")[len("paper-"):]
        abs_link = row.locator('a[data-link="abs"]')
        pdf_link = row.locator('a[data-link="pdf"]')
        assert abs_link.get_attribute("href") == f"https://arxiv.org/abs/{pid}"
        assert pdf_link.get_attribute("href") == f"https://arxiv.org/pdf/{pid}"
        for link in (abs_link, pdf_link):
            assert link.get_attribute("target") == "_blank"
            assert "noopener" in link.get_attribute("rel")


def test_direct_pdf_row_shows_only_the_pdf_link(home):
    page = home
    url = "https://example.org/files/paper.pdf"
    search(page, url, 1)
    row = page.locator("#paper-list li.paper").first
    assert row.get_attribute("id").startswith("paper-pdf:")
    expect(row.locator("a[data-link]")).to_have_count(1)
    expect(row.locator('a[data-link="abs"]')).to_have_count(0)
    pdf_link = row.locator('a[data-link="pdf"]')
    assert pdf_link.get_attribute("href") == url
    assert pdf_link.get_attribute("target") == "_blank"
    assert "noopener" in pdf_link.get_attribute("rel")


def test_load_more_appends_five_then_ends(home):
    page = home
    search(page, TOPIC, 10)
    first_page = set(_ids(page))
    expect(page.locator("#load-more")).to_be_visible()
    page.click("#load-more")
    expect(page.locator("#paper-list li.paper")).to_have_count(15)
    ids = _ids(page)
    assert len(set(ids)) == 15
    assert set(ids) - first_page == NEW_IDS
    expect(page.locator("#load-more")).not_to_be_visible()


def test_id_search_offers_no_load_more(home):
    page = home
    search(page, "2401.00001 2401.00002", 2)
    expect(page.locator("#load-more")).not_to_be_visible()


def test_chat_refuses_out_of_scope_question(home):
    page = home
    search(page, TOPIC, 10)
    page.fill("#question", "What is the capital of France?")
    page.click("#ask")
    last = page.locator("#chat-log li.turn").last
    expect(last.locator(".turn__a--refused")).to_be_visible(timeout=10_000)
    expect(page.locator("#chat-log a.cite")).to_have_count(0)


def _marker_word(page, paper_id):
    title = page.locator(f'[id="paper-{paper_id}"] .paper__title').inner_text()
    return next(w for w in re.findall(r"[A-Za-z]+", title) if len(w) >= 6)


def ask(page, question):
    """Ask in the chat and return the finished turn."""
    count = page.locator("#chat-log li.turn").count()
    page.fill("#question", question)
    page.click("#ask")
    expect(page.locator("#chat-log li.turn")).to_have_count(count + 1)
    expect(page.locator("#ask")).to_be_enabled(timeout=10_000)
    return page.locator("#chat-log li.turn").last


def test_chat_refuses_paper_outside_the_current_set(home):
    page = home
    search(page, TOPIC, 10)
    word = _marker_word(page, "2401.00002")
    # Positive control: the same word is answered while 2401.00002 is in the set.
    turn = ask(page, f"{word}?")
    expect(turn.locator(".turn__a--refused")).to_have_count(0)
    assert set(turn.locator("a.cite").all_inner_texts()) == {"2401.00002"}
    # Now the set is just 2401.00001; 2401.00002 stays stored but out of scope.
    search(page, "2401.00001", 1)
    turn = ask(page, f"{word}?")
    expect(turn.locator(".turn__a--refused")).to_be_visible()
    expect(turn.locator("a.cite")).to_have_count(0)


def test_chat_answer_cites_only_shown_papers(home):
    page = home
    # Seed stored-but-not-shown papers: load-more stores 2401.00011..15, then a fresh search
    # shows only the first page again.
    search(page, TOPIC, 10)
    page.click("#load-more")
    expect(page.locator("#paper-list li.paper")).to_have_count(15)
    outside_id = "2401.00015"
    outside_word = _marker_word(page, outside_id)
    search(page, TOPIC, 10)
    shown = set(_ids(page))
    assert outside_id not in shown
    inside_word = _marker_word(page, "2401.00003")
    # The question names one shown paper and one stored paper that is not shown.
    turn = ask(page, f"{inside_word} {outside_word}?")
    expect(turn.locator("a.cite").first).to_be_visible()
    cited = set(turn.locator("a.cite").all_inner_texts())
    assert cited == {"2401.00003"}
    assert outside_id not in turn.inner_text()


def _chat_scope_ids(page, question):
    """Ask in the chat and return the paper_ids the page sent with the request."""
    with page.expect_request(lambda r: r.url.endswith("/api/chat")) as info:
        ask(page, question)
    return info.value.post_data_json["paper_ids"]


def test_load_more_clears_chat_and_widens_scope(home):
    page = home
    search(page, TOPIC, 10)
    assert len(_chat_scope_ids(page, "What is the capital of France?")) == 10
    expect(page.locator("#chat-log li.turn")).to_have_count(1)

    page.click("#load-more")
    expect(page.locator("#paper-list li.paper")).to_have_count(15)
    # (a) transcript cleared, (c) visible and announced scope line
    expect(page.locator("#chat-log li.turn")).to_have_count(0)
    expect(page.locator("#chat-note")).to_be_visible()
    expect(page.locator("#chat-note")).to_contain_text("Chat now covers 15 papers")
    expect(page.locator("#status")).to_contain_text("Chat now covers 15 papers")
    expect(page.locator("#chat-scope")).to_contain_text("15 papers")
    # (b) next chat request carries all 15 visible ids, in display order
    assert _chat_scope_ids(page, "What is the capital of France?") == _ids(page)
    assert len(_ids(page)) == 15
    expect(page.locator("#chat-note")).to_be_hidden()


def test_load_more_error_keeps_chat_and_scope(home):
    page = home
    search(page, TOPIC, 10)
    ask(page, "What is the capital of France?")
    expect(page.locator("#chat-log li.turn")).to_have_count(1)

    page.route("**/api/triage", lambda route: route.fulfill(
        status=502, content_type="application/json", body='{"detail": "boom"}'))
    page.click("#load-more")
    expect(page.locator(".load-more__error")).to_be_visible(timeout=10_000)
    page.unroute("**/api/triage")
    expect(page.locator("#chat-log li.turn")).to_have_count(1)
    expect(page.locator("#chat-note")).to_be_hidden()
    expect(page.locator("#paper-list li.paper")).to_have_count(10)
    assert len(_chat_scope_ids(page, "What is the capital of France?")) == 10


def test_new_search_clears_chat_transcript(home):
    page = home
    search(page, TOPIC, 10)
    ask(page, "What is the capital of France?")
    expect(page.locator("#chat-log li.turn")).to_have_count(1)
    search(page, "2401.00001", 1)
    expect(page.locator("#chat-log li.turn")).to_have_count(0)
    expect(page.locator("#chat-note")).to_contain_text("Chat now covers 1 paper.")
    assert _chat_scope_ids(page, "What is the capital of France?") == ["2401.00001"]
