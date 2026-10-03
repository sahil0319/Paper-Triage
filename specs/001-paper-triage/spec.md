# Feature Specification: Paper Triage Assistant

**Feature Branch**: `001-paper-triage` (spec dir only; no git branch)

**Created**: 2026-10-01

**Status**: Draft (v4 amendment 2026-10-03; v3 amendment 2026-10-03; v2 amendment 2026-10-01)

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

**v4 input** (2026-10-03): visual redesign to the new Carbon-based DESIGN.md (commit 0da87be;
work list `docs/design/redesign-brief.md` items 1-34; rationale
`docs/design/redesign-recommendation.md`; font sources `docs/research/ibm-verify.md`). Visual
only: no new user stories, no copy, DOM, id, ARIA, route, keyboard or API change. The user
delegated all design decisions to the agents. In-flight fixes that the redesign must keep:
F-016 (highlight selection glitch), F-017 (old results stay interactive during a new search),
F-018 (long multi-keyword search fails; backend) and F-019 (preview opens on the paper chat tab).

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

- Q: Does saving again refresh the snapshot, and how do tags of later queries reach a saved
  paper? → A: The first snapshot and save time are kept (user-confirmed). A repeated save
  request only merges the current query's tags. Because the card's "Saved" control opens the
  unsave confirmation (design brief v3 Rev 2, L4), tags also merge automatically whenever a
  topic search returns an already saved paper.
- Q: When does the mock paper chat answer instead of refusing? → A: Same rule as the results
  chat: only when the question shares a content word (4+ letters, not a stop word) with the
  paper's text; it then cites the first page containing that word. Otherwise it refuses.
- Q: Does "Load 5 more" also clear the results chat transcript (FR-008a)? → A: Yes. Any change of
  the visible result set (new search, load-more, reload) clears the transcript and re-scopes the
  chat, so earlier answers never appear to cover a set they did not see. Shipped as F-006,
  F-007 and F-008.

User decisions (2026-10-03, relayed by the orchestrator):

- Q: May the constitution grow to fit v3? → A: Yes; constitution 2.0.0 raises the scope cap,
  adds the paper-chat scope to principle III and allows vendored front-end libraries.
- Q: Is the paper chat transcript stored? → A: No. It lives in the page only and resets on
  reload or when the preview closes. The prepared per-page paper text is stored and reused; it
  is deleted on Unsave.
- Q: What is the PDF size limit? → A: 50 MB per PDF.
- Q: Can direct (non-arXiv) PDF URLs be saved? → A: Yes, through the same fetch path, without
  the arXiv 3-second throttle, but with the same timeout, 50 MB cap and `%PDF-` check.
- Q: Which browsers must work? → A: Current evergreen Chrome, Firefox and Safari; the modern
  pdf.js build is used, not the legacy one.
- Q: Do highlights and notes feed the paper chat? → A: No, not in v3.
- Q: May a PDF library be vendored under the no-framework rule? → A: Yes (approved): pdf.js is
  vendored as static files, no CDN, no framework, no build step.

Design reconciliations (brief `docs/design/v3-library-brief.md` Rev 2; designer owns UI):

- Q: How many highlight colors? → A: Three: yellow (default), mint, peach. Highlight positions
  are relative to the page, so they stay on the same text at every zoom level.
- Q: How long may a directory name be? → A: 1-40 characters after trimming.
- Q: Is a tag one keyword or the whole topic string? → A: One normalized keyword token each
  (router default), not the whole topic string.
- Q: What does the paper chat do when the PDF is not ready? → A: The chat input is disabled with
  a plain reason; no abstract fallback. The API also refuses without a model call.
- Q: When must Unsave be confirmed? → A: Always, from the result card and from the Library;
  the confirmation says it deletes the saved PDF and any highlights and notes.
- Q: Is find-in-paper served by the API? → A: No. The page searches the PDF text it already
  loads (brief B8 dropped).

### Session 2026-10-03 (v4)

Non-interactive; the user delegated design decisions. Planner defaults:

