"""The country adapters (lexflow/corpus/countries/): the two prototypes turn their sample law (fixtures/corpus/
<cc>/sample.json, one document each, fetched read-only on 19 October 2026) into index rows in the US shape, the
index builds from them and finds a row by citation and by ELI work IRI, and the stubs carry verified source
metadata and refuse to fetch with a reason.  No network."""
import json

import pytest

from lexflow.ask import index as I
from lexflow.corpus import countries as C
from lexflow.corpus.countries import base
from lexflow.municipal import statutes

STATUTE_COLUMNS = set(statutes.COLUMNS)


def test_registry_and_jurisdiction_proposal():
    assert C.CODES == ["pe", "cl", "au", "ro", "gh", "jp"]
    assert C.WIKIDATA == {"pe": "Q419", "cl": "Q298", "au": "Q408", "ro": "Q218", "gh": "Q117", "jp": "Q17"}
    assert [j["code"] for j in C.JURISDICTIONS] == C.CODES
    for j in C.JURISDICTIONS:
        assert j["wikidata"] == C.WIKIDATA[j["code"]] and j["language"] and j["code_label"]
    for code in C.CODES:
        a = C.get(code)
        assert a.sources and all(s.licence and s.verified and s.url.startswith("https://") for s in a.sources)
        assert a.status in ("prototype", "stub")
    with pytest.raises(ValueError):
        C.get("zz")


@pytest.mark.parametrize("code", ["pe", "au", "ro", "gh"])
def test_stubs_refuse_with_a_reason(code):
    a = C.get(code)
    assert a.status == "stub" and a.note
    with pytest.raises(NotImplementedError, match=a.name):
        a.fetch_document("1")
    with pytest.raises(NotImplementedError):
        a.fetch_list()
    assert not C.have(code)


def _rows(code):
    doc = C.load_document(code)
    assert doc is not None and doc.fetched == "2026-10-19"
    return doc, C.rows_for(code, doc)


def test_rows_have_the_us_shape():
    for code in ("cl", "jp"):
        doc, rows = _rows(code)
        fx = json.loads(C.fixture_path(code).read_text(encoding="utf-8"))
        assert fx["row_count"] == len(rows) and fx["licence"] == doc.licence and fx["attribution"]
        for r in rows:
            assert STATUTE_COLUMNS <= set(r), r.keys()
            assert set(base.EXTRA) <= set(r)
            assert r["act_id"].startswith(f"STATE_{code.upper()}_")
            assert r["display_path"].split(" / ")[0] and r["source_url"].startswith("https://")
            assert r["text"] and r["word_count"] > 0 and r["act_status"] == "in_force"
            assert r["eli"].startswith(f"{base.ELI_BASE}/{code}/") and "@" in r["eli"]
            assert r["country"] == code and r["language"] == C.get(code).languages[0]
        assert len({r["citation"] for r in rows}) == len(rows)
        assert len({r["eli"] for r in rows}) == len(rows)
        assert len({r["act_id"] for r in rows}) == len(rows)


def test_chile_sample_law():
    doc, rows = _rows("cl")
    assert doc.kind == "Ley" and doc.number == "19.628" and doc.native_id == "141599"
    assert doc.title == "SOBRE PROTECCION DE LA VIDA PRIVADA" and doc.version_date == "2022-11-10"
    assert doc.url == "https://www.bcn.cl/leychile/navegar?idNorma=141599"
    assert len(rows) == 27                                              # 24 articles + 3 transitory
    first = rows[0]
    assert first["citation"] == "Ley 19.628, art. 1" and first["section_number"] == "1"
    assert first["display_path"] == "Ley 19.628 / Título Preliminar / Artículo 1"
    assert first["act_id"] == "STATE_CL_LEY19628_TPRELIMINAR_A1"
    assert first["eli"] == f"{base.ELI_BASE}/cl/ley/1999/19628/art_1/es@1999-08-28"
    assert first["native_id"] == "141599#8642681" and first["level"] == "Artículo"
    assert first["text"].startswith("El tratamiento de los datos de carácter personal")
    art4 = next(r for r in rows if r["citation"] == "Ley 19.628, art. 4")
    assert art4["display_path"] == "Ley 19.628 / Título I / Artículo 4"
    assert art4["chapter_name"] == "De la utilización de datos personales"
    assert art4["act_id"] == "STATE_CL_LEY19628_TI_A4"
    art17 = next(r for r in rows if r["citation"] == "Ley 19.628, art. 17")
    assert art17["effective_from"] == "2022-11-10"                        # the article's own version date
    trans = [r for r in rows if "transitorio" in r["citation"]]
    assert [r["citation"] for r in trans] == [f"Ley 19.628, art. {n} transitorio" for n in (1, 2, 3)]
    assert trans[0]["display_path"] == "Ley 19.628 / Disposiciones transitorias / Artículo 1 transitorio"
    assert trans[0]["act_id"] == "STATE_CL_LEY19628_DT_A1T"
    # the line wrapping of the source is undone; a verbatim quote from the article survives
    assert "\n" not in first["text"] and "organismos públicos o por particulares" in first["text"]


