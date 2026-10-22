"""Chile: Ley Chile (Biblioteca del Congreso Nacional), the consolidated text of every norma as XML.

Verified 19 October 2026 (docs/design/global-sources.md §2.2):

* ``https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=<id>`` returns one norma's consolidated text as XML
  (schema ``http://www.leychile.cl/esquemas/EsquemaIntercambioNorma-v1-0.xsd``): ``Norma`` (normaId, fechaVersion,
  derogado) > ``Identificador`` (Tipo, Numero, Organismo, fechaPromulgacion, fechaPublicacion) > ``Metadatos``
  (TituloNorma, NombresUsoComun, Materias) > ``EstructurasFuncionales`` > ``EstructuraFuncional`` (tipoParte Libro /
  Título / Capítulo / Párrafo / Artículo / Disposición Transitoria, idParte, fechaVersion, derogado) nested, each
  with ``Texto``.  The same URL is what the Ley Chile web application itself calls; no key was needed for one
  document.
* ``https://datos.bcn.cl/sparql`` (Linked Open Data, Crawl-delay 10) lists the normas: 359,739 ``bcn-norms:RootNorm``
  and 748,821 ``bcn-norms:Norm`` (versions) on 19 October 2026, with ``http://datos.bcn.cl/recurso/cl/{tipo}/{org}/
  {fecha_publicacion}/{numero}`` as persistent URIs.
* Licence: the Ley Chile application states "Ley Chile y sus contenidos se encuentran amparados por la licencia
  Creative Commons CC BY-NC-ND 4.0", and the API conditions (condiciones-de-uso-api-v1.1.pdf) require an API key
  (500 requests per 24 h) and prohibit "extracciones masivas, sistemáticas o automatizadas de datos ... con el
  objeto de replicar, reconstruir o generar una base de datos sustancialmente equivalente a Ley Chile" without the
  Library's express authorisation.  So: samples and per-question lookups are fine; a full pull needs a written
  agreement (global-sources.md §6).

Rows: one per ``Artículo`` (transitory articles under ``Disposiciones transitorias``), path
``Ley 19.628 / Título I / Artículo 4``, citation ``Ley 19.628, art. 4``, act_id ``STATE_CHL_LEY19628_TI_A4`` (the
lexflow key is ISO alpha-3 ``chl``), ELI ``.../eli/cl/ley/1999/19628/art_4/es@<fechaVersion>`` (the ELI keeps
alpha-2 ``cl``).

Interim mode (22 October 2026), until BCN answers the request in docs/design/requests/bcn-chile.md: no bulk pull.
``find(number)`` asks the Linked Open Data endpoint for the norma a question cites by number (10 s pace, no API
quota; a title-word search timed out); ``on_demand(ids)`` fetches at most ``PER_QUESTION`` (3) normas for one
question and ``PER_DAY`` (100) in a UTC day — a fifth of the 500 requests per 24 h an API key allows — through the
same per-document XML the Ley Chile application uses, into a bounded cache (``data/cache/countries/chl/``,
``CACHE_MAX`` normas, refreshed after ``CACHE_DAYS``); ``rows_on_demand`` gives their rows with the attribution the
CC BY-NC-ND licence asks for.  The text is quoted unmodified (ND), the use must stay non-commercial (NC), and every
answer links back to Ley Chile.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import json
import os
import time
from pathlib import Path

from ... import config
from .base import Country, Document, Node, Source

# the interim mode (no agreement with BCN yet): a few normas per question, within a fifth of a key's daily quota
PER_QUESTION = 3
PER_DAY = 100
CACHE = config.DATA_DIR / "cache" / "countries" / "chl"
CACHE_MAX = 300
CACHE_DAYS = 7
ATTRIBUTION = ("Texto: Ley Chile, Biblioteca del Congreso Nacional de Chile, {norma}, versión del {version} "
               "(CC BY-NC-ND 4.0), https://www.bcn.cl/leychile/")
NS = {"l": "http://www.leychile.cl/esquemas"}
XML_URL = "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma={id}"
PAGE_URL = "https://www.bcn.cl/leychile/navegar?idNorma={id}"
SPARQL = "https://datos.bcn.cl/sparql"
# the norms vocabulary as the endpoint uses it (read 22 Oct 2026): a version is a bcn:Norm with bcn:leychileCode,
# dc:title, bcn:isLatestVersion 1 (an integer), bcn:versionOf its root norm, bcn:type .../norma/tipo#ley
TIPO = "http://datos.bcn.cl/recurso/cl/norma/tipo#"
PREFIXES = ("PREFIX bcn: <http://datos.bcn.cl/ontologies/bcn-norms#> PREFIX dc: <http://purl.org/dc/elements/1.1/> ")
# 'Artículo 4°.- El tratamiento', 'Artículo 1º.- Las', 'Artículo 10.- No', 'Artículo 24 bis.- ...'
ARTICLE = re.compile(r"^\s*Art[íi]culo\s+(\d+[a-z]*(?:\s+(?:bis|ter|qu[áa]ter|quinquies))?)\s*[°º]?\s*(?:\.-|\.|-)?\s*",
                     re.I)
LEVELS = {"Libro": "L", "Título": "T", "Titulo": "T", "Capítulo": "C", "Capitulo": "C", "Párrafo": "P", "Parrafo": "P",
          "Disposición Transitoria": "DT", "Artículo": "A", "Articulo": "A", "Parte": "PT", "Sección": "S", "Seccion": "S"}
ROMAN = re.compile(r"^(?:[IVXLCDM]+|\d+|Preliminar|Final|Único|Unico)$", re.I)


class Chile(Country):
    code = "chl"
    iso2 = "cl"
    eli_jurisdiction = "cl"
    name = "Chile"
    wikidata = "Q298"
    languages = ("es",)
    code_label = "Legislación chilena (Ley Chile)"
    pace = 2.0
    citation_template = "{kind} {number}, {label}"      # overridden below: 'Ley 19.628, art. 4'
    status = "prototype"
    sources = (
        Source(name="Ley Chile", publisher="Biblioteca del Congreso Nacional de Chile (BCN)",
               url="https://www.bcn.cl/leychile/",
               holds="every norma (leyes, decretos, DFL, reglamentos, ordenanzas, tratados) as consolidated text with "
                     "version history; 359,739 root normas, 748,821 versions (datos.bcn.cl, 19 Oct 2026)",
               format="XML (EsquemaIntercambioNorma v1.0), HTML, PDF", access="per-document XML endpoint "
               "(obtxml opt=7); API Ley Chile with API key (500 requests/24 h); SPARQL at datos.bcn.cl (Crawl-delay 10)",
               identifier="idNorma / idParte; datos.bcn.cl URI cl/{tipo}/{org}/{fecha}/{numero}; no ELI",
               licence="Ley Chile y sus contenidos se encuentran amparados por la licencia Creative Commons CC BY-NC-ND "
                       "4.0 Atribución/Reconocimiento-NoComercial-SinDerivados 4.0 Internacional.",
               licence_url="https://www.bcn.cl/leychile/assets/doc/condiciones-de-uso-api-v1.1.pdf",
               languages=("es",), verified="2026-10-19",
               automated_reading="API conditions §3(e)(vi)-(vii) prohibit mass, systematic or automated extraction "
                                 "to replicate or rebuild a database substantially equivalent to Ley Chile, and "
                                 "large-scale indexing or persistent storage beyond the declared use, without the "
                                 "Library's express authorisation; standard quota 500 requests per 24 h per key."),
        Source(name="BCN Datos Abiertos Enlazados", publisher="Biblioteca del Congreso Nacional de Chile",
               url="https://datos.bcn.cl/es/", holds="RDF metadata of every norma and version, linked to LeyChile",
               format="RDF (SPARQL JSON/XML)", access="SPARQL endpoint https://datos.bcn.cl/sparql",
               identifier="http://datos.bcn.cl/recurso/cl/{tipo}/{org}/{fecha_publicacion}/{numero}",
               licence="robots.txt: Crawl-delay 10; the portal describes the data as 'puestos a libre disposición' "
                       "(RDF); no licence page found", languages=("es",), verified="2026-10-19",
               automated_reading="SPARQL is the intended machine access; 10 s between requests"),
    )

    def fetch_list(self, limit: int = 20) -> list[dict]:
        """The most recently published leyes with their LeyChile ids, from the SPARQL endpoint (10 s pace).  On 22 Oct
        2026 this ORDER BY over every ley timed out (60 s); a full listing belongs to the BCN API once BCN agrees
        (docs/design/requests/bcn-chile.md), the interim mode needs only ``find``."""
        q = (PREFIXES + "SELECT ?norm ?title ?date ?id WHERE { ?v a bcn:Norm ; bcn:isLatestVersion 1 ; "
             "bcn:leychileCode ?id ; bcn:versionOf ?norm ; bcn:type <http://datos.bcn.cl/recurso/cl/norma/tipo#ley> . "
             "OPTIONAL { ?v dc:title ?title } OPTIONAL { ?v bcn:publishDate ?date } } ORDER BY DESC(?date) "
             f"LIMIT {int(limit)}")
        r = self._sparql(q)
        out = []
        for b in r.json().get("results", {}).get("bindings", []):
            out.append({"native_id": b.get("id", {}).get("value"), "uri": b.get("norm", {}).get("value"),
                        "title": b.get("title", {}).get("value"), "published": b.get("date", {}).get("value")})
        return out

    def fetch_document(self, native_id: str) -> Document:
        r = self.get(XML_URL.format(id=native_id), accept="text/xml")
        return self.parse(r.content, native_id)

    # ------------------------------------------------------------------ the interim mode: a few normas per question
    def _sparql(self, q: str):
        """One SPARQL query to datos.bcn.cl at its robots.txt Crawl-delay (10 s), whatever the adapter's pace."""
        from urllib.parse import urlencode
        pace, self.pace = self.pace, 10.0
        try:
            return self.get(f"{SPARQL}?{urlencode({'query': q, 'format': 'json'})}",
                            accept="application/sparql-results+json")
        finally:
            self.pace = pace

    def find(self, number: str, tipo: str = "ley", limit: int = PER_QUESTION) -> list[dict]:
        """The norma a question cites by number (``Ley 19.628`` -> ``find("19.628")``), from the Linked Open Data
        endpoint (no API quota): its LeyChile id, title and publication date.  The endpoint answers this equality
        lookup in under a second; a CONTAINS search over titles timed out after 60 s (22 Oct 2026), so lexflow
        finds Chilean normas by the number a question or a citation gives, not by words."""
        n = re.sub(r"[^0-9A-Za-z\-]", "", str(number or ""))
        if not n:
            return []
        q = (PREFIXES + "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> SELECT DISTINCT ?norm ?id ?title ?date "
             f'WHERE {{ ?norm a bcn:RootNorm ; bcn:hasNumber "{n}"^^xsd:string ; bcn:type <{TIPO}{_slug(tipo)}> ; '
             "bcn:leychileCode ?id . OPTIONAL { ?norm dc:title ?title } OPTIONAL { ?norm bcn:publishDate ?date } } "
             f"LIMIT {int(limit)}")
        out: dict[str, dict] = {}
        for b in self._sparql(q).json().get("results", {}).get("bindings", []):
            nid = b.get("id", {}).get("value")
            out.setdefault(nid, {"native_id": nid, "uri": b.get("norm", {}).get("value"),
                                 "title": b.get("title", {}).get("value"), "published": b.get("date", {}).get("value")})
        return list(out.values())

    def on_demand(self, ids: list[str], cache: Path | None = None, per_question: int = PER_QUESTION,
                  per_day: int = PER_DAY) -> list[Document]:
        """The normas one question needs, fetched on demand: at most ``per_question`` fetched for one call and
        ``per_day`` in a UTC day (a fifth of the standard API key's 500 requests per 24 h), each kept in a bounded
        cache (``data/cache/countries/chl/``, at most ``CACHE_MAX`` normas, oldest dropped) and refetched after
        ``CACHE_DAYS`` days.  No bulk mirror: BCN's conditions forbid one without its authorisation
        (docs/design/requests/bcn-chile.md asks for it)."""
        cache = cache or CACHE
        cache.mkdir(parents=True, exist_ok=True)
        quota = _Quota(cache / "quota.json", per_day)
        out, fetched = [], 0
        for nid in [str(i) for i in ids if str(i).isdigit()]:
            f = cache / f"{nid}.xml"
            fresh = f.exists() and time.time() - f.stat().st_mtime < CACHE_DAYS * 86400
            if not fresh:
                if fetched >= per_question or not quota.take():
                    if f.exists():                      # stale but within the budget's reach later: use it
                        out.append(self.parse(f.read_bytes(), nid))
                    continue
                body = self.get(XML_URL.format(id=nid), accept="text/xml").content
                tmp = f.with_name(f.name + ".part")
                tmp.write_bytes(body)
                os.replace(tmp, f)
                fetched += 1
            out.append(self.parse(f.read_bytes(), nid))
        _trim(cache, CACHE_MAX)
        return out

    def rows_on_demand(self, ids: list[str], **kw) -> list[dict]:
        """``on_demand`` as index rows, each with the attribution Ley Chile's licence asks for."""
        rows = []
        for doc in self.on_demand(ids, **kw):
            for r in self.to_rows(doc):
                r["attribution"] = ATTRIBUTION.format(norma=f"{doc.kind} {doc.number}", version=doc.version_date)
                rows.append(r)
        return rows

    def parse(self, raw: bytes | str, native_id: str = "") -> Document:
        root = ET.fromstring(raw if isinstance(raw, (bytes, bytearray)) else raw.encode("utf-8"))
        norma_id = root.attrib.get("normaId") or native_id
        tn = root.find("l:Identificador/l:TiposNumeros/l:TipoNumero", NS)
        kind = (tn.findtext("l:Tipo", default="", namespaces=NS) if tn is not None else "").strip() or "Norma"
        number = (tn.findtext("l:Numero", default="", namespaces=NS) if tn is not None else "").strip()
        ident = root.find("l:Identificador", NS)
        promulgated = ident.attrib.get("fechaPromulgacion") if ident is not None else None
        published = ident.attrib.get("fechaPublicacion") if ident is not None else None
        title = (root.findtext("l:Metadatos/l:TituloNorma", default="", namespaces=NS) or "").strip()
        usual = [(e.text or "").strip() for e in root.findall("l:Metadatos/l:NombresUsoComun/l:NombreUsoComun", NS)]
        version = root.attrib.get("fechaVersion")
        derogado = root.attrib.get("derogado", "no derogado")
        doc = Document(country=self.code, native_id=norma_id, kind=kind, kind_token=f"{_tok(kind)}{_tok(number)}",
                       number=_dotted(number), title=title, short_title=f"{kind} {_dotted(number)}",
                       language="es", year=(promulgated or published or "")[:4], eli_type=kind.lower(),
                       eli_number=number,
                       url=PAGE_URL.format(id=norma_id),
                       status="repealed" if derogado != "no derogado" else "in_force",
                       version_date=version, promulgated=promulgated, published=published,
                       last_amended_year=int(version[:4]) if version else None, fetched=self.today(),
                       source=self.sources[0].name, licence=self.sources[0].licence,
                       extra={"organismo": (root.findtext("l:Identificador/l:Organismos/l:Organismo", default="",
                                                           namespaces=NS) or "").strip(), "nombres_uso_comun": usual,
                              "xml_url": XML_URL.format(id=norma_id)})
        doc.root = Node(level=kind, label=doc.short_title, number=number, heading=title, native_id=norma_id)
        for ef in root.findall("l:EstructurasFuncionales/l:EstructuraFuncional", NS):
            doc.root.children.append(self._node(ef))
        return doc

    def citation(self, doc: Document, path, leaf: Node) -> str:
        """``Ley 19.628, art. 4``; a transitory article is ``art. 2 transitorio`` (Chilean usage), so it never
        collides with the main article of the same number."""
        return f"{doc.kind} {doc.number}, art. {leaf.number}" if leaf.level in ("Artículo", "Articulo")             else f"{doc.kind} {doc.number}, {leaf.label}"

    def _node(self, ef, transitory: bool = False) -> Node:
        tipo = (ef.attrib.get("tipoParte") or "").strip()
        texto = ef.findtext("l:Texto", default="", namespaces=NS) or ""
        status = "repealed" if ef.attrib.get("derogado", "no derogado") != "no derogado" else "in_force"
        n = Node(level=tipo, label="", native_id=ef.attrib.get("idParte", ""), status=status,
                 effective_from=ef.attrib.get("fechaVersion"))
        if tipo in ("Artículo", "Articulo"):
            m = ARTICLE.match(texto)
            number = (ef.findtext("l:Metadatos/l:NombreParte", default="", namespaces=NS) or "").strip() \
                or (m.group(1) if m else "")
            n.number = f"{number} transitorio" if transitory else number
            n.label = f"Artículo {n.number}".strip()
            n.text = _clean(texto[m.end():] if m else texto)
            n.token = f"A{_tok(number)}" + ("T" if transitory else "")
        else:
            lines = [ln.strip() for ln in texto.strip().splitlines() if ln.strip()]
            first = re.sub(r"\s+", " ", lines[0]) if lines else tipo
            n.label = first
            n.heading = " ".join(lines[1:]).strip()
            m = re.match(r"^(\S+)\s+(\S+)$", first)
            n.number = m.group(2) if m and ROMAN.match(m.group(2)) else ""
            n.token = (LEVELS.get(tipo, _tok(tipo)[:2].upper()) + _tok(n.number)) if tipo != "Disposición Transitoria" \
                else "DT"
        for child in ef.findall("l:EstructurasFuncionales/l:EstructuraFuncional", NS):
            n.children.append(self._node(child, transitory or tipo == "Disposición Transitoria"))
        return n


