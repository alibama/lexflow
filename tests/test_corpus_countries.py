"""The country adapters (lexflow/corpus/countries/): the registry and its keys (ISO alpha-3, never a US postal
code), the two prototypes turning their sample law (fixtures/corpus/<key>/sample.json, one document each, fetched
read-only on 19 October 2026) into index rows in the US shape, Japan's bulk-XML parser (an inline law, and a sample
of the official zip when it is on disk), the CJK search index (trigram, with Japanese queries), the routing of a
country key to ``statutes_<key>.sqlite``, the wiki graph's law items, and the stubs that carry verified source
metadata and refuse to fetch with a reason.  No network."""
import json
import re

import pytest

from lexflow import config
from lexflow.ask import index as I
from lexflow.corpus import countries as C
from lexflow.corpus.countries import base
from lexflow.corpus.countries import japan as J
from lexflow.municipal import states as S
from lexflow.municipal import statutes

STATUTE_COLUMNS = set(statutes.COLUMNS)
ZIP = config.RAW_DIR / "countries" / "jpn" / "all_xml.zip"


def _eli_cc(code):
    a = C.get(code)
    return a.eli_jurisdiction or a.code


# ---------------------------------------------------------------------- registry and keys
NATIONAL = [c for c in C.CODES if not getattr(C.get(c), "parent", "")]


KNOWN_QIDS = {"per": "Q419", "chl": "Q298", "aus": "Q408", "rou": "Q218", "gha": "Q117", "jpn": "Q17", "bra": "Q155"}


def test_registry_and_jurisdiction_keys():
    # the national keys follow the registry (a new country is one JURISDICTIONS entry and one adapter); the
    # countries known when this was written keep their Wikidata items
    assert NATIONAL == [j["code"] for j in C.JURISDICTIONS if not j.get("parent")]
    assert set(KNOWN_QIDS) <= set(NATIONAL)
    assert {c: C.WIKIDATA[c] for c in KNOWN_QIDS} == KNOWN_QIDS
    assert all(re.fullmatch(r"Q[1-9]\d*", C.WIKIDATA[c]) for c in NATIONAL)
    assert [j["code"] for j in C.JURISDICTIONS] == C.CODES
    for j in C.JURISDICTIONS:
        assert j["wikidata"] == C.WIKIDATA[j["code"]] and j["language"] and j["code_label"]
        assert j["website"].startswith("https://")
        if not j.get("parent"):
            assert C.ISO3[j["iso2"]] == j["code"]
    for code in C.CODES:
        parent = getattr(C.get(code), "parent", "")
        national = code.split("-")[0]
        assert len(national) == 3 and national.isalpha() and national.islower()
        assert not parent or (code.startswith(parent + "-") and parent in NATIONAL)     # aus-nsw under aus
        assert code not in S.NAME                       # alpha-3: never a state's postal code
        a = C.get(code)
        assert a.sources and all(s.licence and s.verified and s.url.startswith("https://") for s in a.sources)
        assert a.status in ("prototype", "stub")
    # alpha-2 codes are aliases (cl, co, de, in ... would collide with states as keys)
    assert C.get("jp") is C.get("jpn") is C.get("JPN") and C.key_of("CL") == "chl"
    with pytest.raises(ValueError):
        C.get("zz")


def test_the_states_registry_lists_japan_beside_the_52_states():
    from lexflow.publish import schema as SC
    assert len(S.STATES) == 52 and "jpn" not in S.CODES and "jpn" not in S.NAME   # the US lists are unchanged
    jp = S.COUNTRY["jpn"]
    assert jp["name"] == "Japan" and jp["wikidata"] == "Q17" and jp["languages"] == ["ja"] and jp["iso2"] == "jp"
    assert jp["code_label"] == {"ja": "日本の法令", "en": "Laws of Japan"}
    assert jp["website"] == "https://laws.e-gov.go.jp/"
    assert S.normalise_any("JPN") == S.normalise_any("Japan") == S.normalise_any("jp") == "jpn"
    assert S.normalise_any("VA") == "va" and S.normalise_any("co") == "co"          # Colorado, not Colombia
    assert S.is_country("jpn") and not S.is_country("co") and S.name_of("jpn") == "Japan"
    assert S.parse_jurisdictions("va,jpn") == ["va", "jpn"]
    with pytest.raises(ValueError):
        S.normalise_any("xx")
    assert SC.is_country_key("jpn") and not SC.is_country_key("va")
    assert SC.key_for("code", "jpn") == "lexflow:code:jpn"
    assert SC.key_for("unit", "jpn", "STATE_JPN_405AC0000000088") == "lexflow:unit:jpn:405ac0000000088"
    assert SC.key_for("jurisdiction", "jpn") == "lexflow:jurisdiction:jpn"


