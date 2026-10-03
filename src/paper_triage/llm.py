"""Single LLM wrapper. Every model call goes through an LLMClient; MOCK_LLM=1 swaps in MockClient.

LLM_PROVIDER picks anthropic (default) or openai; MOCK_LLM=1 wins over both."""

import hashlib
import os
import re
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .config import get_settings
from .models import Critique, Rank, Summary

T = TypeVar("T", bound=BaseModel)

SENTINEL = "NOT_IN_STORED_PAPERS"
MAX_TOKENS = 16000
_PAPER_TAG = re.compile(r'<paper id="([^"]*)"(?:[^>]*?basis="(fulltext|abstract)")?')
_CHAT_PAPER = re.compile(r'<paper id="([^"]*)"(?: title="([^"]*)")?[^>]*>(.*?)</paper>', re.DOTALL)
_PAGE = re.compile(r'<page n="(\d+)">(.*?)</page>', re.DOTALL)
# UI starter questions for paper chat: (question pattern, word the cited page must contain; None =
# the first page with text). Keeps mock answers grounded for the starters on any sample paper.
_PAGE_STARTERS = (
    (re.compile(r"\bmain (?:claim|contribution|idea|result)s?\b"), None),
    (re.compile(r"\bbaselines?\b"), "baseline"),
    (re.compile(r"\blimitations?\b"), "limitation"),
)
_QUESTION = re.compile(r"<question>(.*?)</question>", re.DOTALL)
_WORD = re.compile(r"[a-z]{4,}")
_STOP_TEXT = (
    "about above after also been being both cannot could does done each from have here into "
    "just like made make many more most much must only other over paper papers said same shall "
    "should show some such tell than that their them then there these they this those very want "
    "were what when where which while whom whose will with would your"
)
_MOCK_STOP_WORDS = frozenset(_STOP_TEXT.split())


class LLMError(Exception):
    """Any model-call failure."""


class LLMRefusal(LLMError):
    """The model refused (stop_reason == "refusal")."""


class LLMClient(Protocol):
    def parse(self, system: str, user: str, schema: type[T]) -> T: ...

    def text(self, system: str, user: str) -> str: ...


class MockClient:
    """Deterministic canned responses, keyed by sha256 of the first <paper id="..."> in the prompt."""

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        m = _PAPER_TAG.search(user)
        pid = m.group(1) if m else ""
        basis = (m.group(2) if m else None) or "abstract"
        h = int(hashlib.sha256(pid.encode()).hexdigest(), 16)
        if schema is Summary:
            obj = Summary(
                summary=f"Mock summary of {pid or 'the paper'}.",
                contributions=[f"Mock contribution {h % 100}", "Not stated: further detail"],
            )
        elif schema is Critique:
            obj = Critique(
                weak_claims=[{"claim": f"Mock claim {h % 100}", "why": "Not stated in evidence"}],
                overclaims=[],
                missing_baselines=["Not stated"],
                basis=basis,
            )
        elif schema is Rank:
            obj = Rank(rank=h % 11, rank_reason=f"Mock reason for {pid or 'the paper'}.")
        else:
            raise LLMError(f"MockClient has no canned response for {schema.__name__}")
        return obj  # type: ignore[return-value]

    def text(self, system: str, user: str) -> str:
        """Answer only if the question names a context paper id or shares a content word
        (>= 4 lowercase letters, not a stop word) with a context paper's title or abstract."""
        refusal = f"{SENTINEL} The stored papers do not cover this."
        q = _QUESTION.search(user)
        if '<page n="' in user:
            return self._page_answer(user, q, f"{SENTINEL} This paper does not cover that.")
        papers = _CHAT_PAPER.findall(user[: q.start()] if q else user)
        if q is None or not papers:
            return refusal
        question = q.group(1).lower()
        words = set(_WORD.findall(question)) - _MOCK_STOP_WORDS
        hit = next((pid for pid, _, _ in papers if pid.lower() in question), None)
        for pid, title, body in papers:
            if hit:
                break
            abstract = next(
                (ln[len("Abstract:"):] for ln in body.splitlines() if ln.startswith("Abstract:")), ""
            )
            if words & set(_WORD.findall(f"{title} {abstract}".lower())):
                hit = pid
        return f"Mock answer based on the stored papers [{hit}]." if hit else refusal


    @staticmethod
    def _page_answer(user: str, q, refusal: str) -> str:
        """Paper-chat mode (prompt has <page n=> blocks): cite the first page that shares a content
        word with the question, else refuse."""
        if q is None:
            return refusal
        pages = _PAGE.findall(user[: q.start()])
        question = q.group(1).lower()
        for pattern, key in _PAGE_STARTERS:
            if pattern.search(question):
                hit = next((n for n, t in pages if t.strip() and (key is None or key in t.lower())), None)
                if hit:
                    return f"Mock answer from this paper [p.{hit}]."
        words = set(_WORD.findall(question)) - _MOCK_STOP_WORDS
        for n, text in pages:
            if words & set(_WORD.findall(text.lower())):
                return f"Mock answer from this paper [p.{n}]."
        return refusal


