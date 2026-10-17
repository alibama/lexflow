"""The cleanliness gate before any push: ``out/wikibase/lint-report.md`` (and ``.json``).

Deterministic checks run on every NEW item of the graph and on every existing item whose label differs from the
one ``wikibase_items`` recorded (a changed label or description); each finding has a code:

* ``label-empty``; ``label-bare-key``: a bare key or id for a label (``unit p13_13c``, ``snake_case``,
  ``<State> court <id>``, a lexflow key, a Q-id, a lone section number);
* ``drafting-words``: a label or description with the words of the drafting process ("verifier", "lexflow index
  row", "discovery file", "User-Agent", "Claude", model names, "draft" anywhere but the review-status claim); the
  schema's own class and vocabulary items are exempt (``AI verifier`` and ``draft`` are their terms);
* ``person-name``: a person-like name (``lexflow.privacy``'s markers: an Attn/c-o piece, a title such as Mr, Ms,
  Dr or Hon before a Title-Case name, a Title-Case name before an office-holder's title);
* ``personal-mailbox`` (``privacy.is_office_mailbox`` refuses it) and ``direct-line`` (a phone number in a label or
  description, or a line marked direct, cell, personal, mobile or home);
* ``no-reprint-quote``: quoted text in a reference whose source URL is on a ``quotes.NO_REPRINT`` host;
* ``too-long``: labels, descriptions or aliases over 250, strings over 400, URLs over 500 characters;
* ``future-time``: a time value after today; ``duplicate-label-description``: two items with one label and
  description; ``dangling-reference``: an item value no item of the build carries.

An Ollama pass (``lexflow.extract.ollama.OllamaClient``, qwen3:1.7b, thinking off, JSON format) reads the labels and
descriptions of new items in batches of 25 and answers for each ``readable``, ``person``, ``jargon`` and a
``suggested_label`` when not readable.  It runs on every new item a deterministic check touched plus a seeded random
sample of the rest (``--sample``, 10%), at most ``--cap`` calls (150); the model, the prompt hash and the timing are
recorded.  Its verdicts are advisory: an item is HELD out of the push only when a deterministic check fails or
Ollama flags ``person``; ``jargon`` and ``readable`` findings go to the report with the suggested label for a person
to accept (never applied here).  ``lexflow wikibase push --really`` refuses to run while the report holds items,
unless ``--allow-held``, and never pushes held items.

    lexflow wikibase lint [--no-ollama] [--sample 0.1] [--cap 150] [--seed N] [--states va,dc] [--places gid]
                          [--no-drafts]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .. import config, privacy
from ..municipal import states as S
from ..store import db
from . import graph
from . import schema as SC

OUT_DIR = config.ROOT / "out" / "wikibase"
REPORT_MD = "lint-report.md"
REPORT_JSON = "lint-report.json"
MODEL = "qwen3:1.7b"
BATCH = 25
CAP = 150
SAMPLE = 0.1
SEED = 20261015
LABEL_MAX, STRING_MAX, URL_MAX = SC.LABEL_MAX, SC.STRING_MAX, 500

Log = Callable[[str], None]

# --------------------------------------------------------------------------- deterministic checks

DRAFTING_WORDS = re.compile(r"\b(?:verifier|lexflow index row|discovery file|user-agent|claude|draft|drafts|drafted|"
                            r"qwen\d*|gemma\d*|llama\d*|mistral|gpt-?\d|sonnet|opus|haiku|o\d-mini|deepseek)\b", re.I)
_STATE_NAMES = "|".join(re.escape(n) for _, _, n in sorted(S.STATES, key=lambda s: -len(s[2])))
BARE_LABEL = [
    re.compile(r"^(?:unit|section|step|role|item|code|form|rung|process|agency)\s+\S*[\d_]\S*$", re.I),  # "unit p13_13c"
    re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)+$"),                                                  # snake_case
    re.compile(rf"^(?:{_STATE_NAMES}) court \S+$", re.I),                                          # "<State> court <id>"
    re.compile(r"^(?:lexflow|courtlistener):"),                                                 # a key
    re.compile(r"^[PQ]\d+$"),                                                                   # an id
    re.compile(r"^[\d][\d.\-:/]*[a-z]?$", re.I),                                                  # "2.2-3704"
    re.compile(r"^(?:opinion|cluster)\s+\d+$", re.I),
    re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){2,}$"),                                               # a-slug-of-words
]
_NAME = r"([A-Z][a-z]+)(?:\s+[A-Z]\.?)?\s+([A-Z][a-z]+(?:-[A-Z][a-z]+)?)"
TITLE_NAME = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Hon|Honorable|Judge|Justice|Sen|Senator|Rep|Representative|"
                        r"Gov|Governor|Mayor|Sheriff|Rev|Prof)\.?\s+(?:[A-Z]\.\s*)?" + _NAME + r"\b")
_TITLES = "|".join(sorted(privacy.TITLES, key=len, reverse=True))
NAME_TITLE = re.compile(r"\b" + _NAME + rf",\s+(?:[A-Z][A-Za-z]*\s+){{0,3}}(?i:{_TITLES})\b")
# a Title-Case pair is a name only when neither word is office, page or joining vocabulary ("Deputy Clerk",
# "Public Records" and "City Council" are not names)
_NOT_NAME_WORDS = (privacy.OFFICE_NAME_WORDS | privacy.PAGE_WORDS | privacy.PHONE_FILLER | privacy.STOP |
                   privacy.FILLER | {w.lower() for _, _, n in S.STATES for w in n.split()})
ATTN = re.compile(r"(?:^|[\s,;(])(?:attn\.?|attention|c/o|care\s+of)\s*:?\s", re.I)
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.\-]*)?\(?\d{3}\)?[\s.\-]+\d{3}[\s.\-]\d{4}(?!\d)")
PERSON_LINE = re.compile(r"\b(?:" + "|".join(sorted(privacy.PERSON_MARKERS | privacy.PERSON_LINE_MARKERS)) +
                         r")\b", re.I)
_CASE_CAPTION = re.compile(r"\s+v(?:s)?\.?\s+", re.I)
# a law may be in force until, or from, a date still to come; every other time value records something that happened
FUTURE_OK = {"effective date", "effective until"}


def is_bare(label: str) -> bool:
    s = (label or "").strip()
    return any(p.match(s) for p in BARE_LABEL)


def person_like(text: str, *, case_caption: bool = False) -> str | None:
    """Why a text looks like it names a person, or None."""
    t = text or ""
    if ATTN.search(t):
        return "Attn/c-o marker"
    for m in TITLE_NAME.finditer(t):
        if _is_name(m.group(1), m.group(2)):
            return f"title before a name: {m.group(0)!r}"
    if not case_caption:
        for m in NAME_TITLE.finditer(t):
            if _is_name(m.group(1), m.group(2)):
                return f"name before an office-holder's title: {m.group(0)!r}"
    return None


def _is_name(first: str, last: str) -> bool:
    return not any(w.lower() in _NOT_NAME_WORDS for w in (first, *last.split("-")))


def _values(it: graph.Item):
    for c in it.claims:
        yield c, c.value, "value"
        for _, v in c.qualifiers:
            yield c, v, "qualifier"
        for ref in c.references:
            for _, v in ref:
                yield c, v, "reference"


def check_item(it: graph.Item, today: date, keys: set[str]) -> list[dict]:
    """The deterministic findings for one item: ``[{code, field, detail}]``."""
    out: list[dict] = []
    kind = SC.kind_of(it.key)
    schema_item = kind in ("class", "vocab")
    label, desc = it.label or "", it.description or ""

    def add(code: str, field: str, detail: str = ""):
        out.append({"code": code, "field": field, "detail": detail[:200]})

    if not label.strip():
        add("label-empty", "label")
    elif is_bare(label):
        add("label-bare-key", "label", label)
    for fld, text in (("label", label), ("description", desc), *(("alias", a) for a in it.aliases)):
        if not schema_item:
            m = DRAFTING_WORDS.search(text)
            if m:
                add("drafting-words", fld, f"{m.group(0)!r} in {text[:80]!r}")
        why = person_like(text, case_caption=(kind == "cluster" and fld == "label" and bool(_CASE_CAPTION.search(text))))
        if why:
            add("person-name", fld, why)
        bad = graph.personal_mailbox(text)
        if bad:
            add("personal-mailbox", fld, bad)
        if PHONE.search(text):
            add("direct-line", fld, "phone number in text" + (" (marked as a person's line)" if PERSON_LINE.search(text)
                                                                 else ""))
        if len(text) > LABEL_MAX:
            add("too-long", fld, f"{len(text)} > {LABEL_MAX}")
    class_labels = {c.label for c in SC.CLASSES if c.qid}
    for c, v, where in _values(it):
        if v.kind in ("string", "monolingual") and len(v.value or "") > STRING_MAX:
            add("too-long", f"{c.prop} {where}", f"{len(v.value)} > {STRING_MAX}")
        if v.kind == "url" and len(v.value or "") > URL_MAX:
            add("too-long", f"{c.prop} {where}", f"{len(v.value)} > {URL_MAX}")
        if v.kind == "url" and v.value.lower().startswith("mailto:") and not privacy.is_office_mailbox(v.value[7:]):
            add("personal-mailbox", f"{c.prop} {where}", v.value[7:])
        if v.kind in ("string", "monolingual", "url", "external-id") and graph.personal_mailbox(v.value):
            add("personal-mailbox", f"{c.prop} {where}", graph.personal_mailbox(v.value) or "")
        if v.kind == "time" and c.prop not in FUTURE_OK:
            d = _date_of(v.value)
            if d and d > today:
                add("future-time", f"{c.prop} {where}", v.value)
        if v.kind == "item" and v.value not in keys and v.value not in class_labels:
            add("dangling-reference", f"{c.prop} {where}", v.value)
        if v.kind == "quantity" and v.unit and v.unit not in keys:
            add("dangling-reference", f"{c.prop} unit", v.unit)
    if it.cls and it.cls not in keys and it.cls not in class_labels:
        add("dangling-reference", "instance of", it.cls)
    for c in it.claims:
        for ref in c.references:
            src = next((v.value for p, v in ref if p == "source URL"), None)
            if src and graph.no_reprint(src) and any(p == "quoted text" for p, _ in ref):
                add("no-reprint-quote", f"{c.prop} reference", src)
    if c_phone := next((c for c in it.claims if c.prop == "phone number"), None):
        val = c_phone.value.value or ""
        if PERSON_LINE.search(val) or privacy.office_phone_value(val) is None:
            add("direct-line", "phone number value", val)
    return out


def _date_of(value: str) -> date | None:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (value or "").strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, max(mo, 1), max(d, 1))
    except ValueError:
        return None


def deterministic(items: list[graph.Item], stored_labels: dict[str, str], today: date | None = None
                  ) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Findings by key for every new item and every existing item whose label changed; the second value says why
    each key was checked (``new`` or ``changed``)."""
    today = today or date.today()
    keys = {it.key for it in items}
    checked: dict[str, str] = {}
    for it in items:
        if not it.exists:
            checked[it.key] = "new"
        elif stored_labels.get(it.key) is not None and stored_labels[it.key] != it.label:
            checked[it.key] = "changed"
    findings: dict[str, list[dict]] = {}
    for it in items:
        if it.key in checked:
            f = check_item(it, today, keys)
            if f:
                findings[it.key] = f
    # duplicate label + description pairs, among every item of the build
    groups: dict[tuple[str, str], list[str]] = {}
    for it in items:
        groups.setdefault((it.label, it.description), []).append(it.key)
    for (label, desc), ks in groups.items():
        if len(ks) > 1:
            for k in ks:
                if k in checked:
                    findings.setdefault(k, []).append({"code": "duplicate-label-description", "field": "label",
                                                       "detail": f"also {', '.join(x for x in ks if x != k)[:150]}"})
    return findings, checked


