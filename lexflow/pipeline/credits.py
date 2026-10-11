"""Credits for the Setup page: the outside data, services, models and libraries each step uses.

A credit is a dict with ``name``, ``by`` (the maker), ``licence`` (what the maker's own page or the installed
package says), ``url`` (the maker's page), ``use`` (what lexflow uses it for), and optionally:

* ``licence_url``: the page with the licence or terms, when it is not ``url``;
* ``cite`` and ``cite_by``: a citation, and whose wording it is.  ``cite_by`` is ``"maker"`` only when the text
  is the maker's own citation word for word; otherwise it is ``"lexflow"``: lexflow's own (APA-like) format,
  built from the maker's page, BibTeX or CITATION.cff, and labelled as such on the page;
* ``note``: a condition worth showing next to it, such as a notice the maker requires.

The credits written out below were checked on 10 October 2026, within these limits:

* data and services: against the maker's own page, but the full text of the Hugging Face, Turso and Wikibase.cloud
  terms, CourtListener's site terms, the OMG DMN 1.3 page and the terms for the OMG XSD files, the terms of the
  search engines SearXNG queries, and the 2017 provenance of us-atlas were not read;
* models: only the Ollama tags in ``MODELS`` (the default models) were checked against the maker's card.  A model
  that config names otherwise gets a credit that says its licence was not checked (``model_credit``);
* libraries: many licences were taken from the installed package metadata only, and the Node.js and Python entries
  were not checked.

docs/design/credits-research.md says which is which, with the sources and the open questions, and
docs/design/verify-credits.md has the second check.  ``Step.credits`` in steps.py holds the credits of one step;
``GENERAL`` holds what is used across the steps (or by the Ask page), shown at the end of the Setup page.  None of
this is legal advice.

Credit is not endorsement: the people and projects listed here have not reviewed lexflow.
"""
from __future__ import annotations

CITE_BY = ("maker", "lexflow")


def credit(name: str, by: str, licence: str, url: str, use: str, cite: str = "", note: str = "",
           cite_by: str = "lexflow", licence_url: str = "") -> dict:
    """One credit.  A citation is labelled lexflow's format unless ``cite_by="maker"`` says it is word for word."""
    if cite_by not in CITE_BY:
        raise ValueError(f"cite_by must be one of {CITE_BY}, not {cite_by!r}")
    c = {"name": name, "by": by, "licence": licence, "url": url, "use": use}
    if licence_url:
        c["licence_url"] = licence_url
    if cite:
        c["cite"], c["cite_by"] = cite, cite_by
    if note:
        c["note"] = note
    return c


def used_for(c: dict, use: str, **changes: str) -> dict:
    """The same credit, with what one particular step uses it for (``note=""`` drops a note that does not apply)."""
    return {k: v for k, v in {**c, "use": use, **changes}.items() if v != ""}


# ------------------------------------------------------------------- data and services
CENSUS_GUS = credit(
    "2022 Census of Governments: Government Units Listing", "U.S. Census Bureau", "Public domain (US government work)",
    "https://www.census.gov/data/datasets/2022/econ/gus/public-use-files.html",
    "The 38,736 general-purpose governments that every other step is keyed to",
    # the dataset page gives no citation; this follows the Bureau's citation policy, filled in by lexflow
    cite='U.S. Census Bureau, "2022 Government Units Listing," 2022 Census of Governments, '
         "https://www.census.gov/data/datasets/2022/econ/gus/public-use-files.html, accessed (date)")
OPEN_US_LAW = credit(
    # no version in the name: statutes.py downloads whichever release the maker's manifest lists
    "Open US Law", "Vaquill AI", "CC BY-NC 4.0 (data); Apache-2.0 (scripts)",
    "https://github.com/Vaquill-AI/open-us-law",
    "State statutes, one parquet file per state, each section with the URL of its official publisher",
    cite="@misc{openuslaw2026091, title={Open US Law: Structured Primary Law of the United States}, "
         "author={Vaquill AI}, year={2026}, note={Snapshot v2026.09.1}, "
         "url={https://huggingface.co/datasets/vaquill/open-us-law}}",
    cite_by="maker",
    note="Commercial use needs a licence from Vaquill AI. The statute text is public law; the compilation is "
         "Vaquill AI's. A snapshot, not current law. lexflow downloads the release the maker's manifest lists and "
         "records its version with each state's file; the citation is the maker's for v2026.09.1, the release "
         "checked on 10 October 2026, so cite the release you used.")
