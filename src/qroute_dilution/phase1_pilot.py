"""Frozen, resume-safe scale-controlled Phase 1 pilot execution."""

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
from typing import Any

import numpy as np
import pandas as pd
import scipy

from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json
from .metrics import dilution_score, probability_metrics, uniform_metrics
from .models import Task
from .optimizer import OptimizationTimeout, optimize_cobyla
from .penalties import build_raw_state_components, scale_controlled_penalties
from .qaoa import simulate_qaoa
from .schemas import CANONICAL_FIELDS


PILOT_CONFIG = PROJECT_ROOT / "configs" / "phase1_pilot_v1.yaml"
PILOT_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase1_pilot_v1.json"
RESULT_ROOT = PROJECT_ROOT / "results" / "phase1_pilot_v1"
MASTER_RESULTS = RESULT_ROOT / "master_seed_level_results.csv"

ADDITIONAL_FIELDS = [
    "base_graph_id",
    "stress_level",
    "optimizer_seed",
    "dilution_score",
    "log_feasibility_gain",
    "uniform_log_feasibility_gain",
    "expected_energy_normalized",
    "expected_energy_raw",
    "objective_initial_raw",
    "objective_final_raw",
    "objective_improvement",
    "optimizer_status",
    "hamiltonian_normalization_mode",
    "hamiltonian_normalization_factor",
    "raw_energy_span",
    "normalized_energy_span",
    "penalty_contract",
    "state_norm",
    "row_type",
]
PILOT_FIELDS = [*CANONICAL_FIELDS, *[field for field in ADDITIONAL_FIELDS if field not in CANONICAL_FIELDS]]


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sort_stress(value: str) -> int:
    return int(value[1:])


def freeze_pilot_manifest() -> dict[str, Any]:
    config = load_config(PILOT_CONFIG)
    source = json.loads((PROJECT_ROOT / config["source_task_manifest"]).read_text(encoding="utf-8"))
    size_order = list(load_config(PROJECT_ROOT / "configs" / "phase0_v2_dilution_stress.yaml")["size_strata"])
    family_lookup = {family["base_instance_id"]: family for family in source["families"]}
    selected_bases: dict[str, list[str]] = {}
    for size in size_order:
        families = sorted(
            (family for family in source["families"] if family["size_stratum"] == size),
            key=lambda family: (int(family["base_index"]), family["base_instance_id"]),
        )
        selected_bases[size] = [
            family["base_instance_id"] for family in families[: int(config["base_graphs_per_size"])]
        ]
    selected_set = {base for bases in selected_bases.values() for base in bases}
    tasks = [task for task in source["tasks"] if task["base_instance_id"] in selected_set]
    size_rank = {size: index for index, size in enumerate(size_order)}
    tasks.sort(
        key=lambda task: (
            size_rank[task["size_stratum"]],
            int(task["base_index"]),
            _sort_stress(task["stress_level"]),
            task["task_id"],
        )
    )
    expected_by_size = {"S1": 6, "S2": 8, "S3": 14, "S4": 14, "S5": 14}
    observed_by_size = pd.Series([task["size_stratum"] for task in tasks]).value_counts().to_dict()
    if observed_by_size != expected_by_size or len(tasks) != int(config["expected_task_count"]):
        raise AssertionError(
            f"trajectory selection mismatch: observed={observed_by_size}, expected={expected_by_size}"
        )
    for base in selected_set:
        expected_levels = int(family_lookup[base]["effective_distinct_stress_levels"])
        actual_levels = sum(task["base_instance_id"] == base for task in tasks)
        if actual_levels != expected_levels:
            raise AssertionError(f"incomplete within-base trajectory for {base}")
    payload = {
        "schema_version": "phase1_pilot_v1.manifest.v1",
        "pre_run_git_sha": config["pre_run_git_sha"],
        "source_manifest": config["source_task_manifest"],
        "selection_rule": config["selection_rule"],
        "selected_base_graphs": selected_bases,
        "task_count": len(tasks),
        "task_counts_by_size": expected_by_size,
        "depths": config["depths"],
        "optimizer_seeds": config["optimizer_seeds"],
        "planned_optimized_run_count": len(tasks)
        * len(config["depths"])
        * len(config["optimizer_seeds"]),
        "planned_uniform_row_count": len(tasks),
        "tasks": tasks,
    }
    write_json(PILOT_MANIFEST, payload)
    return payload


