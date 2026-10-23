"""Laws in the shape of WikiProject Brazilian Laws (docs/design/wikidata-laws.md): Japanese law numbers and
amendments, the law item's statements and references, the licence rule, the single-pass push and the
QuickStatements that only add what existing Wikidata items lack.  No network: Wikidata answers are canned."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from lexflow.corpus import countries as CT
from lexflow.corpus.countries import japan as J
from lexflow.publish import graph, lint, push, wikidata_export as WE
from lexflow.publish import schema as SC
from lexflow.publish.graph import Claim, Item, Value

from test_push import FakeSession, api_for, entity, key_claim       # the fake wiki of tests/test_push.py

GYO = "405AC0000000088"            # 行政手続法
AMENDER = "426AC0000000069"        # a listed law that amended it (行政不服審査法の施行に伴う関係法律の整備等に関する法律)
OLD = "133AC0000000067"            # 国税犯則取締法, repealed by 平成二十九年法律第四号
NEW = "429AC0000000004"


# --------------------------------------------------------------------------- law numbers
def test_law_numbers_parse_in_every_spelling():
    p = J.parse_law_num("平成一一年一二月八日法律第一五一号")
    assert (p["era"], p["year"], p["month"], p["day"], p["kind"], p["num"], p["gregorian"]) == \
        ("平成", 11, 12, 8, "法律", 151, 1999)
    assert J.law_num_key("平成五年法律第八十八号") == J.law_num_key("平成五年一一月一二日法律第八八号") == "平成5年法律第88号"
    assert J.law_num_key("令和元年法律第一号") == "令和元年法律第1号"
    assert J.law_num_text("平成一一年一二月八日法律第一五一号") == "平成十一年法律第百五十一号"
    assert J.law_num_text("平成一二年八月一四日総理府・大蔵省令第九号") == "平成十二年総理府・大蔵省令第九号"
    assert J.law_num_date("令和八年七月二四日法律第六六号") == "2026-07-24" and J.law_num_date("平成五年法律第八十八号") is None
    assert J.law_num_key("昭和二十四年人事院規則一―一") == "昭和24年人事院規則一―一"
    assert J.parse_law_num("日本国憲法") is None and J.law_num_key("") == ""
    assert [J.kanji_positional(n) for n in (1, 10, 88, 100, 151, 337, 1234)] == \
        ["一", "十", "八十八", "百", "百五十一", "三百三十七", "千二百三十四"]


def test_makers_come_from_the_law_number():
    assert SC.egov_makers("平成五年法律第八十八号", "Act", "1993-11-12") == ["国会"]
    assert SC.egov_makers("昭和二十二年法律第六十七号", "Act", "1947-04-17") == ["帝国議会"]     # before 3 May 1947
    assert SC.egov_makers("明治十九年法律第一号", "Act", "1886-08-13") == []                    # before the Diet
    assert SC.egov_makers("平成十四年政令第二百七十七号") == ["内閣"]
    assert SC.egov_makers("平成十二年総理府・大蔵省令第九号") == ["総理府", "大蔵省"]
    assert SC.egov_makers("令和四年カジノ管理委員会規則・国土交通省令第一号") == ["カジノ管理委員会", "国土交通省"]
    assert SC.egov_makers("昭和二十四年人事院規則一―一") == ["人事院"]
    assert SC.egov_makers("明治五年太政官布告第三百三十七号") == ["太政官"]
    assert SC.egov_makers("昭和二十一年憲法") == []
    # offices, never persons: the Emperor and the Prime Minister are positions
    assert SC.EGOV_ISSUERS["天皇"][1] == SC.EGOV_ISSUERS["内閣総理大臣"][1] == "position"


# --------------------------------------------------------------------------- amendments
def _xml(num: str, title: str, suppl: list[str]) -> bytes:
    sp = "".join(f'<SupplProvision AmendLawNum="{a}" Extract="true"><SupplProvisionLabel>附則</SupplProvisionLabel>'
                 f'<Paragraph Num="1"><ParagraphSentence><Sentence>x</Sentence></ParagraphSentence></Paragraph>'
                 f'</SupplProvision>' for a in suppl)
    return (f'<?xml version="1.0" encoding="UTF-8"?><Law Era="Heisei" Year="05" Num="088" LawType="Act">'
            f'<LawNum>{num}</LawNum><LawBody><LawTitle>{title}</LawTitle><MainProvision><Article Num="1">'
            f'<Paragraph Num="1"><ParagraphSentence><Sentence>本文</Sentence></ParagraphSentence></Paragraph></Article>'
            f'</MainProvision><SupplProvision><SupplProvisionLabel>附則</SupplProvisionLabel></SupplProvision>{sp}'
            f'</LawBody></Law>').encode("utf-8")


def _zip(path: Path) -> Path:
    rows = [
        {"法令種別": "法律", "法令番号": "平成五年法律第八十八号", "法令名": "行政手続法", "改正法令名": "整備法",
         "改正法令番号": "平成二十六年法律第六十九号", "法令ID": GYO, "本文URL":
         f"https://laws.e-gov.go.jp/law/{GYO}/20160401_{AMENDER}", "未施行": ""},
        {"法令種別": "法律", "法令番号": "平成二十六年法律第六十九号", "法令名": "整備法", "改正法令名": "",
         "改正法令番号": "", "法令ID": AMENDER, "本文URL": f"https://laws.e-gov.go.jp/law/{AMENDER}/20160401_000000000000000",
         "未施行": ""},
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]) + ["法令名読み", "旧法令名", "公布日", "改正法令公布日", "施行日",
                                                        "施行日備考"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("all_law_list.csv", "﻿" + buf.getvalue())
        z.writestr(f"{GYO}_20160401_{AMENDER}/{GYO}_20160401_{AMENDER}.xml",
                   _xml("平成五年法律第八十八号", "行政手続法", ["平成一一年一二月八日法律第一五一号",
                                                       "平成二六年六月一三日法律第六九号", "平成五年一一月一二日法律第八八号"]))
        z.writestr(f"{AMENDER}_20160401_000000000000000/{AMENDER}_20160401_000000000000000.xml",
                   _xml("平成二十六年法律第六十九号", "整備法", []))
    return path


def _law_list() -> dict[str, dict]:
    base = {"law_type": "Act", "abbrev": None, "category": "行政手続", "repeal_status": "None", "repeal_date": None,
            "current_revision_status": "CurrentEnforced", "amendment_law_id": None, "amendment_law_num": None}
    return {
        GYO: dict(base, law_id=GYO, law_num="平成五年法律第八十八号", law_title="行政手続法", abbrev="行手法",
                  promulgation_date="1993-11-12", amendment_law_id=AMENDER, amendment_law_num="平成二十六年法律第六十九号",
                  amendment_promulgate_date="2014-06-13", amendment_enforcement_date="2016-04-01"),
        AMENDER: dict(base, law_id=AMENDER, law_num="平成二十六年法律第六十九号", law_title="整備法",
                      promulgation_date="2014-06-13"),
        OLD: dict(base, law_id=OLD, law_num="明治三十三年法律第六十七号", law_title="国税犯則取締法", category="国税",
                  promulgation_date="1900-03-17", repeal_status="Repeal", repeal_date="2018-04-01",
                  current_revision_status="Repeal", amendment_law_id=NEW, amendment_law_num="平成二十九年法律第四号"),
        NEW: dict(base, law_id=NEW, law_num="平成二十九年法律第四号", law_title="所得税法等の一部を改正する等の法律",
                  category="国税", promulgation_date="2017-03-31"),
    }


def test_amendments_from_the_zip_and_the_list(tmp_path):
    rows = list(J.amendments(_zip(tmp_path / "all_xml.zip"), laws=_law_list(), retrieved="2026-10-22",
                             log=lambda *_: None))
    by = {(r["law_key"], r["amending_num"], r["kind"], r["source"]): r for r in rows}
    rev = by[(GYO, "平成二十六年法律第六十九号", "amended", "egov-bulk-revision")]
    assert rev["amending_key"] == AMENDER and rev["date"] == "2016-04-01" and rev["date_kind"] == "enforced"
    assert rev["revision"] == f"{GYO}_20160401_{AMENDER}" and rev["amending_title"] == "整備法"
    old = by[(GYO, "平成十一年法律第百五十一号", "amended", "egov-bulk-suppl")]
    assert old["amending_key"] is None and old["date"] == "1999-12-08" and old["date_kind"] == "promulgated"
    # the suppl edge names its amending law by number only; the number resolves to the listed law
    assert by[(GYO, "平成二十六年法律第六十九号", "amended", "egov-bulk-suppl")]["amending_key"] == AMENDER
    # a law's own number in its supplementary provisions is no amendment
    assert not [r for r in rows if r["law_key"] == r["amending_key"]]
    assert not [k for k in by if k[0] == GYO and k[1] == "平成五年法律第八十八号"]
    rep = by[(OLD, "平成二十九年法律第四号", "repealed", "egov-api-list")]
    assert rep["amending_key"] == NEW and rep["date"] == "2018-04-01"
    inv = by[(NEW, "明治三十三年法律第六十七号", "repeals", "egov-api-list")]
    assert inv["amending_key"] == OLD
    assert len(rows) == len({(r["law_key"], r["amending_num"], r["kind"], r["source"]) for r in rows})


def test_load_amendments_and_counts(tmp_path):
    import sqlite3
    con = sqlite3.connect(str(tmp_path / "t.db"))
    rows = J.amendments(_zip(tmp_path / "all_xml.zip"), laws=_law_list(), retrieved="2026-10-22", log=lambda *_: None)
    listed = set(_law_list())
    out = J.load_amendments(con, rows, listed=listed)
    # one edge per law and amending law, however many sources name it (the revision folder, the 附則, the list)
    assert out["amended"] == {"edges": 2, "with_law_id": 1, "to_a_listed_law": 1} and out["repealed"]["edges"] == 1
    assert out["repeals"] == {"edges": 1, "with_law_id": 1, "to_a_listed_law": 1} and out["laws_with_amendments"] == 1
    again = J.load_amendments(con, J.amendments(_zip(tmp_path / "z2.zip"), laws=_law_list(), log=lambda *_: None),
                              listed=listed)
    assert again["rows"] == out["rows"]                                       # replaced, not appended


# --------------------------------------------------------------------------- the law item
INDEX = [{"law_id": GYO, "title": "行政手続法", "law_num": "平成五年法律第八十八号", "law_type": "Act", "kind": "法律",
          "category": "行政手続", "abbrev": "行手法", "kana": "", "promulgated": "1993-11-12", "enforced": "2026-07-24",
          "revision_id": f"{GYO}_20260724_508AC0000000066", "url": f"https://laws.e-gov.go.jp/law/{GYO}",
          "status": "in_force", "number_en": "Act No. 88 of 1993", "kind_en": "Act"},
         {"law_id": AMENDER, "title": "整備法", "law_num": "平成二十六年法律第六十九号", "law_type": "Act", "kind": "法律",
          "category": "行政手続", "abbrev": "", "kana": "", "promulgated": "2014-06-13", "enforced": "2016-04-01",
          "revision_id": f"{AMENDER}_20160401_000000000000000", "url": f"https://laws.e-gov.go.jp/law/{AMENDER}",
          "status": "in_force", "number_en": "Act No. 69 of 2014", "kind_en": "Act"},
         {"law_id": NEW, "title": "所得税法等の一部を改正する等の法律", "law_num": "平成二十九年法律第四号", "law_type": "Act",
          "kind": "法律", "category": "国税", "abbrev": "", "kana": "", "promulgated": "2017-03-31",
          "enforced": "2017-04-01", "revision_id": f"{NEW}_20170401_000000000000000",
          "url": f"https://laws.e-gov.go.jp/law/{NEW}", "status": "in_force", "number_en": "Act No. 4 of 2017",
          "kind_en": "Act"}]


@pytest.fixture()
def jpn(con, tmp_path, monkeypatch):
    """Japan's index (three laws), its law list (plus a repealed law) and its amendments, without the network."""
    raw = tmp_path / "raw" / "countries"
    (raw / "jpn").mkdir(parents=True)
    with open(raw / "jpn" / "laws.jsonl", "w", encoding="utf-8") as f:
        for e in _law_list().values():
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    monkeypatch.setattr(CT, "DIR", raw)
    monkeypatch.setattr(CT, "laws", lambda code, corpus="statutes": [dict(x) for x in INDEX] if code == "jpn" else [])
    monkeypatch.setattr(J, "manifest", lambda: {"bulk": {"fetched": "2026-10-22T12:47:00Z"},
                                                "law_list": {"fetched": "2026-10-22T13:04:00Z"}})
    J.load_amendments(con, J.amendments(_zip(tmp_path / "all_xml.zip"), laws=_law_list(), retrieved="2026-10-22",
                                        log=lambda *_: None))
    items = graph.build(con, states=["jpn"], drafts=False, log=lambda *_: None)
    return {it.key: it for it in items}


