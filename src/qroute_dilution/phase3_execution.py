"""Resource-gated, resume-safe execution for the Phase-3 scaling matrix."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import resource
import socket
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import scipy

from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json
from .metrics import probability_metrics
from .models import Task
from .optimizer import OptimizationTimeout, optimize_cobyla
from .phase1_1_diagnostic import embed_p2_in_p3
from .phase1_2_experiment import objective_value_from_probabilities
from .phase1_2_objectives import (
    feasibility_penalty_bound,
    optimize_cobyla_objective,
    weighted_exact_cvar,
)
from .phase3_models import FREEZE_HASH_PATH, load_frozen_models, prepare_scaling_rows
from .phase3_tasks import (
    CHARACTERIZATION_PATH,
    CONFIG_PATH,
    RESULT_ROOT,
    build_phase3_energy_context,
    characterization_lookup,
    load_manifest,
    sha256_file,
    verify_predecessor_hashes,
)
from .qaoa import apply_cost_layer, apply_x_mixer, plus_state, simulate_qaoa


RESOURCE_PREFLIGHT_CSV = RESULT_ROOT / "resource_preflight.csv"
RESOURCE_PREFLIGHT_JSON = RESULT_ROOT / "resource_preflight.json"
RESOURCE_PREFLIGHT_REPORT = RESULT_ROOT / "RESOURCE_PREFLIGHT.md"
EXECUTION_PROVENANCE = RESULT_ROOT / "execution_provenance.json"
EXECUTION_FREEZE_PATH = RESULT_ROOT / "PHASE3_EXECUTION_FREEZE.json"
PREFLIGHT_ROOT = RESULT_ROOT / "preflight"
PREFLIGHT_SUMMARY = PREFLIGHT_ROOT / "preflight_summary.json"
ADEQUACY_2B_PATH = RESULT_ROOT / "optimization_adequacy_2B_runs.csv"
ADEQUACY_PATH = RESULT_ROOT / "optimization_adequacy.csv"
CANONICAL_PATH = RESULT_ROOT / "canonical_results.csv"


SPLIT_RESULT_PATHS = {
    "development": RESULT_ROOT / "development_runs.csv",
    "interpolation_holdout": RESULT_ROOT / "interpolation_holdout_runs.csv",
    "extrapolation_holdout": RESULT_ROOT / "extrapolation_holdout_runs.csv",
}


RUN_FIELDS = [
    "run_id", "phase", "evidence_identity", "matrix_role", "split", "task_id",
    "base_graph_id", "base_instance_id", "size_m", "n_nodes", "n_edges",
    "state_space_size", "n_candidate_routes", "n_feasible_routes",
    "n_feasible_states", "route_feasible_fraction", "feasible_state_fraction",
    "dilution_score", "objective_id", "objective_name", "objective_role", "depth",
    "p2_initialization_seed_set", "optimizer_seed", "selected_p2_seed",
    "selected_p2_run_id", "p3_initial_parameters", "initial_parameters",
    "terminal_parameters", "best_evaluated_parameters", "optimizer", "eval_budget",
    "nfev", "tracked_optimizer_evaluations", "total_objective_evaluations",
    "optimizer_status", "optimizer_message", "objective_start", "objective_final",
    "objective_improvement", "expected_mean_energy", "expected_routing_component",
    "expected_flow_penalty", "expected_resource_penalty", "expected_total_penalty",
    "p_feas", "p_opt", "p_opt_given_feasible", "feasibility_amplification",
    "log_feasibility_gain", "cvar_alpha", "cvar_value", "cvar_cutoff_energy",
    "cvar_tail_fully_feasible", "cvar_tail_feasible_mass",
    "cvar_fractional_cutoff_mass", "strict_energy_class_separation",
    "penalty_bound_pass", "state_norm", "runtime_s", "peak_memory_mb",
    "execution_status", "failure_reason", "resource_censored", "config_sha256",
    "manifest_sha256", "raw_statevector_persisted", "failure_lineage",
]


VALID_TERMINAL_STATUSES = {
    "SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT", "TIMEOUT", "OOM",
    "OPTIMIZER_FAILURE", "NUMERICAL_FAILURE", "RESOURCE_CENSORED",
}
SCIENTIFIC_STATUSES = {"SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT"}


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / 1024.0 if value < 10**9 else value / (1024.0**2))


def _available_ram_mb() -> float:
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return float(line.split()[1]) / 1024.0
    pages = os.sysconf("SC_AVPHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    return float(pages * page_size / (1024**2))


def freeze_execution_identity(pytest_result: str) -> dict[str, Any]:
    """Freeze all prospective inputs after passing tests/preflights, before development."""
    if "passed" not in pytest_result.lower() or "failed" in pytest_result.lower():
        raise RuntimeError("a passing full pytest result is required before execution freeze")
    if not CHARACTERIZATION_PATH.exists() or len(pd.read_csv(CHARACTERIZATION_PATH)) != 180:
        raise RuntimeError("complete 180-task characterization is required")
    if not RESOURCE_PREFLIGHT_JSON.exists():
        raise RuntimeError("resource preflight is required")
    if not PREFLIGHT_SUMMARY.exists():
        raise RuntimeError("final-protocol preflight is required")
    preflight = json.loads(PREFLIGHT_SUMMARY.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASSED":
        raise RuntimeError("final-protocol preflight did not pass")
    predecessor = verify_predecessor_hashes()
    protocol_source = PROJECT_ROOT / "protocols/phase3_scaling_v1/PREREGISTRATION.md"
    result_protocol = RESULT_ROOT / "PREREGISTRATION.md"
    result_protocol.write_text(protocol_source.read_text(encoding="utf-8"), encoding="utf-8")
    scientific_inputs = [
        CONFIG_PATH,
        protocol_source,
        PROJECT_ROOT / "docs/SCALING_LAW_DERIVATION.md",
        PROJECT_ROOT / "src/qroute_dilution/phase3_tasks.py",
        PROJECT_ROOT / "src/qroute_dilution/phase3_execution.py",
        PROJECT_ROOT / "src/qroute_dilution/phase3_models.py",
        PROJECT_ROOT / "src/qroute_dilution/phase3_analysis.py",
        PROJECT_ROOT / "data/manifests/phase3_scaling_v1/task_universe.json",
        PROJECT_ROOT / "data/manifests/phase3_scaling_v1/development.json",
        PROJECT_ROOT / "data/manifests/phase3_scaling_v1/interpolation_holdout.json",
        PROJECT_ROOT / "data/manifests/phase3_scaling_v1/extrapolation_holdout.json",
        PROJECT_ROOT / "data/manifests/phase3_scaling_v1/manifest_hashes.json",
        CHARACTERIZATION_PATH,
        RESOURCE_PREFLIGHT_CSV,
        RESOURCE_PREFLIGHT_JSON,
        PREFLIGHT_SUMMARY,
    ]
    hashes = {str(path.relative_to(PROJECT_ROOT)): sha256_file(path) for path in scientific_inputs}
    config = load_config(CONFIG_PATH)
    payload = {
        "schema_version": "phase3_scaling_v1.execution_freeze.v1",
        "predecessor_git_sha": config["predecessor_git_sha"],
        "predecessor_inventory_sha256": predecessor["inventory_sha256"],
        "predecessor_file_count": predecessor["file_count"],
        "scientific_input_hashes": hashes,
        "pytest_result": pytest_result,
        "task_count": 180,
        "base_graph_count": 30,
        "planned_primary_optimization_runs": 1080,
        "planned_adequacy_2B_additional_runs": 12,
        "development_qaoa_started": False,
        "holdout_qaoa_started": False,
    }
    write_json(EXECUTION_FREEZE_PATH, payload)
    return payload


def verify_execution_identity() -> dict[str, Any]:
    if not EXECUTION_FREEZE_PATH.exists():
        raise RuntimeError("Phase-3 execution identity is not frozen")
    payload = json.loads(EXECUTION_FREEZE_PATH.read_text(encoding="utf-8"))
    for relative, expected in payload["scientific_input_hashes"].items():
        observed = sha256_file(PROJECT_ROOT / relative)
        if observed != expected:
            raise RuntimeError(f"frozen Phase-3 scientific input changed: {relative}")
    verify_predecessor_hashes()
    return payload


def _failure_status(exc: Exception) -> str:
    if isinstance(exc, OptimizationTimeout):
        return "TIMEOUT"
    if isinstance(exc, MemoryError):
        return "OOM"
    if isinstance(exc, FloatingPointError):
        return "NUMERICAL_FAILURE"
    return "OPTIMIZER_FAILURE"


def _row_digest(row: dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _receipt_path(receipt_root: str | Path, run_id: str) -> Path:
    return Path(receipt_root) / f"{run_id}.json"


def write_run_receipt(receipt_root: str | Path, row: dict[str, Any]) -> None:
    path = _receipt_path(receipt_root, str(row["run_id"]))
    if path.exists():
        existing = load_run_receipt(path)
        if existing != row:
            raise RuntimeError(f"attempt to replace immutable run receipt: {row['run_id']}")
        return
    write_json(path, {"row_sha256": _row_digest(row), "row": row})


def load_run_receipt(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    row = payload["row"]
    if payload.get("row_sha256") != _row_digest(row):
        raise RuntimeError(f"run receipt hash invalid: {path}")
    if row.get("execution_status") not in VALID_TERMINAL_STATUSES:
        raise RuntimeError(f"run receipt is not terminal: {path}")
    return row


def _receipt_exists_valid(receipt_root: Path, run_id: str) -> bool:
    path = _receipt_path(receipt_root, run_id)
    if not path.exists():
        return False
    load_run_receipt(path)
    return True


def _run_id(
    namespace: str,
    task_id: str,
    stage: str,
    identity: str,
    budget: int,
    config_hash: str,
) -> str:
    payload = f"{namespace}|{task_id}|{stage}|{identity}|B{budget}|{config_hash}"
    return "phase3-" + hashlib.sha256(payload.encode()).hexdigest()[:24]


def _base_row(
    task: Task,
    characterization: dict[str, Any],
    config: dict[str, Any],
    *,
    namespace: str,
    split: str,
    matrix_role: str,
    stage: str,
    identity: str,
    objective_id: str,
    objective_name: str,
    objective_role: str,
    depth: int,
    budget: int,
    optimizer_seed: int | float = math.nan,
) -> dict[str, Any]:
    config_hash = sha256_file(CONFIG_PATH)
    manifest_hash = json.loads(
        (PROJECT_ROOT / "data/manifests/phase3_scaling_v1/manifest_hashes.json").read_text()
    )["task_universe.json"]
    row = {field: math.nan for field in RUN_FIELDS}
    row.update(
        {
            "run_id": _run_id(namespace, task.task_id, stage, identity, budget, config_hash),
            "phase": "PHASE_3_EMPIRICAL_DILUTION_SCALING",
            "evidence_identity": config["evidence_identity"],
            "matrix_role": matrix_role,
            "split": split,
            "task_id": task.task_id,
            "base_graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_m": len(task.graph.edges),
            "n_nodes": task.graph.n_nodes,
            "n_edges": len(task.graph.edges),
            "state_space_size": int(characterization["state_space_size"]),
            "n_candidate_routes": int(characterization["n_candidate_routes"]),
            "n_feasible_routes": int(characterization["n_feasible_routes"]),
            "n_feasible_states": int(characterization["n_feasible_states"]),
            "route_feasible_fraction": float(characterization["route_feasible_fraction"]),
            "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
            "dilution_score": float(characterization["dilution_score"]),
            "objective_id": objective_id,
            "objective_name": objective_name,
            "objective_role": objective_role,
            "depth": depth,
            "p2_initialization_seed_set": json.dumps(config["p2_preparation"]["optimizer_seeds"]),
            "optimizer_seed": optimizer_seed,
            "optimizer": "COBYLA",
            "eval_budget": budget,
            "execution_status": "SUCCESS",
            "failure_reason": "",
            "resource_censored": False,
            "config_sha256": config_hash,
            "manifest_sha256": manifest_hash,
            "raw_statevector_persisted": False,
            "failure_lineage": "",
        }
    )
    return row


def _scientific_evaluation(
    task: Task,
    context: dict[str, Any],
    parameters: np.ndarray,
    depth: int,
    alpha: float,
) -> dict[str, Any]:
    state = simulate_qaoa(np.asarray(parameters, dtype=float), context["energy"], depth)
    probabilities = np.abs(state) ** 2
    phi = float(context["feasible_mask"].mean())
    metrics = probability_metrics(
        probabilities,
        np.flatnonzero(context["feasible_mask"]),
        np.flatnonzero(context["optimal_mask"]),
        phi,
    )
    p_feas = float(metrics["p_feas"])
    cvar = weighted_exact_cvar(
        context["energy"], probabilities, alpha,
        feasible_mask=context["feasible_mask"], energy_order=context["energy_order"],
    )
    bound = feasibility_penalty_bound(
        probabilities, context["feasible_mask"], context["total_penalty"]
    )
    max_feasible = float(context["energy"][context["feasible_mask"]].max())
    min_infeasible = float(context["energy"][~context["feasible_mask"]].min())
    return {
        "expected_mean_energy": float(np.dot(probabilities, context["energy"])),
        "expected_routing_component": float(np.dot(probabilities, context["routing_component"])),
        "expected_flow_penalty": float(np.dot(probabilities, context["flow_penalty"])),
        "expected_resource_penalty": float(np.dot(probabilities, context["resource_penalty"])),
        "expected_total_penalty": float(np.dot(probabilities, context["total_penalty"])),
        "p_feas": p_feas,
        "p_opt": float(metrics["p_opt"]),
        "p_opt_given_feasible": float(metrics["p_opt_given_feasible"]),
        "feasibility_amplification": float(metrics["feasibility_amplification"]),
        "log_feasibility_gain": float(metrics["log_feasibility_gain"]),
        "cvar_alpha": alpha,
        **cvar,
        "strict_energy_class_separation": bool(min_infeasible > max_feasible),
        "penalty_bound_pass": bool(bound["bound_pass"]),
        "state_norm": float(probabilities.sum()),
    }


def _terminal_probability_status(evaluation: dict[str, Any]) -> tuple[str, str]:
    if evaluation["p_feas"] <= np.finfo(float).tiny:
        return "ZERO_P_FEAS", "ZERO_P_FEAS"
    if evaluation["p_opt"] <= np.finfo(float).tiny:
        return "ZERO_P_OPT", "ZERO_P_OPT"
    return "SUCCESS", ""


def _run_p2_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    config: dict[str, Any],
    namespace: str,
    split: str,
    matrix_role: str,
    seeds: list[int],
    receipt_root: str,
) -> list[str]:
    task = Task.from_dict(task_payload)
    written: list[str] = []
    try:
        context = build_phase3_energy_context(task)
    except Exception as exc:
        context = None
        context_error = exc
    for seed in seeds:
        budget = int(config["p2_preparation"]["eval_budget"])
        row = _base_row(
            task, characterization, config, namespace=namespace, split=split,
            matrix_role=matrix_role, stage="p2", identity=str(seed),
            objective_id="P2_O0", objective_name="MEAN_ENERGY_PREPARATION",
            objective_role="COMMON_INITIALIZATION_PREPARATION", depth=2,
            budget=budget, optimizer_seed=seed,
        )
        try:
            if context is None:
                raise context_error
            result = optimize_cobyla(
                context["energy"], 2, seed, budget,
                timeout_s=float(config["p2_preparation"]["timeout_s"]),
            )
            evaluation = _scientific_evaluation(
                task, context, result.optimized_parameters, 2, float(config["cvar_alpha"])
            )
            row.update(
                {
                    "initial_parameters": json.dumps(result.initial_parameters.tolist()),
                    "terminal_parameters": json.dumps(result.optimized_parameters.tolist()),
                    "best_evaluated_parameters": json.dumps(result.optimized_parameters.tolist()),
                    "objective_start": result.objective_initial,
                    "objective_final": result.objective_final,
                    "objective_improvement": result.objective_initial - result.objective_final,
                    "nfev": result.nfev,
                    "tracked_optimizer_evaluations": result.nfev,
                    "total_objective_evaluations": result.nfev + 1,
                    "optimizer_status": result.status,
                    "optimizer_message": result.message,
                    "runtime_s": result.runtime_s,
                    **evaluation,
                }
            )
            if not result.success or not evaluation["penalty_bound_pass"]:
                raise FloatingPointError("p2 numerical validation failed")
            row["execution_status"], row["failure_reason"] = _terminal_probability_status(evaluation)
        except Exception as exc:
            row["execution_status"] = _failure_status(exc)
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
            row["failure_lineage"] = "p2_preparation"
        row["peak_memory_mb"] = _peak_memory_mb()
        row = {field: row[field] for field in RUN_FIELDS}
        write_run_receipt(receipt_root, row)
        written.append(row["run_id"])
    return written


def _parse_parameters(value: str | list[float]) -> np.ndarray:
    return np.asarray(json.loads(value) if isinstance(value, str) else value, dtype=float)


def _objective_from_evaluation(objective_id: str, evaluation: dict[str, Any]) -> float:
    return {
        "O0": float(evaluation["expected_mean_energy"]),
        "O2": float(1.0 - evaluation["p_feas"]),
        "O3": float(evaluation["cvar_value"]),
    }[objective_id]


def _run_p3_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    selected_p2: dict[str, Any] | None,
    config: dict[str, Any],
    namespace: str,
    split: str,
    matrix_role: str,
    objective_ids: list[str],
    budget: int,
    receipt_root: str,
) -> list[str]:
    task = Task.from_dict(task_payload)
    written: list[str] = []
    objective_config = config["p3_comparison"]
    try:
        if selected_p2 is None:
            raise RuntimeError("no finite common p2 initialization")
        context = build_phase3_energy_context(task)
        initial = embed_p2_in_p3(_parse_parameters(selected_p2["terminal_parameters"]))
    except Exception as exc:
        context = None
        initial = None
        context_error = exc
    for objective_id in objective_ids:
        metadata = objective_config[objective_id]
        row = _base_row(
            task, characterization, config, namespace=namespace, split=split,
            matrix_role=matrix_role, stage="p3", identity=objective_id,
            objective_id=objective_id, objective_name=metadata["name"],
            objective_role=metadata["role"], depth=3, budget=budget,
        )
        if selected_p2 is not None:
            row["selected_p2_seed"] = int(selected_p2["optimizer_seed"])
            row["selected_p2_run_id"] = selected_p2["run_id"]
        try:
            if context is None or initial is None:
                raise context_error
            alpha = float(config["cvar_alpha"])
            start = _scientific_evaluation(task, context, initial, 3, alpha)

            def objective(parameters: np.ndarray) -> float:
                probabilities = np.abs(simulate_qaoa(parameters, context["energy"], 3)) ** 2
                return objective_value_from_probabilities(
                    objective_id, probabilities, context, cvar_alpha=alpha
                )

            result = optimize_cobyla_objective(
                objective, initial, eval_budget=budget,
                timeout_s=float(config["p3_comparison"]["timeout_s"]),
                rhobeg=float(config["cobyla_rhobeg"]),
                catol=float(config["cobyla_catol"]),
            )
            final = _scientific_evaluation(task, context, result.terminal_parameters, 3, alpha)
            final_objective = _objective_from_evaluation(objective_id, final)
            row.update(
                {
                    "p3_initial_parameters": json.dumps(initial.tolist()),
                    "initial_parameters": json.dumps(initial.tolist()),
                    "terminal_parameters": json.dumps(result.terminal_parameters.tolist()),
                    "best_evaluated_parameters": json.dumps(result.best_evaluated_parameters.tolist()),
                    "objective_start": result.objective_start,
                    "objective_final": final_objective,
                    "objective_improvement": result.objective_start - final_objective,
                    "nfev": result.optimizer_nfev,
                    "tracked_optimizer_evaluations": result.tracked_optimizer_evaluations,
                    "total_objective_evaluations": result.total_objective_evaluations,
                    "optimizer_status": result.status,
                    "optimizer_message": result.message,
                    "runtime_s": result.runtime_s,
                    **final,
                }
            )
            if abs(final_objective - result.terminal_objective) > 1e-9:
                raise FloatingPointError("terminal objective recomputation mismatch")
            if not result.numerically_valid or not final["penalty_bound_pass"]:
                raise FloatingPointError("p3 numerical validation failed")
            row["execution_status"], row["failure_reason"] = _terminal_probability_status(final)
        except Exception as exc:
            row["execution_status"] = _failure_status(exc)
            row["failure_reason"] = f"{type(exc).__name__}: {exc}"
            row["failure_lineage"] = (
                f"selected_p2:{selected_p2.get('run_id', '')}" if selected_p2 else "missing_p2"
            )
        row["peak_memory_mb"] = _peak_memory_mb()
        row = {field: row[field] for field in RUN_FIELDS}
        write_run_receipt(receipt_root, row)
        written.append(row["run_id"])
    return written


def _resource_censored_row(
    task: Task,
    characterization: dict[str, Any],
    config: dict[str, Any],
    namespace: str,
    split: str,
    stage: str,
    identity: str,
    objective_id: str,
    objective_name: str,
    objective_role: str,
    depth: int,
    budget: int,
    seed: int | float = math.nan,
) -> dict[str, Any]:
    row = _base_row(
        task, characterization, config, namespace=namespace, split=split,
        matrix_role="PRIMARY_MATRIX", stage=stage, identity=identity,
        objective_id=objective_id, objective_name=objective_name,
        objective_role=objective_role, depth=depth, budget=budget, optimizer_seed=seed,
    )
    row.update(
        {
            "nfev": 0,
            "tracked_optimizer_evaluations": 0,
            "total_objective_evaluations": 0,
            "runtime_s": 0.0,
            "peak_memory_mb": 0.0,
            "execution_status": "RESOURCE_CENSORED",
            "failure_reason": "ALL_TASKS_AT_SIZE_CENSORED_BY_PROSPECTIVE_RESOURCE_GUARD",
            "resource_censored": True,
            "failure_lineage": "resource_preflight",
        }
    )
    return {field: row[field] for field in RUN_FIELDS}


def run_resource_preflight() -> pd.DataFrame:
    """Benchmark only fixed-parameter deterministic simulation kernels at each size."""
    config = load_config(CONFIG_PATH)
    universe = load_manifest()
    task_by_size: dict[int, dict[str, Any]] = {}
    for item in universe["tasks"]:
        task_by_size.setdefault(int(item["size_m"]), item)
    available_mb = _available_ram_mb()
    parameters = np.asarray(config["resource_guards"]["representative_parameters"], dtype=float)
    repeats = int(config["resource_guards"]["timing_repeats"])
    rows: list[dict[str, Any]] = []
    for size_m in (int(value) for value in config["sizes"]):
        task = read_task(PROJECT_ROOT / task_by_size[size_m]["task_path"])
        context_started = time.perf_counter()
        context = build_phase3_energy_context(task)
        context_time = time.perf_counter() - context_started
        energy = context["energy"]
        state = plus_state(size_m)
        cost_times, mixer_times, forward_times = [], [], []
        numerical = True
        try:
            for _ in range(repeats):
                started = time.perf_counter()
                cost_state = apply_cost_layer(state, energy, parameters[0])
                cost_times.append(time.perf_counter() - started)
                started = time.perf_counter()
                mixed_state = apply_x_mixer(state, parameters[3], size_m)
                mixer_times.append(time.perf_counter() - started)
                started = time.perf_counter()
                forward = simulate_qaoa(parameters, energy, 3)
                forward_times.append(time.perf_counter() - started)
                numerical = numerical and bool(
                    np.all(np.isfinite(forward)) and abs(float(np.vdot(forward, forward).real) - 1.0) < 1e-9
                )
                del cost_state, mixed_state, forward
        except (MemoryError, FloatingPointError):
            numerical = False
        n_states = 1 << size_m
        context_bytes = sum(
            value.nbytes for value in context.values() if isinstance(value, np.ndarray)
        )
        # Four complex work vectors cover state, layer output, and mixer low/high copies.
        predicted_peak_mb = (context_bytes + 4 * n_states * 16) / (1024**2)
        forward_s = float(np.median(forward_times)) if forward_times else math.inf
        eval_s = 1.25 * forward_s
        optimization_s = eval_s * int(config["p3_comparison"]["eval_budget"])
        memory_pass = predicted_peak_mb <= float(config["resource_guards"]["maximum_worker_fraction_available_ram"]) * available_mb
        time_pass = optimization_s <= float(config["resource_guards"]["maximum_predicted_single_optimization_s"])
        guard_pass = bool(memory_pass and time_pass and numerical)
        safe_workers = max(
            1,
            min(
                int(config["execution"]["maximum_workers"]),
                int((0.70 * available_mb) // max(predicted_peak_mb, 1.0)),
            ),
        )
        rows.append(
            {
                "size_m": size_m,
                "task_id": task.task_id,
                "state_space_size": n_states,
                "available_ram_mb": available_mb,
                "statevector_memory_mb": n_states * 16 / (1024**2),
                "energy_array_memory_mb": energy.nbytes / (1024**2),
                "context_build_time_s": context_time,
                "single_cost_layer_time_s": float(np.median(cost_times)) if cost_times else math.inf,
                "single_x_mixer_layer_time_s": float(np.median(mixer_times)) if mixer_times else math.inf,
                "single_p3_forward_time_s": forward_s,
                "predicted_memory_per_worker_mb": predicted_peak_mb,
                "predicted_objective_evaluation_s": eval_s,
                "predicted_full_optimization_s": optimization_s,
                "memory_guard_pass": memory_pass,
                "time_guard_pass": time_pass,
                "numerical_statevector_pass": numerical,
                "resource_guard_pass": guard_pass,
                "resource_censored": not guard_pass,
                "safe_worker_count": safe_workers,
                "peak_process_memory_mb": _peak_memory_mb(),
            }
        )
        del context, energy, state
    frame = pd.DataFrame(rows)
    # Censoring is an upper-tail policy: once a size fails, all larger sizes are censored.
    frame = apply_upper_tail_resource_censoring(frame)
    atomic_write_csv(RESOURCE_PREFLIGHT_CSV, frame)
    planned_evaluations = (
        int(config["planned_runs"]["development_p2"]) * int(config["p2_preparation"]["eval_budget"])
        + int(config["planned_runs"]["development_p3"]) * int(config["p3_comparison"]["eval_budget"])
        + int(config["planned_runs"]["interpolation_p2"]) * int(config["p2_preparation"]["eval_budget"])
        + int(config["planned_runs"]["interpolation_p3"]) * int(config["p3_comparison"]["eval_budget"])
        + int(config["planned_runs"]["extrapolation_p2"]) * int(config["p2_preparation"]["eval_budget"])
        + int(config["planned_runs"]["extrapolation_p3"]) * int(config["p3_comparison"]["eval_budget"])
    )
    summary = {
        "implementation": "CPU NumPy exact statevector",
        "available_ram_mb": available_mb,
        "planned_primary_optimization_runs": int(config["planned_runs"]["primary_total"]),
        "planned_objective_evaluations_upper_bound": planned_evaluations,
        "resource_censored_sizes": frame.loc[frame.resource_censored, "size_m"].astype(int).tolist(),
        "largest_allowed_m": int(frame.loc[~frame.resource_censored, "size_m"].max()),
        "m20_pass": bool(frame.loc[frame.size_m == 20, "resource_guard_pass"].iloc[0]),
        "m22_pass": bool(frame.loc[frame.size_m == 22, "resource_guard_pass"].iloc[0]),
    }
    write_json(RESOURCE_PREFLIGHT_JSON, summary)
    lines = [
        "# Phase 3 resource preflight", "",
        "Only deterministic fixed-parameter simulation kernels were benchmarked; no QAOA",
        "performance outcome was used. Runtime is classical CPU simulation/runtime scaling,",
        "not quantum complexity.", "",
        f"- Available RAM: {available_mb:.1f} MB",
        f"- Largest allowed size: m={summary['largest_allowed_m']}",
        f"- Resource-censored sizes: {summary['resource_censored_sizes'] or 'none'}", "",
        frame.to_string(index=False), "",
    ]
    RESOURCE_PREFLIGHT_REPORT.write_text("\n".join(lines), encoding="utf-8")
    if not summary["m20_pass"]:
        raise RuntimeError("SCALING_RANGE_INSUFFICIENT: m=20 failed the prospective resource guard")
    return frame


def apply_upper_tail_resource_censoring(frame: pd.DataFrame) -> pd.DataFrame:
    """If one size fails prospectively, censor it and every larger size uniformly."""
    output = frame.copy()
    failed = sorted(output.loc[~output.resource_guard_pass.astype(bool), "size_m"].astype(int).tolist())
    if failed:
        first = min(failed)
        output.loc[output.size_m >= first, "resource_censored"] = True
        output.loc[output.size_m >= first, "resource_guard_pass"] = False
    return output


def _load_resource_policy() -> tuple[set[int], dict[int, int]]:
    if not RESOURCE_PREFLIGHT_CSV.exists():
        raise RuntimeError("resource preflight must complete before optimization")
    frame = pd.read_csv(RESOURCE_PREFLIGHT_CSV)
    censored = set(frame.loc[frame.resource_censored.astype(bool), "size_m"].astype(int))
    workers = {int(row.size_m): int(row.safe_worker_count) for row in frame.itertuples()}
    return censored, workers


def _select_p2(rows: pd.DataFrame) -> pd.DataFrame:
    eligible = rows[
        rows.objective_id.eq("P2_O0")
        & rows.execution_status.isin(SCIENTIFIC_STATUSES)
        & np.isfinite(rows.objective_final)
    ]
    return (
        eligible.sort_values(["task_id", "objective_final", "optimizer_seed"], kind="stable")
        .groupby("task_id", as_index=False, sort=False).first()
    )


def _assemble_receipts(receipt_root: Path) -> pd.DataFrame:
    rows = [load_run_receipt(path) for path in sorted(receipt_root.glob("*.json"))]
    return pd.DataFrame(rows, columns=RUN_FIELDS)


def _write_split_frame(split: str, receipt_root: Path) -> pd.DataFrame:
    frame = _assemble_receipts(receipt_root)
    selected = _select_p2(frame)
    selected_seed = selected.set_index("task_id").optimizer_seed.to_dict()
    selected_id = selected.set_index("task_id").run_id.to_dict()
    p2_mask = frame.objective_id.eq("P2_O0")
    frame.loc[p2_mask, "selected_p2_seed"] = frame.loc[p2_mask, "task_id"].map(selected_seed)
    frame.loc[p2_mask, "selected_p2_run_id"] = frame.loc[p2_mask, "task_id"].map(selected_id)
    order = {"P2_O0": 0, "O0": 1, "O2": 2, "O3": 3}
    frame["_objective_order"] = frame.objective_id.map(order)
    frame = frame.sort_values(
        ["size_m", "base_instance_id", "dilution_score", "_objective_order", "optimizer_seed"],
        kind="stable",
    ).drop(columns="_objective_order")
    atomic_write_csv(SPLIT_RESULT_PATHS[split], frame)
    return frame


def _set_worker_threads(config: dict[str, Any]) -> None:
    threads = str(config["execution"]["worker_blas_threads"])
    os.environ["OMP_NUM_THREADS"] = threads
    os.environ["OPENBLAS_NUM_THREADS"] = threads
    os.environ["MKL_NUM_THREADS"] = threads


def _run_parallel(jobs: list[tuple[Any, ...]], worker: Callable[..., Any], max_workers: int) -> None:
    if not jobs:
        return
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(worker, *job) for job in jobs]
        for future in as_completed(futures):
            future.result()


def run_split(split: str, *, namespace: str = "phase3-formal") -> pd.DataFrame:
    """Run one split with deterministic receipts and prospective size censoring."""
    if split not in SPLIT_RESULT_PATHS:
        raise ValueError("unknown Phase-3 split")
    verify_execution_identity()
    if split != "development":
        load_frozen_models()  # Hard access gate before any holdout QAOA.
    verify_predecessor_hashes()
    config = load_config(CONFIG_PATH)
    manifest = load_manifest(split)
    characterization = characterization_lookup()
    censored_sizes, workers_by_size = _load_resource_policy()
    receipt_root = RESULT_ROOT / "run_receipts" / split
    receipt_root.mkdir(parents=True, exist_ok=True)
    task_items = {row["task_id"]: row for row in manifest["tasks"]}
    _set_worker_threads(config)

    for size_m in sorted({int(row["size_m"]) for row in manifest["tasks"]}):
        items = [row for row in manifest["tasks"] if int(row["size_m"]) == size_m]
        if size_m in censored_sizes:
            for item in items:
                task = read_task(PROJECT_ROOT / item["task_path"])
                char = characterization[task.task_id]
                for seed in config["p2_preparation"]["optimizer_seeds"]:
                    row = _resource_censored_row(
                        task, char, config, namespace, split, "p2", str(seed), "P2_O0",
                        "MEAN_ENERGY_PREPARATION", "COMMON_INITIALIZATION_PREPARATION", 2,
                        int(config["p2_preparation"]["eval_budget"]), int(seed),
                    )
                    write_run_receipt(receipt_root, row)
                for objective_id in config["p3_comparison"]["objective_ids"]:
                    metadata = config["p3_comparison"][objective_id]
                    row = _resource_censored_row(
                        task, char, config, namespace, split, "p3", objective_id,
                        objective_id, metadata["name"], metadata["role"], 3,
                        int(config["p3_comparison"]["eval_budget"]),
                    )
                    write_run_receipt(receipt_root, row)
            continue
        p2_jobs = []
        for item in items:
            task = read_task(PROJECT_ROOT / item["task_path"])
            missing_seeds = []
            for seed in config["p2_preparation"]["optimizer_seeds"]:
                run_id = _run_id(namespace, task.task_id, "p2", str(seed), int(config["p2_preparation"]["eval_budget"]), sha256_file(CONFIG_PATH))
                if not _receipt_exists_valid(receipt_root, run_id):
                    missing_seeds.append(int(seed))
            if missing_seeds:
                p2_jobs.append((task.to_dict(), characterization[task.task_id], config, namespace, split, "PRIMARY_MATRIX", missing_seeds, str(receipt_root)))
        _run_parallel(p2_jobs, _run_p2_batch, workers_by_size[size_m])
        current = _assemble_receipts(receipt_root)
        selected = _select_p2(current).set_index("task_id")
        p3_jobs = []
        for item in items:
            task = read_task(PROJECT_ROOT / item["task_path"])
            missing_objectives = []
            for objective_id in config["p3_comparison"]["objective_ids"]:
                run_id = _run_id(namespace, task.task_id, "p3", objective_id, int(config["p3_comparison"]["eval_budget"]), sha256_file(CONFIG_PATH))
                if not _receipt_exists_valid(receipt_root, run_id):
                    missing_objectives.append(objective_id)
            if missing_objectives:
                p2_row = selected.loc[task.task_id].to_dict() if task.task_id in selected.index else None
                if p2_row is not None:
                    p2_row["run_id"] = selected.loc[task.task_id].name if "run_id" not in p2_row else p2_row["run_id"]
                p3_jobs.append((task.to_dict(), characterization[task.task_id], p2_row, config, namespace, split, "PRIMARY_MATRIX", missing_objectives, int(config["p3_comparison"]["eval_budget"]), str(receipt_root)))
        _run_parallel(p3_jobs, _run_p3_batch, workers_by_size[size_m])
        _write_split_frame(split, receipt_root)

    frame = _write_split_frame(split, receipt_root)
    expected = int(config["planned_runs"][f"{split.replace('_holdout', '')}_p2"]) + int(config["planned_runs"][f"{split.replace('_holdout', '')}_p3"])
    if len(frame) != expected:
        raise RuntimeError(f"{split} run denominator mismatch: {len(frame)} != {expected}")
    p3 = frame[frame.objective_id.isin(["O0", "O2", "O3"]) & ~frame.resource_censored.astype(bool)]
    common = p3.groupby("task_id").p3_initial_parameters.nunique(dropna=False)
    if len(common) and not common.eq(1).all():
        raise RuntimeError("common p2-to-p3 initialization contract failed")
    if len(p3) and not p3.eval_budget.eq(int(config["p3_comparison"]["eval_budget"])).all():
        raise RuntimeError("matched p3 objective budget contract failed")
    _refresh_canonical()
    verify_predecessor_hashes()
    return frame


def _refresh_canonical() -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in SPLIT_RESULT_PATHS.values() if path.exists()]
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=RUN_FIELDS)
    if len(frame):
        frame = frame.sort_values(["split", "size_m", "base_instance_id", "task_id", "depth", "objective_id", "optimizer_seed"], kind="stable")
    atomic_write_csv(CANONICAL_PATH, frame)
    return frame


def run_protocol_preflight() -> dict[str, Any]:
    """Exercise final p2/p3 code on the first two m=12 development tasks."""
    config = load_config(CONFIG_PATH)
    manifest = load_manifest("development")
    items = [row for row in manifest["tasks"] if int(row["size_m"]) == 12][:2]
    characterization = characterization_lookup()
    receipt_root = PREFLIGHT_ROOT / "run_receipts"
    receipt_root.mkdir(parents=True, exist_ok=True)
    namespace = "phase3-protocol-preflight"
    for item in items:
        task = read_task(PROJECT_ROOT / item["task_path"])
        missing_seeds = [
            int(seed) for seed in config["p2_preparation"]["optimizer_seeds"]
            if not _receipt_exists_valid(
                receipt_root,
                _run_id(namespace, task.task_id, "p2", str(seed), int(config["p2_preparation"]["eval_budget"]), sha256_file(CONFIG_PATH)),
            )
        ]
        if missing_seeds:
            _run_p2_batch(task.to_dict(), characterization[task.task_id], config, namespace, "development", "PROTOCOL_PREFLIGHT", missing_seeds, str(receipt_root))
    frame = _assemble_receipts(receipt_root)
    selected = _select_p2(frame).set_index("task_id")
    for item in items:
        task = read_task(PROJECT_ROOT / item["task_path"])
        p2_row = selected.loc[task.task_id].to_dict()
        missing_objectives = [
            objective for objective in config["p3_comparison"]["objective_ids"]
            if not _receipt_exists_valid(
                receipt_root,
                _run_id(namespace, task.task_id, "p3", objective, int(config["p3_comparison"]["eval_budget"]), sha256_file(CONFIG_PATH)),
            )
        ]
        if missing_objectives:
            _run_p3_batch(task.to_dict(), characterization[task.task_id], p2_row, config, namespace, "development", "PROTOCOL_PREFLIGHT", missing_objectives, int(config["p3_comparison"]["eval_budget"]), str(receipt_root))
    frame = _assemble_receipts(receipt_root)
    atomic_write_csv(PREFLIGHT_ROOT / "preflight_runs.csv", frame)
    p2 = frame[frame.objective_id == "P2_O0"]
    p3 = frame[frame.objective_id.isin(["O0", "O2", "O3"])]
    common = p3.groupby("task_id").p3_initial_parameters.nunique().eq(1).all()
    budgets = p3.groupby("task_id").eval_budget.nunique().eq(1).all()
    prepared = prepare_scaling_rows(p3)
    scaling_pipeline = bool(
        np.isfinite(prepared.Y).all()
        and np.isfinite(prepared.Dc).all()
        and prepared.groupby(["base_graph_id", "objective_id"]).Dc.sum().abs().lt(1e-12).all()
    )
    required = bool(
        len(p2) == 6 and len(p3) == 6
        and p2.execution_status.isin(SCIENTIFIC_STATUSES).all()
        and p3.execution_status.isin(SCIENTIFIC_STATUSES).all()
        and common and budgets
        and p3.penalty_bound_pass.astype(bool).all()
        and p3.strict_energy_class_separation.astype(bool).all()
        and scaling_pipeline
    )
    summary = {
        "status": "PASSED" if required else "FAILED_STOP",
        "task_ids": [item["task_id"] for item in items],
        "p2_rows": len(p2), "p3_rows": len(p3),
        "row_writing_pass": len(frame) == 12,
        "resume_semantics_pass": all(load_run_receipt(path) for path in receipt_root.glob("*.json")),
        "common_initialization_pass": bool(common),
        "budget_equality_pass": bool(budgets),
        "objective_correctness_pass": bool(np.isfinite(p3.objective_final).all()),
        "cvar_correctness_pass": bool(np.isfinite(p3.cvar_value).all()),
        "memory_accounting_pass": bool((frame.peak_memory_mb > 0).all()),
        "scaling_analysis_pipeline_pass": scaling_pipeline,
    }
    write_json(PREFLIGHT_SUMMARY, summary)
    if not required:
        raise RuntimeError("Phase-3 final-protocol preflight failed; STOP")
    return summary


def run_optimization_adequacy() -> pd.DataFrame:
    """Run frozen 2B sentinels after development and compare with reusable B rows."""
    if not SPLIT_RESULT_PATHS["development"].exists():
        raise RuntimeError("development matrix must complete before adequacy sentinels")
    verify_execution_identity()
    config = load_config(CONFIG_PATH)
    development = pd.read_csv(SPLIT_RESULT_PATHS["development"])
    manifest = load_manifest("development")
    characterization = characterization_lookup()
    settings = config["optimization_adequacy"]
    selected_items = []
    for size_m in settings["sizes"]:
        family = next(
            row for row in manifest["families"]
            if int(row["size_m"]) == int(size_m) and int(row["base_index"]) == int(settings["base_index"])
        )
        task_id = family["task_ids"][int(settings["dilution_level_index_zero_based"])]
        selected_items.append(next(row for row in manifest["tasks"] if row["task_id"] == task_id))
    receipt_root = RESULT_ROOT / "run_receipts" / "optimization_adequacy_2B"
    receipt_root.mkdir(parents=True, exist_ok=True)
    namespace = "phase3-optimization-adequacy-2B"
    selected_p2 = _select_p2(development).set_index("task_id")
    _, workers_by_size = _load_resource_policy()
    for item in selected_items:
        task = read_task(PROJECT_ROOT / item["task_path"])
        p2_row = selected_p2.loc[task.task_id].to_dict()
        missing = []
        for objective in config["p3_comparison"]["objective_ids"]:
            run_id = _run_id(namespace, task.task_id, "p3", objective, 480, sha256_file(CONFIG_PATH))
            if not _receipt_exists_valid(receipt_root, run_id):
                missing.append(objective)
        if missing:
            _run_parallel(
                [(task.to_dict(), characterization[task.task_id], p2_row, config, namespace, "development", "ADEQUACY_SENTINEL_2B", missing, 480, str(receipt_root))],
                _run_p3_batch,
                workers_by_size[int(item["size_m"])],
            )
    doubled = _assemble_receipts(receipt_root)
    atomic_write_csv(ADEQUACY_2B_PATH, doubled)
    primary = development[
        development.task_id.isin([item["task_id"] for item in selected_items])
        & development.objective_id.isin(["O0", "O2", "O3"])
    ]
    merged = primary.merge(
        doubled,
        on=["task_id", "objective_id"], suffixes=("_B", "_2B"), validate="one_to_one",
    )
    output = pd.DataFrame(
        {
            "task_id": merged.task_id,
            "base_graph_id": merged.base_graph_id_B,
            "size_m": merged.size_m_B.astype(int),
            "objective_id": merged.objective_id,
            "B": merged.eval_budget_B.astype(int),
            "two_B": merged.eval_budget_2B.astype(int),
            "G_feas_B": merged.log_feasibility_gain_B,
            "G_feas_2B": merged.log_feasibility_gain_2B,
            "Delta_G_budget": merged.log_feasibility_gain_2B - merged.log_feasibility_gain_B,
            "objective_B": merged.objective_final_B,
            "objective_2B": merged.objective_final_2B,
            "Delta_objective_budget": merged.objective_final_B - merged.objective_final_2B,
            "same_common_initialization": merged.p3_initial_parameters_B == merged.p3_initial_parameters_2B,
        }
    )
    threshold = float(settings["substantial_delta_G_decades"])
    output["substantial_budget_sensitivity"] = output.Delta_G_budget.abs() >= threshold
    output["optimizer_adequacy_flag"] = output.substantial_budget_sensitivity & output.size_m.isin([16, 18])
    atomic_write_csv(ADEQUACY_PATH, output)
    return output


def record_execution_provenance(stage: str, wall_time_s: float, details: dict[str, Any]) -> None:
    if EXECUTION_PROVENANCE.exists():
        payload = json.loads(EXECUTION_PROVENANCE.read_text(encoding="utf-8"))
    else:
        payload = {
            "host": socket.gethostname(), "platform": platform.platform(),
            "cpu": platform.processor(), "python": sys.version.replace("\n", " "),
            "numpy": np.__version__, "scipy": scipy.__version__,
            "available_ram_mb_at_start": _available_ram_mb(),
            "worker_blas_threads": int(load_config(CONFIG_PATH)["execution"]["worker_blas_threads"]),
            "stages": {},
        }
    payload["stages"][stage] = {"wall_time_s": wall_time_s, **details}
    payload["recorded_wall_time_s"] = sum(item["wall_time_s"] for item in payload["stages"].values())
    write_json(EXECUTION_PROVENANCE, payload)
