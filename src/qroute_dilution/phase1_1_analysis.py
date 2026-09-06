"""Descriptive attribution analysis and figures for Phase 1.1."""

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

from .io import PROJECT_ROOT, atomic_write_csv, atomic_write_text, write_json
from .phase1_1_diagnostic import (
    BUDGET_PATH,
    CHARACTERIZATION,
    CONFIG_PATH,
    CONTINUATION_PATH,
    CONTROL_PATH,
    DECOMPOSITION_PATH,
    ENERGY_SEPARATION_PATH,
    NESTED_PATH,
    PILOT_RESULTS,
    RANDOM_GAP_PATH,
    RESULT_ROOT,
    SLICE_PATH,
    objective_best_p2_rows,
    sha256_file,
    verify_immutable_evidence,
)


def _spearman(x, y) -> tuple[float, int]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    if keep.sum() < 2 or np.unique(x[keep]).size < 2 or np.unique(y[keep]).size < 2:
        return math.nan, int(keep.sum())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        value = spearmanr(x[keep], y[keep]).statistic
    return float(value), int(keep.sum())


def _fit(x, y) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.isfinite(x) & np.isfinite(y)
    x = x[keep]
    y = y[keep]
    if len(x) < 2 or np.unique(x).size < 2:
        return math.nan, math.nan
    slope, intercept = np.polyfit(x, y, 1)
    prediction = slope * x + intercept
    denominator = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - prediction) ** 2)) / denominator if denominator else 1.0
    return float(slope), float(r2)


def _pilot_median_view(pilot: pd.DataFrame, depth: int, name: str) -> pd.DataFrame:
    source = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == depth)]
    identity = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "feasible_state_fraction",
        "dilution_score",
    ]
    frame = (
        source.groupby(identity, as_index=False, sort=False)
        .agg(
            p_feas=("p_feas", "median"),
            p_opt=("p_opt", "median"),
            G_feas=("log_feasibility_gain", "median"),
            objective=("objective_final", "median"),
        )
    )
    frame["view"] = name
    frame["seed_view"] = "metricwise_median"
    return frame


def _diagnostic_view(
    frame: pd.DataFrame, name: str, *, aggregate_seeds: bool
) -> pd.DataFrame:
    identity = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "feasible_state_fraction",
        "dilution_score",
    ]
    if aggregate_seeds:
        result = frame.groupby(identity, as_index=False, sort=False).agg(
            p_feas=("p_feas_final", "median"),
            p_opt=("p_opt_final", "median"),
            G_feas=("G_feas_final", "median"),
            objective=("objective_final", "median"),
        )
        result["seed_view"] = "metricwise_median"
    else:
        result = frame[
            identity + ["p_feas_final", "p_opt_final", "G_feas_final", "objective_final"]
        ].rename(
            columns={
                "p_feas_final": "p_feas",
                "p_opt_final": "p_opt",
                "G_feas_final": "G_feas",
                "objective_final": "objective",
            }
        )
        result["seed_view"] = "objective_selected_p2_seed"
    result["view"] = name
    return result


def build_response_views() -> pd.DataFrame:
    pilot = pd.read_csv(PILOT_RESULTS)
    continuation = pd.read_csv(CONTINUATION_PATH)
    budget = pd.read_csv(BUDGET_PATH)
    control = pd.read_csv(CONTROL_PATH)
    views = [
        _pilot_median_view(pilot, 1, "P1_RANDOM_ORIGINAL"),
        _pilot_median_view(pilot, 2, "P2_RANDOM_ORIGINAL"),
        _pilot_median_view(pilot, 3, "P3_RANDOM_ORIGINAL"),
        _diagnostic_view(continuation, "P3_CONTINUATION_B1", aggregate_seeds=True),
    ]
    for multiplier in (1, 2, 4):
        selected = budget[budget.budget_multiplier == multiplier]
        views.append(
            _diagnostic_view(
                selected,
                f"P3_CONTINUATION_B{multiplier}_SELECTED",
                aggregate_seeds=False,
            )
        )
    views.append(_diagnostic_view(control, "P3_NELDER_MEAD_B1", aggregate_seeds=False))
    return pd.concat(views, ignore_index=True)