def freeze_execution_identity() -> dict[str, Any]:
    manifest = freeze_pilot_manifest()
    config = load_config(PILOT_CONFIG)
    largest_qubits = max(
        len(read_task(PROJECT_ROOT / task["task_path"]).graph.edges)
        for task in manifest["tasks"]
    )
    largest_states = 1 << largest_qubits
    identity = {
        "pre_run_git_sha": config["pre_run_git_sha"],
        "manifest_sha256": sha256_file(PILOT_MANIFEST),
        "config_sha256": sha256_file(PILOT_CONFIG),
        "manifest_path": str(PILOT_MANIFEST.relative_to(PROJECT_ROOT)),
        "config_path": str(PILOT_CONFIG.relative_to(PROJECT_ROOT)),
        "task_count": manifest["task_count"],
        "planned_optimized_run_count": manifest["planned_optimized_run_count"],
        "planned_uniform_row_count": manifest["planned_uniform_row_count"],
        "pre_execution_resource_estimate": {
            "largest_n_qubits": largest_qubits,
            "largest_state_space_size": largest_states,
            "largest_complex128_statevector_mb": largest_states * 16 / (1024**2),
            "conservative_peak_per_worker_mb": 320.0,
            "configured_max_workers": int(config["max_workers"]),
            "conservative_aggregate_worker_memory_mb": 320.0 * int(config["max_workers"]),
            "raw_statevectors_persisted": False,
        },
        "manifest": manifest,
    }
    write_json(RESULT_ROOT / "manifest_snapshot.json", identity)
    return identity


def load_frozen_identity() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    snapshot = json.loads((RESULT_ROOT / "manifest_snapshot.json").read_text(encoding="utf-8"))
    if sha256_file(PILOT_MANIFEST) != snapshot["manifest_sha256"]:
        raise RuntimeError("pilot manifest hash changed after freeze")
    if sha256_file(PILOT_CONFIG) != snapshot["config_sha256"]:
        raise RuntimeError("pilot config hash changed after freeze")
    config = load_config(PILOT_CONFIG)
    manifest = json.loads(PILOT_MANIFEST.read_text(encoding="utf-8"))
    return snapshot, config, manifest


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / 1024.0 if value < 10**9 else value / (1024.0**2))


def _run_id(
    task_id: str,
    algorithm: str,
    depth: int,
    seed: int,
    config_sha256: str,
) -> str:
    payload = f"phase1_pilot_v1|{task_id}|{algorithm}|{depth}|{seed}|{config_sha256}"
    return "pilot-run-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _energy_arrays(task: Task, normalization_factor: float):
    components = build_raw_state_components(task.graph)
    resource_excess = np.maximum(0.0, components.resource_total - task.budget)
    flow_scale = max(float(components.flow_penalty_raw.max()), 1.0)
    resource_scale = float(sum(edge.resource for edge in task.graph.edges))
    controlled_flow, controlled_resource = scale_controlled_penalties(
        components.flow_penalty_raw,
        resource_excess,
        flow_scale=flow_scale,
        resource_scale=resource_scale,
    )
    raw = components.routing_cost + 172.0 * controlled_flow + 172.0 * controlled_resource
    normalized = raw / normalization_factor
    return components, raw, normalized, controlled_flow, controlled_resource


