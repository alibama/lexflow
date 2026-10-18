"""QuickStatements batches (lexflow/publish/qs.py, docs/design/wikibase-schema.md section 5).

The hand-made items below stand in for ``graph.build``; the fake schema for ``schema.py``.  ``parse`` is a small
V1 parser written from the grammar QuickStatements' own parser uses (importDataFromV1 / parseValueV1): it is the
round-trip check that every line a batch holds is a command QuickStatements will accept.  The last tests parse
whatever ``out/wikibase/`` holds from the last dry generation against the live database.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from lexflow import privacy
from lexflow.municipal import quotes
from lexflow.publish import qs

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "wikibase"


# ----------------------------------------------------------------------------------------- the hand-made graph
@dataclass
class Value:
    kind: str
    value: str
    unit: str | None = None
    lang: str | None = None
    precision: int | None = None


@dataclass
class Claim:
    prop: str
    value: Value
    qualifiers: list = field(default_factory=list)
    references: list = field(default_factory=list)


@dataclass
class Item:
    key: str
    label: str
    description: str = ""
    aliases: list = field(default_factory=list)
    cls: str | None = None
    claims: list = field(default_factory=list)
    exists: bool = False
    kind: str = ""


def I(kind, value, **kw):
    return Value(kind, value, **kw)


EXISTING = {"instance of": "P5", "subclass of": "P6", "equivalent property": "P7", "exact match": "P8",
            "part of": "P9", "has part": "P10", "follows": "P11", "references": "P13",
            "applies to jurisdiction": "P15", "bearer": "P17", "citation": "P22", "official text": "P23",
            "effective date": "P24", "legal identifier": "P25",
            "legal process": "Q7", "legal process step": "Q8", "statute or legal provision": "Q10",
            "jurisdiction": "Q21", "legal role": "Q23"}

PROPERTIES = [
    dict(order=1, label="Wikidata item ID", datatype="external-id", wikidata=None, description="the Wikidata item",
         formatter="https://www.wikidata.org/wiki/$1", formatter_rdf="http://www.wikidata.org/entity/$1"),
    dict(order=2, label="formatter URL", datatype="string", wikidata="P1630", description="URL template"),
    dict(order=3, label="formatter URI for RDF resource", datatype="string", wikidata="P1921", description="IRI"),
    dict(order=4, label="unit level", datatype="item", description="title, chapter, section"),
    dict(order=7, label="sort key", datatype="string", description="zero-padded order"),
    dict(order=11, label="heading text", datatype="monolingualtext", description="the heading"),
    dict(order=12, label="reference type", datatype="item", description="authority, procedure"),
    dict(order=13, label="quoted text", datatype="string", description="the words of the statute"),
    dict(order=14, label="source section", datatype="item", description="section item"),
    dict(order=15, label="pinpoint", datatype="string", description="subsection"),
    dict(order=16, label="source URL", datatype="url", wikidata="P854", description="official page"),
    dict(order=17, label="retrieved", datatype="time", wikidata="P813", description="fetch date"),
    dict(order=19, label="determination method", datatype="item", wikidata="P459", description="how"),
    dict(order=30, label="email address", datatype="url", wikidata="P968", description="office mailbox"),
    dict(order=36, label="time limit", datatype="quantity", description="a deadline"),
    dict(order=37, label="time unit", datatype="item", description="the law's own word"),
    dict(order=38, label="counted from", datatype="string", description="the trigger"),
    dict(order=46, label="fee", datatype="quantity", description="amount in USD"),
    dict(order=50, label="question asked", datatype="monolingual", description="the plain question"),
    dict(order=51, label="review status", datatype="item", description="reviewed / draft"),
    dict(order=99, label="legal identifier", datatype="external-id", description="exists already: must be skipped"),
]
CLASSES = [
    dict(slug="legal-code", label="legal code", description="a jurisdiction's code", wikidata="Q1156854"),
    dict(slug="government-agency", label="government agency", description="a body", wikidata="Q327333"),
    dict(slug="office-type", label="office type", description="a body each county has",
         subclass_of="lexflow:class:government-agency"),
    dict(slug="review-status", label="review status", description="vocabulary"),
    dict(slug="time-unit", label="time unit", description="vocabulary"),
    dict(slug="currency", label="currency", description="vocabulary", subclass_of="legal process"),
    dict(slug="legal process", label="legal process", description="exists", qid="Q7"),
]
VOCAB = [
    dict(set="review-status", slug="draft", label="draft", description="unreviewed", cls="lexflow:class:review-status"),
    dict(set="review-status", slug="reviewed", label="reviewed", description="signed", cls="lexflow:class:review-status"),
    dict(set="time-unit", slug="business-days", label="business days", description="the law's word",
         cls="lexflow:class:time-unit"),
    dict(set="currency", slug="usd", label="US dollar", description="unit for fees", cls="lexflow:class:currency"),
]
SCHEMA = SimpleNamespace(PROPERTIES=PROPERTIES, CLASSES=CLASSES, VOCAB=VOCAB, EXISTING=EXISTING)

LONG = "Public records to be open to inspection; procedure for requesting records and responding to request " * 4
NO_REPRINT_URL = "https://www.albemarle.org/government/community-development/apply-for/permits"


def items() -> list[Item]:
    sec = "lexflow:statute:va:2.2-3704"
    return [
        Item("lexflow:code:va", "Virginia Code", "the Code of Virginia", ["Va. Code"], "lexflow:class:legal-code",
             [Claim("applies to jurisdiction", I("item", "lexflow:jurisdiction:va")),
              Claim("unit level", I("item", "lexflow:vocab:unit-level:code"))], kind="code"),
        Item("lexflow:unit:va:t2.2-sii-pb-c37", "Va. Code Title 2.2, Chapter 37", "chapter", [],
             "lexflow:class:legal-code",
             [Claim("part of", I("item", "lexflow:code:va")), Claim("sort key", I("string", "0002.2-0037")),
              Claim("heading text", I("monolingual", "Virginia Freedom of Information Act", lang="en"))],
             kind="code"),
        Item("lexflow:jurisdiction:va", "Virginia", "state", [], "jurisdiction",
             [Claim("Wikidata item ID", I("external-id", "Q1370"))], exists=True, kind="jurisdiction"),
        Item(sec, "Va. Code Ann. \u00a7 2.2-3704", "section", [], "statute or legal provision",
             [Claim("part of", I("item", "lexflow:unit:va:t2.2-sii-pb-c37")),
              Claim("heading text", I("monolingual", LONG)),
              Claim("effective date", I("time", "2023-07-01")),
              Claim("follows", I("item", "lexflow:statute:va:2.2-3703")),          # not in ids: skipped
              Claim("references", I("item", "lexflow:statute:va:2.2-3705"),
                    qualifiers=[("reference type", I("item", "lexflow:vocab:reference-type:procedure"))])],
             exists=True, kind="section"),
        Item("lexflow:agency:va:charlottesville:clerk", "Clerk of the Circuit Court\tof Charlottesville",
             'The "records" office\nof the city', ["Clerk's Office", "Clerk's Office", "Circuit Court Clerk"],
             "lexflow:class:government-agency",
             [Claim("email address", I("url", "mailto:records@example.org"),
                    references=[[("source URL", I("url", "https://www.example.org/clerk")),
                                 ("retrieved", I("time", "2026-10-15")),
                                 ("determination method", I("item", "lexflow:vocab:method:http-check"))]]),
              Claim("email address", I("url", "mailto:jane.doe@example.org")),       # personal: refused
              Claim("Wikidata item ID", I("external-id", "Q5086")),
              Claim("instance of", I("novalue", ""))],
             kind="agency"),
        Item("lexflow:process:va:foia", "Request public records (Virginia)", "the FOIA request process",
             ["How do I request public records in Virginia?"], "legal process",
             [Claim("question asked", I("monolingual", "How do I request public records in Virginia?", lang="en")),
              Claim("review status", I("item", "lexflow:vocab:review-status:reviewed")),
              Claim("time limit", I("quantity", "5"),
                    qualifiers=[("time unit", I("item", "lexflow:vocab:time-unit:business-days")),
                                ("counted from", I("string", "receiving a request"))],
                    references=[[("source section", I("item", sec)), ("pinpoint", I("string", "B")),
                                 ("quoted text", I("string", 'Any public body ... shall make one of the following '
                                                             'responses in writing within five working days'))],
                                [("source URL", I("url", "https://law.lis.virginia.gov/vacode/2.2-3704/")),
                                 ("retrieved", I("time", "2026-10"))]]),
              Claim("fee", I("quantity", "75.50", unit="lexflow:vocab:currency:usd"),
                    references=[[("source URL", I("url", NO_REPRINT_URL)),
                                 ("quoted text", I("string", "words that may not be reposted"))]]),
              Claim("fee", I("quantity", "not a number")),
              Claim("retrieved", I("time", "2026-13-45"))],
             kind="process"),
        Item("lexflow:step:va:foia:1", "File the request", "step 1 " * 60, [], "legal process step",
             [Claim("part of", I("item", "lexflow:process:va:foia")),
              Claim("review status", I("item", "lexflow:vocab:review-status:draft"))], kind="process"),
        Item("lexflow:step:va:foia:orphan", "Orphan", "subject never created", [], "legal process step",
             [Claim("part of", I("item", "lexflow:process:va:foia"))], kind="process"),
    ]


def by_kind(its):
    out: dict[str, list] = {}
    for it in its:
        out.setdefault(it.kind, []).append(it)
    return out


def fake_ids(its) -> qs.Ids:
    """What --resolve would write after pass 1: every new property and every key but the orphan and two
    sections the graph refers to without creating."""
    ids = qs.Ids()
    ids.add_schema(SCHEMA)
    for n, p in enumerate(PROPERTIES, 100):
        ids.properties.setdefault(p["label"], f"P{n}")
    keys = [it.key for it in its] + [it.key for it in qs.schema_items(SCHEMA)] + [
        "lexflow:vocab:unit-level:code", "lexflow:vocab:reference-type:procedure", "lexflow:vocab:method:http-check"]
    for n, k in enumerate(keys, 1000):
        if "orphan" not in k and not k.endswith("2.2-3703") and not k.endswith("2.2-3705"):
            ids.items.setdefault(k, f"Q{n}")
    return ids


# ----------------------------------------------------------------------------------------- a tiny V1 parser
DATATYPES = {"commonsMedia", "globe-coordinate", "wikibase-item", "wikibase-property", "string", "monolingualtext",
             "external-id", "quantity", "time", "url", "math", "geo-shape", "musical-notation", "tabular-data",
             "wikibase-lexeme", "wikibase-form", "wikibase-sense"}
TIME = re.compile(r"^[+-]\d{4,}-\d\d-\d\dT\d\d:\d\d:\d\dZ/(9|10|11)$")
QUANTITY = re.compile(r"^[+-]?\d+(\.\d+)?(U\d+)?$")
MONO = re.compile(r'^[a-z_-]+:"(.*)"$')
STRING = re.compile(r'^"(.*)"$')
ENTITY = re.compile(r"^[PQ]\d+$")


@dataclass
class Cmd:
    kind: str                      # CREATE, CREATE_PROPERTY, Len, Den, Aen, statement
    subject: str = ""
    prop: str = ""
    value: str = ""
    qualifiers: list = field(default_factory=list)
    references: list = field(default_factory=list)      # groups of (S-prop, value)
    line_no: int = 0


def check_value(v: str, where: str) -> str:
    """The value grammar of parseValueV1; returns the value's type."""
    if v in ("novalue", "somevalue"):
        return v
    if v == "LAST" or ENTITY.match(v):
        return "entity"
    if STRING.match(v):
        inner = STRING.match(v).group(1)
        assert "\t" not in inner and "\n" not in inner, where
        assert "/*" not in inner and "*/" not in inner, f"{where}: comment delimiter inside a string"
        limit = 500 if inner.lower().startswith(("http://", "https://", "mailto:")) else 400
        assert len(inner) <= limit, f"{where}: string of {len(inner)} chars"
        return "string"
    if MONO.match(v):
        assert len(MONO.match(v).group(1)) <= 400, where
        return "monolingualtext"
    if TIME.match(v):
        return "time"
    if QUANTITY.match(v):
        return "quantity"
    raise AssertionError(f"{where}: not a V1 value: {v!r}")


