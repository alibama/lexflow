"""The reviewer list: the people the operator of this lexflow copy vouches for as reviewers.

    lexflow reviewer add "Ana Villamar" --role attorney --licensed-in va --added-by <operator>
    lexflow reviewer list [--all]
    lexflow reviewer token rv-1a2b3c4d          a new token for that reviewer (the old one stops working)
    lexflow reviewer remove rv-1a2b3c4d

lexflow cannot check that a reviewer is a person, and does not pretend to: the operator adds each one and so vouches
for them, with a role from ``signoff.ROLES`` and, for an attorney, the state where they are licensed.  A review (in a
curated file, a place file or ``PUT /api/ask/.../review``) names a reviewer only by the id this list gives them, and
a page prints the name, role and licence from here.  Of lexflow's code, only these commands write the list; the API
and the dashboard read it.

**The list is this copy's own.**  It is not synced: ``reviewers`` is not in ``db.SYNCED``, and push and pull refuse
any table that is not (``turso.check_tables``, from the CLI and from ``POST /api/jobs``), so a pull never adds,
renames or removes a reviewer here.  A removed reviewer keeps their row with ``removed_at``, and their name leaves
every page of this copy at the next render.

**A page names a reviewer only for a review this copy recorded.**  For an asked answer, that is a review recorded
through this copy's review API: the last entry ``review_log`` holds for the answer is that review, by the same
reviewer, of the same text_hash, on the same date (``recorded``, ``asked_reviewer``).  For a curated model, a place
file or a researched process, it is a sign-off in this copy's own file (lexflow/municipal/build.py,
lexflow/publish/lexipedia.py).  Any other review field, one pulled from another copy or written into the database
by hand, counts as not reviewed, and one log line per item says so (``signoff.unrecorded``).

**Each reviewer has a token.**  ``reviewer add`` prints a token once, and ``reviewer token`` prints a new one (the
old one stops working); only its scrypt hash is stored (``token_hash``), and it is compared in constant time.  The
review API records or removes a review only with a reviewer's token in the ``X-Lexflow-Reviewer-Token`` header, and
``review_log`` keeps which reviewer's token was used.  The token shows only that whoever sent it had it: the operator
gives each reviewer their own and answers for who holds it.  A sign-off in a curated file is not bound to a token:
whoever edits the file records it, and the operator answers for it.

The name is cleaned when it is added (``signoff.clean_name``).  A name that contains the name of an AI system or
product (``signoff.is_ai_name``) is not added unless the operator confirms that the reviewer is a person
(``--confirm-person``): that check is a warning, since people are named Wenxin Li or Marie Lechat, and it proves
nothing about anyone.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import unicodedata

from . import signoff
from .store import db

AI_WARNING = ("this name contains the name of an AI system or product ({name!r}). lexflow cannot tell whether a "
              "reviewer is a person; if this reviewer is a person you vouch for, add them again with "
              "--confirm-person")
# the header the review API reads a reviewer's token from
TOKEN_HEADER = "X-Lexflow-Reviewer-Token"
# a token is the reviewer's id, a dot and 32 random bytes (URL-safe base64), so the API finds whose it is
TOKEN = re.compile(r"(rv-[0-9a-f]{8})\.([A-Za-z0-9_-]{43})")
# scrypt's cost: 16 MiB and some 50 ms a check, once per review recorded
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1


class ReviewerError(ValueError):
    """Why a reviewer cannot be added or removed."""


def _plain(value) -> str:
    """Who added a reviewer, as stored: format characters removed, spaces collapsed."""
    s = unicodedata.normalize("NFKC", str(value or ""))
    return " ".join("".join(c for c in s if unicodedata.category(c) not in ("Cf", "Cc")).split())[:80]


def hash_token(token: str, salt: bytes | None = None) -> str:
    """What the list stores for a token: ``scrypt$N$r$p$<salt hex>$<hash hex>``."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(str(token).encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def token_fits(token: str, stored: str | None) -> bool:
    """Whether ``token`` is the one ``stored`` was made from (compared in constant time)."""
    try:
        alg, n, r, p, salt, want = str(stored or "").split("$")
        if alg != "scrypt":
            return False
        want_b = bytes.fromhex(want)
        got = hashlib.scrypt(str(token).encode("utf-8"), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                             dklen=len(want_b))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got, want_b)


