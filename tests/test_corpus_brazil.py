"""Brazil (lexflow/corpus/countries/brazil.py): the registry entry, the URN keys and citations, the compilation parser
(the fixture law, Lei nº 12.527/2011 as the Câmara compiles it on normas.leg.br, and an inline Código-Penal-style
compilation with epígrafes, compiler's notes and revoked articles), the accent-insensitive tokenizer option of the
Brazilian index, Portuguese questions in the Ask flow, and the amendment rows from a Senado open-data record.
No network."""
import json
import sqlite3

import pytest

from lexflow import config
from lexflow.ask import index as I
from lexflow.corpus import countries as C
from lexflow.corpus.countries import base
from lexflow.corpus.countries import brazil as B
from lexflow.municipal import states as S
from lexflow.municipal import statutes

URN = "urn:lex:br:federal:lei:2011-11-18;12527"
FIX = config.ROOT / "fixtures" / "corpus" / "bra"


# ---------------------------------------------------------------------- registry
def test_brazil_is_registered_under_its_alpha3_key():
    a = C.get("bra")
    assert a is C.get("br") is C.get("BRA") and C.key_of("br") == "bra" and C.is_country("bra")
    assert a.name == "Brazil" and a.wikidata == "Q155" and a.languages == ("pt",) and a.iso2 == "br"
    assert a.code_label == "Legislação federal brasileira" and a.eli_jurisdiction == "br"
    assert a.raw_name == "bra/rows" and a.status == "prototype"
    assert all(s.licence and s.verified == "2026-10-22" and s.url.startswith("https://") for s in a.sources)
    assert "9.610" in a.sources[0].licence and "creativecommons.org/licenses/by/4.0" in a.sources[0].licence
    j = C.BY_KEY["bra"]
    assert j["wikidata"] == "Q155" and j["languages"] == ["pt"] and j["website"] == "https://normas.leg.br/"
    assert "bra" not in S.NAME and "bra" not in S.CODES                     # beside the 52 US jurisdictions
    br = S.COUNTRY["bra"]
    assert br["iso2"] == "br" and br["wikidata"] == "Q155" and br["languages"] == ["pt"]
    assert br["code_label"]["pt"] == "Legislação federal brasileira"
    assert S.normalise_any("BRA") == S.normalise_any("Brazil") == S.normalise_any("br") == "bra"
    assert S.name_of("bra") == "Brazil" and S.parse_jurisdictions("va,bra") == ["va", "bra"]


def test_the_states_registry_lists_the_pulled_countries_and_subnational_keys(con):
    """Australia, three of its states and Romania are Ask targets beside Japan and Brazil (states.COUNTRIES), each
    entry agreeing with the country adapters' registry; a subnational key (``aus-tas``) resolves like a country's."""
    from lexflow.ask import pipeline as AP
    want = {"aus": ("Australia", "Q408", ["en"]), "aus-tas": ("Tasmania", "Q34366", ["en"]),
            "aus-sa": ("South Australia", "Q35715", ["en"]), "aus-wa": ("Western Australia", "Q3206", ["en"]),
            "rou": ("Romania", "Q218", ["ro"]), "bra": ("Brazil", "Q155", ["pt"]), "jpn": ("Japan", "Q17", ["ja"])}
    for code, (name, qid, langs) in want.items():
        c = S.COUNTRY[code]
        assert (c["name"], c["wikidata"], c["languages"]) == (name, qid, langs)
        assert C.WIKIDATA[code] == qid and C.NAME[code] == name           # the adapters' registry agrees
        assert c["website"].startswith("https://") and c["code_label"]
        assert S.is_country(code) and S.normalise_any(code.upper()) == code and S.name_of(code) == name
        assert I.is_country(code) and code not in S.NAME
    for sub in ("aus-tas", "aus-sa", "aus-wa"):
        assert S.COUNTRY[sub]["parent"] == "aus" and S.COUNTRY[sub]["iso3166_2"] == sub.upper().replace("AUS", "AU")
        assert S.normalise_any(S.COUNTRY[sub]["name"]) == sub
    assert S.normalise_any("Romania") == S.normalise_any("ro") == "rou" and S.normalise_any("au") == "aus"
    assert S.parse_jurisdictions("va,aus-tas,rou") == ["va", "aus-tas", "rou"]
    assert AP.resolve_targets(con, ["aus-tas", "AUS-SA", "rou"]) == {"aus-tas": [], "aus-sa": [], "rou": []}
    assert not I.is_country("au-tas") and not I.is_country("va")