def _claims(it, prop):
    return [c for c in it.claims if c.prop == prop]


def test_law_item_has_the_brazilian_shape_with_references(jpn):
    law = jpn[f"lexflow:unit:jpn:{GYO.lower()}"]
    assert law.label == "" and law.labels["ja"] == "行政手続法" and law.description == "Japanese law (Act No. 88 of 1993)"
    assert "Act No. 88 of 1993" in law.aliases and {"行手法", "平成五年法律第八十八号"} <= set(law.lang_aliases["ja"])
    one = lambda p: _claims(law, p)[0]                                          # noqa: E731
    assert one("e-Gov law ID").value.value == GYO and one("law number").value.value == "平成五年法律第八十八号"
    assert (one("short name").value.value, one("short name").value.lang) == ("行手法", "ja")
    assert one("legislated by").value.value == "lexflow:agency:jpn:national_diet"
    assert one("language of work").value.value == "lexflow:vocab:language:ja"
    assert one("promulgation date").value.value == "1993-11-12"
    ref = dict(one("e-Gov law ID").references[0])
    assert ref["stated in"].value == "lexflow:source:egov-laws" and ref["retrieved"].value == "2026-10-22"
    assert ref["source URL"].value == f"https://laws.e-gov.go.jp/law/{GYO}"
    # every statement but lexflow's own bookkeeping carries the source reference
    for c in law.claims:
        if c.prop not in ("unit level", "sort key", "act identifier", "Wikidata item ID", "exact match"):
            assert c.references and any(p == "stated in" for p, _ in c.references[0]), c.prop
    # amended by: an item for the listed amending law (its revision's page in the reference), a number otherwise
    amended = _claims(law, "amended by")
    assert [c.value.value for c in amended] == [f"lexflow:unit:jpn:{AMENDER.lower()}"]
    q = dict(amended[0].qualifiers)
    assert q["point in time"].value == "2014-06-13" and q["effective date"].value == "2016-04-01"
    assert dict(amended[0].references[0])["source URL"].value == \
        f"https://laws.e-gov.go.jp/law/{GYO}/20160401_{AMENDER}"
    nums = _claims(law, "amending law number")
    assert [(c.value.value, c.value.lang) for c in nums] == [("平成十一年法律第百五十一号", "ja")]
    assert dict(nums[0].qualifiers)["point in time"].value == "1999-12-08"
    # the source and the maker are items of their own, with their Wikidata ids
    src = jpn["lexflow:source:egov-laws"]
    assert src.labels["ja"] == "e-Gov法令検索" and src.cls == "lexflow:class:database"
    assert _claims(src, "Wikidata item ID")[0].value.value == SC.SOURCES["egov-laws"]["wikidata"]
    diet = jpn["lexflow:agency:jpn:national_diet"]
    assert diet.label == "National Diet" and diet.labels["ja"] == "国会" and diet.cls == "lexflow:class:legislature"
    assert _claims(diet, "Wikidata item ID")[0].value.value == "Q202384"
    ja = jpn["lexflow:vocab:language:ja"]
    assert _claims(ja, "Wikidata item ID")[0].value.value == "Q5287"


