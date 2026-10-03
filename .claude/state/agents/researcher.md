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
