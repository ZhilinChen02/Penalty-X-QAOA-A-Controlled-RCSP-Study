"""B1 depth-by-objective-evaluation-budget ablation."""

from __future__ import annotations

import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, atomic_write_text
from qroute_dilution.optimizer import initial_parameters

from .common import (
    REVIEW_ROOT,
    build_objective_context,
    embed_parameters,
    evaluate_parameters,
    exact_objective_callable,
    load_json,
    sha256_payload,
    stable_run_id,
    task_from_manifest_row,
    utc_timestamp,
)
from .manifests import MANIFEST_PATHS, execution_code_fingerprint
from .optimization import optimize_with_strict_nfev
from .registry import (
    read_valid_terminal_record,
    rebuild_registry,
    registry_payload,
    write_new_record,
)
from .statistics import graph_effect_summary, paired_objective_effects


B1_ROOT = REVIEW_ROOT / "B1_depth_budget"


def _settings(protocol: dict[str, Any]) -> dict[str, float | bool]:
    return {
        "cobyla_rhobeg": float(protocol["cobyla_rhobeg"]),
        "cobyla_catol": float(protocol["cobyla_catol"]),
    }


def validate_single_trajectory_checkpoints(task_record: dict[str, Any]) -> dict[str, Any]:
    """Empirically verify that COBYLA's prefix is max-budget invariant.

    This gate compares every objective value and parameter in independent 120/240
    runs with the corresponding prefix of one 480-call run on a frozen small task.
    Formal B1 cannot start unless both prefixes are identical to tight tolerance.
    """
    manifest = load_json(MANIFEST_PATHS["depth_budget"])
    task = task_from_manifest_row(task_record)
    context = build_objective_context(task)
    depth = 2
    seed = int(manifest["seeds"][0])
    alpha = float(manifest["alpha"])
    x0 = initial_parameters(depth, seed)
    objective = exact_objective_callable(context, depth, "O0", alpha)
    protocol = load_json(PROJECT_ROOT / manifest["protocol_path"])["depth_budget"]
    settings = _settings(protocol)
    long = optimize_with_strict_nfev(
        objective,
        x0,
        method="COBYLA",
        max_nfev=480,
        timeout_s=300.0,
        settings=settings,
    )
    comparisons = []
    for budget in (120, 240):
        short = optimize_with_strict_nfev(
            objective,
            x0,
            method="COBYLA",
            max_nfev=budget,
            timeout_s=300.0,
            settings=settings,
        )
        prefix = long.history[: len(short.history)]
        value_difference = max(
            abs(left.value - right.value)
            for left, right in zip(prefix, short.history)
        )
        parameter_difference = max(
            float(np.max(np.abs(left.parameters - right.parameters)))
            for left, right in zip(prefix, short.history)
        )
        comparisons.append(
            {
                "budget": budget,
                "short_nfev": short.nfev,
                "long_prefix_nfev": len(prefix),
                "maximum_objective_difference": value_difference,
                "maximum_parameter_difference": parameter_difference,
                "pass": bool(
                    len(prefix) == len(short.history)
                    and value_difference <= 1e-12
                    and parameter_difference <= 1e-12
                ),
            }
        )
    return {
        "task_id": task.task_id,
        "method": "COBYLA",
        "long_run_nfev": long.nfev,
        "comparisons": comparisons,
        "pass": all(item["pass"] for item in comparisons),
        "interpretation": (
            "A checkpoint is the best evaluated incumbent in the verified prefix of "
            "one deterministic 480-call trajectory."
        ),
    }


def _run_record_path(root: Path, run_id: str) -> Path:
    return root / "runs" / f"{run_id}.json"