def parse(text: str, name: str = "batch") -> tuple[list[str], list[Cmd]]:
    """``(header comment lines, commands)``; raises on anything QuickStatements would not read as intended."""
    header, cmds = [], []
    last_create = None
    for n, raw in enumerate(text.split("\n"), 1):
        where = f"{name}:{n}"
        assert "\r" not in raw, where
        if raw == "" and n == text.count("\n") + 1:
            continue                                           # the final newline
        assert raw.strip() == raw, f"{where}: stray whitespace"
        if raw.startswith("/*"):
            assert raw.endswith("*/") and raw.count("/*") == 1 and raw.count("*/") == 1, f"{where}: bad comment"
            assert "\t" not in raw and "|" not in raw, f"{where}: tab or pipe in a comment line"
            assert not cmds, f"{where}: comment after commands"
            header.append(raw)
            continue
        assert "|" not in raw or "\t" in raw, f"{where}: a pipe in a row without tabs becomes a tab"
        cols = raw.split("\t")
        assert all(c == c.strip() and c for c in cols), f"{where}: empty or padded column"
        if cols == ["CREATE"]:
            cmds.append(Cmd("CREATE", line_no=n))
            last_create = "item"
        elif cols[0] == "CREATE_PROPERTY":
            assert len(cols) == 2 and cols[1] in DATATYPES, f"{where}: bad CREATE_PROPERTY"
            cmds.append(Cmd("CREATE_PROPERTY", value=cols[1], line_no=n))
            last_create = "property"
        elif len(cols) == 3 and re.fullmatch(r"[LDA]en", cols[1]):
            assert cols[0] == "LAST" or ENTITY.match(cols[0]), where
            if cols[0] == "LAST":
                assert last_create, f"{where}: LAST before any CREATE"
            m = STRING.match(cols[2])
            assert m, f"{where}: label value not quoted"
            assert 0 < len(m.group(1)) <= 250, f"{where}: label of {len(m.group(1))} chars"
            assert "\t" not in m.group(1) and "|" not in m.group(1) or cols[1] != "Aen", where
            cmds.append(Cmd(cols[1], subject=cols[0], value=cols[2], line_no=n))
        else:
            assert len(cols) >= 3, f"{where}: not a command: {raw!r}"
            assert cols[0] == "LAST" or ENTITY.match(cols[0]), f"{where}: bad subject {cols[0]!r}"
            if cols[0] == "LAST":
                assert last_create, f"{where}: LAST before any CREATE"
            assert re.fullmatch(r"P\d+", cols[1]), f"{where}: bad property {cols[1]!r}"
            check_value(cols[2], where)
            cmd = Cmd("statement", subject=cols[0], prop=cols[1], value=cols[2], line_no=n)
            rest = cols[3:]
            assert len(rest) % 2 == 0, f"{where}: incomplete qualifier/reference list"
            group = None
            for k, v in zip(rest[::2], rest[1::2]):
                check_value(v, where)
                if re.fullmatch(r"!?S\d+", k):
                    if group is None or k.startswith("!"):
                        group = []
                        cmd.references.append(group)
                    group.append((k.lstrip("!"), v))
                else:
                    assert re.fullmatch(r"P\d+", k), f"{where}: bad qualifier key {k!r}"
                    assert group is None, f"{where}: qualifier after a reference"
                    cmd.qualifiers.append((k, v))
            cmds.append(cmd)
    return header, cmds


