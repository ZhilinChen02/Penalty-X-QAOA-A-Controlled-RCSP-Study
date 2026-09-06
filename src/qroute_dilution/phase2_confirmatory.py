"""Preregistered, held-out, resume-safe Phase 2 execution."""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json
from .metrics import probability_metrics
from .models import Task
from .optimizer import OptimizationTimeout, optimize_cobyla
from .phase1_1_diagnostic import embed_p2_in_p3
from .phase1_pilot import sha256_file
from .phase1_2_experiment import build_objective_context, objective_value_from_probabilities
from .phase1_2_objectives import (
    feasibility_penalty_bound,
    optimize_cobyla_objective,
    weighted_exact_cvar,
)
from .phase2_statistics import aggregate_base_graph_means, simulate_holm_power
from .qaoa import simulate_qaoa


CONFIG_PATH = PROJECT_ROOT / "configs" / "phase2_confirmatory_v1.yaml"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "phase2_confirmatory_v1.json"
RESULT_ROOT = PROJECT_ROOT / "results" / "phase2_confirmatory_v1"
PREREGISTRATION_PATH = RESULT_ROOT / "PREREGISTRATION.md"
SNAPSHOT_PATH = RESULT_ROOT / "execution_manifest_snapshot.json"
POWER_PATH = RESULT_ROOT / "power_preflight.json"
PREFLIGHT_SUMMARY_PATH = RESULT_ROOT / "preflight" / "preflight_summary.json"
P2_RESULTS_PATH = RESULT_ROOT / "p2_initialization_runs.csv"
P3_RESULTS_PATH = RESULT_ROOT / "p3_objective_results.csv"
ENERGY_AUDIT_PATH = RESULT_ROOT / "energy_separation_audit.csv"


VALID_SCIENTIFIC_STATUSES = {"SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT"}


P2_FIELDS = [
    "run_id",
    "evidence_identity",
    "task_id",
    "base_graph_id",
    "base_instance_id",
    "size_stratum",
    "stress_level",
    "n_edges",
    "dilution_score",
    "feasible_state_fraction",
    "optimizer_seed",
    "objective_id",
    "objective_definition",
    "depth",
    "optimizer",
    "eval_budget",
    "initial_parameters",
    "terminal_parameters",
    "objective_start",
    "objective_final",
    "objective_improvement",
    "p_feas",
    "p_opt",
    "p_opt_given_feasible",
    "log_feasibility_gain",
    "nfev",
    "runtime_s",
    "optimizer_status",
    "optimizer_message",
    "numerically_valid",
    "execution_status",
    "failure_reason",
    "selected_for_p3",
    "config_sha256",
    "raw_statevector_persisted",
    "peak_memory_mb",
]


P3_FIELDS = [
    "run_id",
    "evidence_identity",
    "task_id",
    "base_graph_id",
    "base_instance_id",
    "size_stratum",
    "stress_level",
    "n_edges",
    "dilution_score",
    "feasible_state_fraction",
    "objective_id",
    "objective_name",
    "objective_definition",
    "objective_role",
    "depth",
    "optimizer",
    "eval_budget",
    "source_p2_seed",
    "source_p2_run_id",
    "source_p2_objective_final",
    "initialization_rule",
    "initial_parameters",
    "terminal_parameters",
    "best_evaluated_parameters",
    "objective_start",
    "objective_final",
    "objective_improvement",
    "terminal_objective",
    "best_evaluated_objective",
    "mean_energy_start",
    "mean_energy",
    "expected_routing_component",
    "expected_flow_penalty",
    "expected_resource_penalty",
    "expected_total_penalty",
    "p_feas_start",
    "p_feas",
    "p_feas_change",
    "p_opt_start",
    "p_opt",
    "p_opt_change",
    "p_opt_given_feasible_start",
    "p_opt_given_feasible",
    "feasibility_amplification",
    "log_feasibility_gain_start",
    "log_feasibility_gain",
    "expected_route_cost_given_feasible",
    "cvar_alpha",
    "cvar_value",
    "cvar_cutoff_energy",
    "cvar_tail_feasible_mass",
    "cvar_tail_fully_feasible",
    "cvar_fractional_cutoff_mass",
    "strict_energy_class_separation",
    "penalty_bound_pass",
    "state_norm",
    "nfev",
    "tracked_optimizer_evaluations",
    "total_objective_evaluations",
    "runtime_s",
    "peak_memory_mb",
    "optimizer_status",
    "optimizer_message",
    "numerically_valid",
    "execution_status",
    "failure_reason",
    "paired_analysis_eligible",
    "config_sha256",
    "ansatz_cost_phase_hamiltonian",
    "raw_statevector_persisted",
]


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / 1024.0 if value < 10**9 else value / (1024.0**2))


def _parse_parameters(value: str | list[float]) -> np.ndarray:
    return np.asarray(json.loads(value) if isinstance(value, str) else value, dtype=np.float64)


