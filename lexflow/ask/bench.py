"""AskBench: the local pipeline's answers to new questions, scored against Claude's references (curated_ask/).

Per case (question, state), deterministic first:

* retrieval  - recall of the gold sections in the top 5 / 10 / 15 candidates, of the primary ones in the chosen
               sections, and the reciprocal rank of the first gold section;
* gate       - did the pipeline answer, answer in part, or say "not found" where Claude's coverage says so;
* nuggets    - the share of Claude's vital (and all) nuggets that the quotes the answer shows (its key provisions
               and its steps) cover: one quote holds the nugget's quote or at least COVER (70%) of its words, or the
               parts of the nugget's text they show hold 70% together (one short clause of a long nugget is not);
* citations  - the share of the answer's quotes that come from a gold section, the same section of the same code
               (precision), and that support a nugget;
* slots      - the numbers in Claude's slots (fees, caps, deadlines) that appear in the answer's quotes as whole
               numbers or words (reference.has_num: the 5 of 1995 or the "ten" of "sentence" do not count);
* steps      - for process questions with reference steps, the step equivalence used for the state models.

composite = 0.35 x (step equivalence for process questions, else vital-nugget recall) + 0.20 x citation precision
          + 0.15 x recall@10 + 0.15 x slot match + 0.15 x gate correct      (the components are always reported too)

Arms: ``local`` (the full pipeline, no chat model), ``heuristic`` (the same without the learned section-relevance
reranker), ``profile`` (searching with Claude's concept groups: what
planning loses), ``oracle`` (Claude's gold sections handed to the same
answering stages: what is lost to retrieval vs to answering).  A learned arm whose held-out reranker is missing or
stale runs without it and is stored as ``<arm>-unlearned``.  Every row records ``version()``, the metric version and
a hash of the code and models behind it; docs/askbench.json keeps the current rows only.
"""
from __future__ import annotations

import json
import re
import statistics as st
import time
from pathlib import Path

from ..municipal import statutes
from ..store import db
from . import index as I
from . import reference as R

METRIC_VERSION = 2       # bump when a metric changes meaning (2: whole numbers, same-code citations, most of a
                         # nugget shown, summaries whose claims were all dropped)
COVER = 0.7              # the share of a nugget's words the answer's quotes must hold for it to count as shown
# the code the answers and their scores come from (with the held-out reranker models): a change makes old rows stale
CODE = ("ask/*.py", "extract/segment.py", "extract/strategies.py", "extract/selector.py", "extract/benchmark.py",
        "municipal/statutes.py")


def version() -> str:
    """The metric version and a short hash of CODE and the held-out reranker models."""
    import hashlib
    from . import relevance as RV
    root = Path(__file__).resolve().parents[1]
    files = sorted({p for pat in CODE for p in root.glob(pat)}) + sorted(RV.loqo_path("_").parent.glob("*.json"))
    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return f"{METRIC_VERSION}-{h.hexdigest()[:12]}"


def _ids(state: str, refs: list[str]) -> list[set[int]]:
    return [{r["id"] for r in I.lookup(state, ref)} for ref in refs]


def _norm(s: str) -> str:
    return R.norm(s)


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9$]{3,}", _norm(s))) - {"the", "and", "shall", "may", "any", "such", "for", "with"}


def overlaps(nugget_quote: str, answer_quote: str) -> bool:
    """The answer quote shows the nugget: it holds the nugget's quote, or at least COVER of its words (a short clause
    inside a long nugget does not)."""
    a, b = _norm(nugget_quote), _norm(answer_quote)
    if not a or not b:
        return False
    if a in b:
        return True
    ta = _tokens(a)
    return bool(ta) and len(ta & _tokens(b)) / len(ta) >= COVER


