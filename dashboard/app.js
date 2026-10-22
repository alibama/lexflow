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
  version: -1, running: 0, current: null, focus: null, county: null, topo: null, tableView: false, params: new URLSearchParams(),
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
  jobs: viewJobs, job: viewJob, method: viewMethod, query: viewQuery, who: viewWho, coverage: viewCoverage, compute: viewCompute, hypo: viewHypo,
  benefits: viewBenefits };
routes.pipeline = viewPipeline;
async function route() {
  // #/page/arg?key=value: the query part never reaches the page's arguments; pages read it from S.params
  const [hashPath, query = ""] = (location.hash || "#/map").split("?");
  S.params = new URLSearchParams(query);
  const [, name = "map", ...rest] = hashPath.split("/");
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
// Scored layers read the question's answers; holdings layers (kind "holdings") read what lexflow holds now:
// state models and asked drafts, the latest coverage run, researched localities, the Wikibase, the statute index.
const LAYERS = {
  confidence: { label: "Answer confidence", scope: "county", bins: [0.2, 0.35, 0.5, 0.65],
    labels: ["under 0.20", "0.20–0.35", "0.35–0.50", "0.50–0.65", "0.65 and up"], fmt: (v) => fx(v),
    about: "Mean confidence of the answer for each government in the county, for the question chosen above." },
  tier: { label: "Who built the state model", scope: "state", about: "Whether the state's step-by-step model was reviewed, agreed by two extractions, drafted once, or only the law was found." },
  completion: { label: "State model completion", scope: "state", bins: [0.3, 0.5, 0.7, 0.85],
    labels: ["1–2 of 8 stages", "3 of 8", "4–5 of 8", "6 of 8", "7–8 of 8"], fmt: (v) => pct(v), about: "How many of the eight build stages the state model has passed." },
  quality: { label: "State model quality", scope: "state", bins: [0.5, 0.65, 0.8, 0.9],
    labels: ["under 0.50", "0.50–0.65", "0.65–0.80", "0.80–0.90", "0.90 and up"], fmt: (v) => fx(v), about: "The state model's quality score from its checks." },
  contact: { label: "Contact found", scope: "county", bins: [0.15, 0.3, 0.45, 0.7],
    labels: ["mailing address", "some websites", "most have a website", "email or phone", "records or licence page"], fmt: (v) => fx(v), about: "How good a contact we found for the governments in the county." },
  local: { label: "Local law found (LOCUS)", scope: "county", bins: [0.01, 0.1, 0.25, 0.5],
    labels: ["none", "under 10%", "10–25%", "25–50%", "half or more"], fmt: (v) => pct(v), about: "Share of the county's governments with a local ordinance found in LOCUS." },
  processes: { label: "Processes modelled", scope: "state", kind: "holdings", bins: [1, 2, 3, 10],
    labels: ["none yet", "1", "2", "3–9", "10 and up"], fmt: (v) => fmtInt(v), about: "Process items per state: reviewed or agreed state models plus asked answers that stand as drafts." },
  coverage: { label: "Coverage", scope: "state", kind: "holdings", bins: [0.1, 0.25, 0.5, 0.75],
    labels: ["under 10% adequate", "10–25%", "25–50%", "50–75%", "75% and up"], fmt: (v) => pct(v), about: "Latest coverage run: the share of the questions people ask that the state answers adequately; dots are researched localities, sized by verified processes." },
  localproc: { label: "Local processes researched", scope: "county", kind: "holdings", bins: [5, 10, 20, 40],
    labels: ["1–4", "5–9", "10–19", "20–39", "40 and up"], fmt: (v) => fmtInt(v), about: "Localities with researched local processes (a records request, a licence, a permit): how many, and how many are verified." },
  wikibase: { label: "On the Wikibase", scope: "state", kind: "holdings", bins: [1, 20, 50, 150],
    labels: ["none", "1–19", "20–49", "50–149", "150 and up"], fmt: (v) => fmtInt(v), about: "Items published to the Wikibase per state: statutes, units, processes, steps, roles, forms and more." },
  index: { label: "Statute index", scope: "state", kind: "holdings", bins: [1, 20000, 30000, 50000],
    labels: ["no index", "under 20,000", "20,000–30,000", "30,000–50,000", "50,000 and up"], fmt: (v) => fmtInt(v), about: "Statute sections indexed for full-text search per state, with the regulations index where it exists." },
};
const TIERS_SHOWN = ["found", "single", "agreed", "reviewed"];
const HOLDING_VALUE = {     // the number a holdings layer colours a state by
  processes: (st) => st.processes ? st.processes.value : null,
  coverage: (st) => st.coverage ? st.coverage.share : null,
  wikibase: (st) => st.wikibase ? st.wikibase.value : null,
  index: (st) => st.index ? st.index.sections : null,
};
const verdictLine = (c) => `${c.adequate} adequate · ${c.partial} partial · ${c.draft} on drafts · ${c.none} none of ${c.cells}`;
function binColor(v, bins) {
  let i = 0;
  while (i < bins.length && v >= bins[i]) i++;
  return css(`--seq-${i + 1}`);
}

async function viewMap() {
  if (LAYERS[S.params.get("layer")]) { S.layer = S.params.get("layer"); store("lexflow-layer", S.layer); }   // #/map?layer=index
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
  const holdingsCard = h("section", { class: "card holdings", "aria-label": "What's on the map" });
  rc(view,
    h("div", { class: "page-head" }, h("div", {},
      h("h1", {}, "Where the answers stand"),
      h("p", {}, "Every county, city and town, coloured by how well lexflow can answer the question, and every state by what lexflow holds: models, coverage, Wikibase items and the statute index. Colours update as process models are built, checked and scored."))),
    h("div", { class: "filters" }, questionSeg(load), h("label", { class: "field" }, "Layer", layerSel), h("label", { class: "field" }, "Zoom", stateSel), tableBtn),
    kpis,
    h("div", { class: "grid map-layout" }, h("section", { class: "card" }, mapWrap, legend), side),
    holdingsCard,
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
  const dotsG = g.append("g").attr("class", "dots");     // researched localities, on the coverage and local-process layers
  let zoomK = 1;
  const zoom = d3.zoom().scaleExtent([1, 14]).translateExtent([[-50, -50], [1025, 660]]).on("zoom", (e) => {
    g.attr("transform", e.transform);
    zoomK = e.transform.k;
    dotsG.selectAll("circle").attr("r", (d) => dotR(d) / Math.sqrt(zoomK));
  });
  svg.call(zoom).on("wheel.zoom", null);   // page scroll stays page scroll; buttons and drag still zoom
  mapWrap.append(svg.node());

  let data = null, overview = null, rows = [];
  const isHoldings = () => LAYERS[S.layer].kind === "holdings";
  const placeOf = (fips) => data?.places?.[fips] || null;
  const placeTotal = (p, key) => p.govs.reduce((a, g) => a + (g[key] || 0), 0);
  function valueOf(fips) {
    const layer = LAYERS[S.layer];
    if (S.layer === "localproc") { const p = placeOf(fips); return p ? placeTotal(p, "processes") : null; }
    if (layer.scope === "county") return data.counties[fips]?.value ?? null;
    const st = data.states[fips.slice(0, 2)];
    if (!st) return null;
    if (S.layer === "tier") return st.tier;
    if (HOLDING_VALUE[S.layer]) return HOLDING_VALUE[S.layer](st);
    return st[S.layer] ?? null;
  }
  function fillOf(fips) {
    const v = valueOf(fips);
    const layer = LAYERS[S.layer];
    if (S.layer === "tier") {
      if (!data.states[fips.slice(0, 2)] || !data.states[fips.slice(0, 2)].governments) return "url(#nodata)";
      return v === "none" || v == null ? css("--neutral-fill") : css(`--tier-${v}`);
    }
    if (S.layer === "localproc") return v == null ? css("--neutral-fill") : binColor(v, layer.bins);
    if (v == null) return "url(#nodata)";
    return binColor(v, layer.bins);
  }
  function drawLegend() {
    const layer = LAYERS[S.layer];
    const items = S.layer === "tier"
      ? [["none", "No state law found", css("--neutral-fill")], ...TIERS_SHOWN.map((t) => [t, S.meta.tier_label[t], css(`--tier-${t}`)])]
      : layer.labels.map((l, i) => [i, l, css(`--seq-${i + 1}`)]);
    if (S.layer === "localproc") items.unshift(["none", "Not researched yet", css("--neutral-fill")]);
    const noData = S.layer === "coverage" ? "No coverage run for this state yet" : "No data yet";
    rc(legend, h("span", { class: "title" }, layer.label),
      ...items.map(([, label, color]) => h("span", {}, h("span", { class: "sw", style: `background:${color}` }), label)),
      S.layer === "localproc" ? null : h("span", {}, h("span", { class: "sw", style: `background:repeating-linear-gradient(45deg, var(--nodata) 0 3px, var(--hatch) 3px 4px)` }), noData),
      S.layer === "coverage" || S.layer === "localproc" ? h("span", {}, h("span", { class: "sw dot" }), "Locality with researched processes") : null,
      layer.about ? h("span", { class: "about" }, layer.about) : null);
  }
  const dotR = (d) => 3 + Math.sqrt(placeTotal(d.place, "verified")) * 1.1;
  function drawDots() {
    const show = S.layer === "coverage" || S.layer === "localproc";
    const feats = show && data?.places ? counties.filter((c) => data.places[c.id]).map((c) => ({ id: c.id, place: data.places[c.id], xy: path.centroid(c) })) : [];
    dotsG.selectAll("circle").data(feats, (d) => d.id).join("circle")
      .attr("cx", (d) => d.xy[0]).attr("cy", (d) => d.xy[1]).attr("r", (d) => dotR(d) / Math.sqrt(zoomK));
  }
  function paint() {
    pat.select(".nodata-bg").attr("fill", css("--nodata"));
    pat.select(".nodata-line").attr("stroke", css("--hatch"));
    countyPaths.attr("fill", (d) => fillOf(d.id));
    drawDots();
    drawLegend();
  }
  // the tooltip's lines for a holdings layer: the state's numbers, then the locality's when it has researched processes
  function holdingLines(fips) {
    const sd = data.states[fips.slice(0, 2)] || {};
    const p = placeOf(fips);
    const out = [];
    if (S.layer === "processes" && sd.processes) {
      const t = sd.processes.tiers || {};
      out.push(h("div", { class: "k" }, `State models: ${["reviewed", "agreed", "single", "found"].filter((k) => t[k]).map((k) => `${t[k]} ${S.meta.tier_label[k] || k}`).join(", ") || "none"}`));
      out.push(h("div", { class: "k" }, `Asked drafts: ${fmtInt(sd.processes.asked)}`));
    } else if (S.layer === "coverage") {
      if (sd.coverage) {
        out.push(h("div", { class: "k" }, verdictLine(sd.coverage)));
        if (sd.coverage.missing?.length) out.push(h("div", { class: "k" }, `Most often missing: ${sd.coverage.missing.map(([k, n]) => `${k} (${n})`).join(", ")}`));
        out.push(h("div", { class: "k" }, `Run ${sd.coverage.run}`));
      }
    } else if (S.layer === "wikibase" && sd.wikibase) {
      const kinds = Object.entries(sd.wikibase.kinds || {}).sort((a, b) => b[1] - a[1]).slice(0, 6);
      out.push(h("div", { class: "k" }, kinds.length ? kinds.map(([k, n]) => `${n} ${k}`).join(", ") : "nothing published for this state yet"));
    } else if (S.layer === "index" && sd.index) {
      out.push(h("div", { class: "k" }, `${fmtInt(sd.index.sections)} statute sections` + (sd.index.regulations ? ` · ${fmtInt(sd.index.regulations)} regulation sections` : "")));
    }
    if (p && (S.layer === "coverage" || S.layer === "localproc")) {
      for (const gv of p.govs) {
        out.push(h("div", { style: "margin-top:6px;font-weight:600" }, gv.name));
        out.push(h("div", { class: "k" }, `${fmtInt(gv.processes)} local process${gv.processes === 1 ? "" : "es"} researched, ${fmtInt(gv.verified)} verified`));
        if (gv.coverage) out.push(h("div", { class: "k" }, verdictLine(gv.coverage)));
      }
      out.push(h("div", { class: "k" }, "Click to open the place"));
    } else if (S.layer === "coverage" && sd.coverage) {
      out.push(h("div", { class: "k" }, "Click to open the coverage matrix for this state"));
    }
    return out;
  }
  countyPaths
    .on("pointermove", (evt, d) => {
      const st = stateByFips.get(d.id.slice(0, 2));
      const layer = LAYERS[S.layer];
      const v = valueOf(d.id);
      const c = data?.counties[d.id];
      const sd = data?.states[d.id.slice(0, 2)];
      const vText = S.layer === "tier" ? (S.meta.tier_label[v] || "No data yet")
        : v == null ? (S.layer === "localproc" ? "Not researched yet" : S.layer === "coverage" ? "No coverage run yet" : "No data yet") : layer.fmt(v);
      showTip(evt, isHoldings() ? [
        h("div", { class: "v" }, vText),
        h("div", { class: "k" }, layer.label + (layer.scope === "state" ? ` · ${st ? st.name : ""}` : "")),
        h("div", { style: "margin-top:6px;font-weight:600" }, `${countyName.get(d.id) || d.id}${st ? `, ${st.name}` : ""}`),
        ...holdingLines(d.id),
      ] : [
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
    .on("click", (evt, d) => {
      const p = placeOf(d.id);
      const st = stateByFips.get(d.id.slice(0, 2));
      if (p && (S.layer === "coverage" || S.layer === "localproc")) { location.hash = `#/place/${encodeURIComponent(p.govs[0].gov_id)}`; return; }
      if (S.layer === "coverage" && st && data.states[st.fips]?.coverage) { location.hash = `#/coverage?state=${st.state}`; return; }
      selectCounty(d.id);
    });

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
        h("dt", {}, "Statutes"), h("dd", {}, r.statutes),
        ...holdingRows(data?.states[fips] || {}))));
  }
  // what lexflow holds for a state, as rows of the side panel's list
  function holdingRows(sd) {
    if (!sd.processes) return [];
    const cov = sd.coverage;
    return [
      h("dt", {}, "Processes modelled"), h("dd", {}, h("a", { href: `#/processes` }, `${fmtInt(sd.processes.value)}`), h("span", { class: "muted" }, ` (${fmtInt(sd.processes.asked)} asked drafts)`)),
      h("dt", {}, "Coverage"), h("dd", {}, cov ? h("a", { href: `#/coverage?state=${sd.state}` }, `${cov.adequate} of ${cov.cells} adequate`) : h("span", { class: "muted" }, "no run yet")),
      h("dt", {}, "On the Wikibase"), h("dd", { class: "num" }, fmtInt(sd.wikibase?.value)),
      h("dt", {}, "Index"), h("dd", {}, sd.index?.sections ? `${fmtInt(sd.index.sections)} sections${sd.index.regulations ? ` · ${fmtInt(sd.index.regulations)} regulations` : ""}` : h("span", { class: "muted" }, "not indexed")),
    ];
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
      { key: "modelled", label: "Modelled", num: true, render: (r) => fmtInt(data.states[r.fips]?.processes?.value ?? 0), sort: (r) => data.states[r.fips]?.processes?.value ?? 0 },
      { key: "covered", label: "Coverage", num: true, render: (r) => { const c = data.states[r.fips]?.coverage; return c ? `${c.adequate}/${c.cells}` : "–"; }, sort: (r) => data.states[r.fips]?.coverage?.share ?? -1 },
      { key: "wikibase", label: "Wikibase", num: true, render: (r) => fmtInt(data.states[r.fips]?.wikibase?.value ?? 0), sort: (r) => data.states[r.fips]?.wikibase?.value ?? 0 },
      { key: "indexed", label: "Indexed", num: true, render: (r) => fmtInt(data.states[r.fips]?.index?.sections ?? 0), sort: (r) => data.states[r.fips]?.index?.sections ?? 0 },
      { key: "citation", label: "State law", render: (r) => r.law_url ? h("a", { href: r.law_url, target: "_blank", rel: "noopener", onclick: (e) => e.stopPropagation() }, r.citation) : h("span", { class: "muted" }, r.statutes === "not-in-release" ? "No statutes in release" : r.law_status === "not-located" ? "Not located" : r.law_status) },
    ];
    rc(tableCard, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "State by state"),
      h("p", {}, "Sort by any column. Click a row to zoom the map to that state."))),
      h("div", { class: "card-pad", style: "padding-top:8px" }, sortableTable(cols, rows, { initial: "governments",
        onRow: (r) => { zoomTo(r.fips); window.scrollTo({ top: 0, behavior: "smooth" }); } })));
  }
  // "What's on the map": the totals behind the holdings layers, each linking to its page, and the pool when it is on
  let pool = null;
  function drawHoldings() {
    const t = data.holdings || {};
    const cov = t.coverage || {};
    const tile = (href, value, label, sub) => h("a", { class: "holding", href }, h("span", { class: "value" }, value), h("span", { class: "label" }, label), sub ? h("span", { class: "sub" }, sub) : null);
    rc(holdingsCard,
      h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "What's on the map"), h("p", {}, "Totals behind the holdings layers. Each number opens its page."))),
      h("div", { class: "holdings-row" },
        tile("#/processes", fmtInt(t.states_with_models), "states with process models", `${fmtInt(S.meta.states.length)} states and DC`),
        tile("#/places", fmtInt(t.localities), `localit${t.localities === 1 ? "y" : "ies"} researched`, `${fmtInt(t.local_processes)} local processes`),
        tile("#/coverage", cov.run ? `${fmtInt(cov.adequate)} of ${fmtInt(cov.cells)}` : "–", "questions covered adequately", cov.run ? `${fmtInt(cov.draft)} on drafts alone · run ${cov.run}` : "no coverage run yet"),
        tile("#/query", fmtInt(t.wikibase), "Wikibase items", "statutes, units, processes, steps, roles, forms"),
        tile("#/data", fmtInt(t.index?.sections), "statute sections indexed", `${fmtInt(t.index?.states)} states${t.index?.regulations ? ` · ${fmtInt(t.index.regulations)} regulation sections` : ""}`),
        // countries' national law (statutes_jpn ...): articles and laws, apart from the states' sections
        ...Object.entries(t.countries || {}).map(([k, c]) => tile(`#/query/law-in-order/${encodeURIComponent(`unit=lexflow:code:${k}`)}`,
          fmtInt(c.sections), `articles of ${c.name}'s law indexed`, `${fmtInt(c.laws)} laws · ${k}`)),
        pool && pool.pool ? tile("#/compute", `${fmtInt(pool.totals?.online)} of ${fmtInt(pool.totals?.nodes)}`, "pool nodes online", `${fmtInt(pool.totals?.slots)} slots · ${fmtInt(pool.totals?.busy)} busy`) : null));
  }
  function draw() {
    mapWrap.parentElement.style.display = S.tableView ? "none" : "";
    side.style.display = S.tableView ? "none" : "";
    if (data) paint();
  }
  async function load(themeOnly) {
    if (themeOnly === true && data) { paint(); return; }
    mapWrap.classList.add("loading");
    [data, overview, rows, pool] = await Promise.all([api(`/api/map?question=${S.question}&layer=${S.layer}`), api("/api/overview"), api(`/api/states?question=${S.question}`),
      api("/api/compute").catch(() => null)]);
    mapWrap.classList.remove("loading");
    drawKpis(); drawHoldings(); drawTable(); draw();
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
      serviceCard("Ollama", o.reachable && o.want.every((m) => o.models.includes(m)) ? true : o.reachable ? null : false,
        o.pool ? `${o.pool.online} of ${o.pool.nodes} nodes online: ${(o.pool.names || []).join(", ")}` : o.url,
        h("span", {}, o.reachable ? (o.models.length ? `Models: ${o.models.join(", ")}` : "Running, no models yet") : (o.pool ? "No node online" : "Not reachable: start with --profile llm"),
          " · ", h("a", { href: "#/compute" }, o.pool ? "see Compute" : "Compute"))),
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
    for (const [k, label] of [["force", "Redo"], ["no_llm", "Skip models"], ["regulations", "+ regulations"], ["full", "Full resend"], ["dry_run", "Dry run"], ["drafts", "+ drafts"], ["really", "Write to the wiki"]]) {
      if (!s.params.includes(k)) continue;
      const cb = h("input", { type: "checkbox" });
      values[k] = () => cb.checked;
      opts.append(h("label", { class: "check" }, cb, label));
    }
    const run = h("button", { class: `btn ${s.level === "required" && s.status !== "done" ? "primary" : ""}`, disabled: !s.runnable || s.status === "blocked" || !!job,
      onclick: async () => {
        const args = Object.fromEntries(Object.entries(values).map(([k, f]) => [k, f()]));
        run.disabled = true;
        // a real push or publish is refused here (409): it is started from the Pipeline page, after a dry run
        try { await startRunJob(s.id, args); } catch (e) { alert(e.message); }
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
// a state's or a country's name from its key (va -> Virginia, jpn -> Japan)
function jurName(st) {
  return (S.meta.states.find((s) => s.state === st) || (S.meta.countries || []).find((c) => c.state === st) || {}).name || st;
}

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
      : h("span", { class: "muted" }, "No states, countries or places chosen yet."));
  }
  const find = h("input", { type: "search", placeholder: "Add a state, county, city or town, or a country (Japan)", "aria-label": "Add a state, country or place", style: "width:min(360px, 100%)", autocomplete: "off" });
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
  const place = local.name || jurName(r.state);
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
      h("tbody", {}, arms.map(([arm, s]) => h("tr", {}, h("td", {}, label[arm] || (arm.includes("@") && label[arm.split("@")[0]] ? `${label[arm.split("@")[0]]} (${arm.split("@")[1]})` : arm)), cols.map(([k]) => h("td", { class: "num" }, s[k] == null ? "–" : k === "cases" ? String(s[k]) : fx(s[k])))))))))];
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

