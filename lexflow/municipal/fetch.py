"""Download public data files once, with size/hash checks and progress in the job log."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable

import requests

from .. import config

Log = Callable[[str], None]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url: str, dest: Path, *, sha256: str | None = None, size: int | None = None,
             log: Log = print, progress: Callable[[float], None] | None = None, timeout: int = 120) -> Path:
    """Fetch ``url`` to ``dest`` unless a verified copy is already there."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if sha256 and sha256_of(dest) == sha256:
            log(f"have {dest.name} (sha256 ok)")
            return dest
        if not sha256 and (size is None or dest.stat().st_size == size):
            log(f"have {dest.name}")
            return dest
        log(f"{dest.name} is stale or incomplete, downloading again")
    tmp = dest.with_suffix(dest.suffix + ".part")
    headers = {"User-Agent": config.USER_AGENT}
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or size or 0)
        done, next_report = 0, 0.0
        h = hashlib.sha256()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if total and done / total >= next_report:
                    log(f"{dest.name}: {done / 1e6:.1f} of {total / 1e6:.1f} MB")
                    if progress:
                        progress(done / total)
                    next_report += 0.25
    if sha256 and h.hexdigest() != sha256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"{dest.name}: sha256 mismatch (expected {sha256[:12]}, got {h.hexdigest()[:12]})")
    os.replace(tmp, dest)
    log(f"saved {dest.name} ({done / 1e6:.1f} MB)")
    return dest
