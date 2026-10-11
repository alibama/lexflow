"""Draft forms and letters for steps that have no official form, built only from the statute's own words.

A draft is a list of *elements*. An element is either something the request contains (a field to fill in, a
sentence of the letter) or something the person should know (a duty of the other side, a deadline, a
consequence). Each element cites its section and subsection and quotes the words it rests on. :func:`check`
tests these rules, and :func:`build` refuses to make a draft that breaks one:

* every quote is found word for word in the section text, and inside the subsection it cites, to the depth cited
  ("f.3.D" is (f)(3)(D)). Only whitespace and curly quotation marks are normalised. In a section lettered (a),
  (b) ..., an unlettered paragraph before the first subdivision or after the last is the section's own text and
  belongs to none of them; an unlettered paragraph between two subdivisions is ambiguous, so no citation accepts
  it. In a section lettered A., B. ..., an unlettered paragraph continues the subsection above it. An element with
  no subsection must quote the section's own unlettered text (its opening or closing words);
* the mandatory words of ``required``, ``if_asked`` and ``duty`` elements fall on the right party. The parties are
  the statute's words for each side (``Spec.parties``; the person's include the word for the person's request); a
  spec that names no parties is refused. The *bearer* of "shall", "must" or "may require" is the last party
  before it, in its clause, that heads a subject: one that is not possessive ("the applicant's decision") and has
  nothing but "a", "the", "written" and the like between it and the start of the clause, a comma, semicolon or
  colon, a paragraph mark, or "and", "or", "but" or "then". So a party after a preposition ("to a request", "by
  the applicant"), a verb ("may request") or a subordinating word ("unless the applicant shall ...") is passed
  over. There is no bearer (see :func:`_bearer_at`) when the party right before the mandatory word is passed over
  ("a request that the public body shall answer ... is valid": the word is the public body's, in a relative
  clause); when the party found has a verb of its own right after it ("a board may request ..., provided that
  ... the applicant's decision ... shall not ...") and the mandatory word is not a second verb of it after "and",
  "or", "nor" or "but"; and when the party found is joined to a party of the other side ("the public body or the
  requester shall").

  - ``required``: "shall" or "must" whose bearer is the person, named inside the quote, and not followed by "not",
    "have" or "constitute" (a prohibition, a grant, a legal consequence), by "receive", "obtain", "get" and the
    like (a benefit) or by a passive "be ..." other than the person's own acts ("be made", "be filed", "be
    signed" ...; and not "by" the other side). Or "unless" or "only if" followed by the person as the condition's
    subject, where the rest of the sentence (the consequence) names the person and not the other side, is a loss
    ("waived", "withdrawn", "denied" ...) and is not negated ("shall not be denied" is no loss). So the board's
    duty in § 487 with its "unless the applicant ..." exception, a "deemed a denial" rule and "disclosure is
    voluntary" are not requirements of the person. A quote that says the act is voluntary or optional
    ("voluntary", "need not", "at the option of" ...) is never ``required`` or ``if_asked``;
  - ``if_asked``: "may require" (not "may request", which asks without requiring) whose bearer is the other side,
    with the person the first party after it;
  - ``duty``: "shall" or "must" whose bearer is the other side, not followed by "have", "constitute" or "be
    deemed", "be tolled", "be granted" and the like (a grant or a legal consequence), nor by "not be required",
    "not be obliged", "be exempt" and the like (an exemption). "Shall not" is a duty;
* a requirement of the person is shown as one. An element of any other level whose quote passes the ``required``
  test (:func:`passes`) is refused, so a requirement is never shown as a choice (``right``), a context line, a
  note or a duty of the other side. A ``right`` or ``context`` element whose quote passes the ``if_asked`` test
  is refused too. A ``notice`` or ``duty`` may rest on "may require": neither carries a field for the person to
  fill in, a notice is never in the letter, and Va. Code § 2.2-3704(I) (earlier unpaid bills) is a demand the
  other side may make outside the request. Every ``required`` and ``if_asked`` element is in the letter's layout;
* the label of a ``required``, ``if_asked``, ``duty`` or ``right`` element, and each of its fields (name, and
  label with options), shares a word with its quote, so an element cannot rest on an unrelated sentence. Each
  field of a ``context`` element shares a word with its quote too, where the other side's words count (they name
  who the letter goes to); only the letter's own date and the sender's name (:data:`LETTER_FIELDS`) need none,
  and each only by its name and type, with no placeholder or options, and with a label that holds the date or
  name word and no word outside a short list ("Your name" passes; "Your name and phone number" does not).
  ``duty`` and ``notice`` elements carry no fields, and a ``notice`` element is never part of the letter;
* no text of an element (label, help, condition, letter sentence outside ``{quote}``, field labels, placeholders,
  options and the description of a linked form) uses an obligation word that its quote does not use. The words
  are matched by stem ("requir" for "required" and "requiring") and include "must", "shall", "should", "ought",
  "need", "necessary", "essential", "compulsory", "compelled", "obliged", "mandated", "expected", "req.",
  "please", "is to be" ... (see :data:`_OBLIGATION`). The ``right``, ``context`` and ``notice`` elements use no
  obligation word at all, and neither do the spec's own texts: title, summary, scope, the headings of related
  forms, the fixture's no-form note shown on the page, and the letter's fixed parts (subject, salutation,
  closing). Texts are read after Unicode folding (NFKC, so a full-width "ｍｕｓｔ" is "must"), with invisible
  format characters (soft hyphens, zero-width spaces) removed. No text uses an asterisk-like mark ("*", "＊",
  "∗", "✱" ...: any character whose Unicode name says asterisk), and none uses a letter outside the Latin script,
  which could make an obligation word look like another word;
* no field has a default value, so nothing is chosen for the person;
* an official form linked from an element says what the form is and carries its match, "partial" or "related"
  (never "exact"). A form the fixture links to no step of the same process is at most "related"; otherwise the
  match is never stronger than the fixture gives that form for a step of the same process;
* the letter is assembled from the elements alone, in the spec's layout, and every paragraph carries the id of the
  element it comes from;
* no draft is made for a step that has an official paper form (match ``exact`` in fixtures/forms/forms.json), and
  both the form page and the printable letter list the official alternatives first, under the banner
  :data:`BANNER`.

These checks are mechanical word matching, not parsing. Each case found by docs/design/verify-forms.md and its
two re-checks is refused, and tests/test_forms.py pins each one, but a sentence worded differently can still pass:
for example a context field whose label names the other side, a statute that names a party with a word the spec
does not list or with a pronoun, a benefit verb that is not on the list, or a mandatory word whose real subject is
a noun that is not a party. The checks cannot prove that an element states the law correctly, or that it puts a
duty on the right party. Each spec still needs a lawyer's review.

Printed, each part of the letter page (the scope and official forms, the letter, the notes) starts a new sheet
with the banner at its top, and a CSS page-margin box repeats the banner at the top of every sheet in browsers
that support margin boxes.

The HTML form runs in the browser alone. It has no action URL, sends nothing and stores nothing. Printing is its
only output.

Run ``python -m lexflow.forms.draft --out out/forms`` to write the worked examples (needs the statute text: the
fixture in fixtures/statutes/, else the local open-us-law store).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from . import registry as R

BANNER = ("Draft made by lexflow from the statute; not an official form and not legal advice; "
          "use the official form if the agency has one")
SCHEMA = "lexflow-form-draft/1"

LEVELS = {
    "required": "Required by the statute",
    "if_asked": "Only if they ask for it",
    "right": "Your choice under the statute",
    "context": "Who, what and when",
    "duty": "What the other side has to do",
    "notice": "Good to know",
}
_MARKERS = {
    "required": re.compile(r"\b(shall|must|unless|only if)\b", re.I),
    # "may require" only: "may request" lets the other side ask without making it a requirement
    "if_asked": re.compile(r"\bmay (require)\b", re.I),
    "duty": re.compile(r"\b(shall|must)\b", re.I),
}
# levels whose element states a duty or a right: its label and fields must share a word with its quote
_RELEVANT = {"required", "if_asked", "duty", "right"}
# levels that are notes for the person: nothing to fill in
_NO_FIELDS = {"duty", "notice"}
# levels that must be in the letter: what the statute requires of the person, or lets the other side require
_IN_LETTER = {"required", "if_asked"}
# the letter's own parts, which a context element may carry without quote support: the field's type, the word
# its label must contain, and the only words its label may hold (so "Your name and phone number" is not one)
LETTER_FIELDS = {"date_sent": ("date", "date", frozenset({"date", "you", "send", "sent", "it", "of", "the", "this",
                                                          "letter"})),
                 "name": ("text", "name", frozenset({"your", "name", "full"}))}
# words that state an obligation, matched on the text after Unicode normalisation (:func:`_plain`). Outside a
# quotation they may appear only in required, if_asked and duty elements, and there only when the element's own
# quote uses the same word. Stems catch the inflections ("requir" for "required", "requiring" ...)
_OBLIGATION = re.compile(
    r"\b(must\w*|shall\w*|should\w*|ought\w*|requir\w*|requisit\w*|prerequisit\w*|req(?:d|'d)?(?=\.|\b)|"
    r"have to|has to|had to|having to|got to|gotta|need\w*|necess\w*|essential\w*|indispensab\w*|compuls\w*|"
    r"compel\w*|oblig\w*|mandat\w*|expect\w*|responsib\w*|please|kindly|make sure|be sure|remember to|"
    r"do not forget|don't forget|(?:is|are|am|was|were)\s+to\s+(?:be|give|provide|include|send|state|supply|attach|"
    r"enclose|list|sign|fill|enter|complete)|to be (?:given|provided|included|stated|supplied|attached|enclosed|"
    r"filled|entered|completed|signed|sent))\b", re.I)
# a quote saying the act is voluntary or optional cannot carry a required element
_VOLUNTARY = re.compile(r"\b(voluntary|voluntarily|optional|need not|not required|not be required|"
                        r"at the option of)\b", re.I)
# after "shall" or "must" in a required element: a prohibition, a grant, a benefit or a legal consequence is not a
# duty of the person, and of passive verbs only the person's own acts count ("A request shall be made in
# writing"), and not when the other side is the agent ("shall be made by the public body")
_NOT_A_DUTY = re.compile(r"\s+(not|have|constitute|receive|obtain|get|gain|enjoy|recover|benefit)\b", re.I)
_PASSIVE = re.compile(r"\s+be\b", re.I)
_PASSIVE_OK = re.compile(r"\s+be\s+(made|submitted|filed|signed|sent|delivered|presented|accompanied|"
                         r"in writing)\b", re.I)
# after "shall" or "must" in a duty element: a grant, a legal consequence or an exemption ("shall not be
# required") is not a duty of the other side
_NOT_A_DUTY_OTHER = re.compile(r"\s+(have|constitute|be\s+(deemed|considered|treated|presumed|construed|tolled|"
                               r"credited|allowed|permitted|entitled|given|granted|waived|exempt|exempted|excused|"
                               r"relieved)|not\s+be\s+(required|obliged|obligated|compelled|bound|expected|liable)|"
                               r"not\s+have|not\s+need)\b", re.I)
# the consequence of an "unless" or "only if" condition on the person: a loss, so the condition is a requirement;
# a negated consequence ("shall not be denied") is no loss
_LOSS = re.compile(r"\b(waived?|forfeit|forfeited|lapses?|lapsed|withdrawn|barred|denied|dismissed|lost|"
                   r"abandoned|refused|rejected|void)\b", re.I)
_NEGATION = re.compile(r"\b(not|no|never|neither|nor|cannot|without)\b|n't\b", re.I)
# a verb right after a party: the party is the subject of that verb, not of a mandatory word further on
_OWN_VERB = re.compile(r"\s+(may|shall|must|will|can|could|would|should|might|is|are|was|were|has|have|had|does|"
                       r"do|did)\b", re.I)
# words that may stand between a party and the start of its noun phrase ("a written request")
_MODIFIERS = {"a", "an", "the", "any", "each", "every", "such", "said", "written", "his", "her", "its", "their"}
# words after which a party heads a subject: "and", "or", "but", "then" (and a comma, semicolon, colon or
# paragraph mark, see _heads_subject)
_JOINERS = {"and", "or", "but", "then"}
# words that join two parties into one subject ("the public body or the requester")
_COORDINATORS = {"and", "or", "nor"}
_COORDINATION = _COORDINATORS | {"either", "both", "neither", ","}
_PARA_MARK = re.compile(r"\(\w{1,5}\)|\w{1,3}\.")
_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_OPTIONAL = re.compile(r"\[([^\[\]]*)\]")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', " ": " "})
# paragraph markers: (a) (1) (A) (i) in California style, A. 1. a. in Virginia style
_MARK_PAREN = re.compile(r"\((\d{1,3}|[a-z]{1,5}|[A-Z]{1,2})\)\s*")
_MARK_DOT = re.compile(r"(\d{1,3}|[a-zA-Z])\.\s+")
_ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv", "xvi",
          "xvii", "xviii", "xix", "xx"}
# a clause ends at . ; or : before a capital letter or an opening parenthesis
_CLAUSE_END = re.compile(r"[.;:](?=\s+[A-Z(\"])")
_STOP = {"that", "this", "with", "from", "your", "have", "been", "were", "what", "when", "where", "which", "their",
         "there", "they", "them", "than", "then", "each", "such", "only", "into", "under", "after", "before",
         "would", "like", "about", "also", "does", "other", "these", "those", "will", "upon", "following",
         "either", "whether", "optional", "applies", "shall", "must", "more", "some", "same", "being", "here"}


class DraftError(ValueError):
    """A draft broke one of the rules in the module docstring."""


# ---------------------------------------------------------------------------------------------------- specs
@dataclass(frozen=True)
class Field:
    name: str
    label: str
    type: str = "text"                    # text, textarea, email, date, checkbox, select, radio
    options: tuple[str, ...] = ()
    placeholder: str = ""
    default: str | bool | None = None     # must stay None: check() refuses a default value


@dataclass(frozen=True)
class FormLink:
    """An official form that helps with one element (not the step): its id in fixtures/forms/forms.json, its
    match ("partial" or "related") and what the form is, in plain words."""
    id: str
    match: str
    role: str


@dataclass(frozen=True)
class Element:
    id: str
    level: str                            # a key of LEVELS
    label: str
    section: str                          # the reference the statute loader understands ("2.2-3704", "Cal. BPC § 480")
    subsection: str | None                # "B", "a.1", "f.3.D"; None when the words sit outside a lettered subsection
    quote: str                            # the exact words the element rests on
    fields: tuple[Field, ...] = ()
    letter: str | None = None             # the letter's sentence; {field}, {quote} and {cite} are filled in, and
                                          # a [segment] is kept only when every field in it is filled in
    when: str | None = None               # field names joined by "|": the sentence is used when any is filled in
    help: str | None = None               # plain words shown on the form; never a new requirement
    condition: str | None = None          # when the element applies at all
    forms: tuple[FormLink, ...] = ()      # official forms in fixtures/forms/forms.json that help with this element
    cite_in_letter: bool = True           # print the citation after the letter's sentence


@dataclass(frozen=True)
class Spec:
    id: str
    state: str
    question: str
    step: str                             # the curated step id the draft serves
    title: str
    summary: str
    sections: tuple[str, ...]
    citations: dict                       # section reference -> citation as printed ("Va. Code § 2.2-3704")
    elements: tuple[Element, ...]
    layout: tuple[str, ...]               # element ids and @subject, @salutation, @closing, in letter order
    subject: str
    salutation: str
    closing: str
    parties: dict = field(default_factory=dict)   # "person" and "other": the words the statute uses for each side
    scope: str = ""
    related: tuple[tuple[str, str, str], ...] = ()   # (state, question, heading): official forms to list too
    extra: dict = field(default_factory=dict)


VA = "2.2-3704"
VA_FOIA = Spec(
    id="va-foia-request",
    state="va", question="records", step="submit_request",
    title="Request for public records (Virginia Freedom of Information Act)",
    summary="A request to a Virginia public body for public records under Va. Code § 2.2-3704. The statute sets "
            "no form. It says what a request identifies, what the custodian may ask for, and how and when the "
            "public body answers.",
    sections=(VA,),
    citations={VA: "Va. Code § 2.2-3704"},
    parties={"person": ("requester", "request"), "other": ("public bodies", "public body", "custodian")},
    subject="Request for public records",
    salutation="Dear Records Custodian:",
    closing="Sincerely,\n{name}",
    scope="For records held by a Virginia public body. Section 2.2-3704(A) opens public records to citizens of "
          "the Commonwealth and to representatives of newspapers, magazines and radio and television stations "
          "named there.",
    layout=("date", "custodian", "@subject", "@salutation", "reference", "records", "access", "medium", "email",
            "cost_estimate", "name_address", "response_duty", "@closing"),
    elements=(
        Element("date", "context", "Date you send it", VA, "B",
                "within five working days of receiving a request",
                fields=(Field("date_sent", "Date you send it", "date"),),
                letter="{date_sent}", cite_in_letter=False,
                help="The five working days run from when the public body receives the request, so keep a "
                     "record of when and how you sent it."),
        Element("custodian", "context", "The public body that holds the records", VA, "B",
                "Any public body that is subject to this chapter and that is the custodian of the requested records",
                fields=(Field("custodian", "Public body (and office, if you know it)",
                              placeholder="e.g. County of Albemarle, Department of Finance"),
                        Field("custodian_address", "The public body's postal or email address (optional)",
                              "textarea")),
                letter="{custodian}\n{custodian_address}", cite_in_letter=False,
                help="Send the request to the public body that holds the records. The statute does not ask for "
                     "its address; it is there so the letter can be sent."),
        Element("reference", "right", "Referring to the law", VA, "B",
                "The request need not make reference to this chapter in order to invoke the provisions of this "
                "chapter or to impose the time limits for response by a public body.",
                fields=(Field("refer_to_law", "Refer to the law in the letter", "checkbox"),),
                letter="This is a request for public records under Va. Code § 2.2-3704.", when="refer_to_law",
                cite_in_letter=False,
                help="Referring to the law is optional: the request counts, and the time limits run, without it."),
        Element("records", "required", "The records you are asking for", VA, "B",
                "A request for public records shall identify the requested records with reasonable specificity.",
                fields=(Field("records", "Records you are asking for", "textarea",
                              placeholder="e.g. the contract between the county and the waste hauler in force in "
                                          "2026, with its amendments"),),
                letter="I ask for the following records:\n{records}",
                help="Describe the records as specifically as you reasonably can, for example by subject, date "
                     "range, office or type of document."),
        Element("access", "right", "Inspect or receive copies", VA, "A",
                "Access to such records shall be provided by the custodian in accordance with this chapter by "
                "inspection or by providing copies of the requested records, at the option of the requester.",
                fields=(Field("access", "I would like to", "radio",
                              options=("inspect the records", "receive copies of the records")),),
                letter="I would like to {access}.",
                help="You choose whether to inspect the records or receive copies. Nothing is chosen for you."),
        Element("medium", "right", "Medium for records kept in a database", VA, "G",
                "Public bodies shall produce nonexempt records maintained in an electronic database in any "
                "tangible medium identified by the requester, including, where the public body has the "
                "capability, the option of posting the records on a website or delivering the records through an "
                "electronic mail address provided by the requester, if that medium is used by the public body in "
                "the regular course of business.",
                fields=(Field("medium", "Medium (optional)", placeholder="e.g. a CSV file by email"),),
                letter="For any of these records kept in an electronic database, I ask for them in this medium: "
                       "{medium}.", when="medium",
                help="Applies to records kept in an electronic database, in a medium the public body uses in the "
                     "regular course of business."),
        Element("email", "right", "Email address for records kept in a database", VA, "G",
                "where the public body has the capability, the option of posting the records on a website or "
                "delivering the records through an electronic mail address provided by the requester, if that "
                "medium is used by the public body in the regular course of business",
                fields=(Field("email_address", "Email address (optional)", "email"),),
                letter="For any of these records kept in an electronic database, you can deliver them to this email "
                       "address: {email_address}.", when="email_address",
                help="Section 2.2-3704(G) provides for delivery to an email address the requester gives, for "
                     "records kept in an electronic database, where the public body has the capability and uses "
                     "that medium in the regular course of business. Leave this blank if you prefer another way."),
        Element("cost_estimate", "right", "Cost estimate", VA, "F",
                "The public body shall provide the requester with a cost estimate if requested.",
                fields=(Field("cost_estimate", "Ask for a cost estimate first", "checkbox"),),
                letter="I ask for a cost estimate in advance of the supplying of the records.", when="cost_estimate",
                help="An estimate tells you the cost before the records are supplied. Asking for one also pauses "
                     "the response time from notice of the estimate until you answer it, and a request whose "
                     "estimate gets no answer within 30 days is treated as withdrawn (see the notes)."),
        Element("name_address", "if_asked", "Your name and legal address", VA, "A",
                "The custodian may require the requester to provide his name and legal address.",
                fields=(Field("name", "Your name"), Field("legal_address", "Your legal address", "textarea")),
                letter="My name and legal address:\n{name}\n{legal_address}", when="name|legal_address",
                cite_in_letter=False,
                help="The custodian may require your name and legal address. You can give them now or wait to "
                     "be asked."),
        Element("response_duty", "duty", "When the public body responds", VA, "B",
                "shall promptly, but in all cases within five working days of receiving a request, provide the "
                "requested records to the requester or make one of the following responses in writing",
                letter="Under {cite}, the public body “{quote}” (the responses are listed in that subsection).",
                cite_in_letter=False,
                help="The written responses are: withheld in full; provided in part and withheld in part; not found "
                     "or not existing; or not practically possible to provide within the five-work-day period (see "
                     "“More time” in the notes)."),
        Element("extension", "notice", "More time", VA, "B.4",
                "If the response is made within five working days, the public body shall have an additional seven "
                "work days or, in the case of a request for criminal investigative files pursuant to § 2.2-3706.1 , "
                "60 work days in which to provide one of the four preceding responses.",
                help="If the public body answers within five working days that it is not practically possible to "
                     "respond in time, it gets seven more work days, or 60 work days for a request for criminal "
                     "investigative files under § 2.2-3706.1, to give one of the other responses."),
        Element("court_extension", "notice", "A court can give more time", VA, "C",
                "Any public body may petition the appropriate court for additional time to respond to a request for "
                "records when the request is for an extraordinary volume of records or requires an extraordinarily "
                "lengthy search, and a response by the public body within the time required by this chapter will "
                "prevent the public body from meeting its operational responsibilities. Before proceeding with the "
                "petition, however, the public body shall make reasonable efforts to reach an agreement with the "
                "requester concerning the production of the records requested.",
                help="For an extraordinary volume of records or an extraordinarily lengthy search, the public body "
                     "may ask a court for more time. Before it does, it makes reasonable efforts to agree with you "
                     "on how the records are produced."),
        Element("deemed_denial", "notice", "No answer", VA, "E",
                "Failure to respond to a request for records shall be deemed a denial of the request and shall "
                "constitute a violation of this chapter.",
                help="Silence counts as a denial."),
        Element("charges", "notice", "Charges", VA, "F",
                "a public body may make reasonable charges not to exceed its actual cost incurred in accessing, "
                "duplicating, supplying, or searching for the requested records",
                help="Charges are capped at the public body's actual cost."),
        Element("search_notice", "duty", "Notice of charges before a search", VA, "F",
                "Prior to conducting a search for records, the public body shall notify the requester in writing "
                "that the public body may make reasonable charges not to exceed its actual cost incurred in "
                "accessing, duplicating, supplying, or searching for requested records and inquire of the "
                "requester whether he would like to request a cost estimate in advance of the supplying of the "
                "requested records.",
                help="Before it searches, the public body tells you in writing that it may charge its actual cost, "
                     "and asks whether you want a cost estimate first."),
        Element("estimate_pause", "notice", "The clock pauses for the estimate", VA, "F",
                "The period within which the public body shall respond under this section shall be tolled for the "
                "amount of time that elapses between notice of the cost estimate and the response of the "
                "requester.",
                help="The response time stops between the estimate and your answer to it."),
        Element("estimate_lapse", "notice", "Answer the estimate within 30 days", VA, "F",
                "If the public body receives no response from the requester within 30 days of sending the cost "
                "estimate, the request shall be deemed to be withdrawn.",
                help="If you do not answer a cost estimate within 30 days, the request is treated as withdrawn."),
        Element("deposit", "notice", "Deposit when charges are likely to exceed $200", VA, "H",
                "In any case where a public body determines in advance that charges for producing the requested "
                "records are likely to exceed $200, the public body may, before continuing to process the request, "
                "require the requester to pay a deposit not to exceed the amount of the advance determination. The "
                "deposit shall be credited toward the final cost of supplying the requested records. The period "
                "within which the public body shall respond under this section shall be tolled for the amount of "
                "time that elapses between notice of the advance determination and the response of the requester.",
                help="If the public body determines in advance that charges are likely to exceed $200, it may ask "
                     "for a deposit, up to the amount of that advance determination, before it continues to process "
                     "the request. The deposit counts toward the final cost, and the response time pauses from "
                     "notice of the advance determination until you answer."),
        Element("unpaid", "notice", "Earlier unpaid bills", VA, "I",
                "Before processing a request for records, a public body may require the requester to pay any "
                "amounts owed to the public body for previous requests for records that remain unpaid 30 days or "
                "more after billing.",
                help="Old unpaid charges for earlier requests can hold up a new one."),
        Element("no_new_record", "notice", "Existing records only", VA, "D",
                "no public body shall be required to create a new record if the record does not already exist. "
                "However, a public body may abstract or summarize information under such terms and conditions as "
                "agreed between the requester and the public body.",
                help="Ask for records that exist. A summary or abstract is a matter of agreement with the public "
                     "body."),
    ),
)

BPC = {n: f"Cal. BPC § {n}" for n in ("476", "480", "481", "482", "485", "486", "487")}
_BCIA_ROLE = ("What it is: a request to the California Department of Justice for a copy of your own criminal "
              "record (record review by Live Scan). It is not a form for sending evidence.")
CA_HEARING = Spec(
    id="ca-bpc-485-hearing-request",
    state="ca", question="license_conviction", step="request_hearing",
    title="Request for a hearing on a licence denial based on a conviction (Cal. Bus. & Prof. Code §§ 485, 480, "
          "482)",
    summary="Sections 480 and 482 set the rules a California licensing board follows before it denies a "
            "licence because of a conviction. They do not create a request of their own. The request the law "
            "provides is the written request for a hearing under § 485(b), made within 60 days after the notice "
            "of denial is served. In that request the applicant can rely on §§ 480 and 482 and send evidence of "
            "rehabilitation under § 481(c).",
    sections=tuple(BPC.values()),
    citations={BPC[n]: f"Cal. Bus. & Prof. Code § {n}" for n in BPC},
    parties={"person": ("applicant", "request"), "other": ("boards", "board")},
    subject="Request for hearing on the denial of my license application",
    salutation="Dear Board:",
    closing="Sincerely,\n{name}",
    scope="For a licence regulated by the Business and Professions Code, after a board serves a notice of denial "
          "under § 485(b). Not for licences under the State Bar Act (Chapter 4 of Division 3), the Alcoholic "
          "Beverage Control Act (Division 9) or the Gambling Control Act (Chapter 5 of Division 8): § 476(a) says "
          "Division 1.5, which holds §§ 480 to 487, does not apply to them, so this draft does not apply to them "
          "either. Section 480(i) leaves the licensing authority of the State Athletic Commission, the Bureau for "
          "Private Postsecondary Education and the California Horse Racing Board unchanged. Some practice acts "
          "and divisions have conviction rules of their own. The Board of Pharmacy may deny “Notwithstanding "
          "Section 480” (§ 4202.6). The Board of Accountancy has grounds “In addition to” those of § 480, with no "
          "seven-year limit for some financial felonies (§ 5100.2). Three sections direct a board to deny a "
          "licence to a person subject to sex-offender registration under Penal Code § 290, with exceptions "
          "(§§ 1687, 1958.1, 2660.5). Section 4989.24, in the Educational Psychologist Practice Act, bars a "
          "licence for a conviction, in California, in another state or in a territory of the United States, of a "
          "crime involving sexual abuse of children, or for a person subject to that registration or the "
          "equivalent in another state or territory, and its subdivision (b) applies the conditions for denial in "
          "§ 480 to such a denial. For a state cannabis licence under Division 10, § 26057(b)(2) lets the "
          "Department of Cannabis Control deny "
          "for conduct that is a ground for denial under Chapter 2 of Division 1.5 (commencing with § 480), "
          "“except as otherwise specified” in § 26057 and § 26059. Read the practice act or division that governs "
          "your licence. This draft is not for licences under other codes.",
    related=(("ca", "record_sealing",
              "Official California forms for clearing a record. CR-180 is the petition for the Penal Code "
              "§ 1203.4 dismissals that § 480(c) names; BCIA 8016RR requests a copy of your own record"),),
    layout=("date", "applicant", "board", "@subject", "application", "service_date", "@salutation",
            "hearing_request", "dismissed", "dismissal_proof", "rehabilitated", "sentence_completed",
            "seven_years", "arrest_only", "evidence", "@closing"),
    elements=(
        Element("date", "context", "Date you send it", BPC["485"], "b",
                "if written request for hearing is made within 60 days after service of the notice of denial",
                fields=(Field("date_sent", "Date you send it", "date"),),
                letter="{date_sent}", cite_in_letter=False,
                help="The 60 days for the request run from service of the notice of denial, so keep a record of "
                     "when and how you sent it."),
        Element("applicant", "context", "You", BPC["485"], None,
                "by registered mail addressed to the applicant at the latest address filed by the applicant in "
                "writing with the board in his or her application or otherwise",
                fields=(Field("name", "Your name"), Field("address", "Your current address", "textarea")),
                letter="{name}\n{address}", cite_in_letter=False,
                help="The law lets the board serve the notice of denial by registered mail at the latest address "
                     "you filed with it in writing. This letter gives your current address in writing."),
        Element("board", "context", "The board that denied the licence", BPC["485"], None,
                "Upon denial of an application for a license under this chapter or Section 496, the board shall do "
                "either of the following",
                fields=(Field("board", "Board, bureau or other agency that denied the licence"),
                        Field("board_address", "Its address, from the notice of denial (optional)", "textarea")),
                letter="{board}\n{board_address}", cite_in_letter=False,
                help="Send the request to the board that denied the application, at the address on its notice. "
                     "The statute does not ask for the address; it is there so the letter can be sent."),
        Element("application", "context", "The application that was denied", BPC["485"], "b",
                "Notify the applicant that the application is denied, stating (1) the reason for the denial",
                fields=(Field("application_licence", "Licence you applied for"),
                        Field("application_no", "Application or reference number on the notice (optional)")),
                letter="Re: my application for {application_licence}[ (reference {application_no})]",
                cite_in_letter=False,
                help="The notice of denial states the reason for the denial. Copy the licence and any reference "
                     "number from it."),
        Element("service_date", "context", "When the notice was mailed or served", BPC["485"], None,
                "Service by mail is complete on the date of mailing.",
                fields=(Field("notice_date", "Date the notice of denial was mailed or served (optional)", "date"),),
                letter="The notice of denial was mailed or served on {notice_date}.", when="notice_date",
                cite_in_letter=False,
                help="The 60 days run from service. When the notice is mailed, service is complete on the date of "
                     "mailing, not the day it arrives."),
        Element("hearing_request", "required", "Ask for a hearing, in writing", BPC["485"], "b",
                "Unless written request for hearing is made within the 60-day period, the applicant’s right to a "
                "hearing is deemed waived.",
                letter="I request a hearing on the denial of my application.",
                help="Send the request in writing within 60 days after service of the notice of denial. Without a "
                     "timely written request the right to a hearing is waived."),
        Element("dismissed", "right", "The conviction was dismissed", BPC["480"], "c",
                "a person shall not be denied a license on the basis of any conviction, or on the basis of the "
                "acts underlying the conviction, that has been dismissed pursuant to Section 1203.4, 1203.4a, "
                "1203.41, 1203.42, or 1203.425 of the Penal Code, or a comparable dismissal or expungement",
                fields=(Field("dismissed", "The conviction was dismissed", "checkbox"),
                        Field("dismissal_detail", "Penal Code section, court and case number",
                              placeholder="e.g. Penal Code § 1203.4, Superior Court of ... County, case no. ...")),
                letter="The conviction was dismissed[ ({dismissal_detail})]. Under {cite}, “{quote}.”",
                when="dismissed",
                help="The Judicial Council's petition for a dismissal under Penal Code § 1203.4, 1203.4a, 1203.41 "
                     "or 1203.42 is CR-180, and CR-181 is the order. They are court forms for getting the "
                     "dismissal, not forms for this letter.",
                forms=(FormLink("ca-jc-cr-180", "related",
                                "What it is: the Judicial Council's petition to the court for a dismissal under "
                                "Penal Code § 1203.4, 1203.4a, 1203.41 or 1203.42."),
                       FormLink("ca-jc-cr-181", "related",
                                "What it is: the Judicial Council's order for that dismissal, filed with the "
                                "petition."))),
        Element("dismissal_proof", "required", "Proof of the dismissal", BPC["480"], "c",
                "An applicant who has a conviction that has been dismissed pursuant to Section 1203.4, 1203.4a, "
                "1203.41, or 1203.42 of the Penal Code shall provide proof of the dismissal if it is not reflected "
                "on the report furnished by the Department of Justice.",
                fields=(Field("proof_enclosed", "I enclose proof of the dismissal", "checkbox"),),
                letter="I enclose proof of the dismissal.", when="proof_enclosed",
                condition="Only for a dismissal under Penal Code § 1203.4, 1203.4a, 1203.41 or 1203.42 that is not "
                          "on the Department of Justice report.",
                help="The statute does not say what counts as proof."),
        Element("rehabilitated", "right", "Certificate of rehabilitation, pardon or rehabilitation",
                BPC["480"], "b",
                "a person shall not be denied a license on the basis that the person has been convicted of a "
                "crime, or on the basis of acts underlying a conviction for a crime, if that person has obtained a "
                "certificate of rehabilitation under Chapter 3.5 (commencing with Section 4852.01) of Title 6 of "
                "Part 3 of the Penal Code, has been granted clemency or a pardon by a state or federal executive, "
                "or has made a showing of rehabilitation pursuant to Section 482",
                fields=(Field("rehab_basis", "Which applies", "select",
                              options=("", "I have obtained a certificate of rehabilitation",
                                       "I have been granted clemency or a pardon by a state or federal executive",
                                       "I have made a showing of rehabilitation under Section 482")),),
                letter="{rehab_basis}. Under {cite}, “{quote}.”", when="rehab_basis"),
        Element("sentence_completed", "right", "Sentence completed without a violation", BPC["482"], "b.1",
                "Each board shall consider whether an applicant or licensee has made a showing of rehabilitation if "
                "either of the following are met: (1) The applicant or licensee has completed the criminal sentence "
                "at issue without a violation of parole or probation.",
                fields=(Field("sentence_completed",
                              "I completed the sentence without a violation of parole or probation", "checkbox"),),
                letter="I completed the criminal sentence at issue without a violation of parole or probation, and "
                       "I ask the board to consider whether I have made a showing of rehabilitation ({cite}: "
                       "“{quote}”).", when="sentence_completed",
                help="When this is true, § 482(b) directs the board to consider whether you showed rehabilitation; "
                     "it does not direct the board to find that you did."),
        Element("seven_years", "right", "The seven-year condition", BPC["480"], "a.1",
                "The applicant has been convicted of a crime within the preceding seven years from the date of "
                "application that is substantially related to the qualifications, functions, or duties of the "
                "business or profession for which the application is made, regardless of whether the applicant was "
                "incarcerated for that crime, or the applicant has been convicted of a crime that is substantially "
                "related to the qualifications, functions, or duties of the business or profession for which the "
                "application is made and for which the applicant is presently incarcerated or for which the "
                "applicant was released from incarceration within the preceding seven years from the date of "
                "application",
                fields=(Field("seven_years_facts", "Your facts on the seven-year condition (optional)", "textarea",
                              placeholder="e.g. the date of the conviction; whether you were incarcerated for it "
                                          "and, if so, the date of your release; the date you applied"),),
                letter="Under § 480(a), a board may deny a license on the ground of a conviction or of formal "
                       "discipline only if one of two conditions is met. The first, in {cite}, subject to the "
                       "exceptions in its subparagraphs (A) and (B), reads: “{quote}.” My facts on this condition: "
                       "{seven_years_facts}",
                when="seven_years_facts",
                help="Give your own facts. The draft does not say whether the condition is met. The condition has "
                     "two branches: a conviction within the seven years, or a conviction for which the applicant is "
                     "incarcerated now or was released from incarceration within the seven years. The seven-year "
                     "limit does not apply in the situations in § 480(a)(1)(A) and (B) (see the notes), and some "
                     "practice acts have rules of their own (see the scope above)."),
        Element("arrest_only", "right", "An arrest without a conviction", BPC["480"], "d",
                "a board shall not deny a license on the basis of an arrest that resulted in a disposition other "
                "than a conviction, including an arrest that resulted in an infraction, citation, or a juvenile "
                "adjudication",
                fields=(Field("arrest_only", "Part of the denial rests on an arrest that did not end in a "
                                             "conviction", "checkbox"),),
                letter="Part of the denial rests on an arrest that did not result in a conviction. Under {cite}, "
                       "“{quote}.”", when="arrest_only"),
        Element("evidence", "right", "Evidence of rehabilitation", BPC["481"], "c",
                "A board shall not deny a license based in whole or in part on a conviction without considering "
                "evidence of rehabilitation submitted by an applicant pursuant to any process established in the "
                "practice act or regulations of the particular board and as directed by Section 482.",
                fields=(Field("evidence_list", "Evidence you enclose (optional)", "textarea",
                              placeholder="e.g. certificate of completion of a training programme; letter from an "
                                          "employer"),),
                letter="I enclose the following evidence of rehabilitation and ask the board to consider it:\n"
                       "{evidence_list}", when="evidence_list",
                help="Each board sets its own process for evidence, in its practice act or regulations. Check the "
                     "board's rules. There is no statewide evidence form; the form linked here is about your own "
                     "record.",
                forms=(FormLink("ca-doj-bcia-8016rr", "related", _BCIA_ROLE),)),
        Element("excluded_licences", "notice", "Licences outside this draft", BPC["476"], "a",
                "Except as provided in subdivision (b), nothing in this division shall apply to the licensure or "
                "registration of persons pursuant to Chapter 4 (commencing with Section 6000) of Division 3, or "
                "pursuant to Division 9 (commencing with Section 23000) or pursuant to Chapter 5 (commencing with "
                "Section 19800) of Division 8.",
                help="Division 1.5 of the Business and Professions Code, which holds §§ 480 to 487, does not apply "
                     "to licences under the State Bar Act (Chapter 4 of Division 3), the Alcoholic Beverage Control "
                     "Act (Division 9) or the Gambling Control Act (Chapter 5 of Division 8). This draft does not "
                     "apply to those licences. Under subdivision (b), § 494.5 still applies to them."),
        Element("scope", "notice", "Three bodies keep their own rules", BPC["480"], "i",
                "This section does not in any way modify or otherwise affect the existing authority of the "
                "following entities in regard to licensure: (1) The State Athletic Commission. (2) The Bureau for "
                "Private Postsecondary Education. (3) The California Horse Racing Board.",
                help="Section 480 leaves the licensing authority of these three bodies unchanged."),
        Element("statement_of_issues", "notice", "If the board served a statement of issues instead",
                BPC["485"], "a",
                "File and serve a statement of issues in accordance with Chapter 5 (commencing with Section 11500) "
                "of Part 1 of Division 3 of Title 2 of the Government Code.",
                help="This draft is for a notice of denial under § 485(b). If the board instead filed and served a "
                     "statement of issues under § 485(a), the Government Code procedure for that applies, and this "
                     "letter may not be the right step."),
        Element("only_if", "notice", "When a board may deny for a conviction", BPC["480"], "a",
                "a board may deny a license regulated by this code on the grounds that the applicant has been "
                "convicted of a crime or has been subject to formal discipline only if either of the following "
                "conditions are met",
                help="Section 480(a) lists two conditions. (1) A substantially related conviction within the seven "
                     "years before the application, or a substantially related conviction for which the applicant "
                     "is incarcerated now or was released from incarceration within those seven years; "
                     "subparagraphs (A) and (B) lift the seven-year limit for some crimes. (2) Formal discipline by "
                     "a licensing board in or outside California within those seven years, for substantially "
                     "related professional misconduct that would have been cause for discipline before the board. "
                     "Paragraph (2) has two qualifiers. Discipline within the seven years is not a basis for denial "
                     "if it was based on a conviction dismissed under Penal Code § 1203.4, 1203.4a, 1203.41, 1203.42 "
                     "or 1203.425, or a comparable dismissal or expungement. Discipline older than seven years can "
                     "be a ground only if it was for conduct that, by a California physician and surgeon, would "
                     "have been sexual abuse, misconduct or relations with a patient under § 726, or sexual "
                     "exploitation under § 729(a). Some practice acts have rules of their own (see the scope "
                     "above)."),
        Element("seven_year_exceptions", "notice", "Exceptions to the seven-year limit", BPC["480"], "a.1",
                "However, the preceding seven-year limitation shall not apply in either of the following "
                "situations: (A) The applicant was convicted of a serious felony, as defined in Section 1192.7 of "
                "the Penal Code or a crime for which registration is required pursuant to paragraph (2) or (3) of "
                "subdivision (d) of Section 290 of the Penal Code. (B) The applicant was convicted of a financial "
                "crime currently classified as a felony that is directly and adversely related to the fiduciary "
                "qualifications, functions, or duties of the business or profession for which the application is "
                "made, pursuant to regulations adopted by the board, and for which the applicant is seeking "
                "licensure under any of the following: (i) Chapter 6 (commencing with Section 6500) of Division 3. "
                "(ii) Chapter 9 (commencing with Section 7000) of Division 3. (iii) Chapter 11.3 (commencing with "
                "Section 7512) of Division 3. (iv) Licensure as a funeral director or cemetery manager under "
                "Chapter 12 (commencing with Section 7600) of Division 3. (v) Division 4 (commencing with Section "
                "10000).",
                help="The seven-year limit does not apply to (A) a serious felony under Penal Code § 1192.7 or a "
                     "crime that carries sex-offender registration under Penal Code § 290(d)(2) or (3), or (B) for "
                     "the licences listed in (i) to (v), a felony financial crime directly and adversely related to "
                     "the licence's fiduciary qualifications, functions or duties, under the board's regulations."),
        Element("formal_discipline", "notice", "Formal discipline as a ground for denial", BPC["480"], "a.2",
                "The applicant has been subjected to formal discipline by a licensing board in or outside "
                "California within the preceding seven years from the date of application based on professional "
                "misconduct that would have been cause for discipline before the board for which the present "
                "application is made and that is substantially related to the qualifications, functions, or "
                "duties of the business or profession for which the present application is made. However, prior "
                "disciplinary action by a licensing board within the preceding seven years shall not be the basis "
                "for denial of a license if the basis for that disciplinary action was a conviction that has been "
                "dismissed pursuant to Section 1203.4, 1203.4a, 1203.41, 1203.42, or 1203.425 of the Penal Code or "
                "a comparable dismissal or expungement. Formal discipline that occurred earlier than seven years "
                "preceding the date of application may be grounds for denial of a license only if the formal "
                "discipline was for conduct that, if committed in this state by a physician and surgeon licensed "
                "pursuant to Chapter 5 (commencing with Section 2000) of Division 2, would have constituted an act "
                "of sexual abuse, misconduct, or relations with a patient pursuant to Section 726 or sexual "
                "exploitation as defined in subdivision (a) of Section 729.",
                help="The second condition of § 480(a), quoted in full with both qualifiers: discipline based on a "
                     "dismissed conviction is not a basis for denial, and discipline older than seven years counts "
                     "only for the conduct named in the last sentence."),
        Element("substantial_relation", "notice", "What the board's criteria for a substantially related crime "
                                                "include", BPC["481"], "b",
                "Criteria for determining whether a crime is substantially related to the qualifications, "
                "functions, or duties of the business or profession a board regulates shall include all of the "
                "following: (1) The nature and gravity of the offense. (2) The number of years elapsed since the "
                "date of the offense. (3) The nature and duties of the profession in which the applicant seeks "
                "licensure or in which the licensee is licensed.",
                help="The board's criteria for whether a crime is substantially related to the licence include the "
                     "nature and gravity of the offense, the years since the offense, and the nature and duties of "
                     "the profession."),
        Element("notice_contents", "duty", "What the board shall put in the notice of denial", BPC["480"], "f.3",
                "If a board decides to deny an application for licensure based solely or in part on the applicant’s "
                "conviction history, the board shall notify the applicant in writing of all of the following: (A) "
                "The denial or disqualification of licensure. (B) Any existing procedure the board has for the "
                "applicant to challenge the decision or to request reconsideration. (C) That the applicant has the "
                "right to appeal the board’s decision.",
                help="Read the notice for the board's own challenge or reconsideration procedure."),
        Element("record_copy", "notice", "A copy of your own conviction history", BPC["480"], "f.3.D",
                "The processes for the applicant to request a copy of the applicant’s complete conviction history "
                "and question the accuracy or completeness of the record pursuant to Sections 11122 to 11127 of "
                "the Penal Code.",
                help="Section 480(f)(3)(D) puts this in the notice of denial too. The Department of Justice's form "
                     "for requesting a copy of your own record is BCIA 8016RR.",
                forms=(FormLink("ca-doj-bcia-8016rr", "related", _BCIA_ROLE),)),
        Element("hearing_within", "duty", "When the board holds the hearing", BPC["487"], None,
                "If a hearing is requested by the applicant, the board shall conduct such hearing within 90 days "
                "from the date the hearing is requested unless the applicant shall request or agree in writing to "
                "a postponement or continuance of the hearing. Notwithstanding the above, the Office of "
                "Administrative Hearings may order, or on a showing of good cause, grant a request for, up to 45 "
                "additional days within which to conduct a hearing, except in cases involving alleged examination "
                "or licensing fraud, in which cases the period may be up to 180 days. In no case shall more than "
                "two such orders be made or requests be granted.",
                help="The 90 days run from the date of your request, unless you ask for or agree in writing to a "
                     "postponement or continuance. The Office of Administrative Hearings may add up to 45 days (up "
                     "to 180 in cases of alleged examination or licensing fraud), with no more than two such orders "
                     "or grants."),
        Element("reapply", "notice", "Reapplying", BPC["486"], "a",
                "The earliest date on which the applicant may reapply for a license which shall be one year from "
                "the effective date of the decision, or service of the notice under subdivision (b) of Section 485, "
                "unless the board prescribes an earlier date or a later date is prescribed by another statute.",
                help="The decision or notice states the earliest date you may reapply."),
        Element("reapply_evidence", "notice", "Evidence when you reapply", BPC["486"], "b",
                "That all competent evidence of rehabilitation presented will be considered upon a reapplication.",
                help="The decision or notice of denial also tells you that all competent evidence of rehabilitation "
                     "presented will be considered if you reapply."),
        Element("rehab_criteria", "duty", "The board serves its rehabilitation criteria with the notice",
                BPC["486"], None,
                "Along with the decision, or the notice under subdivision (b) of Section 485, the board shall serve "
                "a copy of the criteria relating to rehabilitation formulated under Section 482.",
                help="With the decision or the notice of denial, the board serves a copy of its criteria for "
                     "evaluating rehabilitation (§ 482)."),
    ),
)

SPECS: dict[str, Spec] = {s.id: s for s in (VA_FOIA, CA_HEARING)}


def spec_for_step(state: str, question: str, step: str) -> Spec | None:
    return next((s for s in SPECS.values() if (s.state, s.question, s.step) == (state, question, step)), None)


# ------------------------------------------------------------------------------------------------ checking
def norm(text: str) -> str:
    """Whitespace and curly quotation marks normalised; nothing else."""
    return re.sub(r"\s+", " ", (text or "").translate(_QUOTES)).strip()


def _style(paras: list[str]) -> str | None:
    """'paren' for sections lettered (a), (b) ...; 'dot' for A., B. ...; None for a section with no letters."""
    for n in paras:
        if n.startswith("(a) "):
            return "paren"
        if n.startswith("A. "):
            return "dot"
    return None


def _trunc(levels: tuple) -> tuple[str, ...]:
    out = []
    for x in levels:
        if x is None:
            break
        out.append(x)
    return tuple(out)


def _layout(text: str) -> tuple[str, list[tuple[int, int, tuple[str, ...]]]]:
    """The normalised text and, for each paragraph, its span and its subsection path, e.g. ("f", "3", "D").

    Top-level letters count only in sequence (a, b, c ... or A, B, C ...), so a nested (i) or (v) is not taken
    for one. Paths go four levels deep in the (a)(1)(A)(i) style and three in the A.1.a. style. In an (a)-style
    section, an unlettered paragraph before the first subdivision or after the last is the section's own text
    (path ()); one between two subdivisions could be either the section's text or the end of the subdivision above,
    so it gets the path ("?",), which no citation matches. In an A.-style section an unlettered paragraph continues
    the subsection above it."""
    paras = [n for n in (norm(p) for p in re.split(r"\n+", text or "")) if n]
    style = _style(paras)
    rx = _MARK_PAREN if style == "paren" else _MARK_DOT if style == "dot" else None
    parts: list[str] = []
    spans: list[tuple[int, int, tuple[str, ...]]] = []
    top = l2 = l3 = l4 = None
    pos = 0
    for n in paras:
        rest, marked = n, False
        while rx is not None:
            m = rx.match(rest)
            if not m:
                break
            tok = m.group(1)
            case_ok = tok.isupper() if style == "dot" else tok.islower()
            if len(tok) == 1 and tok.isalpha() and case_ok and (
                    (top is None and tok in "aA") or (top is not None and ord(tok) == ord(top) + 1)):
                top, l2, l3, l4 = tok, None, None, None
            elif tok.isdigit() and top is not None:
                l2, l3, l4 = tok, None, None
            elif style == "paren" and tok.isupper() and l2 is not None:
                l3, l4 = tok, None
            elif style == "paren" and tok in _ROMAN and l3 is not None:
                l4 = tok
            elif style == "dot" and len(tok) == 1 and tok.islower() and l2 is not None:
                l3 = tok
            else:
                break
            marked = True
            rest = rest[m.end():]
        if marked:
            path = _trunc((top, l2, l3, l4))
        elif style == "dot" and top is not None:
            path = (top,)                     # continues the subsection above
        else:
            path = ()                         # opening words, or the section's closing text
        if parts:
            pos += 1
        spans.append((pos, pos + len(n), path))
        parts.append(n)
        pos += len(n)
    if style == "paren":
        lettered = [i for i, (_, _, p) in enumerate(spans) if p]
        if lettered:
            spans = [(s, e, ("?",) if p == () and lettered[0] < i < lettered[-1] else p)
                     for i, (s, e, p) in enumerate(spans)]
    return " ".join(parts), spans


def _fits(paths: list[tuple[str, ...]], want: tuple[str, ...]) -> bool:
    if not want:
        return bool(paths) and all(p == () for p in paths)
    n = len(want)
    return any(p[:n] == want for p in paths) and all(
        p and p[:min(len(p), n)] == want[:min(len(p), n)] for p in paths)


def _hits(full: str, q: str) -> list[int]:
    return [m.start() for m in re.finditer(re.escape(q), full)]


def locate(text: str, quote: str, subsection: str | None) -> str | None:
    """None when the quote is in the text and under the cited subsection, to the depth cited ("f.3.D"); with no
    subsection, when it is in the section's own unlettered text (see :func:`_layout`). Otherwise what is wrong."""
    full, spans = _layout(text)
    q = norm(quote)
    if not q:
        return "empty quote"
    hits = _hits(full, q)
    if not hits:
        return "quote not found in the section text"
    want = tuple(subsection.split(".")) if subsection else ()
    covered = []
    for h in hits:
        paths = [p for s, e, p in spans if s < h + len(q) and e > h]
        if _fits(paths, want):
            return None
        covered += paths
    if ("?",) in covered:
        return ("quote found, but in an unlettered paragraph between two subdivisions, which may be the section's "
                "own text or the end of the subdivision above; no citation is accepted for it")
    if want:
        return f"quote found, but not under subsection {''.join(f'({x})' for x in want)}"
    return "quote found, but inside a lettered subsection, not in the section's unlettered text"


