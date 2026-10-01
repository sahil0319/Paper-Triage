"""Shared helpers for the LLM agents: load prompt files, render a paper as a tagged block."""

from functools import lru_cache
from pathlib import Path

from .config import get_settings
from .extract import prepare_for_llm

_DIR = Path(__file__).parent / "prompts"


@lru_cache
def load_prompt(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8").strip()


def paper_block(paper: dict, with_text: bool = True) -> str:
    """`<paper id basis>` block: title, abstract and (fulltext basis only) capped body text."""
    basis = paper.get("basis") or "abstract"
    parts = [f"Title: {paper['title']}", f"Abstract: {paper.get('abstract') or ''}"]
    if with_text and basis == "fulltext" and paper.get("full_text"):
        parts.append("Text:\n" + prepare_for_llm(paper["full_text"], get_settings().text_cap))
    body = "\n".join(parts)
    return f'<paper id="{paper["id"]}" basis="{basis}">\n{body}\n</paper>'
