/* Paper Triage UI. Vanilla JS; all text is set with textContent / text nodes (paper titles and
   model output are untrusted, never innerHTML). */
(function () {
  "use strict";

  var form = document.getElementById("triage-form");
  var input = document.getElementById("query");
  var button = document.getElementById("submit");
  var results = document.querySelector(".results");
  var statusEl = document.getElementById("status");
  var alertEl = document.getElementById("alert");
  var notesEl = document.getElementById("notes");
  var listEl = document.getElementById("paper-list");
  var emptyEl = document.getElementById("empty");
  var heading = document.getElementById("results-heading");
  var countEl = document.getElementById("results-count");
  var mockEl = document.getElementById("mock-label");
  var modelEl = document.getElementById("model");
  var chatForm = document.getElementById("chat-form");
  var question = document.getElementById("question");
  var askBtn = document.getElementById("ask");
  var logEl = document.getElementById("chat-log");
  var chatEl = document.getElementById("chat");
  var workingEl = document.getElementById("working");
  var moreWrap = document.getElementById("load-more-wrap");
  var moreBtn = document.getElementById("load-more");
  var moreCaption = document.getElementById("load-more-caption");
  var moreError = document.getElementById("load-more-error");
  var workingMoreEl = document.getElementById("working-more");

  var SVG_NS = "http://www.w3.org/2000/svg";
  var NETWORK_MSG = "Could not reach the server. Check that the app is running.";

  var state = {
    rows: [],          // result items currently shown, in display order
    lastQuery: "",
    running: false,
    mock: false,
    stored: false,      // rows came from GET /api/papers (reload), not a run in this page
    query: "",          // query sent to /api/triage for the current result set
    topic: "",
    nextOffset: null,   // offset for the next load-more call
    hasMore: false,
    loadingMore: false,
    generation: 0       // bumped by every full triage; stale load-more replies are dropped
  };
  var MAX_IDS = 50;
  var PAGE = 5;

  // ---- small DOM helpers ----

  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (attrs[k] !== null && attrs[k] !== undefined) el.setAttribute(k, attrs[k]);
    });
    append(el, Array.prototype.slice.call(arguments, 2));
    return el;
  }

  function svg(tag, attrs) {
    var el = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { el.setAttribute(k, attrs[k]); });
    append(el, Array.prototype.slice.call(arguments, 2));
    return el;
  }

  // Eight-ray activity glyph (D14). Decorative; the animation is CSS only.
  function rayGlyph(size, cls) {
    var g = svg("svg", { class: cls, width: String(size), height: String(size), viewBox: "0 0 24 24",
      "aria-hidden": "true", focusable: "false" });
    for (var i = 0; i < 8; i++) {
      var a = i * Math.PI / 4;
      g.appendChild(svg("line", {
        class: "ray", style: "--i:" + i,
        x1: (12 + 3.5 * Math.cos(a)).toFixed(2), y1: (12 + 3.5 * Math.sin(a)).toFixed(2),
        x2: (12 + 9 * Math.cos(a)).toFixed(2), y2: (12 + 9 * Math.sin(a)).toFixed(2),
        stroke: "currentColor", "stroke-width": "2.25", "stroke-linecap": "round"
      }));
    }
    return g;
  }

  function append(el, children) {
    children.forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      if (Array.isArray(c)) return append(el, c);
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
  }

  function clear(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function authorsLine(list) {
    if (!list || !list.length) return null;
    return list.length > 3 ? list.slice(0, 3).join(", ") + " et al." : list.join(", ");
  }

  function plural(n, word) {
    return n + " " + word + (n === 1 ? "" : "s");
  }

  function errorText(res, body) {
    if (body && typeof body.detail === "string") return body.detail;
    return "The server returned an error (" + res.status + "). Try again.";
  }

  function postJSON(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (body) {
        if (!res.ok) throw new Error(errorText(res, body));
        return body;
      });
    });
  }

  function failMessage(err) {
    return err instanceof TypeError ? NETWORK_MSG : err.message;
  }

  function getJSON(url) {
    return fetch(url).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (body) {
        if (!res.ok) throw new Error(errorText(res, body));
        return body;
      });
    });
  }

  // ---- summary and critique (D12) ----

  function section(title, body) {
    return [h("h4", { class: "critique__h" }, title), body];
  }

  function notStated() {
    return h("p", { class: "none" }, "Not stated");
  }

  function pairList(items, first, second, label) {
    if (!items || !items.length) return notStated();
    return h("ul", {}, items.map(function (it) {
      return h("li", {}, it[first], h("span", { class: "why" }, label + it[second]));
    }));
  }

  function plainList(items) {
    if (!items || !items.length) return notStated();
    return h("ul", {}, items.map(function (t) { return h("li", {}, t); }));
  }

  function chevron() {
    return svg("svg", { class: "chev", width: "10", height: "10", viewBox: "0 0 10 10",
      "aria-hidden": "true", focusable: "false" },
      svg("polyline", { points: "3,1 7,5 3,9", fill: "none", stroke: "currentColor",
        "stroke-width": "1.5", "stroke-linecap": "round", "stroke-linejoin": "round" }));
  }

  function details(r) {
    if (!r.summary && !r.critique) return null;
    var box = h("div", { class: "critique" });
    var parts = [];
    if (r.critique) {
      parts.push(h("p", { class: "basis" },
        r.critique.basis === "abstract"
          ? "Based on the abstract only. Full text was not available."
          : "Based on the full text."));
    }
    if (r.summary) {
      parts = parts.concat(section("Summary", h("p", {}, r.summary.summary)));
      if (r.summary.contributions && r.summary.contributions.length) {
        parts = parts.concat(section("Contributions", plainList(r.summary.contributions)));
      }
    }
    if (r.critique) {
      var c = r.critique;
      parts = parts.concat(
        section("Weak claims", pairList(c.weak_claims, "claim", "why", "")),
        section("Overclaims", pairList(c.overclaims, "claim", "evidence_gap", "Evidence gap: ")),
        section("Missing baselines", plainList(c.missing_baselines))
      );
    }
    parts.forEach(function (p) { box.appendChild(p); });
    return h("details", { class: "disclosure" },
      h("summary", {}, chevron(), h("span", {}, r.critique ? "Summary and critique" : "Summary")),
      box);
  }

  // ---- source links (D10) ----

  function safeUrl(u) {
    if (typeof u !== "string" || !u) return null;
    try {
      var parsed = new URL(u);
      return parsed.protocol === "https:" || parsed.protocol === "http:" ? u : null;
    } catch (e) {
      return null;
    }
  }

  function arxivPath(id) {
    return String(id).split("/").map(encodeURIComponent).join("/");
  }

  function arrowIcon() {
    return svg("svg", { class: "ext", width: "12", height: "12", viewBox: "0 0 12 12",
      "aria-hidden": "true", focusable: "false" },
      svg("path", { d: "M3.5 8.5 8.5 3.5M4 3.5h4.5V8", fill: "none", stroke: "currentColor",
        "stroke-width": "1.5", "stroke-linecap": "round", "stroke-linejoin": "round" }));
  }

  function linkEl(kind, text, href, title) {
    return h("a", { class: "ext-link", href: href, "data-link": kind, target: "_blank",
      rel: "noopener noreferrer", "aria-label": text + ": " + title + " (opens in new tab)" },
      text, arrowIcon());
  }

  function paperLinks(r) {
    var abs = null;
    var pdf = null;
    if (r.source === "arxiv") {
      abs = safeUrl(r.abs_url) || safeUrl("https://arxiv.org/abs/" + arxivPath(r.paper_id));
      pdf = safeUrl(r.pdf_url) || safeUrl("https://arxiv.org/pdf/" + arxivPath(r.paper_id));
    } else {
      pdf = safeUrl(r.pdf_url);
    }
    if (!abs && !pdf) return null;
    return h("div", { class: "paper__links" },
      abs ? linkEl("abs", "arXiv page", abs, r.title) : null,
      pdf ? linkEl("pdf", "PDF", pdf, r.title) : null);
  }

  // ---- paper rows (D8, D9, D11) ----

  function rankBlock(r, failed, forTopic) {
    var n = failed ? null : Math.max(0, Math.min(10, Number(r.rank) || 0));
    return h("div", { class: "rank" },
      h("div", { class: "rank__line" },
        h("span", { class: "rank__n", "aria-label": failed ? "No rank" : "Rank " + n + " of 10" },
          failed ? "–" : String(n)),
        failed ? null : h("span", { class: "rank__of", "aria-hidden": "true" }, "/10")),
      failed ? null : h("div", { class: "rank__meter", "aria-hidden": "true", style: "--rank:" + n },
        h("span", {})),
      forTopic ? h("p", { class: "rank__for" }, "for \"" + forTopic + "\"") : null);
  }

  function row(r) {
    var failed = r.status === "failed";
    var meta = h("div", { class: "paper__meta" },
      h("span", { class: "paper__id" }, r.paper_id),
      r.basis === "abstract" ? h("span", { class: "flag" }, "Abstract only") : null,
      failed ? h("span", { class: "flag flag--failed" }, "Failed") : null,
      paperLinks(r));
    var reason = failed
      ? h("p", { class: "paper__reason paper__reason--failed" }, r.error || "This paper could not be processed.")
      : h("p", { class: "paper__reason" }, r.rank_reason || "");
    var titleId = "paper-title-" + r.paper_id;
    return h("li", { class: "paper", id: "paper-" + r.paper_id, tabindex: "-1" },
      rankBlock(r, failed),
      h("div", { class: "paper__body" },
        h("div", { class: "paper__head" },
          h("h3", { class: "paper__title", id: titleId }, r.title),
          failed ? null : saveControl(r, titleId)),
        authorsLine(r.authors) ? h("p", { class: "paper__authors" }, authorsLine(r.authors)) : null,
        reason, meta, details(r)));
  }

  // ---- save toggle (v3 L3-L6): POST/DELETE /api/library; confirm before every unsave ----

  var SAVE_LABEL = { idle: "Save", busy: "Saving…", done: "Saved", removing: "Removing…" };

  function bookmark(filled) {
    return svg("svg", { class: "save__glyph", width: "16", height: "16", viewBox: "0 0 16 16",
      "aria-hidden": "true", focusable: "false" },
      svg("path", { d: "M4 2.5h8v11L8 10.5 4 13.5z", fill: filled ? "currentColor" : "none",
        stroke: "currentColor", "stroke-width": "1.5", "stroke-linejoin": "round" }));
  }

  function setSaveButton(btn, mode) {
    var saved = mode === "done" || mode === "removing";
    var busy = mode === "busy" || mode === "removing";
    clear(btn);
    btn.appendChild(bookmark(saved));
    btn.appendChild(document.createTextNode(SAVE_LABEL[mode]));
    btn.setAttribute("aria-pressed", saved ? "true" : "false");
    btn.classList.toggle("is-saved", saved);
    btn.classList.toggle("is-busy", busy);
    if (busy) {
      btn.setAttribute("aria-disabled", "true");
      btn.setAttribute("aria-busy", "true");
    } else {
      btn.removeAttribute("aria-disabled");
      btn.removeAttribute("aria-busy");
    }
  }

  function rowError(li, text) {
    var old = li.querySelector(".row-error");
    if (old) old.parentNode.removeChild(old);
    if (!text) return;
    var meta = li.querySelector(".paper__meta");
    var el = h("p", { class: "row-error", role: "alert" }, text);
    meta.parentNode.insertBefore(el, meta.nextSibling);
  }

  function highlightCount(id) {
    var it = libItem(id);
    return it && typeof it.highlight_count === "number" ? it.highlight_count : 0;
  }

  function confirmCopy(n) {
    return n > 0
      ? "Remove from Library? This deletes the saved PDF and " + n + (n === 1 ? " highlight" : " highlights") +
        " with " + (n === 1 ? "its note" : "their notes") + "."
      : "Remove from Library? This deletes the saved PDF.";
  }

  function saveControl(r, titleId) {
    var btn = h("button", { type: "button", class: "btn btn--secondary btn--small save",
      "aria-describedby": titleId, "data-save": r.paper_id });
    setSaveButton(btn, r.saved ? "done" : "idle");

    function li() { return btn.closest("li"); }

    function save() {
      rowError(li(), "");
      setSaveButton(btn, "busy");
      postJSON("/api/library", { paper_id: r.paper_id, topic: state.topic })
        .then(function (data) {
          r.saved = true;
          libraryAdd(data && data.paper);
          setSaveButton(btn, "done");
          announce("Saved to Library.");
        })
        .catch(function (err) {
          setSaveButton(btn, "idle");
          rowError(li(), "Could not save. " + failMessage(err));
        });
    }

    function unsave() {
      rowError(li(), "");
      closeConfirm(false);
      setSaveButton(btn, "removing");
      btn.focus();
      fetch("/api/library?paper_id=" + encodeURIComponent(r.paper_id), { method: "DELETE" })
        .then(function (res) {
          return res.json().catch(function () { return null; }).then(function (body) {
            if (!res.ok) throw new Error(errorText(res, body));
          });
        })
        .then(function () {
          r.saved = false;
          libraryRemove(r.paper_id);
          setSaveButton(btn, "idle");
          announce("Removed from Library.");
        })
        .catch(function (err) {
          setSaveButton(btn, "done");
          rowError(li(), "Could not remove from Library. " + failMessage(err));
        });
    }

    var group = null;
    function closeConfirm(refocus) {
      if (!group) return;
      group.parentNode.removeChild(group);
      group = null;
      btn.hidden = false;
      if (refocus) btn.focus();
    }

    function confirm() {
      rowError(li(), "");
      var keep = h("button", { type: "button", class: "btn btn--secondary btn--small" }, "Keep");
      var remove = h("button", { type: "button", class: "btn btn--secondary btn--small btn--remove",
        "data-confirm-remove": "" }, "Remove");
      keep.addEventListener("click", function () { closeConfirm(true); });
      remove.addEventListener("click", unsave);
      group = h("div", { class: "confirm", role: "group", "aria-label": "Confirm removal",
        "data-confirm": "unsave" },
        h("p", { class: "confirm__text" }, confirmCopy(highlightCount(r.paper_id))), remove, keep);
      group.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") { ev.stopPropagation(); closeConfirm(true); }
      });
      var head = btn.parentNode;
      head.parentNode.insertBefore(group, head.nextSibling);
      btn.hidden = true;
      keep.focus();
    }

    btn.addEventListener("click", function () {
      if (btn.getAttribute("aria-disabled") === "true") return;
      if (btn.getAttribute("aria-pressed") === "true") confirm(); else save();
    });
    // Keep the saved state in step with the Library (an unsave done in the Library view).
    btn.syncSaved = function () {
      if (!lib.loaded || btn.getAttribute("aria-disabled") === "true" || group) return;
      var now = !!libItem(r.paper_id);
      if (now === !!r.saved) return;
      r.saved = now;
      setSaveButton(btn, now ? "done" : "idle");
    };
    return btn;
  }

  function syncSaveButtons() {
    Array.prototype.forEach.call(listEl.querySelectorAll("button.save"), function (b) {
      if (b.syncSaved) b.syncSaved();
    });
  }

  function paperRow(id) {
    return document.getElementById("paper-" + id);
  }

  // ---- states: empty, no results, notes, alert (D13, D29-D31) ----

  var emptyTitle = emptyEl.querySelector(".empty__title");
  var emptyBody = emptyEl.querySelector(".empty__body");
  var emptyExamples = emptyEl.querySelector(".empty__examples");
  var firstRunTitle = emptyTitle.textContent;
  var firstRunBody = emptyBody.textContent;

  function showEmpty(mode, topic) {
    if (mode === "none") {
      emptyTitle.textContent = topic ? "No papers found for “" + topic + "”." : "No papers found.";
      emptyBody.textContent = "Try broader keywords, or paste arXiv IDs or PDF links.";
      emptyExamples.hidden = true;
    } else {
      emptyTitle.textContent = firstRunTitle;
      emptyBody.textContent = firstRunBody;
      emptyExamples.hidden = false;
    }
    emptyEl.hidden = false;
  }

  emptyEl.addEventListener("click", function (ev) {
    var b = ev.target.closest ? ev.target.closest("[data-example]") : null;
    if (!b) return;
    input.value = b.getAttribute("data-example");
    input.focus();
  });

  function showNotes(errors) {
    clear(notesEl);
    var list = errors || [];
    if (list.length) {
      notesEl.appendChild(h("p", { class: "notes__title" },
        "Could not fetch " + plural(list.length, "input")));
      notesEl.appendChild(h("ul", {}, list.map(function (e) {
        return h("li", {}, h("code", {}, e.input), ": " + e.reason);
      })));
    }
    notesEl.hidden = !list.length;
  }

  function showAlert(detail) {
    clear(alertEl);
    if (detail) {
      var retry = h("button", { type: "button", class: "btn btn--on-dark" }, "Try again");
      retry.addEventListener("click", function () {
        if (state.lastQuery) runTriage(state.lastQuery);
      });
      alertEl.appendChild(h("p", { class: "alert__title" }, "Triage failed."));
      alertEl.appendChild(h("p", { class: "alert__detail" }, detail));
      alertEl.appendChild(retry);
    }
    alertEl.hidden = !detail;
  }

  // ---- render results (D7) ----

  function failedCount(rs) {
    return rs.filter(function (r) { return r.status === "failed"; }).length;
  }

  function render(data, stored) {
    var rs = data.results || [];
    var hadRows = state.rows.length > 0;
    state.rows = rs.slice();
    state.topic = data.topic || "";
    state.stored = !!stored;
    state.query = stored ? state.topic : state.lastQuery;
    // After a reload the server sends no paging fields: next offset = rows shown (data-model).
    state.nextOffset = stored ? rs.length : (data.next_offset === undefined ? null : data.next_offset);
    state.hasMore = stored ? !!state.topic : !!data.has_more;
    clear(listEl);
    rs.forEach(function (r) { listEl.appendChild(row(r)); });
    showNotes(data.errors);
    heading.textContent = data.topic ? "Ranked papers for “" + data.topic + "”" : "Ranked papers";
    var failed = failedCount(rs);
    var tail = failed ? " · " + failed + " could not be processed" : "";
    if (rs.length) {
      emptyEl.hidden = true;
      countEl.textContent = (stored
        ? "Showing " + plural(rs.length, "stored paper") + " from your last run"
        : plural(rs.length, "paper") + " · sorted by relevance") + tail;
      countEl.hidden = false;
      statusEl.textContent = stored ? ""
        : plural(rs.length, "paper") + " ranked" + (failed ? ", " + failed + " could not be processed" : "") +
          ". Results below.";
    } else {
      countEl.hidden = true;
      showEmpty("none", data.topic);
      statusEl.textContent = "No papers found.";
    }
    // A new result set replaces the chat scope; a transcript about the old set no longer applies.
    resetChat(hadRows && rs.length > 0 && !stored);
    refreshLoadMore();
  }

  // ---- searching indicator (D14-D18): activity and elapsed time, never progress ----

  var VERBS = [
    "Fetching papers…", "Reading full text…", "Summarizing abstracts…", "Looking for weak claims…",
    "Checking for missing baselines…", "Weighing overclaims…", "Ranking by relevance…"
  ];
  var SHOW_DELAY_MS = 300;
  var VERB_MS = 2400;
  // Reduced motion: the verb never changes (FR-012); a neutral label replaces the stage loop.

  var work = { el: null, compact: false, t0: 0, showT: null, tickT: null, verbT: null, verbI: 0,
    verbEl: null, timeEl: null, noteEl: null, minutes: 0 };

  function reducedMotion() {
    return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  function clock(sec) {
    var m = Math.floor(sec / 60);
    var r = sec % 60;
    return m + ":" + (r < 10 ? "0" : "") + r;
  }

  function noteFor(sec) {
    if (sec >= 180) return "Taking longer than usual. The request has not failed; you can keep waiting.";
    if (sec >= 90) return "Still working. Papers are processed in parallel; results appear when all are ranked.";
    return state.mock ? "Mock mode: canned responses, usually a few seconds."
      : "Live runs take 1 to 3 minutes for up to 10 papers.";
  }

  function elapsedSec() {
    return Math.floor((performance.now() - work.t0) / 1000);
  }

  function updateClock() {
    var sec = elapsedSec();
    if (work.timeEl) work.timeEl.textContent = clock(sec);
    if (work.noteEl) work.noteEl.textContent = noteFor(sec);
    var min = Math.floor(sec / 60);
    if (min > work.minutes) {
      work.minutes = min;
      statusEl.textContent = "Still working, " + plural(min, "minute") + " elapsed.";
    }
  }

  function nextVerb() {
    if (!work.verbEl) return;
    work.verbI = (work.verbI + 1) % VERBS.length;
    if (reducedMotion()) { work.verbEl.textContent = VERBS[work.verbI]; return; }
    var el = work.verbEl;
    el.classList.add("is-out");
    window.setTimeout(function () {
      if (work.verbEl !== el) return;
      el.textContent = VERBS[work.verbI];
      el.classList.remove("is-out");
      el.classList.remove("is-in");
      void el.offsetWidth;
      el.classList.add("is-in");
    }, 150);
  }

  function showWorking() {
    var el = work.el;
    clear(el);
    work.verbI = 0;
    var still = reducedMotion();
    work.verbEl = h("span", { class: "working__verb", "aria-hidden": "true" },
      still ? (work.compact ? "Loading more papers…" : "Triaging papers…") : VERBS[0]);
    work.timeEl = h("span", { class: "working__time", "aria-hidden": "true" }, clock(elapsedSec()));
    work.noteEl = work.compact ? null : h("p", { class: "working__note" }, noteFor(elapsedSec()));
    el.appendChild(h("div", { class: "working__row" },
      h("span", { class: "working__glyph" }, rayGlyph(work.compact ? 16 : 20)), work.verbEl, work.timeEl));
    if (work.noteEl) el.appendChild(work.noteEl);
    el.hidden = false;
    if (!still) work.verbT = window.setInterval(nextVerb, VERB_MS);
  }

  function startWorking(el, compact) {
    stopWorking();
    work.el = el || workingEl;
    work.compact = !!compact;
    work.t0 = performance.now();
    work.minutes = 0;
    work.showT = window.setTimeout(showWorking, SHOW_DELAY_MS);
    work.tickT = window.setInterval(updateClock, 1000);
    if (compact) return;
    // The first-run empty state would contradict the running indicator.
    emptyEl.hidden = true;
    // Previous list stays visible but inert while a new run is in flight (D18).
    [listEl, notesEl].forEach(function (el) {
      el.setAttribute("inert", "");
      el.classList.add("is-stale");
    });
  }

  function stopWorking() {
    window.clearTimeout(work.showT);
    window.clearInterval(work.tickT);
    window.clearInterval(work.verbT);
    work.showT = work.tickT = work.verbT = null;
    work.verbEl = work.timeEl = work.noteEl = null;
    [workingEl, workingMoreEl].forEach(function (el) { clear(el); el.hidden = true; });
    work.el = null;
    [listEl, notesEl].forEach(function (el) {
      el.removeAttribute("inert");
      el.classList.remove("is-stale");
    });
  }

  // ---- submit ----

  function setBusy(busy) {
    state.running = busy;
    button.disabled = busy;
    button.textContent = busy ? "Triaging…" : "Triage papers";
    if (busy) input.setAttribute("readonly", ""); else input.removeAttribute("readonly");
    results.setAttribute("aria-busy", busy ? "true" : "false");
    if (busy) startWorking(); else stopWorking();
    refreshLoadMore();
  }

  function runTriage(query) {
    if (state.running) return;
    state.lastQuery = query;
    state.generation++; // any load-more reply still in flight belongs to the old result set
    state.loadingMore = false;
    moreError.hidden = true;
    setBusy(true);
    showAlert("");
    statusEl.textContent = state.mock ? "Triage started." : "Triage started. This can take 1 to 3 minutes.";
    postJSON("/api/triage", { query: query })
      .then(function (data) { render(data, false); })
      .catch(function (err) {
        showAlert(failMessage(err));
        statusEl.textContent = "";
        if (!state.rows.length) showEmpty("first");
      })
      .then(function () { setBusy(false); });
  }


  // ---- load 5 more (D19, D20) ----

  var loadMoreLabel = "Load 5 more papers";

  function setMoreLabel(loading) {
    clear(moreBtn);
    if (loading) {
      moreBtn.appendChild(rayGlyph(16, "btn__glyph"));
      moreBtn.appendChild(document.createTextNode("Loading 5 more…"));
    } else {
      moreBtn.appendChild(document.createTextNode(loadMoreLabel));
    }
  }

  // Shown only for topic searches with a loaded result set. Hidden during a full triage, when the
  // server says there is nothing more, and at the 50-paper limit.
  function refreshLoadMore() {
    var offered = !!state.topic && state.rows.length > 0 && state.nextOffset !== null &&
      !state.running;
    if (!offered) { moreWrap.hidden = true; return; }
    var full = state.rows.length >= MAX_IDS;
    var canLoad = state.hasMore && !full;
    moreWrap.hidden = false;
    moreBtn.hidden = !canLoad;
    if (state.loadingMore) {
      moreBtn.setAttribute("aria-disabled", "true");
    } else {
      moreBtn.removeAttribute("aria-disabled");
    }
    if (!state.loadingMore) {
      setMoreLabel(false);
      if (!moreError.hidden) moreBtn.firstChild.nodeValue = "Try again";
    }
    var t = "“" + state.topic + "”";
    moreCaption.textContent = !canLoad
      ? (full && state.hasMore
        ? "Showing " + MAX_IDS + " papers, the most one search holds."
        : "No more papers for " + t + ".")
      : "Showing " + plural(state.rows.length, "paper") + " for " + t + ".";
  }

  function showMoreError(detail) {
    moreError.textContent = "Could not load more papers. " + detail;
    moreError.hidden = false;
  }

  function appendPage(data) {
    var seen = {};
    state.rows.forEach(function (r) { seen[r.paper_id] = true; });
    var fresh = [];
    (data.results || []).forEach(function (r) {
      if (seen[r.paper_id] || state.rows.length + fresh.length >= MAX_IDS) return;
      seen[r.paper_id] = true;
      fresh.push(r);
    });
    var first = state.rows.length + 1;
    if (fresh.length) {
      listEl.appendChild(h("li", { class: "batch-sep", "aria-hidden": "true" },
        fresh.length === 1 ? "Paper " + first : "Papers " + first + "–" + (first + fresh.length - 1)));
    }
    var added = [];
    fresh.forEach(function (r) {
      var li = row(r);
      li.classList.add("paper--new");
      listEl.appendChild(li);
      added.push(li);
      state.rows.push(r);
    });
    window.setTimeout(function () {
      added.forEach(function (li) { li.classList.remove("paper--new"); });
    }, reducedMotion() ? 5000 : 1600);
    return added;
  }

  function loadMore() {
    if (state.loadingMore || state.running || !state.hasMore) return;
    var gen = state.generation;
    var focusOnButton = true;
    state.loadingMore = true;
    moreError.hidden = true;
    setMoreLabel(true);
    refreshLoadMore();
    statusEl.textContent = "Loading 5 more papers.";
    startWorking(workingMoreEl, true);
    postJSON("/api/triage", { query: state.query, max_results: PAGE, offset: state.nextOffset })
      .then(function (data) {
        if (gen !== state.generation) return;
        focusOnButton = document.activeElement === moreBtn;
        var added = appendPage(data);
        state.nextOffset = data.next_offset === undefined ? null : data.next_offset;
        state.hasMore = !!data.has_more && state.nextOffset !== null;
        var failed = failedCount(state.rows);
        countEl.textContent = plural(state.rows.length, "paper") +
          " · sorted by relevance within each batch" +
          (failed ? " · " + failed + " could not be processed" : "");
        statusEl.textContent = !added.length
          ? "No new papers in this batch." + (state.hasMore ? "" : " No more for this topic.")
          : "Added " + plural(added.length, "paper") + ". " +
            (state.hasMore ? state.rows.length + " shown." : "No more for this topic.");
        state.loadingMore = false;
        stopWorking();
        refreshLoadMore();
        if (!added.length) {
          moreCaption.textContent = "No new papers in this batch. " + moreCaption.textContent;
        } else if (focusOnButton) {
          added[0].focus();
          added[0].scrollIntoView({ block: "start" });
        }
        if (added.length) {
          // The result set grew: chat scope = every row now shown, transcript starts over.
          resetChat(true);
        } else {
          refreshChat();
        }
      })
      .catch(function (err) {
        if (gen !== state.generation) return;
        state.loadingMore = false;
        stopWorking();
        showMoreError(failMessage(err));
        statusEl.textContent = "";
        refreshLoadMore();
      });
  }

  moreBtn.addEventListener("click", loadMore);

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var query = input.value.trim();
    if (!query) {
      showAlert("");
      statusEl.textContent = "Enter a topic, arXiv IDs, or PDF URLs first.";
      input.focus();
      return;
    }
    runTriage(query);
  });

  // ---- chat: suggestions (D28) ----

  var suggestEl = h("div", { class: "chat__suggest", hidden: "" },
    h("p", { class: "chat__suggest-label" }, "Try one of these:"),
    h("ul", {}, [
      "Which paper has the strongest evidence?",
      "What baselines are missing across these papers?",
      "What does the top-ranked paper claim?"
    ].map(function (q) {
      var b = h("button", { type: "button", class: "btn btn--secondary btn--small btn--suggest" }, q);
      b.addEventListener("click", function () {
        question.value = q;
        chatForm.requestSubmit ? chatForm.requestSubmit() : askBtn.click();
      });
      return h("li", {}, b);
    })));
  chatEl.insertBefore(suggestEl, logEl);

  var chatBusy = false;
  var chatGen = 0; // bumped on every reset; answers for an older scope are dropped
  var scopeEl = document.getElementById("chat-scope");
  var noteEl = document.getElementById("chat-note");

  function okCount() {
    return state.rows.filter(function (r) { return r.status !== "failed"; }).length;
  }

  // Result set changed: clear the transcript, rescope the chat (askInto sends the current rows),
  // and say so. The visible line sits in the chat; #status announces it (polite live region).
  // Callers set #status first; the scope sentence is appended here, once, so each reset is
  // announced exactly once (the note itself is not a live region).
  function resetChat(announce) {
    chatGen++;
    chatBusy = false; // a reply still in flight belongs to the old scope and is dropped
    clear(logEl);
    var failed = failedCount(state.rows);
    var line = "Chat now covers " + plural(okCount(), "paper") +
      (failed ? " (" + failed + " could not be processed and cannot be asked about)" : "") +
      ". Earlier questions were cleared.";
    noteEl.textContent = announce ? line : "";
    noteEl.hidden = !announce;
    if (announce) statusEl.textContent += (statusEl.textContent ? " " : "") + line;
    refreshChat();
  }

  // The chat is scoped to the papers shown (first page + load-more pages), sent as paper_ids.
  function refreshChat() {
    var n = okCount();
    var empty = !state.rows.length;
    clear(scopeEl);
    if (empty) {
      scopeEl.textContent = "Run a search first. Chat only answers from papers triaged here.";
    } else {
      append(scopeEl, ["Chatting about ", h("strong", {}, plural(n, "paper")),
        state.stored ? " from your last run." : " from this search."]);
    }
    question.disabled = empty;
    askBtn.disabled = empty || chatBusy;
    refreshSuggestions();
  }

  function refreshSuggestions() {
    var hasOk = state.rows.some(function (r) { return r.status !== "failed"; });
    suggestEl.hidden = !(hasOk && !logEl.firstChild);
  }

  // ---- chat: citations (D25) ----

  function titleOf(id) {
    var r = paperRow(id);
    var t = r && r.querySelector(".paper__title");
    return t ? t.textContent : "";
  }

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)");

  function flash(target) {
    target.classList.remove("paper--cited");
    void target.offsetWidth; // restart the animation
    target.classList.add("paper--cited");
    window.setTimeout(function () { target.classList.remove("paper--cited"); },
      reduceMotion && reduceMotion.matches ? 2000 : 1600);
  }

  function cite(id) {
    if (!paperRow(id)) {
      return h("span", { class: "cite cite--off", title: "Not in the list shown" }, id);
    }
    var t = titleOf(id);
    var a = h("a", { class: "cite", href: "#paper-" + encodeURIComponent(id),
      "aria-label": t ? "Paper " + id + ": " + t : null }, id);
    a.addEventListener("click", function (ev) {
      var target = paperRow(id);
      if (!target) return;
      ev.preventDefault();
      target.scrollIntoView({ block: "start" });
      target.focus();
      flash(target);
      if (window.history && history.replaceState) history.replaceState(null, "", a.getAttribute("href"));
    });
    return a;
  }

  // Inline [id] markers become chips only for ids the server validated; markers the server
  // dropped (unknown ids) are removed so no made-up id is shown.
  function answerNodes(text, citations, dropped) {
    var ok = citations || [];
    var bad = dropped || [];
    return String(text).split(/(\[[^\[\]\s]+\])/).map(function (part, i) {
      if (i % 2 === 0) return part;
      var id = part.slice(1, -1);
      if (ok.indexOf(id) !== -1) return cite(id);
      if (bad.indexOf(id) !== -1) return "";
      return part;
    });
  }

  function sources(ids) {
    if (!ids || !ids.length) return null;
    return h("div", { class: "sources" },
      h("p", { class: "sources__h" }, ids.length === 1 ? "Cited paper" : "Cited papers"),
      h("ul", {}, ids.map(function (id) {
        return h("li", {}, cite(id), h("span", { class: "sources__title" }, titleOf(id)));
      })));
  }

  // ---- chat: turns (D24, D26, D27) ----

  function newTurn(q) {
    var turn = h("li", { class: "turn" },
      h("p", { class: "turn__q" }, h("span", { class: "sr-only" }, "You asked: "), q));
    logEl.appendChild(turn);
    noteEl.hidden = true;
    suggestEl.hidden = true;
    turn.scrollIntoView({ block: "nearest" });
    return turn;
  }

  function pendingEl() {
    return h("p", { class: "turn__pending" }, rayGlyph(16, "turn__glyph"), "Reading your papers…");
  }

  function answerEl(data) {
    if (data.refused) {
      return h("div", { class: "turn__a turn__a--refused" },
        h("p", { class: "turn__refused-title" }, "Not in these papers"),
        h("p", { class: "turn__refused-body" }, data.answer),
        h("p", { class: "turn__refused-hint" },
          "Ask about something these papers cover, or run a new search above."));
    }
    var box = h("div", { class: "turn__a" }, h("span", { class: "sr-only" }, "Answer: "),
      answerNodes(data.answer, data.citations, data.dropped_citations));
    var src = sources(data.citations);
    if (src) box.appendChild(src);
    return box;
  }

  function askInto(turn, q) {
    var pending = pendingEl();
    turn.appendChild(pending);
    chatBusy = true;
    askBtn.disabled = true;
    var ids = state.rows.map(function (r) { return r.paper_id; }).slice(0, 50);
    var gen = chatGen;
    postJSON("/api/chat", { question: q, paper_ids: ids })
      .then(function (data) {
        if (gen !== chatGen) return; // result set changed meanwhile; the turn is gone
        turn.removeChild(pending);
        turn.appendChild(answerEl(data));
      })
      .catch(function (err) {
        if (gen !== chatGen) return;
        turn.removeChild(pending);
        var again = h("button", { type: "button", class: "btn btn--secondary btn--small" }, "Ask again");
        again.addEventListener("click", function () {
          if (chatBusy) return;
          turn.removeChild(errBox);
          askInto(turn, q);
        });
        var errBox = h("div", { class: "turn__err", role: "alert" },
          h("p", {}, "Could not answer. " + failMessage(err)), again);
        turn.appendChild(errBox);
      })
      .then(function () {
        if (gen !== chatGen) return; // reset already cleared the busy state for the new scope
        chatBusy = false;
        askBtn.disabled = !state.rows.length;
        turn.scrollIntoView({ block: "nearest" });
        question.focus();
      });
  }

  chatForm.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = question.value.trim();
    if (!q) { question.focus(); return; }
    if (askBtn.disabled || chatBusy) return;
    question.value = "";
    askInto(newTurn(q), q);
  });

  // ---- keyboard (D35) ----

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "/" || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var t = ev.target;
    var tag = t && t.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;
    // `/` focuses the main input of the current view.
    var target = route.view === "library" ? document.getElementById("lib-filter")
      : route.view === "preview" ? document.getElementById("pv-chat-question") : input;
    if (!target) return;
    ev.preventDefault();
    target.focus();
  });

  input.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && !state.running) input.value = "";
  });


  // ---- views, hash routes, Library data (v3: L1, L2, L14) ----
  // Triage state stays in memory: switching views only toggles `hidden` (FR-024).

  var libraryEl = document.getElementById("library");
  var libHeading = document.getElementById("library-heading");
  var libListEl = document.getElementById("library-list");
  var navCountEl = document.querySelector(".views__count");
  var previewHeading = document.getElementById("preview-heading");
  var pvStage = document.getElementById("pv-stage");
  var pvBack = document.getElementById("pv-back");

  var BASE_TITLE = "Paper Triage";
  var HEADINGS = { triage: "intro-heading", library: "library-heading", preview: "preview-heading" };

  var route = { view: null, id: null, params: null, hash: "" };
  var libReturn = null;     // where the Library was left for a Preview: hash, scroll, paper id
  var triageScroll = 0;
  var cameFromLibrary = false;
  var viewer = null;        // set by viewer.js through PT.registerViewer
  var viewerFailed = false; // viewer.js did not load (checked on window load)
  if (window.history && "scrollRestoration" in history) history.scrollRestoration = "manual";

  var lib = { papers: [], directories: [], unsorted: 0, total: 0, loaded: false, error: null,
    pending: null, sig: "", dirty: false };

  function parseParams(qs) {
    var out = { dir: "", tags: [], q: "" };
    String(qs || "").split("&").forEach(function (pair) {
      if (!pair) return;
      var i = pair.indexOf("=");
      var k = i < 0 ? pair : pair.slice(0, i);
      var v = i < 0 ? "" : pair.slice(i + 1);
      try {
        if (k === "dir") out.dir = decodeURIComponent(v);
        else if (k === "q") out.q = decodeURIComponent(v);
        else if (k === "tags") {
          out.tags = v.split(",").filter(Boolean).map(function (t) { return decodeURIComponent(t); });
        }
      } catch (e) { /* malformed escape: ignore this parameter */ }
    });
    return out;
  }

  function libraryHash(p) {
    var parts = [];
    if (p && p.dir) parts.push("dir=" + encodeURIComponent(p.dir));
    if (p && p.tags && p.tags.length) parts.push("tags=" + p.tags.map(encodeURIComponent).join(","));
    if (p && p.q) parts.push("q=" + encodeURIComponent(p.q));
    return "#/library" + (parts.length ? "?" + parts.join("&") : "");
  }

  function previewHash(id) {
    return "#/library/paper/" + encodeURIComponent(id);
  }

  // null = a plain in-page fragment (#paper-<id>, skip links): not a route change.
  function parseRoute(hash) {
    if (!hash || hash === "#" || hash === "#/") return { view: "triage" };
    if (hash.indexOf("#/") !== 0) return null;
    var rest = hash.slice(2);
    var q = rest.indexOf("?");
    var parts = (q < 0 ? rest : rest.slice(0, q)).split("/");
    var qs = q < 0 ? "" : rest.slice(q + 1);
    if (parts[0] !== "library") return { view: "triage" };
    if (parts.length === 1 || (parts.length === 2 && parts[1] === "")) {
      return { view: "library", params: parseParams(qs) };
    }
    if (parts[1] === "paper" && parts.length >= 3) {
      try {
        return { view: "preview", id: decodeURIComponent(parts.slice(2).join("/")) };
      } catch (e) { return { view: "triage" }; }
    }
    return { view: "library", params: parseParams(qs) };
  }

  function jump(top) {
    window.scrollTo({ top: top, left: 0, behavior: "instant" });
  }

  function libItem(id) {
    for (var i = 0; i < lib.papers.length; i++) if (lib.papers[i].paper_id === id) return lib.papers[i];
    return null;
  }

  function updateNavCount() {
    var n = lib.loaded ? lib.total : 0;
    navCountEl.textContent = String(n);
    navCountEl.hidden = !n;
  }

  function setLibrary(data) {
    lib.papers = data.papers || [];
    lib.directories = data.directories || [];
    lib.unsorted = data.unsorted_count || 0;
    lib.total = typeof data.total === "number" ? data.total : lib.papers.length;
    lib.loaded = true;
    lib.error = null;
    updateNavCount();
  }

  // Fetches GET /api/library once at a time. Resolves true when the data changed.
  function loadLibrary() {
    if (lib.pending) return lib.pending;
    lib.pending = getJSON("/api/library").then(function (data) {
      var sig = JSON.stringify(data);
      var changed = sig !== lib.sig;
      lib.sig = sig;
      if (changed || !lib.loaded) setLibrary(data);
      return changed;
    }).catch(function (err) {
      lib.error = err.message === "Failed to fetch" ? NETWORK_MSG : failMessage(err);
      return true;
    }).then(function (changed) {
      lib.pending = null;
      if (lib.dirty) { lib.dirty = false; return loadLibrary(); }
      return changed;
    });
    return lib.pending;
  }

  // After a save or unsave elsewhere on the page: keep the cached list and nav count current.
  // Before the first load the list is unknown, so reload instead of guessing a total.
  function libraryAdd(item) {
    if (!lib.loaded) { lib.dirty = true; if (!lib.pending) loadLibrary(); return; }
    if (!item || libItem(item.paper_id)) return;
    lib.papers.unshift(item);
    lib.total = lib.papers.length;
    lib.sig = "";
    updateNavCount();
  }

  function libraryRemove(id) {
    if (!lib.loaded) { lib.dirty = true; if (!lib.pending) loadLibrary(); return; }
    lib.papers = lib.papers.filter(function (p) { return p.paper_id !== id; });
    lib.total = lib.papers.length;
    lib.sig = "";
    updateNavCount();
  }

  // ---- Library view: library.js registers the renderer (PT.registerLibrary) ----

  var libraryView = null;

  function restoreLibraryReturn() {
    if (!libReturn || libReturn.hash !== route.hash) return;
    var ret = libReturn;
    libReturn = null;
    var btn = null;
    var btns = libListEl.querySelectorAll("[data-open-preview]");
    for (var i = 0; i < btns.length; i++) {
      if (btns[i].getAttribute("data-open-preview") === ret.id) btn = btns[i];
    }
    jump(ret.y);
    if (btn) btn.focus({ preventScroll: true });
  }

  function renderLibrary(restore) {
    if (!libraryView) return;
    libraryView.render();
    if (restore) restoreLibraryReturn();
  }

  // Filters live in the hash, but typing or clicking a chip must not add history entries.
  function setLibraryParams(p) {
    var hash = libraryHash(p);
    route.params = p;
    route.hash = hash;
    if (window.history && history.replaceState) history.replaceState(null, "", hash);
  }

  function reloadLibrary() {
    lib.sig = "";
    return loadLibrary();
  }

  // Entering the Library from elsewhere shows the cached list at once and refreshes it in the
  // background; the list is rebuilt only when the server data changed.
  function enterLibrary(force) {
    renderLibrary(true);
    if (lib.loaded && !force) return;
    if (force) { lib.error = null; renderLibrary(false); }
    loadLibrary().then(function (changed) {
      if (route.view === "library" && changed) renderLibrary(true);
    });
  }

  // ---- Preview view (shell; viewer.js renders the PDF, T055) ----

  function previewState(title, body, action) {
    clear(pvStage);
    pvStage.hidden = false;
    pvStage.appendChild(h("div", { class: "empty" },
      h("p", { class: "empty__title" }, title),
      body ? h("p", { class: "empty__body" }, body) : null,
      action || null));
  }

  function renderPreview() {
    var id = route.id;
    if (!lib.loaded && !lib.error) {
      previewHeading.textContent = "Opening…";
      loadLibrary().then(function () { if (route.view === "preview" && route.id === id) renderPreview(); });
      return;
    }
    if (lib.error && !lib.loaded) {
      var again = h("button", { type: "button", class: "btn btn--secondary" }, "Try again");
      again.addEventListener("click", function () {
        lib.error = null;
        renderPreview();
      });
      previewHeading.textContent = "Preview";
      previewState("Could not load your library.", lib.error, h("p", { class: "empty__actions" }, again));
      return;
    }
    var it = libItem(id);
    var title = it ? it.title : "Preview";
    previewHeading.textContent = title;
    previewHeading.setAttribute("title", title);
    document.title = (it ? title : "Preview") + " · " + BASE_TITLE;
    if (!it) {
      if (viewer) viewer.close();
      previewState("This paper is not in your Library.", null,
        h("p", { class: "empty__actions" }, h("a", { class: "btn btn--secondary", href: "#/library" }, "Go to Library")));
      return;
    }
    if (viewer) viewer.open(it);
    else if (viewerFailed) previewState("This PDF could not be displayed.", "The viewer did not load. Reload the page.");
  }

  pvBack.addEventListener("click", function () {
    if (cameFromLibrary) history.back();
    else location.hash = libReturn ? libReturn.hash : "#/library";
  });

  // ---- router ----

  function announce(text) {
    statusEl.textContent = text;
  }

  // Per-view skip links; one that needs a target (the panel) shows only while that target does.
  function refreshSkipLinks(view) {
    view = view || route.view;
    Array.prototype.forEach.call(document.querySelectorAll("[data-skip]"), function (el) {
      var need = el.getAttribute("data-skip-needs");
      var t = need ? document.getElementById(need) : null;
      el.hidden = el.getAttribute("data-skip") !== view ||
        (!!need && (!t || t.hidden || !t.getClientRects().length));
    });
  }

  function setView(view) {
    Array.prototype.forEach.call(document.querySelectorAll("[data-route]"), function (el) {
      el.hidden = el.getAttribute("data-route") !== view;
    });
    refreshSkipLinks(view);
    Array.prototype.forEach.call(document.querySelectorAll(".views a"), function (a) {
      var on = a.getAttribute("data-view") === (view === "preview" ? "library" : view);
      if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
    });
  }

  function applyRoute(first) {
    var r = parseRoute(location.hash);
    if (!r) return; // in-page fragment: stay where we are
    var prev = route;
    if (prev.view === "triage") triageScroll = window.scrollY;
    if (prev.view === "library" && r.view === "preview") {
      libReturn = { hash: prev.hash, y: window.scrollY, id: r.id };
    }
    cameFromLibrary = prev.view === "library" && r.view === "preview";
    if (prev.view === "preview" && r.view !== "preview" && viewer) viewer.close();
    route = { view: r.view, id: r.id || null, params: r.params || null, hash: location.hash };
    setView(r.view);
    if (r.view === "triage") {
      document.title = BASE_TITLE;
      syncSaveButtons();
      jump(first ? 0 : triageScroll);
    } else if (r.view === "library") {
      document.title = "Library · " + BASE_TITLE;
      jump(0);
      enterLibrary(false);
    } else {
      document.title = "Preview · " + BASE_TITLE;
      jump(0);
      renderPreview();
    }
    if (first) return;
    var focusTarget = document.getElementById(HEADINGS[r.view]);
    var restored = r.view === "library" && !libReturn && document.activeElement &&
      document.activeElement.hasAttribute && document.activeElement.hasAttribute("data-open-preview");
    if (focusTarget && !restored) focusTarget.focus({ preventScroll: true });
    announce(r.view === "triage" ? "Triage."
      : r.view === "library" ? "Library."
      : "Preview: " + (libItem(r.id) ? libItem(r.id).title : "opening") + ".");
  }

  window.addEventListener("hashchange", function () { applyRoute(false); });
  window.addEventListener("resize", function () { if (route.view === "preview") refreshSkipLinks(); });
  window.addEventListener("load", function () {
    if (viewer) return;
    viewerFailed = true;
    if (route.view === "preview" && libItem(route.id)) renderPreview();
  });

  // Skip links move focus without touching the hash (a hash change would be a route change).
  Array.prototype.forEach.call(document.querySelectorAll("a.skip"), function (a) {
    a.addEventListener("click", function (ev) {
      var target = document.getElementById((a.getAttribute("href") || "").slice(1));
      if (!target) return;
      ev.preventDefault();
      if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
      target.focus();
    });
  });

  // Shared with viewer.js (a separate ES module); see T055.
  window.PT = {
    h: h, svg: svg, clear: clear, rayGlyph: rayGlyph, refreshSkipLinks: refreshSkipLinks, plural: plural, announce: announce, getJSON: getJSON,
    postJSON: postJSON, failMessage: failMessage, reducedMotion: reducedMotion,
    route: function () { return route; }, libItem: libItem, loadLibrary: loadLibrary,
    libraryAdd: libraryAdd, libraryRemove: libraryRemove, libraryHash: libraryHash,
    previewHash: previewHash, rankBlock: rankBlock, details: details, paperLinks: paperLinks,
    authorsLine: authorsLine, lib: function () { return lib; }, setLibraryParams: setLibraryParams, reloadLibrary: reloadLibrary,
    enterLibrary: enterLibrary, jump: jump,
    registerLibrary: function (v) {
      libraryView = v;
      if (route.view === "library") renderLibrary(true);
    },
    registerViewer: function (v) {
      viewer = v;
      if (route.view === "preview" && lib.loaded) renderPreview();
    }
  };

  // ---- on load: backend status and stored results (no refetching from arXiv) ----

  function loadStatus() {
    return getJSON("/api/status").then(function (s) {
      state.mock = !!s.mock;
      mockEl.hidden = !s.mock;
      modelEl.textContent = s.model ? "Model: " + s.model : "";
      modelEl.hidden = !s.model;
    }).catch(function () {
      // Unknown state: stay quiet rather than claim live or mock.
      mockEl.hidden = true;
      modelEl.hidden = true;
    });
  }

  function loadStored() {
    return getJSON("/api/papers").then(function (data) {
      if (state.running) return; // a triage run started meanwhile; its result wins
      if (data && data.results && data.results.length) render(data, true);
    }).catch(function () {
      // Nothing stored or server unreachable: keep the empty state.
    });
  }

  refreshChat();
  loadStatus();
  loadStored();
  applyRoute(true);
  if (route.view === "triage") loadLibrary(); // fills the nav count; Library and Preview load it themselves
})();
