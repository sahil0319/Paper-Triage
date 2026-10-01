"""Critic runtime agent: one LLM call -> Critique. Basis is set from the paper, not the LLM."""

from .llm import LLMClient
from .models import Critique
from .prompting import load_prompt, paper_block


def critique(paper: dict, client: LLMClient) -> Critique:
    out = client.parse(load_prompt("critic"), paper_block(paper), Critique)
    return out.model_copy(update={"basis": paper.get("basis") or "abstract"})
