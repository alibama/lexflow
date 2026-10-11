"""Defined terms and roles in statute text, and a small classifier that suggests Wikidata items for review.

**Definitions.**  ``definitions(state, row)`` reads one index row's text and returns every term the section
defines or names, each as a :class:`Term`: the term, its defining span with character offsets, the kind of
definition, and the unit the definition governs (``scope_unit``, an index path taken from the row's own path:
"As used in this chapter" in Fla. Stat. § 119.011 -> ``Florida Code / Title X / Chapter 119``).  The forms found:

    means          "X" means / X shall mean / The word "X" shall have the following meaning / (1) Owner. - The ...
                   (a North Carolina list item: see below)
    includes       "X" includes / The terms "X" and "Y" include / "X" shall be defined to include / X also includes
                   (a term already defined here)
    excludes       "X" does not include / shall not apply
    by_reference   "X" has the meaning assigned by ...; X, as defined in § N; defined as X in section N; "X" means
                   X as defined in § N
    parenthetical  ... University of the District of Columbia ("University")
    contents       "X" shall contain ...; The articles of merger shall state the following:
    acts_as        One or more persons may act as the incorporator or incorporators of a corporation ...
    establishes    There is established the Commission on ...
    heading        a section heading that names a role or document ("Incorporators.", "Registered agent.")

A North Carolina list item "(1) Owner. - The holder ..." is a definition only inside the list a lead-in opens, or,
outside every such list, in a section whose heading is about definitions alone ("Definitions.", not "Definitions;
description of boundaries.") and before any lead-in, not counting one inside an earlier definition item ("(1) ...
As used in this subdivision, the following terms apply:" opens a list of its own but does not end the heading's).
N.C. captions ordinary subsections the same way ("(b) Punishment. - A person who violates ..."), so a lead-in's
list ends at the next line that opens with an enumerator of the lead-in's own kind: in "(a) ... For purposes of
this section: (i) ..." it ends at "(b)".  A lower-case "(i)", "(v)" or "(x)" is a roman numeral unless the lead-in's
line has the letter before it ("(h) ... As used in this section:", then "(i) Rights of ..."): then it is that
letter, which ends the list, unless "(ii)" ("(vi)", "(xi)") opens a line before "(j)" ("(w)", "(y)") does.  An item
that quotes its own term ('(3) Mayor. — The term “Mayor” means') gives one Term, the quoted definition; when no
definition of the quoted term is found there ('(1) Adjustment. - "Adjustment" is an act ...'), the item is the
Term.  The rule is a reading of layout, not of meaning: a caption inside a list, or a list laid out without line
breaks, can still be misread.

Scope comes from the definition's own clause ("For purposes of this subsection (g), ...", 'The term "infant", as
used in this chapter, ...'), else from a lead-in: one that ends in a colon or a dash ("As used in this chapter,
the term:", "For purposes of this part —", "The following definitions apply in this Article:", also after a
caption, "(a) Definitions. - For the purpose of this Article:") or a sentence that says where the definitions
apply ("the definitions in this section apply throughout this chapter", "In this subtitle the following words
have the meanings indicated", the UCC's "words or phrases defined in this section, or in ... other titles of the
Maryland Uniform Commercial Code ..."), else from a definitions heading (the enclosing unit), else the section
itself.  Sub-section scopes keep the section's path and add ``scope_pinpoint``.  :func:`resolve_scope` turns the
words into a unit and records how in ``scope_basis``: on the index path; a named unit from :data:`NAMED_UNITS`
(the Maryland UCC is Titles 1-10 of the Commercial Law article); where the path lacks the level (subchapters in
D.C. and Texas, Articles and Parts in North Carolina and Illinois, parts in Maryland, "this act"), a unit anchored
to the section it holds, under the deepest unit of the path that can contain it ('MD Code / Article ggp / Title 5
/ Subtitle 8 / Part containing § 5-857'); a compound scope ("this section and to ss. 605.1006 and
605.1062-605.1072", "this chapter, Chapter 4, Chapter 5, and Chapter 6 of this title") has no one unit, and
``scope_parts`` lists its parts; a run of comma parts counts only when "and" or "or" closes it.  A list of sections
("As used in sections 13-101, 13-103, 13-105 and 13-107") has no unit; the words stay in ``scope``.  Section
numbers may carry footnote asterisks ("RCW * 43.215.145 , * 43.215.147") or be written in words ("sections eleven
hundred seven and eleven hundred eight", without an "and" inside a number).

A role defined by what a person "may act as" governs the chapter it sits in (the incorporator of Fla. Stat.
§ 607.0201 is the Florida Business Corporation Act's incorporator); a heading term governs its own section,
unless the text defines it as an item under a lead-in.  Keys: :func:`term_key`, :func:`group_by_key` (several
definitions can share one key), :func:`unit_key`, :func:`concept_key` (a reviewer's name, with a sense suffix for
homonyms).  A key is made by :func:`slug` and :func:`key_singular`, both frozen at :data:`KEY_VERSION` 1 and
neither touched by the matcher's :func:`norm_term`: improving the matcher's normalisation moves no key, but a key
does move when the extractor captures other words or another pinpoint for a term.

**Wikidata suggestions, for review only.**  ``link(term, candidates)`` -> ``(qid or None, p)``: a logistic
regression over 29 cheap features of each Wikidata search candidate (label and alias match, word overlap, cue
words in the description, P31/P279 classes, a specific statute, jurisdiction, sitelinks, search rank, competing
label matches), fitted on the hand-labelled survey ``fixtures/xref/wikidata_terms.json`` (714 candidates of 150
terms) and evaluated leaving one term out by ``scripts/terms_eval.py``, which also prints :data:`LINK_MODEL`.  A
returned qid is a suggestion for the review queue, never a match: an exact-match statement is written only after
a person has reviewed the pair.  The queue's threshold, :data:`REVIEW_THRESHOLD`, is 0.5, the model's even-odds
point, not a value searched for on the survey's scores: out of fold it suggests 91 terms, 77 exact (precision
0.85, 95% lower bound 0.76); the other 14 are 11 broader or related concepts, two different things (the 18 U.S.C.
§ 2257 custodian of records, and the PropBank "incorporator") and one that possibly is (civil restitution).  The
cue lists name no PropBank tokens any more (they encoded the survey's answers), so the PropBank "incorporator",
Q140403634, scores 0.73 out of fold (0.69 shipped) and is queued: the reviewer, not the score, keeps it out.  A
threshold tuned to out-of-fold precision 0.90 (0.7607) would have excluded it only because that one term's label
places it.  No threshold is shown to give precision 0.95: that target links 2 terms out of fold, with a lower
bound near 0.16.  Pair AUC 0.947.  Items with neither a description nor a class are never suggested.  An optional
embedding-similarity feature (``embed=``, nomic-embed-text over the term, its context and the candidate) is not in
the shipped model, so nothing here needs a model server or the network.
"""
from __future__ import annotations

import json
import math
import re
from bisect import bisect_right
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..municipal.states import NAME as STATE_NAME

SURVEY = Path(__file__).resolve().parents[2] / "fixtures" / "xref" / "wikidata_terms.json"


