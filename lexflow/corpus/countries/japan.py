"""Japan: e-Gov 法令検索 (Digital Agency), every national law and regulation as 法令標準XML, in bulk and by API.

Verified 19 and 22 October 2026 (docs/design/global-sources.md §2.6):

* ``https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true`` is the official bulk export of every
  law in force ("すべての法令データ", 283 MB announced; ``all_xml.zip``, 297,489,146 bytes on 22 Oct 2026): one
  folder per revision ``<law_id>_<enforcement YYYYMMDD>_<amending law_id>/`` holding that revision's XML, plus
  ``all_law_list.csv`` (one row per revision; ``未施行`` marks the revisions not yet in force).  The server sends no
  Content-Length and ignores HTTP Range (it answers 200 with the whole body), so a broken download restarts.
* ``https://laws.e-gov.go.jp/api/2/laws?limit=&offset=&response_format=json`` lists the laws (9,567 on 19 and 22
  Oct 2026) with ``law_info`` (law_id, law_num, law_type, promulgation_date) and ``revision_info`` (title, kana,
  abbreviation, category, amendment promulgation / enforcement dates, repeal status); ``/law_data/{law_id}`` returns
  one law as a JSON tag tree, the same tree the XML gives (``Law > LawBody > MainProvision > Part / Chapter /
  Section / Subsection / Division > Article > Paragraph > Item ...``, plus ``SupplProvision``).  OpenAPI 2.1.139 at
  ``/api/2/swagger-ui/lawapi-v2.yaml``.  No key, no documented quota; lexflow reads it at most once a second.
* Licence: the site's 利用規約 ("本サイトの著作権は、特記されていない限りデジタル庁に帰属し、権利表記の記載がない限り
  「公共データ利用規約（第1.0版）」（PDL1.0）が適用されています") and PDL1.0 itself ("どなたでも ... 複製、公衆送信、翻訳・
  変形等の翻案等、自由に利用できます ... 商用利用も可能です"; 1.1: 出典 must be stated, and an edited work must say that it
  was edited and by whom, and must not be presented as if the government made it).  PDL1.0 is CC BY 4.0 compatible.
  ``ATTRIBUTION`` and ``EDIT_NOTE`` are the statements lexflow makes; ``LICENSE-NOTICE.txt`` beside the download and
  the Japan entry of lexflow/pipeline/credits.py carry them.
* Translations: 日本法令外国語訳データベースシステム (Ministry of Justice) publishes unofficial English translations
  under PDL1.0; "Only the original Japanese texts of the laws and regulations have legal effect".

Rows: one per 条 (Article); transitory and amending provisions under 附則 (SupplProvision), each 附則 a unit whose
articles are rows (a 附則 without articles is one row); a law whose main provision has no articles (元号法) becomes
one row for 本則.  Path ``行政手続法 / 第一章　総則 / 第一条``, citation ``行政手続法第一条``, act_id
``STATE_JPN_405AC0000000088_C1_A1``, ELI ``.../eli/jp/act/1993/88/art_1/ja@<enforcement>`` (the ELI keeps ISO
alpha-2 ``jp``, as ELI jurisdictions are written; lexflow's own keys use ``jpn``), source URL the law's e-Gov page
with the article's anchor (``https://laws.e-gov.go.jp/law/405AC0000000088#Mp-Ch_3-Se_1-At_13``).  Text keeps the
paragraph numbers (１、２) and item titles (一、二) as the source gives them, one paragraph per line, so verbatim
quotes can be checked against the source.  Appended tables (別表), forms and the preamble are not rows yet.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import time
from pathlib import Path
from typing import Callable, Iterator

from ... import config
from .base import Country, Document, Node, Source

API = "https://laws.e-gov.go.jp/api/2"
PAGE_URL = "https://laws.e-gov.go.jp/law/{id}"
BULK_URL = "https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true"
BULK_PAGE = "https://laws.e-gov.go.jp/bulkdownload/"
TERMS_URL = "https://laws.e-gov.go.jp/terms/"
PDL_URL = "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0"
RESEARCH_UA = "lexflow-research/0.1 (https://github.com/alibama/lexflow)"
CODE = "jpn"
RAW = config.RAW_DIR / "countries" / CODE
ZIP_NAME = "all_xml.zip"
LAWS_NAME = "laws.jsonl"                    # the API v2 law list, one law per line
MANIFEST_NAME = "MANIFEST.json"
NOTICE_NAME = "LICENSE-NOTICE.txt"

# PDL1.0 §1.1 and the e-Gov site's own 出典記載例 ("出典：e-Govポータル（https://www.e-gov.go.jp）"); the edit note says
# that lexflow edited the data and that the edited form is not the Digital Agency's
ATTRIBUTION = ("出典：e-Gov法令検索（https://laws.e-gov.go.jp/）「XML一括ダウンロード」（法令標準XML）及び法令API Version 2、"
               "公共データ利用規約（第1.0版）（PDL1.0）（" + PDL_URL + "）")
EDIT_NOTE = ("e-Gov法令検索（https://laws.e-gov.go.jp/）の法令データをもとに lexflow が作成（条ごとに分割し、見出し・階層・"
             "施行日を付して索引化。条文の本文は原文のまま）。lexflow の索引及び構造化データはデジタル庁が作成したものではありません。")
ATTRIBUTION_EN = ("Source: e-Gov Law Search (https://laws.e-gov.go.jp/), Digital Agency, Government of Japan: the bulk "
                  "XML download and Law API v2, under the Public Data License (Version 1.0) (PDL1.0, " + PDL_URL + ")")
EDIT_NOTE_EN = ("Edited by lexflow: split into articles, with headings, hierarchy and enforcement dates added for "
                "search; the article text is unchanged. lexflow's index and structured data are not made by the "
                "Digital Agency.")

LEVELS = {"Part": ("編", "PT"), "Chapter": ("章", "C"), "Section": ("節", "S"), "Subsection": ("款", "SS"),
          "Division": ("目", "D"), "Article": ("条", "A"), "SupplProvision": ("附則", "SP")}
ANCHOR = {"Part": "Pa", "Chapter": "Ch", "Section": "Se", "Subsection": "Ss", "Division": "Di", "Article": "At"}
TITLE_TAGS = {"PartTitle", "ChapterTitle", "SectionTitle", "SubsectionTitle", "DivisionTitle"}
SKIP = {"TOC", "LawTitle", "LawNum", "EnactStatement", "Preamble", "AppdxTable", "AppdxNote", "AppdxStyle", "Appdx",
        "AppdxFig", "AppdxFormat", "SupplProvisionAppdxTable", "SupplProvisionAppdx", "SupplProvisionAppdxStyle"}
LAW_TYPES = {"Constitution": "憲法", "Act": "法律", "CabinetOrder": "政令", "ImperialOrder": "勅令",
             "MinisterialOrdinance": "府省令", "Rule": "規則", "Misc": "その他"}
LAW_TYPE_EN = {"Constitution": "Constitution", "Act": "Act", "CabinetOrder": "Cabinet Order",
               "ImperialOrder": "Imperial Ordinance", "MinisterialOrdinance": "Ministerial Ordinance", "Rule": "Rule",
               "Misc": "Other"}
LAW_TYPE_OF = {v: k for k, v in LAW_TYPES.items()}
ERA = {"Meiji": 1867, "Taisho": 1911, "Showa": 1925, "Heisei": 1988, "Reiwa": 2018}
# the law_id's type letters whose natural numbers are unique within a year (Acts, Cabinet and Imperial Orders, the
# Dajōkan proclamations); a ministerial ordinance's or a rule's number is unique only per issuer, so its ELI natural
# number is the law_id itself (127 collisions in the 22 Oct 2026 zip otherwise)
NUMBERED = {"AC", "CO", "IO", "DF", "DT", "CONSTITUTION"}
_WS = re.compile(r"[ \t\r\n]*")             # XML indentation (never the ideographic space U+3000, which is text)
Log = Callable[[str], None]


class Japan(Country):
    code = CODE
    iso2 = "jp"
    eli_jurisdiction = "jp"
    name = "Japan"
    wikidata = "Q17"
    languages = ("ja",)
    code_label = "日本の法令 (e-Gov法令検索)"
    code_labels = {"ja": "日本の法令", "en": "Laws of Japan"}
    website = "https://laws.e-gov.go.jp/"
    pace = 1.0
    status = "prototype"
    sources = (
        Source(name="e-Gov 法令検索 法令API v2", publisher="デジタル庁 (Digital Agency, Government of Japan)",
               url="https://laws.e-gov.go.jp/",
               holds="the Constitution, Acts, Cabinet Orders, Imperial Orders, ministerial ordinances and rules in "
                     "force, consolidated, with revision history (9,567 laws listed on 19 Oct 2026; 8,981 laws in "
                     "the bulk XML of 22 Oct 2026)",
               format="法令標準XML and JSON tag tree (Law > MainProvision > Chapter > Article > Paragraph > Item)",
               access="REST API without key (/api/2/laws, /law_data, /law_file, /keyword); official bulk XML "
                      "(all_xml.zip) at /bulkdownload; OpenAPI 2.1.139 at /api/2/swagger-ui/lawapi-v2.yaml",
               identifier="law_id (e.g. 405AC0000000088: era-year, type, number), law_num (平成五年法律第八十八号), "
                          "law_revision_id; no ELI",
               licence="本サイトの著作権は、特記されていない限りデジタル庁に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」"
                       "（PDL1.0）が適用されています。 PDL1.0: どなたでも ... 複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます ... "
                       "商用利用も可能です。",
               licence_url=PDL_URL,
               languages=("ja",), verified="2026-10-22",
               automated_reading="allowed: the API and the bulk XML are the published machine access; PDL1.0 asks "
                                 "for a 出典 (source) statement and a note when the content is edited"),
        Source(name="Japanese Law Translation Database System", publisher="法務省 (Ministry of Justice)",
               url="https://www.japaneselawtranslation.go.jp/",
               holds="unofficial English translations of selected laws (bilingual, with the Standard Legal Terms "
                     "Dictionary); outlines of new acts", format="HTML, XML/PDF/DOCX downloads per law",
               access="website; API documented in the user guide (not verified here)",
               identifier="the law's e-Gov law_num; JLT law id", licence="Information published on this site ... is "
               "subject to the \"Public Data License (Version 1.0)\" (PDL1.0) unless stated otherwise. ... The "
               "translations ... are not official texts ... Only the original Japanese texts of the laws and "
               "regulations have legal effect",
               licence_url="https://www.japaneselawtranslation.go.jp/en/index/terms", languages=("en", "ja"),
               verified="2026-10-19", automated_reading="PDL1.0 (reuse allowed with attribution); the site asks "
                                                        "that translations be used as reference material only"),
    )

    # ------------------------------------------------------------------ the API (one law, the law list)
    def fetch_list(self, limit: int = 20, law_type: str = "Act", offset: int = 0) -> list[dict]:
        r = self.get(f"{API}/laws?limit={int(limit)}&offset={int(offset)}&law_type={law_type}&response_format=json",
                     accept="application/json", ua=RESEARCH_UA)
        return [law_entry(law) for law in r.json().get("laws", [])]

    def fetch_document(self, native_id: str) -> Document:
        r = self.get(f"{API}/law_data/{native_id}?response_format=json", accept="application/json", ua=RESEARCH_UA)
        return self.parse(r.content, native_id)

    # ------------------------------------------------------------------ parsing
    def parse(self, raw: bytes | str | dict, native_id: str = "") -> Document:
        """One law from the API's JSON (``law_info``, ``revision_info``, ``law_full_text``), or the same shape
        built from the bulk XML by ``parse_xml``."""
        data = raw if isinstance(raw, dict) else json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        info, rev, tree = data.get("law_info", {}), data.get("revision_info", {}), data.get("law_full_text", {})
        law_id = info.get("law_id") or native_id
        law_type = info.get("law_type", "Act")
        enforcement = rev.get("amendment_enforcement_date")
        year = (info.get("promulgation_date") or "")[:4]
        number = str(info.get("law_num_num") or "").lstrip("0") or "0"
        if _type_letters(law_id) not in NUMBERED:
            number = law_id                         # unique where the bare number is not (see NUMBERED)
        title = rev.get("law_title") or ""
        status = rev.get("current_revision_status", "")
        doc = Document(country=self.code, native_id=law_id, kind=LAW_TYPES.get(law_type, law_type), kind_token=law_id,
                       number=info.get("law_num") or "", title=title, short_title=rev.get("abbrev") or "",
                       language="ja", year=year, eli_type=law_type.lower(), eli_number=number,
                       url=PAGE_URL.format(id=law_id),
                       status={"CurrentEnforced": "in_force", "Repeal": "repealed", "UnEnforced": "not_yet_in_force",
                               "PreviousEnforced": "not_yet_in_force"}.get(status, "in_force"),
                       version_date=enforcement, promulgated=info.get("promulgation_date"),
                       last_amended_year=int(enforcement[:4]) if enforcement else None,
                       fetched=data.get("fetched") or self.today(),
                       source=self.sources[0].name, licence=self.sources[0].licence,
                       extra={"law_revision_id": rev.get("law_revision_id"), "law_title_kana": rev.get("law_title_kana"),
                              "category": rev.get("category"), "updated": rev.get("updated"),
                              "abbrev": rev.get("abbrev"), "law_type": law_type,
                              "amendment_law_num": rev.get("amendment_law_num"),
                              "api_url": f"{API}/law_data/{law_id}?response_format=json"})
        doc.short_title = ""                        # cite by the full title, as Japanese practice does
        doc.root = Node(level=doc.kind, label=title, number=doc.number, heading=title, native_id=law_id)
        body = _child(tree, "LawBody") or {}
        main = _child(body, "MainProvision")
        if main is not None:
            kids = self._nodes(main, "", "Mp", doc.url)
            if kids:
                doc.root.children.extend(kids)
            else:                                   # a law with paragraphs only (元号法): one leaf for the main provision
                doc.root.children.append(Node(level="本則", label="本則", number="", text=_text(main), token="MAIN"))
        for i, sp in enumerate(_children(body, "SupplProvision"), 1):
            label = re.sub(r"\s+", "", _plain(_child(sp, "SupplProvisionLabel"))) or "附則"
            amend = (sp.get("attr") or {}).get("AmendLawNum", "")
            n = Node(level="附則", label=f"{label}（{amend}）" if amend else label, number=str(i), heading=amend,
                     token=f"SP{i}", effective_from=enforcement)
            n.children.extend(self._nodes(sp, f"SP{i}", "", ""))
            if not n.children:
                n.text = _text(sp)
            doc.root.children.append(n)
        return doc

    def parse_xml(self, raw: bytes, meta: dict | None = None, revision: str = "") -> Document:
        """One revision from the bulk zip: the 法令標準XML (``<Law Era= Year= Num= LawType= ...>``) and what the
        zip's ``all_law_list.csv`` row and the API's law list say of it (``meta``: title, category, abbreviation,
        dates), in the shape ``parse`` reads."""
        tree = xml_tree(raw)
        attr = tree.get("attr") or {}
        meta = meta or {}
        law_id, enforced, amend_id = (revision.split("_") + ["", "", ""])[:3]
        law_id = law_id or meta.get("law_id") or ""
        body = _child(tree, "LawBody") or {}
        title_node = _child(body, "LawTitle")
        promulgated = meta.get("promulgation_date") or _gregorian(attr.get("Era"), attr.get("Year"),
                                                                  attr.get("PromulgateMonth"), attr.get("PromulgateDay"))
        law_type = attr.get("LawType") or LAW_TYPE_OF.get(meta.get("law_type_ja", ""), "") or meta.get("law_type") or "Act"
        enforcement = _iso8(enforced) or meta.get("amendment_enforcement_date")
        data = {"law_info": {"law_type": law_type, "law_id": law_id,
                             "law_num": _plain(_child(tree, "LawNum")) or meta.get("law_num") or "",
                             "law_num_num": attr.get("Num") or "", "promulgation_date": promulgated},
                "revision_info": {"law_title": _plain(title_node) or meta.get("law_title") or "",
                                  "law_title_kana": (title_node or {}).get("attr", {}).get("Kana") or meta.get("law_title_kana"),
                                  "abbrev": (title_node or {}).get("attr", {}).get("Abbrev") or meta.get("abbrev"),
                                  "amendment_enforcement_date": enforcement,
                                  "current_revision_status": meta.get("status") or "CurrentEnforced",
                                  "law_revision_id": revision or meta.get("law_revision_id"),
                                  "category": meta.get("category"), "updated": meta.get("updated"),
                                  "amendment_law_num": meta.get("amendment_law_num")},
                "law_full_text": tree, "fetched": meta.get("fetched")}
        doc = self.parse(data, law_id)
        doc.extra["amendment_law_id"] = amend_id if amend_id and amend_id.strip("0") else None
        doc.extra["revision_url"] = meta.get("revision_url")
        return doc

    def _nodes(self, node: dict, prefix: str, anchor: str, page: str) -> list[Node]:
        """The units and articles under ``node``.  ``anchor`` is the e-Gov page's element id of ``node``
        (``Mp-Ch_3-Se_1``) for the main provision, "" inside a 附則 (whose anchors are not stable)."""
        out: list[Node] = []
        for ch in node.get("children", []):
            if not isinstance(ch, dict) or ch["tag"] in SKIP:
                continue
            tag = ch["tag"]
            num = str((ch.get("attr") or {}).get("Num", ""))
            here = f"{anchor}-{ANCHOR[tag]}_{num}" if anchor and tag in ANCHOR and num else ""
            if tag == "Article":
                label = _plain(_child(ch, "ArticleTitle")) or f"第{num}条"
                caption = re.sub(r"^[（(]|[）)]$", "", _plain(_child(ch, "ArticleCaption")))
                out.append(Node(level="条", label=label, number=num, heading=caption,
                                text=_text(ch, skip={"ArticleTitle", "ArticleCaption"}), token=f"A{num.replace('_', '-')}",
                                native_id=f"art{num}", url=f"{page}#{here}" if page and here else "",
                                status="repealed" if (ch.get("attr") or {}).get("Delete") == "true" else "in_force"))
            elif tag in LEVELS and tag != "SupplProvision":
                word, letter = LEVELS[tag]
                title = _plain(_child(ch, f"{tag}Title"))
                m = re.match(r"^(第\S+?[編章節款目])\s*(.*)$", title)
                n = Node(level=word, label=title or f"第{num}{word}",
                         number=num, heading=(m.group(2) if m else "").strip(), token=f"{letter}{num.replace('_', '-')}",
                         status="repealed" if (ch.get("attr") or {}).get("Delete") == "true" else "in_force")
                n.children.extend(self._nodes(ch, n.token, here, page))
                out.append(n)
            # Paragraphs directly under a division without articles are read by the caller as text (_text)
        return out

    def citation(self, doc: Document, path, leaf: Node) -> str:
        """``行政手続法第十三条``; an article of a supplementary provision is cited with the amending law's number,
        ``行政手続法附則（令和八年法律第六六号）第五条``, as Japanese practice does."""
        if leaf.level == "条":
            supp = next((n.label for n in path if n.level == "附則"), "")
            return f"{doc.title}{supp}{leaf.label}"
        return f"{doc.title}{leaf.label if leaf.level != '本則' else ''}"

    def unit_slug(self, leaf: Node, path=()) -> str:
        """``art_13``; inside the n-th supplementary provision ``suppl_16_art_5``, since their numbering restarts."""
        if leaf.level == "附則":                 # a supplementary provision with paragraphs only: one leaf
            return f"suppl_{leaf.number}"
        sp = next((n for n in path if n.level == "附則"), None)
        base = f"art_{leaf.number.replace('_', '-')}" if leaf.level == "条" else "main"
        return f"suppl_{sp.number}_{base}" if sp is not None else base

    # the bulk download, under data/raw/countries/: the file the index is read from and stamped with
    raw_name = f"{CODE}/{ZIP_NAME}"


# ---------------------------------------------------------------------- the law list (API v2)
def law_entry(law: dict) -> dict:
    """One law of ``/api/2/laws`` as lexflow keeps it (the current revision's fields)."""
    info = law.get("law_info") or {}
    rev = law.get("current_revision_info") or law.get("revision_info") or {}
    return {"law_id": info.get("law_id"), "law_num": info.get("law_num"), "law_type": info.get("law_type"),
            "law_num_era": info.get("law_num_era"), "law_num_year": info.get("law_num_year"),
            "law_num_num": info.get("law_num_num"), "promulgation_date": info.get("promulgation_date"),
            "law_title": rev.get("law_title"), "law_title_kana": rev.get("law_title_kana"), "abbrev": rev.get("abbrev"),
            "category": rev.get("category"), "law_revision_id": rev.get("law_revision_id"),
            "amendment_law_id": rev.get("amendment_law_id"), "amendment_law_num": rev.get("amendment_law_num"),
            "amendment_promulgate_date": rev.get("amendment_promulgate_date"),
            "amendment_enforcement_date": rev.get("amendment_enforcement_date"),
            "amendment_scheduled_enforcement_date": rev.get("amendment_scheduled_enforcement_date"),
            "repeal_status": rev.get("repeal_status"), "repeal_date": rev.get("repeal_date"),
            "current_revision_status": rev.get("current_revision_status"), "updated": rev.get("updated"),
            "mission": rev.get("mission")}


def fetch_law_list(dest: Path | None = None, *, page: int = 1000, pace: float = 1.0, log: Log = print) -> dict:
    """Every law of ``/api/2/laws`` (paged, at most one request a second, lexflow's research user agent) written to
    ``laws.jsonl``; returns ``{"laws", "requests", "total_count", "fetched"}`` and records it in the manifest."""
    import requests
    dest = dest or RAW / LAWS_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".jsonl.part")
    offset, n, calls, total, last = 0, 0, 0, None, 0.0
    with open(tmp, "w", encoding="utf-8") as f:
        while True:
            wait = last + pace - time.time()
            if wait > 0:
                time.sleep(wait)
            last = time.time()
            r = requests.get(f"{API}/laws", params={"limit": page, "offset": offset, "response_format": "json"},
                             headers={"User-Agent": RESEARCH_UA, "Accept": "application/json"}, timeout=120)
            calls += 1
            r.raise_for_status()
            data = r.json()
            total = data.get("total_count", total)
            laws = data.get("laws") or []
            for law in laws:
                f.write(json.dumps(law_entry(law), ensure_ascii=False) + "\n")
            n += len(laws)
            log(f"jpn law list: {n:,} of {total:,}")
            nxt = data.get("next_offset")
            if not laws or nxt is None or nxt <= offset or n >= (total or 0):
                break
            offset = nxt
    tmp.replace(dest)
    out = {"file": dest.name, "laws": n, "requests": calls, "total_count": total, "url": f"{API}/laws",
           "fetched": _now(), "bytes": dest.stat().st_size, "sha256": _sha256(dest)}
    _manifest_set("law_list", out)
    return out


