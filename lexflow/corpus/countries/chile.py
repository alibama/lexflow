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
``Ley 19.628 / Título I / Artículo 4``, citation ``Ley 19.628, art. 4``, act_id ``STATE_CL_LEY19628_TI_A4``, ELI
``.../eli/cl/ley/1999/19628/art_4/es@<fechaVersion>``.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .base import Country, Document, Node, Source

NS = {"l": "http://www.leychile.cl/esquemas"}
XML_URL = "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma={id}"
PAGE_URL = "https://www.bcn.cl/leychile/navegar?idNorma={id}"
SPARQL = "https://datos.bcn.cl/sparql"
# 'Artículo 4°.- El tratamiento', 'Artículo 1º.- Las', 'Artículo 10.- No', 'Artículo 24 bis.- ...'
ARTICLE = re.compile(r"^\s*Art[íi]culo\s+(\d+[a-z]*(?:\s+(?:bis|ter|qu[áa]ter|quinquies))?)\s*[°º]?\s*(?:\.-|\.|-)?\s*",
                     re.I)
LEVELS = {"Libro": "L", "Título": "T", "Titulo": "T", "Capítulo": "C", "Capitulo": "C", "Párrafo": "P", "Parrafo": "P",
          "Disposición Transitoria": "DT", "Artículo": "A", "Articulo": "A", "Parte": "PT", "Sección": "S", "Seccion": "S"}
ROMAN = re.compile(r"^(?:[IVXLCDM]+|\d+|Preliminar|Final|Único|Unico)$", re.I)


class Chile(Country):
    code = "cl"
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
        """The most recently published leyes with their LeyChile ids, from the SPARQL endpoint (10 s pace)."""
        q = ("PREFIX bcn: <http://datos.bcn.cl/ontologies/bcn-norms#> SELECT ?norm ?title ?date ?id WHERE { "
             "?norm a bcn:RootNorm ; bcn:hasVersion ?v . ?v bcn:isLatestVersion true ; bcn:hasLeyChileId ?id . "
             "OPTIONAL { ?norm dc:title ?title } OPTIONAL { ?norm bcn:publishDate ?date } } ORDER BY DESC(?date) "
             f"LIMIT {int(limit)}")
        from urllib.parse import urlencode
        self.pace = 10.0
        r = self.get(f"{SPARQL}?{urlencode({'query': q, 'format': 'json'})}", accept="application/sparql-results+json")
        out = []
        for b in r.json().get("results", {}).get("bindings", []):
            out.append({"native_id": b.get("id", {}).get("value"), "uri": b.get("norm", {}).get("value"),
                        "title": b.get("title", {}).get("value"), "published": b.get("date", {}).get("value")})
        return out

    def fetch_document(self, native_id: str) -> Document:
        r = self.get(XML_URL.format(id=native_id), accept="text/xml")
        return self.parse(r.content, native_id)

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
        doc = Document(country="cl", native_id=norma_id, kind=kind, kind_token=f"{_tok(kind)}{_tok(number)}",
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
