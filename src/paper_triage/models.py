"""Pydantic schemas; Summary/Critique/Rank double as LLM output contracts."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Basis = Literal["fulltext", "abstract"]


class Summary(BaseModel):
    summary: str
    contributions: list[str] = Field(min_length=1, max_length=5)

    @field_validator("summary")
    @classmethod
    def _trim(cls, v: str) -> str:
        words = v.split()
        return " ".join(words[:120]) if len(words) > 120 else v


class WeakClaim(BaseModel):
    claim: str
    why: str


class Overclaim(BaseModel):
    claim: str
    evidence_gap: str


class Critique(BaseModel):
    weak_claims: list[WeakClaim] = Field(default_factory=list)
    overclaims: list[Overclaim] = Field(default_factory=list)
    missing_baselines: list[str] = Field(default_factory=list)
    basis: Basis


class Rank(BaseModel):
    rank: int
    rank_reason: str

    @field_validator("rank")
    @classmethod
    def _clamp(cls, v: int) -> int:
        return max(0, min(10, v))


class ChatAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    refused: bool
    dropped_citations: list[str] = Field(default_factory=list)


class PaperOut(BaseModel):
    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    source: Literal["arxiv", "pdf"]
    basis: Basis
    rank: int | None = None
    rank_reason: str | None = None
    summary: Summary | None = None
    critique: Critique | None = None
    status: Literal["ok", "failed"]
    error: str | None = None
    abs_url: str | None = None
    pdf_url: str | None = None
    saved: bool = False


class PdfState(BaseModel):
    status: Literal["pending", "ready", "failed"]
    error: str | None = None
    pages: int | None = None


class LibraryItem(BaseModel):
    """One saved paper: the snapshot taken at first save plus Library state."""

    paper_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    source: Literal["arxiv", "pdf"]
    published: str | None = None
    abstract: str = ""
    basis: Basis
    rank: int | None = None
    rank_reason: str | None = None
    summary: Summary | None = None
    critique: Critique | None = None
    abs_url: str | None = None
    pdf_url: str | None = None
    topic: str = ""
    tags: list[str] = Field(default_factory=list)
    directory_id: int | None = None
    saved_at: str
    pdf: PdfState
    highlight_count: int = 0
