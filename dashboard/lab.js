// lexflow process lab: start a case from a model, record what happened, and see each deadline counted from the
// quoted law.  Cases are kept in this browser's localStorage (every access is wrapped in try/catch, so a private
// window still works for the session).  What the page sends to this lexflow, and nothing else:
//   1. the state and process chosen (to list processes and load a model's steps);
//   2. the state, when one is chosen or any case of that state is opened (whether or not the case has a place, so
//      the request does not tell this lexflow that either): GET /api/lab/states/{state}/places loads every
//      government of the state with the office channels that pass lexflow's office-only checks, once per state per
//      page load.  The place search and the "where to send" lookup run here, on that list: neither the place nor a
//      keystroke is sent;
//   3. the case's event types, dates, step ids and calendar choices (never notes, the label or the place), posted
//      to /api/lab/timeline, which counts and keeps nothing;
//   4. one anonymised outcome (state, place only if ticked, question, step, days taken, outcome), only after the
//      user clicks "Share anonymised outcome" and then "Send these six fields" under the exact preview.
// As in app.js, every value from the API or the user is inserted with textContent (h() below).

const API = "/api/lab";
const KEY = "lexflow-lab-cases";
const SCHEMA = "lexflow-lab/1";
const $ = (sel, el = document) => el.querySelector(sel);
const work = $("#work");
const caseList = $("#case-list");
const apiNote = $("#api-note");

// ------------------------------------------------------------------ helpers
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
function rc(el, ...kids) { el.replaceChildren(...kids.flat().filter((k) => k != null && k !== false)); }
const ICON = {
  done: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="var(--good)"/><path d="M4.5 8.2l2.3 2.3 4.7-4.8" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  partial: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--accent)" stroke-width="1.6"/><path d="M8 1.8a6.2 6.2 0 0 1 0 12.4z" fill="var(--accent)"/></svg>',
  todo: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--baseline)" stroke-width="1.6"/></svg>',
  optional: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--baseline)" stroke-width="1.6" stroke-dasharray="2.4 2.2"/></svg>',
  blocked: '<svg viewBox="0 0 16 16"><path d="M8 1.5l7 12.5H1z" fill="var(--warning)"/><path d="M8 6v3.6M8 11.6v.4" stroke="#0b0b0b" stroke-width="1.6" stroke-linecap="round"/></svg>',
  failed: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="var(--critical)"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>',
  info: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10" cy="10" r="8"/><path d="M10 9v5M10 6.2v.3" stroke-linecap="round"/></svg>',
};
function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = ICON[name] || "";        // static strings only
  return t.content.cloneNode(true);
}
// deadline status -> icon and word (always both: colour is never the only signal)
const STATUS = { "on time": ["partial", "On time"], open: ["partial", "Open (your step)"], overdue: ["failed", "Overdue"],
  lapsed: ["failed", "Your time ended"], met: ["done", "Met"], late: ["blocked", "Answered late"],
  "may apply": ["optional", "May apply"], waiting: ["todo", "Not started"], closed: ["done", "Closed"] };
