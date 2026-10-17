"""Ontology tags for every section of a state's statute index (``lexflow run ontology --states ...``).

Three tags per section, written to ``section_tags`` (one row per ``(state, ref)``; docs/design/legal-ontologies.md
section 3):

(a) **structure**, from the index row's ``path`` and ``act_id`` with rules and no model: the chain of levels from
    the code down to the section's own element, in the ``unit-level`` vocabulary plus the Akoma Ntoso names the
    vocabulary lacks (``book``, ``rule``), joined by ``/`` (``title/subtitle/chapter/article/section``).  The last
    token is the section's own Akoma Ntoso hierarchy element (``section``, or ``article`` for Louisiana's codes
    and Puerto Rico's ``Art.``); ``ontology_map.STRUCTURE_MATCH`` gives each token its AKN, ELI and USLM names.
(b) **norm_types**, which of the seven LKIF-style norm types the section carries (``ontology_map.NORM_TYPES``:
    definition, obligation, permission, prohibition, power, penalty, procedure).  ``rules`` finds them with cue
    phrases on the whole text (microseconds); the decision model (``lexflow.extract.decide``, ``tev1:0.8b``, or
    its chat fallback) answers seven ``noul`` questions on the section head plus the first 1,500 characters in one
    call, cached by the Decider.  ``method`` says which produced the row (``rules``, ``decision``, ``chat``,
    ``rules+decision``, ``rules+chat``); ``confidence`` keeps both sides (``{"rules": {...}, "model": {...}}``)
    so a threshold can be chosen afterwards without re-running anything.
(c) **eli**, the ELI-style identifier (``ontology_map.eli_uri``) from the act_id, stored in ``confidence``'s
    sibling column ``act_id`` plus the derived IRI in the row (``eli`` key of ``confidence``; the IRI is a pure
    function of ``act_id`` and ``state``, so the table does not need a column for it).

The table is local (``db.LOCAL_KEYS``), not ``SYNCED``: it is derived, large (1.7 million rows for the 47 states
with an index) and tied to this copy's index files, so it is rebuilt here rather than pushed through Turso.
``updated_at`` and ``origin`` are kept so that it can be promoted later without a migration.

Runs are resumable: a section already tagged by the same method is skipped unless ``force``; the job commits every
``BATCH`` rows and logs every state.  Model calls are paced (``pace`` seconds between calls) and capped
(``budget`` calls per run), since on this CPU one call is about 12 s: the endpoint encodes the state once per
question (docs/design/legal-ontologies.md section 4).
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from typing import Callable

from ..publish import ontology_map as OM
from ..store import db

Log = Callable[[str], None]

TABLE = "section_tags"
HEAD_CHARS = 1500            # characters of text the model sees after the head
BATCH = 500                  # rows per commit
NORM_TYPES = OM.NORM_TYPES

# --------------------------------------------------------------------------- (a) structure
# the first word of a path element -> level; the vocabulary's levels first (schema.unit_level), then the AKN names
# the vocabulary lacks
_EXTRA_LEVELS = {"libro": "book", "book": "book", "rule": "rule", "regla": "rule"}
_SECTION_WORDS = {"section", "sec", "§", "sección", "seccion"}
_ARTICLE_WORDS = {"article", "art", "artículo", "articulo"}


def _first_word(element: str) -> str:
    parts = (element or "").split()
    return re.sub(r"[.:]+$", "", parts[0]).lower() if parts else ""


def own_element(last_element: str, act_id: str) -> str:
    """The section's own Akoma Ntoso element from its path element (``Section 2.2-3704`` -> section,
    ``Art. 5.07`` -> article, ``Rule 3`` -> rule); the act_id's last token decides when the word is not a level
    (``A1112`` -> article)."""
    w = _first_word(last_element)
    if w in _SECTION_WORDS:
        return "section"
    if w in _ARTICLE_WORDS:
        return "article"
    if w in _EXTRA_LEVELS:
        return _EXTRA_LEVELS[w]
    from ..publish import schema as S
    toks = S.unit_tokens(act_id)
    if toks and toks[-1][:1] == "A" and toks[-1][1:2].isdigit():
        return "article"
    return "section"


def structure(path: str | None, act_id: str | None) -> str:
    """``title/subtitle/chapter/section``: every level between the code and the section, then the section's own
    element.  Levels come from the path's words (``Chapter 37``) or the act_id's letters (``SII`` -> subtitle);
    an element that is neither (a Puerto Rico ley's name) is an ``act``; unknown ones are dropped."""
    from ..publish import schema as S
    elements = [e for e in (path or "").split(" / ") if e.strip()]
    toks = S.unit_tokens(act_id or "")
    levels: list[str] = []
    inner = elements[1:-1] if len(elements) >= 2 else []
    # align act_id tokens with path elements: the tokens below the state, minus the section's own
    unit_toks = toks[:-1] if toks else []
    for i, el in enumerate(inner):
        tok = unit_toks[i] if i < len(unit_toks) else None
        w = _first_word(el)
        lvl = _EXTRA_LEVELS.get(w) or S.unit_level(el, tok)
        if lvl == "section":
            lvl = None
        if lvl:
            levels.append(lvl)
    own = own_element(elements[-1] if elements else "", act_id or "")
    return "/".join(levels + [own])


# --------------------------------------------------------------------------- (b) norm types: the rules
# cue phrases; each is a list of regexes any of which marks the type.  Case-insensitive on the whole text.
_RULES: dict[str, list[re.Pattern]] = {
    "definition": [re.compile(r'[“"][^“”"]{1,90}[”"]\s*(?:,\s*)?(?:means|shall\s+mean|has\s+the\s+(?:same\s+)?meaning|'
                              r'includes?|shall\s+include|does\s+not\s+include|refers\s+to)\b', re.I),
                   re.compile(r"\b(?:as\s+used\s+in\s+this|for\s+(?:the\s+)?purposes?\s+of\s+this|in\s+this)\s+"
                              r"(?:section|chapter|article|part|title|subchapter|act|code)\b[^.]{0,80}?\b(?:means|"
                              r"the\s+following\s+(?:terms|words|definitions))", re.I),
                   re.compile(r"\bthe\s+(?:term|word|phrase)s?\s+[“\"][^“”\"]{1,90}[”\"]", re.I)],
    "obligation": [re.compile(r"\b(?:shall|must)\s+(?!not\b|be\s+(?:unlawful|punish|guilty|subject|liable|fined)|"
                              r"mean|include|have\s+the\s+(?:same\s+)?meaning|apply\b|constitute|be\s+deemed|"
                              r"be\s+construed)", re.I),
                   re.compile(r"\b(?:is|are)\s+required\s+to\b|\bit\s+(?:is|shall\s+be)\s+the\s+duty\s+of\b|"
                              r"\brequired\s+under\s+this\b", re.I)],
    "permission": [re.compile(r"\bmay\s+(?!not\b|be\s+(?:punish|fined|imprisoned|subject|liable))", re.I),
                   re.compile(r"\b(?:is|are|shall\s+be)\s+(?:entitled|permitted|authorized|allowed)\s+to\b", re.I)],
    "prohibition": [re.compile(r"\b(?:shall|may|must)\s+not\b|\bno\s+(?:person|one|public\s+body|agency|officer|"
                               r"employee|entity|individual|licensee|applicant)\s+(?:shall|may)\b|\bis\s+(?:unlawful|"
                               r"prohibited)\b|\bit\s+(?:is|shall\s+be)\s+unlawful\b|\bshall\s+be\s+unlawful\b|"
                               r"\bprohibited\s+from\b", re.I)],
    "power": [re.compile(r"\b(?:is|are|shall\s+be|be)\s+(?:authorized|empowered)\s+(?:and\s+directed\s+)?to\b|"
                         r"\b(?:has|have|shall\s+have)\s+(?:the\s+)?(?:power|authority)\s+to\b|"
                         r"\bmay\s+(?:adopt|promulgate|prescribe|issue|establish|make)\s+(?:such\s+)?"
                         r"(?:rules|regulations|orders|standards)\b|\bmay\s+(?:deny|revoke|suspend|grant|approve|"
                         r"waive|extend|delegate|appoint|impose|order|determine|decide|enforce)\b|"
                         r"\bin\s+(?:its|his\s+or\s+her|their)\s+discretion\b", re.I)],
    "penalty": [re.compile(r"\b(?:guilty\s+of\s+a|is\s+a|constitutes\s+a|commits\s+a)\s+(?:class\s+\w+\s+)?"
                           r"(?:misdemeanor|felony|infraction|violation|offense|offence)\b|\bpunishable\b|"
                           r"\b(?:civil|administrative|criminal)\s+penalty\b|\bfine(?:d|s)?\s+(?:of\s+)?not\s+"
                           r"(?:more|less|exceeding|to\s+exceed)\b|\bimprison(?:ed|ment)\b|\bsubject\s+to\s+a\s+"
                           r"(?:fine|penalty|forfeiture)\b|\bpenalty\s+of\b|\bliable\s+for\s+a\s+(?:civil\s+)?"
                           r"penalty\b|\bshall\s+be\s+(?:fined|punished)\b", re.I)],
    "procedure": [re.compile(r"\bwithin\s+(?:\w+\s+)?\(?\d+\)?\s+(?:calendar\s+|business\s+|working\s+|work\s+)?"
                             r"(?:days|hours|weeks|months|years)\b|\b(?:shall|must|may)\s+(?:file|submit|serve|"
                             r"notify|petition|appeal|apply|request|respond|issue\s+a\s+(?:notice|decision|order)|"
                             r"hold\s+a\s+hearing|conduct\s+a\s+hearing|give\s+(?:written\s+)?notice)\b|"
                             r"\b(?:application|petition|notice\s+of\s+appeal|request)\s+(?:shall|must)\s+be\s+"
                             r"(?:filed|submitted|made|in\s+writing)\b|\bupon\s+receipt\s+of\b", re.I)],
}


def rule_types(text: str, head: str = "", row: dict | None = None) -> dict[str, float]:
    """``{type: 1.0}`` for every norm type a cue phrase marks in ``head + text`` (0.0 for the others).  With a
    ``row`` (state, id, title ...) the definition type comes from ``lexflow.law.terms.definitions``, the full
    definition finder (its forms and evaluation are in docs/design/verify-terms.md), which finds about twice
    what the cue phrase alone does on the evaluation sample; the cue phrase is the fallback."""
    t = f"{head}\n{text or ''}"
    out = {k: (1.0 if any(p.search(t) for p in pats) else 0.0) for k, pats in _RULES.items()}
    if row is not None and row.get("state"):
        try:
            from . import terms as T
            out["definition"] = 1.0 if T.definitions(row["state"], row, text or "") else 0.0
        except Exception:                                               # noqa: BLE001 - the cue phrase stands
            pass
    return out


# --------------------------------------------------------------------------- (b) norm types: the model
QUESTIONS: dict[str, dict] = {
    "definition": {"type": "noul", "instructions": "Does the section define the meaning of a term (for example "
                                                   "'\"X\" means ...' or 'as used in this chapter')?"},
    "obligation": {"type": "noul", "instructions": "Does the section require a person or body to do something "
                                                   "(shall, must, is required to)?"},
    "permission": {"type": "noul", "instructions": "Does the section allow a person or body to do something it is "
                                                   "not required to do (may, is entitled to)?"},
    "prohibition": {"type": "noul", "instructions": "Does the section forbid an act (shall not, may not, is "
                                                    "unlawful, prohibited)?"},
    "power": {"type": "noul", "instructions": "Does the section give a body or official the power to decide, "
                                              "order, adopt rules, grant, deny, revoke or enforce?"},
    "penalty": {"type": "noul", "instructions": "Does the section set a penalty, fine, imprisonment or other "
                                                "sanction for a violation?"},
    "procedure": {"type": "noul", "instructions": "Does the section lay down a procedure: steps to take, filings, "
                                                  "notices, deadlines, hearings or appeals?"},
}
# the probability at which the model's answer counts; calibrated in docs/design/legal-ontologies.md section 4
THRESHOLD: dict[str, float] = {k: 0.5 for k in NORM_TYPES}


def model_state(row: dict, text: str) -> dict:
    """What the model reads: the citation and heading, then the first ``HEAD_CHARS`` characters."""
    head = " ".join(f"{row.get('citation') or row.get('ref') or ''} {row.get('head') or row.get('title') or ''}".split())
    return {"Section": head, "Text": " ".join((text or "").split())[:HEAD_CHARS]}


def model_types(decider, row: dict, text: str) -> tuple[dict[str, float | None], str, float]:
    """``({type: probability}, model name, ms)`` from one decision call (seven noul questions).  A failed call
    gives every probability None and the model name ``error``; nothing raises."""
    try:
        out = decider.decide(model_state(row, text), QUESTIONS)
    except Exception:                                                   # noqa: BLE001 - keep the run going
        return {k: None for k in NORM_TYPES}, "error", 0.0
    answers = out.get("answers") or {}
    probs = {k: (answers.get(k) or {}).get("probability") for k in NORM_TYPES}
    return probs, str(out.get("model") or decider.model), float(out.get("ms") or 0.0)


def merge(rules: dict[str, float], model: dict[str, float | None] | None,
          threshold: dict[str, float] = THRESHOLD) -> list[str]:
    """The norm types of a row: the rules' plus any the model gives at or over its threshold."""
    out = [k for k in NORM_TYPES if rules.get(k)]
    if model:
        for k in NORM_TYPES:
            p = model.get(k)
            if k not in out and p is not None and p >= threshold.get(k, 0.5):
                out.append(k)
    return out


# --------------------------------------------------------------------------- the table
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
  state TEXT NOT NULL,
  ref TEXT NOT NULL,
  act_id TEXT,
  structure TEXT,
  norm_types TEXT,
  method TEXT,
  model TEXT,
  confidence TEXT,
  updated_at TEXT,
  origin TEXT,
  PRIMARY KEY (state, ref)
);
CREATE INDEX IF NOT EXISTS section_tags_state_method ON {TABLE}(state, method);
"""


def ensure_table(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)


def tag_row(row: dict, text: str, decider=None) -> dict:
    """One section's tags (no database): the ``section_tags`` row as a dict."""
    rules = rule_types(text, head=row.get("head") or row.get("title") or "", row=row)
    model_probs, model_name, ms = (None, None, 0.0)
    method = "rules"
    if decider is not None:
        model_probs, model_name, ms = model_types(decider, row, text)
        method = "rules+chat" if getattr(decider, "is_fallback", False) else "rules+decision"
    conf = {"rules": rules, "model": model_probs, "ms": round(ms, 1),
            "eli": OM.eli_uri(row.get("state") or "", row.get("act_id") or "")}
    return {"state": row.get("state"), "ref": row.get("ref"), "act_id": row.get("act_id"),
            "structure": structure(row.get("path"), row.get("act_id")),
            "norm_types": merge(rules, model_probs), "method": method, "model": model_name,
            "confidence": conf}


