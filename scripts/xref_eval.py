"""Score statute cross-reference resolvers against the hand-labelled gold (fixtures/xref/gold_{a,b,c}.json).

    python scripts/xref_eval.py [--resolver current|new|both] [--failures N] [--json PATH] [--only-state ca]
                                [--exclude CITATION ...]

Reads the live statute index read-only; run it where the index is (the app container):

    MSYS_NO_PATHCONV=1 docker exec -i lexflow-app-1 python scripts/xref_eval.py --resolver both

Resolvers
  current  lexflow.ask.retrieve.cited(state, row, limit=100): index rows, no spans, kinds or roles.  Its
           detection is measured with the XREF pattern cited() scans.
  new      lexflow.law.xref.references(state, row)

Gold targets.  A gold reference's target ids are the rows I.lookup(state, citation) returns with exactly that
citation, for each of its target_sections; only references that are resolvable_in_index and not generic count
for target recall (containers whose gold names only a unit, such as "this chapter", have no section targets).

Metrics, each over all 82 sections and again without the two user-example sections (Cal. BPC § 480 and Va. Code
§ 54.1-204):
  detection   share of gold references whose span overlaps a predicted span ('specific' leaves out generic law);
              'strict' matches gold and predicted references one to one by overlap (new resolver only), and
              'spurious' counts predicted references that overlap no gold reference.
  targets     micro precision / recall / F1 of target section ids, per citing section: the union of predicted ids
              against the union of gold ids.  'outward' drops the citing section's own id from both sides
              (cited() never returns it; "this section" and same-section pinpoints then drop out); 'all' keeps it.
  per state and per gold kind (recall of the kind's gold ids among the section's predicted ids; the new
              resolver's precision by its own predicted kind)
  role, kind, unit and pinpoint accuracy over the one-to-one matched pairs (new resolver)
  failures    missed gold references, wrong targets and spurious predictions, grouped, with examples

The resolver's rules were written while reading all three gold files, so every number here is in-sample.
``--exclude`` drops gold sections by citation, e.g. ``--exclude "N.Y. LLC Law § 1101"`` (a 27-item fee schedule
that alone holds 24 of the roles the fee-schedule rule decides) to see how much a number leans on one section.
The gold predates the ``session_law`` kind: it labels Maryland's "CHAPTER 95 OF 2025" named_act and Washington's
"5892.SL" other_code, so those two count as kind errors.
"""
from __future__ import annotations

import argparse
import collections
import functools
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow.ask import index as I  # noqa: E402

GOLD = [ROOT / "fixtures" / "xref" / f"gold_{x}.json" for x in "abc"]
USER_EXAMPLES = {("ca", "Cal. BPC § 480"), ("va", "Va. Code Ann. § 54.1-204")}
NO_TARGET_KINDS = {"generic", "federal", "constitution", "regulation", "court_rule", "session_law"}


# ------------------------------------------------------------------ gold
@functools.lru_cache(maxsize=None)
def lookup_ids(state: str, citation: str) -> tuple:
    rows = I.lookup(state, citation)
    exact = [r["id"] for r in rows if r["citation"] == citation]
    return tuple(exact or [r["id"] for r in rows])


def load_gold() -> list[dict]:
    secs = []
    for p in GOLD:
        d = json.loads(p.read_text(encoding="utf-8"))
        for s in d["sections"]:
            s["file"] = p.stem
            s["user_example"] = (s["state"], s["citation"]) in USER_EXAMPLES
            for r in s["references"]:
                r["is_generic"] = bool(r.get("generic")) or r["kind"] == "generic"
                ids = set()
                if r.get("resolvable_in_index") and not r["is_generic"]:
                    for c in r.get("target_sections") or []:
                        ids.update(lookup_ids(s["state"], c))
                r["ids"] = sorted(ids)
                r["unit_path"] = gold_unit(r.get("target_unit"))
            secs.append(s)
    return secs


def gold_unit(u) -> str | None:
    """The gold unit as an index path, when it is one (gold A: a dict with 'exact'; B and C: a path string)."""
    if isinstance(u, dict):
        return u.get("index_path") if u.get("exact") else None
    if isinstance(u, str) and " / " in u:
        return u
    return None


# ------------------------------------------------------------------ resolvers
def predict_current(state: str, row: dict, text: str) -> dict:
    from lexflow.ask import retrieve
    rows = retrieve.cited(state, row, limit=100)
    spans = [(m.start(), m.end()) for m in retrieve.XREF.finditer(text)]
    return {"ids": {r["id"] for r in rows}, "refs": [], "spans": spans}


