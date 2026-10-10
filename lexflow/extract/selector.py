"""Learn which clauses become process steps from Claude's reference models, and apply that to a new statute.

The small local models are poor judges of "is this sentence a step?", but the reference models in
``curated/`` hold hundreds of such judgements.  This module turns them into a selector that needs no
chat model at all, and gets better with every reference added:

* ``wide_drafts``  - candidate clauses.  The duty rules miss many sentences Claude used (passives with no
  agent, list items under "the custodian shall:", "he shall ...", "such extension shall not exceed"),
  so every clause with a duty word, or under a duty clause ending in ":", is a candidate here, with
  its actor inferred from the context when the grammatical subject is not a person or office.
* ``NaiveBayes``   - over hand-picked features (verb, actor kind, modality, deadline, passive, ...).
* ``Embedder``     - clause embeddings from a local embedding model (nomic-embed-text), cached on disk;
  ``knn`` votes with the labelled clauses of other states, ``library`` is the similarity to the
  nearest clause Claude quoted for a step in another state.
* ``stack``        - a logistic regression over those scores, trained with every state held out in
  turn, with the keep-threshold chosen to maximise step F1 on the training states.

Evaluation never sees the state being scored: a reference is held out together with every other
reference from the same state (a new state has none).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache

import requests

from .. import config
from .segment import Clause, segment

# individual office-holders are "official"; bodies are "public-body" (the references draw the line this way)
OFFICIAL = re.compile(r"\b(custodian|officer|official|clerk|mayor|secretary|director|commissioner|treasurer|"
                      r"administrator|head|governor|registrar|examiner|ombudsman|auditor|comptroller|supervisor)\b", re.I)
OTHER_GOV = re.compile(r"\b(county|city|town|locality|municipality|committee on open government)\b", re.I)
PRONOUN = re.compile(r"^(?:he|she|it|they|he or she|him|them|such person)$", re.I)
PASSIVE = re.compile(r"\bbe [a-z]+ed\b", re.I)
DEEMED = re.compile(r"^\s*(?:\w+ly\s+)?(?:be\s+(?:deemed|considered|treated as)|constitute)\b", re.I)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()


# ------------------------------------------------------------------ candidates
def agent_phrase(s: str) -> str | None:
    """The last person or office named in a stretch of text: 'If the Mayor decides the record' -> 'Mayor'."""
    from .strategies import AGENT_WORDS
    best = None
    for m in re.finditer(r"\b(?:the|a|an|any|each|such|that)\s+((?:[\w.'-]+\s+){0,3}?" + AGENT_WORDS.pattern[2:-2]
                         + r")\b", s, re.I):
        best = m.group(1)
    return re.sub(r"\s+", " ", best).strip() if best else None


LIST_INTRO = re.compile(r"(?::|—|the following)\s*$", re.I)


def _parent(clauses: list[Clause], i: int) -> Clause | None:
    """The duty clause a list item hangs from: '(c) A custodian who denies the application shall: (1) ...'."""
    c = clauses[i]
    cl = c.label or ""
    for j in range(i - 1, max(-1, i - 15), -1):
        p = clauses[j]
        pl = p.label or ""
        if p.section != c.section:
            return None
        if p.modal and LIST_INTRO.search(p.text) and (pl == cl or not pl or cl.startswith(pl + ".")):
            return p
        if p.modal and pl == cl:
            return None                              # a duty sentence of its own in between: not a list
        if pl and cl.split(".")[0] != pl.split(".")[0]:
            return None
    return None


# procedure stated without a duty word, which Claude still made steps of
PRESENT_ACT = re.compile(
    r"\b(?:the|a|an|each|any)\s+((?:[\w.'-]+\s+){0,4}?)(files|issues|endorses|reviews|returns|delivers|sends|records|"
    r"accepts|rejects|refuses|complies|receives|collects|charges|publishes|notifies|determines|grants|denies|makes|"
    r"provides|certifies|stamps|indexes|enters|mails|forwards|commences|submits|signs)\b", re.I)
HAS_TIME = re.compile(r"\b(?:has|have)\s+(?:\w+\s+){0,4}?(?:days?|hours?|weeks?|months?)\s+(?:to|in which to|within which to)\b",
                      re.I)
FEE_LINE = re.compile(r"\$\s?\d", re.I)
FEE_TOPIC = re.compile(r"\b(fee|filing|for filing|charge)\b", re.I)
EFFECT = re.compile(r"\b(?:is formed|are formed|becomes effective|become effective|takes effect|is effective)\b", re.I)


def _unmodal(c: Clause, question: str, dom: str) -> dict | None:
    """A candidate for a clause with no duty word: an office's present-tense act ('The department files a document
    by stamping it'), a time to act ('has three business days to cure'), a fee line ('For filing articles of
    organization, $100.') or the moment something takes effect ('An LLC is formed when ...')."""
    from .strategies import AGENT_WORDS, filer_for, kind_of, verb_phrase
    m = PRESENT_ACT.search(c.text)
    if m and AGENT_WORDS.search(m.group(1) or ""):
        actor = re.sub(r"\s+", " ", m.group(1)).strip() or dom
        action = verb_phrase(c.text[m.start(2):])
        return {"actor": actor, "action": action, "kind": kind_of(action), "modality": "obligation",
                "origin": "present", "actor_src": "subject"}
    if HAS_TIME.search(c.text):
        ap = agent_phrase(c.text[:HAS_TIME.search(c.text).start()]) or dom
        action = verb_phrase(c.text[HAS_TIME.search(c.text).end():])
        return {"actor": ap, "action": action, "kind": kind_of(action), "modality": "obligation",
                "origin": "has_time", "actor_src": "pronoun"}
    if FEE_LINE.search(c.text) and FEE_TOPIC.search(c.text) and len(c.text) < 400:
        return {"actor": filer_for(question), "action": "Pay the filing fee", "kind": "payment", "modality": "obligation",
                "origin": "fee", "actor_src": "filer"}
    if EFFECT.search(c.text):
        return {"actor": dom, "action": "Takes effect", "kind": "act", "modality": "none", "origin": "effect",
                "actor_src": "default"}
    return None


