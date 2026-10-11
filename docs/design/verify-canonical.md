# Verification: canonical workflow packages, CommonForms and C2PA

_10 October 2026. Adversarial check of [canonical-workflows.md](canonical-workflows.md) and its two research notes,
[commonforms.md](commonforms.md) and [c2pa-provenance.md](c2pa-provenance.md). This note is the only file written in
the repository. Method: web pages, READMEs, model cards, PyPI and npm metadata, GitHub API listings and specifications
were read with GET requests, or HEAD requests for two wheel sizes. Each request used lexflow's research User-Agent,
with at least 1.2 s between requests to one host. Pages were searched in memory and not saved. Nothing was downloaded
to keep, installed, built, signed or published. In `lexflow-app-1` the checks were read-only: `SELECT`s on
`/data/lexflow.db` and the per-state search indexes opened with `mode=ro`, plus `pip list` and `mount`. `.env` was not
read. No job, build or benchmark was run. People appear only as authors in citations, and issue comments are cited
by number._

## Verdict

- **Most facts hold.** Every count measured from the repository was measured again and matches. So do the CommonForms
  licence facts, the model files and the paper figures, and most of the C2PA, CAWG, conformance and standards
  quotes. The same goes for the sizes and licences in the downloads list.
- **Four provenance claims go further than the sources allow:**
  - Development C2PA manifests stop validating when the leaf certificate expires (at most 366 days).
  - `human_validated` would be a false statement on a *Claude-checked* package.
  - Rekor v2 has no search index, so an auditor cannot show that a status is current.
  - The `audit_head` check fails as soon as any event is added after the last status statement.
- **Six fit problems with the code:**
  - Four of the five proposed tables cannot go in `db.SYNCED`.
  - All 22 reviewed BPMN files say `reviewStatus="draft"`, inside the payload that is signed.
  - The build writes the current time into `model.json`.
  - The container has no `.git` to read a commit from.
  - The sign job cannot have a key mount of its own.
  - A passphrase passed as a job arg would be stored in the database.
- **Downloads.** The list leaves out about 43 MB that phase 2b would pull in, `av` (PyAV, with FFmpeg bundled)
  among them. It also leaves out `dmn-js`, which phase 4's DRD view needs. One fact is wrong: D.C. has UELMA in
  the local copy, so the count is seven of eleven jurisdictions, not six.

## 1. Confirmed

### 1.1 Repository, database and fixture (measured again, read-only)

| Claim | Result |
|---|---|
| 22 reviewed models | 22 of 104 `process_models` rows have `tier='reviewed'`: records and business for the 11 jurisdictions in `curated/` |
| Stored check metrics | 757 quotes checked, 0 misses. 0 BPMN or DMN XSD errors. 0 bpmnlint errors and 0 warnings. 22 of 22 nets sound. 0 ungrounded activities |
| 229 sections; 56 tables, 52 FIRST | 229 sections. 56 decision tables: 52 FIRST and 4 UNIQUE (hit policies read from the stored DMN) |
| `il.records` counts | 48 quotes, 3 decisions, 12 rules, 3 sections (5 ILCS 140/3, 9, 9.5) |
| Illinois statute row | `v2026.09.1`, `us_il_statutes.parquet`, the URL shown, SHA-256 `8b698ea5…986cec`, 31,415,695 bytes, 72,251 sections |
| Five Illinois act ids, text SHA-256 values and byte counts | All five match. The index stores the parquet `text` column unchanged (`ask/index.py` build loop), and all five texts are ASCII |
| Forms: 17 / 12 / 15 / 12 / 577 / 53 / 1 / 2 | Reproduced from `fixtures/forms/forms.json`: 17 of the 22 have an `exact` form, and 12 of those an exact `pdf_form`. That is 15 distinct forms: 12 AcroForm with 577 fields on 53 pages, the flat PAC form (1 page), and 2 unread (`il-sos-llc-5-5`, `va-llc-1011`) |
| `lex_checks` | Containment only. It visits nodes, data, message flows, decisions and rules, but not `SequenceFlow.sources` (`validate.py:126-160`) |
| dmnlint and Spiff not run per model | `quality.assess` imports only `bpmnlint`, `lex_checks` and `xsd_errors`. `dmnlint()` and `spiff_parser()` are called only from `simulate.py`, `scripts/build_all.py`, tests and `out/design/check_bpc_480.py` |
| Code references | `SectionText` has no act id or hash (`ir.py:208`). `Review.status` includes `legal-reviewed`. The six draft `LEVELS` are right. `strip_history` is at `statutes.py:139`, and `COLUMNS` (lines 26-27) holds `act_status` and `last_amended_year`, which the index lacks. `effective()` is at `ask/index.py:45`. There are 12 `CALENDARS` (`deadlines.py:723`). "Process map (draft)" is at `lexipedia.py:324` and `viewModel` at `app.js:685`. `retrieved_from` is `open-us-law <act_id>` |
| Mounts | `/data` is the `lexflow-data` volume and `./data/raw` is bind-mounted. `/app/out` is baked into the image, not mounted |
| Phase 0 needs no download | `jsonschema` 4.26.0 (for C14), `pyarrow` 25.0.1 and `SpiffWorkflow` 3.2.0 are installed, and `tools/node` has `dmnlint`, `dmn-moddle` and `bpmnlint`. `cryptography` is not installed |
| Licence and publishing rules | `statutes.py` docstring: CC BY-NC 4.0, commercial use needs a licence from Vaquill. The project memory note says "Only Claude-reviewed or two-extraction-agreed models go to either site" and "mark them as drafts instead" |
| Sibling designs | authority-wikibase: 357 "Unreviewed draft" items, 0 qualifiers, structured data CC0. authority-standards §5.4: the Illinois route as described. bpc-480: `lex:decisionMaker`, `Requires`, `KnowledgeSourceRef`, "nothing unused". entities-contacts: D2, D7 (3 hijacked domains), D8 (43 % stale), D9 |
| UELMA wording | RCW 1.70.010(2)(c) and (3)(c), 1.70.040 and 1.70.050(1), Cal. Gov. Code §§ 10291(c) and 10294: every quote is word for word in the local copy. The six listed jurisdictions do carry the act |

