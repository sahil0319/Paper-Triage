# Feature Specification: Paper Triage Assistant

**Feature Branch**: `001-paper-triage` (spec dir only; no git branch)

**Created**: 2026-10-01

**Status**: Draft (v3 amendment 2026-10-03; v2 amendment 2026-10-01)

**Input**: User description: "Paper Triage Assistant. Input topic/keywords or arXiv IDs / PDF URLs.
Fetcher -> Summarizer -> Critic -> Ranker (0-10 + reason), then grounded chat over stored papers
(cites paper ids, refuses outside stored data). One page, local, no auth."

**v2 input** (2026-10-01): full UI redesign per the new DESIGN.md (brief
`docs/design/brief-v2-redesign.md`); a visible animated "searching" status while triage runs;
links to the arXiv abstract page and PDF on every result; chat scoped to the current search's
result set; "Load 5 more" paging for topic searches; offline real-browser e2e tests.

**v3 input** (2026-10-03): save papers from result cards (snapshot of everything the card shows);
a Library section of saved papers with an in-page live PDF preview, the PDF downloaded and kept
locally on save; search keywords become tags, shown at the Library top, searchable and
multi-select; user-created directories to file saved papers into; viewer highlights, short notes
and small reading aids; a side-by-side chat grounded only on the open paper's own text, started
lazily on the first message. Single local user, no auth. Also: the results chat clears and
re-scopes whenever the visible result set changes (bug F-006).

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

### Session 2026-10-03 (v3)

Non-interactive. The first group records defaults given by the orchestrator (router); the second
group are planner answers with defaults for the remaining gaps.

Router defaults:

- Q: What does saving keep, and for how long? → A: A snapshot of paper id, title, authors, date,
  abstract, summary, critique, score + reason, abstract/PDF links, source query keywords and
  save time; it persists independent of later searches. Saving twice is idempotent and merges
  the new query's tags. Unsave deletes the saved paper, its PDF and its annotations after a
  confirmation.
- Q: Where do tags come from and how is the Library filtered? → A: Tags are the normalized
  keywords of the topic query (lowercase, split on whitespace and commas, stop words dropped);
  arXiv-ID/URL inputs get no keyword tags. Tag multi-select is AND; a text box searches tags; a
  title text filter also exists. No manual tag editing in v3.
- Q: How do directories work? → A: Flat, user-created, rename and delete; a paper is in at most
  one directory, default "Unsorted"; deleting a directory moves its papers to "Unsorted".
- Q: How and when is the PDF obtained? → A: Fetched server-side on save, asynchronously, with
  status pending/ready/failed and retry; stored locally (storage form decided at plan time from
  research); served from the app's own origin. Mock/offline mode uses a fixture PDF and no
  network.
- Q: What does the viewer include? → A: In-page viewer using vendored libraries only (the static
  asset guard forbids external URLs). Highlights in a few colors and notes, persisted server-side
  in the local database; annotation list with jump-to; page navigation; zoom; extra aids decided
  at plan time.
- Q: How does the per-paper chat behave? → A: Lazy (no text extraction or model context until the
  first message), grounded only on that paper's text, cites page numbers, refuses outside; the
  mock client returns canned output.

Planner defaults:

- Q: Does saving again refresh the snapshot, and where can a paper be unsaved? → A: No. The
  first snapshot and save time are kept; only tags are merged. A saved card shows "Saved";
  activating it again merges the current query's tags and changes nothing else. Unsave exists
  only in the Library.
- Q: Is the per-paper chat transcript kept? → A: Only in the page: each paper keeps its
  transcript while the page stays open (switching papers keeps it) and loses it on reload. The
  prepared per-page paper text is stored and reused; it is deleted on Unsave.
- Q: When does the mock paper chat answer instead of refusing? → A: Same rule as the results
  chat: only when the question shares a content word (4+ letters, not a stop word) with the
  paper's text; it then cites the first page containing that word. Otherwise it refuses.
