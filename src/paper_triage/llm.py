"""Single LLM wrapper. Every model call goes through an LLMClient; MOCK_LLM=1 swaps in MockClient."""

import hashlib
import re
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .config import get_settings
from .models import Critique, Rank, Summary

T = TypeVar("T", bound=BaseModel)

SENTINEL = "NOT_IN_STORED_PAPERS"
MAX_TOKENS = 16000
_PAPER_TAG = re.compile(r'<paper id="([^"]*)"(?:[^>]*?basis="(fulltext|abstract)")?')


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
        m = _PAPER_TAG.search(user)
        if m is None or "out of scope" in user.lower():
            return f"{SENTINEL} The stored papers do not cover this."
        return f"Mock answer based on the stored papers [{m.group(1)}]."


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


def get_client() -> LLMClient:
    s = get_settings()
    return MockClient() if s.mock else AnthropicClient(model=s.model)
