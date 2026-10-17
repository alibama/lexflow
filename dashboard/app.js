// lexflow dashboard: one page, hash routes, no build step.  Every value from the API is inserted
// with textContent (h() below); only the static icon strings in ICON are parsed as markup.

const $ = (sel, el = document) => el.querySelector(sel);
const view = $("#view");
const tip = $("#tip");

// ------------------------------------------------------------------ helpers
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.append(icon(v));
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
const ICON = {
  done: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="var(--good)"/><path d="M4.5 8.2l2.3 2.3 4.7-4.8" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  partial: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--accent)" stroke-width="1.6"/><path d="M8 1.8a6.2 6.2 0 0 1 0 12.4z" fill="var(--accent)"/></svg>',
  todo: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--baseline)" stroke-width="1.6"/></svg>',
  optional: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--baseline)" stroke-width="1.6" stroke-dasharray="2.4 2.2"/></svg>',
  blocked: '<svg viewBox="0 0 16 16"><path d="M8 1.5l7 12.5H1z" fill="var(--warning)"/><path d="M8 6v3.6M8 11.6v.4" stroke="#0b0b0b" stroke-width="1.6" stroke-linecap="round"/></svg>',
  failed: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="7" fill="var(--critical)"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/></svg>',
  running: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--grid)" stroke-width="2"/><path d="M8 1.8a6.2 6.2 0 0 1 6.2 6.2" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" from="0 8 8" to="360 8 8" dur="0.9s" repeatCount="indefinite"/></path></svg>',
  queued: '<svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6.2" fill="none" stroke="var(--muted)" stroke-width="1.6"/><path d="M8 4.5V8l2.4 1.6" fill="none" stroke="var(--muted)" stroke-width="1.6" stroke-linecap="round"/></svg>',
  info: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="10" cy="10" r="8"/><path d="M10 9v5M10 6.2v.3" stroke-linecap="round"/></svg>',
  check: '<svg viewBox="0 0 16 16"><path d="M3.5 8.4l3 3 6-6.2" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  half: '<svg viewBox="0 0 16 16"><path d="M3.5 8h9" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
  warn: '<svg viewBox="0 0 16 16"><path d="M8 3.2v6M8 12v.6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
};
// replaceChildren, skipping the null/false placeholders that conditional sections leave behind
function rc(el, ...kids) {
  el.replaceChildren(...kids.flat().filter((k) => k != null && k !== false));
}
function icon(name) {
  const t = document.createElement("template");
  t.innerHTML = ICON[name] || "";
  return t.content.firstChild ? t.content.cloneNode(true) : document.createTextNode("");
}
const STATUS_WORD = { done: "Done", partial: "Partly done", todo: "To do", optional: "Optional", blocked: "Needs an earlier step",
  failed: "Failed", running: "Running", queued: "Queued", cancelled: "Cancelled" };
function statusEl(s, word) {
  return h("span", { class: "status" }, icon(ICON[s] ? s : "todo"), word || STATUS_WORD[s] || s);
}
const fmtInt = (n) => (n == null ? "–" : Number(n).toLocaleString());
const pct = (x, d = 0) => (x == null ? "–" : `${(x * 100).toFixed(d)}%`);
const fx = (x, d = 2) => (x == null ? "–" : Number(x).toFixed(d));
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
function ago(ts) {
  if (!ts) return "–";
  const s = (Date.now() - Date.parse(ts)) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(ts).toLocaleDateString();
}
function dur(a, b) {
  if (!a) return "–";
  const s = Math.max(0, ((b ? Date.parse(b) : Date.now()) - Date.parse(a)) / 1000);
  return s < 60 ? `${Math.round(s)} s` : s < 3600 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${(s / 3600).toFixed(1)} h`;
}
async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) {
    let msg = `${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch (e) { /* not json */ }
    throw new Error(msg);
  }
  return r.json();
}
const post = (p, body) => api(p, { method: "POST", body: JSON.stringify(body || {}) });
const put = (p, body) => api(p, { method: "PUT", body: JSON.stringify(body || {}) });
function store(key, value) {
  try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch (e) { return null; }
  return value;
}

// -------------------------------------------------------------- app state
const S = {
  meta: null, question: store("lexflow-q") || "records", layer: store("lexflow-layer") || "confidence",
  version: -1, running: 0, current: null, focus: null, county: null, topo: null, tableView: false,
};
let refreshers = [];          // called when the data version changes
function onRefresh(fn) { refreshers.push(fn); }

async function startRunJob(step, args) {
  const { id } = await post("/api/jobs", { step, args });
  pollSoon();
  return id;
}

// ------------------------------------------------------------- live updates
let pollTimer = null;
async function poll() {
  clearTimeout(pollTimer);
  try {
    const hl = await api("/api/health");
    const live = $("#live");
    live.classList.toggle("on", hl.running > 0);
    $("#live-text").textContent = hl.running > 0 ? `${hl.running} job${hl.running > 1 ? "s" : ""} running` : "Idle";
    const changed = hl.version !== S.version || hl.running !== S.running;
    S.running = hl.running;
    if (changed && S.version !== -1) for (const fn of refreshers) fn();
    S.version = hl.version;
  } catch (e) { $("#live-text").textContent = "Offline"; }
  pollTimer = setTimeout(poll, S.running > 0 ? 2500 : 6000);
}
function pollSoon() { clearTimeout(pollTimer); pollTimer = setTimeout(poll, 400); }

// ---------------------------------------------------------------- routing
const routes = { map: viewMap, setup: viewSetup, places: viewPlaces, place: viewPlace, local: viewLocalProcess, ask: viewAsk, asked: viewAsked, answer: viewAnswer, benchmark: viewBenchmark, processes: viewProcesses, model: viewModel, data: viewData,
  jobs: viewJobs, job: viewJob, method: viewMethod, query: viewQuery, who: viewWho };
async function route() {
  const [, name = "map", ...rest] = (location.hash || "#/map").split("/");
  refreshers = [];
  hideTip();
  for (const a of document.querySelectorAll("nav.tabs a")) {
    const target = a.getAttribute("href").split("/")[1];
    const active = target === name || (name === "model" && target === "processes") || (name === "job" && target === "jobs") || (name === "place" && target === "places") || ((name === "asked" || name === "answer") && target === "ask");
    if (active) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  }
  rc(view, h("p", { class: "muted" }, "Loading…"));
  try {
    if (!S.meta) S.meta = await api("/api/meta");
    await (routes[name] || viewMap)(...rest.map(decodeURIComponent));
  } catch (e) {
    rc(view, h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Could not load this page. "), String(e.message || e))));
  }
}
window.addEventListener("hashchange", route);

$("#theme").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === "dark"
    : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.theme = dark ? "light" : "dark";
  store("lexflow-theme", document.documentElement.dataset.theme);
  for (const fn of refreshers) fn(true);
});

// ------------------------------------------------------------------ pieces
function questionSeg(onChange) {
  const seg = h("div", { class: "seg", role: "group", "aria-label": "Question" });
  for (const [id, q] of Object.entries(S.meta.questions)) {
    seg.append(h("button", { type: "button", "aria-pressed": String(S.question === id), onclick: () => {
      S.question = id; store("lexflow-q", id);
      for (const b of seg.children) b.setAttribute("aria-pressed", String(b.dataset.q === id));
      onChange();
    }, "data-q": id }, q.title));
  }
  return seg;
}
function tierBadge(tier) {
  const label = S.meta.tier_label[tier] || tier;
  const color = tier === "none" ? "var(--neutral-fill)" : `var(--tier-${tier})`;
  return h("span", { class: "badge", title: label }, h("span", { class: "sw", style: `background:${color}` }), label);
}
function stepper(stages) {
  const el = h("span", { class: "stepper", role: "img",
    "aria-label": `${S.meta.stages.filter((s) => stages && stages[s]).length} of ${S.meta.stages.length} stages done` });
  for (const s of S.meta.stages) el.append(h("i", { class: stages && stages[s] ? "on" : "", title: S.meta.stage_label[s] }));
  return el;
}
function mini(v) {
  return h("span", {}, h("span", { class: "mini" }, h("span", { style: `width:${Math.round((v || 0) * 100)}%` })),
    h("span", { class: "num" }, v == null ? "–" : pct(v)));
}
function sortableTable(columns, rows, { onRow, initial } = {}) {
  let sortKey = initial || null, dir = -1;
  const table = h("table", { class: "data" });
  const thead = h("thead"), tbody = h("tbody");
  table.append(thead, tbody);
  function draw() {
    const sorted = [...rows];
    if (sortKey) {
      const col = columns.find((c) => c.key === sortKey);
      const val = col.sort || ((r) => r[sortKey]);
      sorted.sort((a, b) => {
        const x = val(a), y = val(b);
        if (x == null && y == null) return 0;
        if (x == null) return 1;
        if (y == null) return -1;
        return (x > y ? 1 : x < y ? -1 : 0) * dir;
      });
    }
    rc(thead, h("tr", {}, columns.map((c) => h("th", {
      class: c.num ? "num" : "", "data-sort": c.key, scope: "col", "aria-sort": sortKey === c.key ? (dir > 0 ? "ascending" : "descending") : null,
      onclick: () => { if (sortKey === c.key) dir = -dir; else { sortKey = c.key; dir = c.num ? -1 : 1; } draw(); },
    }, c.label, sortKey === c.key ? (dir > 0 ? " ↑" : " ↓") : ""))));
    rc(tbody, ...sorted.map((r) => h("tr", { onclick: onRow ? () => onRow(r) : null, style: onRow ? "cursor:pointer" : "" },
      columns.map((c) => h("td", { class: c.num ? "num" : "" }, c.render ? c.render(r) : (r[c.key] ?? "–"))))));
  }
  draw();
  return h("div", { class: "table-wrap" }, table);
}
function showTip(evt, nodes) {
  rc(tip, ...nodes);
  tip.classList.add("show");
  const pad = 14, w = tip.offsetWidth, hgt = tip.offsetHeight;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
  if (y + hgt > innerHeight - 8) y = evt.clientY - hgt - pad;
  tip.style.left = `${x}px`; tip.style.top = `${y}px`;
}
function hideTip() { tip.classList.remove("show"); }

// ================================================================== MAP
const LAYERS = {
  confidence: { label: "Answer confidence", scope: "county", bins: [0.2, 0.35, 0.5, 0.65],
    labels: ["under 0.20", "0.20–0.35", "0.35–0.50", "0.50–0.65", "0.65 and up"], fmt: (v) => fx(v) },
  tier: { label: "Who built the state model", scope: "state" },
  completion: { label: "State model completion", scope: "state", bins: [0.3, 0.5, 0.7, 0.85],
    labels: ["1–2 of 8 stages", "3 of 8", "4–5 of 8", "6 of 8", "7–8 of 8"], fmt: (v) => pct(v) },
  quality: { label: "State model quality", scope: "state", bins: [0.5, 0.65, 0.8, 0.9],
    labels: ["under 0.50", "0.50–0.65", "0.65–0.80", "0.80–0.90", "0.90 and up"], fmt: (v) => fx(v) },
  contact: { label: "Contact found", scope: "county", bins: [0.15, 0.3, 0.45, 0.7],
    labels: ["mailing address", "some websites", "most have a website", "email or phone", "records or licence page"], fmt: (v) => fx(v) },
  local: { label: "Local law found (LOCUS)", scope: "county", bins: [0.01, 0.1, 0.25, 0.5],
    labels: ["none", "under 10%", "10–25%", "25–50%", "half or more"], fmt: (v) => pct(v) },
};
const TIERS_SHOWN = ["found", "single", "agreed", "reviewed"];
function binColor(v, bins) {
  let i = 0;
  while (i < bins.length && v >= bins[i]) i++;
  return css(`--seq-${i + 1}`);
}

