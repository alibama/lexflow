"""Score lexflow.law.terms: defined-term extraction against the gold sets and on held-out sections, and the
Wikidata link classifier leaving one term out.  Read-only: it writes nothing unless --out is given.

    python scripts/terms_eval.py                       gold definitions and links (definitions need the index)
    python scripts/terms_eval.py --part terms -v       definitions only, with every miss and extra listed
    python scripts/terms_eval.py --part heldout -v     the 54 held-out sections of docs/design/verify-terms.md
    python scripts/terms_eval.py --part heldout --sample 12 -v   a fresh sample of definitions sections, unlabelled
    python scripts/terms_eval.py --part link           the classifier only (needs only the survey fixture)
    python scripts/terms_eval.py --part link --nested  also the nested threshold estimates (about a minute)
    python scripts/terms_eval.py --part link --embed   also the variant with nomic-embed-text similarity
    python scripts/terms_eval.py --print-model         the LINK_MODEL literal for lexflow/law/terms.py

Held-out.  The verifier drew 54 definitions sections that no gold set contains (seed 11, six per state from a
'title:definitions' search; Illinois headings never say "definitions", so it has none).  HELD_OUT lists them with
the terms each defines and the unit those terms govern, as read by hand from the text by the person who then
changed the extractor, so after that change they are a development set, not a blind test: --sample draws a fresh,
unlabelled sample for reading.  A held-out term's scope is right when its unit equals the one read from the text;
a list of sections ("As used in RCW 39.23.005 and 39.23.020") is right only as no unit at all.

Definitions.  Gold: the 'terms' arrays of fixtures/xref/gold_{a,b,c}.json, each in its own convention, keeping
the terms each gold says the section defines itself (A: how not in used / used_defined_elsewhere /
quoted_mention; B: definition_type != used; C: defined_here).  A term is matched per section by its normalised
form (lexflow.law.terms.norm_term: case, quotes and plural folded).  Term + scope also needs the scope: the
gold's scope words are turned into an index path with the same scope_path() (and checked against gold C's own
scope_unit paths), and compared with the predicted unit and pinpoint.  A gold term with no scope (heading terms
in gold A), or a scope the index path cannot express ('this part' in D.C.), is matched on the term alone.

Links.  The survey fixtures/xref/wikidata_terms.json: 714 (term, candidate) pairs of the 150 terms that have
candidates, 111 judged 'exact'.  Each term's candidates are scored by a model fitted on the other 149 terms (the
L2 weight is chosen by that out-of-fold log loss).  A term suggests its best candidate when that candidate clears
a threshold.  The shipped threshold, lexflow.law.terms.REVIEW_THRESHOLD, is 0.5, the model's even-odds point,
a convention rather than a value searched for on these scores, so its out-of-fold precision needs no nested
correction for threshold selection.  It only fills a review queue; nothing is written as a match until a person
accepts it.  The thresholds for precision
targets (0.95, 0.90, 0.85) are listed as diagnostics, each with a 95% Clopper-Pearson lower bound and the term
just below it, whose label places it: the 0.90 one (0.7607) sits just above the PropBank "incorporator", which is
why it is not the review threshold.  Errors are split into neighbouring concepts (broader / narrower / related)
and different things, using REJUDGED where a second reading of a survey pair disagreed with its label.  --nested
reports the target thresholds chosen inside each training fold instead.  The survey's rule baseline (label or
alias match, no junk, no foreign or other-state tag) is re-run on the same features.  Leave-one-term-out
measures fitting, not feature design: the cue lists were written while reading the survey.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow.law import terms as T  # noqa: E402

GOLD = ROOT / "fixtures" / "xref"
PRECISION = 0.95                # a diagnostic target only
REVIEW_PRECISION = 0.90         # a diagnostic target only (it once placed the review threshold; see eval_link)
# Survey pairs whose label a second reading disputes (docs/design/verify-terms.md, finding 3).  Training labels
# are exact / not exact, so this changes only how the errors are split, not the model.
REJUDGED = {
    ("custodian of records", "Q5196342"): "wrong",   # the 18 U.S.C. § 2257 records keeper: a specific statute's role
    ("restitution", "Q1156800"): "wrong?",           # the civil gains-based remedy, not criminal victim restitution
}

SECTIONS = "sections"           # HELD_OUT: the scope is a list of sections, which no unit expresses
# The verifier's 54 held-out sections: (state, citation, the unit their terms govern, the terms they define), read
# by hand from the text.  Units the index path lacks are written the way resolve_scope() anchors them.
_MD_UCC_TERMS = (
    "action|aggrieved party|agreement|bank|bearer|bill of lading|branch|burden of establishing|buyer in ordinary "
    "course of business|conspicuous|consumer|contract|creditor|defendant|delivery|document of title|fault|fungible "
    "goods|genuine|good faith|holder|insolvency proceeding|insolvent|money|organization|party|person|present value|"
    "purchase|purchaser|record|remedy|representative|right|security interest|send|signed|state|surety|term|"
    "unauthorized signature|warehouse receipt|writing")
HELD_OUT = [
    ("fl", "Fla. Stat. § 585.001", "Florida Code / Title XXXV / Chapter 585", "department"),
    ("fl", "Fla. Stat. § 499.61", "Florida Code / Title XXXIII / Chapter 499 / Part II",
     "dealer|department|distributor|ether|manufacturer|purchaser"),
    # "As used herein": the section, the convention of gold C (N.C. Gen. Stat. § 132-1)
    ("fl", "Fla. Stat. § 945.01", "Florida Code / Title XLVII / Chapter 945 / Section 945.01",
     "correctional system|department|secretary|reception center"),
    ("fl", "Fla. Stat. § 218.60", "Florida Code / Title XIV / Chapter 218 / Part VI", "population|utility tax relief"),
    ("fl", "Fla. Stat. § 606.03", "Florida Code / Title XXXVI / Chapter 606 / Act containing § 606.03",
     "business entity|department|master business index|participating agency|single business identifier|"
     "state agency|uniform business report"),
    ("fl", "Fla. Stat. § 627.652", "Florida Code / Title XXXVII / Chapter 627 / Part VII",
     "group health insurance|policy|insurance policy|health insurance policy|group health policy|"
     "group health insurance policy|amount of insurance|insurance|insurer"),
    ("va", "Va. Code Ann. § 10.1-1197.1", "Virginia Code / Title 10.1 / Subtitle II / Chapter 11.1 / Article 4",
     "fund|small business|small business concern|voluntary pollution prevention measures"),
    ("va", "Va. Code Ann. § 15.2-2414", "Virginia Code / Title 15.2 / Subtitle II / Chapter 24.1",
     "board|department|fund|local government|locality"),
    ("va", "Va. Code Ann. § 57-35.35:1", "Virginia Code / Title 57 / Chapter 3 / Article 4",
     "previously unidentified cemetery"),
    ("va", "Va. Code Ann. § 6.2-2100", "Virginia Code / Title 6.2 / Subtitle III / Chapter 21",
     "check casher|item|registrant|registration"),
    ("va", "Va. Code Ann. § 3.2-2900", "Virginia Code / Title 3.2 / Subtitle II / Part C / Chapter 29", "farmers"),
    ("va", "Va. Code Ann. § 2.2-4600", None, ""),
    ("nc", "N.C. Gen. Stat. § 143B-1241", "North Carolina Code / Chapter 143B / Part containing § 143B-1241", "veteran"),
    ("nc", "N.C. Gen. Stat. § 160D-1202", "North Carolina Code / Chapter 160D / Article containing § 160D-1202",
     "owner|parties in interest|public authority|public officer"),
    ("nc", "N.C. Gen. Stat. § 95-240", "North Carolina Code / Chapter 95 / Article containing § 95-240",
     "person|retaliatory action"),
    ("nc", "N.C. Gen. Stat. § 106-966", "North Carolina Code / Chapter 106 / Article containing § 106-966",
     "certified prescribed burner|prescribed burning|prescription"),
    ("nc", "N.C. Gen. Stat. § 120-36.11", None, ""),
    ("nc", "N.C. Gen. Stat. § 14-58.1", "North Carolina Code / Chapter 14 / Article containing § 14-58.1",
     "house|building"),
    ("dc", "D.C. Code § 47-3151", "DC Code / Title 47 / Chapter 31A", "drawer|sale|service"),
    ("dc", "D.C. Code § 28A-202", "DC Code / Title 28A / Chapter 2", "clearly and conspicuously|consumer"),
    ("dc", "D.C. Code § 3-1101", "DC Code / Title 3 / Chapter 11", "commission|committee|council|mayor"),
    ("dc", "D.C. Code § 8-1841.01", "DC Code / Title 8 / Chapter 18 / Subchapter containing § 8-1841.01",
     "commercial guard dog"),
    ("dc", "D.C. Code § 2-1561", "DC Code / Title 2 / Chapter 15 / Subchapter containing § 2-1561",
     "youth|youth council"),
    ("dc", "D.C. Code § 16-4603.01", "DC Code / Title 16 / Chapter 46 / Subchapter containing § 16-4603.01",
     "petitioner|respondent"),
    ("wa", "RCW 43.150.030", "Washington Code / Title 43 / Chapter 150", "volunteer|center"),
    ("wa", "RCW 39.23.010", SECTIONS,
     "sheltered workshops|programs of the department of social and health services|municipality"),
    ("wa", "RCW 13.34.802", None, ""),
    # "when the terms ... are used in this chapter, the terms do not include steam": not extracted
    ("wa", "RCW 82.04.216", "Washington Code / Title 82 / Chapter 04",
     "tangible personal property|ingredient|component part|incorporated into|goods|products|by-products|"
     "materials|consumables"),
    ("wa", "RCW 44.68.010", "Washington Code / Title 44 / Chapter 68", "administrative committee|center|coordinator"),
    ("wa", "RCW 68.05.010", None, ""),
    ("tx", "Tex. Education Code § 21.032", "TX Code / Code ed / Chapter 21 / Subchapter containing § 21.032", "board"),
    ("tx", "Tex. Insurance Code § 705.001", "TX Code / Code in / Chapter 705 / Subchapter containing § 705.001",
     "insurance policy"),
    ("tx", "Tex. Government Code § 482.601", "TX Code / Code gv / Chapter 482 / Subchapter containing § 482.601",
     "executive committee"),
    ("tx", "Tex. Health and Safety Code § 711.053", "TX Code / Code hs / Chapter 711 / Subchapter containing § 711.053",
     "commissioner"),
    ("tx", "Tex. Transportation Code § 453.301", "TX Code / Code tn / Chapter 453 / Subchapter containing § 453.301",
     "bond"),
    ("tx", "Tex. Special District Local Laws Code § 8197.001", "TX Code / Code sd / Chapter 8197", "district"),
    ("md", "Md. Code, Insurance § 5-509", None, ""),
    ("md", "Md. Code, Commercial Law § 22-305", None, ""),
    ("md", "Md. Code, Health - General § 21-238", None, ""),
    ("md", "Md. Code, Commercial Law § 2-311", None, ""),
    ("md", "Md. Code, Correctional Services § 8-601", None, ""),
    ("md", "Md. Code, Commercial Law § 1-201", "MD Code / Article gcl / Titles 1-10", _MD_UCC_TERMS),
    ("ca", "Cal. FAM § 8500", None, ""),
    ("ca", "Cal. FAC § 38911", None, ""),
    ("ca", "Cal. WAT § 23177", None, ""),
    ("ca", "Cal. FAC § 24951", None, ""),
    ("ca", "Cal. FAC § 14921", None, ""),
    ("ca", "Cal. WAT § 20511", None, ""),
    # "For the purposes of this chapter, a small business shall be deemed to be one which ...": not extracted
    ("ny", "N.Y. COM Law § 131", "New York Code / Act COM", "small business"),
    ("ny", "N.Y. PEN Law § 496.01", "New York Code / Act PEN / Part 4 / Title Y-2 / Article 496", "scheme"),
    ("ny", "N.Y. ENV Law § 41-0101", "New York Code / Act ENV / Article 41 / Section 41-0101",
     "sixth park region|adirondack park|catskill park"),
    ("ny", "N.Y. REL Law § 2", "New York Code / Act REL", "cooperative|person|rural areas"),
    # "For purposes of this article": the article, as the text says (it sits in Title 11 of that article)
    ("ny", "N.Y. ENV Law § 19-1101", "New York Code / Act ENV / Article 19",
     "motor vehicle|motor vehicle global warming gases|global warming gases"),
    ("ny", "N.Y. GOB Law § 13-109", SECTIONS, "transfer"),
]


# ------------------------------------------------------------------ definitions
def gold_terms(name: str, s: dict) -> list[dict]:
    out = []
    for t in s["terms"]:
        if name == "a":
            if t["how"] in ("used_defined_elsewhere", "used", "quoted_mention"):
                continue
            span = (t["start"], t["end"]) if t.get("definition") else None
            heading, by_ref = t["how"] == "heading", t["how"] in ("as_defined_in", "meaning_assigned")
            how, unit = t["how"], None
        elif name == "b":
            if t["definition_type"] == "used":
                continue
            span = ((t["definition_start"], t["definition_start"] + len(t["definition"]))
                    if t.get("definition") and t.get("definition_start") is not None else None)
            heading, by_ref = False, t["definition_type"] == "by_reference"
            how, unit = t["definition_type"], None
        else:
            if not t["defined_here"]:
                continue
            span = (t["def_start"], t["def_end"]) if t.get("def_start") is not None else None
            heading, by_ref = t["source"] == "heading", t["source"] == "incorporated_by_reference"
            how, unit = t["source"], t.get("scope_unit")
        out.append({"term": t["term"], "norm": T.norm_term(t["term"]), "scope": t.get("scope"), "unit": unit,
                    "span": span, "heading": heading, "by_ref": by_ref, "how": how, "kind": t.get("kind")})
    return out


def _pin(p: str | None) -> str | None:
    return p.strip("().").lower() if p else None


def gold_scope(row: dict, g: dict) -> tuple | None:
    """(path, pinpoint) of the gold scope, or None when it is not to be checked."""
    if not g["scope"]:
        return None
    path, pin = T.scope_path(row, g["scope"])
    unit = g.get("unit")
    if unit and " / " in unit:
        path = unit
    elif unit:                                       # gold C writes sub-section scopes as 'RCW 42.56.080(3)'
        m = re.search(r"(\([\w\-]+\))\s*$", unit)
        path, pin = row.get("path"), (m.group(1) if m else None)
    if path is None:
        return None
    return path, _pin(pin) or ("?" if g["scope"] and "subsection" in g["scope"].lower() and not pin else None)


def scope_ok(gold: tuple | None, pred: tuple) -> bool:
    if gold is None:
        return True
    if gold[0] != pred[0]:
        return False
    if gold[1] == "?":
        return pred[1] is not None
    return gold[1] == pred[1]


def load_rows(args) -> dict:
    if args.rows:
        return json.loads(Path(args.rows).read_text(encoding="utf-8"))
    from lexflow.ask import index as I
    rows = {}
    for name in "abc":
        for s in json.loads((GOLD / f"gold_{name}.json").read_text(encoding="utf-8"))["sections"]:
            rows[f"{s['state']}:{s['id']}"] = I.by_id(s["state"], s["id"], with_text=True)
    return rows


def eval_terms(args) -> dict:
    rows = load_rows(args)
    tally = defaultdict(Counter)            # (gold, variant) -> tp / pred / gold / tp_scope
    by_kind = defaultdict(Counter)          # predicted kind -> pred / tp
    gold_how = defaultdict(Counter)         # gold convention -> gold / found
    ious, cat = [], Counter()
    unit_check = Counter()
    misses, extras = [], []
    for name in "abc":
        for s in json.loads((GOLD / f"gold_{name}.json").read_text(encoding="utf-8"))["sections"]:
            row = rows[f"{s['state']}:{s['id']}"]
            preds = T.definitions(s["state"], row, row.get("text"))
            gold = gold_terms(name, s)
            for g in gold:
                if g["unit"] and " / " in g["unit"]:
                    unit_check[T.scope_path(row, g["scope"])[0] == g["unit"]] += 1
            for variant in ("all", "no_by_reference"):
                gs = [g for g in gold if variant == "all" or not g["by_ref"]]
                ps = [p for p in preds if variant == "all" or p.kind != "by_reference"]
                gnorm = defaultdict(list)
                for g in gs:
                    gnorm[g["norm"]].append(g)
                pnorm = defaultdict(list)
                for p in ps:
                    pnorm[T.norm_term(p.term)].append(p)
                c = tally[(name, variant)]
                c["gold"] += len(gnorm)
                c["pred"] += len(pnorm)
                for n, plist in pnorm.items():
                    if n in gnorm:
                        c["tp"] += 1
                        gscopes = [gold_scope(row, g) for g in gnorm[n]]
                        if any(scope_ok(gsc, (p.scope_unit, _pin(p.scope_pinpoint))) for gsc in gscopes for p in plist):
                            c["tp_scope"] += 1
                        elif variant == "all" and args.verbose:
                            misses.append(f"  scope {name} {s['citation']}: {plist[0].term!r} gold "
                                          f"{gnorm[n][0]['scope']!r} -> {gscopes[0]} | pred {plist[0].scope!r} -> "
                                          f"{(plist[0].scope_unit, plist[0].scope_pinpoint)}")
                    elif variant == "all":
                        extras.append(f"  extra {name} {s['citation']}: {plist[0].kind} {plist[0].term!r}")
                if variant != "all":
                    continue
                for n, glist in gnorm.items():
                    g = glist[0]
                    hit = n in pnorm
                    gold_how[(name, g["how"])]["gold"] += 1
                    gold_how[(name, g["how"])]["found"] += hit
                    if not hit:
                        misses.append(f"  miss  {name} {s['citation']}: {g['how']} {g['term']!r}")
                        continue
                    p = pnorm[n][0]
                    if g["span"] and p.start is not None:
                        a, b = g["span"], (p.start, p.end)
                        inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
                        ious.append(inter / max(1, max(a[1], b[1]) - min(a[0], b[0])))
                    if g.get("kind"):
                        want = {"role/actor": "role", "document": "document"}.get(g["kind"], "other")
                        cat[want == p.category] += 1
                for n, plist in pnorm.items():
                    for p in plist[:1]:
                        by_kind[p.kind]["pred"] += 1
                        by_kind[p.kind]["tp"] += n in gnorm

    def prf(c):
        p = c["tp"] / c["pred"] if c["pred"] else 0.0
        r = c["tp"] / c["gold"] if c["gold"] else 0.0
        ps = c["tp_scope"] / c["pred"] if c["pred"] else 0.0
        rs = c["tp_scope"] / c["gold"] if c["gold"] else 0.0
        return {"gold": c["gold"], "pred": c["pred"], "tp": c["tp"], "precision": round(p, 3), "recall": round(r, 3),
                "tp_scope": c["tp_scope"], "precision_scope": round(ps, 3), "recall_scope": round(rs, 3)}

    report = {}
    for variant in ("all", "no_by_reference"):
        tot = Counter()
        for name in "abc":
            tot.update(tally[(name, variant)])
            report[f"{name}/{variant}"] = prf(tally[(name, variant)])
        report[f"total/{variant}"] = prf(tot)
    report["predicted_kinds"] = {k: dict(v) for k, v in sorted(by_kind.items())}
    report["gold_recall_by_convention"] = {f"{n}:{h}": f"{c['found']}/{c['gold']}"
                                           for (n, h), c in sorted(gold_how.items())}
    report["span_iou_mean"] = round(sum(ious) / len(ious), 3) if ious else None
    report["category_accuracy"] = f"{cat[True]}/{cat[True] + cat[False]}"
    report["scope_path_vs_gold_c_units"] = f"{unit_check[True]}/{unit_check[True] + unit_check[False]} equal"

    print("\nDEFINITIONS (term = section + normalised term; scope = also the governed unit)")
    print(f"{'set':24s} {'gold':>5s} {'pred':>5s} {'tp':>4s} {'P':>6s} {'R':>6s} {'P+scope':>8s} {'R+scope':>8s}")
    for k, v in report.items():
        if "/" in k:
            print(f"{k:24s} {v['gold']:5d} {v['pred']:5d} {v['tp']:4d} {v['precision']:6.3f} {v['recall']:6.3f} "
                  f"{v['precision_scope']:8.3f} {v['recall_scope']:8.3f}")
    print("predicted kinds (pred / matched a gold term):",
          ", ".join(f"{k} {v['tp']}/{v['pred']}" for k, v in report["predicted_kinds"].items()))
    print("gold recall by convention:", ", ".join(f"{k} {v}" for k, v in report["gold_recall_by_convention"].items()))
    print(f"span IoU on matched terms with gold spans: {report['span_iou_mean']}; category (role/document/other) "
          f"right: {report['category_accuracy']}; scope_path vs gold C scope_unit: "
          f"{report['scope_path_vs_gold_c_units']}")
    if args.verbose:
        print("\n".join(misses + extras))
    return report


# ------------------------------------------------------------------ held-out definitions
def _section_ids() -> set[tuple[str, int]]:
    ids = set()
    for name in "abc":
        for s in json.loads((GOLD / f"gold_{name}.json").read_text(encoding="utf-8"))["sections"]:
            ids.add((s["state"], s["id"]))
    return ids


def held_out_rows() -> list[tuple]:
    """HELD_OUT with each section's index row (with text) and its expected terms normalised."""
    from lexflow.ask import index as I
    out = []
    for st, cit, unit, words in HELD_OUT:
        rows = I.lookup(st, cit, with_text=True)
        out.append((st, cit, rows[0] if rows else None, unit, {T.norm_term(w) for w in words.split("|") if w}))
    return out


