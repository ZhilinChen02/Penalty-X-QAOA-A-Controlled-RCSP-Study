"""Held-out-only confirmatory analysis and reporting for Phase 2."""

from __future__ import annotations

import json
import math
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .io import PROJECT_ROOT, atomic_write_csv, atomic_write_text, load_config, write_json
from .phase2_confirmatory import (
    CONFIG_PATH,
    ENERGY_AUDIT_PATH,
    MANIFEST_PATH,
    P2_RESULTS_PATH,
    P3_RESULTS_PATH,
    POWER_PATH,
    RESULT_ROOT,
    SNAPSHOT_PATH,
    VALID_SCIENTIFIC_STATUSES,
    verify_predecessor_immutability,
)
from .phase2_statistics import confirmatory_graph_inference


VERDICTS = {
    "CVAR_HELDOUT_SUPPORTED",
    "CVAR_IMPROVEMENT_ONLY",
    "CVAR_CAPACITY_NONINFERIOR_ONLY",
    "CVAR_NOT_REPLICATED",
    "STRUCTURE_DEPENDENT_REPLICATION",
    "UNDERPOWERED_HELDOUT_RESULT",
}

RECOMMENDATIONS = {
    "EXPAND_TO_FULL_MECHANISM_STUDY",
    "ADD_WARM_START_CONTROL",
    "TEST_DEPTH_GENERALIZATION",
    "FREEZE_RESULTS_AND_START_MANUSCRIPT",
    "REDESIGN_AFTER_NONREPLICATION",
}

LABELS = {
    "O0": "O0 Mean Energy",
    "O2": "O2 Feasibility Capacity",
    "O3": "O3 CVaR-0.10",
}
COLORS = {"O0": "#1f77b4", "O2": "#d62728", "O3": "#9467bd"}


def _fit(x: Any, y: Any) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    if len(x) < 2 or np.unique(x).size < 2:
        return math.nan, math.nan
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    denominator = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - predicted) ** 2)) / denominator if denominator else 1.0
    return float(slope), float(r2)


def _wide_task_results(results: pd.DataFrame) -> pd.DataFrame:
    identity = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "dilution_score",
        "feasible_state_fraction",
    ]
    metrics = [
        "log_feasibility_gain",
        "p_feas",
        "p_opt",
        "p_opt_given_feasible",
        "expected_route_cost_given_feasible",
        "mean_energy",
        "objective_improvement",
        "p_feas_change",
        "p_opt_change",
    ]
    wide = results.pivot(index=identity, columns="objective_id", values=metrics)
    wide.columns = [f"{metric}_{objective}" for metric, objective in wide.columns]
    return wide.reset_index()