@dataclass
class Term:
    term: str                          # as written ("Public body"); a heading term is lower-cased, and heading,
    #                                    "may act as" and "defined as" terms are made singular by key_singular
    definition_span: str | None        # the defining words; for a heading, the heading segment
    scope_unit: str | None             # index path of the unit the definition governs (None: not expressible)
    kind: str                          # means | includes | excludes | by_reference | parenthetical | contents |
    #                                    acts_as | establishes | heading
    start: int | None                  # offsets of definition_span in the text (None for a heading)
    end: int | None
    scope: str | None = None           # the scope as the text words it: "this chapter", "this subsection (g)"
    scope_pinpoint: str | None = None  # "(3)", "(g)", "A": the scope is that sub-section of the section
    term_start: int | None = None      # offset of the term itself (first mention, for a heading)
    source: str = "text"               # text | heading | heading+text
    category: str = "other"            # role | document | other (a cheap guess from the head word)
    defined_in: str | None = None      # by_reference: the words that name where the meaning is
    scope_basis: str | None = None     # how scope_unit was found (see resolve_scope): path | named | anchored |
    #                                    compound | heading | default; None when no unit expresses the scope (a list
    #                                    of sections)
    alternatives: list[str] = field(default_factory=list)   # the other terms of '"X" or "Y" means ...'
    # a compound scope's parts, each (words, unit or None): [("this section", ".../Section 605.1061"),
    # ("ss. 605.1006 and 605.1062-605.1072", None)]; empty for a one-unit scope
    scope_parts: list[tuple[str, str | None]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ text helpers
_QT = r'[“"](?=[^\s“”"])[^“”"]{1,90}?(?<=\S)[”"]'                 # one quoted term
# "A" or "B"; "A," "B," and ...  Each piece of the separator starts with its own kind of character (space, comma,
# a word, the next quote), so a run of spaces can be split only one way.  The earlier '\s*[,;]?\s*(?:or|and)?\s*'
# could split it three ways, and a failed match retried 3**n splits: N.C. Gen. Stat. § 14-107.1, 18 quoted
# reasons for dishonor and no definition verb, never finished.  Same strings matched; now linear in the list.
_SEP = r'\s*(?:[,;]\s*)?(?:(?:and/or|or|and)\s*)?'
_LIST = rf'{_QT}(?:{_SEP}{_QT})*'
_VERB = (r"(?:shall\s+mean(?:\s+and\s+include)?|means|mean|(?:is|shall\s+be)\s+defined\s+as|refers?\s+to|"
         r"(?:shall\s+have|has|have)\s+the\s+following\s+meanings?|"
         r"(?:shall\s+)?(?:has|have)\s+the\s+(?:same\s+)?meaning|"
         r"(?:also\s+)?includes|(?:shall|may)\s+(?:also\s+)?include|(?:also\s+)?include|"
         r"(?:shall\s+be|is|are)\s+(?:defined|deemed)\s+to\s+(?:include|mean)|"
         r"(?:does|do|shall)\s+not\s+(?:include|apply)|is\s+limited\s+to|(?:is|are)\s+to\s+be\s+read|"
         r"(?:is|are)\s+not\s+exclusive|shall\s+be\s+construed|shall\s+contain|shall\s+consist\s+of|consists\s+of)\b"
         r"(?!-)")                                                    # not "means-tested"
# a list of sections as a scope: "sections 13-101, 13-103 and 13-107", "RCW 39.23.005 and 39.23.020"; a section
# number may carry the reviser's footnote asterisks ("RCW * 43.215.145 , * 43.215.147 , and ** 43.121.185", RCW
# 43.216.157), and New York writes some in words ("sections eleven hundred seven and eleven hundred eight", N.Y.
# LLC Law § 1106)
_SECNUM = r"(?:\*+\s*)?\d(?:[\w.\-–]*\w)?(?::\d(?:[\w.\-]*\w)?)?"   # 876.37-876.50, 57-35.35:1 (not the colon after)
_NUMWORD = (r"(?:(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:-(?:one|two|three|four|five|six|seven|"
            r"eight|nine))?|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|one|two|three|"
            r"four|five|six|seven|eight|nine|ten|hundred|thousand)(?![\w\-])")
_NUMW = rf"{_NUMWORD}(?:\s+{_NUMWORD})*"                          # "eleven hundred seven" (no "and" inside)
_SECTIONS = (rf"(?:(?:sections?|§§?|RCW|ss?\.|G\.S\.|[Cc]hapters|[Aa]rticles)\s*{_SECNUM}"
             rf"(?:(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or|through|to)\s+)(?:sections?\s+|§§?\s*)?{_SECNUM})*|"
             rf"sections?\s+{_NUMW}(?:(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or|through|to)\s+)(?:sections?\s+)?"
             rf"{_NUMW})*)")
_UNIT = (r"(?:this\s+(?:section|subsection|subdivision|paragraph|chapter|subchapter|article|title|subtitle|part|"
         r"subpart|division|act|code|definition)(?:\s*\(\s*[\w.\-]+\s*\))?|herein|"
         rf"section\s+[\w.\-]+\s+of\s+this\s+(?:act|chapter|article|title|code)|"
         # another unit than the section's own, which no unit here expresses: "Chapter 10 (§ 63.2-1000 et seq.) of
         # this title" (Va. Code § 63.2-1100)
         rf"(?:chapter|article|part|subchapter|subtitle|title)\s+[\w.\-]+(?:\s*\([^)]{{0,40}}\))?\s+of\s+this\s+"
         rf"(?:title|code|article|chapter|act|subtitle|division)|{_SECTIONS})")
# The rest of a compound scope: "this section and to ss. 605.1006 and 605.1062-605.1072" (Fla. Stat. § 605.1061),
# "this Article and Articles 21A and 21B of this Chapter" (N.C. Gen. Stat. § 143-212), "this Part or Parts 1 and 2
# of this Article" (N.C. Gen. Stat. § 115C-563), "this section and RCW 24.03A.715 through ...", "this chapter and
# Chapter 10 (...) of this title", "this chapter, chapter 259, chapter 260, or chapter 375" (Fla. Stat. § 253.025),
# "this section and sections eleven hundred seven and eleven hundred eight of this article" (N.Y. LLC Law § 1106).
# Matched one part at a time (see _also_parts), never as a nested repetition.
_LEVELS = (r"(?:sub)?(?:chapter|article|part|title|division)s?|subtitles?|subsections?|subdivisions?|paragraphs?|"
           r"acts?|sections?")
_NUMS = rf"(?:\(\s*[\w.\-]+\s*\)|(?-i:\d[\w.\-]*\w|\d|[IVXL]+(?![a-z]))|{_NUMW})"
_OTHER = (rf"(?:(?:{_LEVELS})\s+{_NUMS}(?:(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or|through|to)\s+){_NUMS})*"
          rf"(?:\s*\([^)]{{0,40}}\))?(?:\s+of\s+this\s+(?:title|code|article|chapter|act|subtitle|division|part))?"
          rf"(?:\s+RCW)?|{_SECTIONS}|this\s+(?:{_LEVELS}|code))")
_ALSO_TAIL = r"(?=[\s,.:;—–\-]|$)"
ALSO = re.compile(rf"(?i:(?:\s*,\s*|\s+)(?:and|or)\s+(?:(?:to|in|throughout|for|under)\s+)?)"
                  rf"(?P<also>(?i:{_OTHER})){_ALSO_TAIL}")
# a middle part of "this chapter, chapter 2, chapter 3, and chapter 4": a comma alone, then a part.  _also_parts
# keeps a run of these only when "and"/"or" follows the run's last part, so "this chapter, chapter 2, the rules"
# stays one unit.
ALSO_COMMA = re.compile(rf"\s*,\s*(?P<also>(?i:{_OTHER})){_ALSO_TAIL}")
_AND_NEXT = re.compile(r"\s*,?\s+(?i:and|or)\s")
_INTRO = (r"(?:as\s+used\s+in|as\s+used(?=\s+herein)|when\s+used\s+in|for\s+(?:the\s+)?purposes?\s+of|"
          r"in\s+construing|in|"
          r"unless\s+the\s+context\s+(?:otherwise\s+)?requires,?\s+(?:as\s+used\s+)?in)")
SCOPE_LEAD = re.compile(rf"(?i:{_INTRO})\s+(?P<u>(?i:{_UNIT}))(?=[\s,:;]|$)")
SCOPE_INNER = re.compile(rf"(?i:as\s+used\s+in|as\s+used(?=\s+herein))\s+(?P<u>(?i:{_UNIT}))")
# the scope words right before a definition in mid-sentence: "As used in sections 13-101, ... and 13-107, the term"
SCOPE_BEFORE = re.compile(rf"(?i:{_INTRO})\s+(?P<u>(?i:{_UNIT}))\s*,?\s*$")
# a sentence that says where the section's definitions apply, without a colon lead-in:
#   "the definitions in this section apply throughout this chapter" (Wash.), "The following definitions apply in
#   this Article:" (N.C.), "the definitions in this section govern the construction of this chapter" (Cal.), and
#   the UCC's general definitions, "words or phrases defined in this section, or in the additional definitions
#   contained in other titles of the Maryland Uniform Commercial Code that apply to ..., have the meanings stated"
_NAMED = r"the\s+(?:[A-Z][\w.]*\s+){0,4}?(?:Code|Act)"
DECLARE = re.compile(
    rf"(?i:\b(?:the\s+)?(?:following\s+)?(?:definitions?|words\s+and\s+phrases)\s+"
    rf"(?:(?:in|of|contained\s+in|set\s+(?:forth|out)\s+in)\s+this\s+section\s+)?(?:shall\s+)?"
    rf"(?:apply|applies|(?:are|is)\s+applicable|govern\s+(?:the\s+)?(?:construction|interpretation)\s+of)\s+"
    rf"(?:(?:in|to|throughout|for\s+(?:the\s+)?purposes?\s+of)\s+)?)(?P<u>(?i:{_UNIT}))(?=[\s,.:;]|$)|"
    rf"(?i:\bwords\s+(?:or|and)\s+phrases\s+defined\s+in\s+this\s+section,?\s+or\s+in\s+the\s+additional\s+"
    rf"definitions\s+contained\s+in\s+other\s+\w+\s+of\s+)(?P<n>(?i:this\s+\w+)|{_NAMED})\s+(?i:that|which)\s+apply|"
    # Maryland: "(a) In this subtitle the following words have the meanings indicated."
    rf"(?i:\bin\s+)(?P<w>(?i:{_UNIT}))(?i:\s*,?\s+(?:the\s+following\s+(?:words|terms|phrases)\s+have\s+the\s+"
    rf"meanings?|(?:the\s+)?definitions?\b[^.;:“”\"]{{0,100}}?\b(?:apply|applies|have\s+the\s+meanings?)))|"
    # N.C. Gen. Stat. § 15A-1368: "(a) The following words have the listed meaning in this Article:"
    rf"(?i:\b(?:the\s+)?following\s+(?:words|terms|phrases)\s+(?:shall\s+)?have\s+the\s+(?:listed\s+|stated\s+)?"
    rf"meanings?\s+(?:in|for|throughout)\s+)(?P<v>(?i:{_UNIT}))(?=[\s,.:;]|$)")
# "(1) Owner. - The holder of the title ...": a North Carolina list item, or a caption of the same shape; definitions()
# reads it as a definition only inside a lead-in's list or under a heading about definitions alone
DASH_DEF = re.compile(r"(?P<t>[A-Z][\w'’\-]*(?:\s+[\w'’\-]+){0,6}?)\.\s*(?:-{1,2}|[–—])\s*(?=\S)")
_DASH_VERBS = {"is", "are", "be", "been", "was", "were", "shall", "may", "must", "will", "has", "have", "had", "not",
               "does", "do", "can", "would", "should"}
# subsection captions, not terms ("(a) Applicability. - ..."); "(2) Record. - Information that ..." is a term
_DASH_CAPTIONS = {"applicability", "scope", "purpose", "short title", "construction", "rules of construction",
                  "general provision", "general", "generally", "severability", "effective date", "intent",
                  "legislative intent", "finding", "legislative finding", "authority", "duty", "requirement",
                  "procedure", "application", "violation", "liability", "repeal", "exception", "exemption", "penalty",
                  "applicability and scope", "rule", "provision", "eligibility", "reserved", "repealed"}
_DASH_NOT = re.compile(r"(?:This|These|Except|Unless|Nothing|Notwithstanding|Subject\s+to|The\s+following|In\s+addition|"
                       r"For\s+(?:the\s+)?purposes|As\s+used|When|If|No\s)\b")
DEF_A = re.compile(rf'(?P<list>{_LIST})(?P<gap>\s*,[^“”";:]{{0,160}}?,\s*|'
                   rf'\s+(?:for|within|under)\s[^“”";:]{{1,160}}?,\s*|'
                   rf'\s+as\s+used\s+in\s+[^“”";:,]{{1,60}}?\s+|'
                   # the UCC's general definitions: '"Agreement", as distinguished from "contract", means',
                   # '"Send" in connection with a writing, record, or notice means', '"Burden of establishing" a fact
                   # means'
                   rf'\s*,\s*as\s+distinguished\s+from\s+{_QT}\s*,\s*|'
                   rf'\s+in\s+connection\s+with\s[^“”";:]{{1,80}}?\s+|\s+(?:an?|the)\s+[a-z]+\s+(?=means\b)|'
                   rf'\s+)(?P<verb>{_VERB})')
DEF_WORDS = re.compile(rf'\b[Tt]he\s+(?:terms?|words?|phrases?|expressions?)\s+(?P<list>{_LIST})'
                       rf'(?P<rest>[^.;“”"]{{0,100}}?)(?P<verb>{_VERB})')
# "X shall mean"; not "by means of" or "Any means-tested benefit program" (N.C. Gen. Stat. § 108A-25.3)
UNQUOTED = re.compile(r"\b(?:shall\s+mean(?:\s+and\s+include)?|means)\b(?!-)(?!\s+of\b)")
ACTS_AS = re.compile(r"\b(?:[Oo]ne\s+or\s+more|[Tt]wo\s+or\s+more|[Aa]ny|[Aa]n?|[Ee]ach)\s+(?:natural\s+)?"
                     r"(?:persons?|individuals?|entit(?:y|ies))\s+(?:may|shall|must|can)\s+(?:act|serve)\s+as\s+"
                     r"(?:the\s+|an?\s+)?(?P<t>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*){0,3}?)"
                     r"(?=\s+or\b|\s+(?:of|to|for|by|under|in|on|with)\b|\s*[,.;])")
CONTENTS = re.compile(r"(?:^|(?<=\n)|(?<=[.:;]\s)|(?<=\)\s))The\s+(?P<t>[a-z][a-z\-]*(?:\s+[a-z][a-z\-]*){0,5}?)\s+"
                      r"(?:shall|must)\s+(?:set\s+forth|state|contain|include)(?:\s+the\s+following)?\s*:")
ESTABLISHES = re.compile(r"\bThere\s+(?:is|are)\s+(?:hereby\s+)?(?:established|created|constituted)?\s*"
                         r"(?:(?:with)?in\s+the\s+[A-Z][\w ]+?\s+)?(?:a|an|the)\s+"
                         r"(?P<t>[A-Z][\w'’\-]*(?:\s+(?:[A-Z][\w'’\-]*|of|and|on|for|the|in))*?)"
                         r"(?=\s+(?:in|within|as|which|that|to|under|is|shall|with)\b|\s*[.,;(])")
PAREN = re.compile(r'\((?:the\s+|hereinafter(?:\s+(?:called|referred\s+to\s+as))?\s+|collectively,?\s+|'
                   r'each\s+an?\s+|an?\s+)?[“"](?P<t>[^“”"]{1,60})[”"]\)')
BY_REF = re.compile(r",?\s+as\s+(?:that\s+term\s+is\s+|such\s+term\s+is\s+|the\s+term\s+is\s+|those\s+terms\s+are\s+)?"
                    r"defined\s+(?:in|by|under)\b")
DEFINED_AS = re.compile(r"\bdefined\s+as\s+(?P<t>[a-z][\w\-]*(?:\s+[a-z][\w\-]*){0,4}?)\s+in\s+"
                        r"(?:section|§|subdivision|article|chapter|s\.|title)", re.I)
# where a meaning is given: up to the end of the clause, but not at the period of "G.S." or "s."
WHERE = re.compile(r"(?:assigned\s+by|given\s+(?:to\s+[^,;]{0,40}?\s+)?in|provided\s+in|defined\s+(?:in|by|under)|"
                   r"as\s+in)\s+(?P<w>[^;)]{2,80}?)"
                   r"(?=[;)]|,\s|(?<!\bG\.S)(?<!\bU\.S\.C)(?<!\bss)(?<!\bs)(?<!\bch)(?<!\bSec)\.(?:\s|$)|$)", re.I)
DEFINITIONS_HEADING = re.compile(r"^\s*(?:definitions?\b|[“\"].+[”\"]\s+defined\b|meaning\s+of\s+(?:terms|words))",
                                 re.I)
EFFECTIVE = re.compile(r"^\s*\((?:Effective|Eff\.)\s[^)]*\)\s*", re.I)
ABBREV = {"s", "ss", "ch", "sec", "secs", "no", "nos", "art", "arts", "par", "subd", "inc", "co", "corp", "ltd", "st",
          "seq", "e.g", "i.e", "v", "vs", "u.s", "u.s.c", "c.f.r", "cfr", "fla", "stat", "va", "ann", "gen", "md",
          "tex", "cal", "n.y", "n.c", "d.c", "g.s", "ilcs", "mr", "mrs", "dr", "jr", "approx", "p.a", "pub", "l", "rev"}
_DET = {"a", "an", "the", "any", "all", "each", "every", "such", "this", "that", "these", "those", "its", "his",
        "her", "their", "no", "other", "said", "same"}
_PREP = {"of", "in", "for", "to", "by", "with", "under", "on", "from", "at", "as", "upon", "into", "about", "than",
         "between", "including", "or", "and", "nor"}
_VERBISH = {"is", "are", "be", "been", "was", "were", "shall", "may", "must", "will", "has", "have", "had", "who",
            "which", "that", "if", "when", "where", "not", "does", "do", "can", "would", "should",
            "means", "mean", "includes", "include"}       # '"Woodland" means woodland as defined in ...'
# words that take an "of"/"in" complement inside one term: "severe form of trafficking in persons"
_RELATIONAL = {"form", "forms", "type", "types", "kind", "kinds", "class", "classes", "certificate", "certificates",
               "articles", "statement", "notice", "plan", "letters", "letter", "order", "writ", "trafficking",
               "possession", "abuse", "use", "transfer"}
_STRUCTURAL = {"chapter", "section", "subsection", "article", "title", "subtitle", "part", "division", "act", "code",
               "law", "laws", "statute", "statutes", "subdivision", "paragraph", "term", "terms", "meaning", "same"}
# heading segments that name no particular role, document or process
GENERIC_HEADINGS = {"definition", "name", "fee", "power", "purpose", "formation", "exemption", "security", "penalty",
                    "applicability", "scope", "short title", "construction", "rules of construction", "organization",
                    "general provision", "severability", "effective date", "intent", "legislative intent", "finding",
                    "legislative finding", "authority", "duty", "requirement", "procedure", "application", "violation",
                    "liability", "record", "report", "repeal", "amendment", "transition", "reserved", "repealed",
                    "expired", "renumbered", "transferred", "miscellaneous", "applicability and scope", "rule",
                    "provision", "powers and duty", "rights and duty", "eligibility", "notice", "filing", "exception",
                    # a statement of policy names no term ("Declaration of policy.", seed 14 of the re-check)
                    "declaration of policy", "declaration of purpose", "legislative declaration", "policy",
                    "legislative policy", "public policy", "statement of purpose", "statement of policy",
                    "description"}             # "Definitions; description of boundaries."
_HEAD_STOP = {"to", "not", "shall", "may", "must", "by", "against", "with", "without", "upon", "under", "from", "into",
              "in", "at", "as", "is", "are", "be", "if", "when", "where", "whether", "which", "who", "that", "or",
              "certain", "other", "general", "specific", "special", "additional", "miscellaneous", "concerning",
              "regarding", "relating", "etc", "the", "a", "an", "this", "each", "any", "all", "use", "used"}
_ROLE_HEADS = {"agent", "officer", "official", "clerk", "attorney", "board", "commission", "agency", "court", "judge",
               "director", "department", "person", "individual", "entity", "body", "custodian", "representative",
               "member", "manager", "partner", "shareholder", "requester", "applicant", "defendant", "victim",
               "guardian", "owner", "employee", "employer", "registrant", "licensee", "debtor", "creditor",
               "beneficiary", "retiree", "legislature", "judiciary", "university", "council", "authority",
               "secretary", "sheriff", "prosecutor", "counsel", "administrator", "trustee", "visitor", "firm",
               "corporation", "company", "partnership", "organization", "office", "division", "bureau", "utility",
               "media", "unit", "team", "panel", "commissioner", "mayor", "governor", "inmate", "prisoner", "offender",
               "party", "public", "state", "county", "municipality", "government"}
_DOC_HEADS = {"record", "certificate", "articles", "article", "statement", "agreement", "contract", "notice", "order",
              "application", "report", "license", "letter", "letters", "petition", "request", "form", "copy",
              "document", "filing", "writ", "plan", "bond", "receipt", "warrant", "summons", "subpoena", "decision",
              "judgment", "return", "registration", "list", "permit", "deed", "instrument", "affidavit", "complaint"}
_NOT_AGENT = {"merger", "order", "number", "paper", "matter", "chapter", "transfer", "letter", "power", "water",
              "register", "error", "factor", "sector", "corridor", "interior", "minor", "major", "content", "consent",
              "extent", "intent", "event", "percent", "agreement", "statement", "payment", "element",
              "component", "accident", "incident", "patent", "talent", "detainer", "cover", "offer", "border"}


def _ws(s: str) -> str:
    return " ".join((s or "").split())


# plurals that are not the plural of the singular word: "damages" (money awarded) is not "damage" (harm)
_NO_SINGULAR = {"damages", "premises", "means", "series", "species", "news", "proceeds", "goods", "arrears",
                "earnings", "savings", "headquarters", "whereabouts", "remains", "thanks", "riches", "lees", "minutes"}
_IRREGULAR = {"gases": "gas", "statuses": "status", "buses": "bus", "censuses": "census", "viruses": "virus",
              "bonuses": "bonus", "campuses": "campus", "surpluses": "surplus", "prospectuses": "prospectus",
              "apparatuses": "apparatus", "consensuses": "consensus", "nexuses": "nexus", "analyses": "analysis",
              "crises": "crisis", "theses": "thesis", "diagnoses": "diagnosis", "prognoses": "prognosis",
              "hypotheses": "hypothesis", "parentheses": "parenthesis", "syntheses": "synthesis",
              "children": "child", "men": "man", "women": "woman"}


def _singular(w: str) -> str:
    """The matcher's singulariser, for :func:`norm_term` only; free to improve (keys use :func:`key_singular`)."""
    lw = w.lower()
    if lw in _NO_SINGULAR:
        return w
    if lw in _IRREGULAR:
        sg = _IRREGULAR[lw]
        return sg.upper() if w.isupper() else sg.capitalize() if w[:1].isupper() else sg
    if len(lw) <= 3 or lw.endswith(("ss", "us", "is", "ics")):
        return w
    if lw.endswith("ies") and len(lw) > 4:
        return w[:-3] + ("Y" if w[-1].isupper() else "y")
    if lw.endswith(("ches", "shes", "xes", "sses")):
        return w[:-2]
    if lw.endswith("s"):
        return w[:-1]
    return w


def norm_term(s: str) -> str:
    """A matching key for a term: lower case, quotes and punctuation dropped, each word singular ("damages",
    "premises" and the like stay as they are).  It is for comparing terms within a run and may be improved at any
    time; nothing that makes a key calls it (see :func:`slug` and :func:`key_singular`)."""
    s = (s or "").replace("’", "'").lower()
    s = re.sub(r"'s\b", "", s)
    s = re.sub(r"[^a-z0-9\- ]+", " ", s)
    return " ".join(_singular(w) for w in s.split())


# ------------------------------------------------------------------ the key form, frozen at KEY_VERSION 1
KEY_VERSION = 1
# A frozen copy of _singular's tables as they stood at KEY_VERSION 1.  The extractor writes a heading term, a "may
# act as" term and a "defined as" term in the singular with key_singular, never with _singular, so a change to
# the matcher's singulariser (as when "Bonuses." stopped giving "bonuse") cannot move a key.  Editing these, or
# key_singular or slug, means a new KEY_VERSION, and every published item keeps its old key as a second P25 value.
_KEY_NO_SINGULAR = frozenset({
    "damages", "premises", "means", "series", "species", "news", "proceeds", "goods", "arrears", "earnings", "savings",
    "headquarters", "whereabouts", "remains", "thanks", "riches", "lees", "minutes"})
_KEY_IRREGULAR = (("gases", "gas"), ("statuses", "status"), ("buses", "bus"), ("censuses", "census"),
                  ("viruses", "virus"), ("bonuses", "bonus"), ("campuses", "campus"), ("surpluses", "surplus"),
                  ("prospectuses", "prospectus"), ("apparatuses", "apparatus"), ("consensuses", "consensus"),
                  ("nexuses", "nexus"), ("analyses", "analysis"), ("crises", "crisis"), ("theses", "thesis"),
                  ("diagnoses", "diagnosis"), ("prognoses", "prognosis"), ("hypotheses", "hypothesis"),
                  ("parentheses", "parenthesis"), ("syntheses", "synthesis"), ("children", "child"), ("men", "man"),
                  ("women", "woman"))
_KEY_IRREGULAR_MAP = dict(_KEY_IRREGULAR)


def key_singular(w: str) -> str:
    """The singular of one word, frozen at :data:`KEY_VERSION` 1 ('Incorporators' -> 'Incorporator', 'Bonuses' ->
    'Bonus', 'Damages' stays).  It is the only singulariser whose output reaches a key."""
    lw = w.lower()
    if lw in _KEY_NO_SINGULAR:
        return w
    if lw in _KEY_IRREGULAR_MAP:
        sg = _KEY_IRREGULAR_MAP[lw]
        return sg.upper() if w.isupper() else sg.capitalize() if w[:1].isupper() else sg
    if len(lw) <= 3 or lw.endswith(("ss", "us", "is", "ics")):
        return w
    if lw.endswith("ies") and len(lw) > 4:
        return w[:-3] + ("Y" if w[-1].isupper() else "y")
    if lw.endswith(("ches", "shes", "xes", "sses")):
        return w[:-2]
    if lw.endswith("s"):
        return w[:-1]
    return w


def slug(s: str) -> str:
    """The term part of a key, frozen at :data:`KEY_VERSION` 1: lower case, every run of characters other than
    a-z and 0-9 -> '-' (the same rule as ``lexflow.law.links``' definition keys).  No plural folding: a quoted
    term keys as written ("gases" stays "gases", "damages" never becomes "damage").  Neither this nor
    :func:`key_singular` calls :func:`norm_term` or ``_singular``, so changing the matcher's normalisation never
    moves a key.  A key still moves when the extractor captures other words for a term, or reads another
    sub-section pinpoint for it (:func:`term_key`)."""
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def _clean(term: str) -> str:
    return _ws(term).strip(" ,.;:")


def _also_parts(text: str, pos: int, endpos: int | None = None) -> tuple[list[str], int]:
    """The further parts of a compound scope that starts with a unit ending at ``pos``: (their words, where the
    last one ends).  ([], pos) when the scope is one unit."""
    endpos = len(text) if endpos is None else endpos
    parts: list[str] = []
    pending: list[str] = []          # comma parts not yet followed by "and"/"or"
    done = pos                       # where the last kept part ends
    while True:
        a = ALSO.match(text, pos, endpos)
        if a:
            parts += pending + [_ws(a.group("also"))]
            pending, pos = [], a.end()
            done = pos
            continue
        c = ALSO_COMMA.match(text, pos, endpos)
        if not c:
            return parts, done
        pending.append(_ws(c.group("also")))
        pos = c.end()
        if _AND_NEXT.match(text, pos, endpos):     # "..., chapter 3, and": the run so far is part of the scope
            parts += pending
            pending, done = [], pos


def _scope_words(text: str, m: re.Match, group: str = "u") -> tuple[str, int]:
    """A matched scope unit with the rest of a compound scope after it: (words, end)."""
    parts, end = _also_parts(text, m.end(group))
    return (_ws(text[m.start(group):end]) if parts else _ws(m.group(group))), end


_FIRST_UNIT = re.compile(rf"(?i:{_UNIT}|the\s+(?:[a-z]+\s+){{0,4}}?(?:code|act))")


def scope_parts(phrase: str | None) -> list[str]:
    """The units a scope phrase names: ['this section', 'ss. 605.1006 and 605.1062-605.1072'] for "this section and
    to ss. 605.1006 and 605.1062-605.1072"; a one-unit phrase gives itself."""
    p = _ws(phrase)
    m = _FIRST_UNIT.match(p)
    if not m:
        return [p] if p else []
    parts, end = _also_parts(p, m.end())
    if not parts or end != len(p):
        return [p]
    return [_ws(m.group(0))] + parts


_ENUM_TOK = re.compile(r"\(\s*([\w.\-]{1,6})\s*\)\s*|([A-Za-z]|\d{1,3})\.\s+")


def _enum_style(label: str, paren: bool) -> str:
    """The kind of an enumerator: '(1)', '(1a)' -> '(1)'; '(a)', '(a1)' -> '(a)'; '(i)', '(iv)' -> '(i)'; '(A)' ->
    '(A)'; '(II)' -> '(I)'; '1.' -> '1.'; 'a.' -> 'a.'; 'A.' -> 'A.'; anything else '?'."""
    if re.fullmatch(r"\d+[a-z]?\d*", label):
        kind = "1"
    elif re.fullmatch(r"[ivx]+", label):
        kind = "i"
    elif re.fullmatch(r"[a-z]{1,2}\d*", label):
        kind = "a"
    elif re.fullmatch(r"[IVX]{2,}", label):
        kind = "I"
    elif re.fullmatch(r"[A-Z]{1,2}\d*", label):
        kind = "A"
    else:
        return "?"
    return f"({kind})" if paren else f"{kind}."


class _Doc:
    """Clause starts, sentence ends and top-level sub-section labels of one section's text."""

    def __init__(self, text: str):
        self.text = text
        ends = []
        for m in re.finditer(r"\.(?=\s+(?:[A-Z“\"(]|\d+\.\s)|\s*$)", text):
            lo = max(0, m.start() - 80)                    # a window, not the whole prefix: linear in the text
            tok = re.search(r"([\w.]+)$", text[lo:m.start()])
            word = (tok.group(1) if tok else "").lower()
            if word in ABBREV:
                continue                                   # "s. 605.0902", "U.S.C. Section"
            if re.fullmatch(r"\d{1,3}|[a-z]", word):
                at = lo + tok.start()
                before = text[max(0, at - 80):at].rstrip() or text[:at].rstrip()
                if not before or before[-1] in "\n:;.§" or before.endswith("Sec"):
                    continue                               # an enumerator: "Sec. 2.", "meaning: 1. Criminal"
            ends.append(m.end())
        self.ends = ends
        raw = {0}
        raw.update(m.end() for m in re.finditer(r"\n\s*|[:;]\s+", text))
        space = re.compile(r"\s*")
        raw.update(space.match(text, e).end() for e in ends)
        self.raw = sorted(p for p in raw if p < len(text))
        enum = re.compile(r"(?:\(\s*[\w.\-]{1,6}\s*\)\s*|(?:[A-Z]|\d{1,3})\.\s+)*")
        ends_at = {p: enum.match(text, p).end() for p in self.raw}
        self.starts = sorted(set(ends_at.values()))
        self.enumerated = {e for p, e in ends_at.items() if e > p}      # clause starts that follow "(1) ", "A. "
        self.labels = self._top_labels()
        self.lines = [space.match(text).end()] + [m.end() for m in re.finditer(r"\n\s*", text) if m.end() < len(text)]
        self._styles: dict[int, list[str]] = {}
        self.leads = self._lead_ins()

    def clause_start(self, pos: int) -> int:
        """The start of the clause holding ``pos``, after its enumerators ("(3)(a) ", "A. ")."""
        i = bisect_right(self.starts, pos) - 1
        return self.starts[i] if i >= 0 else 0

    def raw_start(self, pos: int) -> int:
        i = bisect_right(self.raw, pos) - 1
        return self.raw[i] if i >= 0 else 0

    def sentence_end(self, pos: int) -> int:
        i = bisect_right(self.ends, pos)
        return self.ends[i] if i < len(self.ends) else len(self.text)

    def _top_labels(self) -> list[tuple[int, str]]:
        found = []
        for p in self.raw:
            m = re.match(r"\((\d+|[a-z]{1,2}(?:-\d+)?|[A-Z](?:-\d+)?)\)|(\d{1,3}|[A-Z])\.\s", self.text[p:p + 12])
            if not m:
                continue
            lab = m.group(1) or m.group(2)
            base = lab.split("-")[0]
            style = ("p" if m.group(1) else "d") + ("n" if base.isdigit() else "u" if base.isupper() else "l")
            found.append((p, lab, base, style))
        if not found:
            return []
        style, out, cur = found[0][3], [], None

        def nxt(b: str, k: int) -> str:
            return str(int(b) + k) if b.isdigit() else chr(ord(b) + k) if len(b) == 1 else ""

        for p, lab, base, st in found:
            if st != style:
                continue
            first = cur is None and base in ("1", "a", "A")
            same = cur is not None and "-" in lab and base == cur
            follows = cur is not None and base in (nxt(cur, 1), nxt(cur, 2))
            if first or same or follows:
                out.append((p, f"({lab})" if style[0] == "p" else lab))
                cur = base if not same else cur
        return out

    def label_at(self, pos: int) -> str | None:
        i = bisect_right([p for p, _ in self.labels], pos) - 1
        return self.labels[i][1] if i >= 0 else None

    def _lead_ins(self) -> list[tuple[int, str, int, int]]:
        """'As used in this chapter, the term:' -> (where it takes effect, unit phrase, its own position, where the
        list it opens ends); also a sentence that declares where the definitions apply ('the definitions in this
        section apply throughout this chapter.'), which takes effect where it ends.  A lead-in may end in a dash
        instead of a colon ('For purposes of this part —', D.C. Code § 1-204.24f), and its unit may be compound
        ('this section and to ss. 605.1006 and ...')."""
        out = []
        for s in sorted(set(self.starts) | {self.after_caption(e) for e in self.enumerated}):
            m = SCOPE_LEAD.match(self.text, s)
            if not m:
                continue
            unit, after = _scope_words(self.text, m)
            stop = self.sentence_end(after)
            rest = self.text[after:min(stop, after + 500)]
            dash = re.match(r"\s*,?\s*(?:—|–|--?)\s*(?=\n|\(|$)", rest)
            if dash:
                out.append((after + dash.end(), unit, m.start(), self._list_end(m.start())))
                continue
            colon = rest.find(":")
            # "..., the following terms shall have the following meanings:" and "..., the following terms mean:"
            # are still lead-ins; '"X" means:' is not
            head = re.sub(r"(?i)(?:shall\s+have|has|have)\s+the\s+following\s+meanings?|"
                          r"following\s+(?:terms|words|phrases)\s+(?:shall\s+)?(?:mean|have\s+the\s+meanings?)", "",
                          rest[:colon])
            if colon >= 0 and not re.search(r'[“"]', rest[:colon]) and not re.search(_VERB, head):
                out.append((after + colon, unit, m.start(), self._list_end(m.start())))
        for m in DECLARE.finditer(self.text):
            if m.group("u") or m.group("v"):
                unit, after = _scope_words(self.text, m, "u" if m.group("u") else "v")
            else:
                unit, after = _ws(m.group("n") or m.group("w")), m.end()
            out.append((max(after, m.end()), unit, m.start(), self._list_end(m.start())))
        return sorted(out)

    def after_caption(self, pos: int) -> int:
        """Past a North Carolina caption at ``pos`` ("Definitions. - " in "(a) Definitions. - For the purpose of this
        Article:", N.C. Gen. Stat. § 87-21), so a lead-in after it is found; else ``pos``."""
        m = DASH_DEF.match(self.text, pos)
        return m.end() if m else pos

    def lead_at(self, pos: int) -> str | None:
        """The unit of the last lead-in before ``pos``.  For a quoted definition's scope a lead-in never ends:
        Maryland's "(a) In this subtitle the following words have the meanings indicated." governs its siblings
        (b), (c), ...  A dash item asks :meth:`list_lead_at` instead."""
        best = None
        for at, unit, _, _ in self.leads:
            if at <= pos:
                best = unit
        return best

    def list_lead_at(self, pos: int) -> str | None:
        """The unit of the lead-in whose list holds ``pos``, else None.  A lead-in's list ends at the next line that
        starts with an enumerator of the lead-in's own line's kind: "(a) ... For purposes of this section: (i) ..."
        ends at "(b) Punishment. - ..." (N.C. Gen. Stat. § 14-150.3), so that caption is no definition."""
        best = None
        for at, unit, _, end in self.leads:
            if at <= pos < end:
                best = unit
        return best

    def line_start(self, pos: int) -> int:
        i = bisect_right(self.lines, pos) - 1
        return self.lines[i] if i >= 0 else 0

    def _line_labels(self, ls: int) -> list[tuple[str, bool]]:
        """The enumerators that open the line at ``ls``, each (label, in parentheses): "(a)(1) " -> [('a', True),
        ('1', True)]."""
        if ls not in self._styles:
            out, p = [], ls
            while True:
                m = _ENUM_TOK.match(self.text, p)
                if not m:
                    break
                out.append((m.group(1) or m.group(2), bool(m.group(1))))
                p = m.end()
            self._styles[ls] = out
        return self._styles[ls]

    def _line_styles(self, ls: int) -> list[str]:
        """The kinds of the enumerators that open the line at ``ls``: "(a)(1) " -> ['(a)', '(1)']."""
        return [_enum_style(lab, paren) for lab, paren in self._line_labels(ls)]

    def _letter_not_roman(self, lab: str, paren: bool, own: list[tuple[str, bool]], rest: list[int]) -> bool:
        """Whether "(i)", "(v)" or "(x)" opening a later line is the letter, not a roman numeral: it is when the
        lead-in's own line has the letter before it ("(h) ... As used in this section:" then "(i) Rights of ...",
        N.C. Gen. Stat. § 58-68-60), unless "(ii)" ("(vi)", "(xi)") opens a line before "(j)" ("(w)", "(y)") does.
        With neither after it, it is read as the letter, which ends the list: the conservative reading."""
        if len(lab) != 1 or lab not in "ivx" or (chr(ord(lab) - 1), paren) not in own:
            return False
        roman_next, letter_next = {"i": "ii", "v": "vi", "x": "xi"}[lab], chr(ord(lab) + 1)
        for ls in rest:
            labs = self._line_labels(ls)
            if labs and labs[0][1] == paren and labs[0][0] in (roman_next, letter_next):
                return labs[0][0] == letter_next
        return True

    def _list_end(self, pos: int) -> int:
        """Where the list opened by a lead-in at ``pos`` ends: the next line whose first enumerator is of a kind that
        opens the lead-in's own line.  A lead-in on a line with no enumerator lists to the end of the text.  A
        lower-case "(i)", "(v)" or "(x)" is read as a letter or a roman numeral by :meth:`_letter_not_roman`."""
        i = bisect_right(self.lines, pos) - 1
        own_labels = self._line_labels(self.lines[i]) if i >= 0 else []
        own = {_enum_style(lab, paren) for lab, paren in own_labels} - {"?"}
        if not own:
            return len(self.text)
        later = self.lines[i + 1:]
        for k, ls in enumerate(later):
            labs = self._line_labels(ls)
            if not labs:
                continue
            st = _enum_style(*labs[0])
            if st in ("(i)", "i.") and self._letter_not_roman(labs[0][0], labs[0][1], own_labels, later[k + 1:]):
                st = "(a)" if labs[0][1] else "a."
            if st in own:
                return ls
        return len(self.text)


# ------------------------------------------------------------------ headings and scopes
def heading(row: dict, text: str = "") -> str:
    """The section's own heading without its number: '605.0113 Registered agent.' -> 'Registered agent.'.  The
    index synthesizes a heading from the first sentence where the file has none; that is not used."""
    t = _ws(row.get("original_title") or "")
    if not t:
        title = _ws(row.get("title") or "")
        synthetic = re.match(r"^[^:]{2,80}:\s", title) and not re.match(r"^RCW\s", title)
        t = "" if synthetic else title
    t = EFFECTIVE.sub("", t)
    t = re.sub(r"^(?:RCW\s+|G\.\s?S\.\s+|§+\s*)?\d[\w.\-–:]*\s*[:.]?\s+", "", t)
    if re.fullmatch(r"(?:Section|Sec\.|§+)\s*\d[\w.\-–:]*\.?", t or ""):
        t = ""
    if not t and text:
        m = re.match(r"\s*(?:\([^)]{1,60}\)\s*)*(?:Sec\.|§+)\s*[\w.\-–:]+\.\s+([^.(\n]{2,150}?)\.(?:\s|$)", text)
        if m and not re.search(r"\b(?:shall|may|must|is|are)\b", m.group(1)):
            t = m.group(1) + "."
    return t.strip()


def _heading_terms(head: str) -> list[str]:
    """Segments of a heading that are themselves a term: 'Incorporators.' -> ['incorporator'];
    'Hearings; final decision.' -> ['final decision'] (a lone word only when it is the whole heading)."""
    segs = [s.strip(" .") for s in re.split(r"\s*(?:;|—|--|–)\s*", head) if s.strip(" .")]
    out = []
    for seg in segs:
        words = seg.split()
        if not 1 <= len(words) <= 5 or re.search(r"[\d§,()“”\"/]", seg):
            continue
        if len(words) == 1 and len(segs) > 1:
            continue
        low = [w.lower() for w in words]
        if any(w in _HEAD_STOP or w in _STRUCTURAL or w.startswith("definition") for w in low):
            continue                                   # "Definition and purposes." names no term
        if _generic_heading(norm_term(seg)):
            continue                                   # "Definitions.", "Fees of the department."
        out.append(_heading_case(seg))
    return out


def _generic_heading(n: str) -> bool:
    """A normalised heading segment that names no term: a generic one ("definition", "fee of the department"), one
    whose every "and" part is generic ("fee and penalty"), or one that opens with a generic phrase of two or more
    words ("statement of purpose and authorization", N.C. Gen. Stat. § 106-1041)."""
    def generic(p: str) -> bool:
        return p in GENERIC_HEADINGS or (" of " in p and p.split(" of ")[0] in GENERIC_HEADINGS)

    parts = [p for p in re.split(r"\s+and\s+", n) if p]
    return generic(n) or (len(parts) > 1 and (all(generic(p) for p in parts) or
                                              (" " in parts[0] and generic(parts[0]))))


def _heading_case(seg: str) -> str:
    words = seg.split()
    if seg.isupper() or (words[0][:1].isupper() and all(w.islower() or w in ("of", "and") for w in words[1:])):
        words = [w.lower() for w in words]
    elif words[0][:1].isupper() and len(words) > 1 and words[1][:1].islower():
        words[0] = words[0].lower()
    phrase = " ".join(words)
    if " of " in phrase:
        left, right = phrase.split(" of ", 1)
        lw = left.split()
        if lw[-1].lower() != "articles":
            lw[-1] = key_singular(lw[-1])
        return " ".join(lw) + " of " + right
    words[-1] = key_singular(words[-1])
    return " ".join(words)


def scope_path(row: dict, phrase: str | None) -> tuple[str | None, str | None]:
    """A scope as the text words it -> (index path of the unit, pinpoint).  'this chapter' -> the chapter's path;
    'this subsection (g)' -> (the section's path, '(g)'); None when the index path has no such level."""
    path = row.get("path") or ""
    parts = path.split(" / ")
    containers = parts[:-1]
    p = re.sub(r"\s+", " ", (phrase or "this section").lower().strip())
    if re.search(r"\(=\s*this section\)", p):
        p = "this section"                           # gold A writes "this article (= this section)"
    p = re.sub(r"\s*\((?:=|ch\.|art\.)[^)]*\)\s*$", "", p)
    m = re.fullmatch(r"(?:this )?(?:subsection|subdivision|paragraph)(?: \(\s*([\w.\-]+)\s*\))?", p)
    if m:
        return path, (f"({m.group(1)})" if m.group(1) else None)
    if p in ("this section", "section", "herein", "this definition"):
        return path, None
    m = re.fullmatch(r"section ([\w.\-]+) of this (act|chapter|article|title|code)", p)
    if m:
        unit, _ = scope_path(row, f"this {m.group(2)}")
        return (f"{unit} / Section {m.group(1)}" if unit else None), None
    m = re.fullmatch(r"this (\w+)", p)
    if not m:
        return None, None
    level = m.group(1)

    def find(word: str):
        hits = [i for i, c in enumerate(containers) if c.split(" ")[0].lower() == word]
        return hits[-1] if hits else None

    i = find(level)
    if i is None and level == "chapter":
        i = find("act")                            # New York's consolidated laws are chapters ("Act LLC")
    if i is None and level == "article" and "code of criminal procedure" in (row.get("citation") or "").lower():
        return path, None                          # Texas CCP is numbered in articles: "this article" = the section
    if level == "code":
        codes = [k for k, c in enumerate(containers) if c.split(" ")[0].lower() == "code"]
        i = codes[-1] if codes else (0 if containers else None)
    if i is None:
        return None, None
    return " / ".join(parts[:i + 1]), None


# Units whose extent no index path expresses, taken from their own short-title sections.  Each entry: the names a
# scope phrase may use, a pattern the defining section's path must match (so the name is read only inside that
# unit), the unit's path-like name, and the section that says so.
NAMED_UNITS: dict[str, list[dict]] = {
    "md": [{"names": {"maryland uniform commercial code"},
            "within": r"^MD Code / Article gcl / Title (?:[1-9]|10) /",
            "unit": "MD Code / Article gcl / Titles 1-10", "name": "Maryland Uniform Commercial Code",
            "source": "Md. Code, Commercial Law § 1-101(a)"}],
    "fl": [{"names": {"uniform commercial code", "this code", "code"},
            "within": r"^Florida Code / Title XXXIX / Chapter (?:669|67\d|680) /",
            "unit": "Florida Code / Title XXXIX / Chapters 669-680", "name": "Uniform Commercial Code",
            "source": "Fla. Stat. § 671.101(1)"}],
    "va": [{"names": {"uniform commercial code"},
            "within": r"^Virginia Code / Title 8\.[1-9]A? /",
            "unit": "Virginia Code / Titles 8.1A-8.9A", "name": "Uniform Commercial Code",
            "source": "Va. Code Ann. § 8.1A-101(a)"}],
    "il": [{"names": {"uniform commercial code"},
            "within": r"^Illinois Code / Chapter 810 / Act 5 /",
            "unit": "Illinois Code / Chapter 810 / Act 5", "name": "Uniform Commercial Code",
            "source": "810 ILCS 5/1-101(a)"}],
}
# A level missing from the index path lies inside the deepest of these levels the path has (else the code itself).
# Maryland's "Article" is a whole code, so a Maryland part lies in its subtitle (Md. Gen. Prov. § 5-857: Title 5 /
# Subtitle 8); an Illinois article or part lies in its Act (105 ILCS 5/34-1.1: Chapter 105 / Act 5); a Texas title
# or subtitle lies in its code.  An act is no level of these paths, and its extent is unknown (it may be the whole
# chapter, as Va. Code ch. 66 is, or less, or more): it is anchored under the section's own enclosing unit (None).
_INSIDE: dict[str, tuple[str, ...] | None] = {
    "subchapter": ("chapter",), "article": ("act", "chapter", "title"),
    "part": ("article", "subtitle", "subchapter", "chapter", "act"),
    "subpart": ("part", "article", "subtitle", "subchapter", "chapter", "act"), "subtitle": ("title", "code"),
    "title": ("code", "act"), "division": ("code",), "act": None}


def named_unit(state: str, row: dict, phrase: str | None) -> dict | None:
    """The :data:`NAMED_UNITS` entry a scope phrase names from inside that unit ('the Maryland Uniform Commercial
    Code' in Md. Code, Com. Law § 1-201), else None."""
    p = re.sub(r"^the\s+", "", _ws(phrase).lower())
    for e in NAMED_UNITS.get((state or "").lower(), []):
        if p in e["names"] and re.search(e["within"], row.get("path") or ""):
            return e
    return None


def _section_label(row: dict) -> str:
    num = row.get("section_number") or (row.get("path") or "").split(" / ")[-1]
    num = re.sub(r"^(?:Section|Sec\.|§+)\s*", "", _ws(num))
    return f"§ {num}"


def resolve_scope(state: str, row: dict, phrase: str | None) -> tuple[str | None, str | None, str | None]:
    """A scope phrase -> (unit, pinpoint, basis).  ``basis`` says how the unit was found:

        path      the index path has the unit ("this chapter" -> its chapter; "this subsection (g)" -> the section)
        named     a unit the path cannot express, from :data:`NAMED_UNITS` (the Maryland UCC is Titles 1-10 of the
                  Commercial Law article)
        anchored  the path lacks the level ("this subchapter" in D.C. and Texas, "this Article" and "this Part" in
                  North Carolina and Illinois, "this part" in Maryland, "this act"): the unit is named as the one
                  that holds the section, under the deepest unit of the path that can contain it (:data:`_INSIDE`),
                  'DC Code / Title 2 / Chapter 15 / Subchapter containing § 2-1561', 'MD Code / Article ggp /
                  Title 5 / Subtitle 8 / Part containing § 5-857'.  That names the right unit, but not its extent,
                  and another section of the same subchapter gets another anchor: review these
        compound  the scope is several units ("this section and to ss. 605.1006 and 605.1062-605.1072"); no one
                  unit expresses it, so ``unit`` is None and :func:`scope_parts` lists the parts (a Term carries
                  them, each with its own unit, in ``scope_parts``): review these
        None      nothing expresses the scope (a list of sections: 'sections 13-101, 13-103 and 13-107')
    """
    if len(scope_parts(phrase)) > 1:
        return None, None, "compound"
    named = named_unit(state, row, phrase)
    if named:
        return named["unit"], None, "named"
    unit, pin = scope_path(row, phrase)
    if unit is not None:
        return unit, pin, "path"
    m = re.fullmatch(r"this (\w+)", re.sub(r"\s+", " ", (phrase or "").lower().strip()))
    if not m or m.group(1) not in _INSIDE:
        return None, None, None
    level = m.group(1)
    parts = (row.get("path") or "").split(" / ")
    containers = parts[:-1]
    within = _INSIDE[level]
    if within is None:                                 # an act: under the section's own enclosing unit
        hits = [len(containers) - 1] if containers else []
    else:
        hits = [k for k, c in enumerate(containers) if c.split(" ")[0].lower() in within]
    base = " / ".join(parts[:hits[-1] + 1]) if hits else parts[0]
    return f"{base} / {level.capitalize()} containing {_section_label(row)}", None, "anchored"


def _category(term: str, definition: str | None = None) -> str:
    n = norm_term(term)
    if not n:
        return "other"
    head = n.split(" of ")[0].split()[-1]
    if head in _DOC_HEADS:
        return "document"
    if head in _ROLE_HEADS or (len(head) > 4 and head.endswith(("er", "or", "ant", "ent", "ee", "ist")) and
                               not head.endswith("ment") and not head.startswith(("here", "there")) and
                               head not in _NOT_AGENT):
        return "role"
    if definition and re.search(r"\b(?:person|individual|officer|entity|body)\s+(?:who|that|whose|designated)\b",
                                definition[:200], re.I):
        return "role"
    return "other"


def _np_before(text: str, end: int) -> tuple[str, int]:
    """The noun phrase that ends at ``end``: 'a severe form of trafficking in persons' -> that phrase without 'a'."""
    toks = list(re.finditer(r"[A-Za-z][\w'’\-]*|[^\w\s]", text[max(0, end - 160):end]))
    off = max(0, end - 160)
    words: list[re.Match] = []
    i = len(toks) - 1
    while i >= 0 and len(words) < 7:
        w = toks[i].group(0)
        lw = w.lower()
        prev = toks[i - 1].group(0).lower() if i > 0 else ""
        if lw in ("the", "this") and prev == "of" and [x.group(0).lower() for x in words] == ["state"]:
            words = toks[i - 1:i + 1] + words           # "public retirement system of the state"
            i -= 2
            continue
        if not re.match(r"[A-Za-z]", w) or lw in _DET or lw in _VERBISH:
            break
        if lw in _PREP:
            if lw in ("of", "in") and prev in _RELATIONAL and len(words) <= 3:
                words.insert(0, toks[i])
                i -= 1
                continue
            break
        words.insert(0, toks[i])
        i -= 1
    while words and words[0].group(0).lower() in ("the", "this", "of", "in"):
        words.pop(0)
    while len(words) > 1 and words[0].group(0).lower().endswith("ing") and \
            words[0].group(0).lower() not in _RELATIONAL:
        words.pop(0)                                   # "providing attestation services" -> the services
    if not words:
        return "", end
    start = off + words[0].start()
    return _ws(text[start:end]), start


# ------------------------------------------------------------------ definitions
def definitions(state: str, row: dict, text: str | None = None) -> list[Term]:
    """Every term one section defines or names (see the module docstring for the forms)."""
    if text is None:
        text = row.get("text")
    if text is None:
        from ..ask import index as I
        text = I.text_of(state, row["id"]) if row.get("id") is not None else ""
    text = text or ""
    doc = _Doc(text)
    head = heading(row, text)
    defs_heading = bool(DEFINITIONS_HEADING.match(head or ""))
    found: list[dict] = []

    def scope_for(cs: int, term_pos: int, gap: str = "", start: int | None = None) -> str | None:
        inner = SCOPE_INNER.search(gap or "")
        if inner:
            return _scope_words(gap, inner)[0]
        m = SCOPE_LEAD.match(text, cs) or SCOPE_LEAD.match(text, doc.after_caption(cs))
        if m and m.end() <= term_pos + 1:
            words, end = _scope_words(text, m)
            return words if end <= term_pos + 1 else m.group("u")
        if start is not None:                          # "As used in sections 13-101,\n13-103 ..., the term"
            lo = max(0, start - 250)
            b = SCOPE_BEFORE.search(text, lo, start)
            if b and not re.search(r"\.\s+[A-Z]", text[b.start():start]):
                return _ws(b.group("u"))
        return None

    def add(term: str, kind: str, term_pos: int, start: int, anchor: int, local: str | None = None,
            defined_in: str | None = None, end: int | None = None, alternatives: list[str] | None = None):
        """``start`` opens the definition span, ``anchor`` is where its sentence-end search begins, ``local`` is
        a scope phrase from the definition's own clause."""
        term = _clean(term)
        if not term or len(term) > 120 or not re.search(r"[A-Za-z]", term):
            return
        found.append({"term": term, "kind": kind, "term_pos": term_pos, "start": start, "anchor": anchor,
                      "local": local, "defined_in": defined_in, "end": end, "alternatives": alternatives or []})

    def listed(lst: str, at: int) -> list[tuple[str, int]]:
        """The quoted terms of a list, one per normalised form ("Public record" or "public records": one)."""
        out, forms = [], set()
        for q in re.finditer(_QT, lst):
            if norm_term(q.group(0)) not in forms:
                forms.add(norm_term(q.group(0)))
                out.append((_clean(q.group(0)[1:-1]), at + q.start()))
        return out

    def synonyms(lst: str, terms: list[tuple[str, int]]) -> dict[str, list[str]]:
        """'"Local government" or "locality" means': each term's alternatives.  An 'and' list is several terms
        that share a definition, not synonyms."""
        seps = re.sub(_QT, "\0", lst).split("\0")[1:-1]
        if len(terms) < 2 or not seps or not all(re.fullmatch(r"\s*(?:[,;]\s*)?(?:(?:or|,)\s*)?", s) for s in seps) \
                or not any(re.search(r"\bor\b", s) for s in seps):
            return {}
        return {t: [u for u, _ in terms if u != t] for t, _ in terms}

    # "X" means / "X" and "Y" shall not include / "X", for purposes of ..., means
    for m in DEF_A.finditer(text):
        gap = m.group("gap")
        if re.search(r"\.\s+[A-Z]", gap):
            continue
        if m.start() > 0 and text[m.start() - 1] not in " \n\t([—–-":
            continue
        cs = doc.clause_start(m.start())
        kind = _verb_kind(m.group("verb"))
        items = listed(m.group("list"), m.start("list"))
        alts = synonyms(m.group("list"), items)
        for t, pos in items:
            add(t, kind, pos, m.start(), m.end(), scope_for(cs, pos, gap, m.start()),
                _where(text, m.end()) if kind == "by_reference" else None, alternatives=alts.get(t))
    # The words "this Chapter," "hereof," ... are to be read ...
    for m in DEF_WORDS.finditer(text):
        cs = doc.clause_start(m.start())
        kind = _verb_kind(m.group("verb"))
        items = listed(m.group("list"), m.start("list"))
        alts = synonyms(m.group("list"), items)
        for t, pos in items:            # 'The term "infant" or "minor", as used in this chapter, shall mean'
            add(t, kind, pos, m.start(), m.end(), scope_for(cs, pos, m.group("rest"), m.start()),
                alternatives=alts.get(t))
    # One or more persons may act as the incorporator or incorporators of a corporation ...
    for m in ACTS_AS.finditer(text):
        t = m.group("t")
        words = t.split()
        if words and words[-1] in _PREP:
            continue
        words[-1] = key_singular(words[-1])
        cs = doc.clause_start(m.start())
        add(" ".join(words), "acts_as", m.start("t"), cs, m.end(), "this chapter")
    # The articles of merger shall state the following:
    for m in CONTENTS.finditer(text):
        cs = doc.clause_start(m.start())
        add(m.group("t"), "contents", m.start("t"), m.start(), m.end(), scope_for(cs, m.start("t")))
    # There is established the Commission on ...
    for m in ESTABLISHES.finditer(text):
        t = re.sub(r"(?:\s+(?:of|and|on|for|the|in))+$", "", m.group("t"))
        if len(t.split()) < 2:
            continue
        cs = doc.clause_start(m.start())
        add(t, "establishes", m.start("t"), m.start(), m.end(), scope_for(cs, m.start("t")))
    # University of the District of Columbia ("University")
    for m in PAREN.finditer(text):
        cs = doc.clause_start(m.start())
        name = re.search(r"(?:[A-Z][\w'’\-]*\s+(?:(?:of|and|for|on|the)\s+)*)*[A-Z][\w'’\-]*\s*$",
                         text[cs:m.start()])
        if name:
            start = cs + name.start()                  # University of the District of Columbia ("University")
        else:
            lo = max(cs, m.start() - 160)
            seg = text[lo:m.start()]
            cut = max(seg.rfind(","), seg.rfind(";"), seg.rfind(":"))
            start = lo + (cut + 1 if cut >= 0 else 0)
            start += len(text[start:m.start()]) - len(text[start:m.start()].lstrip())
        add(m.group("t"), "parenthetical", m.start("t") - 1, start, m.end(), scope_for(cs, start), end=m.end())
    # X, as defined in § N  /  individuals defined as police officers in section 1.20
    for m in BY_REF.finditer(text):
        if re.search(r'[”"]\s*$', text[:m.start()]) or re.match(r"\s*this\s", text[m.end():m.end() + 6]):
            continue                                   # a quoted term (handled above), or "as defined in this
            #                                            section/chapter": the meaning is here or in the unit's
            #                                            own definitions, not a citation
        np_, start = _np_before(text, m.start())
        last = norm_term(np_).split()[-1:]
        if not last or last[0] in _STRUCTURAL:
            continue
        # '"Woodland" means woodland as defined in G.S. 105-277.2': one by-reference definition of the quoted term,
        # not a "means" Term and a second, by-reference one on the same key
        same = [f for f in found if f["kind"] == "means" and f["anchor"] <= start and
                not text[f["anchor"]:start].strip() and norm_term(f["term"]) == norm_term(np_)]
        if same:
            for f in same:
                f["kind"], f["defined_in"] = "by_reference", _where(text, m.start())
            continue
        cs = doc.clause_start(start)
        add(np_, "by_reference", start, start, m.end(), scope_for(cs, start), _where(text, m.start()))
    for m in DEFINED_AS.finditer(text):
        t = m.group("t").split()
        t[-1] = key_singular(t[-1])
        cs = doc.clause_start(m.start())
        add(" ".join(t), "by_reference", m.start("t"), m.start(), m.end(), scope_for(cs, m.start()),
            _where(text, m.start()))
    # Agency of North Carolina government or its subdivisions shall mean and include ...
    for m in UNQUOTED.finditer(text):
        if re.search(r'[”",]\s*$', text[max(0, m.start() - 3):m.start()]):
            continue
        cs = doc.clause_start(m.start())
        cand = text[cs:m.start()].strip()
        words = cand.split()
        if not 1 <= len(words) <= 8 or not cand[:1].isupper() or re.search(r'[“”",;:()\d§]', cand):
            continue
        low = [w.lower() for w in words]
        if low[0] in _DET or any(w in _VERBISH for w in low) or low[-1] in _PREP or low[0] in _STRUCTURAL:
            continue
        add(cand, "means", cs, cs, m.end(), scope_for(cs, cs))
    # (1) Owner. - The holder of the title in fee simple ...: a North Carolina list item, read as a definition only
    # inside the list a lead-in opens, or, before any lead-in, in a section whose heading is about definitions alone
    # ("Definitions.", "Definitions relating to resources.", not "Definitions; description of boundaries." or
    # "Definition of service districts.").  N.C. captions ordinary subsections the same way ("(b) Punishment. - A
    # person who violates ..."), and a lead-in's list ends at the next enumerator of the lead-in's own kind
    # (_Doc.list_lead_at).  A lead-in inside a definition item ("(1) Reasonable accommodations. - ... As used in this
    # subdivision, the following terms apply: a. ...") opens a list of its own, but does not end the heading's: the
    # items after it are still read.
    list_heading = defs_heading and not re.search(r"[;—]|--", head) and \
        not re.match(r"(?i)\s*definition\s+of\b", head)
    item_at: dict[int, int] = {}               # line -> where the first definition item on it starts
    for f in found:
        cs = doc.clause_start(f["term_pos"])
        if cs in doc.enumerated and 0 <= f["term_pos"] - cs <= 12:       # '(2) "Agency" means', '(3) The term "X"'
            ln = doc.line_start(cs)
            item_at[ln] = min(item_at.get(ln, cs), cs)

    def inner(own: int) -> bool:
        """A lead-in at ``own`` sits inside a definition item that opens its line."""
        return item_at.get(doc.line_start(own), own) < own

    owns = sorted(own for _, _, own, _ in doc.leads)
    nxt, outer_before = 0, False               # whether a lead-in outside every item starts before the item
    for s in sorted(doc.enumerated):
        while nxt < len(owns) and owns[nxt] <= s:     # every item before owns[nxt] is read by now
            outer_before = outer_before or not inner(owns[nxt])
            nxt += 1
        m = DASH_DEF.match(text, s)
        if not m or _DASH_NOT.match(text, m.end()):
            continue
        quoted = re.match(rf'(?:[Tt]he\s+(?:terms?|words?|phrases?)\s+)?(?P<q>{_QT})', text[m.end():m.end() + 140])
        if quoted and norm_term(quoted.group("q")) == norm_term(m.group("t")):
            # '(3) Mayor. — The term “Mayor” means': the quoted definition is the Term.  Only when one was found
            # there: '(1) Adjustment. - "Adjustment" is an act ...' (N.C. Gen. Stat. § 81A-9) and '(15a) Sell. - The
            # terms "sell," ... are synonymous' (§ 20-286) have no definition verb, so the item is the only Term
            qpos = m.end() + quoted.start("q")
            if any(f["term_pos"] == qpos and norm_term(f["term"]) == norm_term(m.group("t")) for f in found):
                continue
        in_list = doc.list_lead_at(s)
        if in_list is None and not (list_heading and not outer_before):
            continue
        t = m.group("t")
        low = [w.lower() for w in t.split()]
        n = norm_term(t)
        if low[0] in _DET or low[0] in _VERBISH or any(w in _DASH_VERBS for w in low) or low[-1] in _PREP or \
                n in _DASH_CAPTIONS or n.split()[0] in _STRUCTURAL or "definition" in n:
            continue
        ref = re.match(r"(?i)as\s+defined\s+(?:in|by|under)|has\s+the\s+(?:same\s+)?meaning", text[m.end():])
        # outside every list, under the heading: the heading's scope, not an earlier item's inner "this subdivision"
        add(t, "by_reference" if ref else "means", s, s, m.end(), scope_for(s, s) or in_list or "__parent__",
            _where(text, m.end()) if ref else None)          # "(2) Confidential information. - As defined in ..."
        ln = doc.line_start(s)
        item_at[ln] = min(item_at.get(ln, s), s)
    # Private information also includes ... (a term already defined above, now unquoted)
    known = {f["term"] for f in found if f["kind"] in ("means", "includes", "excludes")}
    for t in sorted(known, key=len, reverse=True):
        pat = re.compile(rf"\b{re.escape(t)}\s+(?:also\s+)?(?:includes|(?:does|shall)\s+not\s+include|"
                         rf"(?:may|shall)\s+include)\b", re.I)
        for m in pat.finditer(text):
            cs = doc.clause_start(m.start())
            if cs != m.start():
                continue
            if any(f["term_pos"] in (m.start(), m.start() - 1) for f in found):
                continue
            kind = "excludes" if " not " in m.group(0).lower() else "includes"
            add(text[m.start():m.start() + len(t)], kind, m.start(), m.start(), m.end(), scope_for(cs, m.start()))

    # spans, scopes, dedupe
    found.sort(key=lambda f: (f["start"], f["term_pos"]))
    anchors = sorted({doc.raw_start(f["start"]) for f in found})
    terms: list[Term] = []
    seen: set[tuple[str, int]] = set()
    last_scope: dict[str, tuple] = {}
    for f in found:
        key = (norm_term(f["term"]), f["term_pos"])
        if key in seen:
            continue
        seen.add(key)
        end = f["end"]
        if end is None:
            end = doc.sentence_end(f["anchor"] - 1)
            later = [a for a in anchors if a > f["start"] + 1]
            if later and later[0] < end:
                end = later[0]
        span = text[f["start"]:end].rstrip()
        end = f["start"] + len(span)
        phrase = f["local"]
        if phrase and phrase.lower().strip() == "this definition":
            phrase = (last_scope.get(norm_term(f["term"])) or last_scope.get("") or (None,))[0]
        if phrase is None:
            phrase = doc.lead_at(f["term_pos"])
        fallback = None
        if phrase is None:
            phrase, fallback = ("__parent__", "heading") if defs_heading else ("this section", "default")
        unit, pin, basis = _unit_for(state, row, doc, phrase, f["term_pos"])
        if phrase == "__parent__":
            parts = (row.get("path") or "").split(" / ")[:-1]
            phrase = f"this {parts[-1].split(' ')[0].lower()}" if parts else None
        t = Term(term=f["term"], definition_span=span, scope_unit=unit, kind=f["kind"], start=f["start"], end=end,
                 scope=_ws(phrase) if phrase else None, scope_pinpoint=pin, term_start=f["term_pos"], source="text",
                 category=_category(f["term"], span), defined_in=f["defined_in"], scope_basis=fallback or basis,
                 alternatives=[a for a in f["alternatives"] if norm_term(a) != norm_term(f["term"])],
                 scope_parts=_parts(state, row, phrase) if basis == "compound" else [])
        last_scope[norm_term(f["term"])] = last_scope[""] = (phrase,)
        terms.append(t)

    # role and document headings
    low_text = _ws(text).lower()
    for ht in _heading_terms(head or ""):
        n = norm_term(ht)
        same = [t for t in terms if norm_term(t.term) == n]
        if same:
            for t in same:
                t.source = "heading+text"
            continue
        variants = {ht.lower(), ht.lower() + "s", re.sub(r"y$", "ies", ht.lower()), head.lower().strip(" .")}
        if not any(v in low_text for v in variants):
            continue                                   # a heading term the section never mentions is no term
        mention = _find_mention(text, ht)
        # a heading term governs its own section, unless the text defines it as a list item under a lead-in
        # ('As used in this part: (1) Group health insurance is that form of ...', Fla. Stat. § 627.652)
        phrase = doc.lead_at(mention) if mention is not None and doc.clause_start(mention) == mention else None
        unit, pin, basis = _unit_for(state, row, doc, phrase or "this section", mention or 0)
        terms.insert(0, Term(term=ht, definition_span=head, scope_unit=unit, kind="heading", start=None, end=None,
                             scope=_ws(phrase) if phrase else "this section", scope_pinpoint=pin, term_start=mention,
                             source="heading", category=_category(ht), scope_basis=basis if phrase else "default",
                             scope_parts=_parts(state, row, phrase) if phrase and basis == "compound" else []))
    return terms


def _parts(state: str, row: dict, phrase: str) -> list[tuple[str, str | None]]:
    return [(p, resolve_scope(state, row, p)[0]) for p in scope_parts(phrase)]


def _unit_for(state: str, row: dict, doc: _Doc, phrase: str, term_pos: int) -> tuple[str | None, str | None,
                                                                                       str | None]:
    if phrase == "__parent__":
        # a definitions section with no scope words governs the unit it sits in ('"Public records" defined.')
        parts = (row.get("path") or "").split(" / ")[:-1]
        return (" / ".join(parts) or None), None, "heading"
    unit, pin, basis = resolve_scope(state, row, phrase or "this section")
    if re.match(r"(?i)(?:this\s+)?(?:subsection|subdivision|paragraph)\b", phrase or "") and pin is None and \
            unit is not None:
        pin = doc.label_at(term_pos)
    return unit, pin, basis


def group_by_key(state: str, ref: str, terms: list[Term]) -> dict[str, list[Term]]:
    """Terms by their :func:`term_key`, in text order.  One key can hold several definitions: Md. Code, Com. Law
    § 1-201 says what a "Security interest" means, includes and does not include.  ``Loader.entity()`` replaces an
    item's statements wholesale, so a loader must write each key once, with one *defined in* statement per Term
    in its list; writing one item per Term keeps only the last definition."""
    out: dict[str, list[Term]] = {}
    for t in terms:
        out.setdefault(term_key(state, ref, t.term, t.scope_pinpoint), []).append(t)
    return out


def _find_mention(text: str, term: str) -> int | None:
    m = re.search(r"\b" + r"\s+".join(re.escape(w) for w in term.split()), text, re.I)
    if not m and term.split():
        words = term.split()
        m = re.search(r"\b" + r"\s+".join(re.escape(w) for w in words[:-1] + [words[-1] + "s"]), text, re.I)
    return m.start() if m else None


def _verb_kind(verb: str) -> str:
    v = " ".join(verb.lower().split())
    if "not include" in v or "not apply" in v:
        return "excludes"
    if "include" in v:
        return "includes"
    if "contain" in v or "consist" in v:
        return "contents"
    if "meaning" in v and "following" not in v:
        return "by_reference"
    return "means"


def _where(text: str, at: int) -> str | None:
    m = WHERE.search(text, at, min(len(text), at + 160))
    return _ws(m.group("w")) if m else None


# ------------------------------------------------------------------ keys
def term_key(state: str, ref: str, term: str, pinpoint: str | None = None) -> str:
    """The Wikibase key (P25) of a term as one section defines it, beside that section's statute key
    ``lexflow:statute:{state}:{ref}``: ``lexflow:term:fl:607.0201:incorporator``.  A term with a sub-section scope
    gets the pinpoint, so two definitions of one word for (g) and (h) differ: ``...:request@g``.  Definitions that
    share a key (one term, one scope, several kinds) are one item: see :func:`group_by_key`.  The term part is
    :func:`slug` (frozen, no plural folding)."""
    pin = re.sub(r"[^\w\-]+", "", pinpoint or "").lower()
    return f"lexflow:term:{state}:{ref}:{slug(term)}" + (f"@{pin}" if pin else "")


def unit_key(state: str, scope_unit: str) -> str:
    """The key of a scope unit (a chapter, act or article that a definition governs), from its index path:
    ``lexflow:unit:fl:florida-code-title-xxxvi-chapter-607``; an anchored unit ('... / Subchapter containing
    § 2-1561') and a named one ('MD Code / Article gcl / Titles 1-10') are keyed the same way."""
    return f"lexflow:unit:{state}:" + re.sub(r"[^a-z0-9]+", "-", (scope_unit or "").lower()).strip("-")


def concept_key(name: str, sense: str | None = None) -> str:
    """The key of a cross-jurisdiction concept: ``lexflow:concept:incorporator``.  A homonym gets its sense as a
    suffix: ``concept_key("agency", "public records")`` -> ``lexflow:concept:agency--public-records`` (and agency
    law keeps ``lexflow:concept:agency``).  Nothing here mints one: ``name`` and ``sense`` are a reviewer's
    decision, read from the stored review table, and the extractor's term is only a suggestion for them."""
    return f"lexflow:concept:{slug(name)}" + (f"--{slug(sense)}" if sense and slug(sense) else "")


# ------------------------------------------------------------------ Wikidata candidate features
_LM_STOP = {"of", "the", "a", "an", "and", "or", "for", "to", "in", "on", "by", "s"}
US_STATES = [n for n in STATE_NAME.values()]
_US_STATE_RE = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in sorted(US_STATES, key=len, reverse=True)) +
                          r")\b")