def _clause(full: str, pos: int) -> tuple[int, int]:
    """The span of the clause around pos. The search runs over the whole text (not up to pos), so that the
    look-ahead also sees a clause that starts at pos itself ("... denial. Unless written request ...")."""
    start = 0
    for m in _CLAUSE_END.finditer(full):
        if m.end() > pos:
            break
        start = m.end()
    m = _CLAUSE_END.search(full, pos)
    return start, (m.start() if m else len(full))


def _parties(spec: Spec, s: str) -> list[tuple[int, int, str]]:
    """(start, end, role) of each party word in s, by the spec's parties."""
    terms = sorted(((t, role) for role, ts in spec.parties.items() for t in ts), key=lambda x: -len(x[0]))
    if not terms:
        return []
    roles = {t.lower(): role for t, role in terms}
    rx = re.compile(r"\b(" + "|".join(re.escape(t) for t, _ in terms) + r")\b", re.I)
    return [(m.start(), m.end(), roles[m.group(1).lower()]) for m in rx.finditer(s)]


def _heads_subject(full: str, cs: int, start: int, end: int) -> bool:
    """Whether the party word at full[start:end] heads the subject of the clause that starts at cs: it is not
    possessive, and only modifiers ("a", "the", "written" ...) stand between it and the start of the clause, a
    comma, semicolon or colon, a paragraph mark, or "and", "or", "but" or "then". A party after a preposition, a
    verb or a subordinating word does not."""
    if full.startswith("'", end):                      # "the applicant's decision", "the boards' rules"
        return False
    words = full[cs:start].split()
    while words and words[-1].lower() in _MODIFIERS:
        words.pop()
    if not words:
        return True
    w = words[-1]
    return w[-1] in ",;:" or w.lower() in _JOINERS or bool(_PARA_MARK.fullmatch(w))


