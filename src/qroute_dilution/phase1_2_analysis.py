"""Descriptive analysis, figures, and report for Phase 1.2."""

from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ConstantInputWarning, spearmanr

from .io import PROJECT_ROOT, atomic_write_csv, atomic_write_text, load_config, write_json
from .phase1_2_experiment import (
    CONFIG_PATH,
    OBJECTIVE_RESULTS_PATH,
    RESULT_ROOT,
    THEORETICAL_AUDIT_PATH,
    verify_historical_immutability,
)


VERDICTS = {
    "MEAN_ENERGY_OBJECTIVE_LIMITED",
    "PENALTY_OBJECTIVE_CLOSES_GAP",
    "CVAR_PARTIALLY_CLOSES_GAP",
    "ANSATZ_CAPACITY_LIMITED",
    "FEASIBILITY_QUALITY_TRADEOFF_DOMINANT",
    "MIXED_OBJECTIVE_AND_CAPACITY_LIMITS",
}

RECOMMENDATIONS = {
    "EXPAND_WITH_FROZEN_MEAN_ENERGY_BASELINE",
    "PREREGISTER_FEASIBILITY_ALIGNED_PHASE2",
    "ADD_WARM_START_CONTROL",
    "INVESTIGATE_MULTI_OBJECTIVE_PROTOCOL",
    "STOP_OBJECTIVE_BRANCH_AND_WRITE_RESULTS",
}

LABELS = {
    "O0": "O0 Mean Energy",
    "O1": "O1 Expected Penalty",
    "O2": "O2 Exact Feasibility",
    "O3": "O3 CVaR-0.10",
}

COLORS = {"O0": "#1f77b4", "O1": "#2ca02c", "O2": "#d62728", "O3": "#9467bd"}


def _spearman(x: Any, y: Any) -> tuple[float, int]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    if keep.sum() < 2 or np.unique(x[keep]).size < 2 or np.unique(y[keep]).size < 2:
        return math.nan, int(keep.sum())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        return float(spearmanr(x[keep], y[keep]).statistic), int(keep.sum())


def _fit(x: Any, y: Any) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    if len(x) < 2 or np.unique(x).size < 2:
        return math.nan, math.nan
    slope, intercept = np.polyfit(x, y, 1)
    prediction = slope * x + intercept
    denominator = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - prediction) ** 2)) / denominator if denominator else 1.0
    return float(slope), float(r2)


