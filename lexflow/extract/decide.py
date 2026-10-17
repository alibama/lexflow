"""Typed decisions from a local decision model (Ollama's ``POST /v1/systemone``), with a chat fallback.

Ollama 0.35 added "Jev-style" decision models (``tev1:0.8b``, ``tev1`` 4B, ``nimble`` 9B): instead of a chat
turn, the caller sends a *state* (text) and named *questions*, and the model answers every question in one pass
with a typed answer and a probability over the options, in tens of milliseconds rather than seconds.  Three
question types exist:

* ``choice``: pick one of the ``criteria`` (a map of option name to description, or a list of option names);
  the answer has ``choice``, ``probabilities`` (option -> probability) and ``confidence``.
* ``noul``: a yes/no question; the answer has one probability (``noul``).
* ``score``: an ordered scale given as a list of level names; the answer has ``score`` (0..1), a ``legend``
  (index -> level name), ``probabilities`` keyed by index and ``confidence``.

This module normalises both the request (``state`` is one text, or a map of named fields written as ``name:
value`` lines; questions may say ``question`` or ``instructions``; a choice's criteria may be a list of names,
sent as the map the server requires) and the answers, so every answer is a dict with the keys ``type``, ``choice``,
``probabilities`` and ``confidence`` (plus ``probability`` for ``noul`` and ``score``/``legend`` for ``score``).

No decision model is pulled on this machine yet, so :func:`backend` looks at ``GET /api/tags`` and, when no
decision model is there, :class:`Decider` answers the same questions with :func:`fallback_chat`: a chat model
(``qwen3:1.7b`` by default), thinking off, temperature 0, a JSON schema in ``format`` that lists the same options,
one call for all the questions.  The fallback returns the same shape with ``confidence`` None and one-hot
probabilities, since a chat model gives no distribution.

Settings (``config.py``, from the environment): ``LEXFLOW_DECIDE_URL`` (the Ollama that serves decisions, default
``OLLAMA_URL``), ``LEXFLOW_DECIDE_MODEL`` (default ``tev1:0.8b``), ``LEXFLOW_DECIDE_FALLBACK`` (default
``LEXFLOW_MODEL_A``, ``qwen3:1.7b``) and ``LEXFLOW_DECIDE`` (0 or 1, default 0: whether the live uses of a decision
model run at all; :func:`enabled` and :func:`shared` are what callers ask).

Nothing here writes anywhere except :class:`Decider`'s small on-disk cache (a SQLite file under
``LEXFLOW_DATA/cache/decide``), keyed by the model, a hash of the state and a hash of the questions.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

from .. import config

SYSTEMONE = "/v1/systemone"
TAGS = "/api/tags"
# names a decision model's tag starts with (ollama.com/library): the first found is used
DECISION_MODEL_PREFIXES = ("tev1", "nimble")
# The settings (config.py): the Ollama that serves decisions (a second, newer server may run beside the main one,
# since /v1/systemone with tev1 needs Ollama >= 0.40.4), the decision model, and the chat fallback.
DECIDE_URL = config.DECIDE_URL
DECISION_MODEL = config.DECIDE_MODEL
FALLBACK_MODEL = config.DECIDE_FALLBACK
QUESTION_TYPES = ("choice", "noul", "score")


class DecisionError(RuntimeError):
    """The decision endpoint failed (after its retry) or returned something the parser cannot read."""


# --------------------------------------------------------------------------- request shape
def normalise_state(state: str | dict) -> str:
    """``state`` as the endpoint takes it (Ollama 0.40.4, checked against the server): one text.  A map of named
    fields is written as ``name: value`` lines."""
    if isinstance(state, dict):
        return "\n".join(f"{k}: {'' if v is None else v}" for k, v in state.items())
    return "" if state is None else str(state)


def normalise_questions(questions: dict) -> dict:
    """Each question with ``type``, ``instructions`` and (for choice and score) ``criteria`` in the endpoint's
    shape: choice criteria as a map of option name to description (a list of names becomes ``{name: name}``),
    score criteria as a list of ordered level names, noul with no criteria.  Raises ValueError on a bad one."""
    out = {}
    for name, q in (questions or {}).items():
        if not isinstance(q, dict):
            raise ValueError(f"question {name!r}: expected a dict, got {type(q).__name__}")
        qtype = q.get("type", "choice")
        if qtype not in QUESTION_TYPES:
            raise ValueError(f"question {name!r}: type must be one of {QUESTION_TYPES}, not {qtype!r}")
        text = q.get("instructions") or q.get("question") or ""
        nq: dict[str, Any] = {"type": qtype, "instructions": str(text)}
        crit = q.get("criteria")
        if qtype == "choice":
            if isinstance(crit, dict):
                nq["criteria"] = {str(k): ("" if v is None else str(v)) for k, v in crit.items()}
            elif isinstance(crit, (list, tuple)):
                nq["criteria"] = {str(k): str(k) for k in crit}
            else:
                raise ValueError(f"question {name!r}: a choice needs criteria (a map or a list of options)")
            if len(nq["criteria"]) < 2:
                raise ValueError(f"question {name!r}: a choice needs at least two options")
        elif qtype == "score":
            if isinstance(crit, dict):
                crit = list(crit.keys())
            if not isinstance(crit, (list, tuple)) or len(crit) < 2:
                raise ValueError(f"question {name!r}: a score needs an ordered list of at least two levels")
            nq["criteria"] = [str(c) for c in crit]
        out[str(name)] = nq
    if not out:
        raise ValueError("no questions")
    return out


def request_body(model: str, state: str | dict, questions: dict) -> dict:
    return {"model": model, "state": normalise_state(state), "questions": normalise_questions(questions)}


# --------------------------------------------------------------------------- response shape
def _float(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def parse_answer(qtype: str, raw: dict, question: dict | None = None) -> dict:
    """One answer in the common shape.  ``question`` is the normalised question (for a score's legend when the
    server gives none)."""
    raw = raw or {}
    qtype = raw.get("type", qtype) or qtype
    conf = _float(raw.get("confidence"))
    if qtype == "noul":
        p = _float(raw.get("noul", raw.get("probability")))
        return {"type": "noul", "choice": (p >= 0.5) if p is not None else None, "probability": p,
                "probabilities": ({"yes": p, "no": round(1 - p, 6)} if p is not None else {}), "confidence": conf}
    if qtype == "score":
        legend = raw.get("legend") or {}
        if not legend and question and isinstance(question.get("criteria"), list):
            legend = {str(i): c for i, c in enumerate(question["criteria"])}
        legend = {str(k): str(v) for k, v in dict(legend).items()}
        probs = {str(k): _float(v, 0.0) for k, v in (raw.get("probabilities") or {}).items()}
        score = _float(raw.get("score"))
        choice = raw.get("choice")
        if choice is None and probs:
            choice = legend.get(max(probs, key=probs.get), max(probs, key=probs.get))
        elif choice is None and score is not None and legend:
            idx = str(min(len(legend) - 1, round(score * (len(legend) - 1))))
            choice = legend.get(idx)
        return {"type": "score", "choice": choice, "score": score, "legend": legend, "probabilities": probs,
                "confidence": conf}
    probs = {str(k): _float(v, 0.0) for k, v in (raw.get("probabilities") or {}).items()}
    choice = raw.get("choice")
    if choice is None and probs:
        choice = max(probs, key=probs.get)
    return {"type": "choice", "choice": choice, "probabilities": probs, "confidence": conf}


def parse_response(data: dict, questions: dict) -> dict:
    """The endpoint's JSON as ``{"model", "answers": {name: answer}, "usage"}`` with every answer normalised."""
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise DecisionError(f"no answers in the response: {str(data)[:200]}")
    out = {}
    for name, q in questions.items():
        raw = answers.get(name)
        if raw is None:
            raise DecisionError(f"the response has no answer for question {name!r}")
        out[name] = parse_answer(q["type"], raw, q)
    return {"model": data.get("model"), "answers": out, "usage": data.get("usage") or {}}