def _shared(a: str, b: str, n: int = 24) -> str:
    """The text two spans of the same statute share: b inside a, or b running on past a's end or in from before its
    start (by at least ``n`` characters, about four words)."""
    if b in a:
        return b
    best = ""
    i = a.find(b[:n])
    while i != -1:                                  # b starts inside a and runs on past its end
        if b.startswith(a[i:]) and len(a) - i > len(best):
            best = a[i:]
        i = a.find(b[:n], i + 1)
    j = a.find(b[-n:])
    while j != -1:                                  # b starts before a and ends inside it
        if b.endswith(a[:j + n]) and j + n > len(best):
            best = a[:j + n]
        j = a.find(b[-n:], j + 1)
    return best


def covered(nugget_quote: str, answer_quotes: list[str]) -> bool:
    """One answer quote overlaps() the nugget, or the parts of the nugget's text that the quotes show (a nugget that
    spans clauses, each shown) hold COVER of its words together; quotes that merely use the same words do not add."""
    if any(overlaps(nugget_quote, t) for t in answer_quotes):
        return True
    a = _norm(nugget_quote)
    ta = _tokens(a)
    shown = set().union(*(_tokens(_shared(a, _norm(t))) for t in answer_quotes))
    return bool(ta) and len(ta & shown) / len(ta) >= COVER


def _numbered(state: str, ids) -> dict[str, set[int]]:
    """The given sections' ids by their normalised section number (what a quote's "section" names)."""
    ids = sorted(ids)
    if not ids:
        return {}
    con = I.connect(state)
    try:
        rows = con.execute(f"SELECT id, norm_section FROM sec WHERE id IN ({','.join('?' * len(ids))})",
                           ids).fetchall()
    finally:
        con.close()
    out: dict[str, set[int]] = {}
    for r in rows:
        out.setdefault(r["norm_section"], set()).add(r["id"])
    return out