def qs_count(cmds: list[Cmd]) -> int:
    """What the QuickStatements preview reports: each line one command, plus one per qualifier and per reference
    group."""
    return sum(1 + len(c.qualifiers) + len(c.references) for c in cmds)


def header_counts(header: list[str]) -> tuple[int, Counter]:
    preview = int(re.search(r"preview must show (\d+) commands", header[1]).group(1))
    counts = Counter()
    for part in re.search(r"/\* counts: (.*) \*/", header[2]).group(1).split("; "):
        if part != "none":
            k, v = part.rsplit(" ", 1)
            counts[k] = int(v)
    return preview, counts


def assert_header_matches(header, cmds):
    preview, counts = header_counts(header)
    assert preview == qs_count(cmds)
    got = Counter(c.kind for c in cmds)
    got["qualifier"] = sum(len(c.qualifiers) for c in cmds)
    got["reference"] = sum(len(c.references) for c in cmds)
    assert {k: v for k, v in counts.items()} == {k: v for k, v in got.items() if v}


def mailboxes(cmds):
    for c in cmds:
        for v in [c.value] + [v for _, v in c.qualifiers] + [v for g in c.references for _, v in g]:
            m = re.search(r'"mailto:([^"]+)"', v)
            if m:
                yield m.group(1)
            elif "@" in v:
                yield v.strip('"')


