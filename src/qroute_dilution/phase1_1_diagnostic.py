"""Immutable, resume-safe Phase 1.1 optimization-attribution diagnostics."""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .diagnostic_optimizer import optimize_from_initial
from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json
from .metrics import probability_metrics
from .models import Task
from .phase1_pilot import _energy_arrays, sha256_file
from .qaoa import apply_cost_layer, apply_x_mixer, simulate_qaoa


CONFIG_PATH = PROJECT_ROOT / "configs" / "phase1_1_optimization_diagnostic.yaml"
PILOT_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase1_pilot_v1.json"
PILOT_RESULTS = PROJECT_ROOT / "results" / "phase1_pilot_v1" / "master_seed_level_results.csv"
V2_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase0_v2_dilution_stress.json"
CHARACTERIZATION = (
    PROJECT_ROOT / "results" / "phase0_v2_dilution_stress" / "task_characterization.csv"
)
RESULT_ROOT = PROJECT_ROOT / "results" / "phase1_1_optimization_diagnostic"
IDENTITY_PATH = RESULT_ROOT / "execution_identity.json"
IMMUTABLE_HASH_PATH = RESULT_ROOT / "immutable_evidence_sha256.json"
NESTED_PATH = RESULT_ROOT / "nested_ansatz_identity.csv"
RANDOM_GAP_PATH = RESULT_ROOT / "p3_random_vs_embedded.csv"
CONTINUATION_PATH = RESULT_ROOT / "p3_continuation_seed_level.csv"
BUDGET_PATH = RESULT_ROOT / "p3_budget_scaling.csv"
CONTROL_PATH = RESULT_ROOT / "optimizer_control.csv"
ENERGY_SEPARATION_PATH = RESULT_ROOT / "energy_class_separation.csv"
DECOMPOSITION_PATH = RESULT_ROOT / "objective_decomposition.csv"
SLICE_PATH = RESULT_ROOT / "new_layer_response_slices.csv"


OPTIMIZATION_FIELDS = [
    "run_id",
    "task_id",
    "base_graph_id",
    "base_instance_id",
    "size_stratum",
    "stress_level",
    "n_edges",
    "feasible_state_fraction",
    "dilution_score",
    "arm",
    "optimizer",
    "source_p2_seed",
    "eval_budget",
    "budget_multiplier",
    "reused_from_continuation",
    "initial_parameters",
    "terminal_parameters",
    "best_evaluated_parameters",
    "objective_start",
    "objective_final",
    "terminal_objective",
    "best_evaluated_objective",
    "objective_improvement",
    "best_evaluated_objective_improvement",
    "p_feas_start",
    "p_feas_final",
    "p_feas_best_evaluated",
    "p_opt_start",
    "p_opt_final",
    "p_opt_best_evaluated",
    "p_opt_given_feasible_start",
    "p_opt_given_feasible_final",
    "p_opt_given_feasible_best_evaluated",
    "G_feas_start",
    "G_feas_final",
    "G_feas_best_evaluated",
    "state_norm_start",
    "state_norm_final",
    "state_norm_best_evaluated",
    "expected_routing_component",
    "expected_flow_penalty",
    "expected_resource_penalty",
    "expected_total_penalty",
    "component_sum",
    "component_sum_error",
    "mass_valid_flow_resource_feasible",
    "mass_flow_invalid_resource_feasible",
    "mass_flow_valid_resource_violating",
    "mass_both_flow_and_resource_violating",
    "mass_flow_invalid",
    "mass_resource_violating",
    "mass_category_sum",
    "classification",
    "optimizer_nfev",
    "tracked_optimizer_evaluations",
    "diagnostic_start_evaluations",
    "total_objective_evaluations",
    "optimizer_status",
    "optimizer_message",
    "scipy_success",
    "numerically_valid",
    "runtime_s",
    "peak_memory_mb",
    "execution_status",
    "failure_reason",
    "config_sha256",
]


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / 1024.0 if value < 10**9 else value / (1024.0**2))


def embed_p2_in_p3(parameters: np.ndarray) -> np.ndarray:
    """Embed [gamma1,gamma2,beta1,beta2] as [g1,g2,0,b1,b2,0]."""
    parameters = np.asarray(parameters, dtype=np.float64)
    if parameters.shape != (4,):
        raise ValueError("p=2 parameters must have shape (4,) in gammas-then-betas order")
    return np.asarray(
        [parameters[0], parameters[1], 0.0, parameters[2], parameters[3], 0.0],
        dtype=np.float64,
    )


def _parse_parameters(value: str) -> np.ndarray:
    return np.asarray(json.loads(value), dtype=np.float64)


def _task_sets(task: Task) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return (
        tuple(route.bitstring_int for route in task.feasible_routes),
        tuple(route.bitstring_int for route in task.optimal_routes),
    )


def build_evaluation_context(task: Task) -> dict[str, Any]:
    components, raw, normalized, flow, resource_penalty = _energy_arrays(task, 172.0)
    resource_excess = np.maximum(0.0, components.resource_total - task.budget)
    flow_invalid = components.flow_penalty_raw > 0.0
    resource_violating = resource_excess > 0.0
    return {
        "components": components,
        "raw_energy": raw,
        "energy": normalized,
        "routing_component": components.routing_cost / 172.0,
        "flow_penalty": flow,
        "resource_penalty": resource_penalty,
        "flow_invalid": flow_invalid,
        "resource_violating": resource_violating,
    }


