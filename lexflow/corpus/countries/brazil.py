"""Brazil: federal laws, decree-laws, complementary laws, constitutional amendments and the Constitution, from the
Congresso Nacional's Normas.leg.br (texts) and the Senado Federal's open data (metadata, Diário Oficial publication,
amendment relations).

Verified 22 October 2026 (docs/design/global-sources.md, section "Brazil"), user agent
``lexflow-research/0.1 (https://github.com/alibama/lexflow)``, one request a second per host at most:

* **Copyright.** Lei nº 9.610/1998 (direitos autorais), art. 8º: "Não são objeto de proteção como direitos autorais
  de que trata esta Lei: ... IV - os textos de tratados ou convenções, leis, decretos, regulamentos, decisões
  judiciais e demais atos oficiais;" (read from the Câmara's compiled text on normas.leg.br).
* **The list.**  ``https://legis.senado.leg.br/sigen/api/catalogo/basico?anoInicial=&anoFinal=&tamanhoPagina=&pagina=``
  is the search catalogue behind https://normas.leg.br/busca (pages from 0, at most 1,000 hits a page, 10,000 a
  query): 37,226 federal norms "com força de lei" (laws, decree-laws, complementary and delegated laws, provisional
  measures, constitutions and amendments) with URN, number, signature date, ementa, popular names, the revoking URN
  (``urnRevogacao``) and the Senado's status (``Revogada``, ``Convertida em Lei`` ...).  Decrees are not in it.
* **Texts.**  ``https://normas.leg.br/api/public/normas?urn=<urn>&tipo_documento=maior-detalhe`` gives each norm as
  schema.org/ELI JSON-LD (``license``: https://creativecommons.org/licenses/by/4.0/) with ``encoding``: the original
  publication and the current compilation ("Compilação Monovigente", the Câmara's or the Senado's) as HTML at
  ``/api/public/binario/<uuid>/texto``; for the Constitution, the ADCT, the CPC and norms since 2017 also a
  structured multi-version compilation (``hasPart``).  The portal: "As normas federais com força de lei publicadas
  antes de 2017 são disponibilizadas apenas com a compilação convencional."  robots.txt: ``Allow: /``.
* **Metadata and amendments.**  ``https://legis.senado.leg.br/dadosabertos/legislacao/urn?urn=<urn>`` (Dados Abertos
  Legislativos, OpenAPI 3.1 at /dadosabertos/v3/api-docs, "API de acesso público, sem necessidade de autenticação";
  more than 10 requests a second may get HTTP 429): the Diário Oficial publications with page and column, ``vides``
  (later norms that amend, revoke, regulate or veto this one, with the affected ``dispositivo``s), ``edivs`` (the
  earlier norms this one affects) and ``disps`` (per provision).  ``/dadosabertos/legislacao/lista`` answered 503
  "Recurso de dados indisponível" throughout.
* **Not used.**  LexML's SRU (``https://www.lexml.gov.br/busca/SRU``): robots.txt ``Disallow: /busca/`` and the
  endpoint answers a JavaScript "Verificação de segurança" page; ``/urn/`` pages are allowed (Crawl-delay 5) but
  carry no text.  Planalto (planalto.gov.br/ccivil_03) closed every TLS connection from the research network.  The
  Câmara's open-data API v2 (dadosabertos.camara.leg.br/api/v2) has no norm texts or amendment relations (its
  compilations reach lexflow through normas.leg.br).

Rows: one per article (``Art. 5º``), the paragraphs (§), incisos and alíneas kept in the article's text, one line
each; the hierarchy Parte / Livro / Título / Capítulo / Seção / Subseção in the path; the article's epígrafe (the
Código Penal's "Homicídio simples") as its heading; the compiler's notes ("(Redação dada pela Lei nº 13.964, de
2019)") taken out of the text and kept with the row (``notes``).  Citation ``Lei nº 13.709/2018, art. 5º``; act_id
``STATE_BRA_LEI13709-2018_C1_A5``; native id the LexML URN with its partition, ``urn:lex:br:federal:lei:2018-08-14;
13709!art5`` (``Art. 55-J`` is ``!art55-10``, LexML's numbering of letters); ELI ``.../eli/br/lei/2018/13709/art_5``;
source URL ``https://normas.leg.br/?urn=<urn>!art5``.  Revoked and vetoed articles are kept in the rows file with
their status and are not indexed.

Files under ``data/raw/countries/bra/``: ``catalog/<year>.json`` (the catalogue as read), ``list.jsonl`` (the norms
of the five kinds, with status), ``normas/<key>.json.gz`` (the normas.leg.br record), ``html/<key>.html.gz`` (the
compilation, embedded images removed), ``senado/<key>.json.gz`` (the Senado record), ``rows/<key>.jsonl`` (the index
rows, one file per norm: ``countries._iter_dir`` streams them; new files wait in ``rows-staging/`` until ``publish``),
``amendments.jsonl``, ``errors.jsonl``, ``wikidata/`` (read-only counts), ``MANIFEST.json``, ``LICENSE-NOTICE.txt``.
A code annexed to its enacting norm after the signature (the CLT, annex of Decreto-Lei nº 5.452/1943) is read as the
norm's articles, the enacting articles becoming the unit "Ato de aprovação" (``!apr_art1``).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Iterator

from ... import config
from .base import Country, Document, Node, Source

CODE = "bra"
RAW = config.RAW_DIR / "countries" / CODE
RESEARCH_UA = "lexflow-research/0.1 (https://github.com/alibama/lexflow)"
CATALOG_URL = "https://legis.senado.leg.br/sigen/api/catalogo/basico"
NORMAS_API = "https://normas.leg.br/api/public/normas"
BINARIO = "https://normas.leg.br/api/public/binario/"
SENADO_URN = "https://legis.senado.leg.br/dadosabertos/legislacao/urn"
PAGE_URL = "https://normas.leg.br/?urn={urn}"
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
LEI_9610 = "https://normas.leg.br/?urn=urn:lex:br:federal:lei:1998-02-19;9610!art8"
PACE = 1.0                                  # seconds between requests to one host
Log = Callable[[str], None]

# Lei nº 9.610/1998 art. 8º IV, verbatim (the Câmara's compilation on normas.leg.br, read 22 October 2026)
COPYRIGHT_QUOTE = ("Art. 8º Não são objeto de proteção como direitos autorais de que trata esta Lei: ... IV - os textos "
                   "de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais atos oficiais;")
ATTRIBUTION = ("Fonte: Normas.leg.br (Congresso Nacional: Senado Federal e Câmara dos Deputados), https://normas.leg.br/, "
               "textos compilados e metadados sob a licença Creative Commons Atribuição 4.0 Internacional (CC BY 4.0, "
               + CC_BY + "); publicações no Diário Oficial da União e relações entre normas: Dados Abertos Legislativos "
               "do Senado Federal (https://legis.senado.leg.br/dadosabertos/). Os textos de leis e demais atos oficiais "
               "não são objeto de proteção como direitos autorais (Lei nº 9.610/1998, art. 8º, IV). Este texto não "
               "substitui o publicado no Diário Oficial da União.")
EDIT_NOTE = ("Editado por lexflow: dividido em artigos, com a hierarquia, as epígrafes e as notas de alteração do "
             "compilador separadas do texto para a busca; o texto dos dispositivos não foi alterado. O índice e os "
             "dados estruturados do lexflow não são produzidos pelo Congresso Nacional.")
ATTRIBUTION_EN = ("Source: Normas.leg.br (National Congress of Brazil: Federal Senate and Chamber of Deputies), "
                  "https://normas.leg.br/, compiled texts and metadata under CC BY 4.0; Official Gazette (Diário "
                  "Oficial da União) publications and amendment relations: Federal Senate open data. Laws and other "
                  "official acts are not protected by copyright (Lei nº 9.610/1998, art. 8, IV). This text does not "
                  "replace the one published in the Diário Oficial da União.")
EDIT_NOTE_EN = ("Edited by lexflow: split into articles, with the hierarchy, article headings and the compiler's "
                "amendment notes separated from the text for search; the text of the provisions is unchanged. "
                "lexflow's index and structured data are not made by the National Congress.")

# the kinds of norm lexflow indexes: URN type -> (Senado sigla, name in citations, English, ELI type)
TYPES: dict[str, tuple[str, str, str, str]] = {
    "constituicao": ("CON", "Constituição", "Constitution", "constituicao"),
    "ato.disposicoes.constitucionais.transitorias": ("ADCT", "Ato das Disposições Constitucionais Transitórias",
                                                     "Transitional Constitutional Provisions Act", "adct"),
    "emenda.constitucional": ("EMC", "Emenda Constitucional", "Constitutional Amendment", "emenda-constitucional"),
    "emenda.constitucional.revisao": ("EMR", "Emenda Constitucional de Revisão", "Revision Constitutional Amendment",
                                      "emenda-constitucional-revisao"),
    "lei.complementar": ("LCP", "Lei Complementar", "Complementary Law", "lei-complementar"),
    "lei": ("LEI", "Lei", "Law", "lei"),
    "lei.delegada": ("LDL", "Lei Delegada", "Delegated Law", "lei-delegada"),
    "decreto.lei": ("DEL", "Decreto-Lei", "Decree-Law", "decreto-lei"),
}
# other kinds that appear as amending norms in the Senado's relations (their URNs are built from the name)
OTHER_TYPES = {"Medida Provisória": "medida.provisoria", "Decreto": "decreto", "Decreto Legislativo": "decreto.legislativo",
               "Resolução": "resolucao"}
NAME_TYPE = {v[1]: k for k, v in TYPES.items()} | OTHER_TYPES
NOT_IN_FORCE = {"revogada", "revogado", "inconstitucional", "rejeitada", "rejeitado", "insubsistente", "sucedida",
                "perda de eficácia", "vigência encerrada", "prejudicada"}
# the codes people ask about most, pulled first: (URN type, number, year)
PRIORITY: list[tuple[str, int, int]] = [
    ("constituicao", 1988, 1988), ("ato.disposicoes.constitucionais.transitorias", 1988, 1988),
    ("lei", 10406, 2002), ("decreto.lei", 2848, 1940), ("decreto.lei", 5452, 1943), ("lei", 13105, 2015),
    ("decreto.lei", 3689, 1941), ("lei", 8078, 1990), ("lei", 8069, 1990), ("lei", 13709, 2018), ("lei", 12527, 2011),
    ("lei", 4591, 1964), ("lei", 9610, 1998), ("lei", 5172, 1966), ("lei", 8112, 1990), ("lei", 14133, 2021),
    ("lei", 9099, 1995), ("lei", 8213, 1991), ("lei", 8212, 1991), ("lei", 8245, 1991), ("lei", 11340, 2006),
    ("lei", 9503, 1997), ("lei", 13146, 2015), ("lei", 10741, 2003), ("lei", 11343, 2006), ("lei", 7210, 1984),
    ("lei", 9394, 1996), ("lei", 8080, 1990), ("lei", 6015, 1973), ("lei", 12965, 2014), ("lei.complementar", 101, 2000),
    ("lei.complementar", 123, 2006), ("lei", 9784, 1999), ("lei", 8429, 1992), ("lei", 10257, 2001), ("lei", 6404, 1976),
    ("lei", 11101, 2005), ("lei", 9605, 1998), ("lei", 12651, 2012), ("lei", 4737, 1965), ("decreto.lei", 4657, 1942),
    ("lei", 12016, 2009), ("lei", 7347, 1985), ("lei", 8987, 1995), ("lei", 9279, 1996), ("lei", 10826, 2003),
    ("lei", 13874, 2019), ("lei", 9307, 1996), ("lei", 8742, 1993), ("lei", 6830, 1980), ("lei", 9868, 1999),
    ("lei", 9882, 1999), ("lei", 13460, 2017), ("lei", 13445, 2017), ("lei", 12846, 2013), ("lei", 13140, 2015),
]
LEVELS = {"parte": (0, "Parte", "P"), "livro": (1, "Livro", "L"), "titulo": (2, "Título", "T"),
          "capitulo": (3, "Capítulo", "C"), "secao": (4, "Seção", "S"), "subsecao": (5, "Subseção", "SS")}
WORD_NUM = {"UNICO": "U", "UNICA": "U", "GERAL": "G", "ESPECIAL": "E", "PRELIMINAR": "PRE", "COMPLEMENTAR": "COMP",
            "FINAL": "FIN", "PRIMEIRO": "1", "PRIMEIRA": "1", "SEGUNDO": "2", "SEGUNDA": "2", "TERCEIRO": "3",
            "TERCEIRA": "3"}


class Brazil(Country):
    code = CODE
    iso2 = "br"
    eli_jurisdiction = "br"
    name = "Brazil"
    wikidata = "Q155"
    languages = ("pt",)
    code_label = "Legislação federal brasileira"
    code_labels = {"pt": "Legislação federal brasileira", "en": "Federal legislation of Brazil"}
    website = "https://normas.leg.br/"
    tokenize = "unicode61 remove_diacritics 2"      # accent-insensitive, no English stemmer (countries.tokenizer)
    pace = PACE
    status = "prototype"
    raw_name = f"{CODE}/rows"       # countries.path_for: the rows, one file per norm (countries._iter_dir)
    sources = (
        Source(name="Normas.leg.br", publisher="Congresso Nacional (Senado Federal e Câmara dos Deputados)",
               url="https://normas.leg.br/",
               holds="federal norms with the force of law: the Constitution and ADCT, constitutional amendments, laws, "
                     "complementary and delegated laws, decree-laws, provisional measures; current compilations "
                     "(Câmara 'Compilação Monovigente na CD' or the Senado's) and original publications; structured "
                     "multi-version compilations for the Constitution, the ADCT, the CPC and norms since 2017",
               format="JSON-LD (schema.org Legislation, ELI-like) per norm; HTML texts",
               access="REST: /api/public/normas?urn=<urn>&tipo_documento=maior-detalhe, /api/public/binario/<id>/"
                      "texto; list via the Senado catalogue legis.senado.leg.br/sigen/api/catalogo/basico",
               identifier="LexML URN (urn:lex:br:federal:lei:2018-08-14;13709), partitions !art5",
               licence="Each record: \"license\": \"https://creativecommons.org/licenses/by/4.0/\". Lei nº 9.610/1998, "
                       "art. 8º: \"Não são objeto de proteção como direitos autorais de que trata esta Lei: ... IV - os "
                       "textos de tratados ou convenções, leis, decretos, regulamentos, decisões judiciais e demais "
                       "atos oficiais;\"",
               licence_url=CC_BY, languages=("pt", "en", "fr"), verified="2026-10-22",
               automated_reading="robots.txt 'User-agent: * Allow: /'; the API is the portal's own public API; "
                                 "lexflow reads at most one request a second",
               note="'Este texto não substitui o publicado no Diário Oficial.' (the portal's legal notice)"),
        Source(name="Dados Abertos Legislativos do Senado Federal", publisher="Senado Federal",
               url="https://legis.senado.leg.br/dadosabertos/",
               holds="per norm: identification, Diário Oficial publications (date, page, column), ementa, "
                     "observations, relations to later norms (vides: alteration, revocation, regulation, veto, with "
                     "the affected provisions) and earlier norms (edivs)",
               format="JSON / XML / CSV", access="REST /dadosabertos/legislacao/urn?urn=, /legislacao/{codigo}; "
               "OpenAPI 3.1 at /dadosabertos/v3/api-docs",
               identifier="Senado document code; LexML URN",
               licence="\"Dados Abertos são representados em meio digital, processáveis por máquina, referenciados na "
                       "rede mundial de computadores e disponibilizados sob licença que permita sua livre utilização.\" "
                       "(www12.senado.leg.br/dados-abertos); the API: \"uma API de acesso público, sem necessidade de "
                       "autenticação\"",
               licence_url="https://www12.senado.leg.br/dados-abertos", languages=("pt",), verified="2026-10-22",
               automated_reading="\"Mais de 10 requisições por segundo estão sujeitas a receber o erro HTTP 429\"; "
                                 "robots.txt of legis.senado.leg.br answered 403; lexflow reads one request a second"),
        Source(name="LexML Brasil", publisher="Senado Federal (Rede de Informação Legislativa e Jurídica)",
               url="https://www.lexml.gov.br/",
               holds="metadata of federal, state and municipal norms, bills, case law and doctrine; the URN resolver",
               format="SRU 1.1 XML (LexML schema)", access="SRU at /busca/SRU (not used: robots.txt "
               "'Disallow: /busca/', and a JavaScript security check); /urn/<urn> pages allowed",
               identifier="LexML URN", licence="no reuse terms published", verified="2026-10-22",
               automated_reading="robots.txt: 'Disallow: /busca/', 'Allow: /urn', 'Crawl-delay: 5'"),
    )

    # ------------------------------------------------------------------ the network (one norm)
    def fetch_list(self, limit: int = 20) -> list[dict]:
        return [e for e in read_list()][:limit] if (RAW / "list.jsonl").exists() else []

    def fetch_document(self, native_id: str) -> Document:
        rec = fetch_record(native_id)
        enc = current_encoding(rec)
        page = get(BINARIO + enc["id"] + "/texto", accept="text/html").content if enc else b""
        entry = list_entries().get(native_id) or {"urn": native_id}
        return self.parse({"entry": entry, "record": slim_record(rec), "html": page.decode("utf-8", "replace"),
                           "encoding": enc, "fetched": self.today()}, native_id)

    # ------------------------------------------------------------------ parsing
    def parse(self, raw, native_id: str = "") -> Document:
        """One norm from ``{"entry": the catalogue entry, "record": the normas.leg.br record (``slim_record``),
        "html": the compilation, "encoding": which one}``."""
        data = raw if isinstance(raw, dict) else json.loads(raw)
        entry, rec = data.get("entry") or {}, data.get("record") or {}
        urn = entry.get("urn") or rec.get("legislationIdentifier") or native_id
        u = parse_urn(urn)
        tipo = u["tipo"]
        sigla, kind, _en, eli_type = TYPES.get(tipo, ("NOR", tipo, tipo, tipo.replace(".", "-")))
        cite = law_cite(tipo, u["numero"], u["year"])
        popular, abbr = popular_name(entry.get("apelido") or "", rec.get("alternateName"))
        enc = data.get("encoding") or {}
        lines = html_lines(data.get("html") or "")
        root, last_year = build_tree(lines, preamble=(tipo == "constituicao"))
        dou = dou_of(rec, data.get("senado"))
        status = "in_force" if is_in_force(entry) else "repealed"
        doc = Document(country=self.code, native_id=urn, kind=kind, kind_token=f"{sigla}{u['numero']}-{u['year']}",
                       number=cite, title=rec.get("headline") or entry.get("nome") or cite,
                       short_title=f"{cite} ({popular})" if popular else cite, language="pt", year=u["year"],
                       eli_type=eli_type, eli_number=str(u["numero"]), url=PAGE_URL.format(urn=urn), status=status,
                       version_date=rec.get("dateModified") or None, promulgated=u["date"],
                       published=rec.get("datePublished") or dou.get("date"),
                       last_amended_year=last_year, fetched=data.get("fetched") or self.today(),
                       source=self.sources[0].name, licence=self.sources[0].licence,
                       extra={"urn": urn, "tipo": tipo, "sigla": sigla, "cite": cite, "popular": popular,
                              "abbrev": abbr, "ementa": entry.get("ementa") or rec.get("abstract") or "",
                              "dou": dou, "text_version": enc.get("version") or "",
                              "encoding": enc.get("name") or "", "encoding_type": enc.get("type") or "",
                              "status_senado": [s.get("nomeSituacao") for s in entry.get("status") or []],
                              "revoked_by": entry.get("urnRevogacao")})
        root.level, root.label, root.number, root.heading, root.native_id = kind, doc.short_title, cite, doc.title, urn
        doc.root = root
        return doc

    def citation(self, doc: Document, path, leaf: Node) -> str:
        cite = (doc.extra or {}).get("cite") or doc.number
        if leaf.level == "Preâmbulo":
            return f"{cite}, preâmbulo"
        if leaf.level == "Texto":
            return cite
        if (leaf.native_id or "").startswith("apr_"):           # the enacting articles before an annexed code
            cite = f"{cite} (ato de aprovação)"
        m = re.fullmatch(r"(\d+)(?:-([A-Z]{1,2}))?", leaf.number or "")
        return f"{cite}, art. {art_label(m.group(1), m.group(2) or '')}" if m else f"{cite}, {leaf.label}"

    def unit_slug(self, leaf: Node, path=()) -> str:
        if leaf.level == "Preâmbulo":
            return "preambulo"
        if leaf.level == "Texto":
            return "texto"
        return ("apr_" if (leaf.native_id or "").startswith("apr_") else "") + "art_" + leaf.number.lower()

    def to_rows(self, doc: Document) -> list[dict]:
        """The base rows, with the LexML URN of each article as ``native_id`` and ``urn``, the normas.leg.br
        address of the article as source URL, and the compiler's notes kept beside the text."""
        if doc.root is None or not doc.root.children:
            return []
        rows = super().to_rows(doc)
        leaves = [leaf for _p, leaf in doc.root.leaves()] if doc.root else []
        urn = (doc.extra or {}).get("urn") or doc.native_id
        for r, leaf in zip(rows, leaves):
            frag = leaf.native_id or ""
            r["urn"] = f"{urn}!{frag}" if frag else urn
            r["native_id"] = r["urn"]
            r["source_url"] = PAGE_URL.format(urn=r["urn"])
            r["law_urn"] = urn
            r["notes"] = getattr(leaf, "notes", None) or []
            r["fetched"] = doc.fetched
        return rows