// ================================================================ COMPUTE
// The model servers lexflow can send work to (lexflow/compute, docs/compute.md).  Lexflow's server asks the nodes
// and the overlay; this page only reads /api/compute/* and never fetches a node or the overlay itself.
function nodeStatus(n) {
  if (n.gone) return statusEl("optional", "left the overlay group");
  if (!n.enabled) return statusEl("optional", "disabled");
  if (n.draining) return statusEl("partial", n.busy ? `draining (${n.busy} in flight)` : "drained");
  if (n.status === "online") return statusEl("done", "online");
  if (n.status === "backoff") return statusEl("blocked", `backing off${n.backoff_until ? ` until ${new Date(n.backoff_until).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}` : ""}`);
  if (n.status === "offline") return statusEl("todo", n.overlay && n.overlay.connected === false ? "asleep (overlay)" : `offline${n.last_ok ? `, last seen ${ago(n.last_ok)}` : ""}`);
  return statusEl("todo", "not checked yet");
}
const gb = (x) => (x == null ? "–" : `${Number(x).toFixed(x < 10 ? 1 : 0)} GB`);
const tps = (x) => (x == null ? "–" : `${fx(x, 1)} t/s`);

async function viewCompute() {
  const pills = h("div", { class: "services" });
  const cards = h("div", { class: "grid who-grid", style: "margin-bottom:16px" });
  const notes = h("div");
  const recentBody = h("div", { class: "card-pad" });
  const nodeSel = h("select", { "aria-label": "Node", onchange: () => loadRecent() }, h("option", { value: "" }, "All nodes"));
  const modelSel = h("select", { "aria-label": "Model", onchange: () => loadRecent() }, h("option", { value: "" }, "All models"));
  const checkAll = h("button", { class: "btn", onclick: async () => { checkAll.disabled = true; try { await post("/api/compute/check"); } catch (e) { alert(e.message); } await load(); checkAll.disabled = false; } }, "Check all now");
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Compute"),
      h("p", {}, "Model servers lexflow can send work to. Each call goes to a node that has the model and a free slot; if a node drops out, its work moves to another. Nodes come from LEXFLOW_LLM_NODES or the overlay, never from this page.")),
      h("div", { class: "row-flex" }, checkAll)),
    notes, pills, cards,
    h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Recent work"),
      h("p", {}, "The last model calls: prompt tokens and read speed, output tokens and write speed, the time taken and the result.")),
      h("div", { class: "row-flex" }, nodeSel, modelSel)), recentBody));
  let data = null;
  function pill(label, value, sub) {
    return h("div", { class: "card service" }, h("div", { class: "name" }, value), h("div", { class: "sub" }, label), sub ? h("div", { class: "sub muted" }, sub) : null);
  }
  function hostLines(n) {
    const hst = n.host;
    if (!hst) return null;
    const used = hst.ram_total_gb != null && hst.ram_available_gb != null ? hst.ram_total_gb - hst.ram_available_gb : null;
    return h("div", { class: "sub" },
      h("div", {}, [hst.cpu, hst.threads ? `${hst.threads} threads` : null, hst.load1 != null ? `load ${fx(hst.load1, 1)}` : null].filter(Boolean).join(" · ")),
      used != null ? h("div", {}, `RAM ${fx(used, 1)} of ${fx(hst.ram_total_gb, 1)} GB in use`, h("div", { class: "meter" }, h("span", { style: `width:${Math.round((used / hst.ram_total_gb) * 100)}%` }))) : null,
      h("div", {}, [hst.temp_c != null ? `${Math.round(hst.temp_c)} °C` : null, hst.on_ac != null ? (hst.on_ac ? "on AC" : "on battery") : null, hst.battery_pct != null ? `battery ${hst.battery_pct} %` : null, hst.uptime_h != null ? `up ${fx(hst.uptime_h, 0)} h` : null].filter(Boolean).join(" · ")));
  }
  function pullControl(n) {
    const sel = h("select", { "aria-label": `Model to pull on ${n.name}` }, h("option", { value: "" }, "Pull a model…"),
      ...n.pullable.map((p) => h("option", { value: p.model, disabled: p.fits === false }, `${p.model} · ${gb(p.gb)}${p.fits === false ? " (too big for its RAM)" : ""}`)),
      h("option", { value: "other" }, "other…"));
    const out = h("span", { class: "sub" });
    sel.addEventListener("change", async () => {
      let model = sel.value;
      if (!model) return;
      if (model === "other") model = (prompt("Model to pull (as on ollama.com, e.g. qwen3:8b)") || "").trim();
      sel.value = "";
      if (!model) return;
      const size = (n.pullable.find((p) => p.model === model) || {}).gb;
      if (!confirm(`This downloads ${size ? `${gb(size)}` : "a model of unknown size"} from the Ollama registry onto ${n.name}. Go ahead?`)) return;
      const go = async (confirmBig) => {
        try {
          const r = await post(`/api/compute/nodes/${encodeURIComponent(n.name)}/pull`, { model, confirm: confirmBig });
          rc(out, `Pulling ${r.model}: `, h("a", { href: `#/job/${r.job_id}` }, `job #${r.job_id}`), ` (${r.message})`);
          pollSoon();
        } catch (e) {
          if (!confirmBig && /confirm: true/.test(e.message) && confirm(`${e.message}\n\nPull it anyway?`)) return go(true);
          rc(out, h("span", { class: "muted" }, e.message));
        }
      };
      await go(false);
    });
    return h("div", { class: "row-flex", style: "margin-top:8px" }, sel, out);
  }
  function nodeCard(n) {
    const act = async (what) => {
      try { await post(`/api/compute/nodes/${encodeURIComponent(n.name)}/${what}`); } catch (e) { alert(e.message); }
      await load();
    };
    const flight = n.in_flight.length ? h("div", { class: "sub" }, "Now: ", n.in_flight.map((l) => `${l.model}${l.job_id ? ` · job #${l.job_id} ${l.step || ""}` : ""} · ${l.elapsed_s != null ? `${l.elapsed_s} s` : ""}`).join("; ")) : h("div", { class: "sub muted" }, n.status === "online" ? "idle" : "");
    const models = n.models.length ? sortableTable([
      { key: "name", label: "Model", render: (m) => h("span", { class: "mono", style: "font-size:12px" }, m.name, m.name === data.embed_model ? " (embeds)" : "") },
      { key: "size_gb", label: "Size", num: true, render: (m) => gb(m.size_gb) },
      { key: "quant", label: "Quant", render: (m) => m.quant || "–" },
      { key: "loaded", label: "State", render: (m) => (m.loaded ? `loaded${m.context_length ? ` · ${Math.round(m.context_length / 1024)}k` : ""}` : "on disk") },
      { key: "read", label: "Reads", num: true, sort: (m) => (m.speed || {}).prefill_tps, render: (m) => tps((m.speed || {}).prefill_tps) },
      { key: "write", label: "Writes", num: true, sort: (m) => (m.speed || {}).gen_tps, render: (m) => tps((m.speed || {}).gen_tps) },
    ], n.models, { initial: "name" }) : h("p", { class: "muted", style: "margin:6px 0" }, n.status === "online" ? "No models pulled yet." : "");
    return h("section", { class: "card card-pad" },
      h("div", { class: "row-flex" }, h("h2", { style: "margin:0" }, n.name, n.source === "overlay" ? h("span", { class: "tag" }, "overlay") : null, n.embed || n.name === data.embed_node ? h("span", { class: "tag" }, "embeds") : null), h("span", { class: "right" }, nodeStatus(n))),
      h("div", { class: "sub muted", style: "word-break:break-all" }, n.url, n.version ? ` · Ollama ${n.version}` : "", n.checked_at ? ` · checked ${ago(n.checked_at)}` : ""),
      h("div", { class: "sub muted" }, `${n.busy} of ${n.max_concurrency} slot${n.max_concurrency === 1 ? "" : "s"} busy`, n.threads ? ` · ${n.threads} threads` : "", n.tags.length ? ` · ${n.tags.join(", ")}` : "", n.part_time ? " · part-time" : ""),
      n.last_error && n.status !== "online" ? h("div", { class: "sub", style: "color:var(--critical)" }, n.last_error) : null,
      n.overlay ? h("div", { class: "sub muted" }, `overlay: ${n.overlay.connected ? "connected" : "disconnected"}${n.overlay.last_seen ? ` · last seen ${ago(n.overlay.last_seen)}` : ""}${n.overlay.user ? ` · ${n.overlay.user}` : ""}`) : null,
      hostLines(n), flight,
      n.missing.length ? h("div", { class: "sub" }, statusEl("blocked", ""), `wanted here but not pulled: ${n.missing.join(", ")}`) : null,
      h("h3", { style: "margin:10px 0 4px;font-size:13px" }, "Models"), models,
      h("div", { class: "row-flex", style: "margin-top:10px" },
        h("button", { class: "btn small", onclick: () => act("check") }, "Check now"),
        n.draining || !n.enabled ? h("button", { class: "btn small", onclick: () => act("resume") }, "Enable") : h("button", { class: "btn small", onclick: () => act("drain") }, "Drain")),
      data.pool && n.status === "online" ? pullControl(n) : null);
  }
  async function loadRecent() {
    const q = new URLSearchParams();
    if (nodeSel.value) q.set("node", nodeSel.value);
    if (modelSel.value) q.set("model", modelSel.value);
    q.set("limit", "100");
    const rows = data.pool ? await api(`/api/compute/calls?${q}`) : [];
    rc(recentBody, rows.length ? sortableTable([
      { key: "at", label: "Time", render: (r) => new Date(r.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) },
      { key: "job_id", label: "Job", num: true, render: (r) => (r.job_id ? h("a", { href: `#/job/${r.job_id}` }, `#${r.job_id}`) : "–") },
      { key: "step", label: "Step" }, { key: "node", label: "Node" },
      { key: "model", label: "Model", render: (r) => h("span", { class: "mono", style: "font-size:12px" }, r.model) },
      { key: "kind", label: "Kind" },
      { key: "prompt_tokens", label: "Prompt", num: true, render: (r) => fmtInt(r.prompt_tokens) },
      { key: "prefill_tps", label: "Read t/s", num: true, render: (r) => fx(r.prefill_tps, 1) },
      { key: "out_tokens", label: "Out", num: true, render: (r) => fmtInt(r.out_tokens) },
      { key: "gen_tps", label: "Write t/s", num: true, render: (r) => fx(r.gen_tps, 1) },
      { key: "total_s", label: "Took", num: true, render: (r) => (r.total_s == null ? "–" : `${fx(r.total_s, 1)} s`) },
      { key: "ok", label: "Result", render: (r) => statusEl(r.ok ? "done" : "failed", r.ok ? "ok" : (r.error || "failed").slice(0, 60)) },
    ], rows, { initial: "at" }) : h("p", { class: "muted" }, data.pool ? "No calls yet." : "The calls log needs the pool: set LEXFLOW_LLM_NODES."));
  }
  async function load() {
    data = await api("/api/compute");
    const t = data.totals;
    rc(pills,
      pill("nodes online", `${t.online} of ${t.nodes}`), pill("slots busy", `${t.busy} of ${t.slots}`),
      pill("calls in the last hour", fmtInt(t.calls_1h)), pill("embeddings", data.embed_node || "–", "always on one node"));
    rc(notes,
      !data.pool ? h("div", { class: "notice" }, icon("info"), h("div", {}, data.note || "No pool configured.")) : null,
      data.refused && data.refused.length ? h("div", { class: "notice" }, icon("info"), h("div", {}, "Refused entries of LEXFLOW_LLM_NODES: ", data.refused.join("; "))) : null,
      data.overlay ? h("p", { class: "muted" }, `Nodes are designated in the ${data.overlay.kind} admin (group ${data.overlay.group}); there is no add-node button here.`) : null);
    rc(cards, ...data.nodes.map(nodeCard));
    const names = data.nodes.map((n) => n.name), models = [...new Set(data.nodes.flatMap((n) => n.models.map((m) => m.name)))].sort();
    const keep = (sel, vals, all) => { const v = sel.value; rc(sel, h("option", { value: "" }, all), ...vals.map((x) => h("option", { value: x }, x))); sel.value = vals.includes(v) ? v : ""; };
    keep(nodeSel, names, "All nodes"); keep(modelSel, models, "All models");
    await loadRecent();
  }
  onRefresh(load);
  await load();
}

// =============================================================== PIPELINE
// lexflow as a Petri net (GET /api/pipeline): each circle is a store and its number the tokens it holds, each bar a
// job that moves tokens from the stores it reads (arrows in) to those it writes (arrows out); the compute pool is the
// band underneath the jobs that call a model.  Drawn from the payload, polled every 15 s while the page is open.
const PIPE = { x0: 140, y0: 66, colW: 180, rowH: 100, r: 27, barW: 12, barH: 44, width: 1130 };
const PIPE_COLS = ["Sources", "Index & research", "Drafts", "Verified", "Ready", "Published"];
const PIPE_STATE = { never: ["todo", "Never run"], running: ["running", "Running"], queued: ["queued", "Queued"],
  done: ["done", "Last run finished"], failed: ["failed", "Last run failed"], cancelled: ["optional", "Last run cancelled"] };
const PIPE_FLAG = { force: "Redo", no_llm: "Skip models", regulations: "+ regulations", full: "Full resend", drafts: "+ drafts",
  single_pass: "Single pass", bot: "Bot flag (bot group only)" };
const SVGNS = "http://www.w3.org/2000/svg";
let pipeTimer = null;
function sv(tag, attrs = {}, ...kids) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}
function compactNum(n) {
  if (n == null) return "?";
  const a = Math.abs(n);
  if (a >= 1e6) return `${(n / 1e6).toFixed(a >= 1e7 ? 0 : 1)}M`;
  if (a >= 1e4) return `${Math.round(n / 1e3)}k`;
  return Number(n).toLocaleString();
}
function wrapWords(text, max) {
  const lines = [];
  let cur = "";
  for (const w of String(text || "").split(/\s+/)) {
    if (cur && `${cur} ${w}`.length > max) { lines.push(cur); cur = w; } else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 2);
}
const secs = (s) => (s == null ? "–" : s < 90 ? `${Math.round(s)} s` : s < 5400 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`);
// a path through points with rounded corners (the long way round, for an arc back to the left)
function roundedPath(pts, rad = 10) {
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const [px, py] = pts[i - 1], [x, y] = pts[i], [nx, ny] = pts[i + 1];
    const l1 = Math.hypot(x - px, y - py) || 1, l2 = Math.hypot(nx - x, ny - y) || 1, r = Math.min(rad, l1 / 2, l2 / 2);
    d += ` L${x - ((x - px) / l1) * r},${y - ((y - py) / l1) * r} Q${x},${y} ${x + ((nx - x) / l2) * r},${y + ((ny - y) / l2) * r}`;
  }
  const last = pts[pts.length - 1];
  return `${d} L${last[0]},${last[1]}`;
}

async function viewPipeline() {
  clearInterval(pipeTimer);
  const notes = h("div");
  const chart = h("div", { class: "pipe-scroll" });
  const legend = h("div", { class: "legend pipe-legend" });
  const side = h("aside", { class: "card pipe-side", "aria-live": "polite", hidden: true });
  const layout = h("div", { class: "pipe-layout" }, h("section", { class: "card", "aria-label": "The pipeline as a Petri net" }, chart, legend), side);
  const lists = h("div", { class: "grid two pipe-lists" });
  const others = h("p", { class: "muted", style: "font-size:12.5px;margin:12px 2px 0" });
  const dialog = h("dialog", { class: "pipe-dialog", "aria-labelledby": "pipe-dialog-title" });
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Pipeline"),
      h("p", {}, "lexflow as a Petri net: each circle is a store and its number the tokens it holds now; each bar is a job that moves tokens from the stores it reads to the stores it writes. Click a store to open the page that lists it, a bar for its status, its log, the work waiting for it and what it can run."))),
    notes, layout, lists, others, dialog);
  const parts = { head: h("div", { class: "sec pipe-head" }), status: h("div"), info: h("div"), actions: h("div", { class: "sec" }), log: h("div") };
  side.append(...Object.values(parts));
  let data = null, panelFor = null, logKey = null;
  let sel = S.params.get("open") || null;
  const X = (col) => PIPE.x0 + col * PIPE.colW;
  const Y = (row) => PIPE.y0 + row * PIPE.rowH;
  const laneY = Y(4) + PIPE.r + 41, bandY = laneY + 14, laneX = X(5) + 70;
  const height = bandY + 40 + 12;
  const place = (id) => data.places.find((p) => p.id === id);
  const trans = (id) => data.transitions.find((t) => t.id === id);
  const linkOf = (p) => { const name = (p.href || "").split("?")[0].split("/")[1]; return routes[name] ? p.href : null; };

  function select(id) {
    sel = id;
    try { history.replaceState(null, "", id ? `#/pipeline?open=${encodeURIComponent(id)}` : "#/pipeline"); } catch (e) { /* not allowed */ }
    drawChart();
    drawPanel();
    if (id && matchMedia("(max-width: 1080px)").matches) side.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function arcPaths(t) {
    // the arrows of a transition: in from each place it reads, out to each place it writes
    const bx = X(t.col), by = Y(t.row), out = [];
    const spread = (i, n) => (n > 1 ? Math.max(-16, Math.min(16, (i - (n - 1) / 2) * 10)) : 0);
    t.reads.forEach((pid, i) => {
      const p = place(pid);
      if (!p || p.band) return;
      const px = X(p.col), py = Y(p.row), ey = by + spread(i, t.reads.length), ex = bx - PIPE.barW / 2 - 2;
      if (px > bx) {        // a store to the right of the job (the coverage test reads the Wikibase): round the bottom lane
        out.push({ d: roundedPath([[px + PIPE.r, py], [laneX, py], [laneX, laneY], [bx - 26, laneY], [bx - 26, ey], [ex, ey]]), far: true });
        return;
      }
      const ang = Math.atan2(ey - py, ex - px), sx = px + PIPE.r * Math.cos(ang), sy = py + PIPE.r * Math.sin(ang);
      const k = Math.max(22, (ex - sx) * 0.5);
      out.push({ d: `M${sx},${sy} C${sx + k},${sy} ${ex - k},${ey} ${ex},${ey}`, far: Math.abs(p.col - t.col) > 1.6 || Math.abs(p.row - t.row) > 2.2 });
    });
    t.writes.forEach((pid, i) => {
      const p = place(pid);
      if (!p || p.band) return;
      const px = X(p.col), py = Y(p.row), sy = by + spread(i, t.writes.length), sx = bx + PIPE.barW / 2 + 2;
      const ang = Math.atan2(sy - py, sx - px), ex = px + (PIPE.r + 3) * Math.cos(ang), ey = py + (PIPE.r + 3) * Math.sin(ang);
      const k = Math.max(22, Math.abs(ex - sx) * 0.5);
      out.push({ d: `M${sx},${sy} C${sx + k},${sy} ${ex - k},${ey} ${ex},${ey}`, far: Math.abs(p.col - t.col) > 1.6 || Math.abs(p.row - t.row) > 2.2 });
    });
    return out;
  }
  function hot(id, on) {
    for (const a of chart.querySelectorAll(`[data-arc="${CSS.escape(id)}"]`)) {
      const lit = on || id === sel;
      a.classList.toggle("hot", lit);
      a.setAttribute("marker-end", `url(#${lit ? "pipe-head-hot" : "pipe-head"})`);
    }
  }
  function placeTip(evt, p) {
    showTip(evt, [h("div", { style: "font-weight:600" }, p.label), h("div", { class: "v" }, p.count == null ? "–" : fmtInt(p.count)),
      h("div", { class: "k" }, p.meaning), p.detail ? h("div", { class: "k", style: "margin-top:4px" }, p.detail) : null,
      linkOf(p) ? h("div", { class: "k", style: "margin-top:4px" }, "Click to open the list") : null]);
  }
  function barTip(evt, t) {
    const [, word] = PIPE_STATE[t.status.state] || ["todo", t.status.state];
    showTip(evt, [h("div", { style: "font-weight:600" }, t.label), h("div", { class: "k" }, word + (t.status.active && t.status.active.status === "running" ? ` · ${pct(t.status.active.progress)}` : "")),
      t.waiting && t.waiting.text ? h("div", { class: "k", style: "margin-top:4px" }, t.waiting.text) : null,
      t.external ? h("div", { class: "k", style: "margin-top:4px" }, "Writes outside lexflow") : null,
      h("div", { class: "k", style: "margin-top:4px" }, "Click for status, log and actions")]);
  }
  function drawChart() {
    const svg = sv("svg", { viewBox: `0 0 ${PIPE.width} ${height}`, role: "img", "aria-label": "Pipeline: stores and the jobs that move tokens between them" });
    const defs = sv("defs");
    for (const [id, cls] of [["pipe-head", "pipe-arrow"], ["pipe-head-hot", "pipe-arrow hot"]]) {
      defs.append(sv("marker", { id, viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" },
        sv("path", { d: "M0,1 L9,5 L0,9 z", class: cls })));
    }
    svg.append(defs);
    PIPE_COLS.forEach((c, i) => svg.append(sv("text", { x: X(i), y: 20, class: "pipe-col" }, c)));
    // the compute band, and a dotted spine from it up to each column of jobs that call a model
    const pool = place("compute");
    const arcs = sv("g"), spines = sv("g"), bars = sv("g"), stores = sv("g");
    if (pool) {
      const band = sv("a", { href: "#/compute", class: "pipe-band", "aria-label": `Compute pool: ${pool.detail || ""}` },
        sv("rect", { x: 16, y: bandY, width: PIPE.width - 32, height: 40, rx: 8 }),
        sv("text", { x: 30, y: bandY + 24, class: "pipe-band-title" }, "Compute pool"),
        sv("text", { x: 130, y: bandY + 24, class: "pipe-band-sub" }, pool.detail || ""));
      band.addEventListener("pointermove", (e) => placeTip(e, pool));
      band.addEventListener("pointerleave", hideTip);
      svg.append(band);
      const cols = {};
      for (const t of data.transitions.filter((t) => t.model)) (cols[t.col] = cols[t.col] || []).push(t);
      for (const ts of Object.values(cols)) {
        const top = ts.reduce((a, b) => (b.row < a.row ? b : a));
        const optional = ts.every((t) => t.model === "optional");
        spines.append(sv("path", { d: `M${X(top.col)},${bandY} L${X(top.col)},${Y(top.row) + PIPE.barH / 2}`, class: `pipe-spine${optional ? " optional" : ""}` }));
      }
    }
    for (const t of data.transitions) {
      for (const a of arcPaths(t)) {
        const on = t.id === sel;
        arcs.append(sv("path", { d: a.d, "data-arc": t.id, class: `pipe-arc${a.far ? " far" : ""}${on ? " hot" : ""}`, "marker-end": `url(#${on ? "pipe-head-hot" : "pipe-head"})` }));
      }
    }
    for (const t of data.transitions) {
      const bx = X(t.col), by = Y(t.row), st = t.status.state, act = t.status.active;
      const [, word] = PIPE_STATE[st] || ["todo", st];
      const g = sv("g", { class: `pipe-bar ${st}${t.id === sel ? " sel" : ""}`, tabindex: 0, role: "button",
        "aria-label": `${t.label}: ${word}${t.external ? ", writes outside lexflow" : ""}`, "data-t": t.id });
      g.append(sv("rect", { class: "hit", x: bx - 18, y: by - PIPE.barH / 2 - 6, width: 36, height: PIPE.barH + 12, rx: 5 }),
        sv("rect", { class: "body", x: bx - PIPE.barW / 2, y: by - PIPE.barH / 2, width: PIPE.barW, height: PIPE.barH, rx: 2 }));
      if (st === "running" && act) {
        const hh = Math.max(3, (act.progress || 0) * PIPE.barH);
        g.append(sv("rect", { class: "fill", x: bx - PIPE.barW / 2, y: by + PIPE.barH / 2 - hh, width: PIPE.barW, height: hh, rx: 2 }));
      }
      if (t.external) g.append(sv("text", { x: bx + PIPE.barW / 2 + 3, y: by - PIPE.barH / 2 + 8, class: "pipe-ext" }, "↗"));
      wrapWords(t.label, 13).forEach((line, i) => g.append(sv("text", { x: bx, y: by + PIPE.barH / 2 + 14 + i * 12, class: "pipe-bar-label" }, line)));
      g.addEventListener("click", () => select(t.id));
      g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(t.id); } });
      g.addEventListener("pointerenter", () => hot(t.id, true));
      g.addEventListener("pointerleave", () => { hot(t.id, false); hideTip(); });
      g.addEventListener("pointermove", (e) => barTip(e, t));
      bars.append(g);
    }
    for (const p of data.places.filter((p) => !p.band)) {
      const px = X(p.col), py = Y(p.row), href = linkOf(p);
      const cls = `pipe-place${p.count == null ? " unknown" : ""}${p.error ? " error" : ""}${p.id === "ready" && p.count ? " ready" : ""}`;
      const g = href ? sv("a", { href, class: cls, "aria-label": `${p.label}: ${p.count == null ? "not counted" : fmtInt(p.count)}` })
        : sv("g", { class: cls, tabindex: 0, "aria-label": `${p.label}: ${p.count == null ? "not counted" : fmtInt(p.count)}` });
      g.append(sv("circle", { cx: px, cy: py, r: PIPE.r }), sv("text", { x: px, y: py, class: "pipe-count" }, compactNum(p.count)));
      wrapWords(p.label, 16).forEach((line, i) => g.append(sv("text", { x: px, y: py + PIPE.r + 15 + i * 13, class: "pipe-label" }, line)));
      if (p.id === "ready") g.addEventListener("click", (e) => { e.preventDefault(); hideTip(); select("wikibase"); });
      g.addEventListener("pointermove", (e) => placeTip(e, p));
      g.addEventListener("pointerleave", hideTip);
      stores.append(g);
    }
    svg.append(spines, arcs, bars, stores);
    rc(chart, svg);
  }
  function drawLegend() {
    const bar = (cls, word) => h("span", {}, h("span", { class: `sw pipe-sw ${cls}` }), word);
    rc(legend,
      h("span", {}, h("span", { class: "sw pipe-sw store" }), "store (its tokens)"),
      bar("done", "job: idle"), bar("running", "running"), bar("queued", "queued"), bar("failed", "last run failed"), bar("never", "never run"),
      h("span", {}, h("strong", { style: "margin-right:4px" }, "↗"), "writes outside lexflow"),
      h("span", {}, h("span", { class: "sw pipe-sw spine" }), "calls a model on the compute pool"),
      h("span", { class: "about" }, `Counts as of ${new Date(data.cached_at).toLocaleTimeString()} (kept ${data.ttl} s, fresh after a job ends); job states are live. Dashed arrows are the long ones; hover a job to light up its arrows.`));
  }
  function drawNotes() {
    const ow = data.other_work || [];
    rc(notes,
      ow.length ? h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Other work running in the container: "),
        "logs written in the last 10 minutes by jobs not started from this dashboard: ",
        ow.slice(0, 8).map((w) => `${w.name} (${secs(w.ago_s)} ago)`).join(", "), ow.length > 8 ? ` and ${ow.length - 8} more` : "")) : null,
      data.running.length ? h("p", { class: "muted", style: "margin:0 0 12px" }, `${data.running.length} dashboard job${data.running.length === 1 ? "" : "s"} running or queued: `,
        ...data.running.map((j, i) => [i ? ", " : "", h("a", { href: `#/job/${j.id}` }, `#${j.id} ${j.step}`)])) : null);
  }
  function drawLists() {
    rc(lists,
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Stores"), h("p", {}, "What each circle holds now."))),
        h("div", { class: "card-pad" }, sortableTable([
          { key: "label", label: "Store", render: (p) => (linkOf(p) ? h("a", { href: p.href, onclick: (e) => { if (p.id === "ready") { e.preventDefault(); select("wikibase"); } } }, p.label) : p.label) },
          { key: "count", label: "Holds", num: true, render: (p) => (p.count == null ? "–" : fmtInt(p.count)) },
          { key: "detail", label: "What", render: (p) => h("span", { class: "ink-2", style: "font-size:12.5px" }, p.detail || p.meaning) }], data.places))),
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Jobs"), h("p", {}, "Each bar of the chart; click one for its panel."))),
        h("div", { class: "card-pad" }, sortableTable([
          { key: "label", label: "Job", render: (t) => [t.label, t.external ? " ↗" : ""] },
          { key: "state", label: "Status", sort: (t) => t.status.state, render: (t) => statusEl(...(PIPE_STATE[t.status.state] || ["todo", t.status.state])) },
          { key: "waiting", label: "Work waiting", sort: (t) => t.waiting.count, render: (t) => h("span", { class: "ink-2", style: "font-size:12.5px" }, t.waiting.text) }],
        data.transitions, { onRow: (t) => select(t.id) }))));
    rc(others, data.other_steps.length ? ["Steps not on the chart (they feed the map, the scores or the index tags): ", data.other_steps.map((s) => s.title).join(", "), "; run them from ", h("a", { href: "#/setup" }, "Setup"), "."] : null);
  }
  function drawPanel() {
    const t = sel ? trans(sel) : null;
    layout.classList.toggle("open", !!t);
    side.hidden = !t;
    if (!t) { panelFor = null; return; }
    if (panelFor !== t.id) { drawHead(t); drawActions(t); panelFor = t.id; logKey = null; }
    drawStatus(t);
    drawInfo(t);
    loadLog(t);
  }
  function drawHead(t) {
    rc(parts.head,
      h("div", { class: "row-flex" }, h("h2", { style: "margin:0" }, t.label),
        h("button", { class: "icon-btn right", type: "button", "aria-label": "Close the panel", onclick: () => select(null) }, "×")),
      h("div", { class: "muted", style: "font-size:12.5px;margin-top:2px" }, t.title),
      h("div", { class: "row-flex", style: "margin-top:6px;gap:6px" },
        t.external ? h("span", { class: "tag" }, "writes outside lexflow ↗") : null,
        t.model ? h("span", { class: "tag" }, t.model === "optional" ? "may call a model" : "uses the compute pool") : null,
        t.id === "plan" ? h("span", { class: "tag" }, "dry runs only") : null));
  }
  function jobLine(j, label) {
    if (!j) return null;
    return [h("dt", {}, label), h("dd", {}, h("a", { href: `#/job/${j.id}` }, `#${j.id}`), ` ${j.status}${j.real === false && ["wikibase", "publish"].includes(j.step) ? " (dry run)" : j.real && ["wikibase", "publish"].includes(j.step) ? " (real)" : ""}`,
      j.finished_at ? ` · ${ago(j.finished_at)}` : j.started_at ? ` · started ${ago(j.started_at)}` : "", j.seconds != null ? ` · ${secs(j.seconds)}` : "")];
  }
  function drawStatus(t) {
    const st = t.status, act = st.active, last = st.last;
    const [ic, word] = PIPE_STATE[st.state] || ["todo", st.state];
    const j = act || last;
    rc(parts.status, h("div", { class: "sec" },
      h("div", { class: "row-flex" }, statusEl(ic, act && act.via ? `Running as part of quickstart #${act.id}` : word)),
      j && j.message ? h("div", { class: "ink-2", style: "font-size:12.5px;margin-top:4px;overflow-wrap:anywhere" }, j.message) : null,
      act && act.status === "running" ? h("div", { class: "meter" }, h("span", { style: `width:${Math.round((act.progress || 0) * 100)}%` })) : null,
      h("dl", { class: "kv", style: "margin-top:8px" }, jobLine(act, "Now"), jobLine(last, "Last finished"),
        !j ? [h("dt", {}, "Jobs"), h("dd", {}, "never run from the dashboard")] : null)));
  }
  function placeLinks(ids) {
    return ids.flatMap((id, i) => { const p = place(id); if (!p) return []; const href = linkOf(p); return [i ? ", " : "", href ? h("a", { href }, p.label) : p.label]; });
  }
  // h() flattens one level of children: the rows and their values are flattened here
  function kvRows(rows) { return h("dl", { class: "kv" }, rows.filter(Boolean).flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, [v].flat(Infinity))])); }
  function scopeWords(sc) { sc = sc || {}; return `${sc.states && sc.states.length ? `states ${sc.states.join(", ")}` : "every state"}${sc.drafts ? ", with drafts" : ""}${sc.full ? ", full resend" : ""}${sc.single_pass ? ", single pass" : ""}`; }
  function drawInfo(t) {
    const wb = data.wikibase || {}, pub = data.publish || {};
    const blocks = [h("div", { class: "sec" }, kvRows([
      ["Reads", t.reads.length ? placeLinks(t.reads) : "outside data"],
      (t.also || []).length ? ["Also reads", [placeLinks(t.also), h("span", { class: "muted" }, " (not drawn)")]] : null,
      ["Writes", placeLinks(t.writes)],
      ["Work waiting", t.waiting.text || "–"],
      t.cost ? ["Cost", t.cost] : null]))];
    if (t.id === "plan" || t.id === "wikibase") {
      const d = wb.dry_run;
      blocks.push(h("div", { class: "sec" }, h("h3", {}, "Last dry run"),
        d ? kvRows([
          ["When", `${d.generated} (${secs(d.age_s)} ago)${d.job ? `, job #${d.job}` : ""}`],
          ["Scope", scopeWords(d.scope)],
          ["Creates", `${fmtInt(d.creates)} (pass 1)`], ["Updates", `${fmtInt(d.updates)} (pass 2)`],
          ["Held", `${fmtInt(d.held_count)} by the lint: skipped, never written`],
          ["Dropped", `${fmtInt(d.dropped_snaks)} statements naming an item with no id`],
          Object.keys(d.failures_by_code || {}).length ? ["Failures", Object.entries(d.failures_by_code).map(([k, n]) => `${k} ${n}`).join(", ")] : null,
          ["Push", d.refusal ? h("span", { style: "color:var(--critical)" }, `not now: ${d.refusal}`) : `allowed for ${secs(d.expires_in_s)} more`]])
          : h("p", { class: "muted", style: "margin:4px 0" }, "No dry run recorded here yet: a push needs one from the last 24 hours."),
        wb.plan ? h("p", { class: "muted", style: "font-size:12px;margin:8px 0 0;overflow-wrap:anywhere" },
          `Plan file ${wb.plan.path}: ${wb.plan.dry_run ? "a dry run" : "a real push"} of ${wb.plan.generated}, ${fmtInt(wb.plan.items)} items, ${fmtInt(wb.plan.would_write)} to write.`) : null,
        h("p", { class: "muted", style: "font-size:12px;margin:4px 0 0;overflow-wrap:anywhere" }, wb.lint
          ? `Lint report ${wb.lint.generated}: ${fmtInt(wb.lint.held_count)} held${Object.keys(wb.lint.held_by_kind || {}).length ? ` (${Object.entries(wb.lint.held_by_kind).map(([k, n]) => `${k} ${n}`).join(", ")})` : ""}.`
          : "No lint report yet: the dry run makes one."),
        wb.credentials === false ? h("p", { class: "muted", style: "font-size:12px" }, "WIKIBASE_BOT_USER and WIKIBASE_BOT_PASSWORD are not set: a push would be refused.") : null));
    }
    if (t.id === "publish") {
      const d = pub.dry_run;
      blocks.push(h("div", { class: "sec" }, h("h3", {}, "Last dry run"),
        d ? kvRows([["When", `${d.generated} (${secs(d.age_s)} ago)`], ["Pages", fmtInt(d.pages)],
          ["Would write", fmtInt(d.would_write)], ["Unchanged", d.compared ? fmtInt(d.unchanged) : "not compared"],
          d.unread ? ["Not read", fmtInt(d.unread)] : null, ["Corrections", d.corrections || "–"],
          ["Publish", d.refusal ? h("span", { style: "color:var(--critical)" }, `not now: ${d.refusal}`) : `allowed for ${secs(d.expires_in_s)} more`]])
          : h("p", { class: "muted", style: "margin:4px 0" }, "No dry run recorded yet: a publish needs one from the last 24 hours."),
        !pub.corrections_set ? h("p", { class: "muted", style: "font-size:12px" }, `LEXFLOW_CORRECTIONS is ${pub.corrections_problem || "not set"}: nothing is written, a dry run included, until it is an address readers can reach.`) : null));
    }
    blocks.push(h("details", { class: "sec" }, h("summary", { style: "cursor:pointer" }, "About this step"), h("p", { class: "ink-2", style: "font-size:12.5px" }, t.why)));
    rc(parts.info, ...blocks);
  }
  function drawActions(t) {
    const rows = t.actions.map((a) => {
      if (a.kind === "link") return h("div", { class: "pipe-action" }, h("a", { class: "btn", href: a.href }, a.label));
      const values = {};
      const opts = h("div", { class: "row-flex", style: "gap:6px 10px" });
      for (const p of a.params || []) {
        if (["states", "places", "questions"].includes(p)) {
          const key = `lexflow-${{ states: "st", places: "pl", questions: "qs" }[p]}-${t.step}`;
          const def = p === "states" && t.step !== "wikibase" ? "va" : "";
          const inp = h("input", { type: "text", value: store(key) ?? def, style: "width:150px",
            placeholder: p === "states" ? (t.step === "wikibase" ? "states (blank: all)" : "states: va,dc or all") : p, "aria-label": `${p} for ${t.label}` });
          values[p] = () => { store(key, inp.value); return inp.value || undefined; };
          opts.append(inp);
        } else {
          const cb = h("input", { type: "checkbox" });
          values[p] = () => cb.checked;
          opts.append(h("label", { class: "check" }, cb, PIPE_FLAG[p] || p));
        }
      }
      const out = h("span", { class: "muted", style: "font-size:12.5px" });
      const btn = h("button", { class: `btn ${a.confirm ? "danger" : a.kind === "dry_run" ? "primary" : ""}`, type: "button", onclick: async () => {
        if (a.confirm) { openConfirm(t, a, out, values); return; }
        const args = { ...a.args, ...Object.fromEntries(Object.entries(values).map(([k, f]) => [k, f()])) };
        if (a.kind === "run" && !confirm(`Start “${t.title}”${args.states ? ` for ${args.states}` : ""}? It runs as a background job.`)) return;
        btn.disabled = true;
        try { const id = await startRunJob(t.step, args); rc(out, "queued as ", h("a", { href: `#/job/${id}` }, `job #${id}`)); await load(); }
        catch (e) { rc(out, h("span", { style: "color:var(--critical)" }, e.message)); }
        btn.disabled = false;
      } }, a.label);
      return h("div", { class: "pipe-action" }, opts.childNodes.length ? opts : null, h("div", { class: "row-flex" }, btn, out));
    });
    rc(parts.actions, h("h3", { style: "margin-bottom:6px" }, "Actions"), rows.length ? rows : h("p", { class: "muted" }, "Nothing to run from here."),
      t.id === "wikibase" ? h("p", { class: "muted", style: "font-size:12px;margin:8px 0 0" }, "The dry run comes first: the push asks you to confirm its numbers, and is refused if the graph, the lint or the Wikibase record changed since.") : null);
  }
  function openConfirm(t, a, out, values = {}) {
    const push = a.confirm === "wikibase";
    const chosen = Object.fromEntries(Object.entries(values).map(([k, f]) => [k, f()]));
    const d = push ? (data.wikibase || {}).dry_run : (data.publish || {}).dry_run;
    const why = !d ? "No dry run has been recorded yet: run the dry run first." : d.refusal;
    const site = push ? (data.wikibase || {}).site : (data.publish || {}).site;
    const host = (() => { try { return new URL(site).hostname; } catch (e) { return site || "the site"; } })();
    const go = h("button", { class: "btn danger", type: "button", disabled: !!why, onclick: async () => {
      go.disabled = true;
      const args = push ? { ...a.args, ...chosen, dry_run_id: d.id, states: (d.scope.states || []).join(","), drafts: !!d.scope.drafts, full: !!d.scope.full, single_pass: !!d.scope.single_pass }
        : { ...a.args, dry_run_id: d.id };
      try { const id = await startRunJob(t.step, args); dialog.close(); rc(out, "started as ", h("a", { href: `#/job/${id}` }, `job #${id}`)); await load(); }
      catch (e) { rc(msg, h("span", { style: "color:var(--critical)" }, e.message)); go.disabled = false; }
    } }, push ? "Push for real" : "Publish for real");
    const msg = h("p", { style: "margin:10px 0 0" }, why ? h("span", { style: "color:var(--critical)" }, why) : null);
    const numbers = !d ? null : push ? kvRows([
      ["Dry run", `${d.generated} (${secs(d.age_s)} ago)`], ["Scope", scopeWords(d.scope)], ["Items", fmtInt(d.items)],
      ["Creates", `${fmtInt(d.creates)} new items (pass 1)`], ["Updates", `${fmtInt(d.updates)} items’ statements (pass 2)`],
      ["Held", `${fmtInt(d.held_count)} items the lint holds: skipped, never written`],
      ["Dropped", `${fmtInt(d.dropped_snaks)} statements that name an item with no id yet`],
      chosen.bot ? ["Bot flag", "on: bot=1 is sent, which the wiki honours only for an account in its bot group"] : null])
      : kvRows([["Dry run", `${d.generated} (${secs(d.age_s)} ago)`], ["Pages", fmtInt(d.pages)], ["Writes", `${fmtInt(d.would_write)} pages`],
        ["Unchanged", d.compared ? fmtInt(d.unchanged) : "not compared"], ["Corrections", d.corrections || "–"]]);
    rc(dialog, h("form", { method: "dialog", class: "card-pad" },
      h("h2", { id: "pipe-dialog-title" }, push ? `Push to ${host}?` : `Publish to ${host}?`),
      h("p", { class: "ink-2" }, push
        ? `This writes to ${site} with the bot account: a fresh lint, then pass 1 (creates the new items: labels, descriptions and their legal identifier) and pass 2 (writes every item’s statements). It never deletes or merges an item: on the items lexflow owns, pass 2 replaces their statements; on the others it only adds the statements they lack.`
        : `This writes the ${(data.publish || {}).namespace || "lexflow"}: pages to ${site} with the bot account, and no page outside that namespace. It never deletes a page.`),
      numbers,
      h("p", { class: "muted", style: "font-size:12.5px" }, push
        ? "The job is refused if the graph, the lint or the Wikibase record has changed since this dry run."
        : "The job is refused if the pages have changed since this dry run."),
      msg,
      h("div", { class: "row-flex", style: "justify-content:flex-end;margin-top:14px" }, h("button", { class: "btn", value: "cancel" }, "Cancel"), go)));
    dialog.showModal();
  }
  async function loadLog(t) {
    const j = t.status.active || t.status.last;
    if (!j) { rc(parts.log); logKey = null; return; }
    const key = `${j.id}:${j.status}:${j.progress}:${j.message}`;
    if (key === logKey) return;
    logKey = key;
    try {
      const r = await api(`/api/jobs/${j.id}?lines=30`);
      if (sel !== t.id) return;
      const pre = h("pre", { class: "log" }, r.log || "(no output)");
      rc(parts.log, h("div", { class: "sec" }, h("div", { class: "row-flex" }, h("h3", {}, `Log of job #${j.id}`), h("a", { class: "right", href: `#/job/${j.id}`, style: "font-size:12px" }, "Full log")), pre));
      pre.scrollTop = pre.scrollHeight;
    } catch (e) { rc(parts.log, h("div", { class: "sec muted" }, `No log: ${e.message}`)); }
  }
  async function load() {
    data = await api("/api/pipeline");
    drawNotes();
    drawChart();
    drawLegend();
    drawLists();
    if (sel && !trans(sel)) sel = null;
    drawPanel();
  }
  onRefresh(() => load().catch(() => {}));
  await load();
  pipeTimer = setInterval(() => {
    if (!(location.hash || "").startsWith("#/pipeline")) { clearInterval(pipeTimer); pipeTimer = null; return; }
    load().catch(() => {});
  }, 15000);
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
// ----------------------------------------------------------------- coverage
// The coverage matrix (lexflow.ask.coverage): questions x states and places, a verdict per cell, and on a click the
// probe counts, the answer, the score and what is missing.
const VERDICT_WORD = { adequate: "Adequate", partial: "Partial", none: "None", draft: "Partial, on drafts alone" };
function verdictCell(cell, onpick, picked) {
  if (!cell) return h("td", { class: "num muted" }, "–");
  // the fourth shade: a partial cell whose process items are all drafts (a single-tier model or an asked answer)
  const v = cell.verdict || "none", shade = cell.draft && v === "partial" ? "draft" : v;
  const miss = (cell.missing || []).join(", ");
  return h("td", { class: `cov-cell cov-${shade}${picked ? " picked" : ""}`, title: `${VERDICT_WORD[shade]}${miss ? `; missing ${miss}` : ""}${cell.composite != null ? `; composite ${fx(cell.composite)}` : ""}` },
    h("button", { type: "button", class: "cov-btn", "aria-label": `${cell.qid} ${cell.col}: ${VERDICT_WORD[shade]}${miss ? `, missing ${miss}` : ""}`, onclick: onpick },
      h("span", { class: "cov-mark" }, shade === "adequate" ? "A" : shade === "draft" ? "D" : shade === "partial" ? "P" : "–"),
      cell.composite != null ? h("span", { class: "cov-score" }, fx(cell.composite)) : null,
      miss ? h("span", { class: "cov-miss" }, miss) : null));
}
function coverageDetail(d, row, q) {
  const p = row.probe || {}, c = p.counts || {}, s = row.score, a = p.answer;
  const kv = (k, v) => h("div", { class: "role-row" }, h("span", { class: "k" }, k), h("span", {}, v == null ? "–" : String(v)));
  const counts = h("div", { class: "cov-counts" },
    kv("Wikibase source", `${p.source || "none"}${p.sparql_calls ? ` (${p.sparql_calls} queries)` : ""}`),
    kv("Process items", (p.processes || []).length ? p.processes.map((x) => `${x.key} [${x.status || "no status"}]`).join("; ") : "none for this topic and jurisdiction"),
    kv("Steps / with bearer", `${c.steps ?? 0} / ${c.steps_with_bearer ?? 0}`),
    kv("Bearers resolved to bodies / with channels", `${c.bearers_resolved ?? 0} / ${c.bodies_with_channels ?? 0}`),
    kv("Deadlines / with quotes", `${c.deadlines ?? 0} / ${c.deadlines_quoted ?? 0}`),
    kv("Forms · fees · escalation · cited sections", `${c.forms ?? 0} · ${c.fees ?? 0} · ${c.escalation ?? 0} · ${c.sections ?? 0}`),
    kv("Who do I ask", p.who ? `${p.who.source || "no store"}: ${p.who.roles} state roles, ${p.who.local} local, ${p.who.bodies_with_channels} bodies with channels` : "–"),
    kv("Gold", p.gold || "–"), kv("Route", p.route ? `${p.route.jurisdiction}${p.route.gov_id ? "/" + p.route.gov_id : ""} · topic ${p.route.topic || "?"} (${p.route.topic_by || "none"})` : "–"),
    kv("Timing", p.timings ? Object.entries(p.timings).map(([k, v]) => `${k} ${v}s`).join(" · ") : `${row.seconds} s`));
  const kinds = h("div", { class: "cov-kinds" }, (d.kinds || []).map((k) => {
    const need = (q.needs || []).includes(k), have = (p.kinds || {})[k] || (s && s.kinds && s.kinds[k]);
    return h("span", { class: `badge ${!need ? "muted" : have ? "ok" : "warn"}`, title: !need ? "not needed" : have ? "present" : "missing" }, `${k}${!need ? "" : have ? " ✓" : " ✗"}`);
  }));
  const score = s ? h("div", { class: "cov-counts" },
    kv("Composite", fx(s.composite)), kv("Vital nuggets quoted", pct(s.vital_recall)), kv("All nuggets quoted", pct(s.nugget_recall)),
    kv("Citation precision / support", `${pct(s.citation_precision)} / ${pct(s.citation_support)}`), kv("Gold sections in top 10", pct(s["recall@10"])),
    kv("Fees and deadlines", pct(s.slot_match)), kv("Quotes shown (of them from the wiki)", `${s.quotes_shown} (${s.wiki_quotes})`), kv("Summary claims", s.claims),
    kv("Nuggets hit", (s.nuggets_hit || []).join(", ") || "none")) : h("p", { class: "muted" }, row.arm === "ollama" ? "No gold for this cell: coverage only." : "Coverage-only cell (no Ollama answer).");
  const claims = a && a.summary && a.summary.claims ? h("ul", { style: "padding-left:18px" }, a.summary.claims.map((cl) => h("li", {}, cl.text, " ", h("span", { class: "muted mono" }, (cl.quotes || []).join(" "))))) : null;
  const quotes = a && a.quotes ? h("details", {}, h("summary", {}, `${a.quotes.length} quotes (${a.chosen?.length || 0} sections chosen: ${(a.chosen || []).join(", ")})`),
    h("ul", { style: "padding-left:18px" }, a.quotes.slice(0, 40).map((x) => h("li", {}, h("span", { class: "mono" }, `[${x.id}] ${x.section || x.label || ""} `), String(x.text || "").slice(0, 300))))) : null;
  return h("section", { class: "card", id: "cov-detail" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, `${q.text}`), h("p", {}, `${row.state}${row.gov_id ? " / " + row.gov_id : ""} · ${row.arm} arm${row.model ? ` · ${row.model}` : ""}${row.node ? ` on ${row.node}` : ""} · verdict ${VERDICT_WORD[row.verdict] || row.verdict}${(row.missing || []).length ? ` · missing ${row.missing.join(", ")}` : ""}`))),
    h("div", { class: "card-pad" }, h("h3", {}, "What the question needs"), kinds, h("h3", {}, "Wikibase probe"), counts, h("h3", {}, "Score against the gold"), score,
      a ? [h("h3", {}, `Answer (${a.status || "–"})`), a.summary_error ? h("p", { class: "muted" }, `Summary failed: ${a.summary_error}`) : null, claims || h("p", { class: "muted" }, "No summary claims."), quotes] : null));
}
// ----------------------------------------------------------------- hypotheticals
// A computed answer (lexflow.scenarios): one select per dimension of a question family, the requirements with
// their offices, fees, order and citations, and "what matters most" (the one-at-a-time sensitivity ranking).
async function hypoFamilies() {
  if (!S.hypoFamilies) S.hypoFamilies = (await api("/api/hypo/families")).families || [];
  return S.hypoFamilies;
}
const HYPO_STATUS = { required: "ok", recommended: "ok", "may be required": "warn", "ask first": "warn", blocked: "warn", "not required": "muted" };
function hypoSource(s) {
  if (!s) return null;
  const words = s.quote ? `“${s.quote}”` : s.paraphrase ? `${s.paraphrase} (lexflow's paraphrase)` : "";
  return h("details", {}, h("summary", { class: "muted" }, s.citation || "source"),
    h("p", { style: "margin:4px 0" }, words), s.why_withheld ? h("p", { class: "muted", style: "margin:4px 0;font-size:12px" }, s.why_withheld) : null,
    h("p", { class: "muted", style: "margin:4px 0;font-size:12px" }, s.url ? h("a", { href: s.url, target: "_blank", rel: "noopener" }, s.url) : null,
      s.matched ? ` · matched by lexflow's software (${s.matched_by}${s.checked_on ? `, ${s.checked_on}` : ""})` : " · not matched"));
}
function hypoCard(fam, opts = {}) {
  const card = h("section", { class: "card", id: "hypo-card" });
  const loc0 = opts.locality || (fam.dimensions.find((d) => d.name === "locality") || { default: null }).default;
  let persona = opts.persona || fam.default_persona || (fam.personas[0] || {}).id;
  const sel = {};
  const personaSel = h("select", { "aria-label": "Persona" }, h("option", { value: "" }, "(no persona)"),
    fam.personas.map((p) => h("option", { value: p.id, selected: p.id === persona ? true : null }, p.label)));
  const variantBoxes = fam.variants.map((v) => h("label", { style: "display:flex;gap:6px;align-items:center" }, h("input", { type: "checkbox", value: v.id }), `Variant: ${v.label}`));
  const form = h("div", { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px 12px;margin:8px 0" });
  const out = h("div");
  function inScope(o, loc) { return !o.scope || !o.scope.locality || o.scope.locality.includes(loc); }
  const locOptions = (fam.dimensions.find((d) => d.name === "locality") || { options: [] }).options;
  function drawForm(values) {
    // the locality as a value ("staunton"), whether the form holds its code ("STN") or a value was passed in
    const loc = (locOptions.find((o) => o.code === values.locality) || {}).value || values.locality || loc0;
    if (!values.locality) values = { ...values, locality: (locOptions.find((o) => o.value === loc) || {}).code };
    rc(form, fam.dimensions.map((d) => {
      const s = h("select", { "aria-label": d.label, onchange: () => { if (d.name === "locality") { drawForm({ ...current(), locality: s.value, district: null }); } } },
        d.options.filter((o) => d.name === "locality" || inScope(o, loc)).map((o) => h("option", { value: o.code, selected: values[d.name] === o.code ? true : null },
          o.label + (o.class ? ` · ${o.class.replace("_", " ")}` : "") + (o.tag && o.tag !== "SRC" ? ` (${o.tag})` : ""))));
      sel[d.name] = s;
      return h("label", { style: "display:flex;flex-direction:column;gap:2px;font-size:13px" }, h("span", { class: "muted" }, d.label), s);
    }));
  }
  function current() { const v = {}; for (const [k, s] of Object.entries(sel)) v[k] = s.value; return v; }
  async function fromPersona() {
    persona = personaSel.value;
    if (!persona) return;
    const loc = (current().locality) ? fam.dimensions.find((d) => d.name === "locality").options.find((o) => o.code === current().locality)?.value : loc0;
    const r = await api(`/api/hypo/${encodeURIComponent(fam.id)}/run?persona=${encodeURIComponent(persona)}&locality=${encodeURIComponent(loc || loc0)}`);
    const v = {}; for (const [k, x] of Object.entries(r.inputs)) v[k] = x.code;
    drawForm(v);
    show(r);
  }
  async function run() {
    const q = new URLSearchParams(current());
    const vs = variantBoxes.map((b) => b.querySelector("input")).filter((i) => i.checked).map((i) => i.value);
    if (vs[0]) q.set("variant", vs[0]);
    rc(out, h("p", { class: "muted" }, "Computing…"));
    try { show(await api(`/api/hypo/${encodeURIComponent(fam.id)}/run?${q}`)); } catch (e) { rc(out, h("p", { class: "muted" }, String(e.message || e))); }
  }
  async function show(r) {
    const todo = r.requirements.filter((x) => x.status !== "not required");
    const rows = todo.map((x) => h("tr", {},
      h("td", { class: "num" }, x.order ?? "–"),
      h("td", {}, h("div", {}, x.title), x.deadline ? h("div", { class: "muted", style: "font-size:12px" }, x.deadline) : null, hypoSource(x.source)),
      h("td", {}, x.office.url ? h("a", { href: x.office.url, target: "_blank", rel: "noopener" }, x.office.label) : x.office.label),
      h("td", {}, h("span", { class: `badge ${HYPO_STATUS[x.status] || "muted"}` }, x.status), x.tag === "ASM" || x.assumptions.length ? h("div", { class: "muted", style: "font-size:11px" }, x.assumptions.join(" ")) : null),
      h("td", {}, x.fee.text, x.fee_source ? hypoSource(x.fee_source) : null)));
    const notReq = r.requirements.filter((x) => x.status === "not required");
    const sens = h("div", {}, h("p", { class: "muted" }, "Working out what matters most…"));
    rc(out,
      h("p", {}, h("strong", {}, `${r.counts.to_do} things to do`), ` (${r.counts.required} required, ${r.counts.possible} that the officials may require or that need a question first) · about ${r.order.timeline_days} days end to end (an estimate) · scenario `, h("span", { class: "mono" }, r.scenario)),
      r.blocked ? h("div", { class: "notice" }, icon("blocked"), h("div", {}, h("strong", {}, "Not allowed as set: "), r.requirements.filter((x) => x.status === "blocked").map((x) => x.title).join("; "))) : null,
      h("p", {}, r.fees.summary),
      h("div", { class: "table-wrap" }, h("table", { class: "data" }, h("thead", {}, h("tr", {}, ["#", "What", "From", "Status", "Fee"].map((t) => h("th", { scope: "col" }, t)))), h("tbody", {}, rows))),
      notReq.length ? h("p", { class: "muted" }, "Not required: " + notReq.map((x) => x.title).join("; ")) : null,
      r.appeals.length ? h("details", {}, h("summary", {}, "If something is refused"), h("ul", {}, r.appeals.map((a) => h("li", {}, `${a.table}: ${a.to}, ${a.deadline}`)))) : null,
      h("h3", {}, "What matters most"), sens,
      h("p", { class: "muted", style: "font-size:12px" }, `Assumptions: ${r.assumptions.join(", ") || "none"}. ${fam.status || ""}`));
    const q = new URLSearchParams({}); for (const [k, x] of Object.entries(r.inputs)) q.set(k, x.code);
    if (r.variant) q.set("variant", r.variant);
    try {
      const s = await api(`/api/hypo/${encodeURIComponent(fam.id)}/sens?${q}`);
      const max = Math.max(...s.ranking.map((x) => x.score), 0.001);
      rc(sens, h("div", { style: "display:grid;gap:6px" }, s.ranking.slice(0, 6).map((x) => h("div", {},
        h("div", { style: "display:flex;justify-content:space-between;font-size:13px" }, h("span", {}, x.label), h("span", { class: "muted" }, `±${x.swing_requirements} requirements · ±$${Math.round(x.swing_fees).toLocaleString()} · ±${x.swing_days} days${x.can_block ? " · can block" : ""}`)),
        h("div", { class: "bar" }, h("span", { style: `width:${Math.round(100 * x.score / max)}%` }))))));
    } catch (e) { rc(sens, h("p", { class: "muted" }, String(e.message || e))); }
  }
  personaSel.addEventListener("change", fromPersona);
  rc(card, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Computed answer for a fact pattern"),
      h("p", {}, `${fam.title}: pick the facts and lexflow works out what is needed, from whom, at what cost and in what order, from decision tables whose every rule cites a matched quote. Computed, not reviewed by a person; not legal advice.`))),
    h("div", { class: "card-pad" }, h("div", { class: "row-flex" }, personaSel, ...variantBoxes, h("button", { class: "btn", onclick: run }, "Compute")), form, out));
  drawForm({});
  if (persona) fromPersona();
  return card;
}
async function attachHypo(el, qid, govId) {
  const token = String(Math.random());
  el.dataset.hypo = token;                          // a later click replaces the detail: drop this card then
  const fams = await hypoFamilies().catch(() => []);
  const fam = fams.find((f) => (f.serves || {})[qid]);
  if (!fam || el.dataset.hypo !== token) return;
  const locDim = fam.dimensions.find((d) => d.name === "locality");
  const loc = govId ? (locDim.options.find((o) => o.gov_id === govId) || {}).value : null;
  el.append(h("div", { class: "spacer" }), hypoCard(fam, { locality: loc || undefined }));
}
async function viewHypo(familyId) {
  const fams = await hypoFamilies();
  const fam = fams.find((f) => f.id === familyId) || fams[0];
  if (!fam) { rc(view, h("div", { class: "notice" }, icon("info"), h("div", {}, "No question families (fixtures/families/)."))); return; }
  rc(view, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Hypotheticals"), h("p", {}, `${fam.dimensions.length} dimensions, ${fam.tables} decision tables, ${fam.rules} grounded rules; scenario grammar ${fam.grammar}.`))), hypoCard(fam));
}
async function viewCoverage(runId) {
  const body = h("div");
  rc(view, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Coverage"),
    h("p", {}, "Can we answer what people actually ask? For each question and state (or place): is there a Wikibase process for the topic with bearers, bodies, channels, deadlines, forms, fees and escalation, and does the local model's answer carry the gold facts. A = adequate, P = partial, – = none; the words are the kinds of facts still missing. Click a cell for the details."))), body);
  async function load() {
    const d = await api(`/api/coverage${runId ? `?run=${encodeURIComponent(runId)}` : ""}`);
    if (!d.run || !d.matrix) {
      rc(body, h("div", { class: "notice" }, icon("info"), h("div", {}, "No coverage run yet. Start one with ", h("code", {}, "lexflow run coverage --states va,dc"), " or the button below."),
        h("button", { class: "btn right", onclick: async () => { await startRunJob("coverage", { states: "va,dc", arm: "coverage" }); location.hash = "#/jobs"; } }, "Run the coverage probe")));
      return;
    }
    const m = d.matrix;
    // #/coverage?state=va: only that state's columns (the state and its researched places)
    const only = (S.params.get("state") || "").toLowerCase();
    const cols = Object.keys(m.columns).filter((c) => !only || c === only || c.startsWith(`${only}/`));
    const rowsBy = {};
    for (const r of d.rows) rowsBy[`${r.qid}|${r.state}${r.gov_id ? "/" + r.gov_id : ""}`] = r;
    const qs = {};
    for (const q of d.questions) qs[q.id] = q;
    let picked = store("lexflow-cov-pick") || null;
    const detail = h("div");
    const table = h("table", { class: "data cov-table" });
    function draw() {
      rc(table,
        h("thead", {}, h("tr", {}, h("th", { scope: "col" }, "Question"), cols.map((c) => h("th", { scope: "col" }, c.replace("/", " / "))))),
        h("tbody", {}, m.questions.map((q) => h("tr", {}, h("th", { scope: "row", title: q.text }, h("span", { class: "mono", style: "font-size:12px" }, q.id), h("span", { class: "muted", style: "display:block;font-size:12px" }, `${q.topic} · ${q.level}`)),
          cols.map((c) => { const key = `${q.id}|${c}`; return verdictCell(m.cells[key], () => { picked = key; store("lexflow-cov-pick", key); draw(); drawDetail(); document.getElementById("cov-detail")?.scrollIntoView({ block: "nearest" }); }, picked === key); })))));
    }
    function drawDetail() {
      const r = picked && rowsBy[picked];
      rc(detail, r ? coverageDetail(d, r, qs[r.qid] || { text: r.qid, needs: [] }) : h("p", { class: "muted" }, "Click a cell to see its probe, answer, score and what is missing."));
      if (r) attachHypo(detail, r.qid, r.gov_id);     // a question a family serves gets the computed-answer form
    }
    const summary = h("table", { class: "data" },
      h("thead", {}, h("tr", {}, ["Column", "Cells", "Adequate", "Partial", "None", "Top missing kinds", "Ollama cells", "Composite", "Vital recall", "Citation precision", "s / cell", "s / Ollama cell"].map((t) => h("th", { scope: "col" }, t)))),
      h("tbody", {}, cols.map((c) => { const x = m.columns[c], o = x.ollama || {}; return h("tr", {}, h("td", {}, c), h("td", { class: "num" }, x.cells), h("td", { class: "num" }, x.adequate || 0), h("td", { class: "num" }, x.partial || 0), h("td", { class: "num" }, x.none || 0),
        h("td", {}, (x.top_missing || []).map(([k, n]) => `${k} (${n})`).join(", ") || "–"), h("td", { class: "num" }, x.ollama_cells), h("td", { class: "num" }, x.ollama ? fx(o.composite) : "–"), h("td", { class: "num" }, x.ollama ? pct(o.vital_recall) : "–"), h("td", { class: "num" }, x.ollama ? pct(o.citation_precision) : "–"), h("td", { class: "num" }, fx(x.seconds_mean, 1)), h("td", { class: "num" }, x.ollama_seconds_mean ? fx(x.ollama_seconds_mean, 0) : "–")); })));
    const runs = h("select", { "aria-label": "Run", onchange: (e) => { location.hash = `#/coverage/${encodeURIComponent(e.target.value)}${only ? `?state=${only}` : ""}`; } }, (d.runs || []).map((r) => h("option", { value: r.run_id, selected: r.run_id === d.run ? true : null }, `${r.run_id} · ${r.states} · ${r.cells} cells`)));
    const stateSel = h("select", { "aria-label": "State", onchange: (e) => { location.hash = `#/coverage${runId ? `/${encodeURIComponent(runId)}` : ""}${e.target.value ? `?state=${e.target.value}` : ""}`; } },
      h("option", { value: "" }, "All states"),
      [...new Set(Object.values(m.columns).map((c) => c.state))].sort().map((s) => h("option", { value: s, selected: s === only ? true : null }, (S.meta.states.find((x) => x.state === s) || { name: s.toUpperCase() }).name)));
    rc(body,
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, `Run ${d.run}`), h("p", {}, `${m.totals.adequate} adequate, ${m.totals.partial} partial, ${m.totals.none} none over ${Object.values(m.totals).reduce((a, b) => a + b, 0)} cells. Per column: verdict counts, the kinds most often missing, and the Ollama arm's AskBench means.`)), h("div", { class: "row-flex" }, stateSel, runs)),
        h("div", { class: "card-pad table-wrap" }, summary)),
      h("div", { class: "spacer" }),
      h("section", { class: "card" }, h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "Questions × jurisdictions"), h("p", {}, "Rows are the questions people ask (fixtures/coverage/questions.json); columns a state or a place. A cell shows the verdict, the Ollama composite when scored, and the missing kinds."))),
        h("div", { class: "card-pad table-wrap" }, table),
        h("div", { class: "legend" }, h("span", { class: "title" }, "Verdict"), ...[["adequate", "Adequate"], ["partial", "Partial"], ["draft", "Partial, on drafts alone"], ["none", "None"]].map(([k, l]) => h("span", {}, h("span", { class: `sw cov-${k}` }), l)))),
      h("div", { class: "spacer" }), detail,
      h("div", { class: "row-flex", style: "margin-top:16px" }, h("button", { class: "btn", onclick: async () => { await startRunJob("coverage", { states: "va,dc", arm: "coverage" }); location.hash = "#/jobs"; } }, "Run the coverage probe again")));
    draw();
    drawDetail();
  }
  onRefresh(load);
  await load();
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
    status, out,
    h("p", { class: "muted", style: "margin-top:16px" }, "Retiring? ", h("a", { href: "#/benefits" }, "Retirement benefits: which programs apply to you, who runs them and how your state taxes them")));
  drawChip();
  if (question.value) run();
}

