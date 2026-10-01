"""Environment settings, read at call time."""

import os
from dataclasses import dataclass

DEFAULT_MODEL = "claude-opus-5-5"


@dataclass(frozen=True)
class Settings:
    model: str
    mock: bool
    db_path: str
    max_papers: int = 20
    default_papers: int = 10
    text_cap: int = 40000
    chat_top_k: int = 20


def get_settings() -> Settings:
    return Settings(
        model=os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODEL,
        mock=os.environ.get("MOCK_LLM") == "1",
        db_path=os.environ.get("PAPER_TRIAGE_DB") or "./paper_triage.db",
    )