# ---------------------------------------------------------------------- identifiers and citations
def test_urn_keys_and_citations():
    assert B.parse_urn(URN) == {"tipo": "lei", "date": "2011-11-18", "year": "2011", "numero": 12527}
    assert B.parse_urn(URN + "!art11")["numero"] == 12527 and B.parse_urn("x")["tipo"] == ""
    assert B.key_of(URN) == "lei_2011-11-18_12527"
    assert B.key_of("urn:lex:br:federal:decreto.lei:1940-12-07;2848") == "decreto.lei_1940-12-07_2848"
    assert B.law_cite("lei", 13709, "2018") == "Lei nº 13.709/2018"
    assert B.law_cite("decreto.lei", 2848, "1940") == "Decreto-Lei nº 2.848/1940"
    assert B.law_cite("lei.complementar", 101, "2000") == "Lei Complementar nº 101/2000"
    assert B.law_cite("constituicao", 1988, "1988") == "Constituição Federal"
    assert B.law_cite("ato.disposicoes.constitucionais.transitorias", 1988, "1988") == "ADCT"
    assert [B.art_label(*a) for a in (("5",), ("10",), ("1228",), ("121", "A"), ("1", "A"))] == \
        ["5º", "10", "1.228", "121-A", "1º-A"]
    # LexML numbers the letters of an article: Art. 55-J is art55-10, Art. 121-A art121-1
    assert B.art_fragment("55", "J") == "art55-10" and B.art_fragment("121", "A") == "art121-1"
    assert B.art_fragment("5") == "art5" and B.letters_num("AA") == 27
    assert B.popular_name("DEL-2848-1940-12-07 , Código Penal (1940) (CP)") == ("Código Penal", "CP")
    assert B.popular_name("LEI-12527-2011-11-18 , Lei de Acesso à Informação (LAI) (2011)") == \
        ("Lei de Acesso à Informação", "LAI")
    assert B.urn_of_name("Lei nº 7.209 de 11/07/1984") == "urn:lex:br:federal:lei:1984-07-11;7209"
    assert B.urn_of_name("Medida Provisória nº 869 de 27/12/2018") == \
        "urn:lex:br:federal:medida.provisoria:2018-12-27;869"
    assert B.urn_of_name("Acórdão da Ação Direta de Inconstitucionalidade nº 3.150 de 13/12/2018") is None
    assert B.cite_of_name("Lei Complementar nº 101 de 04/05/2000") == "Lei Complementar nº 101/2000"
    # one comparable form for the ways a Brazilian article is cited (index.lookup's norm_num column)
    forms = ["Lei nº 13.709/2018, art. 5º", "lei 13709/2018 art 5", "Lei n. 13.709, de 2018, art. 5o",
             "Lei nº 13.709, de 14 de agosto de 2018, art. 5º"]
    assert {C.norm_num(f) for f in forms} == {"lei13709/2018art5"}
    assert C.norm_num("Constituição Federal, art. 5º") == C.norm_num("CF art 5") == "cfart5"
    assert C.norm_num("行政手続法 第十三条") == "行政手続法第13条"           # other countries' citations as before
    assert B.cite_key("Ley 19.628, art. 1") is None and B.cite_key("Privacy Act 1988 s 6") is None


