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
| Japan | e-Gov 法令検索, Digital Agency (laws.e-gov.go.jp) | all national laws and regulations in force, consolidated, with revisions | 法令標準XML, JSON tag tree | REST API v2 (no key), official bulk XML zip, OpenAPI spec | law_id (405AC0000000088), law_num; no ELI | PDL1.0 (= CC BY 4.0 compatible): "複製、公衆送信、翻訳・変形等の翻案等、自由に利用できます ... 商用利用も可能です"; API and bulk download are the published machine access | continuous (`updated` per revision) | ja; unofficial en translations (MoJ, PDL1.0) | 9,567 laws listed (8,981 in force); bulk zip 283 MB announced, 297,489,146 bytes, 3.3 GB of XML, 10,469 revisions | **pulled 22 Oct 2026 (§8): 484,159 article rows, `statutes_jpn.sqlite`** |
| Chile | Ley Chile, Biblioteca del Congreso Nacional (bcn.cl/leychile) + datos.bcn.cl LOD | every norma, consolidated, versioned | XML (own schema), HTML, PDF; RDF | per-document XML endpoint (works without key); API Ley Chile with key, 500 req/24 h; SPARQL (Crawl-delay 10) | idNorma/idParte; datos.bcn.cl URI cl/{tipo}/{org}/{fecha}/{numero}; no ELI | CC BY-NC-ND 4.0; API conditions prohibit "extracciones masivas, sistemáticas o automatizadas ... para replicar, reconstruir o generar una base de datos sustancialmente equivalente a Ley Chile" without express authorisation | continuous (`fechaVersion`) | es | 359,739 root normas, 748,821 versions (SPARQL count) | **prototype written; full pull only by agreement with BCN** |
| Australia (federal) | Federal Register of Legislation, OPC (legislation.gov.au) | Acts, legislative/notifiable instruments, gazettes; as made and compiled point-in-time | HTML (from ePub), PDF, DOCX, ePub; OData JSON | OData v4 API (`api.prod.legislation.gov.au/v1`), sitemap; Crawl-delay 10 | register id C1901A00002 / compilation C2026C00117; no ELI | CC BY 4.0 with prescribed attribution ("Sourced from the Federal Register of Legislation at [date] ...") | daily | en | 132,603 titles; 4,774 Acts in force (principal + amending) | **stub with verified sources; second to implement** |
| Australia (states) | QLD, WA, TAS, SA: CC BY 4.0 (QLD API with account, SA XML packages on data.sa.gov.au); NT: own permissive policy; VIC: copyright, "personal use only"; ACT: all rights reserved, document views disallowed to robots; NSW: 403 to all automation | Acts and subordinate legislation | XML (QLD, SA), HTML, PDF | varies | state ids | see §2.3 | varies | en | QLD ~21,000 documents (LDH count) | QLD/SA/TAS/WA after federal; VIC/ACT/NSW need permission |
| Ghana | Parliament of Ghana Library Repository (repository.parliament.gh, DSpace 7) | Acts as passed, by Parliament, EIs, Hansard | PDF (+ mostly empty text bitstream) | DSpace REST API (open), sitemap | handle 123456789/n | "an open access electronic archive" (no reuse licence stated); robots allows API and items | as items are deposited | en | 1,538 items match "Act"; PDFs 0.4-5 MB | **stub; official but PDF-first, OCR needed; consolidation only via GhaLII by agreement (its terms forbid scraping; AKN pages answered 403)** |
| Peru | SPIJ (MINJUSDH): official consolidated texts; Congreso archive (PDF); gob.pe normas (PDF); El Peruano (PDF) | consolidated (SPIJ) vs as-published (others) | HTML (SPIJ, reported), PDF | SPIJ REST API reported, unreachable from here; Congreso robots disallows PDFs; gob.pe pages allowed | SPIJ ids; norm numbers | SPIJ terms unread; others have no licence page | daily (gazette) | es (+qu) | SPIJ ~1.4 M norm ids (LDH) | **stub; blocked until SPIJ's terms are read from a reachable network** |
| Romania | Portal Legislativ, Ministerul Justiției (legislatie.just.ro) | all acts since 1989, consolidated; native ELI | HTML; SOAP XML with full text (reported) | SOAP FreeWebService (reported) | ELI `legislatie.just.ro/eli/{tip}/{an}/{numar}` | unverified: the host closed every TLS connection from the research network and the browser pane | daily | ro | ~240,000 acts (LDH) | **stub; best identifier story, re-verify from another network** |

Recommended order of implementation: **Japan** (open licence, clean structured API, official bulk file; pulled and
indexed on 22 October 2026, §8), **Australia federal** (CC BY 4.0, OData with versions, only an HTML section splitter to write), **Chile**
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
file, stable ids. Implemented (`japan.py`) and pulled on 22 October 2026 (§8).