def _execute_trajectory(
    *,
    task: Any,
    context: dict[str, Any],
    task_record: dict[str, Any],
    objective_id: str,
    depth: int,
    seed: int,
    manifest: dict[str, Any],
    output_root: Path,
) -> str:
    run_id = stable_run_id(
        "b1",
        task.task_id,
        objective_id,
        depth,
        seed,
        manifest["maximum_nfev"],
        execution_code_fingerprint(manifest),
    )
    path = _run_record_path(output_root, run_id)
    if read_valid_terminal_record(path, run_id=run_id) is not None:
        return "SKIPPED_EXISTING"
    started_at = utc_timestamp()
    started = time.perf_counter()
    actual_nfev: int | None = None
    try:
        alpha = float(manifest["alpha"])
        x0 = initial_parameters(int(depth), int(seed))
        objective = exact_objective_callable(context, depth, objective_id, alpha)
        protocol = load_json(PROJECT_ROOT / manifest["protocol_path"])["depth_budget"]
        result = optimize_with_strict_nfev(
            objective,
            x0,
            method=manifest["optimizer"],
            max_nfev=int(manifest["maximum_nfev"]),
            timeout_s=float(
                load_json(PROJECT_ROOT / manifest["protocol_path"])["global"][
                    "timeout_s"
                ]
            ),
            settings=_settings(protocol),
        )
        actual_nfev = result.nfev
        checkpoints = []
        for budget in manifest["evaluation_budgets"]:
            incumbent = result.incumbent_at(int(budget))
            evaluation = evaluate_parameters(
                task, context, incumbent.parameters, depth, alpha=alpha
            )
            recomputed_objective = (
                float(evaluation["mean_energy"])
                if objective_id == "O0"
                else float(evaluation["cvar"])
            )
            if abs(recomputed_objective - incumbent.value) > 2e-10:
                raise RuntimeError("checkpoint objective failed exact recomputation")
            checkpoints.append(
                {
                    "requested_nfev_budget": int(budget),
                    "effective_trajectory_nfev": min(int(budget), result.nfev),
                    "incumbent_evaluation_index": incumbent.nfev,
                    "early_termination_carried_forward": result.nfev < int(budget),
                    "parameters": incumbent.parameters.tolist(),
                    "objective": recomputed_objective,
                    **evaluation,
                }
            )
        terminal_evaluation = evaluate_parameters(
            task, context, result.terminal_parameters, depth, alpha=alpha
        )
        record_status = (
            "TIMEOUT" if result.termination_reason == "WALLTIME_LIMIT" else "COMPLETE"
        )
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        record = {
            "schema_version": "qroute-dilution.B1.trajectory.v1",
            "experiment": "B1_DEPTH_BUDGET",
            "run_id": run_id,
            "status": record_status,
            "task": task_record,
            "objective": objective_id,
            "alpha": alpha,
            "optimizer": manifest["optimizer"],
            "depth": int(depth),
            "seed": int(seed),
            "maximum_nfev": int(manifest["maximum_nfev"]),
            "actual_objective_calls": result.nfev,
            "scipy_reported_nfev": result.scipy_reported_nfev,
            "nit": result.nit,
            "scipy_status": result.status,
            "scipy_success": result.scipy_success,
            "optimizer_message": result.message,
            "termination_reason": result.termination_reason,
            "runtime_s": result.runtime_s,
            "initial_parameters": result.initial_parameters.tolist(),
            "terminal_parameters": result.terminal_parameters.tolist(),
            "terminal_objective_observed": result.terminal_objective_observed,
            "terminal_exact_evaluation": terminal_evaluation,
            "best_evaluated_parameters": result.best_evaluated_parameters.tolist(),
            "best_evaluated_objective": result.best_evaluated_objective,
            "checkpoint_semantics": (
                "best evaluated incumbent within the exact evaluation-history prefix "
                "of one maximum-480 trajectory"
            ),
            "checkpoints": checkpoints,
            "evaluation_history_sha256": sha256_payload(
                [
                    [item.nfev, item.parameters.tolist(), item.value]
                    for item in result.history
                ]
            ),
            "started_at": started_at,
            "finished_at": finished_at,
            "manifest_code_fingerprint": manifest["code_fingerprint"],
            "execution_code_fingerprint": execution_code_fingerprint(manifest),
        }
        record["registry"] = registry_payload(
            experiment="B1_DEPTH_BUDGET",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective=objective_id,
            optimizer=manifest["optimizer"],
            depth=depth,
            alpha=alpha,
            nfev_budget=int(manifest["maximum_nfev"]),
            actual_nfev=result.nfev,
            shots=None,
            seed=seed,
            status=record_status,
            started_at=started_at,
            finished_at=finished_at,
            runtime_s=runtime,
            error_message="",
            git_commit=manifest["code_git_commit"],
            dirty_state_fingerprint=execution_code_fingerprint(manifest),
        )
        write_new_record(path, record)
        return record_status
    except Exception as exc:
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        message = f"{type(exc).__name__}: {exc}"
        record = {
            "schema_version": "qroute-dilution.B1.trajectory.v1",
            "experiment": "B1_DEPTH_BUDGET",
            "run_id": run_id,
            "status": "FAILED",
            "task": task_record,
            "objective": objective_id,
            "optimizer": manifest["optimizer"],
            "depth": depth,
            "seed": seed,
            "error_message": message,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="B1_DEPTH_BUDGET",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective=objective_id,
            optimizer=manifest["optimizer"],
            depth=depth,
            alpha=manifest["alpha"],
            nfev_budget=manifest["maximum_nfev"],
            actual_nfev=actual_nfev,
            shots=None,
            seed=seed,
            status="FAILED",
            started_at=started_at,
            finished_at=finished_at,
            runtime_s=runtime,
            error_message=message,
            git_commit=manifest["code_git_commit"],
            dirty_state_fingerprint=execution_code_fingerprint(manifest),
        )
        write_new_record(path, record)
        return "FAILED"