# ---------------------------------------------------------------------- identifiers and citations
URN_RE = re.compile(r"^urn:lex:br:federal:([a-z.]+):(\d{4})-(\d{2})-(\d{2});([\w.\-]+)$")


def parse_urn(urn: str) -> dict:
    """``urn:lex:br:federal:lei:2018-08-14;13709`` -> tipo, date, year, numero (int when it is one)."""
    m = URN_RE.match((urn or "").split("!")[0].split("@")[0])
    if not m:
        return {"tipo": "", "date": None, "year": "", "numero": ""}
    tipo, y, mo, d, num = m.groups()
    return {"tipo": tipo, "date": f"{y}-{mo}-{d}", "year": y, "numero": int(num) if num.isdigit() else num}


def key_of(urn: str) -> str:
    """The file key of a norm: ``urn:lex:br:federal:lei:2018-08-14;13709`` -> ``lei_2018-08-14_13709``."""
    s = (urn or "").replace("urn:lex:br:federal:", "")
    return re.sub(r"[^\w.\-]+", "_", s.replace(":", "_").replace(";", "_")).strip("_")


def fmt_num(n) -> str:
    """13709 -> 13.709 (Brazilian thousands), 601 -> 601; a non-number as it is."""
    s = str(n)
    return f"{int(s):,}".replace(",", ".") if s.isdigit() else s