def build_phase2_manifest() -> dict[str, Any]:
    """Derive held-out trajectories mechanically from immutable manifest set difference."""
    config = load_config(CONFIG_PATH)
    universe = json.loads(
        (PROJECT_ROOT / config["task_universe_manifest"]).read_text(encoding="utf-8")
    )
    discovery = json.loads(
        (PROJECT_ROOT / config["discovery_manifest"]).read_text(encoding="utf-8")
    )
    discovery_bases = {row["base_instance_id"] for row in discovery["tasks"]}
    discovery_tasks = {row["task_id"] for row in discovery["tasks"]}
    heldout_tasks = [
        row for row in universe["tasks"] if row["base_instance_id"] not in discovery_bases
    ]
    heldout_bases = {row["base_instance_id"] for row in heldout_tasks}
    heldout_task_ids = {row["task_id"] for row in heldout_tasks}
    heldout_families = [
        row for row in universe["families"] if row["base_instance_id"] in heldout_bases
    ]
    graph_overlap = heldout_bases & discovery_bases
    task_overlap = heldout_task_ids & discovery_tasks
    if graph_overlap or task_overlap:
        raise RuntimeError(
            f"held-out overlap detected; STOP: graphs={sorted(graph_overlap)}, tasks={sorted(task_overlap)}"
        )
    counts_by_size: dict[str, dict[str, int]] = {}
    for size in config["expected_counts_by_size"]:
        tasks = [row for row in heldout_tasks if row["size_stratum"] == size]
        bases = {row["base_instance_id"] for row in tasks}
        levels = {base: sum(row["base_instance_id"] == base for row in tasks) for base in bases}
        expected = config["expected_counts_by_size"][size]
        observed = {
            "tasks": len(tasks),
            "base_graphs": len(bases),
            "levels_per_graph": sorted(set(levels.values())),
        }
        if (
            observed["tasks"] != int(expected["tasks"])
            or observed["base_graphs"] != int(expected["base_graphs"])
            or observed["levels_per_graph"] != [int(expected["levels_per_graph"])]
        ):
            raise RuntimeError(f"held-out structure mismatch for {size}: {observed}")
        counts_by_size[size] = observed
    if len(heldout_tasks) != int(config["expected_task_count"]) or len(heldout_bases) != int(
        config["expected_base_graph_count"]
    ):
        raise RuntimeError("held-out task/base denominator mismatch")
    payload = {
        "schema_version": "phase2_confirmatory_v1.manifest.v1",
        "experiment_name": config["experiment_name"],
        "pre_run_git_sha": config["pre_run_git_sha"],
        "selection_rule": config["heldout_selection_rule"],
        "source_task_universe_manifest": config["task_universe_manifest"],
        "source_discovery_manifest": config["discovery_manifest"],
        "task_count": len(heldout_tasks),
        "base_graph_count": len(heldout_bases),
        "counts_by_size": counts_by_size,
        "phase2_base_graph_overlap_with_discovery": len(graph_overlap),
        "phase2_task_overlap_with_discovery": len(task_overlap),
        "planned_p2_runs": int(config["p2_preparation"]["planned_runs"]),
        "planned_p3_runs": int(config["p3_comparison"]["planned_runs"]),
        "planned_total_optimized_runs": int(config["p2_preparation"]["planned_runs"])
        + int(config["p3_comparison"]["planned_runs"]),
        "base_graph_ids": sorted(heldout_bases),
        "families": heldout_families,
        "tasks": heldout_tasks,
    }
    write_json(MANIFEST_PATH, payload)
    return payload


def _immutable_files(config: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    for relative in config["immutable_paths"]:
        path = PROJECT_ROOT / relative
        if path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"immutable predecessor path missing: {relative}")
    return sorted(set(files), key=lambda path: str(path.relative_to(PROJECT_ROOT)))


def preregistration_identity() -> dict[str, str]:
    """Return the exact prospective identity inputs that freeze will record."""
    config = load_config(CONFIG_PATH)
    if not MANIFEST_PATH.exists():
        build_phase2_manifest()
    return {
        "phase2_manifest_sha256": sha256_file(MANIFEST_PATH),
        "phase2_config_sha256": sha256_file(CONFIG_PATH),
        "preregistration_sha256": sha256_file(PREREGISTRATION_PATH),
        "task_universe_manifest_sha256": sha256_file(
            PROJECT_ROOT / config["task_universe_manifest"]
        ),
        "discovery_manifest_sha256": sha256_file(
            PROJECT_ROOT / config["discovery_manifest"]
        ),
        "penalty_contract_sha256": sha256_file(
            PROJECT_ROOT / config["penalty_contract_file"]
        ),
    }