def build_task_contrasts(results: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    wide = _wide_task_results(results)
    eligibility = results.groupby("task_id").paired_analysis_eligible.all()
    wide["paired_analysis_eligible"] = wide.task_id.map(eligibility).fillna(False)
    wide["Delta_CVAR_MEAN"] = wide.log_feasibility_gain_O3 - wide.log_feasibility_gain_O0
    wide["Delta_CVAR_CAPACITY"] = (
        wide.log_feasibility_gain_O3 - wide.log_feasibility_gain_O2
    )
    wide["capacity_gap"] = wide.log_feasibility_gain_O2 - wide.log_feasibility_gain_O0
    wide["cvar_residual_gap"] = (
        wide.log_feasibility_gain_O2 - wide.log_feasibility_gain_O3
    )
    tolerance = float(config["gap_closure_stability_tolerance_decades"])
    wide["stable_gap_closure_eligible"] = wide.capacity_gap > tolerance
    wide["gap_closure"] = np.where(
        wide.stable_gap_closure_eligible,
        wide.Delta_CVAR_MEAN / wide.capacity_gap,
        np.nan,
    )
    ni = float(config["noninferiority_margin_decades"])
    numerical = float(config["numerical_tolerance"])
    wide["O2_greater_than_O0"] = wide.capacity_gap > numerical
    wide["O3_greater_than_O0"] = wide.Delta_CVAR_MEAN > numerical
    wide["O3_at_least_O2"] = wide.Delta_CVAR_CAPACITY >= -numerical
    wide["O3_within_NI_of_O2"] = wide.Delta_CVAR_CAPACITY > -ni
    wide["O3_popt_vs_O0"] = np.select(
        [
            wide.p_opt_O3 > wide.p_opt_O0 + numerical,
            wide.p_opt_O3 < wide.p_opt_O0 - numerical,
        ],
        ["WIN", "LOSS"],
        default="TIE",
    )
    wide["O3_both_pfeas_and_popt_greater"] = (
        (wide.p_feas_O3 > wide.p_feas_O0 + numerical)
        & (wide.p_opt_O3 > wide.p_opt_O0 + numerical)
    )
    wide["O3_feasibility_up_conditional_quality_down"] = (
        (wide.p_feas_O3 > wide.p_feas_O0 + numerical)
        & (
            wide.p_opt_given_feasible_O3
            < wide.p_opt_given_feasible_O0 - numerical
        )
    )
    atomic_write_csv(RESULT_ROOT / "task_level_contrasts.csv", wide)
    return wide


def build_graph_contrasts(
    task: pd.DataFrame, manifest: dict[str, Any], config: dict[str, Any]
) -> pd.DataFrame:
    rows = []
    for graph_id in manifest["base_graph_ids"]:
        group = task[task.base_instance_id == graph_id]
        expected_levels = int(
            config["expected_counts_by_size"][group.size_stratum.iloc[0]]["levels_per_graph"]
        )
        complete = bool(
            len(group) == expected_levels
            and group.paired_analysis_eligible.all()
            and np.isfinite(
                group[
                    [
                        "log_feasibility_gain_O0",
                        "log_feasibility_gain_O2",
                        "log_feasibility_gain_O3",
                    ]
                ].to_numpy()
            ).all()
        )
        record: dict[str, Any] = {
            "base_graph_id": group.base_graph_id.iloc[0],
            "base_instance_id": graph_id,
            "size_stratum": group.size_stratum.iloc[0],
            "planned_levels": expected_levels,
            "observed_task_rows": len(group),
            "complete_graph_eligible": complete,
        }
        for objective in ("O0", "O2", "O3"):
            record[f"bar_G_{objective}"] = (
                float(group[f"log_feasibility_gain_{objective}"].mean())
                if complete
                else math.nan
            )
            record[f"bar_P_feas_{objective}"] = (
                float(group[f"p_feas_{objective}"].mean()) if complete else math.nan
            )
            record[f"bar_P_opt_{objective}"] = (
                float(group[f"p_opt_{objective}"].mean()) if complete else math.nan
            )
        record["Delta1_CVAR_MEAN"] = record["bar_G_O3"] - record["bar_G_O0"]
        record["Delta2_CVAR_CAPACITY"] = record["bar_G_O3"] - record["bar_G_O2"]
        record["Delta_P_opt_CVAR_MEAN"] = record["bar_P_opt_O3"] - record["bar_P_opt_O0"]
        rows.append(record)
    frame = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "graph_level_contrasts.csv", frame)
    return frame


