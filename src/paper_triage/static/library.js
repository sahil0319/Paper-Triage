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
    filters: document.querySelector(".lib-filters"),
    tagbar: $("lib-tagbar"),
    tags: $("lib-tags"),
    tagsMore: $("lib-tags-more"),
    tagsNone: $("lib-tags-none"),
    tagsSummary: $("lib-tags-summary"),
    empty: $("library-empty"),
    emptyAll: $("library-empty-all"),
    list: $("library-list"),
    rail: $("dir-rail"),
    dirList: $("dir-list"),
    newSlot: $("dir-new-slot"),
    newSlotM: $("dir-new-slot-m"),
    renameSlot: $("dir-rename-slot"),
    actions: $("dir-actions"),
    confirm: $("dir-confirm"),
    select: $("dir-select"),
    manage: $("dir-manage"),
    managePanel: $("dir-manage-panel"),
    manageList: $("dir-manage-list")
  };

  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var POLL_MS = window.__PT_POLL_MS || 3000;
  var DEBOUNCE_MS = 150;
  var LOADING_DELAY_MS = 300;

  var ui = { forced: {}, tagsExpanded: false, tagsOverflow: false, loadingT: null, pollT: null, filterT: null };

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

    resetHead();
    if (L.error && !L.loaded) return renderError(L.error);
    if (!L.loaded) {
      ui.loadingT = window.setTimeout(function () {
        if (!lib().loaded && !lib().error && PT.route().view === "library") els.loading.hidden = false;
      }, LOADING_DELAY_MS);
      return;
    }
    if (!L.papers.length) {
      renderDirs(model());
      return renderEmptyLibrary();
    }

    var m = model();
    renderDirs(m);
    renderCount(m);
    els.content.hidden = false;
    if (els.filter.value !== m.p.q) els.filter.value = m.p.q;
    // An empty directory has nothing to filter: only the empty-directory message shows.
    els.filters.hidden = !m.scoped.length;
    els.clear.hidden = !filterActive(m.p);
    renderTags(m);
    renderList(m);
    schedulePoll();
  }

  function renderCount(m) {
    els.count.textContent = countLine(m) + (m.scope.kind !== "all" ? " · " + m.scope.name : "");
    els.count.hidden = false;
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
    var libraryHasTags = lib().papers.some(function (it) { return (it.tags || []).length; });
    els.tagsNone.hidden = !(none && !libraryHasTags);
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
        rowActions(it),
        PT.details(it)));
  }


  // ---- API helper (status and detail are needed for validation copy) ----

  function api(method, url, body) {
    return fetch(url, {
      method: method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined
    }).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function detailOf(r) {
    return r.data && typeof r.data.detail === "string" ? r.data.detail
      : "The server returned an error (" + r.status + "). Try again.";
  }

  // ---- directory data (counts are derived from the papers, so moves update them at once) ----

  function dirCounts() {
    var L = lib();
    var byDir = {};
    var unsorted = 0;
    L.papers.forEach(function (it) {
      if (it.directory_id === null || it.directory_id === undefined) unsorted++;
      else byDir[it.directory_id] = (byDir[it.directory_id] || 0) + 1;
    });
    return { byDir: byDir, unsorted: unsorted, all: L.papers.length };
  }

  function dirByName(name) {
    var dirs = lib().directories;
    for (var i = 0; i < dirs.length; i++) if (fold(dirs[i].name) === fold(name)) return dirs[i];
    return null;
  }

  function selectDir(name, announceText) {
    var p = params();
    setParams({ dir: name, tags: p.tags, q: p.q });
    render();
    if (announceText) PT.announce(announceText);
  }

  function validateName(raw, exceptId) {
    var name = raw.trim();
    if (!name) return "Enter a name.";
    if (name.length > 40) return "Names can be up to 40 characters.";
    var key = fold(name);
    var clash = key === "unsorted" || key === "all saved" || lib().directories.some(function (d) {
      return d.id !== exceptId && fold(d.name) === key;
    });
    return clash ? "\"" + name + "\" already exists." : "";
  }

  var uid = 0;

  // Inline name form (create and rename). `submit(name)` resolves "" on success or an error text.
  function nameForm(o) {
    var n = ++uid;
    var input = h("input", { type: "text", id: "dir-name-" + n, maxlength: "40", autocomplete: "off",
      spellcheck: "false", placeholder: "e.g. final year thesis", value: o.value || "" });
    var err = h("p", { class: "field-error", id: "dir-err-" + n, hidden: "" });
    var go = h("button", { type: "submit", class: "btn btn--secondary btn--small" }, o.submitText);
    var cancel = h("button", { type: "button", class: "text-btn" }, "Cancel");
    var form = h("form", { class: "dir-form", novalidate: "" },
      h("label", { class: "sr-only", for: "dir-name-" + n }, "Directory name"),
      h("div", { class: "dir-form__row" }, input, go, cancel), err);
    function show(msg) {
      err.textContent = msg;
      err.hidden = !msg;
      if (msg) {
        input.setAttribute("aria-invalid", "true");
        input.setAttribute("aria-describedby", err.id);
      } else {
        input.removeAttribute("aria-invalid");
        input.removeAttribute("aria-describedby");
      }
    }
    var busy = false;
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (busy) return;
      var msg = validateName(input.value, o.exceptId);
      if (msg) { show(msg); input.focus(); return; }
      busy = true;
      go.setAttribute("aria-disabled", "true");
      o.submit(input.value.trim()).then(function (failure) {
        busy = false;
        go.removeAttribute("aria-disabled");
        if (failure) { show(failure); input.focus(); }
      });
    });
    input.addEventListener("input", function () { if (err.hidden === false) show(""); });
    cancel.addEventListener("click", function () { o.cancel(); });
    form.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.stopPropagation(); o.cancel(); }
    });
    form.focusInput = function () { input.focus(); input.select(); };
    return form;
  }

  function saveError(r) {
    return r.status === 422 || r.status === 409 ? detailOf(r)
      : "Could not save the directory. " + detailOf(r);
  }

  // ---- create (L9) ----

  function newControl(slot) {
    clear(slot);
    var btn = h("button", { type: "button", class: "btn btn--secondary btn--small dir-new" }, "New directory");
    if (slot === els.newSlot) btn.id = "dir-new";
    btn.addEventListener("click", function () {
      clear(slot);
      var form = nameForm({
        submitText: "Create",
        submit: function (name) {
          return api("POST", "/api/directories", { name: name }).then(function (r) {
            if (!r.ok) return saveError(r);
            newControl(slot);
            return PT.reloadLibrary().then(function () {
              var made = r.data && r.data.name ? r.data.name : name;
              selectDir(made, "Directory \"" + made + "\" created.");
              var again = slot.querySelector(".dir-new");
              if (again) again.focus();
              return "";
            });
          }, function (e) { return "Could not save the directory. " + PT.failMessage(e); });
        },
        cancel: function () { newControl(slot); slot.querySelector(".dir-new").focus(); }
      });
      slot.appendChild(form);
      form.focusInput();
    });
    slot.appendChild(btn);
  }

  // ---- rename and delete (L9) ----

  function resetHead() {
    els.renameSlot.hidden = true;
    clear(els.renameSlot);
    els.heading.hidden = false;
    els.confirm.hidden = true;
    clear(els.confirm);
  }

  function headActions(m) {
    clear(els.actions);
    var user = m.scope.kind === "dir";
    els.actions.hidden = !user;
    if (!user) return;
    var dir = dirByName(m.scope.name);
    var rename = h("button", { type: "button", class: "btn btn--secondary btn--small", "data-act": "rename" }, "Rename");
    var del = h("button", { type: "button", class: "btn btn--secondary btn--small", "data-act": "delete" }, "Delete directory");
    rename.addEventListener("click", function () { startRename(dir, rename); });
    del.addEventListener("click", function () { startDelete(dir, del, els.confirm); });
    els.actions.appendChild(rename);
    els.actions.appendChild(del);
  }

  function startRename(dir, trigger) {
    resetHead();
    els.heading.hidden = true;
    els.renameSlot.hidden = false;
    var form = nameForm({
      submitText: "Save", value: dir.name, exceptId: dir.id,
      submit: function (name) {
        if (fold(name) === fold(dir.name) && name === dir.name) { cancel(); return Promise.resolve(""); }
        return api("PATCH", "/api/directories/" + dir.id, { name: name }).then(function (r) {
          if (!r.ok) return saveError(r);
          return PT.reloadLibrary().then(function () {
            var now = r.data && r.data.name ? r.data.name : name;
            selectDir(now, "Directory renamed to \"" + now + "\".");
            var b = els.actions.querySelector('[data-act="rename"]');
            if (b) b.focus();
            return "";
          });
        }, function (e) { return "Could not save the directory. " + PT.failMessage(e); });
      },
      cancel: cancel
    });
    function cancel() {
      resetHead();
      if (trigger && trigger.isConnected) trigger.focus();
    }
    els.renameSlot.appendChild(form);
    form.focusInput();
  }

  function startDelete(dir, trigger, host) {
    host.hidden = false;
    clear(host);
    var n = dirCounts().byDir[dir.id] || 0;
    var text = n
      ? "Delete \"" + dir.name + "\"? Its " + n + (n === 1 ? " paper moves" : " papers move") + " to Unsorted."
      : "Delete \"" + dir.name + "\"?";
    var keep = h("button", { type: "button", class: "btn btn--secondary btn--small" }, "Keep");
    var del = h("button", { type: "button", class: "btn btn--secondary btn--small btn--remove",
      "data-confirm-delete": "" }, "Delete");
    var group = h("div", { class: "confirm", role: "group", "aria-label": "Confirm directory deletion" },
      h("p", { class: "confirm__text" }, text), del, keep);
    function close(refocus) {
      clear(host);
      host.hidden = true;
      if (refocus && trigger.isConnected) trigger.focus();
    }
    keep.addEventListener("click", function () { close(true); });
    group.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.stopPropagation(); close(true); }
    });
    del.addEventListener("click", function () {
      del.setAttribute("aria-disabled", "true");
      api("DELETE", "/api/directories/" + dir.id).then(function (r) {
        if (!r.ok) {
          del.removeAttribute("aria-disabled");
          host.insertBefore(h("p", { class: "row-error", role: "alert" },
            "Could not delete the directory. " + detailOf(r)), group);
          return;
        }
        var moved = r.data && typeof r.data.moved === "number" ? r.data.moved : n;
        PT.reloadLibrary().then(function () {
          var p = params();
          var was = fold(p.dir) === fold(dir.name);
          setParams({ dir: was ? "Unsorted" : p.dir, tags: p.tags, q: p.q });
          render();
          PT.announce("Directory deleted. " + moved + " paper" + (moved === 1 ? "" : "s") + " moved to Unsorted.");
          (was ? els.heading : document.getElementById("dir-new") || els.heading).focus();
        });
      }, function (e) {
        del.removeAttribute("aria-disabled");
        host.insertBefore(h("p", { class: "row-error", role: "alert" },
          "Could not delete the directory. " + PT.failMessage(e)), group);
      });
    });
    host.appendChild(group);
    keep.focus();
  }

  // ---- rail, mobile select and manage panel (L8, L10b) ----

  function dirItemButton(label, count, dirName, current, full) {
    var b = h("button", { type: "button", class: "rail__item", "data-dir": dirName, title: full || label },
      h("span", { class: "rail__name" }, label), h("span", { class: "rail__count" }, String(count)));
    if (current) {
      b.setAttribute("aria-current", "true");
    }
    b.addEventListener("click", function () {
      selectDir(dirName, countLine(modelFor(dirName)) + ".");
      var again = els.dirList.querySelector('[data-dir="' + cssEscape(dirName) + '"]');
      if (again) again.focus();
    });
    return b;
  }

  function modelFor(dirName) {
    var p = params();
    var saved = PT.route().params;
    PT.route().params = { dir: dirName, tags: p.tags, q: p.q };
    var m = model();
    PT.route().params = saved;
    return m;
  }

  function currentDirKey(m) {
    return m.scope.kind === "all" ? "" : m.scope.kind === "unsorted" ? "Unsorted" : m.scope.name;
  }

  function renderDirs(m) {
    var L = lib();
    var counts = dirCounts();
    var cur = currentDirKey(m);
    var items = [
      { label: "All saved", name: "", count: counts.all },
      { label: "Unsorted", name: "Unsorted", count: counts.unsorted }
    ].concat(L.directories.map(function (d) {
      return { label: d.name, name: d.name, count: counts.byDir[d.id] || 0 };
    }));

    clear(els.dirList);
    items.forEach(function (it) {
      els.dirList.appendChild(h("li", {}, dirItemButton(it.label, it.count, it.name, it.name === cur)));
    });
    newControlOnce(els.newSlot);

    // < 1024px: native select plus a manage panel.
    clear(els.select);
    items.forEach(function (it) {
      var o = h("option", { value: it.name }, it.label + " (" + it.count + ")");
      if (it.name === cur) o.selected = true;
      els.select.appendChild(o);
    });
    renderManage(L.directories, counts);
    newControlOnce(els.newSlotM);

    headActions(m);
    els.heading.textContent = m.scope.kind === "dir" ? m.scope.name : "Library";
  }

  // Keep an open create form alive across re-renders; only (re)build the button when idle.
  function newControlOnce(slot) {
    if (slot.firstChild) return;
    newControl(slot);
  }

  function renderManage(dirs, counts) {
    clear(els.manageList);
    if (!dirs.length) {
      els.manageList.appendChild(h("li", { class: "lib-note" }, "No directories yet."));
      return;
    }
    dirs.forEach(function (d) {
      var li = h("li", { class: "dir-manage__item" });
      paintManageItem(li, d, counts.byDir[d.id] || 0);
      els.manageList.appendChild(li);
    });
  }

  function paintManageItem(li, d, count) {
    clear(li);
    var rename = h("button", { type: "button", class: "text-btn" }, "Rename");
    var del = h("button", { type: "button", class: "text-btn" }, "Delete");
    var confirmHost = h("div", { class: "dir-manage__confirm", hidden: "" });
    rename.setAttribute("aria-label", "Rename " + d.name);
    del.setAttribute("aria-label", "Delete directory " + d.name);
    rename.addEventListener("click", function () {
      clear(li);
      var form = nameForm({
        submitText: "Save", value: d.name, exceptId: d.id,
        submit: function (name) {
          if (name === d.name) { paintManageItem(li, d, count); return Promise.resolve(""); }
          return api("PATCH", "/api/directories/" + d.id, { name: name }).then(function (r) {
            if (!r.ok) return saveError(r);
            var wasCurrent = fold(params().dir) === fold(d.name);
            return PT.reloadLibrary().then(function () {
              var now = r.data && r.data.name ? r.data.name : name;
              var p = params();
              setParams({ dir: wasCurrent ? now : p.dir, tags: p.tags, q: p.q });
              render();
              els.managePanel.hidden = false;
              PT.announce("Directory renamed to \"" + now + "\".");
              return "";
            });
          }, function (e) { return "Could not save the directory. " + PT.failMessage(e); });
        },
        cancel: function () { paintManageItem(li, d, count); li.querySelector(".text-btn").focus(); }
      });
      li.appendChild(form);
      form.focusInput();
    });
    del.addEventListener("click", function () { startDelete(d, del, confirmHost); });
    li.appendChild(h("div", { class: "dir-manage__line" },
      h("span", { class: "dir-manage__name", title: d.name }, d.name),
      h("span", { class: "rail__count" }, String(count)), rename, del));
    li.appendChild(confirmHost);
  }

  els.select.addEventListener("change", function () {
    var name = els.select.value;
    selectDir(name, countLine(modelFor(name)) + ".");
    els.select.focus();
  });

  els.manage.addEventListener("click", function () {
    var open = els.managePanel.hidden;
    els.managePanel.hidden = !open;
    els.manage.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // ---- row actions: move and remove (L13) ----

  function rowActions(it) {
    var counts = lib().directories;
    var sel = h("select", { class: "select lib-dir__select", "data-act": "move",
      "aria-label": "Directory for " + it.title });
    sel.appendChild(h("option", { value: "" }, "Unsorted"));
    counts.forEach(function (d) { sel.appendChild(h("option", { value: String(d.id) }, d.name)); });
    sel.value = it.directory_id === null || it.directory_id === undefined ? "" : String(it.directory_id);
    var label = h("label", { class: "lib-dir" },
      h("span", { class: "lib-dir__label" }, "Directory"), sel);
    sel.addEventListener("change", function () { move(it, sel); });
    var rm = h("button", { type: "button", class: "text-btn", "data-act": "remove" }, "Remove from Library");
    rm.addEventListener("click", function () { confirmRemove(it, rm); });
    return h("div", { class: "lib-actions", "data-actions": "" }, label, rm);
  }

  function rowError(li, text) {
    var old = li.querySelector(".row-error");
    if (old) old.parentNode.removeChild(old);
    if (!text) return;
    var actions = li.querySelector(".lib-actions");
    actions.parentNode.insertBefore(h("p", { class: "row-error", role: "alert" }, text), actions.nextSibling);
  }

  function nextOpenButton(li) {
    var n = li.nextElementSibling;
    return n ? n.querySelector(".open-preview") : null;
  }

  function move(it, sel) {
    var li = rowOf(it.paper_id);
    var target = sel.value === "" ? null : Number(sel.value);
    var before = it.directory_id === undefined ? null : it.directory_id;
    rowError(li, "");
    sel.disabled = true;
    api("POST", "/api/library/move", { paper_id: it.paper_id, directory_id: target }).then(function (r) {
      sel.disabled = false;
      if (!r.ok) {
        sel.value = before === null ? "" : String(before);
        rowError(li, "Could not move. " + detailOf(r));
        return;
      }
      var cur = PT.libItem(it.paper_id) || it;
      cur.directory_id = target;
      lib().sig = "";
      var name = target === null ? "Unsorted" : (lib().directories.filter(function (d) { return d.id === target; })[0] || {}).name;
      PT.announce("Moved to " + name + ".");
      var m = model();
      renderDirs(m);
      if (inScope(cur, m.scope)) {
        renderCount(m);
        renderTags(m);
        return;
      }
      // Filtered out of this directory: collapse the row, then move focus on.
      var nextBtn = nextOpenButton(li);
      collapse(li, function () {
        render();
        var again = nextBtn && nextBtn.isConnected ? nextBtn : null;
        if (!again && nextBtn) {
          var nid = nextBtn.getAttribute("data-open-preview");
          var row = rowOf(nid);
          again = row && row.querySelector(".open-preview");
        }
        (again || els.heading).focus();
      });
    }, function (e) {
      sel.disabled = false;
      sel.value = before === null ? "" : String(before);
      rowError(li, "Could not move. " + PT.failMessage(e));
    });
  }

  function collapse(li, done) {
    if (PT.reducedMotion()) { done(); return; }
    li.classList.add("is-collapsing");
    window.setTimeout(done, 250);
  }

  function confirmRemove(it, trigger) {
    var li = rowOf(it.paper_id);
    var host = li.querySelector(".lib-confirm");
    if (host) return;
    var n = it.highlight_count || 0;
    var text = n > 0
      ? "Remove from Library? This deletes the saved PDF and " + n + (n === 1 ? " highlight" : " highlights") +
        " with " + (n === 1 ? "its note" : "their notes") + "."
      : "Remove from Library? This deletes the saved PDF.";
    var keep = h("button", { type: "button", class: "btn btn--secondary btn--small" }, "Keep");
    var remove = h("button", { type: "button", class: "btn btn--secondary btn--small btn--remove",
      "data-confirm-remove": "" }, "Remove");
    host = h("div", { class: "confirm lib-confirm", role: "group", "aria-label": "Confirm removal",
      "data-confirm": "unsave" }, h("p", { class: "confirm__text" }, text), remove, keep);
    function close(refocus) {
      if (host.parentNode) host.parentNode.removeChild(host);
      trigger.hidden = false;
      if (refocus) trigger.focus();
    }
    keep.addEventListener("click", function () { close(true); });
    host.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.stopPropagation(); close(true); }
    });
    remove.addEventListener("click", function () {
      remove.setAttribute("aria-disabled", "true");
      rowError(li, "");
      api("DELETE", "/api/library?paper_id=" + encodeURIComponent(it.paper_id)).then(function (r) {
        if (!r.ok) {
          remove.removeAttribute("aria-disabled");
          rowError(li, "Could not remove from Library. " + detailOf(r));
          return;
        }
        var nextBtn = nextOpenButton(li);
        var nextId = nextBtn ? nextBtn.getAttribute("data-open-preview") : null;
        PT.libraryRemove(it.paper_id);
        render();
        PT.announce("Removed from Library.");
        var row = nextId ? rowOf(nextId) : null;
        (row ? row.querySelector(".open-preview") : els.heading).focus();
      }, function (e) {
        remove.removeAttribute("aria-disabled");
        rowError(li, "Could not remove from Library. " + PT.failMessage(e));
      });
    });
    trigger.hidden = true;
    li.querySelector(".lib-actions").appendChild(host);
    keep.focus();
  }

  // ---- PDF status: retry and polling (L12, B3) ----

  function retry(it, btn) {
    var li = rowOf(it.paper_id);
    var old = li && li.querySelector(".row-error");
    if (old) old.parentNode.removeChild(old);
    btn.setAttribute("aria-disabled", "true");
    PT.postJSON("/api/library/retry", { paper_id: it.paper_id })
      .then(function (data) {
        // Pending is shown from a copy; the cached item keeps the server's last answer, and the
        // next poll replaces it even when the download ends where it started.
        var cur = PT.libItem(it.paper_id) || it;
        var shown = Object.assign({}, cur, { pdf: (data && data.pdf) || { status: "pending", error: null, pages: null } });
        ui.forced[it.paper_id] = true;
        paintStatus(shown);
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
    return model().shown.filter(function (it) {
      return (it.pdf && it.pdf.status === "pending") || ui.forced[it.paper_id];
    });
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
    PT.reloadLibrary().then(function () {
      if (PT.route().view !== "library") return;
      var forced = ui.forced;
      ui.forced = {};
      model().shown.forEach(function (it) {
        var li = rowOf(it.paper_id);
        var cur = li && li.querySelector(".lib-pdf");
        var now = (it.pdf && it.pdf.status) || "none";
        if (cur && (cur.getAttribute("data-pdf-status") !== now || forced[it.paper_id])) paintStatus(it);
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