def verify_predecessor_commit_clean() -> bool:
    """Verify immutable predecessor paths have no tracked change from the frozen SHA."""
    config = load_config(CONFIG_PATH)
    relative_paths = [str(path) for path in config["immutable_paths"]]
    result = subprocess.run(
        ["git", "diff", "--quiet", str(config["pre_run_git_sha"]), "--", *relative_paths],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("tracked immutable predecessor differs from frozen commit")
    return True


def run_power_preflight() -> dict[str, Any]:
    """Use only Phase-1.2 discovery graph contrasts for the preregistered projection."""
    config = load_config(CONFIG_PATH)
    discovery = pd.read_csv(PROJECT_ROOT / config["phase1_2_results"])
    graph = aggregate_base_graph_means(discovery)
    if len(graph) != 10:
        raise RuntimeError("discovery graph denominator changed")
    contrasts = graph[["Delta1_CVAR_MEAN", "Delta2_CVAR_CAPACITY"]].to_numpy()
    power_config = config["power_preflight"]
    result = simulate_holm_power(
        contrasts,
        heldout_n=int(power_config["heldout_base_graph_n"]),
        simulations=int(power_config["simulations"]),
        seed=int(power_config["seed"]),
        noninferiority_margin=float(config["noninferiority_margin_decades"]),
        family_alpha=float(config["primary_inference"]["family_alpha"]),
    )
    powers = result["projected_Holm_power"]
    minimum = float(power_config["minimum_target"])
    preferred = float(power_config["preferred_target"])
    result.update(
        {
            "source": "Phase 1.2 discovery base graphs only",
            "minimum_target": minimum,
            "preferred_target": preferred,
            "H1_minimum_met": bool(powers["H1"] >= minimum),
            "H2_minimum_met": bool(powers["H2"] >= minimum),
            "H1_preferred_met": bool(powers["H1"] >= preferred),
            "H2_preferred_met": bool(powers["H2"] >= preferred),
            "power_gate": (
                "PASS_CONFIRMATORY"
                if powers["H1"] >= minimum and powers["H2"] >= minimum
                else "UNDERPOWERED_FOR_CONFIRMATORY"
            ),
        }
    )
    write_json(POWER_PATH, result)
    return result


def freeze_execution_identity() -> dict[str, Any]:
    """Hash preregistration and all sources after tests/preflight, before held-out runs."""
    config = load_config(CONFIG_PATH)
    observed_head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if observed_head != str(config["pre_run_git_sha"]):
        raise RuntimeError(
            f"Phase 2 must freeze at {config['pre_run_git_sha']}; observed {observed_head}"
        )
    manifest = build_phase2_manifest()
    if not PREFLIGHT_SUMMARY_PATH.exists():
        raise RuntimeError("discovery-only end-to-end preflight must pass before freeze")
    preflight = json.loads(PREFLIGHT_SUMMARY_PATH.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASSED":
        raise RuntimeError("discovery-only preflight failed; STOP")
    if not POWER_PATH.exists():
        raise RuntimeError("discovery-only power preflight must run before freeze")
    power = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    historical_hashes = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in _immutable_files(config)
    }
    prospective = preregistration_identity()
    identity = {
        "evidence_identity": config["evidence_identity"],
        "pre_run_git_sha": observed_head,
        **prospective,
        "power_preflight_sha256": sha256_file(POWER_PATH),
        "execution_preflight_summary_sha256": sha256_file(PREFLIGHT_SUMMARY_PATH),
        "task_count": manifest["task_count"],
        "base_graph_count": manifest["base_graph_count"],
        "phase2_base_graph_overlap_with_discovery": manifest[
            "phase2_base_graph_overlap_with_discovery"
        ],
        "phase2_task_overlap_with_discovery": manifest[
            "phase2_task_overlap_with_discovery"
        ],
        "planned_p2_runs": manifest["planned_p2_runs"],
        "planned_p3_runs": manifest["planned_p3_runs"],
        "planned_total_optimized_runs": manifest["planned_total_optimized_runs"],
        "power_gate": power["power_gate"],
        "historical_file_count": len(historical_hashes),
        "historical_files": historical_hashes,
        "formal_heldout_optimization_started": False,
    }
    write_json(SNAPSHOT_PATH, identity)
    return identity


def verify_predecessor_immutability() -> dict[str, str]:
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    observed = {
        path: sha256_file(PROJECT_ROOT / path)
        for path in sorted(snapshot["historical_files"])
    }
    if observed != snapshot["historical_files"]:
        changed = [
            path for path in observed if observed[path] != snapshot["historical_files"].get(path)
        ]
        raise RuntimeError(f"immutable predecessor changed: {changed}")
    return observed


def load_frozen_phase2() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    verify_predecessor_immutability()
    config = load_config(CONFIG_PATH)
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    checks = {
        "phase2_manifest_sha256": MANIFEST_PATH,
        "phase2_config_sha256": CONFIG_PATH,
        "preregistration_sha256": PREREGISTRATION_PATH,
        "task_universe_manifest_sha256": PROJECT_ROOT / config["task_universe_manifest"],
        "discovery_manifest_sha256": PROJECT_ROOT / config["discovery_manifest"],
        "penalty_contract_sha256": PROJECT_ROOT / config["penalty_contract_file"],
        "power_preflight_sha256": POWER_PATH,
        "execution_preflight_summary_sha256": PREFLIGHT_SUMMARY_PATH,
    }
    for key, path in checks.items():
        if sha256_file(path) != snapshot[key]:
            raise RuntimeError(f"frozen Phase 2 identity changed: {key}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if (
        manifest["phase2_base_graph_overlap_with_discovery"] != 0
        or manifest["phase2_task_overlap_with_discovery"] != 0
    ):
        raise RuntimeError("held-out overlap changed; STOP")
    characterization = (
        pd.read_csv(PROJECT_ROOT / config["characterization"])
        .set_index("task_id")
        .to_dict(orient="index")
    )
    return config, manifest, characterization


def _scientific_evaluation(
    task: Task,
    context: dict[str, Any],
    parameters: np.ndarray,
    *,
    depth: int,
    cvar_alpha: float,
) -> dict[str, Any]:
    state = simulate_qaoa(np.asarray(parameters, dtype=np.float64), context["energy"], depth)
    probabilities = np.abs(state) ** 2
    phi = float(context["feasible_mask"].mean())
    metrics = probability_metrics(
        probabilities,
        np.flatnonzero(context["feasible_mask"]),
        np.flatnonzero(context["optimal_mask"]),
        phi,
    )
    p_feas = float(metrics["p_feas"])
    flow = float(np.dot(probabilities, context["flow_penalty"]))
    resource = float(np.dot(probabilities, context["resource_penalty"]))
    cvar = weighted_exact_cvar(
        context["energy"],
        probabilities,
        cvar_alpha,
        feasible_mask=context["feasible_mask"],
        energy_order=context["energy_order"],
    )
    bound = feasibility_penalty_bound(
        probabilities, context["feasible_mask"], context["total_penalty"]
    )
    conditional_cost = (
        float(
            np.dot(
                probabilities[context["feasible_mask"]],
                context["routing_cost_raw"][context["feasible_mask"]],
            )
            / p_feas
        )
        if p_feas > 0.0
        else math.nan
    )
    max_feasible = float(context["energy"][context["feasible_mask"]].max())
    min_infeasible = float(context["energy"][~context["feasible_mask"]].min())
    return {
        "mean_energy": float(np.dot(probabilities, context["energy"])),
        "expected_routing_component": float(
            np.dot(probabilities, context["routing_component"])
        ),
        "expected_flow_penalty": flow,
        "expected_resource_penalty": resource,
        "expected_total_penalty": flow + resource,
        "p_feas": p_feas,
        "p_opt": metrics["p_opt"],
        "p_opt_given_feasible": metrics["p_opt_given_feasible"],
        "feasibility_amplification": metrics["feasibility_amplification"],
        "log_feasibility_gain": metrics["log_feasibility_gain"],
        "expected_route_cost_given_feasible": conditional_cost,
        "cvar_alpha": float(cvar_alpha),
        **cvar,
        "strict_energy_class_separation": bool(min_infeasible > max_feasible),
        "penalty_bound_pass": bound["bound_pass"],
        "state_norm": float(probabilities.sum()),
    }


def _failure_status(exc: Exception) -> str:
    if isinstance(exc, OptimizationTimeout):
        return "TIMEOUT"
    if isinstance(exc, MemoryError):
        return "OOM"
    if isinstance(exc, FloatingPointError):
        return "NUMERICAL_FAILURE"
    return "OPTIMIZER_FAILURE"


def _p2_run_id(task_id: str, seed: int, config_hash: str, namespace: str) -> str:
    payload = f"{namespace}|p2|{task_id}|{seed}|{config_hash}"
    return "phase2-p2-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _p3_run_id(task_id: str, objective_id: str, config_hash: str, namespace: str) -> str:
    payload = f"{namespace}|p3|{task_id}|{objective_id}|{config_hash}"
    return "phase2-p3-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _base_p2_row(
    task: Task,
    characterization: dict[str, Any],
    seed: int,
    config: dict[str, Any],
    config_hash: str,
    namespace: str,
) -> dict[str, Any]:
    row = {field: math.nan for field in P2_FIELDS}
    row.update(
        {
            "run_id": _p2_run_id(task.task_id, seed, config_hash, namespace),
            "evidence_identity": config["evidence_identity"],
            "task_id": task.task_id,
            "base_graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "stress_level": task.tightness_level,
            "n_edges": len(task.graph.edges),
            "dilution_score": float(characterization["dilution_score"]),
            "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
            "optimizer_seed": int(seed),
            "objective_id": "P2_MEAN_ENERGY_PREPARATION",
            "objective_definition": "E_theta[H_C]",
            "depth": 2,
            "optimizer": "COBYLA",
            "eval_budget": int(config["p2_preparation"]["eval_budget"]),
            "execution_status": "SUCCESS",
            "failure_reason": "",
            "selected_for_p3": False,
            "config_sha256": config_hash,
            "raw_statevector_persisted": False,
        }
    )
    return row