def predict_new(state: str, row: dict, text: str) -> dict:
    from lexflow.law import xref
    refs = xref.references(state, row)
    ids = {i for r in refs for i in r.ids}
    return {"ids": ids, "refs": refs, "spans": [(r.start, r.end) for r in refs]}


RESOLVERS = {"current": predict_current, "new": predict_new}


# ------------------------------------------------------------------ scoring
def overlap(a, b) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def match(gold: list[dict], refs: list) -> dict[int, int]:
    """One-to-one gold -> predicted index, largest overlaps first."""
    pairs = sorted(((overlap((g["start"], g["end"]), (r.start, r.end)), gi, ri)
                    for gi, g in enumerate(gold) for ri, r in enumerate(refs)
                    if overlap((g["start"], g["end"]), (r.start, r.end)) > 0), reverse=True)
    used_g, used_r, out = set(), set(), {}
    for _, gi, ri in pairs:
        if gi not in used_g and ri not in used_r:
            out[gi] = ri
            used_g.add(gi)
            used_r.add(ri)
    return out


def norm_pin(p) -> tuple:
    return tuple(re.findall(r"[A-Za-z0-9]+(?:-\d+)?", p or ""))


def prf(tp: int, np_: int, ng: int) -> dict:
    p = tp / np_ if np_ else 0.0
    r = tp / ng if ng else 0.0
    return {"p": round(p, 3), "r": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "tp": tp, "pred": np_, "gold": ng}


class Acc:
    """Counts for one resolver over a set of sections."""

    def __init__(self):
        self.c = collections.Counter()
        self.state = collections.defaultdict(collections.Counter)
        self.kind = collections.defaultdict(collections.Counter)
        self.pkind = collections.defaultdict(collections.Counter)
        self.roles = collections.defaultdict(collections.Counter)
        self.confusion = collections.Counter()
        self.kinds_conf = collections.Counter()
        self.kind_file = collections.defaultdict(collections.Counter)
        self.missed, self.wrong, self.spurious, self.role_err = [], [], [], []

    def add(self, s: dict, text: str, pred: dict, new: bool):
        st, own = s["state"], s["id"]
        gold = s["references"]
        G_all = {i for g in gold for i in g["ids"]}
        P_all = set(pred["ids"])
        for tag, G, P in (("all", G_all, P_all), ("out", G_all - {own}, P_all - {own})):
            tp = len(G & P)
            for c in (self.c, self.state[st]):
                c[f"{tag}_tp"] += tp
                c[f"{tag}_pred"] += len(P)
                c[f"{tag}_gold"] += len(G)
        # detection (any overlap)
        for g in gold:
            hit = any(overlap((g["start"], g["end"]), sp) for sp in pred["spans"])
            grp = "generic" if g["is_generic"] else "specific"
            for c in (self.c, self.state[st]):
                c["det_n"] += 1
                c["det_hit"] += hit
                c[f"det_{grp}_n"] += 1
                c[f"det_{grp}_hit"] += hit
            k = self.kind[g["kind"]]
            k["n"] += 1
            k["det"] += hit
            if g["ids"]:
                k["with_targets"] += 1
                k["all_gold"] += len(g["ids"])
                k["all_tp"] += len(set(g["ids"]) & P_all)
                out_ids = set(g["ids"]) - {own}
                k["out_gold"] += len(out_ids)
                k["out_tp"] += len(out_ids & P_all)
        if not new:
            return
        refs = pred["refs"]
        m = match(gold, refs)
        self.c["strict_hit"] += len(m)
        self.c["strict_specific_hit"] += sum(1 for gi in m if not gold[gi]["is_generic"])
        self.state[st]["strict_hit"] += len(m)
        matched_r = set(m.values())
        for ri, r in enumerate(refs):
            self.c["pred_refs"] += 1
            self.pkind[r.kind]["n"] += 1
            self.pkind[r.kind]["pred_ids"] += len(r.ids)
            self.pkind[r.kind]["tp_ids"] += len(set(r.ids) & G_all)
            if ri not in matched_r and not any(overlap((g["start"], g["end"]), (r.start, r.end)) for g in gold):
                self.c["spurious"] += 1
                if r.kind not in NO_TARGET_KINDS:
                    self.c["spurious_specific"] += 1
                self.spurious.append((s, r, text))
        for gi, g in enumerate(gold):
            if gi not in m:
                if not any(overlap((g["start"], g["end"]), sp) for sp in pred["spans"]):
                    self.missed.append((s, g, text))
                continue
            r = refs[m[gi]]
            self.c["pairs"] += 1
            self.c["role_ok"] += r.role == g["role"]
            self.roles[g["role"]]["n"] += 1
            self.roles[g["role"]]["ok"] += r.role == g["role"]
            if r.role != g["role"]:
                self.confusion[(g["role"], r.role)] += 1
                self.role_err.append((s, g, r, text))
            gk = "generic" if g["is_generic"] else g["kind"]     # gold C labels generic law other_code + generic
            self.c["kind_ok"] += r.kind == gk
            self.kind_file[s["file"]]["n"] += 1
            self.kind_file[s["file"]]["ok"] += r.kind == gk
            if r.kind != gk:
                self.kinds_conf[(gk, r.kind)] += 1
            if g["unit_path"]:
                self.c["unit_n"] += 1
                self.c["unit_ok"] += bool(r.unit and r.unit.get("path") == g["unit_path"])
            if g.get("pinpoint") and g["kind"] not in NO_TARGET_KINDS:
                self.c["pin_n"] += 1
                self.c["pin_ok"] += norm_pin(r.pinpoint) == norm_pin(g["pinpoint"])
            if g["ids"]:
                self.c["ref_t_n"] += 1
                ok = set(g["ids"]) == set(r.ids)
                self.c["ref_t_exact"] += ok
                if not ok:
                    self.wrong.append((s, g, r, text))


