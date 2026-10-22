"""Split statute text into labelled clauses whose text is an exact span of the source.

Small models are bad at copying text, so the decomposed strategies never ask them to: they point
at clause ids, and the quote is the clause text itself.  Handles the three label styles seen so
far: Virginia ``A.`` / ``1.`` / ``a.``, and DC / Maryland ``(a)`` / ``(1)`` / ``(A)`` / ``(i)``
(several labels can open one paragraph, e.g. Maryland's ``(a) (1) Except as ...``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_HEAD = re.compile(r"^§ ([\w.:\-]+)\. "
                          # a Brazilian article's citation (lexflow/corpus/countries/brazil.py), as statutes.combined_text
                          # heads it: "§ Lei nº 12.527/2011, art. 11. ", "§ Constituição Federal, art. 5º. "
                          r"|^§ ((?:Constituição Federal|Constituição de \d{4}|ADCT|(?:Lei Complementar|Lei Delegada|"
                          r"Decreto-Lei|Emenda Constitucional(?: de Revisão)?|Lei) nº [\d.]+/\d{4})"
                          r"(?:, (?:art\. [\d.]+º?(?:-[A-Z]{1,2})?|preâmbulo))?)\.(?: |$)")
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"}
# "(a) ", "(b)(1) " (DC stacks labels without a space), "A. ", "12. ", "a. "
LABEL = re.compile(r"^\s*(?:\(([A-Za-z0-9]{1,5}(?:-\d+)?)\)(?:\s+|(?=\())|([A-Z]|\d{1,2}|[a-z])\.\s+)")
ABBREV = re.compile(r"(?:\b(?:U\.S\.C|U\.S|et seq|No|Nos|Va|Md|Sec|Secs|Ch|Art|Inc|Co|Corp|Ltd|Jr|Sr|St|v|e\.g|i\.e|etc|seq|"
                    r"subd|subds|cl|para|p|pp)\.)$", re.I)
MODAL = re.compile(r"\b(shall not|shall|must not|must|may not|may|is entitled to|are entitled to|has the right to|"
                   r"have the right to|is required to|are required to|is authorized to|are authorized to)\b", re.I)
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
           "eleven": 11, "twelve": 12, "fourteen": 14, "fifteen": 15, "twenty": 20, "thirty": 30, "forty-five": 45,
           "forty": 40, "sixty": 60, "ninety": 90,
           # ordinals: "not later than the 10th business day", "before the tenth day"
           "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7, "eighth": 8,
           "ninth": 9, "tenth": 10, "fifteenth": 15, "twentieth": 20, "thirtieth": 30, "forty-fifth": 45,
           "sixtieth": 60, "ninetieth": 90}
DEADLINE = re.compile(
    r"\b(?:within|not more than|no more than|not later than|no later than|at least|before the end of|"
    r"at the end of|not to exceed|shall not exceed|not exceed|exceed|an additional|additional|by|before|has|have|"
    r"shall have)\s+(?:the\s+)?"
    # a number: digits, a word ("ten", "tenth"), or a compound ("one hundred twenty", "forty-five")
    r"(?P<amount>\d+(?=st\b|nd\b|rd\b|th\b|\s|-|\()|[a-z]+(?:-[a-z]+)?(?:\s+hundred(?:\s+(?:and\s+)?[a-z]+(?:-[a-z]+)?)?)?)"
    r"(?:st|nd|rd|th)?\s*(?:\(\d+(?:st|nd|rd|th)?\)\s*)?"
    r"(?:or\s+(?:\d+|[a-z]+(?:-[a-z]+)?)\s+)?"          # "within seven or 14 business days": the first limit
    r"(?P<adj>working|business|calendar|work)?[\s-]*"
    r"(?P<unit>days?|weeks?|months?|years?|hours?)\b(?P<rest>[^.;,]{0,90})", re.I)


@dataclass
class Clause:
    id: str
    label: str            # subsection path, "B.4" or "a.1"
    text: str             # exact span of the source text
    start: int
    paragraph: int
    section: str | None = None   # set when the text is several sections joined by "§ <number>. <title>" headers
    modal: str | None = None
    subject: str | None = None
    deadline: dict | None = None
    tags: list[str] = field(default_factory=list)


def _label_kind(tok: str, stack: list[tuple[str, str]]) -> str:
    if tok.isdigit():
        return "digit"
    if re.fullmatch(r"[a-z]+-\d+", tok):
        return "lower"
    if tok.isupper() and len(tok) == 1:
        return "upper"
    if tok.lower() in ROMAN and tok.islower():
        # 'i' after 'h' is a letter; otherwise roman when a roman level exists or we are below a digit/upper level
        prev = next((t for k, t in reversed(stack) if k == "lower"), None)
        if prev and len(prev) == 1 and len(tok) == 1 and ord(tok) == ord(prev) + 1:
            return "lower"
        if any(k == "roman" for k, _ in stack) or (stack and stack[-1][0] in ("digit", "upper")):
            return "roman"
    if tok.isupper() and tok.lower() in ROMAN:
        return "uroman"
    return "lower" if tok.islower() else "upper"


def _sentences(par: str) -> list[tuple[int, str]]:
    """(offset, sentence) pairs; never splits inside an abbreviation or a citation."""
    out, start = [], 0
    for m in re.finditer(r"[.;:](?=\s+(?:[A-Z(“\"]|\d+\.\s))", par):
        head = par[start:m.end()]
        last = head.rstrip()[-12:]
        if m.group(0) == "." and ABBREV.search(last):
            continue
        if re.search(r"§+\s*[\d.:\-]+$", par[max(0, m.start() - 20):m.start()]):
            continue
        if len(head.strip()) < 25 and m.group(0) != ";":
            continue
        out.append((start, head))
        start = m.end()
    if par[start:].strip():
        out.append((start, par[start:]))
    return [(o + len(s) - len(s.lstrip()), s.strip()) for o, s in out if s.strip()]


JOIN_WRAPPED = True        # join hard-wrapped lines (switchable for experiments)


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """(offset, paragraph) pairs, each an exact span of ``text``.  Hard-wrapped lines are joined back together
    (New York's files break every 72 characters, mid-sentence): a line continues the one before it when that
    one is long, does not end a sentence and is not a section header, and the line opens no label of its own."""
    out: list[list[int]] = []
    pos = 0
    prev = ""
    for line in text.split("\n"):
        start, end = pos, pos + len(line)
        pos = end + 1
        if not line.strip():
            prev = ""
            continue
        joins = (JOIN_WRAPPED and out and prev and len(prev.rstrip()) >= 55 and not re.search(r"[.;:]\s*$", prev)
                 and not SECTION_HEAD.match(prev) and not SECTION_HEAD.match(line) and not LABEL.match(line))
        if joins:
            out[-1][1] = end
        else:
            out.append([start, end])
        prev = line
    return [(a, text[a:b]) for a, b in out]


def segment(text: str) -> list[Clause]:
    clauses: list[Clause] = []
    stack: list[tuple[str, str]] = []          # (kind, label) from outermost to innermost
    section = None
    for p_index, (offset, par) in enumerate(_paragraphs(text)):
        head = SECTION_HEAD.match(par)
        if head:
            section, stack = head.group(1) or head.group(2), []
            continue
        body, body_off = par, offset
        while True:
            m = LABEL.match(body)
            if not m:
                break
            tok = m.group(1) or m.group(2)
            kind = _label_kind(tok, stack)
            depth = next((i for i, (k, _) in enumerate(stack) if k == kind), None)
            stack = stack[:depth] if depth is not None else stack
            stack.append((kind, tok))
            body_off += m.end()
            body = body[m.end():]
        label = ".".join(t for _, t in stack)
        for s_off, sent in _sentences(body):
            start = body_off + s_off
            assert text[start:start + len(sent)] == sent, (start, sent[:40])
            clauses.append(Clause(id=f"c{len(clauses) + 1}", label=label, text=sent, start=start, paragraph=p_index,
                                  section=section))
    for c in clauses:
        annotate(c)
    return clauses


def _amount(tok: str) -> int | None:
    """'10' -> 10, 'ten' -> 10, 'tenth' -> 10, 'one hundred twenty' -> 120, 'two hundred and forty-five' -> 245."""
    tok = re.sub(r"\s+", " ", tok.lower().strip())
    if tok.isdigit():
        return int(tok)
    m = re.fullmatch(r"([a-z]+) hundred(?: (?:and )?([a-z]+(?:-[a-z]+)?))?", tok)
    if m:
        h = WORDNUM.get(m.group(1))
        rest = _compound(m.group(2)) if m.group(2) else 0
        return h * 100 + rest if h and rest is not None else None
    return _compound(tok)


def _compound(tok: str) -> int | None:
    """'forty-five' -> 45 (tens and units); a single number word as WORDNUM has it."""
    if tok in WORDNUM:
        return WORDNUM[tok]
    if "-" in tok:
        a, b = tok.split("-", 1)
        if a in WORDNUM and b in WORDNUM and WORDNUM[a] % 10 == 0 and WORDNUM[b] < 10:
            return WORDNUM[a] + WORDNUM[b]
    return None


def annotate(c: Clause) -> None:
    m = MODAL.search(c.text)
    if m:
        c.modal = m.group(1).lower()
        if re.search(r"(?:^|[,;]\s*)no\s+\w+", c.text[:m.start()], re.I) and " not" not in c.modal:
            c.modal += " not"                       # "No public body shall impose ..." is a prohibition
        c.subject = subject_of(c.text[:m.start()], c.text[m.end():])
        c.tags.append("duty")
    found = [d for d in DEADLINE.finditer(c.text) if _amount(d.group("amount"))]
    after_modal = [d for d in found if m and d.start() > m.start()]
    d = (after_modal or found or [None])[0]
    if d:
        unit = d.group("unit").lower().rstrip("s")
        adj = (d.group("adj") or "").lower()
        # "15 days (except Saturdays, Sundays, and legal public holidays)" counts business days
        no_weekends = re.match(r"\s*\(?\s*(?:except|excluding|exclusive of|not counting)\s+(?:saturdays|weekends)",
                               d.group("rest"), re.I)
        business = adj in ("working", "business", "work") or bool(no_weekends)
        unit = {"day": "business_days" if business else "days", "week": "weeks",
                "month": "months", "year": "years", "hour": "hours"}[unit]
        rest = re.sub(r"^\s*\([^)]*\)?", "", d.group("rest")) if no_weekends else d.group("rest")
        anchor = re.sub(r"^\s*(?:of|after|from|following)\s+", "", rest.strip(" ,")).strip()
        c.deadline = {"amount": _amount(d.group("amount")), "unit": unit, "anchor": anchor[:80] or "the triggering event",
                      "phrase": d.group(0)[:120]}
        c.tags.append("deadline")
    if re.search(r"\b(the following|one of the following|as follows)\b[:]?\s*$", c.text, re.I):
        c.tags.append("enumeration")


DETERMINERS = re.compile(r"^(?:a|an|the|any|each|every|such|said|all|no)\s+", re.I)


def subject_of(before: str, after: str) -> str | None:
    """Who carries the duty: the noun phrase before the modal, or the agent of a passive ('be provided by X')."""
    passive = re.match(r"\s*(?:\w+ly\s+)?be\s+\w+(?:ed|en)\s+(?:\w+\s+){0,3}?by\s+((?:the|a|an|any)\s+[\w ,'-]+?)(?=[,.;]|\s+(?:in|to|within|on|at|for|if|unless|when)\b|$)",
                       after, re.I)
    if passive:
        return _clean_subject(passive.group(1))
    s = before.strip()
    # set aside leading dependent clauses: "Except as provided ..., ", "If ..., ", "In responding to ..., "
    while True:
        m = LEADING_CLAUSE.match(s)
        if not m:
            break
        s = s[m.end():]
    # the subject is the noun phrase that opens what is left: "A public body, upon request ..., shall"
    s = s.split(",")[0]
    s = re.split(r"\s+(?:that|who|which|whose|whom)\b", s)[0]
    return _clean_subject(s) if s.strip() else None


LEADING_CLAUSE = re.compile(r"^(?:except|if|when|whenever|unless|subject to|notwithstanding|in|upon|after|before|"
                            r"for|to the extent|where|once|within|at|during|on|pursuant to)\b[^,]*,\s*", re.I)


def _clean_subject(s: str) -> str | None:
    s = DETERMINERS.sub("", s.strip(" ,;:")).strip()
    s = re.sub(r"\s+", " ", s)
    if not s or len(s.split()) > 8 or not re.search(r"[A-Za-z]", s):
        return None
    return s


def outline(clauses: list[Clause], width: int = 220) -> str:
    """A compact view for prompts: '[c12 B.4] It is not practically possible ...'."""
    return "\n".join(f"[{c.id} {c.label or '-'}] {c.text[:width]}{'…' if len(c.text) > width else ''}" for c in clauses)