def score(ref: dict, row: dict) -> dict:
    state = ref["state"]
    sec = json.loads(row["sections"]) if isinstance(row.get("sections"), str) else (row.get("sections") or {})
    ans = json.loads(row["answer"]) if isinstance(row.get("answer"), str) else (row.get("answer") or {})
    gold = [g["ref"] for g in ref.get("gold_sections") or []]
    primary = [g["ref"] for g in ref.get("gold_sections") or [] if g["role"] == "primary"]
    gold_ids = _ids(state, gold)
    primary_ids = _ids(state, primary)
    cand_ids = [c["id"] for c in sec.get("candidates") or []]
    chosen_ids = {c["id"] for c in sec.get("chosen") or []}
    out: dict = {"case": f"{ref['qid']}.{state}", "coverage": ref["coverage"], "status": row.get("status")}

    def recall_at(k):
        top = set(cand_ids[:k]) | (chosen_ids if k >= 10 else set())
        return sum(1 for g in gold_ids if g & top) / len(gold_ids) if gold_ids else None
    out.update({f"recall@{k}": recall_at(k) for k in (5, 10, 15)})
    out["primary_chosen"] = (sum(1 for g in primary_ids if g & chosen_ids) / len(primary_ids)) if primary_ids else None
    ranks = [i for i, c in enumerate(cand_ids, 1) if any(c in g for g in gold_ids)]
    out["mrr"] = 1.0 / ranks[0] if ranks else 0.0
    # the gate: not_in_code should be "not_found"; in_code and partial should be answered (fully or in part)
    answered = row.get("status") in ("answered", "partial")
    out["gate_correct"] = float((ref["coverage"] == "not_in_code") != answered)
    # what the answer shows, word for word
    shown = [(q.get("section"), q["text"]) for q in ans.get("quotes") or []] + \
            [(s.get("section"), s["quote"]) for s in ans.get("steps") or []]
    nuggets = ref.get("nuggets") or []
    hit = [n for n in nuggets if covered(n["quote"], [t for _, t in shown])]
    vital = [n for n in nuggets if n["importance"] == "vital"]
    out["nugget_recall"] = len(hit) / len(nuggets) if nuggets else None
    out["vital_recall"] = (sum(1 for n in vital if n in hit) / len(vital)) if vital else None
    gold_all = set().union(*gold_ids)
    by_number = _numbered(state, chosen_ids)

    def in_gold(section, text):
        """A quote names only its section's number: the chosen sections with that number (else every section of the
        state with it), narrowed to the one whose text holds the quote, must all be gold."""
        num = statutes.norm_section(section)
        if not num:
            return False
        ids = by_number.get(num) or {r["id"] for r in I.lookup(state, str(section))}
        if len(ids) > 1:                     # the same number in two codes
            ids = {i for i in ids if _norm(text) in _norm(I.text_of(state, i))} or ids
        return bool(ids) and ids <= gold_all
    out["citation_precision"] = (sum(1 for s, t in shown if in_gold(s, t)) / len(shown)) if shown else None
    out["citation_support"] = (sum(1 for _, t in shown if any(overlaps(n["quote"], t) or overlaps(t, n["quote"])
                                                              for n in nuggets)) / len(shown)) if shown else None
    nums = []
    for kind, vals in (ref.get("slots") or {}).items():
        for v in vals if isinstance(vals, list) else [vals]:
            if isinstance(v, dict):
                nums += [n.strip(".,") for n in re.findall(r"\d[\d,.]*", f"{v.get('value', '')} {v.get('amount', '')}")]
    blob = " ".join(_norm(t) for _, t in shown)
    out["slot_match"] = (sum(1 for n in nums if n and R.has_num(n, blob)) / len(nums)) if nums else None
    # the local model's plain-language claims: which vital nuggets they carry (through the quotes they cite); a
    # summary whose claims were all dropped counts too (no claims, no vital nuggets)
    summ = ans.get("summary")
    if isinstance(summ, dict):
        claims = summ.get("claims") or []
        qtext = {q["id"]: q["text"] for q in ans.get("quotes") or []}
        cited = [qtext[i] for c in claims for i in c["quotes"] if i in qtext]
        out["claims"] = len(claims)
        out["claims_dropped"] = len(summ.get("dropped") or [])
        out["claim_vital_recall"] = (sum(1 for n in vital if covered(n["quote"], cited)) / len(vital)
                                     if vital else None)
    out["steps_equivalence"] = None
    if ref.get("steps") and row.get("facts"):
        from ..extract.benchmark import equivalence
        from ..extract.schema import LegalProcessFacts
        try:
            gold_f = LegalProcessFacts.model_validate(ref["steps"])
            cand = LegalProcessFacts.model_validate(json.loads(row["facts"]) if isinstance(row["facts"], str)
                                                    else row["facts"])
            out["steps_equivalence"] = equivalence(cand, gold_f)["value"]
        except Exception:  # noqa: BLE001 - an unparsable candidate scores 0
            out["steps_equivalence"] = 0.0
    elif ref.get("steps"):
        out["steps_equivalence"] = 0.0
    if ref["coverage"] == "not_in_code":
        # nothing to retrieve or quote: the case is about declining
        out["composite"] = out["gate_correct"]
    else:
        core = out["steps_equivalence"] if ref.get("question_type") == "process" and ref.get("steps") \
            else (out["vital_recall"] or 0.0)
        comp = {"core": core, "citation_precision": out["citation_precision"] or 0.0,
                "recall@10": out["recall@10"] or 0.0, "slot_match": out["slot_match"],
                "gate_correct": out["gate_correct"]}
        weights = {"core": 0.35, "citation_precision": 0.2, "recall@10": 0.15, "slot_match": 0.15, "gate_correct": 0.15}
        have = {k: v for k, v in comp.items() if v is not None}
        out["composite"] = round(sum(weights[k] * v for k, v in have.items()) / sum(weights[k] for k in have), 4)
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}


