
## 2026-10-01 brief-v2-redesign (wave 1 design)
- goal: full redesign brief to new Airtable DESIGN.md + running indicator, paper links, load 5 more, chat scope.
- status: done. docs/design/brief-v2-redesign.md, items [FE] D1-D35.
- findings: API lacks pdf_url (B1); no load-more paging (B2); chat answers over top_k of ALL stored papers, not per search (B3). Deviations from DESIGN.md listed in brief section 0 (fonts, input edge #8e939c for 3:1, 12px not pill, 32/48 rhythm).
- next: planner adds T027+ incl. NEEDS-BE B1-B3; frontend-builder implements D1-D35.

## 2026-10-03 v3-library-brief
- goal: v3 brief: Save on result card, Library (tags, directories), PDF preview (highlights, notes, lazy per-paper chat).
- status: done. docs/design/v3-library-brief.md, items [FE] L1-L24, NEEDS-BE B1-B8, assumptions sec 10. Aligned to docs/research/v3-library-preview.md (pdf.js, fractional rects, [p.N], export md, find).
- findings: no nav existed; brief adds Triage/Library view links + hash routes. Open decisions: tag unit (whole topic string assumed), item-only runs no tag, chat without PDF (disabled assumed), unsave cascade, vendored pdf.js needs spec exception.
- next: planner folds B1-B8 + sec 10 into spec/tasks; then frontend-builder.

## 2026-10-03 v3-library-brief Rev 2
- goal: apply user decisions; draft PRODUCT.md Library section.
- status: done. Rev 2 note at top of docs/design/v3-library-brief.md. Draft at docs/design/product-md-library-draft.md (PRODUCT.md untouched).
- findings: chat page-only (resets on reload/close), unsave always confirms + deletes PDF/highlights/notes, no-PDF chat disabled, evergreen only, direct PDF saveable, 3 colours.
- next: planner picks up Rev 2 deltas (L4, L6, L13, L20, B2, B7, sec 10); user pastes PRODUCT draft.

## 2026-10-03 PRODUCT.md Library section (one-time exception, user-approved via orchestrator)
- goal: append docs/design/product-md-library-draft.md body to PRODUCT.md, commit only that file.
- status: done. Commit 374ee23 "docs(product): add Library section", 17 insertions, PRODUCT.md only.
- next: none.

## 2026-10-03 v3 UI audit
- goal: visual/UX audit of shipped v3 (Save, Library, Preview, paper chat) vs v3 brief Rev 2.
- status: done. docs/design/v3-audit.md. 13 must-fix [FE] (L8, L9, L11.5, L11.6/L13, L14/L10d, L3/L11.1, L15/L16 mobile toolbar, L15 tablet, L16 heights+split, L23, L18, L19, L22), 5 nice-to-have. Score 14/20.
- findings: worst = mobile preview toolbar 41% of viewport; rail grid overflow; row Directory select scrollWidth 402 @390. Mock paper-chat refuses starters + triage refusal wording (planner note, NEEDS-BE). Server 8767 killed; screenshots in session scratchpad.
- next: frontend-builder fixes must-fix list; one confirm pass after.

## 2026-10-03 v3 audit re-check (PAUSED by user)
- goal: re-check 13 must-fix after 6e1b9a1 + 22781d9; add "Re-check" section to docs/design/v3-audit.md.
- status: paused. Screenshots done (desktop/tablet/mobile, shots2 in session scratchpad). Server 8767 killed. v3-audit.md NOT updated (left as is per user).
- findings so far: items 1-13 all pass visually. Mobile toolbar deviation (4 rows, 231px) acceptable: accept. One regression: #pv-sheet-open moved by CSS order only (display: contents), so focus order mismatches visual order at <1024. Fix: move #pv-sheet-open in DOM to .pv-toolbar after #pv-controls (not inside it; controls are hidden in failed state). Nice-to-have: "Highlights and chat" label sits ~5px above center. Proposed score 17/20.
- next: on resume, write Re-check section from these findings (no new screenshots needed), then NEXT:frontend-builder for the focus-order fix.