def verify_global_normalization() -> pd.DataFrame:
    _, config, _ = load_frozen_identity()
    source_manifest = json.loads(
        (PROJECT_ROOT / config["source_task_manifest"]).read_text(encoding="utf-8")
    )
    char = pd.read_csv(
        PROJECT_ROOT / "results" / "phase0_v2_dilution_stress" / "task_characterization.csv"
    ).set_index("task_id")
    tasks = [read_task(PROJECT_ROOT / row["task_path"]) for row in source_manifest["tasks"]]
    rows = []
    by_base: dict[str, list[Task]] = {}
    for task in tasks:
        by_base.setdefault(task.base_instance_id, []).append(task)
    factor = float(config["hamiltonian_normalization_factor"])
    for family in by_base.values():
        components = build_raw_state_components(family[0].graph)
        flow_scale = max(float(components.flow_penalty_raw.max()), 1.0)
        resource_scale = float(sum(edge.resource for edge in family[0].graph.edges))
        controlled_flow, _ = scale_controlled_penalties(
            components.flow_penalty_raw,
            np.zeros_like(components.resource_total),
            flow_scale=flow_scale,
            resource_scale=resource_scale,
        )
        for task in family:
            excess = np.maximum(0.0, components.resource_total - task.budget)
            _, controlled_resource = scale_controlled_penalties(
                components.flow_penalty_raw,
                excess,
                flow_scale=flow_scale,
                resource_scale=resource_scale,
            )
            raw = components.routing_cost + 172.0 * controlled_flow + 172.0 * controlled_resource
            normalized = raw / factor
            raw_argmin = np.flatnonzero(raw == raw.min())
            normalized_argmin = np.flatnonzero(normalized == normalized.min())
            exact_states = {route.bitstring_int for route in task.optimal_routes}
            rows.append(
                {
                    "task_id": task.task_id,
                    "base_graph_id": task.graph.graph_id,
                    "size_stratum": task.size_stratum,
                    "stress_level": task.tightness_level,
                    "raw_normalized_argmin_identical": bool(
                        np.array_equal(raw_argmin, normalized_argmin)
                    ),
                    "normalized_ground_state_exact_original_optimal": bool(
                        set(map(int, normalized_argmin)) == exact_states
                    ),
                    "flow_classification_unchanged": bool(
                        np.array_equal(controlled_flow > 0.0, components.flow_penalty_raw > 0.0)
                    ),
                    "resource_classification_unchanged": bool(
                        np.array_equal(controlled_resource > 0.0, excess > 0.0)
                    ),
                    "feasible_state_fraction": float(char.loc[task.task_id, "feasible_state_fraction"]),
                    "dilution_score": float(char.loc[task.task_id, "dilution_score"]),
                    "raw_energy_span": float(raw.max() - raw.min()),
                    "normalized_energy_span": float(normalized.max() - normalized.min()),
                }
            )
    frame = pd.DataFrame(rows)
    required = [
        "raw_normalized_argmin_identical",
        "normalized_ground_state_exact_original_optimal",
        "flow_classification_unchanged",
        "resource_classification_unchanged",
    ]
    atomic_write_csv(RESULT_ROOT / "analysis" / "normalization_preflight.csv", frame)
    if len(frame) != 140 or not frame[required].all().all():
        raise RuntimeError("global normalization preflight failed; Phase 1 must not execute")
    return frame


def _base_row(
    task: Task,
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_sha256: str,
    *,
    algorithm: str,
    depth: int,
    seed: int,
) -> dict[str, Any]:
    row = {field: math.nan for field in PILOT_FIELDS}
    row.update(
        {
            "run_id": _run_id(task.task_id, algorithm, depth, seed, config_sha256),
            "task_id": task.task_id,
            "graph_id": task.graph.graph_id,
            "base_graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "tightness_level": task.tightness_level,
            "stress_level": task.tightness_level,
            "seed": seed,
            "optimizer_seed": seed,
            "algorithm": algorithm,
            "depth": depth,
            "n_nodes": task.graph.n_nodes,
            "n_edges": len(task.graph.edges),
            "n_qubits": len(task.graph.edges),
            "resource_count": 1,
            "budget": task.budget,
            "n_candidate_routes": int(characterization["n_candidate_routes"]),
            "n_feasible_routes": int(characterization["n_feasible_routes"]),
            "route_feasible_fraction": float(characterization["route_feasible_fraction"]),
            "state_space_size": int(characterization["state_space_size"]),
            "n_feasible_states": int(characterization["n_feasible_states"]),
            "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
            "dilution_score": float(characterization["dilution_score"]),
            "n_optimal_states": int(characterization["n_optimal_states"]),
            "optimal_cost": float(characterization["optimal_cost"]),
            "flow_penalty_strength": float(config["flow_penalty_strength_raw"]),
            "resource_penalty_strength": float(config["resource_penalty_strength_raw"]),
            "optimizer": "analytic" if algorithm == "Uniform" else config["optimizer"],
            "eval_budget": 0 if algorithm == "Uniform" else int(config["eval_budget"]),
            "task_build_time_s": float(characterization["task_build_time_s"]),
            "exact_reference_time_s": float(characterization["exact_reference_time_s"]),
            "energy_build_time_s": 0.0,
            "optimization_time_s": 0.0,
            "optimizer_runtime_s": 0.0,
            "total_time_s": 0.0,
            "failure_reason": "",
            "zero_feasible": bool(characterization["zero_feasible"]),
            "zero_optimal_probability": False,
            "resource_censored": False,
            "hamiltonian_normalization_mode": config["hamiltonian_normalization_mode"],
            "hamiltonian_normalization_factor": float(
                config["hamiltonian_normalization_factor"]
            ),
            "penalty_contract": config["penalty_contract"],
            "row_type": "analytic_uniform" if algorithm == "Uniform" else "optimized_seed",
        }
    )
    return row


