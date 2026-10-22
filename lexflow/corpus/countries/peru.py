"""Peru: no official consolidated-text service was reachable; the official sources publish PDFs.  Stub
(docs/design/global-sources.md §2.1).

Verified 19 October 2026:

* SPIJ, Sistema Peruano de Información Jurídica (Ministerio de Justicia y Derechos Humanos),
  https://spij.minjus.gob.pe/ — the official consolidated legislation (texto actualizado) with SPIJ Libre as the
  free tier.  Unreachable from the research network (TCP connect timeout on 443 and 80, also for
  spijlibre.minjus.gob.pe); Legal Data Hunter reports a REST API with public authentication and ~1.4 M norm ids.
  Terms, format and quota remain unverified.
* Archivo Digital de la Legislación del Perú (Congreso de la República), https://leyes.congreso.gob.pe/ — every
  norma con rango de ley since 1904 (leyes, resoluciones legislativas, decretos leyes, decretos legislativos,
  decretos de urgencia, leyes regionales) as PDF scans/prints; ASP.NET search forms; robots.txt ``Disallow: /*.pdf$``
  (the documents themselves may not be fetched by robots); no licence page found.
* gob.pe "Normas y documentos legales" (Plataforma del Estado Peruano, PCM), e.g.
  https://www.gob.pe/institucion/minjus/normas-legales — each norma as a page with metadata and the PDF as published
  (``cdn.www.gob.pe/uploads/document/file/...``); as-published texts, not consolidated; robots.txt allows the
  pages and disallows ``?sheet=`` paging.
* El Peruano (Editora Perú), https://busquedas.elperuano.pe/ — the official gazette's "Normas Legales" by day as
  cuadernillos (PDF) with a sitemap; https://diariooficial.elperuano.pe/ disallows /Normas/ paths to robots.
* Regions: the 25 gobiernos regionales publish ordenanzas regionales on gob.pe under each government's
  "normas-legales" (PDF), the same shape as the national pages.

Peru is PDF-first: an adapter needs a PDF text layer step (the Congreso scans before ~2000 need OCR), and the
consolidated texts live in SPIJ, whose access terms must be read from the site itself first.

Re-checked 22 October 2026: spij.minjus.gob.pe and spijweb.minjus.gob.pe still time out on ports 443 and 80 (TCP
connect, 42 s) and spijlibre.minjus.gob.pe closes the TLS handshake, from the container's network and from a
second network (connection refused).  The Ministry's own page on gob.pe ("Acceder al Sistema Peruano de Información
Jurídica (SPIJ)", https://www.gob.pe/748, last changed 13 September 2023) says that "Existe acceso libre a una parte
importante de los documentos" through "Normativa de Acceso Libre", and that full access needs a subscription "y
realices un pago por licencia": the free part is a website, the rest is licensed; no API or open-data terms are
published there.  Verdict: needs permission (an API or bulk agreement with MINJUSDH), not a pull.
"""
from __future__ import annotations

from .base import Country, Source


class Peru(Country):
    code = "per"
    iso2 = "pe"
    eli_jurisdiction = "pe"
    name = "Peru"
    wikidata = "Q419"
    languages = ("es", "qu", "ay")
    code_label = "Legislación peruana (SPIJ)"
    pace = 5.0
    status = "stub"
    note = ("SPIJ unreachable (22 Oct 2026, two networks) and licensed beyond its free part (gob.pe: full access needs "
            "a paid licence); Congreso and gob.pe publish PDFs only (Congreso's robots.txt disallows PDF fetches): ask "
            "MINJUSDH for API or bulk access")
    sources = (
        Source(name="SPIJ - Sistema Peruano de Información Jurídica", publisher="Ministerio de Justicia y Derechos Humanos",
               url="https://spij.minjus.gob.pe/", holds="consolidated national legislation (textos actualizados), "
               "codes, regulations; SPIJ Libre free tier", format="HTML (reported)", access="REST API with public "
               "auth (reported by Legal Data Hunter); not reachable from the research network (connect timeout)",
               identifier="SPIJ norm id", licence="site unreachable; gob.pe: free access to part of the documents "
               "(Normativa de Acceso Libre), the rest by subscription and paid licence", languages=("es",),
               verified="2026-10-22", automated_reading="unknown (no published API terms); permission needed"),
        Source(name="Archivo Digital de la Legislación del Perú", publisher="Congreso de la República",
               url="https://leyes.congreso.gob.pe/", holds="normas con rango de ley since 1904 (leyes, decretos "
               "legislativos, decretos de urgencia, leyes regionales), constitutions, Leyes de Indias; as published",
               format="PDF", access="ASP.NET search pages; robots.txt Disallow /*.pdf$", identifier="law number",
               licence="no licence page found", languages=("es", "qu"), verified="2026-10-19",
               automated_reading="listing pages allowed; PDFs disallowed to robots"),
        Source(name="gob.pe Normas y documentos legales", publisher="Presidencia del Consejo de Ministros (Plataforma "
               "del Estado Peruano)", url="https://www.gob.pe/institucion/minjus/normas-legales",
               holds="each institution's normas as published, with metadata and PDF (national and regional governments)",
               format="HTML page + PDF", access="website listing pages; no API found; robots.txt disallows ?sheet= paging",
               identifier="gob.pe document id + norm number (190877-1384)", licence="no terms page found (privacy "
               "policy only)", languages=("es",), verified="2026-10-19",
               automated_reading="pages allowed to robots; paging parameter disallowed"),
        Source(name="El Peruano - Normas Legales", publisher="Editora Perú (diario oficial)",
               url="https://busquedas.elperuano.pe/", holds="the official gazette's daily Normas Legales cuadernillos",
               format="PDF (HTML index)", access="website with sitemap", identifier="gazette date + norm number",
               licence="no terms page found", languages=("es",), verified="2026-10-19",
               automated_reading="busquedas.elperuano.pe allows all; diariooficial.elperuano.pe disallows /Normas/"),
    )
