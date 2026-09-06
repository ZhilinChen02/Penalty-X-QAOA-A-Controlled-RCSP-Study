"""A2 post-hoc CVaR-alpha sensitivity with alpha=1 endpoint control."""

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

from .common import (
    REVIEW_ROOT,
    build_objective_context,
    embed_parameters,
    evaluate_parameters,
    exact_objective_callable,
    load_json,
    parse_parameters,
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
from .statistics import bootstrap_mean_ci


A2_ROOT = REVIEW_ROOT / "A2_alpha"
DISCOVERY_P2 = (
    PROJECT_ROOT / "results" / "phase1_pilot_v1" / "master_seed_level_results.csv"
)
HELDOUT_P2 = (
    PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "p2_initialization_runs.csv"
)


def _p2_lookup(split: str, task_ids: set[str]) -> dict[tuple[str, int], dict[str, Any]]:
    if split == "discovery":
        frame = pd.read_csv(DISCOVERY_P2)
        frame = frame[
            frame.task_id.isin(task_ids)
            & (frame.algorithm == "Penalty-X")
            & (frame.depth == 2)
        ].copy()
    elif split == "heldout":
        frame = pd.read_csv(HELDOUT_P2)
        frame = frame[frame.task_id.isin(task_ids) & (frame.depth == 2)].copy()
    else:
        raise ValueError("split must be discovery or heldout")
    lookup = {
        (str(row["task_id"]), int(row["optimizer_seed"])): row
        for row in frame.to_dict(orient="records")
    }
    if len(lookup) != 3 * len(task_ids):
        raise RuntimeError(f"{split} p2 seed rows are incomplete")
    return lookup


def _execute_run(
    *,
    split: str,
    task: Any,
    context: dict[str, Any],
    task_record: dict[str, Any],
    p2_row: dict[str, Any],
    alpha: float,
    seed: int,
    manifest: dict[str, Any],
    output_root: Path,
) -> str:
    run_id = stable_run_id(
        "a2",
        split,
        task.task_id,
        f"{alpha:.12g}",
        seed,
        manifest["evaluation_budget"],
        execution_code_fingerprint(manifest),
    )
    path = output_root / "runs" / f"{run_id}.json"
    if read_valid_terminal_record(path, run_id=run_id) is not None:
        return "SKIPPED_EXISTING"
    started_at = utc_timestamp()
    started = time.perf_counter()
    actual_nfev = None
    try:
        parameter_field = "optimized_parameters" if split == "discovery" else "terminal_parameters"
        initial = embed_parameters(parse_parameters(p2_row[parameter_field]), 2, 3)
        objective = exact_objective_callable(context, 3, "O3", float(alpha))
        protocol = load_json(PROJECT_ROOT / manifest["protocol_path"])
        result = optimize_with_strict_nfev(
            objective,
            initial,
            method=manifest["optimizer"],
            max_nfev=int(manifest["evaluation_budget"]),
            timeout_s=float(protocol["global"]["timeout_s"]),
            settings={
                "cobyla_rhobeg": protocol["alpha_sensitivity"]["cobyla_rhobeg"],
                "cobyla_catol": protocol["alpha_sensitivity"]["cobyla_catol"],
            },
        )
        actual_nfev = result.nfev
        terminal = evaluate_parameters(
            task, context, result.terminal_parameters, 3, alpha=float(alpha)
        )
        endpoint_error = float(terminal["cvar"] - terminal["mean_energy"])
        if float(alpha) == 1.0 and abs(endpoint_error) > 1e-10:
            raise RuntimeError("CVaR alpha=1 failed mean-energy endpoint identity")
        status = "TIMEOUT" if result.termination_reason == "WALLTIME_LIMIT" else "COMPLETE"
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        record = {
            "schema_version": "qroute-dilution.A2.alpha-run.v1",
            "experiment": "A2_ALPHA_SENSITIVITY",
            "run_id": run_id,
            "status": status,
            "split": split,
            "result_label": (
                "POST_HOC_DISCOVERY_SENSITIVITY"
                if split == "discovery"
                else manifest["heldout_result_label"]
            ),
            "task": task_record,
            "objective": "O3",
            "alpha": float(alpha),
            "optimizer": manifest["optimizer"],
            "depth": int(manifest["depth"]),
            "seed": int(seed),
            "source_p2_run_id": p2_row["run_id"],
            "nfev_budget": int(manifest["evaluation_budget"]),
            "actual_objective_calls": result.nfev,
            "scipy_reported_nfev": result.scipy_reported_nfev,
            "nit": result.nit,
            "optimizer_status": result.status,
            "optimizer_success": result.scipy_success,
            "optimizer_message": result.message,
            "termination_reason": result.termination_reason,
            "initial_parameters": initial.tolist(),
            "terminal_parameters": result.terminal_parameters.tolist(),
            "objective_initial": result.objective_initial,
            "terminal_objective_observed": result.terminal_objective_observed,
            "terminal_exact_evaluation": terminal,
            "alpha1_minus_mean_endpoint_error": endpoint_error,
            "runtime_s": result.runtime_s,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A2_ALPHA_SENSITIVITY",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective="O3",
            optimizer=manifest["optimizer"],
            depth=manifest["depth"],
            alpha=alpha,
            nfev_budget=manifest["evaluation_budget"],
            actual_nfev=result.nfev,
            shots=None,
            seed=seed,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            runtime_s=runtime,
            error_message="",
            git_commit=manifest["code_git_commit"],
            dirty_state_fingerprint=execution_code_fingerprint(manifest),
        )
        write_new_record(path, record)
        return status
    except Exception as exc:
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        message = f"{type(exc).__name__}: {exc}"
        record = {
            "schema_version": "qroute-dilution.A2.alpha-run.v1",
            "experiment": "A2_ALPHA_SENSITIVITY",
            "run_id": run_id,
            "status": "FAILED",
            "split": split,
            "task": task_record,
            "alpha": alpha,
            "seed": seed,
            "actual_objective_calls": actual_nfev,
            "error_message": message,
            "runtime_s": runtime,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A2_ALPHA_SENSITIVITY",
            run_id=run_id,
            task_id=task_record["task_id"],
            graph_id=task_record["graph_id"],
            objective="O3",
            optimizer=manifest["optimizer"],
            depth=manifest["depth"],
            alpha=alpha,
            nfev_budget=manifest["evaluation_budget"],
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
    split: str,
    task_record: dict[str, Any],
    p2_rows: dict[int, dict[str, Any]],
    alphas: list[float],
    manifest: dict[str, Any],
    output_root: str,
) -> dict[str, int]:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    task = task_from_manifest_row(task_record)
    context = build_objective_context(task)
    counts: dict[str, int] = {}
    for alpha in alphas:
        for seed in manifest["seeds"]:
            status = _execute_run(
                split=split,
                task=task,
                context=context,
                task_record=task_record,
                p2_row=p2_rows[int(seed)],
                alpha=float(alpha),
                seed=int(seed),
                manifest=manifest,
                output_root=Path(output_root),
            )
            counts[status] = counts.get(status, 0) + 1
    return counts


def run_a2(
    *,
    split: str = "discovery",
    scope: str = "full",
    smoke: bool = False,
    max_workers: int | None = None,
) -> dict[str, int]:
    manifest = load_json(MANIFEST_PATHS["alpha"])
    if split == "discovery":
        tasks = list(manifest["discovery_tasks"])
        alphas = list(manifest["alphas"]["discovery"])
    elif split == "heldout":
        tasks = list(manifest["heldout_tasks"])
        alphas = list(manifest["alphas"]["heldout"])
        if scope == "initial":
            allowed = set(manifest["heldout_initial_task_ids"])
            tasks = [row for row in tasks if row["task_id"] in allowed]
    else:
        raise ValueError("split must be discovery or heldout")
    if split == "discovery" and scope == "initial24":
        optimizer_manifest = load_json(MANIFEST_PATHS["optimizer"])
        allowed = set(optimizer_manifest["initial_24_task_ids"])
        tasks = [row for row in tasks if row["task_id"] in allowed]
    elif scope not in {"full", "initial", "initial24"}:
        raise ValueError("invalid A2 scope")
    output_root = REVIEW_ROOT / "smoke" / "A2_alpha" if smoke else A2_ROOT
    if smoke:
        tasks = sorted(tasks, key=lambda row: (row["m"], row["task_id"]))[:1]
        alphas = [0.1, 1.0]
        reduced = json.loads(json.dumps(manifest))
        reduced["seeds"] = reduced["seeds"][:1]
        manifest = reduced
    else:
        # Start costly statevectors first; scheduling cannot alter any run seed or result.
        tasks = sorted(tasks, key=lambda row: (-int(row["m"]), row["task_id"]))
    p2 = _p2_lookup(split, {row["task_id"] for row in tasks})
    counts: dict[str, int] = {}
    with ProcessPoolExecutor(max_workers=int(max_workers or (1 if smoke else 6))) as executor:
        futures = []
        for task in tasks:
            task_p2 = {seed: p2[(task["task_id"], seed)] for seed in manifest["seeds"]}
            futures.append(
                executor.submit(
                    _task_batch,
                    split,
                    task,
                    task_p2,
                    alphas,
                    manifest,
                    str(output_root),
                )
            )
        for future in as_completed(futures):
            for key, value in future.result().items():
                counts[key] = counts.get(key, 0) + value
    rebuild_registry()
    return counts


def aggregate_a2() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATHS["alpha"])
    paths = sorted((A2_ROOT / "runs").glob("*.json"))
    records = [load_json(path) for path in paths]
    complete = [record for record in records if record.get("status") == "COMPLETE"]
    rows = []
    for record in complete:
        task = record["task"]
        exact = record["terminal_exact_evaluation"]
        rows.append(
            {
                "run_id": record["run_id"],
                "split": record["split"],
                "result_label": record["result_label"],
                "task_id": task["task_id"],
                "graph_id": task["graph_id"],
                "size_stratum": task["size_stratum"],
                "m": task["m"],
                "dilution_score": task["dilution_score"],
                "alpha": record["alpha"],
                "seed": record["seed"],
                "optimizer": record["optimizer"],
                "depth": record["depth"],
                "nfev_budget": record["nfev_budget"],
                "actual_nfev": record["actual_objective_calls"],
                "scipy_reported_nfev": record["scipy_reported_nfev"],
                "nit": record["nit"],
                "termination_reason": record["termination_reason"],
                "wall_time_s": record["runtime_s"],
                "optimized_objective": exact["cvar"],
                "mean_energy": exact["mean_energy"],
                "P_feas": exact["p_feas"],
                "P_opt": exact["p_opt"],
                "P_opt_given_feas": exact["p_opt_given_feas"],
                "G_feas": exact["G_feas"],
                "tail_feasible_fraction": exact["tail_feasible_fraction"],
                "tail_fully_feasible": exact["tail_fully_feasible"],
                "alpha1_minus_mean_endpoint_error": record[
                    "alpha1_minus_mean_endpoint_error"
                ],
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(A2_ROOT / "alpha_runs.csv", frame)
    groups = ["split", "task_id", "graph_id", "size_stratum", "m", "alpha"]
    task_summary = (
        frame.groupby(groups, as_index=False).agg(
            seed_count=("seed", "nunique"),
            optimized_objective=("optimized_objective", "median"),
            mean_energy=("mean_energy", "median"),
            P_feas=("P_feas", "median"),
            P_opt=("P_opt", "median"),
            P_opt_given_feas=("P_opt_given_feas", "median"),
            G_feas=("G_feas", "median"),
            tail_feasible_fraction=("tail_feasible_fraction", "median"),
            fully_feasible_tail_fraction=("tail_fully_feasible", "mean"),
            median_nfev=("actual_nfev", "median"),
            median_wall_time_s=("wall_time_s", "median"),
        )
        if len(frame)
        else pd.DataFrame()
    )
    atomic_write_csv(A2_ROOT / "alpha_summary_task.csv", task_summary)
    graph_summary = (
        task_summary.groupby(["split", "graph_id", "alpha"], as_index=False).agg(
            n_tasks=("task_id", "nunique"),
            optimized_objective=("optimized_objective", "mean"),
            mean_energy=("mean_energy", "mean"),
            P_feas=("P_feas", "mean"),
            P_opt=("P_opt", "mean"),
            P_opt_given_feas=("P_opt_given_feas", "mean"),
            G_feas=("G_feas", "mean"),
            tail_feasible_fraction=("tail_feasible_fraction", "mean"),
        )
        if len(task_summary)
        else pd.DataFrame()
    )
    atomic_write_csv(A2_ROOT / "alpha_summary_graph.csv", graph_summary)
    inference = _alpha_inference(graph_summary, manifest)
    atomic_write_csv(A2_ROOT / "alpha_effect_summary.csv", inference)
    _plot_a2(graph_summary, inference)
    report = _a2_report(manifest, frame, task_summary, inference, len(paths) - len(complete))
    atomic_write_text(A2_ROOT / "A2_ALPHA_SENSITIVITY.md", report)
    return {
        "complete_runs": len(complete),
        "failed_runs": len(paths) - len(complete),
        "discovery_tasks_complete": int(
            frame[frame.split == "discovery"].task_id.nunique()
        ) if len(frame) else 0,
        "heldout_tasks_complete": int(
            frame[frame.split == "heldout"].task_id.nunique()
        ) if len(frame) else 0,
    }


def _alpha_inference(graph: pd.DataFrame, manifest: dict[str, Any]) -> pd.DataFrame:
    settings = load_json(PROJECT_ROOT / manifest["protocol_path"])["global"]
    rows = []
    for split, split_frame in graph.groupby("split") if len(graph) else []:
        endpoint = split_frame[split_frame.alpha == 1.0].set_index("graph_id")
        for alpha, group in split_frame.groupby("alpha"):
            common = sorted(set(group.graph_id) & set(endpoint.index))
            values = np.asarray(
                [
                    float(group[group.graph_id == graph_id].iloc[0].G_feas)
                    - float(endpoint.loc[graph_id].G_feas)
                    for graph_id in common
                ]
            )
            if not len(values):
                continue
            summary = bootstrap_mean_ci(
                values,
                resamples=int(settings["bootstrap_resamples"]),
                seed=int(settings["bootstrap_seed"]) + int(round(alpha * 10000)),
            )
            rows.append(
                {
                    "split": split,
                    "alpha": alpha,
                    "reference_alpha": 1.0,
                    "n_graphs": len(common),
                    **{f"delta_G_vs_alpha1_{key}": value for key, value in summary.items()},
                }
            )
    return pd.DataFrame(rows)


def _plot_a2(graph: pd.DataFrame, inference: pd.DataFrame) -> None:
    if not len(graph):
        return
    figure_root = A2_ROOT / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    discovery = graph[graph.split == "discovery"]
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.7), constrained_layout=True)
    for axis, metric, label in zip(
        axes,
        ("G_feas", "P_feas", "P_opt"),
        ("$G_{feas}$", "$P_{feas}$", "$P_{opt}$"),
    ):
        summary = discovery.groupby("alpha")[metric].agg(["mean", "std", "count"]).reset_index()
        error = summary["std"] / np.sqrt(summary["count"])
        axis.errorbar(summary.alpha, summary["mean"], yerr=error, marker="o", capsize=3)
        axis.set_xscale("log")
        axis.set_xlabel("CVaR alpha")
        axis.set_ylabel(f"Mean graph-level {label}")
        axis.grid(alpha=0.2)
    for panel, axis in zip("abc", axes):
        axis.text(-0.10, 1.06, panel, transform=axis.transAxes, fontweight="bold")
    for suffix in ("png", "pdf"):
        fig.savefig(figure_root / f"Figure_R2_alpha_sensitivity.{suffix}", dpi=300)
    plt.close(fig)