OPEN_US_LAW_REGS = used_for(
    # the regulations add-on: the same maker, licence and citation as the statutes (docs/design/data-expansion.md §2.2)
    OPEN_US_LAW, "State regulations (the add-on), where the release has them: building codes, tax and licensing rules, "
                 "each section with the URL of its official publisher",
    note="Commercial use needs a licence from Vaquill AI. The regulation text is each state's own, as its official "
         "publisher gives it; the compilation is Vaquill AI's. Not every state has a regulations file: v2026.09.1 has "
         "none for 13 of lexflow's 52, among them CA, NY and TX. Where a rule adopts a model code by reference, the "
         "index holds only the state's text, never the model code. A snapshot, not current law: cite the release "
         "you used.")
WIKIDATA = credit(
    "Wikidata", "The Wikidata community, hosted by the Wikimedia Foundation", "CC0 1.0",
    "https://www.wikidata.org/wiki/Wikidata:Licensing",
    "Official websites (P856), office emails (P968) and phone numbers (P1329) from the Wikidata Query Service, "
    "matched by FIPS code (P882, P774)",
    note="To fix a wrong contact, edit Wikidata.")
GOV_DIRECTORY = credit(
    "Govdirectory", "WikiProject Govdirectory", "CC0 1.0", "https://www.govdirectory.org/about/",
    "Not called by lexflow: it shows the same Wikidata statements this step reads")
OLLAMA = credit(
    "Ollama", "Ollama", "MIT", "https://github.com/ollama/ollama",
    "Runs the local models and pulls them from its registry ('llm' profile)")
LOCUS = credit(
    "LOCUS-v1", "LocalLaws", "CC BY-NC 4.0", "https://huggingface.co/datasets/LocalLaws/LOCUS-v1",
    "Finding local ordinances; this step uses it to find law, never to cite it",
    # rewritten from the card's BibTeX (key peskoff2026freeing)
    cite="Peskoff, D., Barrow, J., Vu, C., & Davenport, D. (2026). Freeing the Law with LOCUS: A Local Ordinance "
         "Corpus for the United States. arXiv:2606.19334. https://doi.org/10.48550/arXiv.2606.19334",
    note="Machine-labelled. Its card rules out legal advice and use as a complete census of US local law. The "
         "hand-built test models (lexflow/gold.py) and the prototype process viewer do quote it, for Albemarle "
         "County § 17-211 and Charlottesville's noise ordinance, labelled as LOCUS text to check against the "
         "official code.")
HF_HUB = credit(
    "Hugging Face Hub", "Hugging Face", "Hub Terms of Service", "https://huggingface.co/terms-of-service",
    "Hosts LOCUS-v1; this step reads byte ranges of its parquet files")
COURTLISTENER = credit(
    "CourtListener REST API v4", "Free Law Project", "Allowed API usage policy (no data licence stated)",
    "https://free.law/projects/courtlistener/",
    "Searches opinions in each state's appellate courts that cite the sections behind its models",
    licence_url="https://free.law/membership/allowed-api-usage/",
    # caselaw.search sends COURTLISTENER_TOKEN when it is set; Ask (lexflow/ask/local.py) searches only with it
    note="Ask's court search runs only with a CourtListener account (COURTLISTENER_TOKEN). The cases step uses the "
         "token when it is set and otherwise searches without one, paced the same way; whether CourtListener still "
         "answers searches without an account was not checked. With an account, Free Law Project's allowed API "
         "usage policy (linked above) applies. "
         "Access through a membership is for personal, educational, research, journalistic and exploratory use. "
         "It may not power a commercial product that earns revenue, and may not be used to build tools for "
         "for-profit or non-profit organisations. One account per person; API keys may not be shared. An account "
         "gets 5 requests a minute, 50 an hour and 125 a day, and lexflow paces its requests to stay within them.")
WIKIBASE_CLOUD = credit(
    "Wikibase Cloud", "Wikimedia Deutschland", "Wikibase.cloud Terms of Use; Wikibase software GPL-2.0-or-later",
    "https://meta.wikimedia.org/wiki/Wikibase/Wikibase.cloud",
    "Hosts the Lexipedia Wikibase (lexipedia.wikibase.cloud), edited with a bot password")
