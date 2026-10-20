"""Australia: the Federal Register of Legislation (Office of Parliamentary Counsel) and the eight state and
territory registers.  Stub: the sources are verified, the adapter is not written (docs/design/global-sources.md §2.3).

Verified 19 October 2026:

* Federal Register of Legislation, https://www.legislation.gov.au/: every Commonwealth Act, legislative and
  notifiable instrument and gazette, as made and as compiled (point in time), 132,603 titles (``/v1/titles/$count``),
  4,774 Acts in force (principal and amending).  OData v4 API at ``https://api.prod.legislation.gov.au/v1/``
  (``Titles``, ``Versions``, ``Documents``, ``Affect``, full-text search entity sets; ``$metadata`` served) and the
  compiled text as HTML per version (``/{titleId}/{start}/{start}/text/original/epub/OEBPS/document_1/document_1.html``),
  with PDF, DOCX and ePub downloads.  Identifier: the register id (``C1901A00002``; compilations ``C2026C00117``);
  no ELI.  robots.txt: ``Crawl-delay: 10``.  Licence (terms of use): "all content on the Federal Register of
  Legislation ... is provided under Creative Commons Attribution 4.0 International (the CC BY 4.0 licence)" with the
  attribution "Sourced from the Federal Register of Legislation at [full date of download]. For the latest
  information on Australian Government law please go to https://www.legislation.gov.au."
* States and territories (the first subnational layer): Queensland (CC BY 4.0; API with registration at
  https://api.legislation.qld.gov.au/, XML per document), Western Australia (CC BY 4.0), Tasmania (CC BY 4.0),
  South Australia (CC BY 4.0 fortnightly XML packages on data.sa.gov.au, CKAN), Northern Territory (its own
  copyright policy permitting publication with conditions), Victoria (copyright of the Government Printer,
  "authorised electronic versions ... for personal use only"), ACT (JACS copyright policy, all rights reserved on
  the register), New South Wales (HTTP 403 to every automated request: unverified).

The adapter to write: ``fetch_list`` pages ``Titles`` with ``$filter=isInForce eq true and collection eq 'Act'``,
``fetch_document`` reads the latest ``Version`` and its HTML, ``parse`` splits the compiled HTML by its Chapter /
Part / Division / Subdivision / section headings (the OPC style classes), one row per section.
"""
from __future__ import annotations

from .base import Country, Source