_FOREIGN = re.compile(
    r"\b(?:Afghan|Albania|Algeria|Argentin|Armenia|Australia|Austria|Bangladesh|Belgi|Bermuda|Brazil|Britain|British|"
    r"Bulgaria|Canad|Chile|China|Chinese|Colombia|Croatia|Cyprus|Czech|Danish|Denmark|Dutch|Egypt|England|Estonia|"
    r"Europe|European|Finland|Finnish|France|French|German|Greece|Greek|Hong Kong|Hungar|India|Indonesia|Iran|Ireland|"
    r"Irish|Israel|Ital|Japan|Kenya|Korea|Latvia|Lithuania|Luxembourg|Malaysia|Mexic|Netherlands|New Zealand|Nigeria|"
    r"Norw|Pakistan|Peru|Philippin|Poland|Polish|Portug|Quebec|Romania|Russia|Scotland|Scottish|Singapore|Slovak|"
    r"Sloven|South Africa|Spain|Spanish|Swed|Swiss|Switzerland|Taiwan|Thai|Turk|Uganda|Ukrain|United Kingdom|"
    r"Wales|Welsh|Vietnam|Soviet|Ontario|Prussia|Bavaria|Roman law|UK)\b")
# Generic kinds of Wikidata item that are never a legal concept (works, people, places, organisms), written while
# reading the survey, so leave-one-term-out cannot measure how much they lean on it.  The PropBank tokens that were
# here ("prototypical", "proto-agent", "PropBank", "predicate", "semantic role") are gone: they matched only the
# survey's five PropBank pairs, all judged wrong, incorporator's among them, so they encoded the answers.
_JUNK = re.compile(
    r"(?i:(?:scientific|scholarly) article|article (?:published|from)|\bjournal\b|thesis|monograph|\breport\b|"
    r"\bfilm\b|episode|\balbum\b|video game|single by|\bsong\b|television|TV series|\bnovel\b|comic|\bband\b|"
    r"record label|magazine|newspaper|painting|print in|print by|drawing|sculpture|family name|given name|surname|"
    r"National Archives|\bprotein\b|\bgene\b|"
    r"disambiguation|Wikimedia|commune|census|settlement|\bisland\b|football|\bbuilding\b|\bship\b|library|"
    r"Supreme Court case|patent|database|\bcollection\b|literary work|\bhuman\b|cocktail|\bwork by\b|software|"
    r"species|genus|\bfamily of\b|river|mountain|village|\btown\b|\bcity\b|neighbo(?:u)?rhood|\bstation\b|"
    r"school|university|museum|\bclub\b|\bteam\b|politician|\bactor\b|singer|statistical|race in|fictional)")