function statusEl(s) {
  const [ic, word] = STATUS[s] || ["todo", s || "–"];
  return h("span", { class: "status" }, icon(ic), word);
}
const today = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };
const fmt = (iso) => { if (!iso) return "–"; const d = new Date(`${iso}T12:00:00`); return d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" }); };
const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`);

async function api(path, opts = {}) {
  const r = await fetch(API + path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    let msg = `${r.status}`;
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch (e) { /* not json */ }
    const err = new Error(msg);
    err.status = r.status;
    throw err;
  }
  return r.json();
}
function apiDown(e) {
  if (e && e.status && e.status !== 404) return false;
  rc(apiNote, h("div", { class: "notice" }, icon("info"), h("div", {},
    h("strong", {}, "The lab's API is not reachable here. "),
    "This lexflow does not serve /api/lab yet (the router is not mounted; see docs/design/lab-plan.md). Until it does, a new case cannot be started, because the processes come from the API. Your cases are still kept in this browser, and you can export and import them.")));
  return true;
}

// ------------------------------------------------------------------ per-case values, cleaned before use
const KEY_RE = /^[a-z0-9_]{1,40}$/;
const validDay = (x) => /^\d{4}-\d{2}-\d{2}$/.test(x || "") && !Number.isNaN(Date.parse(`${x}T12:00:00Z`)) &&
  new Date(`${x}T12:00:00Z`).toISOString().slice(0, 10) === x;
// the calendar choices a case keeps (and sends to /timeline): closures, observed optional holidays, holidays the
// office was open (by holiday key), and a variant reading
function cleanOptions(o) {
  const src = o && typeof o === "object" ? o : {};
  const list = (xs, ok, max) => [...new Set((Array.isArray(xs) ? xs : []).map(String).filter(ok))].sort().slice(0, max);
  return { closures: list(src.closures, validDay, 200), observes: list(src.observes, (x) => KEY_RE.test(x), 20),
    opens: list(src.opens, (x) => KEY_RE.test(x), 60),
    variant: typeof src.variant === "string" && KEY_RE.test(src.variant) ? src.variant : null };
}
function cleanPlace(p) {
  if (!p || typeof p !== "object" || typeof p.gov_id !== "string" || !/^[0-9A-Za-z:._-]{1,64}$/.test(p.gov_id)) return null;
  return { gov_id: p.gov_id, name: String(p.name || p.gov_id).slice(0, 200) };
}

// ------------------------------------------------------------------ one state's places, fetched once per state
// The response lists every government of the state and its office channels; searching it and finding a case's
// place in it happen here, so the place never leaves the browser.  Only the state is in the request.
const placeCache = new Map();
function placesFor(st) {
  if (!placeCache.has(st)) {
    placeCache.set(st, api(`/states/${encodeURIComponent(st)}/places`).then((b) => ({ ...b,
      governments: b.governments.map((row) => Object.fromEntries(b.columns.map((k, i) => [k, row[i]]))) })));
  }
  return placeCache.get(st).catch((e) => { placeCache.delete(st); throw e; });
}
function searchPlaces(bundle, q) {
  const needle = q.trim().toLowerCase();
  if (needle.length < 2) return [];
  return bundle.governments.filter((g) => String(g.name || "").toLowerCase().includes(needle)).slice(0, 15);
}

// ------------------------------------------------------------------ local storage (this browser only)
let saveWarned = false;
function loadAll() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "{}");
    return { cases: v.cases && typeof v.cases === "object" ? v.cases : {}, current: v.current || null };
  } catch (e) {
    return { cases: {}, current: null };
  }
}
const db = loadAll();
function saveAll() {
  try {
    localStorage.setItem(KEY, JSON.stringify(db));
    if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  } catch (e) {
    if (!saveWarned) {
      saveWarned = true;
      apiNote.prepend(h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "This browser is not saving cases. "),
        "Storage is blocked or full (a private window, for example). Export the case to keep it.")));
    }
  }
}

// ------------------------------------------------------------------ model cache
const modelCache = new Map();
async function steps(modelId) {
  if (!modelCache.has(modelId)) modelCache.set(modelId, api(`/models/${encodeURIComponent(modelId)}/steps`));
  try { return await modelCache.get(modelId); } catch (e) { modelCache.delete(modelId); throw e; }
}

// what the timeline endpoint needs, and nothing else: no notes, no label, no place
function forServer(c) {
  return { lab: SCHEMA, state: c.state, question: c.question, model_id: c.model_id, started: c.started || null,
    events: (c.events || []).map((e) => { const o = { type: e.type, date: e.date }; if (e.step) o.step = e.step; if (e.until) o.until = e.until; return o; }),
    options: cleanOptions(c.options) };
}

// ------------------------------------------------------------------ case list
function renderList() {
  const ids = Object.keys(db.cases).sort((a, b) => (db.cases[b].created || "").localeCompare(db.cases[a].created || ""));
  rc(caseList, ids.length ? ids.map((id) => {
    const c = db.cases[id];
    return h("li", {}, h("button", { type: "button", "aria-current": id === db.current ? "true" : "false",
      onclick: () => { db.current = id; saveAll(); renderList(); showCase(id); } },
      h("div", { class: "t" }, c.label || c.model_id),
      h("div", { class: "s" }, [c.place && c.place.name, c.title || c.model_id].filter(Boolean).join(" · ")),
      h("div", { class: "s" }, c.last_status ? statusEl(c.last_status) : null, c.started ? ` · started ${fmt(c.started)}` : "")));
  }) : h("li", { class: "muted", style: "padding:10px 18px" }, "No cases yet."));
}

// ------------------------------------------------------------------ start a case
async function showStart(prefill = {}) {
  db.current = null; saveAll(); renderList();
  const placeInput = h("input", { id: "lab-place", type: "search", placeholder: "Choose a state first", autocomplete: "off", disabled: true });
  const results = h("ul", { class: "results", role: "listbox" });
  const NO_PLACE = "No place chosen: the state's own law applies.";
  const chosen = h("div", { class: "muted", style: "font-size:12.5px" }, NO_PLACE);
  const placeNote = h("p", { class: "muted fetch-note" }, "Choosing a state loads, once, the list of its governments and their published office channels from this lexflow (only the state is sent). The place search then runs in this browser: what you type is not sent.");
  const stateSel = h("select", { "aria-label": "State" }, h("option", { value: "" }, "Choose a state"));
  const modelSel = h("select", { "aria-label": "Process", disabled: true }, h("option", { value: "" }, "Choose a state first"));
  const label = h("input", { type: "text", placeholder: "e.g. Police budget request", "aria-label": "Label (kept here only)" });
  const started = h("input", { type: "date", value: today(), "aria-label": "Started" });
  const sentBox = h("input", { type: "checkbox", checked: true });
  const sentDate = h("input", { type: "date", value: today(), "aria-label": "Date the request was sent" });
  const preview = h("div");
  const startBtn = h("button", { class: "btn primary", type: "button", disabled: true }, "Start case");
  let place = null;
  let allModels = [];

  try {
    allModels = await api("/models");
  } catch (e) {
    apiDown(e);
  }
  const states = [...new Set(allModels.map((m) => m.state))].sort();
  for (const s of states) stateSel.append(h("option", { value: s }, s.toUpperCase()));

  function fillModels() {
    const st = stateSel.value;
    rc(modelSel, h("option", { value: "" }, st ? "Choose a process" : "Choose a state first"),
      allModels.filter((m) => m.state === st).map((m) => h("option", { value: m.model_id }, `${m.title}${m.tier === "curated" ? " (curated file)" : ""}`)));
    modelSel.disabled = !st;
    if (prefill.model && allModels.some((m) => m.model_id === prefill.model)) { modelSel.value = prefill.model; prefill.model = null; }
    showPreview();
  }
  async function showPreview() {
    startBtn.disabled = !modelSel.value;
    if (!modelSel.value) { rc(preview); return; }
    try {
      const m = await steps(modelSel.value);
      rc(preview, h("h3", { style: "margin:16px 0 6px" }, "What this process involves"),
        h("p", { class: "ink-2", style: "margin:0 0 6px;font-size:13px" }, m.model.title, m.model.citation ? ` · ${m.model.citation}` : ""),
        h("ol", { class: "steps-list" }, m.steps.map((s) => h("li", {},
          h("strong", {}, s.name), h("span", { class: "muted" }, ` · ${s.you ? "you" : s.actor_name}`),
          s.deadline ? h("div", { class: "how" }, `${s.deadline.rule}, starting when ${s.deadline.starts_when}`, s.deadline.citation ? ` (${s.deadline.citation})` : "") : null,
          s.deadline && s.deadline.quote ? h("p", { class: "quote" }, `“${s.deadline.quote}”`) : null))),
        h("p", { class: "muted", style: "font-size:12px" }, `Holidays: ${m.calendar.name} table. ${m.calendar.business_day}`));
    } catch (e) {
      apiDown(e) || rc(preview, h("p", { class: "muted" }, `Could not load the steps: ${e.message}`));
    }
  }
  let bundle = null;
  async function loadPlaces() {
    const st = stateSel.value;
    bundle = null; place = null; placeInput.value = ""; placeInput.disabled = true; rc(results); rc(chosen, NO_PLACE);
    if (!st) { placeInput.placeholder = "Choose a state first"; return; }
    placeInput.placeholder = "Loading the state's places…";
    try {
      const b = await placesFor(st);
      if (stateSel.value !== st) return;                 // the user picked another state meanwhile
      bundle = b; placeInput.disabled = false; placeInput.placeholder = `City, county or town in ${st.toUpperCase()}`;
      rc(placeNote, `Loaded ${b.governments.length} governments in ${st.toUpperCase()} and their office channels from this lexflow, once (only the state was sent). The search runs in this browser: what you type is not sent.`);
    } catch (e) {
      placeInput.placeholder = "Places could not be loaded";
      apiDown(e) || rc(placeNote, `Could not load the state's places: ${e.message}. You can start a case without a place.`);
    }
  }
  // searched here, in the state's list: nothing is sent while typing
  placeInput.addEventListener("input", () => {
    if (!bundle) return;
    rc(results, searchPlaces(bundle, placeInput.value).map((g) => h("li", {}, h("button", { type: "button", onclick: () => {
      place = { gov_id: g.gov_id, name: g.name };
      rc(chosen, `${g.name} (${g.kind}${g.county_name ? `, ${g.county_name}` : ""})`);
      placeInput.value = g.name; rc(results);
    } }, g.name, g.county_name ? h("span", { class: "muted" }, ` · ${g.county_name}`) : null))));
  });
  stateSel.addEventListener("change", () => { fillModels(); loadPlaces(); });
  modelSel.addEventListener("change", showPreview);
  sentBox.addEventListener("change", () => { sentDate.disabled = !sentBox.checked; });
  startBtn.addEventListener("click", async () => {
    const id = uid();
    const m = allModels.find((x) => x.model_id === modelSel.value);
    let start = started.value || today();
    if (sentBox.checked && sentDate.value && sentDate.value < start) start = sentDate.value;   // a case starts no later than its request
    const c = { lab: SCHEMA, id, created: new Date().toISOString(), label: label.value.trim() || null,
      state: m.state, question: m.question, model_id: m.model_id, title: m.title,
      place: place && place.gov_id && place.name && stateSel.value === m.state ? cleanPlace(place) : null,
      started: start, events: [], options: cleanOptions({}) };
    if (sentBox.checked && sentDate.value) c.events.push({ type: "request_sent", date: sentDate.value, step: null, note: "" });
    db.cases[id] = c; db.current = id; saveAll(); renderList(); showCase(id);
  });

  rc(work, h("section", { class: "card card-pad" },
    h("h2", {}, "Start a case"),
    h("p", { class: "ink-2", style: "margin:4px 0 12px;font-size:13px" }, "Choose the state and the process, then a place if you like. Starting saves the case in this browser; counting its deadlines then sends its events (never the place, the label or your notes) to this lexflow."),
    h("div", { class: "form-grid" },
      h("label", {}, "State", stateSel),
      h("label", {}, "Process", modelSel),
      h("div", { class: "col" }, h("label", { for: "lab-place" }, "Place (optional)"), placeInput, results, chosen),
      h("label", {}, "Label (kept here only)", label),
      h("label", {}, "Started", started),
      h("div", { class: "col" }, h("label", { class: "check" }, sentBox, "I have sent the request"), sentDate)),
    placeNote,
    preview,
    h("div", { class: "row-flex", style: "margin-top:12px" }, startBtn)));
  if (prefill.state || prefill.model) {
    stateSel.value = prefill.state || (prefill.model || "").split(".")[0];
    fillModels();
    if (stateSel.value) loadPlaces();
  }
}