def fresh_sample(seed: int, per: int = 6) -> list[tuple]:
    """The verifier's procedure with another seed, leaving out gold and HELD_OUT sections."""
    from lexflow.ask import index as I
    skip = _section_ids()
    held = {(st, cit) for st, cit, _, _ in HELD_OUT}
    rng = random.Random(seed)
    out = []
    for st in ["fl", "va", "nc", "dc", "wa", "tx", "md", "ca", "ny", "il"]:
        hits = [h for h in I.search(st, "title:definitions", limit=200)
                if (st, h["id"]) not in skip and (st, h["citation"]) not in held]
        rng.shuffle(hits)
        for h in hits[:per]:
            out.append((st, h["citation"], I.by_id(st, h["id"], with_text=True), None, None))
    return out


def _scope_right(t, unit) -> bool:
    if unit == SECTIONS:
        return t.scope_unit is None and bool(re.match(r"(?i)(?:sections?|§|RCW|ss?\.)\s*\d", t.scope or ""))
    return unit is not None and t.scope_unit == unit


def eval_heldout(args) -> dict:
    labelled = args.sample is None
    rows = held_out_rows() if labelled else fresh_sample(args.sample)
    c, basis, lines = Counter(), Counter(), []
    for st, cit, row, unit, want in rows:
        if row is None:
            c["not_in_index"] += 1
            continue
        c["sections"] += 1
        ts = T.definitions(st, row, row.get("text"))
        got = {T.norm_term(t.term) for t in ts}
        c["term_rows"] += len(ts)
        c["sections_with_terms"] += bool(ts)
        c["distinct_terms"] += len(got)
        for t in ts:
            basis[getattr(t, "scope_basis", None) or ("none" if t.scope_unit is None else "?")] += 1
        if labelled:
            c["expected_terms"] += len(want)
            c["tp"] += len(got & want)
            right = [t for t in ts if _scope_right(t, unit)]
            c["scope_right_rows"] += len(right)
            # right only by the labelling convention: an anchored unit (named, not bounded) or no unit at all
            c["scope_right_anchored"] += sum(1 for t in right if t.scope_basis == "anchored")
            c["scope_right_no_unit"] += sum(1 for t in right if t.scope_unit is None)
            c["scope_right_matched"] += len({T.norm_term(t.term) for t in right} & want)
            c["sections_all_scopes_right"] += bool(ts) and len(right) == len(ts)
        if args.verbose:
            lines.append(f"\n{st} {cit} | {row.get('path')}" + (f"\n   want unit {unit!r}; want terms "
                                                                    f"{sorted(want)}" if labelled else ""))
            for t in ts:
                mark = ("ok " if _scope_right(t, unit) else "BAD") if labelled else "   "
                lines.append(f"   {mark} {t.term!r} {t.kind} | {t.scope!r} -> {t.scope_unit} "
                             f"[{getattr(t, 'scope_basis', None)}]" + ("" if not labelled or T.norm_term(t.term) in want
                                                                       else "  (not an expected term)"))
            if labelled:
                for w in sorted(want - got):
                    lines.append(f"   miss {w!r}")
    report = dict(c, scope_basis=dict(basis))
    if labelled:
        report["term_precision"] = round(c["tp"] / c["distinct_terms"], 3) if c["distinct_terms"] else None
        report["term_recall"] = round(c["tp"] / c["expected_terms"], 3) if c["expected_terms"] else None
    print(f"\nHELD-OUT DEFINITIONS ({'the verifier' + chr(39) + 's 54 sections, labelled by hand' if labelled else f'fresh sample, seed {args.sample}, unlabelled'})")
    print("  " + json.dumps(report))
    if labelled:
        print(f"  terms: {c['tp']} of {c['expected_terms']} expected found, {c['distinct_terms']} predicted "
              f"(P {report['term_precision']}, R {report['term_recall']}); scope right on {c['scope_right_rows']} of "
              f"{c['term_rows']} predicted term rows ({c['scope_right_anchored']} of them anchored units and "
              f"{c['scope_right_no_unit']} with no unit, right only by the labelling convention); sections with "
              f"every scope right: {c['sections_all_scopes_right']} of {c['sections_with_terms']} with terms")
    if args.verbose:
        print("\n".join(lines))
    return report