def upsert(con: sqlite3.Connection, rows: list[dict]) -> int:
    return db.upsert(con, TABLE, rows, keys=("state", "ref"))


def status(con: sqlite3.Connection, states: list[str]) -> dict[str, dict]:
    """Per state: rows tagged by method."""
    ensure_table(con)
    out = {st: {} for st in states}
    for r in db.rows(con, f"SELECT state, method, count(*) n FROM {TABLE} GROUP BY state, method"):
        out.setdefault(r["state"], {})[r["method"]] = r["n"]
    return out


# --------------------------------------------------------------------------- the run
def _index_rows(state: str, corpus: str = "statutes"):
    """Every section of a state's index with its text, one row per ref (the first in index order, which is the
    version in force where a ref has several)."""
    from ..ask import index as I
    con = I.connect(state, corpus)
    try:
        seen: set[str] = set()
        cur = con.execute("SELECT s.id, s.ref, s.citation, s.title, s.head, s.path, s.act_id, s.effective_from, "
                          "b.text AS text FROM sec s JOIN body b ON b.id = s.id ORDER BY s.id")
        for r in cur:
            d = dict(r)
            if d["ref"] in seen:
                continue
            seen.add(d["ref"])
            d["state"] = state
            yield d
    finally:
        con.close()


def section_count(state: str, corpus: str = "statutes") -> int:
    from ..ask import index as I
    con = I.connect(state, corpus)
    try:
        return con.execute("SELECT count(DISTINCT ref) FROM sec").fetchone()[0]
    finally:
        con.close()


