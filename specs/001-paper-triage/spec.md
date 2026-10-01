# Feature Specification: Paper Triage Assistant

**Feature Branch**: `001-paper-triage` (spec dir only; no git branch)

**Created**: 2026-10-01

**Status**: Draft (v2 amendment 2026-10-01)

**Input**: User description: "Paper Triage Assistant. Input topic/keywords or arXiv IDs / PDF URLs.
Fetcher -> Summarizer -> Critic -> Ranker (0-10 + reason), then grounded chat over stored papers
(cites paper ids, refuses outside stored data). One page, local, no auth."

**v2 input** (2026-10-01): full UI redesign per the new DESIGN.md (brief
`docs/design/brief-v2-redesign.md`); a visible animated "searching" status while triage runs;
links to the arXiv abstract page and PDF on every result; chat scoped to the current search's
result set; "Load 5 more" paging for topic searches; offline real-browser e2e tests.

## Clarifications

### Session 2026-10-01

Answered by planner with defaults (no user round-trip, per orchestrator).

- Q: If a paper's full text cannot be extracted, should it still be critiqued? → A: Yes, from
  the abstract, with basis flagged "abstract" in data and UI.
- Q: May full extracted text be stored locally? → A: Yes, in the local store only; never served
  to anyone but the local UI/chat; PDFs themselves are not kept.
- Q: Which model is used, and is there a per-run cap? → A: Model from `ANTHROPIC_MODEL` env with
  one documented default; per run max 20 papers (default 10). (T025: optional `LLM_PROVIDER=openai`
  uses `OPENAI_API_KEY`/`OPENAI_MODEL` instead; Anthropic stays the default.)
- Q: Are non-arXiv PDF URLs supported in v1? → A: Yes, as direct URLs only; id is
  `pdf:` + first 12 hex chars of SHA-256 of the URL; title from PDF metadata else URL.
- Q: How does chat find relevant papers when many are stored? → A: Put all stored papers'
  summary, critique and abstract in context (cap: top 20 by rank); no retrieval index in v1.
  (Superseded by v2: context = the current result set, see below.)

### Session 2026-10-01 (v2)

Answered by planner with defaults (non-interactive, per orchestrator).

- Q: How does chat know which papers form the current result set? → A: The page sends the ids
  it shows (first page plus load-more pages, max 50) with every question; the server uses only
  those that are stored, in the order sent, and rejects more than 50 ids.
- Q: When does the mock client answer instead of refusing? → A: Only when the question names a
  paper id from the set or shares a content word (4+ letters, not a stop word such as "paper",
  "which", "about") with a set paper's title or abstract; it then cites that paper. Otherwise it
  returns the refusal sentinel.
- Q: Where do load-more papers go and how big is the first page? → A: The first page keeps the
  user's size (default 10, max 20); each load-more fetches exactly 5 more from the source offset
  after the papers already requested; new papers are appended below, sorted by rank within their
  page; the shown list is never re-sorted. After a reload, the offset is the number of shown
  results.
- Q: How does the system decide there are no more papers? → A: From the source's reported total
  (offset + papers returned >= total); if the total is missing, when a page returns fewer papers
  than asked.
- Q: What happens with load-more for ID/URL searches? → A: Not offered in the UI; the API rejects
  an offset above 0 when the query contains arXiv IDs or URLs (422).

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
4. **Given** a submitted search, **When** triage is still running, **Then** an animated
   "searching" status is visible and announced to assistive tech; **When** results or an error
   arrive, **Then** the status disappears.
5. **Given** a triaged list, **When** the user looks at an arXiv result, **Then** it shows a link
   to its arXiv abstract page and a link to its PDF; a direct-PDF result shows its PDF link only.
6. **Given** a topic search whose source has more papers, **When** the user activates "Load 5
   more", **Then** the next 5 papers for the same query are triaged and appended below the
   current list with no duplicates; **When** the source has no more papers, **Then** the control
   is hidden.
7. **Given** a search made only of arXiv IDs and/or PDF URLs, **When** results show, **Then** no
   "Load 5 more" control is offered.

### User Story 2 - Grounded chat over the current result set (Priority: P2)

The researcher asks questions about the papers of the current search (the list on screen,
including papers added by "Load 5 more"). Every answer cites the paper ids it uses. Questions
those papers cannot answer, including questions about papers stored from earlier searches, get
an explicit refusal.

**Why this priority**: Saves opening PDFs for follow-up questions; depends on Story 1 data.

**Independent Test**: With fixture papers stored and mock mode on, ask an in-scope and an
out-of-scope question about the current set; the first returns cited ids from the set, the
second a refusal.

**Acceptance Scenarios**:

1. **Given** a current result set, **When** the user asks "which paper reports the largest
   speedup?", **Then** the answer cites at least one paper id from the set and no other ids.
2. **Given** a current result set, **When** the user asks about something absent from it (e.g.
   "what is the capital of France?"), **Then** the reply is a visibly intentional refusal, not a
   guess, in mock mode and live mode alike.
3. **Given** no current result set (no search yet and nothing stored), **When** the user asks
   anything, **Then** the system refuses without consulting the model.
4. **Given** a paper stored by an earlier search that is not in the current set, **When** the
   user asks about that paper, **Then** the reply is a refusal and never cites that paper.
5. **Given** papers appended by "Load 5 more", **When** the user asks about one of them, **Then**
   the answer may cite it.

### User Story 3 - Revisit earlier results (Priority: P3)

On reload, previously triaged papers and their results are listed without re-fetching.

**Independent Test**: Triage, restart the app, reload the page; the same ranked list appears.

