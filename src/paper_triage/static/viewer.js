/* Paper Triage PDF viewer (ES module, v3 T055). Canvas + selectable text layer per page, rendered
   only near the viewport. pdf.js is vendored (static/vendor/pdfjs, same-origin worker); no CDN.
   Shares helpers with app.js through window.PT. Text is set with textContent only. */
import * as pdfjsLib from "./vendor/pdfjs/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "/vendor/pdfjs/pdf.worker.min.mjs";

const PT = window.PT;
const $ = (id) => document.getElementById(id);

const el = {
  preview: $("preview"),
  controls: $("pv-controls"),
  well: $("pv-pages"),
  stage: $("pv-stage"),
  external: $("pv-external"),
  prev: $("pv-prev"),
  next: $("pv-next"),
  pageInput: $("pv-page-input"),
  pageOf: $("pv-page-of"),
  zoom: $("pv-zoom"),
  zoomIn: $("pv-zoom-in"),
  zoomOut: $("pv-zoom-out"),
  findBtn: $("pv-find-btn"),
  find: $("pv-find"),
  findInput: $("pv-find-input"),
  findCount: $("pv-find-count"),
  findClose: $("pv-find-close"),
  findResults: $("pv-find-results"),
};

const CSS_PER_PT = 96 / 72; // PDF point to CSS pixel: "100%" is the size browsers show
const ZOOMS = [50, 75, 100, 125, 150, 200];
const WELL_PAD = 16;
const MAX_CANVAS_PIXELS = 16 * 1024 * 1024;
const POLL_MS = window.__PT_POLL_MS || 3000;
const OPENING_DELAY_MS = 300;

let cur = null; // the paper being shown; null when the preview is closed
let token = 0; // bumped on every open/close; async work for an older token is dropped

const h = PT.h;

// ---- helpers ----

function statusKey(item) {
  const p = item.pdf || {};
  return `${p.status}|${p.error || ""}`;
}

function pdfUrl(id) {
  return `/api/library/pdf?paper_id=${encodeURIComponent(id)}`;
}

function setStage(...children) {
  PT.clear(el.stage);
  children.forEach((c) => c && el.stage.appendChild(c));
  el.stage.hidden = !children.length;
}

function sourceUrl(item) {
  return item.abs_url || item.pdf_url || null;
}

function extLink(text, href, extra) {
  return h(
    "a",
    { class: `ext-link ${extra || ""}`.trim(), href, target: "_blank", rel: "noopener noreferrer" },
    text,
  );
}

function stale(t) {
  return !cur || cur.token !== t;
}

// ---- open / close ----

function close() {
  token++;
  if (cur) {
    window.clearInterval(cur.pollT);
    window.clearTimeout(cur.openingT);
    if (cur.io) cur.io.disconnect();
    if (cur.ro) cur.ro.disconnect();
    if (cur.pages) cur.pages.forEach((p) => p.task && p.task.cancel());
    if (cur.loadTask) cur.loadTask.destroy().catch(() => {});
    el.well.removeEventListener("scroll", onScroll);
  }
  cur = null;
  resetFind();
  PT.clear(el.well);
  el.well.hidden = true;
  el.controls.hidden = true;
  el.external.hidden = true;
  setStage();
  setPanelHidden();
}

function setPanelHidden() {
  PT.refreshSkipLinks();
}

function open(item) {
  if (cur && cur.id === item.paper_id && cur.key === statusKey(item)) return;
  const sameKey = cur && cur.id === item.paper_id;
  const keepZoom = sameKey ? cur.mode : null;
  close();
  cur = { id: item.paper_id, item, key: statusKey(item), token, mode: keepZoom || "fit-width", pages: [] };
  const status = (item.pdf && item.pdf.status) || "none";
  if (status === "ready") showPdf();
  else if (status === "pending") showDownloading();
  else showUnavailable();
  setPanelHidden();
}

// ---- states (brief L21) ----

function showDownloading() {
  const c = cur;
  el.well.hidden = true;
  const card = h(
    "div",
    { class: "working pv-card", role: "group", "aria-label": "Downloading the PDF" },
    h(
      "div",
      { class: "working__row" },
      h("span", { class: "working__glyph" }, PT.rayGlyph(20)),
      h("span", { class: "working__verb" }, "Downloading the PDF…"),
    ),
    h("p", { class: "working__note" }, "You can read the critique below while you wait."),
  );
  const crit = PT.details(c.item);
  if (crit) crit.open = true;
  setStage(card, crit);
  c.pollT = window.setInterval(() => poll(c.token), POLL_MS);
}