Re-read on 22 October 2026 (approved pull): the bulk page (https://laws.e-gov.go.jp/bulkdownload/) lists
"すべての法令データ 283MB" (XML only; the set with images and forms cannot be downloaded at once), per-category zips
(`file_section=2&category_cd=N`) and three months of daily update zips (`file_section=3&update_date=YYYYMMDD`). The
site's 利用規約 (https://laws.e-gov.go.jp/terms/, rendered by the page's script) applies PDL1.0 and gives its own
出典記載例 ("出典：e-Govポータル（https://www.e-gov.go.jp）"); PDL1.0 §1.1 asks for a source statement and, for edited
content, a statement that it was edited and by whom, and forbids presenting edited data as the government's own.
lexflow's statements are `japan.ATTRIBUTION` and `japan.EDIT_NOTE`, kept in
`data/raw/countries/jpn/LICENSE-NOTICE.txt` and in the credits (lexflow/pipeline/credits.py, `E_GOV_LAWS`).
robots.txt is not served (the path returns the application's HTML). The zip holds one folder per revision,
`<law_id>_<enforcement YYYYMMDD>_<amending law_id>/`, and `all_law_list.csv` (one row per revision: 法令種別,
法令番号, 法令名, 法令名読み, 公布日, 改正法令, 施行日, 法令ID, 本文URL, 未施行); 1,487 of its 10,469 revisions are marked 未施行
(not yet in force) and every law has a revision in force. The server sends no Content-Length and answered a
`Range` request with 200 and the whole file, so `japan.download_bulk` records size and SHA-256 and restarts a broken
download. The API's law list (9,567 laws) adds category, abbreviation and ISO dates; its 586 laws that the zip lacks
are 560 repealed or expired and 26 not yet in force.

## 3. What the prototypes produce

### 3.1 Row shape

`Country.to_rows(doc)` yields the open-us-law columns municipal/statutes.py reads (`act_id, citation,
section_number, section_title, chapter_name, display_path, act_status, text, source_url, word_count,
last_amended_year`) plus the country columns `kind, language, eli, native_id, level, country, norm_eli` (the index's
`EXTRA`; `norm_eli` is also a `CITES` column so `index.lookup()` finds a row by its ELI work IRI) and `ref` (the
citation), `effective_from` (the unit's own version date where the source gives one, else the law's) and
`effective_until`. `lexflow/corpus/countries/__init__.py` is a corpus module for lexflow/ask/index.py:
`index.build("jpn")` writes `data/index/statutes_jpn.sqlite` (a country is a jurisdiction of the statutes corpus,
§8) from the country's own download, streamed (`iter_rows`), and `index.build("jpn", corpus="countries")` writes
`countries_jpn.sqlite` (the tests); without a download the rows come from `data/raw/countries/<key>.jsonl` or the
fixture.

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
| STATE_JPN_405AC0000000088_C1_A1 | 行政手続法第一条 | 行政手続法 / 第一章　総則 / 第一条 | 目的等 | …/eli/jp/act/1993/88/art_1/ja@2026-07-24 |
| STATE_JPN_405AC0000000088_C3_S1_A13 | 行政手続法第十三条 | 行政手続法 / 第三章　不利益処分 / 第一節　通則 / 第十三条 | 不利益処分をしようとする場合の手続 | …/art_13/ja@2026-07-24 |
| STATE_JPN_405AC0000000088_SP1 | 行政手続法附則 | 行政手続法 / 附則 | | …/suppl_1/ja@2026-07-24 |
| STATE_JPN_405AC0000000088_SP17_A1 | 行政手続法附則（令和八年七月二四日法律第六六号）第一条 | 行政手続法 / 附則（令和八年七月二四日法律第六六号） / 第一条 | 施行期日 | …/suppl_17_art_1/ja@2026-07-24 |

The bulk XML gives the same 76 rows as the API's JSON (`japan.parse_xml` builds the API's tag tree from the XML;
compared row for row on 22 October 2026), plus each main-provision article's anchor on the e-Gov page as its source
URL (`https://laws.e-gov.go.jp/law/405AC0000000088#Mp-Ch_3-Se_1-At_13`, the page's own element ids `Mp-Pa_/Ch_/Se_/
Ss_/Di_/At_`); a 附則 row links to the law's page (its anchors depend on the amending law). A ministerial ordinance's
or rule's number is unique only per ministry, so its ELI natural number is the law_id (127 collisions otherwise):
`…/eli/jp/ministerialordinance/2020/502m60000100011/art_2-2/ja@2020-04-01`.

Article text keeps paragraph numbers and item titles as the source gives them, one per line (`２　次の各号の…`,
`　一　…`), so a verbatim quote can be checked character for character against the API. 48 main-provision articles
plus 17 supplementary provisions (附則) with their own articles; `word_count` is a character count for Japanese.

### 3.4 Quote verification in the source language

lexflow's verification model quotes the source verbatim; nothing in it assumes English. What the prototypes show:

* Spanish: `index.phrase()`/`match()` keep `[A-Za-z0-9]+` words only, so accented words lose their accents in the
  query ("utilizaci n" → two tokens); FTS5 `unicode61 remove_diacritics 2` still matches, but the tokeniser must be
  extended to `\w` for exact phrases. The porter stemmer is English-only: Spanish inflections are not stemmed
  (retrieval recall, not quote accuracy).
* Japanese (done 22 October 2026): the Japanese index uses the FTS5 `trigram` tokenizer (substring search, no
  segmenter). `index.phrase` keeps Unicode letters and digits (`"聴聞"`, `"行政手続"`; English terms give the phrase
  they gave before), and on a trigram index a phrase of one or two characters, which trigrams cannot match, is
  expanded to the OR of the index's own trigrams that begin with it (`fts5vocab`; every column is indexed with two
  padding characters after it, so no occurrence at the end of a column is missed): `聴聞` finds the same 1,415 rows
  a substring scan finds, `審査` 12,785 of 12,785, in 10-20 ms. A one-character term is capped at 400 trigrams.
  `lookup` takes `行政手続法第13条`, `行政手続法 第十三条` and the ELI work IRI (`norm_num`, `norm_eli`).
* Verbatim checks themselves (substring of the indexed text) work in any script; the fixtures carry the source's
  own characters (ideographic spaces, full-width digits) untouched.
* Translations (Japan's JLT) are a second expression of the same work: index them as `language = "en"` rows
  pointing at the same ELI work IRI, flagged unofficial, never as the quoted authority.

## 4. Identifier and schema points to decide (docs/design/wikibase-schema.md §4.1)

1. **Jurisdiction keys** (decided 22 October 2026): a country's key is its ISO 3166-1 alpha-3 code in lower case
   (`jpn`; then `chl`, `aus`, `rou`, `gha`, `per`; a subnational unit under it as `aus-nsw`), because the alpha-2
   codes `cl`/`co`/`de`/`in`/`id`/`ms`/`mt`/`nc`/`pa`/`sc`/`md`/`ar`/`ga`/`la`/`ma` collide with US postal codes. The
   US states keep their two-letter keys (no version 3 rename). The key names the index (`statutes_jpn.sqlite`), the
   wiki keys (`lexflow:jurisdiction:jpn`, `lexflow:code:jpn`, `lexflow:unit:jpn:<law id>`), the registry
   (`states.COUNTRIES`, `countries.JURISDICTIONS`) and the pickers; alpha-2 is accepted as an alias (`jp`). `act_id`
   is `STATE_JPN_…`, so the token helpers work unchanged. The ELI IRIs keep the alpha-2 jurisdiction (`/eli/jp/…`),
   as ELI publishers write it (the US ones are `/eli/us-va/…`). docs/design/wikibase-schema.md §4.8 has the wiki
   side.
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

The same list is `lexflow.corpus.countries.JURISDICTIONS`, keyed by alpha-3 since 22 October 2026 (`per`, `chl`,
`aus`, `rou`, `gha`, `jpn`; §4.1). Japan is also in lexflow/municipal/states.py `COUNTRIES` (key `jpn`, alpha-2 `jp`,
Wikidata Q17, languages `["ja"]`, legal-code label 日本の法令 / "Laws of Japan", official site
https://laws.e-gov.go.jp/), beside, not inside, the 52 US jurisdictions: code that walks the states never meets it.

## 6. Approval list: bulk downloads for a full pull

Japan's row was approved and pulled on 22 October 2026 (§8); nothing else below has been downloaded. Rates are the
source's own or 1 request per 2 s where none is stated.

| Country | What | Source and format | Estimated size | Polite rate | Estimated index |
|---|---|---|---|---|---|
| Japan (pulled 22 Oct 2026) | `all_xml.zip` (every law as 法令標準XML) | https://laws.e-gov.go.jp/bulkdownload?file_section=1&only_xml_flag=true, one zip | 297,489,146 bytes (283 MB announced), 3.3 GB XML, 8,981 laws in force | one download; refresh via the daily update zips or the `/laws` `updated` field | 484,159 article rows, 2,098 MB SQLite (body + trigram FTS); `statutes_jpn.sqlite` |
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
* Search helpers: CJK is done (trigram, §3.4); the porter stemmer is still English, so Spanish inflections are not
  stemmed (a Spanish index would want `unicode61 remove_diacritics 2` without porter).
* The wiki schema has no language on labels/quotes, no `article`/`paragraph` leaf levels and no jurisdiction prefix
  that separates `cl` (Chile) from US states' codes (§4).
* Fixture texts: the Chile sample is one law's text under CC BY-NC-ND with attribution in the fixture; the Japan
  sample (fixtures/corpus/jpn/sample.json, moved from `jp`) is PDL1.0 with the 出典 line. Keep fixtures to one law per
  country.

## 8. Japan: the pull of 22 October 2026

**Download.** `python -m lexflow.corpus.countries.japan download|laws|notice` (user agent
`lexflow-research/0.1 (https://github.com/alibama/lexflow)`, one download, then the API law list at one request a
second):

| file (data/raw/countries/jpn/) | bytes | SHA-256 | what |
|---|---|---|---|
| all_xml.zip | 297,489,146 | b15f40f03d68c7d6c6cc7f700cd5d1873e2886ccbee4ad437684b9975660f9af | every law in force as 法令標準XML: 10,469 revisions of 8,981 laws, 3,306,875,297 bytes unpacked, and all_law_list.csv |
| laws.jsonl | 9,412,939 | 6f8da4ef1e9b142f81437d610784474da2aa72cbcef2e17d4e34d78322e633c0 | the API v2 law list: 9,567 laws in 10 requests (law_id, law_num, title, kana, abbreviation, type, category, promulgation, amendment and enforcement dates, repeal status) |
| MANIFEST.json, LICENSE-NOTICE.txt | | | sizes, digests, retrieval times; the 出典 and 加工 statements of PDL1.0 in Japanese and English |

**Parse.** `japan.iter_documents` reads the zip entry by entry and keeps, per law, the latest revision in force
(none of the 8,981 laws has only future revisions; 1,487 future revisions are counted per law and not indexed); the
XML becomes the API's tag tree and the prototype's parser makes the rows: one per 条, each 附則 a unit with its own
articles (a 附則 without articles one row), and one 本則 row for a law without articles. Result: **484,159 rows**:
383,078 articles (条; 241,912 in main provisions, 141,166 in 附則), 99,883 附則 without articles and 1,198 本則 rows
(laws without articles); a law holds up to 4,171 rows (地方税法); 142,484,585 characters of text. By type: 4,095 ministerial
ordinances (189,511 rows), 2,310 cabinet orders (85,583), 2,100 Acts (191,485), 409 rules (15,764), 66 imperial
ordinances (1,713), the Constitution (103). The 3,756 deleted articles (削除 as their only text) are kept as rows (lookup finds them; retrieval ranks them down); 別表 (appended
tables), forms and the Constitution's preamble are not rows yet.

**Index.** `index.build("jpn")` streams the rows (one law in memory; peak RSS 367 MB) into
`data/index/statutes_jpn.sqlite`: FTS5 `trigram`, 250 characters of each article in `sec.head`, the `law` table (one
row per law: title, number and its English form, type, category, dates, row counts, e-Gov URLs) and the meta rows
`tokenize`, `laws`, `attribution`, `edit_note`, `source_sha256`. **2,098 MB, built in 354 s.** The US indexes keep
`porter unicode61 remove_diacritics 2`.

**Ask and the dashboard.** `jpn` is a target of the Ask flow (`resolve_targets`, the dashboard's target picker,
`/api/targets` for jpn, jp, Japan or 日本): a Japanese question plans from its own kanji and katakana runs
(`plan.cjk_groups`; the thesaurus and the local model's prompt are English), retrieval is lexical (the embedding and
learned relevance models were trained on English sections), the quotes are the articles' own lines (`answer.
cjk_clauses`) and every answer carries the PDL1.0 source statement; steps, a model summary and court cases are not
made for Japanese yet. The home map's holdings card shows the country indexes beside the states' (`totals.countries`),
and the Query page runs `law-in-order` with `unit=lexflow:code:jpn` (the laws in order of promulgation) and
`law-tree` with `section=lexflow:unit:jpn:<law id>`.

**Wiki (dry run only).** One item per law, never per article (docs/design/wikibase-schema.md §4.8): the code item
`lexflow:code:jpn`, the jurisdiction `lexflow:jurisdiction:jpn` and 8,981 statutory units at level `act`, with `ja`
labels, descriptions and aliases, heading text and law number as monolingual `ja` text, the e-Gov law_id as act
identifier, the e-Gov page as official text, the enforcement date of the indexed version as effective date, the
promulgation date, and a topic for the 1,432 laws whose e-Gov category maps to one. `LEXFLOW_LAW_TYPES=Act` (or
`Act,CabinetOrder`) limits the law items to a subset for a first push. `lexflow wikibase lint --no-ollama` holds no
Japanese item (its 24 held items are US drafts and two local items, as before). `lexflow wikibase push --dry-run
--no-drafts --resume` (live reads, 22 Oct 2026 13:20 UTC): creates 10,115 (8,981 Japanese laws, the code, the
jurisdiction, 4 unit levels, 3 properties, and 1,125 pending US items), updates 10,377. Japan alone (`--states jpn`):
pass 1 creates 8,990, pass 2 writes about 8,988 (one clear per law item, the code, the jurisdiction, 5 vocabulary
items), about 17,980 writes. At the measured pass-2 write rates of the earlier pushes (2,978 writes in 61 min on 16
Oct, 0.81/s; 1,889 in 67 min on 18 Oct, 0.47/s) that is 6.2 to 10.6 hours for every law; Acts only (2,100 laws,
about 4,220 writes) 1.4 to 2.5 hours; Acts and Cabinet Orders (4,410 laws, about 8,840 writes) 3.0 to 5.2 hours.
The operator runs the real push, after a Japan-only lint (`lexflow wikibase lint --no-ollama --no-drafts --states
jpn`: 8,987 items checked, none held; the full report holds 24 US items, which `--really` refuses):
`LEXFLOW_LAW_TYPES=Act lexflow wikibase push --really --no-drafts --states jpn --resume` for the Acts first, then
the same without the variable for the rest (set the variable for the lint too).

## 9. Progress: Australia (federal and states), Chile, Romania, Peru and Ghana (22 October 2026)

Approved by the operator ("push hard on the rest"): the §6 downloads whose source licence allows reuse and automated
access. Everything that needs an account or a written agreement is prepared for the operator instead. Keys are ISO
3166-1 alpha-3 (`aus`, `chl`, `rou`, `gha`, `per`); the Australian states are `aus-<abbr>` (`aus-tas`, `aus-sa`,
`aus-wa` ...) with `parent: "aus"` and ELI jurisdiction `au-<abbr>`; the ELI keeps alpha-2 (`/eli/au/`, `/eli/cl/`,
`/eli/ro/`). Every pull below is read-only, paced, resumable, and keeps its source files so a parser change needs no
network (`reparse`).

| Key | Source | Status | Acts | Rows | On disk | Job / log |
|---|---|---|---|---|---|---|
| aus | Federal Register of Legislation | **pulling** (principal Acts first, then amending; ETA about 02:30 UTC 23 Oct) | 4,776 in force listed (1,261 principal) | 81,107 from 930 Acts (15:51 UTC) | 181 MB rows, 73 MB ePub so far | `/data/jobs/aus-pull.sh`, `/data/jobs/aus-pull.log`; index after the pull: `/data/jobs/aus-index-after-pull.sh`, `aus-index.log` |
| aus-tas | Tasmanian Legislation Online | **pulled**, indexed | 609 | 34,220 (33,610 in force indexed) | 62 MB rows, 126 MB XML; index 104 MB | `/data/jobs/aus-tas-pull.sh`, `.log` |
| aus-sa | DataSA XML packages + 2018 RTF snapshot | **pulled** (569 of 571 Acts in force), indexed | 569 | 33,609 (33,583 indexed) | 71 MB rows, 91 MB XML, 81 MB RTF zip; index 122 MB | `/data/jobs/aus-sa-pull.sh`, `.log`; `baseline aus-sa` |
| aus-wa | Western Australian Legislation | **pulled**, indexed | 811 | 51,131 | 101 MB rows, 302 MB HTML; index 169 MB | `/data/jobs/aus-wa-pull.sh`, `.log` |
| aus-qld | Queensland Legislation | needs an account (API) | | | | sign-up steps below |
| aus-nsw, aus-vic, aus-act, aus-nt | | need permission | | | | below |
| chl | Ley Chile (BCN) | needs authorisation; interim per-question mode | sample (Ley 19.628) | 27 | cache ≤ 300 normas | `docs/design/requests/bcn-chile.md` |
| rou | Portal Legislativ FreeWebService | **sample pulled** (50 acts, approved), indexed | 50 | 352 | 1.6 MB; index 1.6 MB | `/data/jobs/rou-sample.log` |
| per | SPIJ | unreachable; licensed beyond its free part | | | | below |
| gha | Parliament of Ghana repository | needs written permission | | | | below |

### 9.1 Australia, federal (`australia.py`)

Measured on the API (`https://api.prod.legislation.gov.au/v1/`, OData v4, no robots.txt; the site's robots.txt has
`Crawl-delay: 10`, which the pull keeps for both hosts): entity sets are lower case (`titles`, `versions`,
`documents`); `$top` is at most 500; `$count` on a filter returns a wrong number (the minimum long), `@odata.count` in
a page is right; `isPrincipal` cannot be filtered on (the server throws), so it is selected and filtered locally;
`$expand=versions($filter=...)` fails ("could not be translated"). `titles?$filter=collection eq 'Act' and isInForce
eq true` lists **4,776 Acts in force, 1,261 of them principal**; `versions?$filter=isCurrent eq true and
contains(titleId,'A')` gives each Act's current compilation (150 Acts in force have none); `documents/find(titleid=
...,asatspecification='Current',type='Primary',format='Epub',uniqueTypeNumber=0,volumeNumber=0,
rectificationVersionNumber=0)` returns the current compilation as **one ePub holding every volume** (the Income Tax
Assessment Act 1997: 12 volumes, 4.5 MB, 4,650 sections), named by its register id (`C2026C00117.epub`). Formats
offered per version: Word, ePub, PDF (no XML); the ePub's XHTML keeps the OPC Word styles, the most structured form
served. The point-in-time page `https://www.legislation.gov.au/<titleId>/<start>/<start>/text` is the rows'
`source_url`.

