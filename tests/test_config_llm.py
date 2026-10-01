from paper_triage.config import Settings, get_settings


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