# --------------------------------------------------------------------------- the Ollama pass

SYSTEM = """You check the names of entries in a public knowledge base about United States law (statutes, agencies,
courts, legal process steps, forms). Each entry has a number, a label and a description. For every entry answer:
- readable: true when a person who knows nothing about the project could tell what the entry is from its label and
  description; false when it reads as a code, a file name, an internal id or a fragment.
- person: true only when the label or description names an individual human being (a staff member, an official named
  by their own name, a private person). Names of courts, offices, positions, bodies, places and the party names in a
  court case caption (Smith v. Jones) are NOT persons.
- jargon: true when the label uses internal ids, keys, snake_case words, abbreviations a reader would not know, or
  project code words (verifier, index row, discovery file, draft).
- suggested_label: a short plain-English label ONLY when readable is false; otherwise an empty string.
Answer with JSON only, one object per entry, in the same order, with the entry's number in "n"."""

SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"n": {"type": "integer"}, "readable": {"type": "boolean"}, "person": {"type": "boolean"},
                       "jargon": {"type": "boolean"}, "suggested_label": {"type": "string"}},
        "required": ["n", "readable", "person", "jargon", "suggested_label"]}}},
    "required": ["items"],
}
PROMPT_HASH = hashlib.sha256((SYSTEM + json.dumps(SCHEMA, sort_keys=True)).encode("utf-8")).hexdigest()[:12]


