"""Atomic JSON/CSV persistence and configuration loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

from .models import Task
from .schemas import CANONICAL_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("configuration root must be a mapping")
    return config


def atomic_write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_json(path: str | Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True, allow_nan=True) + "\n")


def write_task(path: str | Path, task: Task) -> None:
    write_json(path, task.to_dict())


def read_task(path: str | Path) -> Task:
    with Path(path).open(encoding="utf-8") as handle:
        return Task.from_dict(json.load(handle))


def atomic_write_csv(path: str | Path, frame: pd.DataFrame) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def append_canonical_rows(path: str | Path, rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Append new run IDs atomically; never drop failures or overwrite old rows."""
    path = Path(path)
    new = pd.DataFrame(list(rows), columns=CANONICAL_FIELDS)
    if path.exists():
        existing = pd.read_csv(path)
        missing = set(CANONICAL_FIELDS) - set(existing.columns)
        if missing:
            raise ValueError(f"existing result has incompatible schema: {sorted(missing)}")
        known = set(existing["run_id"].astype(str))
        new = new[~new["run_id"].astype(str).isin(known)]
        combined = pd.concat([existing[CANONICAL_FIELDS], new], ignore_index=True)
    else:
        combined = new
    atomic_write_csv(path, combined)
    return combined