def dominant_actor(clauses: list[Clause], question: str) -> str:
    """The office that carries most duties in the text: the default actor for agentless duties."""
    from .strategies import AGENT_WORDS, PRIVATE
    subs = Counter()
    for c in clauses:
        s = (c.subject or "").lower()
        if s and AGENT_WORDS.search(s) and not PRIVATE.search(s) and len(s.split()) <= 4:
            subs[re.sub(r"^(?:official|the)\s+", "", s)] += 1
    if subs:
        return subs.most_common(1)[0][0]
    return {"records": "public body", "business": "filing office"}.get(question, "agency")


# candidate families.  "extras" (the request implied by "upon request", a second duty in one sentence) raises
# perfect selection to 0.78 but adds more noise than the selector can sort: 0.559 -> 0.534 with words only
CANDIDATES = {"unmodal": True, "extras": False}


def wide_drafts(clauses: list[Clause], question: str) -> list[dict]:
    from .strategies import (AGENT_WORDS, FILER_WORDS, filer_for, kind_of, modality_of, rule_drafts, verb_phrase)
    base = {d["clause"].id: d for d in rule_drafts(clauses, question)}
    dom = dominant_actor(clauses, question)
    out = []
    for i, c in enumerate(clauses):
        if c.id in base:
            out.append({**base[c.id], "origin": "rule", "actor_src": "subject"})
            continue
        src, modal, subject, list_item = c, c.modal, c.subject, False
        if not modal:
            p = _parent(clauses, i)
            if p is None:
                u = _unmodal(c, question, dom) if CANDIDATES["unmodal"] else None
                if u is not None:
                    out.append({"clause": c, "condition": None, "deadline": c.deadline, "deemed": False, **u})
                continue
            modal, subject, list_item = p.modal, p.subject, True
            after, before = c.text, ""
        else:
            m = re.search(re.escape(modal.replace(" not", "")), c.text, re.I) or re.search(r"\b(shall|may|must)\b", c.text, re.I)
            after, before = (c.text[m.end():], c.text[:m.start()]) if m else (c.text, "")
        subj = subject or ""
        if PRONOUN.match(subj) or not subj:
            ap = agent_phrase(before)
            subj, actor_src = (ap, "pronoun") if ap else ("", "none")
        else:
            actor_src = "subject"
        if actor_src != "none" and AGENT_WORDS.search(subj):
            actor = subj
        elif FILER_WORDS.search(subj):
            actor, actor_src = filer_for(question), "filer"
        else:
            actor, actor_src = dom, "default"
        if list_item:
            actor_src = "inherited"
        deemed = bool(DEEMED.match(after))
        action = verb_phrase(re.sub(r"^\s*(?:\w+ly\s+)?be\s+", "", after)) if not deemed else "Deemed " + \
            " ".join(after.split()[2:6])
        out.append({"clause": c, "actor": actor, "action": action, "kind": kind_of(action),
                    "modality": "none" if deemed else modality_of(modal), "condition": None,
                    "deadline": c.deadline, "origin": "list" if list_item else "wide", "actor_src": actor_src,
                    "deemed": deemed})
    out = [x for d in out for x in (_with_extras(d, question) if CANDIDATES["extras"] else [d])]
    # where the clause sits: the first section of a reference list is usually the core procedure
    order = list(dict.fromkeys(c.section for c in clauses))
    for d in out:
        d["sec_idx"] = order.index(d["clause"].section)
    return out