# ---------------------------------------------------------------------- the parser
CODE_HTML = """<html><head><style>p{}</style></head><body><div>
<p class="Header" style="text-align:center"><img src="data:image/png;base64,iVBORw0KGgo="/></p>
<p class="Header" style="text-align:center"><span style="font-weight:bold">CÂMARA DOS DEPUTADOS</span></p>
<h2 style="text-align:center"><span>DECRETO-LEI Nº 2.848, DE 7 DE DEZEMBRO DE 1940</span></h2>
<p style="text-indent:226.8pt"><span>Código Penal.</span></p>
<p class="BodyTextIndent2"><span style="font-weight:bold">O PRESIDENTE DA REPÚBLICA</span><span>, decreta a seguinte Lei:</span></p>
<p style="text-align:center"><span>CÓDIGO PENAL</span></p>
<h1 style="text-align:center"><span>PARTE ESPECIAL</span></h1>
<p style="text-align:center"><a href="x"><span class="Hyperlink" style="font-style:italic">(Canceladas na Parte Especial quaisquer referências a valores de multas, de acordo com o art. 2º da Lei nº 7.209, de 11/7/1984)</span></a></p>
<p style="text-align:center"><span>TÍTULO I</span></p>
<p style="text-align:center"><span>DOS CRIMES CONTRA A PESSOA</span></p>
<p style="text-align:center"><span>CAPÍTULO I</span></p>
<p style="text-align:center"><span>DOS CRIMES CONTRA A VIDA</span></p>
<p><span style="font-weight:bold">Homicídio simples</span></p>
<p class="BodyTextIndent"><span>Art. 121. Matar alguém:</span></p>
<p class="BodyTextIndent"><span>Pena - reclusão, de seis a vinte anos.</span></p>
<p class="BodyTextIndent"><span>§ 1º Se o agente comete o crime impelido por motivo de relevante valor social. </span><a href="y"><span class="Hyperlink" style="font-style:italic">(Parágrafo com redação dada pela Lei nº 7.209, de 11/7/1984)</span></a></p>
<p class="BodyTextIndent"><span>VI - </span><a href="z"><span class="Hyperlink" style="font-style:italic">(Inciso acrescido pela Lei nº 13.104, de 9/3/2015, e revogado pela Lei nº 14.994, de 9/10/2024)</span></a></p>
<p class="BodyTextIndent"><span>§ 4º No homicídio culposo, a pena é aumentada (VETADO).</span></p>
<p><span style="font-weight:bold">Feminicídio</span></p>
<p class="BodyTextIndent"><span>Art. 121-A. Matar mulher por razões da condição do sexo feminino: </span><a href="w"><span class="Hyperlink" style="font-style:italic">(“Caput” do artigo acrescido pela Lei nº 14.994, de 9/10/2024)</span></a></p>
<p class="BodyTextIndent"><span>Pena - reclusão, de 20 (vinte) a 40 (quarenta) anos.</span></p>
<p style="text-align:center"><span>Seção I</span></p>
<p style="text-align:center"><span style="font-style:italic">Da Alteração</span></p>
<p class="BodyTextIndent"><span>Art. 1.228. A Lei nº 1.000 passa a vigorar com a seguinte redação:</span></p>
<p class="BodyTextIndent"><span>“Art. 5º O prazo é de 10 (dez) dias.” (NR)</span></p>
<p><span style="font-weight:bold">Adultério</span></p>
<p class="BodyTextIndent"><span>Art. 240. </span><a href="v"><span class="Hyperlink" style="font-style:italic">(Revogado pela Lei nº 11.106, de 28/3/2005)</span></a></p>
<p class="BodyTextIndent"><span>Art. 241. </span><span style="text-decoration:line-through">Texto antigo.</span><span>(VETADO).</span></p>
<p class="BodyTextIndent"><span>Art. 361. Este Código entrará em vigor no dia 1º de janeiro de 1942.</span></p>
<p><span>Rio de Janeiro, 7 de dezembro de 1940; 119º da Independência e 52º da República.</span></p>
<p><span>GETÚLIO VARGAS</span></p>
<p><span>Art. 999. Not a provision: after the signature.</span></p>
</div></body></html>"""


def _code_doc():
    entry = {"urn": "urn:lex:br:federal:decreto.lei:1940-12-07;2848", "tipo": "decreto.lei", "numero": 2848,
             "apelido": "DEL-2848-1940-12-07 , Código Penal (1940) (CP)", "status": [], "urnRevogacao": None}
    rec = {"headline": "Decreto-Lei nº 2.848, de 07 de dezembro de 1940", "dateModified": "2026-09-23",
           "encoding": {"version": "Original", "contentUrl": "https://normas.leg.br/api/binario/"
                        "1fe22fd6-ab76-4b2a-9d67-30e8c570d524/texto", "encodingFormat": "text/html",
                        "name": "Publicação Original [Decreto-Lei nº 2.848 de 07/12/1940]  [Diário Oficial da União  de "
                                "31/12/1940] (p. 23911, col. 2)"}}
    br = B.Brazil()
    doc = br.parse({"entry": entry, "record": B.slim_record(rec), "html": CODE_HTML, "fetched": "2026-10-22"})
    return br, doc, {r["section_number"]: r for r in br.to_rows(doc)}