- Q: Which design system applies? → A: The Carbon-based root DESIGN.md (v2.0,
  Paper-Triage-Carbon) is the single visual source of truth. It supersedes the Airtable-based
  v2 DESIGN.md (kept in `docs/design/DESIGN.airtable.md`) and the visual parts of
  `docs/design/brief-v2-redesign.md` and `docs/design/v3-library-brief.md`. Light theme only;
  dark mode is out of scope.
- Q: How many font files ship? → A: Eight woff2 files, about 125 KB, as listed in DESIGN.md
  section 3.1: Plex Sans 400 and 600 in Latin, Latin-extended and Greek, plus Plex Mono 400 in
  Latin and Latin-extended. The brief's "7 files" is a miscount; DESIGN.md wins. Greek in Mono
  falls back to the system monospace font. Total stays under the 250 KB cap.
- Q: How are the fonts obtained? → A: One build-time network fetch of the pinned packages
  (Fontsource 5.3.0 for Latin and Latin-extended, official IBM Plex Sans 1.1.0 for Greek),
  approved by the orchestrator. The files, the OFL licence and a source/version note are
  committed with the app. No package manager dependency is added and nothing is fetched at
  runtime.
- Q: How is "behaviour unchanged" verified? → A: The existing unit, API and browser suites keep
  passing. Only assertions on old visual values (for example the 0.4 dimming of previous
  results, old radii or old colours) change, to the DESIGN.md values, in the same task that
  changes the style, and the commit says so.
- Q: What is visual regression here? → A: Browser tests assert rendered style values (font
  family, radius, key colours, focus ring, highlight fill, contrast computed from rendered
  colours) at 390, 820 and 1440 px, and save screenshots of Triage, Library and Preview at
  those widths for the designer's re-audit. Screenshots are not pixel-compared: font
  rasterising differs between machines and an image-diff library would be a new dependency.
- Q: How do the in-flight fixes interact with the restyle? → A: F-016, F-017 and F-019 touch the
  same front-end files; front-end restyle work starts after their fix commits land, and the
  redesign keeps their behaviour (F-017 also matches DESIGN.md: previous results keep full
  opacity). F-018 is backend-only and already landed (d323ef9).
- Q: Does the redesign change class names or markup? → A: No. Existing selectors are restyled.
  The only markup addition is the link to the vendored font stylesheet.

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
3. **Given** a paper already saved from "diffusion distillation", **When** a search for
   "consistency models" returns it, **Then** its card shows "Saved", the Library still holds one
   entry, the original snapshot and save time are kept, and the tags now include the keywords of
   both queries (a repeated save request has the same effect).
4. **Given** a search made of arXiv IDs or PDF URLs, **When** the user saves a result, **Then**
   it is saved with no keyword tags.
5. **Given** a saved paper, **When** the user chooses Unsave (card or Library) and confirms, **Then**
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

**Independent Test**: Open a saved paper, highlight a line in mint, add a note to it, restart
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
4. **Given** a paper whose PDF is not ready or has no extractable text, **When** the user opens
   the chat, **Then** its input is disabled with a plain reason; a question sent anyway (direct
   API call) is refused with no model call.

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
- (v3) App restarts while a PDF is pending: on start, pending downloads are marked failed
  ("Download interrupted. Try again.") so the user can retry; never left pending forever.
- (v3) PDF with no text layer (scanned): it still displays; text highlights and paper chat are
  unavailable with a plain message; page notes still work.
- (v3) Unsave or directory delete while the viewer shows an affected paper: the viewer closes
  (unsave) or keeps the paper open under "Unsorted" (directory delete).
- (v3) Query made only of stop words or punctuation: the paper is saved with no tags.
- (v3) Tag search text matches no tag: a plain "no tags match" line; paper list unchanged.
- (v3) PDF still pending or failed: the paper chat input is disabled with the reason; a direct
  API call refuses without a model call.
- (v4) A font file fails to load: text renders in the metric-matched system fallback and the
  layout stays usable; no request goes to another host.
- (v4) A title or author name contains Latin-extended (Dvořák, Łukasz) or Greek (α, β)
  characters: they render in Plex Sans; Greek inside paper ids uses the system monospace font.
- (v4) Forced-colours mode: controls, notifications, chips, panels and the sheet keep a visible
  system-colour border, focus uses the system highlight colour, and highlights show as outlines.