### 1.2 CommonForms

- **Repository and package.**
  - GitHub reports `"license": null`, and the root holds no LICENSE file (its 9 entries were listed). Head is
    `f5f400727132…`, of 17 June 2026.
  - The PyPI wheel of 0.2.1 declares no licence. It is 9,741 bytes, uploaded 26 November 2025.
  - The `pyproject.toml` dependencies are as listed.
- **Code** (`commonforms/inference.py`):
  - `from ultralytics import YOLO` runs at module import, whatever model is chosen.
  - FFDetr loads as `RFDETRMedium`.
  - `image_size = 1024` is overwritten inside `extract_widgets` and is never passed to `predict`.
  - `hf_hub_download` is called with no `revision`.
  - `prepare_form` defaults to FFDetr, 1024 px and confidence 0.4.
- **Issues.**
  - #9: the owner wrote on 12 October 2025, "The code is Apache, but I need to check if the model weights can be
    since they're YOLO models."
  - #9, October 2026 comments: the Apache-2.0 tag is "the only licence statement on the weights". One comment reports
    recall 0.64 and 0.85 at 576 and 1024 px, with precision 0.78 and 0.85.
  - #41 is open, opened 21 August 2026, and says "there is no grant that would let anyone redistribute the weights".
- **Hub.**
  - FFDetr card: `license: apache-2.0`, `base_model: Roboflow/RF-DETR`, revision `56f4e4235e28…`. `FFDetr.pth` is
    134,960,879 bytes, LFS SHA-256 `f852e1ba…69585ef`.
  - The FFDNet-L card has no licence. Its revision is `82547d6c…`.
- **Paper** (arXiv 2509.16506v1).
  - 9 M and 25 M parameters; "roughly 16ms" and "5ms" a page on a 3090 Ti.
  - Table rows: S 61.5/71.3/84.2/72.3 and L 71.4/78.1/93.5/81.0.
  - Domains: government and administrative 82.8 (17.3 % of pages), law and justice 79.7.
  - The "processing error" footnote, and that Acrobat "does not detect choice buttons at all".
- **Third-party pages.** The Ultralytics licence page says "All Ultralytics YOLO trained models fall under the
  AGPL-3.0 License by default". YOLO11l's ONNX CPU time is 238.6 ms at 640 px.

### 1.3 C2PA, CAWG and conformance

- **C2PA 2.4 specification.**
  - §18.28 (`c2pa.ai-disclosure`) has `modelType`, which is required, and the three `humanOversightLevel` values.
    Table 12 has a generic `c2pa.types.model`.
  - `c2pa.types.audit-log` exists, and so does the hashed External Reference (§18.24.1-2).
  - The EKU is `c2pa-kp-claimSigning` (1.3.6.1.4.1.62558.2.1). The `trainedAlgorithmicData` value exists.
  - The `.c2pa` sidecar lookup ("same path or URI").
  - The three validation states. A user can add trust anchors for this EKU (§14.4.1, §15.7), so "Trusted for an
    auditor who adds lexflow's root" holds through `c2patool … trust --trust_anchors`.