def evaluate_parameters(
    task: Task,
    context: dict[str, Any],
    parameters: np.ndarray,
    depth: int,
    *,
    return_state: bool = False,
) -> dict[str, Any]:
    state = simulate_qaoa(np.asarray(parameters, dtype=np.float64), context["energy"], depth)
    probabilities = np.abs(state) ** 2
    feasible, optimal = _task_sets(task)
    phi = len(feasible) / len(probabilities)
    metrics = probability_metrics(probabilities, feasible, optimal, phi)
    flow_invalid = context["flow_invalid"]
    resource_violating = context["resource_violating"]
    valid_feasible = (~flow_invalid) & (~resource_violating)
    flow_only = flow_invalid & (~resource_violating)
    resource_only = (~flow_invalid) & resource_violating
    both = flow_invalid & resource_violating
    routing_expectation = float(np.dot(probabilities, context["routing_component"]))
    flow_expectation = float(np.dot(probabilities, context["flow_penalty"]))
    resource_expectation = float(np.dot(probabilities, context["resource_penalty"]))
    objective = float(np.dot(probabilities, context["energy"]))
    result: dict[str, Any] = {
        "objective": objective,
        "p_feas": metrics["p_feas"],
        "p_opt": metrics["p_opt"],
        "p_opt_given_feasible": metrics["p_opt_given_feasible"],
        "G_feas": metrics["log_feasibility_gain"],
        "state_norm": float(probabilities.sum()),
        "expected_routing_component": routing_expectation,
        "expected_flow_penalty": flow_expectation,
        "expected_resource_penalty": resource_expectation,
        "expected_total_penalty": flow_expectation + resource_expectation,
        "component_sum": routing_expectation + flow_expectation + resource_expectation,
        "component_sum_error": routing_expectation
        + flow_expectation
        + resource_expectation
        - objective,
        "mass_valid_flow_resource_feasible": float(probabilities[valid_feasible].sum()),
        "mass_flow_invalid_resource_feasible": float(probabilities[flow_only].sum()),
        "mass_flow_valid_resource_violating": float(probabilities[resource_only].sum()),
        "mass_both_flow_and_resource_violating": float(probabilities[both].sum()),
        "mass_flow_invalid": float(probabilities[flow_invalid].sum()),
        "mass_resource_violating": float(probabilities[resource_violating].sum()),
        "mass_category_sum": float(
            probabilities[valid_feasible].sum()
            + probabilities[flow_only].sum()
            + probabilities[resource_only].sum()
            + probabilities[both].sum()
        ),
    }
    if return_state:
        result["state"] = state
        result["probabilities"] = probabilities
    return result


def energy_class_gap(energies: np.ndarray, feasible_states: tuple[int, ...]) -> dict[str, Any]:
    energies = np.asarray(energies, dtype=np.float64)
    feasible_mask = np.zeros(len(energies), dtype=bool)
    feasible_mask[np.asarray(feasible_states, dtype=np.int64)] = True
    if not feasible_mask.any():
        return {
            "max_feasible_energy": math.nan,
            "min_infeasible_energy": float(energies.min()),
            "feasible_infeasible_energy_gap": math.nan,
            "complete_energy_separation": False,
        }
    maximum_feasible = float(energies[feasible_mask].max())
    minimum_infeasible = float(energies[~feasible_mask].min())
    return {
        "max_feasible_energy": maximum_feasible,
        "min_infeasible_energy": minimum_infeasible,
        "feasible_infeasible_energy_gap": minimum_infeasible - maximum_feasible,
        "complete_energy_separation": bool(minimum_infeasible > maximum_feasible),
    }


def _immutable_files(config: dict[str, Any]) -> list[Path]:
    files: list[Path] = []
    for relative in config["immutable_paths"]:
        path = PROJECT_ROOT / relative
        if path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
        elif path.is_file():
            files.append(path)
        else:
            raise FileNotFoundError(f"immutable evidence path missing: {relative}")
    return sorted(set(files), key=lambda path: str(path.relative_to(PROJECT_ROOT)))


def freeze_diagnostic_identity() -> dict[str, Any]:
    config = load_config(CONFIG_PATH)
    if config["pre_run_git_sha"] != "96d6dc6b2d9d14d9df7cb6fd3a54a8364ba435f9":
        raise RuntimeError("unexpected frozen pilot commit")
    hashes = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path) for path in _immutable_files(config)
    }
    write_json(
        IMMUTABLE_HASH_PATH,
        {
            "frozen_commit": config["pre_run_git_sha"],
            "file_count": len(hashes),
            "files": hashes,
        },
    )
    manifest = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    identity = {
        "pre_run_git_sha": config["pre_run_git_sha"],
        "config_sha256": sha256_file(CONFIG_PATH),
        "pilot_manifest_sha256": sha256_file(PILOT_MANIFEST),
        "pilot_master_results_sha256": sha256_file(PILOT_RESULTS),
        "immutable_evidence_hash_manifest": str(IMMUTABLE_HASH_PATH.relative_to(PROJECT_ROOT)),
        "immutable_file_count": len(hashes),
        "task_count": manifest["task_count"],
        "p2_seed_rows": config["expected_p2_seed_rows"],
        "original_p3_seed_rows": config["expected_original_p3_seed_rows"],
        "planned_new_optimization_runs": {
            "continuation_b1": 168,
            "budget_b2_b4": 112,
            "nelder_mead_b1": 56,
            "total": 336,
        },
    }
    write_json(IDENTITY_PATH, identity)
    return identity