def assert_privacy_and_quotes(cmds, pid_source_url, pid_quoted_text):
    for mb in mailboxes(cmds):
        assert privacy.is_office_mailbox(mb), f"personal mailbox in a batch: {mb}"
    for c in cmds:
        for group in c.references:
            urls = [v.strip('"') for k, v in group if k == "S" + pid_source_url[1:]]
            if any(quotes.policy(u) for u in urls):
                assert not any(k == "S" + pid_quoted_text[1:] for k, _ in group), \
                    f"line {c.line_no}: quoted text under a NO_REPRINT source"


# ----------------------------------------------------------------------------------------- value syntax
def test_value_syntax():
    ids = fake_ids(items())
    assert qs.qs_string('He said "hi"\there\n/* not a summary */') == '"He said "hi" here / * not a summary * /"'
    assert qs.qs_time("2026-10-15") == "+2026-10-15T00:00:00Z/11"
    assert qs.qs_time("2026-10") == "+2026-10-00T00:00:00Z/10"
    assert qs.qs_time("1975") == "+1975-00-00T00:00:00Z/9"
    assert qs.qs_time("2026-10-15T12:00:00Z", precision=10) == "+2026-10-00T00:00:00Z/10"
    with pytest.raises(qs.QSError):
        qs.qs_time("next Tuesday")
    assert qs.qs_quantity("5") == "5"
    assert qs.qs_quantity("$1,500.00", "Q1003") == "1500.00U1003"
    with pytest.raises(qs.QSError):
        qs.qs_quantity("five")
    assert qs.qs_monolingual("How do I?", "EN") == 'en:"How do I?"'
    assert qs.qs_url("https://example.org/a b") == '"https://example.org/a%20b"'
    with pytest.raises(qs.QSError):
        qs.qs_url("mailto:jane.doe@example.org")
    assert qs.qs_url("mailto:records@example.org") == '"mailto:records@example.org"'
    assert qs.format_value(Value("item", "lexflow:vocab:review-status:draft"), ids).startswith("Q")
    assert qs.format_value(Value("item", "legal process"), ids) == "Q7"
    with pytest.raises(qs.Unresolved):
        qs.format_value(Value("item", "lexflow:nowhere"), ids)
    assert qs.fit("x" * 300, 250).endswith("\u2026") and len(qs.fit("x" * 300, 250)) <= 250
    assert qs.part_suffix(0) == "a" and qs.part_suffix(25) == "z" and qs.part_suffix(26) == "aa"


def test_claim_lines_every_shape():
    ids = fake_ids(items())
    proc = next(it for it in items() if it.key == "lexflow:process:va:foia")
    deadline = next(c for c in proc.claims if c.prop == "time limit")
    lines = qs.claim_lines("Q1005", deadline, ids)
    assert len(lines) == 2, "one line per reference"
    cols = lines[0].split("\t")
    assert cols[:3] == ["Q1005", ids.prop("time limit"), "5"]
    assert cols[3] == ids.prop("time unit") and cols[4] == ids.item("lexflow:vocab:time-unit:business-days")
    assert cols[5] == ids.prop("counted from") and cols[6] == '"receiving a request"'
    assert cols[7] == "S" + ids.prop("source section")[1:] and cols[8] == ids.item("lexflow:statute:va:2.2-3704")
    assert cols[9] == "S" + ids.prop("pinpoint")[1:] and cols[10] == '"B"'
    assert cols[11] == "S" + ids.prop("quoted text")[1:]
    cols2 = lines[1].split("\t")
    assert cols2[:3] == cols[:3] and cols2[3] == "S" + ids.prop("source URL")[1:]
    assert cols2[5] == "S" + ids.prop("retrieved")[1:] and cols2[6] == "+2026-10-00T00:00:00Z/10"
    fee = next(c for c in proc.claims if c.prop == "fee" and c.value.unit)
    (line,) = qs.claim_lines("Q1005", fee, ids)
    cols = line.split("\t")
    assert cols[2] == "75.50U" + ids.item("lexflow:vocab:currency:usd")[1:]
    assert "S" + ids.prop("quoted text")[1:] not in cols, "no quoted text under a NO_REPRINT source URL"
    assert "S" + ids.prop("source URL")[1:] in cols
    for c in [c for c in proc.claims if c.prop == "fee" and not c.value.unit] + \
             [c for c in proc.claims if c.prop == "retrieved"]:
        with pytest.raises(qs.QSError):
            qs.claim_lines("Q1005", c, ids)