Parser: `ActHead1`..`ActHead4` are heading depths whose unit word is read from the text (a Schedule is an
`ActHead1` and its Chapters `ActHead2`), `ActHead5` a section (`CharSectno`), `ActHead6`..`ActHead9` amending
schedules; the oldest compilations use `<h1>`..`<h6>` for the same depths and `NotesSection` for the endnotes.
Dropped: the contents (`TOC*`), running headers, tables of sections (`TofSects*`), endnotes. Headings that are not
units ("Guide to Division 245", "Operative provisions") stay in the path without a level or token. A schedule with
Chapters or Divisions numbers sections (`Competition and Consumer Act 2010 sch 2 s 18`), otherwise clauses (`Privacy
Act 1988 sch 1 cl 1`); a number used twice is qualified by its unit (`Corporations Act 2001 pt 1.5 s 1`, the small
business guide); old schedule headings ("The First Schedule", "Schedules—The Second Schedule") become `sch 1`,
`sch 2`. No-break spaces and hyphens (U+2011) are normalised; nothing else in the text changes. Checked on the Acts
Interpretation Act 1901 (83 rows), Privacy Act 1988 (354), Competition and Consumer Act 2010 (2,026), Corporations
Act 2001 (4,371), Income Tax Assessment Act 1997 (4,650).