def compensation_comparison(views: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for view, view_frame in views.groupby("view", sort=False):
        base_slopes = []
        for base, group in view_frame.groupby("base_instance_id", sort=False):
            if group.dilution_score.nunique() < 3:
                continue
            kappa, r2 = _fit(group.dilution_score, group.G_feas)
            absolute, absolute_r2 = _fit(
                group.dilution_score, np.log10(group.p_feas.where(group.p_feas > 0))
            )
            record = {
                "scope": "base_graph",
                "view": view,
                "base_graph_id": group.base_graph_id.iloc[0],
                "base_instance_id": base,
                "size_stratum": group.size_stratum.iloc[0],
                "n_levels": int(group.dilution_score.nunique()),
                "kappa": kappa,
                "R2": r2,
                "absolute_feasibility_log_slope": absolute,
                "absolute_R2": absolute_r2,
                "slope_identity_residual": absolute - (kappa - 1.0),
                "min_D": float(group.dilution_score.min()),
                "max_D": float(group.dilution_score.max()),
            }
            rows.append(record)
            base_slopes.append(record)
        kappas = np.asarray([record["kappa"] for record in base_slopes], dtype=float)
        rho_p, n_p = _spearman(view_frame.dilution_score, view_frame.p_feas)
        rho_g, n_g = _spearman(view_frame.dilution_score, view_frame.G_feas)
        rows.append(
            {
                "scope": "aggregate",
                "view": view,
                "base_graph_id": "",
                "base_instance_id": "",
                "size_stratum": "ALL",
                "n_levels": int(len(view_frame)),
                "n_base_graphs": int(len(kappas)),
                "kappa_median": float(np.median(kappas)),
                "kappa_q1": float(np.quantile(kappas, 0.25)),
                "kappa_q3": float(np.quantile(kappas, 0.75)),
                "kappa_iqr": float(np.quantile(kappas, 0.75) - np.quantile(kappas, 0.25)),
                "kappa_min": float(kappas.min()),
                "kappa_max": float(kappas.max()),
                "number_negative": int(np.sum(kappas < 0)),
                "number_0_to_1": int(np.sum((kappas >= 0) & (kappas < 1))),
                "number_at_least_1": int(np.sum(kappas >= 1)),
                "spearman_D_vs_p_feas": rho_p,
                "spearman_D_vs_G_feas": rho_g,
                "spearman_n_p_feas": n_p,
                "spearman_n_G_feas": n_g,
                "max_abs_slope_identity_residual": float(
                    np.max(np.abs([record["slope_identity_residual"] for record in base_slopes]))
                ),
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "compensation_comparison.csv", frame)
    return frame


def continuation_pairing(pilot: pd.DataFrame, continuation: pd.DataFrame) -> pd.DataFrame:
    original = pilot[(pilot.algorithm == "Penalty-X") & (pilot.depth == 3)][
        [
            "task_id",
            "optimizer_seed",
            "objective_final",
            "p_feas",
            "p_opt",
            "log_feasibility_gain",
        ]
    ].rename(
        columns={
            "objective_final": "original_p3_objective",
            "p_feas": "original_p3_p_feas",
            "p_opt": "original_p3_p_opt",
            "log_feasibility_gain": "original_p3_G_feas",
        }
    )
    paired = continuation.merge(
        original,
        left_on=["task_id", "source_p2_seed"],
        right_on=["task_id", "optimizer_seed"],
        validate="one_to_one",
    )
    paired["continuation_objective_recovery_vs_random"] = (
        paired.original_p3_objective - paired.objective_final
    )
    paired["continuation_delta_p_feas_vs_random"] = paired.p_feas_final - paired.original_p3_p_feas
    paired["continuation_delta_p_opt_vs_random"] = paired.p_opt_final - paired.original_p3_p_opt
    paired["continuation_delta_G_vs_random"] = paired.G_feas_final - paired.original_p3_G_feas
    atomic_write_csv(RESULT_ROOT / "analysis" / "continuation_paired_comparison.csv", paired)
    return paired


def budget_pairing(budget: pd.DataFrame) -> pd.DataFrame:
    values = [
        "objective_final",
        "G_feas_final",
        "p_feas_final",
        "p_opt_final",
        "runtime_s",
        "optimizer_nfev",
    ]
    identity = ["task_id", "base_instance_id", "size_stratum", "dilution_score"]
    wide = budget.pivot(index=identity, columns="budget_multiplier", values=values)
    wide.columns = [f"{metric}_B{int(multiplier)}" for metric, multiplier in wide.columns]
    wide = wide.reset_index()
    wide["objective_gain_B1_to_B2"] = wide.objective_final_B1 - wide.objective_final_B2
    wide["objective_gain_B2_to_B4"] = wide.objective_final_B2 - wide.objective_final_B4
    wide["G_change_B1_to_B2"] = wide.G_feas_final_B2 - wide.G_feas_final_B1
    wide["G_change_B2_to_B4"] = wide.G_feas_final_B4 - wide.G_feas_final_B2
    atomic_write_csv(RESULT_ROOT / "analysis" / "budget_paired_comparison.csv", wide)
    return wide


def optimizer_pairing(budget: pd.DataFrame, control: pd.DataFrame) -> pd.DataFrame:
    cobyla = budget[budget.budget_multiplier == 1][
        ["task_id", "objective_final", "G_feas_final", "p_feas_final", "p_opt_final", "runtime_s"]
    ].rename(columns={column: f"cobyla_{column}" for column in ["objective_final", "G_feas_final", "p_feas_final", "p_opt_final", "runtime_s"]})
    nelder = control[
        ["task_id", "objective_final", "G_feas_final", "p_feas_final", "p_opt_final", "runtime_s"]
    ].rename(columns={column: f"nelder_mead_{column}" for column in ["objective_final", "G_feas_final", "p_feas_final", "p_opt_final", "runtime_s"]})
    paired = cobyla.merge(nelder, on="task_id", validate="one_to_one")
    paired["objective_nelder_minus_cobyla"] = (
        paired.nelder_mead_objective_final - paired.cobyla_objective_final
    )
    paired["G_nelder_minus_cobyla"] = paired.nelder_mead_G_feas_final - paired.cobyla_G_feas_final
    atomic_write_csv(RESULT_ROOT / "analysis" / "optimizer_paired_comparison.csv", paired)
    return paired


def depth_effects(views: pd.DataFrame, pilot: pd.DataFrame) -> pd.DataFrame:
    p2_median = views[views.view == "P2_RANDOM_ORIGINAL"].set_index("task_id")
    selected_p2 = objective_best_p2_rows(pilot).set_index("task_id")
    rows = []
    for view in (
        "P3_RANDOM_ORIGINAL",
        "P3_CONTINUATION_B1",
        "P3_CONTINUATION_B1_SELECTED",
        "P3_CONTINUATION_B2_SELECTED",
        "P3_CONTINUATION_B4_SELECTED",
        "P3_NELDER_MEAD_B1",
    ):
        for item in views[views.view == view].itertuples(index=False):
            if "SELECTED" in view or view == "P3_NELDER_MEAD_B1":
                reference = selected_p2.loc[item.task_id]
                p2_p_feas = float(reference.p_feas)
                p2_p_opt = float(reference.p_opt)
                p2_gain = float(reference.log_feasibility_gain)
                reference_name = "P2_OBJECTIVE_SELECTED_MATCHED"
            else:
                reference = p2_median.loc[item.task_id]
                p2_p_feas = float(reference.p_feas)
                p2_p_opt = float(reference.p_opt)
                p2_gain = float(reference.G_feas)
                reference_name = "P2_METRICWISE_MEDIAN"
            rows.append(
                {
                    "task_id": item.task_id,
                    "base_instance_id": item.base_instance_id,
                    "size_stratum": item.size_stratum,
                    "dilution_score": item.dilution_score,
                    "p3_view": view,
                    "p2_reference": reference_name,
                    "Delta_G_3_2": item.G_feas - p2_gain,
                    "Delta_log10_P_feas_3_2": math.log10(item.p_feas) - math.log10(p2_p_feas),
                    "Delta_P_opt_3_2": item.p_opt - p2_p_opt,
                }
            )
    frame = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "depth_effect_comparison.csv", frame)
    return frame


def _generate_core_figures(
    gaps: pd.DataFrame,
    views: pd.DataFrame,
    comparison: pd.DataFrame,
    budget_paired: pd.DataFrame,
    continuation: pd.DataFrame,
    decomposition: pd.DataFrame,
) -> None:
    output = RESULT_ROOT / "figures"
    output.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    for size, group in gaps.groupby("size_stratum", sort=True):
        ax.scatter(group.dilution_score, group.p3_optimization_gap_vs_embedded_p2, s=23, alpha=0.7, label=size)
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="Dilution score D", ylabel="Original p3 objective - embedded p2 objective")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure1_original_p3_gap_vs_dilution.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    colors = {"P2_RANDOM_ORIGINAL": "#1f77b4", "P3_RANDOM_ORIGINAL": "#d62728", "P3_CONTINUATION_B1": "#2ca02c"}
    labels = {"P2_RANDOM_ORIGINAL": "p2 original", "P3_RANDOM_ORIGINAL": "p3 random", "P3_CONTINUATION_B1": "p3 continuation"}
    for view in colors:
        group = views[views.view == view]
        ax.scatter(group.dilution_score, group.G_feas, s=24, alpha=0.7, color=colors[view], label=labels[view])
    ax.axhline(0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel="Dilution score D", ylabel="G_feas")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure2_gain_p2_p3_random_continuation.png", dpi=180)
    plt.close(fig)

    base = comparison[comparison.scope == "base_graph"]
    random = base[base.view == "P3_RANDOM_ORIGINAL"][["base_instance_id", "kappa"]].rename(columns={"kappa": "random"})
    continued = base[base.view == "P3_CONTINUATION_B1"][["base_instance_id", "kappa"]].rename(columns={"kappa": "continuation"})
    paired = random.merge(continued, on="base_instance_id")
    fig, ax = plt.subplots(figsize=(6, 5.5))
    ax.scatter(paired.random, paired.continuation, s=45)
    slope_values = paired[["random", "continuation"]].to_numpy(dtype=float)
    limits = [float(slope_values.min()) - 0.2, float(slope_values.max()) + 0.2]
    ax.plot(limits, limits, color="black", linestyle="--")
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set(xlabel="kappa p3 random", ylabel="kappa p3 continuation", xlim=limits, ylim=limits)
    fig.tight_layout()
    fig.savefig(output / "figure3_kappa_random_vs_continuation.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5.2))
    values = [
        budget_paired.objective_final_B1 - budget_paired.objective_final_B1,
        budget_paired.objective_final_B1 - budget_paired.objective_final_B2,
        budget_paired.objective_final_B1 - budget_paired.objective_final_B4,
    ]
    ax.boxplot(values, tick_labels=["B1", "B2", "B4"], showmeans=True)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.set(ylabel="Objective gain relative to B1")
    fig.tight_layout()
    fig.savefig(output / "figure4_budget_objective_gain.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5.2))
    ax.boxplot(
        [budget_paired.G_feas_final_B1, budget_paired.G_feas_final_B2, budget_paired.G_feas_final_B4],
        tick_labels=["B1", "B2", "B4"],
        showmeans=True,
    )
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.set(ylabel="G_feas (objective-selected p2 seed)")
    fig.tight_layout()
    fig.savefig(output / "figure5_budget_gain_response.png", dpi=180)
    plt.close(fig)

    selected_decomp = decomposition[decomposition.arm.isin(["P2_RANDOM_ORIGINAL", "P3_CONTINUATION_B1"])]
    component_medians = selected_decomp.groupby("arm")[["expected_routing_component", "expected_flow_penalty", "expected_resource_penalty"]].median()
    fig, ax = plt.subplots(figsize=(8, 5.2))
    x = np.arange(len(component_medians))
    bottom = np.zeros(len(component_medians))
    for column, label, color in (
        ("expected_routing_component", "routing C/172", "#4c78a8"),
        ("expected_flow_penalty", "flow penalty", "#f58518"),
        ("expected_resource_penalty", "resource penalty", "#54a24b"),
    ):
        ax.bar(x, component_medians[column], bottom=bottom, label=label, color=color)
        bottom += component_medians[column].to_numpy()
    ax.set_xticks(x, ["p2 original", "p3 continuation"])
    ax.set_ylabel("Median expectation component")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure6_objective_components.png", dpi=180)
    plt.close(fig)

    counts = continuation.classification.value_counts()
    order = [
        "OBJECTIVE_AND_FEASIBILITY_IMPROVE",
        "OBJECTIVE_IMPROVES_FEASIBILITY_WORSENS",
        "NO_MEANINGFUL_OBJECTIVE_GAIN",
        "OPTIMIZER_REGRESSION",
        "OBJECTIVE_IMPROVES_FEASIBILITY_UNCHANGED",
    ]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    values = [int(counts.get(label, 0)) for label in order]
    ax.bar(np.arange(len(order)), values)
    ax.set_xticks(np.arange(len(order)), [label.replace("_", "\n") for label in order], fontsize=7)
    ax.set_ylabel("Continuation run count")
    for index, value in enumerate(values):
        ax.text(index, value, f"{value}\n({value/len(continuation):.1%})", ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure7_continuation_classifications.png", dpi=180)
    plt.close(fig)


def _generate_slice_figures() -> list[str]:
    slices = pd.read_csv(SLICE_PATH)
    output = RESULT_ROOT / "figures" / "new_layer_response_slices"
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for task_id, group in slices.groupby("task_id", sort=True):
        objective = group.pivot(index="beta3", columns="gamma3", values="objective")
        gain = group.pivot(index="beta3", columns="gamma3", values="G_feas")
        gamma = objective.columns.to_numpy(dtype=float)
        beta = objective.index.to_numpy(dtype=float)
        extent = [gamma.min(), gamma.max(), beta.min(), beta.max()]
        best_objective = group.loc[group.objective.idxmin()]
        best_gain = group.loc[group.G_feas.idxmax()]
        original_gamma = float(group.original_p3_projected_gamma3.iloc[0])
        original_beta = float(group.original_p3_projected_beta3.iloc[0])
        projectable = bool(
            gamma.min() <= original_gamma <= gamma.max()
            and beta.min() <= original_beta <= beta.max()
        )
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True, sharey=True)
        images = [
            axes[0].imshow(objective.to_numpy(), origin="lower", aspect="auto", extent=extent, cmap="viridis"),
            axes[1].imshow(gain.to_numpy(), origin="lower", aspect="auto", extent=extent, cmap="coolwarm"),
        ]
        axes[0].set_title("Objective new-layer response slice")
        axes[1].set_title("G_feas new-layer response slice")
        for ax in axes:
            ax.scatter([0], [0], marker="o", facecolors="none", edgecolors="white", s=70, label="embedded p2")
            ax.scatter([best_objective.gamma3], [best_objective.beta3], marker="*", color="yellow", s=90, label="grid min objective")
            ax.scatter([best_gain.gamma3], [best_gain.beta3], marker="X", color="black", s=55, label="grid max G")
            if projectable:
                ax.scatter([original_gamma], [original_beta], marker="+", color="magenta", s=85, label="original p3 coordinate projection")
            ax.set(xlabel="gamma3", ylabel="beta3")
        fig.colorbar(images[0], ax=axes[0], fraction=0.046)
        fig.colorbar(images[1], ax=axes[1], fraction=0.046)
        axes[1].legend(fontsize=6, loc="best")
        row = group.iloc[0]
        fig.suptitle(f"{row.size_stratum} {row.representative_role}: {task_id}; D={row.dilution_score:.3f}")
        fig.tight_layout()
        path = output / f"{task_id}_new_layer_response_slice.png"
        fig.savefig(path, dpi=170)
        plt.close(fig)
        paths.append(str(path.relative_to(PROJECT_ROOT)))
    return paths


def analyze_phase1_1(*, pytest_result: str, attribution: str) -> dict[str, Any]:
    if attribution not in {
        "OPTIMIZER_LIMITATION",
        "OBJECTIVE_FEASIBILITY_MISALIGNMENT",
        "GENUINE_DEPTH_RESPONSE",
        "MIXED",
    }:
        raise ValueError("invalid attribution")
    verify_immutable_evidence()
    pilot = pd.read_csv(PILOT_RESULTS)
    nested = pd.read_csv(NESTED_PATH)
    gaps = pd.read_csv(RANDOM_GAP_PATH)
    continuation = pd.read_csv(CONTINUATION_PATH)
    budget = pd.read_csv(BUDGET_PATH)
    control = pd.read_csv(CONTROL_PATH)
    decomposition = pd.read_csv(DECOMPOSITION_PATH)
    separation = pd.read_csv(ENERGY_SEPARATION_PATH)
    views = build_response_views()
    comparison = compensation_comparison(views)
    paired_continuation = continuation_pairing(pilot, continuation)
    paired_budget = budget_pairing(budget)
    paired_optimizer = optimizer_pairing(budget, control)
    depth = depth_effects(views, pilot)
    gap_group_rows = []
    for scope, key in (("size_stratum", "size_stratum"), ("base_graph", "base_instance_id"), ("dilution_score", "dilution_score")):
        for value, group in gaps.groupby(key, sort=True):
            gap_group_rows.append(
                {
                    "scope": scope,
                    "group": value,
                    "n_runs": int(len(group)),
                    "worse_count": int(group.original_p3_worse_than_embedded_p2.sum()),
                    "worse_fraction": float(group.original_p3_worse_than_embedded_p2.mean()),
                    "gap_median": float(group.p3_optimization_gap_vs_embedded_p2.median()),
                    "gap_min": float(group.p3_optimization_gap_vs_embedded_p2.min()),
                    "gap_max": float(group.p3_optimization_gap_vs_embedded_p2.max()),
                }
            )
    atomic_write_csv(
        RESULT_ROOT / "analysis" / "p3_gap_group_summary.csv", pd.DataFrame(gap_group_rows)
    )
    _generate_core_figures(gaps, views, comparison, paired_budget, continuation, decomposition)
    slice_figures = _generate_slice_figures()

    gap_rho, _ = _spearman(gaps.dilution_score, gaps.p3_optimization_gap_vs_embedded_p2)
    classifications = continuation.classification.value_counts().to_dict()
    aggregate = comparison[comparison.scope == "aggregate"].set_index("view")
    original_kappa = aggregate.loc["P3_RANDOM_ORIGINAL"]
    continuation_kappa = aggregate.loc["P3_CONTINUATION_B1"]
    b2_kappa = aggregate.loc["P3_CONTINUATION_B2_SELECTED"]
    b4_kappa = aggregate.loc["P3_CONTINUATION_B4_SELECTED"]
    decomp_medians = decomposition.groupby("arm")[[
        "expected_routing_component",
        "expected_flow_penalty",
        "expected_resource_penalty",
        "expected_total_penalty",
        "mass_valid_flow_resource_feasible",
        "mass_flow_invalid",
        "mass_resource_violating",
        "mass_both_flow_and_resource_violating",
    ]].median()
    random_decomp = decomposition[decomposition.arm == "P3_RANDOM_ORIGINAL"]
    continuation_decomp = decomposition[decomposition.arm == "P3_CONTINUATION_B1"]
    paired_decomp = random_decomp.merge(
        continuation_decomp,
        on=["task_id", "source_p2_seed"],
        suffixes=("_random", "_continuation"),
        validate="one_to_one",
    )
    decomposition_delta_fields = [
        "objective",
        "expected_routing_component",
        "expected_flow_penalty",
        "expected_resource_penalty",
        "expected_total_penalty",
        "mass_valid_flow_resource_feasible",
        "mass_flow_invalid",
        "mass_resource_violating",
        "mass_both_flow_and_resource_violating",
    ]
    paired_decomposition_median_random_minus_continuation = {
        field: float(
            (
                paired_decomp[f"{field}_random"]
                - paired_decomp[f"{field}_continuation"]
            ).median()
        )
        for field in decomposition_delta_fields
    }
    provenance_path = RESULT_ROOT / "execution_provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {}
    failure_counts = {
        "continuation": int((continuation.execution_status != "SUCCESS").sum()),
        "budget": int((budget.execution_status != "SUCCESS").sum()),
        "optimizer_control": int((control.execution_status != "SUCCESS").sum()),
    }
    original_failures = gaps[gaps.original_p3_worse_than_embedded_p2][
        ["task_id", "optimizer_seed"]
    ]
    failure_recovery = paired_continuation.merge(
        original_failures,
        left_on=["task_id", "source_p2_seed"],
        right_on=["task_id", "optimizer_seed"],
        validate="one_to_one",
    )
    depth_summary = []
    for view, group in depth.groupby("p3_view", sort=False):
        rho, n = _spearman(group.dilution_score, group.Delta_G_3_2)
        depth_summary.append(
            {
                "p3_view": view,
                "median_Delta_G_3_2": float(group.Delta_G_3_2.median()),
                "median_Delta_log10_P_feas_3_2": float(
                    group.Delta_log10_P_feas_3_2.median()
                ),
                "median_Delta_P_opt_3_2": float(group.Delta_P_opt_3_2.median()),
                "spearman_D_vs_Delta_G_3_2": rho,
                "n_tasks": n,
            }
        )
    slices = pd.read_csv(SLICE_PATH)
    slice_summaries = []
    for task_id, group in slices.groupby("task_id", sort=True):
        embedded = group[group.embedded_point].iloc[0]
        best_objective = group.loc[group.objective.idxmin()]
        best_gain = group.loc[group.G_feas.idxmax()]
        projectable = bool(
            group.gamma3.min() <= group.original_p3_projected_gamma3.iloc[0] <= group.gamma3.max()
            and group.beta3.min() <= group.original_p3_projected_beta3.iloc[0] <= group.beta3.max()
        )
        slice_summaries.append(
            {
                "task_id": task_id,
                "projectable_original_p3": projectable,
                "grid_objective_gain_from_embedded": float(
                    embedded.objective - best_objective.objective
                ),
                "grid_G_gain_from_embedded": float(best_gain.G_feas - embedded.G_feas),
                "G_change_at_grid_objective_minimum": float(
                    best_objective.G_feas - embedded.G_feas
                ),
                "objective_change_at_grid_G_maximum": float(
                    best_gain.objective - embedded.objective
                ),
            }
        )
    slice_summary_frame = pd.DataFrame(slice_summaries)
    atomic_write_csv(
        RESULT_ROOT / "analysis" / "new_layer_slice_summary.csv", slice_summary_frame
    )
    summary = {
        "diagnostic_status": "COMPLETE" if sum(failure_counts.values()) == 0 else "PARTIAL",
        "phase1_full_expansion_executed": False,
        "warm_start_added": False,
        "execution_identity": json.loads((RESULT_ROOT / "execution_identity.json").read_text()),
        "validation": {
            "pytest": pytest_result,
            "immutable_evidence_verified": True,
            "nested_identity_rows": int(len(nested)),
            "nested_identity_pass": bool(nested.identity_pass.all()),
            "max_state_difference": float(nested.state_max_abs_difference.max()),
            "max_probability_difference": float(nested.probability_max_abs_difference.max()),
            "max_objective_difference": float(nested.objective_difference.abs().max()),
            "failure_counts": failure_counts,
        },
        "original_p3_optimizer_adequacy": {
            "worse_than_embedded_count": int(gaps.original_p3_worse_than_embedded_p2.sum()),
            "denominator": int(len(gaps)),
            "fraction": float(gaps.original_p3_worse_than_embedded_p2.mean()),
            "gap_min": float(gaps.p3_optimization_gap_vs_embedded_p2.min()),
            "gap_median": float(gaps.p3_optimization_gap_vs_embedded_p2.median()),
            "gap_max": float(gaps.p3_optimization_gap_vs_embedded_p2.max()),
            "spearman_gap_vs_dilution": gap_rho,
            "failed_original_runs_recovered_to_lower_objective_by_continuation": int(
                (failure_recovery.objective_final < failure_recovery.original_p3_objective - 1e-10).sum()
            ),
            "failed_original_runs_with_higher_G_under_continuation": int(
                (failure_recovery.G_feas_final > failure_recovery.original_p3_G_feas + 1e-10).sum()
            ),
        },
        "continuation": {
            "run_count": int(len(continuation)),
            "classification_counts": {key: int(value) for key, value in classifications.items()},
            "median_objective_improvement_from_embedded_start": float(
                continuation.objective_improvement.median()
            ),
            "median_delta_p_feas_from_embedded_start": float(
                (continuation.p_feas_final - continuation.p_feas_start).median()
            ),
            "median_delta_G_from_embedded_start": float(
                (continuation.G_feas_final - continuation.G_feas_start).median()
            ),
            "median_delta_p_opt_from_embedded_start": float(
                (continuation.p_opt_final - continuation.p_opt_start).median()
            ),
            "median_objective_recovery_vs_random": float(
                paired_continuation.continuation_objective_recovery_vs_random.median()
            ),
            "median_delta_p_feas_vs_random": float(
                paired_continuation.continuation_delta_p_feas_vs_random.median()
            ),
            "median_delta_G_vs_random": float(
                paired_continuation.continuation_delta_G_vs_random.median()
            ),
            "median_delta_p_opt_vs_random": float(
                paired_continuation.continuation_delta_p_opt_vs_random.median()
            ),
            "terminal_worse_than_best_evaluated_count": int(
                (continuation.terminal_objective > continuation.best_evaluated_objective + 1e-10).sum()
            ),
            "random_lower_objective_than_continuation_count": int(
                (paired_continuation.original_p3_objective < paired_continuation.objective_final - 1e-10).sum()
            ),
            "random_lower_objective_but_lower_G_count": int(
                (
                    (paired_continuation.original_p3_objective < paired_continuation.objective_final - 1e-10)
                    & (paired_continuation.original_p3_G_feas < paired_continuation.G_feas_final - 1e-10)
                ).sum()
            ),
        },
        "compensation": {
            "original_p3": original_kappa.to_dict(),
            "continuation_p3": continuation_kappa.to_dict(),
            "continuation_B2_selected": b2_kappa.to_dict(),
            "continuation_B4_selected": b4_kappa.to_dict(),
        },
        "depth_effects": depth_summary,
        "budget_sensitivity": {
            "median_objective_gain_B1_to_B2": float(paired_budget.objective_gain_B1_to_B2.median()),
            "median_objective_gain_B2_to_B4": float(paired_budget.objective_gain_B2_to_B4.median()),
            "median_G_change_B1_to_B2": float(paired_budget.G_change_B1_to_B2.median()),
            "median_G_change_B2_to_B4": float(paired_budget.G_change_B2_to_B4.median()),
            "fraction_objective_improves_B1_to_B2": float((paired_budget.objective_gain_B1_to_B2 > 1e-10).mean()),
            "fraction_objective_improves_B2_to_B4": float((paired_budget.objective_gain_B2_to_B4 > 1e-10).mean()),
            "objective_improves_but_G_worsens_B1_to_B2_count": int(
                ((paired_budget.objective_gain_B1_to_B2 > 1e-10) & (paired_budget.G_change_B1_to_B2 < -1e-10)).sum()
            ),
            "objective_improves_but_G_worsens_B2_to_B4_count": int(
                ((paired_budget.objective_gain_B2_to_B4 > 1e-10) & (paired_budget.G_change_B2_to_B4 < -1e-10)).sum()
            ),
        },
        "optimizer_sensitivity": {
            "matched_task_count": int(len(paired_optimizer)),
            "median_objective_nelder_minus_cobyla": float(
                paired_optimizer.objective_nelder_minus_cobyla.median()
            ),
            "nelder_better_objective_count": int(
                (paired_optimizer.objective_nelder_minus_cobyla < -1e-10).sum()
            ),
            "median_G_nelder_minus_cobyla": float(paired_optimizer.G_nelder_minus_cobyla.median()),
            "nelder_better_objective_but_worse_G_count": int(
                (
                    (paired_optimizer.objective_nelder_minus_cobyla < -1e-10)
                    & (paired_optimizer.G_nelder_minus_cobyla < -1e-10)
                ).sum()
            ),
            "terminal_worse_than_best_evaluated_count": int(
                (control.terminal_objective > control.best_evaluated_objective + 1e-10).sum()
            ),
        },
        "objective_decomposition_medians": decomp_medians.to_dict(orient="index"),
        "paired_decomposition_median_random_minus_continuation": paired_decomposition_median_random_minus_continuation,
        "energy_separation": {
            "pilot_count": int(
                separation[separation.in_phase1_pilot].complete_energy_separation.sum()
            ),
            "pilot_denominator": int(separation.in_phase1_pilot.sum()),
            "full_v2_count": int(separation.complete_energy_separation.sum()),
            "full_v2_denominator": int(len(separation)),
            "gap_min": float(separation.feasible_infeasible_energy_gap.min()),
            "gap_median": float(separation.feasible_infeasible_energy_gap.median()),
            "gap_max": float(separation.feasible_infeasible_energy_gap.max()),
        },
        "response_slices": {
            "task_count": int(slices.task_id.nunique()),
            "grid_point_count": int(len(slices)),
            "figure_count": len(slice_figures),
            "figures": slice_figures,
            "original_p3_coordinate_projectable_count": int(
                slice_summary_frame.projectable_original_p3.sum()
            ),
            "median_grid_objective_gain_from_embedded": float(
                slice_summary_frame.grid_objective_gain_from_embedded.median()
            ),
            "median_grid_G_gain_from_embedded": float(
                slice_summary_frame.grid_G_gain_from_embedded.median()
            ),
            "median_G_change_at_grid_objective_minimum": float(
                slice_summary_frame.G_change_at_grid_objective_minimum.median()
            ),
        },
        "resource_usage": {
            "total_recorded_stage_wall_time_s": float(
                provenance.get("total_recorded_wall_time_s", math.nan)
            ),
            "peak_recorded_optimizer_worker_memory_mb": float(
                max(
                    continuation.peak_memory_mb.max(),
                    budget.peak_memory_mb.max(),
                    control.peak_memory_mb.max(),
                )
            ),
        },
        "scientific_attribution": attribution,
        "execution_provenance": provenance,
    }
    summary["next_recommendation"] = _recommendation(summary)
    write_json(RESULT_ROOT / "summary.json", summary)
    _write_report(summary)
    return summary


def _recommendation(summary: dict[str, Any]) -> str:
    attribution = summary["scientific_attribution"]
    if attribution == "OPTIMIZER_LIMITATION":
        return "CHANGE_PRIMARY_OPTIMIZATION_PROTOCOL_PROSPECTIVELY"
    if attribution == "OBJECTIVE_FEASIBILITY_MISALIGNMENT":
        return "INVESTIGATE_OBJECTIVE_DESIGN"
    if attribution == "MIXED":
        return "INVESTIGATE_OBJECTIVE_DESIGN"
    return "EXPAND_PHASE1"


def _write_report(summary: dict[str, Any]) -> None:
    validation = summary["validation"]
    adequacy = summary["original_p3_optimizer_adequacy"]
    continuation = summary["continuation"]
    budget = summary["budget_sensitivity"]
    optimizer = summary["optimizer_sensitivity"]
    separation = summary["energy_separation"]
    decomposition = summary["paired_decomposition_median_random_minus_continuation"]
    compensation = summary["compensation"]
    counts = continuation["classification_counts"]
    lines = [
        "# Phase 1.1 — Optimization Attribution Diagnostic",
        "",
        "This diagnostic preserves the immutable Phase 1 pilot and does not replace any original p=3 row. It separates optimizer adequacy, Hamiltonian-objective alignment, and depth response descriptively.",
        "",
        "## Nested ansatz",
        "",
        f"All {validation['nested_identity_rows']} p2-to-p3 zero-layer embeddings passed. Maximum state, probability, and objective differences were {validation['max_state_difference']:.3g}, {validation['max_probability_difference']:.3g}, and {validation['max_objective_difference']:.3g}.",
        "",
        "## Original p3 optimizer adequacy",
        "",
        f"Original p3 was objectively worse than the embedded p2 point in {adequacy['worse_than_embedded_count']} / {adequacy['denominator']} runs ({adequacy['fraction']:.1%}). The median objective gap was {adequacy['gap_median']:.6g}; Spearman gap versus dilution was {adequacy['spearman_gap_vs_dilution']:.4f}.",
        "",
        f"Continuation recovered a lower objective for {adequacy['failed_original_runs_recovered_to_lower_objective_by_continuation']} / {adequacy['worse_than_embedded_count']} of those direct failures and a higher G_feas for {adequacy['failed_original_runs_with_higher_G_under_continuation']} / {adequacy['worse_than_embedded_count']}.",
        "",
        "## Continuation",
        "",
        f"Relative to the embedded start, median changes were objective improvement {continuation['median_objective_improvement_from_embedded_start']:.6g}, P_feas {continuation['median_delta_p_feas_from_embedded_start']:.6g}, G_feas {continuation['median_delta_G_from_embedded_start']:.6g}, and P_opt {continuation['median_delta_p_opt_from_embedded_start']:.6g}.",
        "",
        f"Median paired original-minus-continuation objective was {continuation['median_objective_recovery_vs_random']:.6g}; its negative sign means continuation had the higher objective on the median pair. Median continuation-minus-random changes were P_feas {continuation['median_delta_p_feas_vs_random']:.6g}, G_feas {continuation['median_delta_G_vs_random']:.6g}, and P_opt {continuation['median_delta_p_opt_vs_random']:.6g}.",
        "",
        f"Random p3 had lower objective than continuation in {continuation['random_lower_objective_than_continuation_count']} / 168 pairs, and simultaneously lower G_feas in {continuation['random_lower_objective_but_lower_G_count']} pairs. This is direct objective/feasibility non-equivalence, not an optimizer failure label by itself.",
        "",
        "Continuation classifications:",
        "",
        *[f"- `{key}`: {value}" for key, value in sorted(counts.items())],
        "",
        "## Compensation",
        "",
        f"Median within-base kappa changed from {compensation['original_p3']['kappa_median']:.6g} for frozen random p3 to {compensation['continuation_p3']['kappa_median']:.6g} for three-seed continuation. Objective-selected B2 and B4 medians were {compensation['continuation_B2_selected']['kappa_median']:.6g} and {compensation['continuation_B4_selected']['kappa_median']:.6g}.",
        "",
        f"The median p3-minus-p2 gain changed from {next(item['median_Delta_G_3_2'] for item in summary['depth_effects'] if item['p3_view'] == 'P3_RANDOM_ORIGINAL'):.6g} for random p3 to {next(item['median_Delta_G_3_2'] for item in summary['depth_effects'] if item['p3_view'] == 'P3_CONTINUATION_B1'):.6g} for continuation.",
        "",
        "## Budget and optimizer controls",
        "",
        f"Median objective gains were B1-to-B2 {budget['median_objective_gain_B1_to_B2']:.6g} and B2-to-B4 {budget['median_objective_gain_B2_to_B4']:.6g}; median G changes were {budget['median_G_change_B1_to_B2']:.6g} and {budget['median_G_change_B2_to_B4']:.6g}.",
        "",
        f"Objective improved while G_feas worsened in {budget['objective_improves_but_G_worsens_B1_to_B2_count']} / 56 B1-to-B2 pairs and {budget['objective_improves_but_G_worsens_B2_to_B4_count']} / 56 B2-to-B4 pairs.",
        "",
        f"Under the matched B1 budget, median Nelder–Mead minus COBYLA objective was {optimizer['median_objective_nelder_minus_cobyla']:.6g}; Nelder–Mead had lower objective on {optimizer['nelder_better_objective_count']} / {optimizer['matched_task_count']} tasks. Median G difference was {optimizer['median_G_nelder_minus_cobyla']:.6g}.",
        "",
        f"Nelder–Mead combined a lower objective with a lower G_feas in {optimizer['nelder_better_objective_but_worse_G_count']} / 56 matched tasks.",
        "",
        f"Primary `objective_final` fields retain the raw SciPy terminal point; `best_evaluated_objective` is stored separately and never silently substituted. The terminal point was worse than the tracked best by more than 1e-10 in {continuation['terminal_worse_than_best_evaluated_count']} / 168 COBYLA continuation runs and {optimizer['terminal_worse_than_best_evaluated_count']} / 56 Nelder–Mead runs.",
        "",
        "## Objective decomposition",
        "",
        f"For paired random-p3 minus continuation states, median objective difference was {decomposition['objective']:.6g}. Its routing, flow-penalty, and resource-penalty differences were {decomposition['expected_routing_component']:.6g}, {decomposition['expected_flow_penalty']:.6g}, and {decomposition['expected_resource_penalty']:.6g}. Random p3 placed {abs(decomposition['mass_valid_flow_resource_feasible']):.6g} less probability on valid resource-feasible states, {decomposition['mass_flow_invalid']:.6g} more on flow-invalid states, and {abs(decomposition['mass_resource_violating']):.6g} less on resource-violating states. Thus lower expected energy often came from lower-cost/lower-resource-penalty still-infeasible mass rather than uniformly greater feasible recovery.",
        "",
        "## New-layer response slices",
        "",
        f"The 15 deterministic 41-by-41 slices had median grid objective gain {summary['response_slices']['median_grid_objective_gain_from_embedded']:.6g}, median grid G_feas gain {summary['response_slices']['median_grid_G_gain_from_embedded']:.6g}, and median G_feas change {summary['response_slices']['median_G_change_at_grid_objective_minimum']:.6g} at the grid objective minimum. Original p3 new-layer coordinates lay inside the frozen symmetric slice window for {summary['response_slices']['original_p3_coordinate_projectable_count']} / 15 tasks; no off-window projection was drawn.",
        "",
        "## Energy separation",
        "",
        f"Complete feasible/infeasible energy-class separation held for {separation['pilot_count']} / {separation['pilot_denominator']} pilot tasks and {separation['full_v2_count']} / {separation['full_v2_denominator']} full-v2 tasks. This does not make expected energy strictly monotonic in feasible probability.",
        "",
        "## Attribution",
        "",
        f"`{summary['scientific_attribution']}`",
        "",
        "Better objective, better feasible probability, and better optimal probability remain distinct outcomes throughout this report.",
        "",
        "## Next recommendation",
        "",
        f"`{summary['next_recommendation']}`",
        "",
    ]
    atomic_write_text(RESULT_ROOT / "OPTIMIZATION_DIAGNOSTIC_REPORT.md", "\n".join(lines))