- (v4) Two highlights overlap on a page: the multiplied fills darken where they overlap; both
  stay visible and the text stays legible.

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
- **FR-012** (v2; visual source updated in v4, see FR-030): The UI MUST follow DESIGN.md and
  PRODUCT.md, show rank and reason at a glance,
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
  snapshot and save time and merges the new query's tags; a topic search that returns an
  already saved paper also merges its tags. Cards of saved papers show "Saved" in any search
  and after reload.
- **FR-017**: Unsave (from the result card or the Library, always after explicit confirmation)
  MUST delete the saved entry, its stored PDF, its annotations and its prepared paper text;
  triage results for searches are kept.
- **FR-018**: On save, the system MUST download the paper's PDF in the background without
  delaying the save, store it locally, and expose status pending, ready or failed (with
  reason); failed downloads offer Retry. Limit 50 MB; content not starting with `%PDF-` fails. arXiv
  and direct PDF URLs use the same path; only arXiv downloads are throttled. Pending downloads
  left by a restart are marked failed on start (user retries). Mock/offline mode uses a fixture PDF and no
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
- **FR-023**: Users MUST be able to create, rename and delete flat directories (name 1-40
  characters after trimming, unique case-insensitive). A built-in "Unsorted" directory cannot be
  renamed or deleted. Each saved paper is in exactly one directory (default "Unsorted") and can
  be moved. Deleting a directory (after confirmation) moves its papers to "Unsorted". An "All"
  view lists every saved paper.
- **FR-024**: The viewer MUST offer previous/next page, go to page, "page n of m", zoom in/out,
  fit width, and a link to open the stored PDF in a new tab; closing it keeps the Library
  filters and scroll position.
- **FR-025**: Users MUST be able to highlight selected PDF text in one of 3 colors (yellow
  default, mint, peach; positions stay on the same text at every zoom level), add a short
  note (max 500 characters) to a highlight or to a page, edit, recolor and delete them; all
  annotations persist locally across restarts.
- **FR-026**: The viewer MUST show a per-paper annotation list ordered by page, each entry with
  page, color and excerpt or note; activating an entry jumps to its page and marks it.