@pytest.mark.parametrize("code", [c for c in C.CODES if C.get(c).status == "stub"])
def test_stubs_refuse_with_a_reason(code):
    a = C.get(code)
    assert a.status == "stub" and a.note
    with pytest.raises(NotImplementedError, match=a.name):
        a.fetch_document("1")
    with pytest.raises(NotImplementedError):
        a.fetch_list()
    assert not C.have(code)


# ---------------------------------------------------------------------- the two prototypes' fixtures
def _rows(code):
    doc = C.load_document(code)
    assert doc is not None and doc.fetched == "2026-10-19"
    return doc, C.rows_for(code, doc)


def test_rows_have_the_us_shape():
    for code in ("chl", "jpn"):
        a = C.get(code)
        doc, rows = _rows(code)
        fx = json.loads(C.fixture_path(code).read_text(encoding="utf-8"))
        assert fx["row_count"] == len(rows) and fx["licence"] == doc.licence and fx["attribution"]
        for r in rows:
            assert STATUTE_COLUMNS <= set(r), r.keys()
            assert set(base.EXTRA) <= set(r)
            assert r["act_id"].startswith(f"STATE_{a.code.upper()}_")
            assert r["display_path"].split(" / ")[0] and r["source_url"].startswith("https://")
            assert r["text"] and r["word_count"] > 0 and r["act_status"] == "in_force"
            assert r["eli"].startswith(f"{base.ELI_BASE}/{_eli_cc(code)}/") and "@" in r["eli"]
            assert r["country"] == a.code and r["language"] == a.languages[0]
        assert len({r["citation"] for r in rows}) == len(rows)
        assert len({r["eli"] for r in rows}) == len(rows)
        assert len({r["act_id"] for r in rows}) == len(rows)


def test_chile_sample_law():
    a = C.get("chl")
    cc, el = a.code.upper(), _eli_cc("chl")
    doc, rows = _rows("chl")
    assert doc.kind == "Ley" and doc.number == "19.628" and doc.native_id == "141599"
    assert doc.title == "SOBRE PROTECCION DE LA VIDA PRIVADA" and doc.version_date == "2022-11-10"
    assert doc.url == "https://www.bcn.cl/leychile/navegar?idNorma=141599"
    assert len(rows) == 27                                              # 24 articles + 3 transitory
    first = rows[0]
    assert first["citation"] == "Ley 19.628, art. 1" and first["section_number"] == "1"
    assert first["display_path"] == "Ley 19.628 / Título Preliminar / Artículo 1"
    assert first["act_id"] == f"STATE_{cc}_LEY19628_TPRELIMINAR_A1"
    assert first["eli"] == f"{base.ELI_BASE}/{el}/ley/1999/19628/art_1/es@1999-08-28"
    assert first["native_id"] == "141599#8642681" and first["level"] == "Artículo"
    assert first["text"].startswith("El tratamiento de los datos de carácter personal")
    art4 = next(r for r in rows if r["citation"] == "Ley 19.628, art. 4")
    assert art4["display_path"] == "Ley 19.628 / Título I / Artículo 4"
    assert art4["chapter_name"] == "De la utilización de datos personales"
    assert art4["act_id"] == f"STATE_{cc}_LEY19628_TI_A4"
    art17 = next(r for r in rows if r["citation"] == "Ley 19.628, art. 17")
    assert art17["effective_from"] == "2022-11-10"                        # the article's own version date
    trans = [r for r in rows if "transitorio" in r["citation"]]
    assert [r["citation"] for r in trans] == [f"Ley 19.628, art. {n} transitorio" for n in (1, 2, 3)]
    assert trans[0]["display_path"] == "Ley 19.628 / Disposiciones transitorias / Artículo 1 transitorio"
    assert trans[0]["act_id"] == f"STATE_{cc}_LEY19628_DT_A1T"
    # the line wrapping of the source is undone; a verbatim quote from the article survives
    assert "\n" not in first["text"] and "organismos públicos o por particulares" in first["text"]