# --------------------------------------------------------------------------- the endpoint
def decide(state: str | dict, questions: dict, model: str | None = None, *, base_url: str | None = None,
           timeout: float = 60, retries: int = 1, session=None) -> dict:
    """Ask a decision model the ``questions`` about ``state`` through ``POST /v1/systemone``.

    Returns ``{"model", "answers": {name: {"type", "choice", "probabilities", "confidence", ...}}, "usage",
    "ms"}``.  One retry on a connection error, a timeout or a 5xx; a 4xx is raised at once (the model is not
    pulled, or the body is wrong).
    """
    model = model or DECISION_MODEL
    if not model:
        raise DecisionError("no decision model named (pass model= or set LEXFLOW_DECIDE_MODEL)")
    body = request_body(model, state, questions)
    url = (base_url or DECIDE_URL).rstrip("/") + SYSTEMONE
    http = session or requests
    last: Exception | None = None
    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            r = http.post(url, json=body, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as e:
            last = e
            continue
        if r.status_code >= 500:
            last = DecisionError(f"{SYSTEMONE}: HTTP {r.status_code}: {r.text[:200]}")
            continue
        if r.status_code >= 400:
            raise DecisionError(f"{SYSTEMONE}: HTTP {r.status_code}: {r.text[:200]}")
        try:
            data = r.json()
        except ValueError as e:
            raise DecisionError(f"{SYSTEMONE}: not JSON: {r.text[:200]}") from e
        out = parse_response(data, body["questions"])
        out["ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["attempts"] = attempt + 1
        return out
    raise DecisionError(f"{SYSTEMONE} failed after {retries + 1} attempts: {last}")


def list_models(base_url: str | None = None, timeout: float = 10, session=None) -> list[str]:
    """The tags Ollama has pulled (``GET /api/tags``); [] when Ollama cannot be reached."""
    url = (base_url or DECIDE_URL).rstrip("/") + TAGS
    try:
        r = (session or requests).get(url, timeout=timeout)
        r.raise_for_status()
        return [m.get("name") or m.get("model") for m in r.json().get("models", []) if m.get("name") or m.get("model")]
    except (requests.RequestException, ValueError):
        return []


def is_decision_model(name: str) -> bool:
    return (name or "").split(":", 1)[0].lower() in DECISION_MODEL_PREFIXES


def find_tag(wanted: str, models: list[str]) -> str | None:
    """The pulled tag for a model name: the exact tag, else ``name:latest``, else (for a bare name without a tag)
    any tag of that name.  ``qwen3:1.7b`` never matches ``qwen3:4b``."""
    if not wanted:
        return None
    if wanted in models:
        return wanted
    if ":" not in wanted:
        for m in models:
            if m == wanted + ":latest":
                return m
        for m in models:
            if m.split(":", 1)[0] == wanted:
                return m
    return None


def backend(base_url: str | None = None, model: str | None = None, chat_model: str | None = None,
            session=None) -> dict:
    """What will answer decisions here: ``{"kind": "decision" | "chat" | "none", "model", "models"}``.

    ``decision`` when a decision model is pulled (``model`` or ``LEXFLOW_DECIDE_MODEL``, default ``tev1:0.8b``, if
    that one is there, else the first ``tev1``/``nimble`` tag), ``chat`` when only a chat model is (the fallback, ``chat_model`` or
    ``qwen3:1.7b``), ``none`` when neither is.  ``models`` lists every tag seen.
    """
    models = list_models(base_url, session=session)
    tag = find_tag(model or DECISION_MODEL, models)
    if tag and is_decision_model(tag):
        return {"kind": "decision", "model": tag, "models": models}
    found = [m for m in models if is_decision_model(m)]
    if found:
        # the smallest first: a tag with a size wins over ":latest"
        found.sort(key=lambda m: (":" not in m or m.endswith(":latest"), m))
        return {"kind": "decision", "model": found[0], "models": models}
    chat = find_tag(chat_model or FALLBACK_MODEL, models)
    if chat:
        return {"kind": "chat", "model": chat, "models": models}
    return {"kind": "none", "model": None, "models": models}


# --------------------------------------------------------------------------- the chat fallback
FALLBACK_SYSTEM = ("You answer short typed questions about a STATE text. Read the state, then answer every question "
                   "with exactly one of its options. Reply with JSON only, no explanation.")


def fallback_schema(questions: dict) -> dict:
    """The JSON schema for ``format``: one property per question, an enum of its options (a boolean for noul)."""
    props = {}
    for name, q in questions.items():
        if q["type"] == "noul":
            props[name] = {"type": "boolean"}
        elif q["type"] == "score":
            props[name] = {"type": "string", "enum": list(q["criteria"])}
        else:
            props[name] = {"type": "string", "enum": list(q["criteria"].keys())}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def fallback_prompt(state: str, questions: dict) -> str:
    lines = ["STATE:", state, ""]
    lines.append("QUESTIONS:")
    for name, q in questions.items():
        if q["type"] == "noul":
            lines.append(f'- "{name}" (yes/no, answer true or false): {q["instructions"]}')
        elif q["type"] == "score":
            lines.append(f'- "{name}" (pick one level, lowest to highest: {", ".join(q["criteria"])}): '
                         f'{q["instructions"]}')
        else:
            lines.append(f'- "{name}" (pick one option): {q["instructions"]}')
            for opt, desc in q["criteria"].items():
                lines.append(f"    {opt}: {desc}" if desc and desc != opt else f"    {opt}")
    lines.append("")
    lines.append("Answer with a JSON object whose keys are " + ", ".join(f'"{n}"' for n in questions) + ".")
    return "\n".join(lines)


def _match_option(value, options: list[str]):
    """``value`` as one of ``options`` (exact, then case-insensitive, then by the option's first word); None."""
    if value is None:
        return None
    v = str(value).strip()
    if v in options:
        return v
    low = {o.lower(): o for o in options}
    if v.lower() in low:
        return low[v.lower()]
    for o in options:
        if v.lower().startswith(o.lower()) or o.lower().startswith(v.lower()) and len(v) >= 3:
            return o
    return None


def fallback_chat(state: str | dict, questions: dict, model: str | None = None, *, client=None,
                  base_url: str | None = None, num_ctx: int = 4096, timeout: int = 300) -> dict:
    """The same questions answered by a chat model with a JSON schema: the same shape as :func:`decide`, with
    ``confidence`` None and a one-hot ``probabilities`` (a chat model gives no distribution).

    ``client`` is anything with ``chat(messages, schema=..., temperature=..., max_tokens=...) -> str``
    (:class:`lexflow.extract.ollama.OllamaClient` by default: thinking off, temperature 0).
    """
    model = model or FALLBACK_MODEL
    st, qs = normalise_state(state), normalise_questions(questions)
    if client is None:
        from .ollama import OllamaClient
        client = OllamaClient(base_url=base_url or DECIDE_URL, model=model, num_ctx=num_ctx,
                              timeout=timeout, think=False)
    schema = fallback_schema(qs)
    messages = [{"role": "system", "content": FALLBACK_SYSTEM + "\nJSON schema:\n" + json.dumps(schema)},
                {"role": "user", "content": fallback_prompt(st, qs)}]
    t0 = time.perf_counter()
    content = client.chat(messages, schema=schema, temperature=0.0, max_tokens=64 + 16 * len(qs))
    ms = round((time.perf_counter() - t0) * 1000, 1)
    try:
        data = json.loads(content)
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    answers = {}
    for name, q in qs.items():
        v = data.get(name)
        if q["type"] == "noul":
            if isinstance(v, str):
                v = v.strip().lower() in ("true", "yes", "y", "1")
            p = None if v is None else (1.0 if bool(v) else 0.0)
            answers[name] = parse_answer("noul", {"noul": p, "confidence": None})
        elif q["type"] == "score":
            opt = _match_option(v, q["criteria"])
            idx = q["criteria"].index(opt) if opt is not None else None
            n = len(q["criteria"])
            raw = {"score": (idx / (n - 1)) if idx is not None else None,
                   "legend": {str(i): c for i, c in enumerate(q["criteria"])},
                   "probabilities": {str(i): (1.0 if i == idx else 0.0) for i in range(n)} if idx is not None else {},
                   "choice": opt, "confidence": None}
            answers[name] = parse_answer("score", raw, q)
        else:
            opts = list(q["criteria"].keys())
            opt = _match_option(v, opts)
            raw = {"choice": opt, "probabilities": {o: (1.0 if o == opt else 0.0) for o in opts} if opt else {},
                   "confidence": None}
            answers[name] = parse_answer("choice", raw, q)
        answers[name]["confidence"] = None
    return {"model": getattr(client, "model", model), "answers": answers, "usage": {}, "ms": ms, "fallback": True,
            "raw": content}


# --------------------------------------------------------------------------- cache + Decider
def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def cache_key(model: str, state: str | dict, questions: dict) -> str:
    """``(model, state hash, questions hash)`` as one string."""
    st = normalise_state(state)
    qs = json.dumps(normalise_questions(questions), sort_keys=True, ensure_ascii=False)
    return f"{model}|{_h(st)[:32]}|{_h(qs)[:32]}"


class DecisionCache:
    """A small SQLite map of cache key -> result JSON (``None`` path: in memory only)."""

    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.mem: dict[str, dict] = {}
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path) as con:
                con.execute("CREATE TABLE IF NOT EXISTS decisions(key TEXT PRIMARY KEY, value TEXT NOT NULL, "
                            "created TEXT NOT NULL)")

    def get(self, key: str) -> dict | None:
        with self.lock:
            if key in self.mem:
                return self.mem[key]
            if not self.path:
                return None
            with sqlite3.connect(self.path) as con:
                row = con.execute("SELECT value FROM decisions WHERE key=?", (key,)).fetchone()
            if row:
                self.mem[key] = json.loads(row[0])
                return self.mem[key]
            return None

    def put(self, key: str, value: dict) -> None:
        with self.lock:
            self.mem[key] = value
            if self.path:
                with sqlite3.connect(self.path) as con:
                    con.execute("INSERT OR REPLACE INTO decisions VALUES (?,?,?)",
                                (key, json.dumps(value, ensure_ascii=False),
                                 time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))

    def __len__(self) -> int:
        if not self.path:
            return len(self.mem)
        with sqlite3.connect(self.path) as con:
            return con.execute("SELECT count(*) FROM decisions").fetchone()[0]


def default_cache_path() -> Path:
    return Path(config.DATA_DIR) / "cache" / "decide" / "decisions.sqlite"


class Decider:
    """Answers questions with the decision model when one is pulled, else with the chat fallback, through a cache.

    ``model``: the decision model to use (default: the first pulled one); ``chat_model``: the fallback.
    ``backend_info`` can be passed to skip the ``/api/tags`` call (tests, or a known setup).
    ``answer`` overrides the whole call (a stub: ``answer(state, questions) -> result``).
    """

    def __init__(self, model: str | None = None, chat_model: str | None = None, *, base_url: str | None = None,
                 cache_dir: Path | str | None = None, cache: bool = True, backend_info: dict | None = None,
                 answer: Callable | None = None, timeout: float = 60):
        self.base_url = base_url or DECIDE_URL
        self.requested_model = model
        self.chat_model = chat_model or FALLBACK_MODEL
        self.timeout = timeout
        self._backend = backend_info
        self._answer = answer
        path = None
        if cache:
            path = (Path(cache_dir) / "decisions.sqlite") if cache_dir else default_cache_path()
        self.cache = DecisionCache(path)
        self.stats = {"calls": 0, "hits": 0, "ms": 0.0, "errors": 0}
        self._lock = threading.Lock()

    @property
    def backend(self) -> dict:
        if self._backend is None:
            self._backend = backend(self.base_url, self.requested_model, self.chat_model)
        return self._backend

    @property
    def model(self) -> str:
        b = self.backend
        return b["model"] or (self.requested_model or self.chat_model)

    @property
    def is_fallback(self) -> bool:
        return self.backend["kind"] != "decision"

    def _call(self, state, questions) -> dict:
        if self._answer is not None:
            return self._answer(state, questions)
        b = self.backend
        if b["kind"] == "decision":
            return decide(state, questions, b["model"], base_url=self.base_url, timeout=self.timeout)
        if b["kind"] == "chat":
            return fallback_chat(state, questions, b["model"], base_url=self.base_url)
        raise DecisionError("no decision model and no chat model is pulled: nothing can answer")

    def decide(self, state: str | dict, questions: dict) -> dict:
        key = cache_key(self.model if self._answer is None else "stub", state, questions)
        hit = self.cache.get(key)
        if hit is not None:
            with self._lock:
                self.stats["hits"] += 1
            return {**hit, "cached": True}
        t0 = time.perf_counter()
        try:
            out = self._call(state, questions)
        except Exception:
            with self._lock:
                self.stats["errors"] += 1
            raise
        ms = (time.perf_counter() - t0) * 1000
        with self._lock:
            self.stats["calls"] += 1
            self.stats["ms"] += ms
        out = {k: v for k, v in out.items() if k != "cached"}
        out.setdefault("ms", round(ms, 1))
        self.cache.put(key, out)
        return out

    def __call__(self, state, questions) -> dict:
        return self.decide(state, questions)


# --------------------------------------------------------------------------- step kinds
# facts.steps[].kind (extract/schema.py FStep.kind), with the descriptions of publish.schema.VOCAB["step-kind"]
# (a test keeps them equal; this module stays free of the publish package)
STEP_KINDS: dict[str, str] = {
    "filing": "A request, application or document is filed.",
    "notice": "A notice is given.",
    "decision": "A body decides.",
    "act": "An act other than a filing, notice, decision or payment.",
    "payment": "A fee or tax is paid.",
    "record": "A record is made, kept or delivered.",
    "inspection": "Records or premises are inspected.",
    "hearing": "A hearing is held.",
    "review": "A decision is reviewed.",
}
# the least confidence at which the model's kind replaces the rule's: at 0.8 the benchmark measured 87% precision
# on the reviewed models' steps (docs/design/decision-models.md section 3.2)
KIND_CONFIDENCE = 0.8
STEP_KIND_QUESTIONS = {"kind": {"type": "choice", "instructions": "Which kind of legal process step is this? Judge by "
                                                                   "what the actor does.", "criteria": STEP_KINDS}}


def step_kind_state(action: str | None, quote: str | None) -> dict:
    """The state the benchmark used: the step's action and the law's words behind it."""
    return {"Step": " ".join((action or "").split()), "Law": " ".join((quote or "").split())[:1500]}


def step_kind(decider: "Decider", action: str | None, quote: str | None, rule_kind: str | None,
              threshold: float = KIND_CONFIDENCE) -> tuple[str | None, str, float | None]:
    """``(kind, kind_by, confidence)``: the decision model's choice with ``kind_by`` ``decision`` when its
    confidence is at least ``threshold``, else ``rule_kind`` with ``rule``.  The chat fallback gives no confidence,
    so its answer never replaces the rule; a failed call is the rule too (nothing raises)."""
    try:
        out = decider.decide(step_kind_state(action, quote), STEP_KIND_QUESTIONS)
    except (DecisionError, requests.RequestException, ValueError, OSError):
        return rule_kind, "rule", None
    a = (out.get("answers") or {}).get("kind") or {}
    choice, conf = a.get("choice"), _float(a.get("confidence"))
    if choice in STEP_KINDS and conf is not None and conf >= threshold:
        return choice, "decision", conf
    return rule_kind, "rule", conf


# --------------------------------------------------------------------------- the switch
def enabled() -> bool:
    """Whether the live uses of a decision model are switched on (``LEXFLOW_DECIDE=1``)."""
    return bool(config.DECIDE)


_shared: Decider | None = None
_shared_lock = threading.Lock()


def shared(**kw) -> Decider | None:
    """One process-wide :class:`Decider` for the live uses (step kinds), made on first call; None when the flag is
    off or neither a decision model nor the chat fallback is pulled (``backend()`` finds ``none``), so a caller
    falls back to its rule without a network call per step.  ``reset()`` forgets it (tests)."""
    global _shared
    if not enabled():
        return None
    with _shared_lock:
        if _shared is None:
            d = Decider(**kw)
            _shared = d if d.backend["kind"] != "none" else False      # False: looked, found nothing
        return _shared or None


def reset() -> None:
    global _shared
    with _shared_lock:
        _shared = None


def decide_many(rows: Iterable, questions: dict, concurrency: int = 1, decider: Decider | None = None,
                on_error: str = "raise") -> list[dict]:
    """Answer the same ``questions`` for every state in ``rows`` (strings or dicts), in order.

    ``concurrency`` > 1 runs calls in threads (Ollama serialises model runs, so more than 2 rarely helps on one
    machine).  ``on_error="keep"`` puts ``{"error": str}`` in place of a failed row instead of raising.
    """
    rows = list(rows)
    d = decider or Decider()

    def one(state):
        try:
            return d.decide(state, questions)
        except Exception as e:                     # noqa: BLE001 - the caller asked to keep going
            if on_error == "raise":
                raise
            return {"error": str(e), "answers": {}}

    if concurrency <= 1 or len(rows) <= 1:
        return [one(s) for s in rows]
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        return list(ex.map(one, rows))
