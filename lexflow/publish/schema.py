"""The Lexipedia Wikibase schema, version 2: the one table of classes, vocabularies, properties and key forms.

This is the code form of docs/design/wikibase-schema.md.  ``graph.py`` builds items from it, ``qs.py`` writes
QuickStatements from it and ``rdf.py`` writes Turtle from it; none of them names a property or class any other
way.  Everything here is data and pure functions: nothing reads the database or the network.

* ``CLASSES``: every class item, the existing ones (Q7 legal process ... Q23 legal role, with their Lexipedia
  ``qid``) and the new ones of the doc's section 2 (``qid`` None, key ``lexflow:class:<slug>``).
* ``VOCAB``: the vocabulary sets (``lexflow:vocab:<set>:<slug>``), each entry with a label and a one-line
  description.
* ``PROPERTIES``: the new properties of section 3 in creation order, with the doc's number, the QuickStatements
  datatype, the equivalent Wikidata property where one is exact, the formatter templates and the kinds of value
  they take.  ``EXISTING`` maps the 25 live properties' labels to their ids.
* ``key_for(kind, *parts)`` mints every key form of section 1 and authority-escalation.md section 1.3; keys are
  minted once and never change, so every rule here is deterministic.  ``sort_key(act_id)`` gives the string
  that orders units and sections in the code's order.

Wikidata ids were checked read-only with ``wbgetentities`` on 15 October 2026 (labels and P31/P279): the doc's
*verify* marks resolved to Q922203 (code of law), Q11861227 (administrative regulation) and Q1335296 (form, a
genre of document); Q294414 is "public office", a subclass of position (Q4164871).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------- classes


@dataclass(frozen=True)
class Cls:
    slug: str
    label: str
    description: str
    wikidata: str | None = None           # the equivalent Wikidata item (P8 exact match), when one fits
    subclass_of: str | None = None        # slug of the parent class (P6)
    qid: str | None = None                # the Lexipedia item that already exists (Q7 ...), else None: create it


CLASSES: list[Cls] = [
    # the existing class items are kept; the graph refers to them by label (Item.cls) and never recreates them
    Cls("legal-process", "legal process", "A modeled legal process.", qid="Q7"),
    Cls("legal-process-step", "legal process step", "A step or action within a legal process.", qid="Q8"),
    Cls("decision-point", "decision point",
        "A decision / branch point in a legal process, often backed by a DMN decision table.", qid="Q9"),
    Cls("statute", "statute or legal provision", "A statute or provision referenced by a process.", qid="Q10"),
    Cls("norm", "norm", "A prescriptive statement (LegalRuleML PrescriptiveStatement).", qid="Q11"),
    Cls("deontic-specification", "deontic specification",
        "Parent class of the deontic modalities (LegalRuleML Deontic Specification).", qid="Q12"),
    Cls("obligation", "Obligation", "A state/act to which a Bearer is legally bound.", "deontic-specification",
        qid="Q13"),
    Cls("permission", "Permission", "A state/act the Bearer has no obligation or prohibition to the contrary.",
        subclass_of="deontic-specification", qid="Q14"),
    Cls("prohibition", "Prohibition", "A state/act the Bearer is legally bound to avoid.",
        subclass_of="deontic-specification", qid="Q15"),
    Cls("right", "Right", "A permission to a party implying obligations/prohibitions on auxiliary parties.",
        subclass_of="deontic-specification", qid="Q16"),
    Cls("weak-permission", "weak permission", "Permission as the mere absence of a contrary obligation.",
        subclass_of="permission", qid="Q17"),
    Cls("strong-permission", "strong permission", "Explicit permissive norm, an exception of a prohibition.",
        subclass_of="permission", qid="Q18"),
    Cls("achievement-obligation", "achievement obligation",
        "Obligation fulfilled if the prescribed state holds at least once.", subclass_of="obligation", qid="Q19"),
    Cls("maintenance-obligation", "maintenance obligation",
        "Obligation that must hold for the whole interval it is in force.", subclass_of="obligation", qid="Q20"),
    Cls("jurisdiction", "jurisdiction", "A government whose law a provision or process belongs to.", qid="Q21"),
    Cls("court-decision", "court decision",
        "A judicial opinion; here, one that cites a provision modelled by lexflow.", qid="Q22"),
    Cls("legal-role", "legal role",
        "A party or office that acts in a legal process (a bearer of duties and permissions).", qid="Q23"),
    # new class items (docs/design/wikibase-schema.md section 2)
    Cls("legal-code", "legal code",
        "A jurisdiction's code of laws (Virginia Code, D.C. Code, Fla. Stat.); one item per code.", "Q922203"),
    Cls("statutory-unit", "statutory unit",
        "A title, subtitle, part, chapter, article or subchapter of a code; its level is a claim."),
    Cls("regulation", "regulation", "An administrative code section (a rule issued by an agency).", "Q11861227"),
    Cls("government", "government", "A Census government: a city, county, town or similar local government."),
    Cls("government-agency", "government agency",
        "A department, board, commission or office with standing of its own.", "Q327333"),
    Cls("organizational-unit", "organizational unit", "A division or section inside an agency.", "Q10387680"),
    Cls("court", "court", "A court or court system.", "Q41487"),
    Cls("office-type", "office type",
        "A body each county, profession or record holder has (the clerk of the circuit court)."),
    Cls("position", "position", "A post that exists apart from its holder (Secretary of State of Florida).",
        "Q294414"),
    Cls("position-type", "position type", "A post every body of a kind has (the FOIA officer of a public body)."),
    Cls("process-outcome", "process outcome", "An end state of a process (records released, deemed denied)."),
    Cls("escalation-mechanism", "escalation mechanism",
        "One rung of an escalation ladder: an appeal, petition, review, referral or complaint path the law creates."),
    Cls("statutory-power", "statutory power",
        "What a body may do under a statute (deny a licence, extend time, decide an appeal)."),
    Cls("government-form", "government form", "An official form or online application a step uses.", "Q1335296"),
    Cls("topic", "topic", "Vocabulary: what a process or provision is about."),
    Cls("audience", "audience", "Vocabulary: who a process is for."),
    Cls("review-status", "review status", "Vocabulary: how far lexflow's review of an item has gone."),
    Cls("time-unit", "time unit", "Vocabulary: the unit of a time limit, in the law's own word."),
    Cls("reference-type", "reference type", "Vocabulary: why one provision cites another (lexflow.law.xref.ROLES)."),
    Cls("step-kind", "step kind", "Vocabulary: the kind of a process step (facts.steps[].kind)."),
    Cls("unit-level", "unit level", "Vocabulary: the level of a code, unit or section in the code's hierarchy."),
    Cls("escalation-type", "escalation type",
        "Vocabulary: the ten mechanism types of fixtures/authority/ladders.json."),
    Cls("determination-method", "determination method",
        "Vocabulary: how a claim or match was made (lexflow's software, an AI verifier, a person, an HTTP check)."),
    Cls("defined-term", "defined term", "A term a provision defines (the terms plan).", "Q2135465"),
    Cls("concept", "concept", "A legal concept a defined term or role stands for (the terms plan).", "Q2135465"),
    Cls("legal-document", "legal document", "A document the law names (the terms plan).", "Q49848"),
    Cls("legal-status", "legal status", "A status in law (the terms plan).", "Q2628882"),
]
CLASS_BY_SLUG: dict[str, Cls] = {c.slug: c for c in CLASSES}
CLASS_BY_LABEL: dict[str, Cls] = {c.label: c for c in CLASSES}


# --------------------------------------------------------------------------- vocabularies


@dataclass(frozen=True)
class Voc:
    slug: str
    label: str
    description: str


def _voc(pairs: list[tuple[str, str, str]]) -> list[Voc]:
    return [Voc(s, l, d) for s, l, d in pairs]


VOCAB: dict[str, list[Voc]] = {
    "topic": _voc([
        ("public-records", "public records", "Requesting, inspecting and copying public records."),
        ("business", "business", "Forming, registering and licensing a business."),
        ("building-and-zoning", "building and zoning", "Building permits, zoning and land use."),
        ("taxes", "taxes", "Assessment, billing, relief and appeal of taxes."),
        ("voting", "voting", "Registering to vote and voting."),
        ("courts", "courts", "Court filings, tickets, small claims and probate."),
        ("animals", "animals", "Animal licences and control."),
        ("property", "property", "Deeds, assessments and property records."),
        ("benefits", "benefits", "Public benefits and assistance."),
        ("licensing", "licensing", "Occupational and activity licences and permits."),
        ("criminal-records", "criminal records", "Sealing, expungement and correction of criminal records."),
    ]),
    "audience": _voc([
        ("resident", "resident", "A person who lives in the jurisdiction."),
        ("business", "business", "A business or its owner."),
        ("visitor", "visitor", "A person visiting the jurisdiction."),
        ("property-owner", "property owner", "An owner of real or personal property."),
        ("requester", "requester", "A person asking a public body for records."),
        ("applicant", "applicant", "A person applying for a licence, permit, benefit or filing."),
    ]),
    "review-status": _voc([
        ("reviewed", "reviewed", "A person reviewed the model and every quote was checked."),
        ("agreed", "agreed", "Two independent extractions agree, or lexflow's software matched every quote and "
                             "the AI verifier passed it; no person has signed."),
        ("draft", "draft", "One extraction, unreviewed; may be retired, never deleted."),
        ("superseded", "superseded", "Replaced by a later item; kept, relabelled, no longer maintained."),
    ]),
    "time-unit": _voc([
        ("calendar-days", "calendar days", "Days counted on the calendar."),
        ("business-days", "business days", "Days other than Saturdays, Sundays and legal holidays, in the law's "
                                           "words \"business days\"."),
        ("working-days", "working days", "The law's own word \"working days\"."),
        ("work-days", "work days", "The law's own word \"work days\"."),
        ("hours", "hours", "Hours."),
        ("weeks", "weeks", "Weeks."),
        ("months", "months", "Months."),
        ("years", "years", "Years."),
    ]),
    # lexflow.law.xref.ROLES, verbatim
    "reference-type": _voc([
        ("definition", "definition", "The cited provision defines a term the citing one uses."),
        ("override", "override", "The cited provision prevails over the citing one (\"notwithstanding\")."),
        ("exception", "exception", "The cited provision is an exception to the citing one."),
        ("penalty", "penalty", "The cited provision sets the penalty for the citing one."),
        ("prerequisite_process", "prerequisite process", "The cited provision's process must be completed first."),
        ("authority", "authority", "The cited provision confers the authority the citing one exercises."),
        ("procedure", "procedure", "The cited provision supplies the procedure the citing one follows."),
        ("condition", "condition", "The cited provision states a condition of the citing one."),
        ("scope", "scope", "The cited provision bounds the citing one's scope."),
        ("other", "other", "A cross-reference of no classified role."),
    ]),
    # facts.steps[].kind, as the curated models use it
    "step-kind": _voc([
        ("filing", "filing", "A request, application or document is filed."),
        ("notice", "notice", "A notice is given."),
        ("decision", "decision", "A body decides."),
        ("act", "act", "An act other than a filing, notice, decision or payment."),
        ("payment", "payment", "A fee or tax is paid."),
        ("record", "record", "A record is made, kept or delivered."),
        ("inspection", "inspection", "Records or premises are inspected."),
        ("hearing", "hearing", "A hearing is held."),
        ("review", "review", "A decision is reviewed."),
        ("delivery", "delivery", "Records or a document are delivered."),
    ]),
    "unit-level": _voc([
        ("code", "code", "A code of laws, or a named code inside a state's collection of codes."),
        ("title", "title", "A title."), ("subtitle", "subtitle", "A subtitle."), ("part", "part", "A part."),
        ("division", "division", "A division."), ("chapter", "chapter", "A chapter."),
        ("subchapter", "subchapter", "A subchapter."), ("article", "article", "An article."),
        ("act", "act", "An act (an Illinois compiled statutes act)."), ("section", "section", "A section."),
        ("subsection", "subsection", "A subsection."),
    ]),
    # fixtures/authority/ladders.json vocabulary.type
    "escalation-type": _voc([
        ("internal-appeal", "internal appeal", "Review, reconsideration, rehearing or a cure demand addressed to "
                                               "the same body (or its head, full board, or designee)."),
        ("external-administrative-review", "external administrative review",
         "Review or a binding ruling by a different administrative body."),
        ("ombudsman-mediation", "ombudsman/mediation", "A neutral who tries to settle the dispute and cannot compel."),
        ("advisory-opinion", "advisory opinion", "A non-binding opinion, guideline or eligibility predetermination."),
        ("compliance-board", "compliance board",
         "A standing body that decides complaints and can order the custodian to act."),
        ("judicial-review", "judicial review", "Any court proceeding: petition, suit, mandamus, appeal, writ."),
        ("oversight-inspector-general", "oversight/inspector general",
         "Complaint, reporting, discipline or enforcement by an oversight office or prosecutor."),
        ("referral", "referral", "The process hands the matter, a notice or a record to another body."),
        ("delegation", "delegation", "A body hands its authority to a designee, officer, panel or hearing office."),
        ("deferral-to-another-process", "deferral to another process",
         "The process waits on, is tolled by, or falls back to another body's decision or another process."),
    ]),
    "determination-method": _voc([
        ("software-match", "matched by lexflow's software", "lexflow's software found the quote verbatim in the "
                                                            "cited text."),
        ("ai-verifier", "AI verifier", "An AI verifier checked the claim against its sources."),
        ("curated", "curated", "A person curated or reviewed the claim."),
        ("http-check", "HTTP check", "An HTTP request confirmed the page or address."),
        ("official-page", "found on official page", "The value was read from the body's own official page."),
    ]),
}
VOCAB_BY_KEY: dict[str, Voc] = {f"lexflow:vocab:{s}:{v.slug}": v for s, vs in VOCAB.items() for v in vs}


# --------------------------------------------------------------------------- properties


@dataclass(frozen=True)
class Prop:
    number: int                           # the doc's number (section 3); the four SKOS matches share 60
    label: str
    datatype: str                         # QuickStatements spelling: item, string, url, time, quantity,
    #                                       monolingualtext, external-id
    wikidata: str | None                  # the exact equivalent Wikidata property (P7 on the property), else None
    description: str
    formatter_url: str | None = None      # property 2 on this property
    formatter_rdf: str | None = None      # property 3 on this property
    allowed: tuple[str, ...] = ()         # kinds of item the value may be (item properties) or of literal


def _p(number, label, datatype, wikidata, description, allowed=(), formatter_url=None, formatter_rdf=None):
    return Prop(number, label, datatype, wikidata, description, formatter_url, formatter_rdf, tuple(allowed))


PROPERTIES: list[Prop] = [
    _p(1, "Wikidata item ID", "external-id", None, "The Wikidata item this item is the same as (the identity "
       "crosswalk; exact match keeps the SKOS IRI).", ("any",), "https://www.wikidata.org/wiki/$1",
       "http://www.wikidata.org/entity/$1"),
    _p(2, "formatter URL", "string", "P1630", "Template for a URL from the value of an external identifier.",
       ("property",)),
    _p(3, "formatter URI for RDF resource", "string", "P1921",
       "Template for an RDF IRI from the value of an external identifier.", ("property",)),
    _p(4, "unit level", "item", None, "The level of a code, unit or section in the code's hierarchy.",
       ("vocab:unit-level",)),
    _p(5, "act identifier", "external-id", None, "Open US Law's act_id of a section, or the prefix shared by a "
       "unit's sections.", ("section", "unit"), "https://lexflow.local/law/$1"),
    _p(6, "government ID", "external-id", None, "The Census Bureau government ID (GID).", ("government",),
       "https://lexflow.local/places/$1"),
    _p(7, "sort key", "string", None, "Zero-padded key that orders units, sections and steps in the code's or "
       "the process's order.", ("unit", "section", "step")),
    _p(8, "section number", "string", None, "The bare section number; citation keeps the full citation.",
       ("section",)),
    _p(9, "effective until", "time", None, "The date the provision ceases to be in force (effective date is the "
       "date from).", ("section", "unit")),
    _p(10, "replaced by", "item", "P1366", "The section that replaces this version.", ("section",)),
    _p(11, "heading text", "monolingualtext", None, "The heading of a section, unit, decision point or rung, as "
       "searchable text.", ("section", "unit", "decision", "rung")),
    _p(12, "reference type", "item", None, "Qualifier on references: why the provision cites the other.",
       ("vocab:reference-type",)),
    _p(13, "quoted text", "string", None, "Reference: up to 400 characters of the statute, verbatim, that ground "
       "the claim.", ("reference",)),
    _p(14, "source section", "item", None, "Reference: the section the quoted text is from.", ("section",)),
    _p(15, "pinpoint", "string", None, "Reference or qualifier: the subsection (B.4, (g)).", ("reference",)),
    _p(16, "source URL", "url", "P854", "Reference: the official page a claim was made from.", ("reference",)),
    _p(17, "retrieved", "time", "P813", "Reference: the date lexflow fetched or checked the source.",
       ("reference",)),
    _p(18, "archive URL", "url", "P1065", "Reference: the Internet Archive capture read when the live page "
       "refused automated reading.", ("reference",)),
    _p(19, "determination method", "item", "P459", "Reference: how the claim or match was made.",
       ("vocab:determination-method",)),
    _p(20, "played by", "item", None, "The body, office type, position type or private party that plays a role.",
       ("agency", "unit", "office-type", "court", "position-type", "private-party")),
    _p(21, "head position", "item", "P2388", "The position that heads the agency.", ("position",)),
    _p(22, "position in", "item", "P2389", "The agency a position belongs to (never part of).", ("agency",)),
    _p(23, "appointed by", "item", "P748", "Who appoints the position.", ("position", "agency")),
    _p(24, "supervised by", "item", None, "The agency or position that supervises the agency (statute only).",
       ("agency", "position")),
    _p(25, "designee of", "item", None, "The position or position type a designee stands for.",
       ("position", "position-type")),
    _p(26, "authority conferred by", "item", None, "The section that confers the body's or role's authority; "
       "qualifiers power and quoted text.", ("section",)),
    _p(27, "power", "item", None, "Qualifier on authority conferred by: the statutory power conferred.",
       ("power",)),
    _p(28, "official website", "url", "P856", "The body's or government's official website.",
       ("agency", "government", "jurisdiction")),
    _p(29, "contact page URL", "url", "P11266", "The records page, the permits page: the page to start from.",
       ("agency", "government", "process")),
    _p(30, "email address", "url", "P968", "An office mailbox (mailto:), never a person's.",
       ("agency", "government", "process")),
    _p(31, "phone number", "string", "P1329", "A main office line, never a direct line.",
       ("agency", "government", "process")),
    _p(32, "postal address", "string", None, "An office address, with any staff name removed.",
       ("agency", "government", "process")),
    _p(33, "described at URL", "url", "P973", "The body's Govdirectory page (linked, never copied).", ("agency",)),
    _p(34, "step kind", "item", None, "The kind of a step.", ("vocab:step-kind",)),
    _p(35, "recipient", "item", None, "The role that receives the filing or notice.", ("role",)),
    _p(36, "time limit", "quantity", None, "A time limit; qualifiers time unit, counted from, on expiry; "
       "reference quoted text.", ("step", "rung", "process")),
    _p(37, "time unit", "item", None, "Qualifier on time limit: the unit, in the law's own word.",
       ("vocab:time-unit",)),
    _p(38, "counted from", "string", None, "Qualifier on time limit: the event the limit runs from.", ("step",)),
    _p(39, "on expiry", "item", None, "Qualifier on time limit: the outcome when the limit passes.",
       ("outcome",)),
    _p(40, "outcome", "item", None, "An end state of the process or step.", ("outcome",)),
    _p(41, "escalates to", "item", None, "Statutory escalation from a step, role or process; qualifiers "
       "quoted text, source section, pinpoint, time limit, defers to.",
       ("rung", "role", "agency", "position", "court", "office-type", "position-type")),
    _p(42, "defers to", "item", None, "Referral, forwarding or concurrence to another body or process.",
       ("rung", "role", "agency", "position", "court", "office-type", "position-type", "process")),
    _p(43, "escalation type", "item", None, "The mechanism type of a rung.", ("vocab:escalation-type",)),
    _p(44, "form used", "item", None, "The government form a step or process uses.", ("form",)),
    _p(45, "form number", "string", None, "The form's number (DC-495); official text holds its URL.", ("form",)),
    _p(46, "fee", "quantity", None, "A fee in US dollars; qualifiers source URL, quoted text, fee basis.",
       ("step", "process")),
    _p(47, "fee basis", "string", None, "Qualifier on fee: the rule when the amount is not one number.",
       ("step", "process")),
    _p(48, "topic", "item", None, "What the process, section or form is about.", ("vocab:topic",)),
    _p(49, "audience", "item", None, "Who the process is for.", ("vocab:audience",)),
    _p(50, "question asked", "monolingualtext", None, "The plain-language question the process answers.",
       ("process",)),
    _p(51, "review status", "item", None, "How far lexflow's review has gone.", ("vocab:review-status",)),
    _p(52, "checked on", "time", None, "The date lexflow's software last matched the quotes.",
       ("process", "local-process")),
    _p(53, "court", "item", None, "The court that decided the decision.", ("court", "agency")),
    _p(54, "date decided", "time", "P577", "The date the decision was filed.", ("case",)),
    _p(55, "CourtListener ID", "external-id", None, "The CourtListener opinion cluster id.", ("case",),
       "https://www.courtlistener.com/opinion/$1/"),
    _p(56, "defined in", "item", None, "The section that defines the term (terms plan).", ("section",)),
    _p(57, "scope", "item", None, "The unit or section a definition applies to (terms plan).",
       ("unit", "section")),
    _p(58, "concept", "item", None, "The concept a defined term stands for (terms plan).", ("concept",)),
    _p(59, "role of actor", "item", None, "The defined term or concept a role stands for (terms plan).",
       ("defined-term", "concept")),
    _p(60, "close match", "url", None, "skos:closeMatch to an external IRI (terms plan).", ("concept",)),
    _p(60, "broad match", "url", None, "skos:broadMatch to an external IRI (terms plan).", ("concept",)),
    _p(60, "narrow match", "url", None, "skos:narrowMatch to an external IRI (terms plan).", ("concept",)),
    _p(60, "related match", "url", None, "skos:relatedMatch to an external IRI (terms plan).", ("concept",)),
    _p(61, "match probability", "quantity", None, "Qualifier on exact match and the SKOS matches: the "
       "probability of the match (terms plan).", ("qualifier",)),
]
PROP_BY_LABEL: dict[str, Prop] = {p.label: p for p in PROPERTIES}

# the 25 live properties, reused unchanged (P1-P4 are the sandbox's and are left alone)
EXISTING: dict[str, str] = {
    "instance of": "P5", "subclass of": "P6", "equivalent property": "P7", "exact match": "P8", "part of": "P9",
    "has part": "P10", "follows": "P11", "followed by": "P12", "references": "P13", "based on": "P14",
    "applies to jurisdiction": "P15", "deontic modality": "P16", "bearer": "P17", "condition": "P18",
    "governed by norm": "P19", "sanction": "P20", "defeated by": "P21", "citation": "P22", "official text": "P23",
    "effective date": "P24", "legal identifier": "P25",
}
EXISTING_DATATYPES: dict[str, str] = {
    "instance of": "item", "subclass of": "item", "equivalent property": "url", "exact match": "url",
    "part of": "item", "has part": "item", "follows": "item", "followed by": "item", "references": "item",
    "based on": "item", "applies to jurisdiction": "item", "deontic modality": "item", "bearer": "item",
    "condition": "item", "governed by norm": "item", "sanction": "item", "defeated by": "item",
    "citation": "string", "official text": "url", "effective date": "time", "legal identifier": "external-id",
}


def datatype_of(label: str) -> str:
    """The QuickStatements datatype of a property, existing or new."""
    if label in EXISTING_DATATYPES:
        return EXISTING_DATATYPES[label]
    return PROP_BY_LABEL[label].datatype


ALL_PROPERTY_LABELS: tuple[str, ...] = tuple(EXISTING) + tuple(p.label for p in PROPERTIES)

WIKIDATA_ENTITY = "http://www.wikidata.org/entity/"
USD = "lexflow:vocab:currency:usd"        # the unit item of a fee (created with the vocabularies)
VOCAB["currency"] = _voc([("usd", "US dollar", "United States dollar, the unit of every fee.")])
VOCAB_BY_KEY[USD] = VOCAB["currency"][0]
CLASSES.append(Cls("currency", "currency", "Vocabulary: the unit of a fee.", "Q8142"))
CLASS_BY_SLUG["currency"] = CLASSES[-1]
CLASS_BY_LABEL["currency"] = CLASSES[-1]

PRIVATE_PARTY = "lexflow:private-party"

# The canonical key of a class item is ``lexflow:class:<slug>`` (``key_for("class", slug)``).  An earlier loader
# wrote three class items with the class LABEL in the key (``lexflow:class:court decision``, measured on the wiki on
# 15 October 2026: Q21 jurisdiction, Q22 court decision, Q23 legal role).  Those keys are never reused for new
# items; the graph emits each as a second ``legal identifier`` value on the existing class item (an alias key), so
# the resolver finds the item by either form and nothing is duplicated.  ``legacy_class_key`` gives the label form
# for any class; ``LEGACY_CLASS_KEYS`` lists the ones the wiki is known to hold.
LEGACY_CLASS_KEYS: dict[str, str] = {
    "jurisdiction": "lexflow:class:jurisdiction",
    "court-decision": "lexflow:class:court decision",
    "legal-role": "lexflow:class:legal role",
}


def legacy_class_key(slug_: str) -> str:
    """The label-form key the old loader minted for a class (``lexflow:class:court decision``); equal to the
    canonical key when the label is one word (``lexflow:class:jurisdiction``)."""
    return "lexflow:class:" + CLASS_BY_SLUG[slug_].label


# limits of the wiki (docs section 4): labels and descriptions 250, strings 400
LABEL_MAX = 250
DESCRIPTION_MAX = 250
STRING_MAX = 400


# --------------------------------------------------------------------------- vocabulary maps

# facts.steps[].deadline.unit -> time-unit slug; the law's own word wins when the quote has it (time_unit_for)
TIME_UNITS: dict[str, str] = {
    "days": "calendar-days", "calendar_days": "calendar-days", "business_days": "business-days",
    "working_days": "working-days", "work_days": "work-days", "hours": "hours", "weeks": "weeks",
    "months": "months", "years": "years",
}
_OWN_WORDS = (("working day", "working-days"), ("work day", "work-days"), ("business day", "business-days"),
              ("calendar day", "calendar-days"))


def time_unit_for(unit: str | None, quote: str | None = None) -> str | None:
    """The time-unit vocabulary slug for a model's unit, preferring the law's own word when the quote has it
    (``working days`` is not ``business days``)."""
    q = (quote or "").lower()
    base = TIME_UNITS.get((unit or "").lower())
    if base in ("business-days", "working-days", "work-days"):
        for word, slug in _OWN_WORDS:
            if word in q:
                return slug
    return base


ESCALATION_TYPES: dict[str, str] = {v.label: v.slug for v in VOCAB["escalation-type"]}
ESCALATION_TYPES.update({"oversight": "oversight-inspector-general", "deferral": "deferral-to-another-process",
                         "ombudsman or mediation": "ombudsman-mediation", "ombudsman": "ombudsman-mediation",
                         "mediation": "ombudsman-mediation"})

# the questions' topics and audiences
QUESTION_TOPIC: dict[str, str] = {"records": "public-records", "business": "business"}
QUESTION_AUDIENCE: dict[str, str] = {"records": "requester", "business": "business"}
# place process categories (curated/places/<st>/<place>/<process>.json: category) -> topic slug
CATEGORY_TOPIC: dict[str, str] = {
    "records": "public-records", "business": "business", "business_licensing": "business",
    "building_zoning": "building-and-zoning", "building": "building-and-zoning", "zoning": "building-and-zoning",
    "taxes_assessments": "taxes", "tax_relief": "taxes", "taxes": "taxes", "voting": "voting",
    "elections": "voting", "courts": "courts", "transportation_parking": "courts", "animals": "animals",
    "property": "property", "benefits": "benefits", "licensing": "licensing", "vital_records": "property",
    "criminal_records": "criminal-records",
}
AUDIENCES: dict[str, str] = {"residents": "resident", "resident": "resident", "businesses": "business",
                             "business": "business", "visitors": "visitor", "visitor": "visitor",
                             "property owners": "property-owner", "property_owners": "property-owner",
                             "requesters": "requester", "applicants": "applicant"}

# the closed list of rung subtype codes (authority-escalation.md section 1.3): the fixture's free-text subtype
# maps to a code and is never slugged; a subtype not listed here gets no rung until it is added
SUBTYPE_CODES: dict[str, str] = {
    "30-day record hold pending suit": "record-hold",
    "APA appeal or petition (either)": "apa-appeal",
    "APA court review": "apa-court-review",
    "APA hearing on the record": "apa-hearing",
    "Article 78 proceeding": "article-78",
    "Court of Claims complaint, referred to mediation": "court-of-claims-complaint",
    "OAH hearing, appeal to the board": "oah-hearing-board-appeal",
    "action to compel disclosure (immediate hearing)": "action-to-compel",
    "administrative appeal of the assessment": "assessment-appeal",
    "administrative mandamus (CCP § 1094.5)": "administrative-mandamus",
    "administrative review of a binding opinion": "review-of-binding-opinion",
    "advisory opinion": "advisory-opinion",
    "advisory opinion (public bodies only)": "advisory-opinion-public-bodies",
    "advisory opinion or guideline": "advisory-opinion-guideline",
    "advisory opinion to public bodies": "advisory-opinion-to-public-bodies",
    "annual disclosure report": "annual-report",
    "any appropriate legal remedy, with court costs": "legal-remedy",
    "appeal": "appeal",
    "appeal of Board decision (automatic stay)": "board-decision-appeal",
    "appeal of right from the Commission (exclusive)": "appeal-of-right",
    "appeal to the Tax Commissioner": "tax-commissioner-appeal",
    "application to correct an erroneous assessment": "assessment-correction",
    "automatic sealing pipeline": "automatic-sealing",
    "binding criminal history evaluation letter": "evaluation-letter",
    "binding predetermination": "predetermination",
    "certificate bars a conviction-based denial": "certificate-bar",
    "certificate of rehabilitation petition": "rehabilitation-certificate",
    "civil action with immediate hearing": "civil-action",
    "civil appeal": "civil-appeal",
    "collection suspended pending the appeal": "collection-suspended",
    "complaint (de novo, expedited)": "complaint",
    "complaint escalated to the attorney general": "complaint-to-attorney-general",
    "complaint for failure to respond": "failure-to-respond-complaint",
    "consultation (extension ground)": "consultation-extension",
    "consultation (unusual circumstances)": "consultation",
    "contested case heard by SOAH": "contested-case",
    "copy of each appeal and determination": "appeal-copy",
    "copy to the prosecutor": "prosecutor-copy",
    "corrected refiling": "corrected-refiling",
    "corrected resubmission keeping the original filing date": "corrected-resubmission",
    "cure complaint (mandatory wait)": "cure-complaint",
    "custodian decides the charge": "charge-decision",
    "custodian fixed by law": "custodian-fixed",
    "custodian's designee": "custodian-designee",
    "designated contact in the conference notice": "designated-contact",
    "designated officer": "designated-officer",
    "designated point of contact": "point-of-contact",
    "direct suit (no Mayor review)": "direct-suit",
    "disciplinary referral": "disciplinary-referral",
    "dismissal bars a conviction-based denial": "dismissal-bar",
    "disposition report to the state repository": "disposition-report",
    "dispute resolution (cannot compel)": "dispute-resolution",
    "early disqualification petition": "disqualification-petition",
    "enforcement complaint to a prosecutor": "enforcement-complaint",
    "exclusive custodian": "exclusive-custodian",
    "extension reserved to the head or a designee": "extension-by-head",
    "fall back to petition relief": "petition-relief-fallback",
    "fall back to petition sealing": "petition-sealing-fallback",
    "fee complaint (notice duty)": "fee-complaint",
    "formal hearing at the agency's option": "formal-hearing",
    "hearing before the board": "board-hearing",
    "hearing conducted by OAH": "oah-hearing",
    "hearing delegated to OAH": "oah-delegation",
    "injunctive or declaratory relief, or writ of mandate": "injunctive-relief-or-mandate",
    "internal search and location": "internal-search",
    "local licence waits on the Commission's assumed-name certificate": "assumed-name-prerequisite",
    "local receipt waits on the Division's fictitious-name registration (or a signed statement)":
        "registration-prerequisite",
    "mandamus action": "mandamus",
    "mandatory hearing": "mandatory-hearing",
    "mandatory notice to the prosecutor": "prosecutor-notice",
    "mandatory request for an open records decision": "open-records-decision",
    "motion for rehearing (prerequisite to appeal)": "rehearing-motion",
    "motion: automatic sealing voidable": "sealing-voidable-motion",
    "motion: order voidable": "order-voidable-motion",
    "notice of expungement to other custodians": "expungement-notice-custodians",
    "notice of the automatic expungement date": "expungement-date-notice",
    "notice of the general expungement petition": "expungement-petition-notice",
    "notice of the order": "order-notice",
    "notice that a decision is due; deemed approval": "decision-due-notice",
    "notice to affected third parties (time ground)": "third-party-notice-time",
    "notice to affected third party": "third-party-notice",
    "onward notice to other holders": "onward-notice",
    "overcharge complaint": "overcharge-complaint",
    "panel decision, optional full-board rehearing": "panel-decision",
    "petition for extraordinary writ (no appeal)": "extraordinary-writ",
    "petition for judicial review": "judicial-review-petition",
    "petition for mandamus or injunction": "court-petition",
    "petition for more time": "time-petition",
    "petition for reconsideration": "reconsideration",
    "petition for review": "review-petition",
    "petition to block DOJ relief": "relief-block-petition",
    "petition to compel filing": "petition-to-compel-filing",
    "petition to compel filing (summary proceeding)": "summary-petition-to-compel-filing",
    "petition to correct Commission records": "record-correction-petition",
    "petition to the Mayor (hierarchical review of any public body)": "mayor-petition",
    "point to the right custodian": "custodian-redirect",
    "pre-suit notice (condition of a fee award)": "pre-suit-notice",
    "prompt internal review (deemed complete)": "internal-review",
    "protest to the board": "board-protest",
    "public comment on quality of assistance": "public-comment",
    "reapplication": "reapplication",
    "record correction request": "record-correction-request",
    "record correction route the notice must describe": "record-correction-route",
    "record forwarded to the court": "record-forwarded",
    "redirect to custodian": "custodian-redirect",
    "redirect to mandamus": "mandamus-redirect",
    "request for a contested-case hearing": "hearing-request",
    "request for review (binding opinion or mediation)": "review-request",
    "request to disqualify a member": "disqualification-request",
    "response to notice of intended denial": "denial-response",
    "response to the notice": "notice-response",
    "review yields to the lawsuit": "review-yields",
    "service on the prosecutor": "prosecutor-service",
    "show-cause motion": "show-cause-motion",
    "suit for declaratory relief from the ruling": "declaratory-suit",
    "suit for injunctive or declaratory relief": "injunctive-suit",
    "suit for injunctive or declaratory relief (de novo)": "injunctive-suit-de-novo",
    "suit for writ of mandamus": "mandamus-suit",
    "suit to compel production": "suit-to-compel",
    "suspension, removal or impeachment of the officer": "officer-removal",
    "time limits extended pending dispute resolution": "time-extended",
    "tolling": "tolling",
    "verified petition (order to disclose or show cause)": "verified-petition",
    "voluntary mediation": "fee-mediation",
    "voluntary pre-suit mediation": "pre-suit-mediation",
    "who hears the case": "hearing-assignment",
    "writ of mandate": "writ-of-mandate",
    "written administrative appeal": "written-appeal",
    "written complaint for a decision and order": "written-complaint",
    "written opinion on the exemption": "exemption-opinion",
    "written request for a formal hearing (vacates the committee's order)": "formal-hearing-request",
    "written request for hearing": "hearing-request",
}


def subtype_code(subtype: str | None) -> str | None:
    """The closed code for a rung's free-text subtype, or None when the list lacks it (then no rung is minted
    and the build logs it).  Curly apostrophes and the section sign's spelling do not matter."""
    s = re.sub(r"\s+", " ", (subtype or "").replace("’", "'").replace("�", "§")).strip()
    return SUBTYPE_CODES.get(s)