def _new_token(reviewer_id: str) -> str:
    return f"{reviewer_id}.{secrets.token_urlsafe(32)}"


def add(con, name, role, *, added_by, licensed_in=None, confirm_person: bool = False) -> dict:
    """Put a reviewer on the list and return their row (with the new id) and, under ``token``, their token: shown
    this once, since only its hash is stored.  Raises ReviewerError when the name, role or licence cannot be stored,
    or when the name contains an AI system's and the operator has not confirmed that the reviewer is a person
    (``confirm_person``)."""
    clean, bad = signoff.clean_name(name)
    who = signoff.role_of(role)
    if not who:
        bad.append(f"the role must be one of {', '.join(signoff.ROLES)}")
    lic = None
    if licensed_in not in (None, ""):
        if who not in signoff.ATTORNEY_ROLES:
            bad.append(f"licensed_in is for an attorney: give the role {' or '.join(signoff.ATTORNEY_ROLES)}")
        lic = signoff.state_of(licensed_in)
        if not lic:
            bad.append("licensed_in is the state where the attorney is licensed ('va' or 'Virginia')")
    by = _plain(added_by)
    if not by:
        bad.append("say who is adding the reviewer (--added-by): the operator who vouches for them")
    if bad:
        raise ReviewerError("; ".join(bad))
    if signoff.is_ai_name(clean) and not confirm_person:
        raise ReviewerError(AI_WARNING.format(name=clean))
    same = [r for r in listing(con) if r["name"] == clean and r["role"] == who and (r["licensed_in"] or None) == lic]
    if same:
        raise ReviewerError(f"{clean} is already on the list as {same[0]['id']}")
    ts = db.now()
    rid = "rv-" + secrets.token_hex(4)
    token = _new_token(rid)
    row = {"id": rid, "name": clean, "role": who, "licensed_in": lic, "added_by": by, "added_at": ts,
           "removed_at": None, "updated_at": ts, "token_hash": hash_token(token)}
    db.upsert(con, "reviewers", [row])
    db.bump(con)
    con.commit()
    return {**db.one(con, "SELECT * FROM reviewers WHERE id=?", rid), "token": token}


def _current(con, reviewer_id: str) -> dict:
    row = db.one(con, "SELECT * FROM reviewers WHERE id=?", str(reviewer_id or "").strip())
    if not row:
        raise ReviewerError(f"no reviewer {reviewer_id!r} on the list (`lexflow reviewer list`)")
    if row["removed_at"]:
        raise ReviewerError(f"{row['id']} ({row['name']}) was removed on {row['removed_at'][:10]}")
    return row


def rotate_token(con, reviewer_id: str) -> str:
    """A new token for a reviewer on the list (the old one stops working); only its hash is stored."""
    row = _current(con, reviewer_id)
    token = _new_token(row["id"])
    con.execute("UPDATE reviewers SET token_hash=?, updated_at=? WHERE id=?", (hash_token(token), db.now(), row["id"]))
    con.commit()
    return token


def holder(con, token) -> dict | None:
    """The reviewer on the list (not removed, a row the list would take) whose token this is, or None."""
    m = TOKEN.fullmatch(str(token or "").strip())
    if not m:
        return None
    row = roster(con).get(m.group(1))
    return row if row and token_fits(m.group(0), row.get("token_hash")) else None


def remove(con, reviewer_id: str) -> dict:
    """Take a reviewer off the list (their row stays, with removed_at, and their token stops working).  Every page
    they signed says "Not yet reviewed by a person" at the next render."""
    row = _current(con, reviewer_id)
    ts = db.now()
    con.execute("UPDATE reviewers SET removed_at=?, updated_at=?, token_hash=NULL WHERE id=?", (ts, ts, row["id"]))
    db.bump(con)
    con.commit()
    return db.one(con, "SELECT * FROM reviewers WHERE id=?", row["id"])