def law_list(path: Path | None = None) -> dict[str, dict]:
    """law_id -> the API's entry (empty when the list has not been fetched)."""
    path = path or RAW / LAWS_NAME
    if not path.exists():
        return {}
    out = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                e = json.loads(ln)
                out[e["law_id"]] = e
    return out


# ---------------------------------------------------------------------- amendments (the law_amendments table)
# Every edge lexflow can read from the two e-Gov sources, one row per (law, other law, kind, source):
#
# * ``egov-bulk-revision``: each revision folder of the bulk zip, ``<law_id>_<enforcement YYYYMMDD>_<amending law_id>``,
#   with the zip's ``all_law_list.csv`` row (改正法令番号, 改正法令名); the date is the revision's enforcement date.
# * ``egov-bulk-suppl``: each 附則 of a revision's XML that carries ``AmendLawNum`` ("平成一一年一二月八日法律第一五一号":
#   the supplementary provisions an amending law added, kept in the consolidated text); the date is the amending
#   law's promulgation date, which the attribute spells out.  This is the long history (every amendment whose 附則 the
#   consolidated text keeps), where the revision folders give only the latest one or two.
# * ``egov-api-list``: the API v2 law list's current revision (amendment_law_id, amendment dates) and its repeals
#   (``repeal_status`` Repeal with the repealing law in ``amendment_law_id``), with the inverse ``repeals`` row.
#
# ``law_key`` and ``amending_key`` are e-Gov law_ids; ``amending_key`` is empty when the amending law is in neither
# the API list nor the zip (most 一部改正法 are folded into the laws they amend and have no entry of their own), and
# ``amending_num`` is then the only name of the amending law, written as e-Gov writes law numbers
# (平成十一年法律第百五十一号).  ``law_num_key`` (平成11年法律第151号, the form Wikidata's law identifier uses) joins
# the spellings.
AMEND_TABLE = """CREATE TABLE IF NOT EXISTS law_amendments (
  jurisdiction TEXT NOT NULL,
  law_key TEXT NOT NULL,
  amending_key TEXT,
  amending_num TEXT NOT NULL,
  date TEXT,
  kind TEXT NOT NULL,
  source TEXT NOT NULL,
  date_kind TEXT,
  enforced TEXT,
  amending_title TEXT,
  revision TEXT,
  retrieved TEXT,
  PRIMARY KEY (jurisdiction, law_key, amending_num, kind, source)
);
CREATE INDEX IF NOT EXISTS law_amendments_law ON law_amendments(jurisdiction, law_key);
CREATE INDEX IF NOT EXISTS law_amendments_amending ON law_amendments(jurisdiction, amending_key);"""
AMEND_COLUMNS = ["jurisdiction", "law_key", "amending_key", "amending_num", "date", "kind", "source", "date_kind",
                 "enforced", "amending_title", "revision", "retrieved"]
