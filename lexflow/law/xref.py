"""Cross-references between statute sections, read with the structure of the state's code.

``references(state, row, text=None)`` finds every reference in one index row's text and resolves it to index
rows.  Each :class:`Reference` has the exact span with character offsets, a ``kind``, the target ``code`` (the
index's citation prefix, or a name for law outside the index), the target ``sections`` (index ids and
citations), a ``pinpoint`` below section level, a ``unit`` for containers (index path, first section, size),
the ``role`` the reference plays for the citing rule, and a ``confidence``.  Deterministic, no model calls.

**How a reference is read.**

1. *Excluded text*: the section's own label ("§ 1101. Fees.", "(5 ILCS 140/2) (from Ch. 116, par. 202) Sec.
   2.", New York's starred label of a number with two versions, "* § 92-gg. Subway assistance fund.", and the
   editor's note on the versions, "* NB There are 2 § 92-gg's"), source notes ("(Source: P.A. ...)", "(Amended
   by Stats. ...)"), session-law history ("History: s. 10, ch. 67-125", "Code 1950, § 18.1-27; 1960, c. 358",
   "Added by Acts 2023 ...") and land-survey descriptions ("Section 23, Township 14 South").
2. *Law outside the index first*: a constitution citation ("subdivision (e) of Section 4 of Article VII of the
   California Constitution", "Article IX, Section 5(c) of the Constitution of the State of Illinois", "s. 24,
   Art. I of the State Constitution", "Section 59, Article XVI, Texas Constitution", New York's "section one of
   article seven of the state constitution") is taken whole, pinpoints and lists included, as kind
   ``constitution``; an uncodified session law ("Section 7 of Chapter 129 of the Statutes of 1999", "section 1
   of chapter 1040 of the laws of 1981", New York's budget-bill parts "section 3 of part A of chapter 57 of the
   laws of 2009", its chapters not yet numbered when the text was written, "section four of a chapter of the laws
   of two thousand five", "chapter forty-three of the laws of New Jersey of ...", "chapter 274, Laws of 2006",
   "Section 4, Chapter 697, Acts of the 62nd Legislature", "chapter 87-249, Laws of Florida", "Public Act
   96-731", "Session Laws 2018-146", "D.C. Law 2-38", Maryland's "CHAPTER 95 OF 2025", a California bill's own
   sections, "Section 8 of the act that added this section", "Section 1 of Assembly Bill 2257 of the 2021–22
   Regular Session", and a California initiative's, "Section 2 of Proposition 184", "Section 11 of the initiative
   act approved by a majority of the voters at the general election held on November 4, 1930") as kind
   ``session_law``; Texas "Article 8280-581, Vernon's Texas Civil Statutes" as ``other_code`` outside the index.
   None of them gets an index target: read with the code grammar, their "Section 4" or "Section 7" would resolve
   to the citing code's own § 4 or § 7.  Earlier items of a list that such a citation ends ("Section 5 and
   Section 7 of Chapter 130 of the Statutes of 2000", "section one or section two of chapter seven hundred
   seventy-two of the laws of ...") are that law's too when they are numbered like its first section, read
   inside the citation's own span (so "section 5 or part A of chapter 57 of the laws of 2009, as amended by
   section 3 ..." leaves "section 5" to the code grammar).  New York's "section two of such part" is a section of
   the part cited last before it: a session law's part gives the session law, with no target; a code's part
   ("part one-A of article six of the family court act ... section six hundred thirty-five of such part") gives
   that code's section only when the index holds it inside that part; with no part before it, no target.
3. *Spans*: a small grammar over the text.  Section words per state (``§``, ``Section``, Florida ``s.``/``ss.``,
   ``G.S.``, ``RCW``, Texas ``Article 45A.252``, New York's spelled-out "section two hundred five", its numbers
   with a letter repeated three to seven times, "§ 160-aaa", "section eleven hundred ninety-nine-hhhh", and its
   Uniform Commercial Code's double hyphen "Section 8--404"), pinpoint words (subsection, subdivision,
   paragraph, clause ...) chained with "of", units (Chapter, Title, Division, Part, Subtitle, Subchapter,
   Article) chained with "of" or commas, "(commencing with Section N)", "(§ N et seq.)", relative words ("this
   chapter", "that subsection", "herein"), lists joined by commas, "and", "or" (each item is its own reference;
   an item's designators replace the cited ones from its own level: "RCW 48.110.030 (2)(a) and (b), (3)" is
   (2)(a), (2)(b), (3)), ranges ("to", "through", "605.0903-605.0912", "inclusive", "(2)(a) through (c)").  A
   pinpoint after a comma belongs to the section before it ("G.S. 59-68, subdivision (b)(2)"); "such
   subdivision six" is the pinpoint cited last with that designator, not the citing section.  Federal
   citations, regulations, court rules and generic law ("any other provision of law") are recognised and get a
   kind, but no index target.  A federal law's name ends at an article, a verb, a word for police or courts, or a
   preposition that does not sit between capitalised words or inside a lower-case act's name ("the federal grant
   funds are subject to State law" is the generic "State law"; "federal Department of Labor regulations" and
   "the federal health information technology for economic and clinical health act" are federal), and "law"
   before "enforcement" or "-enforcement" is never law ("federal or State law-enforcement agency", "any other law
   enforcement agency").
4. *Code*: a qualifier after the list ("of the Penal Code", ", Penal Code", "of the Courts Article", "of the
   criminal procedure law", "of this article", "RCW", "of the General Statutes") names the code for the items
   before it, back to the previous qualifier.  Names come from a per-state table derived from the index: the
   distinct citation prefixes (with the name a prefix spells, "Tex. Penal Code" -> "Penal Code", "Md. Code,
   Criminal Law" -> "Criminal Law Article"), plus the names the codes and acts give themselves in their
   short-title sections ("This act shall be known as the Vehicle Code", "This Act may be cited as the Child
   Death Review Team Act"), plus a few documented aliases (Maryland's "Courts Article", California's code names
   behind its abbreviated prefixes).  With no qualifier a number resolves in the citing row's own code (a New
   York row's citation may star its number, "N.Y. STF Law § 92-GG*2": its code is still "N.Y. STF Law § "); a
   number never falls back to another code.  A code's root is the path prefix 95% of its rows share or, when a few odd
   rows keep any prefix below that share, the one most of them share ('Tex. Insurance Code - Not Codified':
   'TX Code / Code i1'); no code of the ten states' tables has an empty root.
5. *Targets*: the full citation (prefix + number) is looked up by the index's normalised citation, so a bare
   "10-105" can never pick up 18 sections of other Maryland articles.  ``sections`` holds what the text names: the
   section, every row of a range, the "(commencing with Section N)" or "(§ N et seq.)" anchor, a named act's
   short-title section.  That includes a law or code a short title names inside a code, whatever its last word:
   "the Maryland Vehicle Law" is Md. Transp. Titles 11 through 27 ("Titles 11 through 27 of this article may be
   cited as the Maryland Vehicle Law"), so its target is § 11-206 and its ``unit`` runs from Title 11 to
   ``through`` Title 27; "the Florida Evidence Code" is Fla. Stat. § 90.101.  A container's ``unit`` carries its
   index path, first section and size: "this chapter/article/title/..." walks up the citing row's path; named
   units walk down from the code's root; "(commencing with Section N)" takes the unit from N's own path, "(§ N
   et seq.)" the unit that begins at N.  A unit the paths do not hold but the numbering shows (RCW 23.95 Article
   2 = 23.95.2xx; G.S. 57D Part 2 of Article 9 = 57D-9-2x; 105 ILCS 5 Article 1E = 5/1E-*) lists its members, or
   only its first when it is large.
6. *Role*: from cue words around the span (as defined in, notwithstanding, except as provided, subject to,
   punishable as provided in, has obtained ... under, regulations adopted pursuant to, in accordance with, if,
   As used in, violation of ...), nearest cue first; see :func:`role_of`.

Measured with ``scripts/xref_eval.py`` on the hand-labelled gold (fixtures/xref/gold_{a,b,c}.json: 82 sections,
10 states, 893 references): specific references detected 99.9%, generic law 78% (57 of 73), target section ids
precision 1.000 / recall 0.969 (``retrieve.cited``: 0.975 / 0.349), role accuracy 70.1% (69.2% without N.Y.
LLC Law § 1101, the 27-item fee schedule where the fee-schedule rule does most of its work; 68.6% with that rule
off), kind accuracy 86.1%.  These numbers are in-sample: the rules were written while reading all three files
(and the three files disagree on some roles, e.g. "Subject to X" is condition in one, exception in two).  Cue
and generic-law phrases that occur in only a few sections of the corpus, written for single gold sentences, were
removed ("copyright or trade secret laws", "its published rules", "statutory fees", "other statute of
limitations", "penalties and provisions of", "venue provisions of", "limitations period set forth in", "conflict
or inconsistency between", "as described and defined in") or replaced by the general form they are an instance of
("constitutional right", rules, regulations or procedures adopted by or under a body, "principles of law and
equity", deadlines or time limits set forth in, a fee schedule's item as any 'For ...' clause naming an amount,
other than a 'For purposes of ...' clause);
expect role accuracy nearer 65% on unseen sections.

Outside the gold (docs/design/verify-resolver.md).  On the 30 random sections the verification read by hand, the
64 outward target ids it confirmed are kept and its two misses (N.Y. UCC "Section 8--404", "Section 8--405")
resolve: 66 of 66, no false id (its Re-check 2; the 30 were not re-read after the last round below).  Phrases with
an id in the citing code, in Re-check 2's corpus scans: New York sections of a part of a session law 40 of 56 -> 0,
lists before a session law 7 of 55 -> 0, California "Section N of the act that added this section" 41 of 78 -> 0
and "Section N of Assembly/Senate Bill M" 4 of 9 -> 0.  The last round (2026-10-11), scanning every section that
has the form: New York "section N of a chapter of the laws of YYYY" 12 of 14 phrases (11 sections) -> 0;
"section N of such part" 4 of 7 (4 sections) -> 0, and one of the 7 now gets the right section of another law
(Soc. Serv. Law § 384-b -> Fam. Ct. Act § 635); California "Section 2 of Proposition 184" and "Section 11 of the
initiative act approved by ..." 3 of 3 -> 0; New York repeated-letter numbers ("§ 160-aaa"; sections under
150,000 characters) 170 of 330 phrases (159 sections) with another section's id -> 0, 324 of them now with the
section named; "law-enforcement" with a hyphen (all ten states, sections under 200,000 characters), 3,684 phrases
in 1,389 sections: 144 read as federal or generic law -> 0, and "other / by / general / under law enforcement" in
five states (Va., N.C., D.C., Md., Wash.) 195 of 430 -> 0.  In 800 sampled sections that contain "federal"
(seeds 3131 and 7272), federal references 952 -> 949: the four lost name no federal law ("federal courts to
comparable antitrust statutes", "Federal courts rule that ...", "federal aid in accordance with law", now the
generic "in accordance with law", "federal write-in absentee ballots for failure to meet certain requirements"),
and the one gained does ("the Federal 1933 Act").
A random diff (seed 5150, 40 sections per state): outward ids 529 -> 529; only starred labels and version notes
stop being references.
"""
from __future__ import annotations

import bisect
import dataclasses
import functools
import re
import sqlite3
from pathlib import Path

from ..ask import index as I
from ..municipal import statutes

ROLES = ("definition", "override", "exception", "penalty", "prerequisite_process", "authority", "procedure",
         "condition", "scope", "other")
KINDS = ("section", "pinpoint", "list_item", "range", "container", "internal_relative", "other_code",
         "named_act", "session_law", "federal", "constitution", "regulation", "court_rule", "generic")
# kinds that never carry an index target: law outside the codes the index holds
NO_TARGET_KINDS = ("session_law", "federal", "constitution", "regulation", "court_rule", "generic")


@dataclasses.dataclass
class Reference:
    span: str
    start: int
    end: int
    kind: str
    code: str | None                   # citation prefix of the target code ("Cal. PEN § "), or a name outside it
    sections: list[dict]               # [{"id": 22375, "citation": "Fla. Stat. § 607.0201"}, ...]
    pinpoint: str | None
    role: str
    confidence: float
    unit: dict | None = None           # {"path", "first": {"id", "citation"} | None, "sections": n, "exact"}
    #                                    (+ "through": the last unit's path, for a run of units like Titles 11-27)
    list_group: int | None = None      # items of one coordinated list share a number
    note: str | None = None            # repealed | not in index | numbering | anaphor | ...

    @property
    def ids(self) -> list[int]:
        return [s["id"] for s in self.sections]

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)


# ------------------------------------------------------------------ lexical pieces
_D = "[-–—]"                                          # hyphen, en dash, em dash
# New York's Uniform Commercial Code writes a double hyphen ('Section 8--404' = N.Y. UCC Law § 8-404); a double
# hyphen joins only digits, so a dash in running text ('section 5--to the extent') stays out.  New York also
# numbers with a letter repeated three to seven times ('§ 160-aaa', 'section eleven hundred ninety-nine-hhhh' = N.Y.
# Pub. Auth. Law § 1199-HHHH); read as '160' or '1199', they would resolve to another section
_REP = "(?:" + "|".join(f"[{c.upper()}{c}]{{3,7}}" for c in "abcdefghijklmnopqrstuvwxyz") + ")"
NUM = (rf"\d+[A-Za-z]{{0,3}}(?:(?:[.:]|{_D})(?:\d+[A-Za-z]{{0,3}}|(?:[A-Za-z]{{1,2}}|{_REP})(?![A-Za-z]))"
       rf"|--\d+[A-Za-z]{{0,3}})*")
PAREN = r"\((?:[A-Za-z]{1,5}|\d{1,3}(?:\.\d+)?[A-Za-z]{0,2}|[A-Za-z]{1,2}-\d+|\d+-\d+)\)"
PIN = rf"(?:{PAREN})+(?:\d{{1,2}}(?![\w.]))?"
_W = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
      "seventeen eighteen nineteen").split()
_T = "twenty thirty forty fifty sixty seventy eighty ninety".split()
NUMWORD = "(?:" + "|".join(sorted(_W + _T + ["hundred", "thousand"], key=len, reverse=True)) + ")"
NUMWORDS = rf"(?i:{NUMWORD}(?:(?:\s+|-)(?:and\s+)?{NUMWORD})*)(?:-(?:[A-Za-z]{{1,2}}|{_REP})(?![A-Za-z]))?"
SUB_KW = (r"\b(?:[Ss]ub(?:sections?|divisions?|paragraphs?|clauses?|items?|parts?)|[Pp]aragraphs?|[Cc]lauses?"
          r"|[Ii]tems?|SUB(?:SECTIONS?|DIVISIONS?|PARAGRAPHS?)|PARAGRAPHS?)\b")
UNIT_KW = (r"\b(?:[Ss]ub)?(?:[Cc]hapters?|[Tt]itles?|[Pp]arts?)\b|\b(?:[Aa]rticles?|[Dd]ivisions?)\b"
           r"|\b(?:SUB)?(?:CHAPTERS?|TITLES?|PARTS?)\b|\b(?:ARTICLES?|DIVISIONS?)\b")
UNIT_DESIG = (rf"(?:\d+[A-Za-z]{{0,2}}(?:\.\d+[A-Za-z]?)*(?:{_D}[A-Z](?![A-Za-z]))?"
              rf"|[IVXLC]+(?:{_D}[A-Z])?(?![A-Za-z])|[A-Z]{{1,2}}(?![A-Za-z]))")
SUB_DESIG = rf"(?:{PIN}|[A-Z]\d{{0,2}}(?![\w])|\d{{1,3}}(?![\w.\-])|{NUMWORDS})"
REL_LEVELS = ("section", "subsection", "subdivision", "paragraph", "subparagraph", "clause", "subclause", "item",
              "definition", "sentence", "chapter", "subchapter", "article", "title", "subtitle", "part", "subpart",
              "division", "act", "code", "law")
REL = (r"\b(?P<det>[Tt]his|[Tt]hat|[Tt]hese|[Tt]hose|THIS)\s+(?P<lvl>(?i:" + "|".join(
    sorted((w + "s?" for w in REL_LEVELS), key=len, reverse=True)) + r"))\b")
SECTION_LEVELS = {"section", "subsection", "subdivision", "paragraph", "subparagraph", "clause", "subclause",
                  "item", "definition", "sentence"}
SEP = re.compile(r"(?:\s*,\s*(?:(?:and/or|and|or|nor)\s+)?|\s+(?:and/or|and|or|nor)\s+|\s*;\s*(?:(?:and|or)\s+)?"
                 r"(?=§))")
MEASURE = re.compile(r"\s*(?:%|percent|per\s?cent|days?|years?|months?|weeks?|hours?|minutes?|dollars?|cents?|"
                     r"feet|foot|miles?|inches?|acres?|times|persons?|members?|votes?|copies|pages?|units?|work|"
                     r"calendar|business|or\s+more|or\s+less|or\s+fewer)\b", re.I)
RANGE_SEP = re.compile(rf"\s*(?:to|through|thru|{_D})\s*(?:and\s+including\s+)?", re.I)
INCLUSIVE = re.compile(r",?\s*inclusive\b", re.I)
ROMAN = re.compile(r"^(?=[ivxlc]+$)c{0,3}(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})$")