def run(con, arms: tuple[str, ...] = ("local", "oracle"), cases: list[tuple[str, str]] | None = None, log=print,
        use_llm: bool = False, llm_plan: bool = False) -> list[dict]:
    """``use_llm``: the local model plans the search and writes the summary; ``llm_plan``: it plans only (one
    short call per question, shared by every state), the answer is the quotes and steps."""
    from . import relevance as RV
    from . import retrieve as RT
    from .pipeline import answer_state, asker_for, embedder
    from .plan import plan as make_plan
    cases = R.cases() if cases is None else cases
    ver = version()
    try:
        emb = embedder()
    except Exception:  # noqa: BLE001
        emb = None
    asker = asker_for(None) if (use_llm or llm_plan) else None
    planner, asker = asker, (asker if use_llm else None)
    plans: dict[str, object] = {}
    rows = []
    for qid, state in cases:
        ref = R.load(qid, state)
        if qid not in plans:                       # one plan per question, as the ask pipeline does
            plans[qid] = make_plan(ref["question"], planner)
        p = plans[qid]
        for arm in arms:
            t0 = time.time()
            oracle_refs = [g["ref"] for g in ref.get("gold_sections") or []] if arm == "oracle" else None
            if arm == "oracle" and not oracle_refs:
                continue
            plan_used = p
            if arm == "profile":                       # Claude's own search concepts: what planning loses
                from .plan import Plan, kind_of
                plan_used = Plan(text=ref["question"], groups=ref["profile"]["groups"], kind=kind_of(ref["question"]),
                                 source="claude-profile")
            # heuristic: the same pipeline without the learned reranker; oracle does not retrieve
            model, reranker = held_out(qid) if arm not in ("heuristic", "oracle") else (None, "none")
            RT.USE_LEARNED, RV.OVERRIDE = model is not None, model
            try:
                row = answer_state(con, f"bench_{qid}", plan_used, state, asker=asker, emb=emb, store=False,
                                   oracle_refs=oracle_refs, log=lambda *_: None)
            finally:
                RT.USE_LEARNED, RV.OVERRIDE = True, None
            s = score(ref, row)
            # without its held-out model the arm is the heuristic one: stored apart, so it never passes for the arm
            s.update(arm=arm + ("-unlearned" if reranker in ("missing", "stale") else "")
                     + ("+llm" if asker else "+llmplan" if planner else ""),
                     reranker=reranker, version=ver, seconds=round(time.time() - t0, 1))
            rows.append(s)
            db.upsert(con, "ask_bench", [{"case_id": s["case"], "arm": s["arm"], "metrics": json.dumps(s),
                                               "ref_hash": R.hash_of(ref), "created_at": db.now()}],
                      keys=("case_id", "arm"), stamp=False)
            con.commit()
            log(f"{s['case']:<28} {s['arm']:<10} composite {s['composite']:.3f} · recall@10 {s['recall@10']} · "
                f"vital {s['vital_recall']} · cite {s['citation_precision']} · slots {s['slot_match']} · "
                f"steps {s['steps_equivalence']} · gate {s['gate_correct']} ({s['status']}) · {s['seconds']}s"
                + (f" · held-out reranker {reranker}: run scripts/train_relevance.py" if model is None
                   and reranker != "none" else ""))
    return rows


def held_out(qid: str) -> tuple[dict | None, str]:
    """The reranker trained without this question (a question is never scored with a model trained on it) and
    'loqo'; or None and 'missing' (not trained yet) or 'stale' (unreadable, or other features than relevance's)."""
    from . import relevance as RV
    p = RV.loqo_path(qid)
    if not p.exists():
        return None, "missing"
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None, "stale"
    return (m, "loqo") if isinstance(m, dict) and m.get("features") == RV.FEATURES else (None, "stale")