function poll(t) {
  if (stale(t)) return;
  PT.loadLibrary().then(() => {
    if (stale(t)) return;
    const it = PT.libItem(cur.id);
    if (!it) return;
    if (statusKey(it) !== cur.key) {
      const ready = it.pdf && it.pdf.status === "ready";
      open(it);
      if (ready) PT.announce("PDF ready.");
    }
  });
}

function showUnavailable() {
  const c = cur;
  el.well.hidden = true;
  const detail = h("p", { class: "alert__detail" }, (c.item.pdf && c.item.pdf.error) || "Try again in a moment.");
  const retry = h("button", { type: "button", class: "btn btn--on-dark" }, "Try again");
  retry.addEventListener("click", () => {
    retry.setAttribute("aria-disabled", "true");
    PT.postJSON("/api/library/retry", { paper_id: c.id })
      .then((data) => {
        if (stale(c.token)) return;
        const it = PT.libItem(c.id) || c.item;
        it.pdf = (data && data.pdf) || { status: "pending", error: null, pages: null };
        open(it);
      })
      .catch((err) => {
        retry.removeAttribute("aria-disabled");
        detail.textContent = PT.failMessage(err);
      });
  });
  const src = sourceUrl(c.item);
  const alert = h(
    "div",
    { class: "alert pv-card", role: "alert" },
    h("p", { class: "alert__title" }, "This PDF could not be downloaded."),
    detail,
    h("div", { class: "alert__actions" }, retry, src ? extLink("Open the source page", src, "ext-link--on-dark") : null),
  );
  setStage(alert);
}

function showRenderFailed() {
  const c = cur;
  PT.clear(el.well);
  el.well.hidden = true;
  el.controls.hidden = true;
  const link = extLink("Open PDF in new tab", pdfUrl(c.id), "ext-link--on-dark");
  setStage(
    h(
      "div",
      { class: "alert pv-card", role: "alert" },
      h("p", { class: "alert__title" }, "This PDF could not be displayed."),
      h("p", { class: "alert__detail" }, "The file may be damaged or use features the viewer does not support."),
      h("div", { class: "alert__actions" }, link),
    ),
  );
}

// ---- the PDF ----

async function showPdf() {
  const c = cur;
  el.external.href = pdfUrl(c.id);
  el.external.hidden = false;
  el.well.hidden = true;
  c.openingT = window.setTimeout(() => {
    if (!stale(c.token) && !c.doc) setStage(h("p", { class: "pv-opening" }, "Opening PDF…"));
  }, OPENING_DELAY_MS);
  let proxies;
  try {
    c.loadTask = pdfjsLib.getDocument({ url: pdfUrl(c.id), isEvalSupported: false });
    c.doc = await c.loadTask.promise;
    proxies = await Promise.all(Array.from({ length: c.doc.numPages }, (_, i) => c.doc.getPage(i + 1)));
  } catch {
    window.clearTimeout(c.openingT);
    if (!stale(c.token)) showRenderFailed();
    return;
  }
  window.clearTimeout(c.openingT);
  if (stale(c.token)) return;
  setStage();
  buildPages(proxies);
}

function buildPages(proxies) {
  const c = cur;
  el.well.hidden = false;
  el.controls.hidden = false;
  PT.clear(el.well);
  c.pages = proxies.map((proxy, i) => {
    const vp = proxy.getViewport({ scale: 1 });
    const label = h("span", { class: "pdf-page__label", "aria-hidden": "true" }, `Page ${i + 1}`);
    const canvas = h("canvas", { "aria-hidden": "true" });
    const text = h("div", { class: "textLayer" });
    const hl = h("div", { class: "hl-layer", "aria-hidden": "true" });
    const sec = h("section", { class: "pdf-page", "data-page": String(i + 1), "aria-label": `Page ${i + 1}` }, label, canvas, text, hl);
    el.well.appendChild(sec);
    return { n: i + 1, proxy, w: vp.width, h: vp.height, sec, canvas, text, hl, label, scale: 0, drawn: 0, task: null, textDone: false };
  });
  c.page = 1;
  el.pageOf.textContent = `of ${c.pages.length}`;
  setFindReady(true);
  el.zoom.value = String(c.mode);
  c.io = new IntersectionObserver(onIntersect, { root: el.well, rootMargin: "200% 0px" });
  c.pages.forEach((p) => c.io.observe(p.sec));
  c.ro = new ResizeObserver(() => {
    if (c.mode === "fit-width" || c.mode === "fit-page") relayout();
  });
  c.ro.observe(el.well);
  el.well.addEventListener("scroll", onScroll, { passive: true });
  relayout();
  setPageUi();
}

// ---- layout and zoom ----