async function viewMap() {
  if (!S.topo) S.topo = await api("/vendor/us-atlas/counties-albers-10m.json");
  const topo = S.topo;
  const counties = topojson.feature(topo, topo.objects.counties).features;
  const statesGeo = topojson.feature(topo, topo.objects.states).features;
  const countyName = new Map(counties.map((c) => [c.id, c.properties.name]));
  const stateByFips = new Map(S.meta.states.map((s) => [s.fips, s]));
  const path = d3.geoPath();

  const layerSel = h("select", { "aria-label": "Map layer", onchange: (e) => { S.layer = e.target.value; store("lexflow-layer", S.layer); load(); } },
    Object.entries(LAYERS).map(([k, l]) => h("option", { value: k, selected: S.layer === k }, l.label)));
  const stateSel = h("select", { "aria-label": "Zoom to a state", onchange: (e) => zoomTo(e.target.value || null) },
    h("option", { value: "" }, "All states"),
    S.meta.states.filter((s) => s.state !== "pr").map((s) => h("option", { value: s.fips }, s.name)));
  const tableBtn = h("button", { class: "btn", type: "button", "aria-pressed": String(S.tableView),
    onclick: () => { S.tableView = !S.tableView; tableBtn.setAttribute("aria-pressed", String(S.tableView)); tableBtn.textContent = S.tableView ? "Show map" : "Table view"; draw(); } },
    S.tableView ? "Show map" : "Table view");
  const kpis = h("div", { class: "grid kpis" });
  const mapWrap = h("div", { class: "map-wrap loading" });
  const legend = h("div", { class: "legend", "aria-label": "Legend" });
  const side = h("aside", { class: "card side", "aria-live": "polite" });
  const tableCard = h("div", { class: "card" });
  rc(view, 
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Where the answers stand"),
      h("p", {}, "Every county, city and town, coloured by how well lexflow can answer the question. Colours update as process models are built, checked and scored."))),
    h("div", { class: "filters" }, questionSeg(load), h("label", { class: "field" }, "Layer", layerSel), h("label", { class: "field" }, "Zoom", stateSel), tableBtn),
    kpis,
    h("div", { class: "grid map-layout" }, h("section", { class: "card" }, mapWrap, legend), side),
    h("div", { class: "spacer" }), tableCard);

  const svg = d3.create("svg").attr("viewBox", "0 0 975 610").attr("role", "img").attr("aria-label", "Map of US counties");
  const defs = svg.append("defs");
  const pat = defs.append("pattern").attr("id", "nodata").attr("width", 5).attr("height", 5)
    .attr("patternUnits", "userSpaceOnUse").attr("patternTransform", "rotate(45)");
  pat.append("rect").attr("width", 5).attr("height", 5).attr("class", "nodata-bg");
  pat.append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 5).attr("class", "nodata-line").attr("stroke-width", 1.2);
  const g = svg.append("g");
  const countyPaths = g.append("g").selectAll("path").data(counties).join("path").attr("class", "county").attr("d", path);
  g.append("path").datum(topojson.mesh(topo, topo.objects.states, (a, b) => a !== b)).attr("class", "state-line").attr("d", path);
  g.append("path").datum(topojson.mesh(topo, topo.objects.nation)).attr("class", "nation").attr("d", path);
  const zoom = d3.zoom().scaleExtent([1, 14]).translateExtent([[-50, -50], [1025, 660]]).on("zoom", (e) => g.attr("transform", e.transform));
  svg.call(zoom).on("wheel.zoom", null);   // page scroll stays page scroll; buttons and drag still zoom
  mapWrap.append(svg.node());

  let data = null, overview = null, rows = [];
  function valueOf(fips) {
    const layer = LAYERS[S.layer];
    if (layer.scope === "county") return data.counties[fips]?.value ?? null;
    const st = data.states[fips.slice(0, 2)];
    if (!st) return null;
    if (S.layer === "tier") return st.tier;
    return st[S.layer] ?? null;
  }
  function fillOf(fips) {
    const v = valueOf(fips);
    const layer = LAYERS[S.layer];
    if (S.layer === "tier") {
      if (!data.states[fips.slice(0, 2)] || !data.states[fips.slice(0, 2)].governments) return "url(#nodata)";
      return v === "none" || v == null ? css("--neutral-fill") : css(`--tier-${v}`);
    }
    if (v == null) return "url(#nodata)";
    return binColor(v, layer.bins);
  }
  function drawLegend() {
    const layer = LAYERS[S.layer];
    const items = S.layer === "tier"
      ? [["none", "No state law found", css("--neutral-fill")], ...TIERS_SHOWN.map((t) => [t, S.meta.tier_label[t], css(`--tier-${t}`)])]
      : layer.labels.map((l, i) => [i, l, css(`--seq-${i + 1}`)]);
    rc(legend, h("span", { class: "title" }, layer.label),
      ...items.map(([, label, color]) => h("span", {}, h("span", { class: "sw", style: `background:${color}` }), label)),
      h("span", {}, h("span", { class: "sw", style: `background:repeating-linear-gradient(45deg, var(--nodata) 0 3px, var(--hatch) 3px 4px)` }), "No data yet"));
  }
  function paint() {
    pat.select(".nodata-bg").attr("fill", css("--nodata"));
    pat.select(".nodata-line").attr("stroke", css("--hatch"));
    countyPaths.attr("fill", (d) => fillOf(d.id));
    drawLegend();
  }
  countyPaths
    .on("pointermove", (evt, d) => {
      const st = stateByFips.get(d.id.slice(0, 2));
      const layer = LAYERS[S.layer];
      const v = valueOf(d.id);
      const c = data?.counties[d.id];
      const sd = data?.states[d.id.slice(0, 2)];
      const vText = S.layer === "tier" ? (S.meta.tier_label[v] || "No data yet") : v == null ? "No data yet" : layer.fmt(v);
      showTip(evt, [
        h("div", { class: "v" }, vText),
        h("div", { class: "k" }, layer.label),
        h("div", { style: "margin-top:6px;font-weight:600" }, `${countyName.get(d.id) || d.id}${st ? `, ${st.name}` : ""}`),
        c ? h("div", { class: "k" }, `${fmtInt(c.n)} government${c.n === 1 ? "" : "s"} scored`) : null,
        c && c.note ? h("div", { class: "k" }, c.note) : null,
        sd && sd.citation ? h("div", { class: "k" }, `State law: ${sd.citation}`) : null,
      ]);
      d3.select(evt.currentTarget).raise();
    })
    .on("pointerleave", hideTip)
    .on("click", (evt, d) => selectCounty(d.id));

  function zoomTo(fips) {
    S.focus = fips;
    stateSel.value = fips || "";
    if (!fips) { svg.transition().duration(600).call(zoom.transform, d3.zoomIdentity); return; }
    const f = statesGeo.find((s) => s.id === fips);
    if (!f) return;
    const [[x0, y0], [x1, y1]] = path.bounds(f);
    const k = Math.min(12, 0.85 / Math.max((x1 - x0) / 975, (y1 - y0) / 610));
    const t = d3.zoomIdentity.translate(975 / 2, 610 / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2);
    svg.transition().duration(700).call(zoom.transform, t);
    if (!S.county) sideState(fips);
  }

  function sideDefault() {
    rc(side, h("div", { class: "card-head" }, h("h2", {}, "Pick a place")),
      h("p", { class: "empty" }, "Click a county to see each government in it: its answer confidence, the state law behind it and who to contact. Choose a state above to zoom in."));
  }
  async function sideState(fips) {
    const r = rows.find((x) => x.fips === fips);
    if (!r) return;
    rc(side, 
      h("div", { class: "card-head" }, h("h2", {}, r.name), h("a", { href: `#/model/${r.state}.${S.question}` }, "Process model →")),
      h("div", { class: "card-pad" }, h("dl", { class: "kv" },
        h("dt", {}, "Governments"), h("dd", { class: "num" }, fmtInt(r.governments)),
        h("dt", {}, "State model"), h("dd", {}, tierBadge(r.tier)),
        h("dt", {}, "Completion"), h("dd", {}, mini(r.completion)),
        h("dt", {}, "Quality"), h("dd", { class: "num" }, fx(r.quality)),
        h("dt", {}, "State law"), h("dd", {}, r.law_url ? h("a", { href: r.law_url, target: "_blank", rel: "noopener" }, r.citation) : (r.citation || "Not located")),
        h("dt", {}, "Located by"), h("dd", {}, r.method ? `${r.method} (score ${fx(r.locator_score, 1)})` : "–"),
        h("dt", {}, "Mean confidence"), h("dd", {}, mini(r.confidence)),
        h("dt", {}, "Records or licence page"), h("dd", { class: "num" }, pct(r.page_share, 1)),
        h("dt", {}, "Statutes"), h("dd", {}, r.statutes))));
  }
  async function selectCounty(fips) {
    S.county = fips;
    countyPaths.classed("active", (d) => d.id === fips);
    if (S.focus !== fips.slice(0, 2)) zoomTo(fips.slice(0, 2));
    rc(side, h("p", { class: "empty" }, "Loading…"));
    const d = await api(`/api/counties/${fips}?question=${S.question}`);
    const st = stateByFips.get(fips.slice(0, 2));
    const head = h("div", { class: "card-head" }, h("div", {},
      h("h2", {}, `${countyName.get(fips) || fips}${st ? `, ${st.name}` : ""}`),
      h("p", {}, `${d.governments.length} government${d.governments.length === 1 ? "" : "s"} · ${S.meta.questions[S.question].title}`)),
      h("button", { class: "btn small", onclick: () => { S.county = null; countyPaths.classed("active", false); sideState(fips.slice(0, 2)); } }, "Close"));
    if (!d.governments.length) {
      rc(side, head, h("p", { class: "empty" }, "No governments loaded for this county yet. Run “Load every county, city and town” on the Setup page, or pull this state from Turso on Data & sync."));
      return;
    }
    rc(side, head, ...d.governments.slice(0, 60).map((g) => h("div", { class: "gov" },
      h("div", { class: "row" }, h("span", { class: "name", style: "color:var(--ink)" }, g.name), h("span", { class: "num" }, g.confidence == null ? "not scored" : fx(g.confidence))),
      h("div", { class: "bar", role: "img", "aria-label": `confidence ${fx(g.confidence)}` }, h("span", { style: `width:${Math.round((g.confidence || 0) * 100)}%` })),
      h("div", { class: "row" }, h("span", {}, `${g.kind}${g.population ? ` · pop. ${fmtInt(g.population)}` : ""}`), h("span", {}, S.meta.contact_label[g.contact_level] || "")),
      g.summary?.offices?.length ? h("ul", { class: "contacts" }, g.summary.offices.map((o) => h("li", {},
        o.kind === "website" || o.kind === "page" ? h("a", { href: o.value, target: "_blank", rel: "noopener" }, o.label || o.value)
          : o.kind === "email" ? h("a", { href: `mailto:${o.value}` }, o.value) : `${o.label ? o.label + ": " : ""}${o.value}`))) : null,
      g.summary?.local?.length ? h("div", { class: "muted", style: "font-size:12px;margin-top:4px" }, `Local law: ${g.summary.local[0]}`) : null)),
      d.governments.length > 60 ? h("p", { class: "empty" }, `…and ${d.governments.length - 60} more.`) : null);
  }

  function drawKpis() {
    const q = overview.questions[S.question];
    const scored = q.answers;
    const models = Object.entries(q.models_by_tier || {}).filter(([t]) => ["reviewed", "agreed", "single"].includes(t)).reduce((a, [, n]) => a + n, 0);
    const page = (q.governments_by_contact || {}).page || 0;
    rc(kpis, 
      h("div", { class: "card tile" }, h("div", { class: "label" }, "Governments scored"), h("div", { class: "value" }, fmtInt(scored)),
        h("div", { class: "sub" }, `of ${fmtInt(overview.governments)} loaded`)),
      h("div", { class: "card tile" }, h("div", { class: "label" }, "Mean answer confidence"), h("div", { class: "value" }, fx(q.mean_confidence)),
        h("div", { class: "meter" }, h("span", { style: `width:${Math.round((q.mean_confidence || 0) * 100)}%` }))),
      h("div", { class: "card tile" }, h("div", { class: "label" }, "States with a step-by-step model"), h("div", { class: "value" }, `${models} of ${S.meta.states.length}`),
        h("div", { class: "sub" }, `${q.states_located} with the state law located`)),
      h("div", { class: "card tile" }, h("div", { class: "label" }, "Records or licence page found"), h("div", { class: "value" }, scored ? pct(page / scored, 1) : "–"),
        h("div", { class: "sub" }, `${fmtInt(page)} government${page === 1 ? "" : "s"}`)));
  }
  function drawTable() {
    const cols = [
      { key: "name", label: "State" },
      { key: "governments", label: "Governments", num: true, render: (r) => fmtInt(r.governments) },
      { key: "tier", label: "State model", render: (r) => tierBadge(r.tier), sort: (r) => S.meta.tiers.indexOf(r.tier) },
      { key: "completion", label: "Completion", render: (r) => mini(r.completion) },
      { key: "quality", label: "Quality", num: true, render: (r) => fx(r.quality) },
      { key: "confidence", label: "Mean confidence", render: (r) => mini(r.confidence) },
      { key: "page_share", label: "Page found", num: true, render: (r) => pct(r.page_share, 1) },
      { key: "citation", label: "State law", render: (r) => r.law_url ? h("a", { href: r.law_url, target: "_blank", rel: "noopener", onclick: (e) => e.stopPropagation() }, r.citation) : h("span", { class: "muted" }, r.statutes === "not-in-release" ? "No statutes in release" : r.law_status === "not-located" ? "Not located" : r.law_status) },
    ];
    rc(tableCard, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "State by state"),
      h("p", {}, "Sort by any column. Click a row to zoom the map to that state."))),
      h("div", { class: "card-pad", style: "padding-top:8px" }, sortableTable(cols, rows, { initial: "governments",
        onRow: (r) => { zoomTo(r.fips); window.scrollTo({ top: 0, behavior: "smooth" }); } })));
  }
  function draw() {
    mapWrap.parentElement.style.display = S.tableView ? "none" : "";
    side.style.display = S.tableView ? "none" : "";
    if (data) paint();
  }
  async function load(themeOnly) {
    if (themeOnly === true && data) { paint(); return; }
    mapWrap.classList.add("loading");
    [data, overview, rows] = await Promise.all([api(`/api/map?question=${S.question}&layer=${S.layer}`), api("/api/overview"), api(`/api/states?question=${S.question}`)]);
    mapWrap.classList.remove("loading");
    drawKpis(); drawTable(); draw();
    if (S.county) selectCounty(S.county); else if (S.focus) sideState(S.focus); else sideDefault();
  }
  onRefresh(load);
  sideDefault();
  await load();
  if (S.focus) zoomTo(S.focus);
  if (!overview.governments) {
    view.prepend(h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Nothing loaded yet. "),
      "Open ", h("a", { href: "#/setup" }, "Setup"), " and tick the required boxes in order, or pull a shared state from ", h("a", { href: "#/data" }, "Data & sync"), ".")));
  }
}

// ================================================================== SETUP
async function viewSetup() {
  const services = h("div", { class: "services" });
  const list = h("ol", { class: "steps" });
  const credits = h("div", { class: "credits-all" });
  const quickStates = h("input", { type: "text", value: store("lexflow-qs-states") || "va", "aria-label": "States", placeholder: "va,dc or all" });
  const quickNoLlm = h("input", { type: "checkbox" });
  rc(view, 
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Setup"),
      h("p", {}, "Everything is rebuilt from public data. Tick the required boxes in order (each one says what it needs), or run them all at once for the states you care about. Boxes tick themselves when the data is there."))),
    services,
    h("section", { class: "card card-pad", style: "margin-bottom:16px" },
      h("div", { class: "row-flex" },
        h("div", {}, h("h2", {}, "Quick start"), h("p", { class: "ink-2", style: "margin:2px 0 0" }, "Runs governments → statutes → law → contacts → models → scores. Use ‘all’ for every state (about 870 MB of statutes).")),
        h("div", { class: "right row-flex" },
          h("label", { class: "field" }, "States", quickStates),
          h("label", { class: "check" }, quickNoLlm, "Skip local models"),
          h("button", { class: "btn primary", onclick: async (e) => {
            store("lexflow-qs-states", quickStates.value);
            e.target.disabled = true;
            await startRunJob("quickstart", { states: quickStates.value, no_llm: quickNoLlm.checked });
            location.hash = "#/jobs";
          } }, "Run required steps")))),
    h("section", { class: "card" }, list),
    credits);

  // one line per credit: name (maker) · licence (linked to its terms when given) · link · what lexflow uses it
  // for, then the citation (labelled the maker's own wording or lexflow's format) and any notice
  function creditList(cs) {
    const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return u; } };
    const https = (u) => /^https:\/\//.test(u || "");
    const out = (u, text, label) => h("a", { href: u, target: "_blank", rel: "noopener", "aria-label": `${label} (opens in a new tab)` }, text);
    return h("ul", { class: "credits" }, cs.map((c) => h("li", {},
      h("span", { class: "name" }, c.name),
      c.by && c.by.toLowerCase() !== String(c.name).toLowerCase() ? ` (${c.by})` : null, " · ",
      https(c.licence_url) ? out(c.licence_url, c.licence, `${c.name} licence or terms: ${c.licence}`) : c.licence, " · ",
      https(c.url) ? out(c.url, `${host(c.url)} ↗`, `${c.name} on ${host(c.url)}`) : c.url,
      c.use ? h("span", { class: "use" }, ` · ${c.use}`) : null,
      c.cite ? h("details", {}, h("summary", { "aria-label": `Cite ${c.name}` }, "Cite"), h("code", {}, c.cite),
        h("div", { class: "note" }, c.cite_by === "maker" ? "The maker's own citation, word for word."
          : "Written in lexflow's format; the maker's page may give its own.")) : null,
      c.note ? h("div", { class: "note" }, c.note) : null)));
  }
  function serviceCard(name, ok, sub, word) {
    return h("div", { class: "card service" }, h("div", { class: "name" }, statusEl(ok === true ? "done" : ok === false ? "blocked" : "optional", ""), name),
      h("div", { class: "sub" }, word), h("div", { class: "sub muted" }, sub));
  }
  async function load() {
    const [setup, jobs] = await Promise.all([api("/api/setup"), api("/api/jobs?limit=40")]);
    const sv = setup.services;
    const o = sv.ollama;
    rc(services, 
      serviceCard("Ollama", o.reachable && o.want.every((m) => o.models.includes(m)) ? true : o.reachable ? null : false, o.url,
        o.reachable ? (o.models.length ? `Models: ${o.models.join(", ")}` : "Running, no models yet") : "Not reachable: start with --profile llm"),
      serviceCard("Turso sharing", sv.turso.configured ? sv.turso.reachable : null, sv.turso.url || "TURSO_DATABASE_URL not set",
        sv.turso.configured ? (sv.turso.reachable ? "Connected" : `Not reachable${sv.turso.error ? `: ${sv.turso.error}` : ""}`) : "Optional"),
      serviceCard("Lexipedia wiki", sv.dokuwiki.configured ? true : null, sv.dokuwiki.url || "DOKUWIKI_URL not set", sv.dokuwiki.configured ? "Bot token set" : "Optional"),
      serviceCard("Data folder", true, sv.data_dir, "Local SQLite store and downloads"));
    const active = new Map();
    for (const j of jobs) if (["running", "queued"].includes(j.status)) {
      if (!active.has(j.step)) active.set(j.step, j);
      if (j.step === "quickstart") for (const s of ["governments", "statutes", "locate", "contacts", "build", "score"]) if (!active.has(s)) active.set(s, j);
    }
    rc(list, ...setup.steps.map((s, i) => stepRow(s, i + 1, active.get(s.id))));
    rc(credits, setup.credits && setup.credits.length ? h("section", { class: "card card-pad" },
      h("h2", {}, "Sources and credits"),
      h("p", { class: "ink-2" }, "Each step above lists the data, services and models it uses. These libraries, tools and services are used across the steps, or by Answer a new question."),
      creditList(setup.credits),
      h("p", { class: "muted" }, "Credit is not endorsement: the people and projects listed here have not reviewed lexflow.")) : null);
  }
  function stepRow(s, n, job) {
    const box = h("span", { class: "box", "aria-hidden": "true" },
      s.status === "done" ? icon("check") : s.status === "partial" ? icon("half") : s.status === "blocked" ? icon("warn") : null);
    const opts = h("div", { class: "opts" });
    const values = {};
    if (s.params.includes("states")) {
      const inp = h("input", { type: "text", placeholder: "states: va,dc or all", value: store(`lexflow-st-${s.id}`) || (s.id === "statutes" || s.id === "locate" ? "all" : "va"), "aria-label": `States for ${s.title}` });
      values.states = () => { store(`lexflow-st-${s.id}`, inp.value); return inp.value; };
      opts.append(inp);
    }
    if (s.params.includes("places")) {
      const inp = h("input", { type: "text", placeholder: "places: va:charlottesville,dc", value: store(`lexflow-pl-${s.id}`) || "", "aria-label": `Places for ${s.title}` });
      values.places = () => { store(`lexflow-pl-${s.id}`, inp.value); return inp.value || undefined; };
      opts.append(inp);
    }
    if (s.params.includes("direction")) {
      const sel = h("select", { "aria-label": "Direction" }, h("option", { value: "push" }, "Push"), h("option", { value: "pull" }, "Pull"));
      values.direction = () => sel.value;
      opts.append(sel);
    }
    for (const [k, label] of [["force", "Redo"], ["no_llm", "Skip models"], ["regulations", "+ regulations"], ["full", "Full resend"], ["dry_run", "Dry run"]]) {
      if (!s.params.includes(k)) continue;
      const cb = h("input", { type: "checkbox" });
      values[k] = () => cb.checked;
      opts.append(h("label", { class: "check" }, cb, label));
    }
    const run = h("button", { class: `btn ${s.level === "required" && s.status !== "done" ? "primary" : ""}`, disabled: !s.runnable || s.status === "blocked" || !!job,
      onclick: async () => {
        const args = Object.fromEntries(Object.entries(values).map(([k, f]) => [k, f()]));
        run.disabled = true;
        await startRunJob(s.id, args);
        load();
      } }, job ? "Running…" : s.status === "done" ? "Run again" : "Run");
    const progress = job ? h("div", { class: "progress" },
      h("div", { class: "row-flex", style: "gap:6px" }, statusEl(job.status), h("a", { href: `#/job/${job.id}`, class: "right", style: "font-size:12px" }, "Log")),
      h("div", { class: "meter" }, h("span", { style: `width:${Math.round((job.progress || 0) * 100)}%` })),
      h("div", { class: "msg", title: job.message || "" }, job.message || "")) : null;
    const frac = s.total ? h("span", { class: "muted num" }, ` · ${fmtInt(s.done)} of ${fmtInt(s.total)}`) : null;
    return h("li", { class: `step ${s.status}` },
      box,
      h("div", {},
        h("div", { class: "title" }, `${n}. ${s.title}`, h("span", { class: `tag ${s.level}` }, s.level), statusEl(job ? job.status : s.status)),
        h("p", { class: "why" }, s.why),
        s.credits && s.credits.length ? h("div", { class: "step-credits" }, h("span", { class: "lab" }, "Credits"), creditList(s.credits))
          : s.credits_note ? h("div", { class: "step-credits" }, h("span", { class: "lab" }, "Credits"), h("span", { class: "muted" }, ` ${s.credits_note}`)) : null,
        h("div", { class: "detail" }, s.detail, frac),
        s.needs.length ? h("div", { class: "meta" }, `Needs: ${s.needs.join(", ")}`) : null,
        s.cost ? h("div", { class: "meta" }, `Cost: ${s.cost}`) : null),
      h("div", { class: "actions" }, opts, run, progress));
  }
  onRefresh(load);
  await load();
}