def _task_batch(
    task_record: dict[str, Any], manifest: dict[str, Any], output_root: str
) -> dict[str, int]:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    task = task_from_manifest_row(task_record)
    context = build_objective_context(task)
    counts: dict[str, int] = {}
    for depth in manifest["depths"]:
        for objective in manifest["objectives"]:
            for seed in manifest["seeds"]:
                status = _execute_trajectory(
                    task=task,
                    context=context,
                    task_record=task_record,
                    objective_id=objective,
                    depth=int(depth),
                    seed=int(seed),
                    manifest=manifest,
                    output_root=Path(output_root),
                )
                counts[status] = counts.get(status, 0) + 1
    return counts


def run_b1(*, smoke: bool = False, max_workers: int | None = None) -> dict[str, int]:
    manifest = load_json(MANIFEST_PATHS["depth_budget"])
    output_root = REVIEW_ROOT / "smoke" / "B1_depth_budget" if smoke else B1_ROOT
    tasks = list(manifest["tasks"])
    if smoke:
        tasks = sorted(tasks, key=lambda row: (row["m"], row["task_id"]))[:2]
    counts: dict[str, int] = {}
    workers = int(max_workers or (2 if smoke else 6))
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_task_batch, task, manifest, str(output_root))
            for task in tasks
        ]
        for future in as_completed(futures):
            for key, value in future.result().items():
                counts[key] = counts.get(key, 0) + value
    rebuild_registry()
    return counts


