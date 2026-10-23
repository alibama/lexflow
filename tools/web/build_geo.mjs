// Cut the home map's boundary files from their public sources (run once; the outputs are committed).
//
//   node tools/web/build_geo.mjs <countries-50m.json> <ne_10m_admin_1_states_provinces.geojson> [dashboard/geo]
//
// Sources, both read once from the operator's download, never fetched here:
//   countries-50m.json   world-atlas 2.0.2 (npm, ISC, Michael Bostock), Natural Earth 1:50m countries (public domain);
//                        copied as it is to dashboard/geo/world-50m.json.
//   ne_10m_admin_1_states_provinces.geojson   Natural Earth 1:10m admin-1 states and provinces, version 5
//                        (github.com/nvkelso/natural-earth-vector, public domain).  Only the countries in COUNTRIES are
//                        kept, simplified, in dashboard/geo/regions-10m.json.
//
// The simplification keeps neighbouring regions' borders identical: every ring is cut at the vertices where the set
// of rings sharing a vertex changes (a border meeting the coast or a third region), and each piece is simplified
// (Douglas-Peucker) on its own, so the two sides of a border keep the same points.  Islands under MIN_AREA square
// degrees are dropped unless they are a region's largest piece.  Coordinates are rounded to 3 decimals (about 100 m).
import fs from "node:fs";
import path from "node:path";
import * as d3 from "d3";

const [worldIn, admin1In, outDir = "dashboard/geo"] = process.argv.slice(2);
if (!worldIn || !admin1In) {
  console.error("usage: node tools/web/build_geo.mjs <countries-50m.json> <ne_10m_admin_1_states_provinces.geojson> [out]");
  process.exit(2);
}
// lexflow's keys (ISO 3166-1 alpha-3, lower case) of the countries whose regions the map draws
const COUNTRIES = ["jpn", "bra", "aus", "chl", "per", "gha", "rou"];
// Natural Earth codes that are not ISO 3166-2: the islands go to the state that governs them
const MERGE = { "AU-X03~": "AU-TAS" };          // Macquarie Island, part of Tasmania (Lord Howe Island is AU-NSW already)
const RENAME = { "AU-X02~": "AU-JBT" };         // Jervis Bay Territory: no ISO 3166-2 code, lexflow's own
// Natural Earth gives Metropolitan Lima (its "Lima Province") the Lima region's code; ISO 3166-2 has it as PE-LMA.
// Ghana is drawn with the ten regions Natural Earth has; the 2018 referendums split it into sixteen.
const BY_ADM1 = { "PER-587": { code: "PE-LMA", name: "Metropolitan Lima" } };
const TOLERANCE = 0.01;                         // degrees, about 1 km
const MIN_AREA = 0.002;                         // square degrees (cos-latitude weighted), about 20 km²
const DIGITS = 3;

const world = JSON.parse(fs.readFileSync(worldIn, "utf8"));
if (world.type !== "Topology" || !world.objects.countries) throw new Error(`${worldIn}: not world-atlas countries`);
const admin1 = JSON.parse(fs.readFileSync(admin1In, "utf8"));
const want = new Set(COUNTRIES.map((c) => c.toUpperCase()));

// 1. the regions, merged by code, each a list of polygons (lists of closed rings)
const regions = new Map();
for (const f of admin1.features) {
  const p = f.properties;
  if (!want.has(p.adm0_a3) || !f.geometry) continue;
  const raw = p.iso_3166_2 || p.adm1_code;
  const fix = BY_ADM1[p.adm1_code] || {};
  const code = fix.code || MERGE[raw] || RENAME[raw] || raw;
  const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
  if (!regions.has(code)) {
    regions.set(code, { code, country: p.adm0_a3.toLowerCase(), name: fix.name || p.name_en || p.name, local: p.name_local || null,
      type: p.type_en || p.type || null, wikidata: p.wikidataid || null, polys: [] });
  }
  regions.get(code).polys.push(...polys);
}

// 2. drop small islands, keeping each region's largest piece
const areaOf = (ring) => {
  let a = 0;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) a += (ring[j][0] + ring[i][0]) * (ring[j][1] - ring[i][1]);
  const lat = ring.reduce((s, c) => s + c[1], 0) / ring.length;
  return Math.abs(a / 2) * Math.cos((lat * Math.PI) / 180);
};
for (const r of regions.values()) {
  const sized = r.polys.map((poly) => [poly, areaOf(poly[0])]).sort((a, b) => b[1] - a[1]);
  r.polys = sized.filter(([, a], i) => i === 0 || a >= MIN_AREA).map(([poly]) => poly);
}