# --------------------------------------------------------------------------- keys

_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
    "district of columbia", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas",
    "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "puerto rico",
}
_LEAD = re.compile(r"^(?:the\s+)?(?:state\s+of\s+|commonwealth\s+of\s+)?(?:" +
                   "|".join(sorted((re.escape(n) for n in _STATE_NAMES), key=len, reverse=True)) +
                   r")\b\s*", re.I)
SLUG_MAX = 48
_SLUG_OK = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def slug(name: str, sep: str = "_") -> str:
    """The slug of a body's or post's name (entities-contacts.md section 1.2): lower-case ASCII words joined by
    ``_``, at most 48 characters (cut at a word boundary), with a leading state name and "the" dropped.
    ``"Virginia State Corporation Commission"`` -> ``state_corporation_commission``.  A name that already is a
    slug is kept as it is."""
    s = (name or "").strip()
    if _SLUG_OK.match(s) and len(s) <= SLUG_MAX:
        return s
    s = re.sub(r"\([^)]*\)", " ", s)                  # "(Tax Commissioner)" is a remark, not the name
    s = _LEAD.sub("", s)
    s = re.sub(r"^the\s+", "", s, flags=re.I)
    s = s.lower().replace("&", " and ")
    s = s.encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", s)
    out = ""
    for w in words:
        cand = f"{out}{sep}{w}" if out else w
        if len(cand) > SLUG_MAX:
            break
        out = cand
    return out or "unnamed"