AMEND_KINDS = ("amended", "repealed", "repeals")
_ERA_BASE = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}
_KNUM = "〇一二三四五六七八九十百千0-9"
LAW_NUM = re.compile(rf"^(明治|大正|昭和|平成|令和)([元{_KNUM}]+)年(?:([{_KNUM}]+)月([{_KNUM}]+)日)?(.+?)"
                     rf"(?:第([{_KNUM}]+)号)?$")
_SUPPL = re.compile(rb"<SupplProvision\b([^>]*)>")
_AMEND_ATTR = re.compile(rb'AmendLawNum="([^"]*)"')


def _knum(s: str) -> int:
    """A number in kanji (positional 百五十一 or digit form 一五一) or Arabic digits."""
    return int(s) if s.isdigit() else kanji_number(s)


def parse_law_num(text: str | None) -> dict | None:
    """``平成五年法律第八十八号`` or ``平成一一年一二月八日法律第一五一号`` (an AmendLawNum) -> ``{era, year, month, day,
    kind, num, gregorian}`` (``kind`` 法律, 政令, 厚生労働省令, 人事院規則一―一 ...; ``num`` None when the number has no
    第…号, as 人事院規則 numbers do); None when it is no era-year law number (日本国憲法's 昭和二十一年憲法 parses with kind
    憲法)."""
    import unicodedata
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or ""))
    m = LAW_NUM.match(s)
    if not m:
        return None
    era, y, mo, d, kind, num = m.groups()
    year = 1 if y == "元" else _knum(y)
    return {"era": era, "year": year, "month": _knum(mo) if mo else None, "day": _knum(d) if d else None,
            "kind": kind, "num": _knum(num) if num else None, "gregorian": _ERA_BASE[era] + year}


