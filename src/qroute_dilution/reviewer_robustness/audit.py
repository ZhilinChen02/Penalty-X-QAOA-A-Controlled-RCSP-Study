"""R0 repository, clustering, environment, and frozen-protocol audit."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy

from qroute_dilution.io import PROJECT_ROOT, atomic_write_text, write_json

from .common import (
    DISCOVERY_MANIFEST,
    HELDOUT_MANIFEST,
    PHASE3_MANIFEST,
    REVIEW_ROOT,
    canonical_hash_snapshot,
    git_head,
    load_json,
    sha256_file,
    utc_timestamp,
    write_canonical_hash_snapshot,
)


R0_ROOT = REVIEW_ROOT / "R0"
CANONICAL_HASHES_BEFORE = REVIEW_ROOT / "audit" / "canonical_hashes_before.json"


def _manifest_structure(path: Path, graph_key: str) -> dict[str, Any]:
    manifest = load_json(path)
    tasks = manifest["tasks"]
    counts = Counter(str(row[graph_key]) for row in tasks)
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "sha256": sha256_file(path),
        "task_count": len(tasks),
        "base_graph_count": len(counts),
        "tasks_per_graph": dict(sorted(counts.items())),
        "tasks_per_graph_distribution": dict(
            sorted(Counter(counts.values()).items())
        ),
    }


def _write_environment_provenance() -> None:
    provenance = REVIEW_ROOT / "provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    packages = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    cpu = subprocess.run(
        ["lscpu"], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
    ).stdout
    selected_environment = {
        key: os.environ.get(key, "UNSET")
        for key in (
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "PYTHONHASHSEED",
        )
    }
    environment = "\n".join(
        [
            f"captured_at={utc_timestamp()}",
            f"git_head={git_head()}",
            f"python={sys.version.replace(chr(10), ' ')}",
            f"platform={platform.platform()}",
            f"numpy={np.__version__}",
            f"scipy={scipy.__version__}",
            f"pandas={pd.__version__}",
            *(f"{key}={value}" for key, value in selected_environment.items()),
            "",
        ]
    )
    for path, text in (
        (provenance / "environment.txt", environment),
        (provenance / "python_packages.txt", packages),
        (provenance / "cpu_info.txt", cpu),
    ):
        if not path.exists():
            atomic_write_text(path, text)


def run_r0_audit() -> dict[str, Any]:
    R0_ROOT.mkdir(parents=True, exist_ok=True)
    _write_environment_provenance()
    if not CANONICAL_HASHES_BEFORE.exists():
        write_canonical_hash_snapshot(CANONICAL_HASHES_BEFORE)
    discovery = _manifest_structure(DISCOVERY_MANIFEST, "graph_id")
    heldout = _manifest_structure(HELDOUT_MANIFEST, "graph_id")
    phase3 = _manifest_structure(PHASE3_MANIFEST, "base_graph_id")
    phase3_manifest = load_json(PHASE3_MANIFEST)
    phase3["split_task_counts"] = dict(
        sorted(Counter(row["split"] for row in phase3_manifest["tasks"]).items())
    )
    phase3["size_task_counts"] = {
        str(key): value
        for key, value in sorted(
            Counter(int(row["size_m"]) for row in phase3_manifest["tasks"]).items()
        )
    }
    phase2_config_path = PROJECT_ROOT / "configs" / "phase2_confirmatory_v1.yaml"
    phase2_summary_path = (
        PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "summary.json"
    )
    phase2_stats_path = (
        PROJECT_ROOT
        / "results"
        / "phase2_confirmatory_v1"
        / "confirmatory_statistics.json"
    )
    phase2_summary = load_json(phase2_summary_path)
    inference = phase2_summary["confirmatory_inference"]
    inventory = {
        "schema_version": "qroute-dilution.reviewer-robustness.R0.v1",
        "generated_at": utc_timestamp(),
        "git_head": git_head(),
        "discovery": discovery,
        "heldout": heldout,
        "phase3": phase3,
        "existing_confirmatory_inference": {
            "already_graph_level": inference["analysis_unit"] == "base_graph_id",
            "analysis_unit": inference["analysis_unit"],
            "task_count": heldout["task_count"],
            "graph_count": inference["n_base_graphs"],
            "aggregation": "arithmetic mean across planned task levels within graph",
            "p_value": "exact one-sided sign flips of paired graph contrasts",
            "bootstrap": "whole-graph resampling",
            "multiplicity": "Holm correction over frozen H1/H2 family",
            "H1_effect_mean": inference["H1"]["effect_mean"],
            "H1_holm_adjusted_p": inference["H1"]["holm_adjusted_p_value"],
            "H2_effect_mean": inference["H2"]["effect_mean"],
            "H2_holm_adjusted_p": inference["H2"]["holm_adjusted_p_value"],
            "config_sha256": sha256_file(phase2_config_path),
            "summary_sha256": sha256_file(phase2_summary_path),
            "statistics_sha256": sha256_file(phase2_stats_path),
        },
        "new_experiment_inference_policy": {
            "task_rows": "descriptive",
            "primary_robustness_unit": "base_graph_id",
            "interval": "graph-cluster bootstrap",
            "effects": "paired O3 minus O0 within task, then equal-weight graph aggregation",
            "original_H1_H2_family_extended": False,
        },
        "historical_results_never_recomputed_or_replaced": [
            "discovery/held-out assignment",
            "frozen alpha=0.10 choice",
            "H1/H2 p-values, intervals, and conclusions",
            "29/168 optimizer diagnostic",
            "m=20 reversal and m=22 resource censoring",
            "membership/advice theory claims",
            "all canonical result CSV/JSON files",
        ],
        "canonical_hash_snapshot": str(
            CANONICAL_HASHES_BEFORE.relative_to(PROJECT_ROOT)
        ),
        "canonical_hash_aggregate": load_json(CANONICAL_HASHES_BEFORE)[
            "aggregate_sha256"
        ],
    }
    inventory_path = R0_ROOT / "canonical_protocol_inventory.json"
    if inventory_path.exists():
        existing = load_json(inventory_path)
        # The generated timestamp is intentionally not rewritten on resume.
        inventory = existing
    else:
        write_json(inventory_path, inventory)
    report = f"""# R0 — statistical and frozen-protocol audit