def make_client(model: str = MODEL):
    from ..extract.ollama import OllamaClient
    return OllamaClient(base_url=config.OLLAMA_URL, model=model, num_ctx=8192, timeout=900, think=False)


def batch_prompt(batch: list[graph.Item]) -> str:
    lines = [f"{n}. label: {it.label[:LABEL_MAX]!r}; description: {(it.description or '')[:LABEL_MAX]!r}"
             for n, it in enumerate(batch, 1)]
    return "Entries:\n" + "\n".join(lines) + f"\n\nReturn JSON with {len(batch)} objects in \"items\"."


def parse_verdicts(text: str, n: int) -> dict[int, dict]:
    try:
        data = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text or "", re.S)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return {}
    out: dict[int, dict] = {}
    rows = data.get("items") if isinstance(data, dict) else data
    for i, r in enumerate(rows or [], 1):
        if not isinstance(r, dict):
            continue
        try:
            k = int(r.get("n") or i)
        except (TypeError, ValueError):
            k = i
        if 1 <= k <= n and k not in out:
            out[k] = {"readable": bool(r.get("readable", True)), "person": bool(r.get("person", False)),
                      "jargon": bool(r.get("jargon", False)),
                      "suggested_label": str(r.get("suggested_label") or "").strip()[:LABEL_MAX]}
    return out


