"""Ranker runtime agent: one LLM call -> Rank (clamped 0-10 by the model validator)."""

from .llm import LLMClient
from .models import Rank, Summary
from .prompting import load_prompt, paper_block


def rank(paper: dict, summary: Summary, topic: str, client: LLMClient) -> Rank:
    topic = topic.strip()
    ask = (
        f"Topic: {topic}"
        if topic
        else "No topic given: rank the paper's overall reading priority."
    )
    user = (
        f"{ask}\n\n{paper_block(paper, with_text=False)}\n\n"
        f"Summary: {summary.summary}\nContributions:\n"
        + "\n".join(f"- {c}" for c in summary.contributions)
    )
    return client.parse(load_prompt("ranker"), user, Rank)