- Q: Which highlight colors, and must highlights survive zoom? → A: Four colors: yellow, green,
  blue, pink (default yellow). Highlight positions are relative to the page, so they stay on the
  same text at every zoom level.
- Q: Does "Load 5 more" also clear the results chat transcript (FR-008a)? → A: Yes. Any change of
  the visible result set (new search, load-more, reload) clears the transcript and re-scopes the
  chat, so earlier answers never appear to cover a set they did not see.

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

### User Story 4 - Save a paper from the results (Priority: P4, v3)

While triaging, the researcher saves a promising paper with one action on its result card. The
saved copy keeps everything the card showed, plus the search keywords as tags, and stays in the
Library no matter what is searched later.

**Why this priority**: Every other v3 story works on saved papers; nothing else exists without it.

**Independent Test**: In mock mode, search a topic, save one card, run a different search,
reload; the paper is in the Library with the same title, summary, critique, score and reason it
had on the card, tagged with the first query's keywords.

**Acceptance Scenarios**:

1. **Given** a result card, **When** the user activates its Save control, **Then** the card shows
   a saved state and the paper appears in the Library with its id, title, authors, date,
   abstract, summary, critique, score and reason, source links, source query, tags and save time.
2. **Given** a saved paper, **When** the user runs another search or the paper is re-triaged with
   a different score, **Then** the Library entry still shows the values captured at save time.
3. **Given** a paper already saved from "diffusion distillation", **When** it shows in a search
   for "consistency models" and the user saves it again, **Then** the Library still holds one
   entry, the original snapshot and save time are kept, and the tags now include the keywords of
   both queries.
4. **Given** a search made of arXiv IDs or PDF URLs, **When** the user saves a result, **Then**
   it is saved with no keyword tags.
5. **Given** a saved paper, **When** the user chooses Unsave in the Library and confirms, **Then**
   the entry, its stored PDF, its highlights, notes and prepared paper text are removed; **When**
   the user cancels, **Then** nothing changes.

### User Story 5 - Library with in-page PDF preview (Priority: P5, v3)

The researcher opens the Library section of the same page, sees all saved papers, and reads any
of them in a PDF viewer inside the page, without opening a new tab. Saving a paper also downloads
its PDF and keeps it locally, so reading works later with no source site involved.

**Why this priority**: Reading saved papers in place is the main reason to save them.

**Independent Test**: In mock mode with no network, save a paper; its PDF status moves from
pending to ready; opening it shows page 1 of the fixture PDF inside the page.

**Acceptance Scenarios**:

1. **Given** saved papers, **When** the user opens the Library, **Then** each entry shows title,
   authors, date, score, tags, directory and PDF status, newest save first.
2. **Given** a just-saved paper, **When** its PDF is still downloading, **Then** its status reads
   pending; **When** the download finishes, **Then** it reads ready without a page reload.
3. **Given** a ready PDF, **When** the user opens the paper, **Then** the PDF renders inside the
   page next to the Library, with page navigation (previous, next, go to page, "page n of m")
   and zoom (in, out, fit width), and the user never leaves the page.
4. **Given** a failed download, **When** the Library shows the entry, **Then** the status reads
   failed with a plain reason and offers Retry; **When** Retry succeeds, **Then** it reads ready.
5. **Given** no saved papers, **When** the user opens the Library, **Then** a plain empty state
   explains how to save a paper from the results.

### User Story 6 - Filter the Library by tags and title (Priority: P6, v3)

The researcher finds saved papers by the keywords they were found with. All tags are listed at
the top of the Library; the researcher narrows the tag list by typing, selects one or more tags,
and sees only papers carrying all of them. A title filter narrows further.

**Why this priority**: Makes a growing Library usable; tags come for free from searches.

**Independent Test**: Save papers from three different topic queries; select two tags; only
papers tagged with both remain; type part of a title; the list narrows again.

**Acceptance Scenarios**:

1. **Given** saved papers with tags, **When** the Library opens, **Then** every tag in use shows
   at the top with the number of saved papers that carry it.