# ------------------------------------------------------------------ links
class PrivateEmbedder:
    """The selector's Embedder (prefix 'classification') with its own cache file: the shared cache under
    data/cache is large and written by running jobs, so it is neither loaded nor appended to here."""

    def __new__(cls, path: Path):
        from lexflow import config
        from lexflow.extract.selector import Embedder

        class _E(Embedder):
            def __init__(self, p):
                self.model = config.EMBED_MODEL
                self.name = self.model
                self.base_url = config.OLLAMA_URL.rstrip("/")
                self.path = Path(p)
                self.cache = {}
                if self.path.exists():
                    for line in self.path.read_text(encoding="utf-8").splitlines():
                        try:
                            k, v = json.loads(line)
                            self.cache[k] = v
                        except ValueError:
                            continue
        return _E(path)


def embedding_rows(pairs: list[dict], path: Path) -> list[float | None] | None:
    import requests
    emb = PrivateEmbedder(path)
    try:
        requests.get(emb.base_url + "/api/tags", timeout=5).raise_for_status()
    except requests.RequestException as e:
        print(f"embedding server not reachable ({type(e).__name__}); skipping the embedding variant")
        return None
    by_term = defaultdict(list)
    for i, p in enumerate(pairs):
        by_term[p["term"]].append(i)
    sims: list[float | None] = [0.0] * len(pairs)
    texts = 0
    for term, idx in by_term.items():
        cands = [pairs[i]["cand"] for i in idx]
        want = [c for c in cands if T._matches(term, c)]
        texts += 1 + len(want) if want else 0
        # the survey's 'source' quotes the headings and curated names the term came from
        context = "; ".join(re.findall(r"'([^']{3,90})'", pairs[idx[0]].get("source") or "")[:3]) or None
        for i, s in zip(idx, T.embedding_sims(term, cands, emb, context)):
            sims[i] = s
    print(f"embedded {texts} short texts (cache {path})")
    return sims