- **Conformance.**
  - c2pa.org/conformance: the Trust List launched "in mid-2025", and the Interim Trust List "has been retired".
  - Certificate Policy v0.2, AL1 leaf: validity at most 366 days; Subject "MUST match" the CPL entry and "Requires C,
    O, CN"; RSA of 2048 bits or more, P-256, P-384 or P-521, or Ed25519; key usage `digitalSignature` and
    `nonRepudiation`; `cA=FALSE`. The CA re-authenticates the subscriber at least every 398 days.
  - Generator Product Security Requirements, O.2 Level 1: the quotes are right. The "Minimal Generator Product"
    backend example exists.
- **TSA Trust List.** `ListIssueDateTime` 2026-08-05, `NextUpdate` 2027-08-05, 13 trusted entities. The PEM files are
  37,911 and 28,863 bytes.
- **C2PA Explainer 2.2.** Content Credentials "do not provide value judgments about whether a given set of provenance
  data is 'true'".
- **CAWG identity 1.3.** A DIF Ratified Specification of 17 August 2026. Accepted EKUs must include
  `id-kp-documentSigning`. The interim rules run to 31 March 2027. The status codes are
  `cawg.x509.credential.trusted` and `cawg.x509.credential.untrusted`.
- **c2pa-rs.** Its format list has `pdf`, `png` and `svg`, and no JSON or generic XML.
- **Tools.**
  - c2patool v0.28.2 (8 October 2026): 12,718,260 bytes for Linux, 10,921,799 for Windows.
  - c2pa-python 0.38.0 (29 September 2026): 15,334,006 bytes, MIT OR Apache-2.0, requires `toml`, `cryptography`
    and `requests`.
  - cosign v3.1.3: 141,178,250 bytes, with a 6,406-byte bundle. The KMS URI schemes are as listed.
  - Rekor v2 keeps only `hashedrekord` and `dsse` entries, and stores no attestations.

### 1.4 Other standards and law

- **Integrity formats.**
  - RFC 8493: "Every payload manifest MUST list every payload file name exactly once", and "One or more linear
    whitespace characters (spaces or tabs)". The reserved bag-info names are right.
  - GNU coreutils' untagged format ("the checksum, a space, a flag indicating binary or text input mode, and the
    file name") makes the two-space manifest readable by `sha256sum -c`.
- **Time-stamps and signatures.**
  - RFC 3161 §2.1: items 6, 8 and 9 are quoted correctly.
  - The in-toto Statement quotes are right ("MUST have `digest` set", "matched purely by digest"), as are DSSE PAE
    and SLSA v1.2 ("MUST be verified downstream").
- **Web Crypto.** The Recommendation is dated 26 January 2017. Level 2 is a First Public Working Draft of
  22 April 2025, with Ed25519.
- **Law.**
  - Fed. R. Evid. 902(14) and the committee-note quotes are right.
  - GR 39(d) and the petition's item 4 are as quoted (WSR 22-01-031).
- **Tools and vocabularies.**
  - pypdf 6.12.0 (2026-05-21) lists "Block encrypting writer in incremental mode (#3789)" under Documentation.
  - `openssl ts -verify` takes `-digest`.
  - ELI `owl:versionInfo` is 1.5, and the four properties exist. `eli:in_force` is an object property, so
    `act_status` maps to a concept, not a string.
  - DokuWiki has `getPage($page, $rev)` and `getPageInfo(…, $hash)`.
- **Download sizes that match.**
  - `cryptography` 50.0.2 `cp311-abi3-manylinux_2_34_x86_64`: 4,752,576 bytes.
  - `pypdf` 6.20.0: 401,710 bytes, BSD-3-Clause.
  - `pypdfium2` 5.14.0: 3,799,581 bytes.
  - `rfdetr` 1.11.2: 788,908 bytes, Apache-2.0.
  - `torch` 2.14.1+cpu: 196,253,677 bytes and `torchvision` 0.29.1+cpu: 1,708,098 bytes (HEAD `Content-Length`).
  - `transformers` 5.19.0: 12,599,123 bytes.
  - `tokenizers`: 3,396,193 bytes. `safetensors`: 516,040 bytes.
  - `supervision` 0.30.9: 409,708 bytes, MIT.

### 1.5 Privacy: what holds

