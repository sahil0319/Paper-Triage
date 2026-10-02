/* "Ask this paper" panel (v3 T063, brief L20 Rev 2). Imported by viewer.js (static import).
   Lazy: nothing is requested until the first question. The transcript lives in memory only and is
   cleared when the preview closes or the page reloads. */

const HISTORY_TURNS = 6;
const SLOW_MS = window.__PT_CHAT_SLOW_MS || 20000; // test hook: shorten the "still reading" wait
const STARTERS = ["What is the main claim?", "What baselines are compared?", "What are the stated limitations?"];

export function initPaperChat(V) {
  const PT = window.PT;
  const h = PT.h;
  const $ = (id) => document.getElementById(id);
  const ui = {
    idle: $("pv-chat-idle"),
    starters: $("pv-chat-starters"),
    log: $("pv-chat-log"),
    reset: $("pv-chat-reset"),
    error: $("pv-chat-error"),
    form: $("pv-chat-form"),
    input: $("pv-chat-question"),
    ask: $("pv-chat-ask"),
    nopdf: $("pv-chat-nopdf"),
  };

  let st = null; // { id, token, turns: [{q, a}], busy, started, status }

  // ---- idle starters ----

  STARTERS.forEach((q) => {
    const b = h("button", { type: "button", class: "btn btn--secondary btn--small btn--suggest" }, q);
    b.addEventListener("click", () => submit(q));
    ui.starters.appendChild(h("li", {}, b));
  });

  // ---- lifecycle ----

  function reset(cur) {
    st = cur ? { id: cur.id, token: cur.token, turns: [], busy: false, started: false, status: cur.status } : null;
    PT.clear(ui.log);
    ui.reset.hidden = true;
    ui.error.hidden = true;
    ui.input.value = "";
    paint();
  }

  V.on("open", (cur) => reset(cur));
  V.on("close", () => reset(null));

  function ready() {
    return !!st && st.status === "ready";
  }

  function paint() {
    const ok = ready();
    ui.nopdf.hidden = ok || !st;
    if (st && !ok) {
      ui.nopdf.textContent =
        st.status === "pending"
          ? "Chat needs the PDF text. It is not ready yet."
          : "Chat needs the PDF text, and this PDF is unavailable.";
    }
    ui.input.disabled = !ok;
    ui.ask.disabled = !ok || (st && st.busy);
    ui.idle.hidden = !ok || !!(st && (st.turns.length || st.busy));
    ui.log.hidden = !(st && ok && (st.turns.length || st.busy));
    ui.reset.hidden = !(st && st.turns.length);
  }

  // ---- answer text ----

  function citeButton(n) {
    const b = h("button", { type: "button", class: "cite", "data-page": String(n), "aria-label": `Go to page ${n}` }, `p. ${n}`);
    b.addEventListener("click", () => {
      if (V.closeSheet) V.closeSheet();
      V.goToPage(n, { flash: true });
      V.el.well.focus({ preventScroll: true });
    });
    return b;
  }

  // [p.N] becomes a jump button only for pages the server validated; markers it dropped vanish.
  function answerNodes(text, pages, dropped) {
    const ok = pages || [];
    const bad = dropped || [];
    return String(text)
      .split(/(\[p\.\s*\d+\]|\[arXiv:[^\]\s]+\])/)
      .map((part, i) => {
        if (i % 2 === 0) return part;
        const pm = /^\[p\.\s*(\d+)\]$/.exec(part);
        if (pm) {
          const n = Number(pm[1]);
          if (ok.includes(n)) return citeButton(n);
          if (bad.includes(n)) return "";
          return part;
        }
        return h("span", { class: "cite" }, part.slice(1, -1));
      });
  }

  function answerEl(data) {
    if (data.refused) {
      return h(
        "div",
        { class: "turn__a turn__a--refused" },
        h("p", { class: "turn__refused-title" }, "Not in this paper"),
        h("p", { class: "turn__refused-body" }, data.answer),
        h("p", { class: "turn__refused-hint" }, "Ask about something this paper covers."),
      );
    }
    const box = h("div", { class: "turn__a" }, h("span", { class: "sr-only" }, "Answer: "), answerNodes(data.answer, data.pages, data.dropped_pages));
    const pages = [...new Set(data.pages || [])];
    if (pages.length) {
      const line = h("p", { class: "sources__h pv-chat__pages" }, "Pages: ");
      pages.forEach((n, i) => {
        if (i) line.appendChild(document.createTextNode(", "));
        line.appendChild(citeButton(n));
      });
      box.appendChild(h("div", { class: "sources" }, line));
    }
    return box;
  }

  // ---- asking ----

  function history() {
    return st.turns.slice(-HISTORY_TURNS).map((t) => ({ question: t.q, answer: t.a }));
  }

  function pendingEl(first) {
    const text = first ? "Reading this paper. The first answer takes longer." : "Reading this paper…";
    return h("p", { class: "turn__pending" }, PT.rayGlyph(16), h("span", { class: "turn__pending-text" }, text));
  }

  function submit(q) {
    if (!ready() || st.busy) return;
    q = q.trim();
    if (!q) {
      ui.input.focus();
      return;
    }
    ui.error.hidden = true;
    const my = st;
    const first = !st.started;
    const body = { paper_id: st.id, question: q, history: history() };
    const turn = h("li", { class: "turn" }, h("p", { class: "turn__q" }, h("span", { class: "sr-only" }, "You asked: "), q));
    ui.input.value = "";
    ui.log.appendChild(turn);
    const pending = pendingEl(first);
    turn.appendChild(pending);
    let slowT = 0;
    if (first) {
      slowT = window.setTimeout(() => {
        const t = pending.querySelector(".turn__pending-text");
        if (t) t.textContent = "Still reading. Long papers take up to a minute.";
      }, SLOW_MS);
    }
    st.busy = true;
    paint();
    turn.scrollIntoView({ block: "nearest" });
    PT.postJSON("/api/paper-chat", body)
      .then(
        (data) => {
          window.clearTimeout(slowT);
          if (st !== my) return;
          pending.remove();
          turn.appendChild(answerEl(data));
          my.turns.push({ q, a: String(data.answer || "") });
          my.started = true;
        },
        (err) => {
          window.clearTimeout(slowT);
          if (st !== my) return;
          pending.remove();
          if (first) {
            // The first question failed while starting: back to idle with the error above the input.
            turn.remove();
            ui.error.textContent = `Could not answer. ${PT.failMessage(err)}`;
            ui.error.hidden = false;
            ui.input.value = q;
            return;
          }
          const again = h("button", { type: "button", class: "btn btn--secondary btn--small" }, "Ask again");
          const box = h("div", { class: "turn__err", role: "alert" }, h("p", {}, `Could not answer. ${PT.failMessage(err)}`), again);
          again.addEventListener("click", () => {
            if (my.busy) return;
            turn.remove();
            submit(q);
          });
          turn.appendChild(box);
        },
      )
      .then(() => {
        if (st !== my) return;
        my.busy = false;
        paint();
        turn.scrollIntoView({ block: "nearest" });
        ui.input.focus();
      });
  }

  ui.form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    if (ui.ask.disabled) return;
    submit(ui.input.value);
  });

  V.chat = { submit };
}