def listing(con, *, removed: bool = False) -> list[dict]:
    """The reviewers on the list, in the order they were added (with the removed ones too when ``removed``)."""
    return db.rows(con, "SELECT * FROM reviewers" + ("" if removed else " WHERE removed_at IS NULL")
                   + " ORDER BY added_at, id")


def roster(con) -> dict[str, dict]:
    """id -> row for the reviewers a page may name now: on this copy's list, not removed, and still a row the list
    would take (``signoff.entry_problems``: a row written by hand or by other code is checked again)."""
    return {r["id"]: r for r in listing(con) if not signoff.entry_problems(r)}


def log_review(con, action: str, question_id: str, target: str, reviewer_id: str, text_hash: str | None,
               at: str | None = None) -> None:
    """Keep which reviewer's token recorded or removed a review (``review_log``, this copy's own), at ``at`` (now
    by default: the review API passes the time the review is dated from)."""
    con.execute("INSERT INTO review_log(at, action, question_id, target, reviewer, text_hash) VALUES (?,?,?,?,?,?)",
                (at or db.now(), action, question_id, target, reviewer_id, text_hash))


def recorded(con, question_id, target, rev) -> bool:
    """Whether this copy's review API recorded the review ``rev`` of an asked answer: the last entry ``review_log``
    holds for that answer is a review by the same reviewer, of the same text_hash, on the review's date.  A review
    pulled from another copy, or written into the database by hand, has no such entry (``review_log`` is this
    copy's own and is never synced), and nor has one removed since (its last entry is the removal)."""
    if con is None or not isinstance(rev, dict):
        return False
    last = db.one(con, "SELECT action, reviewer, text_hash, at FROM review_log WHERE question_id=? AND target=? "
                       "ORDER BY id DESC LIMIT 1", question_id, target)
    return bool(last) and last["action"] == "review" and last["reviewer"] == rev.get("reviewer") \
        and last["text_hash"] == rev.get("text_hash") and signoff.iso_date(last["at"]) is not None \
        and signoff.iso_date(last["at"]) == signoff.iso_date(rev.get("date"))


def asked_reviewer(con, row: dict, listed: dict | None = None) -> dict | None:
    """The reviewer of this text of an asked answer, as a page and the dashboard show them, or None: its
    ``reviewed_by`` must be a sign-off of the stored text by someone on this copy's list (``listed``, as ``roster``
    reads it), dated on or after the answer was made (``signoff.bound``), and recorded through this copy's review
    API with that reviewer's token (``recorded``).  Any other review in the column (pulled from another copy, or
    written into the database by hand) counts as not reviewed, with one log line per answer."""
    rev = row.get("reviewed_by")
    rev = db.loads(rev, None) if isinstance(rev, str) else rev
    if not rev or con is None:
        return None
    metrics = row.get("metrics")
    metrics = (db.loads(metrics, {}) if isinstance(metrics, str) else metrics) or {}
    who = signoff.bound(rev, signoff.row_text(row, signoff.ASKED_TEXT), roster(con) if listed is None else listed,
                        not_before=metrics.get("answered_at"))
    if who and not recorded(con, row.get("question_id"), row.get("target"), rev):
        signoff.unrecorded(f"the asked answer {row.get('question_id')} for {row.get('target')}",
                           "this copy's review_log does not hold that review (it was pulled from another copy, or "
                           "written into the database by hand)")
        return None
    return who


def shown(con) -> list[dict]:
    """The list as the dashboard offers it: id, name, role, licence, and the line a page would print."""
    out = []
    for r in roster(con).values():
        role = r["role"] + (f" licensed in {r['licensed_in']}" if r.get("licensed_in") else "")
        out.append({"id": r["id"], "name": r["name"], "role": r["role"], "licensed_in": r.get("licensed_in"),
                    "label": r["name"] if r["role"] == signoff.NO_ROLE_SHOWN else f"{r['name']}, {role}"})
    return out