Timing: the first 50 Acts took 8.0 min (**9.6 s per Act**, one request per Act at the 10 s pace), so the 4,776 Acts
take about **12.7 hours**; started 13:09 UTC, restarted at 13:17, 14:18 and 14:36 after parser fixes (each time with
`reparse` of the Acts already fetched, from their saved ePubs), and resumed at 14:41 after the container was
recreated (the log shows "508 done, 4268 left": a resume, not a restart); expected to finish about 02:30 UTC on 23
October. Principal Acts come first (done after about 3.5 hours), then the 3,515 amending Acts in force (one row per
amended Act per schedule). Rows average 2.3 KB; the federal corpus is estimated at 130,000 to 150,000 rows, 300 to
350 MB of JSONL. A waiting job (`/data/jobs/aus-index-after-pull.sh`, log `/data/jobs/aus-index.log`) builds
`data/index/countries_aus.sqlite` when the pull ends; a partial index from the first 467 Acts (42,085 sections, 162
MB, 18 s, 100 MB of memory) was built at 14:39 UTC.

    # inside the container (cd /app); rerun to resume; reparse rebuilds rows from the saved ePubs
    nohup sh /data/jobs/aus-pull.sh >> /data/jobs/aus-pull.log 2>&1 &
    python -m lexflow.corpus.countries.australia status      # counts, sizes, errors (MANIFEST.json too)
    python -m lexflow.corpus.countries.australia reparse

Files: `data/raw/countries/aus/list.jsonl` (the Acts and their compilations), `epub/<registerId>.epub`,
`rows/<titleId>.jsonl` (one file per Act, written whole then renamed), `progress.jsonl`, `MANIFEST.json`,
`LICENSE-NOTICE.txt` (the prescribed attribution with the download date). Each row carries `title_id`,
`register_id`, `compilation_number`, `compilation_date` and `fetched`. The credit is `FEDERAL_REGISTER_AU` in
lexflow/pipeline/credits.py.

Index: `countries.path_for("aus")` is the rows directory (`Australia.raw_name = "aus/rows"`), and
`countries.iter_rows` streams it one Act at a time (`_iter_dir`, with a `law` table row per Act from
`australia.law_summary`), so `index.build("aus", corpus="countries")` never holds the corpus in memory.

### 9.2 The states (`australia_states.py`)