- No proposed endpoint receives a filled form, a case or a person's file (§3.4). "Check a file I was sent" hashes in
  the browser.
- The time-stamp is opt-in and off by default. It sends only the 32-byte imprint.
- The six-field outcome rule of lab-plan §3 is unchanged. lab-plan's "a user's case is never posted to a public
  host" is respected.
- `bag-info.txt` carries no Contact fields. Reviewers are roles or organisations. The certificate's O is never a
  private person. C15 scans the bag.
- The remaining gaps are in §2.2 (B6) and §3.5.

## 2. Wrong

### 2.1 Facts

1. **UELMA is in seven of the eleven jurisdictions, not six** (Summary, §1.4).
   - The local copy (v2026.09.1) holds D.C. Code §§ 2-651.01 to 2-651.05, with act ids from
     `STATE_DC_T2_C6_S2-651.01` on.
   - § 2-651.04 reads: the official publisher "shall authenticate the record … unaltered from the official record".
   - § 2-651.05(a) gives the presumption of an accurate copy.
   - § 2-651.02 limits the subchapter to legal material first published electronically on or after 1 July 2017.
   - The short-title search missed it. A search for "legal material" AND "authenticate" finds it.
   - **Fix.** Add D.C. to the list and the counts. Its `official.uelma` names D.C. Code § 2-651.01 et seq.
2. **cosign hardware tokens need no custom build** (§4.2).
   - The documentation sentence is quoted correctly: PIV support "is not included in the standard release".
   - But the v3.1.3 release publishes `cosign-linux-pivkey-pkcs11key-amd64`, 140,294,536 bytes, with a 6,453-byte
     bundle.
   - **Fix.** Name that build as one more optional download.
3. **The DMN namespace is `/ns/decision/`** (§1.1 table).
   - `dmn_xml.py:45` writes `https://lexipedia.xyz/ns/decision/<slug>`. Only the BPMN uses `/ns/process/`
     (`bpmn_xml.py:108`).
4. **The c2patool command order** (§4.3 step 11; c2pa-provenance §2.7 and §6.4).
   - The usage page gives `c2patool <ASSET_PATH> trust [OPTIONS]`, so the asset path comes before `trust`, for
     example `c2patool copy.pdf trust --trust_anchors lexflow-root.pem`.
   - Put `-d` with the top-level options. Its exact position was not tested.
5. **c2pa-provenance §2.2 calls `c2pa.external-reference` "an unhashed, advisory link".**
   - In 2.4, §18.24.1 allows "an unhashed-ext-uri-map … or a hashed-ext-uri-map".
   - §18.24.2 gives the hashed variant for creation-process evidence, `c2pa.types.audit-log` included.
   - The 2.4 history: "Extended External Reference Assertion validation to cover hashed external reference
     assertions".
   - commonforms.md and canonical-workflows.md are right. **Fix** c2pa-provenance.md.
6. **c2pa-provenance §3.4 still puts "the FFDNet weights" and a CommonForms `softwareAgent` in the manifest.**
   - That contradicts commonforms.md §1.9 (an adapter on `rfdetr` with FFDetr, and no `commonforms` package),
     which canonical-workflows follows.
   - "The README states no licence for … the models or the dataset" is true of the README only. The FFDetr and
     dataset cards carry `apache-2.0`.
7. **"Virginia DPOR" is not an unmodelled process** (Summary; phase 2b).
   - Its forms link to steps in `curated_ask/license_conviction/va.json`: `apply` (partial) and `present_case`
     (partial).
   - What is missing is a `process_models` row: there are 0 license-conviction rows.
   - Say "not among the 22 process models".
8. **Minor.**
   - C1's "whitespace and curly quotes normalised": `_norm` (`validate.py:122-123`) folds whitespace and U+2019 only,
     not “ ” or ‘.
   - `<lex:model reviewStatus=…>` is at `bpmn_xml.py:187-190`; line 182 is `_collaboration`.
   - §1.7's fingerprint list leaves out `etag` and `last_modified`, which forms-plan §5 proposes and the conditional
     fetch needs.
   - The phase 2b row gives no licence for `torch`, `tokenizers` or `safetensors`, although the Summary says every
     download carries one.

### 2.2 Provenance claims that go too far