def _subject_before(spec: Spec, full: str, cs: int, pos: int) -> tuple[int, int, str] | None:
    """The last party before pos, in the clause that starts at cs, that heads a subject (see
    :func:`_heads_subject`): (start, end, role), or None. Parties after a preposition, a verb or a subordinating
    word, and possessives, are passed over."""
    found = None
    for s, e, role in _parties(spec, full[cs:pos]):
        if _heads_subject(full, cs, cs + s, cs + e):
            found = (cs + s, cs + e, role)
    return found


def _bearer_at(spec: Spec, full: str, pos: int) -> tuple[int, int, str] | None:
    """The party that bears the mandatory word at full[pos:], as (start, end, role), or None when the rules
    cannot place it. The bearer is the last party before it, in its clause, that heads a subject (see
    :func:`_subject_before`), except that there is none when:

    * the party right before the word (nothing but spaces between) is passed over: the word is that party's, in a
      subordinate clause ("a request that the public body shall answer ... is valid");
    * the party found has a verb of its own right after it ("a board may request ...") other than this word, and
      the word does not follow "and", "or", "nor" or "but" as a second verb of the same subject ("a public body may
      make reasonable charges ... and shall make all reasonable efforts"): the party is the subject of that verb,
      not of a mandatory word further on;
    * the party found is joined to a party of the other side ("the public body or the requester shall"): the word
      binds both, so it is not one side's duty."""
    cs, _ = _clause(full, pos)
    near = _parties(spec, full[cs:pos])
    if near:
        s, e, _ = near[-1]
        if not full[cs + e:pos].strip() and not _heads_subject(full, cs, cs + s, cs + e):
            return None
    subj = _subject_before(spec, full, cs, pos)
    if subj is None:
        return None
    verb = _OWN_VERB.match(full, subj[1])
    lead = full[cs:pos].split()
    if verb and verb.start(1) != pos and not (lead and lead[-1].lower() in _COORDINATORS | {"but"}):
        return None                                  # unless a second verb of the same subject ("may ... and shall")
    before = [(cs + s, cs + e, role) for s, e, role in _parties(spec, full[cs:subj[0]])]
    if before:
        s, e, role = before[-1]
        between = re.findall(r"[\w']+|,", full[e:subj[0]])
        if role != subj[2] and any(w.lower() in _COORDINATORS for w in between) and all(
                w.lower() in _COORDINATION | _MODIFIERS for w in between):
            return None
    return subj