def verify_immutable_evidence() -> dict[str, str]:
    frozen = json.loads(IMMUTABLE_HASH_PATH.read_text(encoding="utf-8"))
    observed = {
        path: sha256_file(PROJECT_ROOT / path) for path in sorted(frozen["files"])
    }
    if observed != frozen["files"]:
        changed = [path for path in observed if observed[path] != frozen["files"].get(path)]
        raise RuntimeError(f"immutable evidence changed: {changed}")
    return observed


def load_diagnostic_inputs() -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame, dict[str, dict[str, Any]]]:
    verify_immutable_evidence()
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    if sha256_file(CONFIG_PATH) != identity["config_sha256"]:
        raise RuntimeError("Phase 1.1 config changed after freeze")
    if sha256_file(PILOT_MANIFEST) != identity["pilot_manifest_sha256"]:
        raise RuntimeError("pilot manifest changed after freeze")
    if sha256_file(PILOT_RESULTS) != identity["pilot_master_results_sha256"]:
        raise RuntimeError("pilot master results changed after freeze")
    config = load_config(CONFIG_PATH)
    manifest = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    pilot = pd.read_csv(PILOT_RESULTS)
    characterization = pd.read_csv(CHARACTERIZATION).set_index("task_id").to_dict(orient="index")
    if manifest["task_count"] != 56:
        raise RuntimeError("pilot task denominator changed")
    return config, manifest, pilot, characterization


def _nested_task_batch(
    task_payload: dict[str, Any],
    p2_rows: list[dict[str, Any]],
    p3_lookup: dict[int, dict[str, Any]],
    characterization: dict[str, Any],
    tolerance: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    task = Task.from_dict(task_payload)
    context = build_evaluation_context(task)
    nested_rows = []
    gap_rows = []
    for p2_row in p2_rows:
        seed = int(p2_row["optimizer_seed"])
        p2_parameters = _parse_parameters(p2_row["optimized_parameters"])
        embedded = embed_p2_in_p3(p2_parameters)
        p2 = evaluate_parameters(task, context, p2_parameters, 2, return_state=True)
        p3_embedded = evaluate_parameters(task, context, embedded, 3, return_state=True)
        objective_difference = p3_embedded["objective"] - p2["objective"]
        p_feas_difference = p3_embedded["p_feas"] - p2["p_feas"]
        p_opt_difference = p3_embedded["p_opt"] - p2["p_opt"]
        probability_max_difference = float(
            np.max(np.abs(p3_embedded["probabilities"] - p2["probabilities"]))
        )
        state_max_difference = float(np.max(np.abs(p3_embedded["state"] - p2["state"])))
        passed = bool(
            abs(objective_difference) < tolerance
            and abs(p_feas_difference) < tolerance
            and abs(p_opt_difference) < tolerance
            and probability_max_difference < tolerance
            and state_max_difference < tolerance
        )
        common = {
            "task_id": task.task_id,
            "base_graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "stress_level": task.tightness_level,
            "n_edges": len(task.graph.edges),
            "optimizer_seed": seed,
            "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
            "dilution_score": float(characterization["dilution_score"]),
            "p2_parameters": json.dumps(p2_parameters.tolist()),
            "p2_embedded_p3_parameters": json.dumps(embedded.tolist()),
        }
        nested_rows.append(
            {
                **common,
                "p2_objective_recomputed": p2["objective"],
                "p3_embedded_objective": p3_embedded["objective"],
                "objective_difference": objective_difference,
                "p2_p_feas_recomputed": p2["p_feas"],
                "p3_embedded_p_feas": p3_embedded["p_feas"],
                "p_feas_difference": p_feas_difference,
                "p2_p_opt_recomputed": p2["p_opt"],
                "p3_embedded_p_opt": p3_embedded["p_opt"],
                "p_opt_difference": p_opt_difference,
                "p2_p_opt_given_feasible": p2["p_opt_given_feasible"],
                "p3_embedded_p_opt_given_feasible": p3_embedded["p_opt_given_feasible"],
                "p2_G_feas": p2["G_feas"],
                "p3_embedded_G_feas": p3_embedded["G_feas"],
                "state_max_abs_difference": state_max_difference,
                "probability_max_abs_difference": probability_max_difference,
                "p2_state_norm": p2["state_norm"],
                "p3_embedded_state_norm": p3_embedded["state_norm"],
                "identity_tolerance": tolerance,
                "identity_pass": passed,
            }
        )
        original_p3 = p3_lookup[seed]
        gap = float(original_p3["objective_final"]) - p3_embedded["objective"]
        gap_rows.append(
            {
                **common,
                "embedded_p2_objective": p3_embedded["objective"],
                "original_p3_objective": float(original_p3["objective_final"]),
                "p3_optimization_gap_vs_embedded_p2": gap,
                "original_p3_worse_than_embedded_p2": bool(gap > tolerance),
                "comparison_tolerance": tolerance,
                "embedded_p2_p_feas": p3_embedded["p_feas"],
                "original_p3_p_feas": float(original_p3["p_feas"]),
                "embedded_p2_p_opt": p3_embedded["p_opt"],
                "original_p3_p_opt": float(original_p3["p_opt"]),
                "embedded_p2_G_feas": p3_embedded["G_feas"],
                "original_p3_G_feas": float(original_p3["log_feasibility_gain"]),
            }
        )
    return nested_rows, gap_rows


def run_nested_identity() -> tuple[pd.DataFrame, pd.DataFrame]:
    config, manifest, pilot, characterization = load_diagnostic_inputs()
    p2 = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 2)]
    p3 = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 3)]
    if len(p2) != 168 or len(p3) != 168:
        raise RuntimeError("unexpected p2/p3 pilot denominator")
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    os.environ["OMP_NUM_THREADS"] = str(config["execution"]["worker_blas_threads"])
    os.environ["OPENBLAS_NUM_THREADS"] = str(config["execution"]["worker_blas_threads"])
    os.environ["MKL_NUM_THREADS"] = str(config["execution"]["worker_blas_threads"])
    nested_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=int(config["execution"]["max_workers"])) as executor:
        futures = []
        for task_id, p2_group in p2.groupby("task_id", sort=False):
            p3_lookup = {
                int(row.optimizer_seed): row._asdict()
                for row in p3[p3.task_id == task_id].itertuples(index=False)
            }
            task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
            futures.append(
                executor.submit(
                    _nested_task_batch,
                    task.to_dict(),
                    p2_group.to_dict(orient="records"),
                    p3_lookup,
                    characterization[task_id],
                    float(config["identity_tolerance"]),
                )
            )
        for future in as_completed(futures):
            nested, gaps = future.result()
            nested_rows.extend(nested)
            gap_rows.extend(gaps)
    nested = pd.DataFrame(nested_rows).sort_values(["size_stratum", "base_instance_id", "stress_level", "optimizer_seed"])
    gaps = pd.DataFrame(gap_rows).sort_values(["size_stratum", "base_instance_id", "stress_level", "optimizer_seed"])
    atomic_write_csv(NESTED_PATH, nested)
    atomic_write_csv(RANDOM_GAP_PATH, gaps)
    if len(nested) != 168 or not nested.identity_pass.all():
        raise RuntimeError("nested ansatz identity failed; Phase 1.1 must stop")
    return nested, gaps