def test_japan_sample_law():
    doc, rows = _rows("jpn")
    assert doc.country == "jpn" and C.fixture_path("jpn").parent.name == "jpn"
    assert doc.kind == "法律" and doc.title == "行政手続法" and doc.native_id == "405AC0000000088"
    assert doc.number == "平成五年法律第八十八号" and doc.eli_number == "88" and doc.year == "1993"
    assert doc.url == "https://laws.e-gov.go.jp/law/405AC0000000088"
    assert len(rows) == 76                                              # 48 main articles + 附則
    first = rows[0]
    assert first["citation"] == "行政手続法第一条" and first["section_title"] == "目的等"
    assert first["display_path"] == "行政手続法 / 第一章　総則 / 第一条"
    assert first["chapter_name"] == "総則" and first["act_id"] == "STATE_JPN_405AC0000000088_C1_A1"
    assert first["eli"] == f"{base.ELI_BASE}/jp/act/1993/88/art_1/ja@2026-07-24"      # ELI keeps alpha-2
    assert first["text"].startswith("この法律は、処分、行政指導及び届出に関する手続")
    art13 = next(r for r in rows if r["citation"] == "行政手続法第十三条")
    assert art13["display_path"] == "行政手続法 / 第三章　不利益処分 / 第一節　通則 / 第十三条"
    assert art13["act_id"] == "STATE_JPN_405AC0000000088_C3_S1_A13"
    assert "\n　一　" in art13["text"] and "\n２　" in art13["text"]          # items and paragraphs kept, one per line
    art2 = next(r for r in rows if r["citation"] == "行政手続法第二条")
    assert "一　法令" in art2["text"]
    supp = [r for r in rows if r["level"] == "附則" or "附則" in r["display_path"]]
    assert supp and supp[0]["citation"] == "行政手続法附則"
    assert supp[0]["eli"].endswith("/suppl_1/ja@2026-07-24")
    with_articles = [r for r in supp if r["level"] == "条"]
    assert with_articles[0]["citation"].startswith("行政手続法附則（") and "第" in with_articles[0]["citation"]
    assert with_articles[0]["eli"].split("/")[-2].startswith("suppl_")


def _genko():
    return {"law_info": {"law_type": "Act", "law_id": "354AC0000000043", "law_num": "昭和五十四年法律第四十三号",
                         "law_num_num": "043", "promulgation_date": "1979-06-12"},
            "revision_info": {"law_title": "元号法", "amendment_enforcement_date": "1979-06-12",
                              "current_revision_status": "CurrentEnforced"},
            "law_full_text": {"tag": "Law", "attr": {}, "children": [{"tag": "LawBody", "attr": {}, "children": [
                {"tag": "LawTitle", "attr": {}, "children": ["元号法"]},
                {"tag": "MainProvision", "attr": {}, "children": [
                    {"tag": "Paragraph", "attr": {"Num": "1"}, "children": [
                        {"tag": "ParagraphNum", "attr": {}, "children": ["１"]},
                        {"tag": "ParagraphSentence", "attr": {}, "children": [
                            {"tag": "Sentence", "attr": {}, "children": ["元号は、政令で定める。"]}]}]},
                    {"tag": "Paragraph", "attr": {"Num": "2"}, "children": [
                        {"tag": "ParagraphNum", "attr": {}, "children": ["２"]},
                        {"tag": "ParagraphSentence", "attr": {}, "children": [
                            {"tag": "Sentence", "attr": {}, "children": ["元号は、皇位の継承があった場合に限り改める。"]}]}]}]}]}]}}


def test_japan_law_without_articles():
    """元号法-shaped laws have paragraphs straight under the main provision: one row for 本則."""
    jp = C.get("jpn")
    doc = jp.parse(json.dumps(_genko()), "354AC0000000043")
    rows = jp.to_rows(doc)
    assert len(rows) == 1 and rows[0]["citation"] == "元号法" and rows[0]["level"] == "本則"
    assert rows[0]["text"] == "１　元号は、政令で定める。\n２　元号は、皇位の継承があった場合に限り改める。"
    assert rows[0]["eli"] == f"{base.ELI_BASE}/jp/act/1979/43/main/ja@1979-06-12"
    assert rows[0]["act_id"] == "STATE_JPN_354AC0000000043_MAIN"


