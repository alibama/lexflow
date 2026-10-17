# Lexipedia QuickStatements packet (for Claude in Chrome)

Generated 2026-10-15T17:54:50Z from lexflow commit `14712a9` by `python -m lexflow.publish.qs` (pass 1 files present).
The contract is `docs/design/wikibase-schema.md` section 5.  Nothing here deletes, merges or relabels anything.

## Files in this packet

| File | Commands the preview must show | Creations (CREATE / CREATE_PROPERTY) | Statements |
|---|---|---|---|
| `01-properties.qs` | 208 | 64 | 16 |
| `02-classes.qs` | 428 | 104 | 116 |
| `03-items-agency.qs` | 1075 | 268 | 268 |
| `03-items-cluster.qs` | 920 | 230 | 230 |
| `03-items-code.qs` | 252 | 63 | 63 |
| `03-items-decision.qs` | 224 | 56 | 56 |
| `03-items-form.qs` | 1236 | 309 | 309 |
| `03-items-gov.qs` | 8 | 2 | 2 |
| `03-items-office-type.qs` | 152 | 38 | 38 |
| `03-items-outcome.qs` | 336 | 84 | 84 |
| `03-items-position-type.qs` | 44 | 11 | 11 |
| `03-items-position.qs` | 44 | 11 | 11 |
| `03-items-private-party.qs` | 4 | 1 | 1 |
| `03-items-process.qs` | 430 | 86 | 86 |
| `03-items-role.qs` | 1068 | 267 | 267 |
| `03-items-rung.qs` | 1952 | 488 | 488 |
| `03-items-statute.qs` | 1732 | 433 | 433 |
| `03-items-step-a.qs` | 1996 | 499 | 499 |
| `03-items-step-b.qs` | 1996 | 499 | 499 |
| `03-items-step-c.qs` | 244 | 61 | 61 |
| `03-items-unit-a.qs` | 1996 | 499 | 499 |
| `03-items-unit-b.qs` | 304 | 76 | 76 |

Every `.qs` file starts with `/* ... */` comment lines that repeat these numbers.  QuickStatements ignores those
lines.  A file with a `-a`, `-b` suffix is one batch split in parts: run the parts in letter order.

## Steps

1. The operator signs in at https://lexipedia.wikibase.cloud with their own account before you start.  You never
   type, see or ask for the password.  If a page asks you to sign in, stop and tell the operator.
2. Open https://lexipedia.wikibase.cloud/tools/quickstatements/#/batch in a tab.  If it shows "Not logged in",
   click "Log in" (OAuth with the operator's wiki account), then come back to the same URL.
3. Pass 1 files, in name order: `01-properties.qs`, `02-classes.qs`, `03-items-agency.qs`, `03-items-cluster.qs`, `03-items-code.qs`, `03-items-decision.qs`, `03-items-form.qs`, `03-items-gov.qs`, `03-items-office-type.qs`, `03-items-outcome.qs`, `03-items-position-type.qs`, `03-items-position.qs`, `03-items-private-party.qs`, `03-items-process.qs`, `03-items-role.qs`, `03-items-rung.qs`, `03-items-statute.qs`, `03-items-step-a.qs`, `03-items-step-b.qs`, `03-items-step-c.qs`, `03-items-unit-a.qs`, `03-items-unit-b.qs`.
   For each file:
   a. Read the file's header comment and note the number after "preview must show".
   b. Click "New batch" if the page does not already show the empty command box.
   c. Paste the whole file (header lines included) into the command box and press "Import V1 commands" (never
      "Import CSV commands").
   d. The preview must show exactly that number of commands and, for `01-properties.qs`, 64
      `CREATE_PROPERTY` rows (208 commands in all) and nothing that is not a property creation,
      label, description, alias or `P7` claim.  For the `02-` and `03-` files every row is `CREATE`, a label,
      description, alias or `P25` (the key), a `P8` Wikidata link, or a `P5`/`P6` to an item that already
      exists.  If the count differs
      or a row shows an error such as "Unknown V1 value format", do not run it: stop and paste the file name and
      the error rows back to Claude Code.
   e. Press "Run in background" (not "Run"), one batch at a time; wait until the batch page shows every command
      done before pasting the next file.  Note the P-ids that `01-properties.qs` created, but do not retype them:
      Claude Code reads them from the wiki.
4. Tell Claude Code "pass 1 is done".  It runs `python -m lexflow.publish.qs --resolve` (reads only) and then
   `write --pass 2`, which writes the `04-*.qs` and `05-*.qs` files into this folder.
5. Pass 2 files, in name order: (written after pass 1).  Paste each the same
   way (steps 3a-3e).  Every row is a statement, qualifier or reference on an existing Q or P id; no `CREATE` rows.
   The header of each file lists the claims that were skipped because an id was still missing; that is expected
   and is not an error.
6. Tell Claude Code "pass 2 is done".  It runs `python -m lexflow.publish.qs --check`, the coverage query against
   the live endpoint, and reports what is missing.
7. Never: delete an item, merge items, edit `Project:` pages, change a label by hand, run a batch whose preview
   count differs from the file's header, or paste a file twice.  If QuickStatements shows errors on any row, stop
   there and paste the error rows (with the file name) back to Claude Code; do not retry or edit the file.

## Before pass 1: the wiki pages the hosting policy needs

Wikibase Cloud's hosting policy needs `Project:Copyrights` to say the structured data is CC0 and `Project:People`
to state the rule that the wiki holds organisations and office channels only (no office holders, staff names,
personal mailboxes or direct lines).  These are wiki pages, not QuickStatements; the operator writes them by hand
and tells you when they are in place.  If either page is missing, say so before running the first batch.
