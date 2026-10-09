"""Local-LLM extraction through Ollama (structured outputs + validate-and-repair loop).

Defaults are deliberately boring: temperature 0, explicit num_ctx (Ollama's default
context is small), the JSON schema passed in ``format`` *and* summarized in the prompt
(Ollama's docs recommend both).  Every quote is checked against the source text;
failures are sent back to the model as concrete repair instructions.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

import requests
from pydantic import ValidationError

from .schema import LegalProcessFacts, ollama_schema

SYSTEM = """You extract legal PROCESS FACTS from one section of a United States municipal or county code.
Return JSON matching the schema. Rules:
1. Every "quote" must be copied character-for-character from the provided text. Never paraphrase inside "quote".
2. Only extract what the text says. If the process needs something the text does not say, add a sentence to "gaps".
3. Actors: who acts or receives (officials, bodies, applicants, courts). Use short snake_case ids.
4. Steps: one per legally meaningful act, in order. "after" lists step ids that must come first.
   kind=filing for submissions by private parties, notice for communications by officials,
   decision for determinations, hearing for hearings, record for record-keeping.
   modality: obligation (shall/must/will), permission (may), prohibition (shall not), right (is entitled), none.
5. Deadlines: amount + unit + anchor in the law's words. consequence=directory-only when the text says missing it
   does not end the matter; right-lapses when a filing must be made within the period.
6. Decisions: when eligibility/standing/limits depend on enumerated conditions, build a decision table.
   Cells are FEEL: "-" any, "\\"text\\"" strings, numbers, true/false, ranges like [0..5], lists like "\\"a\\",\\"b\\"".
7. Cross references: every other law cited (state code, administrative code, other sections).
"""

USER_TEMPLATE = """Jurisdiction: {jurisdiction}
Code: {code}
Section {section}: {title}

TEXT (subsections keep their labels):
<<<
{text}
>>>

Return the JSON now."""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'").replace("“", '"').replace("”", '"')).strip()


def check_facts(facts: LegalProcessFacts, text: str) -> list[str]:
    """Problems a reviewer (or the repair loop) must fix."""
    problems = []
    norm_text = _norm(text)
    quotes = [("trigger_source", facts.trigger_source)]
    quotes += [(f"actor {a.id}", a.source) for a in facts.actors]
    quotes += [(f"step {s.id}", s.source) for s in facts.steps]
    quotes += [(f"step {s.id} deadline", s.deadline.source) for s in facts.steps if s.deadline]
    quotes += [(f"decision {d.id} rule {i}", r.source) for d in facts.decisions for i, r in enumerate(d.rules)]
    quotes += [(f"outcome {o.id}", o.source) for o in facts.outcomes]
    quotes += [(f"cross-reference {c.citation}", c.source) for c in facts.cross_references]
    for where, q in quotes:
        if _norm(q.quote) not in norm_text:
            problems.append(f"{where}: quote is not an exact span of the text: {q.quote[:80]!r}")
    actor_ids = {a.id for a in facts.actors}
    step_ids = {s.id for s in facts.steps}
    decision_ids = {d.id for d in facts.decisions}
    for s in facts.steps:
        if s.actor not in actor_ids:
            problems.append(f"step {s.id}: unknown actor {s.actor}")
        if s.recipient and s.recipient not in actor_ids:
            problems.append(f"step {s.id}: unknown recipient {s.recipient}")
        for a in s.after:
            if a not in step_ids:
                problems.append(f"step {s.id}: 'after' references unknown step {a}")
        if s.decision and s.decision not in decision_ids:
            problems.append(f"step {s.id}: unknown decision {s.decision}")
    for o in facts.outcomes:
        for a in o.after:
            if a not in step_ids:
                problems.append(f"outcome {o.id}: 'after' references unknown step {a}")
    for d in facts.decisions:
        for i, r in enumerate(d.rules):
            if len(r.when) != len(d.inputs) or len(r.then) != len(d.outputs):
                problems.append(f"decision {d.id} rule {i}: cell count does not match the columns")
    if len({s.id for s in facts.steps}) != len(facts.steps):
        problems.append("duplicate step ids")
    return problems


@dataclass
class OllamaClient:
    base_url: str = "http://localhost:11434"
    model: str = "qwen3.6:27b"
    num_ctx: int = 32768
    timeout: int = 900
    keep_alive: str = "10m"
    think: bool | None = False           # turn off "thinking" models' reasoning trace; None = model default
    log: list = field(default_factory=list)

    def chat(self, messages: list[dict], schema: dict | None = None, temperature: float = 0.0) -> str:
        body = {"model": self.model, "messages": messages, "stream": False, "keep_alive": self.keep_alive,
                "options": {"temperature": temperature, "num_ctx": self.num_ctx}}
        if schema is not None:
            body["format"] = schema
        if self.think is not None:
            body["think"] = self.think
        r = requests.post(f"{self.base_url.rstrip('/')}/api/chat", json=body, timeout=self.timeout)
        if r.status_code == 400 and "think" in body and "think" in r.text.lower():
            body.pop("think")                # the model has no thinking mode
            self.think = None
            r = requests.post(f"{self.base_url.rstrip('/')}/api/chat", json=body, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        self.log.append({"request": {k: v for k, v in body.items() if k != "messages"},
                         "eval_count": data.get("eval_count"), "total_duration": data.get("total_duration")})
        return data["message"]["content"]

    def embed(self, texts: list[str], model: str = "bge-m3") -> list[list[float]]:
        r = requests.post(f"{self.base_url.rstrip('/')}/api/embed", json={"model": model, "input": texts},
                          timeout=self.timeout)
        r.raise_for_status()
        return r.json()["embeddings"]


@dataclass
class ExtractionResult:
    facts: LegalProcessFacts | None
    rounds: int
    problems: list[str]
    model: str
    prompt_hash: str
    raw: list[str] = field(default_factory=list)


def extract(client: OllamaClient, *, text: str, section: str, title: str, code: str, jurisdiction: str,
            max_repairs: int = 2) -> ExtractionResult:
    schema = ollama_schema()
    user = USER_TEMPLATE.format(jurisdiction=jurisdiction, code=code, section=section, title=title, text=text)
    messages = [{"role": "system", "content": SYSTEM + "\nJSON schema:\n" + json.dumps(schema)},
                {"role": "user", "content": user}]
    prompt_hash = hashlib.sha256((SYSTEM + json.dumps(schema)).encode()).hexdigest()[:12]
    raw_outputs, problems, facts = [], [], None
    for round_no in range(max_repairs + 1):
        content = client.chat(messages, schema=schema)
        raw_outputs.append(content)
        try:
            facts = LegalProcessFacts.model_validate_json(content)
            problems = check_facts(facts, text)
        except ValidationError as e:
            facts = None
            problems = [f"schema: {err['loc']}: {err['msg']}" for err in e.errors()][:20]
        if not problems:
            return ExtractionResult(facts, round_no + 1, [], client.model, prompt_hash, raw_outputs)
        messages += [{"role": "assistant", "content": content},
                     {"role": "user", "content": "Fix these problems and return the complete corrected JSON:\n- "
                      + "\n- ".join(problems)}]
    return ExtractionResult(facts, max_repairs + 1, problems, client.model, prompt_hash, raw_outputs)