def _groups(pairs):
    g = defaultdict(list)
    for i, p in enumerate(pairs):
        g[p["term"]].append(i)
    return g


def oof(pairs, feats, features, l2, terms=None):
    """Out-of-fold probabilities, one fold per term (or per group of terms when ``terms`` maps term -> fold)."""
    import numpy as np
    X = np.array([[f.get(k, 0.0) for k in features] for f in feats], dtype=float)
    y = np.array([p["y"] for p in pairs], dtype=float)
    groups = _groups(pairs)
    folds = defaultdict(list)
    for t, idx in groups.items():
        folds[terms[t] if terms else t].extend(idx)
    out = np.zeros(len(pairs))
    for idx in folds.values():
        mask = np.ones(len(pairs), bool)
        mask[idx] = False
        beta, mu, sd = T.fit_lr(X[mask], y[mask], l2=l2)
        Z = np.hstack([(X[idx] - mu) / sd, np.ones((len(idx), 1))])
        out[idx] = 1 / (1 + np.exp(-np.clip(Z @ beta, -30, 30)))
    return out


def cp_lower(k: int, n: int, alpha: float = 0.05) -> float | None:
    """The Clopper-Pearson lower bound of a binomial proportion k/n (two-sided 1 - alpha): the p at which
    P(X >= k | n, p) = alpha / 2, found by bisection."""
    if not n:
        return None
    if k == 0:
        return 0.0

    def tail(p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))

    lo, hi = 0.0, k / n
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if tail(mid) < alpha / 2 else (lo, mid)
    return round(lo, 3)


