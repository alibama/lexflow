"""State statutes from open-us-law (Vaquill AI), one parquet file per state.

The manifest at ``https://oss-data-us.vaquill.ai/index.json`` lists every file with its
size and SHA-256, so each state is downloaded once and verified.  The data is
CC BY-NC 4.0 (commercial use needs a licence from Vaquill); every row carries the URL
of the government publisher it came from, which is what lexflow cites.
"""
from __future__ import annotations

import json
import re
import time
from functools import lru_cache
from pathlib import Path

import requests

from .. import config
from ..ir import SectionText
from ..store import db
from . import states as S
from .fetch import Log, download

MANIFEST_URL = "https://oss-data-us.vaquill.ai/index.json"
DIR = config.RAW_DIR / "open-us-law"
COLUMNS = ["act_id", "citation", "section_number", "section_title", "chapter_name", "display_path",
           "act_status", "text", "source_url", "word_count", "last_amended_year"]
LIVE = {"in_force", None, ""}


def manifest(refresh: bool = False, log: Log = print) -> dict:
    path = DIR / "index.json"
    if path.exists() and not refresh and time.time() - path.stat().st_mtime < 86_400:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        r = requests.get(MANIFEST_URL, timeout=60, headers={"User-Agent": config.USER_AGENT})
        r.raise_for_status()
        DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(r.text, encoding="utf-8")
        data = r.json()
        log(f"open-us-law manifest {data.get('version')}: {len(data.get('files', []))} files")
        return data
    except requests.RequestException:
        if path.exists():
            log("manifest refresh failed; using the cached copy")
            return json.loads(path.read_text(encoding="utf-8"))
        raise


def entry(man: dict, state: str, kind: str = "statutes") -> dict | None:
    name = f"us_{state}_{kind}.parquet"
    return next((f for f in man.get("files", []) if f["file"] == name), None)


def path_for(state: str, kind: str = "statutes") -> Path:
    return DIR / f"us_{state}_{kind}.parquet"


def fetch_state(con, state: str, *, kinds=("statutes",), log: Log = print) -> str:
    """Download one state's files.  Returns 'downloaded' or 'not-in-release'."""
    man = manifest(log=log)
    status = "not-in-release"
    for kind in kinds:
        e = entry(man, state, kind)
        if e is None:
            log(f"{S.NAME[state]}: no {kind} file in open-us-law {man.get('version')}")
            continue
        p = download(e["url"], path_for(state, kind), sha256=e.get("sha256"), size=e.get("bytes"), log=log)
        if kind == "statutes":
            status = "downloaded"
            import pyarrow.parquet as pq
            sections = pq.ParquetFile(p).metadata.num_rows
            db.upsert(con, "statute_files", [{
                "state": state, "file": e["file"], "url": e["url"], "bytes": e.get("bytes"), "sha256": e.get("sha256"),
                "version": man.get("version"), "sections": sections, "status": status, "downloaded_at": db.now()}],
                keys=("state",), stamp=False)
    if status == "not-in-release":
        db.upsert(con, "statute_files", [{"state": state, "status": status, "version": man.get("version"),
                                          "downloaded_at": db.now()}], keys=("state",), stamp=False)
    con.commit()
    return status


def have(state: str) -> bool:
    return path_for(state).exists()


@lru_cache(maxsize=2)
def load(state: str):
    """In-force sections of one state as a DataFrame (cached for the two most recent states)."""
    import pandas as pd
    p = path_for(state)
    if not p.exists():
        raise FileNotFoundError(f"statutes for {state} are not downloaded")
    return _prepare(pd.read_parquet(p, columns=COLUMNS))


FIXTURES = config.ROOT / "fixtures" / "statutes"


@lru_cache(maxsize=None)
def load_fixture(state: str):
    """fixtures/statutes/<state>_sections.json (the sections the curated files cite) in the shape of load():
    a few kilobytes instead of a whole state's file, for code that only needs the reference sections."""
    import pandas as pd
    p = FIXTURES / f"{state}_sections.json"
    if not p.exists():
        return None
    df = pd.DataFrame(json.loads(p.read_text(encoding="utf-8"))["sections"])
    for c in COLUMNS:
        if c not in df:
            df[c] = None
    return _prepare(df[COLUMNS])


