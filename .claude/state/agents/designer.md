
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

## 2026-10-03 v3 audit re-check (resumed, done)
- goal: write Re-check section in docs/design/v3-audit.md.
- status: done. 13/13 pass. Mobile toolbar 4 rows/231px accepted. Score 17/20 (18 after R1).
- R1 fix (current, for frontend-builder): move `<button id="pv-sheet-open">` in index.html out of `.pv-bar` to a direct child of `.pv-toolbar` AFTER `#pv-controls` (NOT inside #pv-controls: it is hidden in failed/downloading/not-saved states). Keep CSS order 10 (tablet) / 9 (mobile); >=1024 stays display:none. Verify it shows in failed state <1024.
- next: frontend-builder lands R1; no further designer pass needed.

## 2026-10-03 redesign criteria (phase 1 of 2)
- goal: criteria + weighted rubric for picking a replacement DESIGN.md from the awesome-design collection.
- status: done. docs/design/redesign-criteria.md. No screenshots (audit evidence reused). No server started.
- findings: current Airtable = marketing system; 21 tokens unused; muted 9.6:1 vs body 11.8:1 (no ladder); body 14/1.25 too tight; Haas proprietary, not shipped; highlight fills only 1.19/1.22/1.32:1 on white; no dark, no motion, no states. Rubric: gates G1-G4, C1-C10 weights 15/15/12/12/8/10/10/6/7/5. Fonts must be OFL/Apache woff2, Latin Ext + Greek + tnum, <=3 families, ~250 KB.
- next: phase 2 when docs/research/redesign-design-md-options.md lands; output docs/design/redesign-recommendation.md (top pick + 2 alternates, font pairing, overlay re-map, highlight trio).

## 2026-10-03 redesign recommendation (phase 2)
- goal: score researcher shortlist (docs/research/redesign-design-md-options.md) with rubric; recommend pick + 2 alternates.
- status: done. docs/design/redesign-recommendation.md.
- findings: ibm 82 (top), vercel 68, notion 66, mintlify 65, claude 61 (AI-chat look anti-ref, coral 3.1:1), linear/raycast out G1 (dark only). Fonts for pick: Plex Sans 400/500/600 + Plex Mono 400/500 ~100 KB latin, latin-ext + greek via unicode-range. Highlights: keep names, opaque multiply Yellow #ffde66 / Mint #9fe0c0 / Peach #ffc29e. Q1 light only now, dark later via light-dark(); Q2 sans only (Plex Serif optional); Q3 yes budget + latin-ext, cap 250 KB. Tokens unverified vs raw files; Carbon (C) values from public Carbon.
- next: user chooses + drops DESIGN.md; designer verifies raw tokens, writes docs/design/redesign-brief.md; planner tasks.
- update: user delegated; final pick ibm marked, Q1-3 decided, raw URL listed; next steps rewritten (researcher fetch, designer adapts root DESIGN.md + redesign-brief).

## 2026-10-03 phase 3: adopt Carbon DESIGN.md (user-approved rewrite)
- goal: fetch verbatim IBM source, back up Airtable, write new root DESIGN.md + redesign brief, commit.
- status: done. Commit 0da87be (DESIGN.md, docs/design/{DESIGN.airtable,ibm-DESIGN.source,redesign-criteria,redesign-recommendation,redesign-brief}.md). curl of raw GitHub worked (orchestrator-directed; role rule says curl localhost only, noted).
- findings/decisions: ink-subtle #6f6f6f (src #8c8c8c 3.4:1); body-compact 14/18; Sans 400/600 + Mono 400 only (~125 KB, not 203: Carbon uses no 500); @font-face in static/vendor/fonts/plex.css so own-CSS @font-face test stays valid; highlights opaque multiply #ffde66/#9fe0c0/#ffc29e; light only; breakpoints kept 768/1024. Behaviour B-a (preview default tab Ask this paper, lazy) and B-b (old results interactive, no dim) written into DESIGN.md 8.4/8.8 + brief.
- next: planner turns redesign-brief.md items 1-34 into tasks (T-R1..T-R8); [BE] woff2 mimetypes.add_type.

## 2026-10-04 v4 audit (Carbon redesign, HEAD 14af76e)
- goal: one-pass design audit of T066-T076; write docs/design/v4-audit.md in v3-audit format.
- status: done. Score 17/20 (a11y 3, perf 4, responsive 3, theming 4, integrity 3). 18 after items 1-2, 19 after 1-6. Server 8767 killed.
- findings: BLOCKS 1) `.rail__count` ink-subtle on current item #e0e0e0 = 3.81:1; 2) forced colours paint transparent 2px underline on all `.views a` and `.pv-tab`, so current/selected has weight only. Polish 3) `#pv-back` outline, spec ghost; 4) Create/rename Save (library.js:459) and Save note (annotations.js:652) outline, spec primary; 5) `.confirm` no bottom margin, mobile Save 4px over authors; 6) not-saved Preview left-aligned, heading-xs, h1 "Preview". Nice-to-have 5. B-a, B-b, v3 R1 pass; scrollWidth = viewport everywhere.
- incident: first server start lacked PAPER_TRIAGE_DB, so it used ./paper_triage.db (gitignored dev DB). Writes there: one mock triage "diffusion models video", 4 POST /api/library (all 200 already saved, tags merged), 2 directory POSTs (409), and move 2401.00002 into directory 1 "network" (prior directory unknown). Restarted with temp DB for the audit. Note for future runs: set PAPER_TRIAGE_DB too.
- next: frontend-builder fixes items 1-2 (acceptance), then 3-6 if wanted; no designer confirm pass needed unless asked.