// ------------------------------------------------------------------ a case
async function showCase(id) {
  const c = db.cases[id];
  if (!c) return showStart();
  rc(work, h("section", { class: "card card-pad" }, h("p", { class: "muted" }, "Counting…")));
  // the state's list is loaded for every case opened, with or without a place: the request does not say which
  const bundleP = placesFor(c.state).catch(() => null);
  let m = null, tl = null, err = null;
  try {
    m = await steps(c.model_id);
    tl = await api(`/timeline?today=${today()}`, { method: "POST", body: JSON.stringify(forServer(c)) });
    c.last_status = tl.status; saveAll(); renderList();
  } catch (e) {
    err = e; apiDown(e);
  }
  const header = h("section", { class: "card card-pad" },
    h("div", { class: "row-flex" },
      h("div", {}, h("h2", {}, c.label || (m && m.model.title) || c.model_id),
        h("p", { class: "ink-2", style: "margin:2px 0 0;font-size:13px" },
          [c.place && c.place.name, (m && m.model.title) || c.title, m && m.model.citation].filter(Boolean).join(" · "))),
      h("div", { class: "right row-flex" }, tl ? statusEl(tl.status) : null,
        h("button", { class: "btn small", type: "button", onclick: () => exportJson(c) }, "Export case (.json)"),
        h("button", { class: "btn small", type: "button", disabled: !tl, onclick: () => exportIcs(c, tl) }, "Export deadlines (.ics)"),
        h("button", { class: "btn small", type: "button", disabled: !tl, onclick: () => showShare(c, tl) }, "Share anonymised outcome"),
        h("button", { class: "btn small", type: "button", onclick: () => {
          if (!confirm("Delete this case from this browser? Export it first if you need it.")) return;
          delete db.cases[id]; db.current = null; saveAll(); renderList(); showStart();
        } }, "Delete"))));
  const parts = [header];
  if (err) parts.push(h("section", { class: "card card-pad" }, h("p", { class: "muted" }, `The timeline could not be counted: ${err.message}`)));
  if (tl) parts.push(hereCard(tl), deadlinesCard(tl), timelineCard(tl));
  const bundle = await bundleP;
  if (tl && bundle && c.place && c.place.gov_id) parts.push(channelsCard(c, bundle));
  parts.push(eventsCard(c, m, tl));
  if (m) parts.push(calendarCard(c, m));
  if (tl && tl.gaps && tl.gaps.length) parts.push(h("section", { class: "card card-pad" }, h("details", { class: "more" },
    h("summary", {}, `What the model leaves out (${tl.gaps.length} notes)`), h("ul", { class: "how" }, tl.gaps.map((g) => h("li", {}, g))))));
  if (tl && tl.warnings && tl.warnings.length) parts.push(h("section", { class: "card card-pad how" }, h("ul", {}, tl.warnings.map((w) => h("li", {}, w)))));
  parts.push(h("p", { class: "muted", style: "font-size:12px" }, (tl && tl.disclaimer) || (m && m.disclaimer) || "Information, not legal advice."));
  parts.push(h("div", { id: "share-slot" }));
  rc(work, h("div", { class: "grid" }, parts));
}

