# Links between laws, decisions, processes and terms: a literature review for lexflow

_10 October 2026. Scope: four topics that decide how lexflow should link a statute section to the sections it cites, to the exceptions that override it, to the BPMN and DMN models built from it, and to the terms it defines. Each work below was opened and checked: the DOI resolves (doi.org returns a redirect to the publisher) and the authors, year and venue match Crossref, arXiv, ACL Anthology or the standards body. Numbers come from the paper's abstract or full text, not from secondary summaries, unless the entry says otherwise._

## Summary

- **Cross-references.** Rule-based detection and resolution, run against a model of the code's hierarchy, reaches about 99% precision and recall on internal references (Sannier et al. 2017). A learned approach on Japanese law reported about 80% F for detection. The hard cases are external references, multi-layer references ("paragraph 2 of article 3"), vague references ("the provision"), and delegations to rules not yet written. A reference has an *intent* as well as a target (definition, constraint, exception, delegation, refinement, compliance, amendment), and that intent can be classified from cue words around it, at about 84% F.
- **Exceptions.** Statutes follow a general-case / exception structure. Defeasible logic, Lawsky's default logic and Catala's default calculus model it as a *static tree of rules with priorities*. Catala's semantics give lexflow two checks to run on every decision: *conflict* (two exceptions apply at once) and *empty* (nothing applies). DMN can carry the tree, but the precedence must come from rule order (FIRST) or from chained decisions. The PRIORITY hit policy ranks output *values*, not rules.
- **Decisions and processes.** DMN already has the link from a decision to the law that governs it: a *knowledge source* with a `locationURI`, joined by an *authority requirement*. BPMN has call activities and message flows. Research on compliance checking and on process architectures provides the checks to run once processes from different sections are linked.
- **Terms.** Statutory definitions follow regular patterns, and their scope ("as used in this chapter") matters as much as the term. Small encoder models (GLiNER, GLiClass, SetFit) run on a CPU and handle the "small stuff", such as tagging a term like *incorporator* as a legal role. Wikidata covers broad legal concepts but not state-statute vocabulary. A naive label match to Wikidata is often wrong, so links need type checks, a match grade (SKOS close/broad/exact), and review before an *exact match* is written.

## 0. What the Florida data shows (local probe, 10 October 2026)