# ----------------------------------------------------------------------------------------- pass 1
def test_properties_batch():
    (name, text), = qs.render(qs.properties_batch(SCHEMA), "abc1234")
    header, cmds = parse(text, name)
    assert name == "01-properties.qs"
    assert_header_matches(header, cmds)
    creates = [c for c in cmds if c.kind == "CREATE_PROPERTY"]
    assert len(creates) == len(PROPERTIES) - 1, "legal identifier exists and is not created again"
    assert [c.value for c in creates][:4] == ["external-id", "string", "string", "wikibase-item"]
    assert any(c.value == "monolingualtext" for c in creates)
    assert all(c.kind in ("CREATE_PROPERTY", "Len", "Den", "statement") for c in cmds)
    for c in cmds:
        if c.kind == "statement":
            assert c.subject == "LAST" and c.prop == "P7" and c.value.startswith('"http://www.wikidata.org/entity/P')
    assert sum(c.kind == "statement" for c in cmds) == sum(1 for p in PROPERTIES if p.get("wikidata"))
    assert "abc1234" in header[3]


def test_classes_batch():
    class_items = qs.schema_items(SCHEMA)
    (name, text), = qs.render(qs.classes_batch(SCHEMA, class_items), "abc1234")
    header, cmds = parse(text, name)
    assert_header_matches(header, cmds)
    creates = sum(c.kind == "CREATE" for c in cmds)
    assert creates == len(CLASSES) - 1 + len(VOCAB), "the existing class (Q7) is not created"
    keys = [c.value for c in cmds if c.kind == "statement" and c.prop == "P25"]
    assert keys[:2] == ['"lexflow:class:legal-code"', '"lexflow:class:government-agency"']
    assert keys[-1] == '"lexflow:vocab:currency:usd"', "classes before vocabularies"
    p5 = [c for c in cmds if c.kind == "statement" and c.prop in ("P5", "P6")]
    assert [(c.prop, c.value) for c in p5] == [("P6", "Q7")], \
        "only edges to live items in pass 1: currency subclass of legal process; office type -> agency waits"
    p8 = [c.value for c in cmds if c.kind == "statement" and c.prop == "P8"]
    assert p8 == ['"http://www.wikidata.org/entity/Q1156854"', '"http://www.wikidata.org/entity/Q327333"']
    assert all(c.prop in ("P25", "P5", "P6", "P8") for c in cmds if c.kind == "statement")
    assert all(c.value not in ("novalue", "somevalue") for c in cmds)


def test_items_batches():
    its = items()
    batches = qs.items_batches(by_kind(its))
    names = [b.name for b in batches]
    assert names == ["03-items-code", "03-items-agency", "03-items-process"], "no file for existing-only kinds"
    for b in batches:
        (name, text), = qs.render(b, "abc1234")
        header, cmds = parse(text, name)
        assert_header_matches(header, cmds)
        assert all(c.kind in ("CREATE", "Len", "Den", "Aen", "statement") for c in cmds)
        assert all(c.prop == "P25" and c.subject == "LAST" for c in cmds if c.kind == "statement")
        assert all(c.value not in ("novalue", "somevalue") for c in cmds)
    agency = dict(qs.render(batches[1], "abc1234"))["03-items-agency.qs"]
    _, cmds = parse(agency)
    assert cmds[1].value == '"Clerk of the Circuit Court of Charlottesville"', "tab becomes a space"
    assert cmds[2].value == '"The "records" office of the city"', "inner quotes pass as they are"
    assert [c.value for c in cmds if c.kind == "Aen"] == ['"Clerk\'s Office"', '"Circuit Court Clerk"'], \
        "one Aen line per alias, duplicates dropped"
    process = dict(qs.render(batches[2], "abc1234"))["03-items-process.qs"]
    _, cmds = parse(process)
    step_desc = [c for c in cmds if c.kind == "Den"][1].value
    assert len(step_desc) <= 252 and step_desc.endswith('\u2026"'), "descriptions cut at 250"
    assert sum(c.kind == "CREATE" for c in cmds) == 3