def _load_complete_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted((root / "runs").glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("status") == "COMPLETE":
            records.append(value)
    return records


def aggregate_b1(*, root: Path = B1_ROOT) -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATHS["depth_budget"])
    records = _load_complete_records(root)
    rows = []
    for record in records:
        task = record["task"]
        for checkpoint in record["checkpoints"]:
            rows.append(
                {
                    "run_id": record["run_id"],
                    "task_id": task["task_id"],
                    "graph_id": task["graph_id"],
                    "base_instance_id": task["base_instance_id"],
                    "size_stratum": task["size_stratum"],
                    "stress_level": task["stress_level"],
                    "m": task["m"],
                    "dilution_score": task["dilution_score"],
                    "feasible_fraction_phi": task["feasible_fraction_phi"],
                    "objective": record["objective"],
                    "alpha": record["alpha"],
                    "optimizer": record["optimizer"],
                    "depth": record["depth"],
                    "seed": record["seed"],
                    "budget": checkpoint["requested_nfev_budget"],
                    "effective_trajectory_nfev": checkpoint[
                        "effective_trajectory_nfev"
                    ],
                    "incumbent_evaluation_index": checkpoint[
                        "incumbent_evaluation_index"
                    ],
                    "actual_nfev_max_run": record["actual_objective_calls"],
                    "scipy_reported_nfev": record["scipy_reported_nfev"],
                    "nit": record["nit"],
                    "termination_reason": record["termination_reason"],
                    "optimizer_message": record["optimizer_message"],
                    "runtime_s": record["runtime_s"],
                    "parameters": json.dumps(checkpoint["parameters"]),
                    "objective_value": checkpoint["objective"],
                    "mean_energy": checkpoint["mean_energy"],
                    "P_feas": checkpoint["p_feas"],
                    "P_opt": checkpoint["p_opt"],
                    "P_opt_given_feas": checkpoint["p_opt_given_feas"],
                    "G_feas": checkpoint["G_feas"],
                    "tail_feasible_fraction": checkpoint["tail_feasible_fraction"],
                    "tail_fully_feasible": checkpoint["tail_fully_feasible"],
                    "early_termination_carried_forward": checkpoint[
                        "early_termination_carried_forward"
                    ],
                }
            )
    frame = pd.DataFrame(rows)
    output = root / "depth_budget_runs.csv"
    atomic_write_csv(output, frame)
    nested_rows = []
    if len(frame):
        lookup = {
            key: group.iloc[0]
            for key, group in frame.groupby(
                ["task_id", "objective", "seed", "depth", "budget"], sort=False
            )
        }
        task_records = {row["task_id"]: row for row in manifest["tasks"]}
        contexts: dict[str, tuple[Any, dict[str, Any]]] = {}
        tolerance = float(
            load_json(PROJECT_ROOT / manifest["protocol_path"])["global"][
                "comparison_tolerance"
            ]
        )
        for task_id in sorted(frame.task_id.unique()):
            task = task_from_manifest_row(task_records[task_id])
            contexts[task_id] = (task, build_objective_context(task))
        for (task_id, objective, seed, deeper, budget), deeper_row in lookup.items():
            if int(deeper) not in (3, 4):
                continue
            shallower_key = (task_id, objective, seed, int(deeper) - 1, budget)
            if shallower_key not in lookup:
                continue
            shallower = lookup[shallower_key]
            embedded = embed_parameters(
                np.asarray(json.loads(shallower.parameters), dtype=float),
                int(deeper) - 1,
                int(deeper),
            )
            task, context = contexts[task_id]
            embedded_eval = evaluate_parameters(
                task,
                context,
                embedded,
                int(deeper),
                alpha=float(manifest["alpha"]),
            )
            embedded_objective = (
                embedded_eval["mean_energy"]
                if objective == "O0"
                else embedded_eval["cvar"]
            )
            identity_error = float(embedded_objective - shallower.objective_value)
            regret = float(deeper_row.objective_value - embedded_objective)
            nested_rows.append(
                {
                    "task_id": task_id,
                    "graph_id": deeper_row.graph_id,
                    "objective": objective,
                    "seed": int(seed),
                    "transition": f"p{int(deeper)-1}->p{int(deeper)}",
                    "shallower_depth": int(deeper) - 1,
                    "deeper_depth": int(deeper),
                    "budget": int(budget),
                    "deeper_terminal_objective": deeper_row.objective_value,
                    "embedded_shallower_objective": embedded_objective,
                    "signed_nested_regret": regret,
                    "embedding_identity_error": identity_error,
                    "embedding_identity_pass": abs(identity_error) <= tolerance,
                    "nested_pass": regret <= tolerance,
                    "nested_failure": regret > tolerance,
                    "actual_nfev": int(deeper_row.actual_nfev_max_run),
                    "nit": int(deeper_row.nit),
                    "termination_reason": deeper_row.termination_reason,
                    "wall_time_s": deeper_row.runtime_s,
                }
            )
    nested = pd.DataFrame(nested_rows)
    atomic_write_csv(root / "nested_diagnostics.csv", nested)
    if len(nested) and not nested.embedding_identity_pass.all():
        raise RuntimeError("B1 zero-angle embedding identity failed")
    group = [
        "task_id",
        "graph_id",
        "size_stratum",
        "m",
        "objective",
        "depth",
        "budget",
    ]
    task_summary = (
        frame.groupby(group, as_index=False)
        .agg(
            seed_count=("seed", "nunique"),
            objective_value=("objective_value", "median"),
            mean_energy=("mean_energy", "median"),
            P_feas=("P_feas", "median"),
            P_opt=("P_opt", "median"),
            P_opt_given_feas=("P_opt_given_feas", "median"),
            G_feas=("G_feas", "median"),
            median_actual_nfev=("actual_nfev_max_run", "median"),
            median_nit=("nit", "median"),
            median_wall_time_s=("runtime_s", "median"),
        )
        if len(frame)
        else pd.DataFrame()
    )
    atomic_write_csv(root / "depth_budget_summary_task.csv", task_summary)
    graph_summary = (
        task_summary.groupby(
            ["graph_id", "size_stratum", "objective", "depth", "budget"],
            as_index=False,
        ).agg(
            n_tasks=("task_id", "nunique"),
            objective_value=("objective_value", "mean"),
            mean_energy=("mean_energy", "mean"),
            P_feas=("P_feas", "mean"),
            P_opt=("P_opt", "mean"),
            P_opt_given_feas=("P_opt_given_feas", "mean"),
            G_feas=("G_feas", "mean"),
        )
        if len(task_summary)
        else pd.DataFrame()
    )
    atomic_write_csv(root / "depth_budget_summary_graph.csv", graph_summary)
    effect_summary = pd.DataFrame()
    graph_effects = pd.DataFrame()
    if len(frame):
        _, graph_effects = paired_objective_effects(
            frame,
            value_column="G_feas",
            group_columns=["depth", "budget"],
        )
        settings = load_json(PROJECT_ROOT / manifest["protocol_path"])["global"]
        effect_summary = graph_effect_summary(
            graph_effects,
            group_columns=["depth", "budget"],
            resamples=int(settings["bootstrap_resamples"]),
            seed=int(settings["bootstrap_seed"]) + 100,
        )
    atomic_write_csv(root / "figure_data_O3_minus_O0_G_feas_graph.csv", graph_effects)
    atomic_write_csv(root / "depth_budget_effect_summary.csv", effect_summary)
    nested_summary = (
        nested.groupby(["transition", "budget", "objective"], as_index=False)
        .agg(
            nested_failure_count=("nested_failure", "sum"),
            nested_comparison_count=("nested_failure", "size"),
            median_signed_nested_regret=("signed_nested_regret", "median"),
        )
        if len(nested)
        else pd.DataFrame()
    )
    if len(nested_summary):
        nested_summary["nested_failure_rate"] = (
            nested_summary.nested_failure_count
            / nested_summary.nested_comparison_count
        )
    atomic_write_csv(root / "figure_data_nested_failure.csv", nested_summary)
    _plot_b1(root, graph_summary, effect_summary, nested_summary)
    planned = int(manifest["planned_optimizer_trajectories"])
    complete = len(records)
    failed = len(list((root / "runs").glob("*.json"))) - complete
    report = _b1_report(
        manifest, frame, graph_summary, effect_summary, nested_summary, planned, complete, failed
    )
    atomic_write_text(root / "B1_DEPTH_BUDGET.md", report)
    return {
        "planned_trajectories": planned,
        "complete_trajectories": complete,
        "failed_trajectories": failed,
        "checkpoint_rows": len(frame),
        "nested_rows": len(nested),
    }


