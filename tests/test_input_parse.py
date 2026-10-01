import pytest

from paper_triage.input_parse import Item, parse_query


def test_topic_only():
    assert parse_query("diffusion model distillation") == ("diffusion model distillation", [])


def test_new_style_ids_comma_and_space():
    topic, items = parse_query("2401.01234, 2402.12345v3 2403.0001")
    assert topic == ""
    assert items == [
        Item("arxiv", "2401.01234"),
        Item("arxiv", "2402.12345"),
        Item("arxiv", "2403.0001"),
    ]


def test_old_style_ids():
    _, items = parse_query("math.GT/0107001 hep-th/9901001")
    assert items == [Item("arxiv", "math.GT/0107001"), Item("arxiv", "hep-th/9901001")]


def test_arxiv_urls_normalized():
    _, items = parse_query(
        "https://arxiv.org/abs/2401.01234v2 http://arxiv.org/pdf/2402.00001v1.pdf "
        "https://arxiv.org/abs/math.GT/0107001v1"
    )
    assert items == [
        Item("arxiv", "2401.01234"),
        Item("arxiv", "2402.00001"),
        Item("arxiv", "math.GT/0107001"),
    ]


def test_other_urls_are_pdf_items():
    topic, items = parse_query("https://example.org/papers/x.pdf http://foo.bar/y")
    assert topic == ""
    assert items == [
        Item("pdf", "https://example.org/papers/x.pdf"),
        Item("pdf", "http://foo.bar/y"),
    ]


def test_mixed_topic_and_items():
    topic, items = parse_query("diffusion 2401.01234 distillation https://x.org/a.pdf")
    assert topic == "diffusion distillation"
    assert items == [Item("arxiv", "2401.01234"), Item("pdf", "https://x.org/a.pdf")]


def test_arxiv_prefix_and_dedupe():
    _, items = parse_query("arXiv:2401.01234 2401.01234v2 https://arxiv.org/abs/2401.01234")
    assert items == [Item("arxiv", "2401.01234")]


def test_number_like_word_is_topic():
    topic, items = parse_query("gpt 4 scaling 12345")
    assert items == []
    assert topic == "gpt 4 scaling 12345"


@pytest.mark.parametrize("q", ["", "   ", " , ,"])
def test_empty_raises(q):
    with pytest.raises(ValueError):
        parse_query(q)