B1. **Development C2PA manifests stop validating when K3 expires** (§4.2 "Time").
  - Spec §15.8.2: when neither `sigTst` nor `sigTst2` is present, a manifest "is valid if the current time at
    validation is within the validity period of the signer's certificate and all CA certificates". Otherwise it
    "shall be rejected with a failure code of `claimSignature.outsideValidity`".
  - K3 lives at most 366 days, so a year later every diagram and fillable copy without a token fails. Yet old
    versions are to stay "downloadable and verifiable" (§2.4).
  - Rekor's integrated time does not help, because C2PA validators do not read it.
  - The private credential store "shall not apply to validating time-stamps" (§14.4.3). So the TSA has to be on the
    validator's TSA list (the C2PA TSA Trust List) or be added by the auditor.
  - **Fix.** Put an RFC 3161 token (`sigTst2`) in every manifest from phase 3, from a TSA on that list. Add a phase 3
    test: a manifest made with a short-lived test leaf still validates after the leaf expires.

B2. **`human_validated` on a Claude-checked package is false** (§2.5).
  - The spec's CDDL comment: `"human_validated" -> human reviewed/approved final output prior to release`.
  - A Claude-checked grade has no human review. Use `human_validated` only for person-reviewed or legal-reviewed
    grades. For Claude-checked, use `fully_autonomous` ("no human review after model output"), or leave the
    assertion out.
  - Also, `package_sign` runs only after an accepted review, so the "fully_autonomous before review" branch never
    applies to package files.

B3. **"C2PA proves who signed, from which inputs"** (§4.4).
  - C2PA hash-binds ingredient *manifests*. For an ingredient with no manifest, such as the official PDF or the
    parquet, the hash is only the signer's statement until the verifier hashes the file.
  - With a private CA, "who" is a certificate lexflow issued to itself.
  - Better wording: "that the holder of this key signed this manifest, and the file is unchanged since; the
    ingredients and actions are what the signer states".

B4. **"This shows the status is current"** (§4.3 step 5; §2.1 "in log order").
  - Rekor v2: "The search index has been removed."
  - An auditor cannot list every statement signed with K1. They see only the bundles lexflow ships, so a copy of the
    bag that leaves out a later `withdrawn` looks current.
  - **Fix.** Publish a signed, append-only index of every log entry per key (in the repository and on the wiki), or
    run a tile log that can be read in full. Until then, say "the latest status lexflow shows".

B5. **The `audit_head` check fails on every version that is checked again** (§4.3 step 5).
  - `package_verify` appends `verified` and `rechecked` events (§3.2), so the head moves past the logged
    `audit_head`.
  - **Fix.** The chain must contain the event whose `record_sha256` equals `audit_head`, and verify up to it.

B6. **The browser signature does not show order in time** (§3.8 step 3, "made the records in that order").
  - The holder of the key can sign a rebuilt chain at any time.
  - On the wiki, the case shares its origin with other plugins' scripts (lab-plan §2). Those scripts can call
    `crypto.subtle.sign` with a key read from IndexedDB: non-extractable stops export, not use.
  - Only the RFC 3161 token ties a record to a time.
  - Say "one key signed every record", and add the shared-origin caveat.

B7. **"Any edit breaks the chain"** (§3.3).
  - That holds only up to the last logged `audit_head`. A tail that was never anchored can be rewritten whole, and so
    can every draft trail (drafts are never logged, §2.5).

B8. **"Moving to production means swapping the certificate"** (§4.2).
  - The Security Requirements have six objectives, O.1 to O.6. At Level 1:
    - O.3 and O.4 require SCA or SBOM vulnerability analysis against the NVD;
    - O.5 requires TLS 1.3 between subsystems;
    - the conformance process itself (legal agreement, architecture document, samples, review) comes on top.
  - K3 also does not "mirror" the AL1 leaf profile. The Certificate Policy requires:
    - an EKU with `c2pa-kp-claimSigning` "in addition to at least one of id-kp-emailProtection, id-kp-documentSigning";
    - Certificate Policies with OID 1.3.6.1.4.1.62558.1.1;
    - AIA with OCSP, or CRL distribution points.
  - The CP's root profile asks for P-384 or P-521, while K2 is P-256. That is fine for a private root, but it is not a
    mirror.

### 2.3 Contradictions with the code and the sibling designs

C1. **`db.SYNCED` cannot hold four of the five tables** (§3.2).
  - `db.py`: synced tables "carry `state`, `updated_at` and `origin`". `turso.push` and `pull` filter on
    `state IN (…)` and `updated_at >= ?`.
  - Only `packages` has all three columns. `package_versions` lacks `state`, and the other three have none of them.
  - commonforms.md §3.3's form tables have the same problem.
  - **Fix.** Add the three columns, or sync `packages` and `package_versions` only and rebuild the rest from the bag.