def _run_p2_task_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
    namespace: str,
    seeds: list[int],
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    rows = []
    try:
        context = build_objective_context(
            task, float(config["hamiltonian_normalization_factor"])
        )
    except Exception as exc:
        for seed in seeds:
            row = _base_p2_row(task, characterization, seed, config, config_hash, namespace)
            row["execution_status"] = _failure_status(exc)
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
            row["peak_memory_mb"] = _peak_memory_mb()
            rows.append({field: row[field] for field in P2_FIELDS})
        return rows
    for seed in seeds:
        row = _base_p2_row(task, characterization, seed, config, config_hash, namespace)
        try:
            result = optimize_cobyla(
                context["energy"],
                2,
                int(seed),
                int(config["p2_preparation"]["eval_budget"]),
                timeout_s=float(config["p2_preparation"]["timeout_s"]),
            )
            evaluation = _scientific_evaluation(
                task,
                context,
                result.optimized_parameters,
                depth=2,
                cvar_alpha=float(config["cvar_alpha"]),
            )
            row.update(
                {
                    "initial_parameters": json.dumps(result.initial_parameters.tolist()),
                    "terminal_parameters": json.dumps(result.optimized_parameters.tolist()),
                    "objective_start": result.objective_initial,
                    "objective_final": result.objective_final,
                    "objective_improvement": result.objective_initial - result.objective_final,
                    "p_feas": evaluation["p_feas"],
                    "p_opt": evaluation["p_opt"],
                    "p_opt_given_feasible": evaluation["p_opt_given_feasible"],
                    "log_feasibility_gain": evaluation["log_feasibility_gain"],
                    "nfev": result.nfev,
                    "runtime_s": result.runtime_s,
                    "optimizer_status": result.status,
                    "optimizer_message": result.message,
                    "numerically_valid": result.success,
                }
            )
            if not result.success:
                raise FloatingPointError("non-finite p2 optimizer result")
            if evaluation["p_feas"] <= np.finfo(float).tiny:
                row["execution_status"] = "ZERO_P_FEAS"
                row["failure_reason"] = "ZERO_P_FEAS"
            elif evaluation["p_opt"] <= np.finfo(float).tiny:
                row["execution_status"] = "ZERO_P_OPT"
                row["failure_reason"] = "ZERO_P_OPT"
        except Exception as exc:
            row["execution_status"] = _failure_status(exc)
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
        row["peak_memory_mb"] = _peak_memory_mb()
        rows.append({field: row[field] for field in P2_FIELDS})
    return rows


