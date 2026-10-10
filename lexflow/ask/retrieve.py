"""Find the sections of a state's code that answer a question.

1. **Weigh the concepts** by how many sections contain them (document frequency in the state's index): a concept
   no section uses is dropped, and a very common one ("person", "court") only adds to the ranking.
2. **Several searches, fused**: all core concepts in the heading, all anywhere, the two rarest anywhere, any
   concept in the heading, any anywhere.  Reciprocal-rank fusion rewards sections that rank well in several.
   Then the structure of the code: the sections the best hits cite, and every section of the chapters or
   articles that hold the best hits (on AskBench these two lift gold sections in the top 20 from 0.205 to 0.264
   and in the top 80 from 0.420 to 0.466).
3. **Rerank** the fused list by meaning: embedding similarity of the question to each section's heading and
   opening words, plus small structural signals (repealed and definitions sections down).
4. **Choose** the best section and those close to it, with its neighbours when they belong to the same procedure.
"""
from __future__ import annotations

import re

from . import index as I
from .plan import Plan

PASS_WEIGHT = {"title_all": 1.5, "all": 1.2, "procedure": 1.1, "rarest": 1.0, "facet": 0.9, "title_any": 0.9,
               "feedback": 0.8, "any": 0.6, "unit": 1.0, "cited": 0.8}
# for how-do-I questions: the words of a procedure a person starts (statutes say "petition", not "how to")
ACTION_TERMS = ["petition", "application", "apply", "file", "filing", "motion", "request", "procedure", "hearing"]
REPEALED = re.compile(r"\b(repealed|expired|reserved|transferred|renumbered)\b", re.I)
DEFINITIONS = re.compile(r"^\s*(definitions?|short title|purpose|applicability|construction)\b", re.I)


def document_frequency(state: str, group: list[str]) -> int:
    expr = I.match([group], "or")
    if not expr:
        return 0
    con = I.connect(state)
    try:
        return con.execute("SELECT count(*) FROM fts WHERE fts MATCH ?", (expr,)).fetchone()[0]
    except Exception:  # noqa: BLE001 - a malformed expression
        return 0
    finally:
        con.close()


def sections_count(state: str) -> int:
    con = I.connect(state)
    try:
        r = con.execute("SELECT value FROM meta WHERE key='sections'").fetchone()
        return int(r[0]) if r else 1
    finally:
        con.close()


def weigh(state: str, groups: list[list[str]]) -> list[dict]:
    """Each concept's document frequency in the state's code, most useful first: concepts with legal synonyms or
    phrases (the thesaurus's or a model's) before bare question words, rarest first within each.  A rare bare word
    ("instead", "afford") would otherwise become a required search term."""
    n = max(1, sections_count(state))
    out = []
    for g in groups:
        df = document_frequency(state, g)
        if df:
            legal = len(g) > 1 or " " in g[0]
            out.append({"terms": g, "df": df, "share": round(df / n, 4), "legal": legal})
    return sorted(out, key=lambda x: (not x["legal"], x["df"]))


# RM3-style pseudo-relevance feedback from the first search's top headings: off, it lowered recall on AskBench
# (gold sections in the top 80: 0.452 with facets alone, 0.444 with feedback too)
FEEDBACK = False
USE_LEARNED = True       # rerank with the trained section-relevance model when there is one
FACETS = True            # one sub-query per facet of a many-part question, each with the shared subject
# the cluster hypothesis for codes: a procedure's sections sit together in one chapter or article, and many of
# them never use the question's words ("within 30 days", "the clerk shall").  The units holding the best hits
# lend every one of their sections a vote, by the units' share of those hits.
UNITS = 3                # how many units (0: off)
UNIT_TOP = 20            # the hits that elect them
# and a procedure's details are often in the sections its main section cites ("as provided in § 19.2-305.1")
CITED_TOP = 10           # the best hits whose cross-references are followed (0: off)
_NUM = r"\d+[A-Za-z]?(?:[.:-](?:\d+[A-Za-z]?|[A-Za-z]\b))*"          # 19.2-305.1, 105-113.36A, 50-g
XREF = re.compile(rf"(?P<kw>§§?|\b[Ss]ections?|\b[Aa]rticles?)\s+(?P<nums>{_NUM}"
                  rf"(?:\s*(?:,|and|or|through)\s*{_NUM})*)")
XNUM = re.compile(_NUM)


def _code(r: dict) -> str:
    """The code a section is numbered in, from its citation without the number: '725 ILCS 5/', 'Cal. HSC § '."""
    cite = (r.get("citation") or "").split(";")[0].strip()          # 'A.R.S. § 13-1204; Version 2'
    if not cite:
        return " / ".join((r.get("path") or "").split(" / ")[:2])
    return re.sub(r"[\w.\-:,]+$", "", cite)


