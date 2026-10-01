"""Environment settings, read at call time."""

import os
from dataclasses import dataclass

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_OPENAI_MODEL = "gpt-5-mini"  # user must confirm this id is available to their key


@dataclass(frozen=True)
class Settings:
    model: str
    mock: bool
    db_path: str
    provider: str = "anthropic"
    max_papers: int = 20
    default_papers: int = 10
    text_cap: int = 40000
    chat_top_k: int = 20


def get_settings() -> Settings:
    provider = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider == "openai":
        model = os.environ.get("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
    else:
        model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL
    return Settings(
        model=model,
        provider=provider,
        mock=os.environ.get("MOCK_LLM") == "1",
        db_path=os.environ.get("PAPER_TRIAGE_DB") or "./paper_triage.db",
    )
