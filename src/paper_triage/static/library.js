/* Paper Triage Library view (v3): saved papers, tag and title filters, PDF status polling.
   Classic script; shares state and helpers with app.js through window.PT. All text is set with
   textContent / text nodes (titles and tags are untrusted). */
(function () {
  "use strict";

  var PT = window.PT;
  if (!PT) return;
  var h = PT.h;
  var clear = PT.clear;

  function $(id) { return document.getElementById(id); }

  var els = {
    heading: $("library-heading"),
    count: $("library-count"),
    loading: $("library-loading"),
    alert: $("library-alert"),
    content: $("lib-content"),
    filter: $("lib-filter"),
    clear: $("lib-clear"),
    tagbar: $("lib-tagbar"),
    tags: $("lib-tags"),
    tagsMore: $("lib-tags-more"),
    tagsNone: $("lib-tags-none"),
    tagsSummary: $("lib-tags-summary"),
    empty: $("library-empty"),
    emptyAll: $("library-empty-all"),
    list: $("library-list")
  };

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var POLL_MS = window.__PT_POLL_MS || 3000;
  var DEBOUNCE_MS = 150;
  var LOADING_DELAY_MS = 300;

  var ui = { tagsExpanded: false, tagsOverflow: false, loadingT: null, pollT: null, filterT: null };

  // ---- helpers ----

  function lib() { return PT.lib(); }

  function params() {
    var r = PT.route();
    return r.view === "library" && r.params ? r.params : { dir: "", tags: [], q: "" };
  }

  function setParams(p) { PT.setLibraryParams(p); }

  function fold(s) { return String(s || "").toLowerCase(); }

  function savedLabel(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    return "Saved " + d.getDate() + " " + MONTHS[d.getMonth()];
  }

  // ---- scope and filtering (brief L10a) ----

  // The current directory from the hash: all, unsorted or a user directory (by name).
  function scopeOf(p) {
    var name = p.dir || "";
    if (!name) return { kind: "all", name: "" };
    if (fold(name) === "unsorted") return { kind: "unsorted", name: "Unsorted" };
    var dirs = lib().directories;
    for (var i = 0; i < dirs.length; i++) {
      if (fold(dirs[i].name) === fold(name)) return { kind: "dir", id: dirs[i].id, name: dirs[i].name };
    }
    return { kind: "all", name: "" };
  }

  function inScope(it, scope) {
    if (scope.kind === "all") return true;
    if (scope.kind === "unsorted") return it.directory_id === null || it.directory_id === undefined;
    return it.directory_id === scope.id;
  }

  function hasAllTags(it, tags) {
    var own = it.tags || [];
    return tags.every(function (t) { return own.indexOf(t) !== -1; });
  }

  function titleMatches(it, q) {
    return !q || fold(it.title).indexOf(fold(q)) !== -1;
  }

  function filterActive(p) { return !!(p.q || p.tags.length); }

  function countTags(papers) {
    var counts = {};
    papers.forEach(function (it) {
      (it.tags || []).forEach(function (t) { counts[t] = (counts[t] || 0) + 1; });
    });
    return counts;
  }

  function sortedTags(counts, p) {
    var names = Object.keys(counts);
    p.tags.forEach(function (t) { if (names.indexOf(t) === -1) names.push(t); });
    var q = fold(p.q);
    names = names.filter(function (n) { return p.tags.indexOf(n) !== -1 || !q || fold(n).indexOf(q) !== -1; });
    names.sort(function (a, b) {
      var pa = p.tags.indexOf(a) !== -1 ? 0 : 1;
      var pb = p.tags.indexOf(b) !== -1 ? 0 : 1;
      if (pa !== pb) return pa - pb;
      var ca = counts[a] || 0;
      var cb = counts[b] || 0;
      if (ca !== cb) return cb - ca;
      return fold(a) < fold(b) ? -1 : fold(a) > fold(b) ? 1 : 0;
    });
    return names;
  }

  function joinNames(list) {
    if (list.length <= 1) return list.join("");
    return list.slice(0, -1).join(", ") + " and " + list[list.length - 1];
  }

  // ---- derived view state ----

  function model() {
    var p = params();
    var L = lib();
    var scope = scopeOf(p);
    var scoped = L.papers.filter(function (it) { return inScope(it, scope); });
    var shown = scoped.filter(function (it) { return hasAllTags(it, p.tags) && titleMatches(it, p.q); });
    return { p: p, scope: scope, scoped: scoped, shown: shown, total: L.total };
  }

  function countLine(m) {
    return m.shown.length + " of " + m.total + " saved paper" + (m.total === 1 ? "" : "s");
  }

  // ---- rendering ----

  function stopLoading() {
    window.clearTimeout(ui.loadingT);
    els.loading.hidden = true;
  }

  function render() {
    var L = lib();
    stopLoading();
    clear(els.alert);
    els.alert.hidden = true;
    els.content.hidden = true;
    els.emptyAll.hidden = true;
    els.count.hidden = true;
    els.heading.textContent = "Library";
    window.clearInterval(ui.pollT);
    ui.pollT = null;

    if (L.error && !L.loaded) return renderError(L.error);
    if (!L.loaded) {
      ui.loadingT = window.setTimeout(function () {
        if (!lib().loaded && !lib().error && PT.route().view === "library") els.loading.hidden = false;
      }, LOADING_DELAY_MS);
      return;
    }
    if (!L.papers.length) return renderEmptyLibrary();

    var m = model();
    els.heading.textContent = m.scope.kind === "dir" ? m.scope.name : "Library";
    els.count.textContent = countLine(m) + (m.scope.kind !== "all" ? " · " + m.scope.name : "");
    els.count.hidden = false;
    els.content.hidden = false;
    if (els.filter.value !== m.p.q) els.filter.value = m.p.q;
    els.clear.hidden = !filterActive(m.p);
    renderTags(m);
    renderList(m);
    schedulePoll();
  }

  function renderError(detail) {
    var retry = h("button", { type: "button", class: "btn btn--on-dark" }, "Try again");
    retry.addEventListener("click", function () { PT.enterLibrary(true); });
    els.alert.appendChild(h("p", { class: "alert__title" }, "Could not load your library."));
    els.alert.appendChild(h("p", { class: "alert__detail" }, detail));
    els.alert.appendChild(retry);
    els.alert.hidden = false;
  }

  function renderEmptyLibrary() {
    clear(els.emptyAll);
    els.emptyAll.appendChild(h("p", { class: "empty__title" }, "Nothing saved yet."));
    els.emptyAll.appendChild(h("p", { class: "empty__body" },
      "Save papers from your ranked results. Each saved paper keeps its rank, critique, tags and a local PDF."));
    els.emptyAll.appendChild(h("p", { class: "empty__actions" },
      h("a", { class: "btn btn--secondary", href: "#/" }, "Go to Triage")));
    els.emptyAll.hidden = false;
  }

  // ---- tag bar (L10b) ----

  function chip(name, count, pressed) {
    var b = h("button", { type: "button", class: "tag", "aria-pressed": pressed ? "true" : "false",
      "data-tag": name });
    if (pressed) {
      b.appendChild(PT.svg("svg", { class: "tag__check", width: "12", height: "12", viewBox: "0 0 12 12",
        "aria-hidden": "true", focusable: "false" },
        PT.svg("path", { d: "M2.5 6.5 5 9l4.5-5.5", fill: "none", stroke: "currentColor",
          "stroke-width": "1.7", "stroke-linecap": "round", "stroke-linejoin": "round" })));
    }
    b.appendChild(document.createTextNode(name));
    b.appendChild(h("span", { class: "tag__count" }, String(count)));
    b.addEventListener("click", function () { toggleTag(name); });
    return b;
  }

  function renderTags(m) {
    var counts = countTags(m.scoped);
    var names = sortedTags(counts, m.p);
    var none = !Object.keys(counts).length && !m.p.tags.length;
    els.tagsNone.hidden = !none;
    els.tags.hidden = none;
    els.tagsMore.hidden = true;
    clear(els.tags);
    document.getElementById("lib-tags-label").hidden = none;
    if (none) {
      els.tagsSummary.hidden = true;
      return;
    }
    names.forEach(function (n) { els.tags.appendChild(chip(n, counts[n] || 0, m.p.tags.indexOf(n) !== -1)); });
    // Two rows at most; the rest sits behind "Show all <n> tags".
    els.tags.classList.add("is-clamped");
    ui.tagsOverflow = els.tags.scrollHeight > els.tags.clientHeight + 1;
    if (ui.tagsExpanded && ui.tagsOverflow) els.tags.classList.remove("is-clamped");
    els.tagsMore.hidden = !ui.tagsOverflow;
    els.tagsMore.setAttribute("aria-expanded", ui.tagsExpanded ? "true" : "false");
    els.tagsMore.textContent = ui.tagsExpanded ? "Show fewer tags" : "Show all " + names.length + " tags";
    els.tagsSummary.hidden = !m.p.tags.length;
    els.tagsSummary.textContent = m.p.tags.length ? "Showing papers tagged " + joinNames(m.p.tags) + "." : "";
  }

  function toggleTag(name) {
    var p = params();
    var tags = p.tags.slice();
    var at = tags.indexOf(name);
    var q = p.q;
    if (at === -1) {
      tags.push(name);
      q = ""; // the text was used to find this tag
    } else {
      tags.splice(at, 1);
    }
    setParams({ dir: p.dir, tags: tags, q: q });
    els.filter.value = q;
    render();
    var btn = els.tags.querySelector('[data-tag="' + cssEscape(name) + '"]');
    if (btn) btn.focus();
    PT.announce(countLine(model()) + ".");
  }

  function cssEscape(s) {
    return window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&");
  }

  els.tagsMore.addEventListener("click", function () {
    ui.tagsExpanded = !ui.tagsExpanded;
    renderTags(model());
  });

  // ---- filter input and Clear filters (L10a, L10c) ----

  els.filter.addEventListener("input", function () {
    window.clearTimeout(ui.filterT);
    ui.filterT = window.setTimeout(function () {
      var p = params();
      setParams({ dir: p.dir, tags: p.tags, q: els.filter.value.trim() });
      render();
      PT.announce(countLine(model()) + ".");
    }, DEBOUNCE_MS);
  });

  els.filter.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape" || !els.filter.value) return;
    ev.preventDefault();
    els.filter.value = "";
    window.clearTimeout(ui.filterT);
    var p = params();
    setParams({ dir: p.dir, tags: p.tags, q: "" });
    render();
  });

  els.clear.addEventListener("click", function () {
    var p = params();
    setParams({ dir: p.dir, tags: [], q: "" });
    els.filter.value = "";
    render();
    els.filter.focus();
    var m = model();
    PT.announce("Filters cleared. " + m.shown.length + " saved paper" + (m.shown.length === 1 ? "" : "s") + ".");
  });

  // ---- list and states (L11, L14) ----

  function renderList(m) {
    clear(els.list);
    clear(els.empty);
    els.empty.hidden = true;
    els.list.hidden = false;
    if (m.shown.length) {
      m.shown.forEach(function (it) { els.list.appendChild(row(it)); });
      return;
    }
    els.list.hidden = true;
    if (!m.scoped.length) {
      els.empty.appendChild(h("p", { class: "empty__title" }, "No papers in " + m.scope.name + "."));
      els.empty.appendChild(h("p", { class: "empty__body" }, "Move a saved paper here with its Directory menu."));
    } else {
      var clearBtn = h("button", { type: "button", class: "btn btn--secondary" }, "Clear filters");
      clearBtn.addEventListener("click", function () { els.clear.click(); });
      els.empty.appendChild(h("p", { class: "empty__title" }, "No saved papers match."));
      els.empty.appendChild(h("p", { class: "empty__body" }, "Try fewer tags or a shorter filter."));
      els.empty.appendChild(h("p", { class: "empty__actions" }, clearBtn));
    }
    els.empty.hidden = false;
  }

  function statusText(it) {
    var s = it.pdf && it.pdf.status;
    return s === "pending" ? "Downloading PDF…" : s === "ready" ? "PDF ready"
      : s === "failed" ? "PDF unavailable" : "No PDF";
  }

  function statusEl(it) {
    var s = (it.pdf && it.pdf.status) || "none";
    var wrap = h("span", { class: "lib-pdf" + (s === "failed" ? " lib-pdf--failed" : ""),
      "data-pdf-status": s }, h("span", { class: "lib-pdf__text" }, statusText(it)));
    if (s === "failed") {
      var again = h("button", { type: "button", class: "text-btn text-btn--underlined lib-retry" }, "Try again");
      again.addEventListener("click", function () { retry(it, again); });
      wrap.appendChild(again);
    }
    return wrap;
  }

  function rowOf(id) {
    var rows = els.list.querySelectorAll(".lib-row");
    for (var i = 0; i < rows.length; i++) if (rows[i].getAttribute("data-paper-id") === id) return rows[i];
    return null;
  }

  function row(it) {
    var titleId = "lib-title-" + it.paper_id;
    var open = h("button", { type: "button", class: "btn btn--secondary btn--small open-preview",
      "data-open-preview": it.paper_id, "aria-describedby": titleId }, "Open preview");
    open.addEventListener("click", function () { location.hash = PT.previewHash(it.paper_id); });
    var hl = it.highlight_count || 0;
    var meta = h("div", { class: "paper__meta" },
      h("span", { class: "paper__id" }, it.paper_id),
      h("span", { class: "lib-saved" }, savedLabel(it.saved_at)),
      statusEl(it),
      hl ? h("span", { class: "lib-hl" }, hl + (hl === 1 ? " highlight" : " highlights")) : null,
      PT.paperLinks(it));
    var tags = (it.tags || []).length ? h("p", { class: "paper__authors lib-tagline" }, "Tags: " + it.tags.join(", ")) : null;
    return h("li", { class: "paper lib-row", "data-paper-id": it.paper_id },
      PT.rankBlock(it, false, it.topic),
      h("div", { class: "paper__body" },
        h("div", { class: "paper__head" },
          h("h3", { class: "paper__title", id: titleId }, it.title), open),
        PT.authorsLine(it.authors) ? h("p", { class: "paper__authors" }, PT.authorsLine(it.authors)) : null,
        it.topic ? h("p", { class: "paper__authors lib-for" }, "Ranked for \"" + it.topic + "\"") : null,
        tags,
        it.rank_reason ? h("p", { class: "paper__reason" }, it.rank_reason) : null,
        meta,
        h("div", { class: "lib-actions", "data-actions": "" }),
        PT.details(it)));
  }

  // ---- PDF status: retry and polling (L12, B3) ----

  function retry(it, btn) {
    var li = rowOf(it.paper_id);
    var old = li && li.querySelector(".row-error");
    if (old) old.parentNode.removeChild(old);
    btn.setAttribute("aria-disabled", "true");
    PT.postJSON("/api/library/retry", { paper_id: it.paper_id })
      .then(function (data) {
        var cur = PT.libItem(it.paper_id) || it;
        cur.pdf = (data && data.pdf) || { status: "pending", error: null, pages: null };
        paintStatus(cur);
        schedulePoll();
      })
      .catch(function (err) {
        btn.removeAttribute("aria-disabled");
        var meta = li && li.querySelector(".paper__meta");
        if (meta) {
          meta.parentNode.insertBefore(h("p", { class: "row-error", role: "alert" },
            "Could not retry. " + PT.failMessage(err)), meta.nextSibling);
        }
      });
  }

  // Replace only the status node of a row, so focus and scroll stay put.
  function paintStatus(it) {
    var li = rowOf(it.paper_id);
    var old = li && li.querySelector(".lib-pdf");
    if (!old) return;
    var hadFocus = li.contains(document.activeElement);
    var was = old.getAttribute("data-pdf-status");
    var fresh = statusEl(it);
    old.parentNode.replaceChild(fresh, old);
    if (hadFocus && was !== fresh.getAttribute("data-pdf-status")) PT.announce(statusText(it) + ".");
  }

  function pendingShown() {
    return model().shown.filter(function (it) { return it.pdf && it.pdf.status === "pending"; });
  }

  function schedulePoll() {
    window.clearInterval(ui.pollT);
    ui.pollT = null;
    if (PT.route().view !== "library" || !pendingShown().length) return;
    ui.pollT = window.setInterval(poll, POLL_MS);
  }

  function poll() {
    if (PT.route().view !== "library") {
      window.clearInterval(ui.pollT);
      ui.pollT = null;
      return;
    }
    PT.loadLibrary().then(function () {
      if (PT.route().view !== "library") return;
      pendingShown(); // keep the shown set in sync with the refreshed data
      model().shown.forEach(function (it) {
        var li = rowOf(it.paper_id);
        var cur = li && li.querySelector(".lib-pdf");
        var now = (it.pdf && it.pdf.status) || "none";
        if (cur && cur.getAttribute("data-pdf-status") !== now) paintStatus(it);
      });
      if (!pendingShown().length) {
        window.clearInterval(ui.pollT);
        ui.pollT = null;
      }
    });
  }

  window.addEventListener("resize", function () {
    if (PT.route().view === "library" && lib().loaded && lib().papers.length) renderTags(model());
  });

  PT.registerLibrary({ render: render, rowOf: rowOf, model: model });
})();