def cited(state: str, row: dict, limit: int = 12) -> list[dict]:
    """The sections one section cites, resolved in its own code (a bare number is ambiguous across codes)."""
    out, seen = [], {row["id"]}
    # 'Article 2' is a part of most codes, not a section; codes numbered in articles cite 'art. 2315'
    # (Louisiana) or 'Article 55.01' (Texas criminal procedure)
    articles = bool(re.search(r"\bart\.", row.get("citation") or "", re.I))
    for m in XREF.finditer(I.text_of(state, row["id"]) or ""):
        for n in XNUM.findall(m.group("nums")):
            if m.group("kw")[0] in "Aa" and not articles and not re.search(r"[.:-]", n):
                continue
            hits = I.lookup(state, n)
            same = [h for h in hits if _code(h) == _code(row)] or (hits if len(hits) == 1 else [])
            for h in same:
                if h["id"] not in seen:
                    seen.add(h["id"])
                    out.append(h)
            if len(out) >= limit:
                return out
    return out
HEADING_STOP = frozenset("""section sections chapter article title part subtitle general provisions definitions
definition purpose purposes applicability scope application thereof thereto herein hereunder such other
certain each any all and the for with from into upon under within without when where whose which that this
these those not nor but only also act acts code laws law state states person persons""".split())


def feedback_terms(rows: list[dict], plan: Plan, n_docs: int = 10, n_terms: int = 6) -> list[str]:
    """Words that recur in the headings of the best hits but are not in the question's concepts: the code's own
    vocabulary for the topic (Lavrenko & Croft's relevance model, on headings only, which are short and clean)."""
    import collections
    known = {w for g in plan.groups for t in g for w in re.findall(r"[a-z]+", t.lower())}
    counts = collections.Counter()
    for r in rows[:n_docs]:
        words = {w for w in re.findall(r"[a-z]{4,}", (r.get("title") or "").lower())
                 if w not in HEADING_STOP and w not in known}
        counts.update(words)
    return [w for w, c in counts.most_common(n_terms) if c >= 2]


def fused(state: str, plan: Plan, per_pass: int = 120) -> tuple[list[dict], list[dict]]:
    """Reciprocal-rank fusion of the searches.  Returns (sections, weighted concepts)."""
    w = weigh(state, plan.groups)
    if not w:
        return [], []
    core = [x["terms"] for x in w if x["share"] < 0.2] or [w[0]["terms"]]
    every = [x["terms"] for x in w]
    exprs = {"title_all": I.match(core[:3], "and", columns="title"), "all": I.match(core[:3], "and"),
             "procedure": I.match(core[:2] + [ACTION_TERMS], "and") if plan.kind in ("process", "either") else None,
             "rarest": I.match(core[:2], "and") if len(core) > 2 else None,
             "title_any": I.match(every, "or", columns="title"), "any": I.match(every, "or")}
    scores: dict[int, float] = {}
    rows: dict[int, dict] = {}

    def run(name, expr):
        for rank, r in enumerate(I.search(state, expr, limit=per_pass)):
            scores[r["id"]] = scores.get(r["id"], 0.0) + PASS_WEIGHT[name] / (60 + rank)
            rows.setdefault(r["id"], r).setdefault("passes", []).append(name)
    for name, expr in exprs.items():
        if expr:
            run(name, expr)
    # sub-queries for a question with several facets (payment plans, waivers, community service ...): each facet
    # with the question's broadest legal concept, the subject they share (fines and costs)
    legal = [x for x in w if x.get("legal") and x["share"] < 0.3]
    if FACETS and len(legal) >= 3:
        anchor = max(legal, key=lambda x: x["df"])["terms"]
        for f in [x["terms"] for x in legal if x["terms"] is not anchor][:4]:
            run("facet", I.match([anchor, f], "and"))
    if FEEDBACK and scores:
        first = [rows[i] for i, _ in sorted(scores.items(), key=lambda kv: -kv[1])]
        extra = feedback_terms(first, plan)
        if extra:
            # the code's own words for the topic, with the rarest concept, in the heading
            run("feedback", I.match([core[0], extra], "and", columns="title"))
    if CITED_TOP and scores:
        best = sorted(scores.items(), key=lambda kv: -kv[1])[:CITED_TOP]
        top = best[0][1]
        for sid, s in best:
            for r in cited(state, rows[sid]):
                scores[r["id"]] = scores.get(r["id"], 0.0) + PASS_WEIGHT["cited"] * (s / top) / 60
                rows.setdefault(r["id"], r).setdefault("passes", []).append("cited")
    if UNITS and scores:
        import collections
        mass = collections.Counter()
        for sid, s in sorted(scores.items(), key=lambda kv: -kv[1])[:UNIT_TOP]:
            mass[I.parent(rows[sid])] += s
        units = [u for u, _ in mass.most_common(UNITS) if u]
        top = max(mass.values()) if mass else 1.0
        for r in I.in_units(state, units):
            share = mass[I.parent(r)] / top
            scores[r["id"]] = scores.get(r["id"], 0.0) + PASS_WEIGHT["unit"] * share / 60
            rows.setdefault(r["id"], r).setdefault("passes", []).append("unit")
    out = []
    for sid, s in sorted(scores.items(), key=lambda kv: -kv[1]):
        r = rows[sid]
        r["rrf"] = round(s, 5)
        out.append(r)
    return out, w


