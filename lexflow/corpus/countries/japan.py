"""Japan: e-Gov 法令検索 (Digital Agency), every national law and regulation as structured XML/JSON via the 法令API.

Verified 19 October 2026 (docs/design/global-sources.md §2.6):

* ``https://laws.e-gov.go.jp/api/2/laws?limit=&offset=&law_type=`` lists the laws (9,567 on 19 Oct 2026 with the
  default filters; the v1 list ``/api/1/lawlists/1`` is 2.8 MB of XML);
  ``/api/2/law_data/{law_id}?response_format=json`` returns one law's current consolidated text as a tag tree
  (``Law > LawBody > MainProvision > Part/Chapter/Section/Subsection/Division > Article > Paragraph > Item ...``,
  plus ``SupplProvision``), ``/api/2/law_file/xml/{law_id}`` the same as the 法令標準XML; OpenAPI at
  ``/api/2/swagger-ui/lawapi-v2.yaml`` (version 2.1.139).  No key, no documented quota.
* ``https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true`` is the official bulk export
  (``all_xml.zip``, every law as XML; size not announced by the server).
* Licence: the site's 利用規約 says the content's copyright belongs to the Digital Agency and that the 公共データ利用規約
  （第1.0版） (PDL1.0) applies: "複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます ... 商用利用も可能です" with a
  source statement (出典) and a note when edited.  PDL1.0 is the successor of the 政府標準利用規約 and is CC BY 4.0
  compatible.
* Translations: 日本法令外国語訳データベースシステム (Ministry of Justice, https://www.japaneselawtranslation.go.jp/)
  publishes unofficial English translations under PDL1.0; "Only the original Japanese texts of the laws and
  regulations have legal effect".

Rows: one per 条 (Article), transitory and amending provisions under 附則 (SupplProvision); a law whose main
provision has no articles (元号法) becomes one row for 本則.  Path ``行政手続法 / 第一章　総則 / 第一条``, citation
``行政手続法第一条``, act_id ``STATE_JP_405AC0000000088_C1_A1``, ELI ``.../eli/jp/act/1993/88/art_1/ja@<enforcement>``.
Text keeps the paragraph numbers (１、２) and item titles (一、二) as the source gives them, one paragraph per
line, so verbatim quotes can be checked against the source.
"""
from __future__ import annotations

import re

from .base import Country, Document, Node, Source

API = "https://laws.e-gov.go.jp/api/2"
PAGE_URL = "https://laws.e-gov.go.jp/law/{id}"
LEVELS = {"Part": ("編", "PT"), "Chapter": ("章", "C"), "Section": ("節", "S"), "Subsection": ("款", "SS"),
          "Division": ("目", "D"), "Article": ("条", "A"), "SupplProvision": ("附則", "SP")}
TITLE_TAGS = {"PartTitle", "ChapterTitle", "SectionTitle", "SubsectionTitle", "DivisionTitle"}
SKIP = {"TOC", "LawTitle", "LawNum", "EnactStatement", "Preamble", "AppdxTable", "AppdxNote", "AppdxStyle", "Appdx",
        "AppdxFig", "AppdxFormat", "SupplProvisionAppdxTable", "SupplProvisionAppdx", "SupplProvisionAppdxStyle"}
LAW_TYPES = {"Constitution": "憲法", "Act": "法律", "CabinetOrder": "政令", "ImperialOrder": "勅令",
             "MinisterialOrdinance": "府省令", "Rule": "規則", "Misc": "その他"}