_LAW_INSTANCE = re.compile(r"\b(?:Act|Statute|Code)\b|\bstatute\b|\blegislation\b|\bstatutory instrument\b|"
                           r"\bact of (?:congress|parliament)|\blaw (?:of|in) (?:the )?[A-Z]|\bbill\b")
_DESC_LEGAL = re.compile(r"(?i)\b(?:law|legal|court|judicial|judge|jur|statut|crim|offen[cs]e|prison|jail|inmate|"
                         r"police|attorney|prosecut|government|public|agency|official|licen[cs]|tax|fines?\b|penalt|"
                         r"sentenc|trial|proceeding|lawsuit|litigation|contract|corporat|business|partner|liabilit|"
                         r"debt|payment|fee\b|right|duty|obligation|regulat|enforce)")
_DESC_PERSON = re.compile(r"(?i)\b(?:person|individual|one|someone|party|entity|body|official|officer|agent|employee|"
                          r"member)s?\s+(?:who|that|whose|which|designated|responsible|authorized|appointed|elected)\b|"
                          r"\bofficer\b|\bofficial\b|\bposition\b|\boccupation\b|\bprofession\b|\brole\b")
_DESC_DOC = re.compile(r"(?i)\b(?:document|certificate|record|form|filing|instrument|letter|notice|writ|order|"
                       r"agreement|contract|license|licence|permit)s?\b")
