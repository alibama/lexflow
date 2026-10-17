"""Mappings from the Lexipedia schema to the published legal ontologies (docs/design/legal-ontologies.md).

Everything here is data.  ``schema.py`` imports it to append IRIs to each property's equivalents (``P7 equivalent
property``) and each class's exact matches (``P8 exact match``); ``lexflow.law.ontology`` uses the structure and
norm-type tables to say what a ``section_tags`` row means in those ontologies.

* ``PROPERTY_EQUIV``: lexflow property label (``schema.ALL_PROPERTY_LABELS``) -> IRIs the property is equivalent to.
  Written as ``P7`` on the property item, so a federated query can join on them.  Only exact or near-exact
  equivalents are here; looser kin are in ``PROPERTY_RELATED`` (documented, never written).
* ``CLASS_MATCH``: class slug (``schema.CLASS_BY_SLUG``) -> IRIs the class is the same as (``P8 exact match`` on
  the class item).  ``CLASS_CLOSE`` holds the ``skos:closeMatch`` kin (property 60, ``close match``).
* ``NORM_TYPE_MATCH``: the seven norm types ``lexflow.law.ontology`` tags a section with -> LKIF classes.
* ``STRUCTURE_MATCH``: each ``unit-level`` slug -> the Akoma Ntoso hierarchy element and the ELI type.
* ``ELI_TEMPLATE`` / ``eli_uri``: the ELI-style identifier lexflow mints for a section, unit or code.

Every IRI was checked against the ontology's own source file on 15 October 2026 (the files, not secondary pages:
``norm.owl`` and friends in github.com/RinkeHoekstra/lkif-core, ``http://data.europa.eu/eli/ontology`` as
RDF/XML, schema.org's ``schemaorg-current-https.ttl``, ``https://www.w3.org/ns/prov-o`` as Turtle, the SKOS
reference ``skos.rdf``, ``https://www.w3.org/ns/org``, ``https://www.w3.org/ns/lemon/ontolex``, DCMI terms, FIBO
``FND/Law/LegalCore.rdf`` and OASIS ``akomantoso30.xsd``).  ``resolve_all`` re-checks them read-only (HEAD/GET,
one request a second, cached); ``tests/test_ontology.py`` runs it when ``LEXFLOW_NET=1``.

The hook for ``schema.py`` (not applied here, since another change owns that file): after ``PROPERTIES`` and
``CLASSES`` are built, ::

    from . import ontology_map as OM
    for p in PROPERTIES:                       # Prop gains ``equivalents: tuple[str, ...] = ()``
        p = replace(p, equivalents=tuple(OM.PROPERTY_EQUIV.get(p.label, ())))
    for c in CLASSES:                          # Cls gains ``exact: tuple[str, ...] = ()``; ``wikidata`` stays
        c = replace(c, exact=tuple(OM.CLASS_MATCH.get(c.slug, ())))

and ``qs.py`` writes one ``P7`` line per equivalent (``LAST P7 "<iri>"``, url datatype) beside the Wikidata one,
one ``P8`` line per exact match beside the ``WIKIDATA_ENTITY`` one, and ``close match`` (property 60) for
``CLASS_CLOSE``.  ``EXISTING`` properties get theirs through ``05-updates.qs``.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

# --------------------------------------------------------------------------- namespaces
ELI = "http://data.europa.eu/eli/ontology#"
SCHEMA = "https://schema.org/"
PROV = "http://www.w3.org/ns/prov#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
ORG = "http://www.w3.org/ns/org#"
DCT = "http://purl.org/dc/terms/"
ONTOLEX = "http://www.w3.org/ns/lemon/ontolex#"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
FIBO_LAW = "https://spec.edmcouncil.org/fibo/ontology/FND/Law/LegalCore/"
# LKIF-Core's IRIs (estrellaproject.org) no longer dereference to the OWL files (the host answers with its home
# page, checked 15 October 2026); the source of truth is the GitHub repository, which ``DOCUMENTS`` points at.
LKIF = "http://www.estrellaproject.org/lkif-core/"
LKIF_RAW = "https://raw.githubusercontent.com/RinkeHoekstra/lkif-core/master/"
AKN_NS = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
AKN_XSD = "https://docs.oasis-open.org/legaldocml/akn-core/v1.0/os/part2-specs/schemas/akomantoso30.xsd"
USLM_XSD = "https://raw.githubusercontent.com/usgpo/uslm/main/USLM.xsd"


def lkif(module: str, name: str) -> str:
    return f"{LKIF}{module}.owl#{name}"


def eli(name: str) -> str:
    return ELI + name


def schema(name: str) -> str:
    return SCHEMA + name


def prov(name: str) -> str:
    return PROV + name


# --------------------------------------------------------------------------- properties
# label -> IRIs written as P7 equivalent property (exact or near-exact: same domain of use, same direction)
PROPERTY_EQUIV: dict[str, list[str]] = {
    # the existing 25
    "instance of": [RDF + "type"],
    "subclass of": [RDFS + "subClassOf"],
    "equivalent property": [OWL + "equivalentProperty"],
    "exact match": [SKOS + "exactMatch"],
    "part of": [eli("is_part_of"), schema("isPartOf")],
    "has part": [eli("has_part"), schema("hasPart")],
    "references": [eli("cites")],
    "based on": [eli("based_on")],
    "applies to jurisdiction": [eli("jurisdiction"), schema("legislationJurisdiction")],
    "citation": [schema("legislationIdentifier")],
    "official text": [schema("url")],
    "effective date": [eli("first_date_entry_in_force"), schema("legislationDateOfApplicability")],
    "legal identifier": [eli("id_local"), schema("identifier")],
    # the new ones (docs/design/wikibase-schema.md section 3)
    "unit level": [eli("type_subdivision")],
    "act identifier": [eli("id_local")],
    "government ID": [schema("identifier")],
    "section number": [eli("number")],
    "effective until": [eli("date_no_longer_in_force")],
    "replaced by": [DCT + "isReplacedBy", eli("changed_by")],
    "heading text": [eli("title"), schema("name")],
    "quoted text": [prov("value")],
    "source section": [prov("wasQuotedFrom")],
    "source URL": [prov("hadPrimarySource")],
    "retrieved": [prov("generatedAtTime")],
    "archive URL": [schema("archivedAt")],
    "determination method": [prov("wasAttributedTo")],
    "played by": [lkif("role", "played_by")],
    "position in": [ORG + "postIn"],
    "official website": [schema("url")],
    "email address": [schema("email")],
    "phone number": [schema("telephone")],
    "postal address": [schema("address")],
    "described at URL": [RDFS + "seeAlso"],
    "outcome": [schema("result")],
    "form number": [schema("identifier")],
    "topic": [eli("is_about"), schema("about")],
    "audience": [schema("audience")],
    "checked on": [schema("lastReviewed")],
    "concept": [ONTOLEX + "evokes"],
    "close match": [SKOS + "closeMatch"],
    "broad match": [SKOS + "broadMatch"],
    "narrow match": [SKOS + "narrowMatch"],
    "related match": [SKOS + "relatedMatch"],
}

# kin that are not equivalents (different direction, domain or granularity): documented, never written
PROPERTY_RELATED: dict[str, list[str]] = {
    "references": [schema("citation")],                  # citation takes a CreativeWork or text, any direction
    "replaced by": [schema("legislationChanges")],       # the inverse direction
    "bearer": [LKIF + "role.owl#plays"],                 # LegalRuleML's Bearer has no RDF IRI; LKIF's is agent-side
    "sanction": [],                                      # LegalRuleML PenaltyStatement: XML only, see the doc
    "fee": [schema("price")],                            # on an Offer, not on a step
    "time limit": [],                                    # nothing exact; LegalRuleML temporal is XML only
    "Wikidata item ID": [schema("sameAs")],              # an id string, not the IRI sameAs takes
    "court": [FIBO_LAW + "CourtOfLaw"],                  # a class, used as the range
}

# --------------------------------------------------------------------------- classes
# slug -> IRIs written as P8 exact match (beside the Wikidata one, where there is one)
CLASS_MATCH: dict[str, list[str]] = {
    "statute": [eli("LegalResourceSubdivision")],
    "norm": [lkif("norm", "Norm")],
    "obligation": [lkif("norm", "Obligation")],
    "permission": [lkif("norm", "Permission")],
    "prohibition": [lkif("norm", "Prohibition")],
    "right": [lkif("norm", "Right")],
    "jurisdiction": [eli("AdministrativeArea"), schema("AdministrativeArea")],
    "legal-role": [lkif("legal-role", "Legal_Role")],
    "legal-code": [lkif("norm", "Code"), eli("LegalResource"), schema("Legislation")],
    "statutory-unit": [eli("LegalResourceSubdivision")],
    "regulation": [lkif("norm", "Regulation")],
    "government": [schema("GovernmentOrganization"), ORG + "FormalOrganization"],
    "government-agency": [schema("GovernmentOrganization"), lkif("legal-action", "Public_Body"),
                          ORG + "FormalOrganization"],
    "organizational-unit": [ORG + "OrganizationalUnit"],
    "court": [FIBO_LAW + "CourtOfLaw"],
    "position": [ORG + "Post"],
    "statutory-power": [lkif("norm", "Hohfeldian_Power")],
    "unit-level": [eli("SubdivisionType")],
    "concept": [SKOS + "Concept"],
    "legal-document": [lkif("norm", "Legal_Document")],
}

# slug -> skos:closeMatch (property 60): the same idea at another granularity or with another emphasis
CLASS_CLOSE: dict[str, list[str]] = {
    "legal-process": [schema("GovernmentService"), LKIF + "process.owl#Process"],
    "legal-process-step": [lkif("action", "Action")],
    "decision-point": [lkif("legal-action", "Decision")],
    "statute": [schema("Legislation")],
    "deontic-specification": [lkif("norm", "Normatively_Qualified")],
    "court-decision": [lkif("legal-action", "Decision")],
    "legal-role": [lkif("role", "Role")],
    "statutory-unit": [AKN_XSD + "#hcontainer"],
    "regulation": [eli("LegalResourceSubdivision")],
    "office-type": [ORG + "Organization"],
    "position-type": [ORG + "Post", ORG + "Role"],
    "statutory-power": [lkif("norm", "Enabling_Power")],
    "government-form": [schema("DigitalDocument")],
    "topic": [SKOS + "ConceptScheme"],
    "audience": [SKOS + "ConceptScheme"],
    "defined-term": [lkif("norm", "Definitional_Expression"), ONTOLEX + "LexicalEntry"],
    "concept": [ONTOLEX + "LexicalConcept"],
    "legal-document": [LKIF + "expression.owl#Document"],
}

# --------------------------------------------------------------------------- norm types (section_tags.norm_types)
NORM_TYPES: tuple[str, ...] = ("definition", "obligation", "permission", "prohibition", "power", "penalty",
                               "procedure")
NORM_TYPE_MATCH: dict[str, list[str]] = {
    "definition": [lkif("norm", "Definitional_Expression")],
    "obligation": [lkif("norm", "Obligation")],
    "permission": [lkif("norm", "Permission")],
    "prohibition": [lkif("norm", "Prohibition")],
    "power": [lkif("norm", "Hohfeldian_Power"), lkif("norm", "Enabling_Power")],
    # LegalRuleML's PenaltyStatement is the match, but LegalRuleML publishes no RDF IRIs (its ns/v1.0/ URLs answer
    # 404, checked 15 October 2026): nothing to write; the doc says so
    "penalty": [],
    # lexflow's own: a section that lays down steps, filings, notices, deadlines or hearings; no ontology has it
    "procedure": [],
}

# --------------------------------------------------------------------------- structure (unit-level -> AKN, ELI)
# Akoma Ntoso 3.0 hierarchy elements (``type="hierarchy"`` in akomantoso30.xsd): clause section part paragraph
# chapter title book tome article division list point indent alinea rule subrule proviso subsection subpart
# subparagraph subchapter subtitle subdivision subclause sublist level transitional.  USLM 1.0 has the US ones.
AKN_HIERARCHY: frozenset[str] = frozenset(
    "clause section part paragraph chapter title book tome article division list point indent alinea rule subrule "
    "proviso subsection subpart subparagraph subchapter subtitle subdivision subclause sublist level "
    "transitional".split())
STRUCTURE_MATCH: dict[str, dict] = {
    # unit-level slug: the AKN element, the ELI class, the USLM element (None when USLM has none)
    "code": {"akn": "act", "eli": eli("LegalResource"), "uslm": None},   # akn:act is the document, not hierarchy
    "title": {"akn": "title", "eli": eli("LegalResourceSubdivision"), "uslm": "title"},
    "subtitle": {"akn": "subtitle", "eli": eli("LegalResourceSubdivision"), "uslm": "subtitle"},
    "part": {"akn": "part", "eli": eli("LegalResourceSubdivision"), "uslm": "part"},
    "division": {"akn": "division", "eli": eli("LegalResourceSubdivision"), "uslm": "division"},
    "chapter": {"akn": "chapter", "eli": eli("LegalResourceSubdivision"), "uslm": "chapter"},
    "subchapter": {"akn": "subchapter", "eli": eli("LegalResourceSubdivision"), "uslm": "subchapter"},
    "article": {"akn": "article", "eli": eli("LegalResourceSubdivision"), "uslm": "article"},
    "act": {"akn": "act", "eli": eli("LegalResource"), "uslm": None},
    "section": {"akn": "section", "eli": eli("LegalResourceSubdivision"), "uslm": "section"},
    "subsection": {"akn": "subsection", "eli": eli("LegalResourceSubdivision"), "uslm": "subsection"},
    # levels the paths carry that the unit-level vocabulary does not (Puerto Rico's libro, Louisiana's rules)
    "book": {"akn": "book", "eli": eli("LegalResourceSubdivision"), "uslm": None},
    "rule": {"akn": "rule", "eli": eli("LegalResourceSubdivision"), "uslm": None},
}

# --------------------------------------------------------------------------- ELI-style identifiers
# ELI's pattern is /eli/{jurisdiction}/{type}/{year}/{natural number}/{language}/{version} (ELI Council conclusions
# 2012/C 325/02, the template is each publisher's own).  lexflow's, per state, is
#   work:        {base}/us-{st}/{code}/{section}            e.g. /eli/us-va/code/2.2-3704, /eli/us-ca/gov/7922.535
#   unit:        {base}/us-{st}/{code}/unit/{unit slug}     e.g. /eli/us-va/code/unit/t2.2-sii-pb-c37
#   code:        {base}/us-{st}/{code}                      e.g. /eli/us-va/code, /eli/us-ca/gov
#   expression:  {work}/en@{effective_from}                 the version in force from that date (ISO date)
# {code} is ``schema.code_token(act_id)`` for a state with several codes (ca gov, ny pbo, tx ag, md gab, la
# childrens-code, il 5-140 as ``5-140``) and the word ``code`` for a single-code state (va, fl, dc ...).
# {section} is the section number as the act_id spells it (its last token without the level letter), so it is
# stable across index rebuilds; ``section_number`` from the index is the same string for every state checked.
# Nothing serves these yet: the base is the wiki's host and a redirect from /eli/ is the operator's step (the doc).
ELI_BASE = "https://lexipedia.wikibase.cloud/eli"
ELI_TEMPLATE = "{base}/us-{st}/{code}/{section}"
ELI_UNIT_TEMPLATE = "{base}/us-{st}/{code}/unit/{unit}"
ELI_VERSION_TEMPLATE = "{work}/en@{date}"


def eli_code(act_id: str) -> str:
    """The ``{code}`` token of a state's ELI template: ``bpc`` (California ``Cbpc``), ``abc`` (New York ``AABC``),
    ``gab`` (Maryland ``Agab``), ``childrens-code`` (Louisiana), ``ambiental`` (Puerto Rico's ``AMBIENTAL``),
    ``105-5`` (Illinois chapter 105, act 5: both, since act numbers repeat across chapters), else ``code``."""
    from . import schema as S
    toks = S.unit_tokens(act_id)
    if len(toks) < 2:
        return "code"
    first = toks[0]
    if act_id.startswith("STATE_PR_") and first.isalpha():                     # Puerto Rico's ley token
        return first.lower()
    if first[:1] in ("C", "A") and re.fullmatch(r"[A-Za-z][A-Za-z-]*", first[1:] or "-"):
        return first[1:].lower()
    if first[:1] == "C" and first[1:].isdigit() and toks[1][:1] == "A" and toks[1][1:].isdigit():
        return f"{first[1:]}-{toks[1][1:]}"
    return "code"


def eli_uri(state: str, act_id: str, effective_from: str | None = None, base: str = ELI_BASE) -> str | None:
    """The ELI-style work IRI of a section (or its expression IRI when ``effective_from`` is given); None when
    the act_id has no section token."""
    from . import schema as S
    toks = S.unit_tokens(act_id)
    if not toks:
        return None
    last = toks[-1]
    section = last[1:] if last[:1] in ("S", "A") and len(last) > 1 else last
    section = re.sub(r"^RT(?=\d)", "", section)            # Puerto Rico's ART5_07 -> 5_07 (its own spelling)
    work = ELI_TEMPLATE.format(base=base, st=state.lower(), code=eli_code(act_id), section=section)
    if effective_from:
        return ELI_VERSION_TEMPLATE.format(work=work, date=effective_from)
    return work


def eli_unit_uri(state: str, act_id_prefix: str, base: str = ELI_BASE) -> str:
    from . import schema as S
    return ELI_UNIT_TEMPLATE.format(base=base, st=state.lower(), code=eli_code(act_id_prefix + "_S0"),
                                    unit=S.unit_slug(act_id_prefix))


# --------------------------------------------------------------------------- resolution check
USER_AGENT = "lexflow-research/0.1"
ACCEPT = "application/rdf+xml, text/turtle;q=0.9, application/ld+json;q=0.8, text/html;q=0.5, */*;q=0.1"
# where an IRI's document really is, when the IRI itself does not dereference to it
DOCUMENTS: dict[str, str] = {
    LKIF: LKIF_RAW,          # http://www.estrellaproject.org/lkif-core/norm.owl#X -> raw.githubusercontent.com/.../norm.owl
}


def all_iris() -> list[str]:
    out: set[str] = set()
    for table in (PROPERTY_EQUIV, CLASS_MATCH, CLASS_CLOSE, NORM_TYPE_MATCH):
        for iris in table.values():
            out.update(iris)
    for m in STRUCTURE_MATCH.values():
        out.add(m["eli"])
    out.add(AKN_XSD)
    return sorted(out)


def document_of(iri: str) -> tuple[str, str | None]:
    """``(document URL, fragment)``: the file to fetch and the local name to look for in it.  A hash IRI's
    document is the part before ``#``; a slash-namespace term (schema.org, FIBO, DCMI terms) is its own page."""
    doc, frag = (iri.split("#", 1) if "#" in iri else (iri, None))
    for prefix, real in DOCUMENTS.items():
        if doc.startswith(prefix):
            doc = real + doc[len(prefix):]
    return doc, frag


_FRAG_RE = r"""(?:#|["';:]|name=")%s(?=["\s>;,.)]|$)"""


def _found(frag: str, body: str) -> bool:
    return bool(re.search(_FRAG_RE % re.escape(frag), body))


def fetch(url: str, session=None, timeout: float = 30) -> tuple[int | None, str]:
    """One read-only GET with lexflow's user agent: ``(status, body)``; ``(None, error)`` when it fails."""
    import requests
    s = session or requests.Session()
    try:
        r = s.get(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT}, timeout=timeout, allow_redirects=True)
        return r.status_code, r.text
    except requests.RequestException as e:
        return None, str(e)


