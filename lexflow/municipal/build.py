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
from ..extract.ollama import OllamaClient, check_facts, extract
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


def _pin_sections(facts: LegalProcessFacts, section: str) -> LegalProcessFacts:
    """A model reading one section sometimes writes '§ 2-532' or '2-532(a)'; quotes all come from ``section``."""
    data = facts.model_dump()

    def walk(node):
        if isinstance(node, dict):
            if {"section", "quote"} <= node.keys():
                node["section"] = section
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    return LegalProcessFacts.model_validate(data)


def _compile(facts: LegalProcessFacts, state: str, question: str, texts, provenance: Provenance):
    return compile_facts(facts, model_id=f"{state}-{question}", jurisdiction=state,
                         jurisdiction_name=S.NAME[state], code=texts[0].code, text=texts[0], provenance=provenance)


def build(con, state: str, question: str, *, use_llm: bool = True, force: bool = False, log: Log = print) -> dict:
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
    if curated.exists():
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

    texts = statutes.section_texts(state, [loc["section"]])
    text = texts[0].text
    available = ollama_models() if use_llm else []
    llms = [m for m in (config.MODEL_A, config.MODEL_B) if _has(available, m)]
    if use_llm and not llms:
        log(f"{state} {question}: Ollama has neither {config.MODEL_A} nor {config.MODEL_B}; "
            f"run the 'Pull local models' step (Ollama at {config.OLLAMA_URL}, has: {available or 'nothing'})")
    results = {}
    for llm in llms:
        client = OllamaClient(base_url=config.OLLAMA_URL, model=llm, num_ctx=config.NUM_CTX, timeout=1800)
        t0 = time.time()
        log(f"{state} {question}: extracting with {llm} from {loc['citation']} ({len(text.split())} words)")
        try:
            res = extract(client, text=text, section=texts[0].section, title=texts[0].title, code=texts[0].code,
                          jurisdiction=S.NAME[state], max_repairs=2)
        except requests.RequestException as e:
            log(f"{state} {question}: {llm} failed: {e}")
            continue
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
            results[llm] = _pin_sections(res.facts, texts[0].section)

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
                         Provenance(method="llm-extraction", model=llm, created=db.now()))
        built.append((llm, facts, assess(model, agreement=agree["value"] if agree else None)))
    built.sort(key=lambda x: (x[2]["validated"], x[2]["quality"], len(x[1].steps)), reverse=True)
    llm, facts, res = built[0]
    two = agree is not None and agree["value"] >= meth["agreement_threshold"]
    tier = "agreed" if two else "single"
    stages = _stages(located=True, text=True, extracted=True, cross_checked=two, compiled=True,
                     validated=res["validated"])
    row = _row(state, question, tier=tier, built_by="ollama:" + "+".join(results), stages=stages,
               title=facts.process_name, quality=res["quality"], facts=facts.model_dump(), bpmn=res["bpmn"],
               dmn=res["dmn"], svg=res["svg"], loc=loc,
               metrics={**res["metrics"], "chosen": llm, "agreement_detail": agree, "errors": res["errors"],
                        "sections": [loc["section"]], "gaps": facts.gaps})
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
        progress=None) -> dict:
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
    return tiers
