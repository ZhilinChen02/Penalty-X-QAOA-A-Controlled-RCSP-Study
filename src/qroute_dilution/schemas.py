"""Canonical result schema and row constructors."""

from __future__ import annotations

import hashlib
import json
import math
import resource
import time
from typing import Any

import numpy as np

from .metrics import probability_metrics, uniform_metrics
from .models import Task
from .optimizer import OptimizationTimeout, optimize_cobyla
from .penalties import EnergyComponents, build_diagonal_energies
from .qaoa import simulate_qaoa


EXECUTION_STATUSES = {
    "SUCCESS",
    "TIMEOUT",
    "OOM",
    "NO_FEASIBLE_ROUTE",
    "NO_FEASIBLE_STATE",
    "OPTIMIZER_FAILURE",
    "NUMERICAL_FAILURE",
    "ZERO_P_FEAS",
    "ZERO_P_OPT",
    "RESOURCE_CENSORED",
}

CANONICAL_FIELDS = [
    "run_id",
    "task_id",
    "graph_id",
    "base_instance_id",
    "size_stratum",
    "tightness_level",
    "seed",
    "algorithm",
    "depth",
    "n_nodes",
    "n_edges",
    "n_qubits",
    "resource_count",
    "budget",
    "n_candidate_routes",
    "n_feasible_routes",
    "route_feasible_fraction",
    "state_space_size",
    "n_feasible_states",
    "feasible_state_fraction",
    "n_optimal_states",
    "optimal_cost",
    "flow_penalty_strength",
    "resource_penalty_strength",
    "optimizer",
    "eval_budget",
    "initial_parameters",
    "optimized_parameters",
    "nfev",
    "status",
    "optimizer_message",
    "objective_initial",
    "objective_final",
    "expected_energy",
    "p_feas",
    "p_opt",
    "p_opt_given_feasible",
    "feasibility_amplification",
    "uniform_p_feas",
    "uniform_p_opt",
    "uniform_feasibility_amplification",
    "task_build_time_s",
    "exact_reference_time_s",
    "energy_build_time_s",
    "optimization_time_s",
    "optimizer_runtime_s",
    "total_time_s",
    "peak_memory_mb",
    "execution_status",
    "failure_reason",
    "zero_feasible",
    "zero_optimal_probability",
    "resource_censored",
]


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes.
    return float(value / 1024.0 if value < 10**9 else value / (1024.0**2))


def run_id_for(
    task_id: str,
    algorithm: str,
    depth: int,
    seed: int,
    flow_penalty_strength: float | None = None,
    resource_penalty_strength: float | None = None,
) -> str:
    payload = (
        f"{task_id}|{algorithm}|{depth}|{seed}|"
        f"{flow_penalty_strength}|{resource_penalty_strength}"
    )
    return "run-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def _base_row(task: Task, characterization: dict[str, Any]) -> dict[str, Any]:
    row = {field: math.nan for field in CANONICAL_FIELDS}
    row.update(
        {
            "task_id": task.task_id,
            "graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "tightness_level": task.tightness_level,
        }
    )
    for field in (
        "n_nodes",
        "n_edges",
        "n_qubits",
        "resource_count",
        "budget",
        "n_candidate_routes",
        "n_feasible_routes",
        "route_feasible_fraction",
        "state_space_size",
        "n_feasible_states",
        "feasible_state_fraction",
        "n_optimal_states",
        "optimal_cost",
        "task_build_time_s",
        "exact_reference_time_s",
        "zero_feasible",
    ):
        row[field] = characterization[field]
    row["failure_reason"] = ""
    row["resource_censored"] = False
    row["zero_optimal_probability"] = False
    row["energy_build_time_s"] = 0.0
    row["optimization_time_s"] = 0.0
    row["optimizer_runtime_s"] = 0.0
    return row


def _state_sets(task: Task) -> tuple[tuple[int, ...], tuple[int, ...]]:
    feasible = tuple(route.bitstring_int for route in task.feasible_routes)
    optimal = tuple(route.bitstring_int for route in task.optimal_routes)
    return feasible, optimal


def make_uniform_row(task: Task, characterization: dict[str, Any]) -> dict[str, Any]:
    row = _base_row(task, characterization)
    feasible, optimal = _state_sets(task)
    metrics = uniform_metrics(int(row["state_space_size"]), feasible, optimal)
    row.update(metrics)
    row.update(
        {
            "run_id": run_id_for(task.task_id, "Uniform", 0, 0),
            "seed": 0,
            "algorithm": "Uniform",
            "depth": 0,
            "optimizer": "analytic",
            "eval_budget": 0,
            "nfev": 0,
            "status": 0,
            "optimizer_message": "analytic uniform baseline",
            "uniform_p_feas": metrics["p_feas"],
            "uniform_p_opt": metrics["p_opt"],
            "uniform_feasibility_amplification": metrics["feasibility_amplification"],
            "total_time_s": 0.0,
            "peak_memory_mb": _peak_memory_mb(),
        }
    )
    if len(feasible) == 0:
        row["execution_status"] = "NO_FEASIBLE_STATE"
        row["failure_reason"] = (
            "NO_FEASIBLE_ROUTE; NO_FEASIBLE_STATE"
            if len(task.feasible_routes) == 0
            else "NO_FEASIBLE_STATE"
        )
    else:
        row["execution_status"] = "SUCCESS"
    row["zero_optimal_probability"] = bool(metrics["p_opt"] == 0.0)
    return canonicalize_row(row)