// ============================================================== PROCESSES
async function viewProcesses() {
  const tierSel = h("select", { "aria-label": "Tier", onchange: draw }, h("option", { value: "" }, "All tiers"),
    [...S.meta.tiers].reverse().map((t) => h("option", { value: t }, S.meta.tier_label[t])));
  const statusSel = h("select", { "aria-label": "Status", onchange: draw }, h("option", { value: "" }, "All answers"),
    Object.entries(ASK_STATUS).map(([k, [, word]]) => h("option", { value: k }, word)));
  // every question asked on the Ask page, beside the two built questions; a question asked twice (its id changed
  // with the planner) is listed once, under the id with the most answers
  const askedSel = h("select", { "aria-label": "Asked question", style: "width:46ch;max-width:100%;min-width:0", onchange: () => pick(askedSel.value) });
  const tierField = h("label", { class: "field" }, "Tier", tierSel);
  const statusField = h("label", { class: "field" }, "Answers", statusSel);
  const seg = questionSeg(() => pick(""));
  const funnels = h("div", { class: "grid two" });
  const grid = h("div", { class: "model-grid" });
  const intro = h("p", {});
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Process models"), intro)),
    h("div", { class: "filters" }, seg, h("label", { class: "field", style: "min-width:0;max-width:100%" }, "Asked question", askedSel), tierField, statusField),
    funnels, h("div", { class: "spacer" }), grid);
  let models = [], overview = null, asked = [];
  const detail = {};
  let current = store("lexflow-pq") || "";
  function funnel(qid) {
    const st = overview.stages[qid];
    const max = overview.stages.possible;
    return h("section", { class: "card" },
      h("div", { class: "card-head" }, h("div", {}, h("h2", {}, S.meta.questions[qid].title), h("p", {}, `States reaching each stage, of ${max}`))),
      h("div", { class: "funnel" }, S.meta.stages.map((s) => h("div", { class: "funnel-row", title: `${S.meta.stage_label[s]}: ${st[s]} of ${max}` },
        h("span", { class: "lab" }, S.meta.stage_label[s]),
        h("span", { class: "track" }, h("span", { class: "fill", style: `width:${(st[s] / max) * 100}%` })),
        h("span", { class: "num", style: "text-align:right" }, st[s])))));
  }
  function distinct(rows) {
    const by = new Map();
    for (const r of rows) {
      const k = (r.question || "").toLowerCase().replace(/\s+/g, " ").trim();
      const prev = by.get(k);
      if (!prev || r.answers > prev.answers || (r.answers === prev.answers && r.updated_at > prev.updated_at)) by.set(k, r);
    }
    return [...by.values()].sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  }
  async function pick(qid) {
    current = qid && asked.some((q) => q.question_id === qid) ? qid : "";
    store("lexflow-pq", current);
    askedSel.value = current;
    if (current && !detail[current]) detail[current] = await api(`/api/ask/${encodeURIComponent(current)}`);
    draw();
  }
  function drawBuilt() {
    intro.textContent = "One model per state and question. Each bar shows how far the model has come, from locating the law to publishing it; quality combines exact quotes, schema and lint checks, Petri-net soundness, explicit grounding and agreement between two models.";
    rc(funnels, ...Object.keys(S.meta.questions).map(funnel));
    const shown = models.filter((m) => m.question === S.question && (!tierSel.value || m.tier === tierSel.value))
      .sort((a, b) => S.meta.tiers.indexOf(b.tier) - S.meta.tiers.indexOf(a.tier) || (b.quality || 0) - (a.quality || 0));
    rc(grid, ...(shown.length ? shown.map((m) => h("a", { class: "card model-card", href: `#/model/${m.model_id}` },
      h("div", { class: "top" }, h("strong", {}, m.state_name), tierBadge(m.tier)),
      h("div", {}, m.title || S.meta.questions[m.question].title),
      h("div", { class: "cite" }, m.citation || "No state law located"),
      h("div", { class: "row-flex" }, stepper(m.stages), h("span", { class: "muted num", style: "font-size:12px" }, pct(m.completion))),
      h("div", { class: "row-flex", style: "font-size:12.5px" },
        h("span", { class: "ink-2" }, "Quality ", h("strong", { class: "num", style: "color:var(--ink)" }, fx(m.quality))),
        h("span", { class: "right muted" }, m.built_by || "–"))))
      : [h("p", { class: "muted" }, "No models for this question yet. Run “Build the state process models” on the Setup page.")]));
  }
  function drawAsked() {
    const q = asked.find((x) => x.question_id === current);
    const d = detail[current];
    intro.textContent = "A question asked on the Ask page: one answer per state, each with the sections it rests on and, for a how-do-I question, steps from the law's own words and a draft process map. These are machine-made and not reviewed.";
    const states = d.answers.filter((r) => !r.gov_id);
    const places = {};
    for (const r of d.answers) if (r.gov_id) places[r.state] = (places[r.state] || 0) + 1;
    const count = (s) => states.filter((r) => r.status === s).length;
    rc(funnels, h("section", { class: "card" },
      h("div", { class: "card-head" }, h("div", {}, h("h2", {}, d.question),
        h("p", {}, `${states.length} state ${states.length === 1 ? "answer" : "answers"} · ${d.answers.length - states.length} places · ${{ process: "a how-do-I question", facts: "a question of fact" }[q.kind] || "a question of fact or process"}`))),
      h("div", { class: "funnel" }, Object.entries(ASK_STATUS).map(([k, [, word]]) => h("div", { class: "funnel-row", title: `${word}: ${count(k)} of ${states.length}` },
        h("span", { class: "lab" }, word),
        h("span", { class: "track" }, h("span", { class: "fill", style: `width:${states.length ? (count(k) / states.length) * 100 : 0}%` })),
        h("span", { class: "num", style: "text-align:right" }, count(k))))),
      h("div", { class: "card-pad" }, h("a", { href: `#/asked/${encodeURIComponent(current)}` }, "Every place's answer"))));
    const shown = states.filter((r) => !statusSel.value || r.status === statusSel.value)
      .sort((a, b) => (a.name || "").localeCompare(b.name || ""));
    rc(grid, ...(shown.length ? shown.map((r) => h("a", { class: "card model-card", href: `#/answer/${encodeURIComponent(current)}/${encodeURIComponent(r.target)}` },
      h("div", { class: "top" }, h("strong", {}, r.name), askStatus(r.status)),
      h("div", { class: "cite" }, (r.sections || []).slice(0, 3).join(", ") || "No section found"),
      h("div", { class: "row-flex", style: "font-size:12.5px" },
        h("span", { class: "ink-2" }, r.steps ? `${r.steps} ${r.steps === 1 ? "step" : "steps"}${r.map ? " · draft process map" : ""}` : `${r.quotes} quotes`),
        h("span", { class: "right muted" }, places[r.state] ? `${places[r.state]} places` : "")),
      h("div", { class: "row-flex", style: "font-size:12px" }, h("span", { class: "muted" }, r.model || "no summary model"))))
      : [h("p", { class: "muted" }, "No state answers with this status.")]));
  }
  function draw() {
    if (!overview) return;
    const mode = current && detail[current] ? "asked" : "built";
    for (const b of seg.children) b.setAttribute("aria-pressed", String(mode === "built" && b.dataset.q === S.question));
    tierField.style.display = mode === "built" ? "" : "none";      // .field sets display, which beats [hidden]
    statusField.style.display = mode === "asked" ? "" : "none";
    if (mode === "asked") drawAsked(); else drawBuilt();
  }
  async function load() {
    let rows;
    [models, overview, rows] = await Promise.all([api("/api/models"), api("/api/overview"), api("/api/ask").catch(() => [])]);
    asked = distinct(rows || []);
    rc(askedSel, h("option", { value: "" }, asked.length ? "Choose one…" : "None asked yet"),
      asked.map((q) => h("option", { value: q.question_id }, (q.question || q.question_id).length > 90 ? `${(q.question || q.question_id).slice(0, 88)}…` : (q.question || q.question_id))));
    askedSel.disabled = !asked.length;
    for (const k of Object.keys(detail)) delete detail[k];
    await pick(current);
  }
  onRefresh(load);
  await load();
}