def test_repealed_laws_from_the_list_with_repealed_by_and_repeals(jpn):
    old = jpn[f"lexflow:unit:jpn:{OLD.lower()}"]
    assert old.description.startswith("Repealed Japanese law") and old.labels["ja"] == "国税犯則取締法"
    assert "・廃止" in old.descriptions["ja"]
    assert _claims(old, "effective until")[0].value.value == "2018-04-01" and not _claims(old, "effective date")
    rb = _claims(old, "repealed by")
    assert [c.value.value for c in rb] == [f"lexflow:unit:jpn:{NEW.lower()}"]
    assert dict(rb[0].qualifiers)["effective date"].value == "2018-04-01"
    new = jpn[f"lexflow:unit:jpn:{NEW.lower()}"]
    assert [c.value.value for c in _claims(new, "repeals")] == [f"lexflow:unit:jpn:{OLD.lower()}"]
    code = jpn["lexflow:code:jpn"]
    assert "3 in force and 1 repealed or not yet in force" in code.description


def test_law_items_pass_the_lint(jpn):
    items = list(jpn.values())
    keys = {it.key for it in items}
    from datetime import date
    for k in (f"lexflow:unit:jpn:{GYO.lower()}", f"lexflow:unit:jpn:{OLD.lower()}", "lexflow:agency:jpn:national_diet",
              "lexflow:source:egov-laws"):
        assert lint.check_item(jpn[k], date(2026, 10, 22), keys) == [], k
    # an item with no label in any language is still held, and a future point in time is still caught
    bare = Item("lexflow:unit:jpn:x", "", "", [], None, [Claim("amended by", Value("item", f"lexflow:unit:jpn:{GYO.lower()}"),
                [("point in time", Value("time", "2027-01-01")), ("effective date", Value("time", "2027-01-01"))])], False)
    codes = sorted(f["code"] for f in lint.check_item(bare, date(2026, 10, 22), keys))
    assert codes == ["future-time", "label-empty"]