def _state_sets(task: Task) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return (
        tuple(route.bitstring_int for route in task.feasible_routes),
        tuple(route.bitstring_int for route in task.optimal_routes),
    )


def make_uniform_pilot_row(
    task: Task, characterization: dict[str, Any], config: dict[str, Any], config_sha256: str
) -> dict[str, Any]:
    row = _base_row(
        task,
        characterization,
        config,
        config_sha256,
        algorithm="Uniform",
        depth=0,
        seed=0,
    )
    feasible, optimal = _state_sets(task)
    metrics = uniform_metrics(1 << len(task.graph.edges), feasible, optimal)
    row.update(metrics)
    row.update(
        {
            "uniform_p_feas": metrics["p_feas"],
            "uniform_p_opt": metrics["p_opt"],
            "uniform_feasibility_amplification": 1.0,
            "uniform_log_feasibility_gain": 0.0,
            "log_feasibility_gain": 0.0,
            "nfev": 0,
            "status": 0,
            "optimizer_status": 0,
            "optimizer_message": "analytic uniform baseline",
            "execution_status": "SUCCESS",
            "peak_memory_mb": _peak_memory_mb(),
        }
    )
    return {field: row[field] for field in PILOT_FIELDS}


def _run_failure_status(exc: Exception) -> str:
    if isinstance(exc, OptimizationTimeout):
        return "TIMEOUT"
    if isinstance(exc, MemoryError):
        return "OOM"
    if isinstance(exc, FloatingPointError):
        return "NUMERICAL_FAILURE"
    return "OPTIMIZER_FAILURE"