_DESC_US = re.compile(r"United States|\bU\.S\.|\bUS\b|\bAmerican\b|\bfederal\b")
_CLASS_NEG = re.compile(
    r"(?i)scholarly|\barticle\b|film|episode|television|series|album|song|single|video game|literary|novel|painting|"
    r"\bprint\b|sculpture|collection|exhibition|\bhuman\b|given name|family name|surname|"
    r"\bgene\b|protein|Wikimedia|disambiguation|building|structure|\bship\b|software|library|"
    r"website|\borganization\b|enterprise|business|company|legal case|decision of|statute|\bAct of\b|statutory|"
    r"\bbill\b|report|edition|\bband\b|musical|magazine|newspaper|periodical|geographic|\bcity\b|\btown\b|village|"
    r"municipality|human settlement|census|state agency of|agency of the")
_CLASS_POS = re.compile(
    r"(?i)legal|\blaw\b|occupation|profession|position|\brole\b|status|document|process|procedure|proceeding|crime|"
    r"offen[cs]e|punishment|penalty|sanction|remedy|\bright\b|writ|court|tribunal|government agency|public (?:body|"
    r"office|institution)|business entity|contract|record|\bfee\b|\btax\b|payment|official|\bname\b|juridical|"
    r"\bpartnership\b|corporation|limited company|\bprison\b|\bjail\b|police")