FED_ACTS = ("health insurance portability and accountability act", "hitech act", "health information technology "
            "for economic and clinical health act", "electronic signatures in global and national commerce act",
            "family educational rights and privacy act", "social security act", "internal revenue code",
            "fair credit reporting act", "americans with disabilities act", "national labor relations act",
            "freedom of information act", "privacy act of 1974", "fair labor standards act", "clean water act",
            "clean air act", "employee retirement income security act", "immigration and nationality act",
            "controlled substances act", "bankruptcy code", "help america vote act", "national voter registration "
            "act")
# 'law enforcement', 'law-enforcement': police, not law
NOT_ENF = r"(?![\s\-]+enforcement\b)"
# A word inside a federal law's name ('federal and/or state law', 'federal motor carrier safety regulations').
# An article or determiner, a verb or a relative word ends the name ('a federal or State program allowing a law
# ...', 'the federal grant funds are subject to State law'), and so do police ('federal or State law-enforcement
# agency') and courts ('federal or State court rules' are court rules).  A preposition ends it too ('the federal
# agency in accordance with State law'), except between capitalised words ('federal Department of Labor
# regulations', 'the federal Americans with Disabilities Act') and, before the head word 'act', in a name written
# in lower case ('section 13402 of the federal health information technology for economic and clinical health
# act'); 'to' ends even an act's name ('the federal agency to act').
_FED_STOP = (r"(?:a|an|the|any|this|that|these|those|such|its|their|each|every|no|not|is|are|was|were|be|been|being|"
             r"shall|may|must|will|would|should|can|could|might|has|have|had|do|does|did|allowing|allows?|allowed|"
             r"authori[sz]ed|authori[sz]ing|having|concerning|regarding|relating|related|requiring|required|provided|"
             r"providing|applies|apply|subject|pursuant|according|accordance|including|except|which|who|whom|whose|"
             r"where|when|whether|if|unless|than|as|but|to|courts?)")
_FED_PREP = (r"(?:in|into|with|within|without|for|on|at|from|by|under|upon|over|after|before|between|among|against|"
             r"through|during|about|per|via|of)")
_CAPS = (r"(?-i:[A-Z])[A-Za-z\-]*(?:\s+(?:of|with|for|in|on|to|the|and|from|under|by|at)\s+(?-i:[A-Z])"
         r"(?![A-Za-z\-]*enforcement\b)[A-Za-z\-]*)*")
# (an act's name ends at 'Act': 'the federal Social Security Act and federal regulations' is two references)
FED_WORD = rf"(?!(?:{_FED_STOP}|{_FED_PREP}|acts?)\b)(?![A-Za-z\-]*enforcement\b)(?:{_CAPS}|and/or|[A-Za-z][A-Za-z\-]*)"
# (an act's name may hold a year: 'Section 506 of the Federal 1933 Act')
FED_ACT_WORD = rf"(?!{_FED_STOP}\b)(?![A-Za-z\-]*enforcement\b)(?:{_CAPS}|and/or|[A-Za-z0-9][\w\-]*)"
# codes whose sections are cited as articles ("Article 45A.252"); there "this article" is the section itself
ARTICLE_SECTIONS = {"tx": ("Tex. Code of Criminal Procedure",)}
# states where "subdivision" is the first level below the section (elsewhere it is the second, after subsection)
SUBDIVISION_FIRST = {"ca", "ny"}
# a unit the index paths do not hold but the numbering shows (RCW 23.95 Article 2 = 23.95.2xx) lists its member
# sections as targets when it is small; a larger one (an article of the Illinois School Code) only its first
MAX_MEMBERS = 25
ALIASES = {   # names the texts use that neither the prefixes nor the short titles spell
    # California's prefixes are abbreviations; the codes' own names (from their § 1 short titles) back them up
    # where an index lacks the short-title section
    "ca": {f"{name} code" if not name.endswith("procedure") else name: f"Cal. {abbr} § " for abbr, name in (
        ("BPC", "business and professions"), ("CIV", "civil"), ("CCP", "code of civil procedure"),
        ("COM", "commercial"), ("CORP", "corporations"), ("EDC", "education"), ("ELEC", "elections"),
        ("EVID", "evidence"), ("FAM", "family"), ("FIN", "financial"), ("FGC", "fish and game"),
        ("FAC", "food and agricultural"), ("GOV", "government"), ("HNC", "harbors and navigation"),
        ("HSC", "health and safety"), ("INS", "insurance"), ("LAB", "labor"), ("MVC", "military and veterans"),
        ("PEN", "penal"), ("PROB", "probate"), ("PCC", "public contract"), ("PRC", "public resources"),
        ("PUC", "public utilities"), ("RTC", "revenue and taxation"), ("SHC", "streets and highways"),
        ("UIC", "unemployment insurance"), ("VEH", "vehicle"), ("WAT", "water"), ("WIC", "welfare and institutions"))},
    "md": {"courts article": "Md. Code, Courts and Judicial Proceedings § ",
           "courts and judicial proceedings article": "Md. Code, Courts and Judicial Proceedings § ",
           "corporations and associations article": "Md. Code, Corporations and Associations § ",
           "corps. and ass'ns article": "Md. Code, Corporations and Associations § "},
    "ny": {"civil practice law and rules": "N.Y. CVP Law § ", "cplr": "N.Y. CVP Law § ",
           "vehicle and traffic law": "N.Y. VAT Law § ", "penal law": "N.Y. PEN Law § ",
           "criminal procedure law": "N.Y. CPL Law § ", "business corporation law": "N.Y. BSC Law § ",
           "not-for-profit corporation law": "N.Y. NPC Law § ", "limited liability company law": "N.Y. LLC Law § ",
           "public officers law": "N.Y. PBO Law § ", "civil rights law": "N.Y. CVR Law § ",
           "executive law": "N.Y. EXC Law § ", "general business law": "N.Y. GBS Law § ",
           "partnership law": "N.Y. PTR Law § ", "correction law": "N.Y. COR Law § ",
           "education law": "N.Y. EDN Law § ", "public health law": "N.Y. PBH Law § ",
           "social services law": "N.Y. SOS Law § ", "tax law": "N.Y. TAX Law § ", "labor law": "N.Y. LAB Law § ",
           "judiciary law": "N.Y. JUD Law § ", "legislative law": "N.Y. LEG Law § ",
           "retirement and social security law": "N.Y. RSS Law § ", "family court act": "N.Y. FCT Law § ",
           "general municipal law": "N.Y. GMU Law § ", "insurance law": "N.Y. ISC Law § ",
           "mental hygiene law": "N.Y. MHY Law § ", "real property law": "N.Y. RPP Law § ",
           "state finance law": "N.Y. STF Law § ", "banking law": "N.Y. BNK Law § ",
           "environmental conservation law": "N.Y. ENV Law § ", "election law": "N.Y. ELN Law § ",
           "general obligations law": "N.Y. GOB Law § ", "public authorities law": "N.Y. PBA Law § ",
           "county law": "N.Y. CNT Law § ", "town law": "N.Y. TWN Law § ", "village law": "N.Y. VIL Law § "},
}
SINGLE_NAMES = {"va": ("code of virginia", "code of virginia, 1950"), "fl": ("florida statutes", "f.s."),
                "nc": ("general statutes", "general statutes of north carolina"),
                "wa": ("revised code of washington", "rcw"), "dc": ("d.c. official code", "district of columbia "
                                                                    "official code", "d.c. code")}
STATE_WORDS = ("california", "new york", "new york state", "illinois", "virginia", "maryland", "texas", "florida",
               "washington", "north carolina", "district of columbia", "d.c.")


# ------------------------------------------------------------------ the code table (derived from the index)
@dataclasses.dataclass
class Table:
    state: str
    prefixes: dict            # prefix -> {"root": path, "n": rows}
    single: str | None        # the prefix of a one-code state
    names: dict               # normalised name -> {"prefix", "unit", "anchor": (id, citation) | None, "kind"}
    units: dict               # path -> [min_id, max_id, rows, first_id, first_citation]
    children: dict            # path -> [(level, designator, child path)]


def _prefix(citation: str) -> str:
    """'Cal. PEN § 1170.125' -> 'Cal. PEN § '.  New York marks a second version of a section number with a star
    ('N.Y. STF Law § 92-GG*2', 'N.Y. LAB Law § 850*'): the star belongs to the number, so the prefix is the law's
    ('N.Y. STF Law § '), not 'N.Y. STF Law § 92-GG*', which would read 'section two' as § 92-GG*2 itself."""
    c = (citation or "").split(";")[0].strip()
    return re.sub(r"\[?[\w.\-:,–*]+\]?$", "", c)


def _comp(c: str) -> tuple[str, str]:
    """A path component as (level, designator): 'Chapter 09' -> ('chapter', '9'), 'Article 2 - Formation' ->
    ('article', '2'), 'Code bpc' -> ('code', 'bpc')."""
    c = re.split(r"\s+-\s+", c.strip(), maxsplit=1)[0]
    parts = c.split(None, 1)
    if len(parts) < 2:
        return parts[0].lower() if parts else "", ""
    return parts[0].lower(), _desig(parts[1])


def _desig(d: str) -> str:
    d = re.sub(rf"\s*{_D}\s*", "-", d.strip().lower().strip("."))
    return re.sub(r"^0+(?=\d)", "", d)