def test_push_writes_no_english_label_for_a_japanese_law(jpn):
    body = push.labels_body(jpn[f"lexflow:unit:jpn:{GYO.lower()}"])
    assert "en" not in body["labels"] and body["labels"]["ja"]["value"] == "行政手続法"
    assert body["descriptions"]["en"]["value"] == "Japanese law (Act No. 88 of 1993)"


# --------------------------------------------------------------------------- the licence rule
def test_no_provision_text_of_a_cc_by_jurisdiction(con):
    assert SC.provision_text_ok("jpn") and SC.provision_text_ok("va") and not SC.provision_text_ok("aus")
    assert not SC.provision_text_ok("aus-nsw") and SC.jurisdiction_of("lexflow:unit:aus:c2004a00467") == "aus"
    b = graph.Build(con, states=["jpn"], log=lambda *_: None)
    law = b.add("lexflow:unit:aus:c2004a00467", "Privacy Act 1988", "Law of Australia", None)
    assert b.claim(law, "law digest", graph.mono("An Act to make provision to protect privacy")) is None
    assert b.claim(law, "heading text", graph.mono("Privacy Act 1988")) is not None       # a title is no provision
    step = b.add("lexflow:step:aus.records:ask", "Ask", "Step", None)
    c = b.claim(step, "references", graph.item("lexflow:statute:aus:privacy-6"), [], [
        [("source section", graph.item("lexflow:statute:aus:privacy-6")), ("quoted text", graph.string("words"))]])
    assert [p for p, _ in c.references[0]] == ["source section"]
    c = b.claim(step, "references", graph.item("lexflow:statute:va:2.2-3704"), [], [
        [("source section", graph.item("lexflow:statute:va:2.2-3704")), ("quoted text", graph.string("words"))]])
    assert [p for p, _ in c.references[0]] == ["source section", "quoted text"]
    assert b.gaps.get("provision text withheld (source licence is not CC0-compatible)") == 2