function pageScale(p, mode) {
  const availW = Math.max(120, el.well.clientWidth - 2 * WELL_PAD);
  if (mode === "fit-width") return availW / p.w;
  if (mode === "fit-page") {
    const availH = Math.max(120, el.well.clientHeight - 2 * WELL_PAD);
    return Math.min(availW / p.w, availH / p.h);
  }
  return (Number(mode) / 100) * CSS_PER_PT;
}

function relayout() {
  const c = cur;
  if (!c || !c.pages.length) return;
  const anchor = anchorPoint();
  c.pages.forEach((p) => {
    p.scale = pageScale(p, c.mode);
    p.sec.style.width = `${Math.round(p.w * p.scale)}px`;
    p.sec.style.height = `${Math.round(p.h * p.scale)}px`;
    p.text.style.setProperty("--total-scale-factor", String(p.scale));
    p.text.style.setProperty("--scale-factor", String(p.scale));
  });
  restoreAnchor(anchor);
  c.pages.forEach((p) => {
    if (p.drawn && p.drawn !== p.scale) drawPage(p);
  });
  syncZoomUi();
}

// The current page and how far into it the top of the well sits, kept across a zoom.
function anchorPoint() {
  const c = cur;
  const p = c.pages[c.page - 1];
  if (!p || !p.sec.offsetHeight) return null;
  return { n: c.page, frac: (el.well.scrollTop - p.sec.offsetTop + WELL_PAD) / p.sec.offsetHeight };
}

function restoreAnchor(a) {
  if (!a) return;
  const p = cur.pages[a.n - 1];
  el.well.scrollTop = Math.max(0, p.sec.offsetTop - WELL_PAD + a.frac * p.sec.offsetHeight);
}

function effectivePercent() {
  const p = cur.pages[cur.page - 1] || cur.pages[0];
  return (p.scale / CSS_PER_PT) * 100;
}

function setMode(mode) {
  if (!cur || !cur.pages.length) return;
  cur.mode = mode;
  relayout();
  setPageUi();
}

function stepZoom(dir) {
  if (!cur || !cur.pages.length) return;
  const now = effectivePercent();
  const next = dir > 0 ? ZOOMS.find((z) => z > now + 0.5) : [...ZOOMS].reverse().find((z) => z < now - 0.5);
  if (next) setMode(String(next));
}

function syncZoomUi() {
  const c = cur;
  el.zoom.value = String(c.mode);
  const now = effectivePercent();
  setAria(el.zoomIn, now >= ZOOMS[ZOOMS.length - 1] - 0.5);
  setAria(el.zoomOut, now <= ZOOMS[0] + 0.5);
}

function setAria(btn, disabled) {
  if (disabled) btn.setAttribute("aria-disabled", "true");
  else btn.removeAttribute("aria-disabled");
}

// ---- rendering near the viewport ----

function onIntersect(entries) {
  entries.forEach((e) => {
    const p = cur && cur.pages[Number(e.target.getAttribute("data-page")) - 1];
    if (!p) return;
    if (e.isIntersecting) drawPage(p);
    else releasePage(p);
  });
}

async function drawPage(p) {
  const c = cur;
  const t = c.token;
  const scale = p.scale;
  if (!scale || p.drawn === scale || p.drawing === scale) return;
  if (p.task) p.task.cancel();
  p.drawing = scale;
  const viewport = p.proxy.getViewport({ scale });
  let dpr = window.devicePixelRatio || 1;
  while (dpr > 1 && viewport.width * viewport.height * dpr * dpr > MAX_CANVAS_PIXELS) dpr -= 0.5;
  // Draw into a fresh canvas and swap it in, so a zoom never flashes a blank page.
  const canvas = h("canvas", { "aria-hidden": "true" });
  canvas.width = Math.floor(viewport.width * dpr);
  canvas.height = Math.floor(viewport.height * dpr);
  const task = p.proxy.render({
    canvasContext: canvas.getContext("2d"),
    viewport,
    transform: dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null,
  });
  p.task = task;
  try {
    await task.promise;
  } catch {
    if (p.drawing === scale) p.drawing = 0;
    return; // cancelled by a newer render or a release
  }
  if (stale(t) || p.drawing !== scale) return;
  p.task = null;
  p.drawing = 0;
  p.drawn = scale;
  p.sec.replaceChild(canvas, p.canvas);
  p.canvas = canvas;
  p.sec.classList.add("is-drawn");
  if (!p.textDone) drawText(p, t);
}

