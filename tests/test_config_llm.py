from types import SimpleNamespace

import anthropic
import httpx
import pytest

from paper_triage.config import Settings, get_settings
from paper_triage.llm import (
    SENTINEL,
    AnthropicClient,
    LLMError,
    LLMRefusal,
    MockClient,
    get_client,
)
from paper_triage.models import Critique, Rank, Summary


def test_config_defaults(monkeypatch):
    for k in ("ANTHROPIC_MODEL", "PAPER_TRIAGE_DB", "MOCK_LLM"):
        monkeypatch.delenv(k, raising=False)
    s = get_settings()
    assert isinstance(s, Settings)
    assert s.model == "claude-opus-5-5"
    assert s.mock is False
    assert s.db_path == "./paper_triage.db"
    assert (s.max_papers, s.default_papers, s.text_cap, s.chat_top_k) == (20, 10, 40000, 20)


def test_config_reads_env_at_call_time(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "m-x")
    monkeypatch.setenv("PAPER_TRIAGE_DB", "/tmp/x.db")
    monkeypatch.setenv("MOCK_LLM", "1")
    s = get_settings()
    assert (s.model, s.db_path, s.mock) == ("m-x", "/tmp/x.db", True)
    monkeypatch.setenv("MOCK_LLM", "0")
    assert get_settings().mock is False


def test_config_blank_env_uses_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "")
    monkeypatch.setenv("PAPER_TRIAGE_DB", "")
    s = get_settings()
    assert s.model == "claude-opus-5-5"
    assert s.db_path == "./paper_triage.db"


# ---- T004: LLM wrapper ----------------------------------------------------------------------

P1 = '<paper id="2401.00001" basis="fulltext" title="A">abstract</paper>'
P2 = '<paper id="2401.00002" basis="abstract" title="B">abstract</paper>'


def test_llm_get_client_mock(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    assert isinstance(get_client(), MockClient)


def test_llm_get_client_real_is_lazy(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c = get_client()  # must not need a key or network until used
    assert isinstance(c, AnthropicClient)


def test_llm_mock_parse_deterministic_and_typed():
    m = MockClient()
    s1, s2 = m.parse("sys", P1, Summary), m.parse("sys", P1, Summary)
    assert isinstance(s1, Summary) and s1 == s2
    assert isinstance(m.parse("sys", P1, Critique), Critique)
    r = m.parse("sys", P2, Rank)
    assert isinstance(r, Rank) and 0 <= r.rank <= 10 and r.rank_reason
    assert m.parse("sys", P1, Critique).basis == "fulltext"
    assert m.parse("sys", P2, Critique).basis == "abstract"


def test_llm_mock_rank_varies_across_papers():
    m = MockClient()
    ranks = {m.parse("s", f'<paper id="id{i}">x</paper>', Rank).rank for i in range(12)}
    assert len(ranks) > 1


def _chat_prompt(question):
    return (
        '<paper id="2401.00001" title="Basalt Columns">\nAbstract: Stacked sampler stages.\n'
        'Summary: Mock summary of 2401.00001.\n</paper>\n'
        '<paper id="2401.00002" title="Cobalt Adapters">\nAbstract: Low-rank adapters.\n</paper>\n'
        f"<question>\n{question}\n</question>"
    )


def test_llm_mock_chat_refuses_unrelated_question():
    out = MockClient().text("sys", _chat_prompt("What is the capital of France?"))
    assert out.startswith(SENTINEL)


def test_llm_mock_chat_cites_paper_with_title_word():
    m = MockClient()
    out = m.text("sys", _chat_prompt("Tell me about cobalt?"))
    assert out.endswith("[2401.00002].") and "[2401.00001]" not in out
    out = m.text("sys", _chat_prompt("Which paper discusses sampler stages?"))
    assert "[2401.00001]" in out  # abstract word


def test_llm_mock_chat_cites_named_id_first():
    out = MockClient().text("sys", _chat_prompt("What does 2401.00002 claim, besides basalt?"))
    assert "[2401.00002]" in out and "[2401.00001]" not in out


def test_llm_mock_chat_ignores_stop_words_and_prompt_text():
    m = MockClient()
    # stop words and words that only occur in summary text or the question itself never match
    assert m.text("sys", _chat_prompt("Which paper does this talk about?")).startswith(SENTINEL)
    assert m.text("sys", _chat_prompt("mock summary?")).startswith(SENTINEL)
    assert m.text("sys", _chat_prompt("ok")).startswith(SENTINEL)  # < 4 letters


def test_llm_mock_chat_no_paper_tags_or_question_refuses():
    m = MockClient()
    assert m.text("sys", "No papers here. Question?").startswith(SENTINEL)
    assert m.text("sys", "<question>\nbasalt\n</question>").startswith(SENTINEL)
    assert m.text("sys", P1).startswith(SENTINEL)  # no <question>


class FakeMessages:
    def __init__(self, parse_result=None, create_result=None, exc=None):
        self.calls, self.parse_result, self.create_result, self.exc = [], parse_result, create_result, exc

    def parse(self, **kw):
        self.calls.append(("parse", kw))
        if self.exc:
            raise self.exc
        return self.parse_result

    def create(self, **kw):
        self.calls.append(("create", kw))
        if self.exc:
            raise self.exc
        return self.create_result


def fake_client(**kw):
    msgs = FakeMessages(**kw)
    return AnthropicClient(model="m-test", client=SimpleNamespace(messages=msgs)), msgs


def test_llm_anthropic_parse_args_and_result():
    want = Rank(rank=5, rank_reason="r")
    c, msgs = fake_client(parse_result=SimpleNamespace(stop_reason="end_turn", parsed_output=want))
    assert c.parse("SYS", "USER", Rank) is want
    kind, kw = msgs.calls[0]
    assert kind == "parse"
    assert kw["model"] == "m-test" and kw["system"] == "SYS"
    assert kw["messages"] == [{"role": "user", "content": "USER"}]
    assert kw["output_format"] is Rank
    assert kw["output_config"] == {"effort": "low"}
    assert "temperature" not in kw and kw["max_tokens"] > 0


def test_llm_anthropic_text():
    blocks = [SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text="hi [x]")]
    c, msgs = fake_client(create_result=SimpleNamespace(stop_reason="end_turn", content=blocks))
    assert c.text("SYS", "U") == "hi [x]"
    kw = msgs.calls[0][1]
    assert kw["model"] == "m-test" and "temperature" not in kw


def test_llm_anthropic_refusal():
    c, _ = fake_client(parse_result=SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(LLMRefusal):
        c.parse("s", "u", Rank)
    c, _ = fake_client(create_result=SimpleNamespace(stop_reason="refusal", content=[]))
    with pytest.raises(LLMRefusal):
        c.text("s", "u")


def test_llm_anthropic_missing_parsed_output_is_error():
    c, _ = fake_client(parse_result=SimpleNamespace(stop_reason="max_tokens", parsed_output=None))
    with pytest.raises(LLMError):
        c.parse("s", "u", Rank)


def test_llm_anthropic_sdk_error_wrapped():
    exc = anthropic.APIConnectionError(request=httpx.Request("POST", "http://x"))
    c, _ = fake_client(exc=exc)
    with pytest.raises(LLMError):
        c.parse("s", "u", Rank)
    with pytest.raises(LLMError):
        c.text("s", "u")


def test_llm_refusal_is_llm_error():
    assert issubclass(LLMRefusal, LLMError)


# ---- T025: OpenAI provider ------------------------------------------------------------------


def _oa_client(parse_result=None, create_result=None, exc=None):
    from paper_triage.llm import OpenAIClient

    calls = []

    def parse(**kw):
        calls.append(("parse", kw))
        if exc:
            raise exc
        return parse_result

    def create(**kw):
        calls.append(("create", kw))
        if exc:
            raise exc
        return create_result

    sdk = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse, create=create)))
    return OpenAIClient(model="oa-test", client=sdk), calls