def term_table(pairs, p):
    """Per term: (best candidate's p, its judgement (REJUDGED first), has an exact candidate, its qid)."""
    out = {}
    for t, idx in _groups(pairs).items():
        i = max(idx, key=lambda k: p[k])
        judgement = REJUDGED.get((t, pairs[i]["qid"]), pairs[i]["judgement"])
        out[t] = (float(p[i]), judgement, any(pairs[k]["y"] for k in idx), pairs[i]["qid"])
    return out


def term_metrics(tab, thr):
    linked = [(t, v) for t, v in tab.items() if v[0] >= thr]
    right = sum(1 for _, v in linked if v[1] == "exact")
    has = sum(1 for v in tab.values() if v[2])
    different = sum(1 for _, v in linked if v[1] == "wrong")
    maybe = sum(1 for _, v in linked if v[1] == "wrong?")
    return {"threshold": round(thr, 4), "linked": len(linked), "correct": right, "wrong": len(linked) - right,
            "different_thing": different, "possibly_different": maybe,
            "neighbour_concept": len(linked) - right - different - maybe,
            "precision": round(right / len(linked), 3) if linked else None,
            "precision_lower_95": cp_lower(right, len(linked)),
            "recall_of_terms_with_exact": round(right / has, 3) if has else None, "terms_with_exact": has,
            "wrong_links": sorted(f"{t} -> {v[3]} ({v[1]}, p {v[0]:.3f})" for t, v in linked if v[1] != "exact")}