def law_num_key(text: str | None) -> str:
    """The spelling-independent key of a law number, in the form Wikidata's law identifier (P8550) uses:
    ``平成五年法律第八十八号`` and ``平成五年一一月一二日法律第八八号`` -> ``平成5年法律第88号`` (元年 stays 元年); "" when the
    text is no law number."""
    p = parse_law_num(text)
    if not p:
        return ""
    year = "元" if p["year"] == 1 else str(p["year"])
    return f"{p['era']}{year}年{p['kind']}" + (f"第{p['num']}号" if p["num"] is not None else "")


def kanji_positional(n: int) -> str:
    """88 -> 八十八, 151 -> 百五十一, 1000 -> 千, 0 -> 〇 (the way e-Gov writes law numbers)."""
    if n <= 0:
        return "〇"
    digits = "〇一二三四五六七八九"
    out = ""
    for unit, ch in ((1000, "千"), (100, "百"), (10, "十")):
        q, n = divmod(n, unit)
        if q:
            out += ("" if q == 1 else digits[q]) + ch
    return out + (digits[n] if n else "")


def law_num_text(text: str | None) -> str:
    """A law number as e-Gov's law list writes it, without a date: ``平成一一年一二月八日法律第一五一号`` ->
    ``平成十一年法律第百五十一号``; the text itself when it does not parse."""
    p = parse_law_num(text)
    if not p:
        return (text or "").strip()
    year = "元" if p["year"] == 1 else kanji_positional(p["year"])
    return f"{p['era']}{year}年{p['kind']}" + (f"第{kanji_positional(p['num'])}号" if p["num"] is not None else "")