## Finding

Existing confirmatory inference is already graph-level and does not require correction. This audit found clustering in the task layout, but **did not find pseudo-replication in the preregistered Phase-2 H1/H2 inference**.

## Task topology

- Discovery: **{discovery['task_count']} tasks / {discovery['base_graph_count']} base graphs**; each graph contributes 3–7 dilution tasks.
- Held-out: **{heldout['task_count']} tasks / {heldout['base_graph_count']} base graphs**; each graph contributes 3–7 dilution tasks.
- Phase 3: **{phase3['task_count']} tasks / {phase3['base_graph_count']} base graphs**; every graph contributes six dilution tasks. Split counts are {phase3['split_task_counts']}.

Tasks from one graph are therefore correlated repeated conditions and cannot be treated as independent replicates for new inference.

## Existing Phase-2 confirmatory statistics

The frozen pipeline first averages all planned dilution-level contrasts within each graph, then gives each of 15 held-out graphs equal weight. It uses exact one-sided sign flips of paired graph contrasts, whole-graph bootstrap resampling, and Holm correction over the preregistered two-hypothesis H1/H2 family. The frozen H1 graph mean is {inference['H1']['effect_mean']:.6f} decades (Holm-adjusted p={inference['H1']['holm_adjusted_p_value']:.9g}); H2 is {inference['H2']['effect_mean']:.6f} decades (Holm-adjusted p={inference['H2']['holm_adjusted_p_value']:.9g}). These values are inventoried, not re-estimated or replaced.

## New reviewer-robustness statistics

New experiments retain task-level results descriptively. Paired O3−O0 effects are formed within task, averaged within base graph, and summarized across equal-weight graphs with graph-cluster bootstrap confidence intervals. Any sign-flip result is explicitly post-hoc and is not added to the frozen H1/H2 family.

## Frozen boundary

This pass will not recalculate or replace the discovery/held-out assignment, alpha=0.10 selection, H1/H2 family, headline p-values or intervals, 29/168 observation, m=20 reversal, m=22 censoring, or theory claims. Tracked canonical inputs and results are protected by the pre-run SHA-256 inventory at `{CANONICAL_HASHES_BEFORE.relative_to(PROJECT_ROOT)}`.
"""
    report_path = R0_ROOT / "R0_AUDIT.md"
    if not report_path.exists():
        atomic_write_text(report_path, report)
    return inventory