def run_state(con: sqlite3.Connection, state: str, *, decider=None, force: bool = False, budget: int | None = None,
              pace: float = 0.0, limit: int | None = None, log: Log = print, progress: Callable | None = None,
              corpus: str = "statutes") -> dict:
    """Tag one state's index.  Resumes: rows already tagged by the same method are skipped unless ``force``.
    ``budget`` caps the model calls this run makes (the rest of the sections get ``rules`` rows, retagged with
    the model on the next run); ``pace`` sleeps between model calls; ``limit`` stops after that many sections."""
    ensure_table(con)
    method = "rules" if decider is None else ("rules+chat" if getattr(decider, "is_fallback", False)
                                              else "rules+decision")
    done = {r["ref"] for r in db.rows(con, f"SELECT ref FROM {TABLE} WHERE state=? AND method=?", state, method)} \
        if not force else set()
    total = section_count(state, corpus)
    t0 = time.perf_counter()
    n = calls = skipped = 0
    batch: list[dict] = []
    for i, row in enumerate(_index_rows(state, corpus)):
        if limit is not None and n >= limit:
            break
        if row["ref"] in done:
            skipped += 1
            continue
        use = decider if (decider is not None and (budget is None or calls < budget)) else None
        tagged = tag_row(row, row.pop("text") or "", use)
        if use is not None:
            calls += 1
            if pace:
                time.sleep(pace)
        batch.append(tagged)
        n += 1
        if len(batch) >= BATCH:
            upsert(con, batch)
            con.commit()
            batch = []
            if progress:
                progress(min(1.0, (i + 1) / max(1, total)))
            log(f"{state.upper()}: {n:,} tagged, {skipped:,} already done, {calls} model calls, "
                f"{time.perf_counter() - t0:.0f} s")
    if batch:
        upsert(con, batch)
        con.commit()
    secs = time.perf_counter() - t0
    log(f"{state.upper()}: done, {n:,} tagged ({skipped:,} skipped), {calls} model calls in {secs:.0f} s")
    return {"state": state, "tagged": n, "skipped": skipped, "model_calls": calls, "seconds": round(secs, 1),
            "method": method, "total": total}