def _diagnostic_run_id(
    task_id: str, arm: str, seed: int, budget: int, optimizer: str, config_hash: str
) -> str:
    payload = f"phase1.1|{task_id}|{arm}|{seed}|{budget}|{optimizer}|{config_hash}"
    return "diag-run-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _blank_optimization_row() -> dict[str, Any]:
    return {field: math.nan for field in OPTIMIZATION_FIELDS}


def _copy_evaluation(row: dict[str, Any], evaluation: dict[str, Any], suffix: str) -> None:
    row[f"p_feas_{suffix}"] = evaluation["p_feas"]
    row[f"p_opt_{suffix}"] = evaluation["p_opt"]
    row[f"p_opt_given_feasible_{suffix}"] = evaluation["p_opt_given_feasible"]
    row[f"G_feas_{suffix}"] = evaluation["G_feas"]
    row[f"state_norm_{suffix}"] = evaluation["state_norm"]


def classify_continuation(
    objective_start: float,
    objective_final: float,
    gain_start: float,
    gain_final: float,
    tolerance: float,
) -> str:
    if objective_final > objective_start + tolerance:
        return "OPTIMIZER_REGRESSION"
    if abs(objective_final - objective_start) <= tolerance:
        return "NO_MEANINGFUL_OBJECTIVE_GAIN"
    if gain_final > gain_start + tolerance:
        return "OBJECTIVE_AND_FEASIBILITY_IMPROVE"
    if gain_final < gain_start - tolerance:
        return "OBJECTIVE_IMPROVES_FEASIBILITY_WORSENS"
    return "OBJECTIVE_IMPROVES_FEASIBILITY_UNCHANGED"