def _by_other(spec: Spec, s: str) -> bool:
    """Whether s names the other side as the agent of a passive verb ("by the public body")."""
    return any(role == "other" and re.search(r"\bby\s+(?:(?:the|a|an|any|each|such)\s+)?$", s[:start], re.I)
               for start, _, role in _parties(spec, s))


def _required_bearer(spec: Spec, full: str, h: int, q: str, mk: re.Match) -> bool:
    """Whether one mandatory word of a required element's quote (found at full[h:h+len(q)]) puts a duty on the
    person; the rules are in the module docstring."""
    pos, end = h + mk.start(), h + mk.end()
    cs, ce = _clause(full, pos)
    inside = range(h, h + len(q))
    word = mk.group(1).lower()
    if word in ("shall", "must"):
        if _NOT_A_DUTY.match(full, end):
            return False
        if _PASSIVE.match(full, end) and (not _PASSIVE_OK.match(full, end) or _by_other(spec, full[end:ce])):
            return False                             # "shall be answered (by the public body)": not the person's act
        subj = _bearer_at(spec, full, pos)
        return bool(subj) and subj[2] == "person" and subj[0] in inside
    # "unless" or "only if": the person heads the condition, and the consequence is a loss for the person alone
    after = _parties(spec, full[end:ce])
    if not after:
        return False
    s, e, role = after[0]
    between = full[end:end + s].split()
    if role != "person" or end + s not in inside or full.startswith("'", end + e) or len(between) > 3 or any(
            w.lower() not in _MODIFIERS for w in between):
        return False
    lead = full[cs:pos].strip()
    if not lead or _PARA_MARK.fullmatch(lead):      # "Unless X, Y": the consequence is after the comma
        comma = full.find(",", end, ce)
        main = full[comma + 1:ce] if comma >= 0 else ""
    else:                                            # "Y unless X"
        main = full[cs:pos]
    roles = {r for _, _, r in _parties(spec, main)}
    return "person" in roles and "other" not in roles and bool(_LOSS.search(main)) and not _NEGATION.search(main)