def select_for_ollama(items: list[graph.Item], findings: dict[str, list[dict]], *, sample: float, seed: int,
                      cap: int, batch: int = BATCH) -> list[graph.Item]:
    new = [it for it in items if not it.exists]
    touched = [it for it in new if it.key in findings]
    rest = [it for it in new if it.key not in findings]
    rng = random.Random(seed)
    k = min(len(rest), round(len(rest) * sample))
    sampled = rng.sample(rest, k) if k else []
    chosen = touched + sorted(sampled, key=lambda i: i.key)
    return chosen[:cap * batch]


def ollama_pass(items: list[graph.Item], client, *, batch: int = BATCH, cap: int = CAP, log: Log = print) -> dict:
    verdicts: dict[str, dict] = {}
    calls: list[dict] = []
    t0 = time.monotonic()
    for i in range(0, len(items), batch):
        if len(calls) >= cap:
            break
        chunk = items[i:i + batch]
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": batch_prompt(chunk)}]
        t = time.monotonic()
        try:
            text = client.chat(messages, schema=SCHEMA, temperature=0.0, max_tokens=120 * len(chunk) + 200)
            err = None
        except Exception as e:                                   # noqa: BLE001 - a dead model is a report line
            text, err = "", f"{type(e).__name__}: {e}"[:200]
        got = parse_verdicts(text, len(chunk)) if text else {}
        for n, it in enumerate(chunk, 1):
            if n in got:
                verdicts[it.key] = got[n]
        calls.append({"n": len(calls) + 1, "items": len(chunk), "answered": len(got),
                      "seconds": round(time.monotonic() - t, 1), "error": err})
        log(f"  ollama call {len(calls)}: {len(got)}/{len(chunk)} verdicts in {calls[-1]['seconds']} s"
            + (f" ({err})" if err else ""))
    return {"model": getattr(client, "model", MODEL), "prompt_hash": PROMPT_HASH, "calls": calls,
            "seconds": round(time.monotonic() - t0, 1), "items_sent": sum(c["items"] for c in calls),
            "items_answered": len(verdicts), "verdicts": verdicts}


# --------------------------------------------------------------------------- the report