2. **Given** the tag list, **When** the user types "diff" in the tag search box, **Then** only
   tags containing "diff" are listed; selected tags stay selected.
3. **Given** tags "diffusion" and "distillation" selected, **When** the list updates, **Then**
   only papers tagged with both show; **When** the user clears the selection, **Then** all show.
4. **Given** any tag selection, **When** the user types in the title filter, **Then** the list
   keeps only papers whose title contains the text (case-insensitive).
5. **Given** filters that match nothing, **When** the list updates, **Then** a plain "no saved
   papers match" state shows with a way to clear the filters.

### User Story 7 - File saved papers into directories (Priority: P7, v3)

The researcher creates directories such as "network", "computer vision" or "final year thesis",
moves saved papers into them, and browses one directory at a time.

**Why this priority**: Personal organisation on top of tags; useful but not needed to read.

**Independent Test**: Create directory "thesis", move a paper into it, select "thesis": only
that paper shows; rename it; delete it; the paper is back in Unsorted.

**Acceptance Scenarios**:

1. **Given** the Library, **When** the user creates directory "computer vision", **Then** it is
   listed with a count of 0 next to the built-in "Unsorted" directory and "All".
2. **Given** a newly saved paper, **When** the Library lists it, **Then** it is in "Unsorted".
3. **Given** a paper in "Unsorted", **When** the user moves it to "computer vision", **Then** it
   leaves "Unsorted" and is listed in "computer vision" only.
4. **Given** a directory, **When** the user renames it, **Then** its papers stay in it under the
   new name; a name already in use (case-insensitive) or empty is rejected with a plain message.
5. **Given** a directory holding papers, **When** the user deletes it and confirms, **Then** the
   directory is gone and its papers are in "Unsorted"; no paper is lost.

### User Story 8 - Highlight and annotate while reading (Priority: P8, v3)

In the viewer the researcher highlights lines in one of a few colors, attaches short notes, and
uses a list of all annotations to jump back to any of them later.

**Why this priority**: Turns the preview into a reading tool; depends on Story 5.

**Independent Test**: Open a saved paper, highlight a line in green, add a note to it, restart
the app, reopen the paper; the highlight and note are there, and the annotation list jumps to
the right page.

**Acceptance Scenarios**:

1. **Given** an open PDF with selectable text, **When** the user selects text and picks a color,
   **Then** the text is highlighted in that color and stays highlighted after reopening and
   after an app restart.
2. **Given** a highlight, **When** the user adds a short note, **Then** the note is saved with it;
   the user can also add a note to a page without a highlight.
3. **Given** a highlight or note, **When** the user edits its note, changes its color or deletes
   it, **Then** the change persists.
4. **Given** annotations on several pages, **When** the user opens the annotation list, **Then**
   entries are ordered by page and show page, color and an excerpt or note; **When** the user
   activates one, **Then** the viewer jumps to that page and marks the annotation.

### User Story 9 - Chat with one paper beside the viewer (Priority: P9, v3)

Next to the open PDF, the researcher asks questions about that paper only. Answers use only the
paper's own text and cite page numbers; questions the paper cannot answer get an explicit
refusal. Nothing is prepared for this chat until the first question is sent.

**Why this priority**: Deep reading aid; most costly feature, so built last and started lazily.

**Independent Test**: In mock mode, open a saved paper, confirm no paper-chat work has happened,
ask an in-paper question (answer cites valid page numbers) and an outside question (refusal).

**Acceptance Scenarios**:

1. **Given** an open paper whose chat has never been used, **When** the viewer opens, **Then** no
   text preparation and no model call happen for that chat.
2. **Given** an open paper with a ready PDF, **When** the user sends a question about its
   content, **Then** the answer cites one or more page numbers of that paper, and activating a
   page citation jumps the viewer to that page.
3. **Given** an open paper, **When** the user asks something the paper does not cover (another
   paper, general knowledge), **Then** the reply is a visibly intentional refusal, in mock and
   live mode alike.