# one sentence, two steps: "a public body, upon request ..., shall respond" holds the request and the response
TRIGGER = re.compile(
    r"\b(?:upon|on|after|following)\s+(?:the\s+|a\s+|any\s+|such\s+)?(?:written\s+)?(?:receipt\s+of\s+(?:a\s+|the\s+|any\s+|"
    r"such\s+)?(?:written\s+)?)?(request|application|petition|appeal|complaint)\b"
    r"|\bif\s+(?:a|the|any)\s+(?:person|requester|requestor|applicant|registrant)\b[^,.;]{0,80}?\b"
    r"(?:requests|returns|files|submits|petitions|applies|asks|appeals)\b", re.I)


def _with_extras(d: dict, question: str) -> list[dict]:
    """The candidate, preceded by the act it responds to ('upon request', 'if the applicant returns ...') and
    followed by a second duty in the same sentence ('shall determine ... and shall promptly notify')."""
    from .segment import MODAL
    from .strategies import actor_kind as rule_kind, filer_for, kind_of, modality_of, verb_phrase
    c = d["clause"]
    out = []
    m = TRIGGER.search(c.text)
    if m and d.get("origin") != "fee" and rule_kind(d["actor"]) != "private-party":
        what = (m.group(1) or ("request" if question == "records" else "filing")).lower()
        out.append({**d, "actor": filer_for(question), "action": f"Submit the {what}", "kind": "filing",
                    "modality": "right", "origin": "trigger", "actor_src": "filer", "deadline": None, "deemed": False})
    out.append(d)
    mods = list(MODAL.finditer(c.text))
    if len(mods) >= 2 and d.get("origin") != "list":
        m2 = mods[1]
        action = verb_phrase(c.text[m2.end():])
        out.append({**d, "actor": agent_phrase(c.text[mods[0].end():m2.start()]) or d["actor"], "action": action,
                    "kind": kind_of(action), "modality": modality_of(m2.group(1).lower()), "origin": "second",
                    "actor_src": "pronoun", "deemed": False})
    return out