def _base_p3_row(
    task: Task,
    characterization: dict[str, Any],
    objective_id: str,
    p2_row: dict[str, Any] | None,
    config: dict[str, Any],
    config_hash: str,
    namespace: str,
) -> dict[str, Any]:
    row = {field: math.nan for field in P3_FIELDS}
    objective = config["p3_comparison"][objective_id]
    row.update(
        {
            "run_id": _p3_run_id(task.task_id, objective_id, config_hash, namespace),
            "evidence_identity": config["evidence_identity"],
            "task_id": task.task_id,
            "base_graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "stress_level": task.tightness_level,
            "n_edges": len(task.graph.edges),
            "dilution_score": float(characterization["dilution_score"]),
            "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
            "objective_id": objective_id,
            "objective_name": objective["name"],
            "objective_definition": objective["definition"],
            "objective_role": objective["role"],
            "depth": 3,
            "optimizer": "COBYLA",
            "eval_budget": int(config["p3_comparison"]["eval_budget"]),
            "source_p2_seed": int(p2_row["optimizer_seed"]) if p2_row else math.nan,
            "source_p2_run_id": p2_row["run_id"] if p2_row else "",
            "source_p2_objective_final": (
                float(p2_row["objective_final"]) if p2_row else math.nan
            ),
            "initialization_rule": config["p3_comparison"]["initialization_rule"],
            "execution_status": "SUCCESS" if p2_row else "RESOURCE_CENSORED",
            "failure_reason": "" if p2_row else "no finite p2 preparation available",
            "paired_analysis_eligible": False,
            "config_sha256": config_hash,
            "ansatz_cost_phase_hamiltonian": config["ansatz_cost_phase_hamiltonian"],
            "raw_statevector_persisted": False,
        }
    )
    return row


def _objective_from_evaluation(objective_id: str, evaluation: dict[str, Any]) -> float:
    return {
        "O0": float(evaluation["mean_energy"]),
        "O2": float(1.0 - evaluation["p_feas"]),
        "O3": float(evaluation["cvar_value"]),
    }[objective_id]