class Japan(Country):
    code = "jp"
    name = "Japan"
    wikidata = "Q17"
    languages = ("ja",)
    code_label = "日本の法令 (e-Gov法令検索)"
    pace = 1.5
    status = "prototype"
    sources = (
        Source(name="e-Gov 法令検索 法令API v2", publisher="デジタル庁 (Digital Agency, Government of Japan)",
               url="https://laws.e-gov.go.jp/",
               holds="the Constitution, Acts, Cabinet Orders, Imperial Orders, ministerial ordinances and rules in "
                     "force, consolidated, with revision history (9,567 laws listed on 19 Oct 2026)",
               format="法令標準XML and JSON tag tree (Law > MainProvision > Chapter > Article > Paragraph > Item)",
               access="REST API without key (/api/2/laws, /law_data, /law_file, /keyword); official bulk XML "
                      "(all_xml.zip) at /bulkdownload; OpenAPI 2.1.139 at /api/2/swagger-ui/lawapi-v2.yaml",
               identifier="law_id (e.g. 405AC0000000088: era-year, type, number), law_num (平成五年法律第八十八号), "
                          "law_revision_id; no ELI",
               licence="本サイトの著作権は、特記されていない限りデジタル庁に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」"
                       "（PDL1.0）が適用されています。 PDL1.0: どなたでも ... 複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます ... "
                       "商用利用も可能です。",
               licence_url="https://www.digital.go.jp/resources/open_data/public_data_license_v1.0",
               languages=("ja",), verified="2026-10-19",
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

    def fetch_list(self, limit: int = 20, law_type: str = "Act", offset: int = 0) -> list[dict]:
        r = self.get(f"{API}/laws?limit={int(limit)}&offset={int(offset)}&law_type={law_type}&response_format=json",
                     accept="application/json")
        out = []
        for law in r.json().get("laws", []):
            info, rev = law.get("law_info", {}), law.get("current_revision_info") or law.get("revision_info", {})
            out.append({"native_id": info.get("law_id"), "law_num": info.get("law_num"), "title": rev.get("law_title"),
                        "type": info.get("law_type"), "promulgated": info.get("promulgation_date"),
                        "status": rev.get("current_revision_status")})
        return out

    def fetch_document(self, native_id: str) -> Document:
        r = self.get(f"{API}/law_data/{native_id}?response_format=json", accept="application/json")
        return self.parse(r.content, native_id)

    def parse(self, raw: bytes | str, native_id: str = "") -> Document:
        import json
        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
        info, rev, tree = data.get("law_info", {}), data.get("revision_info", {}), data.get("law_full_text", {})
        law_id = info.get("law_id") or native_id
        law_type = info.get("law_type", "Act")
        enforcement = rev.get("amendment_enforcement_date")
        year = (info.get("promulgation_date") or "")[:4]
        number = str(info.get("law_num_num") or "").lstrip("0") or "0"
        title = rev.get("law_title") or ""
        doc = Document(country="jp", native_id=law_id, kind=LAW_TYPES.get(law_type, law_type), kind_token=law_id,
                       number=info.get("law_num") or "", title=title, short_title=rev.get("abbrev") or "",
                       language="ja", year=year, eli_type=law_type.lower(), eli_number=number,
                       url=PAGE_URL.format(id=law_id),
                       status={"CurrentEnforced": "in_force", "Repeal": "repealed"}.get(
                           rev.get("current_revision_status", ""), "not_yet_in_force"
                           if rev.get("current_revision_status") == "PreviousEnforced" else "in_force"),
                       version_date=enforcement, promulgated=info.get("promulgation_date"),
                       last_amended_year=int(enforcement[:4]) if enforcement else None, fetched=self.today(),
                       source=self.sources[0].name, licence=self.sources[0].licence,
                       extra={"law_revision_id": rev.get("law_revision_id"), "law_title_kana": rev.get("law_title_kana"),
                              "category": rev.get("category"), "updated": rev.get("updated"),
                              "api_url": f"{API}/law_data/{law_id}?response_format=json"})
        doc.short_title = ""                        # cite by the full title, as Japanese practice does
        doc.root = Node(level=doc.kind, label=title, number=doc.number, heading=title, native_id=law_id)
        body = _child(tree, "LawBody") or {}
        main = _child(body, "MainProvision")
        if main is not None:
            kids = self._nodes(main, "")
            if kids:
                doc.root.children.extend(kids)
            else:                                   # a law with paragraphs only (元号法): one leaf for the main provision
                doc.root.children.append(Node(level="本則", label="本則", number="", text=_text(main), token="MAIN"))
        for i, sp in enumerate(_children(body, "SupplProvision"), 1):
            label = re.sub(r"\s+", "", _plain(_child(sp, "SupplProvisionLabel"))) or "附則"
            amend = (sp.get("attr") or {}).get("AmendLawNum", "")
            n = Node(level="附則", label=f"{label}（{amend}）" if amend else label, number=str(i), heading=amend,
                     token=f"SP{i}", effective_from=enforcement)
            n.children.extend(self._nodes(sp, f"SP{i}"))
            if not n.children:
                n.text = _text(sp)
            doc.root.children.append(n)
        return doc

    def _nodes(self, node: dict, prefix: str) -> list[Node]:
        out: list[Node] = []
        for ch in node.get("children", []):
            if not isinstance(ch, dict) or ch["tag"] in SKIP:
                continue
            tag = ch["tag"]
            if tag == "Article":
                num = str((ch.get("attr") or {}).get("Num", ""))
                label = _plain(_child(ch, "ArticleTitle")) or f"第{num}条"
                caption = re.sub(r"^[（(]|[）)]$", "", _plain(_child(ch, "ArticleCaption")))
                out.append(Node(level="条", label=label, number=num, heading=caption,
                                text=_text(ch, skip={"ArticleTitle", "ArticleCaption"}), token=f"A{num.replace('_', '-')}",
                                native_id=f"art{num}",
                                status="repealed" if (ch.get("attr") or {}).get("Delete") == "true" else "in_force"))
            elif tag in LEVELS and tag != "SupplProvision":
                word, letter = LEVELS[tag]
                num = str((ch.get("attr") or {}).get("Num", ""))
                title = _plain(_child(ch, f"{tag}Title"))
                m = re.match(r"^(第\S+?[編章節款目])\s*(.*)$", title)
                n = Node(level=word, label=title or f"第{num}{word}",
                         number=num, heading=(m.group(2) if m else "").strip(), token=f"{letter}{num.replace('_', '-')}",
                         status="repealed" if (ch.get("attr") or {}).get("Delete") == "true" else "in_force")
                n.children.extend(self._nodes(ch, n.token))
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