async function viewModel(mid) {
  const m = await api(`/api/models/${encodeURIComponent(mid)}`);
  const law = m.law || {};
  const metrics = m.metrics || {};
  const downloads = h("div", { class: "row-flex" }, ["bpmn", "dmn", "svg", "facts"].filter((k) => (k === "facts" ? m.facts && Object.keys(m.facts).length : m[k]))
    .map((k) => h("a", { class: "btn small", href: `/api/models/${encodeURIComponent(mid)}/${k}`, download: `${mid}.${k === "facts" ? "json" : k}` }, `.${k === "facts" ? "json" : k}`)));
  const stageList = h("ol", { class: "steps-list", style: "list-style:none;padding-left:18px" },
    S.meta.stages.map((s) => h("li", { class: "row-flex" }, statusEl(m.stages[s] ? "done" : "todo", S.meta.stage_label[s]),
      h("span", { class: "right muted", style: "font-size:12px" }, m.stages[s] ? ago(m.stages[s]) : ""))));
  const kv = [
    ["Quality score", fx(m.quality)], ["Quotes checked", metrics.quotes_checked != null ? `${metrics.quotes_checked} (${metrics.quote_misses} not exact)` : "–"],
    ["BPMN / DMN schema errors", metrics.bpmn_xsd_errors != null ? `${metrics.bpmn_xsd_errors} / ${metrics.dmn_xsd_errors ?? 0}` : "–"],
    ["bpmnlint errors / warnings", metrics.lint_errors != null ? `${metrics.lint_errors} / ${metrics.lint_warnings}` : "–"],
    ["Petri nets sound", metrics.nets ? `${metrics.nets_sound} of ${metrics.nets}` : "–"],
    ["Explicitly grounded", metrics.explicit_share != null ? pct(metrics.explicit_share) : "–"],
    ["Agreement between models", metrics.agreement != null ? fx(metrics.agreement) : "–"],
    ["Flow nodes · timers · rules", metrics.flow_nodes != null ? `${metrics.flow_nodes} · ${metrics.timers} · ${metrics.rules}` : "–"],
    ["Built by", m.built_by || "–"], ["Governments using it", fmtInt(m.governments)],
  ];
  const bpmnHost = h("div", { class: "bpmn-host", id: "bpmn" });
  const steps = h("ol", { class: "steps-list" }, (m.steps || []).map((s) => h("li", {},
    h("div", { class: "row-flex" }, h("strong", {}, s.step), h("span", { class: "muted" }, `· ${s.who}`), s.deadline ? h("span", { class: "badge" }, `within ${s.deadline}`) : null,
      s.modality && s.modality !== "none" ? h("span", { class: "tag" }, s.modality) : null, h("span", { class: "right muted mono" }, s.cite)),
    s.quote ? h("p", { class: "quote" }, `“${s.quote}”`) : null)));
  const decisions = (m.facts?.decisions || []).map((d) => h("section", { class: "card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, d.question), h("p", {}, `Decision table · hit policy ${d.hit_policy}`))),
    decisionTable(d)));
  const quotes = [];
  (function collect(o) { if (o && typeof o === "object") { if (o.quote && typeof o.quote === "string") quotes.push(o.quote); Object.values(o).forEach(collect); } })(m.facts);
  const lawText = h("div", { class: "lawtext" });
  if (law.text) {
    const t = law.text;
    const marks = [];
    for (const q of new Set(quotes)) { let i = t.indexOf(q); while (i >= 0) { marks.push([i, i + q.length]); i = t.indexOf(q, i + q.length); } }
    marks.sort((a, b) => a[0] - b[0]);
    let pos = 0;
    for (const [a, b] of marks) { if (a < pos) continue; lawText.append(t.slice(pos, a), h("mark", {}, t.slice(a, b))); pos = b; }
    lawText.append(t.slice(pos));
  }
  rc(view, 
    h("div", { class: "page-head" }, h("div", {},
      h("div", { class: "muted" }, h("a", { href: "#/processes" }, "Process models"), ` / ${m.state_name}`),
      h("h1", {}, m.title || S.meta.questions[m.question].title),
      h("p", {}, `${S.meta.questions[m.question].title} · ${m.state_name}`)),
      h("div", { class: "row-flex" }, tierBadge(m.tier), downloads)),
    h("div", { class: "grid two" },
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Completion"), stepper(m.stages)), stageList),
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Quality")),
        h("dl", { class: "kv card-pad" }, kv.flatMap(([k, v]) => [h("dt", {}, k), h("dd", { class: "num" }, v)])))),
    h("div", { class: "spacer" }),
    m.bpmn ? h("section", { class: "card" }, h("div", { class: "card-head", style: "padding-bottom:12px" }, h("div", {}, h("h2", {}, "BPMN process map"), h("p", {}, "Drag to pan, scroll to zoom. Every step is grounded in a quote from the statute below."))), bpmnHost) : null,
    m.bpmn ? h("div", { class: "spacer" }) : null,
    m.steps?.length ? h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Steps and the words they come from")), steps) : null,
    ...decisions.flatMap((d) => [h("div", { class: "spacer" }), d]),
    h("div", { class: "spacer" }),
    h("section", { class: "card" },
      h("div", { class: "card-head" }, h("div", {}, h("h2", {}, law.citation || "State law"),
        h("p", {}, law.heading || "Not located", law.method ? ` · found by ${law.method} (score ${fx(law.score, 1)})` : "")),
        law.url ? h("a", { class: "btn small", href: law.url, target: "_blank", rel: "noopener" }, "Official text ↗") : null),
      law.text ? lawText : h("p", { class: "card-pad muted" }, "No text yet.")),
    (metrics.gaps || []).length ? h("div", { class: "spacer" }) : null,
    (metrics.gaps || []).length ? h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Gaps the text leaves open")),
      h("ul", { class: "card-pad", style: "margin:0;padding-left:36px" }, metrics.gaps.map((g) => h("li", {}, g)))) : null,
    m.extractions?.length ? h("div", { class: "spacer" }) : null,
    m.extractions?.length ? h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Local model runs")),
      h("div", { class: "card-pad" }, sortableTable([
        { key: "llm", label: "Model" }, { key: "ok", label: "Quotes exact", render: (r) => statusEl(r.ok ? "done" : "failed", r.ok ? "Yes" : "No") },
        { key: "rounds", label: "Rounds", num: true }, { key: "seconds", label: "Seconds", num: true },
        { key: "problems", label: "First problem", render: (r) => (r.problems && r.problems[0]) || "–" }], m.extractions))) : null,
    law.candidates?.length ? h("div", { class: "spacer" }) : null,
    law.candidates?.length ? h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Other sections the locator considered"), h("p", {}, "Higher scores matched the question more strongly."))),
      h("div", { class: "card-pad" }, sortableTable([
        { key: "citation", label: "Section", render: (r) => h("a", { href: r.url, target: "_blank", rel: "noopener" }, r.citation) },
        { key: "heading", label: "Heading" }, { key: "score", label: "Score", num: true }, { key: "words", label: "Words", num: true }], law.candidates, { initial: "score" }))) : null);
  if (m.bpmn && window.BpmnJS) {
    const viewer = new BpmnJS({ container: bpmnHost });
    try {
      await viewer.importXML(m.bpmn);
      viewer.get("canvas").zoom("fit-viewport", "auto");
    } catch (e) { rc(bpmnHost, h("p", { class: "card-pad muted" }, `Could not draw the diagram: ${e.message}`)); }
  }
}

// A DMN table as HTML: inputs, then outputs (marked →), then the source of each rule
function decisionTable(d) {
  const cell = (x) => h("td", { class: "mono" }, String(x).replace(/^"(.*)"$/, "$1"));
  return h("div", { class: "dmn table-wrap" }, h("table", { class: "data" },
    h("thead", {}, h("tr", {}, d.inputs.map((c) => h("th", { scope: "col" }, c.label)),
      d.outputs.map((c) => h("th", { scope: "col", style: "color:var(--accent-ink)" }, `→ ${c.label}`)), h("th", { scope: "col" }, "Source"))),
    h("tbody", {}, d.rules.map((r) => h("tr", {}, r.when.map(cell), r.then.map(cell),
      h("td", { class: "muted", style: "font-size:12px", title: r.source?.quote || "" },
        `§ ${r.source?.section || ""}${r.source?.subsection ? `(${r.source.subsection.split(".").join(")(")})` : ""}`))))));
}

// ==================================================================== ASK
const ASK_STATUS = { answered: ["done", "Answered"], partial: ["partial", "Partly answered"], not_found: ["blocked", "Law not found"],
  "no-statutes": ["optional", "No statute file"] };
function askStatus(s) { const [ic, word] = ASK_STATUS[s] || ["todo", s || "–"]; return statusEl(ic, word); }

async function viewAsk() {
  const sugg = await api("/api/ask/suggestions");
  const question = h("textarea", { rows: 3, "aria-label": "Your question", placeholder: "Ask about any state's law, e.g. How do I get my record sealed?",
    style: "width:100%;box-sizing:border-box;padding:10px" });
  question.value = store("lexflow-ask-q") || "";
  question.addEventListener("input", () => store("lexflow-ask-q", question.value));
  const examples = h("select", { "aria-label": "Example questions", style: "max-width:min(420px, 60vw)", onchange: (e) => { if (e.target.value) { question.value = e.target.value; store("lexflow-ask-q", question.value); } e.target.value = ""; } },
    h("option", { value: "" }, "Examples…"),
    sugg.map((g) => h("optgroup", { label: g.group }, g.questions.map((q) => h("option", { value: q.text }, q.text.length > 110 ? q.text.slice(0, 107) + "…" : q.text)))));
  // targets: states or governments, chosen from an autocomplete list
  let chosen = JSON.parse(store("lexflow-ask-targets") || "[]");
  const chips = h("div", { class: "row-flex", style: "flex-wrap:wrap;gap:6px" });
  const saveTargets = () => { store("lexflow-ask-targets", JSON.stringify(chosen)); drawChips(); };
  function drawChips() {
    rc(chips, chosen.length ? chosen.map((t, i) => h("span", { class: "tag", style: "display:inline-flex;gap:6px;align-items:center" }, t.label,
      h("button", { class: "icon-btn", "aria-label": `Remove ${t.label}`, onclick: () => { chosen.splice(i, 1); saveTargets(); } }, "×")))
      : h("span", { class: "muted" }, "No states or places chosen yet."));
  }
  const find = h("input", { type: "search", placeholder: "Add a state, county, city or town", "aria-label": "Add a state or place", style: "width:min(360px, 100%)", autocomplete: "off" });
  const results = h("div", { class: "card", style: "position:absolute;z-index:5;min-width:320px;display:none;max-height:300px;overflow:auto" });
  let timer = null;
  find.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = find.value.trim();
      if (q.length < 2) { results.style.display = "none"; return; }
      const rows = await api(`/api/targets?q=${encodeURIComponent(q)}`);
      rc(results, rows.length ? rows.map((r) => h("button", { class: "btn", style: "display:block;width:100%;text-align:left;border:0;border-radius:0",
        onclick: () => { if (!chosen.some((c) => c.target === r.target)) chosen.push({ target: r.target, label: r.label }); saveTargets(); find.value = ""; results.style.display = "none"; } },
        r.label, h("span", { class: "muted" }, r.kind === "state" ? "" : ` · ${r.kind}${r.population ? ` · ${fmtInt(r.population)}` : ""}`)))
        : h("p", { class: "card-pad muted" }, "No match."));
      results.style.display = "block";
    }, 200);
  });
  const bench = h("button", { class: "btn small", onclick: () => {
    for (const [t, label] of [["va", "Virginia (state law)"], ["dc", "District of Columbia (state law)"], ["md", "Maryland (state law)"], ["tx", "Texas (state law)"], ["ca", "California (state law)"]])
      if (!chosen.some((c) => c.target === t)) chosen.push({ target: t, label });
    saveTargets(); } }, "Add the five benchmark states");
  const everyPlace = h("input", { type: "checkbox", id: "ask-all" });
  const useLlm = h("input", { type: "checkbox", id: "ask-llm" });
  useLlm.checked = store("lexflow-ask-llm") === "1";
  useLlm.addEventListener("change", () => store("lexflow-ask-llm", useLlm.checked ? "1" : "0"));
  const msg = h("div");
  const askBtn = h("button", { class: "btn primary", onclick: async () => {
    const targets = chosen.map((c) => c.target);
    if (everyPlace.checked) for (const c of chosen) if (/^[a-z]{2}$/.test(c.target)) targets.push(`${c.target}:*`);
    try {
      const r = await post("/api/ask", { question: question.value, targets, use_llm: useLlm.checked });
      pollSoon();
      rc(msg, h("div", { class: "notice" }, icon("running"), h("div", {}, "Answering in the background (job ", h("a", { href: `#/job/${r.job}` }, `#${r.job}`), "). Answers appear ",
        h("a", { href: `#/asked/${encodeURIComponent(r.question_id)}` }, "here"), " as each state finishes.")));
    } catch (e) { rc(msg, h("div", { class: "notice" }, icon("info"), String(e.message || e))); }
  } }, "Ask");
  const list = h("div");
  async function load() {
    const rows = await api("/api/ask");
    rc(list, rows.length ? sortableTable([
      { key: "question", label: "Question", render: (r) => h("a", { href: `#/asked/${encodeURIComponent(r.question_id)}` }, r.question) },
      { key: "answers", label: "Answers", num: true }, { key: "answered", label: "Answered", num: true },
      { key: "partial", label: "Partly", num: true }, { key: "not_found", label: "Not found", num: true },
      // a review counts only while it is for the text stored now (the API checks its hash); "For the wiki" is
      // what the next publish writes: reviewed answers that are also ticked
      { key: "reviewed", label: "Reviewed", num: true, render: (r) => r.review_stale ? `${r.reviewed} (${r.review_stale} for older text)` : String(r.reviewed || 0) },
      { key: "published", label: "For the wiki", num: true }, { key: "updated_at", label: "Updated", render: (r) => ago(r.updated_at) }], rows, { initial: "updated_at" })
      : h("p", { class: "card-pad muted" }, "No questions asked yet."));
  }
  drawChips();
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Ask a question"),
      h("p", {}, "lexflow searches each chosen state's statutes, quotes the sections that answer the question word for word, extracts the steps of any procedure, and adds each place's local layer. Answers are machine-made; every claim links to the law's own words, and an answer goes on the wiki only after a named person has reviewed it."))),
    h("section", { class: "card" }, h("div", { class: "card-pad" },
      h("div", { class: "row-flex", style: "margin-bottom:8px" }, h("strong", {}, "Question"), h("span", { class: "right" }, examples)), question,
      h("div", { class: "row-flex", style: "margin:14px 0 8px" }, h("strong", {}, "Where"), h("span", { class: "right" }, bench)),
      h("div", { style: "position:relative" }, find, results), h("div", { style: "margin-top:8px" }, chips),
      h("div", { class: "row-flex", style: "margin-top:14px;gap:18px;flex-wrap:wrap" },
        h("label", { class: "check", for: "ask-all" }, everyPlace, "Also answer for every county, city and town in the chosen states"),
        h("label", { class: "check", for: "ask-llm" }, useLlm, `Add a plain-language summary by ${S.meta.ask_model || "a local model"} (slower; every claim is checked against the quotes)`)),
      h("div", { class: "row-flex", style: "margin-top:14px" }, askBtn), msg)),
    h("div", { class: "spacer" }),
    h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Questions asked")), h("div", { class: "card-pad" }, list)));
  onRefresh(load);
  await load();
}

async function viewAsked(qid) {
  const body = h("div");
  async function load() {
    const d = await api(`/api/ask/${encodeURIComponent(qid)}`);
    // an answer goes on the wiki only after a named person has reviewed it: until then the box is off and says why
    const publish = (r) => {
      const ok = !!r.reviewed_by;
      return h("label", { class: "check", title: ok ? r.review_line : "Record a named reviewer on the answer's page first" },
        h("input", { type: "checkbox", "aria-label": `Publish the answer for ${r.name}`, checked: ok && !!r.published, disabled: !ok,
          onchange: async (e) => {
            try { await post(`/api/ask/${encodeURIComponent(qid)}/${encodeURIComponent(r.target)}/publish`, { published: e.target.checked }); }
            catch (err) { e.target.checked = false; e.target.closest("label").title = String(err.message || err); }
          } }),
        ok ? null : h("span", { class: "muted" }, "needs a named reviewer"));
    };
    rc(body,
      h("div", { class: "page-head" }, h("div", {}, h("div", { class: "muted" }, h("a", { href: "#/ask" }, "Ask"), " / question"),
        h("h1", {}, d.question), h("p", {}, `${d.answers.length} answers · an answer can go on the wiki only after a named person has read it against the law: record the reviewer on the answer's page, then tick “For the wiki” to publish it as its own Lexipedia sub-page at the next publish.`))),
      h("section", { class: "card" }, h("div", { class: "card-pad" }, sortableTable([
        { key: "name", label: "Place", render: (r) => h("a", { href: `#/answer/${encodeURIComponent(qid)}/${encodeURIComponent(r.target)}` }, r.name) },
        { key: "status", label: "Status", render: (r) => askStatus(r.status) },
        { key: "sections", label: "Sections", render: (r) => (r.sections || []).join(", ") || "–" },
        { key: "steps", label: "Steps", num: true }, { key: "quotes", label: "Quotes", num: true }, { key: "local", label: "Local", num: true },
        { key: "first_claim", label: "In short", render: (r) => r.first_claim || "–" },
        { key: "seconds", label: "Seconds", num: true },
        { key: "reviewed_by", label: "Reviewed by", sort: (r) => (r.reviewed_by || {}).name, render: (r) => r.reviewed_by ? `${r.reviewed_by.name}, ${r.reviewed_by.role}` : "–" },
        { key: "published", label: "For the wiki", render: publish }], d.answers))));
  }
  rc(view, body);
  onRefresh(load);
  await load();
}

