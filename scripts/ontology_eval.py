"""Measure the section tagger (lexflow.law.ontology) on the xref gold and the reviewed models' sections.

    python -m scripts.ontology_eval [--max 150] [--budget 200] [--chat 30] [--json out.json]

Sample: the 82 gold sections (fixtures/xref/gold_{a,b,c}.json, by state and index id) plus the sections the 22
reviewed models' steps quote (process_models.facts.steps[].source.section, resolved in the state's index by the
model's citation prefix), up to ``--max`` sections.  Labels:

* from the facts: the modalities of the steps a section grounds (obligation / permission / prohibition; ``right``
  counts as permission) -> expected norm types.  The facts are not exhaustive, so recall is the honest number
  there and precision is reported only against what the facts say.
* from the gold: a ``definition`` reference role means the section cites a definition (not that it defines), so
  the definition label here is lexflow.law.terms.definitions (does the section define a term?), and the gold's
  ``penalty`` role (the section cites a penalty provision) is reported as what it is: a weak penalty label.

Arms: rules on the whole text; the decision model (seven noul questions, head + 1,500 chars, one call per section)
on every section within ``--budget``; the chat fallback on the first ``--chat`` sections.  Timing per call is
measured; the nationwide estimate is sections per state (from the indexes) times the measured time.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def gold_sections() -> list[dict]:
    out = []
    for f in "abc":
        p = ROOT / "fixtures" / "xref" / f"gold_{f}.json"
        if not p.exists():
            continue
        g = json.loads(p.read_text(encoding="utf-8"))
        for s in g["sections"]:
            roles = {r.get("role") for r in s.get("references", [])}
            out.append({"state": s["state"], "id": s["id"], "citation": s["citation"], "source": "gold",
                        "labels": {"penalty_role": "penalty" in roles, "definition_role": "definition" in roles}})
    return out


def model_sections(con) -> list[dict]:
    from lexflow.ask import index as I
    from lexflow.store import db
    by: dict[tuple[str, str], dict] = {}
    for r in db.rows(con, "SELECT model_id, state, citation, facts FROM process_models WHERE tier='reviewed'"):
        f = json.loads(r["facts"] or "{}")
        for s in f.get("steps", []):
            sec = (s.get("source") or {}).get("section")
            if not sec:
                continue
            key = (r["state"], sec)
            e = by.setdefault(key, {"state": r["state"], "section": sec, "model_id": r["model_id"],
                                    "citation_prefix": r["citation"], "modalities": set(), "source": "facts"})
            m = s.get("modality")
            if m in ("obligation", "permission", "prohibition"):
                e["modalities"].add(m)
            elif m == "right":
                e["modalities"].add("permission")
    out = []
    for e in by.values():
        prefix = (e["citation_prefix"] or "").split("§")[0].strip()
        cands = I.lookup(e["state"], f"{prefix} § {e['section']}" if prefix else e["section"])
        if not cands:
            cands = I.lookup(e["state"], e["section"])
        if not cands:
            continue
        row = cands[0]
        out.append({"state": e["state"], "id": row["id"], "citation": row["citation"], "source": "facts",
                    "labels": {"modalities": sorted(e["modalities"])}})
    return out


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f = 2 * p * r / (p + r) if p and r else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=150)
    ap.add_argument("--budget", type=int, default=200)
    ap.add_argument("--chat", type=int, default=30)
    ap.add_argument("--json")
    ap.add_argument("--no-model", action="store_true")
    a = ap.parse_args()

    from lexflow.ask import index as I
    from lexflow.extract import decide as D
    from lexflow.law import ontology as O
    from lexflow.law import terms as T
    from lexflow.store import db

    con = db.connect()
    sample = gold_sections()
    seen = {(s["state"], s["id"]) for s in sample}
    for s in model_sections(con):
        if (s["state"], s["id"]) not in seen and len(sample) < a.max:
            sample.append(s)
            seen.add((s["state"], s["id"]))
    sample = sample[:a.max]
    print(f"sample: {len(sample)} sections ({sum(s['source'] == 'gold' for s in sample)} gold, "
          f"{sum(s['source'] == 'facts' for s in sample)} from the reviewed models)")

    # the rows with text, and the definition label from lexflow.law.terms
    rows = []
    for s in sample:
        row = I.by_id(s["state"], s["id"], with_text=True)
        if not row:
            continue
        row["state"] = s["state"]
        text = row.pop("text") or ""
        try:
            defs = T.definitions(s["state"], row, text)
        except Exception:                                   # noqa: BLE001
            defs = []
        s["labels"]["defines"] = bool(defs)
        s["words"] = len(text.split())
        rows.append((s, row, text))
    print(f"with text: {len(rows)}; median words {statistics.median(r[0]['words'] for r in rows):.0f}")

    # arms
    t0 = time.perf_counter()
    for s, row, text in rows:
        s["rules"] = O.rule_types(text, head=row.get("head") or "")
    rules_ms = (time.perf_counter() - t0) * 1000 / max(1, len(rows))

    dec_stats = {"calls": 0, "ms": []}
    chat_stats = {"calls": 0, "ms": []}
    if not a.no_model:
        dec = D.Decider()
        info = dec.backend
        print(f"backend: {info['kind']} {info['model']}")
        calls = 0
        for s, row, text in rows:
            if info["kind"] != "decision" or calls >= a.budget:
                break
            probs, name, ms = O.model_types(dec, row, text)
            if name == "error":
                continue
            calls += 1
            s["decision"] = probs
            s["decision_ms"] = ms
            dec_stats["ms"].append(ms)
        dec_stats["calls"] = calls
        if a.chat and info["kind"] != "none":
            chat = D.Decider(backend_info={"kind": "chat", "model": dec.chat_model, "models": []})
            for s, row, text in rows[:a.chat]:
                if calls + chat_stats["calls"] >= a.budget:
                    break
                probs, name, ms = O.model_types(chat, row, text)
                if name == "error":
                    continue
                chat_stats["calls"] += 1
                s["chat"] = probs
                chat_stats["ms"].append(ms)

    # scoring
    def labelled(s, t):
        """(has label, label value) for a type on a section."""
        L = s["labels"]
        if t in ("obligation", "permission", "prohibition") and "modalities" in L:
            return True, t in L["modalities"]
        if t == "definition":
            return True, L["defines"]
        if t == "penalty" and s["source"] == "gold":
            return True, L["penalty_role"]
        return False, None

    def score(arm, thr):
        out = {}
        for t in O.NORM_TYPES:
            tp = fp = fn = n = 0
            for s, _, _ in rows:
                if arm not in s:
                    continue
                has, y = labelled(s, t)
                if not has:
                    continue
                v = s[arm].get(t)
                if v is None:
                    continue
                pred = v >= thr
                n += 1
                tp += pred and y
                fp += pred and not y
                fn += (not pred) and y
            if n:
                out[t] = {**prf(tp, fp, fn), "n": n, "positives": tp + fn}
        return out

    def best_threshold(arm, t):
        best = (0.5, -1.0)
        for thr in [x / 20 for x in range(1, 20)]:
            r = score(arm, thr).get(t)
            if r and r["f1"] is not None and r["f1"] > best[1]:
                best = (thr, r["f1"])
        return best

    report = {"sample": len(rows), "rules_ms_per_section": rules_ms,
              "decision": {"calls": dec_stats["calls"],
                           "ms_median": statistics.median(dec_stats["ms"]) if dec_stats["ms"] else None,
                           "ms_mean": statistics.mean(dec_stats["ms"]) if dec_stats["ms"] else None},
              "chat": {"calls": chat_stats["calls"],
                       "ms_median": statistics.median(chat_stats["ms"]) if chat_stats["ms"] else None},
              "scores": {"rules": score("rules", 0.5), "decision@0.5": score("decision", 0.5),
                         "chat@0.5": score("chat", 0.5)},
              "best_thresholds": {t: best_threshold("decision", t) for t in O.NORM_TYPES},
              "prevalence": {t: sum(1 for s, _, _ in rows if s[a_] .get(t)) for a_ in ("rules",) for t in O.NORM_TYPES},
              "decision_probs": {t: sorted(round(s["decision"][t], 3) for s, _, _ in rows
                                           if "decision" in s and s["decision"].get(t) is not None)
                                 for t in O.NORM_TYPES}}
    # the union arm: rules plus the model over its best threshold
    for s, _, _ in rows:
        if "decision" in s:
            thr = {t: report["best_thresholds"][t][0] for t in O.NORM_TYPES}
            s["union"] = {t: 1.0 if (s["rules"][t] or (s["decision"].get(t) or 0) >= thr[t]) else 0.0
                          for t in O.NORM_TYPES}
    report["scores"]["union@best"] = score("union", 0.5)
    report["scores"]["decision@best"] = {t: score("decision", report["best_thresholds"][t][0]).get(t)
                                         for t in O.NORM_TYPES}
    # agreement rules vs model at 0.5 on every section (no label needed)
    agree = {}
    for t in O.NORM_TYPES:
        pairs = [(bool(s["rules"][t]), (s["decision"].get(t) or 0) >= 0.5) for s, _, _ in rows if "decision" in s]
        if pairs:
            agree[t] = {"n": len(pairs), "agree": sum(x == y for x, y in pairs) / len(pairs),
                        "rules_yes": sum(x for x, _ in pairs), "model_yes": sum(y for _, y in pairs)}
    report["agreement"] = agree

    def fmt(d):
        return " ".join(f"{k}=P{(v['precision'] or 0) * 100:.0f}/R{(v['recall'] or 0) * 100:.0f}(n{v['n']},+{v['positives']})"
                        for k, v in d.items() if v)
    print(f"rules: {rules_ms:.3f} ms/section; {fmt(report['scores']['rules'])}")
    print(f"decision@0.5 ({dec_stats['calls']} calls, median {report['decision']['ms_median']} ms): "
          f"{fmt(report['scores']['decision@0.5'])}")
    print(f"decision@best: thresholds {report['best_thresholds']}; "
          f"{fmt({k: v for k, v in report['scores']['decision@best'].items() if v})}")
    print(f"union@best: {fmt(report['scores']['union@best'])}")
    print(f"chat@0.5 ({chat_stats['calls']} calls, median {report['chat']['ms_median']} ms): "
          f"{fmt(report['scores']['chat@0.5'])}")
    print("agreement:", {k: f"{v['agree'] * 100:.0f}% (rules {v['rules_yes']}, model {v['model_yes']} of {v['n']})"
                         for k, v in agree.items()})
    print("rules prevalence:", report["prevalence"])
    if a.json:
        Path(a.json).write_text(json.dumps({"report": report, "rows": [s for s, _, _ in rows]}, indent=1,
                                           default=list), encoding="utf-8")
        print("wrote", a.json)


if __name__ == "__main__":
    main()
