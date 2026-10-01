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

  var SVG_NS = "http://www.w3.org/2000/svg";
  var NETWORK_MSG = "Could not reach the server. Check that the app is running.";

  var state = {
    rows: [],          // result items currently shown, in display order
    lastQuery: "",
    running: false,
    mock: false
  };

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
      if (!res.ok) throw new Error(String(res.status));
      return res.json();
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

  // ---- paper rows (D8, D9, D11) ----

  function rankBlock(r, failed) {
    var n = failed ? null : Math.max(0, Math.min(10, Number(r.rank) || 0));
    return h("div", { class: "rank" },
      h("div", { class: "rank__line" },
        h("span", { class: "rank__n", "aria-label": failed ? "No rank" : "Rank " + n + " of 10" },
          failed ? "–" : String(n)),
        failed ? null : h("span", { class: "rank__of", "aria-hidden": "true" }, "/10")),
      failed ? null : h("div", { class: "rank__meter", "aria-hidden": "true", style: "--rank:" + n },
        h("span", {})));
  }

  function row(r) {
    var failed = r.status === "failed";
    var meta = h("div", { class: "paper__meta" },
      h("span", { class: "paper__id" }, r.paper_id),
      r.basis === "abstract" ? h("span", { class: "flag" }, "Abstract only") : null,
      failed ? h("span", { class: "flag flag--failed" }, "Failed") : null);
    var reason = failed
      ? h("p", { class: "paper__reason paper__reason--failed" }, r.error || "This paper could not be processed.")
      : h("p", { class: "paper__reason" }, r.rank_reason || "");
    return h("li", { class: "paper", id: "paper-" + r.paper_id, tabindex: "-1" },
      rankBlock(r, failed),
      h("div", { class: "paper__body" },
        h("h3", { class: "paper__title" }, r.title),
        authorsLine(r.authors) ? h("p", { class: "paper__authors" }, authorsLine(r.authors)) : null,
        reason, meta, details(r)));
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
    state.rows = rs.slice();
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
    refreshSuggestions();
  }

  // ---- searching indicator (D14-D18): activity and elapsed time, never progress ----

  var VERBS = [
    "Fetching papers…", "Reading full text…", "Summarizing abstracts…", "Looking for weak claims…",
    "Checking for missing baselines…", "Weighing overclaims…", "Ranking by relevance…"
  ];
  var SHOW_DELAY_MS = 300;
  var VERB_MS = 2400;
  var VERB_MS_REDUCED = 5000;

  var work = { t0: 0, showT: null, tickT: null, verbT: null, verbI: 0, verbEl: null, timeEl: null,
    noteEl: null, minutes: 0 };

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
    clear(workingEl);
    work.verbI = 0;
    work.verbEl = h("span", { class: "working__verb", "aria-hidden": "true" }, VERBS[0]);
    work.timeEl = h("span", { class: "working__time", "aria-hidden": "true" }, clock(elapsedSec()));
    work.noteEl = h("p", { class: "working__note" }, noteFor(elapsedSec()));
    workingEl.appendChild(h("div", { class: "working__row" },
      h("span", { class: "working__glyph" }, rayGlyph(20)), work.verbEl, work.timeEl));
    workingEl.appendChild(work.noteEl);
    workingEl.hidden = false;
    work.verbT = window.setInterval(nextVerb, reducedMotion() ? VERB_MS_REDUCED : VERB_MS);
  }

  function startWorking() {
    stopWorking();
    work.t0 = performance.now();
    work.minutes = 0;
    work.showT = window.setTimeout(showWorking, SHOW_DELAY_MS);
    work.tickT = window.setInterval(updateClock, 1000);
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
    clear(workingEl);
    workingEl.hidden = true;
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
  }

  function runTriage(query) {
    if (state.running) return;
    state.lastQuery = query;
    setBusy(true);
    showAlert("");
    statusEl.textContent = state.mock ? "Triage started." : "Triage started. This can take 1 to 3 minutes.";
    postJSON("/api/triage", { query: query })
      .then(function (data) { render(data, false); })
      .catch(function (err) {
        showAlert(failMessage(err));
        statusEl.textContent = "";
      })
      .then(function () { setBusy(false); });
  }

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
    askBtn.disabled = true;
    var ids = state.rows.map(function (r) { return r.paper_id; }).slice(0, 50);
    postJSON("/api/chat", { question: q, paper_ids: ids })
      .then(function (data) {
        turn.removeChild(pending);
        turn.appendChild(answerEl(data));
      })
      .catch(function (err) {
        turn.removeChild(pending);
        var again = h("button", { type: "button", class: "btn btn--secondary btn--small" }, "Ask again");
        again.addEventListener("click", function () {
          if (askBtn.disabled) return;
          turn.removeChild(errBox);
          askInto(turn, q);
        });
        var errBox = h("div", { class: "turn__err", role: "alert" },
          h("p", {}, "Could not answer. " + failMessage(err)), again);
        turn.appendChild(errBox);
      })
      .then(function () {
        askBtn.disabled = false;
        turn.scrollIntoView({ block: "nearest" });
        question.focus();
      });
  }

  chatForm.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = question.value.trim();
    if (!q) { question.focus(); return; }
    if (askBtn.disabled) return;
    question.value = "";
    askInto(newTurn(q), q);
  });

  // ---- keyboard (D35) ----

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "/" || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var t = ev.target;
    var tag = t && t.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;
    ev.preventDefault();
    input.focus();
  });

  input.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && !state.running) input.value = "";
  });

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

  loadStatus();
  loadStored();
})();