async function viewAnswer(qid, target) {
  const r = await api(`/api/ask/${encodeURIComponent(qid)}/${encodeURIComponent(target)}`);
  // the people the operator has put on the reviewer list (lexflow reviewer add): the only reviewers a page can name
  const people = await api("/api/reviewers").catch(() => []);
  const a = r.answer || {};
  const sec = r.sections || {};
  const local = r.local || {};
  const metrics = r.metrics || {};
  const place = local.name || (S.meta.states.find((s) => s.state === r.state) || {}).name || r.state;
  const quotes = a.quotes || [];
  const qById = Object.fromEntries(quotes.map((q) => [q.id, q]));
  const claims = (a.summary || {}).claims || [];
  const bpmnHost = h("div", { class: "bpmn-host" });
  const card = (title, sub, ...kids) => [h("div", { class: "spacer" }), h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, title), sub ? h("p", {}, sub) : null)), ...kids)];
  rc(view,
    h("div", { class: "page-head" }, h("div", {},
      h("div", { class: "muted" }, h("a", { href: "#/ask" }, "Ask"), " / ", h("a", { href: `#/asked/${encodeURIComponent(qid)}` }, "question"), ` / ${place}`),
      h("h1", {}, r.question_text), h("p", {}, `${place} · ${r.model ? `summary by ${r.model} · ` : ""}${fx(r.seconds, 0)} s · ${ago(r.updated_at)}`)),
      h("div", { class: "row-flex" }, askStatus(r.status))),
    ...reviewCard(qid, target, r, card, people),
    r.status === "not_found" ? h("div", { class: "notice" }, icon("info"), h("div", {}, "No statute section clearly governs this here. The answer may live in regulations, court rules, agency policy, contracts or local ordinances, which lexflow does not search yet. The closest sections are listed below.")) : null,
    ...(claims.length ? card("In short", "Written by a local model from the quotes below. Claims that cited no quote, or stated a number the quotes do not contain, were dropped.",
      h("ul", { class: "card-pad", style: "margin:0;padding-left:36px" }, claims.map((c) => h("li", {}, c.text, " ",
        ...c.quotes.map((id) => h("a", { href: `#q-${id}`, class: "badge", title: qById[id]?.text || "", style: "margin-left:4px" }, id)))))) : []),
    ...((sec.chosen || []).length ? card("Governing law", `Chosen from ${(sec.candidates || []).length} candidates by full-text search and meaning.`,
      h("ul", { class: "card-pad", style: "margin:0;padding-left:36px" }, sec.chosen.map((s) => h("li", {}, s.url ? h("a", { href: s.url, target: "_blank", rel: "noopener" }, s.citation) : s.citation,
        ` — ${s.title}`, s.version ? h("span", { class: "tag", style: "margin-left:6px" }, s.version) : null)))) : []),
    ...((a.steps || []).length ? card("Steps", "Picked by the learned selector; each step is the law's own words.",
      h("ol", { class: "steps-list" }, a.steps.map((s) => h("li", {}, h("div", { class: "row-flex" }, h("strong", {}, s.action), h("span", { class: "muted" }, `· ${s.actor}`),
        s.deadline ? h("span", { class: "badge" }, `within ${s.deadline}`) : null, h("span", { class: "right muted mono" }, `§ ${s.section}${s.label ? `(${s.label.split(".").join(")(")})` : ""}`)),
        h("p", { class: "quote" }, `“${s.quote}”`))))) : []),
    ...(r.bpmn ? card("Process map", "Drafted from the steps above; not reviewed.", bpmnHost) : []),
    ...(quotes.length ? card("Key provisions", "The clauses that best answer the question, word for word.",
      h("ol", { class: "steps-list" }, quotes.map((q) => h("li", { id: `q-${q.id}` }, h("div", { class: "row-flex" }, h("strong", {}, q.id),
        h("span", { class: "muted mono" }, `§ ${q.section || ""}${q.label ? `(${q.label.split(".").join(")(")})` : ""}`),
        ...(q.slots || []).map((s) => h("span", { class: "tag" }, s))), h("p", { class: "quote" }, `“${q.text}”`))))) : []),
    ...((local.locus || []).length || (local.contacts || []).length ? card(`What ${local.name || "the place"} adds`, "Local ordinance headings from LOCUS-v1 (LocalLaws' Local Ordinance Corpus for the United States) that mention the question, and contacts. LOCUS points at local law; read the ordinance itself before relying on it.",
      h("div", { class: "card-pad" },
        (local.locus || []).length ? h("ul", { style: "margin:0 0 10px;padding-left:20px" }, local.locus.map((x) => h("li", {}, x.header, h("span", { class: "muted" }, ` · ${x.function || ""} ${x.topic ? `· ${x.topic}` : ""}`)))) : null,
        (local.contacts || []).length ? h("ul", { style: "margin:0;padding-left:20px" }, local.contacts.map((c) => h("li", {}, `${c.kind}: `,
          /^https?:/.test(c.value) ? h("a", { href: c.value, target: "_blank", rel: "noopener" }, c.value) : c.value))) : null,
        (local.web || []).length ? h("ul", { style: "margin:10px 0 0;padding-left:20px" }, local.web.map((w) => h("li", {},
          h("a", { href: w.url, target: "_blank", rel: "noopener" }, w.title || w.url), w.snippet ? h("span", { class: "muted" }, ` — ${w.snippet}`) : null))) : null)) : []),
    ...((a.cases || []).length ? card("Court decisions citing these sections", "From CourtListener (Free Law Project); listed for research, not every citing case construes the section.",
      h("ul", { class: "card-pad", style: "margin:0;padding-left:36px" }, a.cases.map((c) => h("li", {},
        h("a", { href: c.url, target: "_blank", rel: "noopener" }, c.case_name || "Opinion"), ` (${c.court || ""}, ${(c.date_filed || "").slice(0, 4)}) — § ${c.section}`)))) : []),
    ...card("How it was found", `Concepts searched: ${(metrics.plan || []).map((g) => g.slice(0, 4).join(" / ")).join("  +  ")}`,
      h("div", { class: "card-pad" }, sortableTable([
        { key: "citation", label: "Section", render: (s) => s.url ? h("a", { href: s.url, target: "_blank", rel: "noopener" }, s.citation) : s.citation },
        { key: "title", label: "Heading" }, { key: "rank_score", label: "Score", num: true }, { key: "similarity", label: "Meaning", num: true },
        { key: "words", label: "Words", num: true }], sec.candidates || [], { initial: "rank_score" }),
        h("p", { class: "muted", style: "margin-top:8px" }, Object.entries(metrics.timings || {}).map(([k, v]) => `${k} ${v} s`).join(" · ")))));
  if (r.bpmn && window.BpmnJS) {
    const viewer = new BpmnJS({ container: bpmnHost });
    try { await viewer.importXML(r.bpmn); viewer.get("canvas").zoom("fit-viewport", "auto"); }
    catch (e) { rc(bpmnHost, h("p", { class: "card-pad muted" }, `Could not draw the diagram: ${e.message}`)); }
  }
}

// The person who read an answer against the law.  Reviewers come from the list the operator keeps (lexflow reviewer
// add): the operator vouches that each one is a person, and lexflow cannot check it.  Here one is picked from that
// list, never typed in; the page prints the name, role and licence the list gives.  The reviewer ticks that they
// read this exact text, and the review is for the text on screen (its text_hash).
function reviewCard(qid, target, r, card, people) {
  const url = `/api/ask/${encodeURIComponent(qid)}/${encodeURIComponent(target)}/review`;
  const rv = r.reviewed_by || {};
  const msg = h("div", { style: "margin-top:8px" });
  const pick = h("select", { "aria-label": "Reviewer from the operator's list" }, h("option", { value: "" }, "Choose a reviewer from the list"),
    ...(people || []).map((p) => h("option", { value: p.id, selected: rv.reviewer === p.id }, p.label)));
  const attest = h("input", { type: "checkbox", "aria-label": "I am a person and I read this exact text against the law" });
  // the reviewer's own token (lexflow reviewer add printed it): the API records or removes a review only with it,
  // and keeps whose token was used.  It is sent with the request and never stored in the browser.
  const token = h("input", { type: "password", autocomplete: "off", spellcheck: "false", "aria-label": "Your reviewer token" });
  const withToken = (method, body) => api(url, { method, body: body ? JSON.stringify(body) : undefined,
    headers: { "Content-Type": "application/json", "X-Lexflow-Reviewer-Token": token.value.trim() } });
  const save = h("button", { class: "btn primary", disabled: !(people || []).length, onclick: async () => {
    try {
      // only the reviewer's id, their statement and the hash of the text on this page: the API refuses a typed
      // name, role or date, and an answer that changed since it was loaded
      await withToken("PUT", { reviewer: pick.value || null, attested: attest.checked, text_hash: r.text_hash || null });
      viewAnswer(qid, target);
    } catch (e) { rc(msg, h("div", { class: "notice" }, icon("info"), h("div", {}, String(e.message || e)))); }
  } }, r.reviewed_by ? "Update reviewer" : "Record reviewer");
  const remove = r.reviewed_by ? h("button", { class: "btn", onclick: async () => {
    try { await withToken("DELETE"); viewAnswer(qid, target); }
    catch (e) { rc(msg, h("div", { class: "notice" }, icon("info"), h("div", {}, String(e.message || e)))); }
  } }, "Remove reviewer") : null;
  const empty = (people || []).length ? null : h("p", { class: "muted" }, "No one is on the reviewer list yet. The operator adds reviewers with “lexflow reviewer add”, and vouches for each one: lexflow cannot check that a reviewer is a person.");
  return card("Human review", r.reviewed_by ? `${r.review_line}. The wiki page will say so.`
    : (r.review_stale ? "The review on record was for another version of this answer, or by someone no longer on the reviewer list, so it no longer counts. " : "")
      + "Not yet reviewed by a person. Pick the person on the operator's reviewer list who read this answer against the law; until then it cannot go on the wiki.",
  h("div", { class: "card-pad" },
    empty,
    h("div", { class: "row-flex", style: "gap:12px;flex-wrap:wrap" }, h("label", { class: "field" }, "Reviewer", pick),
      h("label", { class: "field" }, "Your reviewer token", token)),
    h("p", { class: "muted" }, "Only the reviewer's own token records a review: the operator's “lexflow reviewer add” printed it, and “lexflow reviewer token” makes a new one."),
    h("label", { class: "check", style: "margin-top:10px" }, attest, "I am a person, and I read this exact text against the law"),
    h("div", { class: "row-flex", style: "margin-top:10px;gap:8px" }, save, remove), msg));
}

// AskBench: new questions answered by the local pipeline, scored against Claude's references
function askBenchCard(ab) {
  const arms = Object.entries(ab.summary || {});
  const label = { local: "Local pipeline (search + quotes + steps)", heuristic: "Local, hand-set reranker only",
    profile: "Local answering, Claude's search concepts", oracle: "Same answering, Claude's sections given",
    "local+llmplan": "Local pipeline, local model plans the search", "local+llm": "Local pipeline + local model summary",
    "oracle+llm": "Claude's sections + local model summary" };
  const cols = [["cases", "Cases"], ["composite", "Composite"], ["recall@10", "Gold sections in top 10"], ["vital_recall", "Vital points quoted"],
    ["claim_vital_recall", "Vital points in the summary"], ["citation_precision", "Quotes from gold sections"],
    ["slot_match", "Fees and deadlines"], ["steps_equivalence", "Steps (process questions)"], ["gate_correct", "Answer / not found right"]];
  return [h("div", { class: "spacer" }), h("section", { class: "card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "New questions (AskBench)"),
      h("p", {}, `${ab.cases} reference answers by Claude for six questions on prisons and court debt (VA, DC, MD, TX, CA); every number below compares the local answer with Claude's. lexflow ask-bench to rerun.`))),
    h("div", { class: "card-pad table-wrap" }, h("table", { class: "data" },
      h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Arm"), cols.map(([, l]) => h("th", { scope: "col", class: "num" }, l)))),
      h("tbody", {}, arms.map(([arm, s]) => h("tr", {}, h("td", {}, label[arm] || arm), cols.map(([k]) => h("td", { class: "num" }, s[k] == null ? "–" : k === "cases" ? String(s[k]) : fx(s[k])))))))))];
}

// ============================================================== BENCHMARK
async function viewBenchmark() {
  const body = h("div");
  rc(view, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Local models vs Claude"),
    h("p", {}, "Each strategy turns statute text into process facts on this machine: the stack_* strategies use the learned selector, trained on Claude's references for the other states (a state never trains on itself); the others ask a small local model. Equivalence compares the result with Claude's checked model of the same text (0.5 × step F1 + 0.2 × actors + 0.2 × deadlines + 0.1 × duty type). A run whose quotes are not word for word scores 0."))), body);
  async function load() {
    const d = await api("/api/benchmark");
    if (!d.rows.length) {
      rc(body, h("div", { class: "notice" }, icon("info"), h("div", {}, "No benchmark runs yet. Start one with ",
        h("code", {}, "lexflow run benchmark"), " or the button below."), h("button", { class: "btn right", onclick: async () => { await startRunJob("benchmark", {}); location.hash = "#/jobs"; } }, "Run the benchmark")));
      return;
    }
    const key = (r) => `${r.strategy}${r.model && r.model !== "-" ? ` · ${r.model}` : ""}`;
    const groups = {};
    for (const r of d.rows) (groups[key(r)] ||= []).push(r);
    const means = Object.entries(groups).map(([k, rs]) => ({ k, mean: rs.reduce((a, r) => a + (r.equivalence || 0), 0) / d.cases.length,
      covered: rs.length, secs: rs.reduce((a, r) => a + (r.seconds || 0), 0) / rs.length }))
      .sort((a, b) => b.mean - a.mean);
    const max = 1, barW = 360;
    // the realistic target is how far two Claude drafts agree; perfect selection bounds the selector strategies
    const ceiling = d.ceiling?.claude_vs_claude?.mean ?? d.target;
    const perfect = d.ceiling?.oracle?.wide;
    const mark = (v, dashed) => h("span", { style: `position:absolute;left:${v * 100}%;top:-3px;bottom:-3px;border-left:1px ${dashed ? "dashed" : "solid"} var(--ink-2)` });
    const bars = h("div", { class: "funnel" }, means.map((m) => h("div", { class: "funnel-row", style: "grid-template-columns: 260px minmax(0,1fr) 60px", title: `${m.k}: mean ${fx(m.mean)} over ${d.cases.length} cases (${m.covered} run)` },
      h("span", { class: "lab mono", style: "font-size:12px" }, m.k),
      h("span", { class: "track" }, h("span", { class: "fill", style: `width:${(m.mean / max) * 100}%` }),
        mark(ceiling, false), perfect != null ? mark(perfect, true) : null),
      h("span", { class: "num", style: "text-align:right" }, fx(m.mean)))));
    const curve = d.learning_curve?.curve || [];
    const seq = (v) => { const bins = [0.35, 0.5, 0.65, 0.75]; let i = 0; while (i < bins.length && v >= bins[i]) i++; return [css(`--seq-${i + 1}`), i >= 2]; };
    const dark = () => (document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
    const heat = h("table", { class: "data" },
      h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Strategy · model"), d.cases.map((c) => h("th", { scope: "col", class: "num" }, c)))),
      h("tbody", {}, means.map((m) => h("tr", {}, h("td", { class: "mono", style: "font-size:12px" }, m.k), d.cases.map((c) => {
        const r = groups[m.k].find((x) => x.case === c);
        if (!r) return h("td", { class: "num muted" }, "–");
        const [bg, deep] = seq(r.equivalence || 0);
        const ink = deep !== dark() ? "#ffffff" : "#0b0b0b";
        return h("td", { class: "num", style: `background:${bg};color:${ink};border:2px solid var(--surface)`,
          title: `${c} ${m.k}: equivalence ${fx(r.equivalence)}; steps ${r.steps} vs ${r.gold_steps}; F1 ${fx(r.step_f1)}; deadlines ${fx(r.deadlines)}; ${Math.round(r.seconds)} s, ${r.calls} calls${r.problems?.length ? `; ${r.problems[0]}` : ""}` },
          fx(r.equivalence));
      })))));
    rc(body,
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Mean equivalence by strategy"),
        h("p", {}, `Averaged over ${d.cases.length} cases (a case not run counts 0). ${d.ceiling ? `The solid line is how far two independent Claude drafts agree (${fx(ceiling)}), the realistic target; the dashed line is what perfect sentence selection would score (${fx(perfect)}).` : `The line marks the ${fx(d.target)} target.`} ${fmtInt(d.runs)} runs so far.`))), bars,
        curve.length ? h("p", { class: "muted", style: "margin:12px 16px 16px" }, `More references, better selector (${d.learning_curve.vectors}): `
          + curve.map((p) => `${p.training_states} states ${fx(p.mean)}`).join(" · ")) : null),
      h("div", { class: "spacer" }),
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "By case"),
        h("p", {}, "Darker is closer to Claude. Hover a cell for steps, F1, deadlines, time and any quote problem."))),
        h("div", { class: "card-pad table-wrap" }, heat),
        h("div", { class: "legend" }, h("span", { class: "title" }, "Equivalence"),
          ...["under 0.35", "0.35–0.50", "0.50–0.65", "0.65–0.75", "0.75 and up"].map((l, i) => h("span", {}, h("span", { class: "sw", style: `background:var(--seq-${i + 1})` }), l)))),
      d.askbench ? askBenchCard(d.askbench) : null,
      h("div", { class: "row-flex", style: "margin-top:16px" },
        h("button", { class: "btn", onclick: async () => { await startRunJob("benchmark", {}); location.hash = "#/jobs"; } }, "Run the full benchmark")));
  }
  onRefresh(load);
  await load();
}