def law_cite(tipo: str, numero, year: str) -> str:
    """``Lei nº 13.709/2018``, ``Decreto-Lei nº 2.848/1940``, ``Constituição Federal``, ``ADCT``."""
    if tipo == "constituicao":
        return "Constituição Federal" if str(year) == "1988" else f"Constituição de {year}"
    if tipo == "ato.disposicoes.constitucionais.transitorias":
        return "ADCT"
    name = TYPES.get(tipo, ("", tipo, "", ""))[1]
    return f"{name} nº {fmt_num(numero)}/{year}"


def art_label(num: str, suffix: str = "") -> str:
    """``5`` -> ``5º``, ``10`` -> ``10``, ``1228`` -> ``1.228``, (``121``, ``A``) -> ``121-A``, (``1``, ``A``) ->
    ``1º-A`` (Brazilian usage: ordinal up to nine)."""
    n = int(num)
    out = f"{n}º" if n < 10 else fmt_num(n)
    return f"{out}-{suffix}" if suffix else out


def letters_num(s: str) -> int:
    """LexML numbers a letter suffix: A -> 1, J -> 10, AA -> 27."""
    v = 0
    for ch in s.upper():
        v = v * 26 + (ord(ch) - 64)
    return v


def art_fragment(num: str, suffix: str = "") -> str:
    """The LexML URN partition of an article: ``art5``, ``art55-10`` (Art. 55-J), ``art1228``."""
    return f"art{int(num)}" + (f"-{letters_num(suffix)}" if suffix else "")


def popular_name(apelido: str, alternate=None) -> tuple[str, str]:
    """The first popular name and abbreviation in the Senado's ``apelido`` (``DEL-2848-1940-12-07 , Código Penal
    (1940) (CP)`` -> (``Código Penal``, ``CP``))."""
    names = [x.strip() for x in (apelido or "").split(" , ")[1:] if x.strip()]
    if not names and alternate:
        alts = alternate if isinstance(alternate, list) else [alternate]
        names = [a for a in alts[1:] if isinstance(a, str)]
    if not names:
        return "", ""
    n = names[0]
    abbr = next((m for m in re.findall(r"\(([^()]{1,14})\)", n) if not m.isdigit()), "")
    clean = re.sub(r"\s*\([^()]*\)", "", n).strip()
    return clean, abbr


def number_en(tipo: str, numero, year) -> str:
    if tipo == "constituicao":
        return f"Constitution of {year}"
    if tipo == "ato.disposicoes.constitucionais.transitorias":
        return "Transitional Constitutional Provisions Act (1988)"
    return f"{TYPES.get(tipo, ('', '', 'Norm', ''))[2]} No. {numero:,} of {year}" if isinstance(numero, int) else ""


# a Portuguese citation for index.lookup (countries.norm_num calls it): ``Lei nº 13.709/2018, art. 5º``,
# ``lei 13709/2018 art 5``, ``Lei n. 13.709, de 2018, art. 5o`` -> ``lei13709/2018art5``
_CITE_HEAD = re.compile(r"^\s*(lei complementar|lei delegada|lei|decreto-lei|decreto lei|emenda constitucional de "
                        r"revis[aã]o|emenda constitucional|constitui[cç][aã]o federal|constitui[cç][aã]o|adct|cf)\b", re.I)


def cite_key(cite: str) -> str | None:
    """The comparable form of a Brazilian citation, or None when the text is not one."""
    import unicodedata
    s = unicodedata.normalize("NFKC", cite or "").lower()
    if not _CITE_HEAD.match(s):
        return None
    s = s.replace("constituição", "constituicao").replace("decreto lei", "decreto-lei")
    s = re.sub(r"constituicao federal|^cf\b", "cf", s)
    s = re.sub(r"\bn\s*[º°o.]\s*[º°.]?\s*(?=\d)|\bnúmero\s*(?=\d)", " ", s)     # nº, n.º, no., n. before the number
    s = re.sub(r"(\d)\.(?=\d{3}\b)", r"\1", s)                    # 13.709 -> 13709
    s = re.sub(r",?\s*de\s+(?:\d{1,2}\s+de\s+\w+\s+de\s+)?(\d{4})", r"/\1", s)   # "de 2018" -> /2018
    s = re.sub(r"\b(arts?)\b\.?|\bartigo\b", "art", s)
    s = re.sub(r"(\d)\s*[º°ª]|(\d)o\b", lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r"[\s,.;:]+", "", s)
    return s


# ---------------------------------------------------------------------- HTML -> lines
class Line:
    __slots__ = ("text", "bold", "italic", "center", "tag", "notes", "upper")

    def __init__(self, text, bold=False, italic=False, center=False, tag="p", notes=None):
        self.text, self.bold, self.italic, self.center, self.tag = text, bold, italic, center, tag
        self.notes = notes or []
        letters = [c for c in text if c.isalpha()]
        self.upper = bool(letters) and all(not c.islower() for c in letters)

    def __repr__(self):
        return f"Line({self.text[:60]!r}, bold={self.bold}, center={self.center})"


_WS = re.compile(r"[ \t\r\n    ​﻿]+")
NOTE_START = (r"(?:Reda[çc][ãa]o|Inclu[íi]d|Acrescid|Acrescentad|Revogad|Renumerad|Vide\b|Vig[êe]ncia|Regulamento|"
              r"Regulamenta[çc][ãa]o|Promulga|Produ[çc][ãa]o de efeito|Execu[çc][ãa]o suspensa|Efic[áa]cia|Retificad|"
              r"Convertid|Vetad[oa]s?\s+pel|Declarad|Mantid|Restabelecid|Suprimid|Alterad|Transformad|Primitiv|Artigo|"
              r"Art\.|Par[áa]grafo|§|Inciso|Al[íi]nea|Item|Caput|Express[ãa]o|Texto|Cap[íi]tulo|Se[çc][ãa]o|"
              r"Subse[çc][ãa]o|T[íi]tulo|Livro|Parte|Dispositivo|Numera[çc][ãa]o|Denomina[çc][ãa]o|Anexo|Tabela|Nome|"
              r"Ementa|Pre[âa]mbulo|Com reda|Em vigor|Publica[çc][ãa]o|Republica)")
NOTE_VERB = re.compile(r"reda[çc][ãa]o|acrescid|acrescentad|inclu[íi]d|revogad|renumerad|alterad|suprimid|vetad|vide\b|"
                       r"vig[êe]ncia|transformad|declarad|mantid|restabelecid|efic[áa]cia|efeito|retificad|"
                       r"publicad|em vigor|regulament", re.I)
_PAREN = re.compile(r"\((?:[^()]|\([^()]*\))*\)")
_NOTE_HEAD = re.compile(r"\(\s*" + NOTE_START)


def _is_note(seg: str) -> bool:
    """A parenthesised segment is a compiler's note when it opens with a note word and names what happened."""
    if re.fullmatch(r"\(\s*VETAD[OA]S?\s*\)", seg):
        return False
    return bool(_NOTE_HEAD.match(seg)) and bool(NOTE_VERB.search(seg))


def strip_notes(text: str) -> tuple[str, list[str]]:
    """Text without its compiler's notes, and the notes."""
    notes: list[str] = []

    def rep(m):
        seg = m.group(0)
        if _is_note(seg):
            notes.append(seg)
            return " "
        return seg
    out = _PAREN.sub(rep, text)
    return _WS.sub(" ", out).strip(), notes


def html_lines(raw: str | bytes) -> list[Line]:
    """The compilation as lines: one per paragraph or heading, with whether it is all bold, italic or centred and
    the compiler's notes it carried (italic links whose text is parenthesised, or a parenthesised note in the
    text).  Struck-through text (revoked wording) is dropped."""
    from lxml import etree, html as LH
    if not raw:
        return []
    if isinstance(raw, bytes):                  # the compilations are UTF-8 (their meta says so); lxml would
        raw = raw.decode("utf-8", "replace")    # read bytes without a charset as Latin-1
    raw = re.sub(r"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=\s]+", "data:,", raw)
    raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw)
    try:
        root = LH.fromstring(raw)
    except (etree.ParserError, ValueError):
        return []
    for bad in root.xpath("//style|//script|//head|//img"):
        bad.drop_tree()
    blocks = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li")
    out: list[Line] = []
    for el in root.iter(*blocks):
        if any(a.tag in blocks for a in el.iterancestors()):
            continue
        runs = list(_runs(el, el.tag in ("h3", "h4", "h5", "h6"), False, False, False))
        line = _assemble(runs)
        if line is None:
            continue
        text, bold, italic, notes = line
        st = (el.get("style") or "").replace(" ", "").lower()
        out.append(Line(text, bold, italic, "text-align:center" in st or el.get("align") == "center", el.tag, notes))
    return out


def _runs(el, bold, italic, link, strike):
    tag = el.tag if isinstance(el.tag, str) else ""
    st = (el.get("style") or "").replace(" ", "").lower() if tag else ""
    cls = (el.get("class") or "") if tag else ""
    b = (bold or "font-weight:bold" in st or "font-weight:700" in st or tag in ("b", "strong") or cls == "Strong")
    if "font-weight:normal" in st:
        b = False
    i = italic or "font-style:italic" in st or tag in ("i", "em")
    if "font-style:normal" in st:
        i = False
    lk = link or tag == "a" or cls == "Hyperlink"
    s = strike or "line-through" in st or tag in ("s", "strike", "del")
    if tag == "br":
        yield (" ", b, i, lk, s)
    if el.text and tag:
        yield (el.text, b, i, lk, s)
    for c in el:
        if isinstance(c.tag, str):
            yield from _runs(c, b, i, lk, s)
        if c.tail:
            yield (c.tail, b, i, lk, s)