def unit_tokens(act_id: str) -> list[str]:
    """``STATE_VA_T2.2_SII_PB_C37_S2.2-3704`` -> ``['T2.2', 'SII', 'PB', 'C37', 'S2.2-3704']`` (the tokens after
    the state)."""
    toks = (act_id or "").split("_")
    if len(toks) >= 2 and toks[0] == "STATE":
        toks = toks[2:]
    out: list[str] = []
    for t in toks:
        if not t:
            continue
        if out and t[0].isdigit():            # Minnesota's 'P13_13C' and Utah's 'S48_3a_1103' carry an underscore
            out[-1] += "_" + t
        else:
            out.append(t)
    return out


def unit_prefix(act_id: str, depth: int) -> str:
    """The act_id prefix of the unit ``depth`` tokens below the code: ``STATE_VA_T2.2_SII`` for depth 2."""
    toks = (act_id or "").split("_")
    head = toks[:2] if toks[:1] == ["STATE"] else []
    return "_".join(head + unit_tokens(act_id)[:depth])


def unit_slug(act_id_prefix: str) -> str:
    """The unit part of a unit key: the act_id tokens below the state, lower-cased, joined by ``-``
    (``STATE_VA_T2.2_SII_PB_C37`` -> ``t2.2-sii-pb-c37``)."""
    return "-".join(t.lower() for t in unit_tokens(act_id_prefix))