C2. **Every canonical bag would ship a BPMN that says draft.**
  - All 22 reviewed models' stored BPMN read `reviewStatus="draft" method="gold-manual"` (read-only query).
  - The package never rewrites model files (§1.1), and §2.5 uses this attribute as the BPMN draft marker.
  - It cannot change after review without changing the digest the review signs.
  - **Fix.** Set `review.status` from the tier when the package compiles, or say the attribute is the IR's, not
    the package's.

C3. **`model.json` carries a build time.**
  - `municipal/build.py:225` passes `Provenance(…, created=db.now())` to `_compile`.
  - That breaks "no timestamp in `data/`" and C16's byte-identical rebuild.
  - The `package` step must pass a fixed `created` (the commit time, or null).

C4. **The container cannot see a commit.**
  - Only `lexflow/`, `curated*`, `dashboard/`, `docs/`, `fixtures/`, `scripts/` and `tests/` are bind-mounted. `/app`
    has no `.git` and no `git` binary.
  - `schemas/`, `tools/` and `out/` are baked into the image.
  - A `package` job cannot record `source.commit` or `dirty`, or check "the tree is clean" (C16, G11).
  - **Fix.** Record the image digest plus a commit passed in from the host (an environment variable or a read-only
    `.git` mount), or run the step from the host.

C5. **The key mount and the passphrase.**
  - Jobs are subprocesses of the app container (`jobs.py:1-7, 176-181`). A mount "into the sign job only" would
    therefore also be visible to the API and to every other job.
  - Job args are stored in `jobs.args` and passed as `--args <json>` on the command line. A passphrase "typed at sign
    time" through the dashboard would be kept in SQLite and shown in process listings. The container has no OS
    keyring.
  - **Fix.** Use a separate `sign` compose service with the mount, or sign from the host. Use a kernel-keyring or
    systemd credential (both named in O.2), and never a job arg.

C6. **`stale` needs a signature, and signing is user-triggered.**
  - §3.1 routes `stale` through `package_sign`, which is "user-triggered only". Until the operator signs, the public
    log still says `canonical`.
  - **Fix.** Allow `package_verify` to sign `stale` statuses automatically, as a narrow exception, or show "re-check
    pending" on the wiki.

C7. **Two profiles, one version number.**
  - The key of `package_versions` is `(package_key, version)`, while full and lean have different `package.json`
    digests (§1.14). One version number cannot hold both.
  - Put `profile` in the key, or give each profile its own number.

C8. **Two *review status* properties.**
  - authority-wikibase §4.2 already proposes *review status* (reviewed, agreed or draft) on process, step and role
    items. §3.7 reuses the name for package statuses.
  - Use two properties: the model tier, and a *package status* on package items only.

C9. **Job groups.**
  - `CPU_HEAVY` duplicates the existing `EXCLUSIVE = {build, quickstart, models, ask}` (`jobs.py:24`). Adding
    `form_fields` there is enough.
  - `PACKAGING` would newly stop `publish` and `wikibase` from running beside `build`. That change to existing steps
    is not stated.

C10. **Smaller points.**
  - `bag.zip` is not reproducible across days: `bag-info.txt` has `Bagging-Date`, and `provenance/` grows. Only
    `data/` is reproducible.
  - The phase numbers differ between notes: c2pa-provenance §5.3 puts C2PA in phase 2 and Rekor in 3, this design in
    3 and 6. The section references still resolve, but readers will be misled.

## 3. Missing

### 3.1 Downloads not listed

- **Phase 2b, the transitive packages the container lacks.** Latest versions, Linux x86_64 and CPython 3.12, read
  from PyPI on 10 October 2026; the resolver may pick others.

  | Package | Bytes | Licence (PyPI) | Pulled by |
  |---|---|---|---|
  | `av` 19.0.1 (`cp312-abi3-manylinux_2_28`) | 34,983,451 | BSD-3-Clause; wheels ship "with FFmpeg bundled", and the bundled build's licence was not checked | `supervision` |
  | `sympy` 1.14.0 | 6,299,353 | BSD | `torch` |
  | `mpmath` 1.4.1 | 567,787 | BSD-3-Clause | `sympy` |
  | `setuptools` 84.0.0 | 818,216 | MIT | `torch` (`>=77.0.3`) |
  | `rich` 15.0.0 | 310,654 | MIT | `typer` |
  | `typer` 0.27.3 | 123,312 | MIT | `transformers` |
  | `pyDeprecate` 0.9.0 | 102,725 | Apache-2.0 | `rfdetr` (`<0.10`), `supervision` |
  | `markdown-it-py` 4.2.0 | 91,687 | not stated | `rich` |
  | `mdurl` 0.1.2 | 9,979 | not stated | `markdown-it-py` |
  | `shellingham` 1.5.4 | 9,755 | ISC | `typer` |
  | **Total** | **43,316,919** | | |

  Already installed: matplotlib, scipy, networkx, Jinja2, fsspec, filelock, tqdm, PyYAML, regex, defusedxml,
  packaging, Pygments, annotated-doc, and huggingface_hub 2.2.0, which meets `transformers`' `>=1.31,<3.0`.
