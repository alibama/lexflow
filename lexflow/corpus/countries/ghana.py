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

Re-checked 22 October 2026: the repository runs DSpace 9.1 (``/server/api``), robots.txt still allows the API and
item pages, 1,538 items match "Act".  Its End User Agreement (``/info/end-user-agreement``, "Last updated May 4,
2023") grants "a limited license to access and use the Site and to download or print a copy of any portion of the
Content ... solely for your personal, non-commercial use" and lists among prohibited activities: "Systematically
retrieve data or other content from the Site to create or compile, directly or indirectly, a collection,
compilation, database, or directory without written permission from us."  So an index of the Acts needs the
Parliament's written permission; no pull, no OCR pipeline.  Text layers, five Acts sampled through the API
(Appropriation Acts 2019 and 2021; Chartered Institute of Restructuring and Insolvency Practitioners, Ghana Act,
2024; Rent Control Act, 1986 PNDCL 138 (Revised Edition); Driver and Vehicle Licensing Authority Act, 1999 (Act
569)): three have a text layer (Word-born or OCRed: 18-107k characters), two are image-only scans (the 2021
Appropriation Act, 22 pages, and PNDCL 138, 10 pages from a RICOH scanner), and the DSpace ``.pdf.txt`` text
bitstream is empty for those two.  About two in five would need OCR.
"""
from __future__ import annotations

from .base import Country, Source


class Ghana(Country):
    code = "gha"
    iso2 = "gh"
    eli_jurisdiction = "gh"
    name = "Ghana"
    wikidata = "Q117"
    languages = ("en",)
    code_label = "Acts of the Parliament of Ghana"
    pace = 3.0
    status = "stub"
    note = ("official texts are as-passed PDFs in the Parliament's DSpace repository, whose End User Agreement forbids "
            "systematic retrieval to compile a database without written permission (2 of 5 sampled PDFs are image-only "
            "scans); GhaLII's Akoma Ntoso is consolidated but its terms prohibit scraping: ask either for permission")
    sources = (
        Source(name="Parliament of Ghana Library Repository", publisher="Parliament of Ghana",
               url="https://repository.parliament.gh/", holds="Acts of Parliament by Republic and Parliament "
               "(communities ACTS-1ST REPUBLIC to 9th and 10th Parliament Acts), executive instruments, Hansard, "
               "committee reports; 1,538 items match 'Act' (19 Oct 2026)", format="PDF (+ extracted .txt bitstream, "
               "often empty)", access="DSpace 7 REST API /server/api (discover, items, bitstreams), OAI-PMH "
               "(standard DSpace /server/oai, not verified), sitemap", identifier="handle 123456789/<n>, item uuid",
               licence="an open access electronic archive for collecting, preserving, and sharing digital materials "
                       "... created, owned and hosted by Parliament of Ghana (home page); per-item DSpace deposit "
                       "license.txt; End User Agreement (May 2023): \"limited license ... solely for your personal, "
                       "non-commercial use\"", licence_url="https://repository.parliament.gh/info/end-user-agreement",
               languages=("en",), verified="2026-10-22",
               automated_reading="robots.txt allows the API; the End User Agreement forbids systematic retrieval to "
                                 "compile a database without written permission (read 22 Oct 2026)"),
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
