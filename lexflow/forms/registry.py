"""Official forms, portals and sample letters tied to process steps, from ``fixtures/forms/forms.json``.

Each form entry in the fixture names the curated steps it serves as ``(file, step, match)``. The registry turns
those references into a lookup by ``(state, question, step id)``, so that a model page, an answer, the wiki or the
Setup checklist can list the forms for each step. Where a step has no official form, the fixture's ``no_form``
notes say what the statute requires, and :mod:`lexflow.forms.draft` can build a draft from the statute's own words.

The state and question come from the step's curated file, not from the form: ``curated/<state>/<question>.json``
or ``curated_ask/<question>/<state>.json``. A form can be linked to a step in another process. For example, the
California Department of Justice's record-review request (BCIA 8016RR, a request for a copy of one's own criminal
record) is filed under record sealing, and it is also linked, as a related form, to the evidence step of the
licence-conviction model. Each link keeps its match (exact, partial or related), and pages show it.

Everything here is read-only. Nothing fetches, fills in or submits a form. Link checks are a separate step (see
``docs/design/forms-plan.md``), and this module only reads the results the fixture records.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "forms" / "forms.json"
SCHEMA = "lexflow-forms/1"

MATCH_ORDER = {"exact": 0, "partial": 1, "related": 2}
# kinds that are a form in their own right; sample letters, guides and web pages help but are not forms
FORM_KINDS = {"pdf_form", "word_form", "online_portal"}
PAPER_FORM_KINDS = {"pdf_form", "word_form"}
# verification results that count as checked (fixture setup.status_rule): blocked hosts and robots.txt refusals are
# recorded, not retried, so they do not keep the Setup box unticked
CHECKED = {"ok", "blocked", "not_fetched"}
RECHECK_DAYS = 90

_STEP_FILE = (re.compile(r"^curated/(?P<state>[a-z]{2})/(?P<question>[a-z_]+)\.json$"),
              re.compile(r"^curated_ask/(?P<question>[a-z_]+)/(?P<state>[a-z]{2})\.json$"))
# node types a compiled step can become (lexflow/extract/compile.py): tasks inside the public body's pool, or a
# message catch event where an outside party (requester, applicant, court) acts
_STEP_NODE_TYPES = {"task", "userTask", "serviceTask", "sendTask", "receiveTask", "businessRuleTask", "manualTask",
                    "scriptTask", "callActivity", "subProcess", "intermediateCatchEvent"}


def step_file_key(file: str) -> tuple[str, str]:
    """(state, question) for a curated step file path such as 'curated_ask/record_sealing/va.json'."""
    norm = str(file).replace("\\", "/")
    for rx in _STEP_FILE:
        m = rx.match(norm)
        if m:
            return m["state"], m["question"]
    raise ValueError(f"not a curated step file: {file}")


def step_file(state: str, question: str) -> str:
    """The curated file that holds the step model for (state, question), relative to the repository root."""
    if question in ("records", "business"):
        return f"curated/{state}/{question}.json"
    return f"curated_ask/{question}/{state}.json"


@dataclass(frozen=True)
class StepRef:
    """One form-to-step link from the fixture."""
    form_id: str
    state: str
    question: str
    step: str
    match: str
    step_action: str
    file: str


def summary(form: dict, match: str | None = None) -> dict:
    """The fields a page needs to show one official form, with its last link check (``final_url`` is where the
    publisher's URL redirected to on that check; pages still link the publisher's own ``url``)."""
    v = form.get("verification") or {}
    out = {
        "id": form["id"], "title": form["title"], "form_number": form.get("form_number"),
        "revision": form.get("revision"), "revision_note": form.get("revision_note"),
        "publisher": form["publisher"], "kind": form["kind"],
        "url": form.get("url"), "index_url": form.get("index_url"), "fillable": form.get("fillable"),
        "fee": form.get("fee"), "fee_source": form.get("fee_source"), "statutes": list(form.get("statutes") or []),
        "status": v.get("status"), "checked": v.get("checked"), "final_url": v.get("final_url"),
        "notes": form.get("notes"), "official": True,
    }
    if match is not None:
        out["match"] = match
    return out


class Registry:
    """Lookups over the forms fixture: forms by step, by state and by process model."""

    def __init__(self, data: dict, path: Path | None = None):
        if data.get("schema") != SCHEMA:
            raise ValueError(f"expected schema {SCHEMA}, got {data.get('schema')!r}")
        self.data = data
        self.path = path
        self.forms: dict[str, dict] = {}
        self.links: dict[tuple[str, str, str], list[StepRef]] = {}
        for f in data.get("forms", []):
            if f["id"] in self.forms:
                raise ValueError(f"duplicate form id {f['id']}")
            self.forms[f["id"]] = f
            for s in f.get("steps") or []:
                state, question = step_file_key(s["file"])
                ref = StepRef(f["id"], state, question, s["step"], s["match"], s.get("step_action", ""), s["file"])
                self.links.setdefault((state, question, s["step"]), []).append(ref)
        self.notes: dict[tuple[str, str, str], list[dict]] = {}
        for n in data.get("no_form", []):
            for s in n.get("steps") or []:
                state, question = step_file_key(s["file"])
                self.notes.setdefault((state, question, s["step"]), []).append(n)

    # ------------------------------------------------------------------ lookups
    def form(self, form_id: str) -> dict | None:
        return self.forms.get(form_id)

    def forms_for_step(self, state: str, question: str, step: str,
                       matches: Iterable[str] = ("exact", "partial", "related")) -> list[dict]:
        """Official forms for one step, exact matches first."""
        allowed = set(matches)
        refs = [r for r in self.links.get((state, question, step), []) if r.match in allowed]
        refs.sort(key=lambda r: (MATCH_ORDER.get(r.match, 9), r.form_id))
        return [summary(self.forms[r.form_id], r.match) for r in refs]

    def no_form_for_step(self, state: str, question: str, step: str) -> dict | None:
        """The fixture's note for a step with no official form: the statute, what it requires and a quote."""
        notes = self.notes.get((state, question, step))
        return notes[0] if notes else None

    def has_official_form(self, state: str, question: str, step: str) -> bool:
        """True when a paper form (PDF or Word) is how the step is done (match exact). Portals, sample letters and
        guides do not count: the step can still be done by letter, so a draft may be offered beside them."""
        return any(r.match == "exact" and self.forms[r.form_id]["kind"] in PAPER_FORM_KINDS
                   for r in self.links.get((state, question, step), []))

    def forms_for_state(self, state: str, question: str | None = None) -> list[dict]:
        """Every form of a state, optionally only those filed under one process or serving one of its steps."""
        out = []
        for f in self.forms.values():
            if f["state"] != state:
                continue
            if question and f["process"] != question and not any(
                    step_file_key(s["file"]) == (state, question) for s in f.get("steps") or []):
                continue
            out.append(summary(f))
        return out

    def unlinked_forms(self, state: str, question: str) -> list[dict]:
        """Forms of a state's process that serve no modelled step yet (for example the requester's FOIA petition
        DC-495 in Virginia). A model page lists them under the steps so they are not lost."""
        return [summary(f) for f in self.forms.values()
                if f["state"] == state and f["process"] == question and not f.get("steps")]

    def forms_for_model(self, model: Any) -> list[dict]:
        """For each step of a process model, its official forms, the fixture's no-form note and the draft, if any.

        ``model`` may be a curated file (path or parsed dict, ``curated/`` or ``curated_ask/``), a model row as
        :func:`lexflow.municipal.stats.model_detail` returns it (``state``, ``question``, ``facts``), or a compiled
        :class:`lexflow.ir.LegalProcessModel`, whose step nodes keep the step ids.
        """
        from . import draft as D  # local import: draft uses this module

        state, question, steps = model_steps(model)
        out = []
        for s in steps:
            spec = D.spec_for_step(state, question, s["id"])
            out.append({**s, "forms": self.forms_for_step(state, question, s["id"]),
                        "no_form": self.no_form_for_step(state, question, s["id"]),
                        "draft": spec.id if spec else None})
        return out

    # ------------------------------------------------------------------ checks
    def check_steps(self, root: Path = ROOT) -> list[str]:
        """Problems with the step references: a missing curated file, an unknown step id, or a step_action that no
        longer matches the curated step's action (the curated file changed after the forms were matched)."""
        problems = []
        cache: dict[str, dict | None] = {}
        refs = [(r.form_id, r.file, r.step, r.step_action) for rs in self.links.values() for r in rs]
        refs += [(f"no_form {n['state']}/{n['process']}", s["file"], s["step"], s.get("step_action", ""))
                 for n in self.data.get("no_form", []) for s in n.get("steps") or []]
        for owner, file, step, action in refs:
            if file not in cache:
                p = root / file
                cache[file] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
            doc = cache[file]
            if doc is None:
                problems.append(f"{owner}: {file} does not exist")
                continue
            steps = {s["id"]: s for s in _facts(doc).get("steps", [])}
            if step not in steps:
                problems.append(f"{owner}: no step {step} in {file}")
            elif action and steps[step].get("action") != action:
                problems.append(f"{owner}: {file} step {step} now reads {steps[step].get('action')!r}, "
                                f"not {action!r}")
        return problems

    # ------------------------------------------------------------------ setup
    def setup_entry(self) -> dict:
        """The proposed Setup checklist step, as the fixture records it (id, title, why, level, needs, params,
        cost), for lexflow/pipeline/steps.py to wrap in its Step dataclass."""
        s = self.data.get("setup") or {}
        return {k: s[k] for k in ("id", "title", "why", "level", "needs", "params", "cost") if k in s}

    def setup_status(self, states: Iterable[str] | None = None, today: date | None = None) -> dict:
        """The Setup box for the forms step, by the fixture's status_rule.

        ``done``: every form with a URL for the chosen states was checked within 90 days with status ok, blocked
        or not_fetched (robots.txt). ``partial``: some are older or failed. ``todo``: none was ever checked.
        Forms with no official URL have nothing to check and are counted in the detail line only.
        """
        today = today or date.today()
        chosen = {s.lower() for s in states} if states else None
        forms = [f for f in self.forms.values() if chosen is None or f["state"] in chosen]
        if not forms:
            return {"status": "optional", "done": 0, "total": 0, "detail": "No forms researched for these states"}
        checkable = [f for f in forms if f.get("url")]
        never = [f for f in checkable if not (f.get("verification") or {}).get("checked")]
        stale = [f for f in checkable if not _fresh(f, today)]
        status = "todo" if checkable and len(never) == len(checkable) else "partial" if stale else "done"
        steps = {(s["file"], s["step"]) for f in forms for s in f.get("steps") or []}
        template = (self.data.get("setup") or {}).get(
            "detail_template", "{forms} forms for {steps} steps in {states} states; {fillable} fillable PDFs; "
                               "{stale} links to recheck")
        detail = template.format(forms=len(forms), steps=len(steps), states=len({f["state"] for f in forms}),
                                 fillable=sum(1 for f in forms if f.get("fillable") is True), stale=len(stale))
        no_url = len(forms) - len(checkable)
        if no_url:
            detail += f"; {no_url} with no official URL"
        detail = re.sub(r"(?<![\d,])1 (\w+?)s\b", r"1 \1", detail)    # "1 links to recheck" -> "1 link ..."
        return {"status": status, "done": len(checkable) - len(stale), "total": len(checkable), "detail": detail,
                "stale": sorted(f["id"] for f in stale)}


