"""Gold models: standards validity, legal-lint rules, Petri soundness, publishing payloads."""
import os
import re
from pathlib import Path

import pytest
from lxml import etree

from lexflow.petri import analyse
from lexflow.publish.dokuwiki import DokuWiki, linked_bpmn, publish
from lexflow.publish.wikibase import PROPOSED, build_bundle, quickstatements, resolve
from lexflow.validate import bpmnlint, dmnlint, lex_checks, xsd_errors

NAMES = ["albemarle_17_211", "charlottesville_noise", "va_judicial_review_stub"]


@pytest.mark.parametrize("name", NAMES)
def test_bpmn_valid_layout_clean_lint_clean(built, name):
    xml = built[name]["bpmn"].read_text()
    assert xsd_errors(xml) == []
    assert built[name]["layout_warnings"] == []
    assert bpmnlint(built[name]["bpmn"])["ok"]


@pytest.mark.parametrize("name", ["albemarle_17_211", "charlottesville_noise"])
def test_dmn_valid_and_lint_clean(built, name):
    assert xsd_errors(built[name]["dmn"].read_text(), "dmn") == []
    assert dmnlint(built[name]["dmn"])["ok"]
    for p in built[name]["spiff_dmn"]:
        assert xsd_errors(p.read_text(), "dmn") == []


@pytest.mark.parametrize("name", NAMES)
def test_every_quote_is_verbatim_and_every_step_grounded(models, name):
    rep = lex_checks(models[name])
    assert rep.ok, rep.summary()
    assert rep.quotes_checked > 0


def test_full_dom_coverage(models):
    used = {n.type for m in models.values() for _, _, n in m.iter_nodes()}
    needed = {"startEvent", "endEvent", "intermediateCatchEvent", "boundaryEvent", "userTask", "sendTask",
              "businessRuleTask", "callActivity", "subProcess", "task", "exclusiveGateway", "eventBasedGateway"}
    assert needed <= used
    alb = models["albemarle_17_211"]
    assert any(n.triggered_by_event for m in models.values() for _, _, n in m.iter_nodes())     # event sub-process
    assert any(n.type == "boundaryEvent" and not n.interrupting and n.event == "timer" for _, _, n in alb.iter_nodes())
    assert any(n.type == "boundaryEvent" and n.event == "message" for _, _, n in alb.iter_nodes())


def test_legal_lint_rules_catch_defects(built, tmp_path):
    xml = built["charlottesville_noise"]["bpmn"].read_text()
    xml = re.sub(r'(<bpmn:userTask id="n_responsible"[^>]*>).*?(<bpmn:incoming>)', r"\1\2", xml, flags=re.S)
    xml = xml.replace(">P30D<", ">30 days<")
    broken = tmp_path / "broken.bpmn"
    broken.write_text(xml)
    rules = {p["rule"] for p in bpmnlint(broken)["problems"]}
    assert "lexipedia/grounded-element" in rules


@pytest.mark.parametrize("name", NAMES)
def test_petri_nets_sound(models, name):
    for proc in models[name].processes():
        rep, *_ = analyse(proc)
        assert rep.sound is True and rep.error is None, rep


def test_quickstatements_resolve_and_respect_limits(models):
    b = build_bundle(models["albemarle_17_211"])
    p1, p2 = quickstatements(b)
    fake = {k: f"Q{100 + i}" for i, k in enumerate(b.items)}
    props = {k: f"P{30 + i}" for i, k in enumerate(PROPOSED)}
    lines = resolve(p2, fake, props).splitlines()
    assert lines and all(re.match(r"^Q\d+\tP\d+\t", ln) for ln in lines)
    assert max(len(f) for ln in lines for f in ln.split("\t")) <= 402        # quoted 400-char cap
    assert p1.count("CREATE") == len(b.items)


def test_dokuwiki_links_and_dry_run(built, models):
    xml = built["albemarle_17_211"]["bpmn"].read_text()
    linked, links = linked_bpmn(xml, "va/albemarle_county")
    assert links["c_decide"] == "law:va:albemarle_county:17-211"
    assert etree.fromstring(linked.encode()) is not None
    wiki = DokuWiki("http://example.invalid", dry_run=True)
    res = publish(models["albemarle_17_211"], wiki, xml, built["albemarle_17_211"]["dmn"].read_text())
    methods = [c[0] for c in wiki.calls]
    assert methods.count("core.savePage") == 3 and methods.count("core.saveMedia") == 2
    assert res["process_page"] == "process:va:albemarle_county:17-211"


@pytest.mark.skipif(not os.environ.get("DOKUWIKI_TEST_URL"), reason="set DOKUWIKI_TEST_URL/TOKEN for a live wiki")
def test_dokuwiki_live_round_trip(built, models):
    wiki = DokuWiki(os.environ["DOKUWIKI_TEST_URL"], token=os.environ["DOKUWIKI_TEST_TOKEN"])
    assert wiki.whoami()["login"]
    res = publish(models["charlottesville_noise"], wiki, built["charlottesville_noise"]["bpmn"].read_text(),
                  built["charlottesville_noise"]["dmn"].read_text())
    assert "<bpmnio" in wiki.get_page(res["process_page"])
