"""What the local LLM extracts: legal *facts* with verbatim quotes, not BPMN.

Small open models are far more reliable filling a flat, quote-anchored schema
than drawing a graph.  Modeling conventions (deadline -> timer, filing ->
message, decision -> DMN) are then applied deterministically by
:mod:`lexflow.extract.compile`, identically for every ordinance.
"""
from __future__ import annotations

import copy
from typing import Literal, Optional

from pydantic import BaseModel, Field

ID = r"^[a-z][a-z0-9_]{0,40}$"


class Quote(BaseModel):
    section: str = Field(description="Section number exactly as in the text header, e.g. 17-211")
    subsection: Optional[str] = Field(None, description="Subsection label path, e.g. D.2 or a")
    quote: str = Field(description="Exact span copied from the text (no paraphrase)")


class FActor(BaseModel):
    id: str = Field(pattern=ID)
    name: str
    kind: Literal["public-body", "official", "private-party", "court", "other-government"]
    source: Quote


class FDeadline(BaseModel):
    amount: int = Field(ge=0)
    unit: Literal["hours", "days", "business_days", "weeks", "months", "years"]
    anchor: str = Field(description="What starts the clock, in the law's words")
    consequence: Literal["right-lapses", "action-invalid", "directory-only", "deemed-denial", "unstated"] = Field(
        description="What happens if missed: 'directory-only' when the text says missing it has no effect; "
                    "'deemed-denial' when silence counts as a denial")
    on_miss: Optional[str] = Field(None, description="Id of the outcome or step reached when the deadline passes "
                                                      "(default: an end event of its own)")
    source: Quote


class FStep(BaseModel):
    id: str = Field(pattern=ID)
    actor: str = Field(description="FActor.id of who performs the step")
    action: str = Field(description="Imperative, at most 8 words, e.g. 'File written request with clerk'")
    kind: Literal["act", "notice", "filing", "hearing", "decision", "payment", "inspection", "record", "review"]
    modality: Literal["obligation", "permission", "prohibition", "right", "none"]
    after: list[str] = Field(default_factory=list, description="Ids of steps that must happen first; empty = right after the trigger")
    join: Literal["all", "any"] = Field("all", description="With several 'after' ids: 'all' waits for every one "
                                                         "(parallel join); 'any' continues after whichever happened "
                                                         "(exclusive merge, for branches that rejoin)")
    condition: Optional[str] = Field(None, description="Boolean variable name that must be true, snake_case")
    recipient: Optional[str] = Field(None, description="FActor.id receiving a notice or filing")
    deadline: Optional[FDeadline] = None
    decision: Optional[str] = Field(None, description="FDecision.id evaluated by this step")
    source: Quote


class FColumn(BaseModel):
    name: str = Field(pattern=ID)
    label: str
    type: Literal["string", "number", "boolean"]


class FRule(BaseModel):
    when: list[str] = Field(description="One FEEL unary test per input column, '-' for any")
    then: list[str] = Field(description="One FEEL literal per output column")
    source: Quote


class FDecision(BaseModel):
    id: str = Field(pattern=ID)
    question: str
    hit_policy: Literal["UNIQUE", "FIRST"]
    inputs: list[FColumn]
    outputs: list[FColumn]
    rules: list[FRule]


class FOutcome(BaseModel):
    id: str = Field(pattern=ID)
    description: str
    after: list[str]
    join: Literal["all", "any"] = Field("any", description="With several 'after' ids, an outcome is usually reached "
                                                         "by whichever path happened ('any')")
    when: Optional[str] = Field(None, description="Boolean variable name, if the outcome is conditional")
    source: Quote


class FCrossRef(BaseModel):
    citation: str
    role: str = Field(description="Why it is cited, e.g. 'governs judicial review'")
    source: Quote


class LegalProcessFacts(BaseModel):
    process_name: str
    trigger: str
    trigger_source: Quote
    actors: list[FActor]
    steps: list[FStep]
    decisions: list[FDecision] = Field(default_factory=list)
    outcomes: list[FOutcome] = Field(default_factory=list)
    cross_references: list[FCrossRef] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list, description="Things the text presupposes but does not say")


def ollama_schema() -> dict:
    """JSON schema for Ollama's ``format``: $refs inlined, no Optional anyOf, no unsupported keywords.

    llama.cpp's schema-to-grammar silently ignores what it does not support, so we
    hand it the plainest possible schema and enforce the rest with pydantic.
    """
    raw = LegalProcessFacts.model_json_schema()
    defs = raw.pop("$defs", {})

    def inline(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return inline(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            if "anyOf" in node:                         # Optional[X] -> X (nullable handled by 'required')
                options = [o for o in node["anyOf"] if o.get("type") != "null"]
                base = inline(options[0]) if len(options) == 1 else {"anyOf": [inline(o) for o in options]}
                extra = {k: v for k, v in node.items() if k not in ("anyOf", "default")}
                return {**base, **{k: v for k, v in extra.items() if k in ("description", "title")}}
            out = {}
            for k, v in node.items():
                if k in ("default", "title", "uniqueItems", "examples"):
                    continue
                out[k] = inline(v)
            if out.get("type") == "object":
                out.setdefault("additionalProperties", False)
            return out
        if isinstance(node, list):
            return [inline(x) for x in node]
        return node

    return inline(raw)