def _run_one(
    task: Task,
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_sha256: str,
    depth: int,
    seed: int,
    raw_energy: np.ndarray,
    normalized_energy: np.ndarray,
    energy_build_time_s: float,
) -> dict[str, Any]:
    total_started = time.perf_counter()
    row = _base_row(
        task,
        characterization,
        config,
        config_sha256,
        algorithm="Penalty-X",
        depth=depth,
        seed=seed,
    )
    row["energy_build_time_s"] = energy_build_time_s
    row["raw_energy_span"] = float(raw_energy.max() - raw_energy.min())
    row["normalized_energy_span"] = float(normalized_energy.max() - normalized_energy.min())
    feasible, optimal = _state_sets(task)
    try:
        result = optimize_cobyla(
            normalized_energy,
            depth,
            seed,
            int(config["eval_budget"]),
            timeout_s=float(config["timeout_s"]),
        )
        row.update(
            {
                "initial_parameters": json.dumps(result.initial_parameters.tolist()),
                "optimized_parameters": json.dumps(result.optimized_parameters.tolist()),
                "nfev": result.nfev,
                "status": result.status,
                "optimizer_status": result.status,
                "optimizer_message": result.message,
                "objective_initial": result.objective_initial,
                "objective_final": result.objective_final,
                "objective_initial_raw": result.objective_initial
                * float(config["hamiltonian_normalization_factor"]),
                "objective_final_raw": result.objective_final
                * float(config["hamiltonian_normalization_factor"]),
                "objective_improvement": result.objective_initial - result.objective_final,
                "optimization_time_s": result.runtime_s,
                "optimizer_runtime_s": result.runtime_s,
            }
        )
        if not result.success:
            raise FloatingPointError("non-finite optimizer result")
        state = simulate_qaoa(result.optimized_parameters, normalized_energy, depth)
        probabilities = np.abs(state) ** 2
        norm = float(np.sum(probabilities))
        metrics = probability_metrics(
            probabilities,
            feasible,
            optimal,
            float(characterization["feasible_state_fraction"]),
        )
        expected_normalized = float(np.dot(probabilities, normalized_energy))
        expected_raw = float(np.dot(probabilities, raw_energy))
        row.update(metrics)
        row.update(
            {
                "expected_energy": expected_normalized,
                "expected_energy_normalized": expected_normalized,
                "expected_energy_raw": expected_raw,
                "uniform_p_feas": float(characterization["feasible_state_fraction"]),
                "uniform_p_opt": len(optimal) / (1 << len(task.graph.edges)),
                "uniform_feasibility_amplification": 1.0,
                "uniform_log_feasibility_gain": 0.0,
                "state_norm": norm,
                "execution_status": "SUCCESS",
            }
        )
        if metrics["p_feas"] <= np.finfo(float).tiny:
            row["execution_status"] = "ZERO_P_FEAS"
            row["failure_reason"] = "ZERO_P_FEAS"
        elif metrics["p_opt"] <= np.finfo(float).tiny:
            row["execution_status"] = "ZERO_P_OPT"
            row["failure_reason"] = "ZERO_P_OPT"
        row["zero_optimal_probability"] = bool(metrics["p_opt"] <= np.finfo(float).tiny)
    except Exception as exc:
        row["execution_status"] = _run_failure_status(exc)
        row["failure_reason"] = f"{type(exc).__name__}: {exc}"
    row["total_time_s"] = time.perf_counter() - total_started
    row["peak_memory_mb"] = _peak_memory_mb()
    return {field: row[field] for field in PILOT_FIELDS}


def _worker_task_batch(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    config: dict[str, Any],
    config_sha256: str,
    run_pairs: list[tuple[int, int]],
) -> list[dict[str, Any]]:
    task = Task.from_dict(task_payload)
    try:
        energy_started = time.perf_counter()
        _, raw, normalized, _, _ = _energy_arrays(
            task, float(config["hamiltonian_normalization_factor"])
        )
        energy_time = time.perf_counter() - energy_started
        return [
            _run_one(
                task,
                characterization,
                config,
                config_sha256,
                depth,
                seed,
                raw,
                normalized,
                energy_time,
            )
            for depth, seed in run_pairs
        ]
    except Exception as exc:
        rows = []
        for depth, seed in run_pairs:
            row = _base_row(
                task,
                characterization,
                config,
                config_sha256,
                algorithm="Penalty-X",
                depth=depth,
                seed=seed,
            )
            row["execution_status"] = _run_failure_status(exc)
            row["failure_reason"] = f"energy build: {type(exc).__name__}: {exc}"
            row["peak_memory_mb"] = _peak_memory_mb()
            rows.append({field: row[field] for field in PILOT_FIELDS})
        return rows


def append_pilot_rows(path: str | Path, rows: list[dict[str, Any]]) -> pd.DataFrame:
    path = Path(path)
    new = pd.DataFrame(rows, columns=PILOT_FIELDS)
    if path.exists():
        existing = pd.read_csv(path)
        missing = set(PILOT_FIELDS) - set(existing.columns)
        if missing:
            raise ValueError(f"pilot result schema mismatch: {sorted(missing)}")
        known = set(existing.run_id.astype(str))
        new = new[~new.run_id.astype(str).isin(known)]
        frame = pd.concat([existing[PILOT_FIELDS], new], ignore_index=True)
    else:
        frame = new
    atomic_write_csv(path, frame)
    return frame