def labels_for(cands: list[dict], facts: dict) -> tuple[list[bool], list[str | None]]:
    """Which candidates are reference steps, and the actor kind of the step each stands for.  A clause can hold
    several steps and several candidates: they are paired by actor kind first, then the plain candidate before
    the extras, so an extra counts only when Claude made two steps of that sentence."""
    from .strategies import actor_kind as rule_kind
    kinds = {a["id"]: a["kind"] for a in facts["actors"]}
    steps = [(s["source"]["section"], _norm(s["source"]["quote"]), kinds.get(s["actor"])) for s in facts["steps"]]
    labels: list[bool] = [False] * len(cands)
    out_kinds: list[str | None] = [None] * len(cands)
    groups: dict[str, list[int]] = {}
    for i, d in enumerate(cands):
        groups.setdefault(d["clause"].id, []).append(i)
    for idxs in groups.values():
        c = cands[idxs[0]]["clause"]
        n = _norm(c.text)
        gs = [k for sec, q, k in steps if sec == (c.section or sec) and (q in n or n in q)]
        free = list(range(len(gs)))
        for i in idxs:
            j = next((j for j in free if gs[j] == rule_kind(cands[i]["actor"])), None)
            if j is not None:
                labels[i], out_kinds[i] = True, gs[j]
                free.remove(j)
        for i in sorted(idxs, key=lambda i: cands[i].get("origin") in ("trigger", "second")):
            if not free:
                break
            if not labels[i]:
                labels[i], out_kinds[i] = True, gs[free.pop(0)]
    return labels, out_kinds


# ------------------------------------------------------------------ references
@dataclass
class Reference:
    state: str
    question: str
    text: str
    clauses: list[Clause]
    quotes: list[tuple[str, str]]               # (section, normalised quote) of each step
    actors: dict[str, str]                       # actor name -> kind
    labels: list[bool] = field(default_factory=list)
    cands: list[dict] = field(default_factory=list)
    feats: list[list[str]] = field(default_factory=list)
    kinds: list[str | None] = field(default_factory=list)   # actor kind of the step a positive candidate matched


def _label(d: dict, quotes: list[tuple[str, str]]) -> bool:
    c = d["clause"]
    n = _norm(c.text)
    return any(sec == (c.section or sec) and (q in n or n in q) for sec, q in quotes)


def _step_kind(d: dict, facts: dict) -> str | None:
    """The actor kind of the reference step whose quote this candidate holds (None for a non-step)."""
    c = d["clause"]
    n = _norm(c.text)
    kinds = {a["id"]: a["kind"] for a in facts["actors"]}
    for s in facts["steps"]:
        q = _norm(s["source"]["quote"])
        if s["source"]["section"] == (c.section or s["source"]["section"]) and (q in n or n in q):
            return kinds.get(s["actor"])
    return None


@lru_cache(maxsize=4)
def _references(stamp: tuple) -> tuple[Reference, ...]:
    from ..municipal import statutes
    out = []
    for path in sorted(config.CURATED_DIR.glob("*/*.json")):
        st, q = path.parent.name, path.stem
        if st == "places":
            continue
        try:
            spec = json.loads(path.read_text(encoding="utf-8"))
            text = statutes.combined_text(statutes.reference_texts(st, spec["sections"]))
        except Exception:  # noqa: BLE001 - that state's statutes are not available here
            continue
        clauses = segment(text)
        quotes = [(s["source"]["section"], _norm(s["source"]["quote"])) for s in spec["facts"]["steps"]]
        ref = Reference(st, q, text, clauses, quotes, {a["name"]: a["kind"] for a in spec["facts"]["actors"]})
        ref.cands = wide_drafts(clauses, q)
        ref.labels, ref.kinds = labels_for(ref.cands, spec["facts"])
        ref.feats = [features(d) for d in ref.cands]
        out.append(ref)
    return tuple(out)


def references() -> tuple[Reference, ...]:
    """Every reference model with its candidate clauses labelled by Claude's choices (cached until a file changes)."""
    stamp = tuple(sorted((str(p), p.stat().st_mtime) for p in config.CURATED_DIR.glob("*/*.json")))
    return _references(stamp)


# ------------------------------------------------------------------ actor kinds
def _head(name: str) -> str:
    words = re.findall(r"[a-z]+", re.sub(r"\(.*?\)", "", name.lower()))
    words = [w for w in words if w not in ("the", "of", "a", "an", "or", "and", "any", "state", "public", "s")]
    return words[-1] if words else ""


def actor_kind(name: str, refs=(), exclude_state: str | None = None) -> str:
    """Kind of an actor: what the references call actors with the same head noun, else the rules."""
    from .strategies import COURT, PRIVATE
    votes = Counter(k for r in refs if r.state != exclude_state for n, k in r.actors.items() if _head(n) == _head(name))
    if votes and _head(name):
        return votes.most_common(1)[0][0]
    if COURT.search(name):
        return "court"
    if PRIVATE.search(name) and not re.search(r"\b(public|state|county|city|governmental)\b", name, re.I):
        return "private-party"
    if OTHER_GOV.search(name):
        return "other-government"
    return "official" if OFFICIAL.search(name) else "public-body"