_CLASS_POSITION = re.compile(r"(?i)\b(?:position|occupation|profession|job|title)\b")

_P31_STATUTE = re.compile(r"(?i)\bAct of\b|\bstatute\b|statutory instrument|\blegislation\b|\bbill\b|\bordinance\b|"
                          r"\bregulation\b|\blaw of\b|constitution")

# Left out: whether a candidate came from the survey's second, alternate-phrasing pass (that pass ran only for
# terms whose first pass had no exact hit, so the flag learns the survey's design, not anything a live search
# has), and "same_state" (computed, but the survey records no state per term, so it cannot be fitted; a state
# passed to link() still exempts its own name from desc_us_state).
FEATURES = ["lm_exact", "lm_alias", "lm_partial", "jaccard", "label_extra", "label_missing", "desc_none",
            "desc_legal", "desc_person", "desc_document", "desc_us", "desc_junk", "desc_law_instance",
            "desc_foreign", "desc_us_state", "jur_foreign", "jur_us", "class_pos", "class_neg", "class_position",
            "class_legal_form", "p31_statute", "p279_is_term", "no_class", "sitelinks", "rank_recip",
            "label_mul_only", "most_sitelinks_match", "match_ambiguity"]
EMB_FEATURE = "emb_sim"


def _matches(term: str, cand: dict) -> bool:
    t = _lm_norm(term)
    return bool(t) and (t == _lm_norm(cand.get("label") or "") or
                        any(t == _lm_norm(a) for a in cand.get("aliases") or []))