def keep(s: dict, only_state: str | None = None, exclude=()) -> bool:
    return (not only_state or s["state"] == only_state) and s["citation"] not in set(exclude or ())


def evaluate(secs: list[dict], which: list[str], only_state: str | None = None, exclude=()) -> dict:
    accs = {name: {"all": Acc(), "no_user": Acc()} for name in which}
    times = collections.defaultdict(float)
    for s in secs:
        if not keep(s, only_state, exclude):
            continue
        row = I.by_id(s["state"], s["id"])
        text = I.text_of(s["state"], s["id"])
        for name in which:
            t0 = time.perf_counter()
            pred = RESOLVERS[name](s["state"], row, text)
            times[name] += time.perf_counter() - t0
            accs[name]["all"].add(s, text, pred, new=name == "new")
            if not s["user_example"]:
                accs[name]["no_user"].add(s, text, pred, new=name == "new")
    return {"accs": accs, "times": times}


# ------------------------------------------------------------------ report
def pct(a, b) -> str:
    return f"{a / b:6.1%}" if b else "   n/a"


def summary(acc: Acc) -> dict:
    c = acc.c
    out = {"detection": {"all": round(c["det_hit"] / c["det_n"], 3) if c["det_n"] else None,
                         "specific": round(c["det_specific_hit"] / c["det_specific_n"], 3) if c["det_specific_n"]
                         else None,
                         "generic": round(c["det_generic_hit"] / c["det_generic_n"], 3) if c["det_generic_n"] else None,
                         "n": c["det_n"], "n_specific": c["det_specific_n"]},
           "targets_outward": prf(c["out_tp"], c["out_pred"], c["out_gold"]),
           "targets_all": prf(c["all_tp"], c["all_pred"], c["all_gold"]),
           "per_state": {st: {"outward": prf(x["out_tp"], x["out_pred"], x["out_gold"]),
                              "all": prf(x["all_tp"], x["all_pred"], x["all_gold"]),
                              "detection_specific": round(x["det_specific_hit"] / x["det_specific_n"], 3)
                              if x["det_specific_n"] else None} for st, x in sorted(acc.state.items())},
           "per_kind": {k: {"n": x["n"], "detected": round(x["det"] / x["n"], 3),
                            "with_targets": x["with_targets"],
                            "recall_all": round(x["all_tp"] / x["all_gold"], 3) if x["all_gold"] else None,
                            "recall_outward": round(x["out_tp"] / x["out_gold"], 3) if x["out_gold"] else None}
                        for k, x in sorted(acc.kind.items(), key=lambda kv: -kv[1]["n"])}}
    if c["pairs"]:
        out.update({
            "strict_detection": round(c["strict_hit"] / c["det_n"], 3),
            "strict_detection_specific": round(c["strict_specific_hit"] / c["det_specific_n"], 3),
            "predicted_refs": c["pred_refs"], "spurious": c["spurious"], "spurious_specific": c["spurious_specific"],
            "role_accuracy": round(c["role_ok"] / c["pairs"], 3),
            "kind_accuracy": round(c["kind_ok"] / c["pairs"], 3),
            "unit_accuracy": round(c["unit_ok"] / c["unit_n"], 3) if c["unit_n"] else None, "unit_n": c["unit_n"],
            "pinpoint_accuracy": round(c["pin_ok"] / c["pin_n"], 3) if c["pin_n"] else None, "pin_n": c["pin_n"],
            "reference_targets_exact": round(c["ref_t_exact"] / c["ref_t_n"], 3) if c["ref_t_n"] else None,
            "per_role": {k: {"n": x["n"], "acc": round(x["ok"] / x["n"], 3)}
                         for k, x in sorted(acc.roles.items(), key=lambda kv: -kv[1]["n"])},
            "role_confusions": [[g, p, n] for (g, p), n in acc.confusion.most_common(12)],
            "kind_confusions": [[g, p, n] for (g, p), n in acc.kinds_conf.most_common(10)],
            "kind_accuracy_by_gold_file": {f: round(x["ok"] / x["n"], 3) for f, x in sorted(acc.kind_file.items())},
            "precision_by_predicted_kind": {k: {"n": x["n"], "ids": x["pred_ids"],
                                                "p": round(x["tp_ids"] / x["pred_ids"], 3) if x["pred_ids"] else None}
                                            for k, x in sorted(acc.pkind.items(), key=lambda kv: -kv[1]["n"])}})
    return out


