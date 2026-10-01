"""Summarizer runtime agent: one LLM call -> Summary."""

from .llm import LLMClient
from .models import Summary
from .prompting import load_prompt, paper_block


def summarize(paper: dict, client: LLMClient) -> Summary:
    return client.parse(load_prompt("summarizer"), paper_block(paper), Summary)
