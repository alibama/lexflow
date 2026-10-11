"""A model's notes on what the statute leaves open, split between readers and builders.

The notes in ``curated/<state>/<question>.json`` (``facts.gaps``) were written while building the model.  Many
carry a caveat a reader needs ("The text says 'an additional seven work days' without saying whether they run
from the end of the five-day period or from the B.4 response") in the same sentence as builders' language: the
model's internal names for steps and outcomes (``respond_extended``, ``'respond'``) and process-map terms ("the
timer is a boundary event", "exclusive merges", "join 'any'").

``for_readers`` splits a note into clauses (at sentence ends, '; ' and ': '), keeps those that use none of those
terms and still say something (they have a verb), drops a clause that points back at one it dropped ("This ...",
"they ..."), and gives back None when too little is left.  The full notes, unchanged, go to the builders' section
of lexflow:method.  A clause that mixes the two keeps its plain head when it has one: "The printed text does not say
what happens if it is late, so the deadline's consequence is 'unstated'" keeps "The printed text does not say what
happens if it is late."

A model can instead carry its own plain-language notes (``reader_gaps`` in its curated file), which are then shown
as they are, or put single notes in plain words where cutting would lose what the text leaves open:
``reader_notes`` maps the opening words of a note to the plain text (or to null, to keep that note for builders
only).  Every key must open exactly one note of its model (tests/test_gate0.py checks the curated files).
"""
from __future__ import annotations

import re

BUILDER_TERMS = re.compile(
    r"\b[a-z][a-z0-9]*_[a-z0-9_]+\b|\b(?:bpmn|dmn|feel|petri|timers?|boundary events?|end events?|start events?|"
    r"end states?|gateways?|exclusive merges?|parallel joins?|join ['\"‘“]?(?:any|all)|sequence flows?|message flows?|"
    r"sub-?process(?:es)?|business-rule tasks?|hit polic(?:y|ies)|interrupting|modell?ed|modell?ing|models?|"
    r"main path|paths?|branch(?:es)?|rejoins?|drawn|draws?|compiler|schema|typed|stands for|"
    r"(?:inputs?|outputs?) of the|(?:ruling|fee|decision) tables?|benchmark|word budget|"
    # the table's and the map's own terms: a lane, a rule that fires or falls through, inputs and outputs, routes
    r"lanes?|folded into|(?:rules?|rows?) fires?|fires before|falls? through|inputs?|outputs?|routed|routes?|"
    r"routing|anchors?|actors?|tasks?|invok(?:e|es|ed|ing)|encod(?:e|es|ed|ing)|columns?|the flow|local layer|"
    r"corpus)\b"
    # a consequence named by its stored value: "(consequence 'unstated')", "marked 'unstated'"
    r"|\bconsequence\s+['\"‘“]|['\"‘“](?:unstated|deemed-denial|right-lapses|action-invalid|directory-only)['\"’”]",
    re.I)
# a clause that points back at the one before it: kept only if that one was kept
ANAPHOR = re.compile(r"^(?:this|these|that|those|it|its|they|their|them|so|therefore|thus|both|such|here|there|then|"
                     r"otherwise|instead|the second|the first|the other|the latter|the former)\b", re.I)
# a clause with none of these says nothing on its own ("the determination together with ...")
VERB = re.compile(r"\b(?:may|must|shall|is|are|was|were|be|been|has|have|had|does|do|did|can|cannot|could|will|would|"
                  r"should|leads?|gives?|says?|said|requires?|applies|apply|sets?|lists?|names?|counts?|runs?|ends?|"
                  r"starts?|begins?|takes?|gets?|needs?|allows?|lets?|means?|covers?|stays?|continues?|follows?|"
                  r"states?|provides?|appears?|tolls?|opens?|grants?|qualifies|governs?|caps?|excludes?|includes?|"
                  r"comes?|goes|go|owes?|lapses?|expires?|extends?|limits?|shapes?|exist|exists|"
                  r"miss(?:es)?|presumes?|issues?|files?|sends?|directs?|bars?|pays?|charges?|costs?|carr(?:y|ies)|"
                  r"arises?|differs?|designates?|publish(?:es)?|compl(?:y|ies)|initiates?|supports?|orders?|"
                  r"restates?|attach(?:es)?|submits?|treats?|keeps?|puts?|shows?|marks?|makes?|made|obligates?|"
                  r"happens?|depends?|remains?|becomes?|lasts?|ties|refers?|asks?|decides?|denies|deny|receives?|"
                  r"delivers?|notif(?:y|ies)|waives?|recovers?|sues?|answers?|responds?|produces?|releases?|"
                  r"withholds?|offers?|loses?|leaves?|reads?|finds?|holds?|serves?|seeks?|awards?|permits?|"
                  r"prohibits?|forbids?|entitles?)\b", re.I)