# the path's own word for a unit's level (``Title 2.2`` -> title; Puerto Rico's ``Ley`` is an act)
_LEVEL_WORDS: dict[str, str] = {"ley": "act", "§": "section", "sec": "section", "art": "article", "ch": "chapter",
                                "pt": "part", "div": "division", "subch": "subchapter", "subt": "subtitle"}
# an act_id token's level letter, when the path's word is not a level in the vocabulary
_LEVEL_LETTERS: dict[str, str] = {"T": "title", "S": "subtitle", "P": "part", "D": "division", "C": "chapter",
                                  "A": "article"}


def unit_level(path_element: str | None, token: str | None = None) -> str | None:
    """The unit-level vocabulary slug of a unit, from the path element's first word (``Chapter 37`` -> chapter)
    or, when that word is not a level, from the act_id token's letter (``T48`` -> title, ``SII`` -> subtitle,
    ``C3a`` -> chapter); an alphabetic token (``APBO``, ``TRANSPARENCIA``) is an act.  None when neither says."""
    word = (path_element or "").split()[0].lower().rstrip("s.") if (path_element or "").split() else ""
    word = _LEVEL_WORDS.get(word, word)
    if word and f"lexflow:vocab:unit-level:{word}" in VOCAB_BY_KEY:
        return word
    tok = (token or "").strip()
    if not tok:
        return None
    head, body = tok[:1].upper(), tok[1:]
    level = _LEVEL_LETTERS.get(head)
    if level and (not body or len(body) == 1 or _ROMAN.match(body.upper()) or any(ch.isdigit() for ch in body)):
        return level
    return "act" if tok.isalpha() else None


