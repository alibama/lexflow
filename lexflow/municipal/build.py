"""Build one state's process model for one question and record how complete and how good it is.

Order of preference:

1. a **curated** facts file (``curated/<state>/<question>.json``, written by Claude or a
   person, every quote re-checked here against the downloaded statute) -> tier ``reviewed``;
2. **two local models** from different families extract facts from the located section;
   both must quote the text exactly; if they agree (step F1, actors, deadlines) -> ``agreed``,
   otherwise the better-checked one -> ``single``;
3. nothing extracted -> ``found`` (the law is located but has no steps yet), or ``none``.
"""
from __future__ import annotations

import json
import time

import requests

from .. import config
from ..extract.compile import compile_facts
from ..extract.evaluate import score as compare
from ..extract.ollama import ExtractionResult, OllamaClient, check_facts, extract
from ..extract.schema import LegalProcessFacts
from ..ir import Provenance
from ..store import db
from . import method as M
from . import states as S
from . import statutes
from .fetch import Log
from .quality import assess
from .questions import get as get_question


def model_id(state: str, question: str) -> str:
    return f"{state}.{question}"


def ollama_models(url: str | None = None) -> list[str]:
    try:
        r = requests.get(f"{(url or config.OLLAMA_URL).rstrip('/')}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except requests.RequestException:
        return []


def _has(available: list[str], name: str) -> bool:
    return name in available or f"{name}:latest" in available


def agreement(a: LegalProcessFacts, b: LegalProcessFacts, text: str) -> dict:
    """How far two models' facts agree, averaged both ways, with steps matched by the clause they quote."""
    from ..extract.benchmark import equivalence
    ab, ba = equivalence(a, b), equivalence(b, a)
    return {k: round((ab[k] + ba[k]) / 2, 3) for k in ("value", "step_f1", "actors", "deadlines", "modality")}


def lexical_agreement(a: LegalProcessFacts, b: LegalProcessFacts, text: str) -> dict:
    """The earlier measure: steps matched by the wording of their actions only."""
    ab, ba = compare(a, b, text), compare(b, a, text)
    p, r = ab.step_precision, ab.step_recall
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    has_dl = any(s.deadline for s in a.steps) or any(s.deadline for s in b.steps)
    deadline = (ab.deadline_recall + ba.deadline_recall) / 2 if has_dl else 1.0
    actors = (ab.actor_recall + ba.actor_recall) / 2
    value = 0.5 * f1 + 0.2 * actors + 0.2 * deadline + 0.1 * ab.modality_accuracy
    return {"value": round(value, 3), "step_f1": round(f1, 3), "actors": round(actors, 3),
            "deadlines": round(deadline, 3), "modality": ab.modality_accuracy}


def _stages(**done) -> dict:
    ts = db.now()
    return {s: (ts if done.get(s) else None) for s in M.STAGES}


def _row(state, question, *, tier, built_by, stages, title=None, metrics=None, quality=None, facts=None,
         bpmn=None, dmn=None, svg=None, loc=None) -> dict:
    done = sum(1 for v in stages.values() if v)
    return {"model_id": model_id(state, question), "state": state, "question": question, "scope": "state",
            "title": title, "tier": tier, "built_by": built_by, "stages": stages,
            "completion": round(done / len(M.STAGES), 3), "quality": quality, "metrics": metrics or {},
            "facts": facts, "bpmn": bpmn, "dmn": dmn, "svg": svg,
            "citation": (loc or {}).get("citation"), "source_url": (loc or {}).get("url")}


def _norm_ws(s: str) -> str:
    import re
    return re.sub(r"\s+", " ", s or "").strip().lower()


def related_sections(state: str, question: str, loc: dict, limit: int = 6) -> list[str]:
    """The located section plus the related ones the verification listed for it (requests, responses, fees,
    appeals ...): Claude's reference models draw on 3 to 28 sections, and a process read from one section alone
    misses most of its steps.  Only for a verified section; definitions and sections not in the file are skipped."""
    import re
    from .locator import verified_seeds
    refs = [loc["section"]]
    v = verified_seeds().get(state, {}).get(question) or {}
    if loc.get("method") != "verified" or not v.get("alternates"):
        return refs
    df = statutes.load(state)
    prefix = loc["citation"].rsplit("§", 1)[0].strip() if "§" in (loc.get("citation") or "") else ""
    for alt in v["alternates"]:
        if re.search(r"definition|not present|not in the|repealed|missing", alt, re.I):
            continue
        ref = re.split(r"\s+\(|;", alt, maxsplit=1)[0].strip().rstrip(".,")
        for cand in dict.fromkeys(x for x in (ref, f"{prefix} § {ref}" if prefix and "§" not in ref else None) if x):
            try:
                hit = statutes.find(df, cand)
            except Exception:  # noqa: BLE001 - a malformed reference
                continue
            if len(hit) == 1:
                r = statutes.ref_of(state, hit.iloc[0])
                if r not in refs:
                    refs.append(r)
                break
        if len(refs) >= limit:
            break
    return refs


def _pin_sections(facts: LegalProcessFacts, texts) -> LegalProcessFacts:
    """A model reading one section sometimes writes '§ 2-532' or '2-532(a)'.  Every quote gets the section whose
    text holds it (with one section, that section)."""
    data = facts.model_dump()
    texts = texts if isinstance(texts, list) else None
    known = {t.section for t in texts} if texts else set()

    def home(quote: str, current: str) -> str:
        if not texts or len(texts) == 1:
            return texts[0].section if texts else current
        if current in known:
            return current
        q = _norm_ws(quote)
        return next((t.section for t in texts if q and q in _norm_ws(t.text)), texts[0].section)

    def walk(node):
        if isinstance(node, dict):
            if {"section", "quote"} <= node.keys():
                node["section"] = home(node.get("quote") or "", node.get("section") or "")
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    return LegalProcessFacts.model_validate(data)


def _fix_sources(model, texts) -> None:
    """Point every source at the text it quotes, so citations name the right article or code
    (a Maryland model can quote General Provisions and Corporations and Associations at once)."""
    import re as _re
    by_section: dict[str, list] = {}
    for t in texts:
        by_section.setdefault(t.section, []).append(t)

    def fix(src):
        cands = by_section.get(src.section) or []
        if not cands:
            return
        t = cands[0]
        if len(cands) > 1 and src.quote:
            norm = lambda s: _re.sub(r"\s+", " ", s)  # noqa: E731
            t = next((c for c in cands if norm(src.quote) in norm(c.text)), cands[0])
        sub = "".join(f"({p})" for p in src.subsection.split(".")) if src.subsection else ""
        src.code, src.url = t.code, t.url
        src.citation = f"{t.code} § {src.section}{sub}"

    for _, _, n in model.iter_nodes():
        for s in n.sources:
            fix(s)
    for p in model.processes():
        for f in p.flows:
            for s in f.sources:
                fix(s)
    for mf in model.message_flows:
        for s in mf.sources:
            fix(s)
    for d in model.decisions:
        for s in d.sources:
            fix(s)
        for r in d.rules:
            for s in r.sources:
                fix(s)


def _compile(facts: LegalProcessFacts, state: str, question: str, texts, provenance: Provenance):
    model = compile_facts(facts, model_id=f"{state}-{question}", jurisdiction=state,
                          jurisdiction_name=S.NAME[state], code=texts[0].code, text=texts[0], provenance=provenance)
    model.texts = list(texts)
    _fix_sources(model, texts)
    return model


def build(con, state: str, question: str, *, use_llm: bool = True, force: bool = False, log: Log = print,
          use_curated: bool = True) -> dict:
    q = get_question(question)
    meth = M.get(con)
    loc = db.one(con, "SELECT * FROM located_law WHERE state=? AND question=?", state, question)
    existing = db.one(con, "SELECT tier, stages FROM process_models WHERE model_id=?", model_id(state, question))
    if existing and existing["tier"] == "reviewed" and not force:
        log(f"{state} {question}: already reviewed; use force to rebuild")
        return {"tier": "reviewed", "skipped": True}
    if not loc or loc["status"] != "found":
        row = _row(state, question, tier="none", built_by=None, stages=_stages(), loc=loc)
        db.upsert(con, "process_models", [row])
        db.bump(con)
        con.commit()
        log(f"{state} {question}: no state law located")
        return {"tier": "none"}

    curated = config.CURATED_DIR / state / f"{question}.json"
    if use_curated and curated.exists():
        spec = json.loads(curated.read_text(encoding="utf-8"))
        texts = statutes.section_texts(state, spec["sections"])
        text = statutes.combined_text(texts)
        facts = LegalProcessFacts.model_validate(spec["facts"])
        problems = check_facts(facts, text)
        if problems:
            log(f"{state} {question}: curated facts no longer match the statute text ({len(problems)} problems): "
                + "; ".join(problems[:3]))
        else:
            model = _compile(facts, state, question, texts,
                             Provenance(method="gold-manual", model=spec.get("reviewed_by"), created=db.now(),
                                        notes=[f"curated/{state}/{question}.json"]))
            model.texts = texts
            res = assess(model, agreement=1.0)
            stages = _stages(located=True, text=True, extracted=True, cross_checked=True, compiled=True,
                             validated=res["validated"], reviewed=True)
            row = _row(state, question, tier="reviewed", built_by="claude", stages=stages, title=facts.process_name,
                       metrics={**res["metrics"], "reviewed_by": spec.get("reviewed_by"), "errors": res["errors"],
                                "sections": spec["sections"], "gaps": facts.gaps},
                       quality=res["quality"], facts=facts.model_dump(), bpmn=res["bpmn"], dmn=res["dmn"],
                       svg=res["svg"], loc=loc)
            db.upsert(con, "process_models", [row])
            db.bump(con)
            con.commit()
            log(f"{state} {question}: reviewed model built (quality {res['quality']:.2f}, "
                f"validated={res['validated']})")
            return {"tier": "reviewed", "quality": res["quality"]}

    sections = related_sections(state, question, loc)
    texts = statutes.section_texts(state, sections)
    text = statutes.combined_text(texts)
    available = ollama_models() if use_llm else []
    llms = [m for m in (config.MODEL_A, config.MODEL_B) if _has(available, m)]
    if use_llm and not llms:
        log(f"{state} {question}: Ollama has neither {config.MODEL_A} nor {config.MODEL_B}; "
            f"run the 'Pull local models' step (Ollama at {config.OLLAMA_URL}, has: {available or 'nothing'})")
    from ..extract.benchmark import LLM_FREE
    strategy = config.STRATEGY
    # a strategy that needs no chat model runs once; the cross-check is then a different method with a local
    # model, so "two models agree" always means two independent extractions agree
    if strategy in LLM_FREE:
        runs = [(f"selector:{strategy}", strategy, None)]
        if llms and config.CHECK_STRATEGY:
            runs.append((llms[0], config.CHECK_STRATEGY, llms[0]))
    else:
        runs = [(llm, strategy, llm) for llm in llms]
    results = {}
    for label, strat, llm in runs:
        oneshot = strat == "oneshot"
        client = OllamaClient(base_url=config.OLLAMA_URL, model=llm, num_ctx=config.NUM_CTX if oneshot else 4096,
                              timeout=1800) if llm else None
        t0 = time.time()
        log(f"{state} {question}: extracting with {label} ({strat}) from {loc['citation']} ({len(text.split())} words)")
        try:
            if oneshot:
                res = extract(client, text=text, section=texts[0].section, title=texts[0].title, code=texts[0].code,
                              jurisdiction=S.NAME[state], max_repairs=2)
            else:
                from ..extract import strategies as ST
                run_ = ST.run(strat, text, section=texts[0].section, title=texts[0].title, code=texts[0].code,
                              jurisdiction=S.NAME[state], question=question, client=client, state=state)
                res = ExtractionResult(run_.facts, run_.calls, run_.problems, label, strat)
        except requests.RequestException as e:
            log(f"{state} {question}: {label} failed: {e}")
            continue
        llm = label
        secs = round(time.time() - t0, 1)
        ok = res.facts is not None and not res.problems
        db.upsert(con, "extractions", [{"model_id": model_id(state, question), "llm": llm, "state": state,
                                        "ok": int(ok), "rounds": res.rounds, "problems": res.problems[:30],
                                        "facts": res.facts.model_dump() if res.facts else None,
                                        "seconds": secs, "prompt_hash": res.prompt_hash}])
        con.commit()
        log(f"{state} {question}: {llm} {'passed' if ok else 'failed'} quote checks in {res.rounds} round(s), {secs}s"
            + ("" if ok else f" - {len(res.problems)} problems, e.g. {res.problems[0][:120] if res.problems else ''}"))
        if ok:
            results[llm] = _pin_sections(res.facts, texts)

    if not results:
        tier = "found"
        stages = _stages(located=True, text=True)
        row = _row(state, question, tier=tier, built_by=None, stages=stages, loc=loc,
                   metrics={"llms_tried": llms, "locator_score": loc["score"]})
        db.upsert(con, "process_models", [row])
        db.bump(con)
        con.commit()
        log(f"{state} {question}: law located ({loc['citation']}); no checked extraction yet")
        return {"tier": tier}

    agree = None
    if len(results) == 2:
        (la, fa), (lb, fb) = results.items()
        agree = agreement(fa, fb, text)
        log(f"{state} {question}: {la} vs {lb} agreement {agree['value']:.2f} (steps F1 {agree['step_f1']:.2f})")
    built = []
    for llm, facts in results.items():
        model = _compile(facts, state, question, texts,
                         Provenance(method="learned-selector" if llm.startswith("selector:") else "llm-extraction",
                                    model=llm, created=db.now()))
        built.append((llm, facts, assess(model, agreement=agree["value"] if agree else None)))
    built.sort(key=lambda x: (x[2]["validated"], x[2]["quality"], len(x[1].steps)), reverse=True)
    llm, facts, res = built[0]
    two = agree is not None and agree["value"] >= meth["agreement_threshold"]
    tier = "agreed" if two else "single"
    stages = _stages(located=True, text=True, extracted=True, cross_checked=two, compiled=True,
                     validated=res["validated"])
    row = _row(state, question, tier=tier, built_by="+".join(r if r.startswith("selector:") else f"ollama:{r}"
                                                             for r in results), stages=stages,
               title=facts.process_name, quality=res["quality"], facts=facts.model_dump(), bpmn=res["bpmn"],
               dmn=res["dmn"], svg=res["svg"], loc=loc,
               metrics={**res["metrics"], "chosen": llm, "agreement_detail": agree, "errors": res["errors"],
                        "sections": sections, "gaps": facts.gaps})
    db.upsert(con, "process_models", [row])
    db.bump(con)
    con.commit()
    log(f"{state} {question}: {tier} model from {llm} (quality {res['quality']:.2f}, validated={res['validated']})")
    return {"tier": tier, "quality": res["quality"]}


def rebuild(con, mid: str):
    """The LegalProcessModel behind a stored row (for publishing): same facts, same statute text."""
    r = db.one(con, "SELECT state, question, facts, metrics, built_by FROM process_models WHERE model_id=?", mid)
    if not r or not r["facts"]:
        raise KeyError(f"{mid} has no facts to rebuild from")
    facts = LegalProcessFacts.model_validate(db.loads(r["facts"]))
    metrics = db.loads(r["metrics"], {})
    texts = statutes.section_texts(r["state"], metrics.get("sections") or [])
    prov = Provenance(method="gold-manual" if r["built_by"] == "claude" else "llm-extraction",
                      model=metrics.get("reviewed_by") or metrics.get("chosen"), notes=[f"lexflow {mid}"])
    model = _compile(facts, r["state"], r["question"], texts, prov)
    model.texts = texts
    return model


def run(con, states_: list[str], questions_: list[str], *, use_llm=True, force=False, log: Log = print,
        progress=None, gov_ids: list[str] | None = None) -> dict:
    from . import scoring
    tiers: dict[str, int] = {}
    total = len(states_) * len(questions_)
    i = 0
    for st in states_:
        for qid in questions_:
            try:
                out = build(con, st, qid, use_llm=use_llm, force=force, log=log)
                tiers[out["tier"]] = tiers.get(out["tier"], 0) + 1
            except Exception as e:  # noqa: BLE001 - one state's failure must not stop the run
                log(f"{st} {qid}: build failed: {type(e).__name__}: {e}")
                tiers["error"] = tiers.get("error", 0) + 1
            i += 1
            if progress:
                progress(i / total)
        # re-score straight away so the confidence map follows each state as it is built
        if db.scalar(con, "SELECT count(*) FROM governments WHERE state=?", st, default=0):
            scoring.run(con, st, log=log, gov_ids=gov_ids)
    return tiers
