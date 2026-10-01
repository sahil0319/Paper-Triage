/* Paper Triage UI: triage flow. Vanilla JS; all text is set with textContent (paper titles and
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
  var mockEl = document.getElementById("mock-label");
  var modelEl = document.getElementById("model");

  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (attrs[k] !== null && attrs[k] !== undefined) el.setAttribute(k, attrs[k]);
    });
    append(el, Array.prototype.slice.call(arguments, 2));
    return el;
  }

  function append(el, children) {
    children.forEach(function (c) {
      if (c === null || c === undefined || c === false) return;
      if (Array.isArray(c)) return append(el, c);
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
  }

  function authorsLine(list) {
    if (!list || !list.length) return null;
    return list.length > 3 ? list.slice(0, 3).join(", ") + " et al." : list.join(", ");
  }

  function plural(n, word) {
    return n + " " + word + (n === 1 ? "" : "s");
  }

  // ---- critique ----

  function section(title, body) {
    return [h("h3", {}, title), body];
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
    return h("details", {}, h("summary", {}, r.critique ? "Summary and critique" : "Summary"), box);
  }

  // ---- list ----

  function row(r) {
    var failed = r.status === "failed";
    var rank = h("div", { class: "rank" },
      h("span", { class: "rank__n", "aria-label": failed ? "No rank" : "Rank " + r.rank + " of 10" },
        failed ? "–" : String(r.rank)),
      failed ? null : h("span", { class: "rank__of", "aria-hidden": "true" }, "of 10"));
    var meta = h("p", { class: "paper__meta" },
      h("span", { class: "paper__id" }, r.paper_id),
      r.basis === "abstract" ? h("span", { class: "flag" }, "Abstract only") : null,
      failed ? h("span", { class: "flag flag--failed" }, "Failed") : null);
    var reason = failed
      ? h("p", { class: "paper__reason paper__reason--failed" }, r.error || "This paper could not be processed.")
      : h("p", { class: "paper__reason" }, r.rank_reason || "");
    return h("li", { class: "paper", id: "paper-" + r.paper_id, tabindex: "-1" },
      rank,
      h("div", { class: "paper__body" },
        h("h3", { class: "paper__title" }, r.title),
        authorsLine(r.authors) ? h("p", { class: "paper__authors" }, authorsLine(r.authors)) : null,
        meta, reason, details(r)));
  }

  function clear(el) {
    while (el.firstChild) el.removeChild(el.firstChild);
  }

  function showAlert(text) {
    clear(alertEl);
    if (text) {
      alertEl.appendChild(h("strong", {}, "Triage failed. "));
      alertEl.appendChild(document.createTextNode(text));
    }
    alertEl.hidden = !text;
  }

  function showNotes(errors) {
    clear(notesEl);
    (errors || []).forEach(function (e) {
      notesEl.appendChild(h("li", {}, "Could not fetch " + e.input + ": " + e.reason));
    });
    notesEl.hidden = !notesEl.firstChild;
  }

  function render(data, stored) {
    var rs = data.results || [];
    clear(listEl);
    rs.forEach(function (r) { listEl.appendChild(row(r)); });
    showNotes(data.errors);
    heading.textContent = data.topic ? "Ranked papers for “" + data.topic + "”" : "Ranked papers";
    if (rs.length) {
      emptyEl.hidden = true;
      var failed = rs.filter(function (r) { return r.status === "failed"; }).length;
      statusEl.textContent = (stored ? "Showing " + plural(rs.length, "stored paper") + " from your last run, "
        : plural(rs.length, "paper") + ", ") + "ranked by relevance." +
        (failed ? " " + failed + " could not be processed." : "");
    } else {
      emptyEl.hidden = false;
      emptyEl.textContent = "No papers found. Try broader keywords, or paste arXiv IDs or PDF links.";
      statusEl.textContent = "No papers found.";
    }
  }

  // ---- submit ----

  function setBusy(busy) {
    button.disabled = busy;
    button.textContent = busy ? "Triaging…" : "Triage papers";
    results.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function errorText(res, body) {
    if (body && typeof body.detail === "string") return body.detail;
    return "The server returned an error (" + res.status + "). Try again.";
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
    if (button.disabled) return;
    setBusy(true);
    showAlert("");
    statusEl.textContent = "Fetching and reading papers. This can take a minute.";
    fetch("/api/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    })
      .then(function (res) {
        return res.json().catch(function () { return null; }).then(function (body) {
          if (!res.ok) throw new Error(errorText(res, body));
          return body;
        });
      })
      .then(function (data) { render(data, false); })
      .catch(function (err) {
        var offline = err instanceof TypeError;
        showAlert(offline ? "Could not reach the server. Check that the app is running." : err.message);
        statusEl.textContent = "";
      })
      .then(function () { setBusy(false); });
  });

  // ---- on load: backend status and stored results (no refetching from arXiv) ----

  function getJSON(url) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error(String(res.status));
      return res.json();
    });
  }

  function loadStatus() {
    return getJSON("/api/status").then(function (s) {
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
      if (button.disabled) return; // a triage run started meanwhile; its result wins
      if (data && data.results && data.results.length) render(data, true);
    }).catch(function () {
      // Nothing stored or server unreachable: keep the empty state.
    });
  }

  loadStatus();
  loadStored();
})();
