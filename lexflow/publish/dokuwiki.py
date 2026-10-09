"""Publish Lexipedia models to DokuWiki over the JSON-RPC API (DokuWiki >= 2024-02-06 "Kaos").

Server prerequisites (lexipedia.xyz currently has the API switched off):
  $conf['remote'] = 1;  $conf['remoteuser'] = '@bots';   # never leave remoteuser empty
  a bot user in group "bots" with edit+upload ACL on law:* and process:*;
  a token from the bot's profile page (sent as "Authorization: Bearer ...").

Page layout
  law:<state>:<locality>:<section>      one page per code section (the cross-reference target)
  process:<state>:<locality>:<slug>     the process page with inline <bpmnio> BPMN and DMN
  media  process:<...>:<slug>.bpmn/.dmn/.pnml   canonical downloads
BPMN element names are rewritten to ``[[law:...|Label]]`` in the embedded copy so the
bpmnio plugin turns every grounded step into a link to the section it comes from.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field

import requests
from lxml import etree

from ..bpmn_xml import NS
from ..ir import LegalProcessModel, SectionText

LEX = "{%s}" % NS["lex"]


def page_id(*parts: str) -> str:
    """DokuWiki-safe id: lowercase, ':' only as namespace separator."""
    clean = []
    for p in parts:
        p = p.lower().replace(":", "_").replace("/", ":")
        p = re.sub(r"[^a-z0-9_.:\-]+", "_", p).strip("_")
        clean.append(p)
    return ":".join(clean)


def law_page_id(jurisdiction: str, section: str) -> str:
    return page_id("law", jurisdiction, section)


def process_page_id(model: LegalProcessModel) -> str:
    slug = re.sub(r"^va-[a-z_]+-", "", model.id)
    return page_id("process", model.jurisdiction, slug)


class DokuWikiError(RuntimeError):
    pass


@dataclass
class DokuWiki:
    base_url: str
    token: str | None = None
    user: str | None = None
    password: str | None = None
    dry_run: bool = False
    calls: list = field(default_factory=list)
    timeout: int = 30

    def call(self, method: str, **params):
        self.calls.append((method, {k: (v if k not in ("text", "base64") else f"<{len(str(v))} chars>")
                                    for k, v in params.items()}))
        if self.dry_run:
            return True
        headers = {"Content-Type": "application/json"}
        auth = None
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.user:
            auth = (self.user, self.password or "")
        r = requests.post(f"{self.base_url.rstrip('/')}/lib/exe/jsonrpc.php/{method}",
                          data=json.dumps(params), headers=headers, auth=auth, timeout=self.timeout)
        r.raise_for_status()
        body = r.json()
        err = body.get("error") or {}
        if err.get("code", 0) != 0:
            raise DokuWikiError(f"{method}: {err.get('code')} {err.get('message')}")
        return body.get("result")

    # convenience wrappers (API version 14)
    def whoami(self):
        return self.call("core.whoAmI")

    def get_page(self, page: str) -> str:
        return self.call("core.getPage", page=page)

    def save_page(self, page: str, text: str, summary: str = "lexflow", minor: bool = False):
        return self.call("core.savePage", page=page, text=text, summary=summary, isminor=minor)

    def save_media(self, media: str, data: bytes, overwrite: bool = True):
        return self.call("core.saveMedia", media=media, base64=base64.b64encode(data).decode(), overwrite=overwrite)


# ----------------------------------------------------------------- rendering
def _esc(text: str) -> str:
    """Neutralise DokuWiki markup inside quoted law text."""
    return text.replace("%%", "% %").replace("[[", "[ [").replace("{{", "{ {")


def render_law_page(t: SectionText, cited_by: list[tuple[str, str]] | None = None) -> str:
    lines = [f"====== {t.code} \u00a7 {t.section} ======", "", f"**{t.title}**", ""]
    if t.url:
        lines += [f"Official text: [[{t.url}|{t.url}]]", ""]
    for para in t.text.split("\n\n"):
        lines += [_esc(para.strip()), ""]
    if t.history:
        lines += ["===== History and editorial notes =====", "", "<code>", t.history, "</code>", ""]
    if cited_by:
        lines += ["===== Used by processes =====", ""]
        lines += [f"  * [[{pid}|{title}]]" for pid, title in cited_by]
        lines.append("")
    lines += ["----", f"//Source: {t.retrieved_from}.// " + (f"//{t.license_note}//" if t.license_note else "")]
    return "\n".join(lines) + "\n"


def linked_bpmn(bpmn_xml: str, jurisdiction: str) -> tuple[str, dict[str, str]]:
    """Copy of the BPMN whose grounded elements are named [[law:...|Label]] for bpmnio."""
    doc = etree.fromstring(bpmn_xml.encode())
    links: dict[str, str] = {}
    for el in doc.iter():
        if not isinstance(el.tag, str) or el.get("id") is None or el.get("name") is None:
            continue
        sources = el.findall(f"./{{{NS['bpmn']}}}extensionElements/{LEX}grounding/{LEX}source")
        if not sources:
            continue
        explicit = [s for s in sources if s.get("grounding") == "explicit"] or sources
        src = explicit[0]
        juris = src.get("jurisdiction") or jurisdiction
        target = law_page_id(juris, src.get("section"))
        name = el.get("name").replace("|", "/").replace("]", ")").replace("[", "(")
        el.set("name", f"[[{target}|{name}]]")
        links[el.get("id")] = target
    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8").decode(), links


def render_process_page(model: LegalProcessModel, bpmn_xml: str, dmn_xml: str | None,
                        media_ns: str, powl: dict[str, str] | None = None,
                        checks: dict | None = None) -> str:
    linked, _ = linked_bpmn(bpmn_xml, model.jurisdiction)
    status = model.review.status
    L = [f"====== {model.title} ======", "",
         f"**Jurisdiction:** {model.jurisdiction_name}"
         + (f" ([[https://www.wikidata.org/wiki/{model.jurisdiction_qid}|{model.jurisdiction_qid}]])" if model.jurisdiction_qid else ""),
         f" \\\\ **Review status:** {status} \\\\ **Method:** {model.provenance.method}", "",
         model.summary, "",
         "===== Process =====", "",
         "Click a step to open the law section it comes from.", "",
         '<bpmnio type="bpmn" lint="inactive">', linked.split("?>", 1)[-1].strip(), "</bpmnio>", ""]
    if dmn_xml:
        L += ["===== Decision tables =====", "", '<bpmnio type="dmn">', dmn_xml.split("?>", 1)[-1].strip(), "</bpmnio>", ""]
    L += ["===== Cross-reference: steps to law =====", "",
          "^ Step ^ Type ^ Source ^ Grounding ^ Quoted text ^"]
    for _, _, n in model.iter_nodes():
        for s in n.sources:
            target = law_page_id(s.jurisdiction or model.jurisdiction, s.section)
            quote = (s.quote or "").replace("|", "/")
            if len(quote) > 140:
                quote = quote[:137] + "..."
            L.append(f"| {n.name or n.id} | {n.type} | [[{target}|{s.citation}]] | {s.grounding} | {_esc(quote)} |")
    L += ["", "===== Actors =====", "", "^ Actor ^ Kind ^ Wikidata ^"]
    for a in model.actors:
        wd = f"[[https://www.wikidata.org/wiki/{a.wikidata}|{a.wikidata}]]" if a.wikidata else "-"
        L.append(f"| {a.name} | {a.kind} | {wd} |")
    if model.review.gaps:
        L += ["", "===== Open questions for legal review =====", ""] + [f"  * {g}" for g in model.review.gaps]
    if powl:
        L += ["", "===== Partial order (POWL) and Petri net =====", ""]
        for pid, text in powl.items():
            L += [f"**{pid}**", "<code>", text, "</code>"]
    if checks:
        L += ["", "===== Machine checks =====", "", "<code json>", json.dumps(checks, indent=2), "</code>"]
    L += ["", "===== Downloads =====", "",
          f"  * {{{{:{media_ns}.bpmn|BPMN 2.0 (with DI)}}}}",
          f"  * {{{{:{media_ns}.dmn|DMN 1.3}}}}" if dmn_xml else "",
          "", "----",
          f"//Generated by lexflow; provenance: {', '.join(model.provenance.notes) or model.provenance.method}.//"]
    return "\n".join(x for x in L if x is not None) + "\n"


def publish(model: LegalProcessModel, wiki: DokuWiki, bpmn_xml: str, dmn_xml: str | None,
            pnml: dict[str, str] | None = None, powl: dict[str, str] | None = None,
            checks: dict | None = None) -> dict:
    pid = process_page_id(model)
    media_ns = pid
    done = {"law_pages": [], "process_page": pid, "media": []}
    for t in model.texts:
        lp = law_page_id(t.jurisdiction, t.section)
        wiki.save_page(lp, render_law_page(t, [(pid, model.title)]), summary=f"lexflow: {t.code} § {t.section}")
        done["law_pages"].append(lp)
    wiki.save_media(f"{media_ns}.bpmn", bpmn_xml.encode())
    done["media"].append(f"{media_ns}.bpmn")
    if dmn_xml:
        wiki.save_media(f"{media_ns}.dmn", dmn_xml.encode())
        done["media"].append(f"{media_ns}.dmn")
    wiki.save_page(pid, render_process_page(model, bpmn_xml, dmn_xml, media_ns, powl, checks),
                   summary=f"lexflow: {model.title}")
    return done