function hereCard(tl) {
  const cur = tl.current;
  return h("section", { class: "card card-pad here" },
    h("div", { class: "label" }, "You are here"),
    h("div", { class: "name" }, cur ? cur.name : "Closed"),
    cur ? h("div", { class: "ink-2", style: "font-size:13px" }, cur.kind === "outcome" ? "End of the modelled process" : cur.you ? "Your step" : `Who acts: ${cur.who}`) : null,
    h("p", { style: "margin:6px 0 0" }, tl.current_why),
    cur && cur.quote ? h("p", { class: "quote" }, `“${cur.quote}”`, cur.citation ? h("span", { class: "muted" }, ` ${cur.citation}`) : null) : null,
    cur && cur.next && cur.next.length ? h("p", { class: "how" }, `Next in the model: ${cur.next.join("; ")}`) : null,
    cur && cur.gaps && cur.gaps.length ? h("details", { class: "more" }, h("summary", {}, "What the model does not cover here"), h("ul", { class: "how" }, cur.gaps.map((g) => h("li", {}, g)))) : null,
    tl.attention.length ? h("ul", { class: "attention", style: "padding-left:18px;margin-top:10px" }, tl.attention.map((a) => h("li", {}, a))) : null);
}

// official office channels of the case's government (website, pages, offices, labelled office lines, and office
// mailboxes once a check found them on the office's own page), each with its source.  Found in the state's list
// loaded once (placesFor): the place is not sent.
const KIND_WORD = { website: "Website", page: "Page", office: "Office", email: "Office mailbox", phone: "Office line" };
function channelsCard(c, b) {
  const g = b.governments.find((x) => x.gov_id === c.place.gov_id);
  const head = (title) => h("div", { class: "card-head" }, h("h2", {}, title),
    h("p", {}, b.note, ` Loaded with the list of every government in ${c.state.toUpperCase()}; this place was found in that list in your browser and was not sent.`));
  if (!g) return h("section", { class: "card" }, head(`Where to send: ${c.place.name}`),
    h("p", { class: "muted", style: "padding:6px 18px 14px" }, "This place is not in this lexflow's list for the state; use the government's official website."));
  const link = (u, text) => (/^https?:\/\//.test(u || "") ? h("a", { href: u, target: "_blank", rel: "noopener" }, text) : text);
  const rows = (b.channels[g.gov_id] || []).filter((x) => x.question === c.question || x.question === "general")
    .sort((x, y) => (x.question === c.question ? 0 : 1) - (y.question === c.question ? 0 : 1));
  if (g.website) rows.unshift({ kind: "website", value: g.website, label: "Official website", source: null });
  return h("section", { class: "card" }, head(`Where to send: ${g.name}`),
    rows.length ? h("ul", { class: "how", style: "padding:6px 18px 14px 36px" }, rows.map((x) => h("li", {},
      h("strong", {}, x.label || KIND_WORD[x.kind] || x.kind), ": ", ["page", "website"].includes(x.kind) ? link(x.value, x.value) : h("span", { class: "pre" }, x.value),
      x.source && x.source !== x.value ? h("span", { class: "muted" }, " · ", link(x.source, /^https?:\/\//.test(x.source) ? "source" : `source: ${x.source}`)) : null)))
      : h("p", { class: "muted", style: "padding:6px 18px 14px" }, "No office channel is recorded for this place yet; use the government's official website."));
}

function deadlinesCard(tl) {
  const rows = tl.deadlines.map((d) => h("tr", {},
    h("td", {}, h("div", { style: "font-weight:500" }, d.name), h("div", { class: "muted", style: "font-size:12px" }, d.you ? "you" : d.who)),
    h("td", {}, d.rule, h("div", { class: "muted", style: "font-size:12px" }, `starts when ${d.starts_when || d.anchor || "–"}`)),
    h("td", { class: "num" }, fmt(d.due), d.days_left != null ? h("div", { class: "muted", style: "font-size:12px" }, `${d.days_left} day${d.days_left === 1 ? "" : "s"} left`) : null),
    h("td", {}, statusEl(d.status), d.applies === "if" && d.condition ? h("div", { class: "muted", style: "font-size:12px" }, `if ${d.condition.replace(/_/g, " ")}`) : null),
    h("td", {}, h("details", { class: "more" }, h("summary", {}, d.citation || "How it was counted"),
      h("div", { class: "how" },
        d.quote ? h("p", { class: "quote" }, `“${d.quote}”`) : null,
        d.url && /^https?:\/\//.test(d.url) ? h("p", {}, h("a", { href: d.url, target: "_blank", rel: "noopener" }, "Official text ↗")) : null,
        d.how ? h("p", {}, d.how) : null,
        d.skipped.length ? h("ul", {}, d.skipped.map((s) => h("li", {}, `${fmt(s.date)}: ${s.why}`))) : null,
        d.notes.length ? h("ul", {}, d.notes.map((n) => h("li", {}, n))) : null,
        d.alternatives.length ? h("ul", {}, d.alternatives.map((a) => h("li", {}, `Another reading: ${fmt(a.due)} (${a.reading})`))) : null,
        d.unit_note ? h("p", { class: "muted" }, d.unit_note) : null,
        d.on_miss_names.length ? h("p", {}, `If missed: ${d.on_miss_names.join("; ")} (${d.consequence.replace(/-/g, " ")})`) : null)))));
  return h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Deadlines"),
    h("p", {}, `Counted with the ${tl.calendar.name} calendar. ${tl.calendar.business_day}`)),
    h("div", { class: "table-wrap", style: "padding:6px 8px 12px" }, h("table", { class: "data" },
      h("thead", {}, h("tr", {}, ["Step", "Rule", "Due", "Status", "Law"].map((t) => h("th", {}, t)))), h("tbody", {}, rows))));
}

function timelineCard(tl) {
  return h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Timeline")),
    h("ol", { class: "tl" }, tl.timeline.map((x) => h("li", { class: x.kind },
      h("span", { class: "d" }, fmt(x.date)),
      h("span", { class: "l" }, x.label, x.kind === "implied" ? h("span", { class: "muted" }, ` (${x.why})`) : null,
        x.kind === "due" && x.status ? h("span", { class: "muted" }, ` · ${(STATUS[x.status] || [0, x.status])[1]}`) : null)))));
}

function eventsCard(c, m, tl) {
  const types = m ? m.events : [{ type: "request_sent", label: "Request sent" }, { type: "response_received", label: "Response received" }];
  const typeSel = h("select", { "aria-label": "What happened" }, types.map((t) => h("option", { value: t.type }, t.label)));
  const date = h("input", { type: "date", value: today(), "aria-label": "Date" });
  const stepSel = h("select", { "aria-label": "Step" }, h("option", { value: "" }, "(any step)"),
    (m ? m.steps : []).map((s) => h("option", { value: s.id }, s.name)));
  if (tl && tl.current && tl.current.kind === "step") stepSel.value = tl.current.id;
  const until = h("input", { type: "date", "aria-label": "Date the body states" });
  const untilWrap = h("label", { style: "display:none" }, "Date it states", until);
  const note = h("input", { type: "text", placeholder: "Only kept in this browser", "aria-label": "Note (never sent)" });
  typeSel.addEventListener("change", () => { untilWrap.style.display = typeSel.value === "acknowledged" ? "" : "none"; });
  const add = h("button", { class: "btn primary", type: "button", onclick: () => {
    if (!date.value) return;
    c.events.push({ type: typeSel.value, date: date.value, step: stepSel.value || null, until: until.value || null, note: note.value.trim() });
    c.events.sort((a, b) => a.date.localeCompare(b.date));
    saveAll(); showCase(c.id);
  } }, "Add");
  const rows = c.events.map((e, i) => h("tr", {},
    h("td", { class: "num" }, fmt(e.date)),
    h("td", {}, ((types.find((t) => t.type === e.type) || {}).label) || e.type, e.until ? ` (until ${fmt(e.until)})` : "",
      e.note ? h("div", { class: "note" }, e.note) : null),
    h("td", { class: "muted" }, e.step ? ((m && m.steps.find((s) => s.id === e.step)) || { name: e.step }).name : "–"),
    h("td", {}, h("button", { class: "btn small", type: "button", "aria-label": "Remove this event", onclick: () => { c.events.splice(i, 1); saveAll(); showCase(c.id); } }, "Remove"))));
  return h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "What happened"),
    h("p", {}, "Record each thing as it happens. Notes stay in this browser and are never sent.")),
    h("div", { class: "card-pad" }, h("div", { class: "form-grid" },
      h("label", {}, "What happened", typeSel), h("label", {}, "Date", date), h("label", {}, "Step it belongs to", stepSel),
      untilWrap, h("label", {}, "Note (never sent)", note)), h("div", { class: "row-flex", style: "margin-top:10px" }, add)),
    rows.length ? h("div", { class: "table-wrap", style: "padding:0 8px 12px" }, h("table", { class: "data events" },
      h("thead", {}, h("tr", {}, ["Date", "Event", "Step", ""].map((t) => h("th", {}, t)))), h("tbody", {}, rows))) : null);
}