def _run_p3_task_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    p2_row: dict[str, Any] | None,
    config: dict[str, Any],
    config_hash: str,
    namespace: str,
    objective_ids: list[str],
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    if p2_row is None:
        return [
            {
                **_base_p3_row(
                    task, characterization, objective_id, None, config, config_hash, namespace
                ),
                "peak_memory_mb": _peak_memory_mb(),
            }
            for objective_id in objective_ids
        ]
    try:
        context = build_objective_context(
            task, float(config["hamiltonian_normalization_factor"])
        )
        initial = embed_p2_in_p3(_parse_parameters(p2_row["terminal_parameters"]))
        start = _scientific_evaluation(
            task, context, initial, depth=3, cvar_alpha=float(config["cvar_alpha"])
        )
    except Exception as exc:
        rows = []
        for objective_id in objective_ids:
            row = _base_p3_row(
                task, characterization, objective_id, p2_row, config, config_hash, namespace
            )
            row["execution_status"] = _failure_status(exc)
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
            row["peak_memory_mb"] = _peak_memory_mb()
            rows.append({field: row[field] for field in P3_FIELDS})
        return rows
    rows = []
    for objective_id in objective_ids:
        row = _base_p3_row(
            task, characterization, objective_id, p2_row, config, config_hash, namespace
        )
        try:
            alpha = float(config["cvar_alpha"])

            def objective(parameters: np.ndarray) -> float:
                probabilities = np.abs(simulate_qaoa(parameters, context["energy"], 3)) ** 2
                return objective_value_from_probabilities(
                    objective_id, probabilities, context, cvar_alpha=alpha
                )

            result = optimize_cobyla_objective(
                objective,
                initial,
                eval_budget=int(config["p3_comparison"]["eval_budget"]),
                timeout_s=float(config["p3_comparison"]["timeout_s"]),
                rhobeg=float(config["cobyla_rhobeg"]),
                catol=float(config["cobyla_catol"]),
            )
            final = _scientific_evaluation(
                task,
                context,
                result.terminal_parameters,
                depth=3,
                cvar_alpha=alpha,
            )
            objective_final = _objective_from_evaluation(objective_id, final)
            row.update(
                {
                    "initial_parameters": json.dumps(initial.tolist()),
                    "terminal_parameters": json.dumps(result.terminal_parameters.tolist()),
                    "best_evaluated_parameters": json.dumps(
                        result.best_evaluated_parameters.tolist()
                    ),
                    "objective_start": result.objective_start,
                    "objective_final": objective_final,
                    "objective_improvement": result.objective_start - objective_final,
                    "terminal_objective": result.terminal_objective,
                    "best_evaluated_objective": result.best_evaluated_objective,
                    "mean_energy_start": start["mean_energy"],
                    "mean_energy": final["mean_energy"],
                    "expected_routing_component": final["expected_routing_component"],
                    "expected_flow_penalty": final["expected_flow_penalty"],
                    "expected_resource_penalty": final["expected_resource_penalty"],
                    "expected_total_penalty": final["expected_total_penalty"],
                    "p_feas_start": start["p_feas"],
                    "p_feas": final["p_feas"],
                    "p_feas_change": final["p_feas"] - start["p_feas"],
                    "p_opt_start": start["p_opt"],
                    "p_opt": final["p_opt"],
                    "p_opt_change": final["p_opt"] - start["p_opt"],
                    "p_opt_given_feasible_start": start["p_opt_given_feasible"],
                    "p_opt_given_feasible": final["p_opt_given_feasible"],
                    "feasibility_amplification": final["feasibility_amplification"],
                    "log_feasibility_gain_start": start["log_feasibility_gain"],
                    "log_feasibility_gain": final["log_feasibility_gain"],
                    "expected_route_cost_given_feasible": final[
                        "expected_route_cost_given_feasible"
                    ],
                    "cvar_alpha": alpha,
                    "cvar_value": final["cvar_value"],
                    "cvar_cutoff_energy": final["cvar_cutoff_energy"],
                    "cvar_tail_feasible_mass": final["cvar_tail_feasible_mass"],
                    "cvar_tail_fully_feasible": final["cvar_tail_fully_feasible"],
                    "cvar_fractional_cutoff_mass": final[
                        "cvar_fractional_cutoff_mass"
                    ],
                    "strict_energy_class_separation": final[
                        "strict_energy_class_separation"
                    ],
                    "penalty_bound_pass": final["penalty_bound_pass"],
                    "state_norm": final["state_norm"],
                    "nfev": result.optimizer_nfev,
                    "tracked_optimizer_evaluations": result.tracked_optimizer_evaluations,
                    "total_objective_evaluations": result.total_objective_evaluations,
                    "runtime_s": result.runtime_s,
                    "optimizer_status": result.status,
                    "optimizer_message": result.message,
                    "numerically_valid": result.numerically_valid,
                }
            )
            if abs(objective_final - result.terminal_objective) > 1e-9:
                raise FloatingPointError("terminal objective recomputation mismatch")
            if not result.numerically_valid or not final["penalty_bound_pass"]:
                raise FloatingPointError("numerical or penalty-bound validation failed")
            if final["p_feas"] <= np.finfo(float).tiny:
                row["execution_status"] = "ZERO_P_FEAS"
                row["failure_reason"] = "ZERO_P_FEAS"
            elif final["p_opt"] <= np.finfo(float).tiny:
                row["execution_status"] = "ZERO_P_OPT"
                row["failure_reason"] = "ZERO_P_OPT"
        except Exception as exc:
            row["execution_status"] = _failure_status(exc)
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
        row["peak_memory_mb"] = _peak_memory_mb()
        rows.append({field: row[field] for field in P3_FIELDS})
    return rows


def _append_rows(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> pd.DataFrame:
    new = pd.DataFrame(rows, columns=fields)
    if path.exists():
        existing = pd.read_csv(path)
        if list(existing.columns) != fields:
            raise RuntimeError(f"result schema changed: {path}")
        known = set(existing.run_id.astype(str))
        new = new[~new.run_id.astype(str).isin(known)]
        frame = pd.concat([existing, new], ignore_index=True)
    else:
        frame = new
    atomic_write_csv(path, frame)
    return frame


def _run_parallel_batches(
    jobs: list[tuple[Any, ...]], worker, path: Path, fields: list[str], max_workers: int
) -> pd.DataFrame:
    if jobs:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker, *job) for job in jobs]
            for future in as_completed(futures):
                _append_rows(path, future.result(), fields)
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=fields)


def _set_worker_threads(config: dict[str, Any]) -> None:
    threads = str(config["execution"]["worker_blas_threads"])
    os.environ["OMP_NUM_THREADS"] = threads
    os.environ["OPENBLAS_NUM_THREADS"] = threads
    os.environ["MKL_NUM_THREADS"] = threads