# ---------------------------------------------------------------------- the bulk XML
XML = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<Law Lang="ja" Era="Reiwa" Year="02" Num="011" PromulgateMonth="03" PromulgateDay="31" LawType="MinisterialOrdinance"><LawNum>令和二年厚生労働省令第十一号</LawNum><LawBody><LawTitle Kana="てすとききそく" Abbrev="試規">試験規則</LawTitle>
    <MainProvision>
      <Chapter Num="1">
        <ChapterTitle>第一章　総則</ChapterTitle>
        <Article Num="1">
          <ArticleCaption>（目的）</ArticleCaption>
          <ArticleTitle>第一条</ArticleTitle>
          <Paragraph Num="1">
            <ParagraphNum/>
            <ParagraphSentence>
              <Sentence Num="1">この省令は、<Ruby>聴聞<Rt>ちょうもん</Rt></Ruby>の手続を定める。</Sentence>
            </ParagraphSentence>
            <Item Num="1">
              <ItemTitle>一</ItemTitle>
              <ItemSentence><Sentence Num="1">申請書</Sentence></ItemSentence>
            </Item>
          </Paragraph>
        </Article>
        <Article Num="2_2">
          <ArticleTitle>第二条の二</ArticleTitle>
          <Paragraph Num="1"><ParagraphNum/><ParagraphSentence><Sentence>行政庁は、不利益処分をしようとするときは、聴聞を行う。</Sentence></ParagraphSentence></Paragraph>
        </Article>
      </Chapter>
    </MainProvision>
    <SupplProvision>
      <SupplProvisionLabel>附　則</SupplProvisionLabel>
      <Paragraph Num="1"><ParagraphNum/><ParagraphSentence><Sentence>この省令は、公布の日から施行する。</Sentence></ParagraphSentence></Paragraph>
    </SupplProvision>
  </LawBody>