def assemble(items: list[graph.Item], findings: dict[str, list[dict]], checked: dict[str, str],
             ollama: dict | None, scope: dict) -> dict:
    by_key = {it.key: it for it in items}
    verdicts = (ollama or {}).get("verdicts", {})
    held = []
    for key in sorted(set(findings) | {k for k, v in verdicts.items() if v.get("person")}):
        it = by_key.get(key)
        reasons = [f"{f['code']} ({f['field']}): {f['detail']}" if f["detail"] else f"{f['code']} ({f['field']})"
                   for f in findings.get(key, [])]
        if verdicts.get(key, {}).get("person"):
            reasons.append("ollama: person")
        held.append({"key": key, "kind": SC.kind_of(key), "label": it.label if it else "",
                     "description": (it.description if it else "")[:120], "why": checked.get(key, "new"),
                     "reasons": reasons})
    flags = []
    for key, v in sorted(verdicts.items()):
        if v.get("person") or v.get("jargon") or not v.get("readable", True):
            it = by_key.get(key)
            flags.append({"key": key, "kind": SC.kind_of(key), "label": it.label if it else "",
                          "description": (it.description if it else "")[:120], **v})
    codes = Counter(f["code"] for fs in findings.values() for f in fs)
    by_kind = Counter(h["kind"] for h in held)
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "scope": scope,
        "items": len(items), "new": sum(1 for it in items if not it.exists),
        "checked": {"new": sum(1 for v in checked.values() if v == "new"),
                    "changed": sum(1 for v in checked.values() if v == "changed")},
        "findings_by_code": dict(codes), "held_count": len(held), "held_by_kind": dict(by_kind), "held": held,
        "ollama": {k: v for k, v in (ollama or {}).items() if k != "verdicts"} | ({"flags": flags} if ollama else {}),
        "suggested_labels": [{"key": f["key"], "label": f["label"], "suggested_label": f["suggested_label"]}
                             for f in flags if f.get("suggested_label")],
    }


def markdown(report: dict) -> str:
    L: list[str] = []
    L.append("# Wikibase lint report")
    L.append("")
    L.append(f"_{report['generated']}; {report['items']} items in the graph, {report['new']} new; checked "
             f"{report['checked']['new']} new and {report['checked']['changed']} relabelled items; scope "
             f"{json.dumps(report['scope'])}._")
    L.append("")
    L.append(f"**HELD: {report['held_count']} items** (not pushed until fixed; `push --really` refuses to run while "
             "this list is not empty unless `--allow-held`).")
    L.append("")
    if report["findings_by_code"]:
        L.append("| check | findings |")
        L.append("|---|---|")
        for code, n in sorted(report["findings_by_code"].items(), key=lambda kv: -kv[1]):
            L.append(f"| {code} | {n} |")
        L.append("")
    if report["held_by_kind"]:
        L.append("Held by kind: " + ", ".join(f"{k} {n}" for k, n in sorted(report["held_by_kind"].items())))
        L.append("")
    o = report.get("ollama") or {}
    if o.get("calls") is not None:
        flagged = Counter()
        for f in o.get("flags", []):
            flagged["person"] += bool(f.get("person"))
            flagged["jargon"] += bool(f.get("jargon"))
            flagged["unreadable"] += not f.get("readable", True)
        L.append(f"Ollama: model `{o.get('model')}`, prompt hash `{o.get('prompt_hash')}`, {len(o.get('calls', []))} "
                 f"calls, {o.get('items_sent', 0)} items sent, {o.get('items_answered', 0)} answered, "
                 f"{o.get('seconds', 0)} s. Flags: " + (", ".join(f"{k} {n}" for k, n in flagged.items() if n)
                                                       or "none") + ".")
        L.append("")
    else:
        L.append("Ollama: not run.")
        L.append("")
    L.append("## Held items")
    L.append("")
    if not report["held"]:
        L.append("None.")
    else:
        L.append("| key | label | reasons |")
        L.append("|---|---|---|")
        for h in report["held"]:
            L.append(f"| `{h['key']}` | {_cell(h['label'])} | {_cell('; '.join(h['reasons']))} |")
    L.append("")
    L.append("## Ollama flags (advisory; `person` holds, the rest is for a reader to accept)")
    L.append("")
    flags = o.get("flags") or []
    if not flags:
        L.append("None.")
    else:
        L.append("| key | label | readable | person | jargon | suggested label |")
        L.append("|---|---|---|---|---|---|")
        for f in flags:
            L.append(f"| `{f['key']}` | {_cell(f['label'])} | {f['readable']} | {f['person']} | {f['jargon']} | "
                     f"{_cell(f.get('suggested_label') or '')} |")
    L.append("")
    return "\n".join(L)


