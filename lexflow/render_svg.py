"""Static SVG rendering of BPMN 2.0 + DI, colour-coded by legal grounding.

bpmn-js needs a browser; DokuWiki's PDF export drops bpmnio diagrams; slides and
Wikimedia-style image uploads need a file.  This draws pools, lanes, activities,
events (with timer/message/etc. markers), gateways, data, flows and annotations
directly from the DI geometry.
"""
from __future__ import annotations

import html
import math
from dataclasses import dataclass

from lxml import etree

B = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
DI = "{http://www.omg.org/spec/BPMN/20100524/DI}"
DC = "{http://www.omg.org/spec/DD/20100524/DC}"
DDI = "{http://www.omg.org/spec/DD/20100524/DI}"
LEX = "{https://lexipedia.xyz/ns/lex/1.0}"

PALETTE = {
    "ink": "#1f2933", "muted": "#64707d", "line": "#3e4c59", "pool": "#f7f6f2", "lane": "#d9d6cc",
    "explicit": "#1f2933", "implied": "#a15c07", "assumed": "#7b8794", "timer": "#1d4ed8",
    "fill": "#ffffff", "data": "#52606d", "bg": "#ffffff",
}
TASKS = {"task", "userTask", "serviceTask", "sendTask", "receiveTask", "businessRuleTask", "manualTask",
         "scriptTask", "callActivity"}
EVENTS = {"startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent"}
GATEWAYS = {"exclusiveGateway", "parallelGateway", "inclusiveGateway", "eventBasedGateway", "complexGateway"}


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2


def _local(el) -> str:
    return etree.QName(el).localname


def _short(text: str, limit: int) -> str:
    """A label in full, or cut at a word boundary with an ellipsis: never mid-word (extract/compile.py's rule)."""
    t = " ".join(str(text or "").split())
    if len(t) <= limit or " " not in t[:limit - 1]:
        return t
    return t[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-(") + "…"


def _wrap(text: str, width_px: float, size: float = 11) -> list[str]:
    per_line = max(4, int(width_px / (size * 0.56)))
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= per_line:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > 4:                  # what does not fit ends at a word, with an ellipsis
        lines = lines[:3] + [lines[3].rstrip(" ,;:-(") + "…"]
    return lines


def _text(x, y, lines, size=11, anchor="middle", color=None, weight="400"):
    color = color or PALETTE["ink"]
    out = [f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{color}" '
           f'font-weight="{weight}" font-family="Inter, Helvetica, Arial, sans-serif">']
    start = y - (len(lines) - 1) * size * 0.6
    for i, ln in enumerate(lines):
        out.append(f'<tspan x="{x:.1f}" y="{start + i * size * 1.2:.1f}">{html.escape(ln)}</tspan>')
    out.append("</text>")
    return "".join(out)


def _grounding(el) -> str | None:
    vals = [s.get("grounding") for s in el.findall(f"./{B}extensionElements/{LEX}grounding/{LEX}source")]
    if not vals:
        return None
    if "explicit" in vals:
        return "explicit"
    return "implied" if "implied" in vals else "assumed"


def _clock(cx, cy, r, color):
    s = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff" stroke="{color}" stroke-width="1.5"/>']
    for k in range(12):
        a = k * math.pi / 6
        s.append(f'<line x1="{cx + math.cos(a) * r * 0.75:.1f}" y1="{cy + math.sin(a) * r * 0.75:.1f}" '
                 f'x2="{cx + math.cos(a) * r * 0.92:.1f}" y2="{cy + math.sin(a) * r * 0.92:.1f}" stroke="{color}" stroke-width="1"/>')
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - r * 0.6}" stroke="{color}" stroke-width="1.5"/>')
    s.append(f'<line x1="{cx}" y1="{cy}" x2="{cx + r * 0.45}" y2="{cy}" stroke="{color}" stroke-width="1.5"/>')
    return "".join(s)


def _envelope(cx, cy, w, h, color, filled=False):
    x, y = cx - w / 2, cy - h / 2
    fill = color if filled else "#fff"
    flap = "#fff" if filled else color
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" fill="{fill}" stroke="{color}" stroke-width="1.2"/>'
            f'<polyline points="{x:.1f},{y:.1f} {cx:.1f},{cy + 1:.1f} {x + w:.1f},{y:.1f}" fill="none" stroke="{flap}" stroke-width="1.2"/>')