def build_compensation_slopes(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (base_id, objective_id), group in results.groupby(
        ["base_instance_id", "objective_id"], sort=False
    ):
        valid = group.execution_status.isin(VALID_SCIENTIFIC_STATUSES) & np.isfinite(
            group.log_feasibility_gain
        )
        selected = group[valid]
        kappa, r2 = _fit(selected.dilution_score, selected.log_feasibility_gain)
        rows.append(
            {
                "base_graph_id": group.base_graph_id.iloc[0],
                "base_instance_id": base_id,
                "size_stratum": group.size_stratum.iloc[0],
                "objective_id": objective_id,
                "objective_name": group.objective_name.iloc[0],
                "n_levels": len(selected),
                "kappa": kappa,
                "R2": r2,
                "min_D": float(selected.dilution_score.min()) if len(selected) else math.nan,
                "max_D": float(selected.dilution_score.max()) if len(selected) else math.nan,
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "compensation_slopes.csv", frame)
    return frame


def build_cvar_diagnostics(results: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    tolerance = float(config["numerical_tolerance"])
    cvar = results[results.objective_id == "O3"].copy()
    cvar["p_feas_at_least_alpha"] = cvar.p_feas >= cvar.cvar_alpha - tolerance
    cvar["cvar_tail_condition_pass"] = (
        cvar.cvar_tail_fully_feasible.astype(bool) == cvar.p_feas_at_least_alpha
    )
    mean_gain = results[results.objective_id == "O0"].set_index("task_id")[
        "log_feasibility_gain"
    ]
    cvar["Delta_CVAR_MEAN"] = cvar.log_feasibility_gain - cvar.task_id.map(mean_gain)
    columns = [
        "run_id",
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "dilution_score",
        "p_feas",
        "p_opt",
        "p_opt_given_feasible",
        "Delta_CVAR_MEAN",
        "cvar_alpha",
        "cvar_value",
        "cvar_cutoff_energy",
        "cvar_tail_feasible_mass",
        "cvar_tail_fully_feasible",
        "p_feas_at_least_alpha",
        "cvar_tail_condition_pass",
    ]
    frame = cvar[columns]
    atomic_write_csv(RESULT_ROOT / "cvar_tail_diagnostics.csv", frame)
    return frame


def _failure_census(p2: pd.DataFrame, p3: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for phase, frame, planned in (("P2_PREPARATION", p2, 252), ("P3_COMPARISON", p3, 252)):
        counts = frame.execution_status.value_counts().to_dict()
        for status in (
            "SUCCESS",
            "TIMEOUT",
            "OOM",
            "OPTIMIZER_FAILURE",
            "NUMERICAL_FAILURE",
            "ZERO_P_FEAS",
            "ZERO_P_OPT",
            "RESOURCE_CENSORED",
        ):
            rows.append(
                {
                    "phase": phase,
                    "execution_status": status,
                    "count": int(counts.get(status, 0)),
                    "planned_denominator": planned,
                }
            )
    census = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "failure_census.csv", census)
    return census


def _slope_summary(slopes: pd.DataFrame) -> dict[str, Any]:
    result = {}
    for objective, group in slopes.groupby("objective_id", sort=True):
        values = group.kappa.dropna().to_numpy()
        result[objective] = {
            "n": len(values),
            "median": float(np.median(values)),
            "q1": float(np.quantile(values, 0.25)),
            "q3": float(np.quantile(values, 0.75)),
            "IQR": float(np.quantile(values, 0.75) - np.quantile(values, 0.25)),
            "min": float(values.min()),
            "max": float(values.max()),
            "negative_count": int(np.sum(values < 0.0)),
            "positive_count": int(np.sum(values > 0.0)),
        }
    wide = slopes.pivot(index="base_instance_id", columns="objective_id", values="kappa")
    for column, expression in (
        ("Delta_kappa_CVAR_MEAN", wide.O3 - wide.O0),
        ("Delta_kappa_CVAR_CAPACITY", wide.O3 - wide.O2),
    ):
        values = expression.dropna().to_numpy()
        result[column] = {
            "median": float(np.median(values)),
            "IQR": float(np.quantile(values, 0.75) - np.quantile(values, 0.25)),
            "min": float(values.min()),
            "max": float(values.max()),
            "negative_count": int(np.sum(values < 0.0)),
            "positive_count": int(np.sum(values > 0.0)),
        }
    return result


def _plot_figures(
    results: pd.DataFrame,
    task: pd.DataFrame,
    graph: pd.DataFrame,
    slopes: pd.DataFrame,
    cvar: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    output = RESULT_ROOT / "figures"
    output.mkdir(parents=True, exist_ok=True)
    baseline = results[results.objective_id == "O0"]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(
        baseline.dilution_score,
        baseline.feasible_state_fraction,
        color="gray",
        s=24,
        alpha=0.65,
        label="Uniform analytic baseline",
    )
    for objective, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.dilution_score,
            group.p_feas,
            s=24,
            alpha=0.62,
            color=COLORS[objective],
            label=LABELS[objective],
        )
    ax.set_yscale("log")
    ax.set(xlabel="Dilution score D", ylabel="P_feas", title="HELD-OUT PHASE 2")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure1_main_heldout_result.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for objective, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.dilution_score,
            group.log_feasibility_gain,
            s=24,
            alpha=0.62,
            color=COLORS[objective],
            label=LABELS[objective],
        )
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="Dilution score D", ylabel="G_feas", title="HELD-OUT PHASE 2")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure2_heldout_feasibility_gain.png", dpi=180)
    plt.close(fig)

    eligible = graph[graph.complete_graph_eligible]
    for filename, xcol, ycol, xlabel, ylabel, ni in (
        (
            "figure3_graph_paired_mean_vs_cvar.png",
            "bar_G_O0",
            "bar_G_O3",
            "bar G(O0)",
            "bar G(O3)",
            False,
        ),
        (
            "figure4_graph_paired_capacity_vs_cvar.png",
            "bar_G_O2",
            "bar_G_O3",
            "bar G(O2)",
            "bar G(O3)",
            True,
        ),
    ):
        x, y = eligible[xcol], eligible[ycol]
        limits = [float(min(x.min(), y.min())) - 0.05, float(max(x.max(), y.max())) + 0.05]
        fig, ax = plt.subplots(figsize=(6.2, 5.5))
        ax.scatter(x, y, s=48, alpha=0.8)
        ax.plot(limits, limits, color="black", linestyle="--", label="equality")
        if ni:
            margin = float(config["noninferiority_margin_decades"])
            ax.plot(
                limits,
                [value - margin for value in limits],
                color="red",
                linestyle=":",
                label="non-inferiority boundary (-0.10)",
            )
        ax.set(xlabel=xlabel, ylabel=ylabel, xlim=limits, ylim=limits)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)

    for filename, column, label, margin in (
        ("figure5_graph_delta_cvar_mean.png", "Delta1_CVAR_MEAN", "Delta1 graph: O3 - O0", 0.0),
        (
            "figure6_graph_delta_cvar_capacity.png",
            "Delta2_CVAR_CAPACITY",
            "Delta2 graph: O3 - O2",
            -float(config["noninferiority_margin_decades"]),
        ),
    ):
        fig, ax = plt.subplots(figsize=(7, 5.2))
        ax.hist(eligible[column], bins=min(10, len(eligible)), alpha=0.75, edgecolor="black")
        ax.axvline(margin, color="red" if margin else "black", linestyle="--")
        ax.set(xlabel=label, ylabel="Base-graph count")
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5.2))
    arrays = [slopes[slopes.objective_id == objective].kappa for objective in LABELS]
    boxes = ax.boxplot(arrays, tick_labels=list(LABELS), patch_artist=True)
    for box, objective in zip(boxes["boxes"], LABELS):
        box.set_facecolor(COLORS[objective])
        box.set_alpha(0.65)
    ax.axhline(0.0, color="black", linestyle="--")
    ax.set(ylabel="Within-base kappa")
    fig.tight_layout()
    fig.savefig(output / "figure7_kappa_distributions.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 5.4))
    ax.scatter(task.dilution_score, task.capacity_gap, alpha=0.68, label="O2 - O0 capacity gap")
    ax.scatter(
        task.dilution_score,
        task.cvar_residual_gap,
        alpha=0.68,
        label="O2 - O3 CVaR residual",
    )
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="Dilution score D", ylabel="G_feas gap")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure8_capacity_and_residual_gaps.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    for objective, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.p_feas,
            group.p_opt_given_feasible,
            s=26,
            alpha=0.62,
            color=COLORS[objective],
            label=LABELS[objective],
        )
    ax.set(xlabel="P_feas", ylabel="P_opt_given_feasible")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure9_feasibility_vs_conditional_optimal.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for state, group in cvar.groupby("cvar_tail_fully_feasible", sort=True):
        label = "fully feasible tail" if state else "partially feasible tail"
        axes[0].scatter(group.dilution_score, group.p_feas, alpha=0.7, label=label)
        axes[1].scatter(
            group.dilution_score,
            group.p_opt_given_feasible,
            alpha=0.7,
            label=label,
        )
    axes[0].axhline(float(config["cvar_alpha"]), color="black", linestyle="--", label="alpha=0.10")
    axes[0].set(xlabel="Dilution score D", ylabel="P_feas")
    axes[1].set(xlabel="Dilution score D", ylabel="P_opt_given_feasible")
    axes[0].legend(fontsize=8)
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure10_cvar_tail_state.png", dpi=180)
    plt.close(fig)