# ------------------------------------------------------------------ features and naive Bayes
def features(d: dict) -> list[str]:
    from .strategies import actor_kind as rule_kind, verb_phrase
    c: Clause = d["clause"]
    m = re.search(r"\b(?:shall|may|must)\b(.*)", c.text, re.I | re.S)
    words = [w.lower() for w in re.findall(r"[A-Za-z]+", verb_phrase(m.group(1)) if m else c.text[:80])]
    words = [w for w in words if w not in ("either", "also", "then", "only", "not", "be", "immediately", "promptly")]
    verb = (words[0] if words else "?")[:6]
    who = rule_kind(d["actor"])
    depth = len((c.label or "").split("."))
    cond = bool(re.match(r"\s*(?:if|when|whenever|upon|in the event|unless|after)\b", c.text, re.I))
    return [f"modal={d['modality']}", f"who={who}", f"verb={verb}", f"kind={d['kind']}",
            f"deadline={bool(c.deadline)}", f"depth={min(depth, 3)}", f"who_modal={who}:{d['modality']}",
            f"passive={bool(PASSIVE.search(c.text))}", f"origin={d.get('origin', 'rule')}",
            f"actor_src={d.get('actor_src', 'subject')}", f"cond={cond}", f"deemed={bool(d.get('deemed'))}",
            f"len={min(len(c.text) // 150, 4)}", f"sec={min(d.get('sec_idx', 0), 2)}"]


class NaiveBayes:
    def __init__(self, rows: list[tuple[list[str], bool, float]]):
        self.pos = sum(w for _, y, w in rows if y) or 1e-9
        self.neg = sum(w for _, y, w in rows if not y) or 1e-9
        self.counts: Counter = Counter()
        for feats, y, w in rows:
            for f in feats:
                self.counts[(f, y)] += w
        self.vocab = len({f for feats, _, _ in rows for f in feats}) or 1

    def log_odds(self, feats: list[str]) -> float:
        lo = math.log(self.pos / self.neg)
        for f in feats:
            p = (self.counts[(f, True)] + 1) / (self.pos + self.vocab)
            n = (self.counts[(f, False)] + 1) / (self.neg + self.vocab)
            lo += math.log(p / n)
        return lo


# ------------------------------------------------------------------ embeddings
class Embedder:
    """Embeddings from the local Ollama embedding model, cached on disk by text hash (one-off cost per clause)."""
    floor = 0.6

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or config.EMBED_MODEL
        self.name = self.model
        self.base_url = (base_url or config.OLLAMA_URL).rstrip("/")
        self.path = config.DATA_DIR / "cache" / f"embed-{re.sub(r'[^a-z0-9]+', '-', self.model.lower())}.jsonl"
        self.cache: dict[str, list[float]] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    k, v = json.loads(line)
                    self.cache[k] = v
                except ValueError:
                    continue

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]

    def __call__(self, texts: list[str]):
        import numpy as np
        prefixed = [f"classification: {' '.join(t.split()[:220])}" for t in texts]
        missing = list(dict.fromkeys(t for t in prefixed if self.key(t) not in self.cache))
        if missing:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                for i in range(0, len(missing), 32):
                    batch = missing[i:i + 32]
                    r = requests.post(f"{self.base_url}/api/embed", json={"model": self.model, "input": batch},
                                      timeout=600)
                    r.raise_for_status()
                    for t, v in zip(batch, r.json()["embeddings"]):
                        k = self.key(t)
                        self.cache[k] = v
                        f.write(json.dumps([k, [round(x, 5) for x in v]]) + "\n")
        m = np.array([self.cache[self.key(t)] for t in prefixed], dtype="float32")
        return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)


