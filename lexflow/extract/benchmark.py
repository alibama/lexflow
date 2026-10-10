"""Score extraction strategies x local models against Claude's reference models (curated/<state>/<question>.json).

equivalence = agreement(candidate, reference): 0.5 x step F1 + 0.2 x actors + 0.2 x deadlines + 0.1 x modality,
the same measure the build uses for "two models agree".  A candidate only counts if every quote is exact.
Each row records a hash of the reference it was scored against, because references improve over time.
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache

from .. import config
from ..municipal import statutes
from ..municipal import states as S
from ..store import db
from .evaluate import score
from .ollama import OllamaClient
from .schema import LegalProcessFacts
from . import strategies as ST

LLM_FREE = {"rules", "rules_sub", "learned", "learned_wide", "wide", "stack_nb", "stack", "stack_tfidf", "stack_embed", "stack_combo"}


def cases() -> list[str]:
    return sorted(f"{p.parent.name}.{p.stem}" for p in config.CURATED_DIR.glob("*/*.json"))


def load_case(case: str):
    state, question = case.split(".", 1)
    spec = json.loads((config.CURATED_DIR / state / f"{question}.json").read_text(encoding="utf-8"))
    texts = statutes.reference_texts(state, spec["sections"])
    gold = LegalProcessFacts.model_validate(spec["facts"])
    ghash = hashlib.sha256(json.dumps(spec["facts"], sort_keys=True).encode()).hexdigest()[:12]
    return state, question, texts, statutes.combined_text(texts), gold, ghash


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower())) - {"the", "and", "for", "with", "shall", "may"}


def same_act(c, g) -> float:
    """1.0 when both steps quote the same clause of the law (one quote inside the other); otherwise the
    word overlap of the two action phrases, plus a little when they cite the same subsection."""
    qc, qg = _norm(c.source.quote), _norm(g.source.quote)
    if qc and qg and c.source.section == g.source.section and (qg in qc or qc in qg):
        return 1.0
    a, b = _tokens(c.action), _tokens(g.action)
    sim = len(a & b) / len(a | b) if a | b else 0.0
    same_sub = (c.source.section == g.source.section
                and (c.source.subsection or "").split(".")[0].lower() == (g.source.subsection or "").split(".")[0].lower())
    return sim + (0.15 if same_sub else 0.0)


def equivalence(cand: LegalProcessFacts, gold: LegalProcessFacts, threshold: float = 0.34) -> dict:
    """How close a candidate is to the reference: 0.5 x step F1 + 0.2 x actor kinds + 0.2 x deadlines
    + 0.1 x duty type, with steps matched by the clause they quote (or failing that, by their wording)."""
    kinds_c = {a.id: a.kind for a in cand.actors}
    kinds_g = {a.id: a.kind for a in gold.actors}
    # global best-first assignment: when one clause supports two reference steps (a request and its response
    # in the same sentence), the candidate goes to the step it fits best, preferring matching deadlines
    scored = []
    for gi, g in enumerate(gold.steps):
        for ci, c in enumerate(cand.steps):
            s = same_act(c, g)
            if s < threshold:
                continue
            dl = bool(g.deadline and c.deadline and g.deadline.amount == c.deadline.amount
                      and g.deadline.unit == c.deadline.unit)
            scored.append((s + (0.2 if dl else 0.0), gi, ci))
    scored.sort(key=lambda x: -x[0])
    pairs, used_g, used_c = [], set(), set()
    for _, gi, ci in scored:
        if gi in used_g or ci in used_c:
            continue
        used_g.add(gi)
        used_c.add(ci)
        pairs.append((cand.steps[ci], gold.steps[gi]))
    p = len(pairs) / max(1, len(cand.steps))
    r = len(pairs) / max(1, len(gold.steps))
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    actors = (sum(1 for c, g in pairs if kinds_c.get(c.actor) == kinds_g.get(g.actor)) / len(pairs)) if pairs else 0.0
    gold_dl = [g for g in gold.steps if g.deadline]
    if gold_dl:
        matched = {id(g): c for c, g in pairs}
        hit = sum(1 for g in gold_dl if (c := matched.get(id(g))) and c.deadline
                  and c.deadline.amount == g.deadline.amount and c.deadline.unit == g.deadline.unit)
        deadlines = hit / len(gold_dl)
    else:
        deadlines = 1.0 if not any(c.deadline for c in cand.steps) else 0.5
    modality = (sum(1 for c, g in pairs if c.modality == g.modality) / len(pairs)) if pairs else 0.0
    value = 0.5 * f1 + 0.2 * actors + 0.2 * deadlines + 0.1 * modality
    return {"value": round(value, 3), "step_f1": round(f1, 3), "precision": round(p, 3), "recall": round(r, 3),
            "actors": round(actors, 3), "deadlines": round(deadlines, 3), "modality": round(modality, 3),
            "matched": len(pairs)}


def ceiling() -> list[dict]:
    """How far two careful drafts by Claude agree: each curated_alt/<state>/<question>.json is an independent
    second reference, written without seeing the first.  Equivalence is not symmetric (precision and recall
    swap), so both directions are reported; their mean is the ceiling any local strategy can be measured to."""
    out = []
    for p in sorted((config.ROOT / "curated_alt").glob("*/*.json")):
        case = f"{p.parent.name}.{p.stem}"
        try:
            gold = load_case(case)[4]
            alt = LegalProcessFacts.model_validate(json.loads(p.read_text(encoding="utf-8"))["facts"])
        except Exception as e:  # noqa: BLE001 - no first reference for this case, or a draft that does not load
            out.append({"case": case, "error": f"{type(e).__name__}: {e}"[:200]})
            continue
        a, b = equivalence(alt, gold), equivalence(gold, alt)
        out.append({"case": case, "value": round((a["value"] + b["value"]) / 2, 3), "alt_vs_ref": a,
                    "ref_vs_alt": b, "steps": [len(gold.steps), len(alt.steps)]})
    return out


def oracle(case: str) -> dict:
    """The best a selector could do with each candidate generator: keep exactly the candidates whose clause
    Claude quoted for a step.  What is left below 1.0 is lost to candidate recall, actors or deadlines."""
    from . import selector as SEL
    from .segment import segment
    state, question, texts, text, gold, _ = load_case(case)
    clauses = segment(text)
    out = {}
    for name, cands in (("rules", ST.rule_drafts(clauses, question)), ("wide", SEL.wide_drafts(clauses, question))):
        labels, kinds = SEL.labels_for(cands, gold.model_dump())
        keep = [d for d, y in zip(cands, labels) if y]
        for d in keep:
            d["actor_kind"] = ST.actor_kind(d["actor"])
        if keep:
            eq = equivalence(ST.assemble(keep, clauses, texts[0].section, question, "oracle"), gold)
            out[name] = {**eq, "candidates": len(cands)}
        else:
            out[name] = {"value": 0.0, "candidates": len(cands)}
    return out


def _prior(con, state: str, question: str, model: str):
    row = db.one(con, "SELECT facts FROM extractions WHERE model_id=? AND llm=?", f"{state}.{question}", model)
    facts = db.loads(row["facts"]) if row else None
    return LegalProcessFacts.model_validate(facts) if facts else None


def run_one(con, case: str, strategy: str, model: str | None, log=print) -> dict:
    from ..municipal.build import lexical_agreement
    state, question, texts, text, gold, ghash = load_case(case)
    ctx = config.NUM_CTX if strategy in ("oneshot", "snap") else 4096       # decomposed calls are short
    client = OllamaClient(base_url=config.OLLAMA_URL, model=model, num_ctx=ctx, timeout=1800) \
        if model and strategy not in LLM_FREE else None
    prior = _prior(con, state, question, model) if strategy == "snap" and model else None
    if strategy == "snap" and prior is None:
        log(f"{case} snap/{model}: no stored oneshot output to snap; skipped")
        return {}
    r = ST.run(strategy, text, section=texts[0].section, title=texts[0].title, code=texts[0].code,
               jurisdiction=S.NAME[state], question=question, client=client, prior=prior, state=state)
    row = {"case": case, "strategy": strategy, "model": model if strategy not in LLM_FREE else "-",
           "gold_hash": ghash, "seconds": round(r.seconds, 1), "calls": r.calls, "notes": r.notes,
           "problems": r.problems[:20], "valid": int(r.facts is not None and not r.problems),
           "gold_steps": len(gold.steps), "created_at": db.now()}
    if r.facts is not None:
        sc = score(r.facts, gold, text)
        eq = equivalence(r.facts, gold)
        lex = lexical_agreement(r.facts, gold, text)  # wording-only comparison, kept for transparency
        row.update(equivalence=eq["value"] if row["valid"] else 0.0, raw_equivalence=eq["value"],
                   lexical=lex["value"], step_f1=eq["step_f1"], actors=eq["actors"], deadlines=eq["deadlines"],
                   modality=eq["modality"], step_recall=eq["recall"], step_precision=eq["precision"],
                   quote_validity=sc.quote_validity, steps=len(r.facts.steps), facts=r.facts.model_dump())
    else:
        row.update(equivalence=0.0, raw_equivalence=0.0, steps=0)
    cols = ", ".join(f'"{k}"' for k in row)            # "case" is an SQL keyword
    con.execute(f"INSERT INTO benchmarks ({cols}) VALUES ({', '.join('?' for _ in row)})",
                [json.dumps(v) if isinstance(v, (dict, list)) else v for v in row.values()])
    db.bump(con)
    con.commit()
    log(f"{case} {strategy}/{row['model']}: equivalence {row['equivalence']:.2f} (steps {row.get('steps')} vs "
        f"{row['gold_steps']}, F1 {row.get('step_f1', 0):.2f}, deadlines {row.get('deadlines', 0):.2f}) "
        f"in {row['seconds']}s, {row['calls']} calls" + (f"; {row['problems'][0][:80]}" if row["problems"] else ""))
    return row


def run(con, case_list: list[str], strategy_list: list[str], model_list: list[str], log=print, progress=None) -> dict:
    jobs = []
    for case in case_list:
        for strategy in strategy_list:
            for model in (["-"] if strategy in LLM_FREE else model_list):
                jobs.append((case, strategy, None if model == "-" else model))
    out = []
    for i, (case, strategy, model) in enumerate(jobs):
        try:
            out.append(run_one(con, case, strategy, model, log=log))
        except Exception as e:  # noqa: BLE001 - keep going through the grid
            log(f"{case} {strategy}/{model}: failed: {type(e).__name__}: {e}")
        if progress:
            progress((i + 1) / len(jobs))
    return {"runs": len([o for o in out if o]), "best": best(con)[:10]}


def gold_hashes() -> dict[str, str]:
    """The hash of every current reference, recomputed only when a reference file changes."""
    stamp = tuple(sorted((str(p), p.stat().st_mtime) for p in config.CURATED_DIR.glob("*/*.json")))
    return _gold_hashes(stamp)


@lru_cache(maxsize=2)
def _gold_hashes(stamp: tuple) -> dict[str, str]:
    cur = {}
    for case in cases():
        try:
            cur[case] = load_case(case)[5]
        except Exception:  # noqa: BLE001 - a reference that no longer loads
            continue
    return cur


def best(con, current_only: bool = True) -> list[dict]:
    """Latest run per (case, strategy, model), scored against the current reference."""
    cols = ", ".join(f'b."{c}"' for c in db.columns(con, "benchmarks") if c != "facts")   # facts are large
    rows = db.rows(con, f"""
        SELECT {cols} FROM benchmarks b JOIN (SELECT case_id, strategy, model, max(id) AS id FROM
            (SELECT "case" AS case_id, strategy, model, id FROM benchmarks) GROUP BY case_id, strategy, model) m
        ON b.id = m.id ORDER BY b.equivalence DESC""")
    if current_only:
        cur = gold_hashes()
        rows = [r for r in rows if cur.get(r["case"]) == r["gold_hash"]]
    for r in rows:
        r.pop("facts", None)
        for k in ("notes", "problems"):
            r[k] = db.loads(r[k], [])
    return rows