def _completion(content=None, parsed=None, refusal=None):
    msg = SimpleNamespace(content=content, parsed=parsed, refusal=refusal)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")])


def test_openai_parse_args_and_result():
    want = Rank(rank=7, rank_reason="r")
    c, calls = _oa_client(parse_result=_completion(parsed=want))
    assert c.parse("SYS", "USER", Rank) is want
    kind, kw = calls[0]
    assert kind == "parse" and kw["model"] == "oa-test" and kw["response_format"] is Rank
    assert kw["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]
    assert "temperature" not in kw and "max_tokens" not in kw


def test_openai_parse_refusal():
    c, _ = _oa_client(parse_result=_completion(refusal="no"))
    with pytest.raises(LLMRefusal):
        c.parse("s", "u", Rank)


def test_openai_parse_missing_parsed_is_error():
    c, _ = _oa_client(parse_result=_completion())
    with pytest.raises(LLMError):
        c.parse("s", "u", Rank)


def test_openai_text_and_refusal():
    c, calls = _oa_client(create_result=_completion(content="hi [x]"))
    assert c.text("SYS", "U") == "hi [x]"
    assert calls[0][0] == "create" and "temperature" not in calls[0][1]
    c, _ = _oa_client(create_result=_completion(refusal="no"))
    with pytest.raises(LLMRefusal):
        c.text("s", "u")


def test_openai_api_error_wrapped():
    import openai

    exc = openai.APIConnectionError(request=httpx.Request("POST", "http://x"))
    c, _ = _oa_client(exc=exc)
    with pytest.raises(LLMError):
        c.parse("s", "u", Rank)
    with pytest.raises(LLMError):
        c.text("s", "u")


def test_openai_validation_error_propagates():
    from pydantic import ValidationError

    try:
        Rank(rank="abc", rank_reason="r")  # type: ignore[arg-type]
    except ValidationError as e:
        exc = e
    c, _ = _oa_client(exc=exc)
    with pytest.raises(ValidationError):
        c.parse("s", "u", Rank)


def test_provider_config(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    s = get_settings()
    assert s.provider == "anthropic" and s.model == "claude-opus-5-5"
    monkeypatch.setenv("LLM_PROVIDER", "OpenAI")
    s = get_settings()
    assert s.provider == "openai" and s.model == "gpt-5-mini"
    monkeypatch.setenv("OPENAI_MODEL", "m-o")
    assert get_settings().model == "m-o"
    monkeypatch.setenv("LLM_PROVIDER", "")
    assert get_settings().provider == "anthropic"


def test_provider_switch(monkeypatch):
    from paper_triage.llm import OpenAIClient

    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    c = get_client()
    assert isinstance(c, OpenAIClient)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert isinstance(get_client(), AnthropicClient)


def test_provider_missing_key_clear_error(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        get_client()


def test_provider_unknown_is_error(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "0")
    monkeypatch.setenv("LLM_PROVIDER", "bogus")
    with pytest.raises(LLMError, match="LLM_PROVIDER"):
        get_client()


def test_mock_wins_over_openai(monkeypatch):
    monkeypatch.setenv("MOCK_LLM", "1")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_client(), MockClient)
