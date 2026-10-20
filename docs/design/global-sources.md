# Going global: official primary-law sources for Peru, Chile, Australia, Romania, Ghana and Japan

Research of 19 October 2026, read-only, user agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`,
robots.txt obeyed, at least 1.5 s between requests to a host (10 s where the host asks). Every licence quote below is
copied from the source's own page on that date; "unverified" means the page could not be read from the research
network. Legal Data Hunter (legaldatahunter.com) was read once as a pointer list: its coverage data
(`status.json`) names the sources it indexes per country, and its own terms forbid using its service for "bulk
extraction or delivery, redistribution, ... creation or augmentation of a legal database", so it is a map, never a
source. The code is `lexflow/corpus/countries/` (base adapter, two prototypes, four stubs) and the samples are
`fixtures/corpus/<cc>/sample.json`; `tests/test_corpus_countries.py` builds the index from them.

## 1. Comparison table

| Country | Official source | Holds | Format | Machine access | Identifier | Licence / automated reading | Cadence | Language | Size | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| Japan | e-Gov 法令検索, Digital Agency (laws.e-gov.go.jp) | all national laws and regulations in force, consolidated, with revisions | 法令標準XML, JSON tag tree | REST API v2 (no key), official bulk XML zip, OpenAPI spec | law_id (405AC0000000088), law_num; no ELI | PDL1.0 (= CC BY 4.0 compatible): "複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます ... 商用利用も可能です"; API and bulk download are the published machine access | continuous (`updated` per revision) | ja; unofficial en translations (MoJ, PDL1.0) | 9,567 laws listed; bulk zip size not announced (estimate 200-300 MB zipped, ~1.5 GB XML, ~350k articles) | **prototype written; first to implement** |
| Chile | Ley Chile, Biblioteca del Congreso Nacional (bcn.cl/leychile) + datos.bcn.cl LOD | every norma, consolidated, versioned | XML (own schema), HTML, PDF; RDF | per-document XML endpoint (works without key); API Ley Chile with key, 500 req/24 h; SPARQL (Crawl-delay 10) | idNorma/idParte; datos.bcn.cl URI cl/{tipo}/{org}/{fecha}/{numero}; no ELI | CC BY-NC-ND 4.0; API conditions prohibit "extracciones masivas, sistemáticas o automatizadas ... para replicar, reconstruir o generar una base de datos sustancialmente equivalente a Ley Chile" without express authorisation | continuous (`fechaVersion`) | es | 359,739 root normas, 748,821 versions (SPARQL count) | **prototype written; full pull only by agreement with BCN** |
| Australia (federal) | Federal Register of Legislation, OPC (legislation.gov.au) | Acts, legislative/notifiable instruments, gazettes; as made and compiled point-in-time | HTML (from ePub), PDF, DOCX, ePub; OData JSON | OData v4 API (`api.prod.legislation.gov.au/v1`), sitemap; Crawl-delay 10 | register id C1901A00002 / compilation C2026C00117; no ELI | CC BY 4.0 with prescribed attribution ("Sourced from the Federal Register of Legislation at [date] ...") | daily | en | 132,603 titles; 4,774 Acts in force (principal + amending) | **stub with verified sources; second to implement** |
| Australia (states) | QLD, WA, TAS, SA: CC BY 4.0 (QLD API with account, SA XML packages on data.sa.gov.au); NT: own permissive policy; VIC: copyright, "personal use only"; ACT: all rights reserved, document views disallowed to robots; NSW: 403 to all automation | Acts and subordinate legislation | XML (QLD, SA), HTML, PDF | varies | state ids | see §2.3 | varies | en | QLD ~21,000 documents (LDH count) | QLD/SA/TAS/WA after federal; VIC/ACT/NSW need permission |
| Ghana | Parliament of Ghana Library Repository (repository.parliament.gh, DSpace 7) | Acts as passed, by Parliament, EIs, Hansard | PDF (+ mostly empty text bitstream) | DSpace REST API (open), sitemap | handle 123456789/n | "an open access electronic archive" (no reuse licence stated); robots allows API and items | as items are deposited | en | 1,538 items match "Act"; PDFs 0.4-5 MB | **stub; official but PDF-first, OCR needed; consolidation only via GhaLII by agreement (its terms forbid scraping; AKN pages answered 403)** |
| Peru | SPIJ (MINJUSDH): official consolidated texts; Congreso archive (PDF); gob.pe normas (PDF); El Peruano (PDF) | consolidated (SPIJ) vs as-published (others) | HTML (SPIJ, reported), PDF | SPIJ REST API reported, unreachable from here; Congreso robots disallows PDFs; gob.pe pages allowed | SPIJ ids; norm numbers | SPIJ terms unread; others have no licence page | daily (gazette) | es (+qu) | SPIJ ~1.4 M norm ids (LDH) | **stub; blocked until SPIJ's terms are read from a reachable network** |
| Romania | Portal Legislativ, Ministerul Justiției (legislatie.just.ro) | all acts since 1989, consolidated; native ELI | HTML; SOAP XML with full text (reported) | SOAP FreeWebService (reported) | ELI `legislatie.just.ro/eli/{tip}/{an}/{numar}` | unverified: the host closed every TLS connection from the research network and the browser pane | daily | ro | ~240,000 acts (LDH) | **stub; best identifier story, re-verify from another network** |

Recommended order of implementation: **Japan** (open licence, clean structured API, official bulk file, prototype
done), **Australia federal** (CC BY 4.0, OData with versions, only an HTML section splitter to write), **Chile**
(prototype done, but a full pull needs BCN's written authorisation and the API key, or a scoped pull of leyes in force
agreed with them), **Australian states** (QLD, SA, TAS, WA under CC BY 4.0), **Romania** once reachable (native ELI
makes it the cleanest fit for the schema), **Ghana** (official PDFs with OCR, as-passed only), **Peru** last (no
readable terms, PDF-only official channels, consolidated texts behind SPIJ).

## 2. Sources per country

### 2.1 Peru

* **SPIJ, Sistema Peruano de Información Jurídica** — https://spij.minjus.gob.pe/, Ministerio de Justicia y Derechos
  Humanos. The official consolidated legislation (textos actualizados); SPIJ Libre is the free tier. Unreachable from
  the research network (TCP timeouts on 443 and 80; spijlibre.minjus.gob.pe reset). Legal Data Hunter's pointer records
  a REST API with public authentication and ~1.4 M norm ids with HTML full text. Terms, format, quota: unverified.
* **Archivo Digital de la Legislación del Perú** — https://leyes.congreso.gob.pe/, Congreso de la República. Every
  norma con rango de ley since 1904 (leyes, resoluciones legislativas, decretos leyes, decretos legislativos, decretos
  de urgencia, leyes regionales, constitutions, Leyes de Indias, laws in Quechua) as PDF; ASP.NET search forms. robots:
  `Disallow: /*.pdf$` (the documents may not be fetched by robots), listings allowed. No licence page.
* **gob.pe Normas y documentos legales** — https://www.gob.pe/institucion/minjus/normas-legales (and every other
  institution and regional government, e.g. gobiernos regionales' ordenanzas). One page per norma with metadata and
  the PDF as published (cdn.www.gob.pe). robots allows pages, disallows `?sheet=` paging (note: one listing request
  with `sheet=1` was made before that rule was noticed; nothing else). Only a privacy policy, no terms page.
* **El Peruano** — https://busquedas.elperuano.pe/ (allows all, sitemap): the gazette's daily "Normas Legales"
  cuadernillos as PDF; https://diariooficial.elperuano.pe/ disallows its /Normas/ paths.
* **First subnational layer**: the 25 regional governments publish ordenanzas regionales on gob.pe (PDF), same shape.

Verdict: official channels are PDF-first and as-published; the consolidated texts live in SPIJ whose terms must be read
on the site. No adapter beyond the stub until then.

### 2.2 Chile

* **Ley Chile** — https://www.bcn.cl/leychile/, Biblioteca del Congreso Nacional (BCN). Every norma (leyes, DFL, DL,
  decretos, reglamentos, ordenanzas municipales, tratados) consolidated with version history. The web application is
  an Angular SPA; its bundle calls `https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=<id>`, which returned the
  consolidated text of Ley 19.628 (48 KB) as XML under `http://www.leychile.cl/esquemas/EsquemaIntercambioNorma-v1-0.xsd`:
  `Norma(normaId, fechaVersion, derogado) > Identificador(Tipo, Numero, Organismo, fechaPromulgacion, fechaPublicacion)
  > Metadatos(TituloNorma, NombresUsoComun, Materias) > EstructurasFuncionales > EstructuraFuncional(tipoParte =
  Libro | Título | Capítulo | Párrafo | Artículo | Disposición Transitoria; idParte; fechaVersion; derogado) nested,
  each with Texto`, then `Promulgacion` and `Anexos`. Other documented `opt` values list recent normas, categories and
  search results. No key was needed for the one document.
* **API Ley Chile** (same application, "Condiciones de Uso de la API Ley Chile" v1.1 PDF): an API key per
  applicant, standard quota **500 requests per 24 h**, larger quotas only for public institutions under agreement;
  §3(e)(vi)-(vii) prohibit "extracciones masivas, sistemáticas o automatizadas de datos ... con el objeto de replicar,
  reconstruir o generar una base de datos sustancialmente equivalente a Ley Chile" and "indexación masiva, creación de
  repositorios estructurados de gran escala o almacenamiento persistente que excedan los fines declarados de uso",
  without the Library's express authorisation; AI users must keep provenance traceability (§5(b)(vi)). The application
  states: "Ley Chile y sus contenidos se encuentran amparados por la licencia Creative Commons CC BY-NC-ND 4.0".
* **BCN Datos Abiertos Enlazados** — https://datos.bcn.cl/ (robots: `Crawl-delay: 10`). SPARQL at
  https://datos.bcn.cl/sparql: 359,739 `bcn-norms:RootNorm`, 748,821 `bcn-norms:Norm` (versions), 389,082
  `NormInstance`, 2,875 treaties. Persistent URIs `http://datos.bcn.cl/recurso/cl/{tipo}/{org}/{fecha_publicacion}/
  {numero}` with `datos.{rdf|json|...}` manifestations; norms ontology v1.1. No licence page found on the portal; it
  describes the data as made freely available as RDF.
* No ELI. First subnational layer: regional governments do not legislate; municipal ordenanzas are in Ley Chile.

Verdict: technically the friendliest Spanish-language source (structured XML, article-level ids, version dates), but
NC-ND plus the API's anti-replication clause mean lexflow may fetch samples and answer per question, not mirror.
A full pull needs a written agreement with BCN (the conditions name universities and public bodies as eligible).

### 2.3 Australia

* **Federal Register of Legislation** — https://www.legislation.gov.au/, Office of Parliamentary Counsel. Terms of
  use: "With the exception of the Commonwealth Coat of Arms, and where otherwise noted, all content on the Federal
  Register of Legislation (the Legislation Register) is provided under Creative Commons Attribution 4.0 International
  (the CC BY 4.0 licence)", attribution "Sourced from the Federal Register of Legislation at [full date of download].
  For the latest information on Australian Government law please go to https://www.legislation.gov.au." robots:
  `Crawl-delay: 10`, sitemap. API: OData v4 at https://api.prod.legislation.gov.au/v1/ with `$metadata`; entity sets
  `Titles` (132,603; `$filter=isInForce eq true and collection eq 'Act'` gives 4,774), `Versions` (point in time,
  `compilationNumber`, `registerId`), `Documents` (format, bytes, pageCount), `Affect`, full-text search contexts.
  Compiled text as HTML per version at
  `/{titleId}/{start}/{start}/text/original/epub/OEBPS/document_1/document_1.html` (118 KB for the Acts
  Interpretation Act 1901, compilation 39 of 28 March 2026), plus PDF/DOCX/ePub. Identifier: register id; no ELI.
* **States and territories** (first subnational layer):
  * Queensland — https://www.legislation.qld.gov.au/: CC BY 4.0 ("Unless otherwise noted, all copyright material
    available on or through this website is licensed under a Creative Commons Attribution 4.0 International licence");
    API with registration at https://api.legislation.qld.gov.au/ (Swagger; JSON/XML/HTML/PDF); XML per document.
  * Western Australia — https://www.legislation.wa.gov.au/: CC BY 4.0 (copyright and licence page); no API found;
    no robots.txt.
  * Tasmania — https://www.legislation.tas.gov.au/: CC BY 4.0; sitemap and a crawler feed.
  * South Australia — fortnightly XML update packages on https://data.sa.gov.au/ (CKAN `package_show`, 236 resources,
    `license_id cc-by`); the legislation site itself answers 403 to robots.txt.
  * Northern Territory — https://legislation.nt.gov.au/: its own copyright policy (8 October 1996) granting permission
    to publish legislation under stated conditions.
  * Victoria — https://www.legislation.vic.gov.au/: "The information on this website is copyright ... Authorised
    electronic versions are published on this website ... for personal use only" (Government Printer); permission
    needed.
  * ACT — https://www.legislation.act.gov.au/: JACS Copyright Policy, "All rights reserved"; robots disallows `/View/`
    and `/html/`.
  * New South Wales — https://legislation.nsw.gov.au/: HTTP 403 to every automated request including robots.txt;
    unverified.

Verdict: federal first (CC BY 4.0, OData with versions and affects); the parser is an HTML section splitter on the
OPC styles (Chapter / Part / Division / Subdivision / section). QLD, SA, TAS, WA follow under CC BY 4.0; VIC, ACT and
NSW only with permission.

### 2.4 Romania

* **Portalul Legislativ** — https://legislatie.just.ro/, Ministerul Justiției: all acts published in the Monitorul
  Oficial since 1989 plus older acts in force, consolidated versions, and **native ELI** (`/eli/{tip}/{an}/{numar}`;
  Romania is in the EU ELI register). Legal Data Hunter's pointer: a SOAP `FreeWebService` with full text inline,
  ~240,000 acts. **Not verified here**: the host closed every TLS connection from the research network (Python
  urllib, curl/Schannel, TLS 1.2 forced, and the desktop browser pane), and EUR-Lex's ELI register pages returned an
  empty 202 (bot challenge). Terms, format, quota and robots.txt are unread.
* **Monitorul Oficial** — https://monitoruloficial.ro/: the gazette as a commercial WooCommerce site; `/docs/` and
  search disallowed to robots; not a lexflow source.

Verdict: the best identifier fit (real ELI per act, the schema's `eli` column takes it verbatim). Re-verify from a
network the portal accepts; then the adapter is a SOAP client plus a Titlu / Capitol / Secțiune / Articol splitter.

### 2.5 Ghana

* **Parliament of Ghana Library Repository** — https://repository.parliament.gh/ (DSpace 7): communities "ACTS - 1ST
  REPUBLIC" ... "9th and 10th Parliament Acts", executive instruments, Hansard, committee reports. Open REST API at
  `/server/api` (discover/search, core/items, bundles/bitstreams), 1,538 items match "Act"; each item has the PDF
  (0.4-5 MB in the samples), a thumbnail and a `.pdf.txt` text bitstream that is usually empty (28-42 bytes), and a
  DSpace deposit `license.txt`. robots allows the API and item pages. The home page calls it "an open access
  electronic archive for collecting, preserving, and sharing digital materials that has been created, owned and hosted
  by Parliament of Ghana"; no reuse licence is stated. Official, as-passed texts; not consolidated.
* **GhaLII** — https://ghalii.org/ (Ghana Legal Information Institute, non-profit "in partnership with the Judicial
  Service of Ghana", on the AfricanLII / Laws.Africa platform): 568 legislation documents as Akoma Ntoso with FRBR URIs
  (`/akn/gh/act/1960/7/eng@2010-04-30`), partly consolidated, many older ones PDF only. Terms of use: "Scraping and
  bulk downloading from this website is strictly prohibited ... There are more efficient ways of obtaining access to
  our data in bulk. Please email us if you would like to access our data in bulk." robots: `Content-Signal:
  search=yes,ai-train=no`, named AI crawlers disallowed; listing pages answered 200, the AKN document URL answered
  403 to the research agent. Not official.
* **Laws.Africa API** (https://api.laws.africa/v2/akn/gh/, key required, robots disallows all) carries the same AKN
  data; the **Ghana Publishing Company** (Government Printer) has no online legislation service.

Verdict: official texts exist only as PDFs in the Parliament's repository (OCR needed, as-passed only); consolidated
Akoma Ntoso exists at GhaLII only by agreement. Implement the repository walk after the open-licence countries.

### 2.6 Japan

* **e-Gov 法令検索** — https://laws.e-gov.go.jp/, デジタル庁 (Digital Agency). 利用規約: "本サイトの著作権は、特記されていない限り
  デジタル庁に帰属し、権利表記の記載がない限り「公共データ利用規約（第1.0版）」（PDL1.0）が適用されています". PDL1.0
  (https://www.digital.go.jp/resources/open_data/public_data_license_v1.0): "どなたでも ... 複製、公衆送信、翻訳・変形等の翻案等、
  自由に利用できます ... 商用利用も可能です", with a source statement (出典) and a note when edited. **法令API Version 2**
  (OpenAPI 2.1.139 at `/api/2/swagger-ui/lawapi-v2.yaml`; Redoc at `/api/2/redoc/`): `/laws` (list and filters;
  9,567 laws with the default filters), `/law_revisions/{id}`, `/law_data/{id}` (JSON tag tree or XML of the current
  consolidated text: `Law > LawBody > MainProvision > Part/Chapter/Section/Subsection/Division > Article(Num,
  ArticleCaption, ArticleTitle) > Paragraph(ParagraphNum) > Item > Subitem...`, `SupplProvision(AmendLawNum)`),
  `/law_file/{xml|json|...}/{id}`, `/keyword`, `/attachment`. No key, no documented quota; the JSON form is marked
  試行版 (may change). **Bulk**: `https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true`
  (`all_xml.zip`; the server streams it without Content-Length) and per category. Version 1 (`/api/1/lawlists/1`,
  2.8 MB XML list) still works. Identifier: law_id (era-year + type + number, e.g. `405AC0000000088` = 平成5年法律第88号),
  law_num, law_revision_id; no ELI.
* **日本法令外国語訳データベースシステム, Japanese Law Translation** — https://www.japaneselawtranslation.go.jp/, 法務省
  (Ministry of Justice). Unofficial English translations of selected laws, bilingual with the Standard Legal Terms
  Dictionary; terms: "Information published on this site ... is subject to the 'Public Data License (Version 1.0)'
  (PDL1.0) unless stated otherwise"; "Only the original Japanese texts of the laws and regulations have legal effect,
  and the translations are to be used solely as reference materials". An API is referred to in its user guide (not
  verified here).

Verdict: the friendliest source of the six: open licence, structured text to the paragraph and item, official bulk
file, stable ids. Prototype written (`japan.py`).

## 3. What the prototypes produce

### 3.1 Row shape

`Country.to_rows(doc)` yields the open-us-law columns municipal/statutes.py reads (`act_id, citation,
section_number, section_title, chapter_name, display_path, act_status, text, source_url, word_count,
last_amended_year`) plus the country columns `kind, language, eli, native_id, level, country, norm_eli` (the index's
`EXTRA`; `norm_eli` is also a `CITES` column so `index.lookup()` finds a row by its ELI work IRI) and `ref` (the
citation), `effective_from` (the unit's own version date where the source gives one, else the law's) and
`effective_until`. `lexflow/corpus/countries/__init__.py` is a corpus module for lexflow/ask/index.py:
`index.build("jp", corpus="countries")` writes `data/index/countries_jp.sqlite` from `data/raw/countries/jp.jsonl`
or, until a pull is approved, from the fixture.

### 3.2 Chile, Ley 19.628 (sobre protección de la vida privada), idNorma 141599, version 2022-11-10 — 27 rows

| act_id | citation | display_path | chapter_name | eli | native_id |
|---|---|---|---|---|---|
| STATE_CL_LEY19628_TPRELIMINAR_A1 | Ley 19.628, art. 1 | Ley 19.628 / Título Preliminar / Artículo 1 | Disposiciones generales | …/eli/cl/ley/1999/19628/art_1/es@1999-08-28 | 141599#8642681 |
| STATE_CL_LEY19628_TI_A4 | Ley 19.628, art. 4 | Ley 19.628 / Título I / Artículo 4 | De la utilización de datos personales | …/eli/cl/ley/1999/19628/art_4/es@1999-08-28 | 141599#8642685 |
| STATE_CL_LEY19628_TIII_A17 | Ley 19.628, art. 17 | Ley 19.628 / Título III / Artículo 17 | De la utilización de datos personales relativos a obligaciones … | …/art_17/es@2022-11-10 | 141599#8642700 |
| STATE_CL_LEY19628_DT_A1T | Ley 19.628, art. 1 transitorio | Ley 19.628 / Disposiciones transitorias / Artículo 1 transitorio | Disposiciones transitorias | …/art_1_transitorio/es@1999-08-28 | 141599#8642712 |

Text of art. 1 begins "El tratamiento de los datos de carácter personal en registros o bancos de datos por organismos
públicos o por particulares se sujetará a las disposiciones de esta ley …" (the source's 60-character line wrapping
is undone, paragraph breaks kept). Levels seen: Título (with Preliminar/I-V/Final), Artículo, Disposición
Transitoria; the schema also has Libro, Capítulo, Párrafo.

### 3.3 Japan, 行政手続法 (平成5年法律第88号, law_id 405AC0000000088), enforcement 2026-07-24 — 76 rows

| act_id | citation | display_path | section_title | eli |
|---|---|---|---|---|
| STATE_JP_405AC0000000088_C1_A1 | 行政手続法第一条 | 行政手続法 / 第一章　総則 / 第一条 | 目的等 | …/eli/jp/act/1993/88/art_1/ja@2026-07-24 |
| STATE_JP_405AC0000000088_C3_S1_A13 | 行政手続法第十三条 | 行政手続法 / 第三章　不利益処分 / 第一節　通則 / 第十三条 | 不利益処分をしようとする場合の手続 | …/art_13/ja@2026-07-24 |
| STATE_JP_405AC0000000088_SP1 | 行政手続法附則 | 行政手続法 / 附則 | | …/suppl_1/ja@2026-07-24 |
| STATE_JP_405AC0000000088_SP17_A1 | 行政手続法附則（令和八年七月二四日法律第六六号）第一条 | 行政手続法 / 附則（令和八年七月二四日法律第六六号） / 第一条 | 施行期日 | …/suppl_17_art_1/ja@2026-07-24 |

Article text keeps paragraph numbers and item titles as the source gives them, one per line (`２　次の各号の…`,
`　一　…`), so a verbatim quote can be checked character for character against the API. 48 main-provision articles
plus 17 supplementary provisions (附則) with their own articles; `word_count` is a character count for Japanese.

### 3.4 Quote verification in the source language

lexflow's verification model quotes the source verbatim; nothing in it assumes English. What the prototypes show:

* Spanish: `index.phrase()`/`match()` keep `[A-Za-z0-9]+` words only, so accented words lose their accents in the
  query ("utilizaci n" → two tokens); FTS5 `unicode61 remove_diacritics 2` still matches, but the tokeniser must be
  extended to `\w` for exact phrases. The porter stemmer is English-only: Spanish inflections are not stemmed
  (retrieval recall, not quote accuracy).
* Japanese: unicode61 splits only at punctuation and script changes, so terms standing as their own run are found
  (`"聴聞"` matches 14 rows, `"行政庁は"` 16) but `index.phrase("聴聞")` returns None. Japanese search needs an FTS5
  `trigram` tokenizer (or a segmenter) and query helpers that pass CJK through; the test records the gap.
* Verbatim checks themselves (substring of the indexed text) work in any script; the fixtures carry the source's
  own characters (ideographic spaces, full-width digits) untouched.
* Translations (Japan's JLT) are a second expression of the same work: index them as `language = "en"` rows
  pointing at the same ELI work IRI, flagged unofficial, never as the quoted authority.

## 4. Identifier and schema points to decide (docs/design/wikibase-schema.md §4.1)

1. **Jurisdiction keys**: `lexflow:code:<cc>` / `lexflow:unit:<cc>:…` / `lexflow:statute:<cc>:<ref>` work with
   ISO alpha-2 codes, but `cl`/`co`/`de`/`in`/`id`/`ms`/`mt`/`nc`/`pa`/`sc`/`md`/`ar`/`ga`/`la`/`ma` collide with US
   postal codes. Decide: a `us-` prefix for the states' keys in version 3, or country keys as `lexflow:code:cc-jp`.
   The prototypes' `act_id` keeps `STATE_<CC>_…` so the token helpers work unchanged; rename the prefix (e.g. `JUR_`)
   in the same decision.
2. **Language tags**: labels, heading text and the quoted text need a language (`es`, `ja`, `ro`, `en-AU`); today
   the wiki writes monolingual English. Decide: `heading text` as monolingual text with the law's language, labels in
   the law's language plus an English alias where an official translation exists.
3. **Monolingual quotes**: a quote item/claim must carry the language of the text it quotes; verification compares
   within that expression (the `…/ja@2026-07-24` ELI), never across translations.
4. **Codes without sections**: civil-law countries cite articles (Artículo, 条, Articol) and some laws have only
   paragraphs (元号法). `unit level` needs `article` as a leaf level and `paragraph` below it; `section number`
   becomes `unit number` or gets a sibling `article number`.
5. **Civil-law hierarchy**: Libro/Título/Capítulo/Párrafo/Artículo (Chile), 編/章/節/款/目/条/項/号 (Japan),
   Carte/Titlu/Capitol/Secțiune/Articol (Romania), Part/Division/Subdivision/section (Australia): the `unit-level`
   vocabulary needs `book`, `paragraph` (Párrafo as a unit, 項 as a sub-article), `item` (号) and `supplementary
   provision` (附則 / disposiciones transitorias), with the country's own label kept as the item label.
6. **ELI**: Romania supplies real ELIs; for the others lexflow mints `…/eli/{cc}/{type}/{year}/{number}/{unit}` and
   the expression `/{lang}@{date}`. Decide whether minted IRIs stay under lexipedia.wikibase.cloud or the country's
   own id (LeyChile idNorma, e-Gov law_id, register id) becomes the external identifier property and the ELI only a
   derived label.
7. **Effective dates**: the country rows carry `effective_from` per unit (LeyChile's `fechaVersion`, e-Gov's
   enforcement date); index._build derives dates from the heading text only, so a build-time hook for a supplied
   column is needed before point-in-time answers.
8. **Subnational layers**: Australian states as jurisdictions with P15 → Australia (like US states) rather than
   units under the Commonwealth code.

## 5. Registry proposal (municipal/states.py → a jurisdictions registry)

Wikidata items verified read-only against the item pages on 19 October 2026 (`/w/api.php` is disallowed to
crawlers by Wikidata's robots.txt, so the HTML item pages were read instead):

| code | name | Wikidata | legal-code label | language |
|---|---|---|---|---|
| pe | Peru | Q419 | Legislación peruana (SPIJ) | es (+ qu, ay) |
| cl | Chile | Q298 | Legislación chilena (Ley Chile) | es |
| au | Australia | Q408 | Commonwealth Acts (Federal Register of Legislation) | en; subnational nsw, vic, qld, wa, sa, tas, act, nt |
| ro | Romania | Q218 | Legislația României (Portal Legislativ) | ro |
| gh | Ghana | Q117 | Acts of the Parliament of Ghana | en |
| jp | Japan | Q17 | 日本の法令 (e-Gov法令検索) | ja |

The same list is `lexflow.corpus.countries.JURISDICTIONS`.

## 6. Approval list: bulk downloads for a full pull

Nothing below has been downloaded. Rates are the source's own or 1 request per 2 s where none is stated.

| Country | What | Source and format | Estimated size | Polite rate | Estimated index |
|---|---|---|---|---|---|
| Japan | `all_xml.zip` (every law as 法令標準XML) | https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true, one zip | not announced; estimate 200-300 MB zipped, ~1.5 GB XML, ~9,600 laws | one download; refresh via `/laws` `updated` filter | ~350k article rows, ~1 GB SQLite (body + FTS); `countries_jp.sqlite` |
| Japan (translations) | selected laws' English XML | JLT per-law downloads, PDL1.0 | ~900 laws, ~200 MB | 1 per 2 s | ~60k rows, separate `language=en` |
| Australia (federal) | Titles + latest Version per in-force Act and LI; compiled HTML per version | OData `Titles`/`Versions` JSON + HTML per version | 4,774 Acts × ~300 KB ≈ 1.4 GB; instruments (~20k) ≈ 4 GB more | Crawl-delay 10 s → ~27 h for Acts alone | ~250k sections for Acts, ~600 MB |
| Australia (states) | QLD XML via API (account), SA XML packages (CKAN), TAS/WA HTML | per state | QLD ~21k docs ≈ 2 GB XML; SA packages ≈ 500 MB; TAS/WA ≈ 1 GB | QLD/SA bulk; TAS/WA 1 per 2 s | ~400k sections combined |
| Chile | leyes in force only (scope to agree with BCN) | obtxml XML per norma (48 KB avg) after an API key / written authorisation; SPARQL for the list | ~22k leyes ≈ 1 GB; all 360k normas ≈ 14 GB | API quota 500/day makes any unauthorised pull impossible (720 days); with a convenio 1 per 2 s | leyes: ~800k articles, ~2 GB |
| Ghana | Acts PDFs from the Parliament repository + OCR | DSpace bitstreams | ~1,500 PDFs × 2 MB ≈ 3 GB | 1 per 3 s | ~60k sections after OCR |
| Romania | acts via the SOAP service | unverified | ~240k acts, unknown | unknown | unknown |
| Peru | SPIJ | unverified | ~1.4 M norms (LDH) | unknown | unknown |

## 7. Open problems

* Chile's licence (CC BY-NC-ND) and API conditions conflict with a mirror; lexipedia's non-commercial, attributed,
  unmodified-text use fits NC and ND for quoting, but "reconstruct a database substantially equivalent" is exactly
  what an index is. Needs BCN's agreement or a per-question fetch design (cache per law, bounded, under the 500/day
  key).
* Romania and Peru (SPIJ) could not be read from this network; both verdicts rest on pointers. Re-run the checks from
  another network before scheduling them.
* GhaLII blocks document fetches (403) and forbids scraping; the official Parliament PDFs are as-passed with no text
  layer. Ghana needs either an agreement with GhaLII/Laws.Africa or an OCR pipeline and no consolidation.
* Search helpers are ASCII-only (`index.phrase`), the stemmer is English; CJK needs a trigram tokenizer and Spanish a
  `\w` tokeniser; both are index-wide changes (lexflow/ask/index.py).
* The wiki schema has no language on labels/quotes, no `article`/`paragraph` leaf levels and no jurisdiction prefix
  that separates `cl` (Chile) from US states' codes (§4).
* Fixture texts: the Chile sample is one law's text under CC BY-NC-ND with attribution in the fixture; the Japan
  sample is PDL1.0 with the 出典 line. Keep fixtures to one law per country.