# a topic ("Extension (B.4): ...", "Deemed denial (3(d), 3(f)): ..."), with one level of nested parentheses
TOPIC = re.compile(r"^([A-Z](?:[^:;.()]|\((?:[^()]|\([^()]*\))*\)){1,60}):\s+(?=\S)")
ABBREV = re.compile(r"(?:\b(?:[A-Z]|U\.S\.C|U\.S|et seq|seq|No|Nos|Va|Md|Gen|Prov|Ann|Stat|Code|Rev|Cal|Fla|Tex|Ill|"
                    r"Wash|N\.Y|N\.C|D\.C|Gov|Bus|Prof|Sec|Secs|Ch|Art|Inc|Co|Corp|Ltd|Jr|Sr|St|v|vs|e\.g|i\.e|etc|cf|"
                    r"Tax|Com|Civ|Proc|Pen|Fam|Ins|Educ|Admin|Mun|Crim|Evid|Regs?|Ord|"
                    r"subd|subds|cl|para|p|pp|approx)\.)$")
MIN_KEPT = 40


def internal_names(facts: dict | None) -> set[str]:
    """The ids a model's facts give its actors, steps, outcomes, decisions, conditions and table columns."""
    f = facts or {}
    names = {x.get("id") for k in ("actors", "steps", "outcomes", "decisions") for x in f.get(k) or []}
    names |= {s.get("condition") for s in f.get("steps") or []} | {o.get("when") for o in f.get("outcomes") or []}
    names |= {c.get("name") for d in f.get("decisions") or [] for c in (d.get("inputs") or []) + (d.get("outputs") or [])}
    return {n for n in names if n}


def is_builder(text: str, names: set[str] | frozenset = frozenset()) -> bool:
    """Whether a note (or clause) uses builders' language: process-map terms, or an internal name, bare
    (``respond_extended``) or in quotes ('respond')."""
    if BUILDER_TERMS.search(text or ""):
        return True
    return any(re.search(r"['‘\"“]" + re.escape(n) + r"['’\"”]", text or "") for n in names)


def sentences(text: str) -> list[str]:
    """Split a note into sentences, not at 'Va. Code' or 'e.g.'."""
    out, start = [], 0
    for m in re.finditer(r"[.!?][\"'”’)]*\s+(?=[\"'“‘(§A-Z0-9])", text):
        head = text[start:m.start() + 1]
        if ABBREV.search(head.rstrip("\"'”’)")):
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    return out + ([tail] if tail else [])


def clauses(sentence: str) -> list[str]:
    """Split a sentence at '; ' and ': ' outside parentheses and double quotes."""
    out, depth, quote, start = [], 0, False, 0
    for i, ch in enumerate(sentence):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch in "“”\"":
            quote = ch == "“" or (ch == '"' and not quote)
        elif ch in ";:" and depth == 0 and not quote and sentence[i + 1:i + 2] == " ":
            out.append(sentence[start:i].strip())
            start = i + 2
    out.append(sentence[start:].strip())
    return [c for c in out if c]


def _end(text: str) -> str:
    text = text.rstrip(" ,;:")
    return text if re.search(r"[.!?][\"'”’)]*$", text) else text + "."


# where a clause can be cut and still say what it said: before a consequence ("..., so the deadline's consequence is
# 'unstated'") or a relative clause ("..., which the model marks with ...")
HEAD_CUT = re.compile(r",\s+(?=(?:so|which)\b)")
MIN_HEAD = 30