</Law>"""


def test_japan_bulk_xml_parses_like_the_api_tree():
    jp = C.get("jpn")
    tree = J.xml_tree(XML.encode("utf-8"))

    def first(node, tag):
        if isinstance(node, dict):
            if node["tag"] == tag:
                return node
            for ch in node["children"]:
                hit = first(ch, tag)
                if hit:
                    return hit
        return None
    sent = first(tree, "Sentence")
    assert sent["children"][0] == "この省令は、" and sent["children"][1]["tag"] == "Ruby"   # mixed content kept
    assert not [c for c in first(tree, "MainProvision")["children"] if isinstance(c, str)]   # indentation dropped
    doc = jp.parse_xml(XML.encode("utf-8"), {"category": "厚生", "promulgation_date": None},
                       "502M60000100011_20200401_000000000000000")
    assert doc.title == "試験規則" and doc.number == "令和二年厚生労働省令第十一号" and doc.promulgated == "2020-03-31"
    assert doc.version_date == "2020-04-01" and doc.kind == "府省令" and doc.extra["category"] == "厚生"
    assert doc.eli_number == "502M60000100011"          # an ordinance's number is unique only per ministry
    rows = jp.to_rows(doc)
    assert [r["citation"] for r in rows] == ["試験規則第一条", "試験規則第二条の二", "試験規則附則"]
    a1, a22, sp = rows
    assert a1["text"] == "この省令は、聴聞ちょうもんの手続を定める。\n　一　申請書"
    assert a1["source_url"] == "https://laws.e-gov.go.jp/law/502M60000100011#Mp-Ch_1-At_1"
    assert a22["act_id"] == "STATE_JPN_502M60000100011_C1_A2-2" and a22["source_url"].endswith("#Mp-Ch_1-At_2_2")
    assert a22["eli"] == f"{base.ELI_BASE}/jp/ministerialordinance/2020/502m60000100011/art_2-2/ja@2020-04-01"
    assert sp["level"] == "附則" and sp["text"] == "附　則\nこの省令は、公布の日から施行する。"   # label kept, as the prototype
    assert sp["source_url"] == "https://laws.e-gov.go.jp/law/502M60000100011"      # 附則 anchors are not stable
    assert J.law_number_en("令和二年厚生労働省令第十一号", "MinisterialOrdinance") == "Ministerial Ordinance No. 11 of 2020"
    assert J.law_number_en("平成五年法律第八十八号", "Act") == "Act No. 88 of 1993"
    assert J.law_number_en("明治五年太政官布告第三百三十七号", "CabinetOrder") == "Dajokan Proclamation No. 337 of 1872"
    assert J.kanji_number("百二十七") == 127 and J.kanji_number("二〇") == 20 and J.era_year("令和元年政令第一号") == "2019"


@pytest.mark.skipif(not ZIP.exists(), reason="the e-Gov bulk zip is not downloaded")
def test_japan_bulk_zip_sample():
    """A sample of the official zip: 行政手続法 gives the fixture's rows (plus article anchors), 元号法 the one 本則
    row, 日本国憲法 its 103 articles; the revision chosen is the one in force."""
    jp = C.get("jpn")
    docs = {d.native_id: d for d in J.iter_documents(ZIP, only={"405AC0000000088", "354AC0000000043",
                                                                "321CONSTITUTION"}, log=lambda *_: None)}
    fx = jp.to_rows(C.load_document("jpn"))
    got = jp.to_rows(docs["405AC0000000088"])
    assert len(got) >= len(fx) and [r["citation"] for r in got[:48]] == [r["citation"] for r in fx[:48]]
    if docs["405AC0000000088"].version_date == "2026-07-24":           # the fixture's version: identical rows
        assert [{k: v for k, v in r.items() if k != "source_url"} for r in got] == \
               [{k: v for k, v in r.items() if k != "source_url"} for r in fx]
    assert got[12]["source_url"].endswith("#Mp-Ch_3-Se_1-At_13")
    genko = jp.to_rows(docs["354AC0000000043"])
    assert genko[0]["level"] == "本則" and genko[0]["text"].startswith("１　元号は、政令で定める。")
    kenpo = [r for r in jp.to_rows(docs["321CONSTITUTION"]) if r["level"] == "条"]
    assert len(kenpo) == 103 and kenpo[0]["citation"] == "日本国憲法第一条"
    for d in docs.values():
        assert d.status == "in_force" and d.version_date <= jp.today()


# ---------------------------------------------------------------------- the index: trigram and Japanese queries
@pytest.fixture()
def jp_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(C, "DIR", tmp_path / "raw" / "countries")     # no bulk zip: the fixtures
    I._STAMPS.clear(), I._READY.clear()
    return tmp_path


def test_phrase_and_match_take_any_script():
    for term in ("public records", "and", "driver's license", "§ 2.2-3704", "I-95"):      # English: as before
        import re
        words = re.findall(r"[A-Za-z0-9]+", term)
        assert I.phrase(term) == (f'"{" ".join(words)}"' if words else None)
    assert I.phrase("聴聞") == '"聴聞"' and I.phrase("不利益処分の聴聞、") == '"不利益処分の聴聞"'
    assert I.phrase("行政 手続") == '"行政手続"' and I.phrase("utilización") == '"utilización"'
    assert I.phrase("NPO 法人") == '"NPO 法人"' and I.phrase("、。") is None
    assert I.match([["聴聞", "意見陳述"], ["不利益処分"]]) == '("聴聞" OR "意見陳述") AND ("不利益処分")'


def test_index_builds_from_the_fixture(jp_index):
    for code, n in (("chl", 27), ("jpn", 76)):
        out = I.build(code, log=lambda *_: None, corpus=C.CORPUS)
        assert out["sections"] == n and I.ready(code, corpus=C.CORPUS)
    assert I.tokenizer_of("jpn", corpus=C.CORPUS) == "trigram"
    assert I.tokenizer_of("chl", corpus=C.CORPUS) == I.TOKENIZE                     # Spanish: the statutes' own
    hit = I.lookup("chl", "Ley 19.628, art. 4", with_text=True, corpus=C.CORPUS)
    assert hit and hit[0]["path"] == "Ley 19.628 / Título I / Artículo 4" and hit[0]["kind"] == "Ley"
    assert hit[0]["text"].startswith("El tratamiento de los datos personales sólo puede efectuarse")
    by_eli = I.lookup("chl", f"{base.ELI_BASE}/{_eli_cc('chl')}/ley/1999/19628/art_4", corpus=C.CORPUS)
    assert by_eli and by_eli[0]["citation"] == "Ley 19.628, art. 4"
    found = I.search("chl", I.match([["datos personales"], ["consentimiento"]]), corpus=C.CORPUS)
    assert found and all(r["country"] == C.get("chl").code for r in found)
    jp = I.lookup("jpn", "行政手続法第十三条", corpus=C.CORPUS)
    assert jp and jp[0]["path"].endswith("第十三条") and jp[0]["language"] == "ja"
    # Arabic numerals, a space, the ELI work IRI: the same article
    for ref in ("行政手続法第13条", "行政手続法 第十三条", f"{base.ELI_BASE}/jp/act/1993/88/art_13"):
        assert [r["citation"] for r in I.lookup("jpn", ref, corpus=C.CORPUS)][:1] == ["行政手続法第十三条"], ref


def test_japanese_queries_on_the_trigram_index(jp_index):
    I.build("jpn", log=lambda *_: None, corpus=C.CORPUS)
    con = I.connect("jpn", C.CORPUS)
    try:
        text = {r["citation"]: r["text"] for r in con.execute("SELECT s.citation, b.text FROM sec s JOIN body b ON b.id=s.id")}
    finally:
        con.close()
    for term in ("聴聞", "不利益処分", "行政手続", "弁明の機会"):
        expr = I.match([[term]])
        hits = I.search("jpn", expr, limit=200, corpus=C.CORPUS)
        # every row holding the term in its text is found (the path holds the law's name, so 行政手続 is in every row)
        want = {c for c, t in text.items() if term in t}
        assert want <= {h["citation"] for h in hits}, term
        assert I.count("jpn", expr, corpus=C.CORPUS) == len(hits)
    assert I.count("jpn", I.match([["行政手続"]]), corpus=C.CORPUS) == 76
    best = I.search("jpn", I.match([["聴聞"]], columns="title"), corpus=C.CORPUS)       # two characters, headings only
    assert best and all("聴聞" in h["title"] for h in best)
    both = I.search("jpn", I.match([["聴聞"], ["不利益処分"]], "and"), corpus=C.CORPUS)
    assert both and all("聴聞" in text[h["citation"]] + h["title"] + h["path"] for h in both)   # 第二節　聴聞 in the path
    assert not I.search("jpn", I.match([["存在しない語句"]]), corpus=C.CORPUS)
    assert I.count("jpn", '""', corpus=C.CORPUS) == 0


def test_a_country_key_is_a_jurisdiction_of_the_statutes_corpus(jp_index):
    assert I.path("jpn").name == "statutes_jpn.sqlite" and I.is_country("jpn") and not I.is_country("co")
    assert I._source("statutes", "jpn") is C and I._source("statutes", "va") is statutes
    assert I.have("jpn") and not I.have("zz")
    out = I.build("jpn", log=lambda *_: None)                         # the fixture, as data/index/statutes_jpn
    assert out["sections"] == 76 and I.ready("jpn") and I.path("jpn").exists()
    hits = I.search("jpn", I.match([["聴聞"], ["主宰"]], "and"))
    assert hits and hits[0]["citation"].startswith("行政手続法第")
    laws = C.laws("jpn")
    assert len(laws) == 1 and laws[0]["law_id"] == "405AC0000000088" and laws[0]["title"] == "行政手続法"
    assert laws[0]["number_en"] == "Act No. 88 of 1993" and laws[0]["articles"] == 48 and laws[0]["rows"] == 76


def test_ask_a_japanese_question_and_get_quotes(jp_index, con):
    from lexflow.ask import pipeline as AP
    from lexflow.ask import plan as PL
    p = PL.plan("行政手続法の聴聞の主宰者は誰ですか")
    assert [g[0] for g in p.groups] == ["行政手続法", "聴聞", "主宰者"] and p.source == "rules-cjk"
    assert PL.plan("不利益処分の手続はどうなっていますか").kind == "process"
    assert AP.resolve_targets(con, ["jpn", "JP"]) == {"jpn": []}
    I.build("jpn", log=lambda *_: None)
    row = AP.answer_state(con, "jp_hearing", p, "jpn", emb=None, log=lambda *_: None)
    ans = json.loads(row["answer"])
    assert row["status"] in ("answered", "partial") and ans["quotes"]
    chosen = json.loads(row["sections"])["chosen"]
    assert chosen and chosen[0]["citation"].startswith("行政手続法第")
    con2 = I.connect("jpn")
    try:
        body = "\n".join(t for (t,) in con2.execute("SELECT text FROM body"))
    finally:
        con2.close()
    assert all(q["text"] in body for q in ans["quotes"])                 # every quote is the law's own characters
    assert any("主宰" in q["text"] for q in ans["quotes"])
    assert json.loads(row["metrics"])["quote_misses"] == 0
    assert "e-Gov Law Search" in ans["markdown"] and "§ 行政手続法" not in ans["markdown"]


# ---------------------------------------------------------------------- the wiki graph
def test_the_graph_emits_the_code_and_one_item_per_law(jp_index, con):
    from lexflow.publish import graph, push
    from lexflow.publish import schema as SC
    I.build("jpn", log=lambda *_: None)
    items = graph.build(con, states=["jpn"], drafts=False, log=lambda *_: None)
    by = {it.key: it for it in items}
    jur, code = by["lexflow:jurisdiction:jpn"], by["lexflow:code:jpn"]
    assert jur.label == "Japan" and jur.labels == {"ja": "日本"}
    assert code.label == "Laws of Japan" and code.labels == {"ja": "日本の法令"} and code.cls == "lexflow:class:legal-code"
    law = by["lexflow:unit:jpn:405ac0000000088"]
    # no official English title yet: no English label (never a romanisation), an English description instead
    # (docs/design/wikidata-laws.md §2)
    assert law.label == "" and law.labels["ja"] == "行政手続法" and law.cls == "lexflow:class:statutory-unit"
    assert law.description == "Japanese law (Act No. 88 of 1993)"
    assert "Act No. 88 of 1993" in law.aliases and "平成五年法律第八十八号" in law.lang_aliases["ja"]
    claims = {(c.prop, c.value.kind): c.value for c in law.claims}
    assert claims[("unit level", "item")].value == "lexflow:vocab:unit-level:act"
    assert claims[("part of", "item")].value == "lexflow:code:jpn"
    assert claims[("applies to jurisdiction", "item")].value == "lexflow:jurisdiction:jpn"
    assert claims[("act identifier", "external-id")].value == "405AC0000000088"
    assert claims[("official text", "url")].value == "https://laws.e-gov.go.jp/law/405AC0000000088"
    h = claims[("heading text", "monolingual")]
    assert (h.value, h.lang) == ("行政手続法", "ja")
    n = claims[("law number", "monolingual")]
    assert (n.value, n.lang) == ("平成五年法律第八十八号", "ja")
    assert claims[("effective date", "time")].value == "2026-07-24"
    assert claims[("promulgation date", "time")].value == "1993-11-12"
    # one item per law, never one per article; no chapter units
    assert not [k for k in by if k.startswith("lexflow:statute:jpn:") or k.startswith("lexflow:unit:jpn:405ac0000000088-")]
    body = push.labels_body(law)
    assert body["labels"]["ja"] == {"language": "ja", "value": "行政手続法"} and body["descriptions"]["ja"]["value"]
    assert {a["value"] for a in body["aliases"]["ja"]} >= {"平成五年法律第八十八号"}
    # English-only items keep the digest they were pushed with
    import hashlib
    plain = graph.Item("lexflow:vocab:topic:taxes", "taxes", "Taxes.", [], None, [], True)
    assert set(push.labels_body(plain)["labels"]) == {"en"}
    legacy = {"label": "taxes", "description": "Taxes.", "aliases": [], "cls": None, "claims": []}
    assert push.content_hash(plain) == hashlib.sha256(json.dumps(legacy, sort_keys=True, ensure_ascii=False)
                                                      .encode("utf-8")).hexdigest()[:32]
    assert SC.PROP_BY_LABEL["law number"].datatype == "monolingualtext"
    assert SC.PROP_BY_LABEL["quoted text in language"].datatype == "monolingualtext"
    assert "lexflow:vocab:unit-level:supplementary-provision" in SC.VOCAB_BY_KEY