def in_force(c: dict, as_of: str) -> int:
    """1 in force on as_of, 0 not yet in force, -1 expired (from '(Effective until ...)' style headings)."""
    if c.get("effective_until") and c["effective_until"] <= as_of:
        return -1
    if c.get("effective_from") and c["effective_from"] > as_of:
        return 0
    return 1


def rerank(question: str, cands: list[dict], embedder=None, as_of: str | None = None) -> list[dict]:
    """Order by fused rank and meaning.  Without an embedding model, by fused rank and structure only.
    Expired versions are dropped and versions not yet in force move down (they are kept, to be flagged)."""
    import datetime as dt
    import math
    as_of = as_of or dt.date.today().isoformat()
    cands = [c for c in cands if in_force(c, as_of) >= 0]
    if not cands:
        return []
    top = max(c["rrf"] for c in cands) or 1.0
    sims = [0.0] * len(cands)
    if embedder is not None:
        try:
            import numpy as np
            q = embedder([question], prefix="search_query")
            d = embedder([f"{c['title']}. {c['head'][:500]}" for c in cands], prefix="search_document")
            sims = list((d @ q.T)[:, 0])
            sims = [float(x) for x in np.asarray(sims)]
        except Exception:  # noqa: BLE001 - no embedding server: fused rank only
            sims = [0.0] * len(cands)
    for c, sim in zip(cands, sims):
        s = 0.55 * (c["rrf"] / top) + 0.45 * sim
        s += 0.02 * min(3.0, math.log10(max(10, c.get("words") or 10)))       # room for a procedure
        if "procedure" in (c.get("passes") or []):
            s += 0.03
        if REPEALED.search(c["title"] or "") or len((c.get("head") or "").split()) < 8:
            s -= 0.4
        if DEFINITIONS.match(c["title"] or ""):
            s -= 0.08
        if in_force(c, as_of) == 0:
            s -= 0.25
            c["version"] = f"not in force until {c['effective_from']}"
        c["similarity"] = round(sim, 4)
        c["rank_score"] = round(s, 4)
    return sorted(cands, key=lambda c: -c["rank_score"])


def choose(state: str, ranked: list[dict], k: int = 4, max_words: int = 6000, margin: float = 0.12) -> list[dict]:
    """The best section, others within reach of it, and its neighbours when they rank well too."""
    if not ranked:
        return []
    best = ranked[0]["rank_score"]
    chosen = [ranked[0]]
    near_ids = {n["id"] for n in I.neighbours(state, ranked[0]["id"], span=3)}
    for c in ranked[1:15]:
        if len(chosen) >= k:
            break
        close = c["rank_score"] >= best - margin
        neighbour = c["id"] in near_ids and c["rank_score"] >= best - 2 * margin
        if close or neighbour:
            chosen.append(c)
    words, out = 0, []
    for c in chosen:
        if out and words + (c["words"] or 0) > max_words:
            continue
        out.append(c)
        words += c["words"] or 0
    return out


def learned_order(ranked: list[dict], concepts: list[dict]) -> list[dict]:
    """Reorder by the learned section-relevance model (scripts/train_relevance.py) when one is trained; its
    probability becomes the rank score, so choose() and the answer gate work on it."""
    from . import relevance as RV
    p = RV.score(ranked, concepts) if USE_LEARNED else None
    if p is None:
        return ranked
    for c, pi in zip(ranked, p):
        c["heuristic_score"], c["rank_score"], c["relevance"] = c["rank_score"], round(float(pi), 4), round(float(pi), 4)
    return sorted(ranked, key=lambda c: -c["rank_score"])


def retrieve(state: str, plan: Plan, embedder=None, k: int = 4) -> dict:
    """Everything the answer step needs: the ranked candidates (for review) and the chosen sections."""
    if not I.ensure(state):
        return {"status": "no-statutes", "candidates": [], "chosen": [], "concepts": []}
    cands, weights = fused(state, plan)
    ranked = learned_order(rerank(plan.text, cands[:80], embedder), weights)
    chosen = choose(state, ranked, k=k, margin=0.35 if ranked and "relevance" in ranked[0] else 0.12)
    keep = ("id", "ref", "citation", "title", "chapter", "url", "words", "rrf", "similarity", "rank_score", "passes",
            "effective_from", "effective_until", "version", "relevance", "heuristic_score")
    return {"status": "found" if chosen else "not-found",
            "concepts": weights,
            "candidates": [{k_: c.get(k_) for k_ in keep} for c in ranked[:15]],
            "chosen": [{k_: c.get(k_) for k_ in keep} for c in chosen]}