DOKUWIKI = credit(
    "DokuWiki", "The DokuWiki community", "GPL-2.0", "https://github.com/dokuwiki/dokuwiki",
    "The Lexipedia wiki at lexipedia.xyz, written over JSON-RPC (lexflow: namespace only)")
BPMNIO_PLUGIN = credit(
    "bpmnio plugin for DokuWiki", "Color-Of-Code", "MIT, with the bpmn.io watermark condition",
    "https://github.com/Color-Of-Code/dokuwiki-plugin-bpmnio", "Draws the BPMN and DMN diagrams on the wiki")
LIBSQL = credit(
    "libSQL", "Turso", "MIT", "https://github.com/tursodatabase/libsql",
    "The shared database's protocol, and the self-hosted server ('shared' profile)")
TURSO_CLOUD = credit(
    "Turso Cloud", "Turso", "Turso Terms of Use", "https://turso.tech/terms-of-use", "Optional hosted shared database")
SEARXNG = credit(
    "SearXNG", "The SearXNG project", "AGPL-3.0-or-later", "https://github.com/searxng/searxng",
    "Optional: finds official pages on a place's own site, only when SEARXNG_URL is set",
    note="Runs as a separate, unmodified service; the search engines it queries have their own terms.")
US_ATLAS = credit(
    "us-atlas", "The TopoJSON project", "ISC", "https://github.com/topojson/us-atlas",
    "County and state shapes for the maps",
    note="Built from the U.S. Census Bureau's cartographic boundary files (2017).")
CLAUDE = credit(
    "Claude", "Anthropic", "Anthropic Usage Policy", "https://www.anthropic.com/legal/aup",
    "Wrote and reviewed the reference models (curated/): the gold this step starts from and is scored against")

# ------------------------------------------------------------------------------ models
NOMIC_EMBED = credit(
    "nomic-embed-text v1.5", "Nomic AI", "Apache-2.0", "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5",
    "Clause embeddings for the learned selector; similarity in Ask",
    cite="Nussbaum, Z., Morris, J. X., Duderstadt, B., & Mulyar, A. (2024). Nomic Embed: Training a Reproducible "
         "Long Context Text Embedder. arXiv:2402.01613")
QWEN3 = credit(
    "Qwen3 1.7B", "Qwen Team, Alibaba Cloud", "Apache-2.0", "https://huggingface.co/Qwen/Qwen3-1.7B",
    "The default chat model: plain-language answers and the independent second extraction",
    cite="Qwen Team (2025). Qwen3 Technical Report. arXiv:2505.09388")
GEMMA3 = credit(
    "Gemma 3 1B", "Google", "Gemma Terms of Use", "https://ai.google.dev/gemma/terms",
    "The other model family for the second extraction and the benchmark",
    cite='Gemma Team, "Gemma 3", Kaggle, 2025, https://goo.gle/Gemma3Report',
    note="Gemma is provided under and subject to the Gemma Terms of Use found at ai.google.dev/gemma/terms")

# The Ollama tags whose credits above were checked.  Ollama's nomic-embed-text 'latest' is the v1.5 image.
MODELS: dict[str, dict] = {
    "nomic-embed-text": NOMIC_EMBED, "nomic-embed-text:latest": NOMIC_EMBED, "nomic-embed-text:v1.5": NOMIC_EMBED,
    "qwen3:1.7b": QWEN3, "gemma3:1b": GEMMA3,
}


def _model_page(tag: str) -> str:
    base = tag.split(":", 1)[0].strip("/")
    if base.startswith(("hf.co/", "huggingface.co/")):
        return "https://huggingface.co/" + base.split("/", 1)[1]
    return f"https://ollama.com/{base}" if "/" in base else f"https://ollama.com/library/{base}"


def model_credit(tag: str, use: str) -> dict:
    """The credit for the Ollama model ``tag`` that config names: the checked credit for a known tag, otherwise
    a pointer to the model's own page that says its licence was not checked."""
    known = MODELS.get(tag.strip().lower())
    if known:
        return used_for(known, use)
    return credit(tag, "The maker named on the model's page", "Not checked by lexflow: see the model's card",
                  _model_page(tag), use,
                  note="Set in .env (LEXFLOW_*_MODEL), so lexflow has not checked this model's licence or terms. "
                       "Read its card before you use it or publish its output.")


