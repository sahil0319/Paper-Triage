# Feature Specification: Paper Triage Assistant

**Feature Branch**: `001-paper-triage` (spec dir only; no git branch)

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "Paper Triage Assistant. Input topic/keywords or arXiv IDs / PDF URLs.
Fetcher -> Summarizer -> Critic -> Ranker (0-10 + reason), then grounded chat over stored papers
(cites paper ids, refuses outside stored data). One page, local, no auth."

## Clarifications

### Session 2026-10-01

Answered by planner with defaults (no user round-trip, per orchestrator).

- Q: If a paper's full text cannot be extracted, should it still be critiqued? → A: Yes, from
  the abstract, with basis flagged "abstract" in data and UI.
- Q: May full extracted text be stored locally? → A: Yes, in the local store only; never served
  to anyone but the local UI/chat; PDFs themselves are not kept.
- Q: Which model is used, and is there a per-run cap? → A: Model from `ANTHROPIC_MODEL` env with
  one documented default; per run max 20 papers (default 10).
- Q: Are non-arXiv PDF URLs supported in v1? → A: Yes, as direct URLs only; id is
  `pdf:` + first 12 hex chars of SHA-256 of the URL; title from PDF metadata else URL.
- Q: How does chat find relevant papers when many are stored? → A: Put all stored papers'
  summary, critique and abstract in context (cap: top 20 by rank); no retrieval index in v1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triage a topic into a ranked list (Priority: P1)

The researcher types a topic (or pastes arXiv IDs / PDF URLs). The system fetches the papers,
then for each one writes a short summary, a skeptical critique, and a 0-10 relevance rank with a
one-to-two sentence reason. Results appear as one list sorted by rank.

**Why this priority**: This is the product. Without it there is nothing to chat about.

**Independent Test**: In offline mock mode, submit a topic; a ranked list with summary, critique
and rank+reason per paper appears, using fixture papers and canned model output.

**Acceptance Scenarios**:

1. **Given** an empty store, **When** the user submits "diffusion model distillation", **Then**
   up to N papers appear sorted by rank descending, each showing title, id, rank and reason.
2. **Given** a triaged list, **When** the user opens one paper's critique, **Then** weak claims,
   overclaims and missing baselines are shown, or "not stated" when the text does not say.
3. **Given** input of two arXiv IDs and one PDF URL, **When** submitted, **Then** exactly those
   three papers are triaged.

### User Story 2 - Grounded chat over stored papers (Priority: P2)

The researcher asks questions about the stored papers. Every answer cites the paper ids it uses.
Questions the stored papers cannot answer get an explicit refusal.

**Why this priority**: Saves opening PDFs for follow-up questions; depends on Story 1 data.

**Independent Test**: With fixture papers stored and mock mode on, ask an in-scope and an
out-of-scope question; the first returns cited ids that exist, the second a refusal.

**Acceptance Scenarios**:

1. **Given** stored papers, **When** the user asks "which paper reports the largest speedup?",
   **Then** the answer cites at least one stored paper id and no unknown ids.
2. **Given** stored papers, **When** the user asks about something absent from them, **Then** the
   reply is a visibly intentional refusal, not a guess.
3. **Given** no stored papers, **When** the user asks anything, **Then** the system refuses
   without consulting the model.

### User Story 3 - Revisit earlier results (Priority: P3)

On reload, previously triaged papers and their results are listed without re-fetching.

**Independent Test**: Triage, restart the app, reload the page; the same ranked list appears.

**Acceptance Scenarios**:

1. **Given** a prior triage run, **When** the page is reloaded, **Then** stored results show.

### Edge Cases

- Paper text cannot be extracted: proceed on the abstract; mark the critique "abstract only".
- Topic search returns zero papers: show a plain "no papers found" message.
- Invalid arXiv ID or unreachable URL: that item is reported as failed; others continue.
- Same paper submitted twice: stored once; results reused.
- Model output malformed: retried once, then the item is marked failed with a reason.
- Offline mock mode on: a visible label says so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to submit either a topic/keywords or a list of arXiv IDs and/or
  PDF URLs from one input on one page; per run max 20 papers (default 10).
- **FR-001a**: Non-arXiv PDF URLs get id `pdf:<sha256(url)[:12]>`; title from PDF metadata,
  else the URL.
- **FR-002**: Fetcher MUST retrieve metadata (title, authors, abstract, date, id) and full text
  when available, respecting the source's published rate limit.
- **FR-003**: Summarizer MUST produce a summary (<=120 words) and key contributions per paper.
- **FR-004**: Critic MUST list weak claims, overclaims and missing baselines, only from the
  supplied text, and state its basis (full text or abstract).
- **FR-005**: Ranker MUST give an integer rank 0-10 against the user's topic plus a 1-2 sentence
  reason, using anchors 0-2 off-topic, 3-5 tangential, 6-8 relevant, 9-10 must read.
- **FR-006**: Summarizer, Critic and Ranker MUST each be a separate component with its own
  instructions file.
- **FR-007**: All papers (incl. extracted full text, not PDFs) and results MUST persist locally
  and survive restarts; fetched metadata is cached so repeat requests skip the network.
- **FR-008**: Chat MUST answer only from stored papers (context: summary, critique, abstract of
  top 20 by rank) and cite paper ids for every claim.
- **FR-009**: The system MUST verify that every cited id exists in the store and remove or flag
  any id that does not.
- **FR-010**: Chat MUST refuse explicitly when stored papers cannot answer, and MUST refuse
  without a model call when the store is empty.
- **FR-011**: A mock mode MUST run the full flow with no network and no model key.
- **FR-012**: The UI MUST show rank and reason at a glance, critique one click away, citations as
  links to the cited paper, and a visible mock-mode label; it MUST be keyboard operable.

### Key Entities

- **Paper**: id (arXiv id or derived id for other PDFs), source, title, authors, abstract,
  published date, full text (optional), text basis, fetch status.
- **Triage Result**: paper id, topic, summary, contributions, weak claims, overclaims, missing
  baselines, critique basis, rank, rank reason, status/error.
- **Chat Turn**: question, answer, cited paper ids, refused flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In mock mode, a 5-paper triage completes and renders in under 5 seconds.
- **SC-002**: 100% of chat answers in tests cite only ids present in the store.
- **SC-003**: 100% of out-of-scope test questions produce the refusal state.
- **SC-004**: The full test suite passes with no network access and no model key.
- **SC-005**: A user can go from topic to ranked list with one input and one action.

## Assumptions

- Single local user; no auth, multi-user, or deployment (constitution IV).
- arXiv is the only search source; other hosts are supported only as direct PDF URLs.
- Two-column PDF text may be out of order; acceptable for triage.
- Model chosen by env setting with a documented default; no model id hard-coded elsewhere.
- Text extraction uses a permissive-license library behind one swap point (AGPL alternative not
  bundled).
- Visual style follows DESIGN.md (placeholder now) and PRODUCT.md.