def _assemble(runs) -> tuple[str, bool, bool, list[str]] | None:
    """Join runs into a line: struck text dropped; italic linked runs that form a parenthesised segment are notes."""
    parts: list[tuple[str, bool, bool, bool]] = []          # text, bold, italic, note-candidate
    for text, b, i, lk, s in runs:
        if s or not text:
            continue
        parts.append((text, b, i, bool(i and lk)))
    if not parts:
        return None
    # group consecutive italic-link runs; a group whose text is "( ... )" is a note
    notes, kept = [], []
    j = 0
    while j < len(parts):
        if parts[j][3]:
            k = j
            while k < len(parts) and (parts[k][3] or not parts[k][0].strip()):
                k += 1
            seg = "".join(p[0] for p in parts[j:k])
            segs = _WS.sub(" ", seg).strip()
            if segs.startswith("(") and segs.endswith(")") and not re.fullmatch(r"\(\s*VETAD[OA]S?\s*\)", segs):
                notes.append(segs)
                kept.append((" ", False, False))
            else:
                kept.extend((p[0], p[1], p[2]) for p in parts[j:k])
            j = k
            continue
        kept.append(parts[j][:3])
        j += 1
    text = _WS.sub(" ", "".join(p[0] for p in kept)).strip()
    if not text and not notes:
        return None
    visible = [p for p in kept if p[0].strip()]
    bold = bool(visible) and all(p[1] for p in visible)
    italic = bool(visible) and all(p[2] for p in visible)
    return text, bold, italic, notes


# ---------------------------------------------------------------------- lines -> the tree
ART_RE = re.compile(r"^(?:Art|ART)(?:igo|IGO)?\.?\s*(\d{1,2}(?:\.\d{3})+|\d+)\s*(?:º|°|ª|o(?![a-zà-ú]))?"
                    r"(?:[-–‑]([A-Z]{1,2})(?![\wà-ú]))?\s*(?:º|°)?\s*[.\-–—:]?\s*(.*)$")
ARTS_RE = re.compile(r"^(?:Arts|ARTS)\.?\s*(\d{1,2}(?:\.\d{3})+|\d+)")
STRUCT_RE = re.compile(r"^(PARTE|LIVRO|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O|Parte|Livro|T[íi]tulo|"
                       r"Cap[íi]tulo|Se[çc][ãa]o|Subse[çc][ãa]o)\s+([IVXLCDM]+(?:[-–][A-Z](?![\w]))?|\d+(?:[-–][A-Z](?![\w]))?|"
                       r"[ÚU]NIC[OA]|[ÚU]nic[oa]|GERAL|Geral|ESPECIAL|Especial|PRELIMINAR|Preliminar|COMPLEMENTAR|"
                       r"Complementar|FINAL|Final|PRIMEIR[OA]|SEGUND[OA]|TERCEIR[OA])(?![\w])\s*\.?\s*[-–—:.]?\s*(.*)$")
END_RE = re.compile(r"^(?:[A-ZÀ-Ú][\wÀ-ú.'\- ]{2,40}),\s*(?:em\s+)?\d{1,2}\s*(?:º|°|o)?\s+de\s+[A-Za-zçÇ]+\s+de\s+\d{4}"
                    r"|^Este texto não substitui")
PREAMBLE_RE = re.compile(r"^PRE[ÂA]MBULO\s*$", re.I)
LABEL_ONLY = re.compile(r"^(?:§\s*\d+\s*[º°]?(?:\s*[-–]\s*[A-Z])?\.?|Par[áa]grafo [úu]nico\.?|[IVXLCDM]+\s*(?:[-–]\s*[A-Z])?"
                        r"\s*[-–—]?|[a-z]\)|\d+\))\s*$")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman(s: str) -> int | None:
    s = s.upper()
    if not s or any(c not in ROMAN for c in s):
        return None
    total = 0
    for a, b in zip(s, s[1:] + " "):
        v = ROMAN[a]
        total += -v if b != " " and ROMAN.get(b, 0) > v else v
    return total