def test_the_parser_reads_a_code_with_epigrafes_notes_and_revoked_articles():
    br, doc, rows = _code_doc()
    assert list(rows) == ["121", "121-A", "1228", "240", "241", "361"]          # nothing after the signature
    assert doc.number == "Decreto-Lei nº 2.848/1940" and doc.short_title == "Decreto-Lei nº 2.848/1940 (Código Penal)"
    assert doc.extra["dou"] == {"source": "Diário Oficial da União", "date": "1940-12-31", "page": "23911",
                                "column": "2", "from": "normas"}      # a single (not listed) encoding is read too
    assert doc.last_amended_year == 2024 and doc.extra["abbrev"] == "CP"
    r = rows["121"]
    assert r["citation"] == r["ref"] == "Decreto-Lei nº 2.848/1940, art. 121"
    assert r["section_title"] == "Homicídio simples" and r["chapter_name"] == "DOS CRIMES CONTRA A VIDA"
    assert r["display_path"] == ("Decreto-Lei nº 2.848/1940 (Código Penal) / Parte Especial / Título I / Capítulo I / "
                                 "Art. 121")
    assert r["act_id"] == "STATE_BRA_DEL2848-1940_PE_T1_C1_A121"
    assert r["native_id"] == r["urn"] == "urn:lex:br:federal:decreto.lei:1940-12-07;2848!art121"
    assert r["source_url"] == "https://normas.leg.br/?urn=urn:lex:br:federal:decreto.lei:1940-12-07;2848!art121"
    assert r["eli"] == f"{base.ELI_BASE}/br/decreto-lei/1940/2848/art_121/pt@2026-09-23"
    # the compiler's notes leave the text and stay with the row; a label whose words were all a note keeps it
    assert r["text"].split("\n") == [
        "Matar alguém:", "Pena - reclusão, de seis a vinte anos.",
        "§ 1º Se o agente comete o crime impelido por motivo de relevante valor social.",
        "VI - (Inciso acrescido pela Lei nº 13.104, de 9/3/2015, e revogado pela Lei nº 14.994, de 9/10/2024)",
        "§ 4º No homicídio culposo, a pena é aumentada (VETADO)."]
    assert "(Parágrafo com redação dada pela Lei nº 7.209, de 11/7/1984)" in r["notes"]
    a = rows["121-A"]
    assert a["citation"] == "Decreto-Lei nº 2.848/1940, art. 121-A" and a["section_title"] == "Feminicídio"
    assert a["urn"].endswith("!art121-1") and a["act_id"].endswith("_A121-A") and "Caput" in a["notes"][0]
    c = rows["1228"]
    assert c["citation"] == "Decreto-Lei nº 2.848/1940, art. 1.228" and c["chapter_name"] == "Da Alteração"
    assert c["display_path"].endswith("/ Capítulo I / Seção I / Art. 1.228")
    assert "“Art. 5º O prazo é de 10 (dez) dias.” (NR)" in c["text"]       # a quoted article stays in its article
    assert rows["240"]["act_status"] == "repealed" and rows["240"]["section_title"] == "Adultério"
    assert rows["241"]["act_status"] == "vetoed" and "Texto antigo" not in rows["241"]["text"]   # struck text dropped
    assert rows["361"]["act_status"] == "in_force"
    assert {r["act_status"] for r in rows.values() if C.prepare_row(r) is not None} == {"in_force"}