def _select_p2(frame: pd.DataFrame) -> pd.DataFrame:
    eligible = frame[
        frame.execution_status.isin(VALID_SCIENTIFIC_STATUSES)
        & np.isfinite(frame.objective_final)
    ].copy()
    return (
        eligible.sort_values(
            ["task_id", "objective_final", "optimizer_seed"], kind="stable"
        )
        .groupby("task_id", as_index=False, sort=False)
        .first()
    )


def run_discovery_only_preflight() -> dict[str, Any]:
    """Exercise the final p2/p3 path on two already-consumed discovery tasks only."""
    config = load_config(CONFIG_PATH)
    manifest = json.loads(
        (PROJECT_ROOT / config["discovery_manifest"]).read_text(encoding="utf-8")
    )
    characterization = (
        pd.read_csv(PROJECT_ROOT / config["characterization"])
        .set_index("task_id")
        .to_dict(orient="index")
    )
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    task_ids = list(config["preflight"]["task_ids"])
    if any(task_id not in task_lookup for task_id in task_ids):
        raise RuntimeError("preflight task must come from discovery manifest")
    config_hash = sha256_file(CONFIG_PATH)
    namespace = "phase2-discovery-preflight"
    p2_path = RESULT_ROOT / "preflight" / "p2_initialization_runs.csv"
    p3_path = RESULT_ROOT / "preflight" / "p3_objective_results.csv"
    known_p2 = set(pd.read_csv(p2_path).run_id.astype(str)) if p2_path.exists() else set()
    jobs = []
    for task_id in task_ids:
        seeds = [
            int(seed)
            for seed in config["preflight"]["p2_seeds"]
            if _p2_run_id(task_id, int(seed), config_hash, namespace) not in known_p2
        ]
        if seeds:
            task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
            jobs.append(
                (
                    task.to_dict(),
                    characterization[task_id],
                    config,
                    config_hash,
                    namespace,
                    seeds,
                )
            )
    _set_worker_threads(config)
    p2 = _run_parallel_batches(
        jobs,
        _run_p2_task_batch,
        p2_path,
        P2_FIELDS,
        int(config["execution"]["max_workers"]),
    )
    expected_p2 = len(task_ids) * len(config["preflight"]["p2_seeds"])
    if len(p2) != expected_p2 or not p2.execution_status.isin(VALID_SCIENTIFIC_STATUSES).all():
        write_json(PREFLIGHT_SUMMARY_PATH, {"status": "FAILED_STOP", "stage": "p2"})
        raise RuntimeError("discovery-only p2 preflight failed; STOP")
    selected = _select_p2(p2).set_index("task_id")
    known_p3 = set(pd.read_csv(p3_path).run_id.astype(str)) if p3_path.exists() else set()
    p3_jobs = []
    for task_id in task_ids:
        objectives = [
            objective_id
            for objective_id in config["preflight"]["p3_objective_ids"]
            if _p3_run_id(task_id, objective_id, config_hash, namespace) not in known_p3
        ]
        if objectives:
            task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
            p3_jobs.append(
                (
                    task.to_dict(),
                    characterization[task_id],
                    selected.loc[task_id].to_dict(),
                    config,
                    config_hash,
                    namespace,
                    objectives,
                )
            )
    p3 = _run_parallel_batches(
        p3_jobs,
        _run_p3_task_batch,
        p3_path,
        P3_FIELDS,
        int(config["execution"]["max_workers"]),
    )
    expected_p3 = len(task_ids) * len(config["preflight"]["p3_objective_ids"])
    required = p3.execution_status.isin(VALID_SCIENTIFIC_STATUSES)
    accounting = (
        (p3.nfev <= p3.eval_budget)
        & (p3.total_objective_evaluations == p3.tracked_optimizer_evaluations + 1)
    )
    common = p3.groupby("task_id").initial_parameters.nunique().eq(1)
    if len(p3) != expected_p3 or not required.all() or not accounting.all() or not common.all():
        write_json(PREFLIGHT_SUMMARY_PATH, {"status": "FAILED_STOP", "stage": "p3"})
        raise RuntimeError("discovery-only p3 preflight failed; STOP")
    summary = {
        "status": "PASSED",
        "source": "discovery tasks only; no held-out optimization",
        "task_ids": task_ids,
        "p2_rows": len(p2),
        "p3_rows": len(p3),
        "matched_budget_pass": bool(accounting.all()),
        "common_initialization_pass": bool(common.all()),
        "all_energy_separation_pass": bool(p3.strict_energy_class_separation.all()),
        "all_penalty_bounds_pass": bool(p3.penalty_bound_pass.all()),
    }
    write_json(PREFLIGHT_SUMMARY_PATH, summary)
    return summary