def test_split_at_2000_lines():
    many = [Item(f"lexflow:agency:xx:{n}", f"Agency {n}", "a body", ["alias"], "lexflow:class:government-agency",
                 kind="agency") for n in range(1500)]
    (b,) = qs.items_batches(by_kind(many))
    files = qs.render(b, "abc1234")
    assert [n for n, _ in files] == [f"03-items-agency-{s}.qs" for s in "abcd"]
    total = 0
    for name, text in files:
        lines = text.rstrip("\n").split("\n")
        assert len(lines) <= 2000, name
        header, cmds = parse(text, name)
        assert_header_matches(header, cmds)
        assert cmds[0].kind == "CREATE" and cmds[-1].kind == "statement", "a CREATE group is never split"
        assert f"part {name[-4]} of 4" in header[0]
        total += sum(c.kind == "CREATE" for c in cmds)
    assert total == 1500
    assert qs.split_groups([["a"] * 5, ["b"] * 5, ["c"] * 5], 10) == [[["a"] * 5, ["b"] * 5], [["c"] * 5]]


# ----------------------------------------------------------------------------------------- pass 2
def test_claims_and_updates(tmp_path):
    its = items()
    ids = fake_ids(its)
    class_items = qs.schema_items(SCHEMA)
    batches, updates = qs.claims_batches(by_kind(its), ids, SCHEMA, class_items)
    files = {}
    for b in batches + [updates]:
        for name, text in qs.render(b, "abc1234"):
            files[name] = text
    assert sorted(files) == ["04-claims-agency.qs", "04-claims-classes.qs", "04-claims-code.qs",
                             "04-claims-process.qs", "05-updates.qs"]
    known_q = set(ids.items.values()) | set(ids.labels.values())
    known_p = set(ids.properties.values())
    all_cmds = {}
    for name, text in files.items():
        header, cmds = parse(text, name)
        all_cmds[name] = (header, cmds)
        assert_header_matches(header, cmds)
        assert all(c.kind == "statement" for c in cmds), "pass 2 holds statements only"
        for c in cmds:
            assert c.subject in known_q | known_p, f"{name}: subject {c.subject} not in ids.json"
            assert c.prop in known_p, f"{name}: property {c.prop} not in ids.json"
            for v in [c.value] + [v for _, v in c.qualifiers] + [v for g in c.references for _, v in g]:
                if ENTITY.match(v):
                    assert v in known_q, f"{name}: target {v} not in ids.json"
                m = re.fullmatch(r"[+-]?[\d.]+U(\d+)", v)
                if m:
                    assert "Q" + m.group(1) in known_q, f"{name}: unit Q{m.group(1)} not in ids.json"
            for k, _ in c.qualifiers:
                assert k in known_p
            for g in c.references:
                for k, _ in g:
                    assert "P" + k[1:] in known_p
        assert_privacy_and_quotes(cmds, ids.prop("source URL"), ids.prop("quoted text"))
    # classes: office type -> agency (P6) now; currency -> legal process was written in pass 1; vocab P5 now
    _, cls = all_cmds["04-claims-classes.qs"]
    assert [(c.subject, c.prop, c.value) for c in cls] == [
        (ids.item("lexflow:class:office-type"), "P6", ids.item("lexflow:class:government-agency")),
        (ids.item("lexflow:vocab:review-status:draft"), "P5", ids.item("lexflow:class:review-status")),
        (ids.item("lexflow:vocab:review-status:reviewed"), "P5", ids.item("lexflow:class:review-status")),
        (ids.item("lexflow:vocab:time-unit:business-days"), "P5", ids.item("lexflow:class:time-unit")),
        (ids.item("lexflow:vocab:currency:usd"), "P5", ids.item("lexflow:class:currency"))]
    # agency: P5 first, office mailbox with its reference, personal mailbox skipped
    header, ag = all_cmds["04-claims-agency.qs"]
    assert ag[0].prop == "P5" and ag[0].value == ids.item("lexflow:class:government-agency")
    assert [c.prop for c in ag[1:]] == [ids.prop("email address"), ids.prop("Wikidata item ID"), "P5"]
    assert ag[1].references and len(ag[1].references[0]) == 3
    assert ag[3].value == "novalue", "novalue is a pass-2 value, never a pass-1 one"
    assert any("jane.doe" not in l for l in header) and any("not an office mailbox" in l for l in header)
    assert "jane.doe" not in files["04-claims-agency.qs"].split("*/\n")[-1]
    # process: the orphan subject and the bad values are skipped and listed
    header, pr = all_cmds["04-claims-process.qs"]
    assert any("lexflow:step:va:foia:orphan: subject has no id" in l for l in header)
    assert any("not a quantity" in l for l in header) and any("not a date" in l for l in header)
    assert sum(c.prop == ids.prop("time limit") for c in pr) == 2 and sum(c.prop == ids.prop("fee") for c in pr) == 1
    # updates: the existing section and jurisdiction, plus the property formatters
    header, up = all_cmds["05-updates.qs"]
    subjects = {c.subject for c in up}
    assert ids.item("lexflow:statute:va:2.2-3704") in subjects and "Q21" not in subjects
    assert ids.item("lexflow:jurisdiction:va") in subjects
    assert (ids.prop("Wikidata item ID"), ids.prop("formatter URL"), '"https://www.wikidata.org/wiki/$1"') in \
        [(c.subject, c.prop, c.value) for c in up]
    assert any("2.2-3703" in l for l in header), "a reference to an unresolved key is listed"
    assert not any(c.prop == "P5" for c in up if c.subject == ids.item("lexflow:statute:va:2.2-3704")), \
        "no P5 on an existing item"
    heading = next(c for c in up if c.prop == ids.prop("heading text"))
    assert heading.value.startswith('en:"') and len(heading.value) <= 406


