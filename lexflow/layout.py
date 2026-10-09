"""Add BPMN DI (diagram geometry) with bpmn-auto-layout 2.x.

The layout engine round-trips the XML through bpmn-moddle; to be safe we keep
our own semantic XML byte-for-byte and graft only the generated
``bpmndi:BPMNDiagram`` onto it.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from lxml import etree

from .bpmn_xml import NS

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "node-alpha" / "node_modules" / ".bin" / "bpmn-auto-layout"


class LayoutFailed(RuntimeError):
    pass


def auto_layout(semantic_xml: str, cli: Path = CLI, timeout: int = 120) -> tuple[str, list[dict]]:
    """Return (xml with DI, warnings)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.bpmn"
        dst = Path(tmp) / "out.bpmn"
        src.write_text(semantic_xml, encoding="utf-8")
        proc = subprocess.run([str(cli), str(src), "--output", str(dst)], capture_output=True,
                              text=True, timeout=timeout)
        warnings = []
        for line in proc.stderr.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    warnings.append(json.loads(line))
                except json.JSONDecodeError:
                    warnings.append({"raw": line})
            elif line:
                warnings.append({"raw": line})
        if proc.returncode != 0 or not dst.exists():
            raise LayoutFailed(f"bpmn-auto-layout failed ({proc.returncode}): {proc.stderr.strip()[:2000]}")
        laid_out = dst.read_text(encoding="utf-8")
    return graft_di(semantic_xml, laid_out), warnings


def graft_di(semantic_xml: str, laid_out_xml: str) -> str:
    ours = etree.fromstring(semantic_xml.encode())
    theirs = etree.fromstring(laid_out_xml.encode())
    for old in ours.findall("{%s}BPMNDiagram" % NS["bpmndi"]):
        ours.remove(old)
    diagrams = theirs.findall("{%s}BPMNDiagram" % NS["bpmndi"])
    if not diagrams:
        raise LayoutFailed("layout output has no BPMNDiagram")
    for d in diagrams:
        ours.append(d)
    etree.cleanup_namespaces(ours, top_nsmap={k: v for k, v in NS.items()})
    return etree.tostring(ours, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode()
