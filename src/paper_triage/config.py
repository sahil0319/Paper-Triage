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
    provider: str = ""  # LLM_PROVIDER, no default; validated at the first LLM call
    api_key: str = ""  # AGENT_API_KEY
    max_papers: int = 20
    default_papers: int = 10
    text_cap: int = 40000
    chat_top_k: int = 20
    chat_max_ids: int = 50  # max paper_ids per chat request
    concurrency: int = 4  # papers processed in parallel (TRIAGE_CONCURRENCY, min 1)
    data_dir: str = "./paper_triage_data"  # saved PDFs live under <data_dir>/pdfs
    pdf_max_bytes: int = 52_428_800  # 50 MB cap per saved PDF
    paper_chat_cap: int = 300_000  # max characters of paper text sent to paper chat
    paper_chat_history: int = 6  # max earlier turns accepted by paper chat


def _concurrency() -> int:
    try:
        return max(1, int(os.environ.get("TRIAGE_CONCURRENCY", "").strip() or 4))
    except ValueError:
        return 4


def get_settings() -> Settings:
    """Read env at call time. Never raises: LLM config errors surface in llm.get_client()."""
    provider = (os.environ.get("LLM_PROVIDER") or "").strip().lower()
    default_model = {"anthropic": DEFAULT_MODEL, "openai": DEFAULT_OPENAI_MODEL}.get(provider, "")
    model = (os.environ.get("AGENT_MODEL") or "").strip() or default_model
    return Settings(
        model=model,
        provider=provider,
        api_key=(os.environ.get("AGENT_API_KEY") or "").strip(),
        mock=os.environ.get("MOCK_LLM") == "1",
        db_path=os.environ.get("PAPER_TRIAGE_DB") or "./paper_triage.db",
        concurrency=_concurrency(),
        data_dir=os.environ.get("PAPER_TRIAGE_DATA_DIR") or "./paper_triage_data",
    )
