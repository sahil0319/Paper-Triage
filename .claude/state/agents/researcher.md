# researcher state

## 2026-10-01 paper-triage
- goal: one-page research note, 4 sections + clarification questions.
- status: done. File docs/research/paper-triage.md.
- findings: arXiv 3s/1 conn limit [V]; pypdf default, PyMuPDF AGPL optional; messages.parse + Pydantic [V]; Citations API incompat w/ structured outputs (400) [V]; use sentinel refusal + id validation.
- unverified: pdf URL pattern, pypdf/pdfminer license, prompt patterns (prior knowledge).
- next: planner.

## 2026-10-03 v3-library-preview
- goal: research note for v3 saved-papers library + in-app PDF preview (7 questions).
- status: done. File docs/research/v3-library-preview.md.
- findings: vendor pdfjs-dist 6.3.289 legacy (~1.8 MB, Apache-2.0), canvas+TextLayer own viewer; rect-fraction highlights + quote; PDFs as files on disk, FileResponse (Starlette 1.7.0 has Range); export.arxiv.org + 3s throttle + UA; pypdf per-page text, whole-paper + prompt caching + [p.N] cites. Guard gotchas: no `import(` in app.js, vendor/ must be exempt, register .mjs MIME.
- unverified: .mjs MIME on py3.11, typical arXiv size (0.5-5 MB), tokens/paper estimate.
- next: planner + designer.

## 2026-10-03 redesign-design-md-options
- goal: catalog VoltAgent/awesome-design-md entries, fonts, prior art for redesign.
- status: done. File docs/research/redesign-design-md-options.md.
- findings: repo has 74 design-md dirs (README says 73; slack unlisted). No Perplexity/Readwise/Obsidian/Arc/academic entry. Shortlist: claude, notion, mintlify, ibm, cursor, linear.app, raycast, vercel, wired, stripe. Most fonts proprietary; free: Inter, Geist, Plex, JetBrains Mono. Font sizes via jsdelivr listing.
- unverified: entry details via summarizer; Inter/Plex tnum support; Readwise colour support (blog vs docs conflict).
- next: designer ranks options.

## 2026-10-03 ibm-verify
- goal: save ibm DESIGN.md, verify tokens vs redesign-recommendation.md, Plex font sources.
- status: done. Files docs/research/ibm-DESIGN.md (extract, NOT verbatim: no shell, WebFetch refuses verbatim; curl command in header), docs/research/ibm-verify.md.
- findings: mismatches: ink-subtle #8c8c8c fails AA; body-sm lh 1.29 = 18px not 20px; no notification/tag/hover/motion/control-height tokens in file. Fontsource Plex Sans/Mono have NO greek; official @ibm/plex-sans 1.1.0 split has Greek (8.8-9.1 KB/weight). Total ~203 KB < 250 cap. OFL-1.1.
- unverified: official split exact filenames, @ibm/plex-mono greek, IBM/plex licence path.
- next: designer; someone with shell runs the curl for the verbatim file.