def bearer(spec: Spec, el: Element, text: str) -> str | None:
    """None when a mandatory word of the element's quote falls on the right side: a duty of the person for
    ``required`` (named inside the quote; see the module docstring), a duty of the other side for ``duty``, the
    other side requiring something of the person for ``if_asked``. In each case the bearer is found by
    :func:`_bearer_at`. Otherwise what is wrong."""
    marker = _MARKERS[el.level]
    full, _ = _layout(text)
    q = norm(el.quote)
    for h in _hits(full, q):
        for mk in marker.finditer(q):
            if el.level == "required":
                if _required_bearer(spec, full, h, q, mk):
                    return None
                continue
            pos, end = h + mk.start(), h + mk.end()
            cs, ce = _clause(full, pos)
            subj = _bearer_at(spec, full, pos)
            who = subj[2] if subj else None
            if el.level == "if_asked":
                after = _parties(spec, full[end:ce])
                if who == "other" and after and after[0][2] == "person":
                    return None
            elif who == "other" and not _NOT_A_DUTY_OTHER.match(full, end):
                return None
    if el.level == "required":
        return "its quote does not put the mandatory words on the person as a duty (the requester or applicant, " \
               "or the person's request, heading the subject inside the quote)"
    if el.level == "if_asked":
        return "its quote does not let the other side require it of the person"
    return "its quote does not put the mandatory words on the other side as a duty (the other side heading the " \
           "subject, and not a grant, a legal consequence or an exemption)"


def passes(spec: Spec, el: Element, text: str, level: str) -> bool:
    """Whether the element's quote would pass the mandatory-word test of ``level`` ("required" or "if_asked"):
    its marker, no voluntary words, and the bearer (:func:`bearer`). An element at another level whose quote
    passes is a requirement of the person shown as something less."""
    if not _MARKERS[level].search(el.quote) or _VOLUNTARY.search(el.quote):
        return False
    return bearer(spec, dataclasses.replace(el, level=level), text) is None


def _words(s: str, spec: Spec, roles: tuple[str, ...] = ("person", "other")) -> set[str]:
    """Content words of s, cut to five letters, without the words of the parties in ``roles`` (which every
    sentence has)."""
    party = {w for role in roles for t in spec.parties.get(role, ()) for w in re.findall(r"[a-z]+", t.lower())}
    return {w[:5] for w in re.findall(r"[a-z]+", (s or "").lower())
            if len(w) >= 4 and w not in _STOP and w not in party}


def _letter_field(f: Field) -> bool:
    """The letter's own date or the sender's name (:data:`LETTER_FIELDS`): by name and type, with no placeholder
    and no options, and a label that holds the date or name word and nothing but the words listed for it."""
    kind = LETTER_FIELDS.get(f.name)
    if not kind or f.type != kind[0] or f.placeholder or f.options:
        return False
    words = re.findall(r"\w+", _plain(f.label).lower())
    return kind[1] in words and set(words) <= kind[2]