def law_num_date(text: str | None) -> str | None:
    """The promulgation date an AmendLawNum spells out (``平成一一年一二月八日法律第一五一号`` -> ``1999-12-08``), or None.
    Dates before 明治6年 are the lunar-calendar dates the text gives, unconverted (as e-Gov's own list keeps them)."""
    p = parse_law_num(text)
    if not p or not p["month"] or not p["day"]:
        return None
    return f"{p['gregorian']:04d}-{p['month']:02d}-{p['day']:02d}"


def amendments(path: Path | None = None, *, laws: dict[str, dict] | None = None, retrieved: str | None = None,
               log: Log = print) -> Iterator[dict]:
    """Every amendment and repeal edge of the bulk zip and the API law list, as ``law_amendments`` rows (see above),
    one revision's XML in memory at a time.  Rows are deduplicated per (law, amending number, kind, source)."""
    import zipfile
    path = path or RAW / ZIP_NAME
    laws = law_list() if laws is None else laws
    retrieved = retrieved or ((_manifest().get("bulk") or {}).get("fetched") or "")[:10] or None
    listed = ((_manifest().get("law_list") or {}).get("fetched") or "")[:10] or retrieved
    by_num: dict[str, str] = {}
    for x in laws.values():
        k = law_num_key(x.get("law_num"))
        if k:
            by_num.setdefault(k, x["law_id"])
    seen: set[tuple] = set()

    def row(law_id, amending_key, amending_num, date, kind, source, **extra) -> dict | None:
        num = law_num_text(amending_num) if amending_num else ""
        if not amending_key and num:
            amending_key = by_num.get(law_num_key(num))
        if amending_key == law_id or not (num or amending_key):
            return None
        k = (law_id, num or amending_key, kind, source)
        if k in seen:
            return None
        seen.add(k)
        out = {"jurisdiction": CODE, "law_key": law_id, "amending_key": amending_key or None, "amending_num": num,
               "date": date, "kind": kind, "source": source, "date_kind": extra.get("date_kind"),
               "enforced": extra.get("enforced"), "amending_title": extra.get("amending_title") or None,
               "revision": extra.get("revision"), "retrieved": extra.get("retrieved", retrieved)}
        return out

    if path.exists():
        with zipfile.ZipFile(path) as z:
            names: dict[str, list[str]] = {}
            for i in z.infolist():
                if i.filename.endswith(".xml"):
                    names.setdefault(i.filename.split("/")[0], []).append(i.filename)
            text = z.read("all_law_list.csv").decode("utf-8-sig")
            csv_rows = list(csv.DictReader(io.StringIO(text)))
            for r in csv_rows:                              # the zip's own numbers name laws the API list lacks
                k = law_num_key(r.get("法令番号"))
                if k:
                    by_num.setdefault(k, r["法令ID"])
            for n, r in enumerate(csv_rows, 1):
                url = r.get("本文URL") or ""
                rev = url.rstrip("/").rsplit("/", 1)[-1]
                folder = f"{r['法令ID']}_{rev}" if rev and not rev.startswith(r["法令ID"]) else rev
                law_id, date8, amend_id = (folder.split("_") + ["", "", ""])[:3]
                enforced = _iso8(date8)
                if amend_id.strip("0"):
                    out = row(law_id, amend_id, r.get("改正法令番号") or "", enforced, "amended", "egov-bulk-revision",
                              date_kind="enforced", enforced=enforced, amending_title=r.get("改正法令名"),
                              revision=folder)
                    if out:
                        yield out
                for name in names.get(folder, []):
                    raw = z.read(name)
                    for m in _SUPPL.finditer(raw):
                        a = _AMEND_ATTR.search(m.group(1))
                        if not a:
                            continue
                        for num in re.split(r"[、,]", a.group(1).decode("utf-8")):
                            num = num.strip()
                            if not num:
                                continue
                            out = row(law_id, None, num, law_num_date(num), "amended", "egov-bulk-suppl",
                                      date_kind="promulgated", revision=folder)
                            if out:
                                yield out
                if n % 1000 == 0:
                    log(f"jpn amendments: {n:,} of {len(csv_rows):,} revisions read")
    for x in sorted(laws.values(), key=lambda e: e["law_id"]):
        law_id, amend_id = x["law_id"], x.get("amendment_law_id") or None
        if x.get("repeal_status") == "Repeal" and (amend_id or x.get("amendment_law_num")):
            out = row(law_id, amend_id, x.get("amendment_law_num") or "", x.get("repeal_date"), "repealed",
                      "egov-api-list", date_kind="repealed", enforced=x.get("repeal_date"), retrieved=listed)
            if out:
                yield out
                if out["amending_key"]:
                    inv = row(out["amending_key"], law_id, x.get("law_num") or "", x.get("repeal_date"), "repeals",
                              "egov-api-list", date_kind="repealed", enforced=x.get("repeal_date"), retrieved=listed,
                              amending_title=x.get("law_title"))
                    if inv:
                        yield inv
        elif amend_id or x.get("amendment_law_num"):
            out = row(law_id, amend_id, x.get("amendment_law_num") or "", x.get("amendment_promulgate_date"),
                      "amended", "egov-api-list", date_kind="promulgated", enforced=x.get("amendment_enforcement_date"),
                      revision=x.get("law_revision_id"), retrieved=listed)
            if out:
                yield out