_ROMAN = re.compile(r"^[IVXLCDM]+$")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
PAD = 5


def _roman(s: str) -> int:
    total, prev = 0, 0
    for ch in reversed(s):
        v = _ROMAN_VALUES[ch]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total


def sort_key(act_id: str) -> str:
    """The string that orders units and sections in the code's order: each act_id token after the state, without
    its level letter, lower-cased, with every run of digits zero-padded to five places and a roman numeral
    turned into a number; tokens joined by ``-``.  ``STATE_VA_T2.2_SII_PB_C37_S2.2-3704`` ->
    ``00002.00002-00002-b-00037-00002.00002-03704``.  A unit's key is the prefix of its sections'."""
    out = []
    for tok in unit_tokens(act_id):
        body = tok[1:] if len(tok) > 1 else tok
        if _ROMAN.match(body):
            body = str(_roman(body))
        body = re.sub(r"\d+", lambda m: m.group(0).zfill(PAD), body.lower())
        out.append(body)
    return "-".join(out)


def code_token(act_id: str) -> str | None:
    """The code or act token of an act_id, lower-cased and without its letter prefix: ``gov`` from
    ``STATE_CA_Cgov_…``, ``pbo`` from ``STATE_NY_APBO_…``, ``140`` from ``STATE_IL_C5_A140_S3``; None for a
    single-code state (Virginia, Florida)."""
    toks = unit_tokens(act_id)[:-1]
    for t in toks:
        if t[:1] in ("C", "A") and t[1:].isalpha():
            return t[1:].lower()
    # Illinois: STATE_IL_C5_A140_S3 is chapter 5, act 140 (an article token after a title, as in Virginia's
    # STATE_VA_T13.1_C12_A1_S…, is not an act)
    if len(toks) >= 2 and toks[0][:1] == "C" and toks[0][1:].isdigit() and toks[1][:1] == "A" and toks[1][1:].isdigit():
        return toks[1][1:]
    return None