def plain_head(clause: str, names: set[str] | frozenset = frozenset()) -> str | None:
    """The longest opening of a builder clause, up to a ', so' or ', which', that is plain and says something."""
    best = None
    for m in HEAD_CUT.finditer(clause):
        head = clause[:m.start()].strip()
        if is_builder(head, names):
            break
        if len(head) >= MIN_HEAD and VERB.search(head):
            best = head
    return best


def for_readers(note: str, names: set[str] | frozenset = frozenset()) -> str | None:
    """The note without builders' language, or None when what is left is too little to stand alone."""
    note = re.sub(r"\s+", " ", str(note or "")).strip()
    if not note or not is_builder(note, names):
        return note or None
    topic = ""
    m = TOPIC.match(note)
    if m and not is_builder(m.group(1), names):
        topic, note = m.group(1), note[m.end():]
    whole = sentences(note)
    units = [(i, c) for i, s in enumerate(whole) for c in clauses(s)]
    kept: dict[int, list[str]] = {}
    cut: set[int] = set()        # sentences of which only a head is kept
    prev = True
    for i, c in units:
        ok = not is_builder(c, names) and bool(VERB.search(c)) and (prev or not ANAPHOR.match(c))
        if ok:
            kept.setdefault(i, []).append(c)
        elif (prev or not ANAPHOR.match(c)) and (h := plain_head(c, names)):
            kept.setdefault(i, []).append(h)              # "The text does not say X, so <builder words>": the head
            cut.add(i)
        prev = ok
    out = []
    for i, cs in kept.items():
        if i not in cut and len(cs) == sum(1 for j, _ in units if j == i):
            out.append(whole[i])                         # kept whole: as written
        else:
            text = _end("; ".join(cs))
            out.append(text[:1].upper() + text[1:])
    text = " ".join(out).strip()
    if len(text) < MIN_KEPT:
        return None
    return f"{topic}: {text}" if topic else text


def own_words(gap: str, reader_notes: dict | None) -> tuple[bool, str | None]:
    """(whether a model's ``reader_notes`` puts this note in plain words, and those words: None keeps it off)."""
    for start, text in (reader_notes or {}).items():
        if start and str(gap).startswith(start):
            return True, (str(text) if text else None)
    return False, None


def stale_reader_notes(gaps: list[str], reader_notes: dict | None) -> list[str]:
    """The ``reader_notes`` keys that open no note, or more than one: they would put the wrong words on a page."""
    return [k for k in (reader_notes or {}) if sum(1 for g in gaps if str(g).startswith(k)) != 1]


def split(metrics: dict, facts: dict | None = None) -> tuple[list[str], list[str]]:
    """(notes for readers, notes for builders: every note that readers see shortened, reworded or not at all)."""
    names = internal_names(facts)
    gaps = [str(g) for g in metrics.get("gaps") or []]
    plain = metrics.get("reader_notes") or {}
    own = [str(g) for g in metrics.get("reader_gaps") or []]
    builder = [g for g in gaps if is_builder(g, names) or own_words(g, plain)[0]]
    if own:
        return own, builder
    readers = []
    for g in gaps:
        given, text = own_words(g, plain)
        r = text if given else for_readers(g, names)
        if r:
            readers.append(r)
    return readers, builder


# ------------------------------------------------------------------ drafting notes in researched place files
# What the researching and checking AI passes wrote about their own work into a place file's caveats and source
# titles ("the verifier rendered both pages", "added by the verifier", "(lexflow index row 30394)", "declared research
# User-Agent (lexflow-research/0.1)"): a page describes the place, so the page leaves these out.  The files are not
# changed.  The phrases are lexflow's own list; a note worded otherwise stays.
DRAFTING = re.compile(
    r"\bverifier(?:'s|s)?\b|\bmodell?er(?:'s)?\b|\blexflow(?: full-text)? index\b|\bindex rows? \d|"
    r"\bresearch (?:client|user-agent)\b|\blexflow-research\b|\b(?:earlier|later|previous) lexflow runs?\b|"
    r"\bread for lexflow\b|\bfor lexflow on\b|\bI\.(?:text_of|lookup)\b|\bfixtures/|"
    r"\bthe block was not (?:bypassed|circumvented|worked around)\b|\bthe user (?:may|can|might) (?:overrule|decide)", re.I)