def show(name_sums: dict, title: str):
    names = list(name_sums)
    print(f"\n==================== {title} ====================")
    print(f"{'':36}" + "".join(f"{n:>28}" for n in names))

    def line(label, f):
        print(f"{label:36}" + "".join(f"{f(name_sums[n]):>28}" for n in names))
    d = lambda s, k: "n/a" if s["detection"][k] is None else f"{s['detection'][k]:.1%}"   # noqa: E731
    first = name_sums[names[0]]
    line(f"detection, all ({first['detection']['n']})", lambda s: d(s, "all"))
    line(f"detection, specific ({first['detection']['n_specific']})", lambda s: d(s, "specific"))
    line("detection, generic", lambda s: d(s, "generic"))
    line("strict 1-1 detection, specific", lambda s: f"{s['strict_detection_specific']:.1%}"
         if "strict_detection_specific" in s else "n/a")
    line("predicted refs / spurious (spec.)", lambda s: f"{s['predicted_refs']}/{s['spurious']} ({s['spurious_specific']})"
         if "predicted_refs" in s else "n/a")
    for tag in ("targets_outward", "targets_all"):
        line(f"{tag} P / R / F1", lambda s: f"{s[tag]['p']:.3f}/{s[tag]['r']:.3f}/{s[tag]['f1']:.3f}")
        line(f"{tag} tp / pred / gold", lambda s: f"{s[tag]['tp']}/{s[tag]['pred']}/{s[tag]['gold']}")
    for k in ("role_accuracy", "kind_accuracy", "unit_accuracy", "pinpoint_accuracy", "reference_targets_exact"):
        line(k, lambda s: "n/a" if s.get(k) is None else f"{s[k]:.1%}")
    print("\nper state (outward P/R | all P/R | specific detection)")
    for st in first["per_state"]:
        line(f"  {st}", lambda s: "{:.2f}/{:.2f}|{:.2f}/{:.2f}|{:.0%}".format(
            s["per_state"][st]["outward"]["p"], s["per_state"][st]["outward"]["r"], s["per_state"][st]["all"]["p"],
            s["per_state"][st]["all"]["r"], s["per_state"][st]["detection_specific"] or 0))
    print("\nper gold kind (n, refs with targets: detected | recall outward | recall all)")
    for k, x in first["per_kind"].items():
        line(f"  {k} ({x['n']}, {x['with_targets']})", lambda s: "{} | {} | {}".format(
            f"{s['per_kind'][k]['detected']:.0%}",
            "  - " if s["per_kind"][k]["recall_outward"] is None else f"{s['per_kind'][k]['recall_outward']:.2f}",
            "  - " if s["per_kind"][k]["recall_all"] is None else f"{s['per_kind'][k]['recall_all']:.2f}"))
    for n in names:
        s = name_sums[n]
        if "per_role" not in s:
            continue
        print(f"\n[{n}] role accuracy by gold role: " + ", ".join(
            f"{k} {x['acc']:.0%} ({x['n']})" for k, x in s["per_role"].items()))
        print(f"[{n}] top role confusions (gold -> predicted): " + ", ".join(
            f"{g}->{p} {c}" for g, p, c in s["role_confusions"]))
        print(f"[{n}] top kind confusions (gold -> predicted): " + ", ".join(
            f"{g}->{p} {c}" for g, p, c in s["kind_confusions"]))
        print(f"[{n}] kind accuracy by gold file (each file has its own kind precedence): " + ", ".join(
            f"{f} {x:.0%}" for f, x in s["kind_accuracy_by_gold_file"].items()))
        print(f"[{n}] target precision by predicted kind: " + ", ".join(
            f"{k} {x['p'] if x['p'] is not None else '-'} ({x['n']} refs, {x['ids']} ids)"
            for k, x in s["precision_by_predicted_kind"].items()))