# --------------------------------------------------------------------------- the single pass
def _wiki():
    return FakeSession(entities={
        **{pid: {"id": pid, "datatype": SC.EXISTING_DATATYPES[label], "labels": {"en": {"language": "en", "value": label}},
                 "descriptions": {}, "aliases": {}, "claims": {}} for label, pid in SC.EXISTING.items()},
        "Q10": entity("Q10", "statute or legal provision", "A statute or provision."),
        "Q21": entity("Q21", "jurisdiction", "A government.", {"P25": [key_claim("lexflow:class:jurisdiction")]}),
        "Q30": entity("Q30", "Japan", "Country (lexflow jurisdiction)", {"P25": [key_claim("lexflow:jurisdiction:jpn")]}),
    }, keys={"lexflow:class:jurisdiction": "Q21", "lexflow:jurisdiction:jpn": "Q30"})


def _laws():
    cls_ = Item("lexflow:class:statutory-unit", "statutory unit", "A unit.", [], None, [], False)
    agency_cls = Item("lexflow:class:government-agency", "government agency", "A body.", [], None, [], False)
    jur = Item("lexflow:jurisdiction:jpn", "Japan", "Country (lexflow jurisdiction)", [], "jurisdiction", [], True)
    diet = Item("lexflow:agency:jpn:national_diet", "National Diet", "The legislature of Japan (国会)", [],
                "lexflow:class:government-agency", [Claim("applies to jurisdiction", Value("item", jur.key))], False)

    def law(k, label, claims):
        return Item(f"lexflow:unit:jpn:{k}", "", f"Japanese law ({label})", [], cls_.key,
                    [Claim("applies to jurisdiction", Value("item", jur.key)),
                     Claim("legislated by", Value("item", diet.key))] + claims, False, labels={"ja": label})
    a = law("a", "A", [Claim("amended by", Value("item", "lexflow:unit:jpn:b"),
                             [("point in time", Value("time", "2014-06-13"))])])
    b = law("b", "B", [])
    old = law("old", "Old", [Claim("repealed by", Value("item", "lexflow:unit:jpn:z"))])
    z = law("z", "Z", [Claim("repeals", Value("item", "lexflow:unit:jpn:old"))])
    return [cls_, agency_cls, jur, diet, a, b, old, z]