def analyze_phase2(
    *, verdict: str, recommendation: str, pytest_result: str
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"invalid Phase 2 verdict: {verdict}")
    if recommendation not in RECOMMENDATIONS:
        raise ValueError(f"invalid Phase 2 recommendation: {recommendation}")
    verify_predecessor_immutability()
    config = load_config(CONFIG_PATH)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    power = json.loads(POWER_PATH.read_text(encoding="utf-8"))
    p2 = pd.read_csv(P2_RESULTS_PATH)
    p3 = pd.read_csv(P3_RESULTS_PATH)
    if len(p2) != 252 or len(p3) != 252:
        raise RuntimeError("complete planned Phase 2 denominators required for analysis")
    task = build_task_contrasts(p3, config)
    graph = build_graph_contrasts(task, manifest, config)
    slopes = build_compensation_slopes(p3)
    cvar = build_cvar_diagnostics(p3, config)
    census = _failure_census(p2, p3)
    complete_graphs = graph[graph.complete_graph_eligible]
    inference = confirmatory_graph_inference(
        complete_graphs.Delta1_CVAR_MEAN.to_numpy(),
        complete_graphs.Delta2_CVAR_CAPACITY.to_numpy(),
        noninferiority_margin=float(config["noninferiority_margin_decades"]),
        resamples=int(config["primary_inference"]["bootstrap_resamples"]),
        bootstrap_seed=int(config["primary_inference"]["bootstrap_seed"]),
        family_alpha=float(config["primary_inference"]["family_alpha"]),
    )
    formal_complete = len(complete_graphs) == int(config["expected_base_graph_count"])
    inference["formal_complete_15_graph_family"] = formal_complete
    if not formal_complete:
        inference["H1"]["pass"] = False
        inference["H2"]["pass"] = False
    write_json(RESULT_ROOT / "confirmatory_statistics.json", inference)
    scientific_failures = int(
        (~p2.execution_status.isin(VALID_SCIENTIFIC_STATUSES)).sum()
        + (~p3.execution_status.isin(VALID_SCIENTIFIC_STATUSES)).sum()
    )
    if power["power_gate"] != "PASS_CONFIRMATORY":
        status = "UNDERPOWERED_REPLICATION"
    elif not formal_complete or scientific_failures:
        status = "PARTIAL"
    else:
        status = "COMPLETE"
    eligible_task = task[task.paired_analysis_eligible]
    stable = eligible_task[eligible_task.stable_gap_closure_eligible]
    popt_delta = eligible_task.p_opt_O3 - eligible_task.p_opt_O0
    numerical = float(config["numerical_tolerance"])
    routing = {
        "O3_vs_O0_P_opt_wins": int((popt_delta > numerical).sum()),
        "O3_vs_O0_P_opt_losses": int((popt_delta < -numerical).sum()),
        "O3_vs_O0_P_opt_ties": int((popt_delta.abs() <= numerical).sum()),
        "paired_median_P_opt_difference": float(popt_delta.median()),
        "O3_vs_O0_both_Pfeas_Popt_greater": int(
            eligible_task.O3_both_pfeas_and_popt_greater.sum()
        ),
        "O3_feasibility_up_conditional_quality_down": int(
            eligible_task.O3_feasibility_up_conditional_quality_down.sum()
        ),
        "median_P_opt_given_feasible_O0": float(
            eligible_task.p_opt_given_feasible_O0.median()
        ),
        "median_P_opt_given_feasible_O3": float(
            eligible_task.p_opt_given_feasible_O3.median()
        ),
        "median_conditional_route_cost_O0": float(
            eligible_task.expected_route_cost_given_feasible_O0.median()
        ),
        "median_conditional_route_cost_O3": float(
            eligible_task.expected_route_cost_given_feasible_O3.median()
        ),
        "graph_mean_P_opt_difference": float(
            complete_graphs.Delta_P_opt_CVAR_MEAN.mean()
        ),
    }
    capacity = {
        "median_capacity_gap": float(eligible_task.capacity_gap.median()),
        "median_cvar_residual_gap": float(eligible_task.cvar_residual_gap.median()),
        "median_stable_gap_closure": float(stable.gap_closure.median()),
        "stable_gap_closure_task_count": len(stable),
        "O2_greater_than_O0_count": int(eligible_task.O2_greater_than_O0.sum()),
        "O3_greater_than_O0_count": int(eligible_task.O3_greater_than_O0.sum()),
        "O3_at_least_O2_count": int(eligible_task.O3_at_least_O2.sum()),
        "O3_within_0_10_of_O2_count": int(eligible_task.O3_within_NI_of_O2.sum()),
    }
    alignment = {
        "O3_greater_P_feas_than_O0": int(
            (eligible_task.p_feas_O3 > eligible_task.p_feas_O0 + numerical).sum()
        ),
        "O3_greater_P_opt_than_O0": routing["O3_vs_O0_P_opt_wins"],
        "O3_greater_both": routing["O3_vs_O0_both_Pfeas_Popt_greater"],
        "O3_feasibility_up_conditional_quality_down": routing[
            "O3_feasibility_up_conditional_quality_down"
        ],
        "O3_worse_mean_energy_than_O0": int(
            (eligible_task.mean_energy_O3 > eligible_task.mean_energy_O0 + numerical).sum()
        ),
        "median_objective_improvement_O0": float(
            eligible_task.objective_improvement_O0.median()
        ),
        "median_objective_improvement_O3": float(
            eligible_task.objective_improvement_O3.median()
        ),
        "median_P_feas_change_O0": float(eligible_task.p_feas_change_O0.median()),
        "median_P_feas_change_O3": float(eligible_task.p_feas_change_O3.median()),
        "median_P_opt_change_O0": float(eligible_task.p_opt_change_O0.median()),
        "median_P_opt_change_O3": float(eligible_task.p_opt_change_O3.median()),
    }
    slope_summary = _slope_summary(slopes)
    discovery = json.loads(
        (PROJECT_ROOT / config["phase1_2_summary"]).read_text(encoding="utf-8")
    )
    held_direction = {
        "capacity_gap_positive": capacity["median_capacity_gap"] > 0.0,
        "O3_benefit_positive": float(complete_graphs.Delta1_CVAR_MEAN.mean()) > 0.0,
        "O3_residual_small_direction": capacity["median_cvar_residual_gap"] >= 0.0,
    }
    direction_replicated = (
        "YES" if all(held_direction.values()) else "MIXED" if any(held_direction.values()) else "NO"
    )
    runtime = {
        "p2_total_runtime_s": float(p2.runtime_s.fillna(0.0).sum()),
        "p3_total_runtime_s": float(p3.runtime_s.fillna(0.0).sum()),
        "maximum_recorded_peak_memory_mb": float(
            max(p2.peak_memory_mb.max(), p3.peak_memory_mb.max())
        ),
    }
    summary = {
        "phase": "Phase 2 — Preregistered Held-Out Objective Confirmation",
        "phase2_status": status,
        "evidence_identity": config["evidence_identity"],
        "frozen_identity": {
            key: snapshot[key]
            for key in (
                "pre_run_git_sha",
                "phase2_manifest_sha256",
                "phase2_config_sha256",
                "preregistration_sha256",
                "task_universe_manifest_sha256",
                "penalty_contract_sha256",
            )
        },
        "heldout_task_count": manifest["task_count"],
        "heldout_base_graph_count": manifest["base_graph_count"],
        "phase2_base_graph_overlap_with_discovery": 0,
        "phase2_task_overlap_with_discovery": 0,
        "execution": {
            "planned_p2_runs": 252,
            "completed_p2_rows": len(p2),
            "planned_p3_runs": 252,
            "completed_p3_rows": len(p3),
            "scientific_failure_count": scientific_failures,
            **runtime,
        },
        "power_preflight": power,
        "confirmatory_inference": inference,
        "capacity_gap_replication": capacity,
        "dilution_compensation": slope_summary,
        "routing_quality": routing,
        "objective_alignment_replication": alignment,
        "cvar_tail_mechanism": {
            "strict_energy_separation_count": int(
                pd.read_csv(ENERGY_AUDIT_PATH).strict_energy_class_separation.sum()
            ),
            "fully_feasible_tail_count": int(cvar.cvar_tail_fully_feasible.sum()),
            "tail_condition_pass_count": int(cvar.cvar_tail_condition_pass.sum()),
            "median_P_opt_given_feasible_fully_feasible_tail": float(
                cvar[cvar.cvar_tail_fully_feasible].p_opt_given_feasible.median()
            ),
            "median_P_opt_given_feasible_partial_tail": float(
                cvar[~cvar.cvar_tail_fully_feasible].p_opt_given_feasible.median()
            ),
            "median_O3_minus_O0_G_fully_feasible_tail": float(
                cvar[cvar.cvar_tail_fully_feasible].Delta_CVAR_MEAN.median()
            ),
            "median_O3_minus_O0_G_partial_tail": float(
                cvar[~cvar.cvar_tail_fully_feasible].Delta_CVAR_MEAN.median()
            ),
        },
        "replication_vs_discovery": {
            "discovery_median_capacity_gap": discovery["capacity_gaps"][
                "median_O2_minus_O0_G"
            ],
            "discovery_median_O3_benefit": float(
                discovery["capacity_gaps"]["median_O2_minus_O0_G"]
                - discovery["capacity_gaps"]["median_O2_minus_O3_G"]
            ),
            "discovery_median_cvar_residual_gap": discovery["capacity_gaps"][
                "median_O2_minus_O3_G"
            ],
            "heldout_median_capacity_gap": capacity["median_capacity_gap"],
            "heldout_graph_mean_O3_benefit": float(
                complete_graphs.Delta1_CVAR_MEAN.mean()
            ),
            "heldout_median_cvar_residual_gap": capacity["median_cvar_residual_gap"],
            "direction_replicated": direction_replicated,
        },
        "pytest_result": pytest_result,
        "scientific_verdict": verdict,
        "next_recommendation": recommendation,
        "recommendation_executed": False,
        "raw_statevectors_persisted": False,
    }
    write_json(RESULT_ROOT / "summary.json", summary)
    _plot_figures(p3, task, graph, slopes, cvar, config)

    h1, h2 = inference["H1"], inference["H2"]
    rep = summary["replication_vs_discovery"]
    tail = summary["cvar_tail_mechanism"]
    report = f"""# Phase 2 Confirmatory Report — Held-Out CVaR Dilution Confirmation

## A. Phase 2 status

**{status}**. The held-out inferential dataset is separate from Phase 1.2 discovery evidence.

## B. Frozen identity

- Pre-run SHA: `{snapshot['pre_run_git_sha']}`
- Manifest SHA-256: `{snapshot['phase2_manifest_sha256']}`
- Config SHA-256: `{snapshot['phase2_config_sha256']}`
- Preregistration SHA-256: `{snapshot['preregistration_sha256']}`
- Held-out tasks/base graphs: 84/15
- Discovery graph/task overlap: 0/0

## C. Execution

Planned and retained denominators are 252 p=2 preparation rows and 252 p=3 comparison rows; observed rows are {len(p2)} and {len(p3)}. Scientific failure count is {scientific_failures}. Summed cell runtimes are {runtime['p2_total_runtime_s']:.1f}s (p=2) and {runtime['p3_total_runtime_s']:.1f}s (p=3); maximum recorded worker peak memory is {runtime['maximum_recorded_peak_memory_mb']:.1f} MB. No raw statevector was persisted.

## D. H1 — CVaR versus mean energy

Graph-level mean O3–O0 effect: **{h1['effect_mean']:.4f} decades**. One-sided grouped-bootstrap 95% lower bound: **{h1['one_sided_95_lower_bound']:.4f}**. Exact sign-flip raw p: **{h1['raw_p_value']:.6g}**; Holm-adjusted p: **{h1['holm_adjusted_p_value']:.6g}**. Result: **{'PASS' if h1['pass'] else 'FAIL'}**.

## E. H2 — non-inferiority to capacity control

Graph-level mean O3–O2 effect: **{h2['effect_mean']:.4f} decades**. Frozen margin: **-0.10 decades**. One-sided grouped-bootstrap 95% lower bound: **{h2['one_sided_95_lower_bound']:.4f}**. Exact shifted sign-flip raw p: **{h2['raw_p_value']:.6g}**; Holm-adjusted p: **{h2['holm_adjusted_p_value']:.6g}**. Result: **{'PASS' if h2['pass'] else 'FAIL'}**. O2 remains a statevector mechanistic capacity control, not a deployment-ready solver objective.

## F. Discovery versus held-out replication

| Quantity | Phase 1.2 discovery | Phase 2 held-out |
|---|---:|---:|
| O2–O0 capacity gap | {rep['discovery_median_capacity_gap']:.4f} | {rep['heldout_median_capacity_gap']:.4f} |
| O3–O0 benefit | {rep['discovery_median_O3_benefit']:.4f} | {rep['heldout_graph_mean_O3_benefit']:.4f} |
| O2–O3 residual gap | {rep['discovery_median_cvar_residual_gap']:.4f} | {rep['heldout_median_cvar_residual_gap']:.4f} |

Direction replicated: **{rep['direction_replicated']}**. Discovery rows were not pooled into Phase 2 inference.

## G. Dilution compensation

Median kappa is {slope_summary['O0']['median']:.4f} for O0, {slope_summary['O2']['median']:.4f} for O2, and {slope_summary['O3']['median']:.4f} for O3. The median O3–O0 kappa difference is {slope_summary['Delta_kappa_CVAR_MEAN']['median']:.4f}. These slope analyses are secondary and do not define a threshold or phase transition.

## H. Routing quality

O3 versus O0 `P_opt` wins/losses/ties: {routing['O3_vs_O0_P_opt_wins']}/{routing['O3_vs_O0_P_opt_losses']}/{routing['O3_vs_O0_P_opt_ties']}; paired median difference {routing['paired_median_P_opt_difference']:.6g}. O3 increased both `P_feas` and `P_opt` on {routing['O3_vs_O0_both_Pfeas_Popt_greater']} tasks, while feasibility rose and conditional optimal quality fell on {routing['O3_feasibility_up_conditional_quality_down']} tasks. Median `P_opt_given_feasible` was {routing['median_P_opt_given_feasible_O0']:.4f} (O0) versus {routing['median_P_opt_given_feasible_O3']:.4f} (O3); median conditional route cost was {routing['median_conditional_route_cost_O0']:.4f} versus {routing['median_conditional_route_cost_O3']:.4f}.

O3 ended at higher mean Hamiltonian energy than O0 on {alignment['O3_worse_mean_energy_than_O0']}/84 tasks. This is not classified as an optimization failure because O3 optimizes the frozen CVaR loss rather than mean energy. Median feasibility changes from the common initial point were {alignment['median_P_feas_change_O0']:.6g} for O0 and {alignment['median_P_feas_change_O3']:.6g} for O3; median optimal-probability changes were {alignment['median_P_opt_change_O0']:.6g} and {alignment['median_P_opt_change_O3']:.6g}.

## I. CVaR-tail mechanism

Strict energy separation passed {tail['strict_energy_separation_count']}/84 tasks and the tail condition passed {tail['tail_condition_pass_count']}/84 O3 rows. Fully feasible tails occurred in **{tail['fully_feasible_tail_count']}/84** tasks. Median O3–O0 `G_feas` benefit was {tail['median_O3_minus_O0_G_fully_feasible_tail']:.4f} when the tail was fully feasible and {tail['median_O3_minus_O0_G_partial_tail']:.4f} when it was partial. Median `P_opt_given_feasible` was {tail['median_P_opt_given_feasible_fully_feasible_tail']:.4f} for fully feasible tails and {tail['median_P_opt_given_feasible_partial_tail']:.4f} for partial tails. This is descriptive; alpha remained frozen at 0.10.

## J. Scientific verdict

**{verdict}**

This result does not imply quantum advantage, universal resolution of dilution, a critical dilution threshold, a phase transition, or general QAOA success/failure on RCSP.

## K. Next recommendation

**{recommendation}** — recorded only and not executed.

## Verification

- Tests: `{pytest_result}`
- Immutable predecessors: verified
- Preregistered graph-level family: H1 and H2 only, Holm corrected
- Raw statevectors: not persisted
"""
    atomic_write_text(RESULT_ROOT / "PHASE2_CONFIRMATORY_REPORT.md", report)
    verify_predecessor_immutability()
    return summary
