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
const routes = { map: viewMap, setup: viewSetup, places: viewPlaces, place: viewPlace, benchmark: viewBenchmark, processes: viewProcesses, model: viewModel, data: viewData,
  jobs: viewJobs, job: viewJob, method: viewMethod };
async function route() {
  const [, name = "map", ...rest] = (location.hash || "#/map").split("/");
  refreshers = [];
  hideTip();
  for (const a of document.querySelectorAll("nav.tabs a")) {
    const target = a.getAttribute("href").split("/")[1];
    const active = target === name || (name === "model" && target === "processes") || (name === "job" && target === "jobs") || (name === "place" && target === "places");
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
    h("section", { class: "card" }, list));

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
  const funnels = h("div", { class: "grid two" });
  const grid = h("div", { class: "model-grid" });
  rc(view, 
    h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "Process models"),
      h("p", {}, "One model per state and question. Each bar shows how far the model has come, from locating the law to publishing it; quality combines exact quotes, schema and lint checks, Petri-net soundness, explicit grounding and agreement between two models."))),
    h("div", { class: "filters" }, questionSeg(draw), h("label", { class: "field" }, "Tier", tierSel)),
    funnels, h("div", { class: "spacer" }), grid);
  let models = [], overview = null;
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
  function draw() {
    if (!overview) return;
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
  async function load() {
    [models, overview] = await Promise.all([api("/api/models"), api("/api/overview")]);
    draw();
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
    g.researched ? h("div", { class: "row-flex" }, statusEl(g.verified ? "done" : "partial", g.verified ? "Local answers checked" : "Local answers, not yet checked")) : null);
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
          `Local answer researched ${loc.researched} by ${loc.built_by || "Claude"}${loc.verified ? "; sources re-checked by a second reviewer" : ""}.`) : null));
  });
  rc(view,
    h("div", { class: "page-head" }, h("div", {},
      h("div", { class: "muted" }, h("a", { href: "#/places" }, "Places"), ` / ${(g.state || "").toUpperCase()}`),
      h("h1", {}, g.name),
      h("p", {}, `${g.kind}${g.population ? ` · population ${fmtInt(g.population)}` : ""}${g.county_name ? ` · ${g.county_name}` : ""}`)),
      g.website ? h("a", { class: "btn", href: g.website, target: "_blank", rel: "noopener" }, "Official website ↗") : null),
    h("div", { class: "grid", style: "gap:16px" }, cards));
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

poll();
route();