async function drawText(p, t) {
  p.textDone = true;
  try {
    PT.clear(p.text);
    const viewport = p.proxy.getViewport({ scale: p.scale });
    const layer = new pdfjsLib.TextLayer({
      textContentSource: p.proxy.streamTextContent(),
      container: p.text,
      viewport,
    });
    await layer.render();
    if (!stale(t)) p.sec.classList.add("has-text");
  } catch {
    p.textDone = false;
  }
}

function releasePage(p) {
  if (p.task) p.task.cancel();
  p.task = null;
  p.drawing = 0;
  if (!p.drawn && !p.textDone) return;
  p.drawn = 0;
  p.textDone = false;
  const empty = h("canvas", { "aria-hidden": "true" });
  p.sec.replaceChild(empty, p.canvas);
  p.canvas = empty;
  PT.clear(p.text);
  p.sec.classList.remove("is-drawn", "has-text");
}

// ---- current page, jumps ----

let scrollRaf = 0;
function onScroll() {
  if (scrollRaf) return;
  scrollRaf = window.requestAnimationFrame(() => {
    scrollRaf = 0;
    if (!cur || !cur.pages.length) return;
    const top = el.well.scrollTop;
    const bottom = top + el.well.clientHeight;
    let best = cur.page;
    let bestVisible = -1;
    for (const p of cur.pages) {
      const y0 = p.sec.offsetTop;
      const y1 = y0 + p.sec.offsetHeight;
      const visible = Math.min(y1, bottom) - Math.max(y0, top);
      if (visible > bestVisible) {
        bestVisible = visible;
        best = p.n;
      }
      if (y0 > bottom) break;
    }
    if (best !== cur.page) {
      cur.page = best;
      setPageUi();
    }
  });
}

function clampPage(n) {
  const max = cur ? cur.pages.length : 1;
  n = Math.round(Number(n));
  if (!Number.isFinite(n)) return cur ? cur.page : 1;
  return Math.max(1, Math.min(max, n));
}

let pageInputDirty = false; // the user is typing a page number: do not overwrite it

function setPageUi() {
  const c = cur;
  if (!c || !c.pages.length) return;
  if (!pageInputDirty) el.pageInput.value = String(c.page);
  setAria(el.prev, c.page <= 1);
  setAria(el.next, c.page >= c.pages.length);
}

function goToPage(n, opts) {
  if (!cur || !cur.pages.length) return false;
  n = clampPage(n);
  const p = cur.pages[n - 1];
  el.well.scrollTop = Math.max(0, p.sec.offsetTop - WELL_PAD);
  cur.page = n;
  el.pageInput.value = String(n);
  setPageUi();
  if (opts && opts.flash) flashPage(n);
  return true;
}

function flashPage(n) {
  const p = cur && cur.pages[n - 1];
  if (!p) return;
  p.sec.classList.remove("is-flash");
  void p.sec.offsetWidth;
  p.sec.classList.add("is-flash");
  window.setTimeout(() => p.sec.classList.remove("is-flash"), PT.reducedMotion() ? 2000 : 1600);
}

// ---- controls ----

el.prev.addEventListener("click", () => {
  if (cur && cur.page > 1) goToPage(cur.page - 1);
});
el.next.addEventListener("click", () => {
  if (cur && cur.page < cur.pages.length) goToPage(cur.page + 1);
});
el.pageInput.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") {
    ev.preventDefault();
    commitPageInput();
  } else if (ev.key === "Escape") {
    pageInputDirty = false;
    el.pageInput.value = String(cur ? cur.page : 1);
  }
});
el.pageInput.addEventListener("input", () => {
  pageInputDirty = true;
});
el.pageInput.addEventListener("blur", commitPageInput);
el.pageInput.addEventListener("focus", () => el.pageInput.select());

function commitPageInput() {
  pageInputDirty = false;
  if (!cur || !cur.pages.length) return;
  const n = clampPage(el.pageInput.value);
  el.pageInput.value = String(n);
  if (n !== cur.page) goToPage(n);
}

el.zoom.addEventListener("change", () => setMode(el.zoom.value));
el.zoomIn.addEventListener("click", () => stepZoom(1));
el.zoomOut.addEventListener("click", () => stepZoom(-1));

// Keys work inside the pages region only: never global, never with Ctrl or Cmd.
el.well.addEventListener("keydown", (ev) => {
  if (ev.ctrlKey || ev.metaKey || ev.altKey || !cur) return;
  const t = ev.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
  const k = ev.key;
  if (k === "+" || k === "=") stepZoom(1);
  else if (k === "-") stepZoom(-1);
  else if (k === "0") setMode("fit-width");
  else if (k === "n") goToPage(cur.page + 1);
  else if (k === "p") goToPage(cur.page - 1);
  else if (k === "f") openFind();
  else return;
  ev.preventDefault();
});