_PIN = re.compile(r"\(([^()]+)\)")


def section_slug(citation: str, act_id: str | None = None) -> str:
    """The ``<section-slug>`` of a rung key: the act_id's code token where it has one, the section number as the
    act_id spells it, then the pinpoint's parenthesised parts, lower-cased and joined by ``-``.
    ``("Va. Code Ann. § 2.2-3704(B)(3)", "STATE_VA_…_S2.2-3704")`` -> ``2.2-3704-b-3``;
    ``("Cal. GOV § 7922.535(b)", "STATE_CA_Cgov_…_S7922.535")`` -> ``gov-7922.535-b``."""
    cite = (citation or "").replace("�", "§")
    pins = [p.strip().lower() for p in _PIN.findall(cite)]
    parts = []
    if act_id:
        code = code_token(act_id)
        if code:
            parts.append(code)
        number = unit_tokens(act_id)[-1][1:]
    else:
        m = re.search(r"§\s*([\w.:\-/]+)|(\d[\w.:\-/]*)\s*(?:\(|$)", cite)
        number = (m.group(1) or m.group(2)) if m else re.sub(r"\s+", "", cite)
        number = number.split("(")[0]
    parts.append(number.lower())
    parts += [re.sub(r"[^a-z0-9.]+", "-", p).strip("-") for p in pins]
    return "-".join(p for p in parts if p)