def test_single_pass_creates_items_with_every_statement_once(con, tmp_path):
    wiki = _wiki()
    res = push.run(con, items=_laws(), api=api_for(wiki, dry_run=False), out_dir=tmp_path / "out", dry_run=False,
                   allow_held=True, single_pass=True, log=lambda *a: None)
    s = res["summary"]
    creates = [json.loads(p["data"]) for p in wiki.posts if p.get("new") == "item"]
    item_creates = sum(c.get("create", 0) for k, c in s["counts"]["1"].items() if k != "property")
    assert len(creates) == 7 == item_creates                       # every new item once (the jurisdiction exists)
    assert s["creates_full"] == 6                                  # the 2-cycle old <-> z costs one bare create
    plan = json.loads((tmp_path / "out" / push.PLAN_NAME).read_text(encoding="utf-8"))
    bare = [w["key"] for w in plan["writes"] if w["action"] == "create" and w["kind"] != "property" and not w.get("full")]
    assert bare == ["lexflow:unit:jpn:old"]
    item_updates = [p for p in wiki.posts if p.get("action") == "wbeditentity" and str(p.get("id", "")).startswith("Q")]
    assert {p["id"] for p in item_updates} <= {wiki_qid(wiki, "lexflow:unit:jpn:old"), "Q30"}
    assert wiki_qid(wiki, "lexflow:unit:jpn:old") in {p["id"] for p in item_updates}
    # a waited for b, and its create names b's id; nothing names an id it did not have
    a = next(c for c in creates if c["claims"][0]["mainsnak"]["datavalue"]["value"] == "lexflow:unit:jpn:a")
    pid = push.Resolver(con).pids["amended by"]
    vals = [st["mainsnak"]["datavalue"]["value"]["id"] for st in a["claims"]
            if st["mainsnak"]["property"] == pid]
    assert vals == [wiki_qid(wiki, "lexflow:unit:jpn:b")]
    assert "en" not in a["labels"] and a["labels"]["ja"]["value"] == "A"
    assert s["counts"]["2"]["unit"].get("skip-complete") == 3 and not s["failures_by_code"]
    # the content hash is recorded at the create, so a resumed run skips the complete items
    again = push.run(con, items=_laws(), api=api_for(wiki, dry_run=True), out_dir=tmp_path / "out2", dry_run=True,
                     allow_held=True, resume=True, single_pass=True, log=lambda *a: None)
    c1 = again["summary"]["counts"]["1"]
    assert sum(c.get("create", 0) for k, c in c1.items() if k != "property") == 0
    assert c1["unit"].get("skip-resume", 0) >= 3


def wiki_qid(wiki, key):
    for q, e in wiki.entities.items():
        for st in (e.get("claims") or {}).get("P25", []):
            if st["mainsnak"]["datavalue"]["value"] == key:
                return q
    return None


def test_two_passes_unchanged_without_the_flag(con, tmp_path):
    wiki = _wiki()
    res = push.run(con, items=_laws(), api=api_for(wiki, dry_run=False), out_dir=tmp_path / "out", dry_run=False,
                   allow_held=True, log=lambda *a: None)
    creates = [json.loads(p["data"]) for p in wiki.posts if p.get("new") == "item"]
    assert len(creates) == 7 and res["summary"]["creates_full"] == 0
    assert all(all(st["mainsnak"]["property"] in ("P25", "P5") for st in c["claims"]) for c in creates)
    assert res["summary"]["counts"]["2"]["unit"].get("clear") == 4


def test_single_pass_dry_run_plans_the_halving(con, tmp_path):
    res = push.run(con, items=_laws(), api=api_for(_wiki(), dry_run=True), out_dir=tmp_path / "out", dry_run=True,
                   allow_held=True, single_pass=True, log=lambda *a: None)
    s = res["summary"]
    item_creates = sum(c.get("create", 0) for k, c in s["counts"]["1"].items() if k != "property")
    assert item_creates == 7 and s["creates_full"] == 6 and s["single_pass"]
    item_updates = sum(n for k, c in s["counts"]["2"].items() if k != "property"
                       for a, n in c.items() if a in ("update", "clear"))
    assert item_updates == 2                                        # the bare one and the existing jurisdiction