* **Tasmania** (`aus-tas`, pulled, 21 min): the browse page's own data source lists the Acts in force
  (`/projectdata?ds=EnAct-BrowseDataSource&expression=PrintType=act.reprint AND Repealed<>Y AND Amending<>pure AND
  PitValid=@pointInTime(...)`, 609) and each Act is EnAct XML at `/view/whole/xml/inforce/current/<id>` (numbers in
  attributes, written out as the HTML shows them: `(1)`, `(a)`, `Penalty:`, `Charge:`; `HOWAFFECTED` notes dropped;
  `OMITTED` provisions not indexed). Attribution (changed material): "Based on material from the Tasmanian Legislation
  website at [full date of download]. ...". The Criminal Code is Schedule 1 of its Act: `Criminal Code Act 1924 sch 1
  s 156`.
* **South Australia** (`aus-sa`, pulled): the 231 XML update packages (17 Nov 2017 to 9 Oct 2026, 1.8 GB read, not
  kept) give the newest XML of the **365 Acts amended since 2017**; the package's `titleindex.pdf` (read into
  `titleindex-2026-10-09.json`, 571 Acts in force, 10 uncommenced) filters out 20 no longer in force (repealed or
  replaced, or not yet commenced) and confirms the versions (343 of 345 match the index's version date; two are one
  version behind). The **224 Acts never amended since** come from DataSA's last full snapshot on DataSA (23 March
  2018, RTF, the "Legislative Database" dataset, CC BY 4.0, 81 MB), read by a small RTF reader (OPC styles
  `partheadlevel1`, `divisionheadlevel2`, `clauseheadlevel1-4`); only Acts whose current version is not newer than
  the snapshot are taken. **569 of 571 Acts in force**; missing: ANZ Executors & Trustee Company (South Australia)
  Limited (Transfer of Business) Act 1996 and Cape Jaffa Lighthouse Platform (Civil Liability) Act 2005 (not in the
  snapshot). The dataset says "To request an up-to-date version of this dataset, please email OPCWeb@sa.gov.au" — a
  full current XML export would replace the replay and the RTF; that request is the operator's to send.
* **Western Australia** (`aus-wa`, pulled in 2 h 10 min with one resume, one Act retried after a broken read;
  51,131 rows): the Acts-in-force letter pages (811 Acts), each Act's
  page (currency start, version suffix, Act number), the consolidation's Word-exported HTML (`Heading2` Part,
  `Heading3` Division, `Heading5` section with `CharSectno`, `y*` styles inside schedules, `Footnote*`/`Ednote*` and
  the raised footnote marks dropped, `nHeading2` ends the text). Three requests per Act (page, document, its
  redirect), paced so the average stays one per 2 s. Attribution: "Based on content from the Western Australian
  Legislation website at [full date of download]. ...".
* **Queensland** (`aus-qld`, not approved: account). Steps for the operator: read the "Queensland Legislation API
  Access Agreement" (https://www.legislation.qld.gov.au/api/usage-guidelines: registration needs a name and e-mail;
  credentials may not be shared; content CC BY 4.0; no implied endorsement); register at
  https://www.legislation.qld.gov.au/api/signup (tick "I have read and agree to the terms of the usage guidelines");
  put the credentials in `.env` (names to be chosen when the API's auth scheme is visible: `api.legislation.qld.gov.au`
  answers 401 without an `Authorization` header, so its Swagger description could not be read). Then the EnAct
  reader that reads Tasmania applies. Alternative for the operator to decide: the public website runs the same EnAct
  platform, its robots.txt disallows only `/admin/`, `/view/html/compare/`, `/view/xml/compare` and `/view/pdf/`, and
  its copyright statement is CC BY 4.0, so `Queensland` with `site` set would read `/view/whole/xml/...` as Tasmania's
  does; that route was not on the approval list, so it is not used.
* **New South Wales**: every automated request answers 403 (robots.txt too): ask the NSW Parliamentary Counsel's
  Office for API or bulk access and a reuse licence (the site is EnAct too). **Victoria**: "Authorised electronic
  versions ... for personal use only": a written licence from the Office of the Chief Parliamentary Counsel to
  reproduce the Acts in an index that quotes them, plus permission for automated access. **ACT**: "All rights
  reserved" (JACS policy) and robots.txt disallows `/View/` and `/html/`: a licence and access permission from the ACT
  Parliamentary Counsel's Office. **Northern Territory**: its 1996 policy permits publication on conditions, but NT is
  not on the approval list: the operator reads the conditions and approves first.

### 9.3 Chile (`chile.py`, interim mode)

No bulk pull (CC BY-NC-ND and the API conditions §3 e vi-vii). The request for an API key and express
authorisation, in Spanish and English, with the clauses it answers, is `docs/design/requests/bcn-chile.md`, for the
operator to send in his own words. Interim mode: `Chile.find(number)` asks datos.bcn.cl for the norma a question
cites by number (an equality lookup answers in under a second; a title-word `CONTAINS` search and an `ORDER BY` over
every ley both timed out after 60 s), and `Chile.on_demand(ids)` fetches at most 3 normas per question and 100 a UTC
day (a fifth of a key's 500 per 24 h) into a cache of at most 300 normas refreshed weekly
(`data/cache/countries/chl/`); `rows_on_demand` adds the attribution. The LOD vocabulary as the endpoint uses it: a
version is a `bcn:Norm` with `bcn:leychileCode`, `dc:title`, `bcn:isLatestVersion 1` (an integer), `bcn:versionOf`
the root, `bcn:type .../norma/tipo#ley`, `bcn:hasNumber "19628"^^xsd:string` (the earlier `hasLeyChileId` and
`isLatestVersion true` matched nothing).

### 9.4 Romania (`romania.py`)

`https://legislatie.just.ro/` still closes every TLS connection (robots.txt, pages, ELI URIs and terms unread), but
plain HTTP answers for the web service: `http://legislatie.just.ro/apiws/FreeWebService.svc?wsdl` (WCF SOAP 1.1;
`GetToken`, then `Search(SearchModel{NumarPagina, RezultatePagina, SearchAn, SearchNumar, SearchText,
SearchTitlu}, tokenKey)` returning `Legi{DataVigoare, Emitent, LinkHtml, Numar, Publicatie, Text, TipAct, Titlu}`
with the whole text). Pages are numbered from 1 (0 and 1 are the same page); `SearchAn` weighs rather than filters.
The texts are the acts as published or republished, not the portal's consolidations. The approved sample: the 50
newest laws for `SearchTitlu=LEGE`, `SearchAn=2026` (352 article rows, most of them amending laws: an amending law's
quoted articles stay in its own article's text). Licence: Law 8/1996 art. 9 lit. b excludes official legislative
texts from copyright; the portal's own terms (and any database right claimed) are unread, so nothing beyond the
sample is pulled. EUR-Lex's national transposition measures give Romanian measures with their Monitorul Oficial
references (metadata, not texts); the Monitorul Oficial site is commercial. Next: read the portal's terms from a
network the HTTPS site accepts, then pull through the service.

### 9.5 Peru and Ghana

* **Peru**: SPIJ (spij.minjus.gob.pe, spijweb, spijlibre) still unreachable on 22 October 2026 from two networks
  (TCP connect timeouts; spijlibre resets TLS). The Ministry's gob.pe page (https://www.gob.pe/748, last changed 13
  September 2023) says part of SPIJ is free ("Normativa de Acceso Libre") and full access needs a subscription and a
  paid licence; no API or reuse terms are published. Recommendation: ask MINJUSDH (the SPIJ office) for API or bulk
  access and reuse terms; until then nothing.
* **Ghana**: the Parliament's DSpace 9.1 repository allows the API in robots.txt, but its End User Agreement (May
  2023) grants a licence "solely for your personal, non-commercial use" and forbids "Systematically retriev[ing] data
  or other content from the Site to create or compile ... a collection, compilation, database, or directory without
  written permission". Five Acts sampled through the API for text layers: three have one (a Word-born 1999 Act, the
  2019 Appropriation Act, a 2024 Act with an OCR layer), two are image-only scans (the 2021 Appropriation Act and
  PNDCL 138 of 1986) whose DSpace text bitstreams are empty. Recommendation: written permission from the Parliament
  of Ghana Library (or a bulk agreement with GhaLII/Laws.Africa for consolidated Akoma Ntoso); no OCR pipeline until
  then.

### 9.6 Changes outside the adapters, and what the shared files still need

* `lexflow/corpus/countries/__init__.py`: the state adapters registered after Australia (and in `JURISDICTIONS`
  with `parent`, `iso3166_2`); `path_for` already honours an adapter's `raw_name`, and a `raw_name` that is a
  directory is streamed by `_iter_dir` (and read by `load`), one law file at a time.
* `lexflow/pipeline/credits.py`: one entry, `FEDERAL_REGISTER_AU`, also in `GENERAL`. The states' attributions are
  in their `LICENSE-NOTICE.txt` and `MANIFEST.json`.
* Not done, for the owners of the shared files: `index.is_country` requires three letters, so `aus-tas` and the
  other state keys build only with `corpus="countries"` (`index.build("aus-tas", corpus="countries")`), not as
  statutes jurisdictions; `municipal/states.py` `COUNTRIES` lists only `jpn`, so `aus` and `rou` are not Ask targets
  yet; the Wikibase schema has no unit level for a schedule or a clause.
* Tests: `tests/test_corpus_countries_more.py` (fixtures in `fixtures/corpus/{aus,aus-tas,aus-sa,aus-wa,rou}/`; the
  Chile fixture moved to `fixtures/corpus/chl/`).

## 10. Brazil (`bra`, 22 October 2026)

Approved by the operator. Research and pull read-only, user agent `lexflow-research/0.1 (https://github.com/alibama/lexflow)`,
at most one request a second per host (the pull keeps two hosts busy at once, one job each), robots.txt obeyed. Key
`bra` (ISO alpha-3; alpha-2 `br` is an alias), Wikidata Q155 (verified on Special:EntityData), language `pt`, ELI
jurisdiction `br`. Adapter `lexflow/corpus/countries/brazil.py`; fixture `fixtures/corpus/bra/` (Lei nº 12.527/2011);
tests `tests/test_corpus_brazil.py`.