def load_amendments(con, rows=None, *, log: Log = print, batch: int = 5000, listed: set[str] | None = None) -> dict:
    """Write ``amendments()`` into the ``law_amendments`` table of ``con`` (the lexflow database), replacing Japan's
    rows; returns the counts by source and kind and the distinct edges.  The rows are staged in a scratch SQLite
    file while the zip is read (a minute or two), then copied in one short transaction, so the shared database is
    never locked for the length of the read and never holds all the rows in memory."""
    import sqlite3
    import tempfile
    from collections import Counter
    con.executescript(AMEND_TABLE)
    rows = amendments(log=log) if rows is None else rows
    counts: Counter = Counter()
    cols = ",".join(AMEND_COLUMNS)
    sql = f"INSERT OR REPLACE INTO law_amendments ({cols}) VALUES ({','.join('?' * len(AMEND_COLUMNS))})"
    with tempfile.TemporaryDirectory(prefix="lexflow-amend-") as tmp:
        stage = Path(tmp) / "stage.sqlite"
        sc = sqlite3.connect(str(stage))
        sc.executescript(AMEND_TABLE)
        buf = []
        for r in rows:
            counts[(r["source"], r["kind"])] += 1
            buf.append(tuple(r.get(c) for c in AMEND_COLUMNS))
            if len(buf) >= batch:
                sc.executemany(sql, buf)
                buf.clear()
        if buf:
            sc.executemany(sql, buf)
        sc.commit()
        sc.close()
        con.execute("ATTACH DATABASE ? AS amend_stage", (str(stage),))
        try:
            with con:
                con.execute("DELETE FROM law_amendments WHERE jurisdiction=?", (CODE,))
                con.execute(f"INSERT OR REPLACE INTO law_amendments ({cols}) SELECT {cols} FROM amend_stage.law_amendments")
        finally:
            con.execute("DETACH DATABASE amend_stage")
    return amendment_counts(con, listed) | {"rows_by_source": {f"{s}/{k}": n for (s, k), n in sorted(counts.items())}}


def amendment_counts(con, listed: set[str] | None = None) -> dict:
    """Distinct edges of the ``law_amendments`` table for Japan (one per law and other law, by the other law's
    number): by kind, how many name the other law's e-Gov law_id, how many of those are laws of the API list
    (``listed``, default the list on disk; such laws get items of their own), and how many laws have one."""
    q = lambda sql: con.execute(sql, (CODE,)).fetchall()       # noqa: E731
    listed = set(law_list()) if listed is None else listed
    out = {"rows": q("SELECT COUNT(*) FROM law_amendments WHERE jurisdiction=?")[0][0]}
    edges: dict[str, dict[tuple, str | None]] = {}
    for kind, law, other, num in q("SELECT kind, law_key, amending_key, amending_num FROM law_amendments "
                                   "WHERE jurisdiction=?"):
        k = (law, num or other)
        e = edges.setdefault(kind, {})
        e[k] = e.get(k) or other
    for kind, e in sorted(edges.items()):
        out[kind] = {"edges": len(e), "with_law_id": sum(1 for v in e.values() if v),
                     "to_a_listed_law": sum(1 for v in e.values() if v and v in listed)}
    out["laws_with_amendments"] = q("SELECT COUNT(DISTINCT law_key) FROM law_amendments WHERE jurisdiction=? AND "
                                    "kind='amended'")[0][0]
    out["amending_laws"] = q("SELECT COUNT(DISTINCT COALESCE(NULLIF(amending_num, ''), amending_key)) FROM law_amendments WHERE "
                             "jurisdiction=? AND kind='amended'")[0][0]
    return out