def _run_from_p2(
    task: Task,
    p2_row: dict[str, Any],
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
    *,
    arm: str,
    method: str,
    eval_budget: int,
    budget_multiplier: int,
    timeout_s: float,
) -> dict[str, Any]:
    row = _blank_optimization_row()
    seed = int(p2_row["optimizer_seed"])
    row.update(
        {
            "run_id": _diagnostic_run_id(task.task_id, arm, seed, eval_budget, method, config_hash),
            "task_id": task.task_id,
            "base_graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "stress_level": task.tightness_level,
            "n_edges": len(task.graph.edges),
            "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
            "dilution_score": float(characterization["dilution_score"]),
            "arm": arm,
            "optimizer": method,
            "source_p2_seed": seed,
            "eval_budget": int(eval_budget),
            "budget_multiplier": int(budget_multiplier),
            "reused_from_continuation": False,
            "diagnostic_start_evaluations": 1,
            "config_sha256": config_hash,
            "execution_status": "SUCCESS",
            "failure_reason": "",
        }
    )
    try:
        context = build_evaluation_context(task)
        initial = embed_p2_in_p3(_parse_parameters(p2_row["optimized_parameters"]))
        start = evaluate_parameters(task, context, initial, 3)
        control = config["optimizer_control"]
        continuation = config["continuation"]
        result = optimize_from_initial(
            context["energy"],
            3,
            initial,
            method=method,
            eval_budget=eval_budget,
            timeout_s=timeout_s,
            cobyla_rhobeg=float(continuation["cobyla_rhobeg"]),
            cobyla_catol=float(continuation["cobyla_catol"]),
            nelder_mead_xatol=float(control["xatol"]),
            nelder_mead_fatol=float(control["fatol"]),
            nelder_mead_adaptive=bool(control["adaptive"]),
        )
        terminal = evaluate_parameters(task, context, result.terminal_parameters, 3)
        best = evaluate_parameters(task, context, result.best_evaluated_parameters, 3)
        _copy_evaluation(row, start, "start")
        _copy_evaluation(row, terminal, "final")
        _copy_evaluation(row, best, "best_evaluated")
        row.update(
            {
                "initial_parameters": json.dumps(initial.tolist()),
                "terminal_parameters": json.dumps(result.terminal_parameters.tolist()),
                "best_evaluated_parameters": json.dumps(
                    result.best_evaluated_parameters.tolist()
                ),
                "objective_start": result.objective_start,
                "objective_final": result.terminal_objective,
                "terminal_objective": result.terminal_objective,
                "best_evaluated_objective": result.best_evaluated_objective,
                "objective_improvement": result.objective_start - result.terminal_objective,
                "best_evaluated_objective_improvement": result.objective_start
                - result.best_evaluated_objective,
                "classification": classify_continuation(
                    result.objective_start,
                    result.terminal_objective,
                    start["G_feas"],
                    terminal["G_feas"],
                    float(config["comparison_tolerance"]),
                ),
                "optimizer_nfev": result.optimizer_nfev,
                "tracked_optimizer_evaluations": result.tracked_optimizer_evaluations,
                "total_objective_evaluations": result.total_objective_evaluations,
                "optimizer_status": result.status,
                "optimizer_message": result.message,
                "scipy_success": result.scipy_success,
                "numerically_valid": result.numerically_valid,
                "runtime_s": result.runtime_s,
            }
        )
        for field in (
            "expected_routing_component",
            "expected_flow_penalty",
            "expected_resource_penalty",
            "expected_total_penalty",
            "component_sum",
            "component_sum_error",
            "mass_valid_flow_resource_feasible",
            "mass_flow_invalid_resource_feasible",
            "mass_flow_valid_resource_violating",
            "mass_both_flow_and_resource_violating",
            "mass_flow_invalid",
            "mass_resource_violating",
            "mass_category_sum",
        ):
            row[field] = terminal[field]
        if not result.numerically_valid:
            row["execution_status"] = "NUMERICAL_FAILURE"
            row["failure_reason"] = "non-finite terminal or best-evaluated result"
    except MemoryError as exc:
        row["execution_status"] = "OOM"
        row["failure_reason"] = f"MemoryError: {exc}"
    except Exception as exc:
        name = type(exc).__name__
        row["execution_status"] = "TIMEOUT" if name == "OptimizationTimeout" else "OPTIMIZER_FAILURE"
        row["failure_reason"] = f"{name}: {exc}"
    row["peak_memory_mb"] = _peak_memory_mb()
    return {field: row[field] for field in OPTIMIZATION_FIELDS}


def append_optimization_rows(path: Path, rows: list[dict[str, Any]]) -> pd.DataFrame:
    new = pd.DataFrame(rows, columns=OPTIMIZATION_FIELDS)
    if path.exists():
        existing = pd.read_csv(path)
        if set(existing.columns) != set(OPTIMIZATION_FIELDS):
            raise RuntimeError(f"schema mismatch in {path}")
        known = set(existing.run_id.astype(str))
        new = new[~new.run_id.astype(str).isin(known)]
        frame = pd.concat([existing[OPTIMIZATION_FIELDS], new], ignore_index=True)
    else:
        frame = new
    atomic_write_csv(path, frame)
    return frame


def _continuation_task_batch(
    task_payload: dict[str, Any],
    p2_rows: list[dict[str, Any]],
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    continuation = config["continuation"]
    return [
        _run_from_p2(
            task,
            row,
            characterization,
            config,
            config_hash,
            arm="P3_CONTINUATION_B1",
            method="COBYLA",
            eval_budget=int(continuation["eval_budget"]),
            budget_multiplier=1,
            timeout_s=float(continuation["timeout_s"]),
        )
        for row in p2_rows
    ]


def _run_parallel_task_batches(
    jobs: list[tuple[Any, ...]], worker, output_path: Path, max_workers: int
) -> pd.DataFrame:
    known: set[str] = set()
    frame = pd.DataFrame(columns=OPTIMIZATION_FIELDS)
    if output_path.exists():
        frame = pd.read_csv(output_path)
        known = set(frame.run_id.astype(str))
    pending_jobs = []
    for job in jobs:
        expected_ids = job[-1] if isinstance(job[-1], list) else []
        payload = job[:-1] if expected_ids else job
        if expected_ids and all(run_id in known for run_id in expected_ids):
            continue
        pending_jobs.append(payload)
    if pending_jobs:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker, *job) for job in pending_jobs]
            for future in as_completed(futures):
                frame = append_optimization_rows(output_path, future.result())
    return pd.read_csv(output_path) if output_path.exists() else frame