// ---- find in paper (brief L24): plain text search over each page's text content ----

const FIND_MAX_HITS = 100;
const FIND_CONTEXT = 36;
const FIND_NOT_READY = "Find is available once the PDF is ready.";
let findToken = 0;

function resetFind() {
  findToken++;
  el.find.hidden = true;
  el.findBtn.setAttribute("aria-expanded", "false");
  el.findInput.value = "";
  PT.clear(el.findResults);
  el.findResults.hidden = true;
  el.findCount.textContent = "";
  setFindReady(false);
}

function setFindReady(ready) {
  el.findInput.disabled = !ready;
  if (!ready) el.findCount.textContent = FIND_NOT_READY;
  else if (el.findCount.textContent === FIND_NOT_READY) el.findCount.textContent = "";
}

function openFind() {
  if (!cur || !cur.pages.length) return;
  el.find.hidden = false;
  el.findBtn.setAttribute("aria-expanded", "true");
  el.findInput.focus();
  el.findInput.select();
  loadTexts(cur); // start extracting now; a search waits for it
}

function closeFind(refocus) {
  findToken++;
  el.find.hidden = true;
  el.findBtn.setAttribute("aria-expanded", "false");
  if (refocus) el.findBtn.focus();
}

// Page text, one string per page, whitespace collapsed. Cached for the open document.
function loadTexts(c) {
  if (!c.texts) {
    c.texts = Promise.all(
      c.pages.map((p) =>
        p.proxy.getTextContent().then((tc) =>
          tc.items
            .map((it) => (it.str || "") + (it.hasEOL ? " " : ""))
            .join("")
            .replace(/\s+/g, " ")
            .trim(),
        ),
      ),
    );
  }
  return c.texts;
}

function snippet(text, at, len) {
  const start = Math.max(0, at - FIND_CONTEXT);
  const end = Math.min(text.length, at + len + FIND_CONTEXT);
  return h(
    "span",
    { class: "find-hit__text" },
    start > 0 ? "…" : "",
    text.slice(start, at),
    h("span", { class: "find-match" }, text.slice(at, at + len)),
    text.slice(at + len, end),
    end < text.length ? "…" : "",
  );
}

async function runFind() {
  const c = cur;
  if (!c || !c.pages.length) return;
  const q = el.findInput.value.replace(/\s+/g, " ").trim();
  const my = ++findToken;
  PT.clear(el.findResults);
  el.findResults.hidden = true;
  if (!q) {
    el.findCount.textContent = "";
    return;
  }
  el.findCount.textContent = "Searching…";
  const texts = await loadTexts(c);
  if (my !== findToken || stale(c.token)) return;
  const needle = q.toLowerCase();
  const hits = [];
  let total = 0;
  const pagesHit = new Set();
  texts.forEach((text, i) => {
    const hay = text.toLowerCase();
    let at = hay.indexOf(needle);
    while (at !== -1) {
      total++;
      pagesHit.add(i + 1);
      if (hits.length < FIND_MAX_HITS) hits.push({ page: i + 1, at, text });
      at = hay.indexOf(needle, at + needle.length);
    }
  });
  if (!total) {
    el.findCount.textContent = "No matches.";
    PT.announce("No matches.");
    return;
  }
  const line = `${(total === 1 ? "1 match" : `${total} matches`)} on ${PT.plural(pagesHit.size, "page")}`;
  el.findCount.textContent = line;
  PT.announce(`${line}.`);
  hits.forEach((hit) => {
    const b = h("button", { type: "button", class: "find-hit", "data-page": String(hit.page) }, `Page ${hit.page}: `, snippet(hit.text, hit.at, needle.length));
    b.addEventListener("click", () => goToPage(hit.page, { flash: true }));
    el.findResults.appendChild(h("li", {}, b));
  });
  el.findResults.hidden = false;
}

el.findBtn.addEventListener("click", () => (el.find.hidden ? openFind() : closeFind(false)));
el.findClose.addEventListener("click", () => closeFind(true));
el.findInput.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") {
    ev.preventDefault();
    runFind();
  }
});
el.find.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape") {
    ev.stopPropagation();
    closeFind(true);
  }
});
el.findInput.addEventListener("input", () => {
  if (!el.findInput.value) {
    findToken++;
    PT.clear(el.findResults);
    el.findResults.hidden = true;
    el.findCount.textContent = "";
  }
});

// ---- API for app.js and later viewer features ----

window.PTViewer = {
  open,
  close,
  goToPage,
  flashPage,
  openFind,
  current: () => cur,
  els: el,
};
PT.registerViewer(window.PTViewer);
