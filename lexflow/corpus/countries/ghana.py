"""Ghana: no official consolidated-legislation database online; the Parliament's repository holds the Acts as
PDFs and GhaLII (non-profit, with the Judicial Service) publishes Akoma Ntoso versions.  Stub
(docs/design/global-sources.md §2.5).

Verified 19 October 2026:

* Parliament of Ghana Library Repository, https://repository.parliament.gh/ (DSpace 7): communities "ACTS - 1ST
  REPUBLIC" ... "9th and 10th Parliament Acts", executive instruments, Hansard; 1,538 items match "Act" in the
  discover index; each item has the PDF, a thumbnail and an extracted ``.pdf.txt`` (often empty: 28-42 bytes in
  the samples) as bitstreams; REST API at ``/server/api`` (discover/search, core/items, bundles/bitstreams) is open;
  robots.txt allows the API and item pages (``/search`` and ``/admin`` disallowed).  No licence page beyond the
  DSpace deposit ``license.txt`` per item; the repository calls itself "an open access electronic archive".
  Official but as-passed texts, not consolidated.
* GhaLII, https://ghalii.org/ (Ghana Legal Information Institute, a non-profit "in partnership with the Judicial
  Service of Ghana"; AfricanLII/Laws.Africa platform): 568 legislation documents (Acts, decrees, constitutional
  and executive instruments) as Akoma Ntoso with FRBR URIs ``/akn/gh/act/1960/7/eng@2010-04-30``, consolidated
  for part of the collection, many older ones PDF only.  Terms of use: "Scraping and bulk downloading from this
  website is strictly prohibited ... Please email us if you would like to access our data in bulk"; robots.txt
  allows ``*`` but disallows named AI crawlers; the AKN document URL answered 403 to the research user agent while
  the listing pages answered 200.  Not official; bulk access by agreement.
* Laws.Africa API, https://api.laws.africa/v2/akn/gh/ (the same AKN data, key required; robots.txt disallows all);
  not official.
* Ghana Publishing Company (the Government Printer, Assembly Press) has no online legislation service.

The adapter to write: Parliament repository first (official): ``fetch_list`` walks the Acts communities through
``/server/api/discover/search/objects?scope=<community>&dsoType=ITEM``, ``fetch_document`` downloads the PDF
bitstream (sizes 0.4-5 MB in the samples) and extracts text, ``parse`` splits by "Section N" headings (Ghanaian
Acts use Part / Section / subsection).  Consolidation would come from GhaLII only with their agreement.
"""
from __future__ import annotations

from .base import Country, Source


class Ghana(Country):
    code = "gh"
    name = "Ghana"
    wikidata = "Q117"
    languages = ("en",)
    code_label = "Acts of the Parliament of Ghana"
    pace = 3.0
    status = "stub"
    note = ("official texts are as-passed PDFs in the Parliament's DSpace repository (text layer often empty); "
            "GhaLII's Akoma Ntoso is consolidated but its terms prohibit scraping and bulk download")
    sources = (
        Source(name="Parliament of Ghana Library Repository", publisher="Parliament of Ghana",
               url="https://repository.parliament.gh/", holds="Acts of Parliament by Republic and Parliament "
               "(communities ACTS-1ST REPUBLIC to 9th and 10th Parliament Acts), executive instruments, Hansard, "
               "committee reports; 1,538 items match 'Act' (19 Oct 2026)", format="PDF (+ extracted .txt bitstream, "
               "often empty)", access="DSpace 7 REST API /server/api (discover, items, bitstreams), OAI-PMH "
               "(standard DSpace /server/oai, not verified), sitemap", identifier="handle 123456789/<n>, item uuid",
               licence="an open access electronic archive for collecting, preserving, and sharing digital materials "
                       "... created, owned and hosted by Parliament of Ghana (home page); per-item DSpace deposit "
                       "license.txt", languages=("en",), verified="2026-10-19",
               automated_reading="API and item pages allowed by robots.txt; no reuse licence stated"),
        Source(name="GhaLII", publisher="Ghana Legal Information Institute (non-profit, with the Judicial Service)",
               url="https://ghalii.org/legislation/", holds="568 legislation documents (Acts, decrees, instruments), "
               "part consolidated, as Akoma Ntoso; judgments; gazettes", format="Akoma Ntoso HTML/XML, PDF",
               access="website; API on request; AKN document URLs answered 403 to the research agent",
               identifier="AKN FRBR URI /akn/gh/act/{year}/{number}/eng@{date}",
               licence="Scraping and bulk downloading from this website is strictly prohibited. ... There are more "
                       "efficient ways of obtaining access to our data in bulk. Please email us if you would like to "
                       "access our data in bulk.", licence_url="https://ghalii.org/terms-of-use/", languages=("en",),
               verified="2026-10-19", automated_reading="prohibited without agreement; robots.txt Content-Signal "
               "search=yes, ai-train=no"),
        Source(name="Laws.Africa API (Ghana)", publisher="Laws.Africa", url="https://api.laws.africa/v2/akn/gh/",
               holds="the GhaLII Akoma Ntoso corpus", format="Akoma Ntoso XML, JSON", access="API with key",
               identifier="AKN FRBR URI", licence="free for non-commercial use (reported; terms page not readable: 404)",
               languages=("en",), verified="2026-10-19", automated_reading="robots.txt disallows all; key required"),
    )