def render(bpmn_xml: str, title: str | None = None, scale: float = 1.0, margin: int = 20) -> str:
    root = etree.fromstring(bpmn_xml.encode())
    index = {el.get("id"): el for el in root.iter() if isinstance(el.tag, str) and el.get("id")}
    shapes, edges = [], []
    planes = list(root.iter(f"{DI}BPMNPlane"))
    drilldown = {pl.get("bpmnElement") for pl in planes[1:]}      # collapsed sub-processes with their own plane
    for plane in planes[:1]:
        for s in plane.iter(f"{DI}BPMNShape"):
            b = s.find(f"{DC}Bounds")
            lb = s.find(f"{DI}BPMNLabel/{DC}Bounds")
            box = Box(float(b.get("x")), float(b.get("y")), float(b.get("width")), float(b.get("height")))
            label = Box(float(lb.get("x")), float(lb.get("y")), float(lb.get("width")), float(lb.get("height"))) if lb is not None else None
            shapes.append((s.get("bpmnElement"), box, s.get("isExpanded"), label))
        for e in plane.iter(f"{DI}BPMNEdge"):
            pts = [(float(w.get("x")), float(w.get("y"))) for w in e.findall(f"{DDI}waypoint")]
            lb = e.find(f"{DI}BPMNLabel/{DC}Bounds")
            edges.append((e.get("bpmnElement"), pts, Box(float(lb.get("x")), float(lb.get("y")), float(lb.get("width")), float(lb.get("height"))) if lb is not None else None))
    xs = [b.x for _, b, _, _ in shapes] + [p[0] for _, pts, _ in edges for p in pts]
    ys = [b.y for _, b, _, _ in shapes] + [p[1] for _, pts, _ in edges for p in pts]
    x2 = [b.x + b.w for _, b, _, _ in shapes] + [p[0] for _, pts, _ in edges for p in pts]
    y2 = [b.y + b.h for _, b, _, _ in shapes] + [p[1] for _, pts, _ in edges for p in pts]
    minx, miny = min(xs) - margin, min(ys) - margin - (28 if title else 0)
    width, height = max(x2) - minx + margin, max(y2) - miny + margin
    P = PALETTE
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{minx:.0f} {miny:.0f} {width:.0f} {height:.0f}" '
           f'width="{width * scale:.0f}" height="{height * scale:.0f}" role="img">',
           "<defs>",
           f'<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="{P["line"]}"/></marker>',
           f'<marker id="marr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">'
           f'<path d="M0,0 L10,5 L0,10 z" fill="#fff" stroke="{P["muted"]}"/></marker>',
           f'<marker id="mstart" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6">'
           f'<circle cx="5" cy="5" r="4" fill="#fff" stroke="{P["muted"]}"/></marker>',
           "</defs>",
           f'<rect x="{minx}" y="{miny}" width="{width}" height="{height}" fill="{P["bg"]}"/>']
    if title:
        out.append(_text(minx + margin, miny + 20, [title], size=15, anchor="start", weight="600"))

    def el_type(i):
        el = index.get(i)
        return (_local(el), el) if el is not None else (None, None)

    # containers first: participants, lanes, expanded sub-processes
    for i, b, expanded, _ in shapes:
        t, el = el_type(i)
        if t == "participant":
            out.append(f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" fill="{P["pool"]}" stroke="{P["muted"]}" stroke-width="1.2"/>')
            out.append(f'<line x1="{b.x + 30}" y1="{b.y}" x2="{b.x + 30}" y2="{b.y + b.h}" stroke="{P["muted"]}"/>')
            name = el.get("name", "")
            out.append(f'<text transform="translate({b.x + 19},{b.cy}) rotate(-90)" font-size="12" text-anchor="middle" '
                       f'fill="{P["ink"]}" font-weight="600" font-family="Inter, Helvetica, Arial, sans-serif">{html.escape(_short(name, 60))}</text>')
    for i, b, expanded, _ in shapes:
        t, el = el_type(i)
        if t == "lane":
            out.append(f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" fill="none" stroke="{P["lane"]}"/>')
            out.append(f'<line x1="{b.x + 24}" y1="{b.y}" x2="{b.x + 24}" y2="{b.y + b.h}" stroke="{P["lane"]}"/>')
            out.append(f'<text transform="translate({b.x + 16},{b.cy}) rotate(-90)" font-size="10.5" text-anchor="middle" '
                       f'fill="{P["muted"]}" font-family="Inter, Helvetica, Arial, sans-serif">{html.escape(_short(el.get("name", ""), 50))}</text>')
    for i, b, expanded, _ in shapes:
        t, el = el_type(i)
        if t in ("subProcess", "transaction", "adHocSubProcess") and expanded != "false" and i not in drilldown:
            dash = ' stroke-dasharray="2 3"' if el.get("triggeredByEvent") == "true" else ""
            g = _grounding(el)
            out.append(f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" rx="10" fill="#fdfdfb" '
                       f'stroke="{P.get(g or "explicit")}" stroke-width="1.4"{dash}/>')
            out.append(_text(b.x + 8, b.y + 16, [el.get("name", "")], size=11, anchor="start", weight="600"))

    # edges
    for i, pts, lb in edges:
        t, el = el_type(i)
        if not pts:
            continue
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        if t == "sequenceFlow":
            out.append(f'<path d="{d}" fill="none" stroke="{P["line"]}" stroke-width="1.4" marker-end="url(#arr)"/>')
            src = index.get(el.get("sourceRef"))
            if src is not None and src.get("default") == i and len(pts) > 1:
                (ax, ay), (bx, by) = pts[0], pts[1]
                ang = math.atan2(by - ay, bx - ax)
                mx, my = ax + math.cos(ang) * 10, ay + math.sin(ang) * 10
                out.append(f'<line x1="{mx - 5 * math.sin(ang) - 3 * math.cos(ang):.1f}" y1="{my + 5 * math.cos(ang) - 3 * math.sin(ang):.1f}" '
                           f'x2="{mx + 5 * math.sin(ang) + 3 * math.cos(ang):.1f}" y2="{my - 5 * math.cos(ang) + 3 * math.sin(ang):.1f}" stroke="{P["line"]}" stroke-width="1.4"/>')
            if el.get("name") and lb is not None:
                out.append(_text(lb.cx, lb.cy + 3, _wrap(el.get("name"), max(lb.w, 70), 10), size=10, color=P["muted"]))
        elif t == "messageFlow":
            out.append(f'<path d="{d}" fill="none" stroke="{P["muted"]}" stroke-width="1.2" stroke-dasharray="6 4" '
                       f'marker-start="url(#mstart)" marker-end="url(#marr)"/>')
            if el.get("name") and lb is not None:
                out.append(_text(lb.cx, lb.cy + 3, _wrap(el.get("name"), max(lb.w, 80), 9.5), size=9.5, color=P["muted"]))
        elif t in ("association", "dataInputAssociation", "dataOutputAssociation"):
            arrow = ' marker-end="url(#arr)"' if t != "association" else ""
            out.append(f'<path d="{d}" fill="none" stroke="{P["data"]}" stroke-width="1" stroke-dasharray="2 3"{arrow}/>')

    # nodes
    for i, b, expanded, lb in shapes:
        t, el = el_type(i)
        if t is None or t in ("participant", "lane"):
            continue
        g = _grounding(el) or "explicit"
        stroke = P[g]
        dash = ' stroke-dasharray="5 3"' if g in ("implied", "assumed") else ""
        name = el.get("name", "") or ""
        collapsed = t in ("subProcess", "transaction", "adHocSubProcess") and (expanded == "false" or i in drilldown)
        if t in TASKS or collapsed:
            width = 3 if t == "callActivity" else 1.5
            if collapsed and el.get("triggeredByEvent") == "true":
                dash = ' stroke-dasharray="2 3"'
            out.append(f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" rx="10" fill="{P["fill"]}" stroke="{stroke}" stroke-width="{width}"{dash}/>')
            if collapsed:
                out.append(f'<rect x="{b.cx - 6}" y="{b.y + b.h - 15}" width="12" height="12" fill="#fff" stroke="{P["ink"]}"/>'
                           f'<path d="M{b.cx - 3},{b.y + b.h - 9} h6 M{b.cx},{b.y + b.h - 12} v6" stroke="{P["ink"]}"/>')
            ix, iy = b.x + 12, b.y + 12
            if t == "userTask":
                out.append(f'<circle cx="{ix}" cy="{iy - 2}" r="3.5" fill="none" stroke="{P["muted"]}"/>'
                           f'<path d="M{ix - 6},{iy + 7} Q{ix},{iy} {ix + 6},{iy + 7}" fill="none" stroke="{P["muted"]}"/>')
            elif t in ("sendTask", "receiveTask"):
                out.append(_envelope(ix, iy, 13, 9, P["muted"], filled=(t == "sendTask")))
            elif t == "businessRuleTask":
                out.append(f'<rect x="{ix - 7}" y="{iy - 5}" width="14" height="10" fill="#fff" stroke="{P["muted"]}"/>'
                           f'<line x1="{ix - 7}" y1="{iy - 1}" x2="{ix + 7}" y2="{iy - 1}" stroke="{P["muted"]}"/>'
                           f'<line x1="{ix - 3}" y1="{iy - 1}" x2="{ix - 3}" y2="{iy + 5}" stroke="{P["muted"]}"/>')
            elif t == "manualTask":
                out.append(f'<path d="M{ix - 6},{iy + 3} h10 v-6 h-10 z" fill="none" stroke="{P["muted"]}"/>')
            out.append(_text(b.cx, b.cy + 4, _wrap(name, b.w - 14), size=10.5))
            if el.find(f"{B}multiInstanceLoopCharacteristics") is not None:
                for k in (-4, 0, 4):
                    out.append(f'<line x1="{b.cx + k}" y1="{b.y + b.h - 12}" x2="{b.cx + k}" y2="{b.y + b.h - 4}" stroke="{P["ink"]}"/>')
        elif t in EVENTS:
            r = b.w / 2
            defs = [c for c in el if _local(c).endswith("EventDefinition")]
            kind = _local(defs[0]).replace("EventDefinition", "") if defs else "none"
            color = P["timer"] if kind == "timer" else stroke
            sw = 3 if t == "endEvent" else 1.6
            nonint = (t == "boundaryEvent" and el.get("cancelActivity") == "false") or \
                     (t == "startEvent" and el.get("isInterrupting") == "false")
            d2 = ' stroke-dasharray="4 3"' if nonint else dash
            out.append(f'<circle cx="{b.cx}" cy="{b.cy}" r="{r}" fill="#fff" stroke="{color}" stroke-width="{sw}"{d2}/>')
            if t in ("intermediateCatchEvent", "intermediateThrowEvent", "boundaryEvent"):
                out.append(f'<circle cx="{b.cx}" cy="{b.cy}" r="{r - 3}" fill="none" stroke="{color}" stroke-width="1.2"{d2}/>')
            if kind == "timer":
                out.append(_clock(b.cx, b.cy, r - 6, color))
            elif kind == "message":
                filled = t in ("endEvent", "intermediateThrowEvent")
                out.append(_envelope(b.cx, b.cy, r * 1.05, r * 0.72, color, filled))
            elif kind == "terminate":
                out.append(f'<circle cx="{b.cx}" cy="{b.cy}" r="{r - 6}" fill="{color}"/>')
            elif kind in ("signal", "escalation", "error", "conditional"):
                out.append(_text(b.cx, b.cy + 4, [{"signal": "△", "escalation": "↑", "error": "ϟ",
                                                    "conditional": "≡"}[kind]], size=12, color=color))
            if name:
                if lb is not None:
                    out.append(_text(lb.cx, lb.cy + 3, _wrap(name, max(lb.w, 90), 10), size=10, color=P["muted"] if g == "explicit" else P[g]))
                else:
                    out.append(_text(b.cx, b.y + b.h + 14, _wrap(name, 110, 10), size=10, color=P["muted"]))
        elif t in GATEWAYS:
            pts = f"{b.cx},{b.y} {b.x + b.w},{b.cy} {b.cx},{b.y + b.h} {b.x},{b.cy}"
            out.append(f'<polygon points="{pts}" fill="#fff" stroke="{stroke}" stroke-width="1.5"{dash}/>')
            m = 11
            if t == "exclusiveGateway":
                out.append(f'<path d="M{b.cx - m * .7},{b.cy - m * .7} L{b.cx + m * .7},{b.cy + m * .7} M{b.cx + m * .7},{b.cy - m * .7} L{b.cx - m * .7},{b.cy + m * .7}" stroke="{P["ink"]}" stroke-width="3"/>')
            elif t == "parallelGateway":
                out.append(f'<path d="M{b.cx},{b.cy - m} L{b.cx},{b.cy + m} M{b.cx - m},{b.cy} L{b.cx + m},{b.cy}" stroke="{P["ink"]}" stroke-width="3"/>')
            elif t == "inclusiveGateway":
                out.append(f'<circle cx="{b.cx}" cy="{b.cy}" r="{m}" fill="none" stroke="{P["ink"]}" stroke-width="2.5"/>')
            elif t == "eventBasedGateway":
                out.append(f'<circle cx="{b.cx}" cy="{b.cy}" r="{m}" fill="none" stroke="{P["ink"]}" stroke-width="1"/>'
                           f'<circle cx="{b.cx}" cy="{b.cy}" r="{m - 3}" fill="none" stroke="{P["ink"]}" stroke-width="1"/>')
                pent = " ".join(f"{b.cx + math.cos(-math.pi / 2 + k * 2 * math.pi / 5) * 5.5:.1f},"
                                f"{b.cy + math.sin(-math.pi / 2 + k * 2 * math.pi / 5) * 5.5:.1f}" for k in range(5))
                out.append(f'<polygon points="{pent}" fill="none" stroke="{P["ink"]}"/>')
            if name:
                if lb is not None:
                    out.append(_text(lb.cx, lb.cy + 3, _wrap(name, max(lb.w, 90), 10), size=10, color=P["muted"]))
                else:
                    out.append(_text(b.cx, b.y - 6, [_short(name, 40)], size=10, color=P["muted"]))
        elif t in ("dataObjectReference", "dataObject"):
            f = 10
            out.append(f'<path d="M{b.x},{b.y} h{b.w - f} l{f},{f} v{b.h - f} h{-b.w} z M{b.x + b.w - f},{b.y} v{f} h{f}" '
                       f'fill="#fff" stroke="{P["data"]}" stroke-width="1.2"/>')
            if name:
                out.append(_text(b.cx, b.y + b.h + 12, _wrap(name, 120, 9.5), size=9.5, color=P["data"]))
        elif t == "dataStoreReference":
            ry = 6
            out.append(f'<path d="M{b.x},{b.y + ry} v{b.h - 2 * ry} a{b.w / 2},{ry} 0 0 0 {b.w},0 v{-(b.h - 2 * ry)}" fill="#fff" stroke="{P["data"]}" stroke-width="1.2"/>'
                       f'<ellipse cx="{b.cx}" cy="{b.y + ry}" rx="{b.w / 2}" ry="{ry}" fill="#fff" stroke="{P["data"]}" stroke-width="1.2"/>')
            if name:
                out.append(_text(b.cx, b.y + b.h + 12, _wrap(name, 130, 9.5), size=9.5, color=P["data"]))
        elif t == "textAnnotation":
            out.append(f'<path d="M{b.x + 12},{b.y} h-12 v{b.h} h12" fill="none" stroke="{P["muted"]}"/>')
            txt = (el.findtext(f"{B}text") or "")
            out.append(_text(b.x + 6, b.y + 14, _wrap(txt, b.w - 8, 9.5), size=9.5, anchor="start", color=P["muted"]))
    out.append("</svg>")
    return "\n".join(out)


def legend_svg() -> str:
    P = PALETTE
    items = [("explicit", "Step stated in the text"), ("implied", "Presupposed by another provision"),
             ("assumed", "Modeller's operational assumption")]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 30" width="640" height="30">']
    x = 0
    for key, label in items:
        dash = ' stroke-dasharray="5 3"' if key != "explicit" else ""
        parts.append(f'<rect x="{x + 2}" y="6" width="26" height="18" rx="5" fill="#fff" stroke="{P[key]}" stroke-width="1.6"{dash}/>')
        parts.append(_text(x + 34, 19, [label], size=11, anchor="start", color=P["ink"]))
        x += 215
    parts.append("</svg>")
    return "".join(parts)