# --------------------------------------------------------------------------- QuickStatements
def test_quickstatements_add_only_what_is_missing():
    laws = {GYO: {"title": "行政手続法", "law_num": "平成五年法律第八十八号", "promulgated": "1993-11-12",
                  "enforced": "2026-07-24", "revision_id": f"{GYO}_20260724_508AC0000000066", "in_force": True,
                  "url": f"https://laws.e-gov.go.jp/law/{GYO}"},
            AMENDER: {"title": "整備法", "law_num": "平成二十六年法律第六十九号", "promulgated": "2014-06-13",
                      "enforced": "2016-04-01", "revision_id": f"{AMENDER}_20160401_000000000000000", "in_force": True,
                      "url": f"https://laws.e-gov.go.jp/law/{AMENDER}"},
            OLD: {"title": "国税犯則取締法", "law_num": "明治三十三年法律第六十七号", "promulgated": "1900-03-17",
                  "enforced": None, "revision_id": None, "in_force": False, "url": f"https://laws.e-gov.go.jp/law/{OLD}"}}
    matches = {GYO: [{"qid": "Q4683484", "method": "P8610", "confident": 1}],
               AMENDER: [{"qid": "Q900", "method": "jawiki", "confident": 1}],
               OLD: [{"qid": "Q901", "method": "label", "confident": 0}]}
    snak = lambda pid, v: {"mainsnak": {"property": pid, "datavalue": {"value": v}}}       # noqa: E731
    ents = {"Q4683484": {"claims": {"P8610": [snak("P8610", GYO)], "P7589": [snak("P7589", {"time": "+1993-11-12T00:00:00Z"})]}},
            "Q900": {"claims": {}}}
    amendments = [{"law_key": GYO, "amending_key": AMENDER, "kind": "amended", "date": "2014-06-13",
                   "date_kind": "promulgated", "retrieved": "2026-10-22"},
                  {"law_key": GYO, "amending_key": None, "kind": "amended", "date": "1999-12-08",
                   "date_kind": "promulgated", "retrieved": "2026-10-22"}]
    out = WE.build_qs(laws, matches, ents, amendments, "2026-10-22")
    # the item that has P8610 and P7589 gets neither again; the label-only match gets nothing
    assert [ln.split("\t")[0] for ln in out["P8610"]] == ["Q900"] and [ln.split("\t")[0] for ln in out["P7589"]] == ["Q900"]
    assert not any("Q901" in ln for ls in out.values() for ln in ls)
    p8550 = next(ln for ln in out["P8550"] if ln.startswith("Q4683484"))
    assert p8550.split("\t")[:3] == ["Q4683484", "P8550", '"平成5年法律第88号"']
    assert p8550.split("\t")[3:9] == ["S854", f'"https://laws.e-gov.go.jp/law/{GYO}"', "S813",
                                      "+2026-10-22T00:00:00Z/11", "S248", WE.EGOV_QID]
    # effective date only for a law whose indexed revision is its original text
    assert [ln.split("\t")[:3] for ln in out["P7588"]] == [["Q900", "P7588", "+2016-04-01T00:00:00Z/11"]]
    assert all("\tP407\tQ5287\t" in ln for ln in out["P953"])
    # amended by: both ends confident, with the amending law's promulgation
    assert [ln.split("\t")[:5] for ln in out["P2567"]] == [["Q4683484", "P2567", "Q900", "P585",
                                                           "+2014-06-13T00:00:00Z/11"]]
    ents["Q4683484"]["claims"]["P2567"] = [snak("P2567", {"id": "Q900"})]
    assert WE.build_qs(laws, matches, ents, amendments, "2026-10-22")["P2567"] == []


def test_quickstatements_files_carry_a_header(tmp_path):
    counts = WE.write_qs({"P8610": ['Q1\tP8610\t"x"'], "P8550": [], "P7589": [], "P7588": [], "P953": [],
                          "P2567": []}, tmp_path, retrieved="2026-10-22", summary={"in_force": {"laws": 1, "confident": 1}})
    text = (tmp_path / "jpn-p8610.qs").read_text(encoding="utf-8").splitlines()
    assert counts["P8610"] == 1 and text[-1] == 'Q1\tP8610\t"x"'
    assert all(ln.startswith("#") for ln in text[:-1]) and "statements: 1 on 1 items" in text[1]


