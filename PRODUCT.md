# PRODUCT.md

## Register
product (tool UI, not marketing)

## Product
Paper Triage Assistant. Give a topic/keywords (or arXiv IDs / PDF URLs). It fetches papers, summarizes, critiques (weak claims, overclaims, missing baselines), ranks relevance 0-10 with a reason. Then chat: grounded Q&A over stored papers only.

## Users
Single researcher/engineer skimming a pile of new papers. Local, no auth.

## Purpose
Cut a reading list to the few papers worth opening, fast, with honest critique.

## Brand / tone
Calm, precise, skeptical. Plain words. No hype, no emoji.

## Anti-references
Generic AI-chat gloss, gradient hero, card-grid-of-everything, dashboard clutter.

## Strategic design principles
1. One page. Input top, ranked list, chat beside/below.
2. Rank + reason visible at a glance; critique one click away.
3. Every chat answer shows paper-id citations; refusals look intentional.
4. Offline/mock mode visibly labeled.
5. Accessible: keyboard, contrast, no motion dependence.

## Library
Keep the few papers worth reading. Read, mark and question them in place.

- Save any ranked paper, from arXiv or a direct PDF URL. Saving keeps the card as shown (rank, reason, critique) and a local PDF copy.
- Tags are the search keywords that surfaced a paper. Filter by tags (all must match) or by title.
- Directories are flat and user-named. Each paper lives in one; new papers go to Unsorted.
- Preview reads the PDF in the page: page nav, zoom, find, three highlight colours, short notes, notes export.
- Per-paper chat answers from that paper only and cites pages. Nothing loads until the first question. The chat is not saved; it clears on close or reload.
- Removing a paper deletes its PDF, highlights and notes, after a confirm.

### Library principles
1. Still one page. Library and preview are views, not new pages.
2. Filing is fast and keyboard-reachable; no drag-only actions.
3. Highlight colour is never the only signal.
4. No PDF, no chat: say why instead of guessing from the abstract.
5. Modern evergreen browsers only.