class _Quota:
    """A per-UTC-day request counter kept in a small JSON file (survives restarts; one process at a time)."""

    def __init__(self, path: Path, per_day: int):
        self.path, self.per_day = path, per_day

    def take(self) -> bool:
        import datetime as dt
        day = dt.datetime.now(dt.timezone.utc).date().isoformat()
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        if d.get("day") != day:
            d = {"day": day, "used": 0}
        if d["used"] >= self.per_day:
            return False
        d["used"] += 1
        self.path.write_text(json.dumps(d), encoding="utf-8")
        return True


def _trim(cache: Path, keep: int) -> None:
    files = sorted(cache.glob("*.xml"), key=lambda f: f.stat().st_mtime)
    for f in files[:max(0, len(files) - keep)]:
        f.unlink()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def _tok(s: str) -> str:
    s = re.sub(r"[^\w]+", "", str(s or ""), flags=re.U)
    return s.upper()


def _dotted(number: str) -> str:
    """Chile writes law numbers with a thousands point: 19628 -> 19.628."""
    return f"{int(number):,}".replace(",", ".") if number.isdigit() else number


def _clean(text: str) -> str:
    """The source wraps lines at ~60 characters: join them, keep paragraph breaks."""
    paras = re.split(r"\n\s*\n", text.strip())
    return "\n\n".join(re.sub(r"\s*\n\s*", " ", p).strip() for p in paras if p.strip())