class Tfidf:
    """Word and word-pair TF-IDF vectors over every reference clause: no download and no model server, and statute
    language is formulaic enough ("shall grant or deny the application") that shared wording carries much of
    the signal.  The vocabulary is fitted on reference texts only (no labels), so it is the same for every case."""
    name = "tfidf"
    floor = 0.25                                     # cosine at which two clauses count as the same act

    STOP = frozenset("the a an of to and or in on for by any such be is are that this with as at from under its it "
                     "which who if not no each other than".split())

    def __init__(self, refs=None, max_terms: int = 6000):
        import numpy as np
        refs = references() if refs is None else refs
        docs = [self.tokens(d["clause"].text) for r in refs for d in r.cands]
        df = Counter(t for doc in docs for t in set(doc))
        terms = [t for t, n in df.most_common(max_terms) if n >= 2]
        self.index = {t: i for i, t in enumerate(terms)}
        n = max(1, len(docs))
        self.idf = np.array([math.log((n + 1) / (df[t] + 1)) + 1 for t in terms], dtype="float32")

    def tokens(self, text: str) -> list[str]:
        words = [w for w in re.findall(r"[a-z]+", text.lower()) if w not in self.STOP and len(w) > 2]
        words = [w[:7] for w in words]               # a crude stem: "requests", "requested" -> "request"
        return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]

    def __call__(self, texts: list[str]):
        import numpy as np
        m = np.zeros((len(texts), len(self.index)), dtype="float32")
        for i, t in enumerate(texts):
            for tok, c in Counter(self.tokens(t)).items():
                j = self.index.get(tok)
                if j is not None:
                    m[i, j] = (1 + math.log(c)) * self.idf[j]
        return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)


class Combo:
    """TF-IDF and model embeddings side by side: the cosine of the joined vectors is the mean of the two
    cosines, so shared wording and shared meaning both count."""
    name = "tfidf+embed"

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.floor = (a.floor + b.floor) / 2
        self.name = f"{a.name}+{b.name}"

    def __call__(self, texts: list[str]):
        import numpy as np
        return np.hstack([self.a(texts), self.b(texts)]) / math.sqrt(2)


_TFIDF: dict[int, Tfidf] = {}


def tfidf() -> Tfidf:
    """One vectoriser per set of references (refitted when a reference file changes)."""
    refs = references()
    if id(refs) not in _TFIDF:
        _TFIDF.clear()
        _TFIDF[id(refs)] = Tfidf(refs)
    return _TFIDF[id(refs)]


def knn_sims(sims, train_y, k: int = 9, tau: float = 0.05):
    """Similarity-weighted vote of the k nearest labelled clauses (share of 'step'), from a similarity matrix."""
    import numpy as np
    if sims.shape[1] == 0:
        return np.full(sims.shape[0], 0.3)
    k = min(k, sims.shape[1])
    idx = np.argpartition(-sims, k - 1, axis=1)[:, :k]
    top = np.take_along_axis(sims, idx, axis=1)
    w = np.exp((top - top.max(axis=1, keepdims=True)) / tau)
    return (w * train_y[idx]).sum(axis=1) / w.sum(axis=1)


def knn(x, train_x, train_y, k: int = 9, tau: float = 0.05):
    import numpy as np
    return knn_sims(x @ train_x.T if len(train_x) else np.zeros((len(x), 0)), train_y, k, tau)


def align_sims(blocks, floor: float = 0.6):
    """Project each other state's process onto this text: match its step clauses one-to-one with the candidates
    (most similar pairs first, similarity >= floor) and count, per candidate, the share of states that chose it.
    ``blocks`` holds one (candidates x that state's steps) similarity matrix per state."""
    import numpy as np
    blocks = [b for b in blocks if b.shape[1]]
    if not blocks:
        return None
    votes = np.zeros(blocks[0].shape[0])
    for sims in blocks:
        flat = np.argsort(-sims, axis=None)
        used_i, used_j = set(), set()
        for f in flat:
            i, j = divmod(int(f), sims.shape[1])
            if sims[i, j] < floor:
                break
            if i in used_i or j in used_j:
                continue
            used_i.add(i)
            used_j.add(j)
            votes[i] += 1
            if len(used_j) == sims.shape[1]:
                break
    return votes / len(blocks)