# ---------------------------------------------------------------------- the bulk zip
def download_bulk(dest: Path | None = None, *, url: str = BULK_URL, log: Log = print, force: bool = False) -> dict:
    """The official bulk XML, once: streamed to ``all_xml.zip.part`` with lexflow's research user agent, resumed
    with ``Range: bytes=<have>-`` when a part file is left (the e-Gov server answered 200 to a Range request on 22
    October 2026, so a resume restarts from zero), checked as a zip, renamed, and recorded in the manifest with its
    size and SHA-256.  An existing zip whose size and digest match the manifest is kept."""
    import requests
    import zipfile
    dest = dest or RAW / ZIP_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)
    known = _manifest().get("bulk") or {}
    if dest.exists() and not force:
        if known.get("bytes") == dest.stat().st_size and known.get("sha256"):
            log(f"jpn: {dest.name} present ({dest.stat().st_size:,} bytes, sha256 {known['sha256'][:16]}...)")
            return known
        return record_bulk(dest, url=url, log=log)
    part = dest.with_name(dest.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": RESEARCH_UA, "Accept": "application/zip, application/octet-stream"}
    if have:
        headers["Range"] = f"bytes={have}-"
    h = hashlib.sha256()
    with requests.get(url, headers=headers, stream=True, timeout=(30, 300)) as r:
        r.raise_for_status()
        ranged = r.status_code == 206
        if have and ranged:
            with open(part, "rb") as f:
                for b in iter(lambda: f.read(1 << 20), b""):
                    h.update(b)
        elif have:
            log(f"jpn: the server ignored Range (HTTP {r.status_code}); restarting the download")
            have = 0
        got, t0, shown = have, time.time(), 0
        with open(part, "ab" if have else "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
                got += len(chunk)
                if got - shown >= 50 << 20:
                    shown = got
                    log(f"jpn: {got / 2**20:,.0f} MB")
        info = {"status": r.status_code, "content_length": r.headers.get("Content-Length"),
                "accept_ranges": r.headers.get("Accept-Ranges"), "seconds": round(time.time() - t0, 1)}
    with zipfile.ZipFile(part) as z:
        entries = len(z.infolist())
    part.replace(dest)
    out = {"file": dest.name, "url": url, "bytes": dest.stat().st_size, "sha256": h.hexdigest(), "entries": entries,
           "fetched": _now(), "user_agent": RESEARCH_UA, "http": info}
    _manifest_set("bulk", out)
    return out


def record_bulk(path: Path, *, url: str = BULK_URL, log: Log = print, note: str = "") -> dict:
    """Record a zip already on disk (size, SHA-256, entry count, the file's time) in the manifest."""
    import zipfile
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        xml = sum(1 for i in infos if i.filename.endswith(".xml"))
        unpacked = sum(i.file_size for i in infos)
    out = {"file": path.name, "url": url, "bytes": path.stat().st_size, "sha256": _sha256(path),
           "entries": len(infos), "xml_files": xml, "unpacked_bytes": unpacked,
           "fetched": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "user_agent": RESEARCH_UA,
           "http": {"status": 200, "content_length": None, "accept_ranges": None,
                    "note": note or "the server sent no Content-Length and answered a Range request with 200 and "
                                    "the whole file; resumes restart from zero"}}
    _manifest_set("bulk", out)
    log(f"jpn: recorded {path.name}: {out['bytes']:,} bytes, sha256 {out['sha256']}")
    return out


def revisions(z) -> dict[str, dict]:
    """law_id -> the revision to index, from the zip's ``all_law_list.csv``: the latest revision in force (no
    ``未施行`` mark) by enforcement date, else the earliest one not yet in force.  Each value carries the CSV row,
    the revision folder name and how many revisions the zip holds for the law."""
    raw = z.read("all_law_list.csv")
    text = raw.decode("utf-8-sig")
    by: dict[str, list[dict]] = {}
    for r in csv.DictReader(io.StringIO(text)):
        url = r.get("本文URL") or ""
        rev = url.rstrip("/").rsplit("/", 1)[-1]
        r["_revision"] = f"{r['法令ID']}_{rev}" if rev and not rev.startswith(r["法令ID"]) else rev
        r["_date"] = (r["_revision"].split("_") + ["", ""])[1]
        by.setdefault(r["法令ID"], []).append(r)
    out = {}
    for law_id, revs in by.items():
        now = [r for r in revs if not r.get("未施行")]
        pick = max(now, key=lambda r: r["_date"]) if now else min(revs, key=lambda r: r["_date"])
        pick = dict(pick, _count=len(revs), _future=sum(1 for r in revs if r.get("未施行")),
                    _in_force=bool(now))
        out[law_id] = pick
    return out


def iter_documents(path: Path | None = None, *, laws: dict[str, dict] | None = None, limit: int | None = None,
                   only: set[str] | None = None, log: Log = print) -> Iterator[Document]:
    """Every law of the bulk zip as a ``Document``, one at a time (the zip is read entry by entry; one law's XML
    tree is in memory at once), in law_id order.  ``laws`` is the API law list (category, ISO dates); ``only``
    restricts to some law_ids (tests, samples)."""
    import zipfile
    path = path or RAW / ZIP_NAME
    laws = law_list() if laws is None else laws
    jp = Japan()
    fetched = ((_manifest().get("bulk") or {}).get("fetched") or "")[:10] or jp.today()
    with zipfile.ZipFile(path) as z:
        names = {i.filename.split("/")[0]: i.filename for i in z.infolist() if i.filename.endswith(".xml")}
        picks = revisions(z)
        done = 0
        for law_id in sorted(picks):
            if only is not None and law_id not in only:
                continue
            r = picks[law_id]
            name = names.get(r["_revision"])
            if name is None:
                log(f"jpn: {law_id}: revision {r['_revision']} not in the zip")
                continue
            api = laws.get(law_id) or {}
            meta = {"law_id": law_id, "law_title": r.get("法令名") or api.get("law_title"),
                    "law_title_kana": r.get("法令名読み") or api.get("law_title_kana"), "law_num": r.get("法令番号"),
                    "law_type_ja": r.get("法令種別"), "abbrev": api.get("abbrev"), "category": api.get("category"),
                    "promulgation_date": api.get("promulgation_date"), "updated": api.get("updated"),
                    "amendment_law_num": r.get("改正法令番号") or None, "revision_url": r.get("本文URL"),
                    "status": "CurrentEnforced" if r["_in_force"] else "UnEnforced", "fetched": fetched}
            doc = jp.parse_xml(z.read(name), meta, r["_revision"])
            doc.extra.update(revisions=r["_count"], future_revisions=r["_future"], in_api_list=bool(api),
                             repeal_status=api.get("repeal_status"))
            yield doc
            done += 1
            if limit and done >= limit:
                return


# ---------------------------------------------------------------------- XML -> the API's tag tree
def xml_tree(raw: bytes) -> dict:
    """The 法令標準XML as the API's JSON tag tree: ``{"tag", "attr", "children": [str | node]}``, with the
    indentation between elements dropped (ASCII whitespace only: an ideographic space is text)."""
    import xml.etree.ElementTree as ET
    return _el(ET.fromstring(raw))


def _el(e) -> dict:
    kids: list = []
    if e.text and not _WS.fullmatch(e.text):
        kids.append(e.text)
    for c in e:
        kids.append(_el(c))
        if c.tail and not _WS.fullmatch(c.tail):
            kids.append(c.tail)
    return {"tag": e.tag, "attr": dict(e.attrib), "children": kids}


def _gregorian(era: str | None, year: str | None, month: str | None, day: str | None) -> str | None:
    try:
        y = ERA[era or ""] + int(year or 0)
        return f"{y:04d}-{int(month):02d}-{int(day):02d}"
    except (KeyError, ValueError, TypeError):
        return None


def _iso8(s: str | None) -> str | None:
    s = (s or "").strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if re.fullmatch(r"\d{8}", s) else None


def _type_letters(law_id: str) -> str:
    """``405AC0000000088`` -> ``AC``; ``321CONSTITUTION`` -> ``CONSTITUTION``; ``412M50000100127`` -> ``M5``."""
    rest = (law_id or "")[3:]
    if rest.startswith("CONSTITUTION"):
        return "CONSTITUTION"
    return rest[:2]


def era_year(law_num: str) -> str:
    """The Gregorian year of a law number (``平成五年法律第八十八号`` -> ``1993``), or ""."""
    m = re.match(r"^(明治|大正|昭和|平成|令和)([元〇一二三四五六七八九十百]+)年", law_num or "")
    if not m:
        return ""
    base = {"明治": 1867, "大正": 1911, "昭和": 1925, "平成": 1988, "令和": 2018}[m.group(1)]
    return str(base + kanji_number(m.group(2)))


def kanji_number(s: str) -> int:
    """``八十八`` -> 88, ``元`` -> 1, ``百二十七`` -> 127, ``二〇`` -> 20 (digit form)."""
    digits = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "元":
        return 1
    if s and all(ch in digits for ch in s):
        return int("".join(str(digits[ch]) for ch in s))
    total, cur = 0, 0
    for ch in s:
        if ch in digits:
            cur = digits[ch]
        elif ch in "十百千":
            unit = {"十": 10, "百": 100, "千": 1000}[ch]
            total += (cur or 1) * unit
            cur = 0
    return total + cur


# the kind of instrument a law number names (the words between the year and 第), in English
NUMBER_KIND_EN = (("太政官布告", "Dajokan Proclamation"), ("太政官達", "Dajokan Notice"), ("太政官布達", "Dajokan Notice"),
                  ("法律", "Act"), ("政令", "Cabinet Order"), ("勅令", "Imperial Ordinance"), ("省令", "Ministerial Ordinance"),
                  ("府令", "Ministerial Ordinance"), ("閣令", "Cabinet Ordinance"), ("規則", "Rule"), ("規程", "Rule"))


def law_kind_en(law_num: str, law_type: str = "") -> str:
    """What a law is, in English, from its number's own word (``…厚生労働省令第一号`` -> Ministerial Ordinance;
    ``明治五年太政官布告…`` -> Dajokan Proclamation), else from the e-Gov law type."""
    m = re.match(r"^(?:明治|大正|昭和|平成|令和)[^年]*年(.+?)(?:第|$)", law_num or "")
    word = m.group(1) if m else ""
    for ja, en in NUMBER_KIND_EN:
        if word.endswith(ja):
            return en
    return LAW_TYPE_EN.get(law_type, "Law")


def law_number_en(law_num: str, law_type: str) -> str:
    """``平成五年法律第八十八号`` -> ``Act No. 88 of 1993``, the English citation form of a law number ("" when the
    number does not parse: 日本国憲法, 人事院規則一―一, a decision without a number)."""
    year = era_year(law_num)
    m = re.search(r"第([〇一二三四五六七八九十百千]+)号", law_num or "")
    if not year or not m:
        return ""
    return f"{law_kind_en(law_num, law_type)} No. {kanji_number(m.group(1))} of {year}"


# ---------------------------------------------------------------------- the manifest and the notice
def _manifest() -> dict:
    p = RAW / MANIFEST_NAME
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _manifest_set(key: str, value: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    m = _manifest()
    m[key] = value
    m.setdefault("source", BULK_PAGE)
    m["licence"] = {"name": "公共データ利用規約（第1.0版）(PDL1.0)", "url": PDL_URL, "terms": TERMS_URL,
                    "attribution": ATTRIBUTION, "edit_note": EDIT_NOTE}
    (RAW / MANIFEST_NAME).write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def manifest() -> dict:
    return _manifest()


NOTICE = """e-Gov 法令検索 法令データ (Japan) -- licence notice kept with the download
=====================================================================

出典 (source statement, PDL1.0 1.1)
  {attribution}
  取得日: {fetched}

加工の旨 (edit statement, PDL1.0 1.1)
  {edit_note}

In English
  {attribution_en}
  Retrieved: {fetched}
  {edit_note_en}

Licence as the source states it (read {read})
  e-Gov 法令検索 利用規約 ({terms}):
    「本サイトの著作権は、特記されていない限りデジタル庁に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」
    （PDL1.0）が適用されています。」
  公共データ利用規約（第1.0版） ({pdl}):
    「どなたでも以下の1.1.から1.7.に定める利用ルール（以下「本利用ルール」といいます。）に従って、複製、公衆送信、
    翻訳・変形等の翻案等、自由に利用できます ... 商用利用も可能です。」
    1.1 出典の記載について: 本コンテンツを利用する際は出典を記載してください ... 本コンテンツを編集・加工等して利用する場合は、
    上記出典とは別に、編集・加工等を行ったこと及びその主体を記載してください ... 編集・加工した情報を、あたかも国 ... が作成した
    未加工のままであるかのような態様で公表・利用してはいけません。
    「本利用ルールは、クリエイティブ・コモンズ・ライセンスの表示4.0 国際ライセンス ... と互換性があります。」
  Not covered by PDL1.0 (1.4): symbol marks, logos and character designs of organisations; content for which another
  rule is stated.  Third-party rights (1.2) remain with their holders.

Files here
  {files}
"""


def write_notice(path: Path | None = None) -> Path:
    """``LICENSE-NOTICE.txt`` beside the download: the 出典 and 加工 statements PDL1.0 asks for, in Japanese and
    English, the licence as the source states it, and the files with their digests."""
    path = path or RAW / NOTICE_NAME
    m = _manifest()
    files = []
    for k in ("bulk", "law_list"):
        e = m.get(k)
        if e:
            files.append(f"{e['file']}: {e['bytes']:,} bytes, sha256 {e['sha256']}, retrieved {e['fetched']} from "
                         f"{e['url']}")
    fetched = ((m.get("bulk") or {}).get("fetched") or _now())[:10]
    path.write_text(NOTICE.format(attribution=ATTRIBUTION, edit_note=EDIT_NOTE, attribution_en=ATTRIBUTION_EN,
                                  edit_note_en=EDIT_NOTE_EN, fetched=fetched, read="2026-10-22", terms=TERMS_URL,
                                  pdl=PDL_URL, files="\n  ".join(files) or "(none yet)"), encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------- the tag tree
def _child(node: dict | None, tag: str) -> dict | None:
    for ch in (node or {}).get("children", []):
        if isinstance(ch, dict) and ch["tag"] == tag:
            return ch
    return None


def _children(node: dict | None, tag: str) -> list[dict]:
    return [ch for ch in (node or {}).get("children", []) if isinstance(ch, dict) and ch["tag"] == tag]


def _plain(node: dict | None) -> str:
    """Every string under a node, joined without separators (Japanese has no word spaces)."""
    if node is None:
        return ""
    out = []
    for ch in node.get("children", []):
        out.append(ch if isinstance(ch, str) else _plain(ch))
    return "".join(out).strip()


BLOCK = {"Paragraph", "Item", "Subitem1", "Subitem2", "Subitem3", "Subitem4", "Subitem5", "Subitem6", "Subitem7",
         "Subitem8", "Subitem9", "Subitem10", "List", "Sublist1", "Sublist2", "Sublist3", "TableStruct", "FigStruct",
         "StyleStruct", "NoteStruct", "FormatStruct", "Remarks", "AmendProvision", "Class"}
INLINE_SEP = {"ParagraphNum", "ItemTitle", "Subitem1Title", "Subitem2Title", "Subitem3Title", "ClassTitle",
              "ParagraphCaption"}


def _text(node: dict, skip: set[str] = frozenset(), depth: int = 0) -> str:
    """The text of an article: one line per paragraph or item, numbers kept (``１　...``, ``一　...``), items
    indented by one ideographic space per level, table cells joined by a tab."""
    lines: list[str] = []
    cur: list[str] = []

    def flush():
        s = "".join(cur).strip()
        if s:
            lines.append("　" * depth + s)
        cur.clear()

    for ch in node.get("children", []):
        if isinstance(ch, str):
            cur.append(ch)
            continue
        tag = ch["tag"]
        if tag in skip:
            continue
        if tag in BLOCK:
            flush()
            lines.append(_text(ch, depth=depth + (1 if tag != "Paragraph" else 0)))
        elif tag in INLINE_SEP:
            cur.append(_plain(ch) + "　")
        elif tag in ("TableRow",):
            flush()
            lines.append("　" * depth + "\t".join(_plain(c) for c in ch.get("children", []) if isinstance(c, dict)))
        elif tag == "Column":
            cur.append(_plain(ch) + "　")
        else:
            cur.append(_text(ch, depth=depth) if any(isinstance(c, dict) and c["tag"] in BLOCK
                                                     for c in ch.get("children", [])) else _plain(ch))
    flush()
    return "\n".join(ln for ln in lines if ln.strip())


# ---------------------------------------------------------------------- command line
def main(argv: list[str] | None = None) -> int:
    """``python -m lexflow.corpus.countries.japan download|laws|notice|sample [law_id ...]|amendments``
    (``amendments``: the ``law_amendments`` table of the lexflow database, from the zip and the law list)"""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="lexflow.corpus.countries.japan")
    ap.add_argument("action", choices=["download", "laws", "notice", "sample", "amendments"])
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.action == "download":
        print(json.dumps(download_bulk(force=a.force), ensure_ascii=False, indent=1))
    elif a.action == "laws":
        print(json.dumps(fetch_law_list(), ensure_ascii=False, indent=1))
    elif a.action == "notice":
        print(write_notice())
    elif a.action == "amendments":
        from ...store import db
        con = db.connect()
        try:
            print(json.dumps(load_amendments(con, log=lambda m: print(m, file=sys.stderr)), ensure_ascii=False,
                             indent=1))
        finally:
            con.close()
    else:
        for doc in iter_documents(only=set(a.ids) or None, limit=None if a.ids else 3):
            rows = Japan().to_rows(doc)
            sys.stdout.write(json.dumps({"law_id": doc.native_id, "title": doc.title, "rows": len(rows),
                                         "first": rows[0] if rows else None}, ensure_ascii=False)[:2000] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