def run_execution_preflight() -> dict[str, Any]:
    snapshot, config, manifest = load_frozen_identity()
    char = pd.read_csv(
        PROJECT_ROOT / "results" / "phase0_v2_dilution_stress" / "task_characterization.csv"
    ).set_index("task_id").to_dict(orient="index")
    selected = manifest["tasks"][:2]
    rows = []
    for task_row in selected:
        task = read_task(PROJECT_ROOT / task_row["task_path"])
        rows.extend(
            _worker_task_batch(
                task.to_dict(),
                char[task.task_id],
                config,
                snapshot["config_sha256"],
                [(1, int(config["optimizer_seeds"][0]))],
            )
        )
    path = RESULT_ROOT / "analysis" / "preflight_results.csv"
    first = append_pilot_rows(path, rows)
    second = append_pilot_rows(path, rows)
    resume_ok = len(first) == len(second) == 2
    finite_ok = bool(np.isfinite(second.objective_final).all())
    norm_ok = bool(np.allclose(second.state_norm, 1.0, atol=1e-10))
    bookkeeping_ok = bool(
        np.allclose(
            second.expected_energy_raw,
            second.expected_energy_normalized
            * float(config["hamiltonian_normalization_factor"]),
            rtol=1e-11,
            atol=1e-9,
        )
    )
    probe = dict(rows[0])
    probe["run_id"] = "preflight-synthetic-failure-retention-probe"
    probe["execution_status"] = "OPTIMIZER_FAILURE"
    probe["failure_reason"] = "synthetic preflight persistence probe; not a scientific run"
    probe_path = RESULT_ROOT / "analysis" / "preflight_failure_retention_probe.csv"
    retained = append_pilot_rows(probe_path, [probe])
    failure_retention_ok = bool(
        len(retained) == 1 and retained.execution_status.iloc[0] == "OPTIMIZER_FAILURE"
    )
    status_ok = bool((second.execution_status == "SUCCESS").all())
    summary = {
        "task_count": 2,
        "depths": [1],
        "optimizer_seeds": [int(config["optimizer_seeds"][0])],
        "final_contract": config["penalty_contract"],
        "normalization_factor": config["hamiltonian_normalization_factor"],
        "objective_finite": finite_ok,
        "norm_preserved": norm_ok,
        "canonical_row_writing": len(second) == 2,
        "resume_behavior": resume_ok,
        "failure_retention": failure_retention_ok,
        "normalized_raw_bookkeeping": bookkeeping_ok,
        "execution_success": status_ok,
        "passed": all(
            [
                finite_ok,
                norm_ok,
                resume_ok,
                failure_retention_ok,
                bookkeeping_ok,
                status_ok,
            ]
        ),
    }
    write_json(RESULT_ROOT / "analysis" / "preflight_summary.json", summary)
    if not summary["passed"]:
        raise RuntimeError("execution preflight failed; frozen 504-run pilot must not start")
    return summary


def _provenance(config: dict[str, Any]) -> dict[str, Any]:
    cpu_model = "unknown"
    physical_cores: set[tuple[str, str]] = set()
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        physical_id = core_id = None
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines() + [""]:
            if line.startswith("model name") and cpu_model == "unknown":
                cpu_model = line.split(":", 1)[1].strip()
            elif line.startswith("physical id"):
                physical_id = line.split(":", 1)[1].strip()
            elif line.startswith("core id"):
                core_id = line.split(":", 1)[1].strip()
            elif not line and physical_id is not None and core_id is not None:
                physical_cores.add((physical_id, core_id))
                physical_id = core_id = None
    return {
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_model": cpu_model,
        "cpu_count_physical": len(physical_cores) or None,
        "cpu_count_logical": os.cpu_count(),
        "python_version": sys.version.replace("\n", " "),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "max_workers": int(config["max_workers"]),
        "worker_blas_threads": int(config["worker_blas_threads"]),
        "implementation_device": "CPU NumPy",
    }