The user pointed at [Item:Q168](https://lexipedia.wikibase.cloud/wiki/Item:Q168), Fla. Stat. § 607.0201 "Incorporators". The item currently has a label, a citation, a legal identifier (`lexflow:statute:fl:607.0201`), instance of Q10, applies-to-jurisdiction Q33 and the official URL. It has no `references` (P13) statements and no term items. The section's whole text is one sentence: "One or more persons may act as the incorporator or incorporators of a corporation by delivering articles of incorporation to the department for filing", followed by a history note ("s. 16, ch. 89-154; s. 16, ch. 2019-90").

These counts were read from the local Florida index (25,020 sections) with simple regular expressions, so they are approximate.

| Observation | Count |
|---|---|
| Quoted defined terms in the chapter 607 definitions section, § 607.01401 | 73 ("Articles of incorporation" is one; "incorporator" is not) |
| Sections that use the word *incorporator(s)* | 56, in chapters 607, 624, 626, 628, 663, 395 and others |
| Chapter 607 (263 sections): references found by `retrieve.XREF` | 15 |
| Chapter 607: Florida-style `s.`/`ss.` section references to any chapter, e.g. `s. 607.0202(1)(a)` (history notes excluded) | 633 |
| Chapter 607: implicit references ("this chapter", "this section", "this subsection" …) | 476 |
| Sections containing "notwithstanding" | 2,668 (10.7%) |
| Sections containing "except as (otherwise) provided" | 1,848 (7.4%) |
| Sections containing "as used in this chapter / part / section / act" | 1,933 (7.7%) |
| Quoted `"X" means` definitions | 16,599 in 3,280 sections (13.1%) |
| Sections that borrow a definition: "has the same meaning as in s. …" | 430 (1.7%) |

Findings from Wikidata (read only, 1 request per second):

- **incorporator.** The only item labelled "incorporator" is [Q140403634](https://www.wikidata.org/wiki/Q140403634), a PropBank role ("prototypical agent for predicate mainstream.01", subclass of *proto-agent*, exact match to a Framester URI). It is a textbook false link. There is no English lexeme for the word.
- **articles of incorporation.** [Q17013292](https://www.wikidata.org/wiki/Q17013292) is a good target: part of *corporation*, facet of *incorporation*. The same label also matches an alias of "articles of association", a Japan-specific item and a TV episode.
- **incorporation.** The word has two legal senses: [Q3178478](https://www.wikidata.org/wiki/Q3178478), the process of creating a corporation, and [Q2031217](https://www.wikidata.org/wiki/Q2031217), a "legal term" item.
- **Legal concepts in general.** 24,198 items are instances of *legal term or legal concept* ([Q2135465](https://www.wikidata.org/wiki/Q2135465)) or of its subclasses. However, no item has a *legal citation of this text* ([P1031](https://www.wikidata.org/wiki/Property:P1031)) containing "Fla. Stat.", so Florida's sections are not on Wikidata. Wikidata does have [Florida Statutes](https://www.wikidata.org/wiki/Q16152590) and the [Model Business Corporation Act](https://www.wikidata.org/wiki/Q6888224) as whole works.
- **Model-act text.** The sentence in § 607.0201 appears word for word in [N.H. RSA 293-A:2.01](https://gc.nh.gov/rsa/html/XXVII/293-A/293-A-201.htm), except for the filing office.

So *incorporator* is a term of art with no definitions-section entry. Section 607.0201 is its working definition. It is used in 56 Florida sections and in other states' versions of the model act (e.g. New Hampshire), and it has no valid Wikidata target. It should become a Lexipedia item. The cross-reference resolver also has a large recall gap on Florida's citation form.

## 1. Detecting and resolving cross-references

- **Maxwell, Antón, Swire, Riaz, McCraw (2012).** *A legal cross-references taxonomy for reasoning about compliance requirements.* Requirements Engineering 17(2):99–115. [doi:10.1007/s00766-012-0152-5](https://doi.org/10.1007/s00766-012-0152-5).
  - *Found:* the authors analysed every external cross-reference in the HIPAA Privacy Rule, the GLBA and the GLBA Financial Privacy Rule. They classified each one by whether it introduces a conflicting requirement, introduces a conflicting definition, or refines a requirement, and they found five sets of conflicting requirements.
  - *For lexflow:* a reference is an edge with an effect, so store that effect as a qualifier, not just "references".

- **Adedjouma, Sabetzadeh, Briand (2014).** *Automated detection and resolution of legal cross references: approach and a study of Luxembourg's legislation.* IEEE RE 2014, 63–72. [doi:10.1109/RE.2014.6912248](https://doi.org/10.1109/RE.2014.6912248).
  - *Found:* the authors separated *detection* (recognising the reference expression) from *resolution* (linking it to the target provision).
  - *For lexflow:* score the two steps separately.

- **Sannier, Adedjouma, Sabetzadeh, Briand (2017).** *An automated framework for detection and resolution of cross references in legal texts.* Requirements Engineering 22(2):215–237. [doi:10.1007/s00766-015-0241-3](https://doi.org/10.1007/s00766-015-0241-3) ([author preprint](https://orbilu.uni.lu/bitstream/10993/22286/1/SASB_REJ_authors_preprint.pdf)).
  - *Found:* natural-language patterns plus a schema of the text's hierarchy gave detection precision of 99.7% and recall of 97.9%. Recall reached 100% once the gazetteers of law names and structure markers were completed. Resolution of 2,524 internal references across seven texts scored F ≥ 99.4%.
  - *Errors:* came from external references, multi-layer references and gazetteer gaps. "Unspecific" references (about 3.4% of internal ones, e.g. "the provision") and delegating references ("by regulation") cannot be resolved automatically. "Same paragraph" needed expansion to eight targets. External references were not resolved at all, because the cited text's structure was not loaded.
  - *For lexflow:* resolve against the `path` hierarchy lexflow already keeps. Emit a warning instead of a guess for vague and delegating references. Treat external references as their own class.

- **Sannier, Adedjouma, Sabetzadeh, Briand (2016).** *Automated classification of legal cross references based on semantic intent.* REFSQ 2016, LNCS, 119–134. [doi:10.1007/978-3-319-30282-9_8](https://doi.org/10.1007/978-3-319-30282-9_8) ([companion page](https://people.svv.lu/sannier/CRSemantics/)).
  - *Found:* the words just before and after a reference usually reveal its intent. The intent types are compliance, constraint, definition, delegation, exception, refinement, and five kinds of amendment. The cue-pattern classifier averaged about 84% F, based on 1,079 references studied.
  - *For lexflow:* this is a ready vocabulary for a "reference intent" qualifier. "Exception" feeds DMN precedence, "definition" feeds term borrowing ("has the same meaning as in s. …"), and "delegation" feeds call activities.

- **Tran, Ngo, Nguyen, Shimazu (2014).** *Automated reference resolution in legal texts.* Artificial Intelligence and Law 22(1):29–60. [doi:10.1007/s10506-013-9149-8](https://doi.org/10.1007/s10506-013-9149-8).
  - *Found:* learned detection and resolution on Japanese legal texts. Sannier et al. (2017, related work) report about 80% F for detection and 67% for detection plus resolution, citing Tran et al.
  - *For lexflow:* use rules for spans and targets, and learning only for intent.

- **Palmirani, Brighi, Massini (2003).** *Automated extraction of normative references in legal texts.* ICAIL 2003, 105. [doi:10.1145/1047788.1047815](https://doi.org/10.1145/1047788.1047815).
  - *Found:* in the Italian Ministry of Justice standards effort, marking up a text's identification data, its partitions and its normative references is what lets separate bodies of law be linked and consolidated.
  - *For lexflow:* this is the precursor of Akoma Ntoso's reference model, below.

- **OASIS (2018).** *Akoma Ntoso Version 1.0, Part 1: XML Vocabulary.* OASIS Standard, 29 August 2018; editors Palmirani, Sperberg, Vergottini, Vitali. [docs.oasis-open.org](https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html).
  - *Found:* `ref` handles a single reference, `mref` several, and `rref` a range (`from`/`upTo`). `eId`/`wId` identify partitions. `activeModifications`/`passiveModifications` with `textualMod` record amendments. `def`/`term` carry `refersTo` pointers to Top Level Classes such as TLCPerson, TLCRole, TLCOrganization and TLCConcept.
  - *For lexflow:* model ranges and lists as first-class references ("ss. 607.1301–607.1340"). TLCRole is the right class for *incorporator*.

- **US GPO / House (USLM).** *United States Legislative Markup, schema and User Guide.* [github.com/usgpo/uslm](https://github.com/usgpo/uslm) ([User Guide](https://raw.githubusercontent.com/usgpo/uslm/main/USLM-User-Guide.md)).
  - *Found:* a reference is work + portion + point in time + format, e.g. `/us/usc/t26/s121/a/1`, with `@` followed by a date for point in time. References are stored as absolute paths without a domain, so documents can move. `ref@idref` + `@portion` chain "subsection (b) of such section" onto an earlier reference. `term` sits inside `def`. A resolver returns 404 for unknown references.
  - *For lexflow:* extend `lexflow:statute:fl:607.0201` with a portion (`/1/a`) and an optional `@date`. Use the `idref` + `portion` idea for "such section".

- **Council of the EU (2012) and the ELI ontology.** *Council conclusions inviting the introduction of the European Legislation Identifier.* OJ C 325, 26.10.2012, 3–11. [EUR-Lex 52012XG1026(01)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52012XG1026(01)). ELI ontology v1.5 ([OWL](http://publications.europa.eu/resource/distribution/eli/owl/owl/eli.owl)). [schema.org/Legislation](https://schema.org/Legislation) is derived from it.
  - *Found:* ELI has URI templates, FRBR metadata, RDFa/JSON-LD publication and sitemaps. Its relation properties include `cites` ("citation in the text … includes verbatim citation and citations in referrals"), `based_on` (empowered by an enabling act), `changes`/`amends`/`repeals`/`commences`, and `is_about` (EuroVoc encouraged).
  - *For lexflow:* name Lexipedia's relation properties after ELI so they can be exported as schema.org JSON-LD.

- **Katz & Bommarito (2014).** *Measuring the complexity of the law: the United States Code.* Artificial Intelligence and Law 22:337–374. [doi:10.1007/s10506-014-9160-8](https://doi.org/10.1007/s10506-014-9160-8).
  - *Found:* the authors scored US Code titles by structure, language and *interdependence*.
  - *For lexflow:* once references resolve, the reference graph ranks which chapters need cross-model links first.

## 2. Exceptions, overrides and defaults in executable form

- **Sergot, Sadri, Kowalski, Kriwaczek, Hammond, Cory (1986).** *The British Nationality Act as a logic program.* Communications of the ACM 29(5):370–386. [doi:10.1145/5689.5920](https://doi.org/10.1145/5689.5920).
  - *Found:* the founding demonstration that a statute can be executed as rules.
  - *For lexflow:* lexflow's DMN tables stand in the same tradition. The works below are about representing exceptions.

- **Antoniou, Billington, Governatori, Maher (2001).** *Representation results for defeasible logic.* ACM Transactions on Computational Logic 2(2):255–287. [doi:10.1145/371316.371517](https://doi.org/10.1145/371316.371517).
  - *Found:* defeasible logic is "a simple but efficient formalism … based on rules and priorities", with transformations that support efficient implementation.
  - *For lexflow:* "notwithstanding s. X" means this rule is superior to the conflicting rules in X.

- **Lawsky (2018).** *A Logic for Statutes.* Florida Tax Review 21(1). [UF scholarship repository](https://scholarship.law.ufl.edu/ftr/vol21/iss1/2/).
  - *Found:* using the Internal Revenue Code, Lawsky argues that statutory reasoning, once terms are settled, is defeasible and is better modelled by default logic than by standard logic.
  - *For lexflow:* keep the base rule and its exceptions as separate, linked rules. Do not merge them into one negated condition.

- **Merigoux, Chataing, Protzenko (2021).** *Catala: a programming language for the law.* PACMPL 5(ICFP), 1–29. [doi:10.1145/3473582](https://doi.org/10.1145/3473582) ([arXiv:2103.03198](https://arxiv.org/abs/2103.03198)).
  - *How the default calculus evaluates:* each definition is labelled, and each exception names the rule it overrides. All exceptions are evaluated. If two or more apply, the result is a *conflict error*. If exactly one applies, its value wins. If none apply, the base rule's condition decides, and the result is an *empty error* when that condition is false.
  - *Why it works:* every statute the authors examined, US and French, had this static n-ary tree of exceptions, so the code can mirror the law's structure. The approach found a bug in the official French family-benefits implementation.
  - *For lexflow:* compile "notwithstanding" and "except as provided in" into this tree. Report conflict and empty cases through the existing DMN overlap and completeness checks.

- **Monat, Fromherz, Merigoux (2024).** *Formalizing date arithmetic and statically detecting ambiguities for the law.* ESOP 2024, LNCS, 421–450. [doi:10.1007/978-3-031-57267-8_16](https://doi.org/10.1007/978-3-031-57267-8_16).
  - *Found:* a formal semantics for day, month and year arithmetic, plus a static analysis that found date ambiguities in the Catala version of the French housing benefits.
  - *For lexflow:* flag timers such as "one month after" or "within 1 year" whose result depends on the rounding rule.

- **OASIS (2021).** *LegalRuleML Core Specification Version 1.0.* OASIS Standard, 30 August 2021; editors Palmirani, Governatori, Athan, Boley, Paschke, Wyner. [docs.oasis-open.org](https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/legalruleml-core-spec-v1.0.html).
  - *Found:* rules carry a strength (defeasible, defeater or strict). Precedence is `lrml:Override` with `@over`/`@under`. Legal sources are referenced by IRI and attached to rules through `lrml:Association`, using `appliesSource` → `toTarget`. Authority and Jurisdiction are first-class.
  - *For lexflow:* Lexipedia's existing *defeated by* (P21) is an Override. Add strength, and add the source section as a qualifier.

- **Calvanese, Dumas, Laurson, Maggi, Montali, Teinemaa (2016; 2018).** *Semantics and analysis of DMN decision tables.* BPM 2016, LNCS 9850, 217–233. [doi:10.1007/978-3-319-45348-4_13](https://doi.org/10.1007/978-3-319-45348-4_13). Extended as *Semantics, analysis and simplification of DMN decision tables*, Information Systems 78:112–125. [doi:10.1016/j.is.2018.01.010](https://doi.org/10.1016/j.is.2018.01.010).
  - *Found:* a formal semantics for hit policies, and geometric algorithms that find overlapping rules, find missing rules, and merge rules.
  - *For lexflow:* this formal basis covers lexflow's overlap and completeness checks. Use the overlap report to show which exception wins where.

- **OMG (2021).** *Decision Model and Notation 1.3* (formal/2021-01-01; the latest formal version is 1.6, September 2026). [omg.org/spec/DMN](https://www.omg.org/spec/DMN/).
  - *Found:* PRIORITY "returns the matching rule with the highest output priority … specified in the ordered list of output values … independent from rule sequence". FIRST returns the first hit by rule order and is "not considered good practice".
  - *For lexflow:* for legal precedence, use UNIQUE among sibling exceptions. Use either FIRST with exception rows above the base row (record why) or a chain of decisions, one per exception level. Do not use PRIORITY, because it ranks outputs, not rules.

## 3. Decision requirements, process links and compliance

- **OMG DMN 1.3, decision requirements.** Same source as above; the XSD is in `schemas/dmn/DMN13.xsd`.
  - *Found:* "a knowledge source denotes an authority for a business knowledge model or decision". The spec's own example is "a set of regulations defined by a regulatory body". `tKnowledgeSource` has `locationURI`, `type` and `owner`. `authorityRequirement` can point to a decision, an input or another knowledge source. Knowledge sources have no execution semantics. A business knowledge model is a function invoked from decisions.
  - *For lexflow:* emit one knowledge source per governing section, with `locationURI` set to its Lexipedia item, and link it to each decision by an authority requirement. Make a BKM for any definition that several decisions use ("domestic corporation").

- **Hasić, De Smedt, Vanthienen (2018).** *Augmenting processes with decision intelligence: principles for integrated modelling.* Decision Support Systems 107:1–12. [doi:10.1016/j.dss.2017.12.008](https://doi.org/10.1016/j.dss.2017.12.008).
  - *Found:* principles for modelling decisions across the whole process, not only at local gateways.
  - *For lexflow:* move gateway conditions into DMN decisions called from business-rule tasks.

- **Hasić & Vanthienen (2020).** *From decision knowledge to e-government expert systems: the case of income taxation for foreign artists in Belgium.* Knowledge and Information Systems 62:2011–2028. [doi:10.1007/s10115-019-01416-4](https://doi.org/10.1007/s10115-019-01416-4).
  - *Found:* DMN modelling guidelines, at both the requirements level and the logic level, for a legislation-driven e-government decision.
  - *For lexflow:* a worked example of statute → decision requirements diagram (DRD).

- **Goossens, De Smedt, Vanthienen (2023).** *Extracting Decision Model and Notation models from text using deep learning techniques.* Expert Systems with Applications 211:118667. [doi:10.1016/j.eswa.2022.118667](https://doi.org/10.1016/j.eswa.2022.118667). Also: *Comparing the performance of GPT-3 with BERT for decision requirements modeling*, CoopIS 2023, LNCS, 448–458. [doi:10.1007/978-3-031-46846-9_26](https://doi.org/10.1007/978-3-031-46846-9_26).
  - *For lexflow:* the closest prior work on DMN extraction from text, and a baseline for lexflow's DMN extraction.

- **OMG (2014).** *Business Process Model and Notation 2.0.2* (formal/13-12-09). [omg.org/spec/BPMN/2.0.2](https://www.omg.org/spec/BPMN/2.0.2/).
  - *Found:* `callActivity@calledElement` invokes another process. `collaboration` holds participants (pools), and `messageFlow` (`sourceRef`/`targetRef`) links them.
  - *For lexflow:* lexflow already writes both (`called_element`, `messageFlow`). Use a call activity when a section hands a step to another section's procedure ("in the manner provided in s. X"). Use a message flow when another party's process reacts to a filing or notice.

- **Eid-Sabbagh, Dijkman, Weske (2012).** *Business process architecture: use and correctness.* BPM 2012, LNCS, 65–81. [doi:10.1007/978-3-642-32885-5_5](https://doi.org/10.1007/978-3-642-32885-5_5).
  - *Found:* a formal framework for relations between process models, with anti-patterns that mark erroneous relations.
  - *For lexflow:* once statutes are linked to each other's processes, check the cross-model graph for these anti-patterns, such as processes that wait on each other.

- **Dijkman, Dumas, García-Bañuelos (2009).** *Graph matching algorithms for business process model similarity search.* BPM 2009, LNCS, 48–63. [doi:10.1007/978-3-642-03848-8_5](https://doi.org/10.1007/978-3-642-03848-8_5).
  - *For lexflow:* find the same procedure across states (model-act families like § 607.0201 and RSA 293-A:2.01), and reuse or compare their models.

- **Hashmi, Governatori, Lam, Wynn (2018).** *Are we done with business process compliance: state of the art and challenges ahead.* Knowledge and Information Systems 57:79–133. [doi:10.1007/s10115-017-1142-1](https://doi.org/10.1007/s10115-017-1142-1).
  - *For lexflow:* the survey to read before building checks of BPMN against the rules it came from.

- **Sadiq, Governatori, Namiri (2007).** *Modeling control objectives for business process compliance.* BPM 2007, LNCS, 149–164. [doi:10.1007/978-3-540-75183-0_12](https://doi.org/10.1007/978-3-540-75183-0_12).
  - *Found:* control objectives modelled in a deontic modal logic and propagated onto process models.

- **Governatori (2015).** *The Regorous approach to process compliance.* IEEE EDOCW 2015, 33–40. [doi:10.1109/EDOCW.2015.28](https://doi.org/10.1109/EDOCW.2015.28) ([CSIRO page](https://research.csiro.au/data61/regorous)).
  - *Found:* a compliance-by-design checker. CSIRO's page says it is built on defeasible deontic logic, covering obligations, permissions, prohibitions and violations.
  - *For lexflow:* lexflow's deontic modality labels plus *defeated by* edges are the inputs such a checker needs.

- **Winter, van der Aa, Rinderle-Ma, Weidlich (2020).** *Assessing the compliance of business process models with regulatory documents.* ER 2020, LNCS 12400, 189–203. [doi:10.1007/978-3-030-62522-1_14](https://doi.org/10.1007/978-3-030-62522-1_14) ([author PDF](http://eprints.cs.univie.ac.at/6508/1/compliance_assessment_paper_ER2020.pdf)).
  - *Found:* NLP pairwise matching between parts of a regulatory document and process models in a repository, used to measure coverage and to rank models. Case studies came from the energy domain and the GDPR.
  - *For lexflow:* audit which sentences of a statute a model leaves uncovered.

- **Barrientos, Winter, Rinderle-Ma (2026).** *Impact analysis of regulatory requirement changes on business process compliance.* Information and Software Technology 194:108079. [doi:10.1016/j.infsof.2026.108079](https://doi.org/10.1016/j.infsof.2026.108079).
  - *Found:* RC4PC, a hybrid of LLM and algorithmic steps. It represents requirements in deontic logic, extracts atomic changes between an old and a new version, and explains the effect on process compliance. Precision dropped where representations were inconsistent or redundant.
  - *For lexflow:* when a section's history note changes, diff the versions and flag the models and decisions that cite it.

- **van der Aa, Leopold, Reijers (2017).** *Comparing textual descriptions to process models: the automatic detection of inconsistencies.* Information Systems 64:447–460. [doi:10.1016/j.is.2016.07.010](https://doi.org/10.1016/j.is.2016.07.010).
  - *For lexflow:* extend the quote checks from "every quote matches the text" to "the order and branching of the steps match the text".

- **Bellan, van der Aa, Dragoni, Ghidini, Ponzetto (2023).** *PET: an annotated dataset for process extraction from natural language text tasks.* BPM 2022 Workshops, LNBIP, 315–321. [doi:10.1007/978-3-031-25383-6_23](https://doi.org/10.1007/978-3-031-25383-6_23).
  - *Found:* business-process descriptions annotated with activities, gateways, actors and flow, with baselines.
  - *For lexflow:* an outside test set for step and actor extraction.

- **Robaldo, Bartolini, Palmirani, Rossi, Martoni, Lenzini (2020).** *Formalizing GDPR provisions in reified I/O logic: the DAPRECO knowledge base.* Journal of Logic, Language and Information 29:401–449. [doi:10.1007/s10849-019-09309-z](https://doi.org/10.1007/s10849-019-09309-z).
  - *For lexflow:* an example of formalising one regulation's provisions at scale in a single logic. It is a reference point if lexflow later exports its rules beyond DMN.

## 4. Defined terms, small classifiers and links to Wikidata

- **Definition markup.** Akoma Ntoso `def`/`term` with `refersTo` to TLC classes, and USLM `term` inside `def` (both cited in §1).
  - *For lexflow:* a term is an *addressable entity* with its own identifier, not a string.

- **Hosabettu & Shah (2025).** *Transformer-based extraction of statutory definitions from the U.S. Code.* IEEE AIIoT 2025 (accepted). [arXiv:2504.16353](https://arxiv.org/abs/2504.16353).
  - *Found:* working from US Code XML, a Legal-BERT model first classifies paragraphs as definitional. A pipeline then joins them into definitional units and extracts each term and its *scope*. Scope is inherited from parent units unless overridden. The best model scored 96.8% precision and 98.9% recall.
  - *For lexflow:* treat scope as a field of every definition. Florida's "as used in this chapter" (1,933 sections) and "has the same meaning as in s." (430 sections) are the scope and borrowing signals.

- **Guha et al. (2023).** *LegalBench: a collaboratively built benchmark for measuring legal reasoning in large language models.* NeurIPS 2023 Datasets and Benchmarks. [proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/89e44582fd28ddfea1ea4dcb0ebbf4b0-Abstract.html) ([arXiv:2308.11462](https://arxiv.org/abs/2308.11462)).
  - *Found:* 162 tasks. `definition_extraction` gives about 696 sentences from Supreme Court opinions and asks for the defined term, which need not be quoted. There is a companion task, `definition_classification`.
  - *For lexflow:* a quick check for lexflow's term extractor on unquoted definitions. Note that it is case law, not statutes.

- **Leitner, Rehm, Moreno-Schneider (2019).** *Fine-grained named entity recognition in legal documents.* SEMANTiCS 2019, LNCS, 272–287. [doi:10.1007/978-3-030-33220-4_20](https://doi.org/10.1007/978-3-030-33220-4_20).
  - *Found:* 67,000 sentences of German court decisions with 54,000 entities in 19 classes, including law, ordinance, regulation and court decision. A BiLSTM reached 95.46 F1 on the fine-grained classes.
  - *For lexflow:* legal norms and institutions are NER classes in their own right.

- **Au, Lampos, Cox (2022).** *E-NER: an annotated named entity recognition corpus of legal text.* NLLP 2022, 246–255. [doi:10.18653/v1/2022.nllp-1.22](https://doi.org/10.18653/v1/2022.nllp-1.22).
  - *Found:* models trained on CoNLL-2003 lose 29.4–60.4% F1 on SEC EDGAR legal filings.
  - *For lexflow:* general-domain taggers and linkers cannot be trusted on statutes without checks.

- **Cardellino, Teruel, Alonso Alemany, Villata (2017).** *A low-cost, high-coverage legal named entity recognizer, classifier and linker.* ICAIL 2017, 9–18. [doi:10.1145/3086512.3086514](https://doi.org/10.1145/3086512.3086514). Also *Legal NERC with ontologies, Wikipedia and curriculum learning*, EACL 2017, 254–259. [doi:10.18653/v1/E17-2041](https://doi.org/10.18653/v1/E17-2041).
  - *Found:* the authors mapped the LKIF legal ontology onto YAGO and trained on Wikipedia mentions. The model worked on Wikipedia but performed worse on ECHR judgments.
  - *For lexflow:* anchor senses in the statute's own definition, and use the encyclopaedia only as a secondary match.

- **Zaratiana, Tomeh, Holat, Charnois (2024).** *GLiNER: generalist model for named entity recognition using bidirectional transformer.* NAACL 2024, 5364–5376. [doi:10.18653/v1/2024.naacl-long.300](https://doi.org/10.18653/v1/2024.naacl-long.300).
  - *Found:* a compact encoder that tags spans for any label list given at inference. It beat ChatGPT in zero-shot NER evaluations.
  - *Model:* [gliner_small-v2.1](https://huggingface.co/urchade/gliner_small-v2.1) has 166M parameters and an Apache-2.0 licence. The v0/v1 models are CC BY-NC 4.0, so avoid them.
  - *For lexflow:* this is the "small model for small stuff". It runs on a CPU, takes labels such as `legal role`, `filing document`, `government office` and `defined term`, and needs no chat model.

- **Stepanov & Shtopko (2024).** *GLiNER multi-task.* [arXiv:2406.12925](https://arxiv.org/abs/2406.12925). **Stepanov et al. (2025).** *GLiClass: generalist lightweight model for sequence classification tasks.* [arXiv:2508.07662](https://arxiv.org/abs/2508.07662) ([code, Apache-2.0](https://github.com/Knowledgator/GLiClass)).
  - *Found:* GLiNER-style encoders applied to relation extraction and to zero-shot sentence classification.
  - *For lexflow:* label sentences as definition, exception, obligation or delegation in one pass.

- **Tunstall et al. (2022).** *Efficient few-shot learning without prompts (SetFit).* [arXiv:2209.11055](https://arxiv.org/abs/2209.11055).
  - *Found:* contrastive fine-tuning of a sentence encoder plus a classification head. It matches prompt-based few-shot methods and is an order of magnitude faster to train.
  - *For lexflow:* train "is this a term of art?" and "reference intent" classifiers from a few hundred Claude-reviewed examples, on a CPU.

- **Wu, Petroni, Josifoski, Riedel, Zettlemoyer (2020).** *Scalable zero-shot entity linking with dense entity retrieval (BLINK).* EMNLP 2020. [arXiv:1911.03814](https://arxiv.org/abs/1911.03814). **Logeswaran et al. (2019).** *Zero-shot entity linking by reading entity descriptions.* ACL 2019, 3449–3460. [doi:10.18653/v1/P19-1335](https://doi.org/10.18653/v1/P19-1335).
  - *Found:* entities can be linked from their short descriptions alone. A bi-encoder retrieves candidates and a cross-encoder reranks them.
  - *For lexflow:* compare the statute's definitional sentence with the Wikidata description using `nomic-embed-text` (already installed) as the bi-encoder step.

- **Ayoola, Tyagi, Fisher, Christodoulopoulos, Pierleoni (2022).** *ReFinED: an efficient zero-shot-capable approach to end-to-end entity linking.* NAACL 2022 Industry Track. [arXiv:2207.04108](https://arxiv.org/abs/2207.04108).
  - *Found:* fine-grained entity types plus descriptions let one forward pass link to all of Wikidata, more than 60 times faster than earlier systems.
  - *For lexflow:* use types to reject candidates. Checking the class alone removes the PropBank-role match for *incorporator*.

- **Delpeuch (2020).** *OpenTapioca: lightweight entity linking for Wikidata.* Wikidata Workshop 2020. [arXiv:1904.09131](https://arxiv.org/abs/1904.09131).
  - *Found:* a linker trained only from Wikidata, which shows that data source's strengths and weaknesses.
  - *For lexflow:* a cheap baseline.

- **Martín-Chozas, Ahmadi, Montiel-Ponsoda (2020).** *Defying Wikidata: validation of terminological relations in the web of data.* LREC 2020, 5654–5659. [ACL Anthology](https://aclanthology.org/2020.lrec-1.694/).
  - *Found:* while validating legal-domain terms in four languages, the authors found that some Wikidata properties held a different kind of information from the one they were meant to hold. They proposed validation axioms.
  - *For lexflow:* validate Wikidata relations before copying them.

- **W3C (2009).** *SKOS Simple Knowledge Organization System Reference.* W3C Recommendation, 18 August 2009; editors Miles & Bechhofer. [w3.org/TR/skos-reference](https://www.w3.org/TR/skos-reference/).
  - *Found:* `exactMatch` is transitive. `closeMatch` is deliberately not transitive, to avoid compounding errors across schemes. `broadMatch`, `narrowMatch` and `relatedMatch` cover the other relations.
  - *For lexflow:* Lexipedia has only *exact match* (P8). Most statute-to-Wikidata links are close or broad.

## 5. Recommendations

1. **Widen the reference grammar in a new module.** Cover Florida's `s.`/`ss.` form with subsection paths and ranges (`s. 607.0202(1)(a)`, `ss. 607.1301-607.1340`). Cover implicit references ("this chapter", "subsection (2)") resolved against `path`, and "such section" chaining (USLM `idref` + `portion`). Mark external, vague and delegating references as unresolved instead of guessing. Skip history notes, whose "s. 16, ch. 89-154" entries cite session laws. In chapter 607 the current `XREF` finds 15 references, against 633 `s.` references and 476 implicit ones. Score detection and resolution separately on a gold set of about 200 references from five states.
2. **Give every reference an intent.** Write P13 *references* with a qualifier from Sannier's taxonomy (definition, constraint, exception, delegation, refinement, compliance, amendment) and the target portion. Classify by cue phrases first ("notwithstanding", "except as provided in", "has the same meaning as in", "subject to", "in the manner provided in"). Leave only the remainder to a SetFit or GLiClass classifier.
3. **Compile exceptions as a Catala-style tree.** "Notwithstanding" (10.7% of Florida sections) and "except as provided" (7.4%) become P21 *defeated by* edges and labelled exceptions. In DMN, sibling exceptions must be UNIQUE. Express parent-over-child precedence by FIRST (exception rows above the base row) or by chained decisions, never by PRIORITY. Report Catala's *conflict* and *empty* cases through the existing overlap and completeness checks.
4. **Link decisions to the law in DMN itself.** Write one `knowledgeSource` per governing section, with `locationURI` set to its Lexipedia item (e.g. `https://lexipedia.wikibase.cloud/wiki/Item:Q168`) and `type` = statute, plus an `authorityRequirement` from each decision. Mirror the link as P19 *governed by norm*. Make shared definitions into BKMs.
5. **Link processes across sections.** Use a call activity (`calledElement` = the called process's stable lexflow key) for "in the manner provided in s. X". Use a message flow for another office's reaction. Check the cross-model graph for process-architecture anti-patterns before publishing.
6. **Make terms addressable.** Add a *defined term* class and a *defined in* property, or reuse *legal role* for parties (Akoma Ntoso's TLCRole). Mint "incorporator (Florida)" with *defined in* → Q168, *applies to jurisdiction* → Florida, a scope (chapter 607), and *used in* links to the 56 sections that use it. Extract quoted `"X" means` definitions and their scope with rules (16,599 in Florida). Use `gliner_small-v2.1` (Apache-2.0, CPU) only for undefined terms of art like *incorporator*.
7. **Guard every Wikidata link.**
   - Find candidates by label and alias.
   - Keep a candidate only if its P31/P279 chain reaches an allowed class (legal term or concept Q2135465, legal document, legal process, role or occupation) and avoids a blocklist (scientific article, PropBank or Framester role, creative work).
   - Require an embedding margin between the statute's definitional sentence and the Wikidata description.
   - Write SKOS-style *close match* or *broad match* by default. Reserve P8 *exact match* for reviewed links, and allow "no match".
   - For *incorporator*: reject Q140403634. Add *broad/related match* to incorporation Q3178478, and relate the term to articles of incorporation Q17013292, the document an incorporator delivers.
8. **Link model-act families across states.** Text similarity already shows § 607.0201 ≈ N.H. RSA 293-A:2.01. Record "same provision family" links, tied to the Model Business Corporation Act (Q6888224). Use them to transfer reviewed models between states.
9. **Use standard identifiers and names.** Extend legal identifiers with portions and points in time (`lexflow:statute:fl:607.0201/1/a@2026-10-10`, after USLM). Name relation properties after ELI (`cites`, `based_on`, `changes`/`amends`/`repeals`) so that items can be exported as schema.org `Legislation` JSON-LD.
10. **Measure before publishing.** Build three small gold sets: references (≈200), definitions (≈100 statute definitions, plus LegalBench `definition_extraction` as a check), and term links (≈50 terms with Wikidata judgments, including "none"). Publish links to Lexipedia only once they reach the precision the user sets, following the existing rule that only reviewed or agreed models go to the wiki.
