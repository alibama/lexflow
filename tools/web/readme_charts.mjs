// Draw the README charts from docs/status.json (written by `lexflow export-status`).
//
//   node tools/web/readme_charts.mjs [docs/status.json] [docs/img]
//
// Each chart is written twice, *.svg (light) and *-dark.svg, for a <picture> element.  Colours are the
// dashboard's validated ramps; text is drawn in ink tokens, never in a series colour.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as d3 from "d3";
import * as topojson from "topojson-client";

const here = path.dirname(fileURLToPath(import.meta.url));
const statusPath = process.argv[2] || "docs/status.json";
const outDir = process.argv[3] || "docs/img";
const status = JSON.parse(fs.readFileSync(statusPath, "utf8"));
const statesTopo = JSON.parse(fs.readFileSync(path.join(here, "node_modules/us-atlas/states-albers-10m.json"), "utf8"));
const countiesTopo = JSON.parse(fs.readFileSync(path.join(here, "node_modules/us-atlas/counties-albers-10m.json"), "utf8"));
fs.mkdirSync(outDir, { recursive: true });

const THEMES = {
  light: { surface: "#fcfcfb", ink: "#0b0b0b", ink2: "#52514e", muted: "#898781", grid: "#e1e0d9", line: "#fcfcfb",
    neutral: "#e1e0d9", nodata: "#f3f2ee", hatch: "#c3c2b7",
    tier: { found: "#86b6ef", single: "#3987e5", agreed: "#1c5cab", reviewed: "#0d366b" },
    seq: ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"], bar: "#2a78d6" },
  dark: { surface: "#1a1a19", ink: "#ffffff", ink2: "#c3c2b7", muted: "#898781", grid: "#2c2c2a", line: "#1a1a19",
    neutral: "#383835", nodata: "#222220", hatch: "#383835",
    tier: { found: "#184f95", single: "#2a78d6", agreed: "#6da7ec", reviewed: "#b7d3f6" },
    seq: ["#184f95", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"], bar: "#3987e5" },
};
const FONT = `font-family="system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"`;
const TIER_LABEL = { reviewed: "Checked by Claude or a person", agreed: "Two local models agree", single: "One local model",
  found: "Law found, no steps yet", none: "No state law found" };
const STAGES = ["located", "text", "extracted", "cross_checked", "compiled", "validated", "reviewed", "published"];
const STAGE_LABEL = { located: "Law located", text: "Text loaded", extracted: "Facts extracted", cross_checked: "Cross-checked",
  compiled: "BPMN/DMN compiled", validated: "Checks pass", reviewed: "Reviewed", published: "Published" };
const Q = { records: "How do I request public records?", business: "How do I start a business?" };
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const fmt = (n) => Number(n).toLocaleString("en-US");
const generated = status.generated ? status.generated.slice(0, 10) : "";

function write(name, theme, svg) {
  const file = path.join(outDir, `${name}${theme === "dark" ? "-dark" : ""}.svg`);
  fs.writeFileSync(file, svg);
  return file;
}
function hatch(t) {
  return `<pattern id="nd" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="${t.nodata}"/><line x1="0" y1="0" x2="0" y2="5" stroke="${t.hatch}" stroke-width="1.2"/></pattern>`;
}
function legendRow(t, items, x, y) {
  let out = "", cx = x;
  for (const [label, fill] of items) {
    out += `<rect x="${cx}" y="${y - 10}" width="12" height="12" rx="3" fill="${fill}"/>`;
    out += `<text x="${cx + 18}" y="${y}" font-size="12" fill="${t.ink2}">${esc(label)}</text>`;
    cx += 18 + label.length * 6.3 + 18;
  }
  return out;
}

// ------------------------------------------------ 1. state tier maps (records | business)
function tierMaps(themeName) {
  const t = THEMES[themeName];
  const states = topojson.feature(statesTopo, statesTopo.objects.states).features;
  const byFips = {};
  for (const r of status.states) (byFips[r.fips] ||= {})[r.question] = r;
  const W = 975, H = 610, scale = 0.46, gap = 24, top = 92;
  const width = Math.round(W * scale * 2 + gap + 32), height = Math.round(H * scale + top + 56);
  const geo = d3.geoPath();
  let body = "";
  ["records", "business"].forEach((qid, i) => {
    const ox = i * (W * scale + gap);
    body += `<text x="${ox}" y="${top - 14}" font-size="13" font-weight="600" fill="${t.ink}">${esc(Q[qid])}</text>`;
    body += `<g transform="translate(${ox},${top}) scale(${scale})">`;
    for (const f of states) {
      const r = (byFips[f.id] || {})[qid];
      const fill = !r ? `url(#nd)` : r.tier === "none" ? (r.statutes === "downloaded" ? t.neutral : "url(#nd)") : t.tier[r.tier];
      body += `<path d="${geo(f)}" fill="${fill}" stroke="${t.line}" stroke-width="${1.2 / scale}"><title>${esc(f.properties.name)}: ${esc(r ? TIER_LABEL[r.tier] : "no data")}</title></path>`;
    }
    body += `</g>`;
  });
  const legend = legendRow(t, [["Checked by Claude", t.tier.reviewed], ["Two models agree", t.tier.agreed], ["One model", t.tier.single],
    ["Law found, no steps", t.tier.found], ["No law found", t.neutral], ["Statutes not downloaded", "url(#nd)"]], 0, height - 16);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" ${FONT} role="img" aria-label="Maps of who built each state's process model">
<defs>${hatch(t)}</defs><rect width="100%" height="100%" rx="10" fill="${t.surface}"/>
<g transform="translate(16,0)"><text x="0" y="24" font-size="15" font-weight="650" fill="${t.ink}">Who built each state's process model</text>
<text x="0" y="42" font-size="12" fill="${t.ink2}">Snapshot ${esc(generated)} · ${fmt(status.overview.governments)} governments loaded</text>
${body}${legend}</g></svg>`;
}

// ------------------------------------------------ 2. pipeline completion (small multiples)
function pipeline(themeName) {
  const t = THEMES[themeName];
  const st = status.overview.stages;
  const max = st.possible;
  const rowH = 26, labelW = 132, barW = 230, panelW = labelW + barW + 46, top = 92;
  const width = panelW * 2 + 32, height = top + STAGES.length * rowH + 30;
  let body = "";
  ["records", "business"].forEach((qid, i) => {
    const ox = i * (panelW + 16);
    body += `<text x="${ox}" y="${top - 16}" font-size="13" font-weight="600" fill="${t.ink}">${esc(Q[qid])}</text>`;
    STAGES.forEach((s, k) => {
      const y = top + k * rowH;
      const n = st[qid][s] || 0;
      const w = Math.max(n ? 3 : 0, (n / max) * barW);
      body += `<text x="${ox}" y="${y + 13}" font-size="12" fill="${t.ink2}">${esc(STAGE_LABEL[s])}</text>`;
      body += `<rect x="${ox + labelW}" y="${y + 2}" width="${barW}" height="14" rx="4" fill="${t.grid}" opacity="0.6"/>`;
      if (n) body += `<path d="M${ox + labelW},${y + 2}h${w - 4}a4,4 0 0 1 4,4v6a4,4 0 0 1 -4,4h-${w - 4}z" fill="${t.bar}"/>`;
      body += `<text x="${ox + labelW + barW + 8}" y="${y + 13}" font-size="12" fill="${t.ink}" font-variant-numeric="tabular-nums">${n}</text>`;
    });
  });
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" ${FONT} role="img" aria-label="States reaching each stage of the pipeline">
<rect width="100%" height="100%" rx="10" fill="${t.surface}"/><g transform="translate(16,0)">
<text x="0" y="24" font-size="15" font-weight="650" fill="${t.ink}">How far each state's model has come</text>
<text x="0" y="42" font-size="12" fill="${t.ink2}">States (of ${max}) reaching each stage · snapshot ${esc(generated)}</text>${body}</g></svg>`;
}

// ------------------------------------------------ 3. governments by confidence band (stacked)
function confidence(themeName) {
  const t = THEMES[themeName];
  const bins = [0.2, 0.35, 0.5, 0.65];
  const labels = ["under 0.20", "0.20–0.35", "0.35–0.50", "0.50–0.65", "0.65 and up"];
  const counts = status.confidence_bins || {};
  const barW = 640, top = 82, rowH = 54;
  const width = barW + 220, height = top + 2 * rowH + 40;
  let body = "";
  ["records", "business"].forEach((qid, i) => {
    const c = counts[qid] || [0, 0, 0, 0, 0];
    const total = c.reduce((a, b) => a + b, 0) || 1;
    const y = top + i * rowH;
    body += `<text x="0" y="${y}" font-size="13" font-weight="600" fill="${t.ink}">${esc(Q[qid])}</text>`;
    const mean = status.overview.questions[qid].mean_confidence;
    body += `<text x="${barW + 16}" y="${y + 22}" font-size="12" fill="${t.ink2}">mean ${mean == null ? "–" : mean.toFixed(2)}</text>`;
    let x = 0;
    c.forEach((n, k) => {
      const w = (n / total) * barW;
      if (w <= 0) return;
      body += `<rect x="${x}" y="${y + 9}" width="${Math.max(0, w - 2)}" height="18" fill="${t.seq[k]}"><title>${labels[k]}: ${fmt(n)}</title></rect>`;
      const share = n / total;
      if (w > 64) body += `<text x="${x + 6}" y="${y + 22}" font-size="11.5" fill="${k >= 2 === (themeName === "light") ? "#ffffff" : "#0b0b0b"}">${(share * 100).toFixed(share < 0.1 ? 1 : 0)}%</text>`;
      x += w;
    });
  });
  const legend = legendRow(t, labels.map((l, k) => [l, t.seq[k]]), 0, height - 14);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" ${FONT} role="img" aria-label="Governments by answer confidence">
<rect width="100%" height="100%" rx="10" fill="${t.surface}"/><g transform="translate(16,0)">
<text x="0" y="24" font-size="15" font-weight="650" fill="${t.ink}">Governments by answer confidence</text>
<text x="0" y="42" font-size="12" fill="${t.ink2}">${fmt(status.overview.questions.records.answers)} governments scored per question · bins: ${bins.join(", ")}</text>
${body}${legend}</g></svg>`;
}

// ------------------------------------------------ 4. one state's counties (the most complete state)
function countyMap(themeName, stateFips, question) {
  const t = THEMES[themeName];
  const counties = topojson.feature(countiesTopo, countiesTopo.objects.counties).features.filter((f) => f.id.startsWith(stateFips));
  const state = topojson.feature(countiesTopo, countiesTopo.objects.states).features.find((f) => f.id === stateFips);
  const values = status.county_confidence?.[question] || {};
  const width = 700, height = 380, top = 54;
  const proj = d3.geoIdentity().fitExtent([[0, top], [width - 32, height - 40]], state);
  const geo = d3.geoPath(proj);
  const bins = [0.2, 0.35, 0.5, 0.65];
  const color = (v) => { let i = 0; while (i < bins.length && v >= bins[i]) i++; return t.seq[i]; };
  let body = "";
  for (const f of counties) {
    const v = values[f.id];
    body += `<path d="${geo(f)}" fill="${v == null ? "url(#nd)" : color(v)}" stroke="${t.line}" stroke-width="0.8"><title>${esc(f.properties.name)}: ${v == null ? "no data" : v.toFixed(2)}</title></path>`;
  }
  const name = status.states.find((r) => r.fips === stateFips)?.name || stateFips;
  const legend = legendRow(t, ["under 0.20", "0.20–0.35", "0.35–0.50", "0.50–0.65", "0.65 and up"].map((l, k) => [l, t.seq[k]]), 0, height - 12);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" ${FONT} role="img" aria-label="${esc(name)} counties by answer confidence">
<defs>${hatch(t)}</defs><rect width="100%" height="100%" rx="10" fill="${t.surface}"/><g transform="translate(16,0)">
<text x="0" y="24" font-size="15" font-weight="650" fill="${t.ink}">${esc(name)}: answer confidence by county</text>
<text x="0" y="42" font-size="12" fill="${t.ink2}">${esc(Q[question])} · mean of every county, city and town in the county</text>
${body}${legend}</g></svg>`;
}

// ------------------------------------------------ 5. the README's checklist block
function updateReadme(readmePath) {
  if (!fs.existsSync(readmePath)) return null;
  const text = fs.readFileSync(readmePath, "utf8");
  const start = "<!-- status:start -->", end = "<!-- status:end -->";
  if (!text.includes(start) || !text.includes(end)) return null;
  const word = { done: "done", partial: "partly done", todo: "to do", blocked: "waiting on an earlier step", optional: "not set up" };
  const lines = [`_Snapshot ${generated}. Regenerate with \`lexflow export-status\` and \`node tools/web/readme_charts.mjs\`._`, ""];
  for (const s of status.checklist) {
    const box = s.status === "done" ? "[x]" : "[ ]";
    lines.push(`- ${box} **${s.title}** (${s.level}, ${word[s.status] || s.status}): ${s.detail}`);
  }
  const block = `${start}\n${lines.join("\n")}\n${end}`;
  fs.writeFileSync(readmePath, text.slice(0, text.indexOf(start)) + block + text.slice(text.indexOf(end) + end.length));
  return readmePath;
}

const written = [];
const readme = updateReadme(path.join(path.dirname(path.resolve(outDir)), "..", "README.md"));
if (readme) written.push(readme);
for (const theme of ["light", "dark"]) {
  written.push(write("states-tier", theme, tierMaps(theme)));
  written.push(write("pipeline", theme, pipeline(theme)));
  written.push(write("confidence", theme, confidence(theme)));
  if (status.focus_state) written.push(write("county-confidence", theme, countyMap(theme, status.focus_state, "business")));
}
console.log(written.join("\n"));