def ctx(text: str, a: int, b: int, w: int = 60) -> str:
    return (text[max(0, a - w):a] + "<<" + text[a:b] + ">>" + text[b:b + 25]).replace("\n", " ")


def failures(acc: Acc, n: int):
    print("\n==================== failure patterns (new resolver, all sections) ====================")
    by = collections.defaultdict(list)
    for s, g, text in acc.missed:
        by[g["kind"] + (" (generic)" if g["is_generic"] else "")].append((s, g, text))
    print(f"\nMISSED gold references (no overlapping prediction): {len(acc.missed)}")
    for k, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k}: {len(xs)}")
        for s, g, text in xs[:n]:
            print(f"      {s['state']} {s['citation']}: ...{ctx(text, g['start'], g['end'])}")
    print(f"\nWRONG targets (matched, target ids differ): {len(acc.wrong)}")
    byw = collections.defaultdict(list)
    for s, g, r, text in acc.wrong:
        why = ("no prediction" if not r.ids else "partial" if set(r.ids) < set(g["ids"]) else
               "extra" if set(r.ids) > set(g["ids"]) else "different")
        byw[f"{g['kind']} / {why}"].append((s, g, r, text))
    for k, xs in sorted(byw.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k}: {len(xs)}")
        for s, g, r, text in xs[:n]:
            print(f"      {s['state']} {s['citation']}: ...{ctx(text, g['start'], g['end'])}  gold="
                  f"{(g.get('target_sections') or [])[:3]} pred={[x['citation'] for x in r.sections][:3]} "
                  f"note={r.note}")
    print(f"\nSPURIOUS predictions (overlap no gold reference): {len(acc.spurious)}")
    bys = collections.defaultdict(list)
    for s, r, text in acc.spurious:
        bys[r.kind].append((s, r, text))
    for k, xs in sorted(bys.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k}: {len(xs)}")
        for s, r, text in xs[:n]:
            print(f"      {s['state']} {s['citation']}: ...{ctx(text, r.start, r.end)}")
    print(f"\nROLE errors: {len(acc.role_err)} (examples)")
    for s, g, r, text in acc.role_err[:n * 3 if n < 50 else None]:
        print(f"      {g['role']:>20} <- {r.role:<20} {s['state']}: ...{ctx(text, g['start'], g['end'], 70)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--resolver", choices=["current", "new", "both"], default="both")
    ap.add_argument("--failures", type=int, default=0, help="examples per failure group (new resolver)")
    ap.add_argument("--json", help="write the metrics to this file")
    ap.add_argument("--only-state")
    ap.add_argument("--exclude", action="append", default=[], metavar="CITATION",
                    help="leave out this gold section (repeatable)")
    a = ap.parse_args(argv)
    which = ["current", "new"] if a.resolver == "both" else [a.resolver]
    secs = load_gold()
    unknown = set(a.exclude) - {s["citation"] for s in secs}
    if unknown:
        ap.error(f"not a gold section: {sorted(unknown)}")
    t0 = time.perf_counter()
    if "new" in which:                                    # build the code tables first, outside the timing
        from lexflow.law import xref
        for st in sorted({s["state"] for s in secs}):
            xref.table(st)
    t_tables = time.perf_counter() - t0
    res = evaluate(secs, which, a.only_state, a.exclude)
    sums = {sub: {n: summary(res["accs"][n][sub]) for n in which} for sub in ("all", "no_user")}
    n_secs = sum(1 for s in secs if keep(s, a.only_state, a.exclude))
    show(sums["all"], f"all {n_secs} sections")
    show(sums["no_user"], "without the user examples (Cal. BPC § 480, Va. Code § 54.1-204)")
    print("\ntime per section: " + ", ".join(f"{n} {res['times'][n] / max(1, n_secs) * 1000:.1f} ms" for n in which)
          + (f"; code tables built once in {t_tables:.1f} s" if "new" in which else ""))
    if a.failures and "new" in which:
        failures(res["accs"]["new"]["all"], a.failures)
    if a.json:
        Path(a.json).write_text(json.dumps(sums, indent=1, default=str), encoding="utf-8")
        print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