def test_reconcile_japan_ranks_identifiers_and_flags_conflicts():
    class Fake:
        def sparql(self, q):
            if "wdt:P8610 ?v" in q:
                return [{"item": "Q1", "v": GYO}]
            if "wdt:P8550" in q:
                return [{"item": "Q2", "v": "平成26年法律第69号"}, {"item": "Q3", "v": "平成26年法律第69号"}]
            if "ja.wikipedia.org" in q:
                return [{"item": "Q4", "t": "国税犯則取締法"}, {"item": "Q9", "t": "行政手続法"}]
            if "rdfs:label" in q:
                return []
            if "P279*" in q:
                return [{"item": q_} for q_ in ("Q1", "Q2", "Q3", "Q4", "Q9")]
            return []

        def entities(self, qids, props=None):
            return {"Q1": {"claims": {"P8610": [{"mainsnak": {"datavalue": {"value": GYO}}}]}},
                    "Q4": {"claims": {"P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q17"}}}}]}},
                    "Q9": {"claims": {}}}
    laws = {GYO: {"title": "行政手続法", "law_num": "平成五年法律第八十八号"},
            AMENDER: {"title": "整備法", "law_num": "平成二十六年法律第六十九号"},
            OLD: {"title": "国税犯則取締法", "law_num": "明治三十三年法律第六十七号"}}
    m = WE.reconcile_jpn(Fake(), laws, log=lambda *_: None)["matches"]
    best = {k: [x for x in v if x["confident"]] for k, v in m.items()}
    assert [x["qid"] for x in best[GYO]] == ["Q1"]               # P8610 outranks the jawiki article (Q9)
    assert best[AMENDER] == []                                    # two items carry the number: none is trusted
    assert [x["qid"] for x in best[OLD]] == ["Q4"] and best[OLD][0]["method"] == "jawiki"


def test_bot_flag_and_pause_are_the_operators_choice(con, tmp_path):
    wiki = _wiki()
    api = api_for(wiki, dry_run=False)
    push.run(con, items=_laws(), api=api, out_dir=tmp_path / "out", dry_run=False, allow_held=True, single_pass=True,
             pause=0.25, bot=True, log=lambda *a: None)
    edits = [p for p in wiki.posts if p.get("action") == "wbeditentity"]
    assert edits and all(p.get("bot") == 1 and p["maxlag"] == 5 for p in edits) and api.pause == 0.25
    from lexflow.store import db
    wiki2, con2 = _wiki(), db.connect(tmp_path / "fresh.db")                 # a fresh store for a fresh wiki
    push.run(con2, items=_laws(), api=api_for(wiki2, dry_run=False), out_dir=tmp_path / "out2", dry_run=False,
             allow_held=True, log=lambda *a: None)
    con2.close()
    assert not any("bot" in p for p in wiki2.posts if p.get("action") == "wbeditentity")


def test_a_lint_of_some_states_does_not_clear_a_push_of_others(con, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / push.LINT_NAME).write_text(json.dumps({"held": [], "scope": {"states": ["jpn"]}}), encoding="utf-8")
    with pytest.raises(push.HeldError, match="covers jpn only"):
        push.run(con, items=_laws(), api=api_for(_wiki(), dry_run=False), out_dir=out, dry_run=False,
                 log=lambda *a: None)                                       # every state: not linted
    res = push.run(con, items=_laws(), api=api_for(_wiki(), dry_run=False), out_dir=out, dry_run=False,
                   states=["jpn"], log=lambda *a: None)                     # the linted scope: allowed
    assert not res["summary"]["failures_by_code"]


def test_an_amendment_with_no_number_is_left_out(con, jpn):
    """e-Gov records a few revisions with no amending law number: no empty statement (the wiki refuses the whole
    item for one), a gap instead."""
    con.execute("INSERT INTO law_amendments(jurisdiction, law_key, amending_key, amending_num, date, kind, source) "
                "VALUES ('jpn', ?, NULL, '', '2022-06-17', 'amended', 'egov-bulk-revision')", (GYO,))
    said = []
    items = {it.key: it for it in graph.build(con, states=["jpn"], drafts=False, log=said.append)}
    law = items[f"lexflow:unit:jpn:{GYO.lower()}"]
    assert [c.value.value for c in _claims(law, "amending law number")] == ["平成十一年法律第百五十一号"]
    assert any("amendments recorded with no amending law number" in m for m in said)
