"""Ollama extraction: request shape, repair loop, scoring, compile-to-BPMN (mocked server)."""
import copy
import json
from pathlib import Path

import responses

from lexflow import gold
from lexflow.bpmn_xml import to_bpmn_xml
from lexflow.extract.compile import compile_facts
from lexflow.extract.evaluate import score
from lexflow.extract.ollama import OllamaClient, check_facts, extract
from lexflow.extract.schema import LegalProcessFacts, ollama_schema
from lexflow.validate import xsd_errors

ROOT = Path(__file__).resolve().parents[1]
GOLD = json.loads((ROOT / "fixtures/gold/albemarle_17_211.facts.json").read_text())


def text_17_211():
    return gold.albemarle_17_211().texts[0].text


def test_schema_is_flat_for_llama_cpp():
    s = json.dumps(ollama_schema())
    assert "$ref" not in s and "anyOf" not in s and "uniqueItems" not in s
    assert '"additionalProperties": false' in s


def test_gold_facts_quotes_are_exact():
    facts = LegalProcessFacts.model_validate(GOLD)
    assert check_facts(facts, text_17_211()) == []


@responses.activate
def test_repair_loop_fixes_paraphrased_quote_and_unknown_actor():
    broken = copy.deepcopy(GOLD)
    broken["steps"][0]["source"]["quote"] = "the appellant may ask the County for a hearing"   # paraphrase
    broken["steps"][1]["actor"] = "zoning_administrator"                                     # not declared
    bodies = []

    def reply(request):
        body = json.loads(request.body)
        bodies.append(body)
        content = json.dumps(broken if len(bodies) == 1 else GOLD)
        return 200, {}, json.dumps({"message": {"role": "assistant", "content": content}, "eval_count": 900})

    responses.add_callback(responses.POST, "http://ollama.test:11434/api/chat", callback=reply)
    client = OllamaClient(base_url="http://ollama.test:11434", model="qwen3.6:27b", num_ctx=32768)
    res = extract(client, text=text_17_211(), section="17-211", title="Review of administrator's action",
                  code="Albemarle County Code", jurisdiction="va/albemarle_county")
    assert res.problems == [] and res.rounds == 2
    first = bodies[0]
    assert first["format"]["type"] == "object" and first["stream"] is False
    assert first["options"] == {"temperature": 0.0, "num_ctx": 32768}
    repair = bodies[1]["messages"][-1]["content"]
    assert "not an exact span" in repair and "unknown actor zoning_administrator" in repair


@responses.activate
def test_gives_up_after_max_repairs():
    responses.add(responses.POST, "http://ollama.test:11434/api/chat",
                  json={"message": {"content": "{\"process_name\": \"x\"}"}})
    res = extract(OllamaClient(base_url="http://ollama.test:11434"), text="x", section="1-1", title="t",
                  code="c", jurisdiction="va/x", max_repairs=1)
    assert res.facts is None and res.rounds == 2 and res.problems


def test_scoring_gold_vs_degraded():
    g = LegalProcessFacts.model_validate(GOLD)
    perfect = score(g, g, text_17_211())
    assert perfect.step_recall == 1.0 and perfect.quote_validity == 1.0 and perfect.deadline_recall == 1.0
    worse = copy.deepcopy(GOLD)
    worse["steps"] = worse["steps"][:4]
    worse["steps"][2]["deadline"] = None
    worse["steps"][0]["modality"] = "obligation"
    s = score(LegalProcessFacts.model_validate(worse), g, text_17_211())
    assert s.step_recall == 0.5 and s.deadline_recall < 1.0 and s.modality_accuracy < 1.0


def test_compiled_model_is_valid_bpmn():
    g = gold.albemarle_17_211()
    m = compile_facts(LegalProcessFacts.model_validate(GOLD), model_id="va-albemarle-17-211-compiled",
                      jurisdiction=g.jurisdiction, jurisdiction_name=g.jurisdiction_name,
                      code="Albemarle County Code", text=g.texts[0])
    assert xsd_errors(to_bpmn_xml(m)) == []
    kinds = {n.type for _, _, n in m.iter_nodes()}
    assert {"eventBasedGateway", "boundaryEvent", "businessRuleTask", "parallelGateway"} <= kinds