def _plain(s: str | None) -> str:
    """Text as the obligation check reads it: Unicode compatibility forms folded (NFKC: a full-width "ｍｕｓｔ" or
    "＊" becomes "must" or "*"), invisible format characters removed (a soft hyphen or zero-width space inside a
    word), and curly quotation marks made straight."""
    s = unicodedata.normalize("NFKC", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Cf").translate(_QUOTES)


def _marks(s: str) -> list[str]:
    """The asterisk-like marks in s ("*", "＊", "∗", "✱" ...: any character whose Unicode name says asterisk or
    asterism), which read as "required"."""
    return sorted({c for c in _plain(s) if c == "*" or any(w in unicodedata.name(c, "") for w in
                                                           ("ASTERISK", "ASTERISM"))})


def _foreign_letters(s: str) -> list[str]:
    """Letters outside the Latin script in s: a Cyrillic or Greek look-alike (U+0430 for "a", U+03BF for
    "o") can make an obligation word look like
    another word to the check, so the drafts' own texts use Latin letters only."""
    return sorted({c for c in _plain(s) if unicodedata.category(c).startswith("L")
                   and not unicodedata.name(c, "").startswith("LATIN")})


def _spec_texts(spec: Spec, reg: R.Registry):
    """The spec's own texts shown on the pages, outside any element."""
    yield "title", spec.title
    yield "summary", spec.summary
    yield "scope", spec.scope
    for i, (_, _, heading) in enumerate(spec.related, 1):
        yield f"heading of related forms {i}", heading
    note = reg.no_form_for_step(spec.state, spec.question, spec.step)
    if note:
        yield "fixture's no-form note", note.get("note")
    yield "subject", spec.subject
    yield "salutation", spec.salutation
    yield "closing", spec.closing


def _texts(el: Element):
    yield "label", el.label
    yield "help", el.help
    yield "condition", el.condition
    yield "letter", _strip_quote(el.letter or "")
    for f in el.fields:
        yield f"field {f.name} label", f.label
        yield f"field {f.name} placeholder", f.placeholder
        for o in f.options:
            yield f"field {f.name} option", o
    for link in el.forms:
        yield f"form {link.id} description", link.role


def cite(spec: Spec, el: Element) -> str:
    base = spec.citations[el.section]
    return base + "".join(f"({p})" for p in el.subsection.split(".")) if el.subsection else base


def _strip_quote(template: str) -> str:
    return template.replace("{quote}", "")


def _mark_problems(txt: str | None) -> list[str]:
    """What is wrong with a text's characters: an asterisk-like mark, or a letter outside the Latin script."""
    out = [f"uses a {c!r} mark (U+{ord(c):04X}), which reads as 'required'" for c in _marks(txt or "")]
    out += [f"uses a letter outside the Latin script ({c!r}, U+{ord(c):04X} {unicodedata.name(c, '?')}), which "
            f"could hide an obligation word" for c in _foreign_letters(txt or "")]
    return out


def check(spec: Spec, texts: dict[str, str]) -> list[str]:
    """Every rule in the module docstring, as a list of problems (empty when the draft may be made)."""
    problems = []
    ids = [e.id for e in spec.elements]
    if len(ids) != len(set(ids)):
        problems.append("duplicate element ids")
    fields = {f.name for e in spec.elements for f in e.fields}
    reg = R.registry()
    has_parties = bool(spec.parties.get("person")) and bool(spec.parties.get("other"))
    if not has_parties:
        problems.append(f"{spec.id}: the spec names no parties, so no element's level can be checked")
    for e in spec.elements:
        where = f"{spec.id}/{e.id}"
        if e.level not in LEVELS:
            problems.append(f"{where}: unknown level {e.level}")
        if e.section not in spec.citations:
            problems.append(f"{where}: no citation for section {e.section}")
        if not e.quote.strip():
            problems.append(f"{where}: no quote")
        text = texts.get(e.section)
        marker = _MARKERS.get(e.level)
        if text is None:
            problems.append(f"{where}: no text for {e.section}")
        else:
            issue = locate(text, e.quote, e.subsection)
            if issue:
                problems.append(f"{where}: {issue}")
            elif has_parties:
                if marker and marker.search(e.quote):
                    who = bearer(spec, e, text)
                    if who:
                        problems.append(f"{where}: {who}")
                # a requirement of the person is shown as one: never as a choice, a context line, a note or a
                # duty of the other side; what the other side may require is never a choice or a context line
                if e.level in LEVELS and e.level != "required" and passes(spec, e, text, "required"):
                    problems.append(f"{where}: its quote puts a duty on the person (it passes the 'required' "
                                    f"test), so the element cannot be '{e.level}' ({LEVELS[e.level]!r})")
                elif e.level in ("right", "context") and passes(spec, e, text, "if_asked"):
                    problems.append(f"{where}: its quote lets the other side require it of the person (it passes "
                                    f"the 'if_asked' test), so the element cannot be '{e.level}' "
                                    f"({LEVELS[e.level]!r})")
        article = "an" if e.level[:1] in tuple("aeiou") else "a"
        if e.level in _IN_LETTER and e.id not in spec.layout:
            problems.append(f"{where}: {article} {e.level} element is part of the letter, but it is not in the "
                            f"layout")
        if marker and not marker.search(e.quote):
            problems.append(f"{where}: {article} {e.level} element must quote words such as '{marker.pattern}'")
        if e.level in ("required", "if_asked") and _VOLUNTARY.search(e.quote):
            problems.append(f"{where}: its quote says the act is voluntary or optional "
                            f"({_VOLUNTARY.search(e.quote)[0]!r}), so the element cannot be '{e.level}'")
        # obligation words: none in the plain levels; elsewhere only those the quote itself uses; no asterisk-like
        # mark and no non-Latin letter anywhere
        quote = _plain(e.quote)
        for name, txt in _texts(e):
            problems += [f"{where}: its {name} {p}" for p in _mark_problems(txt)]
            for m in _OBLIGATION.finditer(_plain(txt)):
                word = re.sub(r"\s+", " ", m[0])
                if e.level not in _MARKERS:
                    problems.append(f"{where}: its {name} states an obligation ({word!r}) but the element is "
                                    f"'{e.level}'")
                elif not re.search(r"\b" + re.escape(word).replace(r"\ ", r"\s+") + r"\b", quote, re.I):
                    problems.append(f"{where}: its {name} says {word!r}, which its quote does not")
        # the label and each field rest on the quote, not on an unrelated sentence
        if e.level in _RELEVANT:
            qw = _words(e.quote, spec)
            if not _words(e.label, spec) & qw:
                problems.append(f"{where}: its label {e.label!r} shares no word with its quote")
            for f in e.fields:
                if not _words(f.name.replace("_", " "), spec) & qw:
                    problems.append(f"{where}: field {f.name} shares no word with its quote")
                if not _words(" ".join((f.label,) + f.options), spec) & qw:
                    problems.append(f"{where}: the label of field {f.name} shares no word with its quote")
        # a context field rests on its quote too (the other side's words count), or is the letter's own date or
        # the sender's name; duty and notice elements are notes, with nothing to fill in
        if e.level == "context":
            qw = _words(e.quote, spec, ("person",))
            for f in e.fields:
                if _letter_field(f):
                    continue
                if not _words(f.name.replace("_", " "), spec, ("person",)) & qw:
                    problems.append(f"{where}: field {f.name} of a context element shares no word with its quote "
                                    f"(only the letter's own date and the sender's name need none)")
                if not _words(" ".join((f.label,) + f.options), spec, ("person",)) & qw:
                    problems.append(f"{where}: the label of field {f.name} of a context element shares no word "
                                    f"with its quote")
        if e.level in _NO_FIELDS and e.fields:
            problems.append(f"{where}: a {e.level} element is a note and carries no fields "
                            f"({', '.join(f.name for f in e.fields)})")
        if e.level == "notice" and (e.letter or e.id in spec.layout):
            problems.append(f"{where}: a notice element is not part of the letter")
        for f in e.fields:
            if f.default not in (None, False, ""):
                problems.append(f"{where}: field {f.name} has a default value ({f.default!r}); nothing is "
                                f"chosen for the person")
        for name in _PLACEHOLDER.findall(e.letter or ""):
            if name not in fields and name not in ("quote", "cite"):
                problems.append(f"{where}: letter uses unknown field {{{name}}}")
        for name in (e.when or "").split("|"):
            if name and name not in fields:
                problems.append(f"{where}: 'when' names unknown field {name}")
        for link in e.forms:
            form = reg.form(link.id)
            if form is None:
                problems.append(f"{where}: unknown form id {link.id}")
                continue
            same = [s for s in form.get("steps") or [] if R.step_file_key(s["file"]) == (spec.state, spec.question)]
            if link.match not in ("partial", "related"):
                problems.append(f"{where}: form {link.id} is linked as {link.match!r}; an element's form is "
                                f"'partial' or 'related'")
            elif not same and link.match != "related":
                problems.append(f"{where}: form {link.id} is linked as {link.match!r}, but the fixture links it to "
                                f"no step of {spec.state}/{spec.question}, so it is at most 'related'")
            elif any(R.MATCH_ORDER[link.match] < R.MATCH_ORDER[s["match"]] for s in same):
                problems.append(f"{where}: form {link.id} is linked as {link.match!r}, stronger than the fixture's "
                                f"match for this process")
            if not link.role.strip():
                problems.append(f"{where}: form {link.id} does not say what the form is")
        if e.letter and e.id not in spec.layout:
            problems.append(f"{where}: has a letter sentence but is not in the layout")
    for item in spec.layout:
        if item.startswith("@"):
            if item[1:] not in ("subject", "salutation", "closing"):
                problems.append(f"{spec.id}: unknown layout part {item}")
        elif item not in ids:
            problems.append(f"{spec.id}: layout names unknown element {item}")
        elif not next(e for e in spec.elements if e.id == item).letter:
            problems.append(f"{spec.id}: layout element {item} has no letter sentence")
    # the spec's own texts state no obligation: they describe, and only an element's quote may require
    for name, txt in _spec_texts(spec, reg):
        problems += [f"{spec.id}: the {name} {p}" for p in _mark_problems(txt)]
        for m in _OBLIGATION.finditer(_plain(txt)):
            word = re.sub(r"\s+", " ", m[0])
            problems.append(f"{spec.id}: the {name} states an obligation ({word!r})")
    for name, txt in (("subject", spec.subject), ("salutation", spec.salutation), ("closing", spec.closing)):
        for ph in _PLACEHOLDER.findall(txt):
            if ph not in fields:
                problems.append(f"{spec.id}: the {name} uses unknown field {{{ph}}}")
    if reg.has_official_form(spec.state, spec.question, spec.step):
        problems.append(f"{spec.id}: {spec.state}/{spec.question}/{spec.step} has an official form; no draft")
    return problems


# ------------------------------------------------------------------------------------------------ building
def load_texts(spec: Spec) -> dict[str, dict]:
    """Section texts for a spec: the fixture in fixtures/statutes/ when it holds the section, else the local
    open-us-law store (search index or parquet)."""
    from ..municipal import statutes

    fx = statutes.load_fixture(spec.state)
    out = {}
    for ref in spec.sections:
        if fx is not None and not statutes.find(fx, ref).empty:
            t = statutes.section_texts(spec.state, [ref], df=fx)[0]
            origin = f"fixtures/statutes/{spec.state}_sections.json ({t.retrieved_from})"
        else:
            t = statutes.section_texts(spec.state, [ref])[0]
            origin = t.retrieved_from
        out[ref] = {"ref": ref, "citation": spec.citations[ref], "url": t.url, "text": t.text,
                    "retrieved_from": origin, "license_note": t.license_note}
    return out


def _as_sources(spec: Spec, texts: dict[str, Any]) -> dict[str, dict]:
    out = {}
    for ref in spec.sections:
        t = texts.get(ref)
        if t is None:
            continue
        d = dict(t) if isinstance(t, dict) else {"ref": ref, "text": t}
        d.setdefault("ref", ref)
        d.setdefault("citation", spec.citations[ref])
        d["sha256"] = hashlib.sha256(d["text"].encode("utf-8")).hexdigest()
        out[ref] = d
    return out


def build(spec: Spec | str, texts: dict[str, Any] | None = None, *, as_of: str | None = None) -> dict:
    """The draft as data: elements with citations and quotes, the letter layout, the official alternatives and
    the sources. ``texts`` maps each section reference to its text (a string, or a dict with ``text`` and
    optionally ``url``); by default they are loaded with :func:`load_texts`. Raises DraftError on any problem."""
    spec = SPECS[spec] if isinstance(spec, str) else spec
    sources = _as_sources(spec, texts if texts is not None else load_texts(spec))
    problems = check(spec, {ref: s["text"] for ref, s in sources.items()})
    if problems:
        raise DraftError("; ".join(problems))
    reg = R.registry()
    elements = []
    for e in spec.elements:
        src = sources[e.section]
        elements.append({
            "id": e.id, "level": e.level, "level_label": LEVELS[e.level], "label": e.label,
            "section": e.section, "subsection": e.subsection, "citation": cite(spec, e),
            "section_citation": spec.citations[e.section], "url": src.get("url"), "quote": e.quote,
            "fields": [{"name": f.name, "label": f.label, "type": f.type, "options": list(f.options),
                        "placeholder": f.placeholder, "default": f.default} for f in e.fields],
            "letter": e.letter, "when": e.when, "help": e.help, "condition": e.condition,
            "cite_in_letter": e.cite_in_letter and "{cite}" not in (e.letter or ""),
            "forms": [{**R.summary(reg.form(link.id), link.match), "role": link.role} for link in e.forms],
            "in_letter": e.id in spec.layout,
        })
    note = reg.no_form_for_step(spec.state, spec.question, spec.step)
    return {
        "schema": SCHEMA, "id": spec.id, "title": spec.title, "summary": spec.summary, "scope": spec.scope,
        "state": spec.state, "question": spec.question, "step": spec.step,
        "step_file": R.step_file(spec.state, spec.question), "banner": BANNER,
        "made": as_of or date.today().isoformat(), "generator": "lexflow.forms.draft",
        "review": "draft, machine-checked (quotes and rules); not reviewed by a lawyer",
        "letter": {"layout": list(spec.layout), "subject": spec.subject, "salutation": spec.salutation,
                   "closing": spec.closing},
        "elements": elements,
        "official": reg.forms_for_step(spec.state, spec.question, spec.step),
        "no_form_note": note,
        "related": [{"title": title, "forms": reg.forms_for_state(st, q)} for st, q, title in spec.related],
        "sources": list(sources.values()),
        "checks": {"elements": len(elements), "quotes_found": len(elements), "problems": []},
    }


# ----------------------------------------------------------------------------------------------- rendering
_CSS = """
:root{--bg:#f7f6f2;--card:#fff;--ink:#1d1d1b;--muted:#5d5c57;--line:#dddbd3;--accent:#1f5f8b;--warn-bg:#fff4d6;
--warn-ink:#5a4200;--warn-line:#e0b84c;--quote:#f1efe8;--req:#8a2b12;--ask:#6a4c00;--opt:#1f5f8b;--info:#4d5b2a}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#171716;--card:#21211f;--ink:#ecebe6;
--muted:#a8a69e;--line:#3a3935;--accent:#7fb6dc;--warn-bg:#3a2f0f;--warn-ink:#f4dc9a;--warn-line:#8a6d1e;
--quote:#2a2a27;--req:#f0a08a;--ask:#e8c66a;--opt:#7fb6dc;--info:#b9c98a}}
:root[data-theme=dark]{--bg:#171716;--card:#21211f;--ink:#ecebe6;--muted:#a8a69e;--line:#3a3935;--accent:#7fb6dc;
--warn-bg:#3a2f0f;--warn-ink:#f4dc9a;--warn-line:#8a6d1e;--quote:#2a2a27;--req:#f0a08a;--ask:#e8c66a;--opt:#7fb6dc;
--info:#b9c98a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:16px}
a{color:var(--accent)}
h1{font-size:1.6rem;line-height:1.25;margin:.4em 0 .3em}
h2{font-size:1.15rem;margin:1.6em 0 .6em}
h3{font-size:1rem;margin:0}
.banner{background:var(--warn-bg);color:var(--warn-ink);border:2px solid var(--warn-line);border-radius:8px;
padding:12px 14px;font-weight:600}
.lede{color:var(--muted);max-width:75ch}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:12px 0}
.box ul{margin:.3em 0;padding-left:1.2em}
.grid{display:grid;grid-template-columns:minmax(0,1fr);gap:16px}
@media (min-width:960px){.grid{grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr)}
.sticky{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}}
.el{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--line);border-radius:8px;
padding:12px 14px;margin:0 0 12px}
.el.required{border-left-color:var(--req)}.el.if_asked{border-left-color:var(--ask)}
.el.right{border-left-color:var(--opt)}.el.duty,.el.notice{border-left-color:var(--info)}
.el header{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline;justify-content:space-between}
.badge{font-size:.78rem;border:1px solid currentColor;border-radius:999px;padding:1px 8px;white-space:nowrap}
.required .badge{color:var(--req)}.if_asked .badge{color:var(--ask)}.right .badge{color:var(--opt)}
.duty .badge,.notice .badge,.context .badge{color:var(--muted)}
label{display:block;font-size:.9rem;margin:.6em 0 .2em}
label.inline{display:flex;gap:8px;align-items:flex-start}
input[type=text],input[type=email],input[type=date],textarea,select{width:100%;font:inherit;color:var(--ink);
background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:6px 8px}
textarea{min-height:4.5em}
.help,.cond{font-size:.92rem;margin:.5em 0 0}.cond{color:var(--req)}
blockquote{margin:.6em 0 0;background:var(--quote);border-radius:6px;padding:8px 10px;font-size:.9rem}
blockquote p{margin:0}blockquote footer{margin-top:4px;font-size:.82rem;color:var(--muted)}
.forms{font-size:.9rem;margin:.5em 0 0}
.letter{background:#fff;color:#111;border:1px solid var(--line);border-radius:4px;padding:28px 30px;
font:15px/1.55 Georgia,"Times New Roman",serif}
.letter p{margin:0 0 .9em;white-space:pre-line}
.letter .subject{font-weight:700}
.letter .cite{color:#555;font-size:.8em}
.letter .blank{border-bottom:1px solid #444;display:inline-block;min-width:9em}
.letter .hint{color:#8a8a8a;font:11px/1.2 system-ui,sans-serif;vertical-align:top}
.letter .tick{font-family:system-ui,sans-serif;color:#555}
.letter-banner{font:600 12px/1.4 system-ui,sans-serif;color:#5a4200;border:1px solid #e0b84c;background:#fff4d6;
padding:6px 8px;margin:0 0 18px;border-radius:4px}
.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:8px 0}
button{font:inherit;padding:6px 14px;border-radius:6px;border:1px solid var(--accent);background:var(--accent);
color:#fff;cursor:pointer}
.muted{color:var(--muted)}
.notes{break-before:page}
.printonly{display:none}
@media print{body{background:#fff}main{max-width:none;padding:0}.noprint{display:none!important}
.printonly{display:block}
.grid{display:block}.sticky{position:static;max-height:none;overflow:visible}.letter{border:0;padding:0}
.el{break-inside:avoid}.first-page{break-after:page}}
@page{margin:18mm 14mm 14mm}
""" + ("@page{@top-center{content:\"" + BANNER.replace("\\", "\\\\").replace("\"", "\\\"") + "\";"
       "font:600 8pt/1.3 system-ui,sans-serif;color:#5a4200}}\n")

_JS = """
(function(){
  const D = JSON.parse(document.getElementById('draft-data').textContent);
  const form = document.getElementById('draft-form');
  const out = document.getElementById('letter-body');
  const els = Object.fromEntries(D.elements.map(e => [e.id, e]));
  function values(){
    const v = {};
    for (const e of D.elements) for (const f of e.fields) {
      const nodes = form.querySelectorAll('[name="' + f.name + '"]');
      if (f.type === 'checkbox') v[f.name] = nodes[0] && nodes[0].checked ? 'yes' : '';
      else if (f.type === 'radio') { const c = form.querySelector('[name="' + f.name + '"]:checked'); v[f.name] = c ? c.value : ''; }
      else v[f.name] = nodes[0] ? nodes[0].value.trim() : '';
      if (f.type === 'date' && v[f.name]) {
        const d = new Date(v[f.name] + 'T12:00:00');
        if (!isNaN(d)) v[f.name] = d.toLocaleDateString(undefined, {year:'numeric', month:'long', day:'numeric'});
      }
    }
    return v;
  }
  function fill(p, tpl, v, e){
    tpl = tpl.replace(/\\[([^\\[\\]]*)\\]/g, (all, inner) =>
      (inner.match(/\\{\\w+\\}/g) || []).every(ph => v[ph.slice(1, -1)]) ? inner : '');
    const parts = tpl.split(/(\\{\\w+\\})/);
    for (const part of parts) {
      const m = /^\\{(\\w+)\\}$/.exec(part);
      if (!m) { p.append(part); continue; }
      const k = m[1];
      const val = k === 'quote' ? e.quote : k === 'cite' ? e.citation : (v[k] || '');
      if (val) p.append(val); else { const b = document.createElement('span'); b.className = 'blank'; b.textContent = '\\u00a0'; p.append(b); }
    }
  }
  function render(){
    const v = values();
    out.replaceChildren();
    for (const item of D.letter.layout) {
      const p = document.createElement('p');
      if (item[0] === '@') {
        const key = item.slice(1);
        p.dataset.element = key; if (key === 'subject') p.className = 'subject';
        fill(p, D.letter[key], v, {}); out.append(p); continue;
      }
      const e = els[item];
      if (e.when && !e.when.split('|').some(k => v[k])) continue;
      p.dataset.element = e.id;
      fill(p, e.letter, v, e);
      if (e.cite_in_letter) { const c = document.createElement('span'); c.className = 'cite'; c.textContent = ' [' + e.citation + ']'; p.append(c); }
      out.append(p);
    }
  }
  form.addEventListener('input', render);
  form.addEventListener('change', render);
  form.addEventListener('submit', ev => ev.preventDefault());
  document.getElementById('print').addEventListener('click', () => window.print());
  render();
})();
"""


def _e(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _page(title: str, body: str, script: str = "") -> str:
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<meta name=\"referrer\" content=\"no-referrer\">\n"
            f"<title>{_e(title)}</title>\n<style>{_CSS}</style>\n</head>\n<body>\n<main>\n{body}\n</main>\n"
            f"{script}</body>\n</html>\n")


def _form_link(f: dict) -> str:
    name = f["title"] + (f" ({f['form_number']})" if f.get("form_number") else "")
    link = f"<a href=\"{_e(f['url'])}\" rel=\"noopener noreferrer\">{_e(name)}</a>" if f.get("url") else _e(name)
    bits = [f.get("publisher")]
    if f.get("revision"):
        bits.append(f["revision"] + (" (not confirmed on the form itself)" if f.get("revision_note") else ""))
    if f.get("fillable") is True:
        bits.append("fillable PDF")
    elif f.get("fillable") == "online":
        bits.append("online")
    if f.get("fee"):
        bits.append(f"fee: {f['fee']}")
    if f.get("match"):
        bits.append(f"{f['match']} match")
    if f.get("checked"):
        bits.append(f"link checked {f['checked']} ({f.get('status')})")
    return f"{link} <span class=\"muted\">· {_e(' · '.join(b for b in bits if b))}</span>"


_ELEMENT_FORM_HEAD = {"partial": "Official form for part of this", "related": "Related official form"}


def _element_forms(e: dict) -> str:
    """An element's official forms, each under its match ("Related official form") and with what it is."""
    return "".join(
        f"<p class=\"forms\"><strong>{_e(_ELEMENT_FORM_HEAD.get(f.get('match'), 'Official form'))}:</strong> "
        f"{_form_link(f)}" + (f"<br><span class=\"muted\">{_e(f['role'])}</span>" if f.get("role") else "")
        + "</p>" for f in e["forms"])


def _official_box(d: dict) -> str:
    L = ["<section class=\"box official\" aria-labelledby=\"official-h\"><h2 id=\"official-h\" "
         "style=\"margin-top:0\">Official form first</h2>"]
    if d["official"]:
        L.append("<p>Official help for this step, from the publishers' own sites:</p><ul>")
        L += [f"<li>{_form_link(f)}</li>" for f in d["official"]]
        L.append("</ul>")
    note = d.get("no_form_note")
    if note:
        extra = f" {_e(note['note'])}" if note.get("note") else ""
        L.append(f"<p>No statewide official form was found for this step. The law for this step: "
                 f"{_e(note['statute'])}.{extra} Some agencies publish their own form or portal: use it if they "
                 f"do.</p>")
    for g in d.get("related") or []:
        L.append(f"<h3>{_e(g['title'])}</h3><ul>")
        L += [f"<li>{_form_link(f)}</li>" for f in g["forms"]]
        L.append("</ul>")
    L.append(f"<p class=\"muted\">Forms from <code>fixtures/forms/forms.json</code>; links are checked read-only and "
             f"may have moved since.</p></section>")
    return "\n".join(L)


def _quote_block(e: dict) -> str:
    src = f"<a href=\"{_e(e['url'])}\" rel=\"noopener noreferrer\">{_e(e['citation'])}</a>" if e.get("url") \
        else _e(e["citation"])
    return f"<blockquote><p>“{_e(e['quote'])}”</p><footer>{src}</footer></blockquote>"


def _field_html(f: dict) -> str:
    fid = f"f-{f['name']}"
    t = f["type"]
    if t == "checkbox":
        checked = " checked" if f.get("default") else ""
        return (f"<label class=\"inline\" for=\"{fid}\"><input type=\"checkbox\" id=\"{fid}\" name=\"{_e(f['name'])}\""
                f"{checked}> <span>{_e(f['label'])}</span></label>")
    if t == "radio":
        opts = "".join(f"<label class=\"inline\"><input type=\"radio\" name=\"{_e(f['name'])}\" value=\"{_e(o)}\""
                       f"{' checked' if o == f.get('default') else ''}> <span>{_e(o)}</span></label>"
                       for o in f["options"])
        return f"<fieldset style=\"border:0;padding:0;margin:0\"><legend>{_e(f['label'])}</legend>{opts}</fieldset>"
    if t == "select":
        opts = "".join(f"<option value=\"{_e(o)}\">{_e(o) or '(none)'}</option>" for o in f["options"])
        return f"<label for=\"{fid}\">{_e(f['label'])}</label><select id=\"{fid}\" name=\"{_e(f['name'])}\">{opts}</select>"
    ph = f" placeholder=\"{_e(f['placeholder'])}\"" if f.get("placeholder") else ""
    if t == "textarea":
        return (f"<label for=\"{fid}\">{_e(f['label'])}</label>"
                f"<textarea id=\"{fid}\" name=\"{_e(f['name'])}\"{ph}></textarea>")
    kind = t if t in ("email", "date") else "text"
    return (f"<label for=\"{fid}\">{_e(f['label'])}</label>"
            f"<input type=\"{kind}\" id=\"{fid}\" name=\"{_e(f['name'])}\" autocomplete=\"off\"{ph}>")


def _element_html(e: dict) -> str:
    L = [f"<section class=\"el {e['level']}\" id=\"el-{e['id']}\" data-element=\"{e['id']}\">",
         f"<header><h3>{_e(e['label'])}</h3><span class=\"badge\">{_e(e['level_label'])}</span></header>"]
    L += [_field_html(f) for f in e["fields"]]
    if e.get("condition"):
        L.append(f"<p class=\"cond\">{_e(e['condition'])}</p>")
    if e.get("help"):
        L.append(f"<p class=\"help\">{_e(e['help'])}</p>")
    L.append(_quote_block(e))
    if e["forms"]:
        L.append(_element_forms(e))
    L.append("</section>")
    return "\n".join(L)


def _head(d: dict) -> str:
    return (f"<div class=\"banner\" role=\"note\">{_e(d['banner'])}</div>\n"
            f"<h1>{_e(d['title'])}</h1>\n<p class=\"lede\">{_e(d['summary'])}</p>\n"
            + (f"<p class=\"lede\">{_e(d['scope'])}</p>\n" if d.get("scope") else ""))


def render_form(d: dict) -> str:
    """The fillable HTML form with a live letter preview. Runs offline; sends and stores nothing."""
    letter_els = [e for e in d["elements"] if e["in_letter"]]
    other = [e for e in d["elements"] if not e["in_letter"]]
    data = json.dumps({"elements": d["elements"], "letter": d["letter"]}, ensure_ascii=False).replace("</", "<\\/")
    body = "\n".join([
        "<div class=\"noprint\">", _head(d),
        "<p class=\"box\">This page works offline. Nothing you type is sent anywhere or saved: there is no submit "
        "button, and closing the page clears it. Print the letter, or copy it, when it is ready.</p>",
        _official_box(d),
        "</div>",
        "<div class=\"grid\">",
        "<form id=\"draft-form\" class=\"noprint\" autocomplete=\"off\" novalidate>",
        "<h2>What goes in the letter</h2>",
        *[_element_html(e) for e in letter_els],
        "<h2>What the law says happens next</h2>",
        *[_element_html(e) for e in other],
        "</form>",
        "<section class=\"sticky\" aria-labelledby=\"letter-h\">",
        "<div class=\"toolbar noprint\"><h2 id=\"letter-h\" style=\"margin:0\">Your letter</h2>"
        "<button type=\"button\" id=\"print\">Print the letter</button></div>",
        f"<div class=\"letter\"><div class=\"letter-banner\">{_e(d['banner'])}</div><div id=\"letter-body\"></div>"
        "</div>",
        f"<p class=\"muted noprint\">Made {_e(d['made'])} by lexflow from {_e(', '.join(s['citation'] for s in d['sources']))}"
        f" ({_e(d['review'])}).</p>",
        "</section>", "</div>",
    ])
    script = (f"<script type=\"application/json\" id=\"draft-data\">{data}</script>\n<script>{_JS}</script>\n")
    return _page(d["title"], body, script)


def _blank_fill(template: str, e: dict | None, fields: dict[str, dict]) -> str:
    def rep(m):
        k = m.group(1)
        if e is not None and k == "quote":
            return _e(e["quote"])
        if e is not None and k == "cite":
            return _e(e["citation"])
        f = fields.get(k)
        if f and f["type"] in ("radio", "select") and [o for o in f["options"] if o]:
            return " / ".join(_e(o) for o in f["options"] if o)
        hint = f["label"] if f else k
        return f"<span class=\"blank\"><span class=\"hint\">{_e(hint)}</span></span>"
    template = _OPTIONAL.sub(lambda m: m.group(1), template)
    out, pos = [], 0
    for m in _PLACEHOLDER.finditer(template):
        out.append(_e(template[pos:m.start()]))
        out.append(rep(m))
        pos = m.end()
    out.append(_e(template[pos:]))
    return "".join(out)


def render_letter(d: dict) -> str:
    """The printable letter with blanks, every paragraph tagged with its element. The scope and the official
    alternatives come first (on a page of their own when printed), the notes after the letter, after a page
    break. Printed, each of the three parts starts with the banner, and the page-margin rule in the CSS repeats it
    on every sheet where the browser supports margin boxes."""
    els = {e["id"]: e for e in d["elements"]}
    fields = {f["name"]: f for e in d["elements"] for f in e["fields"]}
    P = []
    for item in d["letter"]["layout"]:
        if item.startswith("@"):
            key = item[1:]
            cls = " class=\"subject\"" if key == "subject" else ""
            P.append(f"<p data-element=\"{key}\"{cls}>{_blank_fill(d['letter'][key], None, fields)}</p>")
            continue
        e = els[item]
        tick = "<span class=\"tick\">☐ </span>" if e.get("when") else ""
        c = f"<span class=\"cite\"> [{_e(e['citation'])}]</span>" if e["cite_in_letter"] else ""
        P.append(f"<p data-element=\"{e['id']}\">{tick}{_blank_fill(e['letter'], e, fields)}{c}</p>")
    notes = [e for e in d["elements"] if not e["in_letter"] or e["level"] in ("required", "if_asked")]
    # printed, each part starts a new sheet with the banner on top; on screen the banner above the page serves
    sheet_banner = f"<div class=\"letter-banner printonly\" role=\"note\">{_e(d['banner'])}</div>"
    N = ["<section class=\"notes\">", sheet_banner,
         "<h2>Notes for you (keep these; they are not part of the letter)</h2>"]
    for e in notes:
        N.append(f"<div class=\"el {e['level']}\" data-note=\"{e['id']}\"><header><h3>{_e(e['label'])}</h3>"
                 f"<span class=\"badge\">{_e(e['level_label'])}</span></header>"
                 + (f"<p class=\"cond\">{_e(e['condition'])}</p>" if e.get("condition") else "")
                 + (f"<p class=\"help\">{_e(e['help'])}</p>" if e.get("help") else "")
                 + _quote_block(e) + _element_forms(e) + "</div>")
    N.append("</section>")
    body = "\n".join([
        f"<div class=\"banner noprint\" role=\"note\">{_e(d['banner'])}</div>",
        f"<p class=\"noprint lede\">{_e(d['title'])}. Fill in the blanks, keep the sentences marked ☐ that apply "
        "and strike out the rest. The fillable version of this page does the same on screen.</p>",
        "<div class=\"first-page\">", sheet_banner,
        f"<p class=\"lede\">{_e(d['scope'])}</p>" if d.get("scope") else "",
        _official_box(d),
        "</div>",
        "<div class=\"letter\">", f"<div class=\"letter-banner\">{_e(d['banner'])}</div>",
        "<div id=\"letter-body\">", *P, "</div>", "</div>",
        *N,
        f"<p class=\"muted\">Made {_e(d['made'])} by lexflow from "
        f"{_e(', '.join(s['citation'] for s in d['sources']))} ({_e(d['review'])}).</p>",
    ])
    return _page(f"{d['title']}: letter", body)


def render_index(drafts: list[dict]) -> str:
    items = "".join(
        f"<li><strong>{_e(d['title'])}</strong><br><a href=\"{_e(d['id'])}.form.html\">Fillable form</a> · "
        f"<a href=\"{_e(d['id'])}.letter.html\">Printable letter</a> · <a href=\"{_e(d['id'])}.json\">Data "
        f"(elements, quotes, sources)</a><br><span class=\"muted\">{len(d['elements'])} elements, each citing "
        f"its section and quoting it; step <code>{_e(d['step'])}</code> in <code>{_e(d['step_file'])}</code>"
        f"</span></li>" for d in drafts)
    body = (f"<div class=\"banner\" role=\"note\">{_e(BANNER)}</div><h1>Drafts from the statute</h1>"
            f"<p class=\"lede\">Worked examples of lexflow's draft generator (<code>lexflow/forms/draft.py</code>) "
            f"for steps with no official form. See <code>docs/design/forms-plan.md</code>.</p>"
            f"<ul class=\"box\" style=\"padding-left:2em\">{items}</ul>")
    return _page("Drafts from the statute", body)


def write(d: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / f"{d['id']}.json", out_dir / f"{d['id']}.form.html", out_dir / f"{d['id']}.letter.html"]
    for p, text in zip(paths, (json.dumps(d, ensure_ascii=False, indent=1) + "\n", render_form(d), render_letter(d))):
        p.write_text(text, encoding="utf-8", newline="\n")
    return paths


def read_sources(paths: list[str]) -> dict[str, dict]:
    """Section texts saved earlier: a draft's own .json (its ``sources``), a list of source dicts, or a mapping
    {reference: {text, url, ...}} as :func:`load_texts` returns it."""
    out: dict[str, dict] = {}
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        rows = data.get("sources", data) if isinstance(data, dict) else data
        if isinstance(rows, dict):
            rows = [{"ref": k, **v} for k, v in rows.items()]
        for r in rows:
            out[r["ref"]] = {k: v for k, v in r.items() if k != "sha256"}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write statute-grounded draft forms and letters.")
    ap.add_argument("specs", nargs="*", help=f"spec ids (default: all of {', '.join(SPECS)})")
    ap.add_argument("--out", default=str(R.ROOT / "out" / "forms"))
    ap.add_argument("--as-of", default=None, help="date stamped on the drafts (default: today)")
    ap.add_argument("--sources", action="append", default=[],
                    help="JSON file of section texts (see read_sources), to build without the statute store")
    a = ap.parse_args(argv)
    saved = read_sources(a.sources) if a.sources else None
    drafts = []
    for sid in a.specs or list(SPECS):
        texts = {r: saved[r] for r in SPECS[sid].sections if r in saved} if saved is not None else None
        d = build(sid, texts, as_of=a.as_of)
        for p in write(d, Path(a.out)):
            print(p)
        drafts.append(d)
    if not a.specs:
        p = Path(a.out) / "index.html"
        p.write_text(render_index(drafts), encoding="utf-8", newline="\n")
        print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