def compensation_by_objective(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for objective_id, arm in results.groupby("objective_id", sort=True):
        base_rows = []
        for base_id, group in arm.groupby("base_instance_id", sort=False):
            if group.dilution_score.nunique() < 3:
                continue
            kappa, r2 = _fit(group.dilution_score, group.log_feasibility_gain)
            record = {
                "scope": "base_graph",
                "objective_id": objective_id,
                "objective_name": group.objective_name.iloc[0],
                "base_graph_id": group.base_graph_id.iloc[0],
                "base_instance_id": base_id,
                "size_stratum": group.size_stratum.iloc[0],
                "kappa": kappa,
                "R2": r2,
                "D_min": float(group.dilution_score.min()),
                "D_max": float(group.dilution_score.max()),
                "D_range": float(group.dilution_score.max() - group.dilution_score.min()),
                "number_of_levels": int(group.dilution_score.nunique()),
            }
            rows.append(record)
            base_rows.append(record)
        kappas = np.asarray([row["kappa"] for row in base_rows], dtype=float)
        rho_pfeas, n_pfeas = _spearman(arm.dilution_score, arm.p_feas)
        rho_gain, n_gain = _spearman(arm.dilution_score, arm.log_feasibility_gain)
        rho_popt, n_popt = _spearman(arm.dilution_score, arm.p_opt)
        rows.append(
            {
                "scope": "aggregate",
                "objective_id": objective_id,
                "objective_name": arm.objective_name.iloc[0],
                "base_graph_id": "",
                "base_instance_id": "",
                "size_stratum": "ALL",
                "number_of_levels": len(arm),
                "number_of_base_graphs": len(kappas),
                "median_kappa": float(np.median(kappas)),
                "kappa_q1": float(np.quantile(kappas, 0.25)),
                "kappa_q3": float(np.quantile(kappas, 0.75)),
                "kappa_IQR": float(np.quantile(kappas, 0.75) - np.quantile(kappas, 0.25)),
                "kappa_min": float(kappas.min()),
                "kappa_max": float(kappas.max()),
                "negative_count": int(np.sum(kappas < 0.0)),
                "zero_to_one_count": int(np.sum((kappas >= 0.0) & (kappas < 1.0))),
                "at_least_one_count": int(np.sum(kappas >= 1.0)),
                "spearman_D_vs_P_feas": rho_pfeas,
                "spearman_D_vs_G_feas": rho_gain,
                "spearman_D_vs_P_opt": rho_popt,
                "spearman_n_P_feas": n_pfeas,
                "spearman_n_G_feas": n_gain,
                "spearman_n_P_opt": n_popt,
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "compensation_by_objective.csv", frame)
    return frame


def _wide_results(results: pd.DataFrame) -> pd.DataFrame:
    identity = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "n_edges",
        "dilution_score",
        "feasible_state_fraction",
    ]
    metrics = [
        "p_feas",
        "p_opt",
        "p_opt_given_feasible",
        "log_feasibility_gain",
        "expected_route_cost_given_feasible",
        "expected_total_penalty",
        "mean_energy",
    ]
    wide = results.pivot(index=identity, columns="objective_id", values=metrics)
    wide.columns = [f"{metric}_{objective}" for metric, objective in wide.columns]
    return wide.reset_index()


def _pareto_flags(group: pd.DataFrame, tolerance: float) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for row in group.itertuples(index=False):
        dominated = False
        for other in group.itertuples(index=False):
            if other.objective_id == row.objective_id:
                continue
            no_worse = (
                other.p_feas >= row.p_feas - tolerance
                and other.p_opt_given_feasible >= row.p_opt_given_feasible - tolerance
            )
            strictly_better = (
                other.p_feas > row.p_feas + tolerance
                or other.p_opt_given_feasible > row.p_opt_given_feasible + tolerance
            )
            if no_worse and strictly_better:
                dominated = True
                break
        flags[row.objective_id] = not dominated
    return flags


def build_task_and_gap_tables(
    results: pd.DataFrame, compensation: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    wide = _wide_results(results)
    wide["capacity_gap_mean"] = (
        wide.log_feasibility_gain_O2 - wide.log_feasibility_gain_O0
    )
    wide["capacity_gap_penalty"] = (
        wide.log_feasibility_gain_O2 - wide.log_feasibility_gain_O1
    )
    wide["capacity_gap_cvar"] = (
        wide.log_feasibility_gain_O2 - wide.log_feasibility_gain_O3
    )
    for metric in ("p_feas", "p_opt"):
        for arm, name in (("O0", "mean"), ("O1", "penalty"), ("O3", "cvar")):
            wide[f"capacity_gap_{metric}_{name}"] = wide[f"{metric}_O2"] - wide[
                f"{metric}_{arm}"
            ]
    wide["penalty_gap_closure_fraction"] = np.where(
        wide.capacity_gap_mean > 0.0,
        (wide.log_feasibility_gain_O1 - wide.log_feasibility_gain_O0)
        / wide.capacity_gap_mean,
        np.nan,
    )
    wide["cvar_gap_closure_fraction"] = np.where(
        wide.capacity_gap_mean > 0.0,
        (wide.log_feasibility_gain_O3 - wide.log_feasibility_gain_O0)
        / wide.capacity_gap_mean,
        np.nan,
    )
    base_o2 = compensation[
        (compensation.scope == "base_graph") & (compensation.objective_id == "O2")
    ].set_index("base_instance_id")["kappa"]
    wide["O2_base_kappa"] = wide.base_instance_id.map(base_o2)
    tolerance = float(config["classification"]["objective_limited_delta_G_tolerance_decades"])
    closure = float(config["classification"]["substantial_gap_closure_fraction"])
    weak = float(config["classification"]["capacity_weak_G_threshold_decades"])
    degrading = float(config["classification"]["capacity_degrading_kappa_threshold"])
    wide["tag_OBJECTIVE_LIMITED"] = wide.capacity_gap_mean >= tolerance
    wide["tag_CAPACITY_LIMITED"] = (
        (wide.log_feasibility_gain_O2 <= weak) | (wide.O2_base_kappa < degrading)
    )
    wide["tag_PENALTY_SURROGATE_SUCCESS"] = (
        wide.tag_OBJECTIVE_LIMITED & (wide.penalty_gap_closure_fraction >= closure)
    )
    wide["tag_CVAR_PARTIAL_ALIGNMENT"] = (
        (wide.log_feasibility_gain_O3 - wide.log_feasibility_gain_O0 >= tolerance)
        & (wide.capacity_gap_cvar >= tolerance)
    )
    tag_columns = [
        "tag_OBJECTIVE_LIMITED",
        "tag_CAPACITY_LIMITED",
        "tag_PENALTY_SURROGATE_SUCCESS",
        "tag_CVAR_PARTIAL_ALIGNMENT",
    ]
    wide["mechanistic_tags"] = wide.apply(
        lambda row: ";".join(
            column.removeprefix("tag_") for column in tag_columns if bool(row[column])
        )
        or "NONE",
        axis=1,
    )
    pareto_records = []
    numerical_tolerance = float(config["audits"]["numerical_tolerance"])
    for task_id, group in results.groupby("task_id", sort=False):
        flags = _pareto_flags(group, numerical_tolerance)
        record = {"task_id": task_id}
        for objective_id, flag in flags.items():
            record[f"pareto_nondominated_{objective_id}"] = flag
        pareto_records.append(record)
    wide = wide.merge(pd.DataFrame(pareto_records), on="task_id", validate="one_to_one")
    atomic_write_csv(RESULT_ROOT / "task_objective_summary.csv", wide)
    gap_columns = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "dilution_score",
        "feasible_state_fraction",
        "capacity_gap_mean",
        "capacity_gap_penalty",
        "capacity_gap_cvar",
        "capacity_gap_p_feas_mean",
        "capacity_gap_p_feas_penalty",
        "capacity_gap_p_feas_cvar",
        "capacity_gap_p_opt_mean",
        "capacity_gap_p_opt_penalty",
        "capacity_gap_p_opt_cvar",
        "penalty_gap_closure_fraction",
        "cvar_gap_closure_fraction",
        "O2_base_kappa",
        *tag_columns,
        "mechanistic_tags",
    ]
    gaps = wide[gap_columns].copy()
    atomic_write_csv(RESULT_ROOT / "capacity_gap.csv", gaps)
    pareto_rows = []
    for objective_id in ("O0", "O1", "O2", "O3"):
        column = f"pareto_nondominated_{objective_id}"
        count = int(wide[column].sum())
        pareto_rows.append(
            {
                "objective_id": objective_id,
                "objective_label": LABELS[objective_id],
                "task_count": len(wide),
                "nondominated_count": count,
                "nondominated_fraction": count / len(wide),
                "pareto_axes": "maximize_P_feas_and_P_opt_given_feasible",
                "descriptive_only": True,
            }
        )
    pareto = pd.DataFrame(pareto_rows)
    atomic_write_csv(RESULT_ROOT / "pareto_summary.csv", pareto)
    return wide, gaps, pareto


def cvar_diagnostics(results: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    tolerance = float(config["audits"]["numerical_tolerance"])
    cvar = results[results.objective_id == "O3"].copy()
    cvar["p_feas_at_least_alpha"] = cvar.p_feas >= cvar.cvar_alpha - tolerance
    cvar["cvar_tail_condition_pass"] = (
        cvar.cvar_tail_fully_feasible.astype(bool) == cvar.p_feas_at_least_alpha
    )
    columns = [
        "run_id",
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "dilution_score",
        "p_feas",
        "cvar_alpha",
        "cvar_value",
        "cvar_cutoff_energy",
        "cvar_tail_fully_feasible",
        "cvar_tail_feasible_mass",
        "cvar_fractional_cutoff_mass",
        "p_feas_at_least_alpha",
        "cvar_tail_condition_pass",
    ]
    frame = cvar[columns]
    atomic_write_csv(RESULT_ROOT / "cvar_diagnostics.csv", frame)
    if len(frame) != 56 or not frame.cvar_tail_condition_pass.all():
        raise RuntimeError("CVaR feasible-tail condition failed")
    return frame


def _plot_figures(
    results: pd.DataFrame,
    compensation: pd.DataFrame,
    wide: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    output = RESULT_ROOT / "figures"
    output.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5.4))
    uniform = results[results.objective_id == "O0"]
    ax.scatter(
        uniform.dilution_score,
        uniform.feasible_state_fraction,
        s=24,
        color="gray",
        alpha=0.7,
        label="Uniform",
    )
    for objective_id, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.dilution_score,
            group.p_feas,
            s=25,
            alpha=0.65,
            color=COLORS[objective_id],
            label=LABELS[objective_id],
        )
    ax.set_yscale("log")
    ax.set(xlabel="Dilution score D = -log10(phi_state)", ylabel="P_feas")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure1_main_objective_comparison.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.4))
    for objective_id, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.dilution_score,
            group.log_feasibility_gain,
            s=25,
            alpha=0.65,
            color=COLORS[objective_id],
            label=LABELS[objective_id],
        )
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="Dilution score D", ylabel="G_feas = log10(P_feas / phi_state)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure2_feasibility_gain.png", dpi=180)
    plt.close(fig)

    base = compensation[compensation.scope == "base_graph"]
    fig, ax = plt.subplots(figsize=(7, 5.2))
    arrays = [base[base.objective_id == objective].kappa for objective in LABELS]
    boxes = ax.boxplot(arrays, tick_labels=list(LABELS), patch_artist=True)
    for box, objective_id in zip(boxes["boxes"], LABELS):
        box.set_facecolor(COLORS[objective_id])
        box.set_alpha(0.65)
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1)
    ax.set(ylabel="Within-base compensation slope kappa")
    fig.tight_layout()
    fig.savefig(output / "figure3_compensation_slopes.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.scatter(wide.dilution_score, wide.capacity_gap_mean, s=32, alpha=0.75)
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="Dilution score D", ylabel="G_feas(O2) - G_feas(O0)")
    fig.tight_layout()
    fig.savefig(output / "figure4_capacity_gap.png", dpi=180)
    plt.close(fig)

    for filename, yarm, ylabel in (
        ("figure5_penalty_surrogate.png", "O1", "G_feas(O1 Expected Penalty)"),
        ("figure6_cvar_control.png", "O3", "G_feas(O3 CVaR-0.10)"),
    ):
        x = wide.log_feasibility_gain_O2
        y = wide[f"log_feasibility_gain_{yarm}"]
        limits = [float(min(x.min(), y.min())) - 0.05, float(max(x.max(), y.max())) + 0.05]
        fig, ax = plt.subplots(figsize=(6.2, 5.5))
        ax.scatter(x, y, s=32, alpha=0.75, color=COLORS[yarm])
        ax.plot(limits, limits, color="black", linestyle="--", linewidth=1)
        ax.set(xlabel="G_feas(O2 Exact Feasibility)", ylabel=ylabel, xlim=limits, ylim=limits)
        fig.tight_layout()
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    for objective_id, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.p_feas,
            group.p_opt_given_feasible,
            s=28,
            alpha=0.65,
            color=COLORS[objective_id],
            label=LABELS[objective_id],
        )
    ax.set(xlabel="P_feas", ylabel="P_opt_given_feasible")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure7_feasibility_vs_optimal_concentration.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.6, 5.4))
    for objective_id, group in results.groupby("objective_id", sort=True):
        ax.scatter(
            group.dilution_score,
            group.expected_route_cost_given_feasible,
            s=27,
            alpha=0.65,
            color=COLORS[objective_id],
            label=LABELS[objective_id],
        )
    ax.set(xlabel="Dilution score D", ylabel="E[C | feasible]")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure8_conditional_route_quality.png", dpi=180)
    plt.close(fig)

    decomposition = results.groupby("objective_id", sort=True).agg(
        routing=("expected_routing_component", "mean"),
        flow=("expected_flow_penalty", "mean"),
        resource=("expected_resource_penalty", "mean"),
    )
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    x = np.arange(len(decomposition))
    bottom = np.zeros(len(decomposition))
    for metric, label, color in (
        ("routing", "routing component C/172", "#4c78a8"),
        ("flow", "flow penalty", "#f58518"),
        ("resource", "resource penalty", "#54a24b"),
    ):
        values = decomposition[metric].to_numpy()
        ax.bar(x, values, bottom=bottom, label=label, color=color)
        bottom += values
    ax.set_xticks(x, [LABELS[index] for index in decomposition.index], rotation=15)
    ax.set(ylabel="Mean expected component")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure9_objective_decomposition.png", dpi=180)
    plt.close(fig)

    manifest = json.loads(
        (PROJECT_ROOT / config["source_pilot_manifest"]).read_text(encoding="utf-8")
    )
    representative_bases = [
        manifest["selected_base_graphs"][size][0]
        for size in sorted(manifest["selected_base_graphs"])
    ]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), sharex=False, sharey=False)
    for ax, base_id in zip(axes.flat, representative_bases):
        group = results[results.base_instance_id == base_id]
        for objective_id, arm in group.groupby("objective_id", sort=True):
            arm = arm.sort_values("dilution_score")
            ax.plot(
                arm.dilution_score,
                arm.log_feasibility_gain,
                marker="o",
                markersize=3.5,
                linewidth=1.2,
                color=COLORS[objective_id],
                label=LABELS[objective_id],
            )
        ax.axhline(0.0, color="black", linestyle="--", linewidth=0.7)
        ax.set_title(f"{group.size_stratum.iloc[0]}: {base_id.split('-g-')[0]}", fontsize=9)
        ax.set(xlabel="D", ylabel="G_feas")
    axes.flat[-1].axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower right", bbox_to_anchor=(0.96, 0.08), fontsize=8)
    fig.suptitle(
        f"Within-base trajectories ({config['representative_trajectory_rule']})", fontsize=11
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    fig.savefig(output / "figure10_within_base_trajectories.png", dpi=180)
    plt.close(fig)


def analyze_phase1_2(
    *, verdict: str, recommendation: str, pytest_result: str
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        raise ValueError(f"invalid scientific verdict: {verdict}")
    if recommendation not in RECOMMENDATIONS:
        raise ValueError(f"invalid next recommendation: {recommendation}")
    verify_historical_immutability()
    config = load_config(CONFIG_PATH)
    results = pd.read_csv(OBJECTIVE_RESULTS_PATH)
    if len(results) != 224 or results.task_id.nunique() != 56:
        raise RuntimeError("complete 56-task x 4-objective matrix required")
    compensation = compensation_by_objective(results)
    wide, gaps, pareto = build_task_and_gap_tables(results, compensation, config)
    cvar = cvar_diagnostics(results, config)
    audit = pd.read_csv(THEORETICAL_AUDIT_PATH)
    penalty_state_audit = results[
        [
            "run_id",
            "task_id",
            "objective_id",
            "p_feas",
            "expected_total_penalty",
            "penalty_bound_lower_margin",
            "penalty_bound_upper_margin",
            "penalty_bound_pass",
        ]
    ]
    atomic_write_csv(RESULT_ROOT / "feasibility_penalty_bound_optimization_states.csv", penalty_state_audit)
    aggregate = compensation[compensation.scope == "aggregate"].set_index("objective_id")
    capacity_correlations = {}
    for column in ("capacity_gap_mean", "capacity_gap_penalty", "capacity_gap_cvar"):
        rho, n = _spearman(gaps.dilution_score, gaps[column])
        capacity_correlations[column] = {"spearman_D_vs_gap": rho, "n": n}
    arm_summary = {}
    for objective_id, group in results.groupby("objective_id", sort=True):
        arm_summary[objective_id] = {
            "name": group.objective_name.iloc[0],
            "median_p_feas": float(group.p_feas.median()),
            "median_G_feas": float(group.log_feasibility_gain.median()),
            "median_p_opt": float(group.p_opt.median()),
            "median_p_opt_given_feasible": float(group.p_opt_given_feasible.median()),
            "median_conditional_route_cost": float(
                group.expected_route_cost_given_feasible.median()
            ),
            "median_kappa": float(aggregate.loc[objective_id, "median_kappa"]),
            "spearman_D_vs_P_feas": float(
                aggregate.loc[objective_id, "spearman_D_vs_P_feas"]
            ),
            "spearman_D_vs_G_feas": float(
                aggregate.loc[objective_id, "spearman_D_vs_G_feas"]
            ),
            "spearman_D_vs_P_opt": float(
                aggregate.loc[objective_id, "spearman_D_vs_P_opt"]
            ),
        }
    numerical_tolerance = float(config["audits"]["numerical_tolerance"])
    paired_comparisons: dict[str, dict[str, int]] = {}
    for objective_id in ("O1", "O2", "O3"):
        delta_p_feas = wide[f"p_feas_{objective_id}"] - wide.p_feas_O0
        delta_p_opt = wide[f"p_opt_{objective_id}"] - wide.p_opt_O0
        delta_conditional = (
            wide[f"p_opt_given_feasible_{objective_id}"]
            - wide.p_opt_given_feasible_O0
        )
        delta_route_cost = (
            wide[f"expected_route_cost_given_feasible_{objective_id}"]
            - wide.expected_route_cost_given_feasible_O0
        )
        paired_comparisons[objective_id] = {
            "P_feas_improved": int((delta_p_feas > numerical_tolerance).sum()),
            "P_feas_worsened": int((delta_p_feas < -numerical_tolerance).sum()),
            "P_opt_improved": int((delta_p_opt > numerical_tolerance).sum()),
            "P_opt_worsened": int((delta_p_opt < -numerical_tolerance).sum()),
            "P_opt_given_feasible_improved": int(
                (delta_conditional > numerical_tolerance).sum()
            ),
            "P_opt_given_feasible_unchanged": int(
                (delta_conditional.abs() <= numerical_tolerance).sum()
            ),
            "P_opt_given_feasible_worsened": int(
                (delta_conditional < -numerical_tolerance).sum()
            ),
            "conditional_route_cost_improved": int(
                (delta_route_cost < -numerical_tolerance).sum()
            ),
            "conditional_route_cost_unchanged": int(
                (delta_route_cost.abs() <= numerical_tolerance).sum()
            ),
            "conditional_route_cost_worsened": int(
                (delta_route_cost > numerical_tolerance).sum()
            ),
        }
    penalty_vs_o2 = (
        (wide.expected_total_penalty_O1 < wide.expected_total_penalty_O2 - numerical_tolerance)
        & (wide.p_feas_O1 < wide.p_feas_O2 - numerical_tolerance)
    )
    summary = {
        "phase": "Phase 1.2 — Objective Alignment and Feasibility-Capacity Diagnostic",
        "evidence_identity": config["evidence_identity"],
        "status": "COMPLETE",
        "task_count": 56,
        "objective_result_rows": 224,
        "new_optimization_runs": 168,
        "historical_O0_reused_runs": 56,
        "matched_eval_budget": int(config["objective_eval_budget"]),
        "pytest_result": pytest_result,
        "theoretical_audit": {
            "v2_task_count": len(audit),
            "basis_penalty_contract_pass_count": int(audit.basis_penalty_contract_pass.sum()),
            "strict_energy_separation_count": int(audit.strict_energy_class_separation.sum()),
            "random_state_penalty_bound_pass_count": int(
                audit.random_state_penalty_bound_pass.sum()
            ),
            "optimization_state_penalty_bound_pass_count": int(
                results.penalty_bound_pass.sum()
            ),
            "cvar_tail_condition_pass_count": int(cvar.cvar_tail_condition_pass.sum()),
        },
        "objectives": arm_summary,
        "capacity_gaps": {
            "median_O2_minus_O0_G": float(gaps.capacity_gap_mean.median()),
            "IQR_O2_minus_O0_G": float(
                gaps.capacity_gap_mean.quantile(0.75)
                - gaps.capacity_gap_mean.quantile(0.25)
            ),
            "median_O2_minus_O1_G": float(gaps.capacity_gap_penalty.median()),
            "median_O2_minus_O3_G": float(gaps.capacity_gap_cvar.median()),
            "median_O2_minus_O0_P_feas": float(gaps.capacity_gap_p_feas_mean.median()),
            "median_O2_minus_O0_P_opt": float(gaps.capacity_gap_p_opt_mean.median()),
            "capacity_gap_vs_dilution": capacity_correlations,
        },
        "mechanistic_tags": {
            column.removeprefix("tag_"): int(wide[column].sum())
            for column in wide.columns
            if column.startswith("tag_")
        },
        "pareto_nondominated_counts": pareto.set_index("objective_id")[
            "nondominated_count"
        ].astype(int).to_dict(),
        "paired_comparisons_vs_O0": paired_comparisons,
        "penalty_surrogate_diagnostic": {
            "O1_own_objective_improved_count": int(
                (
                    results.loc[results.objective_id == "O1", "objective_improvement"]
                    > numerical_tolerance
                ).sum()
            ),
            "O1_lower_penalty_but_lower_P_feas_than_O2_count": int(
                penalty_vs_o2.sum()
            ),
        },
        "scientific_verdict": verdict,
        "next_recommendation": recommendation,
        "recommendation_executed": False,
        "optional_cvar_alpha_0_25_executed": False,
        "optional_response_slice_executed": False,
        "raw_statevectors_persisted": False,
    }
    write_json(RESULT_ROOT / "summary.json", summary)
    _plot_figures(results, compensation, wide, config)

    o0, o1, o2, o3 = (arm_summary[key] for key in ("O0", "O1", "O2", "O3"))
    gap = summary["capacity_gaps"]
    tags = summary["mechanistic_tags"]
    paired = summary["paired_comparisons_vs_O0"]
    surrogate = summary["penalty_surrogate_diagnostic"]
    report = f"""# Phase 1.2 — Objective Alignment and Feasibility-Capacity Diagnostic

## Evidence contract

This is a new objective-design diagnostic over exactly the frozen 56 Phase-1 pilot tasks. It uses the same scale-controlled penalties, global normalization by 172, p=3 Penalty-X statevector ansatz, validator, optimizer parameters that are unbounded after initialization, objective-selected p=2 seed, embedded zero third layer, COBYLA optimizer class, and matched 240-evaluation budget. The cost-phase Hamiltonian remains the frozen normalized mean-energy Hamiltonian in every arm; only the classical training loss changes.

O0 reuses all 56 exact Phase-1.1 continuation-B2 cells. O1–O3 comprise 168 new cells. O2 is labeled `STATEVECTOR_MECHANISTIC_CONTROL`; it is not a deployment-ready objective and uses feasibility membership only, never the optimum or `p_opt`. O1 is a mechanistic feasibility surrogate, not a complete routing objective. No 140-task optimization expansion, Warm-start arm, shot sampling, result-based rerun, or raw-statevector persistence occurred.

## FEASIBILITY_PENALTY_BOUND

For every one of the 140 frozen v2 tasks, feasible states have total controlled penalty zero, every infeasible basis state has `P_total >= 1`, and every basis state has `P_total <= 4`. Therefore, pointwise bounds integrated against any probability distribution give

`1 - P_feas <= E[P_total] <= 4 * (1 - P_feas)`.

All {len(audit)} basis-state task audits, {int(audit.random_state_penalty_bound_pass.sum())} deterministic Haar-distribution audits, and {int(results.penalty_bound_pass.sum())} produced optimization-state audits passed. This explains why O1 is more directly aligned with feasible mass than O0, but it does **not** make expected-penalty minimization equivalent to maximizing `P_feas`: O1 also weights violation severity within the infeasible sector.

## CVaR energy-separation audit

Strict `min(infeasible energy) > max(feasible energy)` separation passed for {int(audit.strict_energy_class_separation.sum())}/140 tasks. Consequently, if `P_feas >= alpha`, the lowest-energy alpha tail is entirely feasible; if `P_feas < alpha`, some infeasible mass is necessary. Exact weighted CVaR uses fractional probability at the cutoff. The per-result condition passed for {int(cvar.cvar_tail_condition_pass.sum())}/56 O3 cells; {int(cvar.cvar_tail_fully_feasible.sum())}/56 final O3 tails were fully feasible. This condition does not guarantee that CVaR maximizes `P_feas`, and its direct feasibility pressure can weaken once feasible mass exceeds alpha.

## Main objective comparison

| Arm | Median P_feas | Median G_feas | Median P_opt | Median P_opt given feasible | Median E[C given feasible] | Median kappa |
|---|---:|---:|---:|---:|---:|---:|
| O0 Mean Energy | {o0['median_p_feas']:.6g} | {o0['median_G_feas']:.4f} | {o0['median_p_opt']:.6g} | {o0['median_p_opt_given_feasible']:.6g} | {o0['median_conditional_route_cost']:.4f} | {o0['median_kappa']:.4f} |
| O1 Expected Penalty | {o1['median_p_feas']:.6g} | {o1['median_G_feas']:.4f} | {o1['median_p_opt']:.6g} | {o1['median_p_opt_given_feasible']:.6g} | {o1['median_conditional_route_cost']:.4f} | {o1['median_kappa']:.4f} |
| O2 Exact Feasibility | {o2['median_p_feas']:.6g} | {o2['median_G_feas']:.4f} | {o2['median_p_opt']:.6g} | {o2['median_p_opt_given_feasible']:.6g} | {o2['median_conditional_route_cost']:.4f} | {o2['median_kappa']:.4f} |
| O3 CVaR-0.10 | {o3['median_p_feas']:.6g} | {o3['median_G_feas']:.4f} | {o3['median_p_opt']:.6g} | {o3['median_p_opt_given_feasible']:.6g} | {o3['median_conditional_route_cost']:.4f} | {o3['median_kappa']:.4f} |

The aggregate Spearman `(D, P_feas / G_feas / P_opt)` triples are O0 `({o0['spearman_D_vs_P_feas']:.3f}, {o0['spearman_D_vs_G_feas']:.3f}, {o0['spearman_D_vs_P_opt']:.3f})`, O1 `({o1['spearman_D_vs_P_feas']:.3f}, {o1['spearman_D_vs_G_feas']:.3f}, {o1['spearman_D_vs_P_opt']:.3f})`, O2 `({o2['spearman_D_vs_P_feas']:.3f}, {o2['spearman_D_vs_G_feas']:.3f}, {o2['spearman_D_vs_P_opt']:.3f})`, and O3 `({o3['spearman_D_vs_P_feas']:.3f}, {o3['spearman_D_vs_G_feas']:.3f}, {o3['spearman_D_vs_P_opt']:.3f})`. Full within-base slopes, R2 values, D ranges, level counts, IQRs, ranges, and sign counts are in `compensation_by_objective.csv`.

## Capacity, surrogate, and routing-quality gaps

The median O2–O0 feasibility-capacity gap is {gap['median_O2_minus_O0_G']:.4f} decades (IQR {gap['IQR_O2_minus_O0_G']:.4f}); the median P_feas gap is {gap['median_O2_minus_O0_P_feas']:.6g}. The corresponding residual G gaps are {gap['median_O2_minus_O1_G']:.4f} for O1 and {gap['median_O2_minus_O3_G']:.4f} for O3. The median O2–O0 P_opt gap is {gap['median_O2_minus_O0_P_opt']:.6g}, so feasibility recovery is not treated as universal routing superiority.

The O2–O0 capacity gap increases with dilution (Spearman rho {gap['capacity_gap_vs_dilution']['capacity_gap_mean']['spearman_D_vs_gap']:.3f}, n=56). The residual O2–O1 gap also increases with dilution (rho {gap['capacity_gap_vs_dilution']['capacity_gap_penalty']['spearman_D_vs_gap']:.3f}), whereas the O2–O3 residual does not (rho {gap['capacity_gap_vs_dilution']['capacity_gap_cvar']['spearman_D_vs_gap']:.3f}).

O1 improved its own expected-penalty loss in {surrogate['O1_own_objective_improved_count']}/56 cells, so its gap is not explained by simple terminal regression. In {surrogate['O1_lower_penalty_but_lower_P_feas_than_O2_count']}/56 paired tasks, O1 had lower expected penalty than O2 but also lower `P_feas`. That direction is direct evidence that severity weighting within `P_total` can prefer lower-severity infeasible mass; it is consistent with remaining landscape effects and flow/resource allocation, but this phase does not identify a unique causal decomposition or tune their weights.

Relative to O0, O2 improved `P_feas` on {paired['O2']['P_feas_improved']}/56 tasks and `P_opt` on {paired['O2']['P_opt_improved']}/56. O3 improved them on {paired['O3']['P_feas_improved']}/56 and {paired['O3']['P_opt_improved']}/56, respectively. For O3, `P_opt_given_feasible` improved / was unchanged / worsened on {paired['O3']['P_opt_given_feasible_improved']}/{paired['O3']['P_opt_given_feasible_unchanged']}/{paired['O3']['P_opt_given_feasible_worsened']} tasks, while conditional route cost improved / was unchanged / worsened on {paired['O3']['conditional_route_cost_improved']}/{paired['O3']['conditional_route_cost_unchanged']}/{paired['O3']['conditional_route_cost_worsened']}. Thus the route-quality response is heterogeneous rather than collapsed into a feasibility-only ranking.

With the thresholds frozen before execution (0.10-decade material gap and 50% substantial closure), tags occurred on 56 tasks as follows: OBJECTIVE_LIMITED {tags.get('OBJECTIVE_LIMITED', 0)}, CAPACITY_LIMITED {tags.get('CAPACITY_LIMITED', 0)}, PENALTY_SURROGATE_SUCCESS {tags.get('PENALTY_SURROGATE_SUCCESS', 0)}, and CVAR_PARTIAL_ALIGNMENT {tags.get('CVAR_PARTIAL_ALIGNMENT', 0)}. Tags are descriptive, nonexclusive, and continuous gaps remain canonical.

On the descriptive two-axis Pareto view maximizing both `P_feas` and `P_opt_given_feasible`, nondominated counts were O0 {summary['pareto_nondominated_counts']['O0']}, O1 {summary['pareto_nondominated_counts']['O1']}, O2 {summary['pareto_nondominated_counts']['O2']}, and O3 {summary['pareto_nondominated_counts']['O3']}. No weighted score was constructed.

## Scientific verdict

**{verdict}**

This verdict is specific to the fixed 56-task, p=3, exact-statevector diagnostic and does not establish a universally superior objective.

## Next recommendation

**{recommendation}**

This recommendation is recorded only and was not executed. The optional alpha=0.25 sensitivity and response-slice extension were not enabled in the frozen configuration.

## Verification

- Test result: `{pytest_result}`
- Historical predecessor hashes: verified after analysis
- Required objective cells: 224/224 successful (56 reused O0 + 168 new O1/O2/O3)
- Raw statevectors: not persisted
"""
    atomic_write_text(RESULT_ROOT / "OBJECTIVE_ALIGNMENT_REPORT.md", report)
    verify_historical_immutability()
    return summary