class AnthropicClient:
    """Real client. SDK imported and constructed lazily so no key/network is needed to build it."""

    def __init__(self, model: str, client=None):
        self.model = model
        self._client = client

    @property
    def _sdk(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def _call(self, fn, **kwargs):
        try:
            import anthropic

            api_error = anthropic.APIError
        except ImportError:  # pragma: no cover
            api_error = ()
        try:
            msg = fn(**kwargs)
        except api_error as e:
            raise LLMError(f"{type(e).__name__}: {e}") from e
        if getattr(msg, "stop_reason", None) == "refusal":
            raise LLMRefusal("model refused")
        return msg

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        msg = self._call(
            self._sdk.messages.parse,
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": "low"},
        )
        out = getattr(msg, "parsed_output", None)
        if out is None:
            raise LLMError(f"no parsed output (stop_reason={msg.stop_reason})")
        return out

    def text(self, system: str, user: str) -> str:
        msg = self._call(
            self._sdk.messages.create,
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


class OpenAIClient:
    """OpenAI chat-completions client. SDK imported and constructed lazily (key checked in get_client)."""

    def __init__(self, model: str, client=None):
        self.model = model
        self._client = client

    @property
    def _sdk(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI()  # reads OPENAI_API_KEY
        return self._client

    def _call(self, fn, **kwargs):
        try:
            import openai

            api_error = openai.APIError
        except ImportError:  # pragma: no cover
            api_error = ()
        try:
            comp = fn(
                model=self.model,
                max_completion_tokens=MAX_TOKENS,
                **kwargs,
            )
        except api_error as e:
            raise LLMError(f"{type(e).__name__}: {e}") from e
        if not getattr(comp, "choices", None):
            raise LLMError("empty completion")
        choice = comp.choices[0]
        if getattr(choice.message, "refusal", None) or getattr(choice, "finish_reason", None) == "content_filter":
            raise LLMRefusal("model refused")
        return choice

    @staticmethod
    def _messages(system: str, user: str) -> list[dict]:
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def parse(self, system: str, user: str, schema: type[T]) -> T:
        choice = self._call(
            self._sdk.chat.completions.parse,
            messages=self._messages(system, user),
            response_format=schema,
        )
        out = getattr(choice.message, "parsed", None)
        if out is None:
            raise LLMError(f"no parsed output (finish_reason={choice.finish_reason})")
        return out

    def text(self, system: str, user: str) -> str:
        choice = self._call(self._sdk.chat.completions.create, messages=self._messages(system, user))
        return choice.message.content or ""


def get_client() -> LLMClient:
    s = get_settings()
    if s.mock:
        return MockClient()
    if s.provider == "anthropic":
        return AnthropicClient(model=s.model)
    if s.provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAIClient(model=s.model)
    raise LLMError(f"unknown LLM_PROVIDER {s.provider!r} (use 'anthropic' or 'openai')")
