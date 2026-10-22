"""Romania: Portalul Legislativ (Ministerul Justiției), every act published in the Monitorul Oficial since 1989 with
its full text, through the portal's free SOAP web service.

Read 22 October 2026 (docs/design/global-sources.md §2.4 and "Progress"):

* ``https://legislatie.just.ro/`` still closes every TLS connection from this network before answering (Python
  requests: ``RemoteDisconnected``), so the portal's pages, its terms of use, its robots.txt and its ELI URIs
  (``/eli/...``) remain unread.  Plain HTTP answers: ``http://legislatie.just.ro/robots.txt`` and ``/`` redirect
  (301) to the HTTPS address that fails, but the web service answers over HTTP:
  ``http://legislatie.just.ro/apiws/FreeWebService.svc?wsdl`` (WCF, SOAP 1.1, ``SoapEndPoint`` at
  ``/apiws/FreeWebService.svc/SOAP``) with two operations: ``GetToken()`` -> a token string, and
  ``Search(SearchModel{NumarPagina, RezultatePagina, SearchAn, SearchNumar, SearchText, SearchTitlu}, tokenKey)``
  -> ``Legi{DataVigoare, Emitent, LinkHtml, Numar, Publicatie, Text, TipAct, Titlu}`` with the act's whole text
  inline (``SearchAn`` is accepted but did not filter by year in the tests).  ``LinkHtml`` is the portal page
  ``http://legislatie.just.ro/Public/DetaliiDocument/<id>`` (the portal's document id is the row's ``native_id``).
* The texts are the acts as published (or republished) in the Monitorul Oficial, not the portal's consolidated
  versions ("forma consolidată"), which are separate documents on the portal.
* Licence: the portal's terms could not be read (HTTPS).  Romanian Law 8/1996 on copyright, art. 9 lit. b, excludes
  "textele oficiale de natură politică, legislativă, administrativă, judiciară şi traducerile oficiale ale acestora"
  from copyright protection, and the service is published as the "FreeWebService"; whether the Ministry claims a
  database right, and what reuse its terms allow, is unverified, so only the 50-act sample the operator approved is
  pulled (``sample``), paced at 5 s.
* The Monitorul Oficial (https://monitoruloficial.ro/) is a commercial site; EUR-Lex's national transposition data
  (``https://eur-lex.europa.eu/``, Commission decision 2011/833/EU on reuse) list Romanian measures transposing
  directives with their Monitorul Oficial references, a metadata route, not the texts.

Rows: one per ``Articolul`` (an ``ARTICOL UNIC`` is one row), units ``Cartea`` / ``Titlul`` / ``Capitolul`` /
``Secțiunea`` / ``Subsecțiunea`` / ``Anexa`` as the text names them; path ``Legea nr. 190/2020 / Capitolul I /
Articolul 1``, citation ``Legea nr. 190/2020, art. 1``, ELI ``.../eli/ro/lege/2020/190/art_1/ro@<DataVigoare>``
(the ELI keeps ISO alpha-2 ``ro``; lexflow keys use ``rou``).  The portal's own ELI cannot be verified from here.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import threading
import time
from pathlib import Path

from ... import config
from .base import Country, Document, Node, Source

CODE = "rou"
SOAP = "http://legislatie.just.ro/apiws/FreeWebService.svc/SOAP"
WSDL = "http://legislatie.just.ro/apiws/FreeWebService.svc?wsdl"
PORTAL = "https://legislatie.just.ro/"
RAW = config.RAW_DIR / "countries" / CODE
ATTRIBUTION = ("Text: Portalul Legislativ, Ministerul Justiției (legislatie.just.ro), FreeWebService; the texts of "
               "the acts as published in the Monitorul Oficial al României.")
EDIT_NOTE = ("lexflow split each act into articles and added the heading path for search; the article text is the "
             "service's, with its spacing normalised. Not an official or consolidated text.")
ATTRIBUTION_EN, EDIT_NOTE_EN = ATTRIBUTION, EDIT_NOTE
# the act types as the service writes them -> how a citation names them
KIND = {"LEGE": "Legea", "DECRET": "Decretul", "HOTĂRÂRE": "Hotărârea", "ORDIN": "Ordinul", "DECIZIE": "Decizia",
        "ORDONANȚĂ DE URGENȚĂ": "Ordonanța de urgență", "ORDONANŢĂ DE URGENŢĂ": "Ordonanța de urgență",
        "ORDONANȚĂ": "Ordonanța", "ORDONANŢĂ": "Ordonanța", "REGULAMENT": "Regulamentul", "NORME": "Normele",
        "CONSTITUȚIE": "Constituția", "CONSTITUŢIE": "Constituția"}
ELI_TYPE = {"LEGE": "lege", "DECRET": "decret", "HOTĂRÂRE": "hg", "ORDIN": "ordin", "DECIZIE": "decizie",
            "ORDONANȚĂ DE URGENȚĂ": "oug", "ORDONANŢĂ DE URGENŢĂ": "oug", "ORDONANȚĂ": "og", "ORDONANŢĂ": "og"}
UNITS = [("Cartea", 1, "CA"), ("Titlul", 2, "T"), ("Capitolul", 3, "C"), ("Secțiunea", 4, "S"), ("Secţiunea", 4, "S"),
         ("Subsecțiunea", 5, "SS"), ("Subsecţiunea", 5, "SS"), ("Paragraful", 6, "PG"), ("Anexa", 1, "AX"),
         ("ANEXA", 1, "AX")]
_UNIT = re.compile(r"^(?P<word>" + "|".join(re.escape(w) for w, _, _ in UNITS) + r")\b\s*(?P<rest>.*)$", re.S | re.I)
_ART = re.compile(r"^(?:Articolul|ARTICOLUL|Art\.)\s+(?P<no>\d+(?:\s*\^\s*\d+)?)\s*(?P<rest>.*)$", re.S)
_UNIC = re.compile(r"^(?:ARTICOL UNIC|Articol unic)\b\s*(?P<rest>.*)$", re.S)
_ROMAN_ART = re.compile(r"^(?:Articolul|ARTICOLUL)\s+(?P<rom>[IVXLC]+)\b\s*(?P<rest>.*)$", re.S)
_SEP = re.compile(r"\n[ \t]*\xa0?\+\xa0?[ \t]*\n")
_MONTHS = {m: i for i, m in enumerate("ianuarie februarie martie aprilie mai iunie iulie august septembrie octombrie "
                                      "noiembrie decembrie".split(), 1)}
_LOCK = threading.Lock()
_LAST = [0.0]


class Romania(Country):
    code = CODE
    iso2 = "ro"
    eli_jurisdiction = "ro"
    name = "Romania"
    wikidata = "Q218"
    languages = ("ro",)
    code_label = "Legislația României (Portal Legislativ)"
    pace = 5.0
    status = "prototype"
    raw_name = f"{CODE}/rows"
    note = ("Portal Legislativ: the free SOAP web service answers over HTTP (HTTPS closes the connection); the "
            "portal's terms are unread, so only the approved 50-act sample is pulled")
    sources = (
        Source(name="Portal Legislativ", publisher="Ministerul Justiției",
               url="https://legislatie.just.ro/", holds="acts published in the Monitorul Oficial since 1989 and "
               "older acts in force, as published and consolidated (~240,000 acts reported)",
               format="SOAP XML with the full text inline (FreeWebService); HTML on the portal",
               access="SOAP web service http://legislatie.just.ro/apiws/FreeWebService.svc (GetToken, Search), "
                      "answering over HTTP; the HTTPS site closes every connection from the research network",
               identifier="portal document id (DetaliiDocument/<id>); ELI on the portal (not verifiable from here)",
               licence="terms unread (HTTPS refused); Law 8/1996 art. 9 lit. b: official legislative texts are not "
                       "protected by copyright", languages=("ro",), verified="2026-10-22",
               automated_reading="the web service is published as free; terms unread: sample only"),
        Source(name="Monitorul Oficial", publisher="Regia Autonomă Monitorul Oficial",
               url="https://monitoruloficial.ro/", holds="the official gazette, issue by issue (commercial site)",
               format="PDF (paid), HTML product pages", access="website; robots.txt disallows /docs/ and search",
               identifier="gazette part/number/date", licence="commercial; no open licence", languages=("ro",),
               verified="2026-10-19", automated_reading="not a source for lexflow: paid issues, /docs/ disallowed"),
    )

    # ------------------------------------------------------------------ the service
    def _post(self, action: str, body: str, timeout: int = 180) -> str:
        import requests
        with _LOCK:
            wait = _LAST[0] + self.pace - time.time()
            if wait > 0:
                time.sleep(wait)
            _LAST[0] = time.time()
        env = f'<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>{body}</s:Body></s:Envelope>'
        r = requests.post(SOAP, data=env.encode("utf-8"), timeout=timeout,
                          headers={"User-Agent": config.USER_AGENT, "Content-Type": "text/xml; charset=utf-8",
                                   "SOAPAction": f'"http://tempuri.org/IFreeWebService/{action}"'})
        r.raise_for_status()
        return r.content.decode("utf-8", "replace")

    def token(self) -> str:
        t = self._post("GetToken", '<GetToken xmlns="http://tempuri.org/"/>')
        m = re.search(r"<GetTokenResult>(.*?)</GetTokenResult>", t)
        if not m:
            raise RuntimeError("FreeWebService: no token")
        return m.group(1)

    def search(self, titlu: str = "", numar: str = "", an: str = "", text: str = "", page: int = 0, per: int = 10,
               token: str | None = None) -> tuple[list[dict], str]:
        """One page of the service's search: the acts (with their text) and the raw response."""
        def el(k: str, v: str) -> str:
            return f"<a:{k}>{html.escape(v)}</a:{k}>" if v else f'<a:{k} i:nil="true"/>'
        body = ('<Search xmlns="http://tempuri.org/"><SearchModel xmlns:a="http://schemas.datacontract.org/2004/07/'
                'FreeWebService" xmlns:i="http://www.w3.org/2001/XMLSchema-instance">'
                f"<a:NumarPagina>{int(page)}</a:NumarPagina><a:RezultatePagina>{int(per)}</a:RezultatePagina>"
                f"{el('SearchAn', an)}{el('SearchNumar', numar)}{el('SearchText', text)}{el('SearchTitlu', titlu)}"
                f"</SearchModel><tokenKey>{html.escape(token or self.token())}</tokenKey></Search>")
        raw = self._post("Search", body)
        return [legi(x) for x in re.findall(r"<a:Legi>(.*?)</a:Legi>", raw, re.S)], raw

    def fetch_list(self, limit: int = 20, titlu: str = "LEGE") -> list[dict]:
        tok, out, page = self.token(), [], 0
        while len(out) < limit:
            got, _ = self.search(titlu=titlu, page=page, per=min(10, limit), token=tok)
            if not got:
                break
            out += got
            page += 1
        return out[:limit]

    def fetch_document(self, native_id: str) -> Document:
        raise NotImplementedError(f"{self.name}: the service searches; it has no fetch by document id (use "
                                  "search() and parse() the result)")

    # ------------------------------------------------------------------ parsing
    def parse(self, raw, native_id: str = "", meta: dict | None = None) -> Document:
        """One ``Legi`` record (the dict ``legi`` gives, or its XML) -> a Document split into articles."""
        rec = raw if isinstance(raw, dict) else legi(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        tip = (rec.get("TipAct") or "").strip().upper()
        title = _ws(rec.get("Titlu") or "")
        numar = (rec.get("Numar") or "").strip()
        m = re.search(r"\bnr\.\s*(\d+)\s+din\s+(\d{1,2})\s+(\w+)\s+(\d{4})", title)
        year = m.group(4) if m else (re.search(r"\b(1[89]\d\d|20\d\d)\b", title) or [None, ""])[1]
        if numar in ("", "0") and m:
            numar = m.group(1)
        date_act = None
        if m and m.group(3).lower() in _MONTHS:
            date_act = f"{m.group(4)}-{_MONTHS[m.group(3).lower()]:02d}-{int(m.group(2)):02d}"
        kind = KIND.get(tip, tip.capitalize() or "Act")
        short = f"{kind} nr. {numar}/{year}" if numar and numar != "0" and year else (title.split(" EMITENT")[0]
                                                                                     .strip()[:120] or kind)
        doc_id = native_id or (re.search(r"DetaliiDocument/(\d+)", rec.get("LinkHtml") or "") or [None, ""])[1]
        heading = re.sub(r"\s+EMITENT.*$", "", title, flags=re.S).strip()
        heading = re.sub(r"^\W+", "", heading)
        vig = (rec.get("DataVigoare") or "")[:10] or None
        doc = Document(country=CODE, native_id=doc_id, kind=kind, kind_token=_tok(f"{ELI_TYPE.get(tip, tip[:4])}{numar}"
                                                                                 f"Y{year}") or f"D{doc_id}",
                       number=f"{numar}/{year}" if numar else "", title=heading, short_title=short, language="ro",
                       year=year or "", eli_type=ELI_TYPE.get(tip, _tok(tip).lower()[:10] or "act"),
                       eli_number=numar if numar not in ("", "0") else f"d{doc_id}",
                       url=f"{PORTAL}Public/DetaliiDocument/{doc_id}" if doc_id else PORTAL, status="in_force",
                       version_date=vig, promulgated=date_act, last_amended_year=int(vig[:4]) if vig else None,
                       fetched=dt.date.today().isoformat(), source=self.sources[0].name,
                       licence=self.sources[0].licence,
                       extra={"tip_act": tip, "emitent": rec.get("Emitent"), "publicatie": rec.get("Publicatie"),
                              "link_html": rec.get("LinkHtml"), "titlu": title, "consolidated": False})
        root = _tree(rec.get("Text") or "", short, doc_id)
        doc.root = root if root.children else None         # no text from the service: no rows
        return doc

    def citation(self, doc: Document, path, leaf: Node) -> str:
        """``Legea nr. 190/2020, art. 1``; an article of an annex is ``..., anexa nr. 1, art. 1``."""
        ax = next((n for n in path if n.token.startswith("AX")), None)
        pre = f"{doc.short_title}, {ax.label.lower()}" if ax is not None else doc.short_title
        if leaf.level == "Articol":
            return f"{pre}, art. {leaf.number}" if leaf.number else f"{pre}, articol unic"
        return f"{pre}, {leaf.label.lower()}" if leaf is not ax else pre

    def unit_slug(self, leaf: Node, path=()) -> str:
        ax = next((n for n in path if n.token.startswith("AX")), None)
        pre = f"anexa_{_slug_no(ax.number)}_" if ax is not None else ""
        if leaf.level == "Articol":
            return pre + (f"art_{_slug_no(leaf.number)}" if leaf.number else "art_unic")
        return (pre + _slug_no(leaf.token).lower()) or "text"


def legi(x: str) -> dict:
    """One ``<a:Legi>`` record's fields (the XML-escaped text unescaped)."""
    out = {}
    for k in ("DataVigoare", "Emitent", "LinkHtml", "Numar", "Publicatie", "Text", "TipAct", "Titlu"):
        m = re.search(rf"<a:{k}>(.*?)</a:{k}>", x, re.S)
        out[k] = html.unescape(m.group(1)) if m else ""
    return out


def _tree(text: str, title: str, doc_id: str) -> Node:
    """The service's text -> units and articles: the blocks are separated by lines holding only ``+``; a block
    starts with its unit word (``Capitolul I   Dispoziții generale``, ``Articolul 1``)."""
    root = Node(level="Act", label=title, heading=title, native_id=doc_id)
    stack: list[tuple[int, Node]] = []
    amending: Node | None = None                 # the amending law's own article (unic, or I, II ...)
    blocks = _SEP.split(text.replace("\r", ""))
    for b in blocks[1:]:                         # the first block is the header: title, issuer, gazette, preamble
        s = b.strip(" \t\n\xa0")
        if not s:
            continue
        m = _ART.match(s)
        u = _UNIC.match(s)
        r = _ROMAN_ART.match(s)
        if (m or (_UNIT.match(s) and not _ROMAN_ART.match(s))) and amending is not None and not r:
            # an article or unit quoted by an amending article ("Articolul 17 ... va avea următorul cuprins"):
            # the text of the amendment, not an article of this law
            amending.text = (amending.text + "\n" + _body(s)).strip()
            continue
        if m or u or r:
            no = re.sub(r"\s+", "", m.group("no")) if m else (r.group("rom") if r else "")
            body = (m or u or r).group("rest")
            leaf = Node(level="Articol", label=f"Articolul {no}" if no else "Articol unic", number=no,
                        text=_body(body), token=f"A{_tok(no)}" if no else "AU", native_id=f"art{no}" if no else "unic")
            (stack[-1][1] if stack else root).children.append(leaf)
            if u or r:
                amending = leaf
            continue
        um = _UNIT.match(s)
        if um:
            word = um.group("word")
            depth, tok = next((d, t) for w, d, t in UNITS if w.lower() == word.lower())
            rest = _ws(um.group("rest"))
            nm = re.match(r"^((?:a\s+)?[IVXLCDM]+|(?:a\s+)?\d+(?:-a)?|nr\.\s*\d+|[A-Z])\b\s*(.*)$", rest)
            number, heading = (nm.group(1), nm.group(2)) if nm else ("", rest)
            unit = Node(level=word.capitalize(), label=f"{word.capitalize()} {number}".strip(), number=number,
                        heading=heading[:300], token=f"{tok}{_tok(number)}")
            while stack and stack[-1][0] >= depth:
                stack.pop()
            (stack[-1][1] if stack else root).children.append(unit)
            stack.append((depth, unit))
            if tok == "AX":                              # an annex is text unless it has articles
                unit.text = _body(um.group("rest"))
            continue
        # text that follows a unit without a heading of its own (a note, the signatures): kept on the unit
        target = stack[-1][1] if stack else None
        if target is not None and not target.children:
            target.text = (target.text + "\n" + _body(s)).strip()
    _prune(root)
    return root


def _prune(n: Node) -> None:
    for c in n.children:
        _prune(c)
    n.children = [c for c in n.children if c.children or c.text]
    for c in n.children:                                  # a unit with articles keeps no text of its own
        if c.children and c.level != "Articol":
            c.text = ""


def _body(s: str) -> str:
    """An article's text: one line per alineat ``(1)`` and literă ``a)``, the service's ``...`` separators as line
    breaks, other spacing collapsed."""
    s = (s or "").replace("\xa0...\xa0", "\n").replace("\r", "")
    s = re.sub(r"[ \t\xa0]{2,}(\(\d+(?:\^\d+)?\))[ \t\xa0]+", r"\n\1 ", s)
    s = re.sub(r"[ \t\xa0]{2,}([a-z](?:\^\d+)?\))[ \t\xa0]+", r"\n\1 ", s)
    lines = [_ws(x) for x in s.split("\n")]
    return "\n".join(x for x in lines if x and x != "...")


def _ws(s: str) -> str:
    return re.sub(r"[\s\xa0﻿]+", " ", s or "").strip()


def _tok(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "", s).upper()


def _slug_no(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()


# ---------------------------------------------------------------------- the approved sample
def sample(n: int = 50, titlu: str = "LEGE", an: str = "", raw: Path = RAW, log=print) -> dict:
    """``n`` distinct acts whose title matches ``titlu`` (and ``an``, which the service weighs rather than
    filters), one rows file per act in ``rows/``, the service's responses in ``src/``: the 50-act sample the
    operator approved.  Pages are numbered from 1 (pages 0 and 1 are the same page)."""
    a = Romania()
    for d in ("rows", "src"):
        (raw / d).mkdir(parents=True, exist_ok=True)
    tok = a.token()
    got, page, acts, total_rows, seen = 0, 1, [], 0, set()
    while got < n and page < 50:
        recs, body = a.search(titlu=titlu, an=an, page=page, per=10, token=tok)
        (raw / "src" / f"search_{_slug_no(titlu)}_{an or 'all'}_{page}.xml").write_text(body, encoding="utf-8")
        if not recs:
            break
        for rec in recs:
            if got >= n:
                break
            doc = a.parse(rec)
            if doc.native_id in seen:
                continue
            seen.add(doc.native_id)
            rows = a.to_rows(doc)
            with open(raw / "rows" / f"{doc.native_id}.jsonl", "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps({**r, "fetched": doc.fetched}, ensure_ascii=False) + "\n")
            acts.append({"native_id": doc.native_id, "title": doc.short_title, "tip": doc.extra["tip_act"],
                         "rows": len(rows), "chars": len(rec.get("Text") or ""), "vigoare": doc.version_date})
            total_rows += len(rows)
            got += 1
        log(f"page {page}: {got} acts, {total_rows} rows")
        page += 1
    m = {"source": "Portal Legislativ FreeWebService", "endpoint": SOAP, "fetched": dt.date.today().isoformat(),
         "acts": len(acts), "rows": total_rows, "query": {"SearchTitlu": titlu, "SearchAn": an}, "list": acts,
         "attribution": ATTRIBUTION, "edit_note": EDIT_NOTE, "pace_seconds": a.pace,
         "note": "sample only: the portal's terms could not be read (HTTPS refused)"}
    tmp = raw / "MANIFEST.json.part"
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, raw / "MANIFEST.json")
    return {k: v for k, v in m.items() if k != "list"}


def main(argv: list[str] | None = None) -> int:
    """``python -m lexflow.corpus.countries.romania sample [--n 50] [--titlu LEGE]``"""
    import argparse
    ap = argparse.ArgumentParser(prog="lexflow.corpus.countries.romania")
    ap.add_argument("action", choices=["sample"])
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--titlu", default="LEGE")
    ap.add_argument("--an", default="")
    o = ap.parse_args(argv)
    print(json.dumps(sample(o.n, o.titlu, o.an, log=lambda s: print(time.strftime("%H:%M:%S ") + s, flush=True)),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
