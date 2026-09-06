"""Freeze all outcome-blind reviewer-robustness choices before formal runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, write_json

from .common import (
    CHARACTERIZATION_PATH,
    DISCOVERY_MANIFEST,
    HELDOUT_MANIFEST,
    MANIFEST_ROOT,
    PHASE3_MANIFEST,
    PROTOCOL_PATH,
    REVIEW_ROOT,
    UNIVERSE_MANIFEST,
    derive_seed,
    git_head,
    git_is_dirty,
    load_json,
    load_protocol,
    sha256_file,
    sha256_payload,
    utc_timestamp,
)
from .selection import (
    select_depth_budget_tasks,
    select_finite_shot_tasks,
    selection_records,
    task_frame,
)


MANIFEST_PATHS = {
    "optimizer": MANIFEST_ROOT / "manifest_optimizer_robustness.json",
    "alpha": MANIFEST_ROOT / "manifest_alpha_sensitivity.json",
    "finite_shot": MANIFEST_ROOT / "manifest_finite_shot.json",
    "depth_budget": MANIFEST_ROOT / "manifest_depth_budget.json",
    "classical": MANIFEST_ROOT / "manifest_classical_baseline.json",
}
CODE_AMENDMENT_ROOT = MANIFEST_ROOT / "code_amendments"


def _code_hashes() -> dict[str, str]:
    paths = [PROTOCOL_PATH]
    source_root = PROJECT_ROOT / "src" / "qroute_dilution" / "reviewer_robustness"
    paths.extend(sorted(source_root.glob("*.py")))
    script_root = PROJECT_ROOT / "paper_scripts" / "reviewer_robustness"
    if script_root.exists():
        paths.extend(sorted(script_root.glob("*.py")))
    return {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in paths
        if path.is_file()
    }


def current_code_fingerprint() -> tuple[dict[str, str], str]:
    hashes = _code_hashes()
    return hashes, sha256_payload(hashes)


def _amendment_paths() -> list[Path]:
    return sorted(CODE_AMENDMENT_ROOT.glob("amendment_*.json"))


def latest_code_amendment() -> dict[str, Any] | None:
    paths = _amendment_paths()
    return load_json(paths[-1]) if paths else None


def execution_code_fingerprint(manifest: dict[str, Any]) -> str:
    amendment = latest_code_amendment()
    if amendment is None:
        return str(manifest["code_fingerprint"])
    if amendment["original_manifest_code_fingerprint"] != manifest["code_fingerprint"]:
        raise RuntimeError("code amendment does not refer to the frozen manifests")
    return str(amendment["amended_code_fingerprint"])


def verify_execution_code_fingerprint() -> dict[str, Any]:
    hashes, observed = current_code_fingerprint()
    amendment = latest_code_amendment()
    expected = (
        amendment["amended_code_fingerprint"]
        if amendment is not None
        else load_json(MANIFEST_PATHS["depth_budget"])["code_fingerprint"]
    )
    return {
        "pass": observed == expected,
        "observed_code_fingerprint": observed,
        "expected_code_fingerprint": expected,
        "file_count": len(hashes),
        "latest_amendment": amendment["amendment_id"] if amendment else None,
    }


def record_code_amendment(reason: str) -> dict[str, Any]:
    """Append, never replace, a machine-readable pre/run-time code amendment."""
    if not reason.strip():
        raise ValueError("a non-empty amendment reason is required")
    frozen = load_json(MANIFEST_PATHS["depth_budget"])
    previous = latest_code_amendment()
    hashes, fingerprint = current_code_fingerprint()
    if previous is not None and previous["amended_code_fingerprint"] == fingerprint:
        return previous
    paths = _amendment_paths()
    amendment_id = f"amendment_{len(paths) + 1:03d}"
    value = {
        "schema_version": "qroute-dilution.reviewer-robustness.code-amendment.v1",
        "amendment_id": amendment_id,
        "recorded_at": utc_timestamp(),
        "reason": reason.strip(),
        "scientific_choices_changed": False,
        "task_selection_changed": False,
        "protocol_changed": False,
        "canonical_outputs_mutable": False,
        "original_manifest_code_fingerprint": frozen["code_fingerprint"],
        "previous_execution_code_fingerprint": (
            previous["amended_code_fingerprint"]
            if previous is not None
            else frozen["code_fingerprint"]
        ),
        "amended_code_file_sha256": hashes,
        "amended_code_fingerprint": fingerprint,
        "git_commit": git_head(),
        "worktree_dirty": git_is_dirty(),
    }
    path = CODE_AMENDMENT_ROOT / f"{amendment_id}.json"
    if path.exists():
        raise FileExistsError(f"refusing to overwrite code amendment {path}")
    write_json(path, value)
    return value


def _source_hashes() -> dict[str, str]:
    paths = [
        DISCOVERY_MANIFEST,
        HELDOUT_MANIFEST,
        UNIVERSE_MANIFEST,
        PHASE3_MANIFEST,
        CHARACTERIZATION_PATH,
        PROJECT_ROOT / "results" / "phase1_pilot_v1" / "master_seed_level_results.csv",
        PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "p2_initialization_runs.csv",
        PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "p3_objective_results.csv",
        PROJECT_ROOT / "results" / "posthoc_finite_shot_endpoint_v1" / "manifest.json",
    ]
    return {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in paths
        if path.is_file()
    }


def _common_metadata(timestamp: str) -> dict[str, Any]:
    code_hashes = _code_hashes()
    return {
        "schema_version": "qroute-dilution.reviewer-robustness.manifest.v1",
        "status": "FROZEN_BEFORE_FORMAL_EXECUTION",
        "scientific_role": "POST_HOC_REVIEWER_ROBUSTNESS_ONLY",
        "primary_headline_reoptimization_authorized": False,
        "canonical_outputs_mutable": False,
        "code_git_commit": git_head(),
        "worktree_dirty_at_freeze": git_is_dirty(),
        "frozen_at": timestamp,
        "protocol_path": str(PROTOCOL_PATH.relative_to(PROJECT_ROOT)),
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "code_file_sha256": code_hashes,
        "code_fingerprint": sha256_payload(code_hashes),
        "source_file_sha256": _source_hashes(),
    }


def _task_identity(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "task_id": row["task_id"],
            "graph_id": row["graph_id"],
            "base_instance_id": row["base_instance_id"],
            "size_stratum": row["size_stratum"],
            "stress_level": row["stress_level"],
            "m": row["m"],
            "feasible_fraction_phi": row["feasible_fraction_phi"],
            "dilution_score": row["dilution_score"],
            "task_path": row["task_path"],
        }
        for row in records
    ]


def build_manifests() -> dict[str, dict[str, Any]]:
    if any(path.exists() for path in MANIFEST_PATHS.values()):
        existing = {}
        for key, path in MANIFEST_PATHS.items():
            if not path.exists():
                raise RuntimeError("partial manifest freeze exists; refusing mixed regeneration")
            value = load_json(path)
            if value.get("status") != "FROZEN_BEFORE_FORMAL_EXECUTION":
                raise RuntimeError(f"manifest is not frozen: {path}")
            existing[key] = value
        return existing

    protocol = load_protocol()
    global_settings = protocol["global"]
    timestamp = utc_timestamp()
    common = _common_metadata(timestamp)
    characterization = pd.read_csv(CHARACTERIZATION_PATH)
    discovery = task_frame(load_json(DISCOVERY_MANIFEST), characterization)
    heldout = task_frame(load_json(HELDOUT_MANIFEST), characterization)
    universe = task_frame(load_json(UNIVERSE_MANIFEST), characterization)
    b1_cfg = protocol["depth_budget"]
    b1 = select_depth_budget_tasks(
        discovery,
        count=int(b1_cfg["task_count"]),
        seed=int(b1_cfg["selection_seed"]),
    )
    a3_cfg = protocol["finite_shot"]
    estimator, training = select_finite_shot_tasks(
        heldout,
        estimator_count=int(a3_cfg["estimator_task_count"]),
        training_count=int(a3_cfg["training_task_count"]),
        seed=int(a3_cfg["selection_seed"]),
    )
    discovery_records = selection_records(discovery)
    heldout_records = selection_records(heldout)
    universe_records = selection_records(universe)
    b1_records = selection_records(b1)
    estimator_records = selection_records(estimator)
    training_records = selection_records(training)

    depth_manifest = {
        **common,
        "experiment": "B1_DEPTH_BUDGET",
        "selection_seed": b1_cfg["selection_seed"],
        "selection_rule": b1_cfg["selection_rule"],
        "selection_algorithm": (
            "Within each of 10 discovery graphs sort only by dilution_score and task_id; "
            "take both endpoints. Rank each remaining graph-median candidate by SHA-256 "
            "of the frozen selection seed and graph ID; take the first four."
        ),
        "tasks": _task_identity(b1_records),
        "graph_ids": sorted(b1.graph_id.unique().tolist()),
        "seeds": global_settings["optimizer_seeds"],
        "optimizer": b1_cfg["optimizer"],
        "objectives": b1_cfg["objectives"],
        "depths": b1_cfg["depths"],
        "evaluation_budgets": b1_cfg["evaluation_budgets"],
        "maximum_nfev": b1_cfg["maximum_nfev"],
        "alpha": global_settings["cvar_primary_alpha"],
        "shots": None,
        "checkpoint_rule": b1_cfg["checkpoint_rule"],
        "output_paths": {
            "root": "results/reviewer_robustness/B1_depth_budget",
            "run_records": "results/reviewer_robustness/B1_depth_budget/runs",
        },
        "planned_optimizer_trajectories": len(b1_records)
        * len(b1_cfg["depths"])
        * len(b1_cfg["objectives"])
        * len(global_settings["optimizer_seeds"]),
        "planned_checkpoint_rows": len(b1_records)
        * len(b1_cfg["depths"])
        * len(b1_cfg["objectives"])
        * len(global_settings["optimizer_seeds"])
        * len(b1_cfg["evaluation_budgets"]),
    }
    optimizer_cfg = protocol["optimizer_robustness"]
    optimizer_manifest = {
        **common,
        "experiment": "A1_OPTIMIZER_ROBUSTNESS",
        "selection_rule": optimizer_cfg["selection_rule"],
        "tasks": _task_identity(discovery_records),
        "graph_ids": sorted(discovery.graph_id.unique().tolist()),
        "seeds": global_settings["optimizer_seeds"],
        "optimizers": optimizer_cfg["optimizers"],
        "objectives": optimizer_cfg["objectives"],
        "depths": optimizer_cfg["depths"],
        "evaluation_budget": optimizer_cfg["evaluation_budget"],
        "alpha": global_settings["cvar_primary_alpha"],
        "shots": None,
        "selection_expansion_rule": (
            "Manifest freezes all 56 tasks. Execution may stop after the first 24 "
            "B1-selected tasks for resource reasons only; no outcome-based expansion."
        ),
        "initial_24_task_ids": [row["task_id"] for row in b1_records],
        "output_paths": {
            "root": "results/reviewer_robustness/A1_optimizer",
            "run_records": "results/reviewer_robustness/A1_optimizer/runs",
        },
        "planned_optimizer_runs": len(discovery_records)
        * len(optimizer_cfg["optimizers"])
        * len(optimizer_cfg["objectives"])
        * len(optimizer_cfg["depths"])
        * len(global_settings["optimizer_seeds"]),
    }
    alpha_cfg = protocol["alpha_sensitivity"]
    alpha_manifest = {
        **common,
        "experiment": "A2_ALPHA_SENSITIVITY",
        "selection_rule": alpha_cfg["selection_rule"],
        "discovery_tasks": _task_identity(discovery_records),
        "heldout_tasks": _task_identity(heldout_records),
        "graph_ids": {
            "discovery": sorted(discovery.graph_id.unique().tolist()),
            "heldout": sorted(heldout.graph_id.unique().tolist()),
        },
        "seeds": global_settings["optimizer_seeds"],
        "optimizer": alpha_cfg["optimizer"],
        "objective": "O3",
        "depth": alpha_cfg["depth"],
        "evaluation_budget": alpha_cfg["evaluation_budget"],
        "alphas": {
            "discovery": alpha_cfg["discovery_alphas"],
            "heldout": alpha_cfg["heldout_alphas"],
        },
        "frozen_primary_alpha": global_settings["cvar_primary_alpha"],
        "heldout_result_label": alpha_cfg["heldout_label"],
        "shots": None,
        "heldout_execution_scope": (
            "All held-out tasks are frozen, but resource-limited execution may use only "
            "the outcome-blind A3 estimator subset; every row remains POST_HOC_SENSITIVITY."
        ),
        "heldout_initial_task_ids": [row["task_id"] for row in estimator_records],
        "output_paths": {
            "root": "results/reviewer_robustness/A2_alpha",
            "run_records": "results/reviewer_robustness/A2_alpha/runs",
        },
    }
    sampling_seeds = []
    for row in estimator_records:
        for objective in a3_cfg["endpoint_objectives"]:
            for shots in a3_cfg["estimator_shots"]:
                for replicate in range(int(a3_cfg["estimator_replicates"])):
                    sampling_seeds.append(
                        {
                            "task_id": row["task_id"],
                            "objective": objective,
                            "shots": int(shots),
                            "replicate": replicate,
                            "seed": derive_seed(
                                "reviewer-A3-estimator-v1",
                                a3_cfg["selection_seed"],
                                row["task_id"],
                                objective,
                                shots,
                                replicate,
                            ),
                        }
                    )
    finite_manifest = {
        **common,
        "experiment": "A3_FINITE_SHOT",
        "selection_seed": a3_cfg["selection_seed"],
        "selection_rule": a3_cfg["selection_rule"],
        "selection_algorithm": (
            "Within each held-out size stratum, SHA-256 orders its three graphs and "
            "assigns low/middle/high within-graph dilution ranks; add alternate endpoints "
            "for S1/S3/S5. Training takes low/high selected dilution tasks per size."
        ),
        "estimator_tasks": _task_identity(estimator_records),
        "training_tasks": _task_identity(training_records),
        "graph_ids": sorted(estimator.graph_id.unique().tolist()),
        "endpoint_source": "frozen held-out O0/O3 terminal theta",
        "endpoint_existing_study": "results/posthoc_finite_shot_endpoint_v1",
        "endpoint_existing_study_reused_not_rerun": True,
        "estimator_alphas": a3_cfg["estimator_alphas"],
        "estimator_shots": a3_cfg["estimator_shots"],
        "estimator_replicates": a3_cfg["estimator_replicates"],
        "sampling_seeds": sampling_seeds,
        "training": {
            "objectives": a3_cfg["training_objectives"],
            "optimizer": a3_cfg["training_optimizer"],
            "depth": a3_cfg["training_depth"],
            "evaluation_budget": a3_cfg["training_evaluation_budget"],
            "alpha": global_settings["cvar_primary_alpha"],
            "shots": a3_cfg["training_shots"],
            "seeds": a3_cfg["training_seed_labels"],
            "rng_rule": a3_cfg["rng_rule"],
        },
        "output_paths": {
            "root": "results/reviewer_robustness/A3_finite_shot",
            "run_records": "results/reviewer_robustness/A3_finite_shot/training_runs",
        },
        "planned_training_runs": len(training_records)
        * len(a3_cfg["training_objectives"])
        * len(a3_cfg["training_shots"])
        * len(a3_cfg["training_seed_labels"]),
    }
    classical_cfg = protocol["classical_baseline"]
    classical_manifest = {
        **common,
        "experiment": "B2_CLASSICAL_CONTEXT",
        "selection_rule": classical_cfg["selection_rule"],
        "tasks": _task_identity(universe_records),
        "graph_ids": sorted(universe.graph_id.unique().tolist()),
        "seeds": [],
        "optimizer": None,
        "objective": "exact constrained route cost",
        "depth": None,
        "evaluation_budget": None,
        "alpha": None,
        "shots": None,
        "solver": classical_cfg["solver"],
        "timing": {
            key: classical_cfg[key]
            for key in (
                "minimum_timing_repeats",
                "maximum_timing_repeats",
                "minimum_timed_duration_s",
            )
        },
        "output_paths": {
            "root": "results/reviewer_robustness/B2_classical",
            "run_records": "results/reviewer_robustness/B2_classical/runs",
        },
        "planned_runs": len(universe_records),
    }
    values = {
        "optimizer": optimizer_manifest,
        "alpha": alpha_manifest,
        "finite_shot": finite_manifest,
        "depth_budget": depth_manifest,
        "classical": classical_manifest,
    }
    for key, value in values.items():
        path = MANIFEST_PATHS[key]
        if path.exists():
            raise FileExistsError(f"refusing to overwrite frozen manifest {path}")
        write_json(path, value)
    # Phase-local copies are immutable provenance conveniences, never alternatives.
    local_paths = {
        "depth_budget": REVIEW_ROOT / "B1_depth_budget" / "manifest.json",
        "finite_shot": REVIEW_ROOT / "A3_finite_shot" / "training_manifest.json",
    }
    for key, path in local_paths.items():
        write_json(path, values[key])
    return values