def _a2_report(
    manifest: dict[str, Any],
    frame: pd.DataFrame,
    task: pd.DataFrame,
    inference: pd.DataFrame,
    failed: int,
) -> str:
    discovery_planned = len(manifest["discovery_tasks"]) * len(manifest["alphas"]["discovery"]) * len(manifest["seeds"])
    discovery_complete = len(frame[frame.split == "discovery"]) if len(frame) else 0
    alpha1_error = (
        frame[frame.alpha == 1.0].alpha1_minus_mean_endpoint_error.abs().max()
        if len(frame) and (frame.alpha == 1.0).any()
        else math.nan
    )
    lines = [
        "# A2 — CVaR alpha sensitivity",
        "",
        f"Discovery completion: {discovery_complete}/{discovery_planned} runs. Failed records across executed scopes: {failed}.",
        "",
        "## Protocol",
        "",
        "The discovery scan freezes alpha={0.02,0.05,0.10,0.25,0.50,1.00}, COBYLA, p=3, the original three p2-seed embeddings, and 120 actual objective calls. Alpha=0.10 remains the historical frozen choice; no sensitivity result can replace the preregistered held-out headline. Every non-0.10 held-out row is labelled POST_HOC_SENSITIVITY.",
        "",
        "Manifest: `results/reviewer_robustness/manifests/manifest_alpha_sensitivity.json`.",
        "",
        "## Numerical findings",
        "",
        f"The maximum observed |CVaR(alpha=1)−mean energy| is {alpha1_error:.3e}; this is the mathematical endpoint control, not a claim that optimized feasibility must be monotone in alpha.",
        "",
    ]
    for row in inference[inference.split == "discovery"].itertuples(index=False) if len(inference) else []:
        lines.append(
            f"- alpha={row.alpha:g}: graph mean G_feas difference versus alpha=1 is {row.delta_G_vs_alpha1_mean:.4f}, 95% graph-cluster bootstrap CI [{row.delta_G_vs_alpha1_ci_lower:.4f}, {row.delta_G_vs_alpha1_ci_upper:.4f}]."
        )
    if len(task):
        wide = task[task.split == "discovery"].pivot(index="task_id", columns="alpha", values="G_feas")
        nonmonotonic = 0
        for values in wide.to_numpy(dtype=float):
            differences = np.diff(values)
            if not (np.all(differences >= -1e-12) or np.all(differences <= 1e-12)):
                nonmonotonic += 1
        lines.append(f"- Non-monotone optimized G_feas trajectories: {nonmonotonic}/{len(wide)} tasks (reported descriptively; no monotonicity was preregistered).")
    lines.extend(
        [
            "",
            "## Interpretation and limitation",
            "",
            "Robustness is judged as a neighborhood around alpha=0.10, not by selecting the best alpha. Task rows are descriptive and graph-level intervals are post-hoc. These results do not alter the frozen confirmatory family.",
            "",
            "## Claim impact",
            "",
            ("The complete discovery grid can determine whether alpha=0.10 is locally robust." if discovery_complete == discovery_planned and failed == 0 else "The alpha grid is incomplete; brittleness or robustness should not yet be asserted."),
            "If the complete graph-level scan supports a neighborhood, the paper may report that neighborhood as post-hoc robustness while retaining alpha=0.10 as the sole frozen confirmatory choice; it must not select a replacement alpha from these results.",
            "",
        ]
    )
    return "\n".join(lines)