def test_ids_json_round_trip(tmp_path):
    ids = fake_ids(items())
    path = tmp_path / "ids.json"
    path.write_text(json.dumps(ids.dump()), encoding="utf-8")
    back = qs.Ids.load(path, SCHEMA)
    assert back.items == ids.items and back.properties == ids.properties and back.labels == ids.labels
    assert back.item("legal process") == "Q7" and back.prop("instance of") == "P5"


def test_write_pass1_and_pass2(tmp_path, monkeypatch):
    """The two passes through the file writers, with ids.json between them."""
    its = items()
    files = qs.write_pass1(SCHEMA, its, by_kind(its), tmp_path, "abc1234", log=lambda *a: None)
    names = sorted(p.name for p in tmp_path.iterdir())
    assert names == ["01-properties.qs", "02-classes.qs", "03-items-agency.qs", "03-items-code.qs",
                     "03-items-process.qs", "README.md", "check.rq"]
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "https://lexipedia.wikibase.cloud/tools/quickstatements/#/batch" in readme
    assert "Project:Copyrights" in readme and "Project:People" in readme
    assert "stop" in readme and "paste" in readme and "error" in readme
    assert "pass 1 is done" in readme and "pass 2 is done" in readme
    assert re.search(r"^\d+\. ", readme, re.M), "numbered steps"
    for name, counts in files:
        assert f"`{name}` | {counts['commands']} |" in readme
    with pytest.raises(qs.QSError):
        qs.write_pass2(SCHEMA, its, by_kind(its), tmp_path, "abc1234", log=lambda *a: None)
    (tmp_path / "ids.json").write_text(json.dumps(fake_ids(its).dump()), encoding="utf-8")
    files2 = qs.write_pass2(SCHEMA, its, by_kind(its), tmp_path, "abc1234", log=lambda *a: None)
    assert [n for n, _ in files2][-5:] == ["04-claims-classes.qs", "04-claims-code.qs", "04-claims-agency.qs",
                                           "04-claims-process.qs", "05-updates.qs"]
    check = (tmp_path / "check.rq").read_text(encoding="utf-8")
    assert "# expected counts" in check and "class government agency: 1" in check
    assert "{P:" not in check or "review status" not in check.split("SELECT")[1], "tokens filled from ids.json"


def test_check_compares_counts(monkeypatch):
    its = items()
    ids = fake_ids(its)

    class FakeClient:
        def sparql(self, query):
            assert "{P:" not in query and "{Q:" not in query
            return [{"class": "x", "classLabel": "government agency", "n": "1"},
                    {"class": "x", "classLabel": "legal process", "status": "reviewed", "n": "1"}]
    out = []
    result = qs.check(its + qs.schema_items(SCHEMA), SCHEMA, ids, FakeClient(), log=out.append)
    assert "legal code" in result["missing"] and "government agency" not in result["missing"]
    assert result["expected"]["legal code"] == 2
    assert result["status_live"] == {"reviewed": 1}
    assert any("missing kinds" in l for l in out)


def test_readme_names_nobody():
    text = qs.readme([("01-properties.qs", Counter(commands=49, CREATE_PROPERTY=49))], 1, "abc1234")
    assert "@" not in text and not re.search(r"\b(reviewer|reviewed by)\b", text, re.I)
    assert "49" in text


def test_git_commit_is_short():
    c = qs.git_commit()
    assert c == "unknown" or re.fullmatch(r"[0-9a-f]{7,12}", c)


# ----------------------------------------------------------------------------------------- the generated packet
GENERATED = sorted(OUT.glob("0[1-5]-*.qs")) if OUT.exists() else []


