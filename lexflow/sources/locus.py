"""Read LocalLaws/LOCUS-v1 rows for one jurisdiction.

LOCUS is CC BY-NC 4.0 and has no per-row source URL, vendor, document id or
effective date, so it is used here to *find and triage* provisions (function
label = Process / Rules / Enforcement / Context) - published text should be
re-fetched from the primary source (municipal clerk files, Municode/eCode360
where terms allow, Virginia LIS for state law).

Live access needs Hugging Face reachability (blocked in the build sandbox, so
:func:`load_jurisdiction` is exercised against the fixture only).
"""
from __future__ import annotations

import json
from pathlib import Path

DATASET = "LocalLaws/LOCUS-v1"
COLUMNS = ["header", "content", "is_substantive", "function", "topic", "source_jurisdiction_type", "state",
           "city", "county", "enforcement_discretion", "opacity", "paternalism", "problem_salience"]
# Row ranges found by paging the viewer (rows are sorted by state, then jurisdiction)
KNOWN_RANGES = {("va", "charlottesville"): (1_948_791, 1_949_728), ("va", "albemarle_county"): (1_997_762, 2_000_209)}


def load_jurisdiction(state: str, city: str | None = None, county: str | None = None):
    """Stream the parquet shards with a predicate push-down (needs `huggingface_hub` + `pyarrow`)."""
    import pyarrow.dataset as ds
    from huggingface_hub import HfFileSystem
    fs = HfFileSystem()
    files = fs.glob(f"datasets/{DATASET}/data/*.parquet")
    dataset = ds.dataset(files, filesystem=fs, format="parquet")
    expr = ds.field("state") == state
    if city:
        expr = expr & (ds.field("city") == city)
    if county:
        expr = expr & (ds.field("county") == county)
    return dataset.to_table(filter=expr, columns=COLUMNS).to_pandas()


def load_fixture(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text())["rows"]


def triage(rows: list[dict]) -> dict[str, list[dict]]:
    """Route chunks by LOCUS function label (these labels are LLM-made and unvalidated; Process F1 0.68)."""
    out = {"bpmn": [], "dmn": [], "boundary-or-sanction": [], "glossary": []}
    for r in rows:
        f = r.get("function")
        if f == "Process":
            out["bpmn"].append(r)
        elif f == "Rules":
            out["dmn"].append(r)
        elif f == "Enforcement":
            out["boundary-or-sanction"].append(r)
        else:
            out["glossary"].append(r)
    return out