def agreement(a: dict, b: dict) -> dict:
    """How far two independent reference answers to the same case agree (the Claude-vs-Claude ceiling): the same
    sections, each other's vital nuggets, the same slot numbers, the same coverage call, the same steps."""
    state = a["state"]
    ga, gb = _ids(state, [g["ref"] for g in a.get("gold_sections") or []]), \
        _ids(state, [g["ref"] for g in b.get("gold_sections") or []])
    fa, fb = set().union(*ga) if ga else set(), set().union(*gb) if gb else set()
    sections = len(fa & fb) / len(fa | fb) if fa | fb else 1.0

    def covers(x, y):
        vital = [n for n in x.get("nuggets") or [] if n["importance"] == "vital"]
        quotes = [n["quote"] for n in y.get("nuggets") or []]
        return sum(1 for n in vital if covered(n["quote"], quotes)) / len(vital) if vital else None
    ca, cb = covers(a, b), covers(b, a)
    nuggets = st.mean([v for v in (ca, cb) if v is not None]) if (ca is not None or cb is not None) else None

    def nums(x):
        out = set()
        for vals in (x.get("slots") or {}).values():
            for v in vals if isinstance(vals, list) else [vals]:
                if isinstance(v, dict):
                    out |= {n.strip(".,") for n in re.findall(r"\d[\d,.]*", f"{v.get('value', '')} {v.get('amount', '')}")}
        return out
    na, nb = nums(a), nums(b)
    slots = len(na & nb) / len(na | nb) if na | nb else None
    steps = None
    if a.get("steps") and b.get("steps"):
        from ..extract.benchmark import equivalence
        from ..extract.schema import LegalProcessFacts
        fa_, fb_ = LegalProcessFacts.model_validate(a["steps"]), LegalProcessFacts.model_validate(b["steps"])
        steps = (equivalence(fa_, fb_)["value"] + equivalence(fb_, fa_)["value"]) / 2
    elif a.get("steps") or b.get("steps"):     # one draft found a process the other did not, as score() counts it
        steps = 0.0
    parts ={"sections": sections, "vital_nuggets": nuggets, "slots": slots,
             "coverage": float(a["coverage"] == b["coverage"]), "steps": steps}
    have = [v for v in parts.values() if v is not None]
    return {"case": f"{a['qid']}.{state}", **{k: (round(v, 3) if v is not None else None) for k, v in parts.items()},
            "mean": round(st.mean(have), 3) if have else None}


def ceiling() -> list[dict]:
    """Agreement of every second draft in curated_ask_alt/ with its first draft; a draft that does not pass the
    reference checks (or cannot be compared) is skipped with a note."""
    out = []
    for qid, state in R.cases(alt=True):
        try:
            alt = R.load(qid, state, alt=True)
            chk = R.check(alt, qid, state)
            if not chk["ok"]:
                out.append({"case": f"{qid}.{state}", "error": "; ".join(chk["problems"][:3])[:300]})
                continue
            out.append(agreement(R.load(qid, state), alt))
        except Exception as e:  # noqa: BLE001 - one bad draft must not stop docs/askbench.json being written
            out.append({"case": f"{qid}.{state}", "error": f"{type(e).__name__}: {str(e)[:200]}"})
    return out


def stored(con) -> tuple[list[dict], dict]:
    """The stored rows of the current code and metrics (version()), each scored against the current version of its
    reference, and how many were left out for either reason."""
    current = {f"{q}.{s}": R.hash_of(R.load(q, s)) for q, s in R.cases()}
    ver = version()
    rows, excluded = [], {"stale_reference": 0, "stale_code": 0}
    for r in db.rows(con, "SELECT metrics, ref_hash, case_id FROM ask_bench"):
        m = json.loads(r["metrics"] or "{}")
        if current.get(r["case_id"]) != r["ref_hash"]:
            excluded["stale_reference"] += 1
        elif m.get("version") != ver:
            excluded["stale_code"] += 1
        else:
            rows.append(m)
    return rows, excluded


def summary(rows: list[dict]) -> dict:
    """Each arm's means over its own rows, with how many cases (and which) they cover: arms differ in coverage."""
    keys = ("composite", "recall@5", "recall@10", "primary_chosen", "mrr", "vital_recall", "nugget_recall",
            "claim_vital_recall", "claims", "claims_dropped",
            "citation_precision", "citation_support", "slot_match", "steps_equivalence", "gate_correct")
    out = {}
    for arm in sorted({r["arm"] for r in rows}):
        rs = [r for r in rows if r["arm"] == arm]
        out[arm] = {"cases": len(rs), "case_ids": sorted(r["case"] for r in rs),
                    **{k: round(st.mean(v), 3) if (v := [r[k] for r in rs if r.get(k) is not None]) else None
                       for k in keys}}
    return out
