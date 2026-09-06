"""Immutable, resume-safe execution for the Phase 1.2 objective diagnostic."""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json
from .metrics import probability_metrics
from .models import Task
from .phase1_1_diagnostic import build_evaluation_context, embed_p2_in_p3
from .phase1_pilot import sha256_file
from .qaoa import simulate_qaoa
from .phase1_2_objectives import (
    OBJECTIVE_IDENTITIES,
    exact_feasibility_objective,
    expected_penalty_objective,
    feasibility_penalty_bound,
    optimize_cobyla_objective,
    weighted_exact_cvar,
)


CONFIG_PATH = PROJECT_ROOT / "configs" / "phase1_2_objective_alignment.yaml"
RESULT_ROOT = PROJECT_ROOT / "results" / "phase1_2_objective_alignment"
OBJECTIVE_RESULTS_PATH = RESULT_ROOT / "objective_results.csv"
IDENTITY_PATH = RESULT_ROOT / "execution_identity.json"
IMMUTABLE_HASH_PATH = RESULT_ROOT / "immutable_evidence_sha256.json"
THEORETICAL_AUDIT_PATH = RESULT_ROOT / "feasibility_penalty_bound_audit.csv"
PREFLIGHT_PATH = RESULT_ROOT / "preflight_summary.json"


RESULT_FIELDS = [
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
    "objective_start",
    "objective_final",
    "objective_improvement",
    "mean_energy",
    "expected_routing_component",
    "expected_flow_penalty",
    "expected_resource_penalty",
    "expected_total_penalty",
    "p_feas",
    "p_opt",
    "p_opt_given_feasible",
    "feasibility_amplification",
    "log_feasibility_gain",
    "expected_route_cost_given_feasible",
    "cvar_alpha",
    "cvar_value",
    "cvar_cutoff_energy",
    "cvar_tail_fully_feasible",
    "cvar_tail_feasible_mass",
    "cvar_fractional_cutoff_mass",
    "penalty_bound_lower_margin",
    "penalty_bound_upper_margin",
    "penalty_bound_pass",
    "state_norm",
    "depth",
    "optimizer",
    "eval_budget",
    "source_p2_seed",
    "source_p2_objective_final",
    "initialization_rule",
    "initial_parameters",
    "terminal_parameters",
    "best_evaluated_parameters",
    "nfev",
    "tracked_optimizer_evaluations",
    "total_objective_evaluations",
    "runtime_s",
    "terminal_objective",
    "best_evaluated_objective",
    "optimizer_status",
    "optimizer_message",
    "scipy_success",
    "numerically_valid",
    "execution_status",
    "failure_reason",
    "historical_reuse",
    "historical_source_path",
    "historical_source_run_id",
    "config_sha256",
    "source_results_sha256",
    "ansatz_cost_phase_hamiltonian",
    "raw_statevector_persisted",
    "peak_memory_mb",
]


def _peak_memory_mb() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return float(value / 1024.0 if value < 10**9 else value / (1024.0**2))


def _parse_parameters(value: str | list[float]) -> np.ndarray:
    return np.asarray(json.loads(value) if isinstance(value, str) else value, dtype=np.float64)


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


def selected_p2_rows(pilot: pd.DataFrame) -> pd.DataFrame:
    """Select one p=2 seed per task using frozen objective_final only."""
    p2 = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 2)].copy()
    return (
        p2.sort_values(
            ["task_id", "objective_final", "optimizer_seed"], kind="stable"
        )
        .groupby("task_id", as_index=False, sort=False)
        .first()
    )