// ------------------------------------------------------------------ retirement benefits
// lexflow.benefits (docs/design/retirement-benefits.md): a place and a kind of person -> the pension systems, the
// state auto-IRA program, the state's tax treatment and the federal pointers.  The person type is a category: nothing
// about the asker leaves this page except the place and that category, and nothing is stored.
const BENEFIT_TREATMENT = { exempt: ["ok", "not taxed"], partly_exempt: ["warn", "partly taxed"], taxable: ["muted", "taxed"],
  no_income_tax: ["ok", "no income tax"], unknown: ["muted", "not grounded"] };
function benefitSource(s) {
  if (!s) return null;
  return h("blockquote", { class: "quote" }, `“${s.quote}”`,
    h("div", { class: "cite" }, s.url ? h("a", { href: s.url, target: "_blank", rel: "noopener" }, s.citation || s.url) : (s.citation || ""),
      s.matched ? ` · matched by lexflow's software (${s.matched_by}${s.checked_on ? `, ${s.checked_on}` : ""})` : ""));
}
function benefitSources(list, label) {
  const xs = (list || []).filter(Boolean);
  return xs.length ? h("details", {}, h("summary", { class: "muted" }, label || `${xs.length} source${xs.length === 1 ? "" : "s"}`), xs.map(benefitSource)) : null;
}
function benefitSystemCard(s) {
  const census = (s.census || []).filter((c) => c.members_active != null || c.beneficiaries != null);
  return h("section", { class: "card role-card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, s.name + (s.short ? ` (${s.short})` : "")),
      h("p", {}, s.level === "local" ? "Run by your local government" : "Statewide system", s.why ? ` · ${s.why}` : ""))),
    h("div", { class: "card-pad role-body" },
      h("div", { class: "role-row" }, h("span", { class: "k" }, "Run by"),
        h("div", {}, h("strong", {}, s.body.name || "–"),
          s.body.wikidata_url ? h("a", { class: "muted", href: s.body.wikidata_url, target: "_blank", rel: "noopener", style: "margin-left:8px" }, `Wikidata ${s.body.wikidata}`) : null)),
      s.channels && s.channels.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Reach them"), h("ul", { class: "chans" }, s.channels.map(channelRow))) : null,
      s.statute ? h("div", { class: "role-row" }, h("span", { class: "k" }, s.statute_role === "establishes" ? "The law that creates it" : "The law"),
        h("div", {}, benefitSource(s.statute), benefitSources(s.also, "more of the law"))) : null,
      s.plans && s.plans.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Plans"), h("div", {}, s.plans.join(" · "))) : null,
      census.length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Members"),
        h("div", { style: "font-size:13px" }, census.map((c) => h("div", {}, `${c.name}: ${fmtInt(c.members_active)} active, ${fmtInt(c.beneficiaries)} receiving benefits (Census ${c.year})`)))) : null,
      s.apply && s.apply.grounded ? h("div", { class: "role-row" }, h("span", { class: "k" }, "How to apply"), h("div", {}, s.apply.text, benefitSources(s.apply.sources))) : null,
      s.appeal && s.appeal.grounded ? h("div", { class: "role-row" }, h("span", { class: "k" }, "How to appeal"), h("div", {}, s.appeal.text, benefitSources(s.appeal.sources))) : null,
      s.family ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Your eligibility"),
        h("div", {}, h("a", { class: "btn small", href: s.family.href }, "Compute your plan and when you can retire →"),
          h("div", { class: "muted", style: "font-size:12.5px;margin-top:4px" }, "From decision tables whose every rule quotes the Code; enter your age and service there; nothing is stored."))) : null,
      s.how ? h("div", { class: "role-row" }, h("span", { class: "k" }, "How lexflow knows"), h("div", { class: "muted", style: "font-size:12.5px" }, s.how, s.source ? ` · ${s.source}` : "")) : null,
      (s.missing || []).length ? h("div", { class: "role-row" }, h("span", { class: "k" }, "Still missing"), h("ul", { class: "does muted" }, s.missing.map((m) => h("li", {}, m)))) : null));
}
function benefitIraCard(p) {
  const facts = p.facts || [];
  return h("section", { class: "card role-card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, p.name),
      h("p", {}, h("span", { class: `badge ${p.mandate ? "warn" : "muted"}` }, p.mandate ? "employers must offer it" : "voluntary"), ` · ${p.status || ""}`,
        p.smallest_employer ? ` · employers with ${p.smallest_employer} or more employees` : ""))),
    h("div", { class: "card-pad role-body" },
      h("div", { class: "role-row" }, h("span", { class: "k" }, "Run by"), h("div", {}, h("strong", {}, p.body.name || "–"),
        p.website ? h("div", {}, h("a", { href: p.website, target: "_blank", rel: "noopener" }, p.website)) : null)),
      p.note ? h("p", { class: "muted" }, p.note) : null,
      facts.length ? h("ul", { class: "does" }, facts.map((f) => h("li", {}, h("span", { class: "tag", style: "margin-right:6px" }, f.kind.replace("_", " ")), f.text,
        f.deadline ? h("span", { class: "badge", style: "margin-left:6px" }, f.deadline) : null, benefitSources(f.sources)))) : null));
}
function benefitTax(t) {
  if (!t) return h("p", { class: "muted" }, "No tax-treatment data for this state yet.");
  const order = [...t.first, ...Object.keys(t.items).filter((k) => !t.first.includes(k))];
  return h("section", { class: "card" },
    h("div", { class: "card-head" }, h("div", {}, h("h2", {}, "How the state taxes retirement income"),
      h("p", {}, t.agency ? [t.agency.url ? h("a", { href: t.agency.url, target: "_blank", rel: "noopener" }, t.agency.name) : t.agency.name, ` · tax year ${t.tax_year || "–"}`] : ""))),
    h("div", { class: "table-wrap" }, h("table", { class: "data" },
      h("thead", {}, h("tr", {}, ["Income", "Treatment", "What the law says"].map((x) => h("th", { scope: "col" }, x)))),
      h("tbody", {}, order.map((k) => {
        const it = t.items[k];
        const [cls, word] = BENEFIT_TREATMENT[it.treatment] || ["muted", it.treatment];
        return h("tr", {}, h("td", {}, it.label), h("td", {}, h("span", { class: `badge ${cls}` }, word)),
          h("td", {}, it.summary || h("span", { class: "muted" }, it.why || ""),
            (it.conditions || []).length ? h("div", { class: "muted", style: "font-size:12.5px" }, it.conditions.join("; ")) : null,
            benefitSources(it.sources)));
      })))),
    t.notes ? h("p", { class: "card-pad muted", style: "font-size:12.5px" }, t.notes) : null);
}
async function viewBenefits() {
  const meta = await api("/api/benefits");
  let chosen = JSON.parse(store("lexflow-benefits-place") || "null");
  const chip = h("span", {});
  const find = h("input", { type: "search", placeholder: "Your state, county, city or town", "aria-label": "Place", autocomplete: "off", style: "width:100%;box-sizing:border-box" });
  const results = h("div", { class: "card", style: "position:absolute;z-index:5;min-width:min(280px, 100%);max-width:100%;display:none;max-height:300px;overflow:auto" });
  function drawChip() {
    rc(chip, chosen ? h("span", { class: "tag", style: "display:inline-flex;gap:6px;align-items:center;text-transform:none;font-size:13px" }, chosen.label,
      h("button", { class: "icon-btn", "aria-label": `Remove ${chosen.label}`, onclick: () => { chosen = null; store("lexflow-benefits-place", ""); drawChip(); } }, "×")) : h("span", { class: "muted" }, "No place chosen yet."));
  }
  let timer = null;
  find.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(async () => {
      const q = find.value.trim();
      if (q.length < 2) { results.style.display = "none"; return; }
      const rows = (await api(`/api/targets?q=${encodeURIComponent(q)}`)).filter((r) => r.kind !== "country");
      rc(results, rows.length ? rows.map((r) => h("button", { class: "btn", style: "display:block;width:100%;text-align:left;border:0;border-radius:0",
        onclick: () => { chosen = { target: r.target, label: r.label.replace(" (state law)", "") }; store("lexflow-benefits-place", JSON.stringify(chosen)); drawChip(); find.value = ""; results.style.display = "none"; } },
        r.label.replace(" (state law)", ""), h("span", { class: "muted" }, r.kind === "state" ? " · state" : ` · ${r.kind}${r.population ? ` · ${fmtInt(r.population)}` : ""}`)))
        : h("p", { class: "card-pad muted" }, "No match."));
      results.style.display = "block";
    }, 200);
  });
  const person = h("select", { "aria-label": "Who you are", style: "width:100%;box-sizing:border-box" },
    meta.person_types.map((p) => h("option", { value: p.id }, p.label)));
  person.value = store("lexflow-benefits-person") || "state_employee";
  person.addEventListener("change", () => store("lexflow-benefits-person", person.value));
  const status = h("p", { class: "muted" });
  const out = h("div");
  async function run() {
    if (!chosen) { status.textContent = "Choose a place first."; return; }
    status.textContent = "Looking it up…";
    rc(out);
    let r;
    try {
      r = await api(`/api/benefits?${new URLSearchParams({ gov_id: chosen.target, person: person.value })}`);
    } catch (e) {
      status.textContent = "";
      rc(out, h("div", { class: "notice" }, icon("info"), h("div", {}, h("strong", {}, "Could not look it up. "), String(e.message || e))));
      return;
    }
    const pl = r.place;
    status.textContent = `${r.person_label} · ${pl.name ? `${pl.name}, ` : ""}${pl.state_name}`;
    const local = r.systems.filter((s) => s.level === "local");
    const statewide = r.systems.filter((s) => s.level !== "local");
    rc(out,
      statewide.length || local.length ? [h("h2", { style: "margin:8px 0 10px" }, "Pension systems"),
        h("div", { class: "grid who-grid" }, [...statewide, ...local].map(benefitSystemCard))] : null,
      r.auto_ira.length ? [h("h2", { style: "margin:18px 0 10px" }, "State retirement savings program"), h("div", { class: "grid who-grid" }, r.auto_ira.map(benefitIraCard))] : null,
      h("h2", { style: "margin:18px 0 10px" }, "Taxes"), benefitTax(r.tax),
      r.federal.length ? [h("h2", { style: "margin:18px 0 10px" }, "Federal programs (everywhere)"),
        h("ul", { class: "does" }, r.federal.map((f) => h("li", {}, h("a", { href: f.website, target: "_blank", rel: "noopener" }, f.name), h("span", { class: "muted" }, ` · ${f.body.name}${f.law ? ` · ${f.law}` : ""}`),
          f.note ? h("div", { class: "muted", style: "font-size:12.5px" }, f.note) : null,
          f.appeal ? h("div", { style: "font-size:12.5px" }, "Disagree with a decision? ", f.appeal.url ? h("a", { href: f.appeal.url, target: "_blank", rel: "noopener" }, f.appeal.text) : f.appeal.text) : null)))] : null,
      (r.notes || []).length || (r.missing || []).length ? h("div", { class: "notice", style: "margin-top:16px" }, icon("info"),
        h("ul", { class: "does", style: "margin:0" }, [...(r.notes || []), ...(r.missing || [])].map((m) => h("li", {}, m)))) : null,
      h("p", { class: "muted", style: "font-size:12.5px;margin-top:16px" }, r.about));
  }
  rc(view,
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Retirement benefits"),
      h("p", {}, "Choose where you work or live and who you are: the retirement programs that apply, who runs each, the law that creates it, how to apply and appeal, and how your state taxes the income. Programs and offices only; your choices stay in this browser and lexflow stores nothing about you."))),
    h("section", { class: "card card-pad", style: "margin-bottom:16px" },
      h("div", { style: "display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:10px;align-items:start" },
        h("div", { style: "position:relative" }, h("label", { class: "muted", style: "font-size:13px" }, "Place"), find, results, h("div", { style: "margin-top:6px" }, chip)),
        h("div", {}, h("label", { class: "muted", style: "font-size:13px" }, "Who you are"), person)),
      h("div", { class: "query-bar", style: "margin-top:10px" }, h("button", { class: "btn primary", type: "button", onclick: run }, "Show my benefits"),
        h("span", { class: "muted" }, "Try: City of Charlottesville · teacher · Maryland · private employee without a plan"))),
    status, out);
  drawChip();
  if (chosen) run();
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
