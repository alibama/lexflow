(function () {
  "use strict";
  var DATA = JSON.parse(document.getElementById("data").textContent);
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;"}[c]; }); };
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var viewer = null, current = null, selected = null, panelName = "decisions", lawExtra = null;
  var DEONTIC = {"obligation": "Must (obligation)", "permission": "May (permission)", "right": "Is entitled (right)",
                 "prohibition": "Must not (prohibition)", "duty-to-decide": "Must decide (duty)"};

  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  // ------------------------------------------------------------- law text
  function formatInline(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|\s)\*([^*]+)\*(?=\s|$|[.,;])/g, "$1<em>$2</em>");
  }
  function renderTable(p) {
    var rows = p.match(/<tr>[\s\S]*?<\/tr>/g) || [];
    var out = rows.map(function (r) {
      var cells = r.match(/<t[hd][^>]*>[\s\S]*?<\/t[hd]>/g) || [];
      return "<tr>" + cells.map(function (c) {
        var tag = /^<th/.test(c) ? "th" : "td";
        var txt = c.replace(/<[^>]+>/g, "").trim();
        var span = (c.match(/colspan="(\d+)"/) || [])[1];
        var rspan = (c.match(/rowspan="(\d+)"/) || [])[1];
        return "<" + tag + (span ? " colspan=\"" + span + "\"" : "") + (rspan ? " rowspan=\"" + rspan + "\"" : "") + ">" + esc(txt) + "</" + tag + ">";
      }).join("") + "</tr>";
    }).join("");
    return "<div class=\"lawtable-wrap\"><table class=\"lawtable\">" + out + "</table></div>";
  }
  function markParagraph(p, quotes) {
    var text = p, ranges = [];
    quotes.forEach(function (q) {
      if (!q) return;
      var i = text.indexOf(q);
      if (i < 0) {
        var norm = text.replace(/\s+/g, " ");
        if (norm.indexOf(q) >= 0) { text = norm; i = text.indexOf(q); }
      }
      while (i >= 0) { ranges.push([i, i + q.length]); i = text.indexOf(q, i + q.length); }
    });
    ranges.sort(function (a, b) { return a[0] - b[0]; });
    var merged = [];
    ranges.forEach(function (r) { var last = merged[merged.length - 1]; if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1]); else merged.push(r.slice()); });
    var html = "", pos = 0;
    merged.forEach(function (r) { html += formatInline(text.slice(pos, r[0])) + "<mark>" + formatInline(text.slice(r[0], r[1])) + "</mark>"; pos = r[1]; });
    html += formatInline(text.slice(pos));
    html = html.replace(/^((?:<mark>)?)(\(?[A-Za-z0-9]{1,4}\)?\.?)(\s)/, "$1<span class=\"sublabel\">$2</span>$3");
    return "<p>" + html + "</p>";
  }
  function renderSection(t, quotes) {
    var paras = t.text.split(/\n\n+/).map(function (p) { return /^\s*<table/.test(p) ? renderTable(p) : markParagraph(p, quotes); }).join("");
    var url = t.url ? " &middot; <a href=\"" + esc(t.url) + "\" target=\"_blank\" rel=\"noopener\">official source</a>" : "";
    var hist = t.history ? "<details><summary>History and editorial notes</summary><pre>" + esc(t.history) + "</pre></details>" : "";
    return "<section><div class=\"lawhead\"><span class=\"kicker\">" + esc(t.code) + " &sect; " + esc(t.section) + url + "</span>" +
           "<h3>" + esc(t.title) + "</h3></div>" + paras + hist + "<div class=\"prov\">" + esc(t.retrieved) + "</div></section>";
  }
  function renderLaw(el) {
    var keys = [], quotes = {};
    (el ? el.sources : []).forEach(function (s) { if (keys.indexOf(s.key) < 0) keys.push(s.key); (quotes[s.key] = quotes[s.key] || []).push(s.quote); });
    if (lawExtra && keys.indexOf(lawExtra) < 0) keys.push(lawExtra);
    if (!keys.length) keys = [current.texts[0].key];
    var html = keys.map(function (k) { var t = current.texts.find(function (x) { return x.key === k; }); return t ? renderSection(t, quotes[k] || []) : ""; }).join("");
    var others = current.texts.filter(function (t) { return keys.indexOf(t.key) < 0; });
    if (others.length) {
      html += "<div class=\"others\"><span class=\"kicker\" style=\"align-self:center\">Other sections</span>" + others.map(function (t) {
        return "<button type=\"button\" data-key=\"" + esc(t.key) + "\">&sect; " + esc(t.section) + "</button>"; }).join("") + "</div>";
    }
    $("law").innerHTML = html;
    Array.prototype.forEach.call($("law").querySelectorAll(".others button"), function (b) {
      b.addEventListener("click", function () { lawExtra = b.getAttribute("data-key"); renderLaw(selected ? current.elements[selected] : null); });
    });
    var first = $("law").querySelector("mark"), col = $("law-col");
    if (first && col.scrollHeight > col.clientHeight + 4) {
      var top = first.getBoundingClientRect().top - col.getBoundingClientRect().top + col.scrollTop - 140;
      col.scrollTo({top: Math.max(0, top), behavior: reduce ? "auto" : "smooth"});
    }
  }

  // ------------------------------------------------------------- step card
  function renderCard(id) {
    var el = id ? current.elements[id] : null;
    if (!el) { $("step-card").innerHTML = "<p class=\"empty\">Select a step in the diagram or the Step list to see the law it comes from.</p>"; return; }
    var b = [];
    if (el.grounding) b.push("<span class=\"badge " + el.grounding + "\">" + {"explicit": "Stated in the text", "implied": "Presupposed by another provision", "assumed": "Modeller's assumption"}[el.grounding] + "</span>");
    if (el.deontic) b.push("<span class=\"badge\">" + esc(DEONTIC[el.deontic] || el.deontic) + (el.bearer ? ": " + esc(el.bearer) : "") + "</span>");
    if (el.timer) b.push("<span class=\"badge deadline\">" + esc(el.timer.human) + " &middot; <span style=\"font-family:var(--font-mono)\">" + esc(el.timer.value) + "</span></span>");
    var facts = [];
    if (el.actor) facts.push("<div class=\"fact\"><b>Who:</b> " + esc(el.actor) + "</div>");
    if (el.timer) {
      facts.push("<div class=\"fact\"><b>Clock starts:</b> " + esc(el.timer.anchor || "not stated") + "</div>");
      facts.push("<div class=\"fact\"><b>If missed:</b> " + (el.timer.strict ? "the matter ends on this path (strict deadline)" : "nothing ends; the step still happens (soft deadline)") +
                 (el.type === "boundaryEvent" ? (el.timer.interrupting ? "; interrupts the step" : "; runs alongside the step") : "") + "</div>");
    }
    if (el.decision) { var d = current.decisions.find(function (x) { return x.id === el.decision; }); facts.push("<div class=\"fact\"><b>Evaluates:</b> " + esc(d ? d.name : el.decision) + " <a href=\"#decisions\" data-goto=\"decisions\">(table below)</a></div>"); }
    if (el.calls) facts.push("<div class=\"fact\"><b>Calls:</b> <span style=\"font-family:var(--font-mono)\">" + esc(el.calls) + "</span>, the state-level process this provision hands off to</div>");
    if (el.doc) facts.push("<div class=\"fact\"><b>Modeling note:</b> " + esc(el.doc) + "</div>");
    var src = el.sources.length ? "<ul class=\"sources\">" + el.sources.map(function (s) {
      var cite = s.url ? "<a href=\"" + esc(s.url) + "\" target=\"_blank\" rel=\"noopener\">" + esc(s.citation) + "</a>" : esc(s.citation);
      return "<li><div class=\"cite\">" + cite + (s.grounding !== "explicit" ? " <span class=\"g\">(" + esc(s.grounding) + ")</span>" : "") + "</div>" +
             (s.quote ? "<p class=\"quote\">" + esc(s.quote) + "</p>" : "") + (s.note ? "<p class=\"note\">" + esc(s.note) + "</p>" : "") + "</li>";
    }).join("") + "</ul>" : "<p class=\"empty\">No citation on this element (gateways and plain start or end events carry none).</p>";
    $("step-card").innerHTML = "<div class=\"kicker\">" + esc(el.kind) + "</div><h2>" + esc(el.name || id) + "</h2>" +
      (b.length ? "<div class=\"badges\">" + b.join("") + "</div>" : "") + facts.join("") + src;
    var go = $("step-card").querySelector("[data-goto]");
    if (go) go.addEventListener("click", function (e) { e.preventDefault(); showPanel("decisions"); document.querySelector(".detail").scrollIntoView({behavior: reduce ? "auto" : "smooth"}); });
  }

  // ------------------------------------------------------------- diagram
  function select(id, scroll) {
    if (viewer) {
      var canvas = viewer.get("canvas"), reg = viewer.get("elementRegistry");
      if (selected && reg.get(selected)) canvas.removeMarker(selected, "lx-selected");
      if (id && reg.get(id)) {
        canvas.addMarker(id, "lx-selected");
        if (scroll) { try { canvas.scrollToElement(reg.get(id), {top: 120, bottom: 120, left: 160, right: 160}); } catch (e) {} }
      }
    }
    selected = id; lawExtra = null;
    $("step-picker").value = id || "";
    renderCard(id); renderLaw(id ? current.elements[id] : null);
  }
  function applyMarkers() {
    var canvas = viewer.get("canvas"), reg = viewer.get("elementRegistry");
    Object.keys(current.elements).forEach(function (id) {
      var el = current.elements[id];
      if (!reg.get(id)) return;
      if (el.sources.length) canvas.addMarker(id, "lx-cited");
      if (el.grounding === "implied") canvas.addMarker(id, "lx-implied");
      if (el.grounding === "assumed") canvas.addMarker(id, "lx-assumed");
      if (el.timer) canvas.addMarker(id, "lx-timer");
    });
  }
  function fillPicker() {
    var opts = Object.keys(current.elements).filter(function (id) { var e = current.elements[id]; return e.name && (e.sources.length || e.type.indexOf("Gateway") > 0); })
      .map(function (id) { var e = current.elements[id]; return "<option value=\"" + esc(id) + "\">" + esc(e.name) + (e.timer ? " (" + esc(e.timer.human) + ")" : "") + "</option>"; });
    $("step-picker").innerHTML = opts.join("");
  }
  function renderIntro() {
    $("m-title").textContent = current.title;
    $("m-meta").innerHTML = esc(current.jurisdiction) + (current.qid ? " &middot; <a href=\"https://www.wikidata.org/wiki/" + esc(current.qid) + "\" target=\"_blank\" rel=\"noopener\">" + esc(current.qid) + "</a>" : "") +
      " &middot; " + esc(current.note);
    $("m-summary").textContent = current.summary;
    var c = current.checks, nets = Object.keys(current.petri), sound = nets.filter(function (k) { return current.petri[k].sound; }).length;
    var chips = [[c.counts.flow_nodes, "flow elements"], [c.counts.pools + " / " + c.counts.lanes, "pools / lanes"],
                 [c.quotes + " / " + c.quotes, "quotes match the text"], [Math.round((c.explicit_share || 0) * 100) + "%", "citations stated, not inferred"],
                 [c.counts.decisions + " / " + c.counts.rules, "DMN tables / rules"], [sound + " / " + nets.length, "Petri nets sound"]];
    if (c.scenarios.length) chips.push([c.scenarios.length, "executed scenarios"]);
    $("m-chips").innerHTML = chips.map(function (x) { return "<li><b>" + esc(x[0]) + "</b><span>" + esc(x[1]) + "</span></li>"; }).join("");
  }
  function loadModel(id) {
    current = DATA.models.find(function (m) { return m.id === id; }) || DATA.models[0];
    store("lx-model", current.id);
    Array.prototype.forEach.call($("models").children, function (b) { b.setAttribute("aria-selected", String(b.dataset.id === current.id)); });
    renderIntro(); fillPicker(); renderPanel();
    if (!viewer) { selected = null; select(current.default, false); return; }
    selected = null;
    viewer.importXML(current.xml).then(function () {
      viewer.get("canvas").zoom("fit-viewport", "auto");
      applyMarkers();
      select(current.default, false);
    }).catch(function (err) {
      $("canvas").innerHTML = "<p class=\"load-error\">The diagram could not be drawn: " + esc(err.message) + "</p>";
      renderCard(current.default); renderLaw(current.elements[current.default]);
    });
  }

  // ------------------------------------------------------------- detail panels
  function feelCell(v, out) { var any = v === "-"; return "<td class=\"feel" + (any ? " any" : "") + (out ? " out" : "") + "\">" + (any ? "any" : esc(v).replace(/,(?=\S)/g, ", ")) + "</td>"; }
  function panelDecisions() {
    if (!current.decisions.length) return "<p class=\"lede\">This model has no decision tables.</p>";
    return "<p class=\"lede\">Each table is DMN 1.3 with FEEL cells (the standard notation), validated against the OMG schema and dmnlint, and cross-checked against SpiffWorkflow's engine on every input combination in the test grid. &ldquo;any&rdquo; matches every value; rules are read top to bottom when the hit policy is FIRST.</p>" +
      current.decisions.map(function (d) {
        var head = "<tr><th rowspan=\"2\">#</th><th class=\"grp\" colspan=\"" + d.inputs.length + "\">When</th><th class=\"grp\" colspan=\"" + d.outputs.length + "\">Then</th><th rowspan=\"2\">Source</th></tr><tr>" +
          d.inputs.map(function (x) { return "<th>" + esc(x) + "</th>"; }).join("") + d.outputs.map(function (x) { return "<th>" + esc(x) + "</th>"; }).join("") + "</tr>";
        var rows = d.rules.map(function (r, i) { return "<tr><td class=\"n\">" + (i + 1) + "</td>" + r.in.map(function (v) { return feelCell(v, false); }).join("") + r.out.map(function (v) { return feelCell(v, true); }).join("") + "<td class=\"src\">" + esc(r.cite) + "</td></tr>"; }).join("");
        return "<div class=\"box\"><h3>" + esc(d.name) + "</h3><p class=\"lede\">" + esc(d.question || "") + " Hit policy " + esc(d.hit) + ".</p><div class=\"dt-wrap\"><table class=\"dt\"><thead>" + head + "</thead><tbody>" + rows + "</tbody></table></div></div>";
      }).join("");
  }
  function panelStructure() {
    return "<p class=\"lede\">Each pool's control flow is projected to a workflow net (Petri net), checked for soundness with pm4py, then converted to POWL 2.0. In POWL, PO lists steps whose order is fixed by &ldquo;order&rdquo; edges (steps without an edge between them can happen concurrently), CHOICE is a choice graph, and ? marks an optional block.</p><div class=\"grid2\">" +
      Object.keys(current.petri).map(function (k) {
        var p = current.petri[k];
        return "<div class=\"box\"><div class=\"kicker\">" + esc(current.procNames[k] || k) + "</div><h3>" + (p.sound ? "Sound workflow net" : "Not sound") + "</h3>" +
          "<div class=\"fact\">" + p.places + " places &middot; " + p.transitions + " transitions &middot; " + p.reachable_states + " reachable states</div>" +
          (p.approximations && p.approximations.length ? "<details><summary class=\"kicker\">Approximations made in the projection</summary><ul class=\"plain\">" + p.approximations.map(function (a) { return "<li>" + esc(a) + "</li>"; }).join("") + "</ul></details>" : "") +
          "<pre>" + esc(p.powl || "(POWL conversion not available)") + "</pre></div>";
      }).join("") + "</div>";
  }
  function panelPractice() {
    var L = DATA.legistar, rows = L.cases;
    var withDays = rows.filter(function (r) { return r.days != null; });
    var W = 760, left = 300, right = 60, rowH = 30, top = 28, max = 42;
    var H = top + withDays.length * rowH + 34;
    var x = function (d) { return left + (W - left - right) * d / max; };
    var svg = "<svg class=\"chart\" viewBox=\"0 0 " + W + " " + H + "\" width=\"100%\" role=\"img\" aria-label=\"Days from the scheduling vote to the Board decision\">";
    for (var t = 0; t <= 42; t += 7) svg += "<line class=\"grid\" x1=\"" + x(t) + "\" x2=\"" + x(t) + "\" y1=\"" + (top - 6) + "\" y2=\"" + (H - 26) + "\" stroke-width=\"1\"/><text class=\"muted\" x=\"" + x(t) + "\" y=\"" + (H - 10) + "\" font-size=\"11\" text-anchor=\"middle\">" + t + "</text>";
    svg += "<text class=\"muted\" x=\"" + left + "\" y=\"14\" font-size=\"11.5\">Days from scheduling vote to Board decision</text>";
    withDays.forEach(function (r, i) {
      var y = top + i * rowH;
      var label = r.subject.length > 44 ? r.subject.slice(0, 43) + "…" : r.subject;
      svg += "<text x=\"" + (left - 10) + "\" y=\"" + (y + 15) + "\" font-size=\"12\" text-anchor=\"end\">" + esc(label) + "</text>";
      svg += "<rect class=\"bar\" x=\"" + left + "\" y=\"" + (y + 4) + "\" width=\"" + (x(r.days) - left) + "\" height=\"16\" rx=\"2\" fill=\"currentColor\"/>";
      svg += "<text x=\"" + (x(r.days) + 6) + "\" y=\"" + (y + 16) + "\" font-size=\"12\" font-weight=\"600\">" + r.days + " d &middot; " + esc(r.trace[r.trace.length - 1]) + "</text>";
    });
    svg += "</svg>";
    var table = "<div class=\"dt-wrap\"><table class=\"dt\"><thead><tr><th>Case (linked matters)</th><th>Recorded actions</th><th>Dates</th></tr></thead><tbody>" +
      rows.map(function (r) { return "<tr><td>" + esc(r.title) + "<div class=\"kicker\">" + r.matters.join(" + ") + "</div></td><td><div class=\"trace\">" + r.trace.map(function (a) { return "<span>" + esc(a) + "</span>"; }).join("") + "</div></td><td class=\"feel\">" + esc(r.dates.join(" → ")) + "</td></tr>"; }).join("") + "</tbody></table></div>";
    return "<p class=\"lede\">How Albemarle County ordinances were actually processed in 2026, rebuilt from the county's Legistar records (one ordinance is split across a consent-agenda matter that schedules the hearing and a later hearing matter). As written, Va. Code &sect; 15.2-1427(F) requires two newspaper notices before a county adopts an ordinance: the first no more than 28 days and the second at least 7 days before the meeting.</p>" +
      "<div class=\"grid2\"><div class=\"box\" style=\"color:var(--accent)\">" + svg + "</div><div class=\"box\"><h3>What the records can and cannot show</h3><ul class=\"plain\">" +
      L.findings.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + "</ul><div class=\"kicker\">Not observable in Legistar: " + esc(L.unobservable.join(", ")) + "</div></div></div>" + table +
      "<p class=\"prov\">" + esc(L.source) + "</p>";
  }
  function panelReview() {
    var flags = DATA.locusFlags, keys = Object.keys(flags);
    var g = current.checks.grounding;
    return "<div class=\"grid2\"><div class=\"box\"><h3>For legal review</h3><ul class=\"plain\">" + current.gaps.map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" +
      "<div class=\"fact\">Citations by grounding: " + Object.keys(g).map(function (k) { return esc(k) + " " + g[k]; }).join(" &middot; ") + "</div></div>" +
      "<div class=\"box\"><h3>Source-text repairs (LOCUS chunks)</h3><p class=\"lede\">Problems found while rebuilding whole sections from the dataset's OCR chunks. Each is flagged on the section so reviewers can check the primary source.</p><ul class=\"plain\">" +
      keys.map(function (k) { return "<li><b>" + esc(k) + ":</b> " + esc(flags[k].join("; ")) + "</li>"; }).join("") + "</ul></div></div>";
  }
  function panelChecks() {
    var c = current.checks;
    var row = function (ok, text) { return "<li><span class=\"" + (ok ? "y" : "n") + "\">" + (ok ? "✓" : "✗") + "</span><span>" + text + "</span></li>"; };
    var items = [
      row(c.bpmn_xsd === 0, "BPMN 2.0 XML validates against the OMG BPMN20.xsd (" + c.bpmn_xsd + " errors)"),
      row(c.layout === 0, "Diagram interchange generated by bpmn-auto-layout 2.0 (" + c.layout + " warnings)"),
      row(c.lint === 0, "bpmnlint recommended rules plus five Lexipedia legal rules (" + c.lint + " findings)"),
      row(c.quote_misses === 0, c.quotes + " quoted spans found verbatim in the rebuilt law text"),
    ];
    if (c.counts.decisions) { items.push(row(c.dmn_xsd === 0, "DMN 1.3 validates against DMN13.xsd")); items.push(row(c.dmnlint === true, "dmnlint recommended rules pass")); }
    items.push(row(true, "Wikibase payload: " + c.wikibase.items + " items, " + c.wikibase.statements + " statements (QuickStatements, two phases)"));
    var sc = c.scenarios.length ? "<div class=\"box\"><h3>Executed in SpiffWorkflow</h3><ul class=\"ticks\">" + c.scenarios.map(function (s) { return row(true, esc(s)); }).join("") + "</ul></div>" : "";
    return "<div class=\"grid2\"><div class=\"box\"><h3>Standards and legal-quality checks</h3><ul class=\"ticks\">" + items.join("") + "</ul></div>" + sc + "</div>";
  }
  var PANELS = {decisions: panelDecisions, structure: panelStructure, practice: panelPractice, review: panelReview, checks: panelChecks};
  function renderPanel() { if (current) $("panel").innerHTML = PANELS[panelName](); }
  function showPanel(name) {
    panelName = PANELS[name] ? name : "decisions";
    Array.prototype.forEach.call($("subtabs").children, function (b) { b.setAttribute("aria-selected", String(b.dataset.panel === panelName)); });
    renderPanel();
  }

  // ------------------------------------------------------------- boot
  $("models").innerHTML = DATA.models.map(function (m) { return "<button type=\"button\" role=\"tab\" data-id=\"" + esc(m.id) + "\" aria-selected=\"false\">" + esc(m.label) + "</button>"; }).join("");
  Array.prototype.forEach.call($("models").children, function (b) { b.addEventListener("click", function () { loadModel(b.dataset.id); }); });
  Array.prototype.forEach.call($("subtabs").children, function (b) { b.addEventListener("click", function () { showPanel(b.dataset.panel); }); });
  $("step-picker").addEventListener("change", function (e) { select(e.target.value, true); });
  $("zoom-in").addEventListener("click", function () { if (viewer) { var c = viewer.get("canvas"); c.zoom(c.zoom() * 1.25); } });
  $("zoom-out").addEventListener("click", function () { if (viewer) { var c = viewer.get("canvas"); c.zoom(c.zoom() / 1.25); } });
  $("zoom-fit").addEventListener("click", function () { if (viewer) viewer.get("canvas").zoom("fit-viewport", "auto"); });
  if (window.BpmnJS) {
    viewer = new window.BpmnJS({container: "#canvas"});
    viewer.get("eventBus").on("element.click", function (e) {
      var el = e.element && (e.element.labelTarget || e.element);
      var id = el && el.businessObject && el.businessObject.id;
      if (id && current.elements[id]) select(id, false);
    });
  } else {
    $("canvas").innerHTML = "<p class=\"load-error\">The diagram library (bpmn-js) did not load, so only the law text and tables are shown. Check the network connection and reload.</p>";
  }
  var hash = (location.hash || "").replace("#", "");
  if (PANELS[hash]) panelName = hash;
  Array.prototype.forEach.call($("subtabs").children, function (b) { b.setAttribute("aria-selected", String(b.dataset.panel === panelName)); });
  loadModel(store("lx-model") || DATA.models[0].id);
})();
