"""Which model's answer a reader shows.

``asked_answers`` keeps one row per (question, target, model), so two models can answer the same cell and be
compared (``lexflow run coverage --fill --cells filled``).  Every reader (the ask API, the dashboard's asked
views, the drafts of ``publish.graph``, the wiki's asked pages, the coverage probe) shows one answer per question
and target: the model ``LEXFLOW_ASK_PREFER`` names when it has a row, else the best-scoring row (status, then a
summary that was written, then the share of quotes that matched the statute text, then the newest).  With one
model this is exactly the row there was before.
"""
from __future__ import annotations

from .. import config
from ..store import db

STATUS_RANK = {"answered": 3, "partial": 2, "not_found": 1, "no-statutes": 0}
KEY = ("question_id", "target")


def preferred_model() -> str | None:
    return (config.ASK_PREFER or "").strip() or None


def rank(row: dict) -> tuple:
    """Higher sorts first.  ``model`` beats everything, so a reader can be pinned to one model's answers."""
    loads = lambda v: (db.loads(v, {}) if isinstance(v, str) else v) or {}     # noqa: E731
    metrics, answer = loads(row.get("metrics")), loads(row.get("answer"))
    summary = answer.get("summary") if isinstance(answer, dict) else None
    claims = len(summary.get("claims") or []) if isinstance(summary, dict) else 0
    checked = int(metrics.get("quotes_checked") or 0)
    matched = (checked - int(metrics.get("quote_misses") or 0)) / checked if checked else 0.0
    return (row.get("model") == preferred_model(), STATUS_RANK.get(row.get("status"), -1), claims > 0,
            round(matched, 3), checked, row.get("updated_at") or "")


def pick(rows: list[dict]) -> dict | None:
    return max(rows, key=rank) if rows else None


def preferred(rows: list[dict], key: tuple[str, ...] = KEY) -> list[dict]:
    """One row per key (question and target), the preferred one, in the order the keys first appear."""
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r.get(k) for k in key), []).append(r)
    return [pick(g) for g in groups.values()]


def answer(con, question_id: str, target: str, model: str | None = None) -> dict | None:
    """The stored answer a reader shows for the question and target: ``model``'s when named, else the preferred."""
    if model:
        return db.one(con, "SELECT * FROM asked_answers WHERE question_id=? AND target=? AND model=?",
                      question_id, target, model)
    return pick(db.rows(con, "SELECT * FROM asked_answers WHERE question_id=? AND target=?", question_id, target))


def models_of(con, question_id: str, target: str) -> list[str]:
    return [r["model"] for r in db.rows(con, "SELECT model FROM asked_answers WHERE question_id=? AND target=? "
                                             "ORDER BY model", question_id, target)]