// ================================================================= PLACES
async function viewPlaces() {
  const results = h("div", { class: "model-grid" });
  const researched = h("div", { class: "model-grid" });
  const q = h("input", { type: "search", placeholder: "Search a county, city or town", "aria-label": "Search governments", style: "min-width:280px" });
  const spec = h("input", { type: "text", value: store("lexflow-place-spec") || "va:charlottesville,dc,md:baltimore", "aria-label": "Places", style: "min-width:300px" });
  const card = (g) => h("a", { class: "card model-card", href: `#/place/${g.gov_id}` },
    h("div", { class: "top" }, h("strong", {}, g.name), h("span", { class: "muted" }, (g.state || "").toUpperCase())),
    h("div", { class: "cite" }, `${g.kind}${g.population ? ` · pop. ${fmtInt(g.population)}` : ""}`),
    g.researched ? h("div", { class: "row-flex" }, statusEl(g.verified ? "done" : "partial", g.verified ? "Local answers checked" : "Local answers, not yet checked")) : null,
    g.processes ? h("div", { class: "row-flex" }, statusEl(g.processes_verified === g.processes ? "done" : "partial",
      `${g.processes} local ${g.processes === 1 ? "process" : "processes"}, ${g.processes_verified} checked`)) : null);
  let timer = null;
  q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      if (q.value.trim().length < 3) { rc(results); return; }
      const rows = await api(`/api/search?q=${encodeURIComponent(q.value.trim())}`);
      rc(results, rows.length ? rows.map(card) : h("p", { class: "muted" }, "No match."));
    }, 250);
  });
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Places"),
      h("p", {}, "Answers for one government at a time: the state law steps, the local procedure, who to contact and the local law, each with its source. Use this to test a few places before running whole states."))),
    h("section", { class: "card card-pad", style: "margin-bottom:16px" },
      h("div", { class: "row-flex" },
        h("div", {}, h("h2", {}, "Answer some places"), h("p", { class: "ink-2", style: "margin:2px 0 0" }, "Runs the pipeline for just these governments: statutes, law, contacts, website scan, local answers, models and scores. Format: va:charlottesville, dc, md:baltimore, md:baltimore county.")),
        h("div", { class: "right row-flex" }, spec,
          h("button", { class: "btn primary", onclick: async (e) => {
            store("lexflow-place-spec", spec.value);
            e.target.disabled = true;
            await startRunJob("quickstart", { places: spec.value });
            location.hash = "#/jobs";
          } }, "Run")))),
    h("div", { class: "filters" }, q), results, h("div", { class: "spacer" }),
    h("h2", { style: "margin:8px 0 12px" }, "Researched places"), researched);
  const load = async () => {
    const rows = await api("/api/places");
    rc(researched, rows.length ? rows.map(card) : h("p", { class: "muted" }, "None yet. Research files go in curated/places/<state>/<place>.json; load them with the “Load checked local answers” step."));
  };
  onRefresh(load);
  await load();
}

async function viewPlace(govId) {
  const d = await api(`/api/answers/${encodeURIComponent(govId)}`);
  const g = d.government;
  const cards = Object.entries(S.meta.questions).map(([qid, q]) => {
    const a = d.answers[qid];
    if (!a) return h("section", { class: "card card-pad" }, h("h2", {}, q.title), h("p", { class: "muted" }, "Not scored yet."));
    const loc = a.local || {};
    const law = a.law || {};
    const contacts = [...(loc.contacts || []).map((c) => ({ ...c, src: "local" })),
      ...d.contacts.filter((c) => c.question === qid || c.question === "general")
        .filter((c) => !(loc.contacts || []).some((x) => x.value === c.value))];
    const link = (c) => c.kind === "email" ? h("a", { href: `mailto:${c.value}` }, c.value)
      : /^https?:/.test(c.value) ? h("a", { href: c.value, target: "_blank", rel: "noopener" }, c.label || c.value)
        : `${c.label ? c.label + ": " : ""}${c.value}`;
    const parts = [a.state_score, a.local_score, a.contact_score];
    return h("section", { class: "card" },
      h("div", { class: "card-head" }, h("div", {}, h("h2", {}, `${q.title.replace(/\?$/, "")} in ${g.name}?`),
        h("p", {}, `Confidence ${fx(a.confidence)} · state law ${fx(parts[0])} · local ${fx(parts[1])} · contact ${fx(parts[2])}`)),
        tierBadge(a.tier)),
      h("div", { class: "card-pad" },
        h("div", { class: "meter", style: "margin:0 0 12px" }, h("span", { style: `width:${Math.round((a.confidence || 0) * 100)}%` })),
        loc.summary ? h("p", { style: "margin:0 0 12px;font-size:14.5px" }, loc.summary)
          : h("p", { class: "muted", style: "margin:0 0 12px" }, "No researched local answer yet; the steps below come from state law."),
        a.steps?.length ? h("div", {}, h("h3", {}, "What state law says", law.citation ? h("span", { class: "muted", style: "font-weight:400" }, ` · ${law.citation}`) : null),
          h("ol", { class: "steps-list", style: "padding-left:20px" }, a.steps.map((s) => h("li", {},
            h("div", { class: "row-flex" }, h("strong", {}, s.step), h("span", { class: "muted" }, `· ${s.who}`), s.deadline ? h("span", { class: "badge" }, `within ${s.deadline}`) : null,
              h("span", { class: "right muted mono" }, s.cite)),
            s.quote ? h("details", {}, h("summary", { class: "muted", style: "font-size:12px;cursor:pointer" }, "The words of the law"), h("p", { class: "quote" }, `“${s.quote}”`)) : null))),
          a.model ? h("p", { style: "margin:4px 0 12px" }, h("a", { href: `#/model/${a.model.model_id}` }, "Open the process map →")) : null) : null,
        (a.decisions || []).filter((t) => t.id === "business_structure" || a.question === "records").map((t) => h("div", { style: "margin-bottom:12px" },
          h("h3", {}, t.question), decisionTable({ ...t, inputs: t.inputs, outputs: t.outputs, rules: t.rules.map((r) => ({ ...r, when: r.when, then: r.then })) }))),
        loc.steps?.length ? h("div", {}, h("h3", {}, `What ${g.name} adds`),
          h("ol", { class: "steps-list", style: "padding-left:20px" }, loc.steps.map((s) => h("li", {},
            h("div", {}, h("strong", {}, s.step), s.who ? h("span", { class: "muted" }, ` · ${s.who}`) : null),
            s.how ? h("div", { class: "ink-2" }, s.how) : null,
            s.url ? h("div", { style: "font-size:12px" }, h("a", { href: s.url, target: "_blank", rel: "noopener" }, "Source"), s.quote ? h("span", { class: "muted" }, ` · “${s.quote}”`) : null) : null)))) : null,
        contacts.length ? h("div", {}, h("h3", {}, "Who to contact"), h("ul", { class: "contacts", style: "padding-left:18px;list-style:disc" }, contacts.slice(0, 8).map((c) => h("li", {}, link(c))))) : null,
        (loc.local_law?.length || a.locus?.length) ? h("div", { style: "margin-top:10px" }, h("h3", {}, "Local law"),
          h("ul", { style: "padding-left:18px;margin:4px 0" }, [...(loc.local_law || []).map((l) => h("li", {}, l.url ? h("a", { href: l.url, target: "_blank", rel: "noopener" }, l.citation) : l.citation, ` — ${l.summary}`)),
            ...(a.locus || []).slice(0, 4).map((l) => h("li", { class: "muted" }, `${l.header} (LOCUS, for finding only)`))])) : null,
        loc.fees ? h("p", {}, h("strong", {}, "Fees: "), loc.fees) : null,
        (loc.caveats || []).length || (a.gaps || []).length ? h("details", { style: "margin-top:8px" }, h("summary", { style: "cursor:pointer" }, "Caveats and gaps"),
          h("ul", { style: "padding-left:18px" }, [...(loc.caveats || []), ...(a.gaps || [])].map((x) => h("li", { class: "ink-2" }, x)))) : null,
        loc.researched ? h("p", { class: "muted", style: "font-size:12px;margin-top:10px" },
          `Local answer researched ${loc.researched} by ${loc.built_by || "Claude"}${loc.verified ? "; sources re-checked by an AI verifier (not a person)" : ""}.`) : null));
  });
  rc(view,
    h("div", { class: "page-head" }, h("div", {},
      h("div", { class: "muted" }, h("a", { href: "#/places" }, "Places"), ` / ${(g.state || "").toUpperCase()}`),
      h("h1", {}, g.name),
      h("p", {}, `${g.kind}${g.population ? ` · population ${fmtInt(g.population)}` : ""}${g.county_name ? ` · ${g.county_name}` : ""}`)),
      g.website ? h("a", { class: "btn", href: g.website, target: "_blank", rel: "noopener" }, "Official website ↗") : null),
    h("div", { class: "grid", style: "gap:16px" }, cards),
    localProcessesCard(govId, await api(`/api/places/${encodeURIComponent(govId)}/processes`).catch(() => [])));
}

// the place's researched processes (curated/places/<state>/<place>/<process>.json), grouped by category
const CATEGORY_TITLE = { records: "Public records", business: "Business", permits_construction: "Building and construction permits",
  zoning_land_use: "Zoning and land use", taxes_assessments: "Taxes and assessments", tax_relief: "Tax relief",
  utilities_services: "Utilities and services", public_safety: "Public safety", courts_legal: "Courts and legal", elections: "Elections",
  health_social_services: "Health and social services", transportation_parking: "Transportation and parking", parks_events: "Parks and events",
  animals: "Animals", housing: "Housing", other: "Other" };
function localProcessesCard(govId, procs) {
  if (!procs || !procs.length) return null;
  const cats = [...new Set(procs.map((p) => p.category || "other"))];
  return [h("div", { class: "spacer" }), h("section", { class: "card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Local processes"),
      h("p", {}, `${procs.length} researched from the official pages and the law they rest on; ${procs.filter((p) => p.verified).length} checked quote by quote by an AI verifier (not a person; lexflow's software matches only their quotes from the state code).`))),
    h("div", { class: "card-pad" }, cats.map((cat) => h("div", { style: "margin-bottom:12px" },
      h("h3", {}, CATEGORY_TITLE[cat] || cat),
      h("ul", { style: "padding-left:18px;margin:4px 0" }, procs.filter((p) => (p.category || "other") === cat).map((p) => h("li", {},
        h("a", { href: `#/local/${encodeURIComponent(govId)}/${encodeURIComponent(p.process)}` }, p.title || p.process),
        p.office ? h("span", { class: "muted" }, ` · ${p.office}`) : null,
        p.verified ? null : h("span", { class: "badge", style: "margin-left:6px" }, "not yet checked"))))))))];
}

async function viewLocalProcess(govId, pid) {
  const r = await api(`/api/places/${encodeURIComponent(govId)}/processes/${encodeURIComponent(pid)}`);
  const s = r.spec || {};
  const g = r.government || {};
  const link = (url, text) => url && /^https?:/.test(url) ? h("a", { href: url, target: "_blank", rel: "noopener" }, text) : text;
  const quote = (q) => q ? h("p", { class: "quote" }, `“${q}”`) : null;
  const forms = Object.fromEntries((s.forms || []).map((f) => [f.id, f]));
  const card = (title, ...kids) => [h("div", { class: "spacer" }), h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, title))), h("div", { class: "card-pad" }, ...kids))];
  const c = s.checks || {};
  rc(view,
    h("div", { class: "page-head" }, h("div", {},
      h("div", { class: "muted" }, h("a", { href: "#/places" }, "Places"), " / ", h("a", { href: `#/place/${encodeURIComponent(govId)}` }, g.name || govId)),
      h("h1", {}, s.title || pid),
      s.question ? h("p", {}, s.question) : null,
      h("p", { class: "muted" }, [s.office, CATEGORY_TITLE[s.category] || s.category, r.verified ? "checked quote by quote by an AI verifier, not a person" : "not yet checked"].filter(Boolean).join(" · ")))),
    h("div", { class: "notice" }, icon("info"), h("div", {}, "Researched by lexflow from the official pages and the law they rest on. Procedures, fees and forms change: follow the links to the office before you act. Information, not legal advice.")),
    s.summary ? card("In short", h("p", {}, s.summary)) : null,
    (s.steps || []).length ? card("Steps", h("ol", { class: "steps-list", style: "padding-left:20px" }, s.steps.map((st) => h("li", {},
      h("div", { class: "row-flex" }, h("strong", {}, st.step), st.who ? h("span", { class: "muted" }, `· ${st.who}`) : null,
        st.deadline ? h("span", { class: "badge" }, st.deadline) : null, st.fee ? h("span", { class: "badge" }, st.fee) : null),
      st.how ? h("div", { class: "ink-2" }, st.how) : null,
      st.form && forms[st.form] ? h("div", { style: "font-size:12.5px" }, "Form: ", link(forms[st.form].url, forms[st.form].title || st.form)) : null,
      st.quote ? h("details", {}, h("summary", { class: "muted", style: "font-size:12px;cursor:pointer" }, st.source ? `The words of ${st.source.startsWith("http") ? "the source" : st.source}` : "The words of the source"), quote(st.quote)) : null,
      st.url ? h("div", { style: "font-size:12px" }, link(st.url, "Official page")) : null)))) : null,
    (s.legal_basis || []).length ? card("The law", h("ul", { style: "padding-left:18px" }, s.legal_basis.map((x) => h("li", {},
      link(x.url, x.citation || "source"), x.role ? h("span", { class: "muted" }, ` · ${x.role}`) : null, quote(x.quote))))) : null,
    (s.forms || []).length ? card("Forms", h("ul", { style: "padding-left:18px" }, s.forms.map((f) => h("li", {}, link(f.url, f.title || f.id), f.number ? h("span", { class: "muted" }, ` (${f.number})`) : null)))) : null,
    (s.fees || []).length ? card("Fees", h("ul", { style: "padding-left:18px" }, s.fees.map((f) => h("li", {}, `${f.item}: ${f.amount}`, f.basis ? h("span", { class: "muted" }, " · ", link(f.basis, /^https?:/.test(f.basis) ? "basis" : f.basis)) : null)))) : null,
    (s.contacts || []).length ? card("Who to contact", h("ul", { style: "padding-left:18px" }, s.contacts.map((x) => h("li", {},
      x.kind === "email" ? h("a", { href: `mailto:${x.value}` }, x.value) : /^https?:/.test(x.value || "") ? link(x.value, x.label || x.value) : `${x.label ? x.label + ": " : ""}${x.value}`)))) : null,
    (s.escalation || []).length ? card("If it goes wrong", h("ul", { style: "padding-left:18px" }, s.escalation.map((e) => h("li", {},
      h("strong", {}, e.trigger), `: ${e.next}`, e.type ? h("span", { class: "muted" }, ` (${e.type})`) : null, e.deadline ? `, within ${e.deadline}` : "",
      e.basis ? h("span", { class: "muted" }, ` · ${e.basis}`) : null, quote(e.quote))))) : null,
    (s.caveats || []).length ? card("Caveats", h("ul", { style: "padding-left:18px" }, s.caveats.map((x) => h("li", { class: "ink-2" }, x)))) : null,
    (s.sources || []).length ? card("Sources", h("ul", { style: "padding-left:18px" }, s.sources.map((x) => h("li", {}, link(x.url, x.title || x.url), x.retrieved ? h("span", { class: "muted" }, ` · retrieved ${x.retrieved}`) : null)))) : null,
    c.verified_by ? h("p", { class: "muted", style: "font-size:12px;margin-top:10px" },
      `Checked by ${c.verified_by}${c.date ? " on " + c.date : ""}: ${c.quotes_confirmed ?? "?"} of ${c.quotes_checked ?? "?"} quotes confirmed${(c.open_issues || []).length ? `; open issues: ${c.open_issues.join("; ")}` : ""}.`) : null);
}

