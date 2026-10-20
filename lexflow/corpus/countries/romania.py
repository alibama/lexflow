"""Romania: Portalul Legislativ (Ministerul Justiției), the national legislation database with native ELI.  Stub
(docs/design/global-sources.md §2.4).

Known and partly verified, 19 October 2026:

* https://legislatie.just.ro/ publishes every act in the Monitorul Oficial since 1989 (and older acts in force)
  with consolidated versions, and mints ELIs natively (``https://legislatie.just.ro/eli/{tip}/{an}/{numar}``; Romania
  is in the EU ELI register).  Legal Data Hunter's pointer records a SOAP web service (``FreeWebService``) with
  full text inline and ~240,000 acts.
* Not verified here: the host closed every TLS connection from the research network before responding (Python,
  curl/Schannel, TLS 1.2 forced, and the desktop browser pane), and EUR-Lex's ELI register pages answered with an
  empty 202 (bot challenge).  Terms, format, quota and the robots.txt are therefore unread: read them from the site
  before any pull, from a network the portal accepts.
* Monitorul Oficial (https://monitoruloficial.ro/) is the gazette, a commercial WordPress/WooCommerce site with
  product pages per issue; not a legislation database.

The adapter to write, once the portal is readable: ``fetch_list`` from the web service's search, ``fetch_document``
by the act's unique id (full text inline), ``parse`` the act's Titlu / Capitol / Secțiune / Articol / Alineat
structure, rows per Articol with the portal's own ELI in ``eli``.
"""
from __future__ import annotations

from .base import Country, Source


class Romania(Country):
    code = "ro"
    name = "Romania"
    wikidata = "Q218"
    languages = ("ro",)
    code_label = "Legislația României (Portal Legislativ)"
    pace = 5.0
    status = "stub"
    note = ("legislatie.just.ro refused every connection from the research network (TLS closed before response), so "
            "format, terms and robots.txt are unverified; the portal mints ELIs natively")
    sources = (
        Source(name="Portal Legislativ", publisher="Ministerul Justiției",
               url="https://legislatie.just.ro/", holds="acts published in the Monitorul Oficial since 1989 and "
               "older acts in force, consolidated versions (~240,000 acts reported)", format="HTML (SOAP XML with "
               "full text inline, reported)", access="SOAP web service FreeWebService (reported); ELI URIs; not "
               "reachable from the research network", identifier="ELI https://legislatie.just.ro/eli/{tip}/{an}/{numar}; "
               "portal document id", licence="not readable (connection refused)", languages=("ro",),
               verified="2026-10-19 (unreachable)", automated_reading="unknown; read the portal's terms first"),
        Source(name="Monitorul Oficial", publisher="Regia Autonomă Monitorul Oficial",
               url="https://monitoruloficial.ro/", holds="the official gazette, issue by issue (commercial site)",
               format="PDF (paid), HTML product pages", access="website; robots.txt disallows /docs/ and search",
               identifier="gazette part/number/date", licence="commercial; no open licence", languages=("ro",),
               verified="2026-10-19", automated_reading="not a source for lexflow: paid issues, /docs/ disallowed"),
    )