def _sitelinks(cand: dict) -> int:
    s = cand.get("sitelinks") or 0
    return len(s) if isinstance(s, (list, tuple)) else int(s)


def _lm_norm(s: str) -> str:
    s = (s or "").lower().replace("’", "'").replace("'s", "")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    words = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in s.split()]
    return " ".join("labor" if w == "labour" else w for w in words)


def _content(s: str) -> set[str]:
    return set(_lm_norm(s).split()) - _LM_STOP


def _labels(xs) -> list[str]:
    out = []
    for x in xs or []:
        out.append((x.get("label") or x.get("qid") or "") if isinstance(x, dict) else str(x))
    return [o for o in out if o]


def candidate_features(term: str, cand: dict, rank: int | None = None, state: str | None = None,
                       emb_sim: float | None = None, peers: list[dict] | None = None) -> dict[str, float]:
    """Features of one Wikidata candidate for one term.  ``cand`` has the survey's shape: qid, label,
    description, aliases, p31 / p279 / jurisdiction as [{qid, label}] (or bare ids), sitelinks (a count),
    label_lang, rank.  ``peers`` are all the term's candidates (this one included): two features compare a
    label-matching candidate with the others that match.  See :func:`candidate_from_entity` for building a
    candidate from ``wbgetentities``."""
    label = cand.get("label") or ""
    aliases = cand.get("aliases") or []
    desc = cand.get("description") or ""
    t, lab = _lm_norm(term), _lm_norm(label)
    exact = bool(t) and t == lab
    alias = not exact and any(t == _lm_norm(a) for a in aliases)
    tw, lw = _content(term), _content(label)
    best_alias = max(aliases, key=lambda a: len(tw & _content(a)), default="")
    alias_words = set().union(*[_content(a) for a in aliases]) if aliases else set()
    partial = not exact and not alias and bool(tw & (lw | alias_words))
    jac = len(tw & lw) / len(tw | lw) if (tw | lw) else 0.0
    classes = _labels(cand.get("p31")) + _labels(cand.get("p279"))
    cls_text = " | ".join(classes)
    jur = _labels(cand.get("jurisdiction"))
    jur_us = any("United States" in j or j in US_STATES for j in jur)
    text = f"{desc} | {cls_text}"
    term_is_law = bool(re.search(r"\b(?:act|law|code|statute|rule)s?\b", term.lower()))
    term_names_state = bool(_US_STATE_RE.search(term)) or "Commonwealth" in term
    states_named = set(_US_STATE_RE.findall(desc)) | {j for j in jur if j in US_STATES}
    own = STATE_NAME.get((state or "").lower())
    pos = sum(1 for c in classes if (re.match(r"(?i)(?:type|kind|class) of", c) or
                                     (_CLASS_POS.search(c) and not _CLASS_NEG.search(c))))
    neg = sum(1 for c in classes if _CLASS_NEG.search(c) and not re.match(r"(?i)(?:type|kind|class) of", c))
    rank = rank or cand.get("rank") or 1
    sitelinks = _sitelinks(cand)
    matching = [c for c in (peers or [cand]) if _matches(term, c)] if (exact or alias) else []
    most = bool(matching) and sitelinks >= max(_sitelinks(c) for c in matching)
    return {
        "lm_exact": float(exact), "lm_alias": float(alias), "lm_partial": float(partial), "jaccard": jac,
        "label_extra": min(4, len(lw - tw)) / 4, "label_missing": min(3, len(tw - lw - _content(best_alias))) / 3,
        "desc_none": float(not desc), "desc_legal": float(bool(_DESC_LEGAL.search(desc))),
        "desc_person": float(bool(_DESC_PERSON.search(desc))), "desc_document": float(bool(_DESC_DOC.search(desc))),
        "desc_us": float(bool(_DESC_US.search(desc))), "desc_junk": float(bool(_JUNK.search(text))),
        "desc_law_instance": float(bool(_LAW_INSTANCE.search(f"{label} | {desc}")) and not term_is_law),
        "desc_foreign": float(bool(_FOREIGN.search(desc))),
        "desc_us_state": float(bool(states_named - ({own} if own else set())) and not term_names_state),
        "same_state": float(bool(own) and own in states_named),
        "jur_foreign": float(bool(jur) and not jur_us), "jur_us": float(jur_us),
        "class_pos": min(2, pos) / 2, "class_neg": min(2, neg) / 2,
        "class_position": float(any(_CLASS_POSITION.search(c) for c in classes)),
        "class_legal_form": float(any(c.lower() == "legal form" for c in classes)),
        "p31_statute": float(any(_P31_STATUTE.search(c) for c in _labels(cand.get("p31")))),
        "p279_is_term": float(any(_lm_norm(c) == t for c in _labels(cand.get("p279")))),
        "no_class": float(not classes), "sitelinks": math.log1p(sitelinks) / math.log(50),
        "rank_recip": 1.0 / max(1, int(rank)), "label_mul_only": float(cand.get("label_lang") == "mul"),
        "most_sitelinks_match": float(most), "match_ambiguity": min(2, max(0, len(matching) - 1)) / 2,
        **({EMB_FEATURE: emb_sim} if emb_sim is not None else {}),
    }