def align_votes(x, step_sets, floor: float = 0.6):
    import numpy as np
    v = align_sims([x @ q.T for q in step_sets if len(q)], floor)
    return np.zeros(len(x)) if v is None else v


def library(x, quote_x):
    """Similarity to the nearest clause that Claude made a step anywhere else."""
    import numpy as np
    if len(quote_x) == 0:
        return np.zeros(len(x))
    return (x @ quote_x.T).max(axis=1)


# ------------------------------------------------------------------ stacking
def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _fit_lr(X, y, w, l2: float = 1.0, iters: int = 600, lr: float = 0.3):
    import numpy as np
    X = np.hstack([X, np.ones((len(X), 1))])
    beta = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ beta))
        g = X.T @ (w * (p - y)) / w.sum() + l2 * np.r_[beta[:-1], 0] / len(X)
        beta -= lr * g
    return beta


def _predict(beta, X):
    import numpy as np
    X = np.hstack([X, np.ones((len(X), 1))])
    return 1 / (1 + np.exp(-X @ beta))


class Selector:
    """Scores the candidate clauses of one case, trained on every reference outside its state."""

    def __init__(self, question: str, state: str | None, embedder=None, use_embeddings: bool = True,
                 only_states: set[str] | None = None):
        self.question, self.state = question, state
        self.refs = [r for r in references() if r.state != state and (only_states is None or r.state in only_states)]
        self.emb = embedder if use_embeddings else None
        self.span: dict[int, tuple[int, int]] = {}   # id(reference) -> its rows in the stacked candidate vectors
        if self.emb is not None:
            try:
                self._embed_refs()
            except requests.RequestException:
                self.emb = None                    # no embedding model reachable: naive Bayes only

    def _w(self, r: Reference) -> float:
        return 1.0 if r.question == self.question else 0.5

    def _embed_refs(self):
        import numpy as np
        refs = [r for r in self.refs if r.cands]
        if not refs:
            self.emb = None
            return
        self.allx = self.emb([d["clause"].text for r in refs for d in r.cands])
        self.ally = np.concatenate([np.array(r.labels, dtype="float32") for r in refs]) if refs else np.zeros(0)
        at = 0
        for r in refs:
            self.span[id(r)] = (at, at + len(r.cands))
            at += len(r.cands)
        self.S = self.allx @ self.allx.T             # every reference clause against every other, computed once

    def _scores(self, cands: list[dict], train: list[Reference], sims=None, feats=None):
        """Raw per-candidate scores from naive Bayes, and kNN / library / alignment when vectors are on.
        ``sims`` is the candidates' similarity to every reference clause (one row per candidate)."""
        import numpy as np
        nb = NaiveBayes([(f, y, self._w(r)) for r in train for f, y in zip(r.feats, r.labels)])
        cols = [[nb.log_odds(f) for f in (feats or [features(d) for d in cands])],
                [1.0 if d["clause"].deadline else 0.0 for d in cands]]
        if self.emb is not None and sims is not None:
            same = [r for r in train if r.question == self.question and id(r) in self.span] or \
                [r for r in train if id(r) in self.span]
            if same:
                idx = np.concatenate([np.arange(*self.span[id(r)]) for r in same])
                y = self.ally[idx]
                pos = idx[y > 0]
                lib = sims[:, pos].max(axis=1) if len(pos) else np.zeros(len(cands))
                blocks = []
                for r in same:
                    a, b = self.span[id(r)]
                    blocks.append(sims[:, np.arange(a, b)[np.array(r.labels, dtype=bool)]])
                al = align_sims(blocks, self.emb.floor)
                al = al if al is not None else np.zeros(len(cands))
                cols += [[_logit(v) for v in knn_sims(sims[:, idx], y)], list(lib * 10), list(al * 4)]
            else:
                cols += [[0.0] * len(cands)] * 3
        return np.array(cols, dtype="float64").T

    def fit(self):
        """Stacked logistic regression with leave-one-state-out scores, and the F1-best keep threshold."""
        import numpy as np
        Xs, ys, ws, groups = [], [], [], []
        for s in sorted({r.state for r in self.refs}):
            train = [r for r in self.refs if r.state != s]
            for r in (r for r in self.refs if r.state == s and r.cands):
                sims = self.S[slice(*self.span[id(r)])] if id(r) in self.span else None
                Xs.append(self._scores(r.cands, train, sims, r.feats))
                ys.append(np.array(r.labels, dtype="float64"))
                ws.append(np.full(len(r.cands), self._w(r)))
                groups.append(r)
        self.train_f1 = 0.0
        if not Xs:
            self.beta, self.threshold = None, 0.5
            return self
        X, y, w = np.vstack(Xs), np.concatenate(ys), np.concatenate(ws)
        self.mu, self.sd = X.mean(axis=0), X.std(axis=0) + 1e-6
        self.beta = _fit_lr((X - self.mu) / self.sd, y, w)
        # the keep threshold that maximises mean step F1 over the training cases of this question
        best, self.threshold = -1.0, 0.5
        preds = [(_predict(self.beta, (Xi - self.mu) / self.sd), yi, r) for Xi, yi, r in zip(Xs, ys, groups)
                 if r.question == self.question]
        for t in np.arange(0.03, 0.7, 0.01):
            f1s = []
            for p_, yi, r in preds:
                keep = p_ >= t
                tp = float((keep & (yi > 0)).sum())
                p = tp / max(1, keep.sum())
                rc = tp / max(1, len(r.quotes))
                f1s.append(2 * p * rc / (p + rc) if p + rc else 0.0)
            if f1s and np.mean(f1s) > best:
                best, self.threshold = float(np.mean(f1s)), float(t)
        self.train_f1 = best
        return self

    def predict(self, cands: list[dict]):
        import numpy as np
        if not cands:
            return np.zeros(0)
        sims = None
        if self.emb is not None:
            self._x = self.emb([d["clause"].text for d in cands])
            sims = self._x @ self.allx.T
        X = self._scores(cands, self.refs, sims)
        if getattr(self, "beta", None) is None:
            return 1 / (1 + np.exp(-X[:, 0]))
        return _predict(self.beta, (X - self.mu) / self.sd)

    def neighbour_kinds(self, cands: list[dict], k: int = 3) -> list[str | None]:
        """For each candidate, the actor kind Claude gave the most similar step clauses of other states
        (a similarity-weighted vote of the k nearest), or None when nothing is similar enough."""
        import numpy as np
        x = getattr(self, "_x", None)
        if self.emb is None or x is None or len(x) != len(cands):
            return [None] * len(cands)
        rows, kinds = [], []
        for r in self.refs:
            if id(r) not in self.span or r.question != self.question:
                continue
            a, _ = self.span[id(r)]
            for i, kind in enumerate(r.kinds):
                if kind:
                    rows.append(a + i)
                    kinds.append(kind)
        if not rows:
            return [None] * len(cands)
        sims = x @ self.allx[np.array(rows)].T
        out = []
        for srow in sims:
            top = np.argsort(-srow)[:k]
            if srow[top[0]] < self.emb.floor:
                out.append(None)
                continue
            votes = Counter()
            for j in top:
                votes[kinds[j]] += float(srow[j])
            out.append(votes.most_common(1)[0][0])
        return out

    def neighbours(self, d: dict, k: int = 3) -> list[tuple[str, bool]]:
        """The most similar labelled clauses of other states for the same question (for a few-shot prompt)."""
        import numpy as np
        if self.emb is None:
            return []
        pool = [(r, i) for r in self.refs if r.question == self.question and id(r) in self.span
                for i in range(len(r.cands))]
        if not pool:
            return []
        x = self.emb([d["clause"].text])
        rows = np.array([self.span[id(r)][0] + i for r, i in pool])
        order = np.argsort(-(x @ self.allx[rows].T)[0])
        out, pos, neg = [], 0, 0
        for j in order:                              # balanced: up to k steps and k non-steps
            r, i = pool[j]
            y = r.labels[i]
            if (y and pos < k) or (not y and neg < k):
                out.append((r.cands[i]["clause"].text, y))
                pos, neg = pos + y, neg + (not y)
            if pos >= k and neg >= k:
                break
        return out