**Acceptance Scenarios**:

1. **Given** a prior triage run, **When** the page is reloaded, **Then** stored results show.
2. **Given** a reload that shows the last topic's stored results, **When** the user chats,
   **Then** the shown list is the current result set; **When** that topic is non-empty, **Then**
   "Load 5 more" continues after the papers already shown.

### Edge Cases

- Paper text cannot be extracted: proceed on the abstract; mark the critique "abstract only".
- Topic search returns zero papers: show a plain "no papers found" message.
- Invalid arXiv ID or unreachable URL: that item is reported as failed; others continue.
- Same paper submitted twice: stored once; results reused.
- Model output malformed: retried once, then the item is marked failed with a reason.
- Offline mock mode on: a visible label says so.
- "Load 5 more" fails (network or model error): a plain error shows next to the control, the
  existing list stays unchanged, and the control is enabled again for a retry.
- "Load 5 more" returns only papers already shown: nothing is appended, the status says so, and
  the control stays available while the source reports more papers.
- Current result set reaches 50 papers: "Load 5 more" is hidden (chat context cap).
- A new search replaces the current result set; papers from the previous search drop out of
  chat scope.
- User prefers reduced motion: the searching status shows as static text (no animation) but is
  still visible and announced.

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
- **FR-008** (v2): Chat MUST answer only from the papers of the current result set (the papers
  shown for the active search, including load-more pages; max 50), using their summary,
  critique and abstract, and cite paper ids for every claim. Papers stored by earlier searches
  are out of scope.
- **FR-009** (v2): The system MUST verify that every cited id belongs to the current result set
  and is stored, and remove or flag any id that does not.
- **FR-010** (v2): Chat MUST refuse explicitly when the current result set cannot answer, in
  live and mock mode alike (mock answers only when the question shares a content word with a
  paper in the set), and MUST refuse without a model call when the set is empty or none of its
  papers is stored.
- **FR-011**: A mock mode MUST run the full flow with no network and no model key.
- **FR-012** (v2): The UI MUST follow DESIGN.md (system-font fallback; layout per
  `docs/design/brief-v2-redesign.md`) and PRODUCT.md, show rank and reason at a glance,
  critique one click away, citations as links to the cited paper, a visible mock-mode label,
  and a visible animated "searching" status (announced politely to assistive tech, static under
  reduced motion) while a triage or load-more request runs (appearing within 300 ms of the
  start, a deliberate delay that avoids a flash on fast runs, and removed as soon as results or
  an error show); it MUST be keyboard operable.
- **FR-013**: Topic searches MUST offer "Load 5 more": same query, next 5 papers from the source
  by offset, triaged and appended below the shown list, deduplicated by paper id; the control
  shows a loading state, an error state with retry, and is hidden when the source reports no
  more papers or the set holds 50 papers. Searches containing arXiv IDs or PDF URLs MUST NOT
  offer it.
- **FR-014**: Every result MUST expose and show source links: arXiv results an abstract-page
  link (`https://arxiv.org/abs/<id>`) and a PDF link (`https://arxiv.org/pdf/<id>`); direct-PDF
  results the original PDF URL only. Links open in a new tab.

### Key Entities

- **Paper**: id (arXiv id or derived id for other PDFs), source, title, authors, abstract,
  published date, full text (optional), text basis, fetch status, abstract-page URL (arXiv
  only), PDF URL.
- **Triage Result**: paper id, topic, summary, contributions, weak claims, overclaims, missing
  baselines, critique basis, rank, rank reason, status/error.
- **Result Set** (v2, client-held): the ordered paper ids shown for the active search (first
  page plus load-more pages), the query, the next source offset, and whether more exist. Not
  persisted; sent with each chat question.
- **Chat Turn**: question, answer, cited paper ids, refused flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In mock mode, a 5-paper triage completes and renders in under 5 seconds.
- **SC-002** (v2): 100% of chat answers in tests cite only ids in the current result set.
- **SC-003** (v2): 100% of out-of-scope test questions (general questions and questions about
  papers outside the current set) produce the refusal state, in mock mode.
- **SC-004** (v2): The full test suite, including real-browser tests, passes with no network
  access and no model key.
- **SC-005**: A user can go from topic to ranked list with one input and one action.
- **SC-006**: In every browser test run, the searching status is visible while a search or
  load-more is pending and is gone once results or an error show.
- **SC-007**: 100% of rendered results show source links (arXiv: 2 links; direct PDF: 1 link)
  whose targets equal the URLs defined in FR-014 for that paper and open in a new tab.
- **SC-008**: Each "Load 5 more" adds at most 5 papers, never a duplicate, and the control is
  absent once the source is exhausted (verified in a browser test).

## Assumptions

- Single local user; no auth, multi-user, or deployment (constitution IV).
- arXiv is the only search source; other hosts are supported only as direct PDF URLs.
- Two-column PDF text may be out of order; acceptable for triage.
- Model chosen by env setting with a documented default; no model id hard-coded elsewhere.
- Text extraction uses a permissive-license library behind one swap point (AGPL alternative not
  bundled).
- Visual style follows DESIGN.md (v2: Airtable-style, user-supplied) and PRODUCT.md; the
  DESIGN.md brand font (Haas Grotesk) is not licensed here, so a system-font stack chosen in
  `docs/design/brief-v2-redesign.md` replaces it. No web fonts or external assets are loaded.
- The searching status is client-side only (cycling phase text plus elapsed time); it does not
  claim real per-paper progress, so no progress endpoint is needed.
- The current result set lives in the page, not the server; a reload rebuilds it from the
  last topic's stored results.