def model_credits(roles: list[tuple[str, str]]) -> list[dict]:
    """One credit per distinct model in ``(tag, use)`` pairs, the uses of a model named twice joined."""
    out: dict[str, dict] = {}
    for tag, use in roles:
        c = model_credit(tag, use)
        if c["name"] not in out:
            out[c["name"]] = c
        elif use.lower() not in out[c["name"]]["use"].lower():
            out[c["name"]]["use"] += f"; {use[0].lower()}{use[1:]}"
    return list(out.values())


# ------------------------------------------------------------------- step libraries
SQLITE_FTS5 = credit(
    "SQLite FTS5", "The SQLite developers", "Public domain", "https://www.sqlite.org/fts5.html",
    "The full-text index, one file per state, ranked with BM25")
OPENPYXL = credit(
    "openpyxl", "The openpyxl project", "MIT", "https://openpyxl.readthedocs.io",
    "Reads the Census Excel workbook")
HF_HUB_LIB = credit(
    "huggingface_hub", "Hugging Face", "Apache-2.0", "https://github.com/huggingface/huggingface_hub",
    "Ranged parquet reads (HfFileSystem)")
OMG_SCHEMAS = credit(
    "BPMN 2.0 and DMN 1.3 schemas", "Object Management Group",
    "OMG specification (terms for the XSD files not checked)",
    "https://www.omg.org/spec/BPMN/2.0/About-BPMN", "Schema checks for every BPMN and DMN file (schemas/)",
    note="The BPMN 2.0 page gives the specification's IPR mode as RF-RAND: that is OMG's patent policy, not a "
         "licence for the XSD files. The DMN 1.3 page was not checked.")
BPMNLINT = credit(
    "bpmnlint", "bpmn.io", "MIT", "https://github.com/bpmn-io/bpmnlint",
    "BPMN lint checks, with lexflow's own Lexipedia rules")
CAMUNDA_COMPAT = credit(
    "bpmnlint-plugin-camunda-compat", "Camunda", "MIT", "https://github.com/camunda/bpmnlint-plugin-camunda-compat",
    "Engine-compatibility lint rules")
DMNLINT = credit("dmnlint", "bpmn.io", "MIT", "https://github.com/bpmn-io/dmnlint", "DMN lint checks")
BPMN_AUTO_LAYOUT = credit(
    "bpmn-auto-layout", "bpmn.io", "MIT", "https://github.com/bpmn-io/bpmn-auto-layout", "Lays out the diagrams")
MODDLE = credit(
    "bpmn-moddle and dmn-moddle", "bpmn.io", "MIT", "https://github.com/bpmn-io",
    "Read and write BPMN and DMN in the Node tools")
PM4PY = credit(
    "pm4py", "Process Intelligence Solutions", "AGPL-3.0-or-later",
    "https://github.com/process-intelligence-solutions/pm4py",
    "Turns each model into a workflow net and checks its soundness",
    cite="Berti, A., van Zelst, S., & Schuster, D. (2023). PM4Py: A process mining library for Python. Software "
         "Impacts, 17, 100556. https://doi.org/10.1016/j.simpa.2023.100556")
# PuLP's LICENSE (repository and the installed 2.9.0 dist-info) is the MIT licence; only its PyPI classifier says BSD
# pm4py's metadata does not require PuLP: lexflow's requirements.txt installs it (pulp<3), and pm4py's
# linear-programming interface (pm4py.util.lp) uses it when it is installed
PULP = credit("PuLP", "COIN-OR", "MIT", "https://github.com/coin-or/pulp",
              "A linear-programming solver interface pm4py can use; installed by lexflow's requirements (pulp<3)",
              note="Ships the CBC solver as binaries under their own licence (EPL-1.0; see CBC).")
# pulp/solverdir/cbc/*/coin-license.txt in the installed PuLP 2.9.0 is the Eclipse Public License v1.0; the CBC
# source on the linked page is now EPL-2.0 (its README), so the licence names the bundled copy
CBC = credit("CBC", "COIN-OR", "EPL-1.0 (the binaries bundled with PuLP 2.9.0)", "https://github.com/coin-or/Cbc",
             "The solver binaries bundled with PuLP (pulp/solverdir/cbc), installed with it",
             note="The licence files bundled with PuLP 2.9.0 are EPL-1.0; the README on the linked page gives "
                  "EPL-2.0 for CBC's current source.")
