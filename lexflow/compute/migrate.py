"""The one-time relabel of benchmark rows made before the pool existed (idempotent; ``lexflow compute relabel``).

Before the pool, an AskBench LLM arm was ``local+llm`` or ``local+llmplan`` with no model in its name, so a run
with another model would have overwritten the rows (the key is case x arm).  New rows are ``<arm>@<model>``; this
relabels the old ones to ``<arm>@<model>`` for the model that made them (``LEXFLOW_ASK_MODEL`` at the time, by
default ``qwen3:1.7b``: the operator confirms) and records the node, in the row and in its metrics JSON.  The
metrics' ``version`` (the bench's code hash) is left exactly as it was.  Extraction benchmark rows already carry
their model; they gain the node.  ``docs/askbench.json``, a derived file, gets the same arm names.

Back the two tables up first (``backup``: a copy under ``data/backup/``), and run on a copy before the live store.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

from .. import config
from ..store import db

LLM_ARM_MARK = "+llm"            # the arms with a chat model in them: local+llm, local+llmplan, oracle+llm


def backup(db_path: Path | None = None, out_dir: Path | None = None) -> Path:
    """Copy the two benchmark tables into ``<out_dir>/bench-<stamp>.db`` (default data/backup/)."""
    src = Path(db_path or config.DB_PATH)
    out_dir = Path(out_dir or (config.DATA_DIR / "backup"))
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"bench-{db.now().replace(':', '').replace('-', '')}.db"
    con = sqlite3.connect(str(src))
    try:
        con.execute("ATTACH DATABASE ? AS b", (str(dest),))
        con.execute("CREATE TABLE b.ask_bench AS SELECT * FROM main.ask_bench")
        con.execute("CREATE TABLE b.benchmarks AS SELECT * FROM main.benchmarks")
        con.commit()
        con.execute("DETACH DATABASE b")
    finally:
        con.close()
    return dest


def copy_store(db_path: Path | None = None, dest: Path | None = None) -> Path:
    """A whole copy of the store (through SQLite's backup API, so a WAL in progress is included)."""
    src = Path(db_path or config.DB_PATH)
    dest = Path(dest or (config.DATA_DIR / "backup" / f"lexflow-copy-{db.now().replace(':', '').replace('-', '')}.db"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    s = sqlite3.connect(str(src))
    d = sqlite3.connect(str(dest))
    try:
        s.backup(d)
    finally:
        d.close()
        s.close()
    return dest


def relabel_arm(arm: str, model: str) -> str:
    return arm if "@" in arm or LLM_ARM_MARK not in arm else f"{arm}@{model}"


def relabel(con, model: str, node: str, docs_path: Path | None = None, dry: bool = False) -> dict:
    """Relabel ``ask_bench`` rows with an LLM arm and no ``@model`` to ``<arm>@<model>`` and set their node;
    fill ``benchmarks.node`` where empty.  A row whose new key already exists is left alone (counted as
    ``skipped``).  Idempotent: a second run changes nothing."""
    out = {"ask_bench": 0, "skipped": 0, "benchmarks": 0, "model": model, "node": node, "dry": dry}
    if "node" not in db.columns(con, "benchmarks"):
        con.execute("ALTER TABLE benchmarks ADD COLUMN node TEXT")
    rows = db.rows(con, "SELECT case_id, arm, metrics FROM ask_bench WHERE arm LIKE ? AND arm NOT LIKE '%@%'",
                   f"%{LLM_ARM_MARK}%")
    for r in rows:
        new = relabel_arm(r["arm"], model)
        if db.one(con, "SELECT 1 FROM ask_bench WHERE case_id=? AND arm=?", r["case_id"], new):
            out["skipped"] += 1
            continue
        m = db.loads(r["metrics"], {}) or {}
        m["arm"] = new
        m.setdefault("model", model)
        m.setdefault("node", node)
        if not dry:
            con.execute("UPDATE ask_bench SET arm=?, metrics=? WHERE case_id=? AND arm=?",
                        (new, json.dumps(m), r["case_id"], r["arm"]))
        out["ask_bench"] += 1
    if dry:
        out["benchmarks"] = db.scalar(con, "SELECT count(*) FROM benchmarks WHERE model != '-' AND (node IS NULL OR node='')", default=0)
    else:
        out["benchmarks"] = con.execute("UPDATE benchmarks SET node=? WHERE model != '-' AND (node IS NULL OR node='')",
                                        (node,)).rowcount
        if out["ask_bench"] or out["benchmarks"]:          # a later no-op run leaves the note of the real one
            con.execute("INSERT INTO meta(key, value) VALUES ('compute:relabel', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (json.dumps({"at": db.now(), "model": model, "node": node, "ask_bench": out["ask_bench"],
                                     "benchmarks": out["benchmarks"]}),))
        con.commit()
    docs_path = docs_path if docs_path is not None else config.ROOT / "docs" / "askbench.json"
    out["docs"] = relabel_docs(docs_path, model, node) if (docs_path and docs_path.exists() and not dry) else 0
    return out


def relabel_docs(path: Path, model: str, node: str) -> int:
    """The same arm names in docs/askbench.json (rows and summary keys); returns the rows changed."""
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    for r in data.get("rows") or []:
        new = relabel_arm(r.get("arm") or "", model)
        if new != r.get("arm"):
            r["arm"] = new
            r.setdefault("model", model)
            r.setdefault("node", node)
            n += 1
    summ = data.get("summary") or {}
    data["summary"] = {relabel_arm(k, model): v for k, v in summ.items()}
    if n or any(relabel_arm(k, model) != k for k in summ):
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        shutil.move(str(tmp), str(path))
    return n


def main(argv=None) -> int:
    """``python -m lexflow.compute.migrate [--model qwen3:1.7b] [--node ollama] [--db path] [--dry] [--no-backup]``."""
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", default=config.ASK_MODEL, help="the model that made the unlabelled rows (default LEXFLOW_ASK_MODEL)")
    ap.add_argument("--node", default=None, help="the node they ran on (default: OLLAMA_URL's host name)")
    ap.add_argument("--db", default=None, help="a store other than LEXFLOW_DB (a copy to try on)")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--no-docs", action="store_true", help="leave docs/askbench.json alone")
    a = ap.parse_args(argv)
    from .nodes import name_for_url
    node = a.node or name_for_url(config.OLLAMA_URL)
    path = Path(a.db) if a.db else config.DB_PATH
    if not a.dry and not a.no_backup:
        print(f"backup: {backup(path)}")
    con = db.connect(path)
    try:
        out = relabel(con, a.model, node, docs_path=(None if a.no_docs else config.ROOT / "docs" / "askbench.json") if not a.db else Path("/nonexistent"), dry=a.dry)
    finally:
        con.close()
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