def _plot_b1(
    root: Path,
    graph: pd.DataFrame,
    effects: pd.DataFrame,
    nested: pd.DataFrame,
) -> None:
    if not len(graph):
        return
    figure_root = root / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0), constrained_layout=True)
    if len(nested):
        for budget, group in nested.groupby("budget"):
            combined = group.groupby("transition", as_index=False).agg(
                rate=("nested_failure_rate", "mean")
            )
            axes[0].plot(combined.transition, combined.rate, marker="o", label=f"nfev={budget}")
    axes[0].set_ylabel("Nested failure rate")
    axes[0].set_xlabel("Depth transition")
    axes[0].set_ylim(bottom=0)
    axes[0].legend(frameon=False, fontsize=8)
    graph_depth = graph.groupby(["objective", "depth", "budget"], as_index=False).G_feas.median()
    for (objective, budget), group in graph_depth.groupby(["objective", "budget"]):
        axes[1].plot(
            group.depth,
            group.G_feas,
            marker="o",
            label=f"{objective}, {budget}",
        )
    axes[1].set_xlabel("QAOA depth p")
    axes[1].set_ylabel("Median graph-level $G_{feas}$")
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    if len(effects):
        for budget, group in effects.groupby("budget"):
            axes[2].errorbar(
                group.depth,
                group.graph_effect_mean,
                yerr=[
                    group.graph_effect_mean - group.graph_effect_ci_lower,
                    group.graph_effect_ci_upper - group.graph_effect_mean,
                ],
                marker="o",
                capsize=3,
                label=f"nfev={budget}",
            )
    axes[2].axhline(0.0, color="black", linewidth=0.8)
    axes[2].set_xlabel("QAOA depth p")
    axes[2].set_ylabel("Graph mean O3−O0 $G_{feas}$")
    axes[2].legend(frameon=False, fontsize=8)
    for axis in axes:
        axis.grid(alpha=0.2)
    for label, axis in zip("abc", axes):
        axis.text(-0.10, 1.06, label, transform=axis.transAxes, fontweight="bold")
    for suffix in ("png", "pdf"):
        fig.savefig(figure_root / f"Figure_R1_depth_budget.{suffix}", dpi=300)
    plt.close(fig)