def _cell(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")[:160]


def write_report(report: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    md, js = out_dir / REPORT_MD, out_dir / REPORT_JSON
    md.write_text(markdown(report), encoding="utf-8")
    js.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return md, js


# --------------------------------------------------------------------------- the run


def reuse_ollama(out_dir: Path) -> dict | None:
    """The Ollama section of the report already in ``out_dir``, as a pass result: its flags are the verdicts that
    matter (every other verdict was clean), so a deterministic re-run after a fix keeps what the model said."""
    try:
        old = json.loads((out_dir / REPORT_JSON).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    o = old.get("ollama") or {}
    if o.get("calls") is None:
        return None
    verdicts = {f["key"]: {k: f.get(k) for k in ("readable", "person", "jargon", "suggested_label")}
                for f in o.get("flags", []) if f.get("key")}
    return {k: v for k, v in o.items() if k != "flags"} | {"verdicts": verdicts, "reused_from": old.get("generated")}


def run(con, *, ollama: bool = True, sample: float = SAMPLE, cap: int = CAP, seed: int = SEED, states=None,
        places=None, drafts: bool = True, client=None, items: list[graph.Item] | None = None,
        out_dir: Path | None = None, today: date | None = None, reuse: bool = False, log: Log = print) -> dict:
    out_dir = out_dir or OUT_DIR
    if items is None:
        items = graph.build(con, states=states, places=places, drafts=drafts, log=log)
    stored = {r["key"]: r["label"] for r in db.rows(con, "SELECT key, label FROM wikibase_items")} if con is not None \
        else {}
    findings, checked = deterministic(items, stored, today)
    log(f"deterministic: {len(checked)} items checked, {len(findings)} with findings")
    result = None
    if reuse:
        result = reuse_ollama(out_dir)
        log(f"ollama: {'reusing ' + str(len(result['verdicts'])) + ' flags from the previous report' if result else 'no previous report to reuse'}")
    elif ollama:
        client = client or make_client()
        chosen = select_for_ollama(items, findings, sample=sample, seed=seed, cap=cap)
        log(f"ollama: {len(chosen)} items in {-(-len(chosen) // BATCH)} calls (cap {cap}), model {client.model}")
        result = ollama_pass(chosen, client, cap=cap, log=log)
    scope = {"states": states, "places": places, "drafts": drafts, "sample": sample, "seed": seed, "cap": cap}
    report = assemble(items, findings, checked, result, scope)
    md, js = write_report(report, out_dir)
    log(f"held {report['held_count']} items; report: {md}")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="lexflow wikibase lint", description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-ollama", action="store_true", help="deterministic checks only")
    ap.add_argument("--reuse", action="store_true", help="keep the Ollama verdicts of the report already in --out "
                                                        "instead of calling the model again")
    ap.add_argument("--sample", type=float, default=SAMPLE, help="share of untouched new items Ollama also reads")
    ap.add_argument("--cap", type=int, default=CAP, help="at most this many Ollama calls")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--states", help="comma-separated state codes to limit the graph")
    ap.add_argument("--places", help="comma-separated government ids to limit the graph")
    ap.add_argument("--no-drafts", action="store_true", help="leave draft (single-tier) models out")
    ap.add_argument("--db", help="path of the lexflow database")
    ap.add_argument("--out", help=f"output directory (default {OUT_DIR})")
    args = ap.parse_args(argv)
    log = lambda *a: print(*a, file=sys.stderr, flush=True)       # noqa: E731
    con = db.connect(args.db) if args.db else db.connect()
    try:
        report = run(con, ollama=not args.no_ollama, sample=args.sample, cap=args.cap, seed=args.seed,
                     states=args.states.split(",") if args.states else None,
                     places=args.places.split(",") if args.places else None, drafts=not args.no_drafts,
                     client=None if (args.no_ollama or args.reuse) else make_client(args.model),
                     out_dir=Path(args.out) if args.out else None, reuse=args.reuse, log=log)
    finally:
        con.close()
    return 1 if report["held_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
