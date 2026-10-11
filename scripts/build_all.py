"""Regenerate every artifact under out/ and write out/report.json (numbers used in the deck).

    python scripts/build_all.py                     # offline: gold models, compiled model, checks

``--publish`` is refused: the gold models' pages are process: and law: pages (with media and a "Machine checks"
block), outside the lexflow: namespace that lexflow may write on lexipedia.xyz.  The lexflow pages are published by
the publish step (``python -m lexflow run publish --dry-run`` first), which, like the DokuWiki client itself, goes
through ``lexflow.publish.dokuwiki.require_namespace``.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import gold  # noqa: E402
from lexflow.bpmn_xml import to_bpmn_xml  # noqa: E402
from lexflow.dmn_xml import write_dmn, write_dmn_split  # noqa: E402
from lexflow.extract.compile import compile_facts  # noqa: E402
from lexflow.extract.schema import LegalProcessFacts, ollama_schema  # noqa: E402
from lexflow.layout import auto_layout  # noqa: E402
from lexflow.petri import analyse, powl_text  # noqa: E402
from lexflow.publish.wikibase import build_bundle, quickstatements, property_proposals_qs  # noqa: E402
from lexflow.render_svg import render  # noqa: E402
from lexflow.sources.legistar import build_cases, conformance  # noqa: E402
from lexflow.text.sections import resegment  # noqa: E402
from lexflow.validate import bpmnlint, dmnlint, lex_checks, xsd_errors  # noqa: E402

OUT = ROOT / "out"


def model_report(name, m, out: Path) -> dict:
    semantic = to_bpmn_xml(m)
    laid, warnings = auto_layout(semantic)
    (out / f"{name}.semantic.bpmn").write_text(semantic)
    (out / f"{name}.bpmn").write_text(laid)
    (out / f"{name}.svg").write_text(render(laid, title=m.title))
    rep = {"title": m.title, "jurisdiction": m.jurisdiction_name}
    types = Counter(n.type for _, _, n in m.iter_nodes())
    rep["counts"] = {"pools": len(m.participants), "lanes": sum(len(p.lanes) for p in m.processes()),
                     "flow_nodes": sum(types.values()), "node_types": dict(types),
                     "sequence_flows": sum(len(p.flows) for p in m.processes()) + sum(len(n.flows) for _, _, n in m.iter_nodes()),
                     "message_flows": len(m.message_flows), "decisions": len(m.decisions),
                     "rules": sum(len(d.rules) for d in m.decisions)}
    rep["bpmn_xsd_errors"] = xsd_errors(laid)
    rep["layout_warnings"] = warnings
    rep["bpmnlint"] = bpmnlint(out / f"{name}.bpmn")["problems"]
    if m.decisions:
        dmn = write_dmn(m)
        (out / f"{name}.dmn").write_text(dmn)
        for did, x in write_dmn_split(m, "python").items():
            (out / f"{name}.{did}.spiff.dmn").write_text(x)
        rep["dmn_xsd_errors"] = xsd_errors(dmn, "dmn")
        rep["dmnlint_ok"] = dmnlint(out / f"{name}.dmn")["ok"]
    rep["lex"] = lex_checks(m).summary()
    nets = {}
    for proc in m.processes():
        r, net, im, fm = analyse(proc, out_dir=out / "petri")
        import powl
        text = powl_text(powl.convert_from_workflow_net(net)) if not r.error else None
        nets[proc.id] = {"places": r.places, "transitions": r.transitions, "visible": r.visible,
                         "sound": r.sound, "reachable_states": r.reachable_states, "powl": text,
                         "approximations": r.notes, "error": r.error}
    rep["petri"] = nets
    b = build_bundle(m)
    p1, p2 = quickstatements(b)
    (out / "wikibase").mkdir(exist_ok=True)
    (out / "wikibase" / f"{name}.phase1.qs").write_text(p1)
    (out / "wikibase" / f"{name}.phase2.qs").write_text(p2)
    rep["wikibase"] = {"items": len(b.items), "statements": len(b.statements)}
    return rep


PUBLISH_REFUSED = ("scripts/build_all.py --publish is refused: it would write process: and law: pages and media, "
                   "outside the lexflow: namespace. Publish the lexflow: pages with `python -m lexflow run publish "
                   "--dry-run`, then `python -m lexflow run publish`.")


def refuse_publish() -> None:
    """The legacy writer's ids go through the same namespace rule as the publish step, before anything is built."""
    from lexflow.publish.dokuwiki import NamespaceError, page_id, require_namespace
    try:
        for legacy in (page_id("process", "va/albemarle_county", "17-211"), page_id("law", "va", "17-211")):
            require_namespace(legacy)
    except NamespaceError as e:
        print(f"{PUBLISH_REFUSED} ({e})", file=sys.stderr)
        raise SystemExit(2) from None


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="refused: see the module docstring")
    args = ap.parse_args(argv)
    if args.publish:
        refuse_publish()
    OUT.mkdir(exist_ok=True)
    report = {"models": {}}
    models = {name: fn() for name, fn in gold.ALL.items()}
    facts = LegalProcessFacts.model_validate_json((ROOT / "fixtures/gold/albemarle_17_211.facts.json").read_text())
    g = models["albemarle_17_211"]
    models["compiled_17_211"] = compile_facts(
        facts, model_id="va-albemarle-17-211-compiled", jurisdiction=g.jurisdiction,
        jurisdiction_name=g.jurisdiction_name, code="Albemarle County Code", text=g.texts[0],
        jurisdiction_qid=g.jurisdiction_qid)
    for name, m in models.items():
        report["models"][name] = model_report(name, m, OUT)
        print("built", name)
    (OUT / "wikibase" / "property_proposals.txt").write_text(property_proposals_qs())
    # text rebuild flags on the LOCUS sample
    rows = json.loads((ROOT / "fixtures/locus/va_samples.json").read_text())["rows"]
    secs = resegment([r for r in rows if r["county"] == "albemarle_county"], "Albemarle County Code", "va/albemarle_county") + \
        resegment([r for r in rows if r["city"] == "charlottesville"], "Charlottesville City Code", "va/charlottesville")
    report["locus_rebuild"] = {"rows": len(rows), "sections": len(secs),
                               "flags": {s.number: s.flags for s in secs if s.flags}}
    d = json.loads((ROOT / "fixtures/legistar/albemarle_2026.json").read_text())
    c = conformance(build_cases(d["matters"], d["histories"]))
    report["legistar"] = {"cases": c.cases, "complete": c.complete_cases, "variants": c.variants,
                          "days_authorize_to_decision": c.days_authorize_to_decision,
                          "unobservable": c.unobservable_steps, "findings": c.findings}
    report["ollama_schema_bytes"] = len(json.dumps(ollama_schema()))
    rt = OUT / "bpmn_assistant_roundtrip.json"
    if rt.exists():
        report["bpmn_assistant_roundtrip"] = json.loads(rt.read_text())
    (OUT / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print("wrote", OUT / "report.json")


if __name__ == "__main__":
    main()