def candidate_from_entity(qid: str, entity: dict, labels: dict[str, str] | None = None, rank: int = 1) -> dict:
    """A ``wbgetentities`` entity (languages en|mul, props labels|descriptions|aliases|claims|sitelinks) -> the
    candidate shape the features read.  ``labels`` names the P31/P279/P17/P1001 values (fetch them in one more
    ``wbgetentities`` call); unnamed classes still count as classes."""
    labels = labels or {}
    claims = entity.get("claims") or {}

    def vals(p):
        out = []
        for c in claims.get(p, []):
            v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
            if isinstance(v, dict) and "id" in v:
                out.append({"qid": v["id"], "label": labels.get(v["id"])})
        return out

    lab = entity.get("labels") or {}
    al = entity.get("aliases") or {}
    return {"qid": qid, "label": (lab.get("en") or lab.get("mul") or {}).get("value"),
            "label_lang": "en" if "en" in lab else "mul" if "mul" in lab else None,
            "description": ((entity.get("descriptions") or {}).get("en") or {}).get("value"),
            "aliases": [a["value"] for a in al.get("en", []) + al.get("mul", [])],
            "p31": vals("P31"), "p279": vals("P279"),
            "jurisdiction": list({d["qid"]: d for d in vals("P1001") + vals("P17")}.values()),
            "sitelinks": len(entity.get("sitelinks") or {}), "rank": rank, "pass": "first"}


# ------------------------------------------------------------------ the model
def _sigmoid(z):
    import numpy as np
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_lr(X, y, l2: float = 1.0, iters: int = 100):
    """L2-penalised logistic regression by Newton's method on standardised columns; returns (beta, mu, sd)."""
    import numpy as np
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-6
    Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    k = Z.shape[1]
    reg = np.r_[np.full(k - 1, l2), 0.0]
    beta = np.zeros(k)
    for _ in range(iters):
        p = _sigmoid(Z @ beta)
        g = Z.T @ (p - y) + reg * beta
        H = (Z * (p * (1 - p))[:, None]).T @ Z + np.diag(reg) + 1e-9 * np.eye(k)
        step = np.linalg.solve(H, g)
        beta -= step
        if np.abs(step).max() < 1e-8:
            break
    return beta, mu, sd


def predict(model: dict, rows: list[dict[str, float]]) -> list[float]:
    import numpy as np
    if not rows:
        return []
    X = np.array([[r.get(f, 0.0) for f in model["features"]] for r in rows], dtype=float)
    mu, sd, beta = (np.asarray(model[k], dtype=float) for k in ("mu", "sd", "beta"))
    Z = np.hstack([(X - mu) / sd, np.ones((len(X), 1))])
    return [float(p) for p in _sigmoid(Z @ beta)]


# The review queue's threshold: the model's even-odds point, a convention, not a value searched for on the survey's
# scores (the precision curve was looked at, not optimised).  The threshold where out-of-fold term precision first
# reaches 0.90 (0.7607) is not used: it sits just above the PropBank "incorporator" (0.727 out of fold, judged
# wrong), so that one term's label places it.
REVIEW_THRESHOLD = 0.5


def fit_link_model(rows: list[dict[str, float]], y: list[int], features: list[str] | None = None, l2: float = 1.0,
                   review_threshold: float | None = None, **meta) -> dict:
    """A model dict for :func:`predict`.  It carries one threshold, ``review_threshold``: the score at which a
    candidate is queued for a person to review.  No threshold makes a link safe to write unreviewed."""
    features = features or FEATURES
    beta, mu, sd = fit_lr([[r.get(f, 0.0) for f in features] for r in rows], y, l2=l2)
    return {"features": features, "mu": [round(float(x), 6) for x in mu], "sd": [round(float(x), 6) for x in sd],
            "beta": [round(float(x), 6) for x in beta], "l2": l2, "review_threshold": review_threshold, **meta}


def survey_pairs(path: Path | str = SURVEY) -> list[dict]:
    """The survey's (term, candidate) pairs: [{term, qid, judgement, y, cand}], y = 1 for 'exact'."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [{"term": r["term"], "qid": c["qid"], "judgement": c["judgement"], "y": int(c["judgement"] == "exact"),
             "cand": c, "kind": r.get("kind"), "source": r.get("source")} for r in d["terms"] for c in r["candidates"]]


def pair_features(pairs: list[dict]) -> list[dict[str, float]]:
    """:func:`candidate_features` of every survey pair, each with its term's other candidates as peers."""
    peers: dict[str, list[dict]] = {}
    for p in pairs:
        peers.setdefault(p["term"], []).append(p["cand"])
    return [candidate_features(p["term"], p["cand"], peers=peers[p["term"]]) for p in pairs]


_MODEL_CACHE: dict = {}


def default_model() -> dict:
    """:data:`LINK_MODEL`, or (when that is unset) the model fitted on the survey fixture."""
    if LINK_MODEL and LINK_MODEL["features"] == FEATURES:
        return LINK_MODEL
    if "fitted" not in _MODEL_CACHE:
        pairs = survey_pairs()
        _MODEL_CACHE["fitted"] = fit_link_model(pair_features(pairs), [p["y"] for p in pairs], l2=10.0,
                                                review_threshold=REVIEW_THRESHOLD)
    return _MODEL_CACHE["fitted"]


def unlinkable(cand: dict) -> bool:
    """An item with neither a description nor a P31/P279 class: nothing on it says which sense it is, so it is
    never linked automatically, whatever its label (the survey's 'Ability-to-pay' and 'Undue hardship')."""
    return not cand.get("description") and not cand.get("p31") and not cand.get("p279")


def link(term: str, candidates: list[dict], *, model: dict | None = None, threshold: float | None = None,
         state: str | None = None, embed=None, context: str | None = None) -> tuple[str | None, float]:
    """A suggestion for review: the Wikidata item that may be the same concept as ``term`` (or None), and the best
    candidate's probability.  It is never an exact match by itself: a link is written only after a person has
    reviewed it, and a returned qid only puts the pair in the review queue.

    ``candidates`` are search hits in rank order (see :func:`candidate_features` for their shape).  ``state``
    (a postal code) keeps a candidate that names that state from counting as "another state's" item, so of five
    state Offices of Administrative Hearings only the right state's escapes that penalty.  ``embed`` (a callable:
    texts -> unit vectors, e.g. ``lexflow.extract.selector.Embedder``) and ``context`` (the defining words or
    heading) feed the embedding-similarity feature, for a model fitted with it; the shipped model has none, so
    both are ignored unless such a model is passed.  ``threshold`` defaults to the model's ``review_threshold``,
    the fixed :data:`REVIEW_THRESHOLD` 0.5 (out-of-fold term precision 0.85 on the survey; see
    :data:`LINK_MODEL`)."""
    if not candidates:
        return None, 0.0
    model = model or default_model()
    sims = [None] * len(candidates)
    if embed is not None and EMB_FEATURE in model["features"]:
        sims = embedding_sims(term, candidates, embed, context)
    rows = [candidate_features(term, c, rank=c.get("rank") or i + 1, state=state, emb_sim=s, peers=candidates)
            for i, (c, s) in enumerate(zip(candidates, sims))]
    ps = [0.0 if unlinkable(c) else p for c, p in zip(candidates, predict(model, rows))]
    i = max(range(len(ps)), key=ps.__getitem__)
    thr = model.get("review_threshold") if threshold is None else threshold
    thr = REVIEW_THRESHOLD if thr is None else thr
    return (candidates[i]["qid"] if ps[i] >= thr else None), ps[i]


suggest = link


def embedding_sims(term: str, candidates: list[dict], embed, context: str | None = None) -> list[float]:
    """Cosine similarity of the term (with its defining context) to each label-matching candidate's label,
    description and classes, minus 0.5; 0 for the others, which the label features already rule out."""
    want = [i for i, c in enumerate(candidates) if _matches(term, c)]
    if not want:
        return [0.0] * len(candidates)
    head = f"legal term in United States law: {term}" + (f". {' '.join(context.split()[:60])}" if context else "")
    v = embed([head] + [_cand_text(candidates[i]) for i in want])
    out = [0.0] * len(candidates)
    for k, i in enumerate(want, 1):
        out[i] = float(v[0] @ v[k]) - 0.5
    return out


def _cand_text(c: dict) -> str:
    classes = ", ".join(_labels(c.get("p31")) + _labels(c.get("p279")))
    return f"{c.get('label') or ''}: {c.get('description') or ''}" + (f" ({classes})" if classes else "")


# Fitted by ``scripts/terms_eval.py --print-model`` on all 714 pairs of fixtures/xref/wikidata_terms.json, with
# no PropBank tokens in the cue lists.  It is review-only.  ``review_threshold`` is :data:`REVIEW_THRESHOLD`, 0.5,
# the even-odds point, not searched for on the survey.  Leaving one term out, it suggests 91 of the survey's 150
# terms, 77 of them the exact item (precision 0.85, 95% Clopper-Pearson lower bound 0.76; recall 77 of the 106
# terms that have an exact item).  Of
# the other 14, 11 are broader or related concepts, 2 are different things (the 18 U.S.C. § 2257 custodian of
# records, and the PropBank "incorporator" at 0.73) and 1 possibly is (the civil restitution remedy).  So it fills
# a queue; a person accepts or rejects every suggestion before anything is written.  No threshold makes
# unreviewed exact links safe: a P >= 0.95 target links 2 terms out of fold (lower bound 0.16), and 1 of 2 in the
# nested estimate; the P >= 0.90 target's threshold (0.7607) is placed by the incorporator, the next term down.
LINK_MODEL: dict | None = {
    "features": ["lm_exact", "lm_alias", "lm_partial", "jaccard", "label_extra", "label_missing", "desc_none",
                 "desc_legal", "desc_person", "desc_document", "desc_us", "desc_junk", "desc_law_instance",
                 "desc_foreign", "desc_us_state", "jur_foreign", "jur_us", "class_pos", "class_neg", "class_position",
                 "class_legal_form", "p31_statute", "p279_is_term", "no_class", "sitelinks", "rank_recip",
                 "label_mul_only", "most_sitelinks_match", "match_ambiguity"],
    "mu": [0.359944, 0.092437, 0.473389, 0.54674, 0.386204, 0.105976, 0.086835, 0.340336, 0.037815, 0.123249,
           0.096639, 0.452381, 0.047619, 0.095238, 0.056022, 0.138655, 0.12465, 0.197479, 0.287815, 0.060224,
           0.053221, 0.04902, 0.05042, 0.05042, 0.268725, 0.511345, 0.026611, 0.179272, 0.369748],
    "sd": [0.479985, 0.289643, 0.499292, 0.386631, 0.395957, 0.212008, 0.281594, 0.473823, 0.19075, 0.328724,
           0.295466, 0.497728, 0.21296, 0.293545, 0.229966, 0.345588, 0.330322, 0.35138, 0.260909, 0.237903,
           0.224475, 0.21591, 0.218811, 0.218811, 0.334809, 0.310763, 0.160944, 0.383581, 0.472474],
    "beta": [0.231234, 0.053226, -0.245836, 0.581549, -0.254617, -0.087913, 0.207722, 0.467774, 0.14154, -0.143832,
             0.048321, -0.695328, -0.247213, -0.387002, -0.172358, -0.246613, 0.202205, 0.308187, -0.397875,
             -0.161854, -0.30003, -0.2748, 0.011151, -0.022511, 0.110886, 0.421201, -0.285028, 0.528819, -0.174396,
             -3.52536],
    "l2": 10.0,
    "review_threshold": 0.5,
    "trained_on": "fixtures/xref/wikidata_terms.json: 150 terms with candidates, 714 pairs",
}