@pytest.mark.skipif(not GENERATED, reason="no generated packet in out/wikibase/")
def test_generated_packet_round_trip():
    ids_path = OUT / "ids.json"
    ids = qs.Ids.load(ids_path) if ids_path.exists() else None
    try:
        from lexflow.publish import schema
        ids = ids or qs.Ids()
        ids.add_schema(schema)
    except ImportError:
        pass
    if ids is not None:
        known_q = set(ids.items.values()) | set(ids.labels.values())
        known_p = set(ids.properties.values())
    for path in GENERATED:
        text = path.read_text(encoding="utf-8")
        header, cmds = parse(text, path.name)
        assert len(text.rstrip("\n").split("\n")) <= 2000, path.name
        assert_header_matches(header, cmds)
        if path.name[:2] in ("01", "02", "03"):
            assert all(c.value not in ("novalue", "somevalue") for c in cmds), path.name
            for c in cmds:
                if c.kind == "statement":
                    assert c.subject == "LAST" and c.prop in ("P25", "P5", "P6", "P7", "P8"), f"{path.name}:{c.line_no}"
                    assert not c.qualifiers and not c.references
                    if ENTITY.match(c.value):
                        assert int(c.value[1:]) <= 75, f"{path.name}:{c.line_no}: pass 1 points at a new item"
            if path.name.startswith("03"):
                assert all(c.prop == "P25" for c in cmds if c.kind == "statement"), path.name
        else:
            assert ids is not None and ids_path.exists(), "pass 2 files need ids.json"
            for c in cmds:
                assert c.kind == "statement"
                assert c.subject in known_q | known_p, f"{path.name}:{c.line_no}: {c.subject}"
                assert c.prop in known_p, f"{path.name}:{c.line_no}: {c.prop}"
                for v in [c.value] + [v for _, v in c.qualifiers] + [v for g in c.references for _, v in g]:
                    if ENTITY.match(v):
                        assert v in known_q, f"{path.name}:{c.line_no}: {v}"
                    m = re.fullmatch(r"[+-]?[\d.]+U(\d+)", v)
                    if m:
                        assert "Q" + m.group(1) in known_q, f"{path.name}:{c.line_no}: unit {v}"
                for k, _ in c.qualifiers:
                    assert k in known_p, f"{path.name}:{c.line_no}: {k}"
                for g in c.references:
                    for k, _ in g:
                        assert "P" + k[1:] in known_p, f"{path.name}:{c.line_no}: {k}"
            src = ids.properties.get("source URL")
            quoted = ids.properties.get("quoted text")
            if src and quoted:
                assert_privacy_and_quotes(cmds, src, quoted)
        for mb in mailboxes(cmds):
            assert privacy.is_office_mailbox(mb), f"{path.name}: personal mailbox {mb}"
        for host in quotes.NO_REPRINT:
            for c in cmds:
                for v in [c.value] + [v for _, v in c.qualifiers] + [v for g in c.references for _, v in g]:
                    if host in v:
                        assert v.startswith('"http'), f"{path.name}:{c.line_no}: {host} words outside a URL"


@pytest.mark.skipif(not GENERATED, reason="no generated packet in out/wikibase/")
def test_generated_readme_lists_every_file():
    readme = (OUT / "README.md").read_text(encoding="utf-8")
    for path in GENERATED:
        assert f"`{path.name}`" in readme, path.name
    assert "https://lexipedia.wikibase.cloud/tools/quickstatements/#/batch" in readme
    assert "Project:Copyrights" in readme and "Project:People" in readme
    assert "@" not in readme


def test_ontology_equivalents_and_class_matches():
    from collections import OrderedDict
    """P7 per equivalent IRI on a new property (pass 1) and on an existing one (05-updates.qs); P8 per exact
    match on a new class item (pass 1); close match (a new property) as a pass-2 claim."""
    eli_about, sch_about = "http://data.europa.eu/eli/ontology#is_about", "https://schema.org/about"
    eli_lrs, sch_leg = "http://data.europa.eu/eli/ontology#LegalResourceSubdivision", "https://schema.org/Legislation"
    lkif_norm = "http://www.estrellaproject.org/lkif-core/norm.owl#Norm"
    schema = SimpleNamespace(
        PROPERTIES=[dict(order=48, label="topic", datatype="item", wikidata=None, description="t",
                         equivalents=[eli_about, sch_about]),
                    dict(order=60, label="close match", datatype="url", wikidata=None, description="c")],
        CLASSES=[dict(slug="norm", label="norm", description="n", qid="Q11", exact=[lkif_norm]),
                 dict(slug="statute", label="statute", description="s", exact=[eli_lrs], close=[sch_leg])],
        VOCAB=[], EXISTING=EXISTING,
        EXISTING_EQUIVALENTS={"part of": ("http://data.europa.eu/eli/ontology#is_part_of",), "follows": ()})
    (_, text), = qs.render(qs.properties_batch(schema), "abc1234")
    _, cmds = parse(text, "01-properties.qs")
    assert [(c.prop, c.value) for c in cmds if c.kind == "statement"] == [("P7", f'"{eli_about}"'), ("P7", f'"{sch_about}"')]
    class_items = qs.schema_items(schema)
    (_, text), = qs.render(qs.classes_batch(schema, class_items), "abc1234")
    _, cmds = parse(text, "02-classes.qs")
    assert [(c.prop, c.value) for c in cmds if c.kind == "statement" and c.prop == "P8"] == [("P8", f'"{eli_lrs}"')]
    ids = qs.Ids()
    ids.add_schema(schema)
    ids.properties.update({"topic": "P100", "close match": "P101"})
    ids.items["lexflow:class:statute"] = "Q1000"
    batches, updates = qs.claims_batches(OrderedDict(), ids, schema, class_items)
    (_, text), = qs.render(updates, "abc1234")
    _, up = parse(text, "05-updates.qs")
    assert ("P9", "P7", '"http://data.europa.eu/eli/ontology#is_part_of"') in [(c.subject, c.prop, c.value) for c in up]
    assert not any(c.subject == "P11" for c in up), "follows has no equivalent"
    (_, text), = qs.render(batches[0], "abc1234")
    _, cls = parse(text, "04-claims-classes.qs")
    assert [(c.subject, c.prop, c.value) for c in cls] == [("Q1000", "P101", f'"{sch_leg}"')]