def test_an_annexed_code_is_read_as_the_norms_articles():
    """The CLT is the annex of Decreto-Lei nº 5.452/1943: its articles are the decree-law's (as the Senado and LexML
    number them), and the decree's own two articles become the unit "Ato de aprovação"."""
    arts = "".join(f"<p><span>Art. {n}{'º' if n < 10 else ''} Texto do artigo {n} da Consolidação.</span></p>"
                   for n in range(1, 7))
    page = ("<html><body><p><span>DECRETO-LEI Nº 5.452, DE 1º DE MAIO DE 1943</span></p>"
            "<p><span>Art. 1º Fica aprovada a Consolidação das Leis do Trabalho, que a este decreto-lei acompanha.</span></p>"
            "<p><span>Art. 2º O presente decreto-lei entrará em vigor em 10 de novembro de 1943.</span></p>"
            "<p><span>Rio de Janeiro, 1 de maio de 1943, 122º da Independência e 55º da República.</span></p>"
            "<p><span>GETÚLIO VARGAS</span></p><p style=\"text-align:center\"><span>CONSOLIDAÇÃO DAS LEIS DO TRABALHO"
            "</span></p><p style=\"text-align:center\"><span>TÍTULO I</span></p><p style=\"text-align:center\"><span>"
            "INTRODUÇÃO</span></p>" + arts + "</body></html>")
    br = B.Brazil()
    doc = br.parse({"entry": {"urn": "urn:lex:br:federal:decreto.lei:1943-05-01;5452", "status": []}, "record": {},
                    "html": page})
    rows = br.to_rows(doc)
    assert [r["citation"] for r in rows[:3]] == ["Decreto-Lei nº 5.452/1943 (ato de aprovação), art. 1º",
                                                 "Decreto-Lei nº 5.452/1943 (ato de aprovação), art. 2º",
                                                 "Decreto-Lei nº 5.452/1943, art. 1º"]
    assert rows[0]["urn"].endswith("!apr_art1") and rows[2]["urn"].endswith("!art1")
    assert rows[0]["display_path"] == "Decreto-Lei nº 5.452/1943 / Ato de aprovação / Art. 1º"
    assert rows[2]["display_path"] == "Decreto-Lei nº 5.452/1943 / Título I / Art. 1º" and len(rows) == 8
    assert len({r["act_id"] for r in rows}) == len({r["eli"] for r in rows}) == len({r["citation"] for r in rows}) == 8


def test_the_fixture_law_parses_from_its_compilation():
    fx = json.loads((FIX / "sample.json").read_text(encoding="utf-8"))
    assert fx["country"] == "bra" and fx["licence_url"] == B.CC_BY and "9.610" in fx["attribution"]
    doc = C.load_document("bra")
    assert doc is not None and doc.native_id == URN and doc.fetched == "2026-10-22"
    rows = C.rows_for("bra", doc)
    assert len(rows) == fx["row_count"] == 47
    # parsing the saved compilation again gives the same rows (the parser is pure)
    again = B.Brazil().parse({"entry": {"urn": URN, "apelido": "LEI-12527-2011-11-18 , Lei de Acesso à Informação (LAI) "
                                                            "(2011)", "status": []},
                              "record": {"dateModified": doc.version_date, "headline": doc.title},
                              "html": (FIX / "lai.html").read_text(encoding="utf-8"), "fetched": doc.fetched})
    redo = B.Brazil().to_rows(again)
    keys = ("act_id", "citation", "section_number", "display_path", "chapter_name", "text", "eli", "native_id")
    assert [{k: r[k] for k in keys} for r in redo] == [{k: r[k] for k in keys} for r in rows]
    for r in rows:
        assert set(statutes.COLUMNS) <= set(r) and set(base.EXTRA) <= set(r)
        assert r["act_id"].startswith("STATE_BRA_LEI12527-2011_") and r["country"] == "bra" and r["language"] == "pt"
        assert r["native_id"].startswith(URN + "!art") and r["eli"].startswith(f"{base.ELI_BASE}/br/lei/2011/12527/art_")
        assert r["text"] and r["act_status"] == "in_force" and r["level"] == "Artigo"
    assert len({r["act_id"] for r in rows}) == len({r["eli"] for r in rows}) == len(rows)
    art11 = next(r for r in rows if r["section_number"] == "11")
    assert art11["citation"] == "Lei nº 12.527/2011, art. 11" and art11["chapter_name"] == "Do Pedido de Acesso"
    assert art11["display_path"] == "Lei nº 12.527/2011 (Lei de Acesso à Informação) / Capítulo III / Seção I / Art. 11"
    assert "em prazo não superior a 20 (vinte) dias" in art11["text"]
    assert art11["text"].startswith("O órgão ou entidade pública deverá autorizar ou conceder o acesso imediato")