### 10.1 Sources and their terms (read 22 October 2026)

* **Copyright.** Lei nº 9.610/1998, art. 8º, read in the Câmara's compilation on normas.leg.br: "Não são objeto de
  proteção como direitos autorais de que trata esta Lei: ... IV - os textos de tratados ou convenções, leis,
  decretos, regulamentos, decisões judiciais e demais atos oficiais;".
* **Normas.leg.br** (https://normas.leg.br/, Congresso Nacional: Senado Federal and Câmara dos Deputados). robots.txt
  `User-agent: * Allow: /`. Every record of its public API states `"license":"https://creativecommons.org/licenses/by/4.0/"`
  (and `sdLicense`); its legal notice: "Este texto não substitui o publicado no Diário Oficial." The help page: the
  portal shows "a compilação estruturada" of the Constitution, the ADCT, the Código de Processo Civil "e também das
  normas federais com força de lei publicadas a partir de 2017. As normas federais com força de lei publicadas antes de
  2017 são disponibilizadas apenas com a compilação convencional." API (read from the site's own script):
  `/api/public/normas?urn=<urn>&tipo_documento=maior-detalhe` (schema.org/ELI JSON-LD: identifiers, dates, ementa,
  popular names, `encoding` with the original publication and the current compilation as HTML at
  `/api/public/binario/<uuid>/texto`; for norms since 2017 also every version of every provision in `hasPart`),
  `/api/public/metadados/simples?urn=`. The current compilation is the Câmara's ("Compilação Monovigente na CD",
  Word-made HTML with the compiler's notes as italic links) or, for the Constitution and the ADCT, the Senado's.
* **The norm list**: the catalogue behind normas.leg.br/busca, `https://legis.senado.leg.br/sigen/api/catalogo/basico?
  anoInicial=&anoFinal=&tamanhoPagina=&pagina=` (pages from 0, up to 1,000 hits a page, 10,000 a query): **37,226
  federal norms "com força de lei"** with URN, number, signature date, ementa, popular names (`apelido`), the revoking
  norm (`urnRevogacao`) and the Senado's status (`Revogada`, `Convertida em Lei`, `Sucedida` ...). Decrees are not in it.
* **Dados Abertos Legislativos do Senado Federal** (https://legis.senado.leg.br/dadosabertos/, OpenAPI 3.1 at
  `/dadosabertos/v3/api-docs`): "uma API de acesso público, sem necessidade de autenticação"; "Mais de 10 requisições
  por segundo estão sujeitas a receber o erro HTTP 429"; the portal (https://www12.senado.leg.br/dados-abertos):
  "Dados Abertos são representados em meio digital, processáveis por máquina, referenciados na rede mundial de
  computadores e disponibilizados sob licença que permita sua livre utilização." `/dadosabertos/legislacao/urn?urn=`
  gives per norm the Diário Oficial publications (date, page, column), the observations, `vides` (later norms acting
  on it: "Declaração de Alteração Permanente", "... Provisória" (a medida provisória), "Declaração de Revogação
  Permanente da Norma no Todo", vetoes, regulations, correlated law, court decisions), each with the affected
  `dispositivo`s and what happened to each (Alteração, Acréscimo, Revogação, Renumeração, Veto ...), `edivs` (earlier
  norms this one acts on) and `disps` (per provision). `/dadosabertos/legislacao/lista` answered 503 "Recurso de dados
  indisponível" throughout. `legis.senado.leg.br/robots.txt` answers 403 (no rules readable).
* **LexML Brasil** (https://www.lexml.gov.br/): robots.txt `Disallow: /busca/`, `Allow: /urn`, `Allow: /sru`,
  `Crawl-delay: 5`. The SRU service the Senado's open-data page documents is `https://www.lexml.gov.br/busca/SRU`, under
  the disallowed path, and it answers a JavaScript "Verificação de segurança — Senado Federal" page (one request
  reached it through the open-data page's redirect; nothing else). `/sru` is 404. No reuse terms are published. Not
  used; the URN scheme (`urn:lex:br:federal:lei:2018-08-14;13709`, partitions `!art5`, `!art55-10` for Art. 55-J) is.
* **Câmara dos Deputados** open data (https://dadosabertos.camara.leg.br/api/v2): deputies, bodies, events, bills,
  votes; no norm texts and no amendment relations. Its compilations reach lexflow through normas.leg.br; its LEGIN pages
  (www2.camara.leg.br/legin, allowed by robots.txt) were read once for the Diário Oficial check below.
* **Planalto** (planalto.gov.br/ccivil_03): every TLS connection closed by the server (Python: "Remote end closed
  connection without response"; curl/Schannel: handshake never completed), robots.txt unread. Not used.
* **Imprensa Nacional** (the Diário Oficial itself): www.in.gov.br robots.txt `Disallow: /`; pesquisa.in.gov.br
  answers "Request Rejected"; the Senado's publication PDF for the Código Penal (`/norma/527942/publicacao/14225750`)
  is empty.

Chosen: (i) the list: the Senado catalogue; (ii) consolidated texts with article structure: the current compilations
on normas.leg.br (structured JSON exists only since 2017, so one HTML parser serves every norm); (iii) amendment and
repeal relations with the affected provisions: the Senado's `vides`, plus the catalogue's `urnRevogacao`.

### 10.2 The pull

    # inside the container (cd /app); every step resumes, keeps its source files, and logs to /data/jobs/
    python -m lexflow.corpus.countries.brazil list            # catalog/<year>.json -> list.jsonl (no network when read)
    nohup sh /data/jobs/bra-all.sh >> /data/jobs/bra-all.log 2>&1 &     # after a container restart: everything below
    sh /data/jobs/bra-texts.sh     # pull-texts: normas record + current compilation + rows, norms in force only
    sh /data/jobs/bra-senado.sh    # pull-senado: the Senado record of every norm of the list
    sh /data/jobs/bra-finish.sh    # waits for both, then pull-texts (retries), publish, reparse, amendments, norms,
                                   # notice, index.build("bra"), status -> data/raw/countries/bra/STATUS.json
    python -m lexflow.corpus.countries.brazil status | reparse | amendments | norms | wikidata | publish

Scope: the list holds **29,416 norms** of the indexed kinds (16,609 laws, 12,352 decree-laws, 240 complementary laws,
189 constitutional amendments and 6 of revision, 13 delegated laws, 6 constitutions and the ADCT); **28,156 are in
force** by the catalogue (no `urnRevogacao`, no status Revogada / Inconstitucional / Rejeitada / Sucedida ...; the
amendments of the 1946 and 1967 constitutions and the five older constitutions are not): 15,892 laws, 11,881
decree-laws, 223 complementary laws, 141 amendments and 6 of revision, 11 delegated laws, the Constitution and the
ADCT. Order: 55 codes people ask about most first (Constitution, ADCT, Código Civil, Código Penal, CLT, CPC, CPP, CDC,
ECA, LGPD, Lei de Acesso à Informação, Lei 4.591/1964 ... `brazil.PRIORITY`), then the amendments, complementary laws,
laws newest first, delegated laws, decree-laws. New rows files wait in `rows-staging/` and are moved into `rows/` (the
index's source) after the priority codes and every 5,000 norms, so the index goes stale a few times, not per norm.
Started 15:17-15:34 UTC; measured at about 2.3 s a norm for the texts (two requests, ETA about 09:30 UTC on 23
October) and 2.6 s for the Senado records (the API slows and answers 503 at times; ETA about 12:00 UTC on 23
October); bra-finish.sh then needs about an hour (reparse and index). 4 recent laws (2024-2025) have no record on
normas.leg.br yet (`errors.jsonl`).

Files under `data/raw/countries/bra/`: `catalog/` (84 MB), `list.jsonl`, `normas/<key>.json.gz`, `html/<key>.html.gz`
(embedded images removed), `senado/<key>.json.gz`, `rows/` and `rows-staging/` (`<key>.jsonl`, key
`lei_2018-08-14_13709`), `amendments.jsonl`, `norms.jsonl` (every norm of the list with number, citation, signature
date, ementa, popular name, status and the original Diário Oficial publication with page and column, from the Senado
record or the normas.leg.br record's name), `errors.jsonl`, `wikidata/`, `MANIFEST.json`, `LICENSE-NOTICE.txt`.

### 10.3 Rows

One row per article; parágrafos, incisos and alíneas stay in the article's text, one per line; the epígrafe above an
article (the Código Penal's "Homicídio simples") is its heading; Parte / Livro / Título / Capítulo / Seção / Subseção
are the path; the compiler's notes ("(Redação dada pela Lei nº 13.964, de 2019)", italic links in the Câmara's HTML or
parenthesised notes in the text) leave the text and are kept with the row (`notes`), except where a provision has no
other words ("VI - (Inciso acrescido ... e revogado pela Lei nº 14.994, de 9/10/2024)"); struck-through wording is
dropped; "(VETADO)" stays (it is the published text). Articles left with nothing but a revocation note are
`repealed`, those with "(VETADO)" alone `vetoed`; both stay in the rows file and are not indexed. The signature line
("Rio de Janeiro, 7 de dezembro de 1940; ...") ends a norm, unless a code with its own articles follows it as an
annex: the CLT is Decreto-Lei nº 5.452/1943's annex, numbered by the Senado and LexML as the decree-law's articles, so
its 922 articles cite as `Decreto-Lei nº 5.452/1943, art. 482` and the decree's own two articles become the unit "Ato
de aprovação" (`!apr_art1`). The Constitution's preamble is a row.

| act_id | citation | display_path | native_id |
|---|---|---|---|
| STATE_BRA_DEL2848-1940_PE_T1_C1_A121 | Decreto-Lei nº 2.848/1940, art. 121 | Decreto-Lei nº 2.848/1940 (Código Penal) / Parte Especial / Título I / Capítulo I / Art. 121 | urn:lex:br:federal:decreto.lei:1940-12-07;2848!art121 |
| STATE_BRA_LEI12527-2011_C3_S1_A11 | Lei nº 12.527/2011, art. 11 | Lei nº 12.527/2011 (Lei de Acesso à Informação) / Capítulo III / Seção I / Art. 11 | urn:lex:br:federal:lei:2011-11-18;12527!art11 |
| STATE_BRA_CON1988-1988_T2_C1_A5 | Constituição Federal, art. 5º | Constituição Federal / Título II / Capítulo I / Art. 5º | urn:lex:br:federal:constituicao:1988-10-05;1988!art5 |
| STATE_BRA_LEI10406-2002_PE_L3_T3_C1_S1_A1228 | Lei nº 10.406/2002, art. 1.228 | Lei nº 10.406/2002 (Código Civil) / Parte Especial / Livro III / ... / Art. 1.228 | ...;10406!art1228 |

ELI `…/eli/br/<type>/<year>/<number>/art_<n>` with the expression `/pt@<the record's dateModified>`; source URL
`https://normas.leg.br/?urn=<urn>!art<n>` (the portal resolves partitions). The act_id's law token carries the year
(`LEI654-1899` and `LEI654-1949` are different laws: 3,386 (type, number) pairs repeat in the catalogue). Measured on the
priority codes: Código Civil 2,079 rows (2,065 in force), CPC 1,073, CPP 832, CLT 935, Código Penal 433 (403 in force),
Constitution 277 (preamble + 276 articles), ADCT 145; recent laws average about 9 rows.

### 10.4 Index and Ask

`statutes_bra.sqlite` (built by `index.build("bra")` from `rows/`, streamed) uses the adapter's own tokenizer
`unicode61 remove_diacritics 2` (`Brazil.tokenize`, read by `countries.tokenizer`; Japan keeps `trigram`, the US and
Australian indexes the statutes' `porter unicode61 remove_diacritics 2`): `"informacao"`, `"informação"` and
`"INFORMAÇÃO"` match the same rows, without the English stemmer. `index.lookup` finds an article however it is cited
(`brazil.cite_key` through `countries.norm_num`, only for citations that open with Lei, Decreto-Lei, Emenda
Constitucional, Constituição, ADCT or CF): `Lei nº 13.709/2018, art. 5º`, `lei 13709/2018 art 5`, `Lei nº 13.709, de
14 de agosto de 2018, art. 5º` -> `lei13709/2018art5`; `CF art 5` -> `cfart5`. With the 55 priority codes: 11,190
sections, 32 MB, 8 s; at 16:50 UTC with 2,301 norms (the codes, every amendment and complementary law, the newest
laws): 29,230 sections, 86 MB, 58 s. The whole corpus is estimated at about 250,000-300,000 articles and 0.8-1 GB
(recent laws average about 9 rows).

Ask: a Portuguese question (`plan.is_portuguese`) plans from its own content words (`plan.pt_groups`: Portuguese stop
words, the other grammatical number of each word, a small Portuguese thesaurus and phrases such as "acesso à
informação", "justa causa", "dados pessoais"), `source="rules-pt"`; retrieval is lexical (the embedding and relevance
models are English) with Portuguese procedure words (`retrieve.ACTION_TERMS_PT`) and a boost for the article whose
first sentence says who ("Considera-se", "somente poderá ser") or within what time ("20 (vinte) dias") when the
question asks "quem pode" / "quem deve" / "prazo"; quotes are the articles' own sentences (the segmenter reads
"§ Lei nº 12.527/2011, art. 11." headers, so each quote names its article) and every answer carries the source
statement. Samples (all quotes verbatim, 0 misses; the first two on the 2,301-norm index of 16:50 UTC, the others
on the priority codes):

| question | status | first articles chosen |
|---|---|---|
| Qual o prazo para resposta a um pedido de acesso à informação? | answered | Lei nº 12.527/2011, art. 11 ("em prazo não superior a 20 (vinte) dias"; § 2º "prorrogado por mais 10 (dez) dias"), arts. 16, 8º, 3º |
| Quem pode ser incorporador? | answered | Lei nº 4.591/1964, art. 31 ("caberão ao incorporador, que somente poderá ser"), arts. 44, 31-B, 29 ("Considera-se incorporador") |
| Quais são os motivos de justa causa para demissão do empregado? | answered | Decreto-Lei nº 5.452/1943 (CLT), art. 482 |
| Qual é a pena para homicídio simples? | answered | Decreto-Lei nº 2.848/1940, art. 121 ("Pena - reclusão, de seis a vinte anos.") |
| O que são dados pessoais sensíveis? | answered | Lei nº 13.709/2018, art. 11 (art. 5º second) |

### 10.5 Amendments

`python -m lexflow.corpus.countries.brazil amendments` writes `amendments.jsonl` in the `law_amendments` shape
(`japan.AMEND_TABLE`: jurisdiction `bra`, law_key the amended norm's URN, amending_key the amending norm's URN (the
catalogue's own, else built from the Senado's name), amending_num `Lei nº 7.209/1984`, date its signature date
(`date_kind` signed), kind `amended` | `repealed` | `repeals`, source, amending_title, retrieved) plus `relation` (the
Senado's words), `provisions` (each affected provision and what happened to it), `published`, `dou` and
`senado_code`. Sources: `senado-dadosabertos` (permanent alterations; whole-norm revocations, with the inverse
`repeals` row), `senado-dadosabertos-mp` (alterations and revocations by a medida provisória, which lapse unless
converted), `senado-catalogo` (the catalogue's `urnRevogacao`, for norms whose Senado record is not read yet). Court
decisions the Senado lists as alterations (Acórdão da ADI / ADPF) are kind `judicial`, kept in the file only; veto
messages and relations whose every item is a veto are part of the enactment and are skipped; "Legislação Correlata",
regulations, "Ressalva" and "Recepção" are not amendments. `brazil.load_amendments(con)` writes the table rows (no
table existed in /data/lexflow.db on 22 October 2026). On the first 1,228 Senado records (16:11 UTC): 1,927 permanent
amended edges on 159 norms by 1,515 amending norms (9,595 provisions), 1,326 by medidas provisórias, 147 court
decisions, 17 whole-norm revocations; plus the catalogue's 1,148 revocations; 36 amending acts have no URN
(Atos do Presidente do Congresso Nacional, the Estado Novo's Leis Constitucionais).

**Código Penal** (Decreto-Lei nº 2.848/1940): the Senado record names **115 amending norms** (113 laws, one
decree-law, one complementary law) touching **606 provisions**, plus 5 court decisions; all 115 resolve to URNs of
lexflow's list. Wikidata's item Q10263220 (read on Special:EntityData, revision 2553153274 of 4 October 2026) carries
P9119 `urn:lex:br:federal:decreto.lei:1940-12-07;2848`, P7588 1942-01-01, P577 1940-12-31 and no P2567 (amended by).

**The Diário Oficial page.** Q10263220's P1433 (Diário Oficial da União, Q3712237) has P304 "2391" and P1932 "D.o.u
de 31/12/1940, pág. nº 2391"; the Senado's record says page **23911**, column 2 (publicação original of 31/12/1940), as
do normas.leg.br ("(p. 23911, col. 2)") and the Câmara's LEGIN record ("Diário Oficial da União - Seção 1 -
31/12/1940, Página 23911"; Coleção de Leis do Brasil 1940 vol. 7 p. 187). The Diário Oficial's own archive could not be
read (www.in.gov.br robots.txt `Disallow: /`, pesquisa.in.gov.br rejects automated requests, the Senado's scan is an
empty file). 23911 is right: the 1940 Diário Oficial numbered its pages through the year, so a page on 31 December
has five digits, and three independent official records agree; Wikidata's 2391 drops the last digit.

### 10.6 Wikidata (read-only) and the Lexipedia registry

query.wikidata.org's robots.txt disallows `/sparql` and www.wikidata.org's disallows `/w/` (the API) but allows
`/wiki/Special:EntityData/*.`; the bulk reads therefore use the QLever Wikidata mirror (https://qlever.dev/api/wikidata,
no robots.txt): 38,018 P9119 statements on its first answer. Its rate limit answered 429 after the first queries and
was still answering 429 at 16:45 UTC; `/data/jobs/bra-wikidata.py` probes every 15 minutes, then saves one query per
property in `wikidata/` and writes the counts to `data/raw/countries/bra/WIKIDATA.json` (bra-finish.sh writes them
again); `python -m lexflow.corpus.countries.brazil wikidata` (offline) prints them: lexflow norms matched by P9119,
items without P2567 / P2568 / P577 / P7589 / P7588 / P1433 / P953, amended-by edges lexflow holds that Wikidata lacks
(both norms with exactly one item), and the Diário Oficial pages that differ from the Senado's.

What `lexflow/publish/wikidata_export.py` needs for Brazil: the `law` table of `statutes_bra.sqlite`
(`countries.laws("bra")`: law_id is the LexML URN, exactly Wikidata's P9119 value, so matching is one equality;
law_num `Lei nº 13.709/2018` for P1031; promulgated is the signature date (P7589); url the normas.leg.br page (P953,
qualifier P407 Portuguese)); `amendments.jsonl` / `law_amendments` rows with kind `amended`, source
`senado-dadosabertos` only (not `-mp`), for P2567 with qualifier P585 = the amending norm's date, and kind `repealed`
for P2568; the Senado record's publication (`brazil.dou_of`, `senado/<key>.json.gz`) for P1433/P304 checks; the
ementa (list.jsonl) for P9376. lexflow has no effective dates (vigência) as data: P7588 cannot be filled from it.

Registry: `bra` is in `countries.JURISDICTIONS` (Q155, `["pt"]`, "Legislação federal brasileira" / "Federal legislation
of Brazil", official sites normas.leg.br, legis.senado.leg.br/dadosabertos, lexml.gov.br, planalto.gov.br) and in
`municipal/states.py` `COUNTRIES` (with `aus`, `aus-tas`, `aus-sa`, `aus-wa` and `rou`, added at the coordinator's
request, their Wikidata items verified on Special:EntityData). The Lexipedia graph (the alignment work) needs for Brazil:
the jurisdiction item `lexflow:jurisdiction:bra` (pt label "Brasil"), the code item `lexflow:code:bra` with pt label
"Legislação federal brasileira", and one statutory unit per law at level `act` (never per article), labelled in `pt`
with the law's citation and popular name, the LexML URN as its act identifier (the P9119 equivalent), the normas.leg.br
page as official text, the signature date, and `amended by` from the amendment rows.

Credit: `NORMAS_LEG_BR` in lexflow/pipeline/credits.py (in `GENERAL`); attribution and edit statements in Portuguese
and English are `brazil.ATTRIBUTION`, `EDIT_NOTE`, `ATTRIBUTION_EN`, `EDIT_NOTE_EN` and `LICENSE-NOTICE.txt`.

### 10.7 Changes outside the adapter

* `countries/__init__.py`: Brazil registered (`ISO3["br"]`, `_adapters`, `JURISDICTIONS`); `tokenizer()` returns an
  adapter's own `tokenize` when it names one; `norm_num()` gives a Brazilian citation Brazil's form (`cite_key`).
* `ask/plan.py`: the Portuguese planner (`is_portuguese`, `pt_groups`, `pt_kind`, `PT_*`); `ask/retrieve.py`:
  `ACTION_TERMS_PT` and `PT_WHO`; `extract/segment.py`: `SECTION_HEAD` also reads a Brazilian citation header.
* `municipal/states.py` `COUNTRIES`: `bra`, `aus`, `aus-tas`, `aus-sa`, `aus-wa`, `rou`; `pipeline/credits.py`:
  `NORMAS_LEG_BR`; `tests/test_corpus_countries.py`: the national keys follow the registry.

### 10.8 Open problems

* Retrieval is lexical: no Portuguese embedding or relevance model, no stemmer beyond the plural forms. Definitions
  can rank below articles that repeat the word (on the priority-only index "Quem pode ser incorporador?" put art. 31
  fourth and art. 29 fifth; with more laws indexed, art. 31 first and art. 29 fourth); a one-law index (the test
  fixture) is too small for the concept weighting to rank by.
* Annexes other than an annexed code (tables, forms, maps after the signature) are not indexed; nor are the "Arts. 1º
  a 3º (Revogados)" ranges as separate articles (they are one row under the first number).
* Effective dates: the Câmara's compilations carry the compilers' amendment dates, not vigência; rows have
  `effective_from` empty and the ELI expression uses the record's `dateModified`.
* 4 laws of 2024-2025 have no record on normas.leg.br yet; Planalto, the Diário Oficial archive and LexML's SRU are
  closed to automated reading from here.
* The Wikidata counts wait for the QLever mirror's rate limit (or a decision that query.wikidata.org may be used as an
  API despite its robots.txt).