def _fold(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def parse_struct(text: str):
    """``TÍTULO II`` / ``CAPÍTULO IV-A - DISPOSIÇÕES FINAIS`` / ``Seção I Do Homicídio`` -> (rank, level, label,
    number token, name) or None."""
    m = STRUCT_RE.match(text)
    if not m or len(text) > 220:
        return None
    word, num, rest = m.group(1), m.group(2), m.group(3).strip()
    if rest and not (rest[0].isupper() or rest[0].isdigit() or rest[0] in "(“\""):
        return None
    if rest.endswith((";", ",")) or re.match(r"^(?:d[aoe]s?t[ae]|d[oa]s? art|deste|desta)\b", rest, re.I):
        return None
    rank, level, letter = LEVELS[_fold(word)]
    numu = num.replace("–", "-").upper()
    base, _, suf = numu.partition("-")
    n = roman(base)
    word_tok = WORD_NUM.get(_fold(base).upper())
    tok = word_tok or (str(n) if n else base)
    if word_tok:
        label = f"{level} {num.strip().capitalize()}"           # Parte Geral, Capítulo Único
    else:
        label = f"{level} {numu}"                                 # Título II, Capítulo IV-A, Seção 1
    return rank, level, label, f"{letter}{tok}{'-' + suf if suf else ''}", rest


def build_tree(lines: list[Line], preamble: bool = False) -> tuple[Node, int | None]:
    """The units and articles of a compilation; returns the root and the latest year named in an amendment note."""
    root = Node(level="norma", label="")
    stack: list[tuple[int, Node]] = [(-1, root)]
    started = False
    cur: Node | None = None
    rubric = ""
    years: list[int] = []
    seen: dict[str, int] = {}
    n = len(lines)

    def next_content(j):
        while j < n and not lines[j].text:
            j += 1
        return j

    def finish(node: Node | None):
        if node is None:
            return
        body = getattr(node, "_lines", [])
        node.text = "\n".join(body).strip()
        first = body[0] if body else ""
        notes = getattr(node, "notes", [])
        if not re.sub(r"[\s.;,:\-–—]+", "", node.text):            # nothing but a note: "Art. 233. (Revogado)."
            node.status = "vetoed" if any(re.search(r"vetad", x, re.I) for x in notes) and not any(
                re.search(r"revogad|suprimid", x, re.I) for x in notes) else "repealed"
            node.text = " ".join(notes)
        elif re.fullmatch(r"[(\[]?\s*(?:revogad[oa]s?|suprimid[oa]s?)\s*[)\]]?\.?", node.text, re.I):
            node.status = "repealed"
        elif re.fullmatch(r"[(\[]?\s*VETAD[OA]S?\s*[)\]]?\.?", first, re.I) and len(body) == 1:
            node.status = "vetoed"
        del node._lines

    annexed = False
    i = 0
    while i < n:
        ln = lines[i]
        t = ln.text
        if not t:
            i += 1
            continue
        if started and END_RE.match(t):
            # the signature ends the norm, unless a code with articles of its own follows it as the norm's annex
            # (the CLT is Decreto-Lei nº 5.452/1943's annex; the Senado and LexML number its articles as the
            # decree-law's): the enacting articles then become the unit "Ato de aprovação" and the annex is read on
            later = [k for k in range(i + 1, n) if ART_RE.match(lines[k].text) and lines[k].text[:1] not in "“\"‘"]
            if annexed or len(later) < 5:
                break
            finish(cur)
            cur, rubric, annexed = None, "", True
            act = Node(level="Aprovação", label="Ato de aprovação", number="APR", token="APR")
            act.children, root.children = root.children, [act]
            for _p, leaf in act.leaves():
                leaf.native_id = f"apr_{leaf.native_id}" if leaf.native_id else leaf.native_id
            stack = [(-1, root)]
            seen = {}
            i += 1
            continue
        for note in ln.notes:
            years += [int(y) for y in re.findall(r"\b(1[89]\d\d|20\d\d)\b", note)
                      if re.search(r"reda|inclu|acresc|revog|renumer|alter", note, re.I)]
        if preamble and PREAMBLE_RE.match(t):
            finish(cur)
            cur = Node(level="Preâmbulo", label="Preâmbulo", number="preambulo", token="PRE", native_id="preambulo")
            cur._lines, cur.notes = [], []
            root.children.append(cur)
            started = True
            i += 1
            continue
        st = parse_struct(t) if not t.startswith(("“", '"', "‘", "'")) else None
        if st:
            finish(cur)
            cur, rubric = None, ""
            started = True
            rank, level, label, tok, name = st
            if not name:
                j = next_content(i + 1)
                if j < n and _is_unit_name(lines[j]):
                    name = lines[j].text
                    i = j
            while stack[-1][0] >= rank:
                stack.pop()
            node = Node(level=level, label=label, number=tok, heading=name, token=tok)
            stack[-1][1].children.append(node)
            stack.append((rank, node))
            i += 1
            continue
        m = ART_RE.match(t) if not t.startswith(("“", '"', "‘")) else None
        ms = ARTS_RE.match(t) if not m else None
        if m or ms:
            finish(cur)
            started = True
            if m:
                num = m.group(1).replace(".", "")
                suf = (m.group(2) or "").upper()
                rest = m.group(3) or ""
            else:
                num, suf, rest = ms.group(1).replace(".", ""), "", t
            label = art_label(num, suf)
            tok = f"A{num}" + (f"-{suf}" if suf else "")
            frag = art_fragment(num, suf)
            k = seen.get(tok, 0)
            seen[tok] = k + 1
            if k:                                       # a number used twice in one norm (renumbering left over)
                tok, frag = f"{tok}-{k + 1}", f"{frag}_{k + 1}"
            rest, notes = strip_notes(rest)
            notes = list(ln.notes) + notes
            cur = Node(level="Artigo", label=f"Art. {label}" if m else t[:40], number=f"{num}{'-' + suf if suf else ''}",
                       heading=rubric, token=tok, native_id=frag)
            cur.notes = notes
            cur._lines = [rest] if rest else []
            stack[-1][1].children.append(cur)
            rubric = ""
            i += 1
            continue
        if not started:
            i += 1
            continue
        j = next_content(i + 1)
        nxt = lines[j] if j < n else None
        if _is_rubric(ln) and nxt is not None and (ART_RE.match(nxt.text) or ARTS_RE.match(nxt.text)):
            finish(cur)
            cur = None
            rubric = t
            i += 1
            continue
        if cur is not None:
            body, notes = strip_notes(t)
            notes = list(ln.notes) + notes
            if LABEL_ONLY.match(body) and notes:        # "§ 3º" whose words were all a note: keep the note
                body = f"{body} {' '.join(notes)}".strip()
            elif not body:
                cur.notes.extend(notes)
                i += 1
                continue
            cur._lines.append(body)
            cur.notes.extend(notes)
        else:
            top = stack[-1][1]
            if top is not root and not top.heading and _is_unit_name(ln):
                top.heading = t
        i += 1
    finish(cur)
    _drop_empty_units(root)
    if not any(True for _ in _leaf_articles(root)):
        # a norm without articles (an old decree-law of one sentence): the whole body is one leaf
        body = [ln.text for ln in lines if ln.text]
        txt = "\n".join(strip_notes(x)[0] for x in body).strip()
        if txt:
            leaf = Node(level="Texto", label="Texto", number="texto", token="TXT", text=txt)
            leaf.notes = []
            root.children = [leaf]
    return root, (max(years) if years else None)


def _leaf_articles(n: Node):
    for _p, leaf in n.leaves():
        if leaf.level in ("Artigo", "Preâmbulo"):
            yield leaf


def _drop_empty_units(n: Node) -> None:
    n.children = [c for c in n.children if c.level in ("Artigo", "Preâmbulo", "Texto") or _has_leaf(c)]
    for c in n.children:
        if c.children:
            _drop_empty_units(c)


def _has_leaf(n: Node) -> bool:
    return any(c.level in ("Artigo", "Preâmbulo") or _has_leaf(c) for c in n.children)


def _is_unit_name(ln: Line) -> bool:
    t = ln.text
    if len(t) > 250 or ART_RE.match(t) or ARTS_RE.match(t) or STRUCT_RE.match(t) or t.startswith(("§", "“", '"')):
        return False
    if re.match(r"^(?:[IVXLCDM]+\s*[-–]|[a-z]\)|Par[áa]grafo)", t):
        return False
    return ln.center or ln.bold or ln.italic or ln.upper or bool(re.match(r"^D[aeo]s?\b", t))


def _is_rubric(ln: Line) -> bool:
    """An article's epígrafe: a short line, all bold or all capitals (or a small heading), right before it."""
    t = ln.text
    if len(t) > 200 or t.endswith((";", ":", ",")) or t.startswith(("§", "“", '"', "Pena")):
        return False
    if re.match(r"^(?:[IVXLCDM]+\s*[-–—]|[a-z]\)|\d+\)|Par[áa]grafo)", t):
        return False
    return ln.bold or ln.tag in ("h3", "h4", "h5", "h6") or (ln.upper and len(t) <= 120)


# ---------------------------------------------------------------------- records
def slim_record(rec: dict) -> dict:
    """The fields of a normas.leg.br record the rows and the law table use (the whole record stays on disk)."""
    keep = ("@id", "name", "headline", "legislationIdentifier", "legislationDate", "datePublished", "dateModified",
            "abstract", "alternateName", "legislationType", "license", "sdLicense", "sameAs", "keywords")
    out = {k: rec.get(k) for k in keep if rec.get(k) is not None}
    out["encoding"] = [{k: e.get(k) for k in ("additionalType", "version", "name", "contentUrl", "encodingFormat",
                                              "datePublished", "license")} for e in _as_list(rec.get("encoding"))]
    return out


def encodings(rec: dict) -> list[dict]:
    out = []
    for e in _as_list(rec.get("encoding")):
        url = e.get("contentUrl") or ""
        m = re.search(r"/binario/([0-9a-f\-]{36})/", url)
        if not m or "html" not in (e.get("encodingFormat") or "html"):
            continue
        out.append({"id": m.group(1), "version": e.get("version") or "", "type": e.get("additionalType") or "",
                    "name": e.get("name") or "", "url": url.replace("/api/binario/", "/api/public/binario/"),
                    "published": e.get("datePublished")})
    return out


def current_encoding(rec: dict) -> dict | None:
    """The current compilation in Portuguese (the Câmara's or the Senado's), else the original publication."""
    encs = [e for e in encodings(rec) if "Traduzida" not in e["type"] and "Traduzida" not in e["name"]]
    cur = [e for e in encs if e["version"] == "Current"]
    return (cur or [e for e in encs if e["version"] == "Original"] or encs or [None])[0]


_PUB = re.compile(r"\[(Diário Oficial[^\]]*?)\s+de\s+(\d{2})/(\d{2})/(\d{4})[^\]]*\]\s*\(p\.\s*([\w\-]+)(?:,\s*col\.\s*(\w+))?\)")


def dou_of(rec: dict, senado: dict | None = None) -> dict:
    """The original Diário Oficial publication: the Senado's record when at hand, else the normas.leg.br name
    ("Publicação Original [...] [Diário Oficial da União de 31/12/1940] (p. 23911, col. 2)")."""
    for p in senado_publications(senado):
        if p.get("tipo") == "PUB":
            d, mth, y = (p.get("data") or "//").split("/")
            src = _WS.sub(" ", re.sub(r"\s+de\s+\d{2}/\d{2}/\d{4}.*$", "", p.get("fonte") or "")).strip()
            return {"source": src, "date": f"{y}-{mth}-{d}", "page": p.get("pagina"),
                    "column": p.get("coluna"), "from": "senado"}
    for e in _as_list((rec or {}).get("encoding")):
        m = _PUB.search(e.get("name") or "")
        if m and (e.get("version") == "Original" or "Original" in (e.get("name") or "")):
            src, d, mth, y, page, col = m.groups()
            return {"source": _WS.sub(" ", src).strip(), "date": f"{y}-{mth}-{d}", "page": page, "column": col,
                    "from": "normas"}
    return {}


def senado_doc(senado: dict | None) -> dict:
    try:
        docs = senado["DetalheDocumento"]["documentos"]["documento"]
    except (KeyError, TypeError):
        return {}
    return (docs[0] if isinstance(docs, list) else docs) or {}


def _as_list(x) -> list:
    if not x:
        return []
    return x if isinstance(x, list) else [x]


def senado_publications(senado: dict | None) -> list[dict]:
    return _as_list((senado_doc(senado).get("publicacoes") or {}).get("publicacao") if senado else None)


def is_in_force(entry: dict) -> bool:
    if entry.get("urnRevogacao"):
        return False
    if any(_fold(s.get("nomeSituacao") or "") in {_fold(x) for x in NOT_IN_FORCE} for s in entry.get("status") or []):
        return False
    u = parse_urn(entry.get("urn") or "")
    if u["tipo"] == "constituicao":
        return u["year"] == "1988"
    if u["tipo"].startswith("emenda.constitucional"):          # amendments of the 1946 and 1967 constitutions
        return (u["date"] or "") >= "1988-10-05"
    return True


# ---------------------------------------------------------------------- the network
_LAST: dict[str, float] = {}


def get(url: str, params: dict | None = None, accept: str = "application/json", tries: int = 5, pace: float = PACE):
    """One paced, read-only GET (one request a second per host), retried with back-off on 429, 5xx and network
    errors; a 404 raises at once."""
    import requests
    from urllib.parse import urlsplit
    host = urlsplit(url).netloc
    err = None
    for k in range(tries):
        wait = _LAST.get(host, 0) + pace - time.time()
        if wait > 0:
            time.sleep(wait)
        _LAST[host] = time.time()
        try:
            r = requests.get(url, params=params, timeout=(30, 180),
                             headers={"User-Agent": RESEARCH_UA, "Accept": accept})
        except requests.RequestException as e:
            err = e
            time.sleep(min(300, 15 * 2 ** k))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            err = RuntimeError(f"HTTP {r.status_code} {url}")
            time.sleep(min(600, int(r.headers.get("Retry-After") or 0) or 30 * 2 ** k))
            continue
        r.raise_for_status()
        return r
    raise err or RuntimeError(f"failed: {url}")


def fetch_record(urn: str) -> dict:
    return get(NORMAS_API, {"urn": urn, "tipo_documento": "maior-detalhe"}).json()


def fetch_senado(urn: str) -> dict:
    return get(SENADO_URN, {"urn": urn}).json()


def fetch_catalog(a: int, b: int, size: int = 1000) -> dict:
    hits, page, total, rel = [], 0, None, None
    while True:
        p = {"anoInicial": a, "anoFinal": b, "tamanhoPagina": size}
        if page:
            p["pagina"] = page
        d = get(CATALOG_URL, p, pace=1.5).json()
        total, rel = d["totalHits"], d.get("totalHitsRelation")
        got = [h["content"] for h in d.get("searchHits") or []]
        hits += got
        if not got or len(hits) >= total:
            break
        page += 1
    return {"anoInicial": a, "anoFinal": b, "totalHits": total, "relation": rel, "fetched": _now(), "hits": hits}


# ---------------------------------------------------------------------- files
def _gz_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    with gzip.open(tmp, "wb", compresslevel=6) as f:
        f.write(data)
    os.replace(tmp, path)


def _gz_json(path: Path):
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def _write_lines(path: Path, items: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    n = 0
    with open(tmp, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, path)
    return n


def read_lines(path: Path) -> Iterator[dict]:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    yield json.loads(ln)
                except json.JSONDecodeError:
                    continue


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_error(raw: Path, urn: str, stage: str, err) -> None:
    with open(raw / "errors.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"urn": urn, "stage": stage, "error": str(err)[:500], "at": _now()}, ensure_ascii=False) + "\n")


def manifest(raw: Path = RAW, **changes) -> dict:
    p = raw / "MANIFEST.json"
    try:
        m = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        m = {}
    if changes:
        m.update(changes)
        m["licence"] = {"texts": CC_BY, "copyright": LEI_9610, "attribution": ATTRIBUTION, "edit_note": EDIT_NOTE}
        raw.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return m


# ---------------------------------------------------------------------- the list
def build_list(raw: Path = RAW, refresh: bool = False, log: Log = print) -> dict:
    """``list.jsonl``: the norms of the five kinds (and delegated laws) from the catalogue, read year by year into
    ``catalog/`` (a year already read is kept unless ``refresh``)."""
    cat = raw / "catalog"
    cat.mkdir(parents=True, exist_ok=True)
    this_year = dt.date.today().year
    buckets = [(1500, 1899)] + [(y, y) for y in range(1900, this_year + 1)]
    for a, b in buckets:
        p = cat / (f"{a}.json" if a == b else f"{a}-{b}.json")
        if p.exists() and not refresh:
            continue
        d = fetch_catalog(a, b)
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        log(f"bra catalogue {a}-{b}: {d['totalHits']}")
    entries = []
    for p in sorted(cat.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for h in d.get("hits") or []:
            if h.get("tipo") not in TYPES:
                continue
            u = parse_urn(h["urn"])
            entries.append({"urn": h["urn"], "key": key_of(h["urn"]), "tipo": h["tipo"], "numero": h.get("numero"),
                            "date": h.get("assinatura") or u["date"], "year": u["year"], "nome": h.get("nome"),
                            "apelido": h.get("apelido") or "", "ementa": h.get("ementa") or "",
                            "urnRevogacao": h.get("urnRevogacao"), "status": h.get("status") or [],
                            "in_force": is_in_force(h), "cite": law_cite(h["tipo"], u["numero"], u["year"]),
                            "catalogued": d.get("fetched")})
    entries.sort(key=lambda e: (e["tipo"], e["date"] or "", str(e["numero"])))
    n = _write_lines(raw / "list.jsonl", entries)
    from collections import Counter
    by = Counter(e["tipo"] for e in entries)
    force = Counter(e["tipo"] for e in entries if e["in_force"])
    out = {"norms": n, "by_type": dict(by), "in_force_by_type": dict(force), "in_force": sum(force.values()),
           "built": _now(), "catalogue": CATALOG_URL}
    manifest(raw, list=out)
    list_entries.cache_clear()
    return out


def read_list(raw: Path = RAW) -> Iterator[dict]:
    return read_lines(raw / "list.jsonl")


@lru_cache(maxsize=1)
def list_entries(raw: Path = RAW) -> dict[str, dict]:
    return {e["urn"]: e for e in read_list(raw)}


def ordered(entries: list[dict], texts: bool) -> list[dict]:
    """The pull order: the codes people ask about most, then (for texts, norms in force only) the Constitution,
    its amendments, complementary laws, laws newest first, delegated laws, decree-laws newest first."""
    by_num = {(e["tipo"], e["numero"], int(e["year"] or 0)): e for e in entries}
    first = [by_num[k] for k in PRIORITY if k in by_num]
    seen = {e["urn"] for e in first}
    rank = {"constituicao": 0, "ato.disposicoes.constitucionais.transitorias": 0, "emenda.constitucional": 1,
            "emenda.constitucional.revisao": 1, "lei.complementar": 2, "lei": 3, "lei.delegada": 4, "decreto.lei": 5}
    rest = [e for e in entries if e["urn"] not in seen and (e["in_force"] or not texts)]
    rest.sort(key=lambda e: (rank.get(e["tipo"], 9), -(int(e["year"] or 0)), e["date"] or "", str(e["numero"])))
    return first + rest


# ---------------------------------------------------------------------- the pulls (resumable)
def pull_texts(limit: int | None = None, raw: Path = RAW, log: Log = print, only: list[str] | None = None) -> dict:
    """For each norm in force, in ``ordered`` order: the normas.leg.br record, the current compilation's HTML, and
    the rows.  A norm whose rows file exists is skipped, so a rerun resumes; failures go to ``errors.jsonl``."""
    br = Brazil()
    entries = list(read_list(raw))
    todo = [e for e in ordered(entries, texts=True) if (not only or e["urn"] in only)]
    n_first = sum(1 for e in todo[:len(PRIORITY)] if (e["tipo"], e["numero"], int(e["year"] or 0)) in set(PRIORITY))
    done = errs = skipped = 0
    t0 = time.time()
    total = len(todo)
    for k, e in enumerate(todo, 1):
        key = e["key"]
        rows_p = raw / STAGING / f"{key}.jsonl"
        if ((raw / "rows" / f"{key}.jsonl").exists() or rows_p.exists()) and not only:
            skipped += 1
            continue
        try:
            rec_p = raw / "normas" / f"{key}.json.gz"
            if rec_p.exists():
                rec = _gz_json(rec_p)
            else:
                rec = fetch_record(e["urn"])
                _gz_write(rec_p, json.dumps(rec, ensure_ascii=False).encode("utf-8"))
            enc = current_encoding(rec)
            page = ""
            if enc:
                html_p = raw / "html" / f"{key}.html.gz"
                if html_p.exists():
                    with gzip.open(html_p, "rb") as f:
                        page = f.read().decode("utf-8", "replace")
                else:
                    body = get(enc["url"], accept="text/html").content
                    body = re.sub(rb"data:[a-z/+.-]+;base64,[A-Za-z0-9+/=\s]+", b"data:,", body)
                    _gz_write(html_p, body)
                    page = body.decode("utf-8", "replace")
            senado = None
            sen_p = raw / "senado" / f"{key}.json.gz"
            if sen_p.exists():
                senado = _gz_json(sen_p)
            doc = br.parse({"entry": e, "record": slim_record(rec), "html": page, "encoding": enc or {},
                            "senado": senado, "fetched": dt.date.today().isoformat()})
            rows = br.to_rows(doc)
            if not rows:
                _log_error(raw, e["urn"], "parse", f"no rows (encoding {enc and enc['type']})")
            _write_lines(rows_p, rows)
            done += 1
        except Exception as ex:  # noqa: BLE001 - one norm's failure never stops the pull
            errs += 1
            _log_error(raw, e["urn"], "texts", f"{type(ex).__name__}: {ex}")
        if (done + errs) % 25 == 0 and done + errs:
            rate = (time.time() - t0) / max(1, done + errs)
            log(f"bra texts: {k:,}/{total:,} ({done:,} done, {errs} errors, {skipped:,} skipped); "
                f"{rate:.1f} s/norm, ETA {(total - k) * rate / 3600:.1f} h")
        if k == n_first or (done and done % PUBLISH_EVERY == 0):
            log(f"bra texts: published {publish(raw)} rows files")
        if limit and done >= limit:
            break
    published = publish(raw)
    out = {"done": done, "errors": errs, "skipped": skipped, "total": total, "finished": _now(),
           "published": published}
    manifest(raw, texts=out)
    return out


STAGING = "rows-staging"        # new rows files wait here: the index is stamped with rows/, which changes only here
PUBLISH_EVERY = 5000


def publish(raw: Path = RAW) -> int:
    """Move the staged rows files into ``rows/`` (one rename each), so the index source changes in a few steps
    rather than with every norm (index.ready compares the directory's size and time)."""
    src, dst = raw / STAGING, raw / "rows"
    if not src.exists():
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(src.glob("*.jsonl")):
        os.replace(p, dst / p.name)
        n += 1
    return n


def pull_senado(limit: int | None = None, raw: Path = RAW, log: Log = print) -> dict:
    """The Senado record (publications, relations) of every norm of the list, the priority codes first."""
    entries = list(read_list(raw))
    todo = ordered(entries, texts=False)
    done = errs = skipped = 0
    t0 = time.time()
    for k, e in enumerate(todo, 1):
        p = raw / "senado" / f"{e['key']}.json.gz"
        if p.exists():
            skipped += 1
            continue
        try:
            d = fetch_senado(e["urn"])
            _gz_write(p, json.dumps(d, ensure_ascii=False).encode("utf-8"))
            done += 1
        except Exception as ex:  # noqa: BLE001
            errs += 1
            _log_error(raw, e["urn"], "senado", f"{type(ex).__name__}: {ex}")
        if (done + errs) % 50 == 0 and done + errs:
            rate = (time.time() - t0) / max(1, done + errs)
            log(f"bra senado: {k:,}/{len(todo):,} ({done:,} done, {errs} errors, {skipped:,} skipped); "
                f"ETA {(len(todo) - k) * rate / 3600:.1f} h")
        if limit and done >= limit:
            break
    out = {"done": done, "errors": errs, "skipped": skipped, "total": len(todo), "finished": _now()}
    manifest(raw, senado=out)
    return out


def reparse(raw: Path = RAW, log: Log = print, only: Iterable[str] | None = None) -> dict:
    """Rebuild every rows file from the saved records and HTML (no network)."""
    br = Brazil()
    only = set(only or [])
    n = rows = 0
    for e in read_list(raw):
        if only and e["urn"] not in only and e["key"] not in only:
            continue
        rec_p = raw / "normas" / f"{e['key']}.json.gz"
        if not rec_p.exists():
            continue
        try:
            rec = _gz_json(rec_p)
            enc = current_encoding(rec)
            page = ""
            html_p = raw / "html" / f"{e['key']}.html.gz"
            if html_p.exists():
                with gzip.open(html_p, "rb") as f:
                    page = f.read().decode("utf-8", "replace")
            sen_p = raw / "senado" / f"{e['key']}.json.gz"
            senado = _gz_json(sen_p) if sen_p.exists() else None
            doc = br.parse({"entry": e, "record": slim_record(rec), "html": page, "encoding": enc or {},
                            "senado": senado,
                            "fetched": dt.datetime.fromtimestamp(rec_p.stat().st_mtime).date().isoformat()})
            rr = br.to_rows(doc)
        except Exception as ex:  # noqa: BLE001 - a damaged file: logged, the norm's old rows stay
            _log_error(raw, e["urn"], "reparse", f"{type(ex).__name__}: {ex}")
            continue
        _write_lines(raw / "rows" / f"{e['key']}.jsonl", rr)
        n += 1
        rows += len(rr)
        if n % 500 == 0:
            log(f"bra reparse: {n:,} norms, {rows:,} rows")
    return {"norms": n, "rows": rows}


def status(raw: Path = RAW) -> dict:
    from collections import Counter
    entries = list(read_list(raw))
    keys = {e["key"]: e for e in entries}
    have = lambda d, suf: {p.name[: -len(suf)] for p in (raw / d).glob("*" + suf)} if (raw / d).exists() else set()  # noqa: E731
    pub_k, stage_k = have("rows", ".jsonl"), have(STAGING, ".jsonl")
    rows_k, sen_k, html_k = pub_k | stage_k, have("senado", ".json.gz"), have("html", ".html.gz")
    nrows = arts = 0
    for k in rows_k:
        for r in read_lines(raw / ("rows" if k in pub_k else STAGING) / f"{k}.jsonl"):
            nrows += 1
            arts += r.get("act_status") == "in_force" and r.get("level") == "Artigo"
    errors = Counter(x.get("stage") for x in read_lines(raw / "errors.jsonl"))
    size = sum(p.stat().st_size for p in raw.rglob("*") if p.is_file())
    return {"norms": len(entries), "in_force": sum(1 for e in entries if e["in_force"]),
            "by_type": dict(Counter(e["tipo"] for e in entries)),
            "texts_done": len(rows_k), "published": len(pub_k), "html": len(html_k), "senado_done": len(sen_k),
            "rows": nrows, "articles_in_force": arts,
            "texts_by_type": dict(Counter(keys[k]["tipo"] for k in rows_k if k in keys)),
            "error_lines": dict(errors), "bytes_on_disk": size}


# ---------------------------------------------------------------------- the law table (countries._iter_dir)
def law_summary(rows: list[dict], kept: int) -> dict:
    """One norm's row of the index's ``law`` table (countries.LAW_COLUMNS)."""
    r = rows[0]
    urn = r.get("law_urn") or (r.get("native_id") or "").split("!")[0]
    e = list_entries().get(urn) or {}
    u = parse_urn(urn)
    cite = law_cite(u["tipo"], u["numero"], u["year"])
    pop, abbr = popular_name(e.get("apelido") or "")
    eli = r.get("eli") or ""
    head = eli.rpartition("/")[0] if "@" in eli.rpartition("/")[2] else eli
    return {"law_id": urn, "title": (r.get("display_path") or "").split(" / ")[0], "law_num": cite,
            "law_type": u["tipo"], "kind": r.get("kind") or "", "category": "", "abbrev": abbr or pop,
            "kana": "", "promulgated": u["date"] or "", "enforced": r.get("effective_from") or "",
            "revision_id": "", "url": PAGE_URL.format(urn=urn), "revision_url": "",
            "status": "in_force" if e.get("in_force", True) else "repealed", "rows": kept,
            "articles": sum(1 for x in rows if x.get("level") == "Artigo"), "suppl": 0,
            "main_only": int(any(x.get("level") == "Texto" for x in rows)), "revisions": 1, "future_revisions": 0,
            "in_api_list": 1, "number_en": number_en(u["tipo"], u["numero"], u["year"]),
            "eli_work": head.rsplit("/", 1)[0], "kind_en": TYPES.get(u["tipo"], ("", "", "", ""))[2]}


# ---------------------------------------------------------------------- amendments (the law_amendments table shape)
# One row per (law, amending norm, kind, source), in the shape of the law_amendments table (japan.AMEND_TABLE):
# jurisdiction, law_key (the amended norm's URN), amending_key (the amending norm's URN), amending_num (its citation,
# ``Lei nº 7.209/1984``), date (its signature date), kind (amended | repealed | repeals), source, date_kind, enforced,
# amending_title (the Senado's name), revision, retrieved; plus, in amendments.jsonl only, ``relation`` (the Senado's
# words) and ``provisions`` (the affected provisions and what happened to each: "Art. 121, § 2, Inciso 6": Acréscimo).
# Court decisions (Acórdão da ADI / ADPF) that the Senado lists as alterations are kept with kind ``judicial`` in the
# file, never as table rows.
AMENDING = re.compile(r"Altera[çc][ãa]o (?:Permanente|Provis[óo]ria)|Revoga[çc][ãa]o|Acr[ée]scimo Permanente|"
                      r"Renumera[çc][ãa]o", re.I)
NOT_AMENDING = re.compile(r"Vetad|Veto|Correlata|Regulamenta|Ressalva|Recep[çc][ãa]o|Prorroga", re.I)
NAME_RE = re.compile(r"^(Lei Complementar|Lei Delegada|Lei|Decreto-Lei|Decreto Legislativo|Decreto|Medida Provis[óo]ria|"
                     r"Emenda Constitucional de Revis[ãa]o|Emenda Constitucional|Resolu[çc][ãa]o)\s+n[ºo°]\s*([\d.]+)"
                     r"(?:-([A-Z]))?\s+de\s+(\d{2})/(\d{2})/(\d{4})")


def urn_of_name(name: str) -> str | None:
    """``Lei nº 7.209 de 11/07/1984`` -> ``urn:lex:br:federal:lei:1984-07-11;7209`` (the catalogue's own URN when it
    lists the norm)."""
    m = NAME_RE.match((name or "").strip())
    if not m:
        return None
    kind, num, suf, d, mth, y = m.groups()
    kind = kind.replace("Provisoria", "Provisória").replace("Revisao", "Revisão")
    tipo = NAME_TYPE.get(kind) or NAME_TYPE.get(kind.replace("ó", "o"))
    if not tipo:
        return None
    return f"urn:lex:br:federal:{tipo}:{y}-{mth}-{d};{num.replace('.', '')}{('-' + suf.lower()) if suf else ''}"


def cite_of_name(name: str) -> str:
    """``Lei nº 7.209 de 11/07/1984`` -> ``Lei nº 7.209/1984``; other names as they are."""
    m = NAME_RE.match((name or "").strip())
    if not m:
        return (name or "").strip()
    kind, num, suf, _d, _m, y = m.groups()
    return f"{kind} nº {num}{'-' + suf if suf else ''}/{y}"


def amendment_rows(urn: str, senado: dict, retrieved: str | None = None, names: dict[str, str] | None = None
                   ) -> list[dict]:
    """The amendment edges of one norm from its Senado record's ``vides`` (later norms acting on it)."""
    doc = senado_doc(senado)
    by: dict[tuple, dict] = {}
    for v in _as_list((doc.get("vides") or {}).get("vide")):
        rel = v.get("comentario") or ""
        if NOT_AMENDING.search(rel) or not AMENDING.search(rel):
            continue
        name = (v.get("nomeNormaPosterior") or "").strip()
        items = _as_list((v.get("itens") or {}).get("item") if isinstance(v.get("itens"), dict) else None)
        if name.startswith("Mensagem de Veto") or (items and all(re.match(r"Veto", x.get("comentario") or "")
                                                                 for x in items)):
            continue                    # a veto is part of the enactment, not a later amendment
        judicial = name.startswith("Acórdão")
        a_urn = (names or {}).get(name) or (None if judicial else urn_of_name(name))
        whole = bool(re.search(r"Revoga[çc][ãa]o", rel)) and not items
        kind = "judicial" if judicial else ("repealed" if whole else "amended")
        # a provisional measure's alteration lasts only if Congress converts it: its own source, for the exporters
        source = "senado-dadosabertos-mp" if re.search(r"Provis[óo]ria", rel) else "senado-dadosabertos"
        d = (v.get("datAssinatura") or "//").split("/")
        date = f"{d[2]}-{d[1]}-{d[0]}" if len(d) == 3 and d[2] else None
        k = (urn, a_urn or name, kind, source)
        row = by.get(k)
        if row is None:
            dp = (v.get("datapub") or "//").split("/")
            row = by[k] = {"jurisdiction": CODE, "law_key": urn, "amending_key": a_urn, "amending_num": cite_of_name(name),
                           "date": date, "kind": kind, "source": source, "date_kind": "signed",
                           "enforced": None, "amending_title": name, "revision": None, "retrieved": retrieved,
                           "relation": rel, "provisions": [], "senado_code": v.get("codnormaposterior"),
                           "published": f"{dp[2]}-{dp[1]}-{dp[0]}" if len(dp) == 3 and dp[2] else None,
                           "dou": v.get("nomePub")}
        for it in items:
            p = {"provision": _WS.sub(" ", it.get("dispositivo") or "").strip(), "action": it.get("comentario")}
            if p not in row["provisions"]:
                row["provisions"].append(p)
    out = list(by.values())
    for r in list(out):
        if r["kind"] == "repealed" and r["amending_key"]:
            out.append(dict(r, law_key=r["amending_key"], amending_key=urn, amending_num=_cite_of_urn(urn),
                            kind="repeals", amending_title=None, provisions=[]))
    return out


def _cite_of_urn(urn: str) -> str:
    u = parse_urn(urn)
    return law_cite(u["tipo"], u["numero"], u["year"]) if u["tipo"] else urn


def build_amendments(raw: Path = RAW, log: Log = print) -> dict:
    """``amendments.jsonl`` from every Senado record on disk, plus the catalogue's revocations (``urnRevogacao``,
    source ``senado-catalogo``) for the norms whose Senado record is not on disk yet."""
    from collections import Counter
    names: dict[str, str] = {}
    entries = list(read_list(raw))
    for p in sorted((raw / "catalog").glob("*.json")):
        for h in json.loads(p.read_text(encoding="utf-8")).get("hits") or []:
            if h.get("nome"):
                names.setdefault(h["nome"].strip(), h["urn"])
    counts: Counter = Counter()

    def gen():
        for e in entries:
            p = raw / "senado" / f"{e['key']}.json.gz"
            rows = []
            if p.exists():
                retrieved = dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).date().isoformat()
                rows = amendment_rows(e["urn"], _gz_json(p), retrieved, names)
            if e.get("urnRevogacao") and not any(r["kind"] == "repealed" for r in rows):
                a = e["urnRevogacao"]
                base = {"jurisdiction": CODE, "date": parse_urn(a)["date"], "source": "senado-catalogo",
                        "date_kind": "signed", "enforced": None, "revision": None,
                        "retrieved": (e.get("catalogued") or "")[:10] or None, "relation": "urnRevogacao",
                        "provisions": []}
                rows.append(dict(base, law_key=e["urn"], amending_key=a, amending_num=_cite_of_urn(a), kind="repealed",
                                 amending_title=None))
                rows.append(dict(base, law_key=a, amending_key=e["urn"], amending_num=e["cite"], kind="repeals",
                                 amending_title=e.get("nome")))
            for r in rows:
                counts[(r["source"], r["kind"])] += 1
                yield r
    n = _write_lines(raw / "amendments.jsonl", gen())
    out = {"rows": n, "by": {f"{s}/{k}": c for (s, k), c in sorted(counts.items())}, "built": _now()}
    manifest(raw, amendments=out)
    return out


def load_amendments(con, raw: Path = RAW) -> dict:
    """Write amendments.jsonl into the ``law_amendments`` table of ``con`` (created in Japan's shape when missing),
    replacing Brazil's rows; court decisions stay in the file only."""
    from .japan import AMEND_COLUMNS, AMEND_TABLE
    con.executescript(AMEND_TABLE)
    sql = (f"INSERT OR REPLACE INTO law_amendments ({','.join(AMEND_COLUMNS)}) "
           f"VALUES ({','.join('?' * len(AMEND_COLUMNS))})")
    n = 0
    with con:
        con.execute("DELETE FROM law_amendments WHERE jurisdiction=?", (CODE,))
        buf = []
        for r in read_lines(raw / "amendments.jsonl"):
            if r["kind"] not in ("amended", "repealed", "repeals"):
                continue
            buf.append(tuple(r.get(c) for c in AMEND_COLUMNS))
            n += 1
            if len(buf) >= 5000:
                con.executemany(sql, buf)
                buf.clear()
        if buf:
            con.executemany(sql, buf)
    return {"rows": n}


def build_norms(raw: Path = RAW, log: Log = print) -> dict:
    """``norms.jsonl``: one line per norm of the list with its metadata: URN, kind, number, citation, signature
    date, ementa, popular name, status (in force by the catalogue, the Senado's status, the revoking URN) and the
    original Diário Oficial publication (date, page, column) from the Senado record, else from the normas.leg.br
    record's name.  No network."""
    from collections import Counter
    counts: Counter = Counter()

    def gen():
        for e in read_list(raw):
            sp, rp = raw / "senado" / f"{e['key']}.json.gz", raw / "normas" / f"{e['key']}.json.gz"
            dou, sid = {}, None
            try:
                if sp.exists():
                    sen = _gz_json(sp)
                    dou, sid = dou_of({}, sen), senado_doc(sen).get("id")
                if not dou and rp.exists():
                    dou = dou_of(_gz_json(rp))
            except (OSError, ValueError, EOFError):
                pass
            pop, abbr = popular_name(e.get("apelido") or "")
            counts["dou_page" if dou.get("page") else "no_dou_page"] += 1
            yield {"urn": e["urn"], "tipo": e["tipo"], "numero": e["numero"], "cite": e["cite"], "date": e["date"],
                   "ementa": e.get("ementa") or "", "popular": pop, "abbrev": abbr, "in_force": e["in_force"],
                   "status_senado": [s.get("nomeSituacao") for s in e.get("status") or []],
                   "revoked_by": e.get("urnRevogacao"), "dou": dou or None, "senado_id": sid,
                   "normas_url": PAGE_URL.format(urn=e["urn"]), "lexml_url": f"https://www.lexml.gov.br/urn/{e['urn']}"}
    n = _write_lines(raw / "norms.jsonl", gen())
    out = {"norms": n, **counts, "built": _now()}
    manifest(raw, norms=out)
    return out


# ---------------------------------------------------------------------- Wikidata (read-only counts)
def _wd_rows(raw: Path, name: str) -> list[dict] | None:
    p = raw / "wikidata" / f"{name}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("rows") or []


def _qid(v: str) -> str:
    return (v or "").rsplit("/", 1)[-1]


def reconcile(raw: Path = RAW, focus: str = "urn:lex:br:federal:decreto.lei:1940-12-07;2848") -> dict:
    """Counts only, from the files ``data/raw/countries/bra/wikidata/*.json`` (Wikidata items with a LexML Brazil ID,
    P9119, and their statements, read-only from the QLever Wikidata mirror) against lexflow's list, rows and
    amendments: how many of lexflow's norms have an item, how many items lack what lexflow holds (amended by P2567,
    repealed by P2568, publication date P577, date of promulgation P7589, effective date P7588, published in P1433
    with its page), and the Diário Oficial pages that differ.  ``focus`` gets the per-law detail (the Código Penal)."""
    from collections import Counter, defaultdict
    p9119 = _wd_rows(raw, "p9119")
    if p9119 is None:
        return {"error": "no wikidata/p9119.json yet (the QLever read has not run)"}
    item_of: dict[str, set[str]] = defaultdict(set)
    for r in p9119:
        item_of[r["urn"].strip()].add(_qid(r["item"]))
    has = {}
    for name in ("p2567", "p2568", "p3148", "p7588", "p577", "p7589", "p953", "p1433", "p31", "p1031"):
        rows = _wd_rows(raw, name)
        if rows is not None:
            has[name] = defaultdict(set)
            for r in rows:
                has[name][_qid(r["item"])].add(_qid(r.get("v", "")) if name in ("p2567", "p2568", "p3148", "p31",
                                                                                 "p1433") else r.get("v"))
    entries = list(read_list(raw))
    ours = {e["urn"]: e for e in entries}
    texts = {p.name[:-6] for p in (raw / "rows").glob("*.jsonl")} if (raw / "rows").exists() else set()
    matched = {u: item_of[u] for u in ours if u in item_of}
    one = {u: next(iter(q)) for u, q in matched.items() if len(q) == 1}
    out = {"wikidata_p9119_statements": len(p9119), "wikidata_distinct_urns": len(item_of),
           "lexflow_norms": len(entries), "lexflow_in_force": sum(1 for e in entries if e["in_force"]),
           "matched_norms": len(matched), "matched_one_item": len(one),
           "matched_several_items": sum(1 for q in matched.values() if len(q) > 1),
           "matched_by_type": dict(Counter(ours[u]["tipo"] for u in matched)),
           "matched_with_text_indexed": sum(1 for u in matched if ours[u]["key"] in texts),
           "wikidata_urns_not_in_lexflow_list": sum(1 for u in item_of if u not in ours),
           "wikidata_not_in_list_by_type": dict(Counter(parse_urn(u)["tipo"] or "other" for u in item_of
                                                        if u not in ours).most_common(12))}
    items = set(one.values())
    for name, label in (("p7588", "effective_date_P7588"), ("p577", "publication_date_P577"),
                        ("p7589", "date_of_promulgation_P7589"), ("p1433", "published_in_P1433"),
                        ("p2567", "amended_by_P2567"), ("p2568", "repealed_by_P2568"), ("p953", "full_text_url_P953")):
        if name in has:
            out[f"items_without_{label}"] = sum(1 for q in items if not has[name].get(q))
    # what lexflow holds: amendment edges between two norms that both have exactly one item
    edges = list(read_lines(raw / "amendments.jsonl"))
    perm = [e for e in edges if e["kind"] == "amended" and e["source"] == "senado-dadosabertos"]
    both = [e for e in perm if e["law_key"] in one and e.get("amending_key") in one]
    out["lexflow_amended_edges_permanent"] = len(perm)
    out["amended_edges_both_items"] = len(both)
    if "p2567" in has:
        missing = [e for e in both if one[e["amending_key"]] not in has["p2567"].get(one[e["law_key"]], set())]
        out["amended_by_edges_missing_on_wikidata"] = len(missing)
        out["items_lacking_amended_by_that_lexflow_has"] = len({e["law_key"] for e in missing})
    rep = [e for e in edges if e["kind"] == "repealed" and e["law_key"] in one and e.get("amending_key") in one]
    if "p2568" in has:
        out["repealed_by_edges_missing_on_wikidata"] = sum(
            1 for e in rep if one[e["amending_key"]] not in has["p2568"].get(one[e["law_key"]], set()))
    # Diário Oficial pages: Wikidata's P1433/P304 against the Senado's record
    pages = _wd_rows(raw, "p1433") or []
    wd_page = defaultdict(set)
    for r in pages:
        if r.get("page"):
            wd_page[_qid(r["item"])].add(r["page"].strip())
    diffs, compared = [], 0
    for u, q in one.items():
        if not wd_page.get(q):
            continue
        sp = raw / "senado" / f"{ours[u]['key']}.json.gz"
        if not sp.exists():
            continue
        dou = dou_of({}, _gz_json(sp))
        if not dou.get("page"):
            continue
        compared += 1
        if dou["page"] not in wd_page[q]:
            diffs.append({"urn": u, "item": q, "wikidata": sorted(wd_page[q]), "senado": dou["page"],
                          "date": dou.get("date")})
    out["dou_pages_compared"] = compared
    out["dou_pages_differing"] = len(diffs)
    out["dou_page_examples"] = diffs[:20]
    # the focus law (the Código Penal): its amending norms and their items
    fe = [e for e in perm if e["law_key"] == focus]
    out["focus"] = {"law": focus, "item": sorted(item_of.get(focus, [])),
                    "amending_norms": len({e["amending_key"] for e in fe}),
                    "amending_norms_with_item": len({e["amending_key"] for e in fe if e["amending_key"] in one}),
                    "amended_by_on_wikidata": len(has.get("p2567", {}).get(one.get(focus, ""), set())),
                    "provisions": sum(len(e.get("provisions") or []) for e in fe)}
    manifest(raw, wikidata=dict((k, v) for k, v in out.items() if k != "dou_page_examples"))
    return out


# ---------------------------------------------------------------------- the notice
NOTICE = """Normas.leg.br and Senado Federal open data (Brazil) -- licence notice kept with the download
=========================================================================================

Atribuição (fonte)
  {attribution}
  Obtido em: {fetched}

Edição
  {edit_note}

In English
  {attribution_en}
  Retrieved: {fetched}
  {edit_note_en}

As the sources state it (read 2026-10-22)
  Normas.leg.br, every record: "license": "{cc}"  (also "sdLicense")
  Lei nº 9.610/1998 (direitos autorais), art. 8º ({lei}):
    "{copyright}"
  Senado Federal, Dados Abertos (https://www12.senado.leg.br/dados-abertos):
    "Dados Abertos são representados em meio digital, processáveis por máquina, referenciados na rede mundial de
    computadores e disponibilizados sob licença que permita sua livre utilização."
  Dados Abertos Legislativos API (https://legis.senado.leg.br/dadosabertos/v3/api-docs): "uma API de acesso público,
    sem necessidade de autenticação"; "Mais de 10 requisições por segundo estão sujeitas a receber o erro HTTP 429".
  Normas.leg.br legal notice: "Este texto não substitui o publicado no Diário Oficial."

Files here
  {files}
"""


def write_notice(raw: Path = RAW) -> Path:
    m = manifest(raw)
    files = [f"{k}: {json.dumps(v, ensure_ascii=False)[:300]}" for k, v in m.items() if k in ("list", "texts", "senado",
                                                                                              "amendments")]
    p = raw / "LICENSE-NOTICE.txt"
    raw.mkdir(parents=True, exist_ok=True)
    p.write_text(NOTICE.format(attribution=ATTRIBUTION, edit_note=EDIT_NOTE, attribution_en=ATTRIBUTION_EN,
                               edit_note_en=EDIT_NOTE_EN, fetched=dt.date.today().isoformat(), cc=CC_BY, lei=LEI_9610,
                               copyright=COPYRIGHT_QUOTE, files="\n  ".join(files) or "(none yet)"), encoding="utf-8")
    return p


# ---------------------------------------------------------------------- command line
def main(argv: list[str] | None = None) -> int:
    """``python -m lexflow.corpus.countries.brazil list|pull-texts|pull-senado|reparse|amendments|status|notice|
    sample <urn>``"""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="lexflow.corpus.countries.brazil")
    ap.add_argument("action", choices=["list", "pull-texts", "pull-senado", "reparse", "amendments", "status", "notice",
                                       "publish", "wikidata", "norms", "sample"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args(argv)

    def log(s):
        print(f"{time.strftime('%H:%M:%S')} {s}", flush=True)
    if a.action == "list":
        out = build_list(refresh=a.refresh, log=log)
    elif a.action == "pull-texts":
        out = pull_texts(limit=a.limit, log=log, only=a.ids or None)
    elif a.action == "pull-senado":
        out = pull_senado(limit=a.limit, log=log)
    elif a.action == "reparse":
        out = reparse(log=log, only=a.ids or None)
    elif a.action == "amendments":
        out = build_amendments(log=log)
    elif a.action == "status":
        out = status()
    elif a.action == "notice":
        out = str(write_notice())
    elif a.action == "publish":
        out = {"published": publish()}
    elif a.action == "wikidata":
        out = reconcile()
    elif a.action == "norms":
        out = build_norms(log=log)
    else:
        br = Brazil()
        for urn in a.ids:
            doc = br.fetch_document(urn)
            rows = br.to_rows(doc)
            sys.stdout.write(json.dumps({"urn": urn, "rows": len(rows), "first": rows[0] if rows else None},
                                        ensure_ascii=False)[:3000] + "\n")
        return 0
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