- **Phase 4: `dmn-js`.** It is needed for "the DRD through dmn-js" (§3.5). Only `bpmn-js` is installed
  (`/app/tools/web/node_modules`).
  - `dmn-js` 17.12.3 from npm: 7,795,743 bytes unpacked, plus `dmn-js-drd`, `-shared`, `-decision-table`,
    `-boxed-expression` and `-literal-expression`.
  - Licence: MIT terms plus a clause that the bpmn.io watermark "MUST NOT be removed or changed".
- **Phase 3.**
  - A TSA, for B1. It is a network service, not a download, but the plan needs it.
  - Optionally, `c2patool init trust`, which fetches the official trust lists.
- **Phase 6.**
  - The prebuilt PIV cosign (§2.1 item 2), as an option.
  - A self-run tile log is "no download" only if lexflow writes it itself. The plan should say so.

### 3.2 Open questions this check answers, or adds

- **Whether `rfdetr` fetches a backbone** (commonforms.md §3.2). Partly answered, read at `develop`:
  - `RFDETRMediumConfig` has `patch_size` 16 and `resolution` 576.
  - `dinov2.py` sets `load_dinov2_weights = False` when the patch size is not 14, and builds the backbone from the
    JSON configs bundled in `rfdetr`, so there is no `facebook/dinov2-…` fetch.
  - Confirm at 1.11.2 under `HF_HUB_OFFLINE=1`.
  - The 576 px default also explains issue #9's observation.
- **c2pa-rs support for the 2.4 assertions.** Its CHANGELOG mentions neither `c2pa.ai-disclosure` nor the External
  Reference. Phase 3 must test both. If neither is supported, they can go in as generic assertions, and validators
  will not check their schemas.
- **lab-plan §3's table needs the new data flows:**
  - the TSA request, which sends the imprint, the person's network address and the time to a third party the person
    chose;
  - the file names in `proof-<case>.json`, which can contain personal names, so let the person blank them before
    sharing;
  - the shared wiki origin (B6).
- **Secure context.** `crypto.subtle` needs one. `http://localhost:8000` qualifies; the dashboard reached by a LAN
  address does not.
- **`openssl ts -verify -in` reads a TimeStampResp.** If the proof keeps only the TimeStampToken, use `-token_in`
  (OpenSSL manual).
- **Scope.** 11 exact official PDF forms on the `curated_ask` step files (court debt, licence conviction, record
  sealing) are outside the 22-model plan. G7 grows to cover them when those processes get packages.

## Sources

All read on 10 October 2026, read-only.

- **CommonForms.**
  - GitHub API: https://api.github.com/repos/jbarrow/commonforms, `/contents/`, `/commits`, `/issues/41`,
    `/issues/9/comments`.
  - Raw files: https://raw.githubusercontent.com/jbarrow/commonforms/main/pyproject.toml and
    `/commonforms/inference.py`.
  - PyPI: https://pypi.org/pypi/commonforms/0.2.1/json.
  - Hub: https://huggingface.co/api/models/jbarrow/FFDetr?blobs=true, https://huggingface.co/api/models/jbarrow/FFDNet-L.
  - Paper: Barrow, J. (2025), arXiv:2509.16506, https://arxiv.org/html/2509.16506v1.
  - https://www.ultralytics.com/license; https://docs.ultralytics.com/models/yolo11/.
- **RF-DETR.** https://raw.githubusercontent.com/roboflow/rf-detr/develop/src/rfdetr/models/backbone/dinov2.py,
  `…/backbone/backbone.py`, `…/src/rfdetr/config.py`; tree via
  https://api.github.com/repos/roboflow/rf-detr/git/trees/develop?recursive=1.
