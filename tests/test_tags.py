from paper_triage.tags import STOP_WORDS, keywords


def test_basic_keywords_lowercased_in_order():
    assert keywords("Diffusion models, for VIDEO generation") == [
        "diffusion", "models", "video", "generation",
    ]


def test_surrounding_punctuation_stripped():
    assert keywords("(rag).") == ["rag"]
    assert keywords('"retrieval", [augmented]!') == ["retrieval", "augmented"]


def test_inner_hyphen_kept():
    assert keywords("self-supervised learning") == ["self-supervised", "learning"]


def test_one_char_and_stop_words_dropped():
    assert keywords("a b c of the RL in LLMs") == ["rl", "llms"]


def test_duplicates_removed_keeping_first_order():
    assert keywords("Diffusion video diffusion VIDEO models") == ["diffusion", "video", "models"]


def test_empty_and_all_stop_words():
    assert keywords("") == []
    assert keywords("the of and") == []
    assert keywords("   ,, ;; ") == []


def test_stop_words_is_frozenset():
    assert isinstance(STOP_WORDS, frozenset)
    assert "the" in STOP_WORDS