def make_resource_censored_row(
    task: Task,
    characterization: dict[str, Any],
    *,
    depth: int,
    seed: int,
    flow_penalty_strength: float,
    resource_penalty_strength: float,
    eval_budget: int,
) -> dict[str, Any]:
    row = _base_row(task, characterization)
    row.update(
        {
            "run_id": run_id_for(
                task.task_id,
                "Penalty-X",
                depth,
                seed,
                flow_penalty_strength,
                resource_penalty_strength,
            ),
            "seed": seed,
            "algorithm": "Penalty-X",
            "depth": depth,
            "flow_penalty_strength": flow_penalty_strength,
            "resource_penalty_strength": resource_penalty_strength,
            "optimizer": "COBYLA",
            "eval_budget": eval_budget,
            "execution_status": "RESOURCE_CENSORED",
            "failure_reason": "n_qubits exceeds configured exact-statevector limit",
            "resource_censored": True,
            "total_time_s": 0.0,
            "peak_memory_mb": _peak_memory_mb(),
        }
    )
    return canonicalize_row(row)


def run_penalty_x(
    task: Task,
    characterization: dict[str, Any],
    *,
    depth: int,
    seed: int,
    flow_penalty_strength: float,
    resource_penalty_strength: float,
    eval_budget: int,
    energy_components: EnergyComponents | None = None,
    energy_build_time_s: float | None = None,
    timeout_s: float | None = None,
) -> dict[str, Any]:
    total_started = time.perf_counter()
    row = _base_row(task, characterization)
    row.update(
        {
            "run_id": run_id_for(
                task.task_id,
                "Penalty-X",
                depth,
                seed,
                flow_penalty_strength,
                resource_penalty_strength,
            ),
            "seed": seed,
            "algorithm": "Penalty-X",
            "depth": depth,
            "flow_penalty_strength": flow_penalty_strength,
            "resource_penalty_strength": resource_penalty_strength,
            "optimizer": "COBYLA",
            "eval_budget": eval_budget,
        }
    )
    feasible, optimal = _state_sets(task)
    try:
        if energy_components is None:
            energy_started = time.perf_counter()
            energy_components = build_diagonal_energies(
                task.graph,
                task.budget,
                flow_penalty_strength,
                resource_penalty_strength,
            )
            energy_build_time_s = time.perf_counter() - energy_started
        row["energy_build_time_s"] = float(energy_build_time_s or 0.0)
        result = optimize_cobyla(
            energy_components.total, depth, seed, eval_budget, timeout_s=timeout_s
        )
        row.update(
            {
                "initial_parameters": json.dumps(result.initial_parameters.tolist()),
                "optimized_parameters": json.dumps(result.optimized_parameters.tolist()),
                "nfev": result.nfev,
                "status": result.status,
                "optimizer_message": result.message,
                "objective_initial": result.objective_initial,
                "objective_final": result.objective_final,
                "expected_energy": result.objective_final,
                "optimization_time_s": result.runtime_s,
                "optimizer_runtime_s": result.runtime_s,
            }
        )
        if not result.success:
            row["execution_status"] = "OPTIMIZER_FAILURE"
            row["failure_reason"] = "non-finite optimizer result"
        else:
            state = simulate_qaoa(
                result.optimized_parameters, energy_components.total, depth
            )
            probabilities = np.abs(state) ** 2
            metrics = probability_metrics(
                probabilities,
                feasible,
                optimal,
                float(row["feasible_state_fraction"]),
            )
            row.update(metrics)
            row["uniform_p_feas"] = float(row["feasible_state_fraction"])
            row["uniform_p_opt"] = len(optimal) / int(row["state_space_size"])
            row["uniform_feasibility_amplification"] = (
                1.0 if float(row["feasible_state_fraction"]) > 0 else math.nan
            )
            if len(feasible) == 0:
                row["execution_status"] = "NO_FEASIBLE_STATE"
                row["failure_reason"] = "NO_FEASIBLE_STATE"
            elif metrics["p_feas"] <= np.finfo(float).tiny:
                row["execution_status"] = "ZERO_P_FEAS"
                row["failure_reason"] = "ZERO_P_FEAS"
            elif metrics["p_opt"] <= np.finfo(float).tiny:
                row["execution_status"] = "ZERO_P_OPT"
                row["failure_reason"] = "ZERO_P_OPT"
            else:
                row["execution_status"] = "SUCCESS"
            row["zero_optimal_probability"] = bool(
                metrics["p_opt"] <= np.finfo(float).tiny
            )
    except OptimizationTimeout as exc:
        row["execution_status"] = "TIMEOUT"
        row["failure_reason"] = str(exc)
    except MemoryError as exc:
        row["execution_status"] = "OOM"
        row["failure_reason"] = str(exc) or "MemoryError"
    except FloatingPointError as exc:
        row["execution_status"] = "NUMERICAL_FAILURE"
        row["failure_reason"] = str(exc)
    except Exception as exc:  # experiment rows preserve unexpected run failures
        row["execution_status"] = "OPTIMIZER_FAILURE"
        row["failure_reason"] = f"{type(exc).__name__}: {exc}"
    row["total_time_s"] = time.perf_counter() - total_started
    row["peak_memory_mb"] = _peak_memory_mb()
    return canonicalize_row(row)


def canonicalize_row(row: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in CANONICAL_FIELDS if field not in row]
    if missing:
        raise ValueError(f"row missing canonical fields: {missing}")
    status = row["execution_status"]
    if status not in EXECUTION_STATUSES:
        raise ValueError(f"unknown execution_status: {status}")
    return {field: row[field] for field in CANONICAL_FIELDS}
