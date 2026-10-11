# Content Credentials (C2PA) and other provenance for lexflow's outputs

_10 October 2026. Research and design only. This note looks at whether C2PA (Content Credentials) can make lexflow's
outputs cleanly auditable, and compares it with in-toto/SLSA, Sigstore, W3C Verifiable Credentials and plain signed
hash logs. The test case is an auditor checking three things about a published process map: it was derived from a
given statute version, by a given pipeline, and was reviewed by a given party. Nothing was installed, downloaded, built,
signed or published. No existing file was edited._

_Method. Specifications, READMEs, release listings and package indexes were read on 10 October 2026. Every request was
read-only, sequential, one page at a time per host, with lexflow's research User-Agent. Release sizes come from the
GitHub releases API and PyPI's JSON API, not from downloading the files. Repository facts come from reading this tree
and from read-only `pip list` and `uname` checks in the `lexflow-app-1` container. `.env` was not read. Each claim is
linked to its source in the text or under [Sources](#sources)._

_Revision (10 October 2026). [verify-canonical.md](verify-canonical.md) found errors in this note, and they are
fixed here:_

- _§2.2: the External Reference assertion has a hashed form;_
- _§2.7 and §6.4: the c2patool argument order;_
- _§3.4: FFDetr through lexflow's adapter, not the FFDNet weights or CommonForms, and the licence statement was
  narrowed to the README;_
- _§5.3: a note on phase numbers._

_Each fix was re-read at its source, read-only._

_Privacy and credit. This note names organisations, standards bodies and software projects only. People appear only as
authors in citations. Nobody is a partner, advisor or endorser of lexflow. This is information, not legal advice._

## Summary

- **C2PA fits part of the chain well, and a few parts not at all.** It is built for files that carry their own history:
  each manifest names its *ingredients* and links to their signed manifests by hash. A validator can walk the chain back
  to the first input. SVG, PNG and PDF can carry an embedded manifest, and the 2.4 spec (April 2026) also covers HTML,
  XML and other text. lexflow's central artifact is different: the process-model JSON. JSON can't hold an embedded
  manifest and is not in the SDK's format list. The statute parquet, the DokuWiki page source and Wikibase items can't
  carry one either. C2PA can only reach them through sidecar files, and the off-the-shelf validators may not be able to
  check those sidecars (§2.4, §9).
- **"Trusted" in C2PA means a certificate from a CA on the C2PA Trust List, and those CAs issue only to products
  that have passed the C2PA conformance programme.** Conformance has no fee. It does need a legal agreement, a
  security architecture document, the Assurance Level 1 security requirements and sample files (§2.8). Until then,
  lexflow's manifests would validate as *Valid*. An auditor who adds lexflow's root certificate to their own validator
  would see them as trusted. That is enough for a sandbox audit and too little for a public trust claim.
- **For the auditor's question, the backbone should be detached, format-agnostic attestations.** The proposal is an
  in-toto Statement with a SLSA Build Provenance predicate for each model release. Its subjects are every published
  file, matched by SHA-256. Its resolved dependencies are the open-us-law file, the section texts, the model or selector
  digests and the lexflow commit. A test-result statement covers the checks, and the reviewer signs a separate review
  statement. All are DSSE-signed, and each is entered in a transparency log: Rekor, signed with a key and not a personal
  identity, or a lexflow-run tile log (§4, §5).
- **C2PA then goes on the files people pass around:** diagrams (SVG, PNG), printed letters and fillable forms (PDF),
  and later the HTML drafts. Each manifest records how the file was made: converted from the BPMN, which was compiled
  from the model, which was extracted from the statute. Each also points to the release statement by hash. These
  credentials can be stripped, so the release statement and log stay the source of truth (§2.9).
- **The provenance data comes first, and that needs no download.** Today's records can't support an audit. Prompt
  and spec hashes are cut to 12 hex characters. Section texts in the model carry no hash. The open-us-law file's
  SHA-256 sits in the `statute_files` table and not in the model. The review is free text. The wiki and Wikibase
  revisions a publish creates are not recorded (§1.3). Fixing these is phase 0 of the plan (§5.3).
- **Downloads for a prototype** (§7, none made): `cryptography` 50.0.2 (4.75 MB) for phase 1 signing; c2pa-python
  0.38.0 (15.3 MB wheel) for phase 2 embedding; c2patool 0.28.2 (12.7 MB) as the auditor's CLI; optionally cosign
  3.1.3 (141 MB) for Rekor logging. All are Apache-2.0 or MIT licensed, or dual-licensed with BSD.

## 1. What an audit has to show

### 1.1 The question

An auditor holds a published process map: a Lexipedia page `lexflow:va:records`, its BPMN media file, its Wikibase
items, and perhaps a draft letter. They want to confirm four things, each by a check they can repeat without trusting
lexflow's word:

1. **Statute version.** The quoted words come from a named release of the statute data (open-us-law v2026.09.1, file
   `us_va_statutes.parquet` with a stated SHA-256), at named sections (act ids) whose text hashes match.
2. **Pipeline.** A named lexflow commit turned those sections into facts, by a stated method, and compiled the facts
   into this exact model, BPMN, DMN and SVG. The method is one of: written by Claude, two local models that agree, or
   the learned selector, with its settings.
3. **Checks.** The stated checks ran on these exact files and gave the stated results: quotes verified, schemas,
   bpmnlint and dmnlint, SpiffWorkflow parse, Petri-net soundness.
4. **Review.** A named party reviewed these exact files, in a stated role and with a stated result. The party is an
   organisation, a role, or "Claude (model id)" recorded by the operator.

Then each published copy must be shown to be byte-identical to what was attested: the wiki revision, the wiki media
file and the Wikibase revision.

### 1.2 The chain, as lexflow runs it today

| Stage | What exists now | Where |
|---|---|---|
| Statute snapshot | One parquet file per state from open-us-law. The download is checked against the SHA-256 and size in the upstream `index.json` manifest. The `statute_files` table keeps `file, url, bytes, sha256, version, sections, downloaded_at`. | `lexflow/municipal/statutes.py`, `lexflow/store/db.py` (`statute_files`) |
| Section text | `SectionText(section, title, code, jurisdiction, text, url, history, retrieved_from, license_note)`, with no hash and no act id field. `retrieved_from` holds `open-us-law <act_id>` as a string. | `lexflow/ir.py:209`, `lexflow/municipal/statutes.py:233` |
| Extraction | `Provenance(method, model, prompt_hash, dataset_rows, created, notes)`. The Ollama prompt hash is `sha256(...).hexdigest()[:12]`. Curated files carry a free-text `reviewed_by`, for example `"Claude (claude-opus-5-5), 2026-10-10; every quote checked against open-us-law v2026.09.1"`. | `lexflow/extract/ollama.py:150`, `curated/va/records.json` |
| Model, BPMN, DMN, SVG | Stored in `process_models` (`tier, built_by, facts, bpmn, dmn, svg, metrics`). The BPMN writes `<lex:model reviewStatus=… method=…>` into the collaboration's `extensionElements`. | `lexflow/store/db.py`, `lexflow/bpmn_xml.py:182` |
| Checks | `lex_checks` counts `quotes_checked` and quote misses, with XSD, bpmnlint, dmnlint, Spiff and soundness. The wiki NOTE states that they passed. | `lexflow/validate.py`, `lexflow/publish/lexipedia.py:29` |
| Review | `Review(status: draft / machine-checked / legal-reviewed, gaps, reviewers: list[str])`; a `tier` of `reviewed / agreed / single` | `lexflow/ir.py:232`, `lexflow/municipal/build.py` |
| Published | `core.savePage` for law and process pages, `core.saveMedia` for `<page>.bpmn` and `.dmn`. Wikibase is written through `wbeditentity` payloads and QuickStatements. | `lexflow/publish/dokuwiki.py:184`, `lexflow/publish/wikibase.py` |
| Forms | Draft JSON records each section's text, URL, origin and SHA-256 (of the UTF-8 text, with no normalisation). | `lexflow/forms/draft.py:916` |
| Lab | The case is a JSON document in the browser, exported as `.json` and `.ics`. `POST /timeline` keeps nothing. Only opt-in outcome rows (six fields) are stored, in the user's own SQLite. | `docs/design/lab-plan.md` §3 |

### 1.3 Gaps found while mapping it

These need fixing whichever technology signs the records:

- **Truncated hashes.** `prompt_hash` keeps 12 hex characters (48 bits), at `lexflow/extract/ollama.py:150`.
  `lexflow/ask/reference.py:202` does the same, and the selector uses `sha1(...)[:20]` (`lexflow/extract/selector.py:476`).
  These are fine as cache keys but too short to bind an audit claim to its input. Attestations need the full SHA-256.
- **The statute file is not linked from the model.** The parquet SHA-256 and version are in `statute_files`, keyed by
  state only. A model records neither, so after a re-download nothing shows which release it was built from.
- **Section texts carry no digest and no act id field.** The act id survives only inside the `retrieved_from` string.
- **Model identity.** `Provenance.model` is a name. Ollama models and the selector need a content digest of the
  weights or of the settings.
- **Pipeline identity.** The tree is a git checkout (last commit `dc138f25…`, 10 Oct 2026), but it had uncommitted
  changes when read. A run must record the commit and whether the tree was dirty, with a digest of the diff if it
  was. Otherwise "lexflow at commit X" is ambiguous. CI (`.github/workflows/ci.yml`) runs the tests only. Extraction and
  publishing run on the workstation.
- **Review is free text.** `reviewed_by` and `Review.reviewers` are strings with no structure, no subject digest and
  no signature.
- **Published copies are not pinned.** `dokuwiki.publish()` saves the page and media but keeps no revision. DokuWiki's
  API can read any revision: `getPage($page, $rev)` takes a revision timestamp, and `getPageInfo(..., $hash)` returns an
  MD5 of the content ([ApiCore.php](https://raw.githubusercontent.com/dokuwiki/dokuwiki/master/inc/Remote/ApiCore.php)).
  MD5 is not adequate for an audit, so lexflow would compute SHA-256 itself. Wikibase serves any entity revision as JSON
  at `Special:EntityData/Q….json?revision=N` ([Wikidata:Data access](https://www.wikidata.org/wiki/Wikidata:Data_access)),
  but lexflow keeps no `lastrevid`.

## 2. C2PA in brief

The current specification is **C2PA 2.4, April 2026**
([spec](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html), §5.3; the index at
`c2pa.org/specifications/` now redirects to `spec.c2pa.org`). The text is licensed CC BY 4.0. The patent policy is the
W3C Patent Mode (2004) with RF licensing commitments (§20). Recent versions added:

- **2.2 (May 2025):** the soft-binding API, multi-part assets, and time-stamps and revocation data in update
  manifests. It also added the `c2pa-kp-claimSigning` EKU and restricted the C2PA Trust List to certificates that carry
  it.
- **2.3 (December 2025):** live video, unstructured text, a non-hashed External Reference assertion, and manifests
  that declare the spec version and trust list they were validated against.
- **2.4 (April 2026):** HTML and structured-text embedding, the crJSON view, the Repository Receipt, Environmental
  Sustainability and AI Disclosure assertions, and `specVersion` moved into `claim_generator_info`.

### 2.1 Manifest model

- **Manifest store.** Every manifest attached to an asset, embedded or external. The last one is the *active
  manifest* (§2.3.5, §15.5).
- **Manifest.** A set of assertions, one claim and one claim signature, stored as JUMBF boxes (§11.1). There are two
  kinds:
  - A *standard* manifest (`c2ma`) holds exactly one hard binding.
  - An *update* manifest (`c2um`) is for adding assertions when the content has not changed (§11.2). It carries exactly
    one `parentOf` ingredient. Its actions are limited to `c2pa.edited.metadata`, `c2pa.opened`, `c2pa.published` and
    `c2pa.redacted`. It may not hold hash or thumbnail assertions. It may hold a time-stamp or certificate-status
    assertion.
- **Claim** (`c2pa.claim.v2`, deterministic CBOR, §10.2). Its fields are:
  - `instanceID`, the asset version;
  - `claim_generator_info`, the software and its `specVersion`;
  - `signature`, a URI to the claim signature;
  - `created_assertions`, which are attributed to the signer;
  - `gathered_assertions`, collected from elsewhere and not attributed to the signer (§9.2);
  - `redacted_assertions`, `dc:title` and `alg`.

  Each assertion should carry a random salt (§6.6).
- **Claim signature** (§13.2). A `COSE_Sign1_Tagged` structure over the serialized claim, as a detached payload.
  - Allowed signature algorithms: ES256, ES384, ES512, PS256, PS384 and PS512 (RSA keys of 2048 bits or more), and
    EdDSA with Ed25519 only.
  - Allowed hashes: SHA2-256, SHA2-384 and SHA2-512 (§13.1).
  - The certificate chain goes in the protected header, label 33 (§14.5).
- **Identifiers.** Each manifest has a `urn:c2pa:<uuid>[:<generator>][:<version>_<reason>]` identifier (§8.1).
- **crJSON (2.4).** A JSON-LD rendering of a manifest store. The spec says it is a derived view, not independently
  verifiable and not an input format. It suits display on a wiki page, not verification.

### 2.2 Bindings, actions and ingredients

- **Hard bindings** (§9.2, §18.5–18.9). A hard binding ties a manifest to exact bytes.
  - `c2pa.hash.data` hashes byte ranges, with exclusions for the manifest itself. It applies to any format, and is
    the method for text.
  - `c2pa.hash.boxes` hashes boxes or chunks in JPEG, PNG and GIF.
  - `c2pa.hash.bmff` covers MP4 and other ISO BMFF files.
  - `c2pa.hash.collection.data` hashes each file of a set individually, listed by URI (§18.8). The spec warns that
    an incomplete list lets an adversary add files.
  - `c2pa.hash.multi-asset` covers multi-part assets.

  *Soft bindings* (watermarks, fingerprints) only find a manifest again; they never replace a hard binding.
- **Actions** (`c2pa.actions.v2`, §18.15). Standard names include:
  - `c2pa.created`, which must carry a `digitalSourceType`;
  - `c2pa.opened`, which sets the `parentOf` ingredient;
  - `c2pa.placed`, which adds `componentOf` ingredients;
  - `c2pa.edited`, `c2pa.converted` (format change, non-editorial), `c2pa.transcoded`, `c2pa.repackaged` and
    `c2pa.published` (released to a wider audience).

  Entity-specific names are allowed, as dot-separated labels that begin with the entity's reverse domain name (§6.2.1;
  see §3.1 for lexflow's). Each action has one
  `softwareAgent` (a generator-info map: name, version). Its `parameters.ingredients` are hashed URIs to ingredient
  assertions. `when` is an untrusted time. A manifest with only `published`, `transcoded` or `repackaged` actions
  signals that no editorial change was made (§18.15.9).
- **`digitalSourceType`.** The value is an IPTC term (`http://cv.iptc.org/newscodes/digitalsourcetype/…`) or one of
  two C2PA values: `http://c2pa.org/digitalsourcetype/empty` and
  **`http://c2pa.org/digitalsourcetype/trainedAlgorithmicData`**, for data produced by a model trained on sampled data
  (§18.15.4.5). The C2PA AI/ML guidance points to this value for model output that is not media. It also records a
  prompt as an `inputTo` ingredient ([AI/ML guidance 2.3](https://spec.c2pa.org/specifications/specifications/2.3/ai-ml/ai_ml.html),
  §9). IPTC's vocabulary includes `digitalCreation` (made by people with non-generative tools) and `algorithmicMedia`
  (made purely by an algorithm, without training data) ([IPTC](https://cv.iptc.org/newscodes/digitalsourcetype/)).
- **Ingredients** (`c2pa.ingredient.v3`, §18.16). Each has a required `relationship`:
  - `parentOf`: the current asset is derived from this one;
  - `componentOf`: this one is a part of the current asset;
  - `inputTo`: this one was input to a computational process such as an AI/ML model.

  For an ingredient that has its own manifest, `activeManifest` and `claimSignature` are hashed URIs to that
  manifest's boxes. This is the link that chains manifests. For an ingredient with **no** manifest (the open-us-law
  parquet, an agency PDF), v3 has no field for the hash of its bytes. The way to bind it is `data`, as a `hashed-ext-uri`
  (`url`, `alg`, `hash`) or a hashed URI to an embedded-data assertion. A validator reports `ingredient.actionMissing`
  if no action references an ingredient.
- **Other assertions that matter here:**
  - `c2pa.time-stamp` adds an RFC 3161 token after the fact, at most one per manifest (§18.18).
  - `c2pa.certificate-status` holds later OCSP responses (§18.19).
  - `c2pa.external-reference` (§18.24) points to data stored outside the manifest. Its `location` may be "an
    `unhashed-ext-uri-map` … where the referenced data is advisory and may change over time, or a
    `hashed-ext-uri-map`, where the referenced data is cryptographically bound to the manifest at signing time"
    (§18.24.1). §18.24.2 uses the hashed form for creation-process evidence, with `c2pa.types.audit-log` ("A
    structured log of creation-phase events") among its data types. The 2.4 history says it "Extended External
    Reference Assertion validation to cover hashed external reference assertions". (An earlier version of this note
    called it only "an unhashed, advisory link", which is wrong for 2.4.)
  - `c2pa.repository-receipt` (§18.27) is a JSON-LD record from the repository that ingested a manifest. It holds the
    repository's URI, its `manifestId` and an `anchor` with a repository-specific `proof`, and it appears only in an
    update manifest. The spec does not define the proof, so a Merkle-log or SCITT receipt could fill it. That use is an
    idea, not something the spec says.
  - `c2pa.ai-disclosure` (§18.28).

### 2.3 Signing, time-stamps and trust

- **Certificates** (§14.5). The profile is:
  - X.509 v3 with the `digitalSignature` key usage;
  - a non-empty EKU, never `anyExtendedKeyUsage`;
  - the C2PA signer EKU `c2pa-kp-claimSigning` (1.3.6.1.4.1.62558.2.1), with `id-kp-emailProtection` and
    `id-kp-documentSigning` accepted for compatibility;
  - `cA` not asserted;
  - an AIA extension for OCSP.

  OCSP responses are stapled in `rVals`. A claim generator may not use CRLs. When no revocation method exists, the
  validator treats the credential as not revoked. Online status checks are optional, and the spec warns that they can
  reveal which asset is being checked (§15.9).
- **Time-stamps** (§10.3.2.5, §15.8). The RFC 3161 token goes in the `sigTst2` header, one per manifest. A validated,
  trusted time-stamp replaces the current time when certificate validity is checked, and it stays valid after the
  TSA's own certificate expires. The `iat` header is a claimed time only.
- **Validation states and trust lists** (§14.3, §14.4). A manifest is *Well-Formed*, *Valid* or *Trusted*, each state
  including the one before. A validator keeps three lists:
  - a signer list, which must include C2PA's list;
  - a separate TSA list, which includes the C2PA TSA Trust List;
  - a *private credential store*, local to the validator and never pre-configured. It applies to manifests, not
    time-stamps.
- **The C2PA Trust List and the conformance programme**
  ([c2pa.org/conformance](https://c2pa.org/conformance/);
  [Conformance Program v0.2](https://raw.githubusercontent.com/c2pa-org/conformance-public/main/docs/v0.2/C2PA%20Conformance%20Program.md)).
  - The Trust List launched in mid-2025 and replaced the Interim Trust List. The Interim list was frozen on 1 January
    2026: its certificates stay valid until they expire, and it takes no new ones.
  - CAs on the Trust List may issue claim-signing certificates only to instances of generator products marked
    conformant on the Conforming Products List.
  - Getting there takes an expression of interest, a legal agreement signed through the Linux Foundation, an intake
    form, a Generator Product Security Architecture document in Markdown, sample files of every media type the product
    claims, and review by two people. The product then receives a signed Notice of Conformance.
  - There are two Assurance Levels, and Level 1 is the minimum.
  - The lists are published as PEM and JSON in
    [conformance-public/trust-list](https://github.com/c2pa-org/conformance-public/tree/main/trust-list) (CC BY 4.0).
  - The TSA Trust List was issued on 2026-08-05 and is due for update on 2027-08-05. It names 13 operators, among them
    DigiCert, Google, SSL.com, Trufo, Tauth Labs and TrustAsia.
- **A test certificate for development.** The CAI SDK refuses self-signed signing certificates. c2pa-rs ships test
  certificates and keys in `sdk/tests/fixtures/certs/`, and the Node, Python and C++ libraries carry a subset in
  `tests/fixtures` ([CAI: test certificates](https://opensource.contentauthenticity.org/docs/signing/test-certs)).
  c2patool signs with a built-in test certificate when no signer is configured
  ([signing.md](https://raw.githubusercontent.com/contentauth/c2patool/main/docs/signing.md)). Inspect shows the issuer
  of test-signed claims as unrecognised. For lexflow, a better development setup is a private two-level CA made locally
  (root → end-entity with the claim-signing EKU, `O=lexflow`). The auditor adds its root as a trust anchor. No
  certificate needs downloading.

### 2.4 Formats: embedded, sidecar or remote

From Appendix A of the 2.4 spec and the c2pa-rs format list
([supported-formats.md](https://raw.githubusercontent.com/contentauth/c2pa-rs/main/docs/supported-formats.md)):

| Format | What the spec says | c2pa-rs today | For lexflow |
|---|---|---|---|
| **PDF** | Embedded as an embedded file stream with an `AF` entry in the catalog. Object-level manifests are possible. Incremental updates give several manifests, and the most recent one is active. A PDF signature covers the whole file including the manifest, and its `Contents` range is excluded from `c2pa.hash.data`. If a certifying signature exists, the annotation approach keeps its DocMDP rules intact (A.4). | `pdf` listed. The `pdf_io.rs` handler on `main` reads and writes, with one manifest per PDF for reading. | **Embed**: printed letters, fillable forms |
| **SVG** | Base64 in a `c2pa:manifest` element inside `<metadata>`, with `xmlns:c2pa="http://c2pa.org/manifest"`. The spec says an external manifest is preferred (A.3.3). | `svg` listed | **Embed** (and keep a sidecar) |
| **XML** (BPMN, DMN, PNML) | The structured-text method applies to `text/xml`, `application/xml` and XML-derived types, using XML comment syntax. A `-----BEGIN C2PA MANIFEST-----` … `-----END C2PA MANIFEST-----` block holds a URL (preferred) or a `data:application/c2pa;base64,…` URI. It goes at the end of the file when the first line is an XML declaration. One data-hash exclusion covers the block. Files are read in binary, with LF or CRLF only. The spec warns that the method depends on the toolchain keeping comments (A.9). | Not listed. The experimental `unstable_structured_text` feature lists only `atom` and `rss` among XML types. | **Sidecar now**; embed once the SDK supports it |
| **JSON** | Not covered. A.9 is for `text/` types and XML types. JSON is `application/json`, has no comment syntax, and A.9 does not mention it. | Not listed | **Sidecar or remote** (model, facts, check report, drafts, Wikibase payloads, lab case) |
| **HTML** | Embedded as `<script type="application/c2pa">` in `<head>`, with one exclusion covering the element. Or referenced with `<link rel="c2pa-manifest">`, in which case the hash covers the whole document (A.7). Under the HTML standard, a script of that type is a *data block*: the browser does not run it ([WHATWG](https://html.spec.whatwg.org/multipage/scripting.html)). That keeps the drafts' no-network rule. | Not listed. A third-party crate, `c2pa-html` 0.2.0 (MIT/Apache-2.0, not from the CAI), embeds HTML and computes the hash, but does no signature or trust validation ([docs.rs](https://docs.rs/c2pa-html)). | **Sidecar now** (draft forms, letters); embed later |
| **Plain text** | Embedded as invisible Unicode variation selectors in a `C2PATextManifestWrapper` after a U+FEFF, at the end of the text. The hash is over the NFC-normalised UTF-8 bytes. The spec says the method is under review and may change (A.8). | `txt` behind the non-default `unstable_plain_text` feature | Not for lexflow: the wiki source is not plain text, and invisible characters in law text would be a hazard |
| **DokuWiki source** | Would need comment syntax or front matter (A.9). DokuWiki core defines neither ([syntax.txt](https://raw.githubusercontent.com/dokuwiki/dokuwiki/master/data/pages/wiki/syntax.txt)). The HTML is rendered by DokuWiki, not by lexflow. | — | **Sidecar** for the page source at a stated revision |
| **PNG / JPEG** | `caBX` chunk; APP11 segments | listed | **Embed** (README and deck images) |
| **Parquet** (statute data) | No Appendix A section | not listed | **No manifest.** A downstream manifest references it as a non-C2PA ingredient by `hashed-ext-uri` |

**External manifests** (§11.4, §11.5, §15.5.3):

- The media type is `application/c2pa`. The older `application/x-c2pa-manifest-store` is deprecated, though c2pa-rs's
  list still uses it.
- A validator that finds no embedded manifest should look for a sidecar at the same path with a `.c2pa` extension. An
  HTTP response can point to one with `Link: <…>; rel="c2pa-manifest"`.
- A file with XMP can point to its manifest with `dcterms:provenance`.
- An embedded manifest takes precedence over a remote one.
- A remote manifest that is documented but missing is reported as `manifest.inaccessible`.

### 2.5 Tools

| Tool | What it is (10 Oct 2026) | Licence |
|---|---|---|
| [c2pa-rs](https://github.com/contentauth/c2pa-rs) | The Rust SDK, beta (0.x). It implements a subset of C2PA 2.4 and the CAWG identity assertion, and writes v2 claims by default. A C API is in `c2pa_c_ffi`. `main` is unstable; releases go to crates.io. | MIT and Apache-2.0 (some components differ) |
| [c2patool](https://github.com/contentauth/c2patool) | The CLI. It moved out of the c2pa-rs monorepo; versions up to 0.27.15 were released from c2pa-rs. **v0.28.2, 8 Oct 2026.** Options: `-m` manifest definition, `-o` output, `-s` sidecar, `-r` remote URL, `-p` parent ingredient, `-d` detailed report, and `trust` with `--trust_anchors`, `--allowed_list` and `--trust_config`. Signers can be local, a subprocess (`--signer-path`) or a remote HTTP service. A `[cawg_x509_signer.local]` section signs CAWG identity assertions ([usage.md](https://raw.githubusercontent.com/contentauth/c2patool/main/docs/usage.md)). | Apache-2.0 per GitHub's detection; the README's About section says Apache-2.0 and MIT |
| [c2pa-python](https://github.com/contentauth/c2pa-python) | **0.38.0, 29 Sep 2026**, Python ≥ 3.10. It requires `toml`, `cryptography>=41` and `requests`. API: `Builder.from_json` with `add_ingredient`, `add_action`, `set_no_embed`, `set_remote_url`, `sign` and `sign_file`; `Reader` with `json`, `detailed_json`, `crjson`, `get_validation_state` and `get_remote_url`; `Signer.from_info` and `Signer.from_callback(callback, alg, certs, tsa_url)` ([API](https://contentauth.github.io/c2pa-python/api/c2pa/index.html)). Trust anchors are set through `Settings` ([usage.md](https://raw.githubusercontent.com/contentauth/c2pa-python/main/docs/usage.md)). A build from source downloads a prebuilt native library from a c2pa-rs release (README). | MIT OR Apache-2.0 |
| [c2pa-js](https://github.com/contentauth/c2pa-js) | A monorepo. `c2pa-web` runs in the browser on WASM bindings (`c2pa-wasm`). `c2pa-node` reads, validates and signs; `c2pa-node-v2` was merged into it in June 2026. The older c2pa-js is now `c2pa-js-legacy` and deprecated. | MIT |

In the ingredient JSON the SDK reads, `relationship` takes `parentOf`, `componentOf` (the default) or `inputTo`. The
JSON also has `data`, `instance_id` and `hash`
([ManifestDefinition schema](https://opensource.contentauthenticity.org/docs/manifest/json-ref/manifest-definition-schema)).

### 2.6 Identity: the CAWG identity assertion

The Creator Assertions Working Group publishes its specifications at [cawg.io](https://cawg.io/). The current identity
assertion is **1.3, a DIF Ratified Specification dated 17 August 2026**, built on C2PA 2.4
([identity 1.3](https://cawg.io/identity/1.3/)). The index page at `cawg.io/identity/` still names 1.2, dated 15 Dec
2025.

- **What it binds.** A `cawg.identity` assertion ties a *named actor* to a list of `referenced_assertions`, and that
  list **must include the manifest's hard binding**.
  - Its optional `role` suggests `cawg.creator`, `cawg.contributor`, `cawg.editor`, `cawg.producer`,
    `cawg.publisher`, `cawg.sponsor` and `cawg.translator`. Other values may be used.
  - One manifest may carry several identity assertions, one per actor.
  - The identity assertion generator may be someone other than the claim generator.
  - Version 1.3 removed the `expected_*` fields.
- **Signature types.**
  - `cawg.x509.cose`: an X.509 certificate with a COSE signature.
  - `cawg.identity_claims_aggregation`: a W3C VC from an *identity claims aggregator*, with `verifiedIdentities` of
    the types `cawg.document_verification`, `cawg.web_site`, `cawg.affiliation`, `cawg.social_media` and
    `cawg.crypto_wallet` (taken from version 1.2).
- **X.509 trust** (§8.2.4).
  - The validator's accepted EKUs must include `id-kp-documentSigning`, which needs no certificate policy or anchors
    for now.
  - Until 31 March 2027, interim rules also accept `id-kp-emailProtection` certificates. They need organisation-,
    sponsor- or individual-validated policies and must chain to the Mozilla S/MIME roots or to the IPTC Origin Verified
    News Publishers list.
  - Version 1.3 reports the outcome as `cawg.x509.credential.trusted` or `cawg.x509.credential.untrusted`.
  - CAWG has not advised which aggregators to trust.
- **Organisations.** C2PA 2.4's identity recommendation tells organisations to use the CAWG *Organizational Identity
  Profile* 1.0. Software acting in its own name should use the ordinary claim signature with a conformance certificate
  ([C2PA identity recommendation](https://spec.c2pa.org/specifications/specifications/2.4/identity/identity.html)).
- **Endorsement** ([draft 1.0, 14 Apr 2025](https://cawg.io/endorsement/1.0-draft/)). The signer of an ingredient
  approves later actions on it, and the endorsee adds the endorsement. That is not a review of finished output, so it
  does not fit lexflow's review step.

### 2.7 How a third party verifies

1. **Open the file** in `c2patool <file> -d`, `c2pa-python`'s `Reader`, a c2pa-js page, or CAI's Inspect site
   ([inspect.cr](https://inspect.cr)). The validator finds the embedded manifest, or a `.c2pa` sidecar or `Link` target
   if there is none.
2. **Check the claim signature** (COSE) and the certificate chain against the validator's trust lists. A lexflow
   auditor adds lexflow's root with `c2patool <file> trust --trust_anchors lexflow-root.pem` or the Python settings.
   The usage page gives `c2patool <ASSET_PATH> [OPTIONS] [SUBCOMMAND]` and `c2patool <ASSET_PATH> trust [OPTIONS]`,
   so the asset path comes first and `trust` follows the top-level options, for example `c2patool copy.pdf -d trust
   --trust_anchors lexflow-root.pem`. This order was read from the usage page, not run.
3. **Check the time-stamp.** A trusted TSA gives an attested time. Then check OCSP if it is stapled.
4. **Check the hard binding.** Recompute the hash of the asset's bytes, minus the exclusions.
5. **Check the assertions,** then **each ingredient's manifest** in turn: its claim signature and hashed URIs (§15.11).
   The validator can't re-hash an ingredient's *content* unless it has that file. The auditor checks those against the
   files they hold.
6. **Read the result:** Well-Formed, Valid or Trusted, with status codes. CAWG identity assertions are reported
   separately.

### 2.8 Cost

| Item | Cost found |
|---|---|
| Spec and SDKs | Free: CC BY 4.0 text, W3C RF patent mode, MIT/Apache-2.0 code |
| Conformance programme | No application fee and no fee for listing on the Trust List or the Conforming Products List. The work is the legal agreement, the security architecture document, the Level 1 security requirements and the samples ([Conformance Program v0.2](https://raw.githubusercontent.com/c2pa-org/conformance-public/main/docs/v0.2/C2PA%20Conformance%20Program.md)). |
| Claim-signing certificate from a Trust List CA | No price is published. CAI listed DigiCert, SSL.com, Tauth Labs and Trufo as of April 2026 ([CAI: get a certificate](https://opensource.contentauthenticity.org/docs/signing/get-cert)). [DigiCert](https://www.digicert.com/solutions/c2pa-media-trust) offers media companies a free beta account and says nothing of price. [SSL.com](https://www.ssl.com/article/c2pa-enterprise-content-authenticity-solutions/) offers a contact form and lists C2PA TSA endpoints. In both cases a certificate requires conformance first. |
| Time-stamping | c2pa-python's example uses DigiCert's public timestamp URL. Whether that service chains to the C2PA TSA Trust List was not checked (§9). |
| Engineering | The real cost: format coverage for JSON, XML and wiki text; a key; publishing sidecars; documenting how to verify |

### 2.9 Limits

- **It proves who signed and what they say happened, not that it is true.** The C2PA Explainer says plainly that
  Content Credentials make no value judgement on whether provenance data is true, and are no cure for misinformation
  ([Explainer 2.2](https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html), §2, §3, §7.2.2).
  For lexflow, a valid chain shows that this BPMN was compiled by this commit from facts extracted by this method from
  these section texts. It does not show that the BPMN reads the statute correctly. Checks and review answer that, and
  they must say exactly what they checked.
- **Stripping.** Any tool that rewrites a file can drop an embedded manifest without leaving a trace: an image
  optimiser, a wiki re-render, an XML re-serialiser. The spec's *durable* Content Credentials recover a manifest
  through watermarks or fingerprints (soft bindings) looked up in a store (Explainer §6.2, §7.2.3). lexflow should rely
  on its own release log, and treat an embedded manifest as a convenience that points back to it.
- **Replacement.** Someone can strip lexflow's manifest and sign a new one. Whom to trust is the consumer's decision
  (Explainer §7.5.1). So lexflow must publish its certificate fingerprints and its release log where readers can find
  them: the wiki start page and the repository.
- **No transparency.** A time-stamp proves a signature existed at a time. It does not prove that lexflow never signed a
  different chain for the same page. That needs an append-only log (§4.3, §4.5).
- **Format coverage and maturity.** The SDK is beta (0.x). Plain text and structured text are unstable features, and
  HTML and generic XML are not supported yet. The text embedding methods are new (2.3 and 2.4), and the plain-text one
  is marked under review. The spec changed three times in a year (2.2, 2.3, 2.4).
- **Privacy.** The core spec does not deal with human identity, and the Explainer warns about the privacy effects of
  adding it (§7.2.4). An identity assertion with a person's certificate puts that person's name into every copy of the
  file. lexflow's rule is that public outputs name no private person.

## 3. Mapping lexflow's chain onto C2PA

### 3.1 Per artifact

| # | Stage | Artifact | Manifest | Action(s) and ingredients |
|---|---|---|---|---|
| 0 | Statute snapshot | `us_<st>_statutes.parquet` (open-us-law v2026.09.1) | None; lexflow did not make it | Referenced downstream as a non-C2PA ingredient. `data` is a `hashed-ext-uri` holding the upstream `url`, `alg: sha256` and the SHA-256 from upstream `index.json`, which `statute_files` already holds |
| 0 | Section texts | `sections.json` (the model's `texts`, one entry per section with `act_id`, citation, `source_url`, `last_amended_year` and the SHA-256 of the exact UTF-8 text) | Sidecar `sections.json.c2pa` | `c2pa.opened`, with the parquet as `parentOf`; entity action `xyz.lexipedia.lexflow.selected` (query, index version, selected act ids). Custom assertion `xyz.lexipedia.lexflow.statute-sections` |
| 1–2 | Retrieval and extraction | `facts.json` | Sidecar | `c2pa.created` with `digitalSourceType` `…/trainedAlgorithmicData` for Claude-written, two-model or selector output, or IPTC `digitalCreation` for a person's gold file. `softwareAgent` gives the model name and digest: Claude model id, Ollama model and digest, or selector version and settings digest. Ingredients: `sections.json` as `inputTo` (`activeManifest` link), and the prompt or system text as `inputTo` with `data` pointing to the prompt file at the commit, full SHA-256 |
| 2 | Agreement (tier `agreed`) | The second model's `facts.json` | Sidecar | `inputTo` ingredient on the chosen facts, with an `xyz.lexipedia.lexflow.agreement` assertion (fields compared, F1) |
| 3 | Process model | `model.json` (LegalProcessModel, the exact bytes published) | Sidecar `model.json.c2pa`; the lexflow API can also send `Link: rel="c2pa-manifest"` | `c2pa.opened` (facts as `parentOf`), then `xyz.lexipedia.lexflow.compiled` (`softwareAgent` lexflow at commit; dirty flag) |
| 4 | BPMN, semantic BPMN, DMN, Spiff DMN, PNML | XML | Sidecar now; A.9 comment later | `c2pa.opened` (model as `parentOf`), then `c2pa.converted` |
| 4 | Diagram | `.svg` | **Embedded** in `<metadata>` (plus a sidecar) | `c2pa.opened` (BPMN), then `c2pa.converted` (render; layout settings in `parameters`) |
| 4 | Diagram | `.png` (cairosvg) | **Embedded** (`caBX`) | `c2pa.opened` (SVG), then `c2pa.converted` |
| 5 | Checks | `checks.json` (tool versions, config digests, results) | Inside the release manifest as `xyz.lexipedia.lexflow.check-report` (created assertion) | The checks run before the release is signed, so the signed manifest states them |
| 6 | Review | `review.json` | See §3.3 | — |
| 7 | Release | the set of files above | Sidecar `release.c2pa` with `c2pa.hash.collection.data` over every file, the sidecars included | `c2pa.placed` with each file as `componentOf`; `c2pa.published` |
| 7 | Wiki page source | `lexflow_<st>_<q>.txt` as saved, plus the revision timestamp from `core.getPageInfo` after the save | Sidecar (no comment syntax) | `c2pa.converted` (model and texts as `componentOf`), then `c2pa.published`. The sidecar is uploaded as wiki media next to the existing `.bpmn` and `.dmn` media, or hosted in the repository |
| 7 | Wikibase items | the payloads lexflow sent, then per item the RFC 8785 (JCS) canonical JSON of the statements lexflow wrote, at the `lastrevid` returned | Sidecar per release, listing `Q…@rev` and its digest | `c2pa.converted`, `c2pa.published` |
| 7 | Draft form and letter | `*.form.html`, `*.letter.html`, `*.json` | Sidecar now; HTML embedding later (data block, no network) | `c2pa.created` (`digitalSourceType` `algorithmicMedia`, made by rules, not a trained model), with section texts as `inputTo` |
| 7 | Printed letter, fillable form | PDF | **Embedded** | `c2pa.converted` (from the HTML letter), or §3.4 for a fillable copy of an official PDF |
| 8 | Lab case | case `.json`, `.ics`, a printed timeline | **None signed by lexflow.** The user's data never goes to a log | The export records `model_id` plus the release statement digest and log entry, so a third party can check the model part. A user who holds a certificate could sign their own export locally |

`xyz.lexipedia.lexflow.*` labels are entity-specific names, which the spec allows for actions (§18.15) and assertions
(§6.2.1). An entity-specific namespace must begin with the entity's own Internet domain name, written reverse-domain
style (`com.litware` in the spec's examples). So `org.lexflow` would be right only if the project held `lexflow.org`.
A `github.com`-based name would not do either, because that domain belongs to GitHub. This note uses the user's own domain
`lexipedia.xyz`, reversed. CAWG custom roles follow the same label rules. Every hash is the full SHA-256 of the exact
bytes published.

### 3.2 How the ingredients chain

```
open-us-law index.json (v2026.09.1)
   └─ sha256 ─▶ us_va_statutes.parquet  (no manifest; hashed-ext-uri ingredient)
                   │ parentOf
                   ▼
            sections.json.c2pa   [opened, xyz.lexipedia.lexflow.selected]          signer: lexflow release key
                   │ inputTo (+ prompt inputTo)
                   ▼
            facts.json.c2pa      [created: trainedAlgorithmicData, softwareAgent = model+digest]
                   │ parentOf
                   ▼
            model.json.c2pa      [opened, xyz.lexipedia.lexflow.compiled @ commit]
                   │ parentOf
          ┌────────┴────────┐
          ▼                 ▼
   records.bpmn.c2pa   records.dmn.c2pa   [opened, converted]
          │ parentOf
          ▼
   records.svg (embedded) ──parentOf──▶ records.png (embedded)
          │
          └─ all of the above + checks.json ─ componentOf ─▶ release.c2pa [placed, published,
                                                             collection hash, xyz.lexipedia.lexflow.check-report,
                                                             xyz.lexipedia.lexflow.review-ref]
                                                                 │ componentOf
                                                                 ▼
                                          wiki source .c2pa, Wikibase snapshot .c2pa  [converted, published]
```

Each arrow is an ingredient whose `activeManifest` and `claimSignature` are hashed URIs into the upstream manifest.
If the upstream manifests are included in each downstream manifest store, a validator holding only `records.svg` can
check every claim signature back to `sections.json.c2pa`. How the SDK includes them is to be confirmed in the
prototype. To re-hash the content of each upstream file, the validator needs those files from the release.

### 3.3 Review: a person, an organisation, or Claude

- **Claude review** (`tier = reviewed`, `built_by = claude`). Claude holds no credential, so it signs nothing. The
  operator records the review as an action, `xyz.lexipedia.lexflow.reviewed`, with `softwareAgent` `{name: "Claude", version:
  "claude-opus-5-5"}`, the date, the scope ("every quote checked against open-us-law v2026.09.1") and the result. The
  operator's release key signs it. The record must say this is the operator's statement that Claude ran the review,
  not a signature from Anthropic.
- **Organisational or role review.** The CAWG route is a `cawg.identity` assertion in the release manifest, with a
  custom role (`xyz.lexipedia.lexflow.reviewer`) and the reviewer's own X.509 certificate. It must reference the release
  manifest's hard binding, the collection hash, so the reviewer signs their `signer_payload` while lexflow builds the
  manifest. It reads as trusted only if the reviewer's certificate meets the CAWG trust model (§2.6). A review given
  *after* the release cannot go in an update manifest cleanly. An update manifest has no hard binding, and CAWG 1.3
  requires the identity assertion to reference one. The spec does not settle whether the parent's binding, reached
  through the ingredient, is enough (§9).
- **The simpler route, which works for every reviewer.** A separate review statement is signed by the reviewer's own
  key over the release digests (§4.1). The release manifest's `xyz.lexipedia.lexflow.review-ref` then names it by hash. This
  avoids a timing dependency between reviewer and builder, and it works for late reviews and withdrawn reviews.
- **Privacy.** A review identity is an organisation or a role, never a private person's name or email (§4.3).

### 3.4 Where CommonForms would sit

[CommonForms](https://github.com/jbarrow/commonforms) turns a PDF into a fillable form by detecting form fields. Its
README describes:

- the CLI `commonforms in.pdf out.pdf`, with options `--model FFDNet-L|FFDNet-S|<.pt>`, `--confidence` (default 0.3)
  and `--image-size` (default 1600);
- the Python call `prepare_form(...)`;
- the CommonForms dataset, and Barrow (2025), arXiv:2509.16506, to cite.

The README itself states no licence for the code, the models or the dataset. That is true of the README only. The
repository has no LICENSE file, and the FFDNet model cards carry no licence. But the FFDetr model card and the
CommonForms dataset card both carry `license: apache-2.0` (Hugging Face API, read 10 October 2026). For licence
reasons, [commonforms.md](commonforms.md) §1.9 recommends not using the `commonforms` package at all. lexflow would
instead write a small adapter on `rfdetr` (Apache-2.0) with the FFDetr weights, and
[canonical-workflows.md](canonical-workflows.md) follows it.

If the lab made a fillable copy of an official form on the user's machine, a C2PA manifest would describe it well. It
follows [commonforms.md](commonforms.md) §3.8:

- the official PDF as `parentOf`, with `data` as a `hashed-ext-uri` to the publisher's URL and the fingerprint that
  the forms checker already takes (`docs/design/forms-plan.md` §5);
- the detector named in a `c2pa.ai-disclosure` assertion: FFDetr, with the Hub repo and revision as
  `modelIdentifier`;
- an action `xyz.lexipedia.lexflow.fields_detected` whose `parameters` give the weights' SHA-256, the confidence
  threshold and the image size. Its `softwareAgent` is lexflow's own adapter (`lexflow.forms.fields`, with the
  `rfdetr` version), not CommonForms, which is not used;
- `c2pa.edited`, because fields were added;
- a hashed `c2pa.external-reference` of type `c2pa.types.audit-log` to the form's run log.

That makes "lexflow modified this; it is not the agency's file" machine-readable. Two existing rules still apply.
Official forms are linked, not copied (forms-plan §Privacy and credit). And the FFDetr card's Apache-2.0 tag is the
only licence statement on those weights, so its notice and the Hub revision travel in the run record.

## 4. Alternatives

### 4.1 in-toto attestations with SLSA provenance

- **in-toto Attestation Framework v1.2**
  ([spec](https://raw.githubusercontent.com/in-toto/attestation/main/spec/README.md)).
  - A Statement (`_type: https://in-toto.io/Statement/v1`) has a `subject` list of resource descriptors. Each must
    carry a `digest`, and subjects are matched purely by digest, whatever their content type. It also has a
    `predicateType` URI and a `predicate`.
  - The recommended envelope is DSSE, with `payloadType: application/vnd.in-toto+json`. DSSE allows several
    signatures. COSE_Sign1 carries one signer only, which is why it is not ITE-5 compliant
    ([envelope](https://raw.githubusercontent.com/in-toto/attestation/main/spec/v1/envelope.md)).
  - Vetted predicates include provenance, VSA, `test-result`, release, SCAI and link
    ([predicates](https://github.com/in-toto/attestation/tree/main/spec/predicates)).
- **SLSA v1.2** (approved) Build Provenance, `predicateType: https://slsa.dev/provenance/v1`
  ([build provenance](https://slsa.dev/spec/v1.2/build-provenance)).
  - `buildDefinition` holds `buildType`, `externalParameters` (untrusted, must be checked), `internalParameters` and
    `resolvedDependencies`.
  - `runDetails` holds `builder.id`, `metadata` (invocation id, start and finish) and `byproducts`.
  - Verifiers accept only known signer–builder pairs and reject unexpected `externalParameters` fields.
  - Build L1 means provenance exists. L2 means a hosted build platform generates and signs it. L3 means a hardened
    platform ([track basics](https://slsa.dev/spec/v1.2/build-track-basics)).
  - The VSA (`https://slsa.dev/verification_summary/v1`) reports SLSA levels, so lexflow's checks fit the in-toto
    `test-result/v0.1` predicate better. Its fields are `result` (PASSED, WARNED or FAILED), a required
    `configuration`, and the passed, warned and failed tests
    ([test-result](https://raw.githubusercontent.com/in-toto/attestation/main/spec/predicates/test-result.md)).
- **For lexflow.** A model release is a build in this sense:

  | SLSA field | lexflow value |
  |---|---|
  | `subject` | Every published file with its SHA-256 (model, BPMN, DMN, SVG, PNG, wiki source, Wikibase snapshot, forms) |
  | `externalParameters` | State, question, method or tier, and the extraction settings |
  | `resolvedDependencies` | The parquet (URL plus SHA-256), each section (act id plus SHA-256), the prompt file, model digests, lexflow's git commit and dirty state |
  | `builder.id` | A URI for "lexflow on the operator's workstation". That is Build L1. A release built in GitHub Actions with GitHub's artifact attestations would reach L2 ([GitHub](https://docs.github.com/en/actions/concepts/security/artifact-attestations)) |

  The test-result statement covers checks. A review statement is a small custom predicate: reviewer kind and id,
  scope, result, date, and the release statement digest. The reviewer signs it.
- **Weaknesses.** Nothing travels inside the files. There is no visual tooling for readers. The builder's trust rests
  on lexflow's key.

### 4.2 Sigstore: cosign and the Rekor transparency log

- **Signing.**
  - `cosign sign-blob --bundle` signs a file. `cosign attest-blob --predicate <file> --type slsaprovenance1|custom|<URI>
    --key … --bundle …` signs an in-toto attestation.
  - `cosign verify-blob-attestation --bundle … --key … --type …` verifies one. `--check-claims`, on by default,
    confirms the file's digest is a subject.
  - Signing can use a local key or KMS key, or be keyless
    ([attest-blob](https://raw.githubusercontent.com/sigstore/cosign/main/doc/cosign_attest-blob.md),
    [verify-blob-attestation](https://raw.githubusercontent.com/sigstore/cosign/main/doc/cosign_verify-blob-attestation.md),
    [signing blobs](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/)).
- **Keyless signing.** Fulcio issues 10-minute X.509 certificates bound to an OpenID Connect identity. It is described
  as free. Fulcio must publish every certificate to the log, and the log is append-only
  ([Fulcio](https://docs.sigstore.dev/certificate_authority/overview/),
  [security model](https://docs.sigstore.dev/about/security/)). cosign's consent prompt warns that the signer's
  identity "will be stored in public transparency logs and cannot be removed later" (as reproduced by
  [Chainguard Academy](https://edu.chainguard.dev/open-source/sigstore/cosign/how-to-sign-a-container-with-cosign/index.md)).
- **Rekor.**
  - The public instance is `rekor.sigstore.dev`, run with a 99.5% availability SLO
    ([Rekor](https://docs.sigstore.dev/logging/overview/)).
  - Rekor v2 reached GA on 10 Oct 2025 ([blog](https://blog.sigstore.dev/rekor-v2-ga/)). It is tile-backed on
    Tessera and keeps only `hashedrekord` and `dsse` entries.
  - v2 stores no attestations, so they must be kept beside the artifacts. It has no search index yet, and time-stamps
    come from a separate TSA.
  - cosign 2.6.0+ or 3.0.1+ supports v2.
- **For lexflow.** Rekor adds the piece C2PA lacks: an independent, append-only, public record that lexflow published
  *this* release statement at a given point. Monitors can see any other statement signed with the same key. The
  rule is to sign with a project key, not a personal OIDC identity. The log then holds the public key and digests of
  content that is public anyway. Keyless signing from a CI workflow would put the workflow identity in the log instead
  of a person.

### 4.3 W3C Verifiable Credentials 2.0

- **Status.** VC Data Model 2.0 and VC Data Integrity 1.0 are both W3C Recommendations of 15 May 2025
  ([VC 2.0](https://www.w3.org/TR/vc-data-model-2.0/), [Data Integrity](https://www.w3.org/TR/vc-data-integrity/)).
- **Structure.** A credential has `issuer`, `validFrom`/`validUntil`, `credentialSubject`, `credentialStatus`
  (revocation), `credentialSchema` and `evidence`. It is secured by an embedded Data Integrity proof (for example
  `eddsa-jcs-2022` or `ecdsa-rdfc-2019`) or by an enveloping JOSE or COSE signature.
- **`relatedResource`.** It lists `id` and `digestSRI` or `digestMultibase` for external resources. A verifier that
  uses one must compute its digest and fail on a mismatch. The spec suggests sha384 as a minimum.
- **For lexflow.** VCs fit **statements about a party**: "organisation X reviewed release R, digest D, with result
  'legal-reviewed'", which can later be withdrawn through `credentialStatus`. JSON-LD sits naturally next to Wikibase.
  CAWG's identity claims aggregation also uses VCs. VCs fit pipeline provenance poorly. lexflow would have to design
  its own vocabulary for what SLSA already defines, and run issuer keys and DIDs.

### 4.4 Plain signed hash manifests and a Merkle log

- **The simplest version.** A JSON (or JSON-LD) release manifest lists every file's SHA-256 and its inputs. It is
  canonicalised with RFC 8785 JCS ([RFC 8785](https://www.rfc-editor.org/info/rfc8785), Informational) and signed with
  Ed25519 or ES256. It is appended to an append-only Merkle log.
- **The log.** [C2SP tlog-tiles](https://c2sp.org/tlog-tiles) defines such a log as static files: Merkle-tree tiles
  and a signed checkpoint, a design taken from the Go checksum database. It can be served from the repository or any
  static host. Inclusion and consistency proofs then show that a release was logged, and that history was not rewritten
  as long as someone else saw the earlier checkpoint. A log with no witness or cosigner gives the operator room to show
  different views to different readers.
- **The standard form of the same idea.** SCITT is now **RFC 9943** (Proposed Standard, 2026)
  ([RFC 9943](https://www.rfc-editor.org/info/rfc9943),
  [datatracker](https://datatracker.ietf.org/doc/draft-ietf-scitt-architecture/)). An issuer's COSE_Sign1 *signed
  statement* is registered with a transparency service, which returns a *receipt* (RFC 9942 COSE Receipts) proving
  inclusion. A C2PA claim signature is also COSE_Sign1, which makes SCITT a natural future home for lexflow's release
  statements.
- **Weaknesses.** It is bespoke. No reader has a ready validator, and lexflow must write, document and maintain the
  verifier.

### 4.5 Compared for the auditor's question

| Need | C2PA | in-toto + SLSA | Sigstore (Rekor) | W3C VC | Signed manifest + Merkle log |
|---|---|---|---|---|---|
| Statute version (parquet and section hashes) | Yes, through `hashed-ext-uri` ingredients and a custom assertion | Yes: `resolvedDependencies` | Not on its own (it carries in-toto) | Possible, with a custom vocabulary | Yes, with a custom schema |
| Pipeline identity and parameters | Yes: actions, `softwareAgent`, custom assertions | **Yes; this is its purpose** (`builder.id`, `externalParameters`) | Signer identity only | Weak | Custom |
| Every artifact covered, JSON included | Only through sidecars; validator support for unsupported formats is uncertain | **Yes**, matched by digest whatever the format | Yes (hashedrekord, dsse) | Yes (`relatedResource`) | Yes |
| Evidence travels inside the file | **Yes** for SVG, PNG, PDF; later HTML and XML | No | No | No | No |
| Review by a named party | `cawg.identity` (fits awkwardly, §3.3) | Custom predicate, signed by the reviewer | Signer identity | **Yes** | Custom |
| Third party can tell nothing was hidden or backdated | No (time-stamp only) | No | **Yes** (append-only public log) | No | Yes, if witnessed |
| Off-the-shelf verifier | c2patool, Inspect, SDKs | cosign, in-toto tools | cosign | Several libraries | None |
| Trust anchor in a sandbox | lexflow root added by the auditor (*Valid* otherwise) | lexflow public key | lexflow key plus the public log | Issuer DID or key | lexflow key |
| Privacy risk | Identity assertions travel with files | Low (keys) | High with keyless personal identities; low with keys or a CI identity | Depends on the subject | Low |
| Cost | Free; Trusted needs conformance | Free | Free public good | Free | Free; maintenance |

## 5. Recommendation

### 5.1 What to use for which artifact

| Artifact | Primary record | Plus |
|---|---|---|
| Statute snapshot, section texts | In the release statement's `resolvedDependencies` (parquet URL and SHA-256 from upstream `index.json`; per section act id and SHA-256) | Referenced as `hashed-ext-uri` ingredients in the C2PA chain |
| Facts, model JSON, check report | Subjects of the DSSE-signed in-toto release statement (SLSA provenance), plus a test-result statement for the checks | C2PA sidecars chained by ingredient, once the prototype shows validators accept them |
| BPMN, DMN, PNML | Release statement subjects | C2PA sidecar now; embedded comment once the SDK supports XML |
| SVG, PNG diagrams | Release statement subjects | **Embedded C2PA** manifest that points back to the release statement |
| Draft forms and letters (HTML) | Release statement subjects | Embedded C2PA (A.7 data block) once tooling exists; sidecar now |
| Printed letters, fillable PDFs | Release statement subjects, when published | **Embedded C2PA** |
| Wiki page source, wiki media | Release statement subjects, with the page id and revision timestamp; the release lists the revision | A "Provenance" section on the page (§6.3); the sidecar uploaded as media |
| Wikibase items | Release statement subjects: JCS digest of the lexflow-written statements at `Q…@lastrevid` | A provenance property on each item (§8) |
| Review | Review statement signed by the reviewer's key: in-toto custom predicate, or a VC if the reviewer prefers | `xyz.lexipedia.lexflow.review-ref` in the release manifest; `cawg.identity` only for an organisation that holds a suitable certificate |
| Every statement | Entered in **Rekor** with a project key, or in a lexflow tile log with outside witnesses | Log index and URL printed on the wiki page |
| Lab case | Nothing signed or logged by lexflow | The export carries the model release digest and log index |

### 5.2 Why this split

- **One format-agnostic record answers the auditor's whole question.** The in-toto/SLSA statement does not care
  whether a subject is JSON, XML, wiki text or a Wikibase snapshot, because subjects are matched by digest alone. It
  already has fields for the statute inputs (`resolvedDependencies`), the pipeline (`builder.id`, `externalParameters`)
  and the run.
- **Rekor supplies the one property nothing else gives:** a public, append-only record a third party can check.
- **C2PA is the right tool where people pass files around** and where readers' tools can display a credential: the
  diagrams and documents. Its ingredient chain mirrors lexflow's real derivation steps. Its gaps are JSON, the wiki
  source, Wikibase, trust without conformance, and transparency, so it should not be the only record.
- **VCs fit statements about parties.** Use them for reviews if a reviewing organisation asks, not for the pipeline.

### 5.3 Phases

| Phase | Work | Downloads |
|---|---|---|
| 0 | Fix the provenance data (§1.3): full SHA-256 for prompts, selector settings and model weights; the parquet SHA-256 and version in the model; act id and text SHA-256 for each section; git commit and dirty flag; structured review records; the DokuWiki revision and Wikibase `lastrevid` recorded after each publish. Write unsigned release statements (in-toto JSON) with the standard library alone (`json`, `hashlib`). | none |
| 1 | Sign the statements with DSSE (ES256 or Ed25519; key file path in `.env`, the value never printed). Write a small verifier script. Publish the public key in the repository and on `lexflow:start`. | `cryptography` |
| 2 | Embed C2PA in SVG, PNG and PDF; write sidecars for JSON and XML; set up the private CA; give the auditor the c2patool commands. | `c2pa-python`; `c2patool` for auditors |
| 3 | Enter the statements in Rekor (`cosign attest-blob --key …`), or run a tile log. Print the log index on wiki pages. | `cosign`, or nothing for a self-run log |
| Later | Build releases in GitHub Actions with artifact attestations (SLSA Build L2). Join the C2PA conformance programme only if lexflow ships as a product. | — |

The package design in [canonical-workflows.md](canonical-workflows.md) §5 numbers the same work differently. Phases
0 and 1 match. Phase 2 here (C2PA) is phase 3 there, and phase 3 here (Rekor) is phase 6 there.

## 6. Prototype design (not built)

### 6.1 Proposed layout of a release

```
out/releases/<model_id>/<release_id>/
  sections.json  facts.json  model.json  checks.json
  <q>.bpmn  <q>.semantic.bpmn  <q>.dmn  <q>.svg  <q>.png
  wiki/<page_id>.txt            # the exact text saved, with page id and revision in release.json
  wikibase/<Q…>@<rev>.jcs.json  # canonical snapshot of the statements lexflow wrote
  forms/…                       # when the model has drafts
  provenance/
    release.intoto.json         # DSSE envelope: SLSA provenance, subjects = all files above
    checks.intoto.json          # DSSE envelope: in-toto test-result
    review.intoto.json          # DSSE envelope signed by the reviewer (custom predicate)
    *.sigstore.json             # cosign bundles with Rekor inclusion (phase 3)
    *.c2pa                      # C2PA sidecars (phase 2)
```

### 6.2 Proposed release statement (abridged, illustrative)

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {"name": "model.json", "digest": {"sha256": "…"}},
    {"name": "records.bpmn", "digest": {"sha256": "…"}},
    {"name": "wiki/lexflow:va:records@1760100000.txt", "digest": {"sha256": "…"}}
  ],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": {
    "buildDefinition": {
      "buildType": "https://github.com/alibama/lexflow/blob/<commit>/docs/design/c2pa-provenance.md#build-type",
      "externalParameters": {"state": "va", "question": "records", "tier": "reviewed",
                             "method": "assistant-edited", "curated_file": "curated/va/records.json"},
      "resolvedDependencies": [
        {"uri": "https://…/us_va_statutes.parquet", "digest": {"sha256": "…"},
         "annotations": {"dataset": "open-us-law", "version": "v2026.09.1"}},
        {"name": "Va. Code § 2.2-3704", "uri": "open-us-law:act:<act_id>", "digest": {"sha256": "<text sha256>"}},
        {"uri": "git+https://github.com/alibama/lexflow@<commit>", "digest": {"gitCommit": "<commit>"},
         "annotations": {"dirty": false}}
      ]
    },
    "runDetails": {
      "builder": {"id": "https://github.com/alibama/lexflow/builders/workstation"},
      "metadata": {"invocationId": "<release_id>", "startedOn": "…", "finishedOn": "…"}
    }
  }
}
```

The `buildType` URI must point to a page that explains the build. Its exact location is for the repository's owner
to choose.

### 6.3 On the wiki page (a proposal for `lexflow/publish/lexipedia.py`)

A short "Provenance" section would sit under the checks. It would show:

- the release id;
- the release statement's SHA-256;
- the Rekor log index (or the lexflow log's position) with its link;
- the statute release, file SHA-256, section act ids and text SHA-256s;
- the method or tier, and the review record (organisation, role, or "Claude (model id), run by the lexflow
  operator");
- a link to the release folder;
- the commands to verify.

It names no private person.

### 6.4 The auditor's procedure

1. Read the page's Provenance section. Fetch the page source at the stated revision through the DokuWiki API
   (`getPage(page, rev)`), and fetch the `.bpmn` media file. Compute their SHA-256.
2. `cosign verify-blob-attestation --bundle release.sigstore.json --key lexflow.pub --type <the type used when
   attesting> <file>` for each file. `attest-blob` accepts `slsaprovenance1` among its types. This checks the DSSE signature, Rekor inclusion and the subject digest. Without phase 3, run the
   verifier script with the published key.
3. Download open-us-law's `index.json` for the stated version and the parquet. Check the parquet's SHA-256 against
   both the index and `resolvedDependencies`. Read the rows by act id and hash each `text`. They must equal the
   section digests, and every quote in `model.json` must appear in them. The repository's quote check does this.
4. Optionally, reproduce the build: run lexflow at the commit on the recorded `facts.json` and compare the BPMN, DMN
   and SVG bytes. Compilation is deterministic, as far as this design assumes; extraction by a model is not. This test
   would check the assumption.
5. Verify `checks.intoto.json`, and `review.intoto.json` with the reviewer's published key.
6. For a diagram or letter someone sent them: `c2patool <file> -d trust --trust_anchors lexflow-root.pem` (the asset
   path first, then `-d`, then the `trust` subcommand, as the usage page gives it; §2.7). The
   ingredient chain must reach the release, and the embedded `xyz.lexipedia.lexflow.release` reference must equal the release
   statement's digest.
7. For Wikibase: `Special:EntityData/Q….json?revision=N`. Take JCS of the lexflow-written statements and compare.

### 6.5 Tests the prototype would need

- Tampering: change one byte of the BPMN, the wiki source or a section text, and verification fails at the right step.
- A swapped statute release, a swapped model digest, or a dirty tree passed off as clean is detected.
- A stripped SVG manifest still verifies through the release statement.
- A sidecar for an unsupported type (JSON, BPMN): record what c2patool and c2pa-python actually report (§9).
- No private key and no `.env` value ever appears in output or logs.

## 7. Downloads a prototype would need (none made; each needs the user's approval)

The container runs Python 3.12.15 on x86_64 Debian 12 (glibc 2.36). `requests` 2.34.2, `toml` 0.10.2 and `cffi`
2.1.1 are installed; `cryptography` is not.

| What | Source | Size | Licence | Why | Phase |
|---|---|---|---|---|---|
| `cryptography` 50.0.2, `cp311-abi3-manylinux_2_34_x86_64` wheel | [PyPI](https://pypi.org/project/cryptography/50.0.2/) | 4,752,576 bytes | Apache-2.0 OR BSD-3-Clause | DSSE signing (ES256 or Ed25519), the private dev CA, and c2pa-python's dependency | 1 |
| `c2pa-python` 0.38.0, `py3-none-manylinux_2_28_x86_64` wheel | [PyPI](https://pypi.org/project/c2pa-python/0.38.0/) | 15,334,006 bytes | MIT OR Apache-2.0 | Build, sign and read C2PA manifests in the container. Install the wheel; a source build would download a native library as well | 2 |
| `c2patool` v0.28.2, `x86_64-unknown-linux-gnu.tar.gz` (Windows: `x86_64-pc-windows-msvc.zip`, 10,921,799 bytes) | [GitHub release](https://github.com/contentauth/c2patool/releases/tag/v0.28.2) | 12,718,260 bytes | Apache-2.0 (GitHub); README: Apache-2.0 and MIT | Independent validation, as an auditor would run it; the trust subcommand | 2 (auditor) |
| C2PA Trust List and TSA Trust List PEMs (optional) | [conformance-public/trust-list](https://github.com/c2pa-org/conformance-public/tree/main/trust-list) | 37,911 and 28,863 bytes | CC BY 4.0 | Only to show how a file validates against the public lists. Not needed with a private CA | 2 (optional) |
| `cosign` v3.1.3, `cosign-linux-amd64`, with its `.sigstore.json` bundle (6,406 bytes) to verify the download | [GitHub release](https://github.com/sigstore/cosign/releases/tag/v3.1.3) | 141,178,250 bytes | Apache-2.0 | `attest-blob` and `verify-blob-attestation`; Rekor entries | 3 (or a self-run log, no download) |

Not recommended for the first prototype:

- `sigstore` (sigstore-python) 4.5.0 is 111,724 bytes but pulls in `pyOpenSSL`, `tuf`, `rfc3161-client`, `id`,
  `pyjwt`, `rich`, `rfc8785`, `pyasn1`, `platformdirs`, `sigstore-models` and `sigstore-rekor-types`. Their sizes were
  not read.
- A W3C VC library.
- The c2pa-rs test certificates: a locally made private CA replaces them.

## 8. Changes proposed elsewhere (not made)

| Where | Change |
|---|---|
| `lexflow/ir.py` | `SectionText`: `act_id`, `sha256` (of the exact UTF-8 text). `Provenance`: `statute: [{dataset, version, file, url, bytes, sha256}]`, `source: {repo, commit, dirty, diff_sha256}`, `extraction: {models: [{name, digest}], prompt_sha256, selector: {version, settings_sha256}}`, `release: {statement_sha256, log: {kind, index, url}}`. `Review`: `records: [{kind: ai-assistant / organisation / role, id, model, date, scope, result, statement_sha256}]` in place of free-text `reviewers` |
| `lexflow/extract/ollama.py:150`, `lexflow/ask/reference.py:202`, `lexflow/extract/selector.py:476` | Keep the short hashes as cache keys, and record the full SHA-256 alongside them |
| `lexflow/municipal/statutes.py`, `lexflow/municipal/build.py` | Copy the `statute_files` row (version, file, SHA-256) into each model's provenance; set `act_id` on each `SectionText` |
| `lexflow/publish/dokuwiki.py` | After `save_page`, call `core.getPageInfo` and record the revision; compute SHA-256 of the saved text; upload sidecars as media. This needs the wiki owner to allow the media types (`.c2pa`, `.json`) |
| `lexflow/publish/wikibase*.py` | Record `lastrevid` for each item written, plus a JCS digest of lexflow's statements; propose a "provenance statement" (URL) property and a "content digest" qualifier, following the property-proposal pattern in `docs/design/terms-wikibase.md` |
| `lexflow/publish/lexipedia.py` | The Provenance section (§6.3) |
| `lexflow/api/app.py` | `Link: <…>; rel="c2pa-manifest"` headers on the routes that serve BPMN, DMN, SVG and model JSON |
| A new `lexflow/provenance/` package | `release_statement()`, `sign_dsse()`, `verify()`, and in phase 2 `c2pa_embed()` and `c2pa_sidecar()` |

## 9. Open questions

- **Sidecars for unsupported formats.** Will c2patool or c2pa-python validate a `.c2pa` sidecar against a JSON,
  BPMN or DokuWiki-text file? The SDK's format list does not include them, so the hard binding may not be checked. This
  is the first thing a prototype must test. If they fail, those files are audited through the in-toto layer only.
- **Collection hash support.** Does c2pa-rs create and validate `c2pa.hash.collection.data`? This was not found in
  the documents read.
- **Late reviews in C2PA.** Can a review given after release be expressed with a CAWG identity assertion in an update
  manifest, given that the assertion must reference a hard binding? If not, reviews stay in signed review statements,
  as §3.3 proposes.
- **Time-stamps.** Which TSA should lexflow use? Does DigiCert's public timestamp URL, used in the SDK examples, chain
  to the C2PA TSA Trust List? Sigstore's TSA is not on that list.
- **Public log or own log.** Rekor entries are permanent. A project key keeps personal data out, but a mistaken
  release statement stays in the log for good. Is that acceptable for a sandbox wiki, or should lexflow run its own
  tile log and add witnesses later?
- **Who reviews, and as what identity.** Reviewers should be organisations or roles, never private persons, in public
  outputs. Which reviewers does the user expect, and do they hold X.509 or VC credentials?
- **Wiki administration.** Allowing `.c2pa` and `.json` uploads and adding the Provenance section are changes for the
  wiki owner.
- **Licences.** The open-us-law compilation is CC BY-NC 4.0 (noted in `lexflow/municipal/statutes.py`). Statements and
  manifests carry digests and act ids, not the text, except `sections.json`, which the wiki already reproduces. The
  CommonForms README states no licence.
- **Label namespace and URIs.** C2PA needs entity-specific labels under a domain the entity holds. This note uses
  `xyz.lexipedia.lexflow.*`, from the user's own domain. The SLSA `buildType` and `builder.id` URIs also need a stable
  home. Both are the user's choice.
- **Conformance.** Only worth joining if lexflow becomes a product that others run. For a sandbox audit, a private CA
  plus a public log is enough.

## Sources

All read on 10 October 2026. Each was opened, read-only.

**C2PA and CAI**
- C2PA Technical Specification 2.4 (April 2026): https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html. Sections used: §5.3 version history, §6–§11, §13–§15, §18 (assertions, actions, ingredients, time-stamps, repository receipt, digital source types), §20 patent policy, Appendix A (A.3.3 SVG, A.4 PDF, A.7 HTML, A.8 unstructured text, A.9 structured text). The text licence is CC BY 4.0.
- C2PA 2.4 specifications index: https://spec.c2pa.org/specifications/specifications/2.4/index.html (`https://c2pa.org/specifications/` redirects to `spec.c2pa.org`)
- C2PA Explainer 2.2: https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html
- C2PA Guidance for AI and ML 2.3: https://spec.c2pa.org/specifications/specifications/2.3/ai-ml/ai_ml.html
- C2PA Human and Organizational Identity Recommendation: https://spec.c2pa.org/specifications/specifications/2.4/identity/identity.html
- C2PA conformance: https://c2pa.org/conformance/; Conformance Program v0.2: https://raw.githubusercontent.com/c2pa-org/conformance-public/main/docs/v0.2/C2PA%20Conformance%20Program.md; documents list via https://api.github.com/repos/c2pa-org/conformance-public/contents/docs/v0.2; trust lists via https://api.github.com/repos/c2pa-org/conformance-public/contents/trust-list; TSA list content: https://raw.githubusercontent.com/c2pa-org/conformance-public/main/trust-list/C2PA-TSA-TRUST-LIST.json; repository licence via https://api.github.com/repos/c2pa-org/conformance-public/license
- CAI: get a certificate: https://opensource.contentauthenticity.org/docs/signing/get-cert; test certificates: https://opensource.contentauthenticity.org/docs/signing/test-certs; ManifestDefinition schema: https://opensource.contentauthenticity.org/docs/manifest/json-ref/manifest-definition-schema
- c2pa-rs: https://github.com/contentauth/c2pa-rs; supported formats: https://raw.githubusercontent.com/contentauth/c2pa-rs/main/docs/supported-formats.md; PDF handler: https://raw.githubusercontent.com/contentauth/c2pa-rs/main/sdk/src/asset_handlers/pdf_io.rs
- c2patool: https://github.com/contentauth/c2patool; latest release via https://api.github.com/repos/contentauth/c2patool/releases/latest; licence via https://api.github.com/repos/contentauth/c2patool; usage: https://raw.githubusercontent.com/contentauth/c2patool/main/docs/usage.md; signing: https://raw.githubusercontent.com/contentauth/c2patool/main/docs/signing.md; manifest: https://raw.githubusercontent.com/contentauth/c2patool/main/docs/manifest.md
- c2pa-python: README https://raw.githubusercontent.com/contentauth/c2pa-python/main/README.md; usage https://raw.githubusercontent.com/contentauth/c2pa-python/main/docs/usage.md; API https://contentauth.github.io/c2pa-python/api/c2pa/index.html; PyPI https://pypi.org/pypi/c2pa-python/json and https://pypi.org/pypi/c2pa-python/0.38.0/json
- c2pa-js: https://raw.githubusercontent.com/contentauth/c2pa-js/main/README.md
- c2pa-html (third party): https://docs.rs/c2pa-html
- SSL.com C2PA page: https://www.ssl.com/article/c2pa-enterprise-content-authenticity-solutions/; DigiCert C2PA page: https://www.digicert.com/solutions/c2pa-media-trust
- IPTC Digital Source Type vocabulary: https://cv.iptc.org/newscodes/digitalsourcetype/

**CAWG**
- CAWG index: https://cawg.io/; identity index: https://cawg.io/identity/
- Identity Assertion 1.3 (DIF Ratified, 17 Aug 2026): https://cawg.io/identity/1.3/; 1.2 (15 Dec 2025): https://cawg.io/identity/1.2/
- Endorsement Assertion 1.0 draft: https://cawg.io/endorsement/1.0-draft/

**in-toto, SLSA, Sigstore, GitHub**
- in-toto Attestation Framework: https://raw.githubusercontent.com/in-toto/attestation/main/spec/README.md; Statement: https://raw.githubusercontent.com/in-toto/attestation/main/spec/v1/statement.md; Envelope: https://raw.githubusercontent.com/in-toto/attestation/main/spec/v1/envelope.md; predicates list via https://api.github.com/repos/in-toto/attestation/contents/spec/predicates; test-result: https://raw.githubusercontent.com/in-toto/attestation/main/spec/predicates/test-result.md
- SLSA: https://slsa.dev/spec/; v1.2 build provenance: https://slsa.dev/spec/v1.2/build-provenance; VSA: https://slsa.dev/spec/v1.2/verification_summary; build track basics: https://slsa.dev/spec/v1.2/build-track-basics
- Sigstore: Rekor overview https://docs.sigstore.dev/logging/overview/; Fulcio https://docs.sigstore.dev/certificate_authority/overview/; security model https://docs.sigstore.dev/about/security/; signing blobs https://docs.sigstore.dev/cosign/signing/signing_with_blobs/; attestations https://docs.sigstore.dev/cosign/verifying/attestation/; Rekor v2 GA https://blog.sigstore.dev/rekor-v2-ga/; cosign CLI docs https://raw.githubusercontent.com/sigstore/cosign/main/doc/cosign_attest-blob.md and https://raw.githubusercontent.com/sigstore/cosign/main/doc/cosign_verify-blob-attestation.md; cosign release via https://api.github.com/repos/sigstore/cosign/releases/latest; licence via https://api.github.com/repos/sigstore/cosign
- cosign consent prompt, as reproduced in Chainguard Academy: https://edu.chainguard.dev/open-source/sigstore/cosign/how-to-sign-a-container-with-cosign/index.md
- sigstore-python on PyPI: https://pypi.org/pypi/sigstore/json and https://pypi.org/pypi/sigstore/4.5.0/json
- GitHub artifact attestations: https://docs.github.com/en/actions/concepts/security/artifact-attestations

**W3C, IETF, C2SP, WHATWG**
- VC Data Model 2.0 (W3C Recommendation, 15 May 2025): https://www.w3.org/TR/vc-data-model-2.0/
- VC Data Integrity 1.0 (W3C Recommendation, 15 May 2025): https://www.w3.org/TR/vc-data-integrity/
- RFC 9943, SCITT architecture: https://www.rfc-editor.org/info/rfc9943; datatracker: https://datatracker.ietf.org/doc/draft-ietf-scitt-architecture/
- RFC 8785, JCS: https://www.rfc-editor.org/info/rfc8785
- C2SP tlog-tiles: https://c2sp.org/tlog-tiles
- HTML Standard, the script element and data blocks: https://html.spec.whatwg.org/multipage/scripting.html

**Wikis and other**
- DokuWiki API (`getPage`, `getPageInfo`): https://raw.githubusercontent.com/dokuwiki/dokuwiki/master/inc/Remote/ApiCore.php; syntax page: https://raw.githubusercontent.com/dokuwiki/dokuwiki/master/data/pages/wiki/syntax.txt (dokuwiki.org itself answered 402 to scripted reads, so the GitHub sources were used)
- Wikidata: Data access (`Special:EntityData`, `revision`): https://www.wikidata.org/wiki/Wikidata:Data_access
- CommonForms README: https://raw.githubusercontent.com/jbarrow/commonforms/main/README.md; card licences through the Hugging Face API: https://huggingface.co/api/models/jbarrow/FFDetr, https://huggingface.co/api/models/jbarrow/FFDNet-L, https://huggingface.co/api/datasets/jbarrow/CommonForms
- cryptography on PyPI: https://pypi.org/pypi/cryptography/json and https://pypi.org/pypi/cryptography/50.0.2/json

Repository files read: `lexflow/ir.py`, `lexflow/municipal/statutes.py`, `lexflow/municipal/build.py`,
`lexflow/store/db.py`, `lexflow/bpmn_xml.py`, `lexflow/validate.py`, `lexflow/render_svg.py`,
`lexflow/publish/dokuwiki.py`, `lexflow/publish/lexipedia.py`, `lexflow/publish/wikibase.py`,
`lexflow/publish/wikibase_lexipedia.py`, `lexflow/forms/draft.py`, `lexflow/extract/ollama.py`,
`lexflow/extract/selector.py`, `lexflow/ask/reference.py`, `curated/va/records.json`, `requirements.txt`, `Dockerfile`,
`.github/workflows/ci.yml`, `docs/design/forms-plan.md`, `docs/design/lab-plan.md`, `docs/design/terms-wikibase.md`,
`docs/design/bpc-480-decision.md`.