// ================================================================== DATA
async function viewData() {
  const body = h("div");
  rc(view, 
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Data & sync"),
      h("p", {}, "Your results live in a local SQLite file. Point lexflow at a shared Turso database to push what you build and pull what others have built — by state, so a new machine only downloads what it needs."))),
    body);
  async function load() {
    const s = await api("/api/sync");
    const statesInput = h("input", { type: "text", placeholder: "all, or va,dc", "aria-label": "States to sync", value: store("lexflow-sync-states") || "" });
    const full = h("input", { type: "checkbox" });
    const go = (direction) => async () => {
      store("lexflow-sync-states", statesInput.value);
      await startRunJob("sync", { direction, states: statesInput.value || undefined, full: full.checked });
      location.hash = "#/jobs";
    };
    const auto = h("input", { type: "checkbox", checked: !!s.settings.auto_pull, onchange: async (e) => { await put("/api/settings", { auto_pull: e.target.checked }); } });
    const tables = Object.keys(s.local).map((t) => ({ table: t, local: s.local[t], remote: s.remote ? s.remote[t] : null }));
    const remoteStates = Object.entries(s.remote_states || {}).map(([st, v]) => ({ state: st, name: (S.meta.states.find((x) => x.state === st) || {}).name || st, ...v }));
    rc(body, 
      !s.configured ? h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Sharing is off. "),
        "Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env (Turso cloud), or start the bundled libSQL server with ",
        h("code", {}, "docker compose --profile shared up -d"), " and set TURSO_DATABASE_URL=http://libsql:8080. Then restart the app.")) : null,
      s.error ? h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Turso error: "), s.error)) : null,
      h("div", { class: "grid two" },
        h("section", { class: "card card-pad" },
          h("h2", {}, "Shared database"),
          h("dl", { class: "kv", style: "margin-top:10px" },
            h("dt", {}, "URL"), h("dd", { class: "mono" }, s.url || "not set"),
            h("dt", {}, "This machine"), h("dd", {}, s.origin),
            h("dt", {}, "Status"), h("dd", {}, s.configured ? statusEl(s.error ? "failed" : "done", s.error ? "Not reachable" : "Connected") : statusEl("optional", "Not configured"))),
          h("div", { class: "row-flex", style: "margin-top:14px" },
            h("label", { class: "field" }, "States", statesInput), h("label", { class: "check" }, full, "Full resend"),
            h("button", { class: "btn primary", disabled: !s.configured, onclick: go("push") }, "Push"),
            h("button", { class: "btn", disabled: !s.configured, onclick: go("pull") }, "Pull")),
          h("label", { class: "check", style: "margin-top:12px" }, auto, "Pull a state automatically the first time it is opened (pull as needed)")),
        h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Tables")),
          h("div", { class: "card-pad" }, sortableTable([{ key: "table", label: "Table" }, { key: "local", label: "Local rows", num: true, render: (r) => fmtInt(r.local) },
            { key: "remote", label: "Shared rows", num: true, render: (r) => (r.remote == null ? "–" : fmtInt(r.remote)) }], tables)))),
      h("div", { class: "spacer" }),
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "States in the shared database"), h("p", {}, "Pull one to load it here without running the pipeline."))),
        h("div", { class: "card-pad" }, remoteStates.length ? sortableTable([
          { key: "name", label: "State" }, { key: "governments", label: "Governments", num: true, render: (r) => fmtInt(r.governments) },
          { key: "answers", label: "Answers", num: true, render: (r) => fmtInt(r.answers) }, { key: "process_models", label: "Models", num: true, render: (r) => fmtInt(r.process_models) },
          { key: "pull", label: "", render: (r) => h("button", { class: "btn small", onclick: async (e) => { e.stopPropagation(); await startRunJob("sync", { direction: "pull", states: r.state }); location.hash = "#/jobs"; } }, "Pull") }],
          remoteStates, { initial: "governments" }) : h("p", { class: "muted" }, s.configured ? "Nothing shared yet. Push to add your states." : "Configure Turso to see shared states."))),
      s.contributors?.length ? h("div", { class: "spacer" }) : null,
      s.contributors?.length ? h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Who built the shared models")),
        h("div", { class: "card-pad" }, sortableTable([{ key: "origin", label: "Machine" }, { key: "n", label: "Models", num: true }, { key: "last", label: "Last change", render: (r) => ago(r.last) }], s.contributors))) : null,
      h("div", { class: "spacer" }),
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Sync history")),
        h("div", { class: "card-pad" }, s.log.length ? sortableTable([
          { key: "direction", label: "Direction" }, { key: "states", label: "States", render: (r) => (JSON.parse(r.states || "null") || ["all"]).join(", ") },
          { key: "rows", label: "Rows", num: true, render: (r) => fmtInt(r.rows) }, { key: "ok", label: "Result", render: (r) => statusEl(r.ok ? "done" : "failed", r.ok ? "OK" : r.message) },
          { key: "finished_at", label: "When", render: (r) => ago(r.finished_at) }], s.log) : h("p", { class: "muted" }, "No syncs yet."))));
  }
  onRefresh(load);
  await load();
}

// ================================================================== JOBS
async function viewJobs() {
  const body = h("section", { class: "card" });
  rc(view, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Jobs"), h("p", {}, "Each step runs in the background as its own process. Open one to read its log."))), body);
  async function load() {
    const jobs = await api("/api/jobs?limit=60");
    rc(body, h("div", { class: "card-pad" }, jobs.length ? sortableTable([
      { key: "id", label: "#", num: true },
      { key: "title", label: "Step" },
      { key: "args", label: "Options", render: (r) => Object.entries(r.args || {}).filter(([, v]) => v !== false && v !== "" && v != null).map(([k, v]) => (v === true ? k : `${k} ${v}`)).join(" · ") || "–" },
      { key: "status", label: "Status", render: (r) => statusEl(r.status) },
      { key: "progress", label: "Progress", render: (r) => mini(r.progress) },
      { key: "message", label: "Latest", render: (r) => h("span", { class: "ink-2", title: r.message || "" }, (r.message || "").slice(0, 90)) },
      { key: "started_at", label: "Took", render: (r) => dur(r.started_at, r.finished_at) },
    ], jobs, { initial: "id", onRow: (r) => { location.hash = `#/job/${r.id}`; } }) : h("p", { class: "muted" }, "No jobs yet. Start one from Setup.")));
  }
  onRefresh(load);
  await load();
}

async function viewJob(id) {
  const body = h("div");
  rc(view, body);
  let timer = null;
  async function load() {
    const j = await api(`/api/jobs/${id}?lines=400`);
    const pre = h("pre", { class: "log" }, j.log || "(no output yet)");
    rc(body, 
      h("div", { class: "page-head" }, h("div", {}, h("div", { class: "muted" }, h("a", { href: "#/jobs" }, "Jobs"), ` / #${j.id}`),
        h("h1", {}, (S.meta && j.step) ? j.step : "Job"), h("p", {}, j.message || "")),
        h("div", { class: "row-flex" }, statusEl(j.status), ["running", "queued"].includes(j.status) ? h("button", { class: "btn", onclick: async () => { await post(`/api/jobs/${id}/cancel`); load(); } }, "Cancel") : null)),
      h("section", { class: "card card-pad" }, h("div", { class: "meter", style: "margin:0 0 12px" }, h("span", { style: `width:${Math.round((j.progress || 0) * 100)}%` })), pre));
    pre.scrollTop = pre.scrollHeight;
    clearTimeout(timer);
    if (["running", "queued"].includes(j.status) && location.hash === `#/job/${id}`) timer = setTimeout(load, 2000);
  }
  await load();
}

// ================================================================= METHOD
async function viewMethod() {
  const r = await api("/api/method");
  const m = structuredClone(r.method);
  const body = h("div");
  rc(view, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Method"),
    h("p", {}, "How each answer's confidence is scored: confidence = w_state × state law + w_local × local law + w_contact × contact. Change a number and re-score; the maps follow."))), body);
  const num = (obj, key, step = 0.05) => h("input", { type: "number", min: 0, max: 1, step, value: obj[key], onchange: (e) => { obj[key] = Number(e.target.value); check(); } });
  const sums = {};
  function check() {
    for (const [q, w] of Object.entries(m.weights)) {
      const s = Object.values(w).reduce((a, b) => a + b, 0);
      rc(sums[q], statusEl(Math.abs(s - 1) < 0.011 ? "done" : "blocked", `adds up to ${s.toFixed(2)}`));
    }
  }
  const saveMsg = h("span", { class: "muted" });
  body.append(
    h("div", { class: "grid two" },
      ...Object.entries(m.weights).map(([q, w]) => {
        sums[q] = h("span");
        return h("section", { class: "card card-pad" }, h("h2", {}, S.meta.questions[q].title),
          h("dl", { class: "kv", style: "margin-top:10px;align-items:center" },
            h("dt", {}, "State law"), h("dd", {}, num(w, "state")), h("dt", {}, "Local law"), h("dd", {}, num(w, "local")),
            h("dt", {}, "Contact"), h("dd", {}, num(w, "contact")), h("dt", {}, ""), h("dd", {}, sums[q])));
      })),
    h("div", { class: "spacer" }),
    h("div", { class: "grid two" },
      h("section", { class: "card card-pad" }, h("h2", {}, "State law score by tier"),
        h("dl", { class: "kv", style: "margin-top:10px;align-items:center" }, [...r.tiers].reverse().flatMap((t) => [h("dt", {}, r.tier_label[t]), h("dd", {}, num(m.tier_score, t))])),
        h("p", { class: "muted", style: "font-size:12.5px" }, "“Law found” is also multiplied by the locator's score (1.0 for a verified known section, 0.4–0.8 for keyword matches).")),
      h("section", { class: "card card-pad" }, h("h2", {}, "Contact score by level"),
        h("dl", { class: "kv", style: "margin-top:10px;align-items:center" }, ["page", "direct", "website", "postal", "none"].flatMap((c) => [h("dt", {}, r.contact_label[c]), h("dd", {}, num(m.contact_score, c))])),
        h("dl", { class: "kv", style: "margin-top:14px;align-items:center" },
          h("dt", {}, "Local law found"), h("dd", {}, num(m, "local_found_score")),
          h("dt", {}, "Two models agree at"), h("dd", {}, num(m, "agreement_threshold"))))),
    h("div", { class: "row-flex", style: "margin-top:16px" },
      h("button", { class: "btn primary", onclick: async () => {
        try { await put("/api/method", m); saveMsg.textContent = "Saved. Re-score to update the maps."; } catch (e) { saveMsg.textContent = `Not saved: ${e.message}`; }
      } }, "Save"),
      h("button", { class: "btn", onclick: async () => { await startRunJob("score", { states: "all" }); location.hash = "#/jobs"; } }, "Re-score all states"),
      h("button", { class: "btn", onclick: async () => { await put("/api/method", r.defaults); viewMethod(); } }, "Reset to defaults"),
      saveMsg));
  check();
}

// -------------------------------------------------------------------- query
// SPARQL over the local Wikibase copy (data/wikibase/) or the live lexipedia.wikibase.cloud endpoint, through
// GET /api/sparql.  Canned queries come from lexflow/publish/sparql/*.rq (docs/design/wikibase-schema.md §6).
const ENTITY_BASE = "https://lexipedia.wikibase.cloud/entity/";
function shortIri(iri) {
  const bases = [["lx", ENTITY_BASE], ["lxt", "https://lexipedia.wikibase.cloud/prop/direct/"], ["lxp", "https://lexipedia.wikibase.cloud/prop/"],
    ["wd", "http://www.wikidata.org/entity/"], ["wikibase", "http://wikiba.se/ontology#"]];
  for (const [p, b] of bases) if (iri.startsWith(b) && /^[A-Za-z0-9_-]+$/.test(iri.slice(b.length))) return `${p}:${iri.slice(b.length)}`;
  return iri;
}
function wikiHref(iri) {
  const m = iri.startsWith(ENTITY_BASE) && iri.slice(ENTITY_BASE.length).match(/^([PQ])(\d+)$/);
  if (!m) return iri;
  if (Number(m[2]) >= 900) return null;                       // provisional id: nothing on the wiki yet
  return `https://lexipedia.wikibase.cloud/wiki/${m[1] === "P" ? "Property" : "Item"}:${m[1]}${m[2]}`;
}
function cellValue(b) {
  if (!b) return "";
  if (b.type === "uri") return shortIri(b.value);
  return b.value;
}
function cell(b) {
  if (!b) return h("span", { class: "muted" }, "–");
  if (b.type === "uri") {
    const href = wikiHref(b.value);
    const short = shortIri(b.value);
    return href ? h("a", { href, target: "_blank", rel: "noopener", title: b.value }, short) : h("span", { class: "mono", title: b.value }, short);
  }
  const v = b.value;
  const num = b.datatype && /#(integer|decimal|double|float|int|long)$/.test(b.datatype);
  return h("span", { class: num ? "num" : "", title: v.length > 60 ? v : null }, v.length > 200 ? `${v.slice(0, 200)}…` : v);
}
// ------------------------------------------------------------------ who do I ask
const PLAYED_KIND = { body: "a body", unit: "a unit of a body", court: "a court", "office type": "an office every locality has",
  post: "a post", "post type": "a post every body has", government: "a government", "private-party": "you, or a private party", unknown: "nobody recorded yet" };