// the calendar, and the case's own choices: a variant reading, holidays this office was open, optional holidays it
// observes, and days it was closed.  They are kept in the case (and its export) and sent with the timeline.
const openDetails = new Set();      // which of this page's details elements the user opened (kept across redraws)
function keepOpen(key, el) {
  if (openDetails.has(key)) el.open = true;
  el.addEventListener("toggle", () => { if (el.open) openDetails.add(key); else openDetails.delete(key); });
  return el;
}
function calendarCard(c, m) {
  const cal = m.calendar;
  const opts = cleanOptions(c.options);
  const save = (next) => { c.options = cleanOptions({ ...opts, ...next }); saveAll(); showCase(c.id); };
  const toggle = (xs, key, on) => (on ? [...xs, key] : xs.filter((x) => x !== key));
  const sel = h("select", { "aria-label": "Calendar reading" }, h("option", { value: "" }, `${cal.name}: default table`),
    cal.variants.map((v) => h("option", { value: v.key }, v.text)));
  sel.value = opts.variant || "";
  sel.addEventListener("change", () => save({ variant: sel.value || null }));
  const dayRow = (x, list, field, text) => h("li", {}, h("label", { class: "check" },
    h("input", { type: "checkbox", checked: list.includes(x.key), onchange: (ev) => save({ [field]: toggle(list, x.key, ev.target.checked) }) }),
    h("span", {}, x.name, h("span", { class: "muted" }, ` · ${x.rule}${x.part_day ? ` (${cal.part_day_rule || "part day off"})` : ""}`), text ? h("span", { class: "muted" }, ` · ${text}`) : null)));
  const fixedDays = cal.holidays.filter((x) => !x.optional);
  const optionalDays = cal.holidays.filter((x) => x.optional);
  const closeDate = h("input", { type: "date", "aria-label": "A day the office was closed" });
  const addClosure = h("button", { class: "btn small", type: "button", onclick: () => {
    if (validDay(closeDate.value)) save({ closures: [...opts.closures, closeDate.value] });
  } }, "Add closure");
  const set = [opts.opens.length && `${opts.opens.length} open`, opts.observes.length && `${opts.observes.length} observed`,
    opts.closures.length && `${opts.closures.length} closure${opts.closures.length === 1 ? "" : "s"}`, opts.variant && "another reading"].filter(Boolean);
  return h("section", { class: "card card-pad" }, keepOpen("calendar", h("details", { class: "more" },
    h("summary", {}, `Holiday calendar: ${cal.name}${set.length ? ` · this case: ${set.join(", ")}` : ""}`),
    h("div", { class: "how" },
      h("p", {}, cal.business_day), h("p", {}, `Last day on a weekend or holiday: ${cal.roll} (${cal.roll_source}).`),
      cal.closures ? h("p", {}, `Closures: ${cal.closures}.`) : null,
      cal.variants.length ? h("label", { class: "field" }, "Reading", sel) : null,
      h("h3", { class: "opt-h" }, "Days this office treats differently"),
      h("p", {}, "Kept in this case and in its export, and sent with the events to count the dates."),
      keepOpen("opens", h("details", { class: "more" }, h("summary", {}, `Holidays the office was open${opts.opens.length ? ` (${opts.opens.length})` : ""}`),
        h("p", {}, "Tick a holiday the office was open on; it is then counted as a working day in every year of this case."),
        h("ul", { class: "opts" }, fixedDays.map((x) => dayRow(x, opts.opens, "opens"))))),
      optionalDays.length ? keepOpen("observes", h("details", { class: "more" }, h("summary", {}, `Optional holidays the body observes${opts.observes.length ? ` (${opts.observes.length})` : ""}`),
        h("p", {}, "Tick an optional holiday the body observes; it is then not counted."),
        h("ul", { class: "opts" }, optionalDays.map((x) => dayRow(x, opts.observes, "observes", x.cite))))) : null,
      keepOpen("closures", h("details", { class: "more" }, h("summary", {}, `Days the office was closed${opts.closures.length ? ` (${opts.closures.length})` : ""}`),
        h("p", {}, "A whole day the office was closed is not counted. (“Office closed all day” under What happened does the same.)"),
        h("div", { class: "row-flex" }, closeDate, addClosure),
        opts.closures.length ? h("ul", { class: "opts" }, opts.closures.map((d) => h("li", {}, fmt(d), " ",
          h("button", { class: "btn small", type: "button", "aria-label": `Remove the closure on ${d}`, onclick: () => save({ closures: opts.closures.filter((x) => x !== d) }) }, "Remove")))) : null)),
      cal.notes.length ? h("ul", {}, cal.notes.map((n) => h("li", {}, n))) : null,
      h("ul", {}, cal.sources.map((s) => h("li", {}, /^https?:\/\//.test(s.url) ? h("a", { href: s.url, target: "_blank", rel: "noopener" }, `${s.cite} ↗`) : s.cite)))))));
}

// ------------------------------------------------------------------ share (opt-in, previewed, anonymised)
const OUTCOMES = [["answered_in_time", "Answered in time"], ["answered_late", "Answered late"], ["extension_notice", "Body claimed more time"],
  ["denied", "Denied"], ["no_answer", "No answer (deemed denial)"], ["estimate_tolled", "Clock paused for a cost estimate"],
  ["withdrawn", "Withdrawn"], ["still_open", "Still open"]];
function suggest(d) {
  const done = d.done && d.done.type;
  if (d.status === "met") return done === "extension_claimed" ? "extension_notice" : done === "denied" ? "denied" : "answered_in_time";
  return { late: "answered_late", overdue: "no_answer" }[d.status] || "still_open";
}
function showShare(c, tl) {
  const slot = $("#share-slot");
  const counted = tl.deadlines.filter((d) => d.elapsed != null);
  if (!counted.length) {
    rc(slot, h("section", { class: "card card-pad" }, h("p", {}, "Nothing to share yet: no deadline has started.")));
    slot.scrollIntoView({ behavior: "smooth" });
    return;
  }
  const stepSel = h("select", { "aria-label": "Step" }, counted.map((d) => h("option", { value: d.step }, d.name)));
  const outSel = h("select", { "aria-label": "Outcome" }, OUTCOMES.map(([k, t]) => h("option", { value: k }, t)));
  const days = h("input", { type: "number", min: "0", max: "3660", "aria-label": "Days taken" });
  const withPlace = h("input", { type: "checkbox", disabled: !(c.place && c.place.gov_id) });
  const pre = h("pre", { class: "preview" });
  const sendBtn = h("button", { class: "btn primary", type: "button" }, "Send these six fields");
  const result = h("p", { class: "how" });
  const unitLabel = h("span", {}, "Time taken");
  const pick = () => counted.find((d) => d.step === stepSel.value);
  const payload = () => ({ state: c.state, place: withPlace.checked && c.place ? c.place.gov_id : null, question: c.question,
    step: stepSel.value, days_taken: Math.max(0, Math.min(3660, parseInt(days.value, 10) || 0)), outcome: outSel.value });
  const refresh = () => { pre.textContent = JSON.stringify(payload(), null, 2); };
  const fill = () => {
    const d = pick();
    days.value = d.elapsed; outSel.value = suggest(d);
    unitLabel.textContent = `Time taken (${d.elapsed_unit || "days"})`;
    refresh();
  };
  stepSel.addEventListener("change", fill);
  for (const el of [outSel, days, withPlace]) el.addEventListener("input", refresh);
  withPlace.addEventListener("change", refresh);
  sendBtn.addEventListener("click", async () => {
    sendBtn.disabled = true;
    try {
      await api("/outcomes", { method: "POST", body: JSON.stringify(payload()) });
      rc(result, "Shared with this lexflow. Only the fields above were sent; no date, note, label or name.");
    } catch (e) {
      sendBtn.disabled = false;
      apiDown(e) || rc(result, `Not shared: ${e.message}`);
    }
  });
  rc(slot, h("section", { class: "card card-pad", "aria-labelledby": "share-h" },
    h("h2", { id: "share-h" }, "Share anonymised outcome"),
    h("p", { class: "ink-2", style: "font-size:13px" }, "This sends exactly what is shown below to this lexflow's own database (table lab_outcomes), and nothing else: no dates, notes, label, request text or name. The row is kept under a random key, with no date or time, and is only ever counted inside a summary of at least 10 reports, where no group of fewer than 10 is shown. The web server's access log still records that a report arrived, when, and from which network address (the client IP). The time it took is in the model's own units. Leave the place out unless you are comfortable with it: a body that received few requests may recognise yours."),
    h("div", { class: "form-grid" }, h("label", {}, "Step", stepSel), h("label", {}, "Outcome", outSel),
      h("label", {}, unitLabel, days),
      h("div", { class: "col" }, h("label", { class: "check" }, withPlace, "Include the place"), c.place ? c.place.name : "No place in this case")),
    pre,
    h("div", { class: "row-flex" }, sendBtn,
      h("button", { class: "btn", type: "button", onclick: () => download(`lexflow-outcome-${c.state}-${stepSel.value}.json`, JSON.stringify(payload(), null, 2), "application/json") }, "Save as a file instead"),
      h("button", { class: "btn", type: "button", onclick: () => rc(slot) }, "Cancel")),
    result));
  fill();
  slot.scrollIntoView({ behavior: "smooth" });
}

// ------------------------------------------------------------------ export / import
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = h("a", { href: url, download: name });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const slug = (s) => String(s || "case").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 40) || "case";
function exportJson(c) {
  const { last_status, ...keep } = c;     // a cached display value, not part of the case
  download(`lexflow-case-${slug(c.label || c.model_id)}.json`, JSON.stringify(keep, null, 2), "application/json");
}
function icsText(s) { return String(s).replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n"); }
function fold(line) {           // RFC 5545 §3.1: lines longer than 75 octets are folded (approximated in characters)
  const out = [];
  while (line.length > 74) { out.push(line.slice(0, 74)); line = ` ${line.slice(74)}`; }
  out.push(line);
  return out.join("\r\n");
}
function exportIcs(c, tl) {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//lexflow//process lab//EN", "CALSCALE:GREGORIAN"];
  for (const d of tl.deadlines.filter((x) => x.due && ["on time", "open", "may apply"].includes(x.status))) {
    const day = d.due.replace(/-/g, "");
    const next = new Date(`${d.due}T12:00:00Z`); next.setUTCDate(next.getUTCDate() + 1);
    lines.push("BEGIN:VEVENT", `UID:${c.id}-${d.step}@lexflow-lab`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${day}`,
      `DTEND;VALUE=DATE:${next.toISOString().slice(0, 10).replace(/-/g, "")}`,
      fold(`SUMMARY:${icsText(`Due: ${d.name}${d.citation ? ` (${d.citation})` : ""}`)}`),
      fold(`DESCRIPTION:${icsText([d.rule, d.how, d.quote ? `“${d.quote}”` : "", ...d.notes].filter(Boolean).join("\n"))}`),
      "BEGIN:VALARM", "ACTION:DISPLAY", fold(`DESCRIPTION:${icsText(`Tomorrow: ${d.name}`)}`), "TRIGGER:-P1D", "END:VALARM", "END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  download(`lexflow-deadlines-${slug(c.label || c.model_id)}.ics`, `${lines.join("\r\n")}\r\n`, "text/calendar");
}
$("#import-file").addEventListener("change", async (ev) => {
  const f = ev.target.files && ev.target.files[0];
  ev.target.value = "";
  if (!f) return;
  try {
    const c = JSON.parse(await f.text());
    if (c.lab !== SCHEMA || !/^[a-z]{2}$/.test(c.state || "") || !/^[a-z_]+$/.test(c.question || "") || !Array.isArray(c.events)) throw new Error("not a lexflow lab case file");
    const id = c.id && !db.cases[c.id] ? String(c.id) : uid();
    // the case's calendar choices and place come back with it (cleaned); the export (exportJson) writes them all
    db.cases[id] = { ...c, id, model_id: c.model_id || `${c.state}.${c.question}`, created: c.created || new Date().toISOString(),
      place: cleanPlace(c.place), options: cleanOptions(c.options),
      events: c.events.filter((e) => e && typeof e.type === "string" && validDay(e.date)) };
    db.current = id; saveAll(); renderList(); showCase(id);
  } catch (e) {
    alert(`Could not import: ${e.message}`);
  }
});

// ------------------------------------------------------------------ boot
$("#new-case").addEventListener("click", () => showStart());
$("#theme").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme === "dark" ||
    (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "light" : "dark";
  try { localStorage.setItem("lexflow-theme", document.documentElement.dataset.theme); } catch (e) { /* not kept */ }
});
const params = new URLSearchParams(location.hash.slice(1));   // lab.html#model=va.records (a "Start this process" link)
renderList();
if (params.get("model") || params.get("state")) showStart({ model: params.get("model"), state: params.get("state") });
else if (db.current && db.cases[db.current]) showCase(db.current);
else showStart();
