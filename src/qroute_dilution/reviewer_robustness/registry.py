"""Run-record validation and unified resumability registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from qroute_dilution.io import atomic_write_csv, write_json

from .common import REVIEW_ROOT


REGISTRY_PATH = REVIEW_ROOT / "run_registry.csv"
TERMINAL_STATUSES = {"COMPLETE", "FAILED", "TIMEOUT", "RESOURCE_CENSORED"}
REGISTRY_FIELDS = [
    "experiment",
    "run_id",
    "task_id",
    "graph_id",
    "objective",
    "optimizer",
    "depth",
    "alpha",
    "nfev_budget",
    "actual_nfev",
    "shots",
    "seed",
    "status",
    "started_at",
    "finished_at",
    "runtime_s",
    "output_path",
    "error_message",
    "git_commit",
    "dirty_state_fingerprint",
]


def read_valid_terminal_record(path: Path, *, run_id: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"existing run record is unreadable: {path}: {exc}") from exc
    if value.get("run_id") != run_id:
        raise RuntimeError(f"existing run ID mismatch at {path}")
    if value.get("status") not in TERMINAL_STATUSES:
        raise RuntimeError(f"existing run is incomplete and will not be overwritten: {path}")
    return value


def write_new_record(path: Path, record: dict[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing run record: {path}")
    write_json(path, record)


def rebuild_registry() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for path in sorted(REVIEW_ROOT.glob("**/*runs/*.json")):
        # Smoke records deliberately share scientific run IDs with their formal
        # counterparts but live in an isolated namespace.  The unified registry
        # is the formal execution ledger; smoke evidence remains on disk under
        # ``results/reviewer_robustness/smoke`` and is not double-counted here.
        if "smoke" in path.relative_to(REVIEW_ROOT).parts:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        registry = dict(value.get("registry", {}))
        if not registry:
            continue
        registry["output_path"] = str(path.relative_to(REVIEW_ROOT.parent.parent))
        rows.append({field: registry.get(field) for field in REGISTRY_FIELDS})
    frame = pd.DataFrame(rows, columns=REGISTRY_FIELDS)
    if len(frame):
        frame = frame.sort_values(["experiment", "run_id"], kind="stable")
        if frame.run_id.duplicated().any():
            raise RuntimeError("duplicate run IDs found while rebuilding registry")
    atomic_write_csv(REGISTRY_PATH, frame)
    return frame


def registry_payload(
    *,
    experiment: str,
    run_id: str,
    task_id: str,
    graph_id: str,
    objective: str | None,
    optimizer: str | None,
    depth: int | None,
    alpha: float | None,
    nfev_budget: int | None,
    actual_nfev: int | None,
    shots: int | None,
    seed: int | None,
    status: str,
    started_at: str,
    finished_at: str,
    runtime_s: float,
    error_message: str,
    git_commit: str,
    dirty_state_fingerprint: str,
) -> dict[str, Any]:
    return {key: value for key, value in locals().items()}