# ---------------------------------------------------------------------- the index (tokenizer option)
@pytest.fixture()
def br_index(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(C, "DIR", tmp_path / "raw" / "countries")     # no pull on disk: the fixture
    I._STAMPS.clear(), I._READY.clear()
    return tmp_path


def test_the_brazilian_index_is_accent_insensitive_and_the_others_keep_their_tokenizers(br_index):
    assert C.tokenizer("bra") == "unicode61 remove_diacritics 2"
    assert C.tokenizer("jpn") == "trigram" and C.tokenizer("aus") is None        # the statutes' porter default
    assert I.path("bra").name == "statutes_bra.sqlite" and I.is_country("bra") and I._source("statutes", "bra") is C
    out = I.build("bra", log=lambda *_: None)
    assert out["sections"] == 47 and I.ready("bra")
    assert I.tokenizer_of("bra") == "unicode61 remove_diacritics 2"
    n = I.count("bra", '"informação"')
    assert n > 0 and I.count("bra", '"informacao"') == n == I.count("bra", '"INFORMAÇÃO"')
    assert I.count("bra", '"órgão"') == I.count("bra", '"orgao"') > 0
    hits = I.search("bra", I.match([["prazo"], ["pedido"], ["acesso à informação"]], "and"))
    assert "Lei nº 12.527/2011, art. 11" in [h["ref"] for h in hits[:5]]
    assert [r["ref"] for r in I.lookup("bra", "Lei 12.527/2011, art. 11")] == ["Lei nº 12.527/2011, art. 11"]
    assert [r["ref"] for r in I.lookup("bra", "Lei nº 12.527, de 18 de novembro de 2011, art. 11")] == \
        ["Lei nº 12.527/2011, art. 11"]
    con = I.connect("bra")
    try:
        meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
        law = dict(con.execute("SELECT * FROM law").fetchone())
    finally:
        con.close()
    assert meta["language"] == "pt" and meta["attribution"] == B.ATTRIBUTION and meta["laws"] == "1"
    assert law["law_id"] == URN


def test_ask_a_portuguese_question_and_get_verbatim_quotes(br_index, con):
    from lexflow.ask import pipeline as AP
    from lexflow.ask import plan as PL
    q = "Qual o prazo para resposta a um pedido de acesso à informação?"
    p = PL.plan(q)
    assert p.source == "rules-pt" and p.kind == "facts"
    assert ["acesso à informação", "acesso a informações", "acesso às informações"] in p.groups
    assert any("pedido" in g and "resposta" in g for g in p.groups) and ["prazo", "prazos"] in p.groups
    assert PL.plan("Quem pode ser incorporador?").groups == [["incorporador", "incorporadores", "incorporação"]]
    assert PL.plan("How do I seal a criminal record?").source == "rules"          # English as before
    assert PL.pt_forms("informação") == ["informações"] and PL.pt_forms("pedidos") == ["pedido"]
    assert AP.resolve_targets(con, ["bra", "BR"]) == {"bra": []}
    I.build("bra", log=lambda *_: None)
    row = AP.answer_state(con, "br_lai_prazo", p, "bra", emb=None, log=lambda *_: None)
    ans = json.loads(row["answer"])
    sec = json.loads(row["sections"])
    # one law of 47 articles is a degenerate corpus (every article holds "acesso à informação" in its path), so the
    # order is not tested here; on the pulled corpus art. 11 comes first (docs/design/global-sources.md, Brazil)
    assert row["status"] in ("answered", "partial") and sec["chosen"]
    assert "Lei nº 12.527/2011, art. 11" in [c["ref"] for c in sec["candidates"]]
    con2 = I.connect("bra")
    try:
        body = "\n".join(t for (t,) in con2.execute("SELECT text FROM body"))
    finally:
        con2.close()
    assert ans["quotes"] and all(x["text"] in body for x in ans["quotes"])     # the law's own words
    chosen = {c["ref"] for c in sec["chosen"]}
    assert all(x["section"] in chosen for x in ans["quotes"])                   # each quote names its own article
    assert json.loads(row["metrics"])["quote_misses"] == 0
    assert "Normas.leg.br" in ans["markdown"]


def test_the_segmenter_reads_brazilian_section_headers():
    from lexflow.extract.segment import segment
    text = ("§ Lei nº 4.591/1964, art. 31. \nA iniciativa e a responsabilidade das incorporações imobiliárias caberão "
            "ao incorporador.\n\n§ Decreto-Lei nº 2.848/1940, art. 121-A. Feminicídio\nMatar mulher por razões da "
            "condição do sexo feminino.\n\n§ 19.2-305. Probation\nThe court may place the defendant on probation.")
    assert [c.section for c in segment(text)] == ["Lei nº 4.591/1964, art. 31", "Decreto-Lei nº 2.848/1940, art. 121-A",
                                                  "19.2-305"]


# ---------------------------------------------------------------------- amendments
SENADO = {"DetalheDocumento": {"documentos": {"documento": [{
    "id": "527942", "identificacao": {"normaNome": "Decreto-Lei nº 2.848 de 07/12/1940"},
    "publicacoes": {"publicacao": [{"tipo": "PUB", "fonte": "Diário Oficial da União  de 31/12/1940", "data": "31/12/1940",
                                    "pagina": "23911", "coluna": "2"}]},
    "vides": {"vide": [
        {"codnormaposterior": "549085", "datAssinatura": "11/07/1984", "nomeNormaPosterior": "Lei nº 7.209 de 11/07/1984",
         "datapub": "13/07/1984", "nomePub": "Publicação Original [Diário Oficial da União de 13/07/1984] (p. 10217, col. 1)",
         "comentario": "Declaração de Alteração Permanente",
         "itens": {"item": [{"dispositivo": "Art. 1 ", "comentario": "Alteração"},
                            {"dispositivo": "Art. 121, § 2, Inciso 6 ", "comentario": "Acréscimo"}]}},
        {"codnormaposterior": "549085", "datAssinatura": "11/07/1984", "nomeNormaPosterior": "Lei nº 7.209 de 11/07/1984",
         "comentario": "Declaração de Alteração Permanente", "itens": {"item": {"dispositivo": "Art. 1 ",
                                                                              "comentario": "Alteração"}}},
        {"codnormaposterior": "1", "datAssinatura": "28/03/2005", "nomeNormaPosterior": "Lei nº 11.106 de 28/03/2005",
         "comentario": "Declaração de Revogação Permanente", "itens": ""},
        {"codnormaposterior": "2", "datAssinatura": "13/12/2018",
         "nomeNormaPosterior": "Acórdão da Ação Direta de Inconstitucionalidade nº 3.150 de 13/12/2018",
         "comentario": "Declaração de Alteração Permanente", "itens": ""},
        {"codnormaposterior": "3", "datAssinatura": "05/02/2009", "nomeNormaPosterior": "Decreto nº 6.759 de 05/02/2009",
         "comentario": "Declaração de Legislação Correlata", "itens": ""},
        {"codnormaposterior": "4", "datAssinatura": "14/08/2018", "nomeNormaPosterior": "Mensagem de Veto Parcial nº 451",
         "comentario": "Declaração de Veto Original", "itens": ""}]}}]}}}


def test_amendment_rows_in_the_law_amendments_shape(tmp_path):
    from lexflow.corpus.countries.japan import AMEND_COLUMNS
    law = "urn:lex:br:federal:decreto.lei:1940-12-07;2848"
    rows = B.amendment_rows(law, SENADO, "2026-10-22")
    kinds = sorted((r["kind"], r["amending_num"]) for r in rows)
    assert kinds == [("amended", "Lei nº 7.209/1984"), ("judicial",
                     "Acórdão da Ação Direta de Inconstitucionalidade nº 3.150 de 13/12/2018"),
                     ("repealed", "Lei nº 11.106/2005"), ("repeals", "Decreto-Lei nº 2.848/1940")]
    am = next(r for r in rows if r["kind"] == "amended")
    assert set(AMEND_COLUMNS) <= set(am) and am["jurisdiction"] == "bra" and am["law_key"] == law
    assert am["amending_key"] == "urn:lex:br:federal:lei:1984-07-11;7209" and am["date"] == "1984-07-11"
    assert am["source"] == "senado-dadosabertos" and am["date_kind"] == "signed" and am["published"] == "1984-07-13"
    assert am["provisions"] == [{"provision": "Art. 1", "action": "Alteração"},
                                {"provision": "Art. 121, § 2, Inciso 6", "action": "Acréscimo"}]   # merged, no repeats
    inv = next(r for r in rows if r["kind"] == "repeals")
    assert inv["law_key"] == "urn:lex:br:federal:lei:2005-03-28;11106" and inv["amending_key"] == law
    assert B.dou_of({}, SENADO) == {"source": "Diário Oficial da União", "date": "1940-12-31", "page": "23911",
                                    "column": "2", "from": "senado"}
    con = sqlite3.connect(":memory:")
    B._write_lines(tmp_path / "amendments.jsonl", rows)
    assert B.load_amendments(con, raw=tmp_path) == {"rows": 3}                 # court decisions stay in the file
    got = con.execute("SELECT kind, amending_key FROM law_amendments ORDER BY kind").fetchall()
    assert [k for k, _ in got] == ["amended", "repealed", "repeals"]