def _groups(text: str) -> list[tuple[int, int]]:
    """(start, end) of each outermost parenthesis in ``text``, the brackets included."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch == "(":
            if depth == 0:
                start = i
            depth += 1
        elif ch == ")" and depth:
            depth -= 1
            if depth == 0:
                out.append((start, i + 1))
    return out


def _top_parts(inner: str) -> list[str]:
    """``inner`` split at '; ' outside nested parentheses."""
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(inner):
        depth += (ch == "(") - (ch == ")" and depth > 0)
        if ch == ";" and depth == 0 and inner[i + 1:i + 2] == " ":
            parts.append(inner[start:i])
            start = i + 2
    return parts + [inner[start:]]


def _drop_in_parentheses(text: str) -> str:
    """Each parenthesis without its parts (between '; ') that are drafting notes, and without the parenthesis
    itself when nothing else is left: "(lexflow index row 30394)" goes, "(ECC; the verifier re-read the page on
    2026-10-11)" becomes "(ECC)".  A parenthesis inside one is treated the same way."""
    out, last = [], 0
    for a, b in _groups(text):
        out.append(text[last:a])
        last = b
        inner = text[a + 1:b - 1]
        if not DRAFTING.search(inner):
            out.append(text[a:b])
            continue
        kept = [_drop_in_parentheses(p).strip() for p in _top_parts(inner)]
        kept = [p for p in kept if p and not DRAFTING.search(p) and not re.fullmatch(r"rows? \d+(?: to \d+)?", p)]
        if kept:
            out.append(f"({'; '.join(kept)})")
        elif out:
            out[-1] = out[-1].rstrip()
    out.append(text[last:])
    return "".join(out)


def _tidy(text: str) -> str:
    text = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s{2,}", " ", text)).strip()
    return re.sub(r"^[,;:]\s*|[,;:]\s*$", "", text).strip()


def _sentences(text: str) -> list[str]:
    """``sentences``, also splitting before a sentence that opens with a web address ("... live. www.example.org
    answered ...")."""
    out = []
    for s in sentences(text):
        out += [x for x in re.split(r"(?<=[.!?])\s+(?=www\.)", s) if x]
    return out


def without_drafting(text: str) -> str:
    """A caveat without the drafting notes in it (``DRAFTING``): first the parts of parentheses that are, then each
    clause of a sentence that still is one (between '; ' and ': '), and a clause that points back at one dropped
    ("this", "that").  Empty when nothing else is left."""
    text = _drop_in_parentheses(str(text or ""))
    kept = []
    for sent in _sentences(text):
        if not DRAFTING.search(sent):
            kept.append(sent)
            continue
        parts, dropped = [], False
        for c in clauses(sent):
            if DRAFTING.search(c) or (dropped and ANAPHOR.match(c)):
                dropped = True
                continue
            parts.append(c)
        if parts:
            joined = _end("; ".join(parts))
            kept.append(joined[:1].upper() + joined[1:])
    return _tidy(" ".join(kept))


def title_without_drafting(text: str) -> str:
    """A title (a process's, a source's) without its drafting notes: the parts of parentheses that are, then each
    clause (between ', ' or '; ') that still is one: "Va. Code § 8.01-15.2 (lexflow index row 30394), added by the
    verifier" becomes "Va. Code § 8.01-15.2"."""
    text = _drop_in_parentheses(str(text or ""))
    if DRAFTING.search(text):
        parts = re.split(r"([,;]\s+)", text)
        out = parts[0] if not DRAFTING.search(parts[0]) else ""
        for sep, part in zip(parts[1::2], parts[2::2]):
            if not DRAFTING.search(part):
                out += (sep if out else "") + part
        text = out
    return _tidy(text)