def run_continuation() -> pd.DataFrame:
    config, manifest, pilot, characterization = load_diagnostic_inputs()
    if not NESTED_PATH.exists() or not pd.read_csv(NESTED_PATH).identity_pass.all():
        raise RuntimeError("nested identity must pass before continuation")
    p2 = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 2)]
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    config_hash = sha256_file(CONFIG_PATH)
    jobs = []
    for task_id, group in p2.groupby("task_id", sort=False):
        task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
        rows = group.to_dict(orient="records")
        expected = [
            _diagnostic_run_id(
                task_id,
                "P3_CONTINUATION_B1",
                int(row["optimizer_seed"]),
                int(config["continuation"]["eval_budget"]),
                "COBYLA",
                config_hash,
            )
            for row in rows
        ]
        jobs.append((task.to_dict(), rows, characterization[task_id], config, config_hash, expected))
    return _run_parallel_task_batches(
        jobs,
        _continuation_task_batch,
        CONTINUATION_PATH,
        int(config["execution"]["max_workers"]),
    )


def objective_best_p2_rows(pilot: pd.DataFrame) -> pd.DataFrame:
    p2 = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 2)].copy()
    return p2.sort_values(["task_id", "objective_final", "optimizer_seed"], kind="stable").groupby(
        "task_id", as_index=False, sort=False
    ).first()