def strip_pinpoint(citation: str) -> tuple[str, str | None]:
    """``"Va. Code Ann. § 2.2-3704(B)(3)"`` -> ``("Va. Code Ann. § 2.2-3704", "(B)(3)")``."""
    cite = (citation or "").replace("�", "§").strip()
    m = re.search(r"(\([^()]+\))+\s*$", cite)
    if not m:
        return cite, None
    return cite[:m.start()].strip(), m.group(0).strip()


def key_for(kind: str, *parts: str) -> str:
    """Every key form of the contract.  ``parts`` are the natural pieces; names are slugged where the form
    wants a slug, and a part that already is a slug is kept.

    code (st[, sub]) · unit (st, act_id prefix) · statute (st, ref) · regulation (st, ref) · gov (gid) ·
    agency (scope, name) · office-type (st, name) · position (scope, name) · position-type (st, name) ·
    role (st, question, actor) or (gid, process, actor) · process (model_id) or (gid, process) ·
    step (model_id, step) or (gid, process, step) · decision (model_id, id) · outcome (model_id, id) ·
    rung (st, question, section_slug, subtype_code) · form (gid, process, id) · vocab (set, slug) ·
    class (slug) · power (slug) · jurisdiction (st) · case (cluster_id) · private-party ()

    ``class``: the canonical form is ``lexflow:class:<slug>`` (``lexflow:class:court-decision``).  The label form
    an earlier loader wrote for three items (``lexflow:class:court decision``, ``LEGACY_CLASS_KEYS``) is an alias
    the graph keeps as a second legal identifier on the existing item; it is never minted for a new item.
    """
    p = [str(x) for x in parts]
    if kind == "code":
        return "lexflow:code:" + ":".join([p[0].lower()] + [x.lower() for x in p[1:]])
    if kind == "unit":
        return f"lexflow:unit:{p[0].lower()}:{unit_slug(p[1])}"
    if kind in ("statute", "regulation"):
        return f"lexflow:{kind}:{p[0].lower()}:{p[1].strip()}"
    if kind == "gov":
        return f"lexflow:gov:{p[0]}"
    if kind in ("agency", "office-type", "position", "position-type"):
        return f"lexflow:{kind}:{p[0].lower()}:{slug(p[1])}"
    if kind == "role":
        return f"lexflow:role:{p[0]}:{p[1]}:{p[2]}"
    if kind == "process":
        return "lexflow:process:" + ":".join(p)
    if kind == "step":
        return "lexflow:step:" + ":".join(p)
    if kind in ("decision", "outcome"):
        return f"lexflow:{kind}:{p[0]}:{p[1]}"
    if kind == "rung":
        return f"lexflow:rung:{p[0]}:{p[1]}:{p[2]}:{p[3]}"
    if kind == "form":
        return f"lexflow:form:{p[0]}:{p[1]}:{p[2]}"
    if kind == "vocab":
        return f"lexflow:vocab:{p[0]}:{p[1]}"
    if kind == "class":
        return f"lexflow:class:{p[0]}"
    if kind == "power":
        return f"lexflow:power:{slug(p[0], '-')}"
    if kind == "jurisdiction":
        return f"lexflow:jurisdiction:{p[0].lower()}"
    if kind == "case":
        return f"courtlistener:cluster:{p[0]}"
    if kind == "private-party":
        return PRIVATE_PARTY
    raise ValueError(f"unknown key kind {kind!r}")


def kind_of(key: str) -> str:
    """``lexflow:statute:va:2.2-3704`` -> ``statute``; ``courtlistener:cluster:7`` -> ``cluster``."""
    return key.split(":")[1] if ":" in key else key


def class_key(slug_: str) -> str:
    """The class reference the graph uses: the label of an existing class item, else ``lexflow:class:<slug>``."""
    c = CLASS_BY_SLUG[slug_]
    return c.label if c.qid else key_for("class", slug_)


def vocab_key(set_: str, slug_: str) -> str:
    k = key_for("vocab", set_, slug_)
    if k not in VOCAB_BY_KEY:
        raise KeyError(f"no vocabulary entry {k}")
    return k