4. **Given** a paper whose PDF is not ready or has no extractable text, **When** the user asks a
   question, **Then** the chat refuses with a plain reason and no model call is made.

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
- (v3) Visible result set changes (new search, "Load 5 more", reload): the results chat
  transcript clears and the chat scope is the new visible set before the next question.
- (v3) Saving a card whose triage failed: Save is not offered; only completed results can be
  saved.
- (v3) PDF download fails (unreachable host, not a PDF, larger than 50 MB): status failed with a
  plain reason; the snapshot is kept; Retry is offered.
- (v3) App restarts while a PDF is pending: on start, pending downloads are retried once or
  marked failed; never left pending forever.
- (v3) PDF with no text layer (scanned): it still displays; text highlights and paper chat are
  unavailable with a plain message; page notes still work.
- (v3) Unsave or directory delete while the viewer shows an affected paper: the viewer closes
  (unsave) or keeps the paper open under "Unsorted" (directory delete).
- (v3) Query made only of stop words or punctuation: the paper is saved with no tags.
- (v3) Tag search text matches no tag: a plain "no tags match" line; paper list unchanged.
- (v3) Paper chat question while the PDF is still pending: refusal with "PDF not ready yet".

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
- **FR-008a** (v3): Whenever the visible result set changes (new search, "Load 5 more", reload),
  the results chat MUST clear its transcript and use the new visible set as its scope for the
  next question.

#### v3: Library

- **FR-015**: Every completed result card MUST offer Save. Saving stores a snapshot: paper id,
  title, authors, date, abstract, summary, critique (weak claims, overclaims, missing baselines,
  basis), score and reason, abstract-page and PDF links, source query, tags, and save time.
  Snapshots persist across restarts and are not changed by later searches or re-triage.
- **FR-016**: Saving an already saved paper MUST NOT create a second entry; it keeps the original
  snapshot and save time and merges the new query's tags. Cards of saved papers show "Saved" in
  any search and after reload; activating it again only merges tags.
- **FR-017**: Unsave (Library only, after explicit confirmation) MUST delete the saved entry, its
  stored PDF, its annotations and its prepared paper text; triage results for searches are kept.
- **FR-018**: On save, the system MUST download the paper's PDF in the background without
  delaying the save, store it locally, and expose status pending, ready or failed (with
  reason); failed downloads offer Retry. Limit 50 MB; non-PDF content fails. Pending downloads
  left by a restart are resumed or failed on start. Mock/offline mode uses a fixture PDF and no
  network.
- **FR-019**: Stored PDFs MUST be served by the app itself and shown in an in-page viewer; viewing
  loads no external hosts or assets.
- **FR-020**: The page MUST have a Library section listing saved papers (title, authors, date,
  score, tags, directory, PDF status), newest save first, with an empty state.
- **FR-021**: Tags MUST be derived from a topic query: lowercase, split on whitespace and commas,
  surrounding punctuation stripped, English stop words and 1-character tokens dropped,
  duplicates removed. Queries with arXiv IDs or URLs yield no tags. No manual tag editing (v3).
- **FR-022**: The Library top MUST list every tag in use with its paper count, a text box that
  narrows the tag list, multi-select (papers must carry all selected tags), clear-all, and a
  case-insensitive title filter; tag, title and directory filters combine (AND), with a
  "no match" state.
- **FR-023**: Users MUST be able to create, rename and delete flat directories (name 1-60
  characters after trimming, unique case-insensitive). A built-in "Unsorted" directory cannot be
  renamed or deleted. Each saved paper is in exactly one directory (default "Unsorted") and can
  be moved. Deleting a directory (after confirmation) moves its papers to "Unsorted". An "All"
  view lists every saved paper.
- **FR-024**: The viewer MUST offer previous/next page, go to page, "page n of m", zoom in/out,
  fit width, and a link to open the original PDF in a new tab; closing it keeps the Library
  filters and scroll position.
- **FR-025**: Users MUST be able to highlight selected PDF text in one of 4 colors (yellow
  default, green, blue, pink; positions stay on the same text at every zoom level), add a short
  note (max 500 characters) to a highlight or to a page, edit, recolor and delete them; all
  annotations persist locally across restarts.
