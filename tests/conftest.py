import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lexflow import gold  # noqa: E402
from lexflow.bpmn_xml import to_bpmn_xml  # noqa: E402
from lexflow.dmn_xml import write_dmn, write_dmn_split  # noqa: E402
from lexflow.layout import auto_layout  # noqa: E402


FIXTURES = ROOT / "fixtures" / "statutes"


@pytest.fixture()
def con(tmp_path, monkeypatch):
    """An empty store in a temp dir, with no shared database or wiki configured."""
    from lexflow import config
    from lexflow.store import db
    monkeypatch.setattr(config, "TURSO_URL", "")
    monkeypatch.setattr(config, "DOKUWIKI_URL", "")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "JOBS_DIR", tmp_path / "jobs")
    c = db.connect(tmp_path / "t.db")
    yield c
    c.close()


def fixture_frame(state: str):
    """fixtures/statutes/<state>_sections.json (every section the curated files cite) as the loader's DataFrame."""
    import json
    import pandas as pd
    from lexflow.municipal import statutes
    path = FIXTURES / f"{state}_sections.json"
    if not path.exists():
        raise FileNotFoundError(path)
    secs = json.loads(path.read_text(encoding="utf-8"))["sections"]
    rows = [dict(act_id=s.get("act_id", f"FIX_{s['section_number']}"), citation=s["citation"],
                 section_number=s["section_number"], section_title=s.get("section_title", ""),
                 chapter_name=s.get("chapter_name", ""), display_path="", act_status="in_force", text=s["text"],
                 source_url=s["source_url"], word_count=len(s["text"].split()), last_amended_year=2023) for s in secs]
    if state == "va":
        rows.append(dict(act_id="decoy", citation="Va. Code Ann. § 18.2-107", section_number="18.2-107",
                         section_title="Theft or destruction of public records by others than officers",
                         chapter_name="", display_path="", act_status="in_force",
                         text="If any person steal public records...", source_url="u", word_count=10,
                         last_amended_year=1975))
    df = pd.DataFrame(rows)
    df["norm_section"] = df["section_number"].map(statutes.norm_section)
    return df


@pytest.fixture()
def va_statutes(monkeypatch):
    """Serve the fixture sections of every state that has a fixture file, as if its parquet were downloaded."""
    from lexflow.municipal import statutes
    frames = {p.name.split("_")[0]: None for p in FIXTURES.glob("*_sections.json")}

    def load(state):
        if frames.get(state) is None:
            frames[state] = fixture_frame(state)
        return frames[state]
    monkeypatch.setattr(statutes, "load", load)
    monkeypatch.setattr(statutes, "have", lambda state: state in frames)
    return load("va")


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