def _budget_task_batch(
    task_payload: dict[str, Any],
    p2_row: dict[str, Any],
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    timeout_lookup = config["budget_scaling"]["timeout_s_by_budget"]
    rows = []
    for multiplier, budget in zip(
        config["budget_scaling"]["multipliers"], config["budget_scaling"]["budgets"]
    ):
        if int(multiplier) == 1:
            continue
        rows.append(
            _run_from_p2(
                task,
                p2_row,
                characterization,
                config,
                config_hash,
                arm=f"P3_CONTINUATION_B{int(multiplier)}",
                method="COBYLA",
                eval_budget=int(budget),
                budget_multiplier=int(multiplier),
                timeout_s=float(timeout_lookup[int(budget)]),
            )
        )
    return rows


def run_budget_scaling() -> pd.DataFrame:
    config, manifest, pilot, characterization = load_diagnostic_inputs()
    continuation = pd.read_csv(CONTINUATION_PATH)
    if len(continuation) != 168:
        raise RuntimeError("complete continuation evidence required before budget scaling")
    selected = objective_best_p2_rows(pilot)
    config_hash = sha256_file(CONFIG_PATH)
    b1_rows = []
    for p2_row in selected.to_dict(orient="records"):
        source = continuation[
            (continuation.task_id == p2_row["task_id"])
            & (continuation.source_p2_seed == int(p2_row["optimizer_seed"]))
        ]
        if len(source) != 1:
            raise RuntimeError("missing unique B1 continuation row for selected p2 seed")
        row = source.iloc[0].to_dict()
        row["run_id"] = _diagnostic_run_id(
            p2_row["task_id"],
            "P3_CONTINUATION_B1_SELECTED",
            int(p2_row["optimizer_seed"]),
            120,
            "COBYLA",
            config_hash,
        )
        row["arm"] = "P3_CONTINUATION_B1_SELECTED"
        row["reused_from_continuation"] = True
        b1_rows.append({field: row[field] for field in OPTIMIZATION_FIELDS})
    append_optimization_rows(BUDGET_PATH, b1_rows)
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    jobs = []
    for p2_row in selected.to_dict(orient="records"):
        task_id = p2_row["task_id"]
        task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
        expected = [
            _diagnostic_run_id(
                task_id,
                f"P3_CONTINUATION_B{multiplier}",
                int(p2_row["optimizer_seed"]),
                int(budget),
                "COBYLA",
                config_hash,
            )
            for multiplier, budget in zip(
                config["budget_scaling"]["multipliers"], config["budget_scaling"]["budgets"]
            )
            if int(multiplier) != 1
        ]
        jobs.append((task.to_dict(), p2_row, characterization[task_id], config, config_hash, expected))
    frame = _run_parallel_task_batches(
        jobs,
        _budget_task_batch,
        BUDGET_PATH,
        int(config["execution"]["max_workers"]),
    )
    return frame.sort_values(["size_stratum", "base_instance_id", "stress_level", "budget_multiplier"])


def _control_task_batch(
    task_payload: dict[str, Any],
    p2_row: dict[str, Any],
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    control = config["optimizer_control"]
    return [
        _run_from_p2(
            task,
            p2_row,
            characterization,
            config,
            config_hash,
            arm="P3_NELDER_MEAD_B1",
            method="Nelder-Mead",
            eval_budget=int(control["eval_budget"]),
            budget_multiplier=1,
            timeout_s=float(control["timeout_s"]),
        )
    ]


def run_optimizer_control() -> pd.DataFrame:
    config, manifest, pilot, characterization = load_diagnostic_inputs()
    selected = objective_best_p2_rows(pilot)
    config_hash = sha256_file(CONFIG_PATH)
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    jobs = []
    for p2_row in selected.to_dict(orient="records"):
        task_id = p2_row["task_id"]
        task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
        expected = [
            _diagnostic_run_id(
                task_id,
                "P3_NELDER_MEAD_B1",
                int(p2_row["optimizer_seed"]),
                int(config["optimizer_control"]["eval_budget"]),
                "Nelder-Mead",
                config_hash,
            )
        ]
        jobs.append((task.to_dict(), p2_row, characterization[task_id], config, config_hash, expected))
    return _run_parallel_task_batches(
        jobs,
        _control_task_batch,
        CONTROL_PATH,
        int(config["execution"]["max_workers"]),
    )


def run_energy_separation() -> pd.DataFrame:
    config, pilot_manifest, _, characterization = load_diagnostic_inputs()
    full_manifest = json.loads(V2_MANIFEST.read_text(encoding="utf-8"))
    pilot_ids = {row["task_id"] for row in pilot_manifest["tasks"]}
    rows = []
    for task_row in full_manifest["tasks"]:
        task = read_task(PROJECT_ROOT / task_row["task_path"])
        context = build_evaluation_context(task)
        feasible, _ = _task_sets(task)
        gap = energy_class_gap(context["energy"], feasible)
        rows.append(
            {
                "task_id": task.task_id,
                "base_graph_id": task.graph.graph_id,
                "base_instance_id": task.base_instance_id,
                "size_stratum": task.size_stratum,
                "stress_level": task.tightness_level,
                "n_edges": len(task.graph.edges),
                "feasible_state_fraction": float(
                    characterization[task.task_id]["feasible_state_fraction"]
                ),
                "dilution_score": float(characterization[task.task_id]["dilution_score"]),
                "in_phase1_pilot": task.task_id in pilot_ids,
                **gap,
            }
        )
    frame = pd.DataFrame(rows).sort_values(
        ["size_stratum", "base_instance_id", "stress_level"], kind="stable"
    )
    atomic_write_csv(ENERGY_SEPARATION_PATH, frame)
    return frame


def _decomposition_record(
    task: Task,
    context: dict[str, Any],
    characterization: dict[str, Any],
    *,
    arm: str,
    seed: int,
    depth: int,
    parameters: np.ndarray,
    eval_budget: int | float,
) -> dict[str, Any]:
    evaluation = evaluate_parameters(task, context, parameters, depth)
    return {
        "task_id": task.task_id,
        "base_graph_id": task.graph.graph_id,
        "base_instance_id": task.base_instance_id,
        "size_stratum": task.size_stratum,
        "stress_level": task.tightness_level,
        "n_edges": len(task.graph.edges),
        "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
        "dilution_score": float(characterization["dilution_score"]),
        "arm": arm,
        "source_p2_seed": int(seed),
        "depth": int(depth),
        "eval_budget": eval_budget,
        "state_variant": "terminal",
        "parameters": json.dumps(np.asarray(parameters, dtype=float).tolist()),
        **{key: value for key, value in evaluation.items() if key not in {"state", "probabilities"}},
    }


def _decomposition_task_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    pilot_rows: list[dict[str, Any]],
    diagnostic_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    context = build_evaluation_context(task)
    rows = []
    for source in pilot_rows:
        rows.append(
            _decomposition_record(
                task,
                context,
                characterization,
                arm=f"P{int(source['depth'])}_RANDOM_ORIGINAL",
                seed=int(source["optimizer_seed"]),
                depth=int(source["depth"]),
                parameters=_parse_parameters(source["optimized_parameters"]),
                eval_budget=int(source["eval_budget"]),
            )
        )
    for source in diagnostic_rows:
        rows.append(
            _decomposition_record(
                task,
                context,
                characterization,
                arm=str(source["arm"]),
                seed=int(source["source_p2_seed"]),
                depth=3,
                parameters=_parse_parameters(source["terminal_parameters"]),
                eval_budget=int(source["eval_budget"]),
            )
        )
    return rows


def run_objective_decomposition() -> pd.DataFrame:
    config, manifest, pilot, characterization = load_diagnostic_inputs()
    continuation = pd.read_csv(CONTINUATION_PATH)
    budget = pd.read_csv(BUDGET_PATH)
    control = pd.read_csv(CONTROL_PATH)
    if len(continuation) != 168 or len(budget) != 168 or len(control) != 56:
        raise RuntimeError("optimization diagnostics incomplete before decomposition")
    pilot = pilot[(pilot.algorithm == "Penalty-X") & pilot.depth.isin([2, 3])]
    diagnostic = pd.concat(
        [
            continuation,
            budget[budget.budget_multiplier.isin([2, 4])],
            control,
        ],
        ignore_index=True,
    )
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=int(config["execution"]["max_workers"])) as executor:
        futures = []
        for task_id, task_row in task_lookup.items():
            task = read_task(PROJECT_ROOT / task_row["task_path"])
            futures.append(
                executor.submit(
                    _decomposition_task_batch,
                    task.to_dict(),
                    characterization[task_id],
                    pilot[pilot.task_id == task_id].to_dict(orient="records"),
                    diagnostic[diagnostic.task_id == task_id].to_dict(orient="records"),
                )
            )
        for future in as_completed(futures):
            rows.extend(future.result())
    frame = pd.DataFrame(rows).sort_values(
        ["size_stratum", "base_instance_id", "stress_level", "arm", "source_p2_seed"],
        kind="stable",
    )
    atomic_write_csv(DECOMPOSITION_PATH, frame)
    if len(frame) != 672:
        raise RuntimeError(f"objective decomposition denominator mismatch: {len(frame)}")
    if float(frame.component_sum_error.abs().max()) >= 1e-10:
        raise RuntimeError("objective component sum failed")
    if float((frame.mass_category_sum - 1.0).abs().max()) >= 1e-10:
        raise RuntimeError("probability-mass category sum failed")
    return frame


def select_response_slice_tasks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for size, bases in manifest["selected_base_graphs"].items():
        first_base = bases[0]
        candidates = [
            row for row in manifest["tasks"] if row["base_instance_id"] == first_base
        ]
        candidates.sort(key=lambda row: (int(row["actual_feasible_route_count"]), row["task_id"]))
        indices = sorted({0, (len(candidates) - 1) // 2, len(candidates) - 1})
        role_by_index = {
            0: "most_diluted",
            (len(candidates) - 1) // 2: "median_dilution",
            len(candidates) - 1: "least_diluted",
        }
        for index in indices:
            selected.append({**candidates[index], "representative_role": role_by_index[index]})
    return selected


def _slice_task_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    p2_row: dict[str, Any],
    p3_row: dict[str, Any],
    representative_role: str,
    gamma_values: list[float],
    beta_values: list[float],
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    context = build_evaluation_context(task)
    p2_parameters = _parse_parameters(p2_row["optimized_parameters"])
    p2_state = simulate_qaoa(p2_parameters, context["energy"], 2)
    feasible, optimal = _task_sets(task)
    phi = float(characterization["feasible_state_fraction"])
    rows = []
    n_qubits = len(task.graph.edges)
    for gamma_index, gamma in enumerate(gamma_values):
        costed = apply_cost_layer(p2_state, context["energy"], gamma)
        for beta_index, beta in enumerate(beta_values):
            state = apply_x_mixer(costed, beta, n_qubits)
            probabilities = np.abs(state) ** 2
            metrics = probability_metrics(probabilities, feasible, optimal, phi)
            rows.append(
                {
                    "slice_point_id": f"{task.task_id}-g{gamma_index:02d}-b{beta_index:02d}",
                    "task_id": task.task_id,
                    "base_graph_id": task.graph.graph_id,
                    "base_instance_id": task.base_instance_id,
                    "size_stratum": task.size_stratum,
                    "stress_level": task.tightness_level,
                    "representative_role": representative_role,
                    "dilution_score": float(characterization["dilution_score"]),
                    "source_p2_seed": int(p2_row["optimizer_seed"]),
                    "gamma3_index": gamma_index,
                    "beta3_index": beta_index,
                    "gamma3": float(gamma),
                    "beta3": float(beta),
                    "objective": float(np.dot(probabilities, context["energy"])),
                    "p_feas": metrics["p_feas"],
                    "p_opt": metrics["p_opt"],
                    "G_feas": metrics["log_feasibility_gain"],
                    "state_norm": float(probabilities.sum()),
                    "embedded_point": bool(abs(gamma) < 1e-15 and abs(beta) < 1e-15),
                    "original_p3_projected_gamma3": float(
                        _parse_parameters(p3_row["optimized_parameters"])[2]
                    ),
                    "original_p3_projected_beta3": float(
                        _parse_parameters(p3_row["optimized_parameters"])[5]
                    ),
                }
            )
    return rows


def _append_slice_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    new = pd.DataFrame(rows)
    if SLICE_PATH.exists():
        existing = pd.read_csv(SLICE_PATH)
        known = set(existing.slice_point_id.astype(str))
        new = new[~new.slice_point_id.astype(str).isin(known)]
        frame = pd.concat([existing, new], ignore_index=True)
    else:
        frame = new
    atomic_write_csv(SLICE_PATH, frame)
    return frame


def run_response_slices() -> pd.DataFrame:
    config, manifest, pilot, characterization = load_diagnostic_inputs()
    selection = select_response_slice_tasks(manifest)
    write_json(
        RESULT_ROOT / "response_slice_selection.json",
        {
            "selection_rule": config["response_slice"]["representative_rule"],
            "task_count": len(selection),
            "tasks": selection,
        },
    )
    grid_size = int(config["response_slice"]["grid_size"])
    gamma_values = np.linspace(*map(float, config["response_slice"]["gamma3_interval"]), grid_size)
    beta_values = np.linspace(*map(float, config["response_slice"]["beta3_interval"]), grid_size)
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    p2 = objective_best_p2_rows(pilot)
    p3 = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 3)].sort_values(
        ["task_id", "objective_final", "optimizer_seed"], kind="stable"
    ).groupby("task_id", as_index=False, sort=False).first()
    existing_ids: set[str] = set()
    if SLICE_PATH.exists():
        existing = pd.read_csv(SLICE_PATH)
        counts = existing.groupby("task_id").size()
        existing_ids = set(counts[counts == grid_size * grid_size].index)
    with ProcessPoolExecutor(
        max_workers=int(config["execution"]["response_slice_max_workers"])
    ) as executor:
        futures = []
        for selected in selection:
            task_id = selected["task_id"]
            if task_id in existing_ids:
                continue
            task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
            futures.append(
                executor.submit(
                    _slice_task_batch,
                    task.to_dict(),
                    characterization[task_id],
                    p2[p2.task_id == task_id].iloc[0].to_dict(),
                    p3[p3.task_id == task_id].iloc[0].to_dict(),
                    selected["representative_role"],
                    gamma_values.tolist(),
                    beta_values.tolist(),
                )
            )
        for future in as_completed(futures):
            _append_slice_rows(future.result())
    frame = pd.read_csv(SLICE_PATH)
    expected = len(selection) * grid_size * grid_size
    if len(frame) != expected:
        raise RuntimeError(f"response-slice denominator mismatch: {len(frame)} != {expected}")
    if float((frame.state_norm - 1.0).abs().max()) >= 1e-10:
        raise RuntimeError("response-slice norm check failed")
    return frame