- **FR-026**: The viewer MUST show a per-paper annotation list ordered by page, each entry with
  page, color and excerpt or note; activating an entry jumps to its page and marks it.
- **FR-027**: A paper chat MUST sit beside the viewer and answer only from that paper's own text,
  citing page numbers (activating one jumps the viewer). It is lazy: no text preparation and no
  model call before the first question for that paper. It refuses explicitly when the paper
  cannot answer (mock and live alike; mock answers only when the question shares a content word
  with the paper's text and cites the first page containing it) and refuses without a model call
  when the PDF is not ready or has no extractable text. The transcript lives in the page only.
- **FR-028**: The system MUST verify every cited page number exists in that paper and remove or
  flag any that does not; paper chat never cites other papers.
- **FR-029**: Library, viewer, annotations and paper chat MUST follow DESIGN.md, the v3 design
  brief (`docs/design/v3-library-brief.md`) and PRODUCT.md, stay on the one page, and be
  keyboard operable; destructive actions need confirmation.

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
- **Saved Paper** (v3): snapshot of a result card (see FR-015), source query, save time,
  directory, tag set. Independent of later triage results.
- **Stored PDF** (v3): one per saved paper; status pending/ready/failed, failure reason, size,
  page count. Deleted with its saved paper.
- **Tag** (v3): normalized keyword; many-to-many with saved papers.
- **Directory** (v3): user-named flat folder; built-in "Unsorted"; one per saved paper.
- **Annotation** (v3): saved paper, page, kind (highlight or page note), color, highlighted text
  and its position on the page, note text, created/updated time.
- **Paper Text** (v3): per-page text of a saved paper, prepared on the first paper-chat question
  and reused afterwards.
- **Paper Chat Turn** (v3, client-held): saved paper, question, answer, cited page numbers,
  refused flag. Kept per paper while the page is open; not persisted.

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
- **SC-009** (v3): 100% of saved papers in tests still show their save-time snapshot after a new
  search, a re-triage and an app restart.
- **SC-010** (v3): Saving one paper from two queries yields exactly one Library entry whose tags
  are the union of both queries' tags.
- **SC-011** (v3): In mock mode with no network, a saved paper's PDF is ready within 5 seconds and
  its first page shows in the in-page viewer within 2 seconds of opening, without leaving the
  page.
- **SC-012** (v3): In every tag-filter test, the list holds exactly the saved papers carrying all
  selected tags (and matching the title filter and directory, when set).
- **SC-013** (v3): 100% of highlights and notes created in tests are present, with the same page,
  color and text, after an app restart.
- **SC-014** (v3): In tests, 100% of paper-chat answers cite only page numbers that exist in that
  paper, 100% of out-of-paper questions are refused, and zero text preparation or model calls
  happen before the first question.
- **SC-015** (v3): After Unsave, no stored PDF, annotation or prepared paper text remains for that
  paper; after a directory delete, zero saved papers are lost.
- **SC-016** (v3): A user can go from a result card to reading its PDF in the Library in at most
  3 actions (save, open Library, open paper).

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
- (v3) Scope grows past constitution IV (max 3 stories / 15 FRs) and adds a second chat scope
  (one paper's text) next to principle III's result-set scope; PDFs are now kept for saved
  papers (supersedes the v1 "PDFs are not kept" answer for saved papers only). A constitution
  amendment (and a PRODUCT.md note by the orchestrator) is required before plan.
- (v3) The Library, viewer and paper chat are views of the same single page, not new pages.
- (v3) The PDF download runs inside the app process (no job queue); one retry on restart.
- (v3) The PDF viewer library is vendored into the app's static assets; which library, how the
  PDF is stored (disk file vs database), and any extra small viewer aids (for example find in
  document, remember last page) are decided at plan time from `docs/research/v3-library-preview.md`.
- (v3) Paper chat refuses with the same deliberate refusal state as the results chat.