def resolve_all(iris: list[str] | None = None, cache: Path | str | None = None, pace: float = 1.0,
                max_age_days: int = 30, fetch_fn=fetch) -> dict[str, dict]:
    """Resolve every IRI (default ``all_iris()``): one GET per document, a second apart, with a JSON cache so a
    re-run inside ``max_age_days`` makes no request.  Each result: ``{"iri", "url", "status", "found", "ok",
    "at"}``, ``found`` being whether the fragment's local name occurs in the document (None without one)."""
    iris = list(iris or all_iris())
    path = Path(cache) if cache else None
    store: dict[str, dict] = {}
    if path and path.exists():
        try:
            store = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            store = {}
    fresh = time.time() - max_age_days * 86400
    docs: dict[str, tuple[int | None, str]] = {}
    out: dict[str, dict] = {}
    for iri in iris:
        hit = store.get(iri)
        if hit and hit.get("at", 0) >= fresh:
            out[iri] = hit
            continue
        doc, frag = document_of(iri)
        if doc not in docs:
            docs[doc] = fetch_fn(doc)
            if pace:
                time.sleep(pace)
        status, body = docs[doc]
        found = _found(frag, body) if frag and status == 200 else (False if frag else None)
        out[iri] = {"iri": iri, "url": doc, "status": status, "found": found,
                    "ok": status == 200 and found is not False, "at": time.time()}
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({**store, **out}, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":                           # python -m lexflow.publish.ontology_map: the resolution report
    import sys
    from .. import config
    res = resolve_all(cache=Path(config.DATA_DIR) / "cache" / "ontology_iris.json")
    bad = [r for r in res.values() if not r["ok"]]
    for r in res.values():
        print(("ok  " if r["ok"] else "BAD ") + r["iri"] + ("" if r["found"] is None else f"  found={r['found']}")
              + f"  status={r['status']}")
    print(f"{len(res) - len(bad)} of {len(res)} resolve")
    sys.exit(1 if bad else 0)
