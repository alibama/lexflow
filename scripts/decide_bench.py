"""Benchmark: the current rules vs an embedding classifier vs a decision model, on lexflow's own labelled data.

    python scripts/decide_bench.py [--tasks step_kind,xref_role,topic,unit_level,mailbox] [--max-decisions 150]
                                   [--no-decide] [--no-embed] [--json PATH] [--write-doc] [--seed 7]

Run it where the data is (the app container, read-only on the live store and the statute index):

    MSYS_NO_PATHCONV=1 docker exec -i -w /app lexflow-app-1 python scripts/decide_bench.py --write-doc

Tasks (each >= 100 labelled examples, a deterministic 70/30 split by a hash of the state text):
  step_kind   steps[].kind of the reviewed process models (process_models tier reviewed/agreed); state = the
              step's action and its source quote.  Rule: lexflow.extract.strategies.kind_of (verb lists).
  xref_role   the role of a cross-reference, from the hand-labelled gold (fixtures/xref/gold_*.json); state = the
              citing sentence with the reference marked.  Rule: lexflow.law.xref.role_of (cue words).
  topic       the topic vocabulary slug of a process: place processes (place_processes.category through
              schema.CATEGORY_TOPIC) and the state models (their question id through schema.QUESTION_TOPIC);
              state = title + question.  "Rule": the lookup itself, which needs the category field the other arms
              do not see, so it is a ceiling (100% by construction), not a competitor.
  unit_level  the unit-level slug of a statutory unit from the index path ("Title 2.2 / Subtitle II / Chapter 37");
              label = schema.unit_level(path word, act_id token), what the publish step writes.  Rule:
              schema.unit_level on the path word alone (the token's level letter is withheld from every arm).
  mailbox     office (role-shaped) vs personal mailbox, synthetic made-up addresses at RFC 2606 example domains
              built from privacy.py's own vocabulary and placeholder names.  Rule: privacy.mailbox_shape.

Arms:
  (a) rules    the code lexflow uses today for that task (see above), timed per decision.
  (b) embed    nomic-embed-text vectors (Ollama /api/embed), fit on the train split: kNN (k=5, cosine, distance
               weighted) and nearest centroid; the per-decision time includes embedding the test text.
  (c) decide   lexflow.extract.decide.Decider: the decision model through /v1/systemone when backend() finds one,
               else the chat fallback (qwen3:1.7b, JSON schema), reported as arm (c') and labelled as the slow
               fallback.  Capped at --max-decisions over all tasks (sampled deterministically from the test split).

Reports accuracy, macro-F1, ms per decision and the commonest confusions, one table; --write-doc puts the table
and the per-task details into docs/design/decision-models.md between its result markers; --json keeps everything.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import config  # noqa: E402
from lexflow.extract import decide as D  # noqa: E402
from lexflow.publish import schema as SC  # noqa: E402

DOC = ROOT / "docs" / "design" / "decision-models.md"
BEGIN, END = "<!-- decide_bench:begin -->", "<!-- decide_bench:end -->"
TEST_SHARE = 30                 # percent of each task held out, by hash


# --------------------------------------------------------------------------- examples and tasks
@dataclass
class Example:
    state: str
    label: str
    meta: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        return hashlib.sha256(self.state.encode("utf-8")).hexdigest()

    @property
    def is_test(self) -> bool:
        return int(self.key[:8], 16) % 100 < TEST_SHARE


@dataclass
class Task:
    name: str
    labels: list[str]
    question: dict                     # the decide() questions (one question, named "answer")
    rule: callable                     # Example -> label
    rule_name: str
    examples: list[Example]
    note: str = ""

    @property
    def train(self) -> list[Example]:
        return [e for e in self.examples if not e.is_test]

    @property
    def test(self) -> list[Example]:
        return [e for e in self.examples if e.is_test]


def _vocab(set_name: str, only: list[str] | None = None) -> dict[str, str]:
    crit = {v.slug: v.description for v in SC.VOCAB[set_name]}
    if only:
        crit = {k: crit.get(k, k) for k in only}
    return crit


def _ro(path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)


# ---- (1) step kind
STEP_KINDS = ["act", "notice", "filing", "hearing", "decision", "payment", "inspection", "record", "review"]


def load_step_kind(db_path=None) -> Task:
    from lexflow.extract.strategies import kind_of
    con = _ro(db_path or config.DB_PATH)
    try:
        rows = con.execute("SELECT model_id, facts FROM process_models WHERE tier IN ('reviewed','agreed') "
                           "AND facts IS NOT NULL ORDER BY model_id").fetchall()
    finally:
        con.close()
    ex = []
    for model_id, facts in rows:
        d = json.loads(facts)
        for s in d.get("steps", []):
            kind = s.get("kind")
            if kind not in STEP_KINDS:
                continue
            quote = ((s.get("source") or {}).get("quote") or "").strip()
            state = f"Step: {s.get('action', '').strip()}\nLaw: {quote}"
            ex.append(Example(state, kind, {"model": model_id, "step": s.get("id")}))
    q = {"answer": {"type": "choice", "instructions": "Which kind of legal process step is this? Judge by what "
                                                      "the actor does.", "criteria": _vocab("step-kind", STEP_KINDS)}}
    return Task("step_kind", STEP_KINDS, q, lambda e: kind_of(e.state.split("\n", 1)[0][6:]),
                "extract.strategies.kind_of", ex, "reviewed models' steps; state = action + source quote")


# ---- (2) cross-reference role
def _sentence(text: str, start: int, end: int) -> str:
    """The sentence of ``text`` around [start, end), with the reference marked ``[[...]]``."""
    left = text[:start]
    m = list(re.finditer(r"(?<!\d)[.;:]\s+|\n\s*\n|\n(?=\s*\(?[A-Za-z0-9]{1,4}[.)]\s)", left))
    s0 = m[-1].end() if m else 0
    m2 = re.search(r"(?<!\d)[.;]\s+|\n\s*\n|\n(?=\s*\(?[A-Za-z0-9]{1,4}[.)]\s)", text[end:])
    e0 = end + (m2.end() if m2 else min(len(text) - end, 400))
    s0 = max(s0, start - 600)
    sent = text[s0:start] + "[[" + text[start:end] + "]]" + text[end:e0]
    return " ".join(sent.split())


def load_xref_role(gold_dir: Path | None = None) -> Task:
    from lexflow.ask import index as I
    from lexflow.law import xref
    gold_dir = gold_dir or ROOT / "fixtures" / "xref"
    texts: dict[tuple[str, int], str] = {}
    ex = []
    skipped = 0
    for p in sorted(gold_dir.glob("gold_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for s in d["sections"]:
            st = s["state"]
            key = (st, s["id"])
            if key not in texts:
                rows = [r for r in I.lookup(st, s["citation"]) if r["citation"] == s["citation"]]
                texts[key] = I.text_of(st, rows[0]["id"]) if rows else ""
            text = texts[key]
            for r in s["references"]:
                role = r.get("role")
                if role not in xref.ROLES or not text or text[r["start"]:r["end"]] != r["span"]:
                    skipped += 1
                    continue
                state = "Sentence: " + _sentence(text, r["start"], r["end"]) + f"\nReference: {r['span']}"
                ex.append(Example(state, role, {"citation": s["citation"], "span": r["span"], "kind": r["kind"],
                                                "start": r["start"], "end": r["end"], "sec": key}))
    roles = list(xref.ROLES)
    q = {"answer": {"type": "choice", "instructions": "Why does the sentence cite the marked [[reference]]? What "
                                                      "role does the cited provision play for the citing rule?",
                    "criteria": _vocab("reference-type", roles)}}

    def rule(e: Example) -> str:
        m = e.meta
        return xref.role_of(texts[m["sec"]], m["start"], m["end"], m["kind"], {})[0]

    return Task("xref_role", roles, q, rule, "law.xref.role_of", ex,
                f"gold references with text in the index; {skipped} skipped (text drift or unknown role)")


# ---- (3) topic
def load_topic(db_path=None) -> Task:
    from lexflow.municipal import questions as Q
    con = _ro(db_path or config.DB_PATH)
    try:
        places = con.execute("SELECT gov_id, process, title, question, category FROM place_processes "
                             "ORDER BY gov_id, process").fetchall()
        models = con.execute("SELECT model_id, question, title FROM process_models ORDER BY model_id").fetchall()
    finally:
        con.close()
    ex = []
    for gov_id, process, title, question, category in places:
        topic = SC.CATEGORY_TOPIC.get(category or "")
        if not topic:
            continue
        ex.append(Example(f"Title: {title or process}\nQuestion: {question or ''}", topic,
                          {"category": category, "source": "place"}))
    for model_id, qid, title in models:
        topic = SC.QUESTION_TOPIC.get(qid)
        if not topic:
            continue
        ex.append(Example(f"Title: {title or model_id}\nQuestion: {Q.get(qid).title}", topic,
                          {"category": qid, "source": "model"}))
    topics = [v.slug for v in SC.VOCAB["topic"]]
    q = {"answer": {"type": "choice", "instructions": "Which topic does this government process belong to?",
                    "criteria": _vocab("topic")}}

    def rule(e: Example) -> str:
        c = e.meta["category"]
        return SC.CATEGORY_TOPIC.get(c) or SC.QUESTION_TOPIC.get(c) or "other"

    return Task("topic", topics, q, rule, "schema.CATEGORY_TOPIC/QUESTION_TOPIC lookup (sees the category: ceiling)",
                ex, "place processes + state models; unmapped place categories left out")


# ---- (4) unit level
UNIT_STATES = ("va", "ca", "ny", "il", "tx", "md", "fl", "wa", "nc", "dc", "mn", "oh", "mi", "pa", "nj", "ma")


def load_unit_level(index_dir: Path | None = None, per_state_label: int = 12) -> Task:
    from lexflow.ask import index as I
    index_dir = Path(index_dir) if index_dir else Path(I.index_dir())
    ex = []
    for st in UNIT_STATES:
        p = index_dir / f"statutes_{st}.sqlite"
        if not p.exists():
            continue
        con = _ro(p)
        try:
            rows = con.execute("SELECT path, act_id FROM sec").fetchall()
        finally:
            con.close()
        seen: dict[tuple, Example] = {}
        for path, act in rows:
            elems = (path or "").split(" / ")
            toks = SC.unit_tokens(act or "")
            if len(elems) < 3 or len(elems) != len(toks) + 1:
                continue
            for i, (el, tok) in enumerate(zip(elems[1:-1], toks[:-1]), 1):
                label = SC.unit_level(el, tok)
                if not label or (el, label) in seen:
                    continue
                tail = " / ".join(elems[max(1, i - 1):i + 1])            # the unit and the unit above it
                state = f"Unit: {el}\nPath: {elems[0]} / ... / {tail}" if i > 1 else f"Unit: {el}\nPath: {elems[0]} / {el}"
                seen[(el, label)] = Example(state, label, {"state": st, "token": tok})
        by_label: dict[str, list[Example]] = collections.defaultdict(list)
        for e in seen.values():
            by_label[e.label].append(e)
        for label, lst in by_label.items():
            lst.sort(key=lambda e: e.key)
            ex.extend(lst[:per_state_label])
    levels = [v.slug for v in SC.VOCAB["unit-level"]]
    q = {"answer": {"type": "choice", "instructions": "What level in the code's hierarchy is this unit?",
                    "criteria": _vocab("unit-level")}}
    return Task("unit_level", levels, q, lambda e: SC.unit_level(e.state.split("\n", 1)[0][6:], None) or "none",
                "publish.schema.unit_level (path word only)", ex,
                f"unique (unit, level) pairs, <= {per_state_label} per state and level, {len(UNIT_STATES)} states")


# ---- (5) office vs personal mailbox (synthetic)
GIVEN = ["jane", "john", "alex", "sam", "pat", "chris", "kim", "lee", "morgan", "taylor", "robin", "jordan"]
# placeholder surnames, the conventional "nobody in particular" names of several languages
SURNAMES = ["doe", "roe", "bloggs", "sample", "nemo", "fulano", "mustermann", "dupont", "rossi", "tanaka", "nguyen",
            "placeholder"]
ROLE_SINGLE = ["foia", "records", "publicrecords", "clerk", "permits", "info", "council", "planning", "zoning", "tax",
               "treasury", "elections", "licensing", "inquiries", "webmaster", "procurement", "assessor", "opra",
               "pia", "help", "contact", "business", "revenue", "finance", "utilities", "housing"]
ROLE_PAIRS = [("public", "records"), ("records", "request"), ("foia", "appeals"), ("business", "license"),
              ("tax", "office"), ("city", "clerk"), ("county", "clerk"), ("permits", "desk"), ("open", "records"),
              ("info", "desk"), ("board", "appeals"), ("zoning", "board"), ("voter", "registration"),
              ("help", "desk"), ("customer", "service"), ("building", "permits"), ("police", "records")]
# office-looking addresses the whole-token rule cannot account for (not in its vocabulary): labelled office
ROLE_HARD = ["cityhall", "mayorsoffice", "townoffice", "frontdesk", "ourtown", "villageoffice", "countyexec",
             "sunshinelaw", "openmeetings", "recordscenter", "gis", "311", "dpw", "dmv", "ocr"]
DOMAINS = ["example.gov", "example.org", "example.com", "cityof.example.org", "county.example.net"]


def load_mailbox(n_per_label: int = 90) -> Task:
    from lexflow.privacy import mailbox_shape
    ex: list[Example] = []
    rng_i = 0

    def pick(lst):
        nonlocal rng_i
        rng_i += 1
        return lst[(rng_i * 7919) % len(lst)]

    office: list[tuple[str, str]] = []
    for w in ROLE_SINGLE:
        office.append((w, "Example City"))
    for a, b in ROLE_PAIRS:
        office += [(f"{a}.{b}", "Example County"), (f"{a}{b}", "Example City"), (f"{a}_{b}", "Example Town")]
    office += [(f"{w}{d}", "Example Village") for w, d in zip(ROLE_SINGLE, (2, 2024, 1, 3, 2))]
    office += [("mpd", "Metropolitan Police Department"), ("bmza", "Board of Municipal and Zoning Appeals"),
               ("dhcd.pia", "Department of Housing and Community Development"), ("CorpHelp", "Division of Corporations"),
               ("FOIARequests", "Example City"), ("OpenRecords", "Example County")]
    office += [(w, "Example City") for w in ROLE_HARD]
    personal: list[tuple[str, str]] = []
    for g in GIVEN:
        for s in SURNAMES[:4]:
            personal.append((f"{g}.{s}", "Example City"))
    for g, s in zip(GIVEN, SURNAMES):
        personal += [(f"{g[0]}{s}", "Example County"), (f"{s}{g[0]}", "Example Town"), (f"{g}{s}77", "Example City"),
                     (f"{s}.{g}", "Example Village"), (f"{g}_{s}", "Example County"), (f"{g}.{s}.records", "Example City"),
                     (f"{s}", "Example City"), (f"{g}", "Example Town"), (f"{g}{s[0]}", "Example County")]
    personal += [("mayor", "Example City"), ("director", "Example County"), ("treasurer", "Example Town"),
                 ("clerk.jdoe", "Example City"), ("foia.jdoe", "Example County"), ("sheriff", "Example County"),
                 ("cc", "City of Charlottesville"), ("jd", "Example City")]
    for label, pool in (("office", office), ("personal", personal)):
        pool = sorted(set(pool))
        pool.sort(key=lambda t: hashlib.sha256(t[0].encode()).hexdigest())
        for local, owner in pool[:n_per_label]:
            addr = f"{local}@{pick(DOMAINS)}"
            ex.append(Example(f"Address: {addr}\nOffice: {owner}", label, {"owner": owner, "address": addr}))
    q = {"answer": {"type": "noul", "instructions": "Is this e-mail address an office's general mailbox (a role "
                                                    "address such as records@ or clerk@) rather than a named "
                                                    "person's own mailbox? Answer yes for an office mailbox."}}

    def rule(e: Example) -> str:
        return "office" if mailbox_shape(e.meta["address"], e.meta["owner"]) == "role" else "personal"

    return Task("mailbox", ["office", "personal"], q, rule, "privacy.mailbox_shape", ex,
                "synthetic: role words, pairs and initialisms vs placeholder names; example.* domains only")


LOADERS = {"step_kind": load_step_kind, "xref_role": load_xref_role, "topic": load_topic,
           "unit_level": load_unit_level, "mailbox": load_mailbox}


# --------------------------------------------------------------------------- metrics
def metrics(golds: list[str], preds: list[str], labels: list[str]) -> dict:
    n = len(golds)
    acc = sum(g == p for g, p in zip(golds, preds)) / n if n else 0.0
    f1s = []
    for lab in labels:
        tp = sum(g == lab and p == lab for g, p in zip(golds, preds))
        fp = sum(g != lab and p == lab for g, p in zip(golds, preds))
        fn = sum(g == lab and p != lab for g, p in zip(golds, preds))
        if tp + fp + fn == 0:
            continue                                   # the label is absent from both: not scored
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    conf = collections.Counter((g, p) for g, p in zip(golds, preds) if g != p)
    return {"n": n, "accuracy": round(acc, 4), "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
            "confusions": [{"gold": g, "pred": p, "count": c} for (g, p), c in conf.most_common(3)]}


def _confusion_text(m: dict) -> str:
    return "; ".join(f"{c['gold']}->{c['pred']} x{c['count']}" for c in m["confusions"]) or "-"


# --------------------------------------------------------------------------- arms
def run_rule(task: Task, examples: list[Example]) -> dict:
    t0 = time.perf_counter()
    preds = [task.rule(e) for e in examples]
    sec = time.perf_counter() - t0
    m = metrics([e.label for e in examples], preds, task.labels)
    return {**m, "arm": "(a) rules", "detail": task.rule_name, "seconds": round(sec, 3),
            "ms_per_decision": round(sec * 1000 / max(1, len(examples)), 3), "preds": preds}


def embed_texts(texts: list[str], model: str, base_url: str, batch: int = 32) -> tuple[list[list[float]], float]:
    import requests
    out: list[list[float]] = []
    t0 = time.perf_counter()
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        r = requests.post(base_url.rstrip("/") + "/api/embed", json={"model": model, "input": chunk}, timeout=600)
        r.raise_for_status()
        out.extend(r.json()["embeddings"])
    return out, time.perf_counter() - t0


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def run_embed(task: Task, train: list[Example], test: list[Example], model: str, base_url: str, k: int = 5) -> dict:
    tr_vecs, tr_sec = embed_texts([e.state for e in train], model, base_url)
    te_vecs, te_sec = embed_texts([e.state for e in test], model, base_url)
    tr_vecs = [_unit(v) for v in tr_vecs]
    te_vecs = [_unit(v) for v in te_vecs]
    t0 = time.perf_counter()
    cents: dict[str, list[float]] = {}
    for e, v in zip(train, tr_vecs):
        c = cents.setdefault(e.label, [0.0] * len(v))
        for i, x in enumerate(v):
            c[i] += x
    cents = {lab: _unit(c) for lab, c in cents.items()}
    knn_preds, cent_preds = [], []
    for v in te_vecs:
        sims = sorted(((_dot(v, tv), e.label) for e, tv in zip(train, tr_vecs)), reverse=True)[:k]
        votes: dict[str, float] = collections.defaultdict(float)
        for s, lab in sims:
            votes[lab] += max(s, 1e-6)
        knn_preds.append(max(votes, key=votes.get) if votes else "none")
        cent_preds.append(max(cents, key=lambda lab: _dot(v, cents[lab])) if cents else "none")
    cls_sec = time.perf_counter() - t0
    golds = [e.label for e in test]
    per = (te_sec + cls_sec) * 1000 / max(1, len(test))
    knn = {**metrics(golds, knn_preds, task.labels), "arm": "(b) embed kNN", "detail": f"{model}, k={k}, "
           f"train n={len(train)}", "seconds": round(tr_sec + te_sec + cls_sec, 2), "fit_seconds": round(tr_sec, 2),
           "ms_per_decision": round(per, 1), "preds": knn_preds}
    cent = {**metrics(golds, cent_preds, task.labels), "arm": "(b') embed centroid", "detail": f"{model}, nearest "
            f"centroid, train n={len(train)}", "seconds": round(tr_sec + te_sec + cls_sec, 2),
            "fit_seconds": round(tr_sec, 2), "ms_per_decision": round(per, 1), "preds": cent_preds}
    return {"knn": knn, "centroid": cent}


def run_decide(task: Task, examples: list[Example], decider: D.Decider) -> dict:
    preds, ms_list, errors = [], [], 0
    try:                                           # a warm-up call (model load) kept out of the timing
        tw = time.perf_counter()
        decider.decide("warm-up: a short text that is not an example", task.question)
        warm_ms = round((time.perf_counter() - tw) * 1000, 1)
    except D.DecisionError as ex:
        warm_ms = None
        print(f"  warm-up failed: {ex}", file=sys.stderr)
    t0 = time.perf_counter()
    for e in examples:
        try:
            out = decider.decide(e.state, task.question)
            a = out["answers"]["answer"]
            if a["type"] == "noul":
                pred = ("office" if a["choice"] else "personal") if a["choice"] is not None else "none"
            else:
                pred = a["choice"] or "none"
            ms_list.append(out.get("ms", 0.0))
        except D.DecisionError as ex:
            errors += 1
            pred = "none"
            print(f"  decide error: {ex}", file=sys.stderr)
        preds.append(pred)
    sec = time.perf_counter() - t0
    fallback = decider.is_fallback
    arm = "(c') chat fallback [slow]" if fallback else "(c) decision model"
    m = metrics([e.label for e in examples], preds, task.labels)
    return {**m, "arm": arm, "detail": f"{decider.model}" + (" via /api/chat + JSON schema" if fallback else
                                                           " via /v1/systemone"),
            "seconds": round(sec, 1), "ms_per_decision": round(sum(ms_list) / len(ms_list), 1) if ms_list else None,
            "ms_wall_per_decision": round(sec * 1000 / max(1, len(examples)), 1), "errors": errors,
            "fallback": fallback, "warm_up_ms": warm_ms, "preds": preds}


# --------------------------------------------------------------------------- reporting
def table(results: dict) -> str:
    L = ["| task | n test | arm | accuracy | macro-F1 | ms/decision | arm time | top confusions |",
         "|---|---:|---|---:|---:|---:|---:|---|"]
    for name, r in results.items():
        for a in r["arms"]:
            ms = a.get("ms_per_decision")
            ms_s = "-" if ms is None else (f"{ms:.3f}" if ms < 1 else f"{ms:,.0f}")
            L.append(f"| {name} | {a['n']} | {a['arm']} | {a['accuracy'] * 100:.1f} | {a['macro_f1'] * 100:.1f} | "
                     f"{ms_s} | {a['seconds']:.1f} s | {_confusion_text(a)} |")
    return "\n".join(L)


def details(results: dict, backend_info: dict) -> str:
    L = [f"Backend seen by `decide.backend()` at `{backend_info.get('url', '?')}`: kind `{backend_info['kind']}`, "
         f"model `{backend_info['model']}`; tags pulled: {', '.join(backend_info.get('models') or []) or 'none'}.", ""]
    for name, r in results.items():
        L.append(f"- **{name}**: {r['n_total']} examples ({r['n_train']} train / {r['n_test']} test), labels "
                 f"{', '.join(f'{k} {v}' for k, v in r['label_counts'].items())}. Rule: `{r['rule']}`. {r['note']}.")
        for a in r["arms"]:
            extra = ""
            if a.get("fit_seconds") is not None:
                extra = f"; embedding the train split took {a['fit_seconds']} s"
            if a.get("errors"):
                extra += f"; {a['errors']} errors"
            if a.get("warm_up_ms") is not None:
                extra += f"; warm-up call {a['warm_up_ms']} ms, left out of the timing"
            if a.get("ms_wall_per_decision") is not None:
                extra += f"; {a['ms_wall_per_decision']} ms wall per decision including the cache"
            L.append(f"  - {a['arm']}: {a['detail']}; n={a['n']}, accuracy {a['accuracy'] * 100:.1f}, macro-F1 "
                     f"{a['macro_f1'] * 100:.1f}, {a['seconds']} s{extra}.")
    return "\n".join(L)


ARM_ORDER = ["(a) rules", "(b) embed kNN", "(b') embed centroid", "(c) decision model", "(c') chat fallback [slow]",
             "(a) rules, same sample", "(b) embed kNN, same sample", "(b') embed centroid, same sample"]


def merge(prior: dict, current: dict) -> dict:
    """``prior``'s tasks and arms, with ``current``'s arms replacing those of the same name, in ARM_ORDER."""
    out = {}
    for name in list(prior) + [n for n in current if n not in prior]:
        p, c = prior.get(name), current.get(name)
        if p and c:
            arms = {a["arm"]: a for a in p["arms"]}
            arms.update({a["arm"]: a for a in c["arms"]})
            merged = {**p, **c, "arms": sorted(arms.values(), key=lambda a: (ARM_ORDER.index(a["arm"])
                                                                            if a["arm"] in ARM_ORDER else 99))}
        else:
            merged = p or c
        out[name] = merged
    return out


def render(results: dict, backends, stamp: str, budget) -> str:
    if isinstance(backends, dict):
        backends = [backends]
    head = f"Run: {stamp}; {len(results)} tasks; chat-fallback budget {budget} decisions in all."
    return f"{head}\n\n{table(results)}\n\n" + "\n\n".join(details(results, b) if i == 0 else _backend_line(b)
                                                          for i, b in enumerate(backends))


def _backend_line(b: dict) -> str:
    return (f"Later run, backend seen by `decide.backend()` at `{b.get('url', '?')}`: kind `{b['kind']}`, model "
            f"`{b['model']}`; tags pulled: {', '.join(b.get('models') or []) or 'none'}.")


def write_doc(text: str) -> None:
    if not DOC.exists():
        raise SystemExit(f"{DOC} does not exist: write it first, with the markers {BEGIN} ... {END}")
    doc = DOC.read_text(encoding="utf-8")
    if BEGIN not in doc or END not in doc:
        raise SystemExit(f"{DOC} has no {BEGIN} / {END} markers")
    head, rest = doc.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    DOC.write_text(head + BEGIN + "\n" + text.rstrip() + "\n" + END + tail, encoding="utf-8")


# --------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tasks", default=",".join(LOADERS), help="comma-separated task names")
    ap.add_argument("--max-decisions", type=int, default=150,
                    help="total chat-fallback calls over all tasks (a real decision model runs the full test sets)")
    ap.add_argument("--cap-decision-model", action="store_true", help="apply --max-decisions to the decision model too")
    ap.add_argument("--decide-url", default=D.DECIDE_URL, help="the Ollama that serves decisions (LEXFLOW_DECIDE_URL)")
    ap.add_argument("--force-fallback", action="store_true",
                    help="run arm (c') with the chat fallback even when a decision model is pulled")
    ap.add_argument("--merge", default=None, help="a previous --json file: its arms are kept where this run has none")
    ap.add_argument("--doc-from", default=None, help="only render the doc block from this --json file")
    ap.add_argument("--no-decide", action="store_true", help="skip arm (c)")
    ap.add_argument("--no-embed", action="store_true", help="skip arm (b)")
    ap.add_argument("--embed-model", default=config.EMBED_MODEL)
    ap.add_argument("--decision-model", default=None, help="decision model tag (default: the first pulled)")
    ap.add_argument("--chat-model", default=None, help="the fallback chat model (default qwen3:1.7b)")
    ap.add_argument("--cache-dir", default=None, help="Decider cache directory (default LEXFLOW_DATA/cache/decide)")
    ap.add_argument("--json", default=None, help="write every number and prediction here")
    ap.add_argument("--write-doc", action="store_true", help=f"put the table into {DOC.relative_to(ROOT)}")
    args = ap.parse_args(argv)
    if args.doc_from:
        prior = json.loads(Path(args.doc_from).read_text(encoding="utf-8"))
        write_doc(render(prior["results"], prior.get("backends", prior["backend"]), prior.get("stamp", "?"),
                         prior.get("budget", "?")))
        print(f"wrote {DOC} from {args.doc_from}")
        return 0

    names = [t.strip() for t in args.tasks.split(",") if t.strip()]
    bad = [t for t in names if t not in LOADERS]
    if bad:
        raise SystemExit(f"unknown tasks {bad}; known: {list(LOADERS)}")
    backend_info = {"kind": "skipped", "model": None, "models": []}
    decider = None
    if not args.no_decide:
        backend_info = D.backend(args.decide_url, args.decision_model, args.chat_model)
        backend_info["url"] = args.decide_url
        if args.force_fallback and backend_info["kind"] == "decision":
            want = args.chat_model or D.FALLBACK_MODEL
            pulled = D.find_tag(want, backend_info["models"])
            if not pulled or D.is_decision_model(pulled):
                raise SystemExit(f"--force-fallback: the chat model {want!r} is not pulled")
            backend_info = {**backend_info, "kind": "chat", "model": pulled}
        print(f"backend: {backend_info['kind']} {backend_info['model']!r}; tags: {backend_info['models']}")
        if backend_info["kind"] == "none":
            print("no decision model and no chat model pulled: arm (c) skipped")
        else:
            decider = D.Decider(args.decision_model, args.chat_model, base_url=args.decide_url,
                                cache_dir=args.cache_dir, backend_info=backend_info)
    budget_each = max(1, args.max_decisions // max(1, len(names)))
    if decider is not None and not decider.is_fallback and not args.cap_decision_model:
        budget_each = 10 ** 9                       # the decision model is fast: every test example
    results: dict[str, dict] = {}
    for name in names:
        t0 = time.perf_counter()
        task = LOADERS[name]()
        train, test = task.train, task.test
        counts = collections.Counter(e.label for e in task.examples)
        print(f"\n== {name}: {len(task.examples)} examples ({len(train)} train / {len(test)} test), labels "
              f"{dict(counts)}; loaded in {time.perf_counter() - t0:.1f} s")
        if len(task.examples) < 100:
            print(f"   warning: fewer than 100 examples")
        arms = [run_rule(task, test)]
        print(f"   {arms[-1]['arm']}: acc {arms[-1]['accuracy']:.3f} f1 {arms[-1]['macro_f1']:.3f}")
        if not args.no_embed:
            try:
                emb = run_embed(task, train, test, args.embed_model, config.OLLAMA_URL)
                arms += [emb["knn"], emb["centroid"]]
                for a in arms[-2:]:
                    print(f"   {a['arm']}: acc {a['accuracy']:.3f} f1 {a['macro_f1']:.3f} {a['ms_per_decision']} ms")
            except Exception as e:                   # noqa: BLE001 - report, keep the other arms
                print(f"   embed arm failed: {e}", file=sys.stderr)
        if decider is not None:
            sample = sorted(test, key=lambda e: e.key)[:budget_each]
            # the same sample is what the rule and embedding arms are re-scored on, for a like-for-like line
            a = run_decide(task, sample, decider)
            print(f"   {a['arm']}: acc {a['accuracy']:.3f} f1 {a['macro_f1']:.3f} {a['ms_per_decision']} ms "
                  f"(n={a['n']}, {a['seconds']} s)")
            arms.append(a)
            if len(sample) < len(test):
                r = run_rule(task, sample)
                r["arm"] = "(a) rules, same sample"
                arms.append(r)
                for b in [x for x in arms if x["arm"].startswith("(b)")]:
                    idx = {e.key: i for i, e in enumerate(test)}
                    preds = [b["preds"][idx[e.key]] for e in sample]
                    m = metrics([e.label for e in sample], preds, task.labels)
                    arms.append({**b, **m, "arm": b["arm"] + ", same sample"})
        results[name] = {"n_total": len(task.examples), "n_train": len(train), "n_test": len(test),
                         "label_counts": dict(counts), "rule": task.rule_name, "note": task.note, "arms": arms}
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    backends = [backend_info]
    if args.merge and Path(args.merge).exists():
        prior = json.loads(Path(args.merge).read_text(encoding="utf-8"))
        results = merge(prior["results"], results)
        backends = prior.get("backends", [prior["backend"]]) + backends
        stamp = f"{prior.get('stamp', '?')} + {stamp}"
    tbl = table(results)
    print("\n" + tbl)
    if decider is not None:
        print(f"\ndecider stats: {decider.stats}")
    if args.json:
        Path(args.json).write_text(json.dumps({"backend": backend_info, "backends": backends, "results": results,
                                               "stamp": stamp, "budget": args.max_decisions}, indent=1,
                                              ensure_ascii=False), encoding="utf-8")
    if args.write_doc:
        write_doc(render(results, backends, stamp, args.max_decisions))
        print(f"\nwrote {DOC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