def reference_texts(state: str, numbers: list[str]) -> list[SectionText]:
    """section_texts() served from the fixture file when it holds every section, else from the statutes."""
    fx = load_fixture(state)
    if fx is not None and all(not find(fx, n).empty for n in numbers):
        return section_texts(state, numbers, df=fx)
    return section_texts(state, numbers)


def _prepare(df):
    df = df[df["act_status"].isin(["in_force"]) | df["act_status"].isna()].copy()
    df["section_title"] = df["section_title"].fillna("").str.replace(r"^§\s*[\w.:\-/]+\.?\s*", "", regex=True)
    # Maryland's file carries only stubs like "–203." instead of headings: treat those as no heading
    df.loc[df["section_title"].str.fullmatch(r"[–\-]?[\w.\-–]*\d[\w.\-–]*\.?"), "section_title"] = ""
    df["chapter_name"] = df["chapter_name"].fillna("")
    df["text"] = df["text"].fillna("")
    df["norm_section"] = df["section_number"].fillna("").map(norm_section)
    return df.reset_index(drop=True)


def norm_section(s: str) -> str:
    return re.sub(r"[\s§]+", "", str(s or "")).strip(".").lower()


def strip_history(text: str) -> str:
    """Drop the trailing session-law history line (e.g. '1968, c. 479; ... 2023, c. 534 .')."""
    paras = text.rstrip().split("\n")
    while paras and re.match(r"^\s*(\(?\d{4}[,.)]|Acts \d{4}|L\. ?\d{4}|History|Source:|\[?\d{4}\s*,\s*c)", paras[-1]):
        paras.pop()
    return "\n".join(paras).rstrip()


SINGLE_CODE = {"va": "Code of Virginia", "dc": "D.C. Code"}


def find(df, ref: str):
    """Rows for a section reference: '2.2-3704', or 'General Provisions § 4-203' where a state numbers
    sections within each article or code (Maryland, Texas, California, New York ...)."""
    # a full citation first: some files number sections without their title ("121.01" for A.R.S. § 39-121.01),
    # and some citations have no "§" at all ("5 ILCS 140/3", "La. R.S. 44:33")
    exact = df[df["citation"].fillna("").map(_norm_cite) == _norm_cite(ref)]
    if not exact.empty:
        return exact
    if "§" in ref:
        article, number = (x.strip() for x in ref.rsplit("§", 1))
        hit = df[df["norm_section"] == norm_section(number)]
        return hit[hit["citation"].str.contains(re.escape(article), case=False, regex=True)]
    return df[df["norm_section"] == norm_section(ref)]


def _norm_cite(s: str) -> str:
    return re.sub(r"[\s.]+", " ", str(s or "")).strip().lower()


def ref_of(state: str, row) -> str:
    """The reference to store for a row: the bare number where numbers are unique, else the citation."""
    if state in SINGLE_CODE:
        return row["section_number"]
    df = load(state)
    return row["section_number"] if (df["norm_section"] == row["norm_section"]).sum() == 1 else row["citation"]


def code_of(state: str, row) -> str:
    if state in SINGLE_CODE:
        return SINGLE_CODE[state]
    return str(row["citation"]).rsplit("§", 1)[0].strip().rstrip(",") or f"{S.NAME[state]} statutes"


def section_texts(state: str, numbers: list[str], code: str | None = None, df=None) -> list[SectionText]:
    df = load(state) if df is None else df
    out = []
    for n in numbers:
        hit = find(df, n)
        if hit.empty:
            raise KeyError(f"{state}: section {n} not found in the downloaded statutes")
        if len(hit) > 1 and "§" not in n:
            raise KeyError(f"{state}: section {n} is ambiguous; name the article, e.g. "
                           + "; ".join(hit["citation"].head(4)))
        r = hit.iloc[0]
        out.append(SectionText(section=r["section_number"], title=r["section_title"], code=code or code_of(state, r),
                               jurisdiction=state, text=strip_history(r["text"]), url=r["source_url"],
                               retrieved_from=f"open-us-law {r['act_id']}",
                               license_note="open-us-law (Vaquill AI), CC BY-NC 4.0; text from the government "
                                            "publisher at the URL shown"))
    return out


def code_name(state: str) -> str:
    return SINGLE_CODE.get(state, f"{S.NAME[state]} statutes")


def combined_text(texts: list[SectionText]) -> str:
    if len(texts) == 1:
        return texts[0].text
    return "\n\n".join(f"§ {t.section}. {t.title}\n{t.text}" for t in texts)