def test_japan_sample_law():
    doc, rows = _rows("jp")
    assert doc.kind == "法律" and doc.title == "行政手続法" and doc.native_id == "405AC0000000088"
    assert doc.number == "平成五年法律第八十八号" and doc.eli_number == "88" and doc.year == "1993"
    assert doc.url == "https://laws.e-gov.go.jp/law/405AC0000000088"
    assert len(rows) == 76                                              # 48 main articles + 附則
    first = rows[0]
    assert first["citation"] == "行政手続法第一条" and first["section_title"] == "目的等"
    assert first["display_path"] == "行政手続法 / 第一章　総則 / 第一条"
    assert first["chapter_name"] == "総則" and first["act_id"] == "STATE_JP_405AC0000000088_C1_A1"
    assert first["eli"] == f"{base.ELI_BASE}/jp/act/1993/88/art_1/ja@2026-07-24"
    assert first["text"].startswith("この法律は、処分、行政指導及び届出に関する手続")
    art13 = next(r for r in rows if r["citation"] == "行政手続法第十三条")
    assert art13["display_path"] == "行政手続法 / 第三章　不利益処分 / 第一節　通則 / 第十三条"
    assert art13["act_id"] == "STATE_JP_405AC0000000088_C3_S1_A13"
    assert "\n　一　" in art13["text"] and "\n２　" in art13["text"]          # items and paragraphs kept, one per line
    art2 = next(r for r in rows if r["citation"] == "行政手続法第二条")
    assert "一　法令" in art2["text"]
    supp = [r for r in rows if r["level"] == "附則" or "附則" in r["display_path"]]
    assert supp and supp[0]["citation"] == "行政手続法附則"
    assert supp[0]["eli"].endswith("/suppl_1/ja@2026-07-24")
    with_articles = [r for r in supp if r["level"] == "条"]
    assert with_articles[0]["citation"].startswith("行政手続法附則（") and "第" in with_articles[0]["citation"]
    assert with_articles[0]["eli"].split("/")[-2].startswith("suppl_")


def test_japan_law_without_articles():
    """元号法-shaped laws have paragraphs straight under the main provision: one row for 本則."""
    raw = {"law_info": {"law_type": "Act", "law_id": "354AC0000000043", "law_num": "昭和五十四年法律第四十三号",
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
    jp = C.get("jp")
    doc = jp.parse(json.dumps(raw), "354AC0000000043")
    rows = jp.to_rows(doc)
    assert len(rows) == 1 and rows[0]["citation"] == "元号法" and rows[0]["level"] == "本則"
    assert rows[0]["text"] == "１　元号は、政令で定める。\n２　元号は、皇位の継承があった場合に限り改める。"
    assert rows[0]["eli"] == f"{base.ELI_BASE}/jp/act/1979/43/main/ja@1979-06-12"
    assert rows[0]["act_id"] == "STATE_JP_354AC0000000043_MAIN"


def test_eli_and_act_id_helpers():
    assert base.eli_uri("cl", "ley", "1999", "19628", "art_4") == f"{base.ELI_BASE}/cl/ley/1999/19628/art_4"
    assert base.eli_uri("cl", "ley", "1999", "19628", "art_4", "es", "2022-11-10").endswith("/art_4/es@2022-11-10")
    assert base.act_id("cl", "LEY19628", ["TI", "A4"]) == "STATE_CL_LEY19628_TI_A4"
    assert C.work_iri(f"{base.ELI_BASE}/cl/ley/1999/19628/art_4/es@2022-11-10") == \
        f"{base.ELI_BASE}/cl/ley/1999/19628/art_4"
    assert C.work_iri(f"{base.ELI_BASE}/cl/ley/1999/19628/art_4") == f"{base.ELI_BASE}/cl/ley/1999/19628/art_4"
    # the schema's token helpers read the country act_id unchanged
    from lexflow.publish import schema as S
    assert S.unit_tokens("STATE_JP_405AC0000000088_C3_S1_A13") == ["405AC0000000088", "C3", "S1", "A13"]


def test_index_builds_from_the_fixture(tmp_path, monkeypatch):
    from lexflow import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(C, "DIR", tmp_path / "raw" / "countries")
    I._STAMPS.clear(), I._READY.clear()
    for code, n in (("cl", 27), ("jp", 76)):
        out = I.build(code, log=lambda *_: None, corpus=C.CORPUS)
        assert out["sections"] == n and I.ready(code, corpus=C.CORPUS)
    hit = I.lookup("cl", "Ley 19.628, art. 4", with_text=True, corpus=C.CORPUS)
    assert hit and hit[0]["path"] == "Ley 19.628 / Título I / Artículo 4" and hit[0]["kind"] == "Ley"
    assert hit[0]["text"].startswith("El tratamiento de los datos personales sólo puede efectuarse")
    by_eli = I.lookup("cl", f"{base.ELI_BASE}/cl/ley/1999/19628/art_4", corpus=C.CORPUS)
    assert by_eli and by_eli[0]["citation"] == "Ley 19.628, art. 4"
    found = I.search("cl", I.match([["datos personales"], ["consentimiento"]]), corpus=C.CORPUS)
    assert found and all(r["country"] == "cl" for r in found)
    jp = I.lookup("jp", "行政手続法第十三条", corpus=C.CORPUS)
    assert jp and jp[0]["path"].endswith("第十三条") and jp[0]["language"] == "ja"
    # unicode61 splits Japanese only at punctuation and script changes, so a term that stands as its own run is found
    # with a raw FTS phrase, but index.phrase() keeps ASCII words only and returns None for Japanese: the query
    # helpers need a CJK path (trigram tokenizer or a segmenter) before Japanese search is real
    # (docs/design/global-sources.md §3.4)
    assert I.search("jp", '"聴聞"', corpus=C.CORPUS) and I.search("jp", '"行政庁は"', corpus=C.CORPUS)
    assert I.phrase("聴聞") is None