def _fresh(form: dict, today: date) -> bool:
    v = form.get("verification") or {}
    if v.get("status") not in CHECKED or not v.get("checked"):
        return False
    try:
        return (today - date.fromisoformat(v["checked"])).days <= RECHECK_DAYS
    except ValueError:
        return False


def _facts(doc: dict) -> dict:
    """The step model inside a curated file: ``facts`` in curated/, ``steps`` in curated_ask/."""
    if isinstance(doc.get("facts"), dict):
        return doc["facts"]
    if isinstance(doc.get("steps"), dict):
        return doc["steps"]
    return doc


def model_steps(model: Any) -> tuple[str, str, list[dict]]:
    """(state, question, steps) for a curated file, a model row or a compiled model; each step has id, action,
    actor and kind (the BPMN node type for a compiled model)."""
    if isinstance(model, (str, Path)):
        p = Path(model)
        p = p if p.is_absolute() else ROOT / p
        doc = json.loads(p.read_text(encoding="utf-8"))
        rel = p.resolve().relative_to(ROOT.resolve()).as_posix()
        state, question = step_file_key(rel)
        return state, question, _plain_steps(_facts(doc))
    if hasattr(model, "iter_nodes"):                      # lexflow.ir.LegalProcessModel
        state = model.jurisdiction.split("/")[0]
        question = model.id.split("-", 1)[1] if "-" in model.id else model.id.split(".", 1)[-1]
        steps = []
        for _, _, n in model.iter_nodes():
            if n.type in _STEP_NODE_TYPES and (n.type != "intermediateCatchEvent" or n.event == "message"):
                steps.append({"id": n.id, "action": n.name, "actor": n.bearer or n.lane, "kind": n.type})
        return state, question, steps
    if isinstance(model, dict):
        state = model.get("state")
        # curated_ask files keep the question id in qid and the question's wording in question
        question = model.get("qid") or model.get("question")
        if not state or not question:
            raise ValueError("a model dict needs state and question (or qid)")
        return state, question, _plain_steps(_facts(model))
    raise TypeError(f"cannot read steps from {type(model).__name__}")


def _plain_steps(facts: dict) -> list[dict]:
    return [{"id": s["id"], "action": s.get("action", ""), "actor": s.get("actor"), "kind": s.get("kind")}
            for s in facts.get("steps", [])]


@lru_cache(maxsize=4)
def registry(path: str | None = None) -> Registry:
    """The registry loaded from fixtures/forms/forms.json (or another file in the same format)."""
    p = Path(path) if path else FIXTURE
    return Registry(json.loads(p.read_text(encoding="utf-8")), p)