// 3. which rings share each vertex
const key = (c) => `${c[0]},${c[1]}`;
const rings = [];
for (const r of regions.values()) for (const poly of r.polys) for (const ring of poly) rings.push(ring);
const at = new Map();
rings.forEach((ring, id) => {
  for (let i = 0; i < ring.length - 1; i++) {
    const k = key(ring[i]);
    if (!at.has(k)) at.set(k, new Set());
    at.get(k).add(id);
  }
});
const sig = (c) => [...at.get(key(c))].sort((a, b) => a - b).join(" ");

// 4. Douglas-Peucker on an open path, endpoints kept
function dp(pts) {
  if (pts.length <= 2) return pts;
  const keep = new Uint8Array(pts.length);
  keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop();
    const [ax, ay] = pts[a], [bx, by] = pts[b];
    const dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
    let far = -1, best = TOLERANCE * TOLERANCE;
    for (let i = a + 1; i < b; i++) {
      const [px, py] = pts[i];
      let t = len2 ? ((px - ax) * dx + (py - ay) * dy) / len2 : 0;
      t = Math.max(0, Math.min(1, t));
      const ex = px - (ax + t * dx), ey = py - (ay + t * dy), d2 = ex * ex + ey * ey;
      if (d2 > best) { best = d2; far = i; }
    }
    if (far > 0) { keep[far] = 1; stack.push([a, far], [far, b]); }
  }
  return pts.filter((_, i) => keep[i]);
}
const round = (c) => c.map((v) => +v.toFixed(DIGITS));

// 5. a closed ring, cut at its junctions and simplified piece by piece
function simplifyRing(ring) {
  const n = ring.length - 1;                    // the last point repeats the first
  const s = ring.slice(0, n).map(sig);
  const cuts = [];
  for (let i = 0; i < n; i++) if (s[i] !== s[(i - 1 + n) % n] || s[i] !== s[(i + 1) % n]) cuts.push(i);
  if (!cuts.length) {                           // an island or a ring no other ring touches: cut at 0 and its far point
    let far = 0, best = -1;
    for (let i = 1; i < n; i++) { const d = (ring[i][0] - ring[0][0]) ** 2 + (ring[i][1] - ring[0][1]) ** 2; if (d > best) { best = d; far = i; } }
    cuts.push(0, far);
  }
  const out = [];
  for (let c = 0; c < cuts.length; c++) {
    const a = cuts[c], b = cuts[(c + 1) % cuts.length];
    const piece = [];
    for (let i = a; ; i = (i + 1) % n) { piece.push(ring[i]); if (i === b && piece.length > 1) break; if (piece.length > n + 1) break; }
    // the same border walked the other way gives the same points: simplify it in a canonical direction
    const fwd = key(piece[0]) <= key(piece[piece.length - 1]);
    const simple = fwd ? dp(piece) : dp(piece.slice().reverse()).reverse();
    out.push(...simple.slice(0, -1));
  }
  out.push(out[0]);
  return out.map(round);
}

// 6. the features, wound for d3 (a region's area is under a hemisphere)
const features = [];
let points = 0;
for (const r of [...regions.values()].sort((a, b) => a.code.localeCompare(b.code))) {
  const polys = r.polys.map((poly) => poly.map(simplifyRing).filter((ring, i) => i === 0 || ring.length >= 4))
    .filter((poly) => poly[0].length >= 4);
  let f = { type: "Feature", id: r.code, properties: { country: r.country, name: r.name, local: r.local, type: r.type,
    wikidata: r.wikidata }, geometry: { type: "MultiPolygon", coordinates: polys } };
  if (d3.geoArea(f) > 2 * Math.PI) {
    polys.forEach((poly) => poly.forEach((ring) => ring.reverse()));
  }
  points += polys.reduce((s, poly) => s + poly.reduce((t, ring) => t + ring.length, 0), 0);
  features.push(f);
}
const collection = { type: "FeatureCollection",
  source: "Natural Earth 1:10m admin-1 states and provinces v5 (public domain), simplified by tools/web/build_geo.mjs",
  features };
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "regions-10m.json"), JSON.stringify(collection));
fs.copyFileSync(worldIn, path.join(outDir, "world-50m.json"));
const by = {};
for (const f of features) by[f.properties.country] = (by[f.properties.country] || 0) + 1;
console.log(`regions: ${features.length} (${Object.entries(by).map(([k, n]) => `${k} ${n}`).join(", ")}), ${points} points, ` +
  `${fs.statSync(path.join(outDir, "regions-10m.json")).size} bytes; world: ${fs.statSync(path.join(outDir, "world-50m.json")).size} bytes`);