def run_energy_separation_audit() -> pd.DataFrame:
    config, manifest, characterization = load_frozen_phase2()
    rows = []
    for item in manifest["tasks"]:
        task = read_task(PROJECT_ROOT / item["task_path"])
        context = build_objective_context(task)
        feasible = context["feasible_mask"]
        max_feasible = float(context["energy"][feasible].max())
        min_infeasible = float(context["energy"][~feasible].min())
        rows.append(
            {
                "task_id": task.task_id,
                "base_graph_id": task.graph.graph_id,
                "base_instance_id": task.base_instance_id,
                "size_stratum": task.size_stratum,
                "stress_level": task.tightness_level,
                "dilution_score": float(characterization[task.task_id]["dilution_score"]),
                "max_feasible_energy": max_feasible,
                "min_infeasible_energy": min_infeasible,
                "energy_class_gap": min_infeasible - max_feasible,
                "strict_energy_class_separation": bool(min_infeasible > max_feasible),
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(ENERGY_AUDIT_PATH, frame)
    if len(frame) != 84 or not frame.strict_energy_class_separation.all():
        raise RuntimeError("held-out energy-separation audit failed; STOP")
    return frame


def run_formal_p2_preparation() -> pd.DataFrame:
    config, manifest, characterization = load_frozen_phase2()
    power = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    if power["power_gate"] != "PASS_CONFIRMATORY":
        raise RuntimeError("UNDERPOWERED_FOR_CONFIRMATORY: user authorization required")
    if not ENERGY_AUDIT_PATH.exists() or not pd.read_csv(
        ENERGY_AUDIT_PATH
    ).strict_energy_class_separation.all():
        raise RuntimeError("84-task energy audit must pass before formal optimization")
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    config_hash = sha256_file(CONFIG_PATH)
    namespace = "phase2-heldout-formal"
    known = set(pd.read_csv(P2_RESULTS_PATH).run_id.astype(str)) if P2_RESULTS_PATH.exists() else set()
    jobs = []
    for task_id, item in task_lookup.items():
        seeds = [
            int(seed)
            for seed in config["p2_preparation"]["optimizer_seeds"]
            if _p2_run_id(task_id, int(seed), config_hash, namespace) not in known
        ]
        if seeds:
            task = read_task(PROJECT_ROOT / item["task_path"])
            jobs.append(
                (
                    task.to_dict(),
                    characterization[task_id],
                    config,
                    config_hash,
                    namespace,
                    seeds,
                )
            )
    _set_worker_threads(config)
    frame = _run_parallel_batches(
        jobs,
        _run_p2_task_batch,
        P2_RESULTS_PATH,
        P2_FIELDS,
        int(config["execution"]["max_workers"]),
    )
    if len(frame) != int(config["p2_preparation"]["planned_runs"]):
        raise RuntimeError("formal p2 denominator mismatch")
    selected = _select_p2(frame)
    frame["selected_for_p3"] = frame.run_id.isin(set(selected.run_id))
    frame = frame.sort_values(
        ["size_stratum", "base_instance_id", "stress_level", "optimizer_seed"],
        kind="stable",
    )
    atomic_write_csv(P2_RESULTS_PATH, frame)
    verify_predecessor_immutability()
    return frame


def run_formal_p3_comparison() -> pd.DataFrame:
    config, manifest, characterization = load_frozen_phase2()
    if not P2_RESULTS_PATH.exists():
        raise RuntimeError("formal p2 preparation must complete before p3")
    p2 = pd.read_csv(P2_RESULTS_PATH)
    if len(p2) != int(config["p2_preparation"]["planned_runs"]):
        raise RuntimeError("formal p2 denominator incomplete")
    selected = _select_p2(p2).set_index("task_id")
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    config_hash = sha256_file(CONFIG_PATH)
    namespace = "phase2-heldout-formal"
    known = set(pd.read_csv(P3_RESULTS_PATH).run_id.astype(str)) if P3_RESULTS_PATH.exists() else set()
    jobs = []
    for task_id, item in task_lookup.items():
        objectives = [
            objective_id
            for objective_id in config["p3_comparison"]["objective_ids"]
            if _p3_run_id(task_id, objective_id, config_hash, namespace) not in known
        ]
        if objectives:
            task = read_task(PROJECT_ROOT / item["task_path"])
            p2_row = selected.loc[task_id].to_dict() if task_id in selected.index else None
            jobs.append(
                (
                    task.to_dict(),
                    characterization[task_id],
                    p2_row,
                    config,
                    config_hash,
                    namespace,
                    objectives,
                )
            )
    _set_worker_threads(config)
    frame = _run_parallel_batches(
        jobs,
        _run_p3_task_batch,
        P3_RESULTS_PATH,
        P3_FIELDS,
        int(config["execution"]["max_workers"]),
    )
    if len(frame) != int(config["p3_comparison"]["planned_runs"]):
        raise RuntimeError("formal p3 denominator mismatch")
    eligibility = frame.execution_status.isin(VALID_SCIENTIFIC_STATUSES) & np.isfinite(
        frame.log_feasibility_gain
    )
    task_eligible = eligibility.groupby(frame.task_id).transform("all")
    frame["paired_analysis_eligible"] = task_eligible
    frame = frame.sort_values(
        ["size_stratum", "base_instance_id", "stress_level", "objective_id"],
        kind="stable",
    )
    atomic_write_csv(P3_RESULTS_PATH, frame)
    common = frame.groupby("task_id").initial_parameters.nunique(dropna=False)
    if not common.eq(1).all():
        raise RuntimeError("common O0/O2/O3 initialization contract failed")
    budget = frame[frame.execution_status != "RESOURCE_CENSORED"]
    if not (budget.eval_budget == int(config["p3_comparison"]["eval_budget"])).all():
        raise RuntimeError("matched p3 budget identity failed")
    verify_predecessor_immutability()
    return frame