def run_frozen_pilot() -> tuple[pd.DataFrame, dict[str, Any]]:
    snapshot, config, manifest = load_frozen_identity()
    normalization = pd.read_csv(RESULT_ROOT / "analysis" / "normalization_preflight.csv")
    if len(normalization) != 140 or not normalization[
        [
            "raw_normalized_argmin_identical",
            "normalized_ground_state_exact_original_optimal",
            "flow_classification_unchanged",
            "resource_classification_unchanged",
        ]
    ].all().all():
        raise RuntimeError("normalization verification missing or failed")
    preflight = json.loads(
        (RESULT_ROOT / "analysis" / "preflight_summary.json").read_text(encoding="utf-8")
    )
    if not preflight["passed"]:
        raise RuntimeError("execution preflight did not pass")
    os.environ["OMP_NUM_THREADS"] = str(config["worker_blas_threads"])
    os.environ["OPENBLAS_NUM_THREADS"] = str(config["worker_blas_threads"])
    os.environ["MKL_NUM_THREADS"] = str(config["worker_blas_threads"])
    char = pd.read_csv(
        PROJECT_ROOT / "results" / "phase0_v2_dilution_stress" / "task_characterization.csv"
    ).set_index("task_id").to_dict(orient="index")
    tasks = [read_task(PROJECT_ROOT / row["task_path"]) for row in manifest["tasks"]]

    uniform_rows = [
        make_uniform_pilot_row(task, char[task.task_id], config, snapshot["config_sha256"])
        for task in tasks
    ]
    frame = append_pilot_rows(MASTER_RESULTS, uniform_rows)
    known = set(frame.run_id.astype(str))
    work = []
    for task in tasks:
        pending = [
            (int(depth), int(seed))
            for depth in config["depths"]
            for seed in config["optimizer_seeds"]
            if _run_id(
                task.task_id,
                "Penalty-X",
                int(depth),
                int(seed),
                snapshot["config_sha256"],
            )
            not in known
        ]
        if pending:
            work.append((task, pending))
    started = time.perf_counter()
    if work:
        with ProcessPoolExecutor(max_workers=int(config["max_workers"])) as executor:
            futures = {
                executor.submit(
                    _worker_task_batch,
                    task.to_dict(),
                    char[task.task_id],
                    config,
                    snapshot["config_sha256"],
                    pending,
                ): (task, pending)
                for task, pending in work
            }
            for future in as_completed(futures):
                task, pending = futures[future]
                try:
                    rows = future.result()
                except BaseException as exc:
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    rows = []
                    for depth, seed in pending:
                        row = _base_row(
                            task,
                            char[task.task_id],
                            config,
                            snapshot["config_sha256"],
                            algorithm="Penalty-X",
                            depth=depth,
                            seed=seed,
                        )
                        row["execution_status"] = _run_failure_status(exc)
                        row["failure_reason"] = f"worker failure: {type(exc).__name__}: {exc}"
                        row["peak_memory_mb"] = _peak_memory_mb()
                        rows.append({field: row[field] for field in PILOT_FIELDS})
                frame = append_pilot_rows(MASTER_RESULTS, rows)
    elapsed = time.perf_counter() - started
    frame = pd.read_csv(MASTER_RESULTS)
    task_order = {task["task_id"]: index for index, task in enumerate(manifest["tasks"])}
    frame["_task_order"] = frame.task_id.map(task_order)
    frame = frame.sort_values(
        ["_task_order", "algorithm", "depth", "optimizer_seed"],
        key=lambda series: series.map({"Uniform": 0, "Penalty-X": 1})
        if series.name == "algorithm"
        else series,
    ).drop(columns="_task_order")
    atomic_write_csv(MASTER_RESULTS, frame[PILOT_FIELDS])
    execution = {
        "new_execution_wall_time_s": elapsed,
        "total_rows": int(len(frame)),
        "uniform_rows": int((frame.algorithm == "Uniform").sum()),
        "optimized_rows": int((frame.algorithm == "Penalty-X").sum()),
        "provenance": _provenance(config),
    }
    provenance_path = RESULT_ROOT / "analysis" / "execution_provenance.json"
    if not work and provenance_path.exists():
        execution = json.loads(provenance_path.read_text(encoding="utf-8"))
    else:
        write_json(provenance_path, execution)
    return frame, execution