- **FR-027**: A paper chat MUST sit beside the viewer and answer only from that paper's own text,
  citing page numbers (activating one jumps the viewer). It is lazy: no text preparation and no
  model call before the first question for that paper. It refuses explicitly when the paper
  cannot answer (mock and live alike; mock answers only when the question shares a content word
  with the paper's text and cites the first page containing it) and refuses without a model call
  when the PDF is not ready or has no extractable text (the page disables the chat input with
  the reason). The transcript lives in the page only and resets on reload or when the preview
  closes. Highlights and notes are not chat context.
- **FR-028**: The system MUST verify every cited page number exists in that paper and remove or
  flag any that does not; paper chat never cites other papers.
- **FR-029**: Library, viewer, annotations and paper chat MUST follow DESIGN.md, the v3 design
  brief (`docs/design/v3-library-brief.md`) and PRODUCT.md, stay on the one page, and be
  keyboard operable. Unsave and directory delete need explicit confirmation; deleting a
  highlight or note offers Undo for 8 seconds instead.

#### v4: Visual redesign

- **FR-030** (v4): The whole page (Triage, Library, Preview) MUST use the Carbon-based DESIGN.md
  as its only visual system while its behaviour stays unchanged:
  (a) every colour, type role, spacing, control size, radius, motion and shadow value comes
  from the DESIGN.md design tokens; no token of the previous design remains, and no literal
  colour is used outside the token layer (system colours in forced-colours mode excepted);
  (b) text uses IBM Plex Sans (weights 400 and 600) and IBM Plex Mono (400) from font files
  shipped with the app, together with their OFL licence and a source and version note; no font,
  style or script loads from another host at runtime;
  (c) text meets WCAG 2.1 AA contrast (at least 4.5:1, large rank numerals at least 3:1),
  control edges and the rank meter meet 3:1, every interactive element shows a visible focus
  indicator, and colour is never the only signal;
  (d) the three highlight fills (yellow, mint, peach) are drawn opaque with multiply blending,
  so they read at full strength on PDF pages and the glyphs beneath stay legible; stored colour
  names do not change;
  (e) when the user prefers reduced motion, no transition, keyframe flash or sheet slide runs,
  and each motion has a static equivalent with the same meaning; in forced-colours mode,
  controls, panels and highlights keep visible borders or outlines;
  (f) copy, DOM order, element ids, ARIA, hash routes, keyboard paths, API calls and stored data
  are unchanged, including the fixes F-016 (highlight selection), F-017 (previous results stay
  at full opacity and interactive during a new search), F-018 (long multi-keyword topic
  searches succeed) and F-019 (every preview opens on the "Ask this paper" tab; the paper chat
  still loads nothing before the first question).

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
- **SC-017** (v4): In every browser test run at 390, 820 and 1440 px, zero requests leave the
  local app, the shipped Plex faces are loaded and used for body text and paper ids, and the
  shipped font files total at most 250 KB.
- **SC-018** (v4): 100% of the sampled text and background pairs in the rendered page (titles,
  reasons, secondary and tertiary text, links, nav and tabs, error and refusal states, cite
  chips) measure at least 4.5:1, and sampled control edges and the rank meter measure at least
  3:1.
- **SC-019** (v4): Each of the 3 highlight colours renders on a PDF page as an opaque fill equal
  to its DESIGN.md value with multiply blending, and the highlight list prints its colour name.
- **SC-020** (v4): With reduced motion requested, zero animations or transitions run on flashed
  rows, the disclosure, the bottom sheet and row removal, while the cited-row, new-row and
  working states stay visible.
- **SC-021** (v4): The pre-redesign unit, API and browser suites pass, with only assertions on
  old visual values updated, and the F-016, F-017 and F-019 browser checks pass on the
  redesigned page.
- **SC-022** (v4): Screenshots of Triage, Library and Preview at 390, 820 and 1440 px are produced
  by the final browser run, and the designer's re-audit of them ends with zero blocking items.

## Assumptions

- Single local user; no auth, multi-user, or deployment (constitution IV).
- arXiv is the only search source; other hosts are supported only as direct PDF URLs.
- Two-column PDF text may be out of order; acceptable for triage.
- Model chosen by env setting with a documented default; no model id hard-coded elsewhere.
- Text extraction uses a permissive-license library behind one swap point (AGPL alternative not
  bundled).
- Visual style follows DESIGN.md and PRODUCT.md. (v2 used an Airtable-style DESIGN.md with a
  system-font stack; superseded in v4 by the Carbon-based DESIGN.md with vendored, OFL-licensed
  IBM Plex fonts.) No external assets are loaded.
- The searching status is client-side only (cycling phase text plus elapsed time); it does not
  claim real per-paper progress, so no progress endpoint is needed.
- The current result set lives in the page, not the server; a reload rebuilds it from the
  last topic's stored results.
- (v3) Constitution 2.0.0 covers v3: scope cap 9 stories / 32 FRs (this spec: 9 / 31), a
  second chat scope (one paper's text) in principle III, vendored front-end libraries, and PDFs
  kept for saved papers (supersedes the v1 "PDFs are not kept" answer for saved papers only).
  The PRODUCT.md Library section is drafted separately by the designer for user review.
- (v3) The Library, viewer and paper chat are views of the same single page, not new pages.
- (v3) The PDF download runs inside the app process (no job queue); a download cut off by a
  restart is marked failed and retried only by the user.
- (v3) The PDF viewer library is vendored into the app's static assets; which library, how the
  PDF is stored (disk file vs database), and any extra small viewer aids (for example find in
  document, remember last page) are decided at plan time from `docs/research/v3-library-preview.md`.
- (v3) Paper chat refuses with the same deliberate refusal state as the results chat.
- (v4) Constitution 2.0.0 covers v4 unchanged: the redesign adds one requirement (FR-030;
  this spec: 9 stories / 32 FRs, at the cap) and no user story. Vendored font files fall under
  principle I's rule for vendored static assets (same origin, licence and pinned version kept,
  no CDN). PRODUCT.md needs no change.
- (v4) Current evergreen Chrome, Firefox and Safari support every style feature DESIGN.md
  allows; no fallback for older browsers is planned.