def next_below(tab, thr) -> str | None:
    """The best-scoring term below ``thr``: the one whose label decides where a precision target's threshold
    falls."""
    below = sorted(((v[0], t, v[1]) for t, v in tab.items() if v[0] < thr), reverse=True)
    return f"{below[0][1]} (p {below[0][0]:.3f}, {below[0][2]})" if below else None


def term_threshold(tab, target=PRECISION):
    cands = sorted({v[0] for v in tab.values()}, reverse=True)
    best = None
    for thr in cands:
        m = term_metrics(tab, thr)
        if m["precision"] is not None and m["precision"] >= target:
            best = thr
    return best


def nested(pairs, feats, features, l2, inner_folds=10, seed=7, target=PRECISION):
    """Each held-out term is linked with a threshold chosen (for ``target`` precision) on inner folds of the other
    terms only."""
    import numpy as np
    groups = _groups(pairs)
    terms = sorted(groups)
    rng = random.Random(seed)
    decisions = {}
    X = np.array([[f.get(k, 0.0) for k in features] for f in feats], dtype=float)
    y = np.array([p["y"] for p in pairs], dtype=float)
    for t in terms:
        rest = [u for u in terms if u != t]
        shuffled = rest[:]
        rng.shuffle(shuffled)
        fold = {u: k % inner_folds for k, u in enumerate(shuffled)}
        sub = [i for u in rest for i in groups[u]]
        sub_pairs = [pairs[i] for i in sub]
        sub_feats = [feats[i] for i in sub]
        p_in = gate(sub_pairs, oof(sub_pairs, sub_feats, features, l2, terms=fold))
        thr = term_threshold(term_table(sub_pairs, p_in), target)
        thr = 1.01 if thr is None else thr
        beta, mu, sd = T.fit_lr(X[sub], y[sub], l2=l2)
        idx = groups[t]
        Z = np.hstack([(X[idx] - mu) / sd, np.ones((len(idx), 1))])
        pt = np.array(gate([pairs[i] for i in idx], 1 / (1 + np.exp(-np.clip(Z @ beta, -30, 30)))))
        j = int(np.argmax(pt))
        decisions[t] = (float(pt[j]) >= thr, pairs[idx[j]]["judgement"], any(pairs[i]["y"] for i in idx), thr)
    linked = [v for v in decisions.values() if v[0]]
    right = sum(1 for v in linked if v[1] == "exact")
    has = sum(1 for v in decisions.values() if v[2])
    thrs = sorted(v[3] for v in decisions.values())
    return {"target": target, "linked": len(linked), "correct": right,
            "precision": round(right / len(linked), 3) if linked else None,
            "precision_lower_95": cp_lower(right, len(linked)),
            "recall_of_terms_with_exact": round(right / has, 3), "threshold_median": round(thrs[len(thrs) // 2], 4)}


def gate(pairs, p):
    """terms.link() never links an item with neither a description nor a class: score those 0 here too."""
    return [0.0 if T.unlinkable(x["cand"]) else float(q) for x, q in zip(pairs, p)]


def auc(p, y):
    pos = [q for q, t in zip(p, y) if t]
    neg = [q for q, t in zip(p, y) if not t]
    wins = sum((a > b) + 0.5 * (a == b) for a in pos for b in neg)
    return round(wins / (len(pos) * len(neg)), 3)


def logloss(p, y):
    return -sum(math.log(max(1e-9, q if t else 1 - q)) for q, t in zip(p, y)) / len(y)


def rule_baseline(pairs: list[dict], feats: list[dict]) -> dict:
    """The survey's rule baseline, re-run on these features: label or alias match, no junk, no foreign or other
    state's tag; a term links its first accepted first-pass candidate.  A link to a different thing is counted by
    the survey's labels and, as ``different_thing``, with REJUDGED applied."""
    y = [p["y"] for p in pairs]
    rule = [bool(f["lm_exact"] or f["lm_alias"]) and not f["desc_junk"] and not f["desc_foreign"] and
            not f["jur_foreign"] and not f["desc_us_state"] for f in feats]
    tp = sum(1 for r, t in zip(rule, y) if r and t)
    fp = sum(1 for r, t in zip(rule, y) if r and not t)
    base = Counter()
    for t, idx in _groups(pairs).items():
        pick = next((i for i in idx if rule[i] and pairs[i]["cand"].get("pass") == "first"), None)
        if pick is None:
            continue
        rejudged = REJUDGED.get((t, pairs[pick]["qid"]), pairs[pick]["judgement"])
        base["linked"] += 1
        base["correct"] += pairs[pick]["y"] == 1
        base["different_thing_survey"] += pairs[pick]["judgement"] == "wrong"
        base["different_thing"] += rejudged == "wrong"
        base["possibly_different"] += rejudged == "wrong?"
    return {"pair_precision": round(tp / (tp + fp), 3), "pair_recall": round(tp / sum(y), 3), **base}


def eval_link(args) -> dict:
    pairs = T.survey_pairs()
    y = [p["y"] for p in pairs]
    feats = T.pair_features(pairs)
    report = {"pairs": len(pairs), "exact_pairs": sum(y), "terms": len(_groups(pairs))}
    print(f"\nLINKS: {report['terms']} terms, {report['pairs']} candidate pairs, {report['exact_pairs']} exact")

    report["rule_baseline"] = rule_baseline(pairs, feats)
    base_terms = report["rule_baseline"]
    print(f"rule baseline: pairs P={base_terms['pair_precision']} "
          f"R={base_terms['pair_recall']};"
          f" terms linked {base_terms['linked']}, correct {base_terms['correct']}, to a different thing "
          f"{base_terms['different_thing']} with REJUDGED ({base_terms['different_thing_survey']} by the survey's "
          f"labels), possibly different {base_terms['possibly_different']}")

    variants = {"base": T.FEATURES}
    if args.embed:
        sims = embedding_rows(pairs, Path(args.embed_cache))
        if sims is not None:
            for f, s in zip(feats, sims):
                f[T.EMB_FEATURE] = s
            variants["base+embedding"] = T.FEATURES + [T.EMB_FEATURE]
    chosen = {}
    for name, features in variants.items():
        losses = {l2: logloss(oof(pairs, feats, features, l2), y) for l2 in (0.3, 1.0, 3.0, 10.0)}
        l2 = min(losses, key=losses.get)
        p = gate(pairs, oof(pairs, feats, features, l2))
        tab = term_table(pairs, p)
        r = {"l2": l2, "loto_logloss": {str(k): round(v, 4) for k, v in losses.items()}, "pair_auc": auc(p, y),
             "review_queue": term_metrics(tab, T.REVIEW_THRESHOLD),
             "diagnostic_targets": {str(t): (dict(term_metrics(tab, th), next_below=next_below(tab, th))
                                             if (th := term_threshold(tab, t)) is not None else None)
                                    for t in (0.95, REVIEW_PRECISION, 0.85)}}
        if args.nested:
            r["nested"] = {str(t): nested(pairs, feats, features, l2, target=t) for t in (REVIEW_PRECISION, PRECISION)}
        report[name] = r
        chosen[name] = (features, l2)
        print(f"\n[{name}] l2={l2} (LOTO log loss {r['loto_logloss']}); pair AUC {r['pair_auc']}")
        m = r["review_queue"]
        print(f"  REVIEW QUEUE at the fixed review_threshold {T.REVIEW_THRESHOLD} (even odds; not searched for on "
              f"these scores): {m['linked']} suggested, {m['correct']} exact (P={m['precision']}, 95% lower bound "
              f"{m['precision_lower_95']}), recall {m['recall_of_terms_with_exact']} of {m['terms_with_exact']}; "
              f"errors: {m['neighbour_concept']} broader/narrower/related, {m['different_thing']} a different "
              f"thing, {m['possibly_different']} possibly a different thing")
        print("    not exact:", "; ".join(m["wrong_links"]))
        print("  diagnostics only (each threshold is picked on these out-of-fold scores, so the term just below "
              "it places it; none is an operating point):")
        for tgt, m in r["diagnostic_targets"].items():
            if m:
                print(f"    P>={tgt}: threshold {m['threshold']:.4f}, {m['linked']} suggested, {m['correct']} exact "
                      f"(P={m['precision']}, 95% lower bound {m['precision_lower_95']}), recall "
                      f"{m['recall_of_terms_with_exact']}; errors: {m['neighbour_concept']} neighbouring, "
                      f"{m['different_thing']} different, {m['possibly_different']} possibly different; next term "
                      f"below: {m['next_below']}")
        if args.nested:
            for tgt, v in r["nested"].items():
                print(f"  nested, threshold for P>={tgt} chosen inside each training fold: {v}")
        for t in ("incorporator", "organizer", "founder", "registered agent", "statutory agent", "custodian of records",
                  "restitution", "scofflaw", "articles of incorporation", "Office of Administrative Hearings",
                  "Administrative Procedure Act"):
            v = tab.get(t)
            if v:
                print(f"    {t!r}: best {v[3]} p={v[0]:.3f} ({v[1]})")
        props = [f"{q['term']} {q['qid']} p={float(x):.3f}" for q, x in zip(pairs, p)
                 if "for predicate" in (q["cand"].get("description") or "")]
        print("    PropBank pairs (no feature names PropBank):", "; ".join(props))

    features, l2 = chosen["base"]
    model = T.fit_link_model(feats, y, features=features, l2=l2, review_threshold=T.REVIEW_THRESHOLD,
                             trained_on="fixtures/xref/wikidata_terms.json: 150 terms with candidates, 714 pairs")
    names = sorted(zip(model["beta"][:-1], features), key=lambda x: -abs(x[0]))
    print("\nlargest standardised coefficients (base model on all pairs):",
          ", ".join(f"{f} {b:+.2f}" for b, f in names[:12]))
    full = dict(zip([q["term"] + " " + q["qid"] for q in pairs], gate(pairs, T.predict(model, feats))))
    print("shipped model (fitted on all pairs): incorporator Q140403634 p="
          f"{full.get('incorporator Q140403634', float('nan')):.3f}")
    report["model"] = model
    if args.print_model:
        print("\nLINK_MODEL = " + json.dumps(model, indent=None))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--part", choices=["terms", "heldout", "link", "all"], default="all")
    ap.add_argument("--sample", type=int, help="heldout: a fresh unlabelled sample with this seed")
    ap.add_argument("--rows", help="section rows with text as JSON {state:id: row} (instead of the index)")
    ap.add_argument("--embed", action="store_true", help="add the nomic-embed-text similarity variant")
    ap.add_argument("--embed-cache", default=str(Path(tempfile.gettempdir()) / "lexflow-terms-embed.jsonl"))
    ap.add_argument("--nested", action="store_true", help="also the nested threshold estimates (a minute or two)")
    ap.add_argument("--print-model", action="store_true")
    ap.add_argument("--out", help="write the report as JSON here")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    report = {}
    if args.part in ("terms", "all"):
        report["definitions"] = eval_terms(args)
    if args.part == "heldout":
        report["held_out"] = eval_heldout(args)
    if args.part in ("link", "all"):
        report["links"] = eval_link(args)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    main()
