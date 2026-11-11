"""Thai Token Tax: how many more tokens Thai costs than the same English text.

Pipeline: prepare -> count -> (verify) -> analyze. See ARCHITECTURE.md.
This measures token cost only, not answer quality.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

__version__ = "0.1.0"


class Stop(Exception):
    """The run must stop here. Raised instead of continuing with doubtful data."""


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def new_file(path: Path) -> Path:
    """Result files are append-only: never overwrite one that already exists."""
    if path.exists():
        raise Stop(f"{path} already exists. Results are never overwritten; use --out for a new set.")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
