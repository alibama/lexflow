"""The two questions every government gets an answer for, and how each one is scored.

``seeds`` are section numbers where the answer is known to live.  They are hints, not
answers: the locator only uses one after finding it in the downloaded statutes, in force,
with matching words in its title or text.  Anything not seeded (or a seed that fails that
check) falls back to keyword ranking, and the method used is stored with the result.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    short: str
    title_strong: re.Pattern
    title_moderate: re.Pattern
    title_negative: re.Pattern
    text_required: re.Pattern | None
    text_features: tuple[re.Pattern, ...]
    seeds: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # headings that describe the procedure itself get a small boost (time limits, responses, fees)
    title_bonus: re.Pattern | None = None
    # LOCUS (local ordinance) matching
    local_header: re.Pattern | None = None
    # website crawl: link text / URL that marks the right page
    page_link: re.Pattern | None = None


RECORDS = Question(
    id="records",
    title="How do I request public records?",
    short="Public records",
    title_strong=re.compile(
        r"right (of|to) (access|inspect)|open to (public )?inspection|inspection and cop|procedure for request|"
        r"requests? for (public )?records|access to (public )?records|public records? (request|open|access|inspection)|"
        r"examination of (public )?records|time (limit|for response)|response to request", re.I),
    title_moderate=re.compile(r"public records?|freedom of information|open records|right[- ]to[- ]know|"
                              r"public information|inspection of records|records? request", re.I),
    title_negative=re.compile(r"exempt|exclusion|exception|confidential|destroy|destruction|theft|forg|archiv|"
                              r"disposition|retention|advisory|council|penalt|violation|definitions?\b|short title|"
                              r"immunity|correction of|essential|security|seizure|court records|vital records|"
                              r"land records|recordation|recorder", re.I),
    text_required=re.compile(r"record", re.I),
    text_features=(re.compile(r"\brequest", re.I), re.compile(r"within \w+ (\(\d+\) )?(working |business )?days", re.I),
                   re.compile(r"\binspect", re.I), re.compile(r"\bcop(y|ies)\b", re.I),
                   re.compile(r"custodian", re.I), re.compile(r"\bden(y|ial|ied)\b", re.I)),
    seeds={
        "al": ("36-12-40",), "ak": ("40.25.110", "40.25.120"), "az": ("39-121.01", "39-121"),
        "ca": ("7922.535", "7922.530", "7922.525"), "ct": ("1-210", "1-212"), "de": ("10003",),
        "dc": ("2-532",), "fl": ("119.07",), "hi": ("92F-11",), "id": ("74-102", "74-103"),
        "il": ("140/3",), "in": ("5-14-3-3",), "ia": ("22.2", "22.8"), "ks": ("45-218",),
        "ky": ("61.872", "61.880"), "la": ("44:32", "44:31"), "me": ("408-A",),
        "md": ("General Provisions § 4-203", "General Provisions § 4-202"),
        "mi": ("15.235", "15.233"), "mn": ("13.03",), "mo": ("610.023",), "mt": ("2-6-1006", "2-6-1003"),
        "ne": ("84-712",), "nv": ("239.0107", "239.010"), "nh": ("91-A:4",), "nj": ("47:1A-5",),
        "nm": ("14-2-8", "14-2-1"), "nc": ("132-6",), "nd": ("44-04-18",), "oh": ("149.43",),
        "ok": ("24A.5",), "or": ("192.324", "192.329"), "pa": ("67.701", "67.901"), "ri": ("38-2-3", "38-2-7"),
        "sc": ("30-4-30",), "sd": ("1-27-37", "1-27-1"), "tx": ("552.221", "552.301"), "ut": ("63G-2-204",),
        "va": ("2.2-3704",), "wa": ("42.56.520", "42.56.080"), "wv": ("29B-1-3",), "wi": ("19.35",),
        "wy": ("16-4-202",),
    },
    title_bonus=re.compile(r"request|respon|time limits?|deadline|costs?|fees?|charges", re.I),
    local_header=re.compile(r"public records?|freedom of information|\bfoia\b|open records|records? request|"
                            r"inspection of public records|right[- ]to[- ]know", re.I),
    page_link=re.compile(r"public records?|records? request|freedom of information|\bfoia\b|open records|"
                         r"right[- ]to[- ]know|records? custodian|\bopra\b|\bcpra\b|transparen", re.I),
)

BUSINESS = Question(
    id="business",
    title="How do I start a business?",
    short="Start a business",
    title_strong=re.compile(r"articles of organization|certificate of organization|certificate of formation|"
                            r"formation of (a )?limited liability compan|organizers?\b", re.I),
    title_moderate=re.compile(r"limited liability compan|articles of incorporation|incorporators?|"
                              r"formation|organization", re.I),
    title_negative=re.compile(r"amend|restat|surrender|cancel|foreign|cooperative|series|correction|merger|"
                              r"conversion|domestication|reinstat|dissol|nonprofit|non-profit|professional|"
                              r"low-profit|benefit|close corporation|bank|insurance|credit union|church|"
                              r"cemetery|homeowner|condominium|electric|water|telephone", re.I),
    text_required=re.compile(r"limited liability compan|corporation", re.I),
    text_features=(re.compile(r"limited liability compan", re.I),
                   re.compile(r"secretary of state|commission|department of state|mayor|division of corporations|"
                              r"registrar|department of commerce|filing office", re.I),
                   re.compile(r"\bfil(e|ed|ing)\b", re.I), re.compile(r"\bshall (set forth|state|contain)\b", re.I)),
    seeds={
        "va": ("13.1-1011", "13.1-1010"), "dc": ("29-802.01",), "de": ("18-201",), "ca": ("17702.01",),
        "tx": ("3.005", "3.001"), "md": ("Corporations and Associations § 4A-202",), "fl": ("605.0201",), "wa": ("25.15.071",), "id": ("30-25-201",),
        "ia": ("489.201",), "mn": ("322C.0201",), "ne": ("21-118", "21-117"), "nj": ("42:2C-31",),
        "ut": ("48-3a-201",), "wy": ("17-29-201",), "al": ("10A-5A-2.01",), "ky": ("275.025", "275.020"),
        "oh": ("1706.16",), "mi": ("450.4202",), "nc": ("57D-2-21", "57D-2-20"), "il": ("180/5-5",),
        "pa": ("8821",), "ma": ("12",), "nv": ("86.151",), "az": ("29-3201",), "or": ("63.047", "63.044"),
    },
    title_bonus=re.compile(r"formation|certificate of organization|articles of organization|filing", re.I),
    local_header=re.compile(r"business licen[cs]e|license tax|business registration|business tax|\bbpol\b|"
                            r"occupational licen[cs]e|business permit|general business|peddler|vendor licen", re.I),
    page_link=re.compile(r"business licen[cs]e|business tax|business registration|\bbpol\b|"
                         r"occupational licen[cs]e|start(ing)? a business|business permit|open a business", re.I),
)

QUESTIONS: dict[str, Question] = {q.id: q for q in (RECORDS, BUSINESS)}


def get(qid: str) -> Question:
    if qid not in QUESTIONS:
        raise ValueError(f"unknown question {qid!r}; expected one of {sorted(QUESTIONS)}")
    return QUESTIONS[qid]


def parse(arg: str | None) -> list[str]:
    if not arg or arg == "all":
        return list(QUESTIONS)
    return [get(q.strip()).id for q in arg.split(",") if q.strip()]