def norm_name(s: str) -> str:
    s = (s or "").lower().replace("’", "'").replace("&", " and ")
    s = re.sub(r"[\"“”]", "", s)
    s = re.sub(rf"\s*{_D}\s*", "-", s)
    s = re.sub(r"[^a-z0-9\-.' ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    return re.sub(r"^the ", "", s)


def _variants(name: str) -> set[str]:
    """A name as the texts may write it: without 'of California', 'of 1963', a leading state name, or a
    parenthetical ('Florida RICO (Racketeer Influenced and Corrupt Organization) Act' -> 'Florida RICO Act' and
    'Racketeer Influenced and Corrupt Organization Act')."""
    n = norm_name(name)
    out = {n, norm_name(re.sub(r"\s*\([^)]*\)", "", name or ""))}
    m = re.search(r"\(([^)]{4,})\)\s*(act|code|law)\W*$", name or "", re.I)
    if m:
        out.add(norm_name(f"{m.group(1)} {m.group(2)}"))
    for _ in range(2):
        for v in list(out):
            out.add(re.sub(r"\s+of\s+(?:the\s+state\s+of\s+)?(?:" + "|".join(STATE_WORDS) + r")$", "", v))
            out.add(re.sub(r"\s+of\s+\d{4}$", "", v))
            out.add(re.sub(r"^(?:" + "|".join(STATE_WORDS) + r")\s+", "", v))
    return {v for v in out if len(v) > 4}


SHORT_TITLE = re.compile(
    r"\b(?i:this|the)\s+(?P<lvl>(?i:act|code|chapter|article|title|part|division|law|subtitle|subchapter))\b"
    r"[^.;]{0,60}?\b(?i:shall|may)\s+be\s+(?i:known|cited|referred\s+to|designated)"
    r"(?:\s+(?i:and|or)\s+(?:(?i:may|shall)\s+be\s+)?(?i:cited|known|referred\s+to))?\s+(?i:as|by)\s+"
    r"(?:(?i:the)\s+)?(?:[\"“'‘](?P<q>[^\"”’]{2,140}?)\.?[\"”’']"
    r"|(?P<name>[A-Za-z][^\"”’;:()\n]{2,140}?)(?=\s*(?:[.;,(]|$|\s+and\s+(?:may|shall)|\s+or\s+)))", re.S)
# 'Sections 895.01-895.06 shall be known as the "Florida RICO (...) Act."': the act is that range of sections
SHORT_TITLE_RANGE = re.compile(
    rf"\b(?i:sections?)\s+(?P<nums>{NUM}(?:\s+(?i:through|to)\s+{NUM})?)\s+(?i:shall|may)\s+be\s+(?i:known|cited|"
    r"referred\s+to)(?:\s+(?i:and|or)\s+(?:(?i:may|shall)\s+be\s+)?(?i:cited|known))?\s+(?i:as)\s+(?:(?i:the)\s+)?"
    r"(?:[\"“'‘](?P<q>[^\"”’]{2,140}?)\.?[\"”’']|(?P<name>[A-Z][^\"”’;:()\n]{2,140}?)"
    r"(?=\s*[.;,(]))", re.S)
# 'Titles 11 through 27 of this article may be cited as the Maryland Vehicle Law': the law is those units, not the
# article the sentence ends its subject with
SHORT_TITLE_UNITS = re.compile(
    rf"\b(?P<lvl>(?i:titles|subtitles|chapters|subchapters|parts|articles|divisions))\s+(?P<a>{UNIT_DESIG})\s+"
    rf"(?i:through|to)\s+(?P<b>{UNIT_DESIG})(?:\s+(?i:of\s+this)\s+(?P<of>[A-Za-z]+))?\s+(?i:shall|may)\s+be\s+"
    r"(?i:known|cited|referred\s+to)(?:\s+(?i:and|or)\s+(?:(?i:may|shall)\s+be\s+)?(?i:cited|known))?\s+(?i:as)\s+"
    r"(?:(?i:the)\s+)?(?:[\"“'‘](?P<q>[^\"”’]{2,140}?)\.?[\"”’']|(?P<name>[A-Z][^\"”’;:()\n]{2,140}?)(?=\s*[.;,(]))",
    re.S)
NAMEWORD = re.compile(r"(?:act|code|law|article|compact|rules|charter|ordinance)(?:\s+of\s+\d{4})?$")


def _index_file(state: str) -> Path | None:
    p = I.path(state)
    return p if p.exists() else None


def _connect(p: Path) -> sqlite3.Connection:
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True, timeout=60, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def table(state: str) -> Table | None:
    """The state's code table, built once per index file (a second or so for the largest states)."""
    p = _index_file(state)
    if not p:
        return None
    st = p.stat()
    return _table(state, str(p), st.st_mtime_ns, st.st_size)


@functools.lru_cache(maxsize=16)
def _table(state: str, path: str, mtime: int, size: int) -> Table:
    con = _connect(Path(path))
    try:
        prefixes: dict[str, dict] = {}
        roots: dict[str, dict] = {}
        units: dict[str, list] = {}
        children: dict[str, set] = {}
        for r in con.execute("SELECT id, citation, path FROM sec ORDER BY id"):
            pre = _prefix(r["citation"])
            comps = [c for c in (r["path"] or "").split(" / ") if c][:-1]
            e = prefixes.setdefault(pre, {"n": 0})
            e["n"] += 1
            cnt = roots.setdefault(pre, {})
            for k in range(1, min(3, len(comps)) + 1):
                key = " / ".join(comps[:k])
                cnt[key] = cnt.get(key, 0) + 1
            for k in range(1, len(comps) + 1):
                u = " / ".join(comps[:k])
                x = units.get(u)
                if x is None:
                    units[u] = [r["id"], r["id"], 1, r["id"], r["citation"]]
                    if k > 1:
                        lvl, d = _comp(comps[k - 1])
                        children.setdefault(" / ".join(comps[:k - 1]), set()).add((lvl, d, u))
                else:
                    x[1] = r["id"]
                    x[2] += 1
        # a code's root: a path prefix that 95% of its rows share (a few rows carry odd paths), at the depth most of
        # the state's rows have their code at ('California Code / Code pen', 'Illinois Code / Chapter 805 / Act 180')
        shared = {pre: [k for k, c in cnt.items() if c >= 0.95 * prefixes[pre]["n"]] for pre, cnt in roots.items()}
        depths: dict[int, int] = {}
        for pre, ks in shared.items():
            if ks:
                d = max(k.count(" / ") for k in ks)
                depths[d] = depths.get(d, 0) + prefixes[pre]["n"]
        total = sum(e["n"] for e in prefixes.values()) or 1
        depth = max(depths, key=depths.get) if depths else 0
        for pre, ks in shared.items():
            e = prefixes[pre]
            if e["n"] > 0.99 * total:        # a one-code state: its first level ('Virginia Code')
                ks = [k for k in ks if k.count(" / ") == 0]
            fit = [k for k in ks if k.count(" / ") <= depth]
            if not fit:
                # no prefix 95% of the rows share, because the odd rows are too many for a small code ('Tex.
                # Insurance Code - Not Codified': 64 of 68 rows under 'TX Code / Code i1', 4 under 'Texas Code /
                # Code i1'): the deepest prefix, at the code depth, that most of its rows share
                fit = [k for k, c in roots[pre].items() if c > 0.5 * e["n"] and k.count(" / ") <= depth]
            e["root"] = max(fit, key=lambda k: (k.count(" / "), roots[pre][k])) if fit else ""
        total = sum(e["n"] for e in prefixes.values()) or 1
        top = max(prefixes, key=lambda k: prefixes[k]["n"]) if prefixes else None
        single = top if top and prefixes[top]["n"] / total > 0.99 else None
        names: dict[str, dict] = {}

        def add(name, entry, force=False):
            for v in _variants(name):
                if force or v not in names:
                    names[v] = entry

        for pre, e in prefixes.items():                      # the names the prefixes spell
            entry = {"prefix": pre, "unit": e["root"], "anchor": None, "kind": "code", "name": pre.strip(" §/")}
            p = pre.strip().rstrip("§/").strip(" ,")
            if state == "tx" and p.startswith("Tex. "):
                add(p[5:], entry)
            elif state == "md" and "," in p:
                base = p.split(",", 1)[1].strip()
                add(base + " Article", entry)
            if re.search(r"\b(?:Code|Law|Statutes)$", p) and state not in ("tx", "md"):
                add(p, entry)
        _short_titles(con, prefixes, add, children)
        for name in SINGLE_NAMES.get(state, ()):
            if single:
                add(name, {"prefix": single, "unit": prefixes[single]["root"], "anchor": None, "kind": "code",
                           "name": name}, force=True)
        for name, pre in ALIASES.get(state, {}).items():
            if pre in prefixes and norm_name(name) not in names:
                add(name, {"prefix": pre, "unit": prefixes[pre]["root"], "anchor": None, "kind": "code",
                           "name": name})
        return Table(state, prefixes, single, names, units, {k: sorted(v) for k, v in children.items()})
    finally:
        con.close()


def _short_titles(con, prefixes, add, children=None):
    """Names from short-title sections: 'This act shall be known as the Vehicle Code' names the code (the unit is
    the code's root); 'This article shall be known as the Setoff Debt Collection Act' names a unit inside it;
    'Titles 11 through 27 of this article may be cited as the Maryland Vehicle Law' names a run of units."""
    try:
        rows = con.execute("""SELECT s.id, s.citation, s.path, substr(b.text, 1, 2500) AS text FROM fts
                              JOIN sec s ON s.id = fts.rowid JOIN body b ON b.id = s.id
                              WHERE fts MATCH '"known as" OR "cited as" OR "referred to as"' ORDER BY s.id""")
        rows = rows.fetchall()
    except sqlite3.Error:
        return
    found = []
    for r in rows:
        spans = []
        for m in SHORT_TITLE_UNITS.finditer(r["text"] or ""):
            name = " ".join((m.group("q") or m.group("name") or "").split())
            if not name or not any(NAMEWORD.search(v) for v in _variants(name)):
                continue
            spans.append((m.start(), m.end()))
            lvl = _unit_level(m.group("lvl"))
            path = r["path"] or ""
            parent = _ancestor(path, m.group("of").lower()) if m.group("of") else None
            if parent is None:              # the units sit beside the one that holds the short title
                own = _ancestor(path, lvl)
                parent = own.rsplit(" / ", 1)[0] if own else _parent(_parent(path))
            lo, hi = natkey(_desig(m.group("a"))), natkey(_desig(m.group("b")))
            members = [p for cl, d, p in (children or {}).get(parent, ()) if cl == lvl and lo <= natkey(d) <= hi]
            members.sort(key=lambda p: natkey(_comp(p.rsplit(" / ", 1)[-1])[1]))
            add(name, {"prefix": _prefix(r["citation"]), "unit": None, "units": members, "kind": "act",
                       "anchor": (r["id"], r["citation"]), "name": name})
        for m in SHORT_TITLE.finditer(r["text"] or ""):
            if any(a < m.end() and m.start() < b for a, b in spans):
                continue
            name = " ".join((m.group("q") or m.group("name") or "").split())
            if not name or not any(NAMEWORD.search(v) for v in _variants(name)):   # 'Penal Code of California'
                continue
            found.append((m.group("lvl").lower(), name, r))
        for m in SHORT_TITLE_RANGE.finditer(r["text"] or ""):
            name = " ".join((m.group("q") or m.group("name") or "").split())
            nums = re.split(r"\s+(?i:through|to)\s+", m.group("nums"))
            ends = tuple(nums) if len(nums) == 2 else _split_range(norm_num(nums[0])) or (nums[0], nums[0])
            if name and any(NAMEWORD.search(v) for v in _variants(name)):
                add(name, {"prefix": _prefix(r["citation"]), "unit": _parent(r["path"] or ""), "kind": "act",
                           "anchor": (r["id"], r["citation"]), "range": tuple(norm_num(x) for x in ends), "name": name})
    for lvl, name, r in found:
        pre = _prefix(r["citation"])
        root = prefixes.get(pre, {}).get("root", "")
        unit = _ancestor(r["path"] or "", lvl) if lvl not in ("code", "law") else None
        if unit is None:
            # no such level in the path: 'This chapter' of a New York law is the law; 'This act' in Florida is
            # the chapter that holds the short title (Cal. 'This act shall be known as the Vehicle Code': the code)
            unit = root if lvl in ("code", "law", "chapter") else _parent(r["path"] or "")
        kind = "code" if unit == root else "act"
        add(name, {"prefix": pre, "unit": unit, "anchor": (r["id"], r["citation"]), "kind": kind, "name": name})


def _ancestor(path: str, level: str) -> str | None:
    comps = [c for c in path.split(" / ") if c][:-1]
    for k in range(len(comps) - 1, 0, -1):
        if _comp(comps[k])[0] == level:
            return " / ".join(comps[:k + 1])
    return None


def _parent(path: str) -> str:
    comps = [c for c in path.split(" / ") if c]
    return " / ".join(comps[:-1])


# ------------------------------------------------------------------ excluded text
# a New York section with two versions starts its label with a star ('* § 92-gg. Subway assistance fund.')
LABEL = re.compile(r"^\s*(?:(?:\([^()]*\bILCS\b[^()]*\)\s*)+(?:\((?:from|was|formerly)\b[^()]*(?:\([^()]*\)[^()]*)*"
                   r"\)\s*)*(?:Sec\.\s*[\w.\-]+\.?)?|(?:\*{1,2}\s*)?(?:§+|Section\.?)\s*[\w.\-–:]*\d[\w\-–:]*\.(?=\s))")
# N.Y. '§ 220.65 Criminal'
LABEL_LOOSE = re.compile(r"^\s*(?:\*{1,2}\s*)?(?:§+|Section\.?)\s*[\w.\-–:]*\d[\w.\-–:]*(?=\s)")
LABEL_STATES = {"ny", "nc", "md"}
# the New York editor's note on such a section ('* NB There are 2 § 92-gg's') names the section's own number
NB_VERSIONS = re.compile(r"(?m)^[ \t]*\*\s*NB\s+There\s+are\s+\d+\s+§[^\n]*")
SOURCE = re.compile(r"\((?:Source|Added|Amended|Repealed|Renumbered|Enacted)\b[^()]*(?:\([^()]*\)[^()]*)*\)")
HISTORY = re.compile(r"(?:^|\n)\s*(?:History\s*[:.—-]|Added\s+by\s+Acts|Amended\s+by\s*:|Acts\s+\d{4},|"
                     r"Code\s+1950\b|\d{4},\s*cc?\.\s*\d|\(?\d{4}\)?\s*,\s*(?:c|ch|chap)\.\s*\d|L\.\s?\d{4},)")
FL_HISTORY = re.compile(r"\bHistory\s*[:.—-]")


def excluded(text: str, state: str = "") -> list[tuple[int, int]]:
    """Text that is not statute: the section's own label, source notes, the session-law history and New York's
    note on a section number with two versions ('* NB There are 2 § 92-gg's')."""
    zones = []
    m = LABEL.match(text) or (LABEL_LOOSE.match(text) if state in LABEL_STATES else None)
    if m and m.end() > 0:
        zones.append((0, m.end()))
    if state in LABEL_STATES:                     # a second version's label ('§10–401. ** TAKES EFFECT ...')
        zones += [(m.start(1), m.end(1)) for m in re.finditer(r"(?:^|\n)\s*(?:\*{1,2}\s*)?(§\s*\d[\w.\-–:]*\.)(?=\s)",
                                                               text)]
    if state == "ny":
        zones += [(m.start(), m.end()) for m in NB_VERSIONS.finditer(text)]
    zones += [(m.start(), m.end()) for m in SOURCE.finditer(text)]
    m = HISTORY.search(text)
    while m:                       # history paragraphs run to the end; a match must not be followed by statute text
        rest = text[m.start():]
        if not re.search(r"\n\s*\(?[A-Za-z0-9]{1,4}[.)]\s+[A-Z][a-z]", rest[5:]):
            zones.append((m.start(), len(text)))
            break
        m = HISTORY.search(text, m.end())
    m = FL_HISTORY.search(text)
    if m:
        zones.append((m.start(), len(text)))
    return sorted(zones)


# ------------------------------------------------------------------ numbers
def words_to_num(s: str) -> str:
    """'three hundred one-A' -> '301-A'; 'ten hundred three' -> '1003'; 'twenty-three' -> '23';
    'eleven hundred ninety-nine-hhhh' -> '1199-HHHH'."""
    s = " ".join(s.lower().split())
    suffix = ""
    m = re.search(r"-([a-z]{1,2}|([a-z])\2{2,6})$", s)
    if m and m.group(1) not in _W + _T:
        suffix, s = "-" + m.group(1).upper(), s[:m.start()]
    total = cur = 0
    for w in re.split(r"[\s-]+", s):
        if w == "and" or not w:
            continue
        if w in _W:
            cur += _W.index(w)
        elif w in _T:
            cur += 20 + 10 * _T.index(w)
        elif w == "hundred":
            cur = (cur or 1) * 100
        elif w == "thousand":
            total += (cur or 1) * 1000
            cur = 0
    return f"{total + cur}{suffix}"


def norm_num(n: str) -> str:
    return re.sub(rf"{_D}+", "-", n.strip().strip("."))          # '8--404' -> '8-404'


def natkey(n: str) -> tuple:
    """Order of section numbers: a part after a dot is a decimal fraction ('605.0903' < '605.09091' < '605.0912',
    '1203.4' < '1203.41'), other parts are integers ('19.2-31' < '19.2-305')."""
    out = []
    for sep, digits, letters in re.findall(r"([.\-:–]?)(\d+)([A-Za-z]*)", n):
        out.append((1, digits, letters.lower()) if sep == "." else (0, int(digits), letters.lower()))
    return tuple(out)


def _split_range(n: str) -> tuple[str, str] | None:
    """'605.0903-605.0912' -> ('605.0903', '605.0912'); '19.2-305.1' is one number."""
    for m in re.finditer(_D, n):
        a, b = n[:m.start()], n[m.end():]
        if not a or not b:
            continue
        shape = lambda x: re.sub(r"[A-Za-z]", "", re.sub(r"\d+", "9", x))   # noqa: E731
        if (re.split(r"[.\-]", a)[0] == re.split(r"[.\-]", b)[0] and shape(a) == shape(b) and "." in a
                and natkey(a) < natkey(b)):
            return a, b
    return None


# ------------------------------------------------------------------ outline (for relative pinpoints)
MARK = re.compile(r"(?:^|(?<=\n)|(?<=[.:;]\s)|(?<=[.:;]\s\s)|(?<=—))[ \t]*((?:\((?:[A-Za-z]{1,5}|\d{1,3})"
                  r"(?:-\d+)?\)\s*)+|[A-Z]\.(?=\s)|\d{1,2}\.(?=\s)|[a-z]\.(?=\s))")


def _mtype(label: str, last1: str | None) -> str:
    """The marker's type: digit, lower, upper, roman, or a dotted form (Virginia 'A.', '1.')."""
    if label.endswith("."):
        x = label[:-1]
        return "dot-upper" if x.isupper() else "dot-digit" if x.isdigit() else "dot-lower"
    m = re.match(r"\(?([A-Za-z0-9]+)", label)
    x = m.group(1) if m else label
    if x[:1].isdigit():
        return "digit"
    if x.isupper():
        return "upper"
    before = {"i": "h", "v": "u", "x": "w"}.get(x)
    if ROMAN.match(x) and (len(x) > 1 or (before and last1 != before)):   # '(c)' is a letter, '(i)' after '(h)' too
        return "roman"
    return "lower"


class Outline:
    """Where each sub-section marker sits, with its level (levels by first appearance of each marker type)."""

    def __init__(self, text: str, zones: list[tuple[int, int]] = ()):
        self.levels: dict[str, int] = {}
        self.snaps: list[tuple[int, tuple]] = []
        stack: dict[int, str] = {}
        last1 = None
        for m in MARK.finditer(text):
            if any(a <= m.start(1) < b for a, b in zones):      # the label 'Sec. 2.' is not a marker
                continue
            labels = re.findall(r"\([^)]*\)|[A-Za-z0-9]+\.", m.group(1))
            for lab in labels:
                t = _mtype(lab, last1)
                lvl = self.levels.setdefault(t, len(self.levels) + 1)
                stack = {k: v for k, v in stack.items() if k < lvl}
                stack[lvl] = lab if lab.startswith("(") else lab[:-1]
                if lvl == 1:
                    last1 = lab.strip("().")
            self.snaps.append((m.start(1), tuple(stack[k] for k in sorted(stack))))
        self.pos = [s[0] for s in self.snaps]

    def at(self, pos: int, depth: int) -> list[str]:
        i = bisect.bisect_right(self.pos, pos) - 1
        return list(self.snaps[i][1][:depth]) if i >= 0 else []

    def level_of(self, label: str) -> int | None:
        return self.levels.get(_mtype(label, None))


def _ptypes(labels: list[str]) -> list[set]:
    """The marker types each designator can have, read in order: '(i)' after a letter is a roman numeral; alone it
    may be either."""
    out: list[set] = []
    for k, lab in enumerate(labels):
        x = lab.strip("().")
        if x[:1].isdigit():
            s = {"digit"}
        elif x.islower():
            s = {"roman"} if ROMAN.match(x) and len(x) > 1 else {"lower", "roman"} if x in ("i", "v", "x") else {"lower"}
        else:
            lo = x.lower()
            s = {"uroman"} if ROMAN.match(lo) and len(lo) > 1 else {"upper", "uroman"} if lo in ("i", "v", "x") else {"upper"}
        if len(s) > 1 and k and out[k - 1] & {"lower", "upper"} and not out[k - 1] & {"roman", "uroman"}:
            s = s - {"lower", "upper"}                  # (a)(i): after a letter, a roman numeral
        out.append(s)
    return out


def _pin_merge(old: list[str], new: list[str]) -> list[str]:
    """A list item's designators replace the cited ones from the level of the item's first designator:
    '(2)(a) and (b), (3), and (4)(e)' -> (2)(a), (2)(b), (3), (4)(e)."""
    if not new:
        return list(old)
    t = _ptypes(new[:1])[0]
    types = _ptypes(old)
    for j in range(len(old) - 1, -1, -1):
        if types[j] & t:
            return old[:j] + new
    return (old[:-len(new)] if len(old) >= len(new) else []) + new


def _pin_join(parts: list[str]) -> str | None:
    parts = [p for p in parts if p]
    if not parts:
        return None
    out = ""
    for p in parts:
        out += p if p.startswith("(") or not out else " " + p
    return out


def _pin_label(d: str) -> str:
    d = d.strip()
    if re.fullmatch(NUMWORDS, d):
        return f"({words_to_num(d)})"
    return d


# ------------------------------------------------------------------ law outside the index
# A constitution or an uncodified session law is cited with the same words as a code ('Section 4 of Article XIII A
# of the California Constitution', 'Section 7 of Chapter 129 of the Statutes of 1999', 'section 1 of chapter 1040
# of the laws of 1981'); read as a code citation, its 'Section 4' or 'Section 7' would resolve in the citing code.
# These patterns take the whole citation, pinpoints and lists included, before the code grammar runs.
_STATES = r"(?:California|Illinois|New\s+York|Florida|Texas|Virginia|Maryland|Washington|North\s+Carolina)"
_ORD = r"\d+(?:st|nd|rd|th)"
_ORDW = (r"(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth|"
         r"Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|Twentieth|Twenty-\w+)")
CONST_NAME = (rf"(?:(?:the\s+)?(?:{_STATES}\s+(?:[Ss]tate\s+)?|[Ss]tate\s+|United\s+States\s+|U\.\s?S\.\s+|[Ff]ederal\s+)?"
              rf"(?:Constitution|constitution|Const\.)(?:\s+of\s+(?:the\s+)?(?:[Ss]tate\s+of\s+)?(?:{_STATES}|United\s+"
              rf"States(?:\s+of\s+America)?|this\s+[Ss]tate))?(?:\s+of\s+\d{{4}})?|(?:the\s+)?(?:Maryland\s+)?Declaration"
              rf"\s+of\s+Rights|(?:Fla|Cal|Ill|Tex|Va|Md|Wash|N\.\s?C|N\.\s?Y|U\.\s?S)\.\s+Const\.)")
_SECKW = r"(?:\b[Ss]ections?\b|\bSECTIONS?\b|§§?|\b[Ss]ecs?\.|(?<![\w.])ss?\.)"
_LIST = r"(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or|to|through)\s+)"
_SL_BODY = r"(?:[Ss]tatutes|[Ll]aws|[Aa]cts|Session\s+Laws)"
_ACT_THAT = r"[Aa]ct\s+(?:(?:that|which)\s+(?:added|amended|enacted|repealed|renumbered)|adding|amending|enacting)\b"
_LEG_TAIL = (rf"(?:,?\s+(?:(?:Regular|{_ORDW}|{_ORD})\s+(?:Extraordinary\s+|Special\s+|Called\s+)?Session|{_ORD}\s+"
             r"(?:sp|ex)\.\s*sess\.|\d{4}(?![\d.\-–]\d)))*")
SURVEY = re.compile(r"\b(?:[Ss]ections?|SECTIONS?|Secs?\.)\s+\d+(?:\s*(?:,|and|&)\s*\d+)*\s*,?\s*(?:(?:of|in)\s+)?"
                    r"(?:Townships?\b|TOWNSHIPS?\b|Twp\.|T\.?\s?\d+\s?[NS]\b)")     # Fla. 'Section 23, Township 14 South'
VERNON = re.compile(r"\b(?:Articles?|Arts?\.)\s+\d+[\w\-.()]*(?:(?:\s*,\s*(?:and\s+)?|\s+(?:and|or)\s+)\d+[\w\-.()]*)*"
                    r"\s*,\s*(?:Vernon'?s\s+)?(?:Texas\s+)?(?:Revised\s+)?Civil\s+Statutes(?:\s+Annotated)?")


@functools.lru_cache(maxsize=4)
def _outside(words: bool) -> tuple[re.Pattern, re.Pattern]:
    """(constitution, session law) patterns; ``words`` adds New York's spelled-out numbers ('section one of
    article seven', 'chapter ninety-six of the laws of nineteen hundred ninety-five')."""
    nw = NUMWORDS if words else r"(?!x)x"
    subd = rf"(?:{PIN}|[A-Z]\d{{0,2}}(?![\w])|\d{{1,3}}(?![\w.\-])|{nw})"
    pins = rf"(?:(?:{SUB_KW}|[Cc]lauses?)\s*{subd}(?:{_LIST}{subd})*\s*,?\s+of\s+)*"
    # list items without their own keyword only: in 's. 119.07(1), s. 286.011, or s. 24, Art. I of the State
    # Constitution' only the last item is the constitution's
    secs = rf"{_SECKW}\s*(?:{NUM}|{nw})(?:\s?{PIN})?(?:{_LIST}(?:{NUM}|{nw})(?:\s?{PIN})?)*"
    # 'Article XIII A', 'Article XIII  D', 'Article XIII (C)', 'Article 7', 'article seven'
    artd = rf"(?:[IVXLC]+(?:\s{{0,2}}[A-Z](?![A-Za-z])|\s?\([A-Z]\))?|\d+[A-Z]?|{nw})(?![\w])"
    art = rf"(?:[Aa]rticles?|ARTICLES?|[Aa]rt\.)\s*{artd}(?:(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+)(?:[Aa]rticles?\s+)?{artd})*"
    artsec = rf"{art}(?:\s*,\s*{secs})?(?:\s*,\s*(?:{SUB_KW}|[Cc]lause)\s*{subd})?"
    join = r"(?:\s*,\s*|\s*,?\s+of\s*,?\s+(?:the\s+)?)"
    # 'Section 3 of, and subdivisions (b) and (c) of Section 4 of, Article XIII of the California Constitution'
    shared = rf"(?:{pins}{secs}\s+of\s*,\s*(?:and\s+|or\s+)?)*"
    const = (rf"{shared}{pins}(?:{secs}{join})?{artsec}\s*(?:,\s*|,?\s+of\s+|\s+(?:to|in)\s+){CONST_NAME}"
             rf"|(?:the\s+)?(?:{_ORDW}|{_ORD})\s+[Aa]mendment\s+(?:to|of)\s+{CONST_NAME}")
    chap = rf"(?:\d+(?:-\d+)?|{nw})"
    chaps = rf"(?:[Cc]hapters?|CHAPTERS?|ch\.|c\.)\s*{chap}(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+){chap})*"
    bill = (r"(?:\s*\(\s*(?:[HS]\.\s?[BJR]\.|(?:Assembly|Senate)\s+Bill)\s*(?:No\.\s*)?\d+\s*\)"
            r"|\s*\(\s*pp?\.\s*\d+(?:\s*[-–]\s*\d+)?\s*\))?")
    year = rf"(?:\d{{4}}|{nw})"
    lead_req = rf"{pins}{secs}\s*(?:,\s*|,?\s+of\s+(?:the\s+)?)"
    lead = rf"(?:{lead_req})?"
    # New York's budget bills are cut into parts: 'section 3 of part A of chapter 57 of the laws of 2009', 'section
    # one of subpart F of part EE of chapter fifty-six of the laws of two thousand fifteen', 'section three of the
    # part of the chapter of the laws of two thousand twenty-five which amended this subdivision'
    parts = (r"(?:(?:(?:[Ss]ub)?[Pp]arts?\s+[A-Z]{1,4}\d{0,2}(?![\w])|(?:the|such|said|a)\s+(?:sub)?part)\s*,?\s+of\s+"
             r"(?:the\s+)?)*")
    # a California bill's own sections: 'Section 8 of the act that added this section', 'subdivision (n) of Section
    # 1 of the act adding this section', 'Section 1 of Assembly Bill 2257 of the 2021–22 Regular Session'
    act_that = (rf"{_ACT_THAT}(?:\s+(?:this|that)\s+(?:section|subdivision|subparagraph|paragraph|article|chapter|part|"
                r"division|title|code)\b|\s+(?:subdivision|subparagraph|paragraph)\s+\([A-Za-z0-9]{1,4}\)"
                r"(?:\s+(?:of|to)\s+this\s+section)?)?")
    bill_no = (rf"(?:Assembly|Senate)\s+Bill\s+(?:No\.\s*)?\d+(?:\s+of\s+the\s+\d{{4}}{_D}\d{{2,4}}\s+(?:Regular|"
               rf"{_ORDW}\s+Extraordinary)\s+Session(?:\s+of\s+the\s+Legislature)?)?")
    # a California initiative's own sections: 'Section 2 of Proposition 184', 'Section 11 of the initiative act
    # approved by a majority of the voters at the general election held on November 4, 1930'
    initiative = (r"(?:Proposition\s+\d+[A-Z]?(?![\w])|(?:(?:the|that|this)\s+)?[Ii]nitiative\s+(?:[Aa]ct|[Mm]easure|"
                  r"[Ss]tatute)\b"
                  r"(?:,?\s+(?:approved|adopted|enacted)\s+by\s+(?:a\s+majority\s+of\s+)?the\s+"
                  r"(?:voters|electors|people)(?:\s+(?:at|in)\s+the\s+(?:[A-Za-z]+\s+){0,3}?election(?:\s+held)?"
                  r"(?:\s+on)?\s+[A-Z][a-z]+\.?\s+\d{1,2},\s+\d{4})?)?)")
    session = (
        rf"{lead}{parts}{chaps}{bill}(?:,\s*sections?\s+\d+,?)?(?:\s*,\s*|\s+of\s+)(?:the\s+)?{_SL_BODY}"
        rf"(?:\s+of\s+Assembly)?\s+of\s+(?:the\s+)?(?:{year}|Florida|New\s+Jersey(?:\s+of\s+{year})?|{_ORD}\s+"
        rf"Legislature){_LEG_TAIL}"                                           # 'Chapter 129 of the Statutes of 1999'
        rf"|{lead}{chaps}{bill}\s+of\s+the\s+\d{{4}}\s+(?:Acts\s+of\s+Assembly|Session\s+Laws|Acts|Statutes)"  # Va.
        # N.Y. 'the chapter of the laws of 2019', 'section four of a chapter of the laws of two thousand five'
        rf"|{lead}{parts}(?:(?:the|a)\s+)?chapter\s+of\s+the\s+laws\s+of\s+{year}"
        rf"|{lead_req}(?:{act_that}|{bill_no}|{initiative})"                 # Cal. bill and initiative sections
        r"|\bCHAPTERS?\s+\d+(?:\s+AND\s+\d+)*\s+OF\s+(?:THE\s+ACTS\s+OF\s+)?\d{4}\b"    # Md. 'PER CHAPTER 386 OF 2024'
        rf"|{lead}(?:\b[Ll]aws|\bStatutes)\s+of\s+\d{{4}}{_LEG_TAIL},\s*(?:ch\.|[Cc]hapter)\s*\d+"
        rf"|{lead}\b(?:Public\s+Acts?|P\.\s?A\.)\s+\d{{2,3}}-\d{{1,4}}(?:{_LIST}\d{{2,3}}-\d{{1,4}})*"     # Ill.
        rf"|{lead}\b(?:Session|Public-Local|Private)\s+Laws\s+(?:of\s+)?\d{{4}}(?:-\d+|,\s*(?:c\.|[Cc]hapter)\s*\d+)?"
        rf"(?:,\s*s\.\s*\d+(?:\.\d+)?(?:\([a-z0-9]+\))*)?|{lead}\bS\.\s?L\.\s*\d{{4}}-\d+"                 # N.C.
        rf"|{lead}\bD\.C\.\s+(?:Law|Act)\s+\d+-\d+"                                                  # D.C.
        rf"|\b[HS]\.\s?[BJR]\.\s*(?:No\.\s*)?\d+\s*,\s*Acts\s+of\s+the\s+{_ORD}\s+Legislature{_LEG_TAIL}"    # Tex.
        r"|\b\d{4}\.SL\b|\b\d{4}\s+(?:Va\.\s+)?Acts?,?\s+c\.\s*\d+")
    return re.compile(const), re.compile(session)


# every constitution or session-law citation contains one of these words; the patterns run only around them
CONST_ANCHOR = re.compile(r"[Cc]onstitution|Const\.|Declaration\s+of\s+Rights")
SESSION_ANCHOR = re.compile(r"(?i:\b(?:statutes|laws|acts)\s+of\b)|\b\d{4}\s+(?:Acts|Session\s+Laws|Statutes)\b|"
                            r"\bOF\s+\d{4}\b|\bPublic\s+Acts?\b|\bP\.\s?A\.|\bLaws\s+\d{4}|\bS\.\s?L\.|\bD\.C\.\s+"
                            rf"(?:Law|Act)\b|\.SL\b|\bActs?,?\s+c\.|\b(?:Assembly|Senate)\s+Bill\b|\b{_ACT_THAT}|"
                            r"\bProposition\s+\d|\b[Ii]nitiative\s+(?:[Aa]ct|[Mm]easure|[Ss]tatute)\b")


def _anchored(pat: re.Pattern, anchor: re.Pattern, t: str, back: int = 400, fwd: int = 240) -> list[re.Match]:
    """The matches of ``pat`` that contain a match of ``anchor``, found in windows around the anchors: what a scan
    of the whole text finds, without trying the pattern at each of a long section's 500,000 positions."""
    best: dict[int, re.Match] = {}
    for a in anchor.finditer(t):
        for m in pat.finditer(t, max(0, a.start() - back), min(len(t), a.end() + fwd)):
            prev = best.get(m.start())
            if m.start() <= a.start() and a.end() <= m.end() and (prev is None or m.end() > prev.end()):
                best[m.start()] = m
    out, last = [], -1
    for s in sorted(best):
        if s >= last:
            out.append(best[s])
            last = best[s].end()
    return out


# ------------------------------------------------------------------ the parser
@dataclasses.dataclass
class _Atom:
    start: int
    end: int
    kind: str                        # sec | sub | unit | rel
    num: str | None = None           # section number (sec)
    num_end: str | None = None       # range end
    pins: list = dataclasses.field(default_factory=list)   # designators inside-out ("(2)", "(d)")
    pin_range: str | None = None
    kw: str = ""
    lvl: str | None = None           # unit/rel level
    desig: str | None = None         # unit designator
    chain: list = dataclasses.field(default_factory=list)  # units outer -> inner (unit)
    anchor: str | None = None        # (commencing with Section N), (§ N et seq.)
    repealed: bool = False
    rel_tail: str | None = None      # "of this section" / "of this paragraph"
    sec_of: "_Atom | None" = None    # sub atoms: the section they are in
    code: dict | None = None         # resolved qualifier
    external: str | None = None      # federal / anaphor / unknown act: no index target
    et_seq: bool = False
    item: bool = False               # a list continuation without its own keyword
    det: str | None = None


class _Parser:
    def __init__(self, state: str, row: dict, text: str, tab: Table | None, con):
        self.state, self.row, self.text, self.tab, self.con = state, row or {}, text, tab, con
        self.own_prefix = _prefix(self.row.get("citation") or "")
        self.zones = excluded(text, state)
        # a land survey's 'Section 23, Township 14 South' is a section of the survey grid, not of a code
        self.zones = sorted(self.zones + [(m.start(), m.end()) for m in SURVEY.finditer(text)])
        self.outside: list[tuple[int, int, str]] = []     # pass1 spans of law outside the index: (start, end, kind)
        self._outline = None
        self.cache: dict = {}
        words = state == "ny"                         # New York spells numbers out: 'section two hundred five'
        self.NUMW = NUMWORDS if words else r"(?!x)x"
        self.SUB_DESIG = SUB_DESIG if words else rf"(?:{PIN}|[A-Z]\d{{0,2}}(?![\w])|\d{{1,3}}(?![\w.\-]))"
        kws = [r"§§?", r"\b[Ss]ections?\b", r"\bSECTIONS?\b"]
        if state == "fl":
            kws.append(r"(?<![\w.])ss?\.(?=\s*\d)")
        if state == "nc":
            kws.append(r"\bG\.\s?S\.(?=\s*\d)")
        if state == "wa":
            kws.append(r"\bRCW(?=\s+\d)")
        if state in ARTICLE_SECTIONS:
            kws.append(r"\b[Aa]rt(?:icles?|\.)(?=\s*\d+[A-Z]?\.\d)")
        self.SEC_KW = "(?:" + "|".join(kws) + ")"
        sp = r"(?:\s(?=\())?" if state == "wa" else ""
        self.SEC = re.compile(rf"(?P<kw>{self.SEC_KW})\s*(?:(?P<num>{NUM})|(?P<words>{self.NUMW}))(?P<pin>{sp}{PIN})?")
        self.TRIG = re.compile(rf"(?P<rel>{REL})|(?P<sub>{SUB_KW})(?=\s*{self.SUB_DESIG})|(?P<sec>{self.SEC_KW})"
                               rf"(?=\s*(?:\d|{self.NUMW}))|(?P<unit>{UNIT_KW})(?=\s+(?:{UNIT_DESIG}|{self.NUMW}))"
                               rf"|(?P<herein>\b(?:used|defined|provided|set\s+forth|specified|contained|described)"
                               rf"\s+herein\b)")
        self.taken: list[tuple[int, int]] = []

    # -- helpers
    def outline(self) -> Outline:
        if self._outline is None:
            self._outline = Outline(self.text, self.zones)
        return self._outline

    def excluded_at(self, a: int, b: int | None = None) -> bool:
        b = a + 1 if b is None else b
        return any(x < b and a < y for x, y in self.zones) or any(x < b and a < y for x, y in self.taken)

    def m(self, pat, pos, flags=0):
        if isinstance(pat, str):
            pat = _compiled(pat, flags)
        return pat.match(self.text, pos)

    # -- atoms
    def atom(self, pos: int) -> _Atom | None:
        t = self.text
        m = self.m(REL, pos)
        if m:
            det, lvl = m.group("det").lower(), _rel_level(m.group("lvl"))
            plural = m.group("lvl").lower().endswith("s") and lvl + "s" == m.group("lvl").lower()
            if det == "that" and lvl in ("part", "title", "item", "code", "law", "definition", "sentence"):
                return None                           # 'that part of the record', 'that title to the land'
            if det in ("these", "those") and not plural:
                return None
            if pos and t[pos - 1] in "\"“'‘":
                return None                           # a quoted mention: the words "this Chapter," mean ...
            a = _Atom(pos, m.end(), "rel", lvl=lvl, det=det)
            g = self.m(rf"\s*({PIN})", a.end)
            if g and a.lvl in SECTION_LEVELS:
                a.pins = [g.group(1)]
                a.end = g.end()
            return a
        m = self.m(rf"(?P<kw>{SUB_KW})\s*(?P<d>{self.SUB_DESIG})", pos)
        if m:
            a = _Atom(pos, m.end(), "sub", kw=m.group("kw").lower(), pins=[_pin_label(m.group("d"))])
            r = self.m(rf"\s+(?i:to|through)\s+(?P<d>{PIN})", a.end)          # 'subdivisions (a) through (p)'
            if r:
                a.pin_range, a.end = _pin_label(r.group("d")), r.end()
            self._sub_chain(a)
            return a
        m = self.SEC.match(t, pos)
        if m:
            return self._sec_atom(m, pos)
        m = self.m(rf"(?P<kw>{UNIT_KW})\s+(?P<d>{UNIT_DESIG}|{self.NUMW})", pos)
        if m:
            d = m.group("d")
            d = words_to_num(d) if re.fullmatch(NUMWORDS, d) and not re.fullmatch(UNIT_DESIG, d) else d
            a = _Atom(pos, m.end(), "unit", kw=m.group("kw").lower(), lvl=_unit_level(m.group("kw")), desig=_desig(d))
            a.chain = [(a.lvl, a.desig)]
            self._unit_tail(a)
            return a
        return None

    def _sec_atom(self, m, pos) -> _Atom:
        kw = m.group("kw")
        num = m.group("num")
        if num is None:
            num = words_to_num(m.group("words"))
        a = _Atom(pos, m.end(), "sec", kw=kw, num=norm_num(num))
        if m.group("pin"):
            a.pins = re.findall(rf"{PAREN}|\d+$", m.group("pin").strip())
            self._pin_range(a)
        sr = _split_range(a.num)
        if sr:
            a.num, a.num_end = sr
        else:
            r = RANGE_SEP.match(self.text, a.end)
            if r:
                n2 = self.m(rf"(?:{self.SEC_KW})?\s*(?P<num>{NUM})", r.end())
                if n2 and not MEASURE.match(self.text, n2.end()) and _shape_ok(a.num, n2.group("num")):
                    a.num_end, a.end = norm_num(n2.group("num")), n2.end()
                    inc = INCLUSIVE.match(self.text, a.end)
                    if inc:
                        a.end = inc.end()
        if re.search(r"\bformer\s*$", self.text[max(0, pos - 12):pos], re.I):
            a.repealed = True
        return a

    def _pin_range(self, a: _Atom):
        """'RCW 48.110.030 (2)(a) through (c)': a range of the last designator."""
        r = self.m(rf"\s+(?i:to|through)\s+(?P<d>{PIN})", a.end)
        if r and a.pins:
            a.pin_range, a.end = "".join(re.findall(PAREN, r.group("d"))) or r.group("d"), r.end()

    def _sub_chain(self, a: _Atom):
        """'paragraph (1) of subdivision (i) of Section 136.2', 'subsection A of § 19.2-390', 'paragraph two of
        subdivision (e) of section three hundred one of this chapter', 'subsection (c) of this section'."""
        while True:
            m = self.m(rf"\s+of\s+(?:{SUB_KW})\s*(?P<d>{self.SUB_DESIG})", a.end)
            if not m:
                break
            a.pins.append(_pin_label(m.group("d")))
            a.end = m.end()
        m = self.m(r"\s+of\s+", a.end)
        if m:
            s = self.SEC.match(self.text, m.end())
            if s:
                a.sec_of = self._sec_atom(s, m.end())
                a.end = a.sec_of.end
                return
            r = self.m(REL, m.end())
            if r:
                lvl = r.group("lvl").lower()
                a.rel_tail = _rel_level(lvl)
                a.end = r.end()
                g = self.m(rf"\s*({PIN})", a.end)
                if g and a.rel_tail in SECTION_LEVELS:
                    a.pins.append(g.group(1))
                    a.end = g.end()

    def _unit_tail(self, a: _Atom):
        """'(commencing with Section 6500)', '[repealed]', ' of Division 3', ', Subtitle 3', ' of Title 4 of Part 6'."""
        while True:
            m = self.m(r"\s*\[\s*repealed\s*\]", a.end, re.I)
            if m:
                a.repealed, a.end = True, m.end()
                continue
            m = self.m(rf"\s*\(\s*commencing\s+with\s+(?:{self.SEC_KW})\s*(?P<n>{NUM})\s*\)", a.end, re.I)
            if m:
                a.anchor, a.end = norm_num(m.group("n")), m.end()
                continue
            m = self.m(rf"\s*[(\[]\s*(?:§§?|ss?\.|G\.S\.|RCW)\s*(?P<n>{NUM})\s+et\s+seq\.?\s*[)\]]", a.end)
            if m:
                a.anchor, a.et_seq, a.end = norm_num(m.group("n")), True, m.end()
                continue
            m = self.m(rf"(?:,\s*|\s+)of\s+(?:the\s+)?(?P<kw>{UNIT_KW})\s+(?P<d>{UNIT_DESIG}|{self.NUMW})", a.end)
            if m:
                d = m.group("d")
                d = words_to_num(d) if re.fullmatch(NUMWORDS, d) and not re.fullmatch(UNIT_DESIG, d) else d
                a.chain.insert(0, (_unit_level(m.group("kw")), _desig(d)))
                a.end = m.end()
                continue
            m = self.m(rf",\s*(?P<kw>{UNIT_KW})\s+(?P<d>{UNIT_DESIG})", a.end)
            if m:
                lvl = _unit_level(m.group("kw"))
                cur = a.chain[-1][0]
                if lvl == "sub" + cur or (cur, lvl) in (("subtitle", "part"), ("title", "subtitle")):
                    a.chain.append((lvl, _desig(m.group("d"))))          # outer, then inner (Md.)
                elif cur == "sub" + lvl:
                    a.chain.insert(0, (lvl, _desig(m.group("d"))))       # inner, then outer (Tex.)
                else:
                    break
                a.end = m.end()
                continue
            break

    def cont(self, pos: int, prev: _Atom, first: _Atom, sep: str = ",") -> _Atom | None:
        """A list item without its own keyword: '1203.4a', '(iii)', 'C', 'VII', 'eight hundred two'.  A bare
        marker after a plain comma that a lower-case word follows ('..., (ii) executing such articles') opens an
        enumeration, not a list item."""
        t = self.text
        def marker(m):
            return sep.strip() == "," and re.match(r"\s+(?!(?:of|and|or|to|through|inclusive)\b)[a-z]", t[m.end():])
        if first.kind == "sec" or prev.kind == "sec":
            base = prev if prev.kind == "sec" else first
            sp = r"(?:\s(?=\())?" if self.state == "wa" else ""
            m = self.m(rf"(?P<num>{NUM})(?P<pin>{sp}{PIN})?", pos)
            if m and not MEASURE.match(t, m.end()) and _shape_ok(base.num or "", m.group("num")) \
                    and not re.match(r"\s*(?:U\.?S\.?C|C\.?F\.?R|ILCS)", t[m.end():m.end() + 8]):
                a = _Atom(pos, m.end(), "sec", kw=base.kw, num=norm_num(m.group("num")), item=True)
                if m.group("pin"):
                    a.pins = re.findall(rf"{PAREN}|\d+$", m.group("pin").strip())
                    self._pin_range(a)
                sr = _split_range(a.num)
                if sr:
                    a.num, a.num_end = sr
                else:
                    r = RANGE_SEP.match(t, a.end)
                    n2 = r and self.m(rf"(?P<num>{NUM})", r.end())
                    if n2 and not MEASURE.match(t, n2.end()) and _shape_ok(a.num, n2.group("num")):
                        a.num_end, a.end = norm_num(n2.group("num")), n2.end()
                return a
            m = self.m(rf"{PIN}", pos)
            if m and base.num and (base.pins or prev.item) and not marker(m):
                a = _Atom(pos, m.end(), "sec", kw=base.kw, num=base.num, item=True)
                a.pins = _pin_merge(list(base.pins), re.findall(PAREN, m.group(0)))   # (2)(a) and (b), (3)
                self._pin_range(a)
                return a
            if base.kw.lower().startswith("section") and self.state == "ny":
                m = self.m(NUMWORDS, pos)
                # not 'twenty dollars', nor '... section nine-f of the banking law, or one of its affiliates'
                if m and not MEASURE.match(t, m.end()) and not re.match(
                        r"\s+of\s+(?:its|their|them|his|her|whom|which|those|these|the\s+following)\b", t[m.end():]):
                    return _Atom(pos, m.end(), "sec", kw=base.kw, num=words_to_num(m.group(0)), item=True)
        if first.kind == "sub" or prev.kind == "sub":
            base = prev if prev.kind == "sub" else first
            d0 = base.pins[0] if base.pins else ""
            if d0.startswith("("):
                pat = PIN
            elif re.fullmatch(r"[A-Z]\d{0,2}", d0):
                pat = r"[A-Z]\d{0,2}(?![\w])"         # Virginia 'subsection B or C'
            else:
                pat = None
            m = self.m(pat, pos) if pat else None
            if m and not marker(m):                                 # its tail ('of subdivision (d) of Section 290') is the list's
                lab = _pin_label(m.group(0))
                if pat == PIN and d0.count("(") > 1:                # 'subsection (c)(2), (3), or (4)' -> (c)(3), (c)(4)
                    lab = "".join(_pin_merge(re.findall(PAREN, d0), re.findall(PAREN, lab)))
                return _Atom(pos, m.end(), "sub", kw=base.kw, pins=[lab], item=True)
        if first.kind == "unit" or prev.kind == "unit":
            base = prev if prev.kind == "unit" else first
            style = (r"\d+[A-Za-z]{0,2}(?:\.\d+[A-Za-z]?)*" if (base.desig or "")[:1].isdigit() else
                     rf"[IVXLC]+(?:{_D}[A-Z])?(?![A-Za-z])" if ROMAN.match((base.desig or "").split("-")[0]) else
                     r"[A-Z]{1,2}(?![A-Za-z])")
            m = self.m(rf"(?P<d>{style})", pos)
            if m and not MEASURE.match(t, m.end()):
                a = _Atom(pos, m.end(), "unit", kw=base.kw, lvl=base.lvl, desig=_desig(m.group("d")), item=True)
                a.chain = [(a.lvl, a.desig)]
                self._unit_tail(a)
                return a
        return None

    # -- qualifiers
    def quals(self, pos: int, group: list[_Atom]) -> int | None:
        """Qualifiers after a list item or a list: they apply to the open group.  Returns the new end, or None."""
        t = self.text
        end = pos
        hit = False
        while True:
            # a pinpoint tail for pinpoint-only items: ' of subdivision (d) of Section 290', ' of this section'
            subs = [a for a in group if a.kind == "sub" and not a.sec_of and not a.rel_tail]
            if subs:
                m = self.m(rf"\s+of\s+(?:{SUB_KW})\s*(?P<d>{self.SUB_DESIG})", end)
                if m:
                    for a in subs:
                        a.pins.append(_pin_label(m.group("d")))
                    end, hit = m.end(), True
                    continue
                m = self.m(r"\s+of\s+", end)
                s = m and self.SEC.match(t, m.end())
                if s:
                    sa = self._sec_atom(s, m.end())
                    for a in subs:
                        a.sec_of = sa
                    end, hit = sa.end, True
                    continue
                r = m and self.m(REL, m.end())
                if r:
                    lvl = r.group("lvl").lower()
                    lvl = _rel_level(lvl)
                    for a in subs:
                        a.rel_tail = lvl
                    end, hit = r.end(), True
                    continue
            m = self.m(r",?\s+of\s+(?:this|that|the\s+same)\s+(?P<lvl>(?i:code|chapter|article|title|subtitle|"
                       r"subchapter|act|part|division|law|section))\b", end)
            if m:
                lvl = m.group("lvl").lower()
                if self.m(r",?\s+of\s+that\s+act\b", end, re.I):
                    for a in group:
                        a.external = "anaphor"
                else:
                    for a in group:
                        if a.kind in ("sec", "unit") and a.code is None:
                            a.code = {"rel": lvl, "prefix": self.own_prefix}
                        elif a.kind == "sub" and not a.rel_tail and not a.sec_of:
                            a.rel_tail = lvl
                end, hit = m.end(), True
                continue
            # 'section two of such part': a section of the part named before, not of the citing law (see _such_part)
            m = self.m(r",?\s+of\s+(?:such|said)\s+(?:sub)?part\b", end, re.I)
            if m and any(a.kind == "sec" or a.sec_of for a in group):
                for a in group:
                    if (a.kind == "sec" or a.sec_of) and a.code is None and a.external is None:
                        a.external = "such-part"
                end, hit = m.end(), True
                continue
            if any(a.kind == "unit" for a in group):
                m = self.m(rf"(?:,\s*|\s+)of\s+(?:the\s+)?(?P<kw>{UNIT_KW})\s+(?P<d>{UNIT_DESIG}|{self.NUMW})", end)
                if m:
                    d = m.group("d")
                    d = words_to_num(d) if re.fullmatch(NUMWORDS, d) and not re.fullmatch(UNIT_DESIG, d) else d
                    for a in group:
                        if a.kind == "unit":
                            a.chain.insert(0, (_unit_level(m.group("kw")), _desig(d)))
                    end, hit = m.end(), True
                    continue
                m = self.m(rf",\s*(?P<kw>{UNIT_KW})\s+(?P<d>{UNIT_DESIG})", end)
                if m and any(a.kind == "unit" and a.chain and a.chain[0][0] == "sub" + _unit_level(m.group("kw"))
                             for a in group):
                    for a in group:
                        if a.kind == "unit":
                            a.chain.insert(0, (_unit_level(m.group("kw")), _desig(m.group("d"))))
                    end, hit = m.end(), True
                    continue
            if self.state == "wa":
                m = self.m(r"\s+RCW\b", end)
                if m:
                    for a in group:
                        a.code = a.code or {"prefix": self.tab.single if self.tab else self.own_prefix}
                    end, hit = m.end(), True
                    continue
            m = self.m(r"\s+et\s+seq\.?", end, re.I)
            if m:
                for a in group:
                    a.et_seq = True
                end, hit = m.end(), True
                continue
            m = self.m(r"\s+and\s+following\b", end, re.I)
            if m:
                for a in group:
                    a.et_seq = True
                end, hit = m.end(), True
                continue
            m = self.m(r"\s*\[\s*repealed\s*\]", end, re.I)
            if m:
                for a in group[-1:]:
                    a.repealed = True
                end, hit = m.end(), True
                continue
            m = self.m(rf"\s*\(\s*(?:§§?|ss?\.)\s*(?P<n>{NUM})\s+et\s+seq\.?\s*\)", end)
            if m and hit:
                end = m.end()
                continue
            m = self.m(r",?\s*approved\s+[A-Z][a-z]+\s+\d{1,2},\s+\d{4}(?:,\s+as\s+amended)?", end)
            if m and hit:
                end = m.end()
                continue
            q = self.code_qual(end)
            if q:
                qend, entry = q
                last = group[-1].kind if group else None          # 'Section 1464 or Chapter 12 (...) of the
                for a in group:                                   # Government Code': the code is the chapter's
                    if a.kind != last and {a.kind, last} != {"sub", "sec"}:
                        continue
                    if a.code is None and a.external is None:
                        if isinstance(entry, str):
                            a.external = entry
                        else:
                            a.code = entry
                end, hit = qend, True
                continue
            break
        return end if hit else None

    def code_qual(self, pos: int):
        """' of the Penal Code', ', Penal Code', ' of the Courts Article', ' of "The Illinois Vehicle Code"',
        ' of the federal ... act' -> (end, table entry | 'federal' | 'unknown')."""
        m = self.m(rf",?\s+of\s+(?:the\s+)?federal\s+(?:{FED_ACT_WORD}\s+){{1,12}}?act\b(?:\s+of\s+\d{{4}})?", pos,
                   re.I)
        if m:
            return m.end(), "federal"
        m = self.m(r",?\s+of\s+(?:title\s+\d+\s+of\s+)?the\s+United\s+States\s+Code\b", pos, re.I)
        if m:
            return m.end(), "federal"
        for lead in (r",?\s+of\s+(?:the\s+)?", r",\s+", r"\s+of\s+"):
            m = self.m(lead, pos)
            if not m:
                continue
            got = self.name_at(m.end(), comma=lead == r",\s+")
            if got:
                return got
        m = self.m(r",?\s+of\s+(?:the\s+)?(?P<n>(?:[A-Z][\w'\-]*\s+(?:(?:of|and|for|the|on|in|to)\s+)*){0,10}"
                   r"(?:Act|Code|Law|Article)(?:\s+of\s+(?:[A-Z][\w'\-]*(?:\s+(?=[A-Z]))?){1,3})?)\b(?:\s+of\s+\d{4})?",
                   pos)                                 # 'the Unified Code of Corrections'
        if self.tab is None:                            # no index: keep the name as the text writes it
            m = m or self.m(r",\s+(?P<n>(?:[A-Z][\w'\-]*\s+(?:(?:of|and)\s+)*){0,6}Code)\b", pos) or (
                self.m(r",?\s+of\s+the\s+(?P<n>(?:[a-z][\w\-]*\s+){0,6}law)\b", pos) if self.state == "ny" else None)
            if m:
                n = norm_name(m.group("n"))
                return m.end(), "federal" if any(f in n for f in FED_ACTS) else {"prefix": None, "named": m.group("n")}
        if m and self.tab and not self.tab.single:
            n = norm_name(m.group("n"))
            return m.end(), "federal" if any(f in n for f in FED_ACTS) else "unknown"
        if m and self.tab and self.tab.single:                    # an act inside a one-code state
            n = norm_name(m.group("n"))
            if any(f in n for f in FED_ACTS):
                return m.end(), "federal"
            e = m.end()
            p = self.m(rf"\s*\(\s*(?:§§?|ss?\.|G\.S\.|RCW)\s*{NUM}\s+et\s+seq\.?\s*\)", e)
            return (p.end() if p else e), {"prefix": self.tab.single, "named": m.group("n")}
        return None

    def name_at(self, pos: int, comma: bool = False):
        """The longest code or act name of the state's table starting at pos."""
        if not self.tab:
            return None
        t = self.text
        toks = list(re.finditer(r"[\"“”]|[\w.'’&]+|\s[–—-]\s", t[pos:pos + 220]))
        words, ends = [], []
        for k, tok in enumerate(toks):
            gap = t[pos + (toks[k - 1].end() if k else 0):pos + tok.start()]
            if k and re.search(r"[,;:()\[\]]|\n\s*\n", gap):
                break
            words.append(tok.group(0))
            ends.append(pos + tok.end())
            if len(words) > 16:
                break
        for k in range(len(words), 0, -1):
            cand = norm_name(" ".join(words[:k]))
            e = self.tab.names.get(cand)
            if e and (not comma or re.search(r"(?:code|article|law)$", cand)):
                end = ends[k - 1]
                if re.fullmatch(r"[A-Za-z]{3,}\.", words[k - 1]):
                    end -= 1                       # 'the general municipal law.': the sentence's full stop
                q = self.m(r"[\"”]", end)
                if q:
                    end = q.end()
                p = self.m(rf"\s*\(\s*(?:§§?|ss?\.)\s*{NUM}\s+et\s+seq\.?\s*\)", end)
                if p:
                    end = p.end()
                return end, e
        return None

    # -- lists
    def parse(self, pos: int):
        first = self.atom(pos)
        if not first:
            return None
        items, groups, open_g = [first], [], [first]
        end = first.end
        while True:
            q = self.quals(end, open_g)
            if q is not None:
                end = q
                groups.append(open_g)
                open_g = []
            s = SEP.match(self.text, end)
            if not s:
                break
            out = next(((a, b, k) for a, b, k in self.outside if a == s.end() and k != "other_code"), None)
            if out:
                # 'Section 5 and Section 7 of Chapter 130 of the Statutes of 2000', 'section one or section two of
                # chapter seven hundred seventy-two of the laws of ...': the earlier items are that law's when they are
                # numbered like its first section ('s. 119.07(1), s. 286.011, or s. 24, Art. I of the State
                # Constitution': the Florida Statutes' sections are not).  Its first section is read inside its own
                # span: in 'section 5 or part A of chapter 57 of the laws of 2009, as amended by section 3 of this
                # chapter' the session law has none, and the 'section 3' after it is the citing law's
                m = re.search(rf"{_SECKW}\s*(?:({NUM})|({self.NUMW}))", self.text[out[0]:out[1]])
                its_first = (m.group(1) or words_to_num(m.group(2))) if m else None
                for a in open_g:
                    sec = a if a.kind == "sec" else a.sec_of if a.kind == "sub" else None
                    if (its_first and sec and a.code is None and a.external is None and sec.code is None
                            and _num_shape(sec.num or "") == _num_shape(its_first)):
                        a.external = out[2]
                break
            nxt = self.atom(s.end())
            if nxt and nxt.kind == "rel" and nxt.lvl not in SECTION_LEVELS and first.kind != "rel":
                nxt = None
            if nxt is None:
                nxt = self.cont(s.end(), items[-1], first, s.group(0))
            if nxt is None or self.excluded_at(s.end(), nxt.end):
                break
            last = items[-1]
            if (nxt.kind == "sub" and not nxt.item and not nxt.sec_of and not nxt.rel_tail and not nxt.pin_range
                    and s.group(0).strip() == "," and last.kind == "sec" and not last.pins and not last.num_end
                    and not last.repealed and not self.m(r",?\s+of\s", nxt.end)):
                # 'G.S. 59-68, subdivision (b)(2)': a pinpoint of the section just cited, not of this one
                last.pins = [p for x in reversed(nxt.pins) for p in (re.findall(PAREN, x) or [x])]
                last.end = end = nxt.end
                continue
            items.append(nxt)
            open_g.append(nxt)
            end = nxt.end
        if open_g:
            groups.append(open_g)
        if end > first.end and len(items) == 1:
            first.end = end
        # the list's trailing qualifiers belong to the last item's span
        items[-1].end = max(items[-1].end, end)
        return end, items

    def run(self) -> list[dict]:
        drafts = []
        t = self.text
        for d in self.pass1():
            drafts.append(d)
            self.taken.append((d["start"], d["end"]))
        pos = 0
        gid = 0
        while True:
            m = self.TRIG.search(t, pos)
            if not m:
                break
            if self.excluded_at(m.start(), m.end()):
                pos = m.end()
                continue
            if m.group("herein"):
                h = m.end() - len("herein")
                drafts.append({"start": h, "end": m.end(), "kind": "internal_relative", "atom": _Atom(
                    h, m.end(), "rel", lvl="section", det="this"), "group": None})
                pos = m.end()
                continue
            got = self.parse(m.start())
            if not got:
                pos = m.end()
                continue
            end, items = got
            g = None
            if len(items) > 1:
                gid += 1
                g = gid
            for k, a in enumerate(items):
                s = a.start
                e = items[k].end if k == len(items) - 1 else a.end
                if k < len(items) - 1:
                    e = min(e, items[k + 1].start)
                drafts.append({"start": s, "end": e, "atom": a, "group": g, "n_items": len(items)})
            self.taken.append((m.start(), end))
            pos = max(end, m.end())
        for d in self.pass3():
            if not self.excluded_at(d["start"], d["end"]):
                drafts.append(d)
                self.taken.append((d["start"], d["end"]))
        drafts.sort(key=lambda d: (d["start"], -d["end"]))
        out, last = [], -1
        for d in drafts:
            if d["start"] < last:
                continue
            out.append(d)
            last = d["end"]
        return out

    # -- recognisers without index targets
    def pass1(self) -> list[dict]:
        t = self.text
        out = []
        const, session = _outside(self.state == "ny")
        pats = [
            ("constitution", (const, CONST_ANCHOR)),
            ("federal", r"\b(?:Title\s+)?\d+\s+U\.\s?S\.\s?C\.(?:\s?A\.)?\s*(?:(?:§§?|[Ss]ec(?:tions?|s?\.)?)\s*)?"
                        r"\d+[\w.\-]*(?:\s*\([\w.\-]+\))*(?:\s+et\s+seq\.?)?"),
            ("federal", r"\b\d+\s+C\.?\s?F\.?\s?R\.?\s*(?:(?:Parts?|§§?|[Ss]ec(?:tions?|\.)?)\s*)?\d+[\w.\-]*"
                        r"(?:\s+(?:and|or|through|to)\s+\d+[\w.\-]*)*"),
            ("federal", r"\b(?:P\.\s?L\.|Pub\.\s?L\.(?:\s?No\.)?|Public\s+Law)\s*\d+[-–]\d+"),
            ("session_law", (session, SESSION_ANCHOR)),
            ("other_code", VERNON if self.state == "tx" else None),     # 'Article 8280-581, Vernon's Texas Civil Statutes'
        ]
        codes = {"federal": "U.S.", "constitution": "constitution", "session_law": "session law",
                 "other_code": "Vernon's Texas Civil Statutes"}
        for kind, p in pats:
            if p is None:
                continue
            ms = _anchored(*p, t) if isinstance(p, tuple) else (_compiled(p, 0) if isinstance(p, str) else p).finditer(t)
            for m in ms:
                if not self.excluded_at(m.start(), m.end()) and not any(
                        o["start"] < m.end() and m.start() < o["end"] for o in out):
                    out.append({"start": m.start(), "end": m.end(), "kind": kind, "group": None, "code": codes[kind],
                                "note": "not in index" if kind == "other_code" else None})
                    if kind != "federal":
                        self.outside.append((m.start(), m.end(), kind))
        if self.state == "il":
            for m in re.finditer(rf"\b(?P<ch>\d+)\s+ILCS\s+(?P<act>\d+)/(?P<sec>{NUM})?", t):
                if self.excluded_at(m.start(), m.end()):
                    continue
                pre = f"{m.group('ch')} ILCS {m.group('act')}/"
                d = {"start": m.start(), "end": m.end(), "group": None, "ilcs": pre, "sec": m.group("sec")}
                out.append(d)
        return out

    def pass3(self) -> list[dict]:
        t = self.text
        out = []

        def add(m, kind, code=None, g=0, **kw):
            s, e = m.start(g), m.end(g)
            if not self.excluded_at(s, e) and not any(o["start"] < e and s < o["end"] for o in out):
                out.append({"start": s, "end": e, "kind": kind, "group": None, "code": code, **kw})

        for m in re.finditer(r"\b(?:the\s+)?(?:laws?|statutes?|regulations?)\s+of\s+the\s+United\s+States\b", t, re.I):
            add(m, "federal", "U.S.")
        # 'federal law', 'the federal Fair Credit Reporting Act', 'federal and/or state laws', 'comply with all federal
        # and state laws', 'federal and state requirements', 'federal Department of Labor regulations'; not 'federal
        # or State program allowing a law enforcement agency', 'federal or state agencies authorized by law', 'the
        # federal grant funds are subject to State law' or 'the federal agency in accordance with State law' (see
        # FED_WORD), 'federal or state law enforcement agencies', 'federal or State law-enforcement agency' or 'federal
        # or State court rules'
        for m in re.finditer(rf"\bfederal\s+(?:(?:{FED_WORD}\s+){{0,10}}?(?:law|laws|regulations?|requirements?|statutes?|"
                             rf"rules?|policy)\b{NOT_ENF}|(?:{FED_ACT_WORD}\s+){{0,12}}?act\b)(?:\s+of\s+\d{{4}})?", t,
                             re.I):
            add(m, "federal", "U.S.")
        for m in re.finditer(r"\bUnited\s+States\s+(?:department|code)\b[^.;,]{0,120}?\b(?:policy|code)\b", t, re.I):
            add(m, "federal", "U.S.")
        for m in re.finditer(rf"\b(?:the\s+)?(?:United\s+States\s+|U\.\s?S\.\s+|federal\s+|State\s+|{_STATES}\s+)?"
                             r"Constitution\b(?:\s+of\s+(?:the\s+)?(?:State\s+of\s+)?(?:United\s+States|[A-Z][a-z]+))?"
                             r"|\bconstitutional\s+rights?\b", t):
            add(m, "constitution", "constitution")
        # regulations and court rules
        # rules an agency or a court adopts ('regulations adopted by the board', 'rules adopted by the Judicial
        # Council', 'any rule or regulation adopted under it'); the Judicial Council and the courts make court rules
        for m in re.finditer(r"\b(?:the\s+)?(?:lawful\s+)?(?:any\s+)?(?:rules?\s+(?:and|or)\s+)?(?:(?:regulations?|rules?)"
                             r"\s+(?:adopted|promulgated|issued|prescribed|established)|procedures\s+(?:adopted|promulgated))"
                             r"\s+(?:by|under|pursuant\s+to)\s+(?:the\s+)?(?:[A-Za-z]+\s+){0,3}?(?:board|department|"
                             r"commission|director|secretary|agency|mayor|commissioner|administration|division|council|it|"
                             r"court)\b", t, re.I):
            add(m, "court_rule" if re.search(r"judicial\s+council|court", m.group(0), re.I) else "regulation",
                "regulations")
        for m in re.finditer(r"\bregulations?\s+of\s+the\s+(?:[a-z]+\s+){0,3}(?:board|department|commission|agency)\b",
                             t, re.I):
            add(m, "regulation", "regulations")
        for m in re.finditer(r"\brules?\s+of\s+(?:the\s+)?[Cc]ourt\b|\bRules\s+of\s+(?:Civil|Criminal|Appellate|Evidence)"
                             r"\b[\w ]{0,20}", t):
            add(m, "court_rule", "court rules")
        for m in re.finditer(r"\bby\s+rule\b", t):
            court = re.search(r"\bCourt\b", t[max(0, m.start() - 80):m.start()])
            add(m, "court_rule" if court else "regulation", "rules")
        # named acts and whole codes (from the table), unknown acts
        if self.tab:
            lead = r"\b(?:the|The)\s+(?=[A-Za-z\"“])" if self.state == "ny" else r"\b(?:the|The)\s+(?=[A-Z\"“])"
            for m in re.finditer(lead, t):
                got = self.name_at(m.end())
                if got:
                    end, e = got
                    nm = norm_name(re.sub(rf"\s*\(\s*(?:§§?|ss?\.)\s*{NUM}\s+et\s+seq\.?\s*\)$", "", t[m.end():end]))
                    if any(nm == f or nm.endswith(" " + f) for f in FED_ACTS) and not nm.startswith(STATE_WORDS):
                        continue                  # HIPAA, not the 'Illinois Health Insurance Portability ... Act'
                    if re.search(r"(?:code|article|law|act|compact|statutes)$", nm):
                        # an act, anchored at its short title: any name a short title gives a unit inside a code
                        # ('the Maryland Vehicle Law' = Md. Transp. Titles 11-27, § 11-206), or a name ending in Act
                        act = e.get("kind") == "act" or bool(re.search(r"(?:act|compact)$", nm))
                        out_d = {"start": m.start(), "end": end, "kind": "named_act" if act else "other_code",
                                 "group": None, "entry": e}
                        if not self.excluded_at(m.start(), end) and not any(
                                o["start"] < end and m.start() < o["end"] for o in out):
                            out.append(out_d)
        for m in re.finditer(r"\b(?:the\s+)?(?:federal\s+)?(?P<n>(?:[A-Z][\w'\-]*\s+(?:(?:of|and|for|the|on|in|to)\s+)*)"
                             rf"{{1,10}}Act)\b(?:\s+of\s+\d{{4}})?(?:\s*\(\s*(?:§§?|ss?\.)\s*{NUM}\s+et\s+seq\.?\s*\))?",
                             t):
            n = norm_name(m.group("n"))
            fed = any(f in n for f in FED_ACTS) or re.match(r"(?:the\s+)?federal\b", m.group(0), re.I)
            if n in ("this act", "the act", "such act", "that act", "an act", "public act") or \
                    n.split()[0] in ("this", "that", "public"):
                continue
            add(m, "federal" if fed else "named_act", "U.S." if fed else m.group("n"))
        # generic law; 'law' before 'enforcement' or '-enforcement' is police ('any other law enforcement agency')
        for p in (rf"\bany\s+other\s+(?:applicable\s+)?(?:provisions?\s+of\s+)?(?:law|statute)s?\b{NOT_ENF}(?:\s+of\s+"
                  r"this\s+state)?", rf"\b(?:other\s+applicable|applicable\s+statutory|other)\s+(?:law|statute)s?\b{NOT_ENF}",
                  r"\b(?:the\s+)?laws?\s+of\s+(?:this|the)\s+[Ss]tate\b", rf"\b[Ss]tate\s+law\b{NOT_ENF}",
                  r"\bthe\s+common\s+law\b", rf"\bgeneral\s+law\b{NOT_ENF}",
                  r"\b(?:the\s+)?(?:rules|principles)\s+of\s+law\s+and\s+equity\b",
                  r"\bother\s+provisions\s+of\s+law\b"):
            for m in re.finditer(p, t):
                add(m, "generic", None)
        for m in re.finditer(r"\b(?:otherwise\s+)?(?:provided|prescribed|required|authorized|established|created|"
                             rf"fixed|allowed|charged|imposed|specifically\s+provided)\s+by\s+(law|statute)\b{NOT_ENF}", t,
                             re.I):
            add(m, "generic", None, g=0)
        for m in re.finditer(r"\b(?:pursuant\s+to|under|in\s+accordance\s+with|consistent\s+with|inconsistent\s+with|"
                             rf"the\s+manner\s+required\s+by)\s+(law|statute)\b{NOT_ENF}(?:\s+or\s+ordinance)?\b", t):
            add(m, "generic", None, g=0)
        for m in re.finditer(r"\b[Ee]xcept\s+as\s+otherwise\s+provided\b(?!\s+(?:in|by|under|for)\b)", t):
            add(m, "generic", None)
        return out

    # -- resolution
    def resolve(self, d: dict) -> Reference:
        t = self.text
        a: _Atom | None = d.get("atom")
        s, e = d["start"], d["end"]
        span = t[s:e]
        kind = d.get("kind")
        code, sections, pin, unit, note, conf = d.get("code"), [], None, None, d.get("note"), 0.6
        if "ilcs" in d:
            pre = d["ilcs"]
            code = pre
            if d.get("sec"):
                sections = self.cite(pre, d["sec"])
                kind = "other_code" if pre != self.own_prefix else "section"
            else:
                kind = "named_act" if pre != self.own_prefix else "internal_relative"
                unit = self.unit_info((self.tab.prefixes.get(pre) or {}).get("root")) if self.tab else None
            conf = 0.9 if sections or unit else 0.5
        elif "entry" in d:
            en = d["entry"]
            code = en["prefix"]
            if en.get("anchor") and kind == "named_act":
                sections = [{"id": en["anchor"][0], "citation": en["anchor"][1]}]
                if en.get("range"):                          # an act that is a range of sections
                    sections = self.range_rows(code, *en["range"]) or sections
            p = re.search(rf"\(\s*(?:§§?|ss?\.)\s*(?P<n>{NUM})\s+et\s+seq", span)
            unit = self.unit_info(en.get("unit")) if en.get("unit") else self.units_info(en.get("units"))
            if p:
                anchored = self.cite(code, norm_num(p.group("n")))
                if anchored:
                    sections = anchored
                    unit = self.unit_info(self._unit_starting_at(anchored[0])) or unit
            conf = 0.8
        elif a is not None:
            kind, code, sections, pin, unit, note, conf = self.resolve_atom(a, d)
        else:                       # a named act the table does not know: '(§ 58.1-520 et seq.)' still anchors it
            p = re.search(rf"\(\s*(?:§§?|ss?\.)\s*(?P<n>{NUM})\s+et\s+seq", span)
            if p and kind == "named_act" and self.tab:
                code = self.tab.single or self.own_prefix
                sections = self.cite(code, norm_num(p.group("n")))
                unit = self.unit_info(self._unit_starting_at(sections[0])) if sections else None
                conf = 0.8 if sections else 0.5
        role, rconf = role_of(t, s, e, kind, d)
        return Reference(span=span, start=s, end=e, kind=kind or "section", code=code, sections=sections,
                         pinpoint=pin, role=role, confidence=round(min(conf, 0.5 + rconf / 2), 2), unit=unit,
                         list_group=d.get("group"), note=note)

    def resolve_atom(self, a: _Atom, d: dict):
        n_items = d.get("n_items", 1)
        listed = n_items > 1
        if a.kind == "rel":
            if a.det in ("those", "these"):
                return self._anaphor(a, d)
            if a.lvl in SECTION_LEVELS or (a.lvl == "article" and self._article_is_section()):
                pin = None
                if a.pins:                                       # 'this subsection (g)'
                    pin = _pin_join(a.pins)
                elif a.lvl not in ("section", "article"):
                    pin = _pin_join(self.outline().at(a.start, self._depth(a.lvl)))
                    if a.det == "that":
                        pin = self._last_pin(a.start) or pin
                return ("internal_relative", self.own_prefix, self._own(), pin, None, None, 0.9)
            path = self.rel_unit(a.lvl)
            return ("internal_relative", self.own_prefix, [], None, self.unit_info(path[0], exact=path[1]), None,
                    0.85 if path[0] else 0.5)
        if a.kind == "sub":
            pins_out = list(reversed(a.pins))                      # outer -> inner
            if a.pin_range:
                pins_out[-1] = f"{pins_out[-1]}-{a.pin_range}"
            if a.sec_of:
                sa = a.sec_of
                sa.code = sa.code or a.code
                sa.external = sa.external or a.external     # '... of Section 36 of the federal ... Act'
                kind, code, sections, pin, unit, note, conf = self._sec(sa, d)
                pin = _pin_join(list(sa.pins) + pins_out)
                if kind == "section":
                    kind = "pinpoint"
                if listed and kind in ("pinpoint", "section"):
                    kind = "list_item"
                return kind, code, sections, pin, unit, note, conf
            if a.external:                                  # 'subsection (c) of that act': not this section
                _, ext = self._code_of(a)
                kind = (ext if ext in ("constitution", "session_law") else
                        "federal" if ext in ("federal", "anaphor-federal") else "other_code")
                return kind, "U.S." if kind == "federal" else None, [], _pin_join(pins_out), None, ext, 0.5
            anaphor = self._such(a, pins_out)
            if anaphor is not None:
                return anaphor
            # pinpoint in this section, or in the relative unit named after it
            lvl = a.rel_tail
            if lvl == "article" and self._article_is_section():
                lvl = "section"                              # Tex. CCP 'Subsection (a) of this article'
            first = pins_out[0] if pins_out else ""
            if lvl and lvl not in SECTION_LEVELS and not (lvl == "article" and self._article_is_section()):
                ctx = []                                     # 'subsections (6)(a) and (b) of this Act': the section
            elif lvl and lvl != "section":
                ctx = self.outline().at(a.start, self._depth(lvl))
            elif lvl == "section":
                ctx = []
            else:
                level = self.outline().level_of(first) if first else None
                ctx = self.outline().at(a.start, level - 1) if level and level > 1 else []
            pin = _pin_join(ctx + pins_out)
            kind = "range" if a.pin_range else "list_item" if listed else "pinpoint"
            return kind, self.own_prefix, self._own(), pin, None, None, 0.85
        if a.kind == "sec":
            kind, code, sections, pin, unit, note, conf = self._sec(a, d)
            if listed and kind in ("section", "pinpoint"):
                kind = "list_item"
            return kind, code, sections, pin, unit, note, conf
        if a.kind == "unit":
            return self._unit(a, d)
        return "section", None, [], None, None, None, 0.3

    def _sec(self, a: _Atom, d: dict):
        pre, ext = self._code_of(a)
        pin = _pin_join(a.pins)
        if pin and a.pin_range:
            pin = f"{pin}-{a.pin_range}"                  # '(2)(a)-(c)'
        if ext == "such-part":
            return self._such_part(a, pin)
        if ext in ("constitution", "session_law"):
            return ext, "constitution" if ext == "constitution" else "session law", [], pin, None, None, 0.6
        if ext:
            return ("federal" if ext in ("federal", "anaphor-federal") else "other_code"), (
                "U.S." if ext.startswith(("federal", "anaphor")) else None), [], pin, None, ext, 0.6
        if a.repealed:
            return "section", pre, [], pin, None, "repealed", 0.6
        if a.num_end:
            rows = self.range_rows(pre, a.num, a.num_end) if pre else []
            return "range", pre or _named(a), rows, pin, None, None if rows else "not in index", 0.85 if rows else 0.4
        rows = self.cite(pre, a.num)
        kind = "other_code" if pre != self.own_prefix else "pinpoint" if a.pins else "section"
        note = None if rows else "not in index" if self.con else "no index"
        if a.et_seq and rows:                            # '§ 16-801 et seq.': the unit that begins there
            return kind, pre, rows, pin, self.unit_info(self._unit_starting_at(rows[0])), None, 0.85
        return kind, pre or _named(a), rows, pin, None, note, 0.9 if rows else 0.4

    def _code_of(self, a: _Atom) -> tuple[str, str | None]:
        if a.external == "anaphor":
            return self.own_prefix, "anaphor-federal" if self._last_federal(a.start) else "anaphor"
        if a.external:
            return self.own_prefix, a.external
        c = a.code
        if c and c.get("prefix") and "rel" not in c:
            return c["prefix"], None
        if c and c.get("named") and not c.get("prefix"):
            return None, None                           # a named code, without an index to resolve it
        if self.tab and self.tab.single:
            return self.tab.single, None
        if a.kw.lower().startswith("art") and self.state in ARTICLE_SECTIONS:
            for p in ARTICLE_SECTIONS[self.state]:
                pre = p + " § "
                if self.tab and pre in self.tab.prefixes:
                    return pre, None
        return self.own_prefix, None

    def _unit(self, a: _Atom, d: dict):
        pre, ext = self._code_of(a)
        kind = "container"
        if ext in ("constitution", "session_law"):
            return ext, "constitution" if ext == "constitution" else "session law", [], None, None, None, 0.5
        if ext:
            return ("federal" if "federal" in ext else "other_code"), None, [], None, None, ext, 0.5
        if a.repealed:
            return kind, pre, [], None, None, "repealed", 0.6
        sections, unit, note = [], None, None
        if a.anchor:
            sections = self.cite(pre, a.anchor)
            if sections:
                path = self._anchor_unit(sections[0], a.chain[-1] if a.chain else None)
                unit = self.unit_info(path) if path else None
        if unit is None:
            base = None
            rel = a.code.get("rel") if a.code else None
            if rel:
                base = self.rel_unit(rel)[0]
            if base is None and self.tab:
                base = (self.tab.prefixes.get(pre) or {}).get("root")
            path, exact = self.walk(base, a.chain)
            if path:
                unit = self.unit_info(path, exact=exact)
                if not exact:
                    nb = self._by_numbering(path, a.chain)
                    if nb:
                        sections, note = nb, "numbering"
                    else:
                        note = "unit not a level of the index"
            else:
                note = "not in index"
        conf = 0.9 if sections and unit else 0.8 if unit and unit.get("exact") else 0.45
        return kind, pre or _named(a), sections, None, unit, note, conf

    def _such(self, a: _Atom, pins_out: list[str]):
        """'such subdivision six', 'said subsection (b)': the pinpoint cited last with that designator, not this
        section ('... subdivision six of section one hundred twenty-w of the general municipal law and the term as
        used in such subdivision six')."""
        if a.rel_tail or not re.search(r"\b(?:such|said|the\s+same)\s+$", self.text[max(0, a.start - 12):a.start], re.I):
            return None
        want = pins_out[-1] if pins_out else ""
        for r in reversed(getattr(self, "_resolved", [])):
            if r.start < a.start and r.pinpoint and want and r.pinpoint.endswith(want):
                kind = r.kind if r.kind in ("other_code", "federal") + NO_TARGET_KINDS else "pinpoint"
                return kind, r.code, list(r.sections), r.pinpoint, None, "anaphor", 0.6
        return "pinpoint", None, [], _pin_join(pins_out), None, "anaphor", 0.3

    def _such_part(self, a: _Atom, pin: str | None):
        """'section two of such part', 'subdivision (b) of section two of such part': a section of the part cited
        last before it.  A session law's part ('part VV of the chapter of the laws of two thousand eighteen') gives
        that session law, with no index target.  A code's part ('part one-A of article six of the family court act')
        gives that code's section only when the index holds it inside that part (N.Y. Fam. Ct. Act § 635 is in Part
        1-A).  Without such a part before it, no target: the citing law's own section N is not what it names."""
        ante = None
        for r in reversed(getattr(self, "_resolved", [])):
            if r.start < a.start and r.note != "anaphor" and re.search(r"\b(?:sub)?parts?\b", r.span, re.I):
                ante = r
                break
        if ante is None:
            return "section", None, [], pin, None, "anaphor", 0.3
        if ante.kind in NO_TARGET_KINDS:
            return ante.kind, ante.code, [], pin, None, "anaphor", 0.5
        path = (ante.unit or {}).get("path")
        code = ante.code if ante.code and self.tab and ante.code in self.tab.prefixes else None
        rows = []
        if code and path and a.num:
            rows = self.range_rows(code, a.num, a.num_end) if a.num_end else self.cite(code, a.num)
            rows = [r for r in rows if self._in_unit(r["id"], path)]
        kind = "range" if a.num_end else "other_code" if code and code != self.own_prefix else "section"
        return kind, code, rows, pin, None, "anaphor", 0.7 if rows else 0.3

    def _in_unit(self, sec_id: int, path: str) -> bool:
        r = self.con.execute("SELECT path FROM sec WHERE id=?", (sec_id,)).fetchone() if self.con else None
        return bool(r and (r["path"] or "").startswith(path + " / "))

    def _anaphor(self, a: _Atom, d: dict):
        """'those chapters', 'those sections': the targets of the units or sections listed just before, in the same
        sentence."""
        if a.lvl in ("law", "act", "code"):              # 'Unless those laws ...': law named before, not a unit
            return "generic", None, [], None, None, "anaphor", 0.4
        left = self.text[:a.start]
        cut = max(left.rfind(". "), left.rfind("\n"))
        want = ("container",) if a.lvl not in SECTION_LEVELS else ("section", "list_item", "range", "pinpoint",
                                                                      "other_code")
        prev = [x for x in getattr(self, "_resolved", []) if x.start > cut and x.kind in want and x.sections]
        secs = list({s["id"]: s for x in prev for s in x.sections}.values())
        kind = "container" if a.lvl not in SECTION_LEVELS else "list_item"
        return kind, self.own_prefix, secs, None, None, "anaphor", 0.6 if secs else 0.3

    # -- index access
    def cite(self, prefix: str, num: str) -> list[dict]:
        if not self.con or not prefix:
            return []
        c = prefix + norm_num(num)
        if c in self.cache:
            return self.cache[c]
        rows = self.con.execute("SELECT id, citation FROM sec WHERE norm_cite=? ORDER BY id",
                                (statutes._norm_cite(c),)).fetchall()
        out = [{"id": r["id"], "citation": r["citation"]} for r in rows if _prefix(r["citation"]) == prefix]
        self.cache[c] = out
        return out

    def range_rows(self, prefix: str, a: str, b: str) -> list[dict]:
        lo, hi = self.cite(prefix, a), self.cite(prefix, b)
        if not self.con:
            return []
        ka, kb = natkey(norm_num(a)), natkey(norm_num(b))
        if lo and hi and lo[0]["id"] <= hi[-1]["id"]:
            rows = self.con.execute("SELECT id, citation FROM sec WHERE id BETWEEN ? AND ? ORDER BY id",
                                    (lo[0]["id"], hi[-1]["id"])).fetchall()
        elif lo or hi:
            anchor = (lo or hi)[0]["id"]
            rows = self.con.execute("SELECT id, citation FROM sec WHERE id BETWEEN ? AND ? ORDER BY id",
                                    (anchor - 400, anchor + 400)).fetchall()
        else:
            return []
        out = []
        for r in rows:
            if _prefix(r["citation"]) != prefix:
                continue
            k = natkey(norm_num(r["citation"][len(prefix):]))
            if ka <= k <= kb:
                out.append({"id": r["id"], "citation": r["citation"]})
        return out

    def _own(self) -> list[dict]:
        if self.row.get("id") is None:
            return []
        return [{"id": self.row["id"], "citation": self.row.get("citation")}]

    def unit_info(self, path: str | None, exact: bool = True) -> dict | None:
        if not path:
            return None
        u = self.tab.units.get(path) if self.tab else None
        if not u:
            return {"path": path, "first": None, "sections": 0, "exact": False}
        return {"path": path, "first": {"id": u[3], "citation": u[4]}, "sections": u[2], "exact": exact}

    def units_info(self, paths) -> dict | None:
        """A run of units ('Titles 11 through 27'): the first unit's path, the last one's as 'through', their first
        section and their size.  Not one level of the index, so never exact."""
        us = [(p, self.tab.units.get(p)) for p in paths or () if self.tab and self.tab.units.get(p)]
        if not us:
            return None
        first = us[0][1]
        return {"path": us[0][0], "through": us[-1][0], "first": {"id": first[3], "citation": first[4]},
                "sections": sum(u[2] for _, u in us), "exact": False}

    def rel_unit(self, lvl: str) -> tuple[str | None, bool]:
        path = self.row.get("path") or ""
        root = (self.tab.prefixes.get(self.own_prefix) or {}).get("root") if self.tab else None
        if lvl in ("code", "law"):
            return root or _parent(path) or None, True
        hit = _ancestor(path, lvl)
        if hit:
            return hit, True
        if lvl in ("chapter", "act"):
            return root or _parent(path) or None, bool(root)
        return _parent(path) or None, False

    def walk(self, base: str | None, chain: list) -> tuple[str | None, bool]:
        if base is None or not self.tab:
            return None, False
        cur = base
        chain = list(chain)
        if self.state == "wa":                               # 'chapter 71.09' is Title 71, Chapter 09
            fixed = []
            for lvl, d in chain:
                if lvl == "chapter" and "." in d:
                    ti, ch = d.split(".", 1)
                    fixed += [("title", _desig(ti)), ("chapter", _desig(ch))]
                else:
                    fixed.append((lvl, d))
            chain = fixed
        for lvl, d in chain:
            nxt = self._find_child(cur, lvl, d)
            if nxt is None:
                return cur, False
            cur = nxt
        return cur, True

    def _find_child(self, start: str, lvl: str, d: str, depth: int = 3) -> str | None:
        frontier = [start]
        for _ in range(depth):
            nxt = []
            for p in frontier:
                for clvl, cd, cpath in self.tab.children.get(p, []):
                    if clvl == lvl and cd == d:
                        return cpath
                    nxt.append(cpath)
            frontier = nxt
        return None

    def _anchor_unit(self, sec: dict, inner) -> str | None:
        r = self.con.execute("SELECT path FROM sec WHERE id=?", (sec["id"],)).fetchone() if self.con else None
        if not r or not inner:
            return None
        comps = [c for c in (r["path"] or "").split(" / ") if c][:-1]
        for k in range(len(comps) - 1, 0, -1):
            if _comp(comps[k]) == tuple(inner):
                return " / ".join(comps[:k + 1])
        return None

    def _unit_starting_at(self, sec: dict) -> str | None:
        """'(§ 58.1-520 et seq.)': the shallowest unit (below the code's root) whose first section is § 58.1-520."""
        r = self.con.execute("SELECT citation, path FROM sec WHERE id=?", (sec["id"],)).fetchone() if self.con else None
        if not r or not self.tab:
            return None
        root = (self.tab.prefixes.get(_prefix(r["citation"])) or {}).get("root") or ""
        comps = [c for c in (r["path"] or "").split(" / ") if c][:-1]
        for k in range(1, len(comps) + 1):
            p = " / ".join(comps[:k])
            u = self.tab.units.get(p)
            if u and len(p) > len(root) and u[3] == sec["id"]:
                return p
        return None

    def _by_numbering(self, path: str, chain: list) -> list[dict]:
        """Units the index paths do not hold, where the numbering shows them: RCW 23.95 Article 2 = 23.95.2xx;
        G.S. 57D Part 2 of Article 9 = 57D-9-2x."""
        if not self.tab or not self.con:
            return []
        u = self.tab.units.get(path)
        if not u:
            return []
        levels = dict(chain)
        rows = self.con.execute("SELECT id, citation, section_number FROM sec WHERE id BETWEEN ? AND ? ORDER BY id",
                                (u[0], u[1])).fetchall()
        out = []
        art, part = levels.get("article"), levels.get("part")
        for r in rows:
            num = r["citation"] or ""
            if self.state == "wa" and art and not part:
                last = num.rsplit(".", 1)[-1]
                if re.fullmatch(rf"{re.escape(art)}\d\d[A-Za-z]?", last):
                    out.append({"id": r["id"], "citation": r["citation"]})
            elif self.state == "nc" and art:
                m = re.search(r"§\s*([\dA-Z]+)-(\d+)-(\d+)$", num)
                if m and m.group(2).lstrip("0") == art.lstrip("0") and (not part or m.group(3).startswith(part)):
                    out.append({"id": r["id"], "citation": r["citation"]})
            elif self.state == "il" and art and not part:             # 105 ILCS 5 Article 1E = 5/1E-*
                if re.match(rf"{re.escape(art)}-", num.rsplit("/", 1)[-1], re.I):
                    out.append({"id": r["id"], "citation": r["citation"]})
        return out if len(out) <= MAX_MEMBERS else out[:1]

    # -- context
    def _article_is_section(self) -> bool:
        return any((self.row.get("citation") or "").startswith(p) for p in ARTICLE_SECTIONS.get(self.state, ()))

    def _depth(self, lvl: str) -> int:
        """How many outline levels a sub-section word spans: California 'subdivision' is the first level below
        the section; elsewhere 'subsection' is, and 'subdivision' or 'paragraph' the second."""
        if self.state in SUBDIVISION_FIRST:
            depth = {"subdivision": 1, "subsection": 1, "paragraph": 2, "subparagraph": 3, "clause": 4,
                     "subclause": 5, "item": 5}
        else:
            depth = {"subsection": 1, "subdivision": 2, "paragraph": 2, "subparagraph": 3, "clause": 4,
                     "item": 3 if self.state == "md" else 4, "subclause": 5}
        return depth.get(lvl, 1)

    def _last_pin(self, pos: int) -> str | None:
        for r in reversed(getattr(self, "_resolved", [])):
            if r.start < pos and r.pinpoint and r.sections and r.sections[0]["id"] == self.row.get("id"):
                return r.pinpoint
        return None

    def _last_federal(self, pos: int) -> bool:
        for r in reversed(getattr(self, "_resolved", [])):
            if r.start < pos and r.kind in ("federal", "named_act"):
                return r.kind == "federal"
        return False


def _named(a: _Atom) -> str | None:
    return (a.code or {}).get("named")


def _unit_level(kw: str) -> str:
    k = kw.lower()
    k = k[:-1] if k.endswith("s") else k
    return k


def _rel_level(word: str) -> str:
    w = word.lower()
    return w[:-1] if w.endswith("s") and w[:-1] in REL_LEVELS else w


def _num_shape(n: str) -> str:
    """'1203.4' -> '9.9', '7' -> '9', '54.1-204' -> '9.9-9'."""
    return re.sub(r"[A-Za-z]", "", re.sub(r"\d+", "9", norm_num(n)))


def _shape_ok(first: str, nxt: str) -> bool:
    """A bare list item must look like a section number of the same family: after a title-section number
    ('53.1-42', '57D-3-01', '10:2') only another such number ('53.1-43', not the '60' of '60 work days'); after a
    plain or decimal number (Cal. '987.8', Fla. '605.0112') any number."""
    hy = lambda x: bool(re.search(rf":|{_D}", x))   # noqa: E731
    return hy(nxt) or not hy(first)


@functools.lru_cache(maxsize=512)
def _compiled(p: str, flags: int):
    return re.compile(p, flags)


# ------------------------------------------------------------------ roles
_C = lambda p: re.compile(p, re.I | re.S)   # noqa: E731
# cues on the words just before the reference (or before its list's first item), each ending at it
DEFINITION = _C(r"\b(?:as\s+)?(?:(?:that|such|the|this)\s+terms?\s+(?:is|are)\s+)?(?:is\s+|are\s+)?defined\s+"
                r"(?:as\s+[\w\s'\-]{1,40}?\s+)?(?:in|by|under)\s+$|\bha(?:s|ve)\s+the\s+(?:same\s+)?meanings?\s+(?:as\s+)?"
                r"(?:(?:assigned|given|provided|ascribed|set\s+forth|defined|stated)\s+)?(?:(?:to\s+(?:it|them|that\s+term|"
                r"the\s+term)\s+)?(?:\"[^\"]{1,40}\"\s+)?(?:by|in|under)\s+)?(?:the\s+term\s+\S+\s+in\s+)?$|\bwithin\s+the\s+"
                r"meaning\s+of\s+$|\bto\s+refer\s+to\s+$")
OVERRIDE = _C(r"\bnotwithstanding\b|\bsupersedes?\b|\bprevails?\s+over\b")
EXCEPTION_NEAR = _C(
    r"\b(?:except|excepting)\b(?:\s+(?:as|to\s+the\s+extent)\s+(?:otherwise\s+)?(?:provided|specified|set\s+forth|"
    r"described|authorized|permitted|required|stated|prohibited)(?:\s+(?:for|from\s+disclosure))?(?:\s+(?:in|by|under))?)?"
    r"\s+$|\bunless\s+(?:otherwise\s+)?(?:specifically\s+)?(?:provided|specified|stated|prescribed)\s+(?:otherwise\s+)?"
    r"(?:in|by)\s+$|\bother\s+than\s+(?:(?:pursuant\s+to|under|as\s+provided\s+in)\s+)?$|\bnot\s+(?:be\s+)?subject\s+to\s+"
    r"(?:the\s+(?:\w+\s+){0,2}(?:provisions|requirements)\s+of\s+)?$|\bsubject\s+to\s+(?:the\s+(?:provisions|limitations)"
    r"\s+of\s+)?(?:any\s+limitations\s+provided\s+in\s+)?$|\bdoes\s+not\s+(?:modify|limit|supersede)\b[^.;]{0,120}$")
EXCEPTION_CHUNK = _C(r"\b(?:except(?!\s+as\s+otherwise\s+provided\s*$)|other\s+than|excluding|exempt(?:ed)?|does\s+not\s+"
                     r"include|unless\s+exempted)\b")
NOT_APPLY = _C(r"\b(?:does|do|shall|will|may)\s+not\s+apply\s+to\b")
PENALTY = _C(r"\b(?:punishable|punished|penalt(?:y|ies)|fines?|fined|surcharges?|assessments?|forfeitures?)\b"
             r"(?:\s+[\w,\-]+){0,8}?\s+(?:as\s+)?(?:provided|prescribed|set\s+forth|imposed|authorized|established|specified"
             r"|required|assessed)?\s*(?:in|by|under|pursuant\s+to)\s+$")
PREREQUISITE = _C(
    r"\b(?:dismissed|dismissal(?:\s+of\s+[\w\s]{1,30}?)?|obtained|granted|issued|entere?d?(?:s|ing)?(?:\s+into)?"
    r"(?:\s+[\w\-]+){0,4}?|referred(?:\s+[\w\-]+){0,3}?|registered|formed|organized|confined|withheld|accumulated"
    r"(?:\s+[\w\-]+){0,4}?|designated(?:\s+[\w,\-]+){0,8}?|deposited(?:\s+[\w\-]+){0,8}?|approved(?:\s+[\w\-]+){0,5}?|"
    r"determined(?:\s+[\w\-]+){0,5}?|requests?(?:ed)?(?:\s+[\w\-]+){0,6}?|made|filed|placed|computed|compromised\s+and\s+"
    r"settled|continuation(?:\s+[\w\-]+){0,6}?|identification(?:\s+[\w\-]+){0,6}?|receipt(?:\s+[\w\-]+){0,6}?|"
    r"receiving\s+notice|notices?(?:\s+(?:issued|to\s+appear))?|findings?|determination\s+made|showing(?:\s+of\s+\w+)?|"
    r"noncompliance|nondisclosure|agreements?|plans?|orders?(?:\s+[\w\-]+){0,3}?|certificates?(?:\s+of\s+\w+)?|"
    r"(?:licensed|certified|registered)(?:,?\s+(?:or\s+)?(?:licensed|certified|registered))*)\s+(?:pursuant\s+to|under|in\s+"
    r"accordance\s+with|as\s+provided\s+(?:in|under))\s+(?:the\s+provisions\s+of\s+)?$|\bha(?:s|ve)\s+complied\s+with\s+$|"
    r"\bfail(?:s|ed|ing)?\s+to\s+comply\s+with\s+(?:a\s+notice\s+under\s+|[\w\s]{0,40}?\s+under\s+)$|\bhearing\s+"
    r"(?:under|pursuant\s+to)\s+$")
AUTHORITY = _C(r"\b(?:authorized|authority|powers?|duties|conferred|delegated|adopted|promulgated|established|created|"
               r"administered|maintained|regulated|designated|permitted|issued\s+by\s+the\s+court|(?<!as\s)required)\b"
               r"(?:\s+[\w,\-]+){0,8}?\s+(?:by|under|pursuant\s+to|in|as\s+provided\s+in|in\s+accordance\s+with)\s+$|"
               r"\bacts?\s+under\s+$|\bby\s+the\s+\w+\s+under\s+$")
AUTHORITY_AGENT = _C(r"\b(?:agency|board|department|officer|official|entity|commission|person)\s+designated\s+"
                     r"(?:pursuant\s+to|under|by)\s+$")
# a fee schedule's item: a clause that begins 'For ...' and names an amount of money ('(a) For filing articles of
# organization pursuant to section two hundred three of this chapter, two hundred dollars.'): the reference says
# which filing the fee is for.  Not a 'For purposes of ...' clause: '(h) For purposes of making the computations
# required by Section 8 of Article XVI of the California Constitution, two billion ... dollars' says what a figure
# counts for, and its reference keeps the role its own cue gives it
FEE_ITEM = _C(r"^\W{0,4}(?:\(?\w{1,3}[.)]\s*)?for\s+(?!(?:the\s+|all\s+)?purposes?\b)"
              r"(?:the\s+|a\s+|an\s+|each\s+|every\s+)?\w+")
MONEY = _C(r"\$\s?\d|\bdollars?\b|\bcents?\b")
PROCEDURE = _C(r"\b(?:in\s+accordance\s+with|as\s+(?:provided|set\s+forth|specified|prescribed|described|directed)\s+(?:in|by|"
               r"under)|in\s+the\s+(?:same\s+)?manner\s+(?:provided|prescribed|permitted|required|described)\s+(?:in|by|under)|"
               r"pursuant\s+to\s+the\s+provisions\s+of|for\s+filing\s+(?:under|in\s+accordance\s+with)|procedures?\s+(?:set\s+"
               r"forth|provided|described|established)\s+(?:in|by)|procedures?\s+in|(?:under\s+)?the\s+process\s+described\s+"
               r"in|hearing\s+provisions\s+of|(?:deadlines?|time\s+limits?)\s+(?:set\s+forth|specified|prescribed|"
               r"established)\s+in|subject\s+to\s+the\s+(?:procedures|[\w\s]{0,30}?provisions)\s+(?:set\s+forth\s+in|of))\s+$|"
               r"\b(?:apply|applies|notify|file|filed|"
               r"submit|submitted|petition(?:\s+for\s+\w+)?|conference|relief(?:\s+available)?|expungement|sealing|merge|"
               r"correct|question|storage|served|review)\b(?:\s+[\w,\-']+){0,6}?\s+(?:pursuant\s+to|under|per|in\s+"
               r"accordance\s+with)\s+$")
CONDITION = _C(r"\b(?:compl(?:y|ies|ied|iance)\s+with|satisf(?:y|ies|ied)|meets?|consistent\s+with|in\s+conformity\s+with|"
               r"(?:requirements?|criteria|factors|qualifications|conditions|standards)(?:\s+(?:for\s+[\w\s]{1,20}?|set\s+forth|"
               r"specified|prescribed|established|required))?\s+(?:of|in|by|under)|eligible\s+[\w\s]{0,30}?(?:pursuant\s+to|"
               r"under)|not\s+in\s+conflict\s+with\s+[\w\s]{0,40}?of|purposes\s+set\s+forth\s+in)\b[^.;]{0,30}?$")
SCOPE = _C(r"\b(?:as\s+used\s+in|for\s+(?:the\s+)?purposes?\s+of|in|nothing\s+in|violat(?:es?|ions?|ing)(?:\s+of)?"
           r"(?:\s+any\s+(?:provision|of\s+the\s+provisions)\s+of)?|offenses?\s+(?:specified|listed|described)\s+(?:in|under)|"
           r"specified\s+in|described\s+(?:in|by)|listed\s+(?:in|under)|(?:the\s+)?provisions\s+of|enumerated\s+in|"
           r"offense\s+under)\s+$")
CONDITION_IF = _C(r"\b(?:if|unless|only\s+if|only\s+when|provided\s+that|when|whenever)\b[^.;:]{0,90}$")
CLAUSE = re.compile(r"(?<!\d)[.;:](?=\s)|\n\s*\n|\n[ \t]*(?=\(?[A-Za-z0-9]{1,4}[.)]\s)|—")


def role_of(text: str, start: int, end: int, kind: str | None, d: dict):
    """The role the target plays for the rule that cites it, from cue words around the reference.

    The words before the reference are read back to the start of its clause (for a list item, from the list's
    first item; New York's hard line breaks do not end a clause).  In order: a definition cue just before it
    ('as defined in', 'has the meaning given in'); 'notwithstanding' or 'supersedes' in the same comma-delimited
    chunk, or 'prevails' after it (override); an exception cue ('except as provided in', 'other than', 'exempt
    from', 'does not apply to', 'subject to', an enumeration whose lead-in 'does not apply to the following:', or a
    subject that 'shall not apply'); then the cue just before it: penalty ('punishable as provided in'), a fee
    schedule's item (a clause that begins 'For ...', not 'For purposes of ...', and names an amount of money:
    scope), prerequisite
    ('dismissed pursuant to', 'has obtained a certificate ... under', 'an order entered under'), authority
    ('regulations adopted pursuant to', 'authorized by'), procedure ('in accordance with', 'as provided in',
    'apply ... under'), condition ('comply with', 'the requirements of', an if-clause), scope ('As used in',
    'violation of', 'under this section').  Without a cue, 'under X' for another section reads as a prerequisite
    (a status or document produced under X: the commonest reading in the gold); a session law is history
    ('as amended by Chapter 857 of the Statutes of 1965': other); otherwise scope.
    Returns (role, confidence)."""
    s0, e0 = d.get("list_start", start), d.get("list_end", end)
    raw = text[max(0, s0 - 320):s0]
    clause = CLAUSE.split(raw)[-1]
    near = " ".join(clause.split())
    near = re.sub(r"[\s\[(\"“]+$", "", near)[-180:] + " "
    chunk = near.rsplit(",", 1)[-1]
    right = " ".join(text[e0:e0 + 160].split())
    right_clause = re.split(r"(?<!\d)[.;:](?=\s)", right)[0]
    relative = kind == "internal_relative" or getattr(d.get("atom"), "kind", None) == "rel"   # 'those chapters'
    if DEFINITION.search(near):
        return "definition", 0.85
    if OVERRIDE.search(chunk) or re.match(r"\W{0,3}prevails?\b", right, re.I):
        return "override", 0.85
    if EXCEPTION_NEAR.search(near) or EXCEPTION_CHUNK.search(chunk) or NOT_APPLY.search(near):
        return "exception", 0.8
    if len(near.split()) <= 4 and re.match(r"[^.;:]{0,90}?\b(?:shall|does|do|will|may)\s+not\s+(?:apply|be\s+applicable)\b",
                                           right_clause, re.I):
        return "exception", 0.7                    # 'The provisions of this chapter ... shall not apply'
    if len(near.split()) <= 6:                     # an enumerated item: its lead-in ('does not apply to the following:')
        lead = text[max(0, s0 - len(clause) - 400):max(0, s0 - len(clause))]
        if re.search(r"(?:not\s+apply\s+to|exempt\w*|except\w*)\b[^.;]{0,160}:\s*(?:\(?[A-Za-z0-9]{1,4}[.)]\s*)*$", lead,
                     re.I):
            return "exception", 0.6
    if PENALTY.search(near) and not (relative and re.search(r"\bunder\s+$", near)):
        return "penalty", 0.8
    if FEE_ITEM.search(" ".join(clause.split())) and MONEY.search(right_clause):   # 'For filing ..., $200'
        return "scope", 0.6
    if AUTHORITY_AGENT.search(near):
        return "authority", 0.7
    if relative:                                   # 'orders entered pursuant to this subsection': what the rule covers
        if re.search(r"\b(?:authority|powers?|duties)\b", near, re.I) and AUTHORITY.search(near):
            return "authority", 0.7
        if PROCEDURE.search(near):
            return "procedure", 0.7
    else:
        for role, pat in (("prerequisite_process", PREREQUISITE), ("authority", AUTHORITY), ("procedure", PROCEDURE)):
            if pat.search(near):
                return role, 0.7
    if CONDITION.search(near):
        return "condition", 0.65
    if CONDITION_IF.search(near) and not relative:
        return "condition", 0.5
    if SCOPE.search(near) or relative or kind == "generic":
        return "scope", 0.5
    if kind == "session_law":                      # 'as amended by Chapter 857 of the Statutes of 1965': history
        return "other", 0.3
    if kind in ("federal", "regulation", "court_rule", "constitution"):
        return "condition", 0.3
    if re.search(r"\bunder\s+$", near, re.I) and not re.search(r"\b(?:offen[cs]es?|violations?|charged|convicted)\b",
                                                                 near, re.I):
        return "prerequisite_process", 0.4
    if kind == "named_act":
        return "condition", 0.3
    return "scope", 0.3


# ------------------------------------------------------------------ the public function
def references(state: str, row: dict, text: str | None = None) -> list[Reference]:
    """Every reference in one index row's text (or in ``text``, read as if it were that row's), resolved against
    the state's index.  Without an index the spans, kinds, pinpoints and roles are still returned."""
    row = dict(row or {})
    p = _index_file(state)
    con = _connect(p) if p else None
    try:
        if text is None:
            if con is None or row.get("id") is None:
                return []
            r = con.execute("SELECT text FROM body WHERE id=?", (row["id"],)).fetchone()
            text = (r["text"] if r else "") or ""
        if con is not None and row.get("id") is not None and not (row.get("citation") and row.get("path")):
            r = con.execute("SELECT citation, path FROM sec WHERE id=?", (row["id"],)).fetchone()
            if r:
                row.setdefault("citation", r["citation"])
                row["path"] = row.get("path") or r["path"]
        try:
            tab = table(state) if con is not None else None
        except sqlite3.Error:
            tab, con = None, None
        parser = _Parser(state, row, text, tab, con)
        drafts = parser.run()
        groups: dict[int, int] = {}
        ends: dict[int, int] = {}
        for d in drafts:
            if d.get("group"):
                groups.setdefault(d["group"], d["start"])
                d["list_start"] = groups[d["group"]]
                ends[d["group"]] = d["end"]
        for d in drafts:
            if d.get("group"):
                d["list_end"] = ends[d["group"]]
        out: list[Reference] = []
        parser._resolved = out
        for d in drafts:
            out.append(parser.resolve(d))
        return out
    finally:
        if con is not None:
            con.close()


def edges(state: str, row: dict, text: str | None = None) -> list[dict]:
    """The resolved references as edges (one per target section), for storing or ranking."""
    out = []
    for r in references(state, row, text):
        for s in r.sections:
            out.append({"source": row.get("id"), "target": s["id"], "target_citation": s["citation"],
                        "kind": r.kind, "role": r.role, "pinpoint": r.pinpoint, "span": r.span, "start": r.start})
    return out