POWL = credit(
    "POWL", "Fraunhofer FIT process mining group", "AGPL-3.0-or-later", "https://github.com/fit-process-mining/POWL",
    "POWL 2.0 choice graphs derived from the net",
    # the README asks for no citation; it refers to this paper
    cite="Kourani, H., Park, G., & van der Aalst, W. M. P. (2025). Unlocking Non-Block-Structured Decisions: "
         "Inductive Mining with Choice Graphs. arXiv:2505.07052")
SPIFFWORKFLOW = credit(
    # the file headers grant "version 3.0 of the License, or (at your option) any later version"
    "SpiffWorkflow", "Sartography", "LGPL-3.0-or-later", "https://github.com/sartography/SpiffWorkflow",
    "Runs the models (simulation) and checks the DMN tables",
    # from CITATION.cff (title, version, date-released, doi and authors, in the file's order).  The file lists one
    # author with family-names "Jon" and given-names "Herron"; that is kept as the file gives it.
    cite="Esswein, E., Abels, S., Funk, D., Jon, H., & McDonald, K. (2025). SpiffWorkflow (Version 3.1.1) "
         "[Computer software]. Zenodo. https://doi.org/10.5281/zenodo.14966563",
    note="lexflow applies a small patch (patches/spiffworkflow-nested-data-object.patch). It runs 3.2.0; the "
         "maker's CITATION.cff lists 3.1.1 under the concept DOI, which covers every version.")

# ------------------------------------------------- used across the steps (end of the Setup page)
GENERAL: list[dict] = [
    credit("FastAPI", "The FastAPI project", "MIT", "https://fastapi.tiangolo.com/", "The dashboard's API"),
    credit("Starlette", "The Starlette project", "BSD-3-Clause", "https://starlette.dev/", "FastAPI's web toolkit"),
    credit("Uvicorn", "The Uvicorn project", "BSD-3-Clause", "https://uvicorn.dev/", "The web server"),
    credit("SQLite", "The SQLite developers", "Public domain", "https://www.sqlite.org/copyright.html",
           "The local store"),
    credit("bpmn-js", "bpmn.io, Camunda Services GmbH", "bpmn.io licence (MIT terms and a visible watermark)",
           "https://bpmn.io/license/", "Diagrams on the model, answer and job pages",
           note="The bpmn.io watermark stays fully visible on every diagram, as the licence requires."),
    credit("d3", "The d3 project", "ISC", "https://d3js.org", "Maps and charts"),
    credit("topojson-client", "The TopoJSON project", "ISC", "https://github.com/topojson/topojson-client",
           "Turns the map shapes into GeoJSON"),
    credit("requests", "Python Software Foundation", "Apache-2.0", "https://github.com/psf/requests",
           "Every HTTP request"),
    credit("pyarrow", "Apache Arrow", "Apache-2.0", "https://arrow.apache.org/",
           "Reads the parquet files (statutes, LOCUS, Ask)"),
    credit("pandas", "The pandas development team", "BSD-3-Clause", "https://pandas.pydata.org",
           "Tables while loading governments and statutes"),
    credit("NumPy", "The NumPy developers", "BSD-3-Clause (with MIT, 0BSD, Zlib and CC0 parts)", "https://numpy.org",
           "The selector's and Ask's vectors"),
    credit("lxml", "The lxml dev team", "BSD-3-Clause", "https://lxml.de/",
           "Writes BPMN and DMN, validates them against the schemas, renders wiki pages"),
    credit("pydantic", "Pydantic", "MIT", "https://github.com/pydantic/pydantic",
           "The facts schema and the API's request models"),
    credit("Graphviz and the graphviz Python package", "The Graphviz project", "EPL; the Python package is MIT",
           "https://graphviz.org/license/", "Draws the POWL graphs"),
    credit("CairoSVG", "CourtBouillon", "LGPL-3.0-or-later", "https://github.com/Kozea/CairoSVG/",
           "SVG to PNG for drawings and charts"),
    # the Ask job is not a Setup step, so its one outside service is credited here
    used_for(SEARXNG, "Optional, for Answer a new question (Ask): finds official pages on a place's own site, only "
                      "when SEARXNG_URL is set ('search' profile)"),
    credit("Python", "Python Software Foundation", "PSF-2.0", "https://docs.python.org/3/license.html",
           "The pipeline and the API"),
    credit("Node.js", "OpenJS Foundation", "MIT", "https://nodejs.org/", "Runs the BPMN and DMN tools"),
]
