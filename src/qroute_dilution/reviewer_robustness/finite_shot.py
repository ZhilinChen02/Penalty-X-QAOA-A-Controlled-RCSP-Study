"""A3 audit, alpha-by-shot estimators, and end-to-end shot-trained QAOA."""

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
from qroute_dilution.phase1_2_objectives import weighted_exact_cvar
from qroute_dilution.qaoa import simulate_qaoa

from .common import (
    REVIEW_ROOT,
    build_objective_context,
    derive_seed,
    embed_parameters,
    evaluate_parameters,
    evaluate_probabilities,
    load_json,
    parse_parameters,
    sha256_file,
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


A3_ROOT = REVIEW_ROOT / "A3_finite_shot"
HELDOUT_P2 = (
    PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "p2_initialization_runs.csv"
)
HELDOUT_P3 = (
    PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "p3_objective_results.csv"
)
EXISTING_ENDPOINT_ROOT = PROJECT_ROOT / "results" / "posthoc_finite_shot_endpoint_v1"


def empirical_cvar(sample_energies: np.ndarray, alpha: float) -> float:
    """Empirical lower-tail CVaR with a fractional boundary observation."""
    values = np.asarray(sample_energies, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("sample energies must be a finite nonempty vector")
    if not 0.0 < float(alpha) <= 1.0:
        raise ValueError("alpha must be in (0,1]")
    tail_size = float(alpha) * len(values)
    full = int(math.floor(tail_size))
    fractional = tail_size - full
    needed = full + int(fractional > 1e-14)
    if needed >= len(values):
        ordered = np.sort(values)
    else:
        ordered = np.partition(values, needed - 1)[:needed]
        ordered.sort()
    numerator = float(ordered[:full].sum()) if full else 0.0
    if fractional > 1e-14:
        numerator += fractional * float(ordered[full])
    return numerator / tail_size


def sample_states(probabilities: np.ndarray, shots: int, seed: int) -> np.ndarray:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if probabilities.ndim != 1 or int(shots) <= 0:
        raise ValueError("invalid sampling inputs")
    probabilities = probabilities / probabilities.sum()
    cdf = np.cumsum(probabilities, dtype=np.float64)
    cdf[-1] = 1.0
    rng = np.random.default_rng(int(seed))
    return np.searchsorted(cdf, rng.random(int(shots)), side="right")


def empirical_event_probability(states: np.ndarray, event_mask: np.ndarray) -> float:
    """Estimate an event probability from sampled basis-state indices."""
    sampled = np.asarray(states)
    mask = np.asarray(event_mask, dtype=bool)
    if sampled.ndim != 1 or not len(sampled) or mask.ndim != 1:
        raise ValueError("states must be nonempty and event_mask must be one-dimensional")
    if np.any(sampled < 0) or np.any(sampled >= len(mask)):
        raise ValueError("sampled state index is outside event_mask")
    return float(mask[sampled].mean())


def total_shot_count(nfev: int, shots_per_evaluation: int) -> int:
    """Return the exact sampling-resource count for a training run."""
    if int(nfev) < 0 or int(shots_per_evaluation) <= 0:
        raise ValueError("nfev must be nonnegative and shots_per_evaluation positive")
    return int(nfev) * int(shots_per_evaluation)


def audit_existing_endpoint_study() -> dict[str, Any]:
    manifest_path = EXISTING_ENDPOINT_ROOT / "manifest.json"
    manifest = load_json(manifest_path)
    mismatches = []
    for relative, expected in manifest["input_sha256"].items():
        path = PROJECT_ROOT / relative
        if not path.exists() or sha256_file(path) != expected:
            mismatches.append(relative)
    for relative, expected in manifest["output_sha256"].items():
        path = EXISTING_ENDPOINT_ROOT / relative
        if not path.exists() or sha256_file(path) != expected:
            mismatches.append(str(path.relative_to(PROJECT_ROOT)))
    metrics = pd.read_csv(EXISTING_ENDPOINT_ROOT / "metrics.csv")
    exact = pd.read_csv(EXISTING_ENDPOINT_ROOT / "exact_reference.csv")
    audit = {
        "manifest_path": str(manifest_path.relative_to(PROJECT_ROOT)),
        "manifest_sha256": sha256_file(manifest_path),
        "integrity_pass": not mismatches,
        "hash_mismatches": mismatches,
        "task_count": int(metrics.task_id.nunique()),
        "base_graph_count": int(metrics.base_graph_id.nunique()),
        "objectives": sorted(metrics.objective_id.unique().tolist()),
        "shots": sorted(int(value) for value in metrics.shots.unique()),
        "replicates": int(metrics.replicate.nunique()),
        "replicate_metric_rows": len(metrics),
        "exact_endpoint_rows": len(exact),
        "metrics": ["P_feas", "P_opt", "mean_energy", "CVaR_alpha_0.10"],
        "fixed_theta_only": True,
        "optimizer_invoked": False,
        "reused_without_rerun": True,
    }
    if not audit["integrity_pass"]:
        raise RuntimeError(f"existing endpoint study hash mismatch: {mismatches}")
    report = f"""# Existing finite-shot endpoint study audit

## Integrity and coverage

The pre-existing post-hoc study at `results/posthoc_finite_shot_endpoint_v1/` passes its recorded input/output SHA-256 checks. It covers all **{audit['task_count']} held-out tasks / {audit['base_graph_count']} graphs**, both O0 and O3 frozen terminal states, {audit['shots']} shots, and {audit['replicates']} deterministic sampling replicates. It records P_feas, P_opt, mean energy, and empirical CVaR(alpha=0.10), with exact endpoint reconstruction errors checked against authoritative rows.

This evidence is reused and was **not rerun**. The new reviewer work only adds the missing alpha×shot paired estimator grid and end-to-end finite-shot optimization.

## Scientific boundary

The existing study holds theta fixed after exact-statevector training. It tests estimator error and endpoint ordering only. It cannot establish finite-shot training robustness, device or hardware robustness, noise robustness, compilation robustness, or hardware readiness.
"""
    A3_ROOT.mkdir(parents=True, exist_ok=True)
    path = A3_ROOT / "ENDPOINT_STUDY_AUDIT.md"
    if not path.exists():
        atomic_write_text(path, report)
    return audit


def _endpoint_lookup(task_ids: set[str]) -> dict[tuple[str, str], dict[str, Any]]:
    frame = pd.read_csv(HELDOUT_P3)
    frame = frame[
        frame.task_id.isin(task_ids)
        & frame.objective_id.isin(["O0", "O3"])
        & (frame.execution_status == "SUCCESS")
    ]
    if len(frame) != 2 * len(task_ids):
        raise RuntimeError("frozen held-out O0/O3 endpoint rows are incomplete")
    return {
        (str(row["task_id"]), str(row["objective_id"])): row
        for row in frame.to_dict(orient="records")
    }


def _estimator_record(
    task_record: dict[str, Any],
    endpoint: dict[str, Any],
    *,
    objective_id: str,
    shots: int,
    replicate: int,
    expected_seed: int,
    manifest: dict[str, Any],
    output_root: Path,
    prepared_task: Any | None = None,
    prepared_context: dict[str, Any] | None = None,
    prepared_probabilities: np.ndarray | None = None,
    prepared_exact_by_alpha: dict[str, dict[str, Any]] | None = None,
    prepared_maximum_difference: float | None = None,
) -> str:
    run_id = stable_run_id(
        "a3est", task_record["task_id"], objective_id, shots, replicate, execution_code_fingerprint(manifest)
    )
    path = output_root / "estimator_runs" / f"{run_id}.json"
    if read_valid_terminal_record(path, run_id=run_id) is not None:
        return "SKIPPED_EXISTING"
    started_at = utc_timestamp()
    started = time.perf_counter()
    try:
        task = prepared_task or task_from_manifest_row(task_record)
        context = prepared_context or build_objective_context(task)
        parameters = parse_parameters(endpoint["terminal_parameters"])
        if prepared_probabilities is None:
            state = simulate_qaoa(parameters, context["energy"], 3)
            probabilities = np.abs(state) ** 2
        else:
            probabilities = prepared_probabilities
        exact_by_alpha = prepared_exact_by_alpha or {
            str(alpha): evaluate_probabilities(task, context, probabilities, alpha=float(alpha))
            for alpha in manifest["estimator_alphas"]
        }
        if prepared_maximum_difference is None:
            stored_checks = {
                "p_feas": float(endpoint["p_feas"]),
                "p_opt": float(endpoint["p_opt"]),
                "mean_energy": float(endpoint["mean_energy"]),
            }
            maximum_difference = max(
                abs(float(exact_by_alpha[str(manifest["training"]["alpha"])][key]) - value)
                for key, value in stored_checks.items()
            )
        else:
            maximum_difference = float(prepared_maximum_difference)
        if maximum_difference > 1e-10:
            raise RuntimeError("endpoint exact reconstruction differs from frozen row")
        states = sample_states(probabilities, int(shots), int(expected_seed))
        energies = context["energy"][states]
        sampled = {
            "p_feas": empirical_event_probability(states, context["feasible_mask"]),
            "p_opt": empirical_event_probability(states, context["optimal_mask"]),
            "mean_energy": float(energies.mean()),
            "cvar_by_alpha": {
                str(alpha): empirical_cvar(energies, float(alpha))
                for alpha in manifest["estimator_alphas"]
            },
        }
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        record = {
            "schema_version": "qroute-dilution.A3.estimator.v1",
            "experiment": "A3_ALPHA_SHOT_ESTIMATOR",
            "run_id": run_id,
            "status": "COMPLETE",
            "task": task_record,
            "endpoint_objective": objective_id,
            "source_run_id": endpoint["run_id"],
            "terminal_parameters": parameters.tolist(),
            "shots": int(shots),
            "replicate": int(replicate),
            "sampling_seed": int(expected_seed),
            "alphas": manifest["estimator_alphas"],
            "exact_by_alpha": exact_by_alpha,
            "sampled": sampled,
            "maximum_exact_difference_vs_frozen": maximum_difference,
            "runtime_s": runtime,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A3_ALPHA_SHOT_ESTIMATOR",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective=objective_id,
            optimizer=None,
            depth=3,
            alpha=None,
            nfev_budget=None,
            actual_nfev=None,
            shots=shots,
            seed=expected_seed,
            status="COMPLETE",
            started_at=started_at,
            finished_at=finished_at,
            runtime_s=runtime,
            error_message="",
            git_commit=manifest["code_git_commit"],
            dirty_state_fingerprint=execution_code_fingerprint(manifest),
        )
        write_new_record(path, record)
        return "COMPLETE"
    except Exception as exc:
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        message = f"{type(exc).__name__}: {exc}"
        record = {
            "schema_version": "qroute-dilution.A3.estimator.v1",
            "experiment": "A3_ALPHA_SHOT_ESTIMATOR",
            "run_id": run_id,
            "status": "FAILED",
            "task": task_record,
            "endpoint_objective": objective_id,
            "shots": shots,
            "replicate": replicate,
            "sampling_seed": expected_seed,
            "error_message": message,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A3_ALPHA_SHOT_ESTIMATOR",
            run_id=run_id,
            task_id=task_record["task_id"],
            graph_id=task_record["graph_id"],
            objective=objective_id,
            optimizer=None,
            depth=3,
            alpha=None,
            nfev_budget=None,
            actual_nfev=None,
            shots=shots,
            seed=expected_seed,
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


def _estimator_task_batch(
    task_record: dict[str, Any],
    endpoints: dict[str, dict[str, Any]],
    seed_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    output_root: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    task = task_from_manifest_row(task_record)
    context = build_objective_context(task)
    prepared: dict[str, tuple[np.ndarray, dict[str, dict[str, Any]], float]] = {}
    for objective, endpoint in endpoints.items():
        parameters = parse_parameters(endpoint["terminal_parameters"])
        probabilities = np.abs(simulate_qaoa(parameters, context["energy"], 3)) ** 2
        exact = {
            str(alpha): evaluate_probabilities(task, context, probabilities, alpha=float(alpha))
            for alpha in manifest["estimator_alphas"]
        }
        reference = exact[str(manifest["training"]["alpha"])]
        difference = max(
            abs(float(reference[key]) - float(endpoint[source]))
            for key, source in (
                ("p_feas", "p_feas"),
                ("p_opt", "p_opt"),
                ("mean_energy", "mean_energy"),
            )
        )
        prepared[objective] = (probabilities, exact, difference)
    for seed_row in seed_rows:
        objective = str(seed_row["objective"])
        probabilities, exact, difference = prepared[objective]
        status = _estimator_record(
            task_record,
            endpoints[objective],
            objective_id=objective,
            shots=int(seed_row["shots"]),
            replicate=int(seed_row["replicate"]),
            expected_seed=int(seed_row["seed"]),
            manifest=manifest,
            output_root=Path(output_root),
            prepared_task=task,
            prepared_context=context,
            prepared_probabilities=probabilities,
            prepared_exact_by_alpha=exact,
            prepared_maximum_difference=difference,
        )
        counts[status] = counts.get(status, 0) + 1
    return counts


def endpoint_objectives_from_manifest(manifest: dict[str, Any]) -> tuple[str, ...]:
    """Recover the frozen endpoint arms from the explicit sampling-seed table."""
    objectives = tuple(
        sorted({str(row["objective"]) for row in manifest.get("sampling_seeds", [])})
    )
    if not objectives:
        raise ValueError("finite-shot manifest has no endpoint sampling objectives")
    training_objectives = tuple(
        sorted(str(value) for value in manifest.get("training", {}).get("objectives", []))
    )
    if training_objectives and objectives != training_objectives:
        raise ValueError(
            "endpoint sampling objectives disagree with the frozen training objectives"
        )
    return objectives


def run_alpha_shot_estimators(
    *, smoke: bool = False, max_workers: int | None = None
) -> dict[str, int]:
    manifest = load_json(MANIFEST_PATHS["finite_shot"])
    output_root = REVIEW_ROOT / "smoke" / "A3_finite_shot" if smoke else A3_ROOT
    tasks = list(manifest["estimator_tasks"])
    if smoke:
        tasks = sorted(tasks, key=lambda row: (row["m"], row["task_id"]))[:1]
    else:
        # Largest statevectors first keeps the fixed worker pool occupied near the tail.
        tasks = sorted(tasks, key=lambda row: (-int(row["m"]), row["task_id"]))
    task_ids = {row["task_id"] for row in tasks}
    endpoints_all = _endpoint_lookup(task_ids)
    endpoint_objectives = endpoint_objectives_from_manifest(manifest)
    seed_rows = [
        row for row in manifest["sampling_seeds"] if row["task_id"] in task_ids
    ]
    if smoke:
        seed_rows = [row for row in seed_rows if int(row["replicate"]) < 2]
    counts: dict[str, int] = {}
    with ProcessPoolExecutor(max_workers=int(max_workers or (1 if smoke else 4))) as executor:
        futures = []
        for task in tasks:
            endpoints = {
                objective: endpoints_all[(task["task_id"], objective)]
                for objective in endpoint_objectives
            }
            task_seeds = [row for row in seed_rows if row["task_id"] == task["task_id"]]
            futures.append(
                executor.submit(
                    _estimator_task_batch,
                    task,
                    endpoints,
                    task_seeds,
                    manifest,
                    str(output_root),
                )
            )
        for future in as_completed(futures):
            for key, value in future.result().items():
                counts[key] = counts.get(key, 0) + value
    rebuild_registry()
    return counts


def aggregate_alpha_shot_estimators(*, root: Path = A3_ROOT) -> dict[str, Any]:
    records = []
    for path in sorted((root / "estimator_runs").glob("*.json")):
        value = load_json(path)
        if value.get("status") == "COMPLETE":
            records.append(value)
    rows = []
    for record in records:
        task = record["task"]
        sampled = record["sampled"]
        for alpha_text, estimate in sampled["cvar_by_alpha"].items():
            exact = record["exact_by_alpha"][alpha_text]
            error = float(estimate) - float(exact["cvar"])
            rows.append(
                {
                    "run_id": record["run_id"],
                    "task_id": task["task_id"],
                    "graph_id": task["graph_id"],
                    "size_stratum": task["size_stratum"],
                    "m": task["m"],
                    "dilution_score": task["dilution_score"],
                    "endpoint_objective": record["endpoint_objective"],
                    "shots": record["shots"],
                    "replicate": record["replicate"],
                    "sampling_seed": record["sampling_seed"],
                    "alpha": float(alpha_text),
                    "cvar_estimate": float(estimate),
                    "cvar_exact": float(exact["cvar"]),
                    "cvar_error": error,
                    "relative_error": (
                        error / abs(float(exact["cvar"]))
                        if abs(float(exact["cvar"])) > 1e-15
                        else math.nan
                    ),
                    "p_feas_estimate": sampled["p_feas"],
                    "p_feas_exact": exact["p_feas"],
                    "p_opt_estimate": sampled["p_opt"],
                    "p_opt_exact": exact["p_opt"],
                }
            )
    frame = pd.DataFrame(rows)
    atomic_write_csv(root / "alpha_shot_estimator_runs.csv", frame)
    summary_rows = []
    if len(frame):
        for (objective, alpha, shots), group in frame.groupby(
            ["endpoint_objective", "alpha", "shots"], sort=True
        ):
            errors = group.cvar_error.to_numpy(dtype=float)
            relative = group.relative_error.to_numpy(dtype=float)
            summary_rows.append(
                {
                    "endpoint_objective": objective,
                    "alpha": alpha,
                    "shots": int(shots),
                    "n_tasks": int(group.task_id.nunique()),
                    "n_estimates": len(group),
                    "bias": float(errors.mean()),
                    "mae": float(np.abs(errors).mean()),
                    "rmse": float(np.sqrt(np.mean(errors**2))),
                    "standard_deviation": float(errors.std(ddof=1)),
                    "empirical_error_p025": float(np.quantile(errors, 0.025)),
                    "empirical_error_p975": float(np.quantile(errors, 0.975)),
                    "relative_bias": float(np.nanmean(relative)),
                    "relative_mae": float(np.nanmean(np.abs(relative))),
                    "relative_rmse": float(np.sqrt(np.nanmean(relative**2))),
                }
            )
    summary = pd.DataFrame(summary_rows)
    ordering_rows = []
    if len(frame):
        pivot = frame.pivot(
            index=["task_id", "graph_id", "alpha", "shots", "replicate"],
            columns="endpoint_objective",
            values=["cvar_estimate", "cvar_exact"],
        )
        pivot.columns = [f"{metric}_{objective}" for metric, objective in pivot.columns]
        pivot = pivot.reset_index()
        pivot["sample_delta"] = pivot.cvar_estimate_O3 - pivot.cvar_estimate_O0
        pivot["exact_delta"] = pivot.cvar_exact_O3 - pivot.cvar_exact_O0
        pivot["ordering_preserved"] = (
            np.sign(pivot.sample_delta) == np.sign(pivot.exact_delta)
        )
        for (alpha, shots), group in pivot.groupby(["alpha", "shots"], sort=True):
            comparable = group[group.exact_delta != 0.0]
            ordering_rows.append(
                {
                    "alpha": alpha,
                    "shots": int(shots),
                    "n_comparisons": len(comparable),
                    "n_tasks": int(comparable.task_id.nunique()),
                    "ordering_preservation_probability": float(
                        comparable.ordering_preserved.mean()
                    ),
                }
            )
    ordering = pd.DataFrame(ordering_rows)
    if len(ordering):
        ordering = ordering.rename(columns={"n_tasks": "ordering_n_tasks"})
    merged = summary.merge(ordering, on=["alpha", "shots"], how="left")
    atomic_write_csv(root / "alpha_shot_estimator.csv", merged)
    atomic_write_csv(root / "figure_data_alpha_shot_heatmap.csv", merged)
    _plot_alpha_shot(root, summary, ordering)
    report = _alpha_shot_report(records, summary, ordering)
    atomic_write_text(root / "ALPHA_SHOT_ANALYSIS.md", report)
    return {
        "complete_sampling_records": len(records),
        "long_metric_rows": len(frame),
        "summary_rows": len(merged),
        "total_sampled_bitstrings": int(
            sum(int(record["shots"]) for record in records)
        ),
    }


def _plot_alpha_shot(root: Path, summary: pd.DataFrame, ordering: pd.DataFrame) -> None:
    if not len(summary):
        return
    figure_root = root / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    combined = summary.groupby(["alpha", "shots"], as_index=False).rmse.mean()
    table = combined.pivot(index="alpha", columns="shots", values="rmse")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.8), constrained_layout=True)
    image = axes[0].imshow(table.to_numpy(), aspect="auto", origin="lower", cmap="viridis")
    axes[0].set_xticks(range(len(table.columns)), [f"{value:g}" for value in table.columns])
    axes[0].set_yticks(range(len(table.index)), [f"{value:g}" for value in table.index])
    axes[0].set_xlabel("Shots")
    axes[0].set_ylabel("CVaR alpha")
    axes[0].set_title("CVaR estimator RMSE")
    fig.colorbar(image, ax=axes[0], shrink=0.85)
    for alpha, group in ordering.groupby("alpha"):
        axes[1].plot(group.shots, group.ordering_preservation_probability, marker="o", label=f"alpha={alpha:g}")
    axes[1].set_xscale("log")
    axes[1].set_ylim(0.0, 1.02)
    axes[1].set_xlabel("Shots")
    axes[1].set_ylabel("Exact ordering preserved")
    axes[1].legend(frameon=False, fontsize=7, ncol=2)
    axes[1].grid(alpha=0.2)
    for label, axis in zip("ab", axes):
        axis.text(-0.10, 1.06, label, transform=axis.transAxes, fontweight="bold")
    for suffix in ("png", "pdf"):
        fig.savefig(figure_root / f"Figure_R4_alpha_shots.{suffix}", dpi=300)
    plt.close(fig)


def _alpha_shot_report(
    records: list[dict[str, Any]], summary: pd.DataFrame, ordering: pd.DataFrame
) -> str:
    lines = [
        "# Alpha × shot-count estimator analysis",
        "",
        f"Complete independent sampling records: {len(records)}. No quantum optimization was rerun for this grid.",
        "",
        "The grid uses frozen O0/O3 held-out endpoint distributions, alpha in {0.02, 0.05, 0.10, 0.25, 0.50}, and 1e3/1e4/1e5 shots. Each sample is reused across alpha values within a record, providing a paired view of tail aggressiveness versus sampling cost.",
        "",
        "## Numerical summary",
        "",
    ]
    if len(summary):
        combined = summary.groupby(["alpha", "shots"], as_index=False).rmse.mean()
        for row in combined.itertuples(index=False):
            order = ordering[(ordering.alpha == row.alpha) & (ordering.shots == row.shots)]
            agreement = order.iloc[0].ordering_preservation_probability if len(order) else math.nan
            lines.append(
                f"- alpha={row.alpha:g}, shots={int(row.shots):g}: mean O0/O3 CVaR RMSE={row.rmse:.6g}; exact ordering preservation={agreement:.3f}."
            )
    else:
        lines.append("No complete estimator records are available yet.")
    lines.extend(
        [
            "",
            "This is fixed-parameter estimator evidence only. It does not establish finite-shot training, hardware, or noise robustness.",
            "",
        ]
    )
    return "\n".join(lines)


def _selected_p2_lookup(task_ids: set[str]) -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(HELDOUT_P2)
    frame = frame[frame.task_id.isin(task_ids) & frame.selected_for_p3.astype(bool)]
    if len(frame) != len(task_ids):
        raise RuntimeError("held-out selected p2 initialization is incomplete")
    return {str(row["task_id"]): row for row in frame.to_dict(orient="records")}


def _shot_training_record(
    task_record: dict[str, Any],
    p2_row: dict[str, Any],
    *,
    objective_id: str,
    shots: int,
    training_seed: int,
    manifest: dict[str, Any],
    output_root: Path,
    prepared_task: Any | None = None,
    prepared_context: dict[str, Any] | None = None,
) -> str:
    training = manifest["training"]
    run_id = stable_run_id(
        "a3train",
        task_record["task_id"],
        objective_id,
        shots,
        training_seed,
        training["evaluation_budget"],
        execution_code_fingerprint(manifest),
    )
    path = output_root / "training_runs" / f"{run_id}.json"
    if read_valid_terminal_record(path, run_id=run_id) is not None:
        return "SKIPPED_EXISTING"
    started_at = utc_timestamp()
    started = time.perf_counter()
    evaluation_seeds: list[int] = []
    actual_nfev: int | None = None
    try:
        task = prepared_task or task_from_manifest_row(task_record)
        context = prepared_context or build_objective_context(task)
        depth = int(training["depth"])
        alpha = float(training["alpha"])
        initial = embed_parameters(
            parse_parameters(p2_row["terminal_parameters"]), 2, depth
        )

        def sampled_objective(parameters: np.ndarray) -> float:
            evaluation_index = len(evaluation_seeds) + 1
            sampling_seed = derive_seed(
                "reviewer-A3-training-evaluation-v1",
                task.task_id,
                objective_id,
                shots,
                training_seed,
                evaluation_index,
            )
            evaluation_seeds.append(sampling_seed)
            state = simulate_qaoa(parameters, context["energy"], depth)
            probabilities = np.abs(state) ** 2
            states = sample_states(probabilities, int(shots), sampling_seed)
            energies = context["energy"][states]
            if objective_id == "O0":
                return float(energies.mean())
            return empirical_cvar(energies, alpha)

        protocol = load_json(PROJECT_ROOT / manifest["protocol_path"])
        result = optimize_with_strict_nfev(
            sampled_objective,
            initial,
            method=training["optimizer"],
            max_nfev=int(training["evaluation_budget"]),
            timeout_s=float(protocol["global"]["timeout_s"]),
            settings={
                "cobyla_rhobeg": protocol["finite_shot"]["cobyla_rhobeg"],
                "cobyla_catol": protocol["finite_shot"]["cobyla_catol"],
            },
        )
        actual_nfev = result.nfev
        if len(evaluation_seeds) != result.nfev:
            raise RuntimeError("sampling-seed lineage does not equal objective-call count")
        exact_terminal = evaluate_parameters(
            task, context, result.terminal_parameters, depth, alpha=alpha
        )
        exact_best_noisy = evaluate_parameters(
            task, context, result.best_evaluated_parameters, depth, alpha=alpha
        )
        record_status = (
            "TIMEOUT" if result.termination_reason == "WALLTIME_LIMIT" else "COMPLETE"
        )
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        record = {
            "schema_version": "qroute-dilution.A3.shot-training.v1",
            "experiment": "A3_FINITE_SHOT_TRAINING",
            "run_id": run_id,
            "status": record_status,
            "task": task_record,
            "objective": objective_id,
            "alpha": alpha,
            "shots_per_evaluation": int(shots),
            "training_seed": int(training_seed),
            "sampling_seed_namespace": "reviewer-A3-training-evaluation-v1",
            "evaluation_sampling_seeds": evaluation_seeds,
            "optimizer": training["optimizer"],
            "depth": depth,
            "nfev_budget": int(training["evaluation_budget"]),
            "actual_objective_calls": result.nfev,
            "scipy_reported_nfev": result.scipy_reported_nfev,
            "nit": result.nit,
            "termination_reason": result.termination_reason,
            "optimizer_status": result.status,
            "optimizer_success": result.scipy_success,
            "optimizer_message": result.message,
            "total_sampled_bitstrings": total_shot_count(result.nfev, int(shots)),
            "initial_parameters": initial.tolist(),
            "terminal_parameters": result.terminal_parameters.tolist(),
            "best_sampled_parameters": result.best_evaluated_parameters.tolist(),
            "sampled_objective_initial": result.objective_initial,
            "sampled_objective_terminal_observed": result.terminal_objective_observed,
            "sampled_objective_best_observed": result.best_evaluated_objective,
            "exact_terminal_evaluation": exact_terminal,
            "exact_best_sampled_evaluation": exact_best_noisy,
            "final_evaluation_semantics": "exact statevector evaluation of optimizer terminal theta",
            "runtime_s": result.runtime_s,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A3_FINITE_SHOT_TRAINING",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective=objective_id,
            optimizer=training["optimizer"],
            depth=depth,
            alpha=alpha,
            nfev_budget=int(training["evaluation_budget"]),
            actual_nfev=result.nfev,
            shots=shots,
            seed=training_seed,
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
            "schema_version": "qroute-dilution.A3.shot-training.v1",
            "experiment": "A3_FINITE_SHOT_TRAINING",
            "run_id": run_id,
            "status": "FAILED",
            "task": task_record,
            "objective": objective_id,
            "shots_per_evaluation": shots,
            "training_seed": training_seed,
            "actual_objective_calls": actual_nfev,
            "evaluation_sampling_seeds": evaluation_seeds,
            "error_message": message,
            "runtime_s": runtime,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="A3_FINITE_SHOT_TRAINING",
            run_id=run_id,
            task_id=task_record["task_id"],
            graph_id=task_record["graph_id"],
            objective=objective_id,
            optimizer=manifest["training"]["optimizer"],
            depth=manifest["training"]["depth"],
            alpha=manifest["training"]["alpha"],
            nfev_budget=manifest["training"]["evaluation_budget"],
            actual_nfev=actual_nfev,
            shots=shots,
            seed=training_seed,
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


def _training_task_batch(
    task_record: dict[str, Any],
    p2_row: dict[str, Any],
    manifest: dict[str, Any],
    output_root: str,
) -> dict[str, int]:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    counts: dict[str, int] = {}
    training = manifest["training"]
    task = task_from_manifest_row(task_record)
    context = build_objective_context(task)
    for shots in training["shots"]:
        for objective in training["objectives"]:
            for seed in training["seeds"]:
                status = _shot_training_record(
                    task_record,
                    p2_row,
                    objective_id=objective,
                    shots=int(shots),
                    training_seed=int(seed),
                    manifest=manifest,
                    output_root=Path(output_root),
                    prepared_task=task,
                    prepared_context=context,
                )
                counts[status] = counts.get(status, 0) + 1
    return counts


def run_finite_shot_training(
    *, smoke: bool = False, max_workers: int | None = None
) -> dict[str, int]:
    manifest = load_json(MANIFEST_PATHS["finite_shot"])
    output_root = REVIEW_ROOT / "smoke" / "A3_finite_shot" if smoke else A3_ROOT
    tasks = list(manifest["training_tasks"])
    if smoke:
        tasks = sorted(tasks, key=lambda row: (row["m"], row["task_id"]))[:1]
        reduced = json.loads(json.dumps(manifest))
        reduced["training"]["seeds"] = reduced["training"]["seeds"][:1]
        manifest = reduced
    p2 = _selected_p2_lookup({row["task_id"] for row in tasks})
    counts: dict[str, int] = {}
    with ProcessPoolExecutor(max_workers=int(max_workers or (1 if smoke else 4))) as executor:
        futures = [
            executor.submit(
                _training_task_batch,
                task,
                p2[task["task_id"]],
                manifest,
                str(output_root),
            )
            for task in tasks
        ]
        for future in as_completed(futures):
            for key, value in future.result().items():
                counts[key] = counts.get(key, 0) + value
    rebuild_registry()
    return counts


def aggregate_finite_shot_training(*, root: Path = A3_ROOT) -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATHS["finite_shot"])
    records = []
    for path in sorted((root / "training_runs").glob("*.json")):
        value = load_json(path)
        if value.get("status") == "COMPLETE":
            records.append(value)
    rows = []
    for record in records:
        task = record["task"]
        exact = record["exact_terminal_evaluation"]
        rows.append(
            {
                "run_id": record["run_id"],
                "training_regime": f"SHOT_{record['shots_per_evaluation']}",
                "task_id": task["task_id"],
                "graph_id": task["graph_id"],
                "size_stratum": task["size_stratum"],
                "m": task["m"],
                "dilution_score": task["dilution_score"],
                "objective": record["objective"],
                "alpha": record["alpha"],
                "shots_per_evaluation": record["shots_per_evaluation"],
                "seed": record["training_seed"],
                "nfev_budget": record["nfev_budget"],
                "actual_nfev": record["actual_objective_calls"],
                "scipy_reported_nfev": record["scipy_reported_nfev"],
                "nit": record["nit"],
                "termination_reason": record["termination_reason"],
                "optimizer_status": record["optimizer_status"],
                "optimizer_success": record["optimizer_success"],
                "wall_time_s": record["runtime_s"],
                "total_sampled_bitstrings": record["total_sampled_bitstrings"],
                "sampled_objective_terminal": record[
                    "sampled_objective_terminal_observed"
                ],
                "mean_energy": exact["mean_energy"],
                "P_feas": exact["p_feas"],
                "P_opt": exact["p_opt"],
                "P_opt_given_feas": exact["p_opt_given_feas"],
                "G_feas": exact["G_feas"],
                "terminal_parameters": json.dumps(record["terminal_parameters"]),
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(root / "finite_shot_training_runs.csv", frame)
    task_summary = (
        frame.groupby(
            [
                "training_regime",
                "shots_per_evaluation",
                "task_id",
                "graph_id",
                "size_stratum",
                "m",
                "objective",
            ],
            as_index=False,
        ).agg(
            seed_count=("seed", "nunique"),
            mean_energy=("mean_energy", "median"),
            P_feas=("P_feas", "median"),
            P_opt=("P_opt", "median"),
            P_opt_given_feas=("P_opt_given_feas", "median"),
            G_feas=("G_feas", "median"),
            G_feas_sd=("G_feas", "std"),
            median_nfev=("actual_nfev", "median"),
            median_nit=("nit", "median"),
            median_wall_time_s=("wall_time_s", "median"),
        )
        if len(frame)
        else pd.DataFrame()
    )
    # Add frozen exact-trained endpoints as a non-optimized reference regime.
    task_ids = {row["task_id"] for row in manifest["training_tasks"]}
    endpoints = _endpoint_lookup(task_ids)
    exact_rows = []
    for task_record in manifest["training_tasks"]:
        for objective in ("O0", "O3"):
            endpoint = endpoints[(task_record["task_id"], objective)]
            exact_rows.append(
                {
                    "training_regime": "EXACT_CANONICAL",
                    "shots_per_evaluation": 0,
                    "task_id": task_record["task_id"],
                    "graph_id": task_record["graph_id"],
                    "size_stratum": task_record["size_stratum"],
                    "m": task_record["m"],
                    "objective": objective,
                    "seed_count": 1,
                    "mean_energy": endpoint["mean_energy"],
                    "P_feas": endpoint["p_feas"],
                    "P_opt": endpoint["p_opt"],
                    "P_opt_given_feas": endpoint["p_opt_given_feasible"],
                    "G_feas": endpoint["log_feasibility_gain"],
                    "G_feas_sd": math.nan,
                    "median_nfev": endpoint["nfev"],
                    "median_nit": math.nan,
                    "median_wall_time_s": endpoint["runtime_s"],
                }
            )
    task_summary = pd.concat([pd.DataFrame(exact_rows), task_summary], ignore_index=True)
    atomic_write_csv(root / "finite_shot_training_summary_task.csv", task_summary)
    graph_summary = task_summary.groupby(
        ["training_regime", "shots_per_evaluation", "graph_id", "objective"],
        as_index=False,
    ).agg(
        n_tasks=("task_id", "nunique"),
        mean_energy=("mean_energy", "mean"),
        P_feas=("P_feas", "mean"),
        P_opt=("P_opt", "mean"),
        P_opt_given_feas=("P_opt_given_feas", "mean"),
        G_feas=("G_feas", "mean"),
    )
    atomic_write_csv(root / "finite_shot_training_summary_graph.csv", graph_summary)
    task_effects, graph_effects = paired_objective_effects(
        task_summary.rename(columns={"training_regime": "regime"}),
        value_column="G_feas",
        group_columns=["regime", "shots_per_evaluation"],
    )
    settings = load_json(PROJECT_ROOT / manifest["protocol_path"])["global"]
    effect_summary = graph_effect_summary(
        graph_effects,
        group_columns=["regime", "shots_per_evaluation"],
        resamples=int(settings["bootstrap_resamples"]),
        seed=int(settings["bootstrap_seed"]) + 300,
    )
    atomic_write_csv(root / "finite_shot_training_effects_task.csv", task_effects)
    atomic_write_csv(root / "finite_shot_training_effects_graph.csv", graph_effects)
    atomic_write_csv(root / "finite_shot_training_effect_summary.csv", effect_summary)
    _plot_training(root, effect_summary, frame)
    planned = int(manifest["planned_training_runs"])
    failed = len(list((root / "training_runs").glob("*.json"))) - len(records)
    report = _training_report(manifest, records, frame, effect_summary, planned, failed)
    atomic_write_text(root / "A3_FINITE_SHOT_TRAINING.md", report)
    return {
        "planned_runs": planned,
        "complete_runs": len(records),
        "failed_runs": failed,
        "actual_objective_calls": int(frame.actual_nfev.sum()) if len(frame) else 0,
        "total_sampled_bitstrings": int(frame.total_sampled_bitstrings.sum()) if len(frame) else 0,
    }


def _plot_training(root: Path, effects: pd.DataFrame, frame: pd.DataFrame) -> None:
    if not len(effects):
        return
    figure_root = root / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    order = {"EXACT_CANONICAL": 0, "SHOT_10000": 1, "SHOT_1000": 2}
    plot = effects.copy()
    plot["order"] = plot.regime.map(order)
    plot = plot.sort_values("order")
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.8), constrained_layout=True)
    axes[0].errorbar(
        range(len(plot)),
        plot.graph_effect_mean,
        yerr=[
            plot.graph_effect_mean - plot.graph_effect_ci_lower,
            plot.graph_effect_ci_upper - plot.graph_effect_mean,
        ],
        marker="o",
        capsize=4,
    )
    axes[0].set_xticks(range(len(plot)), plot.regime, rotation=20)
    axes[0].axhline(0.0, color="black", linewidth=0.8)
    axes[0].set_ylabel("Graph mean O3−O0 $G_{feas}$")
    axes[0].set_title("Ordering after exact endpoint evaluation")
    if len(frame):
        data = [
            group.G_feas.to_numpy(dtype=float)
            for _, group in frame.groupby("training_regime", sort=True)
        ]
        labels = [name for name, _ in frame.groupby("training_regime", sort=True)]
        axes[1].boxplot(data, tick_labels=labels, showfliers=False)
        axes[1].tick_params(axis="x", rotation=20)
    axes[1].set_ylabel("Exact terminal $G_{feas}$")
    axes[1].set_title("Training-run variability")
    for axis in axes:
        axis.grid(alpha=0.2)
    for label, axis in zip("ab", axes):
        axis.text(-0.10, 1.06, label, transform=axis.transAxes, fontweight="bold")
    for suffix in ("png", "pdf"):
        fig.savefig(figure_root / f"Figure_R3_finite_shot_training.{suffix}", dpi=300)
    plt.close(fig)


def _training_report(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    frame: pd.DataFrame,
    effects: pd.DataFrame,
    planned: int,
    failed: int,
) -> str:
    complete = len(records)
    status = "COMPLETE" if complete == planned and failed == 0 else "PARTIAL"
    lines = [
        "# A3 — End-to-end finite-shot training",
        "",
        f"**Execution status: {status}.** Completed {complete}/{planned} planned runs; failed records: {failed}.",
        "",
        "## Protocol",
        "",
        f"The manifest freezes {len(manifest['training_tasks'])} held-out tasks selected only by graph, m, feasible fraction, and dilution. O0 and O3(alpha=0.10) use COBYLA with {manifest['training']['evaluation_budget']} actual objective calls, 1e3 or 1e4 shots per call, and {len(manifest['training']['seeds'])} independent training/sampling seeds.",
        "",
        "Every evaluation receives a fresh PCG64 sample whose seed is a stable SHA-256 derivation of task, objective, shots, training seed, and evaluation index. Final theta is evaluated with the exact statevector, separating noisy training from true final quality.",
        "",
        "Manifest: `results/reviewer_robustness/manifests/manifest_finite_shot.json`; execution copy: `results/reviewer_robustness/A3_finite_shot/training_manifest.json`.",
        "",
        "## Numerical findings",
        "",
    ]
    if len(effects):
        for row in effects.sort_values("shots_per_evaluation", ascending=False).itertuples(index=False):
            lines.append(
                f"- {row.regime}: graph mean O3−O0 G_feas={row.graph_effect_mean:.4f}, 95% graph-cluster bootstrap CI [{row.graph_effect_ci_lower:.4f}, {row.graph_effect_ci_upper:.4f}]."
            )
    else:
        lines.append("No complete paired effects are available yet.")
    if len(frame):
        lines.append(
            f"- Total objective calls: {int(frame.actual_nfev.sum())}; total sampled bitstrings: {int(frame.total_sampled_bitstrings.sum())}."
        )
        for shots, group in frame.groupby("shots_per_evaluation"):
            lines.append(
                f"- {int(shots):g} shots/eval: median actual nfev={group.actual_nfev.median():.0f}; median exact-terminal G_feas SD across task/objective groups={group.groupby(['task_id','objective']).G_feas.std().median():.4g}."
            )
    lines.extend(
        [
            "",
            "## Interpretation and limitations",
            "",
            "Ordering and variance are reported without a positivity requirement. This simulator experiment tests sampling noise in the classical objective only; it does not model device, gate, readout, or hardware noise and does not establish hardware readiness.",
            "",
            "## Claim impact",
            "",
            ("The complete graph-level effects above determine whether finite-shot training preserves the exact ordering." if status == "COMPLETE" else "The incomplete matrix is not sufficient for a paper-level finite-shot-training claim."),
            "Any paper statement must remain about finite-sampling objective estimation/training in an exact simulator; it must not be described as device-noise robustness or hardware readiness.",
            "",
        ]
    )
    return "\n".join(lines)
