"""A1 local-optimizer robustness and certified-pass mechanism analysis."""

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
from .statistics import bootstrap_mean_ci, graph_effect_summary, paired_objective_effects


A1_ROOT = REVIEW_ROOT / "A1_optimizer"


def _optimizer_settings(protocol: dict[str, Any]) -> dict[str, float | bool]:
    return {
        "cobyla_rhobeg": 0.5,
        "cobyla_catol": 1e-8,
        "nelder_mead_xatol": protocol["nelder_mead_xatol"],
        "nelder_mead_fatol": protocol["nelder_mead_fatol"],
        "nelder_mead_adaptive": protocol["nelder_mead_adaptive"],
        "slsqp_ftol": protocol["slsqp_ftol"],
    }


def _execute_run(
    *,
    task: Any,
    context: dict[str, Any],
    task_record: dict[str, Any],
    optimizer: str,
    objective_id: str,
    depth: int,
    seed: int,
    manifest: dict[str, Any],
    output_root: Path,
) -> str:
    run_id = stable_run_id(
        "a1",
        task.task_id,
        optimizer,
        objective_id,
        depth,
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
        alpha = float(manifest["alpha"])
        x0 = initial_parameters(int(depth), int(seed))
        objective = exact_objective_callable(context, depth, objective_id, alpha)
        protocol = load_json(PROJECT_ROOT / manifest["protocol_path"])
        result = optimize_with_strict_nfev(
            objective,
            x0,
            method=optimizer,
            max_nfev=int(manifest["evaluation_budget"]),
            timeout_s=float(protocol["global"]["timeout_s"]),
            settings=_optimizer_settings(protocol["optimizer_robustness"]),
        )
        actual_nfev = result.nfev
        terminal = evaluate_parameters(
            task, context, result.terminal_parameters, depth, alpha=alpha
        )
        exact_objective = (
            terminal["mean_energy"] if objective_id == "O0" else terminal["cvar"]
        )
        status = "TIMEOUT" if result.termination_reason == "WALLTIME_LIMIT" else "COMPLETE"
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        record = {
            "schema_version": "qroute-dilution.A1.optimizer-run.v1",
            "experiment": "A1_OPTIMIZER_ROBUSTNESS",
            "run_id": run_id,
            "status": status,
            "task": task_record,
            "optimizer": optimizer,
            "objective": objective_id,
            "alpha": alpha,
            "depth": int(depth),
            "seed": int(seed),
            "nfev_budget": int(manifest["evaluation_budget"]),
            "actual_objective_calls": result.nfev,
            "scipy_reported_nfev": result.scipy_reported_nfev,
            "nfev_accounting_match": (
                result.scipy_reported_nfev is None
                or result.scipy_reported_nfev == result.nfev
            ),
            "nit": result.nit,
            "optimizer_status": result.status,
            "optimizer_success": result.scipy_success,
            "optimizer_message": result.message,
            "termination_reason": result.termination_reason,
            "initial_parameters": x0.tolist(),
            "terminal_parameters": result.terminal_parameters.tolist(),
            "best_evaluated_parameters": result.best_evaluated_parameters.tolist(),
            "objective_initial": result.objective_initial,
            "terminal_objective_observed": result.terminal_objective_observed,
            "terminal_objective_exact": exact_objective,
            "best_evaluated_objective": result.best_evaluated_objective,
            "terminal_exact_evaluation": terminal,
            "runtime_s": result.runtime_s,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A1_OPTIMIZER_ROBUSTNESS",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective=objective_id,
            optimizer=optimizer,
            depth=depth,
            alpha=alpha,
            nfev_budget=int(manifest["evaluation_budget"]),
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
            "schema_version": "qroute-dilution.A1.optimizer-run.v1",
            "experiment": "A1_OPTIMIZER_ROBUSTNESS",
            "run_id": run_id,
            "status": "FAILED",
            "task": task_record,
            "optimizer": optimizer,
            "objective": objective_id,
            "depth": depth,
            "seed": seed,
            "actual_objective_calls": actual_nfev,
            "error_message": message,
            "runtime_s": runtime,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A1_OPTIMIZER_ROBUSTNESS",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective=objective_id,
            optimizer=optimizer,
            depth=depth,
            alpha=manifest["alpha"],
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


def _task_batch(task_record: dict[str, Any], manifest: dict[str, Any], output_root: str) -> dict[str, int]:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    task = task_from_manifest_row(task_record)
    context = build_objective_context(task)
    counts: dict[str, int] = {}
    for optimizer in manifest["optimizers"]:
        for objective in manifest["objectives"]:
            for depth in manifest["depths"]:
                for seed in manifest["seeds"]:
                    status = _execute_run(
                        task=task,
                        context=context,
                        task_record=task_record,
                        optimizer=optimizer,
                        objective_id=objective,
                        depth=int(depth),
                        seed=int(seed),
                        manifest=manifest,
                        output_root=Path(output_root),
                    )
                    counts[status] = counts.get(status, 0) + 1
    return counts


def run_a1(
    *, scope: str = "full", smoke: bool = False, max_workers: int | None = None
) -> dict[str, int]:
    manifest = load_json(MANIFEST_PATHS["optimizer"])
    tasks = list(manifest["tasks"])
    if scope == "initial24":
        allowed = set(manifest["initial_24_task_ids"])
        tasks = [row for row in tasks if row["task_id"] in allowed]
    elif scope != "full":
        raise ValueError("scope must be initial24 or full")
    output_root = REVIEW_ROOT / "smoke" / "A1_optimizer" if smoke else A1_ROOT
    if smoke:
        tasks = sorted(tasks, key=lambda row: (row["m"], row["task_id"]))[:1]
        reduced = json.loads(json.dumps(manifest))
        reduced["optimizers"] = ["COBYLA", "SLSQP"]
        reduced["seeds"] = reduced["seeds"][:1]
        manifest = reduced
    counts: dict[str, int] = {}
    with ProcessPoolExecutor(max_workers=int(max_workers or (1 if smoke else 6))) as executor:
        futures = [
            executor.submit(_task_batch, task, manifest, str(output_root)) for task in tasks
        ]
        for future in as_completed(futures):
            for key, value in future.result().items():
                counts[key] = counts.get(key, 0) + value
    rebuild_registry()
    return counts


def aggregate_a1() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATHS["optimizer"])
    records = []
    all_paths = list((A1_ROOT / "runs").glob("*.json"))
    for path in sorted(all_paths):
        value = load_json(path)
        if value.get("status") == "COMPLETE":
            records.append(value)
    rows = []
    for record in records:
        task = record["task"]
        exact = record["terminal_exact_evaluation"]
        rows.append(
            {
                "run_id": record["run_id"],
                "task_id": task["task_id"],
                "graph_id": task["graph_id"],
                "size_stratum": task["size_stratum"],
                "m": task["m"],
                "dilution_score": task["dilution_score"],
                "optimizer": record["optimizer"],
                "objective": record["objective"],
                "alpha": record["alpha"],
                "depth": record["depth"],
                "seed": record["seed"],
                "nfev_budget": record["nfev_budget"],
                "actual_nfev": record["actual_objective_calls"],
                "scipy_reported_nfev": record["scipy_reported_nfev"],
                "nfev_accounting_match": record["nfev_accounting_match"],
                "nit": record["nit"],
                "success": record["optimizer_success"],
                "status": record["optimizer_status"],
                "message": record["optimizer_message"],
                "termination_reason": record["termination_reason"],
                "wall_time_s": record["runtime_s"],
                "initial_parameters": json.dumps(record["initial_parameters"]),
                "terminal_parameters": json.dumps(record["terminal_parameters"]),
                "objective_value": record["terminal_objective_exact"],
                "mean_energy": exact["mean_energy"],
                "P_feas": exact["p_feas"],
                "P_opt": exact["p_opt"],
                "P_opt_given_feas": exact["p_opt_given_feas"],
                "G_feas": exact["G_feas"],
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(A1_ROOT / "optimizer_runs.csv", frame)
    nested_rows = []
    lookup = {
        key: group.iloc[0]
        for key, group in frame.groupby(
            ["task_id", "optimizer", "objective", "seed", "depth"], sort=False
        )
    } if len(frame) else {}
    task_records = {row["task_id"]: row for row in manifest["tasks"]}
    contexts: dict[str, tuple[Any, dict[str, Any]]] = {}
    tolerance = float(
        load_json(PROJECT_ROOT / manifest["protocol_path"])["global"]["comparison_tolerance"]
    )
    for task_id in sorted(frame.task_id.unique()) if len(frame) else []:
        task = task_from_manifest_row(task_records[task_id])
        contexts[task_id] = (task, build_objective_context(task))
    for (task_id, optimizer, objective, seed, depth), deeper in lookup.items():
        if int(depth) != 3:
            continue
        key = (task_id, optimizer, objective, seed, 2)
        if key not in lookup:
            continue
        shallower = lookup[key]
        embedded = embed_parameters(parse_parameters(shallower.terminal_parameters), 2, 3)
        task, context = contexts[task_id]
        embedded_eval = evaluate_parameters(
            task, context, embedded, 3, alpha=float(manifest["alpha"])
        )
        embedded_objective = embedded_eval["mean_energy"] if objective == "O0" else embedded_eval["cvar"]
        identity_error = float(embedded_objective - shallower.objective_value)
        regret = float(deeper.objective_value - embedded_objective)
        nested_rows.append(
            {
                "task_id": task_id,
                "graph_id": deeper.graph_id,
                "optimizer": optimizer,
                "objective": objective,
                "seed": seed,
                "embedded_p2_objective": embedded_objective,
                "terminal_p3_objective": deeper.objective_value,
                "signed_nested_regret": regret,
                "embedding_identity_error": identity_error,
                "embedding_identity_pass": abs(identity_error) <= tolerance,
                "nested_pass": regret <= tolerance,
                "nested_failure": regret > tolerance,
                "embedded_p2_mean_energy": embedded_eval["mean_energy"],
                "embedded_p2_P_feas": embedded_eval["p_feas"],
                "embedded_p2_G_feas": embedded_eval["G_feas"],
                "terminal_p3_mean_energy": deeper.mean_energy,
                "terminal_p3_P_feas": deeper.P_feas,
                "terminal_p3_G_feas": deeper.G_feas,
                "actual_nfev": deeper.actual_nfev,
                "scipy_reported_nfev": deeper.scipy_reported_nfev,
                "nit": deeper.nit,
                "termination_reason": deeper.termination_reason,
                "wall_time_s": deeper.wall_time_s,
            }
        )
    nested = pd.DataFrame(nested_rows)
    atomic_write_csv(A1_ROOT / "optimizer_nested.csv", nested)
    if len(nested) and not nested.embedding_identity_pass.all():
        raise RuntimeError("A1 exact p2->p3 embedding identity failed")
    pass_rows = []
    if len(nested):
        pass_lookup = nested.set_index(["task_id", "optimizer", "objective", "seed"])
        for key in sorted(
            set(
                (row.task_id, row.optimizer, row.seed)
                for row in nested.itertuples(index=False)
            )
        ):
            task_id, optimizer, seed = key
            o0_key = (task_id, optimizer, "O0", seed)
            o3_key = (task_id, optimizer, "O3", seed)
            if o0_key not in pass_lookup.index or o3_key not in pass_lookup.index:
                continue
            o0_diag = pass_lookup.loc[o0_key]
            o3_diag = pass_lookup.loc[o3_key]
            if not (bool(o0_diag.nested_pass) and bool(o3_diag.nested_pass)):
                continue
            o0 = lookup[(task_id, optimizer, "O0", seed, 3)]
            o3 = lookup[(task_id, optimizer, "O3", seed, 3)]
            pass_rows.append(
                {
                    "task_id": task_id,
                    "graph_id": o0.graph_id,
                    "optimizer": optimizer,
                    "seed": seed,
                    "O0_mean_energy": o0.mean_energy,
                    "O3_mean_energy": o3.mean_energy,
                    "O0_P_feas": o0.P_feas,
                    "O3_P_feas": o3.P_feas,
                    "O0_G_feas": o0.G_feas,
                    "O3_G_feas": o3.G_feas,
                    "delta_mean_energy_O3_minus_O0": o3.mean_energy - o0.mean_energy,
                    "delta_P_feas_O3_minus_O0": o3.P_feas - o0.P_feas,
                    "delta_G_feas_O3_minus_O0": o3.G_feas - o0.G_feas,
                    "O0_lower_energy_but_lower_feasibility_than_O3": bool(
                        o0.mean_energy < o3.mean_energy - tolerance
                        and o0.P_feas < o3.P_feas - tolerance
                    ),
                    "O0_pass_improves_energy_but_reduces_feasibility_vs_embedded_p2": bool(
                        o0.mean_energy < o0_diag.embedded_p2_mean_energy - tolerance
                        and o0.P_feas < o0_diag.embedded_p2_P_feas - tolerance
                    ),
                }
            )
    pass_frame = pd.DataFrame(pass_rows)
    atomic_write_csv(A1_ROOT / "optimizer_pass_subset.csv", pass_frame)
    task_summary = (
        frame.groupby(["task_id", "graph_id", "optimizer", "objective", "depth"], as_index=False)
        .agg(
            seed_count=("seed", "nunique"),
            objective_value=("objective_value", "median"),
            mean_energy=("mean_energy", "median"),
            P_feas=("P_feas", "median"),
            P_opt=("P_opt", "median"),
            P_opt_given_feas=("P_opt_given_feas", "median"),
            G_feas=("G_feas", "median"),
            median_nfev=("actual_nfev", "median"),
            median_nit=("nit", "median"),
            median_wall_time_s=("wall_time_s", "median"),
        )
        if len(frame)
        else pd.DataFrame()
    )
    atomic_write_csv(A1_ROOT / "optimizer_summary_task.csv", task_summary)
    graph_summary = (
        task_summary.groupby(["graph_id", "optimizer", "objective", "depth"], as_index=False)
        .agg(
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
    atomic_write_csv(A1_ROOT / "optimizer_summary_graph.csv", graph_summary)
    summary = _optimizer_summary(nested, graph_summary, pass_frame, manifest)
    atomic_write_csv(A1_ROOT / "optimizer_summary.csv", summary)
    _plot_a1(summary)
    failed = len(all_paths) - len(records)
    report = _a1_report(manifest, frame, nested, pass_frame, summary, failed)
    atomic_write_text(A1_ROOT / "A1_OPTIMIZER_ROBUSTNESS.md", report)
    return {
        "planned_runs": manifest["planned_optimizer_runs"],
        "complete_runs": len(records),
        "failed_runs": failed,
        "nested_comparisons": len(nested),
        "certified_pass_pairs": len(pass_frame),
    }


def _optimizer_summary(
    nested: pd.DataFrame,
    graph: pd.DataFrame,
    pass_frame: pd.DataFrame,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    settings = load_json(PROJECT_ROOT / manifest["protocol_path"])["global"]
    rows = []
    for optimizer in sorted(nested.optimizer.unique()) if len(nested) else []:
        for objective in ("O0", "O3"):
            diagnostic = nested[
                (nested.optimizer == optimizer) & (nested.objective == objective)
            ]
            graph_g = graph[
                (graph.optimizer == optimizer)
                & (graph.objective == objective)
                & (graph.depth == 3)
            ]
            absolute = (
                bootstrap_mean_ci(
                    graph_g.G_feas.to_numpy(dtype=float),
                    resamples=int(settings["bootstrap_resamples"]),
                    seed=int(settings["bootstrap_seed"])
                    + sum(ord(ch) for ch in optimizer + objective),
                )
                if len(graph_g)
                else {name: math.nan for name in ("mean", "median", "ci_lower", "ci_upper", "bootstrap_se")}
            )
            paired = pass_frame[pass_frame.optimizer == optimizer]
            graph_delta = (
                paired.groupby("graph_id").delta_G_feas_O3_minus_O0.mean().to_numpy(dtype=float)
                if len(paired)
                else np.asarray([])
            )
            effect = (
                bootstrap_mean_ci(
                    graph_delta,
                    resamples=int(settings["bootstrap_resamples"]),
                    seed=int(settings["bootstrap_seed"])
                    + 1000
                    + sum(ord(ch) for ch in optimizer),
                )
                if len(graph_delta)
                else {name: math.nan for name in ("mean", "median", "ci_lower", "ci_upper", "bootstrap_se")}
            )
            rows.append(
                {
                    "optimizer": optimizer,
                    "objective": objective,
                    "nested_failure_count": int(diagnostic.nested_failure.sum()),
                    "nested_comparison_count": len(diagnostic),
                    "nested_failure_rate": float(diagnostic.nested_failure.mean()) if len(diagnostic) else math.nan,
                    "median_signed_nested_regret": float(diagnostic.signed_nested_regret.median()) if len(diagnostic) else math.nan,
                    "median_graph_G_feas": absolute["median"],
                    "mean_graph_G_feas": absolute["mean"],
                    "graph_G_feas_ci_lower": absolute["ci_lower"],
                    "graph_G_feas_ci_upper": absolute["ci_upper"],
                    "certified_pass_pair_count": len(paired),
                    "certified_pass_graph_count": int(paired.graph_id.nunique()) if len(paired) else 0,
                    "pass_subset_O3_minus_O0_G_mean": effect["mean"],
                    "pass_subset_O3_minus_O0_G_ci_lower": effect["ci_lower"],
                    "pass_subset_O3_minus_O0_G_ci_upper": effect["ci_upper"],
                }
            )
    return pd.DataFrame(rows)


def _plot_a1(summary: pd.DataFrame) -> None:
    if not len(summary):
        return
    figure_root = A1_ROOT / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.8), constrained_layout=True)
    pivot = summary.pivot(index="optimizer", columns="objective", values="nested_failure_rate")
    pivot.plot(kind="bar", ax=axes[0], rot=0)
    axes[0].set_ylabel("p2→p3 nested failure rate")
    axes[0].legend(frameon=False)
    effect = summary.groupby("optimizer", as_index=False).first()
    axes[1].errorbar(
        range(len(effect)),
        effect.pass_subset_O3_minus_O0_G_mean,
        yerr=[
            effect.pass_subset_O3_minus_O0_G_mean - effect.pass_subset_O3_minus_O0_G_ci_lower,
            effect.pass_subset_O3_minus_O0_G_ci_upper - effect.pass_subset_O3_minus_O0_G_mean,
        ],
        marker="o",
        linestyle="none",
        capsize=4,
    )
    axes[1].set_xticks(range(len(effect)), effect.optimizer)
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set_ylabel("PASS-only graph mean O3−O0 $G_{feas}$")
    for axis in axes:
        axis.grid(alpha=0.2)
    for label, axis in zip("ab", axes):
        axis.text(-0.10, 1.06, label, transform=axis.transAxes, fontweight="bold")
    for suffix in ("png", "pdf"):
        fig.savefig(figure_root / f"optimizer_objective_effect.{suffix}", dpi=300)
    plt.close(fig)


def _a1_report(
    manifest: dict[str, Any],
    frame: pd.DataFrame,
    nested: pd.DataFrame,
    passed: pd.DataFrame,
    summary: pd.DataFrame,
    failed: int,
) -> str:
    planned = int(manifest["planned_optimizer_runs"])
    complete = int(len(frame))
    full = complete == planned and failed == 0
    lines = [
        "# A1 — Optimizer robustness",
        "",
        f"**Execution status: {'COMPLETE' if full else 'PARTIAL'}.** Completed {complete}/{planned} runs; failed records: {failed}.",
        "",
        "## Protocol",
        "",
        "The frozen matrix uses discovery tasks, the three original seeds, p=2/3, O0/O3(alpha=0.10), COBYLA/Nelder–Mead/SLSQP, and a strict 120-objective-call budget. Every SLSQP finite-difference call is counted by the wrapper. SciPy-reported nfev is retained when SciPy returns normally; a null value after a hard wrapper stop is disclosed rather than imputed.",
        "",
        "Manifest: `results/reviewer_robustness/manifests/manifest_optimizer_robustness.json`.",
        "",
        "## Numerical findings",
        "",
    ]
    for row in summary.itertuples(index=False) if len(summary) else []:
        lines.append(
            f"- {row.optimizer}/{row.objective}: nested failures {row.nested_failure_count}/{row.nested_comparison_count} ({row.nested_failure_rate:.3f}); median signed regret {row.median_signed_nested_regret:.6g}; median graph G_feas {row.median_graph_G_feas:.4f}."
        )
    if len(passed):
        lines.extend(
            [
                "",
                "## Certified-pass mechanism test",
                "",
            ]
        )
        for optimizer, group in passed.groupby("optimizer"):
            lines.append(
                f"- {optimizer}: {len(group)} O0/O3 pairs pass both nested diagnostics; O0 has lower energy but lower feasibility than O3 in {int(group.O0_lower_energy_but_lower_feasibility_than_O3.sum())}/{len(group)}, and an O0 p3 energy improvement with feasibility loss versus embedded p2 occurs in {int(group.O0_pass_improves_energy_but_reduces_feasibility_vs_embedded_p2.sum())}/{len(group)}."
            )
    lines.extend(
        [
            "",
            "## Interpretation and limitation",
            "",
            "The historical 29/168 value remains frozen and is not expected to be reproduced mechanically. This post-hoc matrix asks whether nested failure occurs outside COBYLA and whether energy–feasibility misalignment survives after certified failures are removed. Task rows are descriptive; effect intervals aggregate paired effects within graph.",
            "",
            "No global optimizer, hardware noise, alternative mixer, or advantage comparison is included.",
            "",
            "## Claim impact",
            "",
            ("The complete optimizer and PASS-only results above can support a qualified mechanism statement." if full else "Coverage is incomplete; no universal optimizer-robustness statement is licensed."),
            "For a complete matrix, the paper may state that nested failure is not COBYLA-specific across the three tested local optimizers and that objective misalignment persists on dual-PASS runs. It should not call any optimizer universally unsuitable.",
            "",
        ]
    )
    return "\n".join(lines)
