"""Config-driven, restartable Phase 0 and Phase 1 workflows."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .exact import characterize_family
from .io import (
    PROJECT_ROOT,
    append_canonical_rows,
    atomic_write_csv,
    load_config,
    read_task,
    write_json,
    write_task,
)
from .penalties import build_diagonal_energies
from .plotting import plot_phase0, plot_phase1
from .rcsp import build_task_family
from .schemas import make_resource_censored_row, make_uniform_row, run_id_for, run_penalty_x


def _experiment_paths(config: dict[str, Any]) -> dict[str, Path]:
    name = str(config["experiment_name"])
    result_dir = PROJECT_ROOT / "results" / name
    return {
        "task_dir": PROJECT_ROOT / "data" / "tasks" / name,
        "manifest": PROJECT_ROOT / "data" / "manifests" / f"{name}_tasks.csv",
        "result_dir": result_dir,
        "characterization": result_dir / "task_characterization.csv",
        "master": result_dir / "master_results.csv",
        "summary": result_dir / "summary.json",
        "figure_dir": PROJECT_ROOT / "figures",
    }


def _penalty_contracts(qconfig: dict[str, Any]) -> list[tuple[str, float, float]]:
    contracts = qconfig.get("penalty_contracts")
    active = qconfig.get("active_penalty_contracts")
    if contracts is None or active is None:
        return [
            (
                "default",
                float(qconfig["flow_penalty_strength"]),
                float(qconfig["resource_penalty_strength"]),
            )
        ]
    resolved = []
    for name in active:
        if name not in contracts:
            raise ValueError(f"unknown active penalty contract: {name}")
        resolved.append(
            (
                str(name),
                float(contracts[name]["flow_penalty_strength"]),
                float(contracts[name]["resource_penalty_strength"]),
            )
        )
    if not resolved:
        raise ValueError("at least one penalty contract must be active")
    return resolved


def generate_task_universe(config_path: str | Path) -> tuple[list[Any], pd.DataFrame]:
    config = load_config(config_path)
    paths = _experiment_paths(config)
    paths["task_dir"].mkdir(parents=True, exist_ok=True)
    all_tasks = []
    manifest_rows = []
    tightness = config["tightness_levels"]
    for stratum, spec in config["size_strata"].items():
        for base_index in range(int(config["instances_per_cell"])):
            family = build_task_family(
                size_stratum=stratum,
                target_n_edges=int(spec["target_n_edges"]),
                layer_widths=spec["layer_widths"],
                base_index=base_index,
                master_seed=int(config["master_seed"]),
                tightness_levels=tightness,
                quantile_method=str(config.get("quantile_method", "lower")),
            )
            for task in family:
                task_path = paths["task_dir"] / f"{task.task_id}.json"
                write_task(task_path, task)
                all_tasks.append(task)
                manifest_rows.append(
                    {
                        "task_id": task.task_id,
                        "graph_id": task.graph.graph_id,
                        "base_instance_id": task.base_instance_id,
                        "size_stratum": task.size_stratum,
                        "tightness_level": task.tightness_level,
                        "target_n_edges": task.target_n_edges,
                        "actual_n_edges": task.actual_n_edges,
                        "budget": task.budget,
                        "generation_seed": task.generation_seed,
                        "duplicate_budget": task.duplicate_budget,
                        "duplicate_feasible_set": task.duplicate_feasible_set,
                        "task_path": str(task_path.relative_to(PROJECT_ROOT)),
                    }
                )
    manifest = pd.DataFrame(manifest_rows)
    atomic_write_csv(paths["manifest"], manifest)
    return all_tasks, manifest


def characterize_tasks(config_path: str | Path) -> pd.DataFrame:
    config = load_config(config_path)
    paths = _experiment_paths(config)
    if not paths["manifest"].exists():
        generate_task_universe(config_path)
    manifest = pd.read_csv(paths["manifest"])
    existing = (
        pd.read_csv(paths["characterization"])
        if paths["characterization"].exists()
        else pd.DataFrame()
    )
    existing_ids = set(existing["task_id"].astype(str)) if len(existing) else set()
    new_rows: list[dict[str, object]] = []
    for _, family_manifest in manifest.groupby("base_instance_id", sort=False):
        family_ids = set(family_manifest["task_id"].astype(str))
        if family_ids.issubset(existing_ids):
            continue
        tasks = [
            read_task(PROJECT_ROOT / task_path)
            for task_path in family_manifest["task_path"].tolist()
        ]
        family_rows = characterize_family(tasks)
        for task, row in zip(tasks, family_rows):
            if int(row["structural_path_state_count"]) != len(task.candidate_routes):
                raise AssertionError("exhaustive structural states disagree with simple routes")
            if int(row["n_feasible_states"]) != len(task.feasible_routes):
                raise AssertionError("edge-bit feasible states disagree with exact routes")
        new_rows.extend(family_rows)
        combined = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)
        combined = combined.drop_duplicates("task_id", keep="first")
        atomic_write_csv(paths["characterization"], combined)
    if paths["characterization"].exists():
        return pd.read_csv(paths["characterization"])
    return pd.DataFrame(new_rows)


def run_phase0_workflow(config_path: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config(config_path)
    paths = _experiment_paths(config)
    started = time.perf_counter()
    tasks, manifest = generate_task_universe(config_path)
    characterization = characterize_tasks(config_path)
    figure_paths = plot_phase0(
        characterization, paths["figure_dir"], str(config["experiment_name"])
    )
    summary = {
        "experiment_name": config["experiment_name"],
        "task_count": int(len(characterization)),
        "base_graph_count": int(characterization["graph_id"].nunique()),
        "size_strata": list(config["size_strata"]),
        "tightness_levels": list(config["tightness_levels"]),
        "instances_per_cell": int(config["instances_per_cell"]),
        "zero_feasible_count": int(characterization["zero_feasible"].astype(bool).sum()),
        "duplicate_budget_count": int(characterization["duplicate_budget"].astype(bool).sum()),
        "duplicate_feasible_set_count": int(
            characterization["duplicate_feasible_set"].astype(bool).sum()
        ),
        "feasible_state_fraction_min": float(characterization["feasible_state_fraction"].min()),
        "feasible_state_fraction_max": float(characterization["feasible_state_fraction"].max()),
        "largest_n_qubits": int(characterization["n_qubits"].max()),
        "largest_state_space_size": int(characterization["state_space_size"].max()),
        "manifest": str(paths["manifest"].relative_to(PROJECT_ROOT)),
        "task_file_count": int(len(tasks)),
        "figures": [str(Path(p).relative_to(PROJECT_ROOT)) for p in figure_paths],
        "phase0_wall_time_s": time.perf_counter() - started,
    }
    write_json(paths["summary"], summary)
    return characterization, summary


def run_phase1_workflow(config_path: str | Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config(config_path)
    paths = _experiment_paths(config)
    if not paths["characterization"].exists() or not paths["manifest"].exists():
        run_phase0_workflow(config_path)
    else:
        portable_manifest = pd.read_csv(paths["manifest"])
        if any(
            not (PROJECT_ROOT / task_path).exists()
            for task_path in portable_manifest["task_path"].tolist()
        ):
            generate_task_universe(config_path)
    characterization = pd.read_csv(paths["characterization"])
    char_by_id = characterization.set_index("task_id").to_dict(orient="index")
    manifest = pd.read_csv(paths["manifest"])
    qconfig = config.get("qaoa", config.get("pilot_qaoa"))
    if qconfig is None:
        raise ValueError("resource projection requires qaoa or pilot_qaoa configuration")
    penalty_contracts = _penalty_contracts(qconfig)
    eval_budget = int(qconfig["eval_budget"])
    timeout_s = float(qconfig["timeout_s"]) if qconfig.get("timeout_s") is not None else None
    max_qubits = int(qconfig["max_qubits"])
    depths = [int(value) for value in qconfig["depths"]]
    seeds = [int(value) for value in qconfig["optimizer_seeds"]]
    existing_ids: set[str] = set()
    if paths["master"].exists():
        existing_ids = set(pd.read_csv(paths["master"], usecols=["run_id"])["run_id"].astype(str))

    for manifest_row in manifest.to_dict(orient="records"):
        task = read_task(PROJECT_ROOT / manifest_row["task_path"])
        task_char = char_by_id[task.task_id]
        uniform = make_uniform_row(task, task_char)
        if uniform["run_id"] not in existing_ids:
            append_canonical_rows(paths["master"], [uniform])
            existing_ids.add(uniform["run_id"])

        pending = [
            (contract_name, flow_strength, resource_strength, depth, seed)
            for contract_name, flow_strength, resource_strength in penalty_contracts
            for depth in depths
            for seed in seeds
            if run_id_for(
                task.task_id,
                "Penalty-X",
                depth,
                seed,
                flow_strength,
                resource_strength,
            ) not in existing_ids
        ]
        if not pending:
            continue
        if task.actual_n_edges > max_qubits:
            rows = [
                make_resource_censored_row(
                    task,
                    task_char,
                    depth=depth,
                    seed=seed,
                    flow_penalty_strength=flow_strength,
                    resource_penalty_strength=resource_strength,
                    eval_budget=eval_budget,
                )
                for _, flow_strength, resource_strength, depth, seed in pending
            ]
        else:
            rows = []
            for _, flow_strength, resource_strength in penalty_contracts:
                contract_pending = [
                    item
                    for item in pending
                    if item[1] == flow_strength and item[2] == resource_strength
                ]
                if not contract_pending:
                    continue
                energy_started = time.perf_counter()
                energy = build_diagonal_energies(
                    task.graph,
                    task.budget,
                    flow_strength,
                    resource_strength,
                )
                energy_time = time.perf_counter() - energy_started
                rows.extend(
                    run_penalty_x(
                        task,
                        task_char,
                        depth=depth,
                        seed=seed,
                        flow_penalty_strength=flow_strength,
                        resource_penalty_strength=resource_strength,
                        eval_budget=eval_budget,
                        energy_components=energy,
                        energy_build_time_s=energy_time,
                        timeout_s=timeout_s,
                    )
                    for _, _, _, depth, seed in contract_pending
                )
        combined = append_canonical_rows(paths["master"], rows)
        existing_ids.update(row["run_id"] for row in rows)

    results = pd.read_csv(paths["master"])
    figure_paths = plot_phase1(results, paths["figure_dir"], str(config["experiment_name"]))
    status_counts = results["execution_status"].value_counts(dropna=False).to_dict()
    summary_path = paths["summary"]
    summary: dict[str, Any] = {}
    if summary_path.exists():
        import json

        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    penalty_rows = results[results["algorithm"] == "Penalty-X"]
    summary.update(
        {
            "result_row_count": int(len(results)),
            "uniform_row_count": int((results["algorithm"] == "Uniform").sum()),
            "penalty_x_row_count": int(len(penalty_rows)),
            "execution_status_counts": {str(k): int(v) for k, v in status_counts.items()},
            "failure_count": int((results["execution_status"] != "SUCCESS").sum()),
            "zero_optimal_probability_count": int(
                penalty_rows["zero_optimal_probability"].astype(bool).sum()
            ),
            "p_feas_min": float(penalty_rows["p_feas"].min()),
            "p_feas_max": float(penalty_rows["p_feas"].max()),
            "feasibility_amplification_min": float(
                penalty_rows["feasibility_amplification"].min()
            ),
            "feasibility_amplification_max": float(
                penalty_rows["feasibility_amplification"].max()
            ),
            "phase1_figures": [str(Path(p).relative_to(PROJECT_ROOT)) for p in figure_paths],
        }
    )
    write_json(summary_path, summary)
    return results, summary


def build_resource_projection(
    characterization: pd.DataFrame,
    config_path: str | Path,
    smoke_results_path: Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    qconfig = config.get("qaoa", config.get("pilot_qaoa"))
    if qconfig is None:
        raise ValueError("resource projection requires qaoa or pilot_qaoa configuration")
    penalty_contracts = _penalty_contracts(qconfig)
    depths = [int(value) for value in qconfig["depths"]]
    seeds = [int(value) for value in qconfig["optimizer_seeds"]]
    eval_budget = int(qconfig["eval_budget"])
    run_count = len(characterization) * len(depths) * len(seeds) * len(penalty_contracts)
    largest_n = int(characterization["n_qubits"].max())
    largest_states = int(characterization["state_space_size"].max())
    raw_statevector_mb = 16 * largest_states / 1024**2
    incremental_numeric_mb = 128 * largest_states / 1024**2
    conservative_process_mb = 256.0 + incremental_numeric_mb

    slope = 2.0e-9
    intercept = 5.0e-4
    calibration = "conservative affine analytic default"
    if smoke_results_path is not None and smoke_results_path.exists():
        smoke = pd.read_csv(smoke_results_path)
        smoke = smoke[(smoke["algorithm"] == "Penalty-X") & (smoke["nfev"] > 0)]
        if len(smoke):
            smoke = smoke.assign(
                seconds_per_evaluation=smoke["optimization_time_s"] / smoke["nfev"],
                work_units=smoke["depth"] * smoke["n_qubits"] * smoke["state_space_size"],
            )
            grouped = smoke.groupby("n_qubits")[["seconds_per_evaluation", "work_units"]].mean()
            if len(grouped) >= 2:
                slope_fit, intercept_fit = np.polyfit(
                    grouped["work_units"].to_numpy(float),
                    grouped["seconds_per_evaluation"].to_numpy(float),
                    1,
                )
                slope = max(0.0, float(slope_fit))
                intercept = max(0.0, float(intercept_fit))
                calibration = (
                    "affine fit to smoke seconds/evaluation = intercept + "
                    "slope*(depth*qubit*state)"
                )
    central_seconds = 0.0
    for row in characterization.to_dict(orient="records"):
        for depth in depths:
            central_seconds += (
                len(penalty_contracts)
                * len(seeds)
                * eval_budget
                * (
                    intercept
                    + slope
                    * depth
                    * int(row["n_qubits"])
                    * int(row["state_space_size"])
                )
            )
    estimated_csv_mb = run_count * 2.5 / 1024
    task_dir = PROJECT_ROOT / "data" / "tasks" / str(config["experiment_name"])
    task_json_mb = sum(path.stat().st_size for path in task_dir.glob("*.json")) / 1024**2
    return {
        "phase1_penalty_x_run_count": int(run_count),
        "uniform_analytic_row_count": int(len(characterization)),
        "depths": depths,
        "optimizer_seed_count": len(seeds),
        "active_penalty_contracts": [name for name, _, _ in penalty_contracts],
        "eval_budget_per_run": eval_budget,
        "largest_n_qubits": largest_n,
        "largest_state_space_size": largest_states,
        "largest_raw_complex128_statevector_mb": raw_statevector_mb,
        "estimated_incremental_numeric_arrays_mb": incremental_numeric_mb,
        "conservative_peak_process_rss_mb": conservative_process_mb,
        "implementation_device": "CPU NumPy exact statevector (GPU not required or used)",
        "wall_clock_central_hours_single_process": central_seconds / 3600,
        "wall_clock_range_hours_single_process": [
            central_seconds * 0.5 / 3600,
            central_seconds * 5 / 3600,
        ],
        "timing_calibration": calibration,
        "timing_fit_intercept_s_per_evaluation": intercept,
        "timing_fit_slope_s_per_depth_qubit_state": slope,
        "estimated_canonical_csv_mb": estimated_csv_mb,
        "generated_task_json_mb": task_json_mb,
        "estimated_total_disk_mb_without_statevectors": task_json_mb + estimated_csv_mb + 2.0,
        "raw_statevectors_persisted": False,
    }