def _b1_report(
    manifest: dict[str, Any],
    frame: pd.DataFrame,
    graph: pd.DataFrame,
    effects: pd.DataFrame,
    nested: pd.DataFrame,
    planned: int,
    complete: int,
    failed: int,
) -> str:
    status = "COMPLETE" if complete == planned and failed == 0 else "PARTIAL"
    lines = [
        "# B1 — Depth × optimization-budget ablation",
        "",
        f"**Execution status: {status}.** Completed {complete}/{planned} optimizer trajectories; failed records: {failed}; checkpoint rows: {len(frame)}.",
        "",
        "## Protocol",
        "",
        f"The outcome-blind manifest freezes {len(manifest['tasks'])} discovery tasks spanning {len(manifest['graph_ids'])} graphs, p=2/3/4, O0/O3 (alpha=0.10), three original seeds, COBYLA, and nfev checkpoints 120/240/480. The resource unit is actual objective calls, not iterations.",
        "",
        "One deterministic 480-call trajectory is used only because the smoke gate verified that its first 120 and 240 calls are exactly identical to separately capped trajectories. Each checkpoint is the best evaluated incumbent in that genuine prefix; early solver termination is explicitly carried and flagged.",
        "",
        f"Manifest: `results/reviewer_robustness/manifests/manifest_depth_budget.json`.",
        "",
        "## Numerical findings",
        "",
    ]
    if not len(frame):
        lines.extend(["No complete trajectories are available yet.", ""])
    else:
        for transition in ("p2->p3", "p3->p4"):
            subset = nested[nested.transition == transition]
            for budget in (120, 240, 480):
                row = subset[subset.budget == budget]
                if len(row):
                    rate = row.nested_failure_count.sum() / row.nested_comparison_count.sum()
                    lines.append(
                        f"- {transition} at {budget} nfev: {int(row.nested_failure_count.sum())}/{int(row.nested_comparison_count.sum())} nested failures ({rate:.3f})."
                    )
        for budget in (120, 240, 480):
            row = effects[effects.budget == budget] if len(effects) else pd.DataFrame()
            if len(row):
                p4 = row[row.depth == 4]
                if len(p4):
                    value = p4.iloc[0]
                    lines.append(
                        f"- p=4, {budget} nfev: graph mean O3−O0 G_feas={value.graph_effect_mean:.4f}, 95% graph-cluster bootstrap CI [{value.graph_effect_ci_lower:.4f}, {value.graph_effect_ci_upper:.4f}]."
                    )
    lines.extend(
        [
            "",
            "## Interpretation and limitations",
            "",
            "Depth comparisons are optimization-budget-conditioned. If p=4 remains below p=3 at 480 evaluations, the only licensed wording is that increased depth was not recovered within the tested classical evaluation budgets; this experiment does not diagnose a barren plateau or intrinsic depth disadvantage.",
            "",
            "Task rows are descriptive. Robustness intervals use paired task effects averaged within graph, then equal-weight graph resampling. These post-hoc results neither replace frozen headlines nor enter the preregistered H1/H2 family.",
            "",
            "## Claim impact",
            "",
            ("The claim impact is assessable from the complete matrix above." if status == "COMPLETE" else "No paper wording should be changed from this incomplete matrix."),
            "",
        ]
    )
    return "\n".join(lines)
