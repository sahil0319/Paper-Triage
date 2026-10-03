/* Highlights, notes and Markdown export for the PDF preview (v3 T062, brief L16, L18, L19, L23).
   Imported by viewer.js (static import). Highlight geometry is stored as fractions of the page box,
   so zoom needs no re-anchoring: rects are positioned in percent inside each page. */

const COLORS = ["yellow", "mint", "peach"];
const COLOR_NAME = { yellow: "Yellow", mint: "Mint", peach: "Peach" };
const UNDO_MS = window.__PT_UNDO_MS || 8000; // test hook: shorten the 8 s undo window
const NOTE_MAX = 500;
const COUNTER_FROM = 400;
const QUOTE_MAX = 500;
const CONTEXT = 32;
const POPOVER_CLOSE_SCROLL = 200;

export function initAnnotations(V) {
  const PT = window.PT;
  const h = PT.h;
  const el = V.el;
  const $ = (id) => document.getElementById(id);
  const ui = {
    list: $("pv-hl-list"),
    empty: $("pv-hl-empty"),
    msg: $("pv-hl-msg"),
    count: $("pv-hl-count"),
    tools: $("pv-hl-tools"),
    noteAdd: $("pv-note-add"),
    hlBtn: $("pv-hl-btn"),
    hlColor: $("pv-hl-color"),
    exportBtn: $("pv-export"),
    popover: $("pv-popover"),
  };

  let st = null; // state for the open paper: { id, ann, tombs, editing, ready, token }
  let lastColor = "yellow";
  let snapshot = null; // the last valid selection, kept while focus sits in the toolbar or popover
  let seq = 0;
  let popoverTop = 0;

  // ---- small helpers ----

  const pct = (v) => `${(v * 100).toFixed(4)}%`;

  function topOf(a) {
    return a.rects && a.rects.length ? Math.min(...a.rects.map((r) => r[1])) : 0;
  }

  function sortKey(a, b) {
    return a.page - b.page || topOf(a) - topOf(b) || (a._seq || 0) - (b._seq || 0);
  }

  function liveSorted() {
    return st ? st.ann.slice().sort(sortKey) : [];
  }

  function highlights() {
    return st ? st.ann.filter((a) => a.kind === "highlight") : [];
  }

  function colorName(c) {
    return COLOR_NAME[c] || "Yellow";
  }

  function api(method, url, body) {
    return fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    }).then((res) => {
      if (res.status === 204) return { ok: true, status: 204, data: null };
      return res
        .json()
        .catch(() => null)
        .then((data) => ({ ok: res.ok, status: res.status, data }));
    });
  }

  function reason(r) {
    return r.data && typeof r.data.detail === "string" ? r.data.detail : `The server returned an error (${r.status}). Try again.`;
  }

  function failText(err) {
    return PT.failMessage(err);
  }

  const stale = (t) => !st || st.token !== t;

  // Keep the cached library item's highlight count current (Library row, unsave confirm copy).
  function syncCount() {
    const n = highlights().length;
    ui.count.textContent = String(n);
    const it = PT.libItem(st.id);
    if (it) it.highlight_count = n;
    const hasAny = st.ann.some((a) => !a._failed);
    ui.exportBtn.hidden = !st.ready;
    if (hasAny) ui.exportBtn.removeAttribute("aria-disabled");
    else ui.exportBtn.setAttribute("aria-disabled", "true");
  }

  // ---- lifecycle ----

  V.on("open", (cur) => {
    st = { id: cur.id, ann: [], tombs: [], editing: null, draft: null, ready: false, token: cur.token, status: cur.status, item: cur.item };
    ui.msg.hidden = true;
    ui.exportBtn.hidden = true;
    ui.hlBtn.parentNode.hidden = true;
    ui.tools.hidden = true;
    ui.list.hidden = false;
    PT.clear(ui.list);
    ui.empty.hidden = true;
    ui.count.textContent = "0";
    closePopover();
    if (cur.status !== "ready") {
      ui.list.hidden = true;
      ui.msg.hidden = false;
      ui.msg.textContent = "Highlights are available once the PDF is ready.";
      return;
    }
    loadAnnotations(cur.token);
  });

  V.on("close", () => {
    if (st) st.tombs.forEach((t) => window.clearTimeout(t.timer));
    st = null;
    closePopover();
    snapshot = null;
    ui.hlBtn.parentNode.hidden = true;
    ui.exportBtn.hidden = true;
  });

  V.on("pages", () => {
    if (!st) return;
    ui.hlBtn.parentNode.hidden = false;
    setHlButton();
    drawAll();
  });

  V.on("render-failed", () => {
    if (!st) return;
    ui.hlBtn.parentNode.hidden = true;
    ui.tools.hidden = true;
  });

  V.on("text", (p) => {
    // A page whose text layer came out empty is a scan: highlighting is not possible there.
    const none = !p.text.querySelector("span:not(.markedContent)");
    p.sec.classList.toggle("no-text", none);
    let note = p.sec.querySelector(".pdf-page__notext");
    if (none && !note) {
      p.sec.appendChild(h("p", { class: "pdf-page__notext" }, "No selectable text on this page. You can still add a note for this page."));
    } else if (!none && note) {
      note.remove();
    }
  });

  V.on("release", (p) => {
    const note = p.sec.querySelector(".pdf-page__notext");
    if (note) note.remove();
    p.sec.classList.remove("no-text");
  });

  function loadAnnotations(token) {
    api("GET", `/api/annotations?paper_id=${encodeURIComponent(st.id)}`).then(
      (r) => {
        if (stale(token)) return;
        if (!r.ok) {
          ui.msg.hidden = false;
          ui.msg.textContent = `Could not load highlights. ${reason(r)}`;
          return;
        }
        st.ready = true;
        st.ann = (r.data.annotations || []).map((a) => ({ ...a, _seq: ++seq }));
        ui.tools.hidden = false;
        syncCount();
        renderList();
        drawAll();
      },
      (err) => {
        if (stale(token)) return;
        ui.msg.hidden = false;
        ui.msg.textContent = `Could not load highlights. ${failText(err)}`;
      },
    );
  }

  // ---- drawing on the pages ----

  function drawAll() {
    const c = V.cur();
    if (!st || !c || !c.pages) return;
    c.pages.forEach((p) => drawPage(p));
  }

  function drawPage(p) {
    PT.clear(p.hl);
    if (!st) return;
    st.ann.forEach((a) => {
      if (a.page !== p.n || !a.rects) return;
      a.rects.forEach((r) => {
        const d = h("div", { class: `hl hl--${a.color}${a._failed ? " hl--failed" : ""}`, "data-annotation-id": String(a.id) });
        d.style.left = pct(r[0]);
        d.style.top = pct(r[1]);
        d.style.width = pct(r[2]);
        d.style.height = pct(r[3]);
        p.hl.appendChild(d);
      });
    });
  }

  function drawPageNumber(n) {
    const c = V.cur();
    const p = c && c.pages && c.pages[n - 1];
    if (p) drawPage(p);
  }

  function flashAnnotation(a) {
    const c = V.cur();
    const p = c && c.pages[a.page - 1];
    if (!p) return;
    const els = p.hl.querySelectorAll(`[data-annotation-id="${a.id}"]`);
    els.forEach((d) => {
      d.classList.remove("is-flash");
      void d.offsetWidth;
      d.classList.add("is-flash");
    });
    window.setTimeout(() => els.forEach((d) => d.classList.remove("is-flash")), PT.reducedMotion() ? 2000 : 1600);
  }

  function goTo(a) {
    const c = V.cur();
    if (!c || !c.pages || !c.pages.length) return;
    const p = c.pages[a.page - 1];
    if (!p) return;
    const y = topOf(a);
    el.well.scrollTop = Math.max(0, p.sec.offsetTop + y * p.sec.clientHeight - 0.25 * el.well.clientHeight);
    V.syncPage(a.page);
    flashAnnotation(a);
    el.well.focus({ preventScroll: true });
  }

  // ---- selection to rects (page-box fractions) ----

  function elementOf(node) {
    return node && node.nodeType === 1 ? node : node && node.parentElement;
  }

  function mergeLines(rects) {
    const list = rects.slice().sort((a, b) => a.top - b.top || a.left - b.left);
    const out = [];
    list.forEach((r) => {
      const prev = out[out.length - 1];
      if (prev) {
        const overlap = Math.min(prev.bottom, r.bottom) - Math.max(prev.top, r.top);
        const minH = Math.min(prev.height, r.height);
        if (overlap > 0.5 * minH && r.left <= prev.right + 3) {
          prev.left = Math.min(prev.left, r.left);
          prev.right = Math.max(prev.right, r.right);
          prev.top = Math.min(prev.top, r.top);
          prev.bottom = Math.max(prev.bottom, r.bottom);
          prev.width = prev.right - prev.left;
          prev.height = prev.bottom - prev.top;
          return;
        }
      }
      out.push({ left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height });
    });
    return out;
  }

  const clamp01 = (v) => Math.max(0, Math.min(1, v));

  // Reads the current selection. Only the part on the page where it started is used.
  function readSelection() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
    const range = sel.getRangeAt(0);
    const startEl = elementOf(range.startContainer);
    const layer = startEl && startEl.closest(".textLayer");
    if (!layer || !el.well.contains(layer)) return null;
    const sec = layer.closest(".pdf-page");
    const page = Number(sec.getAttribute("data-page"));
    let r = range;
    let partial = false;
    if (!layer.contains(range.endContainer)) {
      r = document.createRange();
      r.setStart(range.startContainer, range.startOffset);
      r.setEnd(layer, layer.childNodes.length);
      partial = true;
    }
    const quote = r.toString().replace(/\s+/g, " ").trim().slice(0, QUOTE_MAX);
    if (!quote) return null;
    const box = sec.getBoundingClientRect();
    const left0 = box.left + sec.clientLeft;
    const top0 = box.top + sec.clientTop;
    const W = sec.clientWidth;
    const H = sec.clientHeight;
    const raw = Array.from(r.getClientRects()).filter((q) => q.width >= 1 && q.height >= 1 && !(q.width > 0.95 * W && q.height > 0.9 * H));
    if (!raw.length) return null;
    let rects = mergeLines(raw).map((q) => {
      const x = clamp01((q.left - left0) / W);
      const y = clamp01((q.top - top0) / H);
      const w = clamp01((q.right - left0) / W) - x;
      const hh = clamp01((q.bottom - top0) / H) - y;
      return [round(x), round(y), round(w), round(hh)];
    });
    rects = rects.filter((q) => q[2] > 0 && q[3] > 0).slice(0, 50);
    if (!rects.length) return null;
    const pre = document.createRange();
    pre.selectNodeContents(layer);
    pre.setEnd(r.startContainer, r.startOffset);
    const post = document.createRange();
    post.selectNodeContents(layer);
    post.setStart(r.endContainer, r.endOffset);
    const prefix = pre.toString().replace(/\s+/g, " ").slice(-CONTEXT);
    const suffix = post.toString().replace(/\s+/g, " ").slice(0, CONTEXT);
    return { page, rects, quote, prefix, suffix, partial, anchor: r.getBoundingClientRect() };
  }

  const round = (v) => Math.round(v * 1e5) / 1e5;

  // ---- creating highlights ----

  function setHlButton() {
    const on = !!snapshot;
    if (on) ui.hlBtn.removeAttribute("aria-disabled");
    else ui.hlBtn.setAttribute("aria-disabled", "true");
  }

  function inChrome(node) {
    return !!node && (ui.popover.contains(node) || $("pv-controls").contains(node));
  }

  function updateFromSelection() {
    if (!st || !st.ready) return;
    const info = readSelection();
    if (info) {
      snapshot = info;
      setHlButton();
      return info;
    }
    if (!inChrome(document.activeElement)) {
      snapshot = null;
      setHlButton();
      closePopover();
    }
    return null;
  }

  function create(info, color, opts) {
    const t = st.token;
    const body = {
      paper_id: st.id,
      page: info.page,
      kind: "highlight",
      color,
      rects: info.rects,
      quote: info.quote,
      prefix: info.prefix || "",
      suffix: info.suffix || "",
      note: "",
    };
    const a = { ...body, id: `tmp-${++seq}`, _seq: seq, _pending: true };
    st.ann.push(a);
    drawPageNumber(a.page);
    send(a, body, t, opts);
    const msg = info.partial
      ? `Highlighted the part on page ${info.page}. Select across pages one page at a time.`
      : `${colorName(color)} highlight added on page ${info.page}.`;
    PT.announce(msg);
    window.getSelection().removeAllRanges();
    snapshot = null;
    setHlButton();
    closePopover();
    return a;
  }

  // POST the annotation; on failure the highlight stays drawn (dashed) with a retry line.
  function send(a, body, t, opts) {
    return api("POST", "/api/annotations", body).then(
      (r) => {
        if (stale(t)) return;
        if (!r.ok) return fail(a, reason(r));
        adopt(a, r.data, opts);
      },
      (err) => {
        if (!stale(t)) fail(a, failText(err));
      },
    );
  }

  function adopt(a, saved, opts) {
    const tmpId = a.id;
    Object.assign(a, saved, { _pending: false, _failed: false, _error: null });
    drawPageNumber(a.page);
    syncCount();
    renderList();
    if (opts && opts.editNote) startEdit(a);
    void tmpId;
  }

  function fail(a, why) {
    a._failed = true;
    a._pending = false;
    a._error = why;
    drawPageNumber(a.page);
    syncCount();
    renderList();
  }

  // ---- popover and toolbar control ----

  function buildPopover() {
    PT.clear(ui.popover);
    COLORS.forEach((c) => {
      const b = h("button", { type: "button", class: `swatch swatch--${c}${c === lastColor ? " is-last" : ""}`, "aria-label": `Highlight ${c}`, "data-color": c });
      b.addEventListener("click", () => applyColor(c));
      ui.popover.appendChild(b);
    });
    const add = h("button", { type: "button", class: "text-btn", "data-act": "pop-note" }, "Add note");
    add.addEventListener("click", () => {
      const info = snapshot || updateFromSelection();
      if (!info) return;
      setLast(lastColor);
      openPanelHighlights();
      create(info, lastColor, { editNote: true });
    });
    ui.popover.appendChild(add);
  }

  function setLast(c) {
    lastColor = c;
    ui.hlColor.value = c;
  }

  function applyColor(c) {
    const info = snapshot || updateFromSelection();
    if (!info) return;
    setLast(c);
    create(info, c);
    el.well.focus({ preventScroll: true });
  }

  function showPopover(info) {
    buildPopover();
    ui.popover.hidden = false;
    popoverTop = el.well.scrollTop;
    const a = info.anchor;
    const ph = ui.popover.offsetHeight;
    const pw = ui.popover.offsetWidth;
    const wellTop = el.well.getBoundingClientRect().top;
    let top = a.top - ph - 8;
    if (top < wellTop + 8) top = a.bottom + 8; // never over the toolbar
    top = Math.max(wellTop + 8, Math.min(window.innerHeight - ph - 8, top));
    let left = a.left + a.width / 2 - pw / 2;
    left = Math.max(8, Math.min(window.innerWidth - pw - 8, left));
    ui.popover.style.top = `${Math.round(top)}px`;
    ui.popover.style.left = `${Math.round(left)}px`;
  }

  function closePopover() {
    ui.popover.hidden = true;
  }

  function maybePopover() {
    const info = updateFromSelection();
    if (info) showPopover(info);
  }

  el.well.addEventListener("mouseup", () => window.setTimeout(maybePopover, 0));
  el.well.addEventListener("keyup", (ev) => {
    if (ev.key === "Escape") return;
    if (ev.shiftKey || ev.key.startsWith("Arrow") || ev.key === "Shift") window.setTimeout(maybePopover, 0);
  });
  document.addEventListener("selectionchange", () => {
    if (!st) return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) {
      window.setTimeout(() => {
        if (!inChrome(document.activeElement)) {
          const info = readSelection();
          if (!info) {
            snapshot = null;
            setHlButton();
            closePopover();
          }
        }
      }, 0);
    } else {
      const info = readSelection();
      if (info) {
        snapshot = info;
        setHlButton();
      }
    }
  });
  el.well.addEventListener(
    "scroll",
    () => {
      if (!ui.popover.hidden && Math.abs(el.well.scrollTop - popoverTop) > POPOVER_CLOSE_SCROLL) closePopover();
    },
    { passive: true },
  );
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !ui.popover.hidden) {
      closePopover();
      el.well.focus({ preventScroll: true });
    }
  });

  ui.hlBtn.addEventListener("click", () => {
    if (ui.hlBtn.getAttribute("aria-disabled") === "true") return;
    const info = snapshot || updateFromSelection();
    if (!info) return;
    create(info, lastColor);
    el.well.focus({ preventScroll: true });
  });
  ui.hlColor.addEventListener("change", () => {
    lastColor = ui.hlColor.value;
  });

  // ---- the panel ----

  function openPanelHighlights() {
    V.showPanel("highlights");
  }

  function renderList() {
    PT.clear(ui.list);
    if (!st) return;
    const entries = [];
    st.ann.forEach((a) => entries.push({ a }));
    st.tombs.forEach((t) => entries.push({ a: t.a, tomb: t }));
    entries.sort((x, y) => sortKey(x.a, y.a));
    const draft = st.draft;
    if (draft) ui.list.appendChild(draftItem(draft));
    entries.forEach((e) => ui.list.appendChild(e.tomb ? tombItem(e) : item(e.a)));
    ui.empty.hidden = !!(entries.length || draft);
    ui.list.hidden = !(entries.length || draft);
  }

  function swatchDot(color) {
    return h("span", { class: `dot dot--${color}`, "aria-hidden": "true" });
  }

  function item(a) {
    const isNote = a.kind === "note";
    const li = h("li", { class: `hl-item${a._failed ? " is-failed" : ""}`, "data-annotation-id": String(a.id), "data-kind": a.kind });
    const goto = h("button", { type: "button", class: "text-btn", "aria-label": `Go to ${isNote ? "note" : "highlight"} on page ${a.page}` }, "Go to");
    goto.addEventListener("click", () => {
      closeSheetIfAny();
      goTo(a);
    });
    li.appendChild(
      h(
        "div",
        { class: "hl-item__line" },
        isNote ? h("span", { class: "hl-item__kind" }, "Page note") : [swatchDot(a.color), h("span", { class: "hl-item__kind" }, colorName(a.color))],
        h("span", { class: "hl-item__page" }, `Page ${a.page}`),
        goto,
      ),
    );
    if (!isNote) li.appendChild(quoteEl(a));
    if (st.editing === a.id) {
      li.appendChild(editor(a));
    } else {
      if (a.note) li.appendChild(h("p", { class: "hl-item__note" }, a.note));
      if (a._failed) {
        const again = h("button", { type: "button", class: "text-btn" }, "Try again");
        again.addEventListener("click", () => retrySend(a));
        li.appendChild(h("p", { class: "row-error", role: "alert" }, `Could not save. ${a._error}`, " ", again));
      } else if (!a._pending) {
        li.appendChild(actions(a, isNote));
      }
    }
    return li;
  }

  function quoteEl(a) {
    const q = h("p", { class: `hl-item__quote hl-item__quote--${a.color}` }, a.quote);
    const wrap = h("div", { class: "hl-item__quotewrap" }, q);
    if (a.quote.length > 140) {
      q.classList.add("is-clamped");
      const more = h("button", { type: "button", class: "text-btn", "aria-expanded": "false" }, "Show more");
      more.addEventListener("click", () => {
        const open = q.classList.toggle("is-clamped") === false;
        more.textContent = open ? "Show less" : "Show more";
        more.setAttribute("aria-expanded", open ? "true" : "false");
      });
      wrap.appendChild(more);
    }
    return wrap;
  }

  function actions(a, isNote) {
    const row = h("div", { class: "hl-item__actions" });
    const edit = h("button", { type: "button", class: "text-btn", "data-act": "edit-note" }, a.note ? "Edit note" : "Add note");
    edit.addEventListener("click", () => startEdit(a));
    row.appendChild(edit);
    if (!isNote) {
      const sel = h("select", { class: "select hl-item__color", "aria-label": `Color for highlight on page ${a.page}`, "data-act": "color" });
      COLORS.forEach((c) => sel.appendChild(h("option", { value: c }, colorName(c))));
      sel.value = a.color;
      sel.addEventListener("change", () => changeColor(a, sel));
      row.appendChild(h("label", { class: "hl-item__colorlab" }, h("span", { class: "sr-only" }, "Color"), sel));
    }
    const del = h("button", { type: "button", class: "text-btn", "data-act": "delete" }, "Delete");
    del.addEventListener("click", () => remove(a));
    row.appendChild(del);
    return row;
  }

  function closeSheetIfAny() {
    if (V.closeSheet) V.closeSheet();
  }

  // ---- note editor ----

  function startEdit(a) {
    st.editing = a.id;
    openPanelHighlights();
    renderList();
    const ta = ui.list.querySelector(`[data-annotation-id="${a.id}"] textarea`);
    if (ta) {
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    }
  }

  function counterText(n) {
    return `${n}/${NOTE_MAX}`;
  }

  function editorBox(opts) {
    const ta = h("textarea", { rows: "3", maxlength: String(NOTE_MAX), id: `note-${++seq}` });
    ta.value = opts.value || "";
    const counter = h("span", { class: "note-counter", "aria-live": "off", hidden: "" });
    const paint = () => {
      const n = ta.value.length;
      counter.hidden = n < COUNTER_FROM;
      counter.textContent = counterText(n);
      counter.classList.toggle("is-max", n >= NOTE_MAX);
    };
    ta.addEventListener("input", () => {
      if (opts.onInput) opts.onInput(ta.value);
      paint();
    });
    const save = h("button", { type: "button", class: "btn btn--secondary btn--small" }, opts.saveText || "Save note");
    const cancel = h("button", { type: "button", class: "text-btn" }, "Cancel");
    save.addEventListener("click", () => opts.save(ta.value));
    cancel.addEventListener("click", () => opts.cancel());
    ta.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") {
        ev.preventDefault();
        ev.stopPropagation();
        opts.cancel();
      } else if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) {
        ev.preventDefault();
        opts.save(ta.value);
      }
    });
    paint();
    return h("div", { class: "note-editor" }, h("label", { class: "note-editor__label", for: ta.id }, "Note"), ta, h("div", { class: "note-editor__row" }, save, cancel, counter));
  }

  function editor(a) {
    return editorBox({
      value: a.note || "",
      save: (v) => saveNote(a, v),
      cancel: () => {
        st.editing = null;
        renderList();
        const b = ui.list.querySelector(`[data-annotation-id="${a.id}"] [data-act="edit-note"]`);
        if (b) b.focus();
      },
    });
  }

  function saveNote(a, value) {
    const note = value.trim();
    if (a.kind === "note" && !note) {
      st.editing = null;
      remove(a);
      return;
    }
    const t = st.token;
    api("PATCH", `/api/annotations/${a.id}`, { note }).then(
      (r) => {
        if (stale(t)) return;
        if (!r.ok) return editError(a, `Could not save. ${reason(r)}`);
        Object.assign(a, r.data);
        st.editing = null;
        renderList();
        PT.announce(note ? "Note saved." : "Note removed.");
        const b = ui.list.querySelector(`[data-annotation-id="${a.id}"] [data-act="edit-note"]`);
        if (b) b.focus();
      },
      (err) => {
        if (!stale(t)) editError(a, `Could not save. ${failText(err)}`);
      },
    );
  }

  function editError(a, text) {
    const li = ui.list.querySelector(`[data-annotation-id="${a.id}"]`);
    if (!li) return;
    const old = li.querySelector(".row-error");
    if (old) old.remove();
    li.appendChild(h("p", { class: "row-error", role: "alert" }, text));
  }

  // ---- page notes ----

  ui.noteAdd.addEventListener("click", () => {
    if (!st || !st.ready) return;
    const c = V.cur();
    const page = c ? c.page : 1;
    st.draft = { page, text: "" };
    renderList();
    const ta = ui.list.querySelector("[data-draft] textarea");
    if (ta) ta.focus();
  });

  function draftItem(d) {
    const li = h("li", { class: "hl-item", "data-draft": "", "data-kind": "note" });
    li.appendChild(h("div", { class: "hl-item__line" }, h("span", { class: "hl-item__kind" }, "Page note"), h("span", { class: "hl-item__page" }, `Page ${d.page}`)));
    li.appendChild(
      editorBox({
        value: d.text,
        saveText: "Save note",
        onInput: (v) => (d.text = v),
        cancel: () => {
          st.draft = null;
          renderList();
          ui.noteAdd.focus();
        },
        save: (v) => {
          const note = v.trim();
          if (!note) {
            st.draft = null;
            renderList();
            ui.noteAdd.focus();
            return;
          }
          const t = st.token;
          api("POST", "/api/annotations", { paper_id: st.id, page: d.page, kind: "note", note, rects: [], quote: "" }).then(
            (r) => {
              if (stale(t)) return;
              if (!r.ok) return draftError(li, `Could not save. ${reason(r)}`);
              st.draft = null;
              st.ann.push({ ...r.data, _seq: ++seq });
              syncCount();
              renderList();
              PT.announce(`Note added on page ${d.page}.`);
              const b = ui.list.querySelector(`[data-annotation-id="${r.data.id}"] [data-act="edit-note"]`);
              if (b) b.focus();
            },
            (err) => {
              if (!stale(t)) draftError(li, `Could not save. ${failText(err)}`);
            },
          );
        },
      }),
    );
    return li;
  }

  function draftError(li, text) {
    const old = li.querySelector(".row-error");
    if (old) old.remove();
    li.appendChild(h("p", { class: "row-error", role: "alert" }, text));
  }

  // ---- color, retry, delete with undo ----

  function changeColor(a, sel) {
    const t = st.token;
    const before = a.color;
    api("PATCH", `/api/annotations/${a.id}`, { color: sel.value }).then(
      (r) => {
        if (stale(t)) return;
        if (!r.ok) {
          sel.value = before;
          return editError(a, `Could not save. ${reason(r)}`);
        }
        a.color = r.data.color;
        drawPageNumber(a.page);
        renderList();
        const again = ui.list.querySelector(`[data-annotation-id="${a.id}"] select`);
        if (again) again.focus();
        PT.announce(`Color changed to ${colorName(a.color)}.`);
      },
      (err) => {
        sel.value = before;
        if (!stale(t)) editError(a, `Could not save. ${failText(err)}`);
      },
    );
  }

  function retrySend(a) {
    const t = st.token;
    a._failed = false;
    a._pending = true;
    renderList();
    drawPageNumber(a.page);
    send(
      a,
      { paper_id: st.id, page: a.page, kind: a.kind, color: a.color, rects: a.rects, quote: a.quote, prefix: a.prefix || "", suffix: a.suffix || "", note: a.note || "" },
      t,
    );
  }

  function remove(a) {
    const t = st.token;
    const snap = { ...a };
    const apiDelete = typeof a.id === "number" ? api("DELETE", `/api/annotations/${a.id}`) : Promise.resolve({ ok: true });
    apiDelete.then(
      (r) => {
        if (stale(t)) return;
        if (!r.ok && r.status !== 404) return editError(a, `Could not delete. ${reason(r)}`);
        st.ann = st.ann.filter((x) => x !== a);
        const tomb = { a: snap, timer: 0 };
        tomb.timer = window.setTimeout(() => expire(tomb), UNDO_MS);
        st.tombs.push(tomb);
        drawPageNumber(snap.page);
        syncCount();
        renderList();
        const undo = ui.list.querySelector(`[data-tomb="${tombKey(tomb)}"] button`);
        if (undo) undo.focus();
        PT.announce(a.kind === "note" ? "Note deleted." : "Highlight deleted.");
      },
      (err) => {
        if (!stale(t)) editError(a, `Could not delete. ${failText(err)}`);
      },
    );
  }

  const tombKeys = new WeakMap();
  function tombKey(tomb) {
    if (!tombKeys.has(tomb)) tombKeys.set(tomb, String(++seq));
    return tombKeys.get(tomb);
  }

  function tombItem(e) {
    const tomb = e.tomb;
    const undo = h("button", { type: "button", class: "text-btn" }, "Undo");
    undo.addEventListener("click", () => restore(tomb));
    return h("li", { class: "hl-item hl-item--deleted", "data-tomb": tombKey(tomb) }, h("span", {}, e.a.kind === "note" ? "Note deleted." : "Highlight deleted."), " ", undo);
  }

  function expire(tomb) {
    if (!st) return;
    const li = ui.list.querySelector(`[data-tomb="${tombKey(tomb)}"]`);
    const hadFocus = li && li.contains(document.activeElement);
    const next = li && li.nextElementSibling;
    st.tombs = st.tombs.filter((t) => t !== tomb);
    renderList();
    if (hadFocus) {
      const target = next && next.getAttribute("data-annotation-id") ? ui.list.querySelector(`[data-annotation-id="${next.getAttribute("data-annotation-id")}"] button`) : null;
      (target || ui.noteAdd).focus();
    }
  }

  function restore(tomb) {
    window.clearTimeout(tomb.timer);
    st.tombs = st.tombs.filter((t) => t !== tomb);
    const a = tomb.a;
    const body = { paper_id: st.id, page: a.page, kind: a.kind, color: a.color, rects: a.rects || [], quote: a.quote || "", prefix: a.prefix || "", suffix: a.suffix || "", note: a.note || "" };
    const back = { ...body, id: `tmp-${++seq}`, _seq: seq, _pending: true };
    st.ann.push(back);
    drawPageNumber(back.page);
    renderList();
    send(back, body, st.token).then(() => {
      const b = ui.list.querySelector(`[data-annotation-id="${back.id}"] [data-act="edit-note"]`);
      if (b) b.focus();
    });
  }

  // ---- export notes (L23) ----

  function markdown() {
    const c = V.cur();
    const title = (c && c.item && c.item.title) || "Notes";
    const link = (c && c.item && (c.item.abs_url || c.item.pdf_url)) || "";
    const out = [`# ${title}`, `${st.id}${link ? ` · ${link}` : ""}`, ""];
    liveSorted()
      .filter((a) => !a._failed)
      .forEach((a) => {
        if (a.kind === "highlight") {
          out.push(`> ${a.quote} (p.${a.page})`);
          if (a.note) out.push(a.note);
        } else {
          out.push(`Page ${a.page} note: ${a.note}`);
        }
        out.push("");
      });
    return `${out.join("\n")}\n`;
  }

  ui.exportBtn.addEventListener("click", () => {
    if (!st || ui.exportBtn.getAttribute("aria-disabled") === "true") return;
    const blob = new Blob([markdown()], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = h("a", { href: url, download: `${st.id.replace(/[^A-Za-z0-9._-]+/g, "_")}-notes.md` });
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    PT.announce("Notes exported.");
  });

  // Exposed for tests and for the panel (T063).
  V.annotations = { goTo, markdown: () => (st ? markdown() : ""), list: () => (st ? st.ann.slice() : []) };
}