class Australia(Country):
    code = "au"
    name = "Australia"
    wikidata = "Q408"
    languages = ("en",)
    code_label = "Commonwealth Acts (Federal Register of Legislation)"
    pace = 10.0                     # robots.txt Crawl-delay
    status = "stub"
    note = ("Federal Register of Legislation OData API verified (CC BY 4.0); the HTML-splitting parser for compiled "
            "Acts is not written; state registers are listed in docs/design/global-sources.md §2.3")
    sources = (
        Source(name="Federal Register of Legislation", publisher="Office of Parliamentary Counsel (Commonwealth)",
               url="https://www.legislation.gov.au/",
               holds="Commonwealth Acts, legislative and notifiable instruments, gazettes; as made and compiled "
                     "point-in-time versions; 132,603 titles, 4,774 Acts in force (19 Oct 2026)",
               format="HTML (from ePub), PDF, DOCX, ePub per version; JSON (OData) metadata",
               access="OData v4 API https://api.prod.legislation.gov.au/v1/ (Titles, Versions, Documents, Affect, "
                      "full-text search), sitemap; no bulk export",
               identifier="register id C1901A00002 (title), C2026C00117 (compilation); no ELI",
               licence="With the exception of the Commonwealth Coat of Arms, and where otherwise noted, all content "
                       "on the Federal Register of Legislation (the Legislation Register) is provided under Creative "
                       "Commons Attribution 4.0 International (the CC BY 4.0 licence).",
               licence_url="https://www.legislation.gov.au/terms-of-use", languages=("en",), verified="2026-10-19",
               automated_reading="allowed (CC BY 4.0, attribution wording prescribed); robots.txt Crawl-delay 10"),
        Source(name="Queensland Legislation", publisher="Office of the Queensland Parliamentary Counsel",
               url="https://www.legislation.qld.gov.au/", holds="Queensland Acts and subordinate legislation in force, "
               "as passed/made, repealed; reprints", format="XML, HTML, PDF", access="API with registration "
               "(https://api.legislation.qld.gov.au/, Swagger), /view/whole/xml per document",
               identifier="OQPC document id", licence="Unless otherwise noted, all copyright material available on "
               "or through this website is licensed under a Creative Commons Attribution 4.0 International licence "
               "(CC BY 4.0).", licence_url="https://www.legislation.qld.gov.au/copyright", languages=("en",),
               verified="2026-10-19", automated_reading="allowed with attribution; API needs an account"),
        Source(name="Western Australian Legislation", publisher="Parliamentary Counsel's Office (WA)",
               url="https://www.legislation.wa.gov.au/", holds="WA Acts and subsidiary legislation, in force and ceased",
               format="HTML, PDF, DOCX", access="website (Lotus Notes .nsf views); no API found",
               identifier="statutes.nsf document ids", licence="the State of Western Australia's copyright material "
               "available on this website (Licensed Material) is licensed under a Creative Commons Attribution 4.0 "
               "International Licence (CC BY 4.0).",
               licence_url="https://www.legislation.wa.gov.au/legislation/statutes.nsf/copyright.html",
               languages=("en",), verified="2026-10-19", automated_reading="allowed with attribution; no robots.txt"),
        Source(name="South Australian Legislation (DataSA XML packages)", publisher="Attorney-General's Department (SA)",
               url="https://data.sa.gov.au/data/dataset/database-update-package-xml",
               holds="SA Acts and regulations as XML, fortnightly update packages (236 resources on 8 Oct 2026)",
               format="XML (zip)", access="CKAN API (package_show) and direct download", identifier="SA legislation id",
               licence="license_id cc-by: Creative Commons Attribution 4.0 (CKAN metadata)",
               licence_url="http://creativecommons.org/licenses/by/4.0", languages=("en",), verified="2026-10-19",
               automated_reading="allowed (CC BY 4.0); the legislation site itself returns 403 to robots.txt"),
        Source(name="Tasmanian Legislation Online", publisher="Office of Parliamentary Counsel (Tasmania)",
               url="https://www.legislation.tas.gov.au/", holds="Tasmanian Acts and statutory rules in force, as made, "
               "repealed", format="HTML, PDF", access="website, sitemap and crawler feed (/feed?id=crawler)",
               identifier="Tasmanian legislation id", licence="Unless otherwise noted, all material provided on this "
               "website is licensed under a Creative Commons Attribution 4.0 International licence (CC BY 4.0).",
               licence_url="https://www.legislation.tas.gov.au/copyrightanddisclaimer", languages=("en",),
               verified="2026-10-19", automated_reading="allowed with attribution"),
        Source(name="Northern Territory Legislation", publisher="Office of the Parliamentary Counsel (NT)",
               url="https://legislation.nt.gov.au/", holds="NT Acts and subordinate legislation, reprints, gazettes",
               format="HTML, PDF, DOCX", access="website; no API found", identifier="NT legislation id",
               licence="The Northern Territory grants permission to any person to publish or deal with any legislation "
                       "of the Northern Territory in accordance with the following conditions (copyright policy of "
                       "8 October 1996)", licence_url="https://legislation.nt.gov.au/en/Footer/Terms-of-Use",
               languages=("en",), verified="2026-10-19", automated_reading="permitted under the policy's conditions "
               "(read the conditions before a full pull)"),
        Source(name="Victorian Legislation", publisher="Office of the Chief Parliamentary Counsel (Victoria)",
               url="https://www.legislation.vic.gov.au/", holds="Victorian Acts and statutory rules in force, as made, "
               "historical (1851-1995)", format="HTML, PDF, DOCX", access="website (Drupal); robots.txt Crawl-delay 2",
               identifier="Victorian legislation id", licence="The information on this website is copyright. No part "
               "may be reproduced by any process except in accordance with the provisions of the Copyright Act 1968 "
               "of the Commonwealth. ... Authorised electronic versions are published on this website ... for "
               "personal use only.", licence_url="https://www.legislation.vic.gov.au/copyright", languages=("en",),
               verified="2026-10-19", automated_reading="not granted: permission needed from the OCPC"),
        Source(name="ACT Legislation Register", publisher="Parliamentary Counsel's Office (ACT)",
               url="https://www.legislation.act.gov.au/", holds="ACT Acts, subordinate laws, instruments, gazettes",
               format="HTML, PDF, DOCX", access="website; robots.txt Crawl-delay 10, /View/ and /html/ disallowed",
               identifier="ACT legislation id (A2001-14)", licence="Use of material on the ACT Legislation Register "
               "should be in accordance with the JACS Copyright Policy ... Copyright 2001 ACT Government. All rights "
               "reserved.", licence_url="https://www.legislation.act.gov.au/Static/Footerlinks/Copyright/copyright.html",
               languages=("en",), verified="2026-10-19", automated_reading="document views disallowed by robots.txt; "
               "policy to be read before any pull"),
        Source(name="NSW Legislation", publisher="Parliamentary Counsel's Office (NSW)",
               url="https://legislation.nsw.gov.au/", holds="NSW Acts and statutory instruments (not verified)",
               format="HTML, XML, PDF (reported)", access="none: HTTP 403 to every automated request, robots.txt included",
               identifier="NSW legislation id", licence="not readable (403)", languages=("en",), verified="2026-10-19",
               automated_reading="blocked at the edge; ask the PCO for access"),
    )