def freeze_execution_identity() -> dict[str, Any]:
    """Freeze source evidence and objective-selected initializations before execution."""
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
            f"Phase 1.2 must freeze at {config['pre_run_git_sha']}; observed {observed_head}"
        )
    pilot_path = PROJECT_ROOT / config["source_pilot_results"]
    manifest_path = PROJECT_ROOT / config["source_pilot_manifest"]
    pilot = pd.read_csv(pilot_path)
    selected = selected_p2_rows(pilot)
    if len(selected) != int(config["expected_task_count"]):
        raise RuntimeError("objective-selected p2 task denominator changed")
    frozen_initializations = []
    for row in selected.itertuples(index=False):
        initial = embed_p2_in_p3(_parse_parameters(row.optimized_parameters))
        frozen_initializations.append(
            {
                "task_id": row.task_id,
                "source_p2_seed": int(row.optimizer_seed),
                "source_p2_objective_final": float(row.objective_final),
                "embedded_p3_parameters": initial.tolist(),
            }
        )
    historical_hashes = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in _immutable_files(config)
    }
    write_json(
        IMMUTABLE_HASH_PATH,
        {
            "frozen_commit": observed_head,
            "file_count": len(historical_hashes),
            "files": historical_hashes,
        },
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    identity = {
        "evidence_identity": config["evidence_identity"],
        "pre_run_git_sha": observed_head,
        "config_sha256": sha256_file(CONFIG_PATH),
        "pilot_manifest_sha256": sha256_file(manifest_path),
        "pilot_results_sha256": sha256_file(pilot_path),
        "phase1_1_b2_results_sha256": sha256_file(
            PROJECT_ROOT / config["source_phase1_1_b2_results"]
        ),
        "historical_hash_manifest": str(IMMUTABLE_HASH_PATH.relative_to(PROJECT_ROOT)),
        "historical_file_count": len(historical_hashes),
        "task_count": manifest["task_count"],
        "objective_ids": list(config["objectives"]),
        "new_optimization_run_count": 168,
        "reused_O0_run_count": 56,
        "objective_eval_budget": int(config["objective_eval_budget"]),
        "frozen_initializations": frozen_initializations,
    }
    write_json(IDENTITY_PATH, identity)
    return identity


def verify_historical_immutability() -> dict[str, str]:
    frozen = json.loads(IMMUTABLE_HASH_PATH.read_text(encoding="utf-8"))
    observed = {
        path: sha256_file(PROJECT_ROOT / path) for path in sorted(frozen["files"])
    }
    if observed != frozen["files"]:
        changed = [path for path in observed if observed[path] != frozen["files"].get(path)]
        raise RuntimeError(f"historical evidence changed: {changed}")
    return observed


def load_frozen_inputs() -> tuple[
    dict[str, Any], dict[str, Any], pd.DataFrame, pd.DataFrame, dict[str, dict[str, Any]]
]:
    verify_historical_immutability()
    config = load_config(CONFIG_PATH)
    identity = json.loads(IDENTITY_PATH.read_text(encoding="utf-8"))
    if sha256_file(CONFIG_PATH) != identity["config_sha256"]:
        raise RuntimeError("Phase 1.2 config changed after freeze")
    manifest_path = PROJECT_ROOT / config["source_pilot_manifest"]
    pilot_path = PROJECT_ROOT / config["source_pilot_results"]
    b2_path = PROJECT_ROOT / config["source_phase1_1_b2_results"]
    if sha256_file(manifest_path) != identity["pilot_manifest_sha256"]:
        raise RuntimeError("pilot manifest changed after Phase 1.2 freeze")
    if sha256_file(pilot_path) != identity["pilot_results_sha256"]:
        raise RuntimeError("pilot results changed after Phase 1.2 freeze")
    if sha256_file(b2_path) != identity["phase1_1_b2_results_sha256"]:
        raise RuntimeError("Phase 1.1 B2 results changed after Phase 1.2 freeze")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pilot = pd.read_csv(pilot_path)
    b2 = pd.read_csv(b2_path)
    characterization = (
        pd.read_csv(PROJECT_ROOT / config["source_characterization"])
        .set_index("task_id")
        .to_dict(orient="index")
    )
    if manifest["task_count"] != int(config["expected_task_count"]):
        raise RuntimeError("Phase 1.2 task denominator changed")
    return config, manifest, pilot, b2, characterization


def build_objective_context(task: Task, normalization_factor: float = 172.0) -> dict[str, Any]:
    context = build_evaluation_context(task)
    size = len(context["energy"])
    feasible_mask = np.zeros(size, dtype=bool)
    optimal_mask = np.zeros(size, dtype=bool)
    feasible_mask[[route.bitstring_int for route in task.feasible_routes]] = True
    optimal_mask[[route.bitstring_int for route in task.optimal_routes]] = True
    context.update(
        {
            "feasible_mask": feasible_mask,
            "optimal_mask": optimal_mask,
            "total_penalty": context["flow_penalty"] + context["resource_penalty"],
            "routing_cost_raw": context["components"].routing_cost,
            "energy_order": np.argsort(context["energy"], kind="stable"),
            "normalization_factor": float(normalization_factor),
        }
    )
    return context


def evaluate_objective_state(
    task: Task,
    context: dict[str, Any],
    parameters: np.ndarray,
    *,
    cvar_alpha: float,
) -> dict[str, Any]:
    state = simulate_qaoa(np.asarray(parameters, dtype=np.float64), context["energy"], 3)
    probabilities = np.abs(state) ** 2
    phi = float(context["feasible_mask"].mean())
    metrics = probability_metrics(
        probabilities,
        np.flatnonzero(context["feasible_mask"]),
        np.flatnonzero(context["optimal_mask"]),
        phi,
    )
    mean_energy = float(np.dot(probabilities, context["energy"]))
    flow = float(np.dot(probabilities, context["flow_penalty"]))
    resource = float(np.dot(probabilities, context["resource_penalty"]))
    routing = float(np.dot(probabilities, context["routing_component"]))
    p_feas = float(metrics["p_feas"])
    conditional_route_cost = (
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
    return {
        "mean_energy": mean_energy,
        "expected_routing_component": routing,
        "expected_flow_penalty": flow,
        "expected_resource_penalty": resource,
        "expected_total_penalty": flow + resource,
        "p_feas": p_feas,
        "p_opt": metrics["p_opt"],
        "p_opt_given_feasible": metrics["p_opt_given_feasible"],
        "feasibility_amplification": metrics["feasibility_amplification"],
        "log_feasibility_gain": metrics["log_feasibility_gain"],
        "expected_route_cost_given_feasible": conditional_route_cost,
        "cvar_alpha": float(cvar_alpha),
        **cvar,
        "penalty_bound_lower_margin": bound["lower_bound_margin"],
        "penalty_bound_upper_margin": bound["upper_bound_margin"],
        "penalty_bound_pass": bound["bound_pass"],
        "state_norm": float(probabilities.sum()),
    }


def objective_value_from_probabilities(
    objective_id: str,
    probabilities: np.ndarray,
    context: dict[str, Any],
    *,
    cvar_alpha: float,
) -> float:
    if objective_id == "O0":
        return float(np.dot(probabilities, context["energy"]))
    if objective_id == "O1":
        return expected_penalty_objective(probabilities, context["total_penalty"])
    if objective_id == "O2":
        return exact_feasibility_objective(probabilities, context["feasible_mask"])
    if objective_id == "O3":
        return float(
            weighted_exact_cvar(
                context["energy"],
                probabilities,
                cvar_alpha,
                energy_order=context["energy_order"],
            )["cvar_value"]
        )
    raise ValueError(f"unknown frozen objective_id: {objective_id}")


def _objective_value_from_evaluation(objective_id: str, evaluation: dict[str, Any]) -> float:
    return {
        "O0": float(evaluation["mean_energy"]),
        "O1": float(evaluation["expected_total_penalty"]),
        "O2": float(1.0 - evaluation["p_feas"]),
        "O3": float(evaluation["cvar_value"]),
    }[objective_id]


def _run_id(task_id: str, objective_id: str, config_hash: str) -> str:
    payload = f"phase1.2|{task_id}|{objective_id}|p3|COBYLA|B2|{config_hash}"
    return "objective-run-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def _base_result_row(
    task: Task,
    characterization: dict[str, Any],
    p2_row: dict[str, Any],
    objective_id: str,
    config: dict[str, Any],
    config_hash: str,
) -> dict[str, Any]:
    row = {field: math.nan for field in RESULT_FIELDS}
    name, definition, role = OBJECTIVE_IDENTITIES[objective_id]
    row.update(
        {
            "run_id": _run_id(task.task_id, objective_id, config_hash),
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
            "objective_name": name,
            "objective_definition": definition,
            "objective_role": role,
            "depth": 3,
            "optimizer": "COBYLA",
            "eval_budget": int(config["objective_eval_budget"]),
            "source_p2_seed": int(p2_row["optimizer_seed"]),
            "source_p2_objective_final": float(p2_row["objective_final"]),
            "initialization_rule": config["initialization_rule"],
            "execution_status": "SUCCESS",
            "failure_reason": "",
            "historical_reuse": False,
            "historical_source_path": "",
            "historical_source_run_id": "",
            "config_sha256": config_hash,
            "source_results_sha256": "",
            "ansatz_cost_phase_hamiltonian": config["ansatz_cost_phase_hamiltonian"],
            "raw_statevector_persisted": False,
        }
    )
    return row


def _copy_evaluation(row: dict[str, Any], evaluation: dict[str, Any]) -> None:
    for field in (
        "mean_energy",
        "expected_routing_component",
        "expected_flow_penalty",
        "expected_resource_penalty",
        "expected_total_penalty",
        "p_feas",
        "p_opt",
        "p_opt_given_feasible",
        "feasibility_amplification",
        "log_feasibility_gain",
        "expected_route_cost_given_feasible",
        "cvar_alpha",
        "cvar_value",
        "cvar_cutoff_energy",
        "cvar_tail_fully_feasible",
        "cvar_tail_feasible_mass",
        "cvar_fractional_cutoff_mass",
        "penalty_bound_lower_margin",
        "penalty_bound_upper_margin",
        "penalty_bound_pass",
        "state_norm",
    ):
        row[field] = evaluation[field]


def _run_new_objective_cell(
    task_payload: dict[str, Any],
    characterization: dict[str, Any],
    p2_row: dict[str, Any],
    objective_id: str,
    config: dict[str, Any],
    config_hash: str,
) -> dict[str, Any]:
    task = Task.from_dict(task_payload)
    row = _base_result_row(task, characterization, p2_row, objective_id, config, config_hash)
    try:
        context = build_objective_context(
            task, float(config["hamiltonian_normalization_factor"])
        )
        initial = embed_p2_in_p3(_parse_parameters(p2_row["optimized_parameters"]))
        alpha = float(config["cvar"]["primary_alpha"])

        def objective(parameters: np.ndarray) -> float:
            state = simulate_qaoa(parameters, context["energy"], 3)
            return objective_value_from_probabilities(
                objective_id, np.abs(state) ** 2, context, cvar_alpha=alpha
            )

        result = optimize_cobyla_objective(
            objective,
            initial,
            eval_budget=int(config["objective_eval_budget"]),
            timeout_s=float(config["timeout_s"]),
            rhobeg=float(config["cobyla_rhobeg"]),
            catol=float(config["cobyla_catol"]),
        )
        evaluation = evaluate_objective_state(
            task, context, result.terminal_parameters, cvar_alpha=alpha
        )
        objective_final = _objective_value_from_evaluation(objective_id, evaluation)
        _copy_evaluation(row, evaluation)
        row.update(
            {
                "objective_start": result.objective_start,
                "objective_final": objective_final,
                "objective_improvement": result.objective_start - objective_final,
                "initial_parameters": json.dumps(initial.tolist()),
                "terminal_parameters": json.dumps(result.terminal_parameters.tolist()),
                "best_evaluated_parameters": json.dumps(
                    result.best_evaluated_parameters.tolist()
                ),
                "nfev": result.optimizer_nfev,
                "tracked_optimizer_evaluations": result.tracked_optimizer_evaluations,
                "total_objective_evaluations": result.total_objective_evaluations,
                "runtime_s": result.runtime_s,
                "terminal_objective": result.terminal_objective,
                "best_evaluated_objective": result.best_evaluated_objective,
                "optimizer_status": result.status,
                "optimizer_message": result.message,
                "scipy_success": result.scipy_success,
                "numerically_valid": result.numerically_valid,
            }
        )
        if abs(objective_final - result.terminal_objective) > 1e-9:
            raise RuntimeError("terminal objective failed exact recomputation")
        if not bool(evaluation["penalty_bound_pass"]):
            raise RuntimeError("FEASIBILITY_PENALTY_BOUND failed at optimization state")
        if not result.numerically_valid:
            raise RuntimeError("optimizer returned non-finite state")
    except Exception as exc:
        row["execution_status"] = "FAILURE"
        row["failure_reason"] = f"{type(exc).__name__}: {exc}"
    row["peak_memory_mb"] = _peak_memory_mb()
    return {field: row[field] for field in RESULT_FIELDS}


def _append_results(rows: list[dict[str, Any]]) -> pd.DataFrame:
    new = pd.DataFrame(rows, columns=RESULT_FIELDS)
    if OBJECTIVE_RESULTS_PATH.exists():
        existing = pd.read_csv(OBJECTIVE_RESULTS_PATH)
        if list(existing.columns) != RESULT_FIELDS:
            raise RuntimeError("Phase 1.2 objective-results schema changed")
        known = set(existing.run_id.astype(str))
        new = new[~new.run_id.astype(str).isin(known)]
        frame = pd.concat([existing, new], ignore_index=True)
    else:
        frame = new
    atomic_write_csv(OBJECTIVE_RESULTS_PATH, frame)
    return frame


def reuse_o0_rows() -> pd.DataFrame:
    config, manifest, pilot, b2, characterization = load_frozen_inputs()
    selected = selected_p2_rows(pilot).set_index("task_id")
    source = b2[b2.budget_multiplier == int(config["objective_budget_multiplier"])]
    if len(source) != int(config["expected_task_count"]):
        raise RuntimeError("historical O0 B2 denominator mismatch")
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    config_hash = sha256_file(CONFIG_PATH)
    source_hash = sha256_file(PROJECT_ROOT / config["source_phase1_1_b2_results"])
    rows = []
    for historical in source.to_dict(orient="records"):
        task_id = historical["task_id"]
        p2_row = selected.loc[task_id].to_dict()
        p2_row["task_id"] = task_id
        task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
        row = _base_result_row(task, characterization[task_id], p2_row, "O0", config, config_hash)
        initial = embed_p2_in_p3(_parse_parameters(p2_row["optimized_parameters"]))
        if int(historical["source_p2_seed"]) != int(p2_row["optimizer_seed"]):
            raise RuntimeError(f"historical O0 seed mismatch for {task_id}")
        if int(historical["eval_budget"]) != int(config["objective_eval_budget"]):
            raise RuntimeError(f"historical O0 budget mismatch for {task_id}")
        if not np.allclose(
            initial, _parse_parameters(historical["initial_parameters"]), rtol=0.0, atol=1e-12
        ):
            raise RuntimeError(f"historical O0 initialization mismatch for {task_id}")
        terminal_parameters = _parse_parameters(historical["terminal_parameters"])
        evaluation = evaluate_objective_state(
            task,
            build_objective_context(task, float(config["hamiltonian_normalization_factor"])),
            terminal_parameters,
            cvar_alpha=float(config["cvar"]["primary_alpha"]),
        )
        if abs(evaluation["mean_energy"] - float(historical["objective_final"])) > 1e-9:
            raise RuntimeError(f"historical O0 objective mismatch for {task_id}")
        _copy_evaluation(row, evaluation)
        row.update(
            {
                "objective_start": float(historical["objective_start"]),
                "objective_final": float(historical["objective_final"]),
                "objective_improvement": float(historical["objective_improvement"]),
                "initial_parameters": historical["initial_parameters"],
                "terminal_parameters": historical["terminal_parameters"],
                "best_evaluated_parameters": historical["best_evaluated_parameters"],
                "nfev": int(historical["optimizer_nfev"]),
                "tracked_optimizer_evaluations": int(
                    historical["tracked_optimizer_evaluations"]
                ),
                "total_objective_evaluations": int(
                    historical["total_objective_evaluations"]
                ),
                "runtime_s": float(historical["runtime_s"]),
                "terminal_objective": float(historical["terminal_objective"]),
                "best_evaluated_objective": float(
                    historical["best_evaluated_objective"]
                ),
                "optimizer_status": int(historical["optimizer_status"]),
                "optimizer_message": historical["optimizer_message"],
                "scipy_success": bool(historical["scipy_success"]),
                "numerically_valid": bool(historical["numerically_valid"]),
                "historical_reuse": True,
                "historical_source_path": config["source_phase1_1_b2_results"],
                "historical_source_run_id": historical["run_id"],
                "source_results_sha256": source_hash,
                "peak_memory_mb": math.nan,
            }
        )
        rows.append({field: row[field] for field in RESULT_FIELDS})
    return _append_results(rows)


def run_theoretical_audits() -> pd.DataFrame:
    config, _, _, _, characterization = load_frozen_inputs()
    full_manifest = json.loads(
        (PROJECT_ROOT / config["source_v2_manifest"]).read_text(encoding="utf-8")
    )
    if len(full_manifest["tasks"]) != int(config["expected_v2_task_count"]):
        raise RuntimeError("v2 audit task denominator changed")
    tolerance = float(config["audits"]["numerical_tolerance"])
    namespace = str(config["audits"]["random_state_seed_namespace"])
    rows = []
    for task_row in full_manifest["tasks"]:
        task = read_task(PROJECT_ROOT / task_row["task_path"])
        context = build_objective_context(task)
        feasible = context["feasible_mask"]
        infeasible = ~feasible
        penalty = context["total_penalty"]
        classifications_match = bool(np.array_equal(penalty == 0.0, feasible))
        minimum_infeasible = float(penalty[infeasible].min())
        maximum_penalty = float(penalty.max())
        maximum_feasible = float(penalty[feasible].max())
        maximum_feasible_energy = float(context["energy"][feasible].max())
        minimum_infeasible_energy = float(context["energy"][infeasible].min())
        seed = int.from_bytes(
            hashlib.sha256(f"{namespace}|{task.task_id}".encode()).digest()[:8], "big"
        )
        rng = np.random.default_rng(seed)
        random_probabilities = rng.exponential(1.0, len(penalty))
        random_probabilities /= random_probabilities.sum()
        bound = feasibility_penalty_bound(
            random_probabilities, feasible, penalty, tolerance=tolerance
        )
        alpha = float(config["cvar"]["primary_alpha"])
        random_p_feas = float(random_probabilities[feasible].sum())
        cvar = weighted_exact_cvar(
            context["energy"],
            random_probabilities,
            alpha,
            feasible_mask=feasible,
            energy_order=context["energy_order"],
        )
        tail_condition = bool(cvar["cvar_tail_fully_feasible"]) == bool(
            random_p_feas >= alpha - tolerance
        )
        rows.append(
            {
                "task_id": task.task_id,
                "base_graph_id": task.graph.graph_id,
                "base_instance_id": task.base_instance_id,
                "size_stratum": task.size_stratum,
                "stress_level": task.tightness_level,
                "n_edges": len(task.graph.edges),
                "dilution_score": float(characterization[task.task_id]["dilution_score"]),
                "minimum_infeasible_total_penalty": minimum_infeasible,
                "maximum_total_penalty": maximum_penalty,
                "maximum_feasible_total_penalty": maximum_feasible,
                "penalty_feasibility_classification_match": classifications_match,
                "basis_penalty_contract_pass": bool(
                    classifications_match
                    and minimum_infeasible >= 1.0 - tolerance
                    and maximum_penalty <= 4.0 + tolerance
                    and maximum_feasible <= tolerance
                ),
                "max_feasible_energy": maximum_feasible_energy,
                "min_infeasible_energy": minimum_infeasible_energy,
                "strict_energy_class_separation": bool(
                    minimum_infeasible_energy > maximum_feasible_energy
                ),
                "random_state_seed": seed,
                "random_state_p_feas": random_p_feas,
                "random_state_expected_total_penalty": bound["expected_total_penalty"],
                "random_state_lower_bound_margin": bound["lower_bound_margin"],
                "random_state_upper_bound_margin": bound["upper_bound_margin"],
                "random_state_penalty_bound_pass": bound["bound_pass"],
                "random_state_cvar_tail_fully_feasible": cvar[
                    "cvar_tail_fully_feasible"
                ],
                "random_state_cvar_tail_feasible_mass": cvar[
                    "cvar_tail_feasible_mass"
                ],
                "random_state_cvar_tail_condition_pass": tail_condition,
            }
        )
    frame = pd.DataFrame(rows).sort_values(
        ["size_stratum", "base_instance_id", "stress_level"], kind="stable"
    )
    atomic_write_csv(THEORETICAL_AUDIT_PATH, frame)
    required = [
        "basis_penalty_contract_pass",
        "strict_energy_class_separation",
        "random_state_penalty_bound_pass",
        "random_state_cvar_tail_condition_pass",
    ]
    if len(frame) != int(config["expected_v2_task_count"]) or not frame[required].all().all():
        raise RuntimeError("Phase 1.2 theoretical audit failed; STOP")
    return frame


def _run_new_matrix(task_ids: list[str], objective_ids: list[str]) -> pd.DataFrame:
    config, manifest, pilot, _, characterization = load_frozen_inputs()
    selected = selected_p2_rows(pilot).set_index("task_id")
    task_lookup = {row["task_id"]: row for row in manifest["tasks"]}
    config_hash = sha256_file(CONFIG_PATH)
    known: set[str] = set()
    if OBJECTIVE_RESULTS_PATH.exists():
        known = set(pd.read_csv(OBJECTIVE_RESULTS_PATH).run_id.astype(str))
    jobs = []
    for task_id in task_ids:
        if task_id not in task_lookup:
            raise RuntimeError(f"non-pilot task requested: {task_id}")
        p2_row = selected.loc[task_id].to_dict()
        p2_row["task_id"] = task_id
        task = read_task(PROJECT_ROOT / task_lookup[task_id]["task_path"])
        for objective_id in objective_ids:
            if objective_id not in {"O1", "O2", "O3"}:
                raise RuntimeError(f"new optimization is forbidden for {objective_id}")
            if _run_id(task_id, objective_id, config_hash) in known:
                continue
            jobs.append(
                (
                    task.to_dict(),
                    characterization[task_id],
                    p2_row,
                    objective_id,
                    config,
                    config_hash,
                )
            )
    if jobs:
        threads = str(config["execution"]["worker_blas_threads"])
        os.environ["OMP_NUM_THREADS"] = threads
        os.environ["OPENBLAS_NUM_THREADS"] = threads
        os.environ["MKL_NUM_THREADS"] = threads
        with ProcessPoolExecutor(
            max_workers=int(config["execution"]["max_workers"])
        ) as executor:
            futures = [executor.submit(_run_new_objective_cell, *job) for job in jobs]
            for future in as_completed(futures):
                _append_results([future.result()])
    return pd.read_csv(OBJECTIVE_RESULTS_PATH)


def _validate_result_rows(frame: pd.DataFrame, *, expected_rows: int) -> None:
    config = load_config(CONFIG_PATH)
    tolerance = float(config["audits"]["numerical_tolerance"])
    if len(frame) != expected_rows:
        raise RuntimeError(f"objective result denominator mismatch: {len(frame)} != {expected_rows}")
    if not (frame.execution_status == "SUCCESS").all():
        failures = frame[frame.execution_status != "SUCCESS"][
            ["task_id", "objective_id", "failure_reason"]
        ].to_dict(orient="records")
        raise RuntimeError(f"objective optimization failure; STOP: {failures}")
    if not frame.penalty_bound_pass.astype(bool).all():
        raise RuntimeError("optimization-state FEASIBILITY_PENALTY_BOUND failed")
    if float((frame.state_norm - 1.0).abs().max()) > tolerance:
        raise RuntimeError("optimization-state norm audit failed")
    if not (frame.eval_budget == int(config["objective_eval_budget"])).all():
        raise RuntimeError("matched budget identity failed")
    if not (frame.nfev <= frame.eval_budget).all():
        raise RuntimeError("optimizer exceeded matched evaluation budget")
    if not (
        frame.total_objective_evaluations == frame.tracked_optimizer_evaluations + 1
    ).all():
        raise RuntimeError("matched budget accounting failed")
    expected = np.select(
        [
            frame.objective_id == "O0",
            frame.objective_id == "O1",
            frame.objective_id == "O2",
            frame.objective_id == "O3",
        ],
        [
            frame.mean_energy,
            frame.expected_total_penalty,
            1.0 - frame.p_feas,
            frame.cvar_value,
        ],
        default=np.nan,
    )
    if float(np.nanmax(np.abs(frame.objective_final - expected))) > 1e-9:
        raise RuntimeError("objective identity/provenance recomputation failed")


def run_preflight() -> pd.DataFrame:
    config = load_config(CONFIG_PATH)
    if not THEORETICAL_AUDIT_PATH.exists():
        raise RuntimeError("theoretical audit must pass before preflight")
    audit = pd.read_csv(THEORETICAL_AUDIT_PATH)
    if not audit.basis_penalty_contract_pass.all():
        raise RuntimeError("theoretical audit did not pass; STOP")
    task_ids = list(config["preflight"]["task_ids"])
    objective_ids = list(config["preflight"]["objective_ids"])
    frame = _run_new_matrix(task_ids, objective_ids)
    selected = frame[
        frame.task_id.isin(task_ids) & frame.objective_id.isin(objective_ids)
    ].copy()
    try:
        _validate_result_rows(selected, expected_rows=len(task_ids) * len(objective_ids))
    except Exception as exc:
        write_json(
            PREFLIGHT_PATH,
            {
                "status": "FAILED_STOP",
                "task_ids": task_ids,
                "objective_ids": objective_ids,
                "reason": f"{type(exc).__name__}: {exc}",
            },
        )
        raise
    write_json(
        PREFLIGHT_PATH,
        {
            "status": "PASSED",
            "task_ids": task_ids,
            "objective_ids": objective_ids,
            "row_count": len(selected),
            "run_ids": sorted(selected.run_id.tolist()),
            "all_penalty_bounds_pass": bool(selected.penalty_bound_pass.all()),
            "maximum_nfev": int(selected.nfev.max()),
        },
    )
    return selected


def run_full_matrix() -> pd.DataFrame:
    config, manifest, _, _, _ = load_frozen_inputs()
    if not PREFLIGHT_PATH.exists() or json.loads(PREFLIGHT_PATH.read_text())["status"] != "PASSED":
        raise RuntimeError("successful 2-task preflight is required; STOP")
    reuse_o0_rows()
    task_ids = [row["task_id"] for row in manifest["tasks"]]
    frame = _run_new_matrix(task_ids, ["O1", "O2", "O3"])
    frame = frame[frame.task_id.isin(task_ids) & frame.objective_id.isin(OBJECTIVE_IDENTITIES)]
    _validate_result_rows(frame, expected_rows=int(config["expected_task_count"]) * 4)
    counts = frame.groupby("objective_id").size().to_dict()
    if counts != {"O0": 56, "O1": 56, "O2": 56, "O3": 56}:
        raise RuntimeError(f"objective arm denominator mismatch: {counts}")
    if not frame[frame.objective_id == "O0"].historical_reuse.astype(bool).all():
        raise RuntimeError("O0 historical reuse identity failed")
    if frame[frame.objective_id != "O0"].historical_reuse.astype(bool).any():
        raise RuntimeError("new objective was incorrectly marked as historical reuse")
    frame = frame.sort_values(
        ["size_stratum", "base_instance_id", "stress_level", "objective_id"],
        kind="stable",
    )
    atomic_write_csv(OBJECTIVE_RESULTS_PATH, frame)
    verify_historical_immutability()
    return frame
