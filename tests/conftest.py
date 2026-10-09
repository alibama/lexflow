import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import gold  # noqa: E402
from lexflow.bpmn_xml import to_bpmn_xml  # noqa: E402
from lexflow.dmn_xml import write_dmn, write_dmn_split  # noqa: E402
from lexflow.layout import auto_layout  # noqa: E402


@pytest.fixture(scope="session")
def models():
    return {name: fn() for name, fn in gold.ALL.items()}


@pytest.fixture(scope="session")
def built(models, tmp_path_factory):
    """Canonical artifacts (BPMN with DI, FEEL DMN, Spiff DMN per decision) for every gold model."""
    out = tmp_path_factory.mktemp("built")
    files = {}
    for name, m in models.items():
        semantic = to_bpmn_xml(m)
        laid, warnings = auto_layout(semantic)
        bpmn = out / f"{name}.bpmn"
        bpmn.write_text(laid)
        entry = {"bpmn": bpmn, "semantic": semantic, "layout_warnings": warnings, "spiff_dmn": []}
        if m.decisions:
            dmn = out / f"{name}.dmn"
            dmn.write_text(write_dmn(m))
            entry["dmn"] = dmn
            for did, xml in write_dmn_split(m, "python").items():
                p = out / f"{name}.{did}.spiff.dmn"
                p.write_text(xml)
                entry["spiff_dmn"].append(p)
        files[name] = entry
    return files