function channelRow(c) {
  const link = c.kind === "website" || c.kind === "page" ? h("a", { href: c.value, target: "_blank", rel: "noopener" }, c.value)
    : c.kind === "email" ? h("a", { href: `mailto:${c.value}` }, c.value) : h("span", {}, c.value);
  const src = c.source ? (c.source.startsWith("http") ? h("a", { href: c.source, target: "_blank", rel: "noopener", class: "muted" }, "source") : h("span", { class: "muted" }, c.source)) : null;
  return h("li", { class: "chan" }, h("span", { class: "tag" }, c.kind), link, c.label ? h("span", { class: "muted" }, c.label) : null,
    src, c.retrieved ? h("span", { class: "muted" }, c.retrieved) : null);
}
function roleCard(r) {
  const pb = r.played_by || {};
  const links = pb.links || {};
  const quotes = (r.quotes || []).filter((q) => q.text);
  return h("section", { class: "card role-card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, r.label), h("p", {}, r.process ? r.process.label : ""))),
    h("div", { class: "card-pad role-body" },
      h("div", { class: "role-row" }, h("span", { class: "k" }, "Played by"),
        h("div", {}, h("strong", {}, pb.label || "–"), PLAYED_KIND[pb.kind] && PLAYED_KIND[pb.kind] !== pb.label ? h("span", { class: "muted" }, ` · ${PLAYED_KIND[pb.kind]}`) : null,
          pb.lexipedia ? h("a", { class: "muted", href: pb.lexipedia, target: "_blank", rel: "noopener", style: "margin-left:8px" }, "on Lexipedia") : null,
          pb.resolved_for ? h("div", { class: "muted", style: "font-size:12.5px" }, pb.office_type ? `the ${pb.office_type.label} of ${pb.resolved_for}` : `resolved to the office of ${pb.resolved_for}`) : null)),
      pb.chain && pb.chain.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Part of"),
        h("div", {}, pb.chain.map((c, i) => h("span", {}, i ? " › " : "", c.lexipedia ? h("a", { href: c.lexipedia, target: "_blank", rel: "noopener" }, c.label) : c.label)))) : null,
      pb.head ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Head"), h("div", {}, pb.head.label)) : null,
      pb.channels && pb.channels.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Reach them"),
        h("ul", { class: "chans" }, pb.channels.map(channelRow), pb.channels_more ? h("li", { class: "muted" }, `${pb.channels_more} more on the body's page`) : null)) : null,
      links.wikidata || links.govdirectory ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Elsewhere"),
        h("div", { class: "row-flex" }, links.wikidata ? h("a", { href: links.wikidata, target: "_blank", rel: "noopener" }, `Wikidata ${links.wikidata_qid}`) : null,
          links.govdirectory ? h("a", { href: links.govdirectory, target: "_blank", rel: "noopener" }, "Govdirectory") : null)) : null,
      quotes.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "The law says"),
        h("div", {}, quotes.map((q) => h("blockquote", { class: "quote" }, `“${q.text}”`,
          h("div", { class: "cite" }, q.url ? h("a", { href: q.url, target: "_blank", rel: "noopener" }, q.section) : q.section, q.pinpoint ? ` ${q.pinpoint}` : ""))))) : null,
      r.steps && r.steps.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Does"),
        h("ul", { class: "does" }, r.steps.map((s) => h("li", {}, s.label, s.limit ? h("span", { class: "tag", style: "margin-left:6px" }, `${s.limit} ${s.unit || ""}`) : null,
          (s.fees || []).map((f) => h("span", { class: "tag", style: "margin-left:6px" }, `$${f.amount}${f.basis ? ` ${f.basis}` : ""}`)),
          (s.sections || []).map((c) => h("div", { class: "muted", style: "font-size:12.5px" }, c.url ? h("a", { href: c.url, target: "_blank", rel: "noopener" }, c.section) : c.section, c.pinpoint ? ` ${c.pinpoint}` : "", c.text ? ` — “${c.text}”` : "")),
          !(s.sections || []).length && s.quote ? h("div", { class: "muted", style: "font-size:12.5px" }, `“${s.quote}”`) : null,
          (s.forms || []).map((f) => h("div", { style: "font-size:12.5px" }, "Form: ", f.url ? h("a", { href: f.url, target: "_blank", rel: "noopener" }, f.label) : f.label, f.number ? ` (${f.number})` : "")))))) : null,
      r.missing && r.missing.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Still missing"),
        h("ul", { class: "does muted" }, r.missing.map((m) => h("li", {}, m)))) : null));
}
async function viewWho() {
  const question = h("input", { type: "search", "aria-label": "Your question", placeholder: "e.g. who handles a FOIA request in Charlottesville", autocomplete: "off",
    style: "width:100%;box-sizing:border-box;padding:10px;font-size:15px" });
  question.value = store("lexflow-who-q") || "";
  let chosen = JSON.parse(store("lexflow-who-place") || "null");
  const chip = h("span", {});
  const find = h("input", { type: "search", placeholder: "Place (optional): a state, county, city or town", "aria-label": "Place", autocomplete: "off", style: "width:100%;box-sizing:border-box" });
  const results = h("div", { class: "card", style: "position:absolute;z-index:5;min-width:280px;max-width:100%;display:none;max-height:300px;overflow:auto" });
  function drawChip() {
    rc(chip, chosen ? h("span", { class: "tag", style: "display:inline-flex;gap:6px;align-items:center;text-transform:none;font-size:13px" }, chosen.label,
      h("button", { class: "icon-btn", "aria-label": `Remove ${chosen.label}`, onclick: () => { chosen = null; store("lexflow-who-place", ""); drawChip(); } }, "×")) : null);
  }
  let timer = null;
  find.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = find.value.trim();
      if (q.length < 2) { results.style.display = "none"; return; }
      const rows = await api(`/api/targets?q=${encodeURIComponent(q)}`);
      rc(results, rows.length ? rows.map((r) => h("button", { class: "btn", style: "display:block;width:100%;text-align:left;border:0;border-radius:0",
        onclick: () => { chosen = { target: r.target, label: r.label }; store("lexflow-who-place", JSON.stringify(chosen)); drawChip(); find.value = ""; results.style.display = "none"; } },
        r.label, h("span", { class: "muted" }, r.kind === "state" ? "" : ` · ${r.kind}${r.population ? ` · ${fmtInt(r.population)}` : ""}`)))
        : h("p", { class: "card-pad muted" }, "No match."));
      results.style.display = "block";
    }, 200);
  });
  let live = store("lexflow-who-live") === "1";
  const liveSeg = h("div", { class: "seg", role: "group", "aria-label": "Store" });
  function drawSeg() {
    rc(liveSeg, h("button", { type: "button", "aria-pressed": String(!live), onclick: () => { live = false; store("lexflow-who-live", "0"); drawSeg(); } }, "Local"),
      h("button", { type: "button", "aria-pressed": String(live), onclick: () => { live = true; store("lexflow-who-live", "1"); drawSeg(); } }, "Live"));
  }
  drawSeg();
  const status = h("p", { class: "muted" });
  const out = h("div");
  async function run() {
    const q = question.value.trim();
    store("lexflow-who-q", q);
    if (!q) { status.textContent = "Type a question first."; return; }
    status.textContent = live ? "Asking lexipedia.wikibase.cloud…" : "Looking it up…";
    rc(out);
    let a;
    try {
      const u = new URLSearchParams({ q, live: live ? "1" : "0" });
      if (chosen) u.set("place", chosen.target);
      a = await api(`/api/who?${u}`);
    } catch (e) {
      status.textContent = "";
      rc(out, h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Could not answer. "), String(e.message || e))));
      return;
    }
    const r = a.route;
    const where = r.place ? r.place.name + ", " : "";
    status.textContent = `${where}${r.jurisdiction ? S.meta.states?.[r.jurisdiction] || r.jurisdiction.toUpperCase() : "no place"} · topic: ${r.topic_label || "not recognised"}${r.topic_by === "decision" ? ` (decision model, ${(r.confidence * 100).toFixed(0)}%)` : ""} · ${a.source === "store" ? "local store" : a.source === "live" ? "live endpoint" : "models' facts (no store built)"}`;
    const sparqlLink = a.sparql ? h("a", { class: "btn small", href: `#/query/${a.sparql.query}/${encodeURIComponent(Object.entries(a.sparql.params).map(([k, v]) => `${k}=${v}`).join("&"))}` }, "Run as SPARQL") : null;
    const place = a.place ? h("section", { class: "card role-card" },
      h("div", { class: "card-head" }, h("div", {}, h("h2", {}, a.place.label), h("p", {}, "The locality itself"))),
      h("div", { class: "card-pad role-body" },
        a.place.channels.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Reach them"), h("ul", { class: "chans" }, a.place.channels.map(channelRow))) : null,
        a.place.links.wikidata ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Elsewhere"), h("div", {}, h("a", { href: a.place.links.wikidata, target: "_blank", rel: "noopener" }, `Wikidata ${a.place.links.wikidata_qid}`))) : null)) : null;
    rc(out,
      h("div", { class: "row-flex", style: "margin-bottom:12px" }, sparqlLink, r.processes.length ? h("span", { class: "muted" }, `${r.processes.length} ${r.processes.length === 1 ? "process" : "processes"}: ${r.processes.map((p) => p.title || p.process || p.model_id).join("; ")}`) : null),
      a.roles.length ? h("div", { class: "grid who-grid" }, a.roles.map(roleCard)) : null,
      a.local.length ? [h("h2", { style: "margin:18px 0 10px" }, "Ask the locality"), h("div", { class: "grid who-grid" }, a.local.map(roleCard))] : null,
      place ? [h("h2", { style: "margin:18px 0 10px" }, "The place"), place] : null,
      a.missing.length ? h("div", { class: "notice", style: "margin-top:16px" }, icon("info"), h("ul", { class: "does", style: "margin:0" }, a.missing.map((m) => h("li", {}, m)))) : null,
      !a.roles.length && !a.local.length ? h("p", { class: "muted" }, "No roles found for this question yet.") : null);
  }
  question.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); run(); } });
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Who do I ask"),
      h("p", {}, "Name a thing you want to do and a place: every role the law gives it, who plays the role, how to reach them, and the words of the statute that make them responsible. Organisations and office channels only, never a person."))),
    h("section", { class: "card card-pad", style: "margin-bottom:16px" },
      h("div", { class: "who-form" },
        question,
        h("div", { class: "who-place" }, find, results, chip),
        h("div", { class: "query-bar" }, h("button", { class: "btn primary", type: "button", onclick: run }, "Ask"), liveSeg,
          h("span", { class: "muted" }, "Try: starting an LLC in Virginia · FOIA request in Charlottesville · dog license in Staunton")))),
    status, out);
  drawChip();
  if (question.value) run();
}

async function viewQuery(pickName, pickParams) {
  const cat = await api("/api/sparql/queries");
  let live = store("lexflow-sparql-live") === "1";
  let current = null;
  const params = {};
  const editor = h("textarea", { class: "sparql", spellcheck: "false", "aria-label": "SPARQL query", placeholder: "Pick a question on the left, or write SPARQL here. {P:label} and {Q:key} tokens are expanded." });
  const paramBox = h("div", { class: "query-params" });
  const results = h("div");
  const status = h("span", { class: "muted" });
  const list = h("ul", { class: "query-list" });
  const liveSeg = h("div", { class: "seg", role: "group", "aria-label": "Store" });
  function drawSeg() {
    rc(liveSeg, h("button", { type: "button", "aria-pressed": String(!live), onclick: () => { live = false; store("lexflow-sparql-live", "0"); drawSeg(); } }, "Local"),
      h("button", { type: "button", "aria-pressed": String(live), onclick: () => { live = true; store("lexflow-sparql-live", "1"); drawSeg(); } }, "Live"));
  }
  drawSeg();
  function drawList() {
    rc(list, ...cat.queries.map((q) => h("li", {}, h("button", { type: "button", class: "query-btn", "aria-pressed": String(current && current.name === q.name), onclick: () => pick(q) },
      h("span", { class: "name" }, q.name, q.live_only ? h("span", { class: "tag" }, "live only") : null), h("span", { class: "q" }, q.question)))));
  }
  function pick(q) {
    current = q;
    editor.value = q.text;
    for (const k of Object.keys(params)) delete params[k];
    drawList();
    drawParams();
    if (q.live_only && !live) { live = true; store("lexflow-sparql-live", "1"); drawSeg(); }
  }
  function drawParams() {
    const entries = current ? Object.entries(current.params) : [];
    rc(paramBox, ...entries.map(([k, v]) => h("label", { class: "field" }, k,
      h("input", { type: "text", value: v, placeholder: v || "any", "aria-label": `parameter ${k}`, oninput: (e) => { params[k] = e.target.value; } }))));
    paramBox.style.display = entries.length ? "" : "none";
  }
  function request() {
    const u = new URLSearchParams();
    const canned = current && editor.value === current.text;
    u.set("q", canned ? current.name : editor.value);
    u.set("live", live ? "1" : "0");
    if (canned) for (const [k, v] of Object.entries(params)) if (v) u.append("param", `${k}=${v}`);
    return u;
  }
  function curlText() {
    const u = request();
    const parts = [`curl -sG '${location.origin}/api/sparql'`];
    for (const [k, v] of u.entries()) parts.push(`--data-urlencode ${JSON.stringify(`${k}=${v}`).replace(/'/g, "'\\''").replace(/^"|"$/g, "'")}`);
    return parts.join(" \\\n  ");
  }
  async function copy(text, label) {
    try { await navigator.clipboard.writeText(text); status.textContent = `${label} copied.`; } catch (e) { window.prompt(`Copy ${label}:`, text); }
  }
  async function run() {
    if (!editor.value.trim()) { status.textContent = "Nothing to run."; return; }
    status.textContent = live ? "Asking lexipedia.wikibase.cloud…" : "Running on the local store…";
    rc(results);
    let r;
    try {
      r = await api(`/api/sparql?${request()}`);
    } catch (e) {
      status.textContent = "";
      rc(results, h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Query failed. "), String(e.message || e))));
      return;
    }
    const cols = r.vars.map((v) => ({ key: v, label: v, render: (row) => cell(row[v]), sort: (row) => {
      const b = row[v]; if (!b) return null; const n = Number(b.value); return b.type === "literal" && b.value !== "" && !Number.isNaN(n) ? n : cellValue(b); } }));
    const where = r.live ? "live endpoint" : "local store";
    status.textContent = `${fmtInt(r.n)} row${r.n === 1 ? "" : "s"}${r.truncated ? ` (first ${fmtInt(r.n)} only)` : ""} from the ${where} in ${fmtInt(r.ms)} ms` +
      (r.unresolved.length ? ` · provisional ids for: ${r.unresolved.join(", ")}` : "");
    rc(results, r.n ? h("section", { class: "card" }, h("div", { class: "card-pad", style: "padding-top:8px" }, sortableTable(cols, r.rows)))
      : h("p", { class: "muted" }, r.live ? "No rows on the wiki yet; this part of the schema may be waiting for pass 2." : "No rows. If the local store is empty, run lexflow sparql --build."));
    for (const td of results.querySelectorAll("td")) td.classList.add("cell");
  }
  const runBtn = h("button", { class: "btn primary", type: "button", onclick: run }, "Run");
  editor.addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); run(); } });
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Query"),
      h("p", {}, "Ask the law graph in SPARQL: the local copy built from this database (", h("code", {}, "lexflow sparql --build"), ") or the live ",
        h("a", { href: "https://lexipedia.wikibase.cloud/query/", target: "_blank", rel: "noopener" }, "lexipedia.wikibase.cloud"), " endpoint. ",
        cat.local_built ? "" : "The local store has not been built yet. ", cat.ids_resolved ? "" : "Ids not yet on the wiki are provisional (P900+, Q900000+). ",
        cat.turtle_stale ? "The wiki's id map is newer than the local store: rebuild it to query by the wiki's ids." : ""))),
    h("div", { class: "grid query-layout" },
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("h2", {}, "Questions")), list),
      h("div", {},
        h("section", { class: "card card-pad" },
          editor, paramBox,
          h("div", { class: "query-bar" }, runBtn, liveSeg,
            h("button", { class: "btn small", type: "button", onclick: () => copy(curlText(), "cURL") }, "Copy as cURL"),
            h("button", { class: "btn small", type: "button", onclick: () => copy(editor.value, "query") }, "Copy query"),
            h("span", { class: "muted" }, "Ctrl+Enter runs")),
          h("div", { class: "query-bar" }, status)),
        h("div", { class: "spacer" }),
        results,
        h("div", { class: "spacer" }),
        h("details", { class: "card prefixes" }, h("summary", {}, "Prefixes for the wiki's own query UI"),
          h("div", { class: "query-note" }, "Lexipedia's entities are not under wd:/wdt:; paste these before a query at ",
            h("a", { href: `${cat.endpoint.replace(/\/sparql$/, "/")}`, target: "_blank", rel: "noopener" }, "the wiki's query service"), "."),
          h("pre", { class: "log" }, cat.prefixes),
          h("div", { class: "query-note" }, h("button", { class: "btn small", type: "button", onclick: () => copy(cat.prefixes, "prefix block") }, "Copy prefixes"))))));
  drawList();
  drawParams();
  const wanted = pickName && cat.queries.find((q) => q.name === pickName);
  if (wanted) {
    pick(wanted);
    for (const [k, v] of new URLSearchParams(pickParams || "")) if (k in wanted.params) params[k] = v;
    drawParams();
    for (const input of paramBox.querySelectorAll("input")) if (params[input.getAttribute("aria-label").replace("parameter ", "")]) input.value = params[input.getAttribute("aria-label").replace("parameter ", "")];
    run();
  } else if (cat.queries.length) pick(cat.queries.find((q) => q.name === "coverage") || cat.queries[0]);
}

poll();
route();
