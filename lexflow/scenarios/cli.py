"""``lexflow hypo``: question families, their scenario space, runs, sensitivity and free-text intake.

    lexflow hypo family [glass_studio_va] [--save]      the family: dimensions, tables, grounding, dropped rules
    lexflow hypo expand glass_studio_va [--by-district] the size of the space: all combinations and a pairwise set
    lexflow hypo run glass_studio_va CVL-CCX8-EX-NG-O2Y-P50-F0-WR-E2-H0-R50-S1 [--variant highimpact] [--json]
    lexflow hypo run glass_studio_va --persona hot_shop_classes --locality staunton
    lexflow hypo run glass_studio_va --set locality=albemarle --set fuel=propane ...
    lexflow hypo run glass_studio_va --pairwise [--save]  every pairwise scenario, baseline and each variant
    lexflow hypo sens glass_studio_va --persona hot_shop_classes --locality charlottesville
    lexflow hypo ask glass_studio_va "a hot shop with a gas furnace in Staunton, classes of 60, wine nights"
    lexflow hypo report glass_studio_va --out <file.json>  personas x localities, sensitivity, pairwise, variants
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from ..store import db
from . import expand as X
from . import intake as IN
from . import run as R
from . import sensitivity as SE
from .family import COUNTED, Family, FamilyError, families

DEFAULT = "glass_studio_va"


def _fam(name: str | None) -> Family:
    return Family.load(name or DEFAULT)


def _sets(pairs: list[str] | None) -> dict:
    out = {}
    for p in pairs or []:
        k, _, v = p.partition("=")
        v = v.strip()
        if v.lower() in ("true", "false"):
            out[k.strip()] = v.lower() == "true"
        else:
            try:
                out[k.strip()] = float(v) if "." in v else int(v)
            except ValueError:
                out[k.strip()] = v
    return out


def cmd_family(a) -> int:
    fams = [_fam(a.family)] if a.family else families()
    for f in fams:
        probs = f.check()
        print(json.dumps({**f.summary(), "grounding": {k: v for k, v in (f.spec.get("grounding") or {}).items()
                                                        if k != "unmatched"},
                          "problems": probs, "dropped": f.dropped}, indent=1, ensure_ascii=False))
        if a.save:
            con = db.connect()
            try:
                R.save_family(con, f)
            finally:
                con.close()
            print(f"saved {f.id}: families, {len(f.personas)} personas, {len(f.assumptions)} assumptions")
    return 0


def cmd_expand(a) -> int:
    f = _fam(a.family)
    t0 = time.time()
    full = X.count(f, by_class=False)
    by = X.count(f, by_class=True)
    pw = X.pairwise(f, by_class=not a.by_district)
    cov = X.pair_coverage(f, pw, by_class=not a.by_district)
    print(json.dumps({"family": f.id, "all_combinations": full, "all_by_class": by,
                      "pairwise": {"scenarios": len(pw), "by_class": not a.by_district, **cov},
                      "district_classes": X.classes(f, "district", tuple(f.variants)),
                      "seconds": round(time.time() - t0, 1)}, indent=1, default=str))
    return 0


def _print(out: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    else:
        print(R.text(out))
        print(f"timeline about {out['order']['timeline_days']} days; assumptions {', '.join(out['assumptions'])}")


def cmd_run(a) -> int:
    from .family import FAMILIES_DIR
    if a.family and a.scenario is None and not (FAMILIES_DIR / f"{a.family}.json").exists() and "-" in a.family:
        a.scenario, a.family = a.family, DEFAULT           # `lexflow hypo run CVL-...` with the default family
    f = _fam(a.family)
    if a.pairwise:
        return run_population(f, save=a.save)
    if a.scenario:
        inputs, variant = f.parse_id(a.scenario)
        variant = a.variant or variant
    elif a.persona:
        inputs, variant = f.persona_inputs(a.persona, a.locality), a.variant
    else:
        inputs, variant = _sets(a.set), a.variant
    out = R.evaluate(f, inputs, variant)
    _print(out, a.json)
    if a.save:
        con = db.connect()
        try:
            rid = R.record(con, f, out, persona=a.persona, created_by="persona" if a.persona else "cli")
        finally:
            con.close()
        print(f"stored run {rid}", file=sys.stderr)
    return 0


def run_population(f: Family, save: bool = False, log=print) -> int:
    """Every pairwise scenario under the baseline and under each variant; with ``save`` the scenarios and runs are
    stored (one short write each).  Prints what each variant changes."""
    t0 = time.time()
    tests = X.pairwise(f, by_class=True, variants=tuple(f.variants))
    con = db.connect() if save else None
    base_out = {}
    try:
        for inp in tests:
            o = R.evaluate(f, inp)
            base_out[o["scenario"]] = o
            if con:
                R.record(con, f, o, created_by="expand-pairwise", commit=False)
        changes = {}
        for vid in f.variants:
            n_changed, blocked, added = 0, 0, {}
            for sid, o in base_out.items():
                v = R.evaluate(f, {k: o["inputs"][k]["value"] for k in o["inputs"]}, vid)
                if con:
                    R.record(con, f, v, created_by="expand-pairwise", commit=False)
                a_ids = {r["id"] for r in v["requirements"] if r["status"] in COUNTED}
                b_ids = {r["id"] for r in o["requirements"] if r["status"] in COUNTED}
                if a_ids != b_ids or v["blocked"] != o["blocked"]:
                    n_changed += 1
                    blocked += int(v["blocked"] and not o["blocked"])
                    for x in a_ids - b_ids:
                        added[x] = added.get(x, 0) + 1
            changes[vid] = {"scenarios": len(base_out), "changed": n_changed, "newly_blocked": blocked,
                            "requirements_added": added}
        if con:
            con.commit()
    finally:
        if con:
            con.close()
    log(json.dumps({"family": f.id, "pairwise_scenarios": len(tests), "runs": len(tests) * (1 + len(f.variants)),
                    "stored": bool(save), "variants": changes, "seconds": round(time.time() - t0, 2)}, indent=1))
    return 0


def cmd_sens(a) -> int:
    f = _fam(a.family)
    if a.persona:
        s = SE.for_persona(f, a.persona, a.locality or f.localities()[0], a.variant)
    else:
        s = SE.swings(f, _sets(a.set), a.variant)
    if a.json:
        print(json.dumps(s, indent=1, default=str))
    else:
        print(f"base {s['base']}: {s['base_counts']['to_do']} to do, fee floor ${s['base_fee_floor']:,.2f}, "
              f"about {s['base_days']} days")
        for r in s["ranking"]:
            print(f"  {r['score']:>6}  {r['dimension']:<10} requirements ±{r['swing_requirements']:<3} fees "
                  f"±${r['swing_fees']:,.2f}  days ±{r['swing_days']}{'  can block' if r['can_block'] else ''}")
    return 0


def cmd_ask(a) -> int:
    f = _fam(a.family)
    res = IN.intake(f, a.text, threshold=a.threshold, use_model=not a.no_model)
    print(json.dumps({k: v for k, v in res.items()}, indent=1, ensure_ascii=False, default=str))
    if res["ask"] and not a.defaults:
        print(f"{len(res['ask'])} questions to ask before a computed answer (or rerun with --defaults)", file=sys.stderr)
        return 0
    inputs, methods = IN.with_defaults(f, res) if res["ask"] else (res["inputs"], res["methods"])
    try:
        out = R.evaluate(f, inputs)
    except FamilyError as e:
        print(f"cannot evaluate: {e}", file=sys.stderr)
        return 1
    _print(out, a.json)
    if a.save:
        con = db.connect()
        try:
            rid = R.record(con, f, out, created_by="intake", local_only=True, method=methods)
        finally:
            con.close()
        print(f"stored run {rid} (local only)", file=sys.stderr)
    return 0


def report(f: Family, variants: bool = True) -> dict:
    """Every persona in every locality (requirements, known fees, order), with its sensitivity, and the variants'
    effect on the same persona."""
    out = {"family": f.id, "version": f.version, "hash": f.content_hash(), "personas": {}}
    for pid, p in f.personas.items():
        per = {"label": p.get("label"), "localities": {}}
        for loc in f.localities():
            o = R.evaluate(f, f.persona_inputs(pid, loc))
            s = SE.for_persona(f, pid, loc)
            v = {vid: R.evaluate(f, f.persona_inputs(pid, loc), vid) for vid in f.variants} if variants else {}
            per["localities"][loc] = {
                "scenario": o["scenario"], "blocked": o["blocked"], "counts": o["counts"],
                "requirements": [{"order": r["order"], "id": r["id"], "status": r["status"], "title": r["title"],
                                  "office": r["office"]["label"], "fee": r["fee"]["text"]}
                                 for r in o["requirements"] if r["status"] in COUNTED or r["status"] == "blocked"],
                "fees": {k: o["fees"][k] for k in ("summary", "known_required_usd", "known_possible_usd",
                                                    "minimum_usd")},
                "unknown_fees": [u["title"] for u in o["fees"]["unknown"]],
                "order": [s_["id"] for s_ in o["order"]["steps"]], "timeline_days": o["order"]["timeline_days"],
                "top_drivers": SE.top(s), "ranking": s["ranking"],
                "variants": {vid: {"scenario": x["scenario"], "blocked": x["blocked"],
                                   "added": sorted({r["id"] for r in x["requirements"] if r["status"] in COUNTED}
                                                   - {r["id"] for r in o["requirements"] if r["status"] in COUNTED}),
                                   "removed": sorted({r["id"] for r in o["requirements"] if r["status"] in COUNTED}
                                                     - {r["id"] for r in x["requirements"] if r["status"] in COUNTED})}
                             for vid, x in v.items()}}
        out["personas"][pid] = per
    return out


def cmd_report(a) -> int:
    f = _fam(a.family)
    rep = report(f)
    text = json.dumps(rep, indent=1, ensure_ascii=False, default=str)
    if a.out:
        from pathlib import Path
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="lexflow hypo", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("family")
    p.add_argument("family", nargs="?")
    p.add_argument("--save", action="store_true", help="put the family, personas and assumptions in the database")
    p.set_defaults(fn=cmd_family)
    p = sub.add_parser("expand")
    p.add_argument("family", nargs="?", default=DEFAULT)
    p.add_argument("--by-district", action="store_true", help="pairwise over every district, not one per class")
    p.set_defaults(fn=cmd_expand)
    p = sub.add_parser("run")
    p.add_argument("family", nargs="?", default=DEFAULT)
    p.add_argument("scenario", nargs="?", help="a scenario id in the family's grammar")
    p.add_argument("--persona")
    p.add_argument("--locality")
    p.add_argument("--set", action="append", metavar="DIM=VALUE")
    p.add_argument("--variant")
    p.add_argument("--pairwise", action="store_true", help="run every pairwise scenario (baseline and variants)")
    p.add_argument("--save", action="store_true", help="store the scenario(s) and run(s)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("sens")
    p.add_argument("family", nargs="?", default=DEFAULT)
    p.add_argument("--persona")
    p.add_argument("--locality")
    p.add_argument("--set", action="append", metavar="DIM=VALUE")
    p.add_argument("--variant")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_sens)
    p = sub.add_parser("ask")
    p.add_argument("family", nargs="?", default=DEFAULT)
    p.add_argument("text")
    p.add_argument("--threshold", type=float, default=IN.THRESHOLD)
    p.add_argument("--no-model", action="store_true", help="patterns and questions only")
    p.add_argument("--defaults", action="store_true", help="fill what is left with the family defaults (tagged ASM)")
    p.add_argument("--save", action="store_true", help="store the scenario (local only) and its run")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_ask)
    p = sub.add_parser("report")
    p.add_argument("family", nargs="?", default=DEFAULT)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    try:
        return a.fn(a)
    except FamilyError as e:
        print(f"hypo: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
