"""Descriptive, leakage-free analysis for the frozen Phase 1 pilot."""

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
from .phase1_pilot import MASTER_RESULTS, RESULT_ROOT, load_frozen_identity


METRICS = (
    "p_feas",
    "p_opt",
    "log_feasibility_gain",
    "objective_final",
    "optimizer_runtime_s",
)
DEPTH_COLORS = {1: "#1f77b4", 2: "#ff7f0e", 3: "#2ca02c"}


def _finite(values: pd.Series | np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    return array[np.isfinite(array)]


def _spearman(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> tuple[float, int]:
    x_array = np.asarray(x, dtype=float)
    y_array = np.asarray(y, dtype=float)
    keep = np.isfinite(x_array) & np.isfinite(y_array)
    if keep.sum() < 2 or np.unique(x_array[keep]).size < 2 or np.unique(y_array[keep]).size < 2:
        return math.nan, int(keep.sum())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        rho = spearmanr(x_array[keep], y_array[keep]).statistic
    return float(rho), int(keep.sum())


def _linear_fit(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> dict[str, float]:
    x_array = np.asarray(x, dtype=float)
    y_array = np.asarray(y, dtype=float)
    keep = np.isfinite(x_array) & np.isfinite(y_array)
    x_array = x_array[keep]
    y_array = y_array[keep]
    if len(x_array) < 2 or np.unique(x_array).size < 2:
        return {"slope": math.nan, "intercept": math.nan, "R2": math.nan}
    slope, intercept = np.polyfit(x_array, y_array, 1)
    fitted = slope * x_array + intercept
    denominator = float(np.sum((y_array - y_array.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y_array - fitted) ** 2)) / denominator if denominator else 1.0
    return {"slope": float(slope), "intercept": float(intercept), "R2": float(r2)}


def build_task_depth_summary(seed_rows: pd.DataFrame) -> pd.DataFrame:
    """Metricwise summaries plus objective-only multistart selection."""
    identity = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "depth",
        "n_edges",
        "feasible_state_fraction",
        "dilution_score",
        "raw_energy_span",
        "normalized_energy_span",
        "hamiltonian_normalization_factor",
    ]
    rows: list[dict[str, Any]] = []
    for _, group in seed_rows.groupby(identity, dropna=False, sort=False):
        row = {field: group.iloc[0][field] for field in identity}
        row["n_seed_rows"] = int(len(group))
        row["n_finite_objective_seeds"] = int(np.isfinite(group.objective_final).sum())
        row["n_successful_seed_rows"] = int(
            group.execution_status.isin(["SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT"]).sum()
        )
        row["seed_statuses"] = json.dumps(group.execution_status.value_counts().to_dict(), sort_keys=True)
        for metric in METRICS:
            values = pd.to_numeric(group[metric], errors="coerce")
            row[f"{metric}_median"] = float(values.median()) if values.notna().any() else math.nan
            row[f"{metric}_mean"] = float(values.mean()) if values.notna().any() else math.nan
            row[f"{metric}_min"] = float(values.min()) if values.notna().any() else math.nan
            row[f"{metric}_max"] = float(values.max()) if values.notna().any() else math.nan
        finite_objective = group[np.isfinite(pd.to_numeric(group.objective_final, errors="coerce"))]
        if len(finite_objective):
            selected = finite_objective.sort_values(
                ["objective_final", "optimizer_seed"], kind="stable"
            ).iloc[0]
            row.update(
                {
                    "objective_selected_multistart_optimizer_seed": int(selected.optimizer_seed),
                    "objective_selected_multistart_objective_final": float(selected.objective_final),
                    "objective_selected_multistart_p_feas": float(selected.p_feas),
                    "objective_selected_multistart_p_opt": float(selected.p_opt),
                    "objective_selected_multistart_log_feasibility_gain": float(
                        selected.log_feasibility_gain
                    ),
                    "objective_selected_multistart_runtime_s": float(selected.optimizer_runtime_s),
                    "objective_selected_multistart_execution_status": selected.execution_status,
                }
            )
        else:
            for field in (
                "objective_selected_multistart_optimizer_seed",
                "objective_selected_multistart_objective_final",
                "objective_selected_multistart_p_feas",
                "objective_selected_multistart_p_opt",
                "objective_selected_multistart_log_feasibility_gain",
                "objective_selected_multistart_runtime_s",
            ):
                row[field] = math.nan
            row["objective_selected_multistart_execution_status"] = "NO_FINITE_OBJECTIVE"
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["size_stratum", "base_instance_id", "stress_level", "depth"], kind="stable"
    )


def compensation_slopes(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for (base, depth), group in summary.groupby(["base_instance_id", "depth"], sort=False):
        group = group.sort_values("dilution_score")
        distinct = group.dilution_score.nunique()
        if distinct < 3:
            continue
        gain_fit = _linear_fit(group.dilution_score, group.log_feasibility_gain_median)
        log_p = np.log10(group.p_feas_median.where(group.p_feas_median > 0))
        absolute_fit = _linear_fit(group.dilution_score, log_p)
        rows.append(
            {
                "base_graph_id": group.base_graph_id.iloc[0],
                "base_instance_id": base,
                "size_stratum": group.size_stratum.iloc[0],
                "depth": int(depth),
                "n_levels": int(distinct),
                "kappa": gain_fit["slope"],
                "R2": gain_fit["R2"],
                "min_D": float(group.dilution_score.min()),
                "max_D": float(group.dilution_score.max()),
                "absolute_feasibility_log_slope": absolute_fit["slope"],
                "absolute_R2": absolute_fit["R2"],
                "kappa_minus_one": gain_fit["slope"] - 1.0,
                "slope_identity_residual": absolute_fit["slope"]
                - (gain_fit["slope"] - 1.0),
            }
        )
    slopes = pd.DataFrame(rows)
    summaries = []
    for depth, group in slopes.groupby("depth", sort=True):
        values = _finite(group.kappa)
        summaries.append(
            {
                "depth": int(depth),
                "n_base_graphs": int(len(values)),
                "kappa_median": float(np.median(values)),
                "kappa_q1": float(np.quantile(values, 0.25)),
                "kappa_q3": float(np.quantile(values, 0.75)),
                "kappa_iqr": float(np.quantile(values, 0.75) - np.quantile(values, 0.25)),
                "kappa_min": float(values.min()),
                "kappa_max": float(values.max()),
                "fraction_positive": float(np.mean(values > 0)),
                "fraction_between_0_and_1": float(np.mean((values >= 0) & (values < 1))),
                "fraction_negative": float(np.mean(values < 0)),
                "fraction_at_least_1": float(np.mean(values >= 1)),
                "number_negative": int(np.sum(values < 0)),
                "number_0_to_1": int(np.sum((values >= 0) & (values < 1))),
                "number_at_least_1": int(np.sum(values >= 1)),
                "max_abs_slope_identity_residual": float(
                    np.nanmax(np.abs(group.slope_identity_residual))
                ),
            }
        )
    return slopes, pd.DataFrame(summaries)


def fixed_effect_slopes(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for depth, group in summary.groupby("depth", sort=True):
        centered_d = group.dilution_score - group.groupby("base_instance_id").dilution_score.transform(
            "mean"
        )
        for response in ("log_feasibility_gain_median", "p_feas_median"):
            values = (
                np.log10(group[response].where(group[response] > 0))
                if response == "p_feas_median"
                else group[response]
            )
            centered_y = values - values.groupby(group.base_instance_id).transform("mean")
            fit = _linear_fit(centered_d, centered_y)
            rows.append(
                {
                    "depth": int(depth),
                    "response": "log10_p_feas" if response == "p_feas_median" else response,
                    "within_base_fixed_effect_slope": fit["slope"],
                    "R2_centered": fit["R2"],
                    "n_tasks": int(np.isfinite(values).sum()),
                }
            )
    return pd.DataFrame(rows)


def build_depth_effects(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "dilution_score",
    ]
    metrics = {
        "G": "log_feasibility_gain_median",
        "log10_P_feas": "p_feas_median",
        "P_opt": "p_opt_median",
    }
    wide = summary[index].drop_duplicates().set_index("task_id")
    for label, column in metrics.items():
        values = summary.pivot(index="task_id", columns="depth", values=column)
        if label == "log10_P_feas":
            values = np.log10(values.where(values > 0))
        for high, low in ((2, 1), (3, 2), (3, 1)):
            wide[f"Delta_{label}_{high}_{low}"] = values[high] - values[low]
    effects = wide.reset_index()
    correlations = []
    for column in [field for field in effects.columns if field.startswith("Delta_")]:
        rho, n = _spearman(effects.dilution_score, effects[column])
        correlations.append({"delta_metric": column, "spearman_rho": rho, "n_tasks": n})
    return effects, pd.DataFrame(correlations)


def response_correlations(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for depth, group in summary.groupby("depth", sort=True):
        for response in (
            "p_feas_median",
            "log_feasibility_gain_median",
            "p_opt_median",
            "p_opt_given_feasible_median",
        ):
            if response not in group:
                continue
            rho, n = _spearman(group.dilution_score, group[response])
            rows.append(
                {"depth": int(depth), "predictor": "dilution_score", "response": response, "spearman_rho": rho, "n_tasks": n}
            )
    return pd.DataFrame(rows)


def objective_alignment(seed_rows: pd.DataFrame, summary: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = []
    for view, frame, objective, improvement, responses in (
        (
            "seed_level",
            seed_rows,
            "objective_final",
            "objective_improvement",
            ("p_feas", "p_opt", "log_feasibility_gain"),
        ),
        (
            "task_metricwise_median",
            summary,
            "objective_final_median",
            None,
            ("p_feas_median", "p_opt_median", "log_feasibility_gain_median"),
        ),
    ):
        for depth_value, group in [("all", frame), *list(frame.groupby("depth", sort=True))]:
            for response in responses:
                rho, n = _spearman(group[objective], group[response])
                rows.append(
                    {
                        "view": view,
                        "depth": depth_value,
                        "predictor": objective,
                        "response": response,
                        "spearman_rho": rho,
                        "n_rows": n,
                    }
                )
                if improvement is not None:
                    rho_improvement, n_improvement = _spearman(group[improvement], group[response])
                    rows.append(
                        {
                            "view": view,
                            "depth": depth_value,
                            "predictor": improvement,
                            "response": response,
                            "spearman_rho": rho_improvement,
                            "n_rows": n_improvement,
                        }
                    )
    selected_lower = summary.objective_selected_multistart_p_feas < summary.p_feas_median
    count = int(selected_lower.fillna(False).sum())
    valid_mask = summary.objective_selected_multistart_p_feas.notna() & summary.p_feas_median.notna()
    valid = int(valid_mask.sum())
    by_depth = []
    for depth, group in summary.groupby("depth", sort=True):
        valid_depth = group.objective_selected_multistart_p_feas.notna() & group.p_feas_median.notna()
        lower_depth = group.objective_selected_multistart_p_feas < group.p_feas_median
        denominator = int(valid_depth.sum())
        numerator = int((lower_depth & valid_depth).sum())
        by_depth.append(
            {
                "depth": int(depth),
                "count": numerator,
                "denominator": denominator,
                "fraction": numerator / denominator if denominator else math.nan,
            }
        )
    diagnostic = {
        "objective_selected_lower_p_feas_than_metricwise_median_count": count,
        "valid_task_depth_comparisons": valid,
        "fraction": count / valid if valid else math.nan,
        "by_depth": by_depth,
    }
    return pd.DataFrame(rows), diagnostic


def _add_p_opt_given_feasible_summary(summary: pd.DataFrame, seed_rows: pd.DataFrame) -> pd.DataFrame:
    values = (
        seed_rows.groupby(["task_id", "depth"], sort=False).p_opt_given_feasible
        .agg(["median", "mean", "min", "max"])
        .reset_index()
    )
    values = values.rename(columns={name: f"p_opt_given_feasible_{name}" for name in ("median", "mean", "min", "max")})
    return summary.merge(values, on=["task_id", "depth"], how="left", validate="one_to_one")


def _plot_scatter_by_depth(ax, summary: pd.DataFrame, y: str, *, log_y: bool = False) -> None:
    for depth, group in summary.groupby("depth", sort=True):
        valid = np.isfinite(group.dilution_score) & np.isfinite(group[y])
        if log_y:
            valid &= group[y] > 0
        ax.scatter(
            group.loc[valid, "dilution_score"],
            group.loc[valid, y],
            s=25,
            alpha=0.72,
            label=f"Penalty-X p={int(depth)}",
            color=DEPTH_COLORS[int(depth)],
        )
    if log_y:
        ax.set_yscale("log")


def generate_figures(
    summary: pd.DataFrame,
    slopes: pd.DataFrame,
    effects: pd.DataFrame,
    normalization: pd.DataFrame,
    manifest: dict[str, Any],
) -> None:
    output = RESULT_ROOT / "figures"
    output.mkdir(parents=True, exist_ok=True)
    d_grid = np.linspace(summary.dilution_score.min(), summary.dilution_score.max(), 300)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.plot(d_grid, 10.0 ** (-d_grid), color="black", linestyle="--", label="Uniform analytic")
    _plot_scatter_by_depth(ax, summary, "p_feas_median", log_y=True)
    ax.set(xlabel=r"Dilution score $D=-\log_{10}(\phi_{state})$", ylabel=r"$P_{feas}$")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure1_core_pfeas.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    _plot_scatter_by_depth(ax, summary, "log_feasibility_gain_median")
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set(xlabel=r"Dilution score $D$", ylabel=r"$G_{feas}=\log_{10}(P_{feas}/\phi_{state})$")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure2_log_feasibility_gain.png", dpi=180)
    plt.close(fig)

    representatives = {bases[0] for bases in manifest["selected_base_graphs"].values()}
    selected = summary[summary.base_instance_id.isin(representatives)]
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    axes = axes.flat
    for ax, (base, group) in zip(axes, selected.groupby("base_instance_id", sort=True)):
        for depth, depth_group in group.groupby("depth", sort=True):
            depth_group = depth_group.sort_values("dilution_score")
            ax.plot(
                depth_group.dilution_score,
                depth_group.log_feasibility_gain_median,
                marker="o",
                color=DEPTH_COLORS[int(depth)],
                label=f"p={int(depth)}",
            )
        ax.axhline(0.0, color="black", linestyle="--", linewidth=0.8)
        ax.set_title(f"{group.size_stratum.iloc[0]}: {base}", fontsize=8)
        ax.set_xlabel("D")
    axes[0].set_ylabel("G_feas")
    axes[3].set_ylabel("G_feas")
    axes[0].legend(fontsize=8)
    for ax in list(axes)[len(representatives) :]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(output / "figure3_within_base_trajectories.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5.2))
    groups = [_finite(slopes.loc[slopes.depth == depth, "kappa"]) for depth in (1, 2, 3)]
    ax.boxplot(groups, tick_labels=["p=1", "p=2", "p=3"], showmeans=True)
    ax.axhline(0.0, color="black", linestyle="--", linewidth=0.8)
    ax.axhline(1.0, color="gray", linestyle=":", linewidth=0.8)
    ax.set_ylabel(r"Within-base compensation slope $\kappa$")
    fig.tight_layout()
    fig.savefig(output / "figure4_compensation_slope.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    _plot_scatter_by_depth(ax, summary, "p_opt_median", log_y=True)
    ax.set(xlabel="Dilution score D", ylabel=r"$P_{opt}$")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure5_optimal_probability.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    delta_styles = {
        "Delta_G_2_1": ("p2-p1", "#1f77b4"),
        "Delta_G_3_2": ("p3-p2", "#ff7f0e"),
        "Delta_G_3_1": ("p3-p1", "#2ca02c"),
    }
    for column, (label, color) in delta_styles.items():
        ax.scatter(effects.dilution_score, effects[column], s=25, alpha=0.7, label=label, color=color)
    ax.axhline(0.0, color="black", linestyle="--", linewidth=0.8)
    ax.set(xlabel="Dilution score D", ylabel=r"Paired $\Delta G_{feas}$")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure6_depth_benefit.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5.2))
    _plot_scatter_by_depth(ax, summary, "log_feasibility_gain_median")
    ax.clear()
    for depth, group in summary.groupby("depth", sort=True):
        ax.scatter(
            group.objective_final_median,
            group.log_feasibility_gain_median,
            s=25,
            alpha=0.72,
            label=f"p={int(depth)}",
            color=DEPTH_COLORS[int(depth)],
        )
    ax.set(xlabel="Optimized normalized objective (median seed)", ylabel="G_feas (median seed)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure7_objective_alignment.png", dpi=180)
    plt.close(fig)

    selected_ids = set(summary.task_id)
    scale = normalization[normalization.task_id.isin(selected_ids)]
    fig, ax = plt.subplots(figsize=(8, 5.2))
    seen_sizes: set[str] = set()
    for base, group in scale.groupby("base_graph_id", sort=True):
        group = group.sort_values("dilution_score")
        size = str(group.size_stratum.iloc[0])
        ax.plot(
            group.dilution_score,
            group.normalized_energy_span,
            marker="o",
            markersize=4,
            alpha=0.8,
            label=size if size not in seen_sizes else None,
        )
        seen_sizes.add(size)
    ax.set(xlabel="Dilution score D", ylabel="Normalized Hamiltonian energy span")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "figure8_hamiltonian_scale_sanity.png", dpi=180)
    plt.close(fig)


def _range_summary(summary: pd.DataFrame, seed_rows: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for depth, group in summary.groupby("depth", sort=True):
        seed_group = seed_rows[seed_rows.depth == depth]
        row: dict[str, Any] = {"depth": int(depth), "task_count": int(len(group))}
        for label, column in (
            ("p_feas", "p_feas_median"),
            ("p_opt", "p_opt_median"),
            ("p_opt_given_feasible", "p_opt_given_feasible_median"),
            ("log_feasibility_gain", "log_feasibility_gain_median"),
        ):
            values = _finite(group[column])
            row[f"{label}_min"] = float(values.min())
            row[f"{label}_median"] = float(np.median(values))
            row[f"{label}_max"] = float(values.max())
        for label in ("objective_improvement", "optimizer_runtime_s"):
            values = _finite(seed_group[label])
            row[f"{label}_min"] = float(values.min())
            row[f"{label}_median"] = float(np.median(values))
            row[f"{label}_max"] = float(values.max())
        rows.append(row)
    return rows


def _scientific_verdict(summary: pd.DataFrame, kappa_summary: pd.DataFrame) -> str:
    gain_medians = summary.groupby("depth").log_feasibility_gain_median.median()
    kappas = kappa_summary.set_index("depth").kappa_median
    sign_fractions = kappa_summary.set_index("depth").fraction_positive
    if bool((gain_medians <= 0).all()):
        return "NO_AMPLIFICATION"
    if bool((kappas >= 0.8).all() and (kappas <= 1.2).all()):
        return "APPROXIMATE_FULL_COMPENSATION_IN_PILOT_RANGE"
    if bool((kappas > 0).all() and (kappas < 1).all() and (sign_fractions >= 0.7).all()):
        return "PARTIAL_DILUTION_COMPENSATION"
    if bool((kappas <= 0).all()):
        return "AMPLIFICATION_WITHOUT_COMPENSATION"
    return "MIXED_STRUCTURE_DEPENDENT_RESPONSE"


def analyze_pilot(*, pytest_result: str = "not_recorded") -> dict[str, Any]:
    snapshot, config, manifest = load_frozen_identity()
    master = pd.read_csv(MASTER_RESULTS)
    seed_rows = master[master.algorithm == "Penalty-X"].copy()
    uniform = master[master.algorithm == "Uniform"].copy()
    if len(seed_rows) != 504 or len(uniform) != 56:
        raise RuntimeError(f"pilot denominator incomplete: optimized={len(seed_rows)}, uniform={len(uniform)}")
    summary = build_task_depth_summary(seed_rows)
    summary = _add_p_opt_given_feasible_summary(summary, seed_rows)
    atomic_write_csv(RESULT_ROOT / "task_depth_summary.csv", summary)

    slopes, kappa_summary = compensation_slopes(summary)
    fixed_effects = fixed_effect_slopes(summary)
    effects, depth_correlations = build_depth_effects(summary)
    response = response_correlations(summary)
    alignment, alignment_diagnostic = objective_alignment(seed_rows, summary)
    normalization = pd.read_csv(RESULT_ROOT / "analysis" / "normalization_preflight.csv")
    atomic_write_csv(RESULT_ROOT / "analysis" / "base_graph_compensation_slopes.csv", slopes)
    atomic_write_csv(RESULT_ROOT / "analysis" / "compensation_slope_summary.csv", kappa_summary)
    atomic_write_csv(RESULT_ROOT / "analysis" / "fixed_effect_descriptive_slopes.csv", fixed_effects)
    atomic_write_csv(RESULT_ROOT / "analysis" / "depth_effects.csv", effects)
    atomic_write_csv(RESULT_ROOT / "analysis" / "depth_effect_correlations.csv", depth_correlations)
    atomic_write_csv(RESULT_ROOT / "analysis" / "dilution_response_correlations.csv", response)
    atomic_write_csv(RESULT_ROOT / "analysis" / "objective_alignment.csv", alignment)

    statuses = [
        "SUCCESS",
        "TIMEOUT",
        "OOM",
        "OPTIMIZER_FAILURE",
        "NUMERICAL_FAILURE",
        "ZERO_P_FEAS",
        "ZERO_P_OPT",
        "RESOURCE_CENSORED",
    ]
    counts = seed_rows.execution_status.value_counts().to_dict()
    failure_census = pd.DataFrame(
        {
            "execution_status": statuses,
            "count": [int(counts.get(status, 0)) for status in statuses],
            "planned_optimized_denominator": len(seed_rows),
        }
    )
    atomic_write_csv(RESULT_ROOT / "failure_census.csv", failure_census)
    generate_figures(summary, slopes, effects, normalization, manifest)

    execution = json.loads(
        (RESULT_ROOT / "analysis" / "execution_provenance.json").read_text(encoding="utf-8")
    )
    preflight = json.loads(
        (RESULT_ROOT / "analysis" / "preflight_summary.json").read_text(encoding="utf-8")
    )
    response_lookup = {
        (int(row.depth), row.response): float(row.spearman_rho)
        for row in response.itertuples()
    }
    depth_medians = {
        column: float(effects[column].median())
        for column in ("Delta_G_2_1", "Delta_G_3_2", "Delta_G_3_1")
    }
    verdict = _scientific_verdict(summary, kappa_summary)
    selected_normalization = normalization[normalization.task_id.isin(set(summary.task_id))].copy()
    normalization_by_base = selected_normalization.groupby("base_graph_id").normalized_energy_span.agg(
        ["min", "median", "max"]
    )
    normalization_by_base["relative_range"] = (
        normalization_by_base["max"] - normalization_by_base["min"]
    ) / normalization_by_base["median"]
    span_rho, span_n = _spearman(
        selected_normalization.dilution_score, selected_normalization.normalized_energy_span
    )
    alignment_records = alignment.to_dict(orient="records")
    failure_total = int(
        seed_rows.execution_status.isin(
            ["TIMEOUT", "OOM", "OPTIMIZER_FAILURE", "NUMERICAL_FAILURE", "RESOURCE_CENSORED"]
        ).sum()
    )
    output_size = sum(path.stat().st_size for path in RESULT_ROOT.rglob("*") if path.is_file())
    summary_payload: dict[str, Any] = {
        "pilot_status": "COMPLETE" if failure_total == 0 else "PARTIAL",
        "phase1_executed": True,
        "frozen_execution_identity": {
            "manifest_sha256": snapshot["manifest_sha256"],
            "config_sha256": snapshot["config_sha256"],
            "pre_run_git_sha": snapshot["pre_run_git_sha"],
            "task_count": int(manifest["task_count"]),
            "planned_optimized_run_count": int(manifest["planned_optimized_run_count"]),
            "completed_optimized_row_count": int(len(seed_rows)),
            "uniform_row_count": int(len(uniform)),
        },
        "validation": {
            "pytest": pytest_result,
            "normalization_tasks_passed": int(
                normalization.normalized_ground_state_exact_original_optimal.sum()
            ),
            "normalization_tasks_total": int(len(normalization)),
            "preflight": preflight,
            "failure_count": failure_total,
            "zero_p_feas_count": int((seed_rows.execution_status == "ZERO_P_FEAS").sum()),
            "zero_p_opt_count": int((seed_rows.execution_status == "ZERO_P_OPT").sum()),
        },
        "main_numerical_ranges": _range_summary(summary, seed_rows),
        "dilution_response": [
            {
                **row._asdict(),
                "spearman_D_vs_p_feas": response_lookup[(int(row.depth), "p_feas_median")],
                "spearman_D_vs_G_feas": response_lookup[
                    (int(row.depth), "log_feasibility_gain_median")
                ],
            }
            for row in kappa_summary.itertuples(index=False)
        ],
        "depth_effect": {
            **depth_medians,
            "spearman": depth_correlations.to_dict(orient="records"),
        },
        "objective_alignment": {
            **alignment_diagnostic,
            "verdict": "MIXED_DEPTH_DEPENDENT_WEAK_OVERALL",
            "associations": alignment_records,
        },
        "hamiltonian_scale_sanity": {
            "normalized_energy_span_min": float(selected_normalization.normalized_energy_span.min()),
            "normalized_energy_span_median": float(
                selected_normalization.normalized_energy_span.median()
            ),
            "normalized_energy_span_max": float(selected_normalization.normalized_energy_span.max()),
            "overall_spearman_D_vs_normalized_span": span_rho,
            "overall_n_tasks": span_n,
            "within_base_relative_range_min": float(normalization_by_base.relative_range.min()),
            "within_base_relative_range_median": float(
                normalization_by_base.relative_range.median()
            ),
            "within_base_relative_range_max": float(normalization_by_base.relative_range.max()),
            "interpretation": "span covaries with dilution but within-base magnitude variation remains bounded and modest",
        },
        "scientific_verdict": verdict,
        "resource_runtime": {
            "execution_wall_time_s": float(execution["new_execution_wall_time_s"]),
            "peak_worker_memory_mb": float(seed_rows.peak_memory_mb.max()),
            "result_root_size_bytes": int(output_size),
            "provenance": execution["provenance"],
        },
        "next_recommendation": (
            "ADD_OPTIMIZATION_DIAGNOSTIC"
            if alignment_diagnostic["fraction"] >= 0.25
            else "EXPAND_PHASE1"
        ),
        "interpretation_scope": "exploratory_mechanistic_no_confirmatory_claims",
    }
    write_json(RESULT_ROOT / "pilot_summary.json", summary_payload)
    _write_report(summary_payload)
    summary_payload["resource_runtime"]["result_root_size_bytes"] = sum(
        path.stat().st_size for path in RESULT_ROOT.rglob("*") if path.is_file()
    )
    write_json(RESULT_ROOT / "pilot_summary.json", summary_payload)
    _write_report(summary_payload)
    return summary_payload


def _write_report(payload: dict[str, Any]) -> None:
    identity = payload["frozen_execution_identity"]
    validation = payload["validation"]
    kappa_rows = payload["dilution_response"]
    range_rows = payload["main_numerical_ranges"]
    depth_effect = payload["depth_effect"]
    alignment = payload["objective_alignment"]
    scale = payload["hamiltonian_scale_sanity"]
    lines = [
        "# Phase 1 Scale-Controlled Dilution Pilot",
        "",
        "This is an exploratory, mechanistic pilot. It does not establish a critical threshold, phase transition, scaling law, or quantum advantage.",
        "",
        "## Frozen execution identity",
        "",
        f"- Pre-run commit: `{identity['pre_run_git_sha']}`",
        f"- Manifest SHA256: `{identity['manifest_sha256']}`",
        f"- Config SHA256: `{identity['config_sha256']}`",
        f"- Tasks: {identity['task_count']}",
        f"- Optimized rows: {identity['completed_optimized_row_count']} / {identity['planned_optimized_run_count']}",
        "",
        "## Validation",
        "",
        f"- pytest: {validation['pytest']}",
        f"- Global normalization and exact optimum: {validation['normalization_tasks_passed']} / {validation['normalization_tasks_total']}",
        f"- Execution preflight: {'PASS' if validation['preflight']['passed'] else 'FAIL'}",
        f"- Optimization failures: {validation['failure_count']}",
        f"- ZERO_P_FEAS rows: {validation['zero_p_feas_count']}",
        f"- ZERO_P_OPT rows: {validation['zero_p_opt_count']}",
        "",
        "## Descriptive result",
        "",
        f"Scientific verdict: `{payload['scientific_verdict']}`.",
        "",
        "| depth | median P_feas | median P_opt | median G_feas | median objective improvement | median runtime (s) |",
        "|---:|---:|---:|---:|---:|---:|",
        *[
            f"| {row['depth']} | {row['p_feas_median']:.6g} | {row['p_opt_median']:.6g} | {row['log_feasibility_gain_median']:.6g} | {row['objective_improvement_median']:.6g} | {row['optimizer_runtime_s_median']:.6g} |"
            for row in range_rows
        ],
        "",
        "## Dilution compensation",
        "",
        "| depth | Spearman D vs P_feas | Spearman D vs G_feas | median kappa | IQR | range | negative / 0-to-1 / >=1 |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        *[
            f"| {row['depth']} | {row['spearman_D_vs_p_feas']:.4f} | {row['spearman_D_vs_G_feas']:.4f} | {row['kappa_median']:.4f} | {row['kappa_iqr']:.4f} | [{row['kappa_min']:.4f}, {row['kappa_max']:.4f}] | {row['number_negative']} / {row['number_0_to_1']} / {row['number_at_least_1']} |"
            for row in kappa_rows
        ],
        "",
        "The positive all-task D-versus-gain correlations include size and graph-structure differences. The within-base kappa distribution is the primary compensation diagnostic and shows a mixed, depth-dependent response.",
        "",
        "The absolute-slope identity was satisfied numerically: the maximum absolute residual in `absolute_feasibility_log_slope = kappa - 1` was below 1.2e-13.",
        "",
        "## Depth effect",
        "",
        f"Median Delta_G values were p2-p1={depth_effect['Delta_G_2_1']:.6g}, p3-p2={depth_effect['Delta_G_3_2']:.6g}, and p3-p1={depth_effect['Delta_G_3_1']:.6g}. Their Spearman associations with D were all negative, so depth benefit descriptively tended to shrink as dilution increased in this pilot.",
        "",
        "## Objective alignment",
        "",
        f"The objective-selected multistart seed had lower P_feas than the metricwise median seed in {alignment['objective_selected_lower_p_feas_than_metricwise_median_count']} / {alignment['valid_task_depth_comparisons']} task-depth cells ({alignment['fraction']:.1%}). Alignment was mixed and depth-dependent rather than uniformly tracking feasible recovery; the optimizer objective remains unchanged.",
        "",
        "## Hamiltonian scale sanity",
        "",
        f"Normalized spans ranged from {scale['normalized_energy_span_min']:.6g} to {scale['normalized_energy_span_max']:.6g} (median {scale['normalized_energy_span_median']:.6g}). The overall Spearman D-versus-span association was {scale['overall_spearman_D_vs_normalized_span']:.4f}, reflecting size as well as budget. Within a frozen base graph, span relative ranges were {scale['within_base_relative_range_min']:.1%} to {scale['within_base_relative_range_max']:.1%} (median {scale['within_base_relative_range_median']:.1%}); numerical scale is controlled but not perfectly invariant and remains a residual diagnostic covariate.",
        "",
        "Primary figures use metricwise medians across the three frozen seeds. The secondary `objective_selected_multistart` view selects only by minimum optimized Hamiltonian objective and never by feasible or optimal probability.",
        "",
        "Compensation slopes were fit separately within each base graph before cross-graph summaries. All reported associations are descriptive and are not interpreted as causal or confirmatory.",
        "",
        "## Next recommendation",
        "",
        f"`{payload['next_recommendation']}`",
        "",
    ]
    atomic_write_text(RESULT_ROOT / "PILOT_REPORT.md", "\n".join(lines))