- **C2PA.**
  - Specification 2.4: https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html (§14.3-14.4,
    §15.7-15.8, §18.24, §18.28, Table 12, version history).
  - Explainer 2.2: https://spec.c2pa.org/specifications/specifications/2.2/explainer/Explainer.html.
  - https://c2pa.org/conformance/.
  - Certificate Policy and Generator Product Security Requirements v0.2:
    https://raw.githubusercontent.com/c2pa-org/conformance-public/main/docs/v0.2/.
  - Trust lists: https://api.github.com/repos/c2pa-org/conformance-public/contents/trust-list and
    `…/trust-list/C2PA-TSA-TRUST-LIST.json`.
  - c2pa-rs: https://raw.githubusercontent.com/contentauth/c2pa-rs/main/docs/supported-formats.md and `…/CHANGELOG.md`.
  - c2patool: https://raw.githubusercontent.com/contentauth/c2patool/main/docs/usage.md;
    https://api.github.com/repos/contentauth/c2patool/releases/tags/v0.28.2.
  - c2pa-python: https://pypi.org/pypi/c2pa-python/0.38.0/json.
- **CAWG.** https://cawg.io/identity/1.3/.
- **Sigstore.** https://api.github.com/repos/sigstore/cosign/releases/tags/v3.1.3;
  https://docs.sigstore.dev/cosign/key_management/overview/;
  https://docs.sigstore.dev/cosign/key_management/hardware-based-tokens/; https://blog.sigstore.dev/rekor-v2-ga/.
- **Standards.**
  - https://www.rfc-editor.org/rfc/rfc8493.txt; https://www.rfc-editor.org/rfc/rfc3161.txt.
  - https://www.gnu.org/software/coreutils/manual/html_node/cksum-output-modes.html.
  - https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/; https://www.w3.org/TR/webcrypto-2/.
  - https://raw.githubusercontent.com/in-toto/attestation/main/spec/v1/statement.md;
    https://raw.githubusercontent.com/secure-systems-lab/dsse/master/protocol.md;
    https://slsa.dev/spec/v1.2/build-provenance.
  - https://raw.githubusercontent.com/py-pdf/pypdf/main/CHANGELOG.md; https://docs.openssl.org/3.0/man1/openssl-ts/.
  - http://publications.europa.eu/resource/distribution/eli/owl/owl/eli.owl.
  - https://raw.githubusercontent.com/dokuwiki/dokuwiki/master/inc/Remote/ApiCore.php.
- **Law.** https://www.law.cornell.edu/rules/fre/rule_902; https://lawfilesext.leg.wa.gov/Law/WSR/2022/01/22-01-031.htm.
  D.C. Code §§ 2-651.01-.05, RCW 1.70, Cal. Gov. Code §§ 10291 and 10294, from lexflow's local open-us-law copy
  (v2026.09.1).
- **Packages.**
  - PyPI JSON for `rfdetr` 1.11.2, `supervision` 0.30.9, `transformers` 5.19.0, `torch` 2.14.1, `cryptography` 50.0.2,
    `pypdf` 6.20.0, `pypdfium2` 5.14.0, `av`, `sympy`, `mpmath`, `typer`, `setuptools`, `pyDeprecate`, `shellingham`,
    `rich`, `tokenizers`, `safetensors`, `markdown-it-py` and `mdurl`.
  - HEAD on https://download.pytorch.org/whl/cpu/ for the two CPU wheels.
  - npm: https://registry.npmjs.org/dmn-js/latest; https://raw.githubusercontent.com/bpmn-io/dmn-js/develop/LICENSE.
- **lexflow.**
  - Code: `lexflow/store/db.py`, `lexflow/store/turso.py`, `lexflow/pipeline/jobs.py`, `lexflow/pipeline/steps.py`,
    `lexflow/validate.py`, `lexflow/municipal/quality.py`, `lexflow/municipal/build.py`,
    `lexflow/municipal/statutes.py`, `lexflow/ask/index.py`, `lexflow/ir.py`, `lexflow/bpmn_xml.py`,
    `lexflow/dmn_xml.py`, `lexflow/forms/draft.py`, `lexflow/forms/registry.py`, `lexflow/lab/deadlines.py`,
    `lexflow/publish/lexipedia.py`, `lexflow/api/app.py`, `dashboard/app.js`, `dashboard/index.html`,
    `docker-compose.yml`, `requirements.txt`, `tools/node/package.json`, `schemas/dmn/DMN13.xsd`.
  - Data: `fixtures/forms/forms.json`.
  - Container: read-only `process_models`, `statute_files` and `statutes_{il,dc,ca,wa,…}.sqlite`.
  - Design notes: lab-plan, forms-plan, authority-wikibase, authority-standards, bpc-480-decision, entities-contacts,
    terms-wikibase.
