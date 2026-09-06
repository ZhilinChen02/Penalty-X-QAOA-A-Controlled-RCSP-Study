"""Phase 0.6 exhaustive Hamiltonian scale and penalty-confound audit."""

from __future__ import annotations

import hashlib
import json
import math
import time
import warnings
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import ConstantInputWarning, spearmanr

from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task
from .models import Task
from .optimizer import initial_parameters
from .penalties import RawStateComponents, build_raw_state_components, scale_controlled_penalties
from .representation import validate_edge_selection


CURRENT_FLOW_STRENGTH = 50.0
CURRENT_RESOURCE_STRENGTH = 20.0
CONTROLLED_FLOW_STRENGTH = 172.0
CONTROLLED_RESOURCE_STRENGTH = 172.0
FROZEN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "phase06_frozen_evidence_sha256.json"
RESULT_DIR = PROJECT_ROOT / "results" / "phase0_v2_dilution_stress"


def verify_phase06_frozen_evidence() -> dict[str, str]:
    fixture = json.loads(FROZEN_FIXTURE.read_text(encoding="utf-8"))
    observed: dict[str, str] = {}
    for relative, expected in fixture["files"].items():
        digest = hashlib.sha256((PROJECT_ROOT / relative).read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"frozen evidence hash mismatch: {relative}")
        observed[relative] = digest
    return observed


def _load_v2_tasks() -> tuple[list[Task], pd.DataFrame]:
    manifest = json.loads(
        (PROJECT_ROOT / "data" / "manifests" / "phase0_v2_dilution_stress.json").read_text(
            encoding="utf-8"
        )
    )
    tasks = [read_task(PROJECT_ROOT / row["task_path"]) for row in manifest["tasks"]]
    characterization = pd.read_csv(RESULT_DIR / "task_characterization.csv")
    return tasks, characterization


def _load_v1_tasks() -> tuple[list[Task], pd.DataFrame]:
    manifest = pd.read_csv(PROJECT_ROOT / "data" / "manifests" / "phase0_tasks.csv")
    tasks = [read_task(PROJECT_ROOT / path) for path in manifest["task_path"]]
    characterization = pd.read_csv(PROJECT_ROOT / "results" / "phase0" / "task_characterization.csv")
    return tasks, characterization


def _stats(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "p95": float(np.percentile(values, 95)),
    }


def _minimum_positive(values: np.ndarray) -> float:
    positive = values[values > 0.0]
    return float(np.min(positive)) if positive.size else math.nan


def _ground_state_audit(
    task: Task, total_energy: np.ndarray, components: RawStateComponents
) -> dict[str, Any]:
    energy_min = float(np.min(total_energy))
    indices = np.flatnonzero(np.isclose(total_energy, energy_min, rtol=0.0, atol=1e-12))
    validations = [validate_edge_selection(task.graph, int(state), task.budget) for state in indices]
    valid = bool(validations and all(item.valid_structure for item in validations))
    resource_feasible = bool(
        len(indices) and np.all(components.resource_total[indices] <= task.budget + 1e-12)
    )
    exact_states = {route.bitstring_int for route in task.optimal_routes}
    original_optimal = bool(len(indices) and all(int(state) in exact_states for state in indices))
    ground_costs = components.routing_cost[indices]
    ground_cost = float(np.min(ground_costs)) if len(indices) else math.nan
    exact_cost = float(task.optimal_cost) if task.optimal_cost is not None else math.nan
    return {
        "n_penalty_ground_states": int(len(indices)),
        "penalty_ground_state_valid": valid,
        "penalty_ground_state_resource_feasible": resource_feasible,
        "penalty_ground_state_original_optimal": original_optimal,
        "penalty_ground_state_cost": ground_cost,
        "penalty_ground_state_cost_max": float(np.max(ground_costs)) if len(indices) else math.nan,
        "exact_rcsp_cost": exact_cost,
        "ground_state_gap_to_exact": ground_cost - exact_cost,
    }


def _gamma_initialization_summary() -> dict[str, float | str]:
    config = load_config(PROJECT_ROOT / "configs" / "phase0_v2_dilution_stress.yaml")
    qconfig = config["pilot_qaoa"]
    gammas: list[float] = []
    for depth in qconfig["depths"]:
        for seed in qconfig["optimizer_seeds"]:
            gammas.extend(initial_parameters(int(depth), int(seed))[: int(depth)].tolist())
    values = np.asarray(gammas)
    return {
        "gamma_initial_min": float(values.min()),
        "gamma_initial_median": float(np.median(values)),
        "gamma_initial_max": float(values.max()),
        "gamma_initial_support": "uniform [0, 2*pi]",
        "optimizer_parameter_bounds": "none after initialization; gamma is not wrapped",
    }


def _current_task_row(
    task: Task,
    characterization: dict[str, Any],
    components: RawStateComponents,
    gamma: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, np.ndarray]:
    resource_excess = np.maximum(0.0, components.resource_total - task.budget)
    resource_penalty_raw = resource_excess**2
    weighted_flow = CURRENT_FLOW_STRENGTH * components.flow_penalty_raw
    weighted_resource = CURRENT_RESOURCE_STRENGTH * resource_penalty_raw
    weighted_total_penalty = weighted_flow + weighted_resource
    total_energy = components.routing_cost + weighted_total_penalty
    routing = _stats(components.routing_cost)
    flow = _stats(components.flow_penalty_raw)
    resource = _stats(resource_penalty_raw)
    total = _stats(total_energy)
    cost_denominator = max(routing["p95"], np.finfo(float).eps)
    energy_span = total["max"] - total["min"]
    row: dict[str, Any] = {
        "task_id": task.task_id,
        "base_graph_id": task.graph.graph_id,
        "base_instance_id": task.base_instance_id,
        "size_stratum": task.size_stratum,
        "stress_level": task.tightness_level,
        "n_edges": len(task.graph.edges),
        "state_space_size": 1 << len(task.graph.edges),
        "budget": task.budget,
        "edge_resource_min": min(edge.resource for edge in task.graph.edges),
        "edge_resource_max": max(edge.resource for edge in task.graph.edges),
        "edge_resource_mean": float(np.mean([edge.resource for edge in task.graph.edges])),
        "feasible_state_fraction": float(characterization["feasible_state_fraction"]),
        "dilution_score": float(characterization.get("dilution_score", -math.log10(characterization["feasible_state_fraction"]))),
        "routing_cost_min": routing["min"],
        "routing_cost_max": routing["max"],
        "routing_cost_mean": routing["mean"],
        "routing_cost_p95": routing["p95"],
        "flow_penalty_min": flow["min"],
        "flow_penalty_max": flow["max"],
        "flow_penalty_mean": flow["mean"],
        "flow_penalty_p95": flow["p95"],
        "minimum_positive_flow_penalty": _minimum_positive(components.flow_penalty_raw),
        "resource_excess_max": float(resource_excess.max()),
        "resource_penalty_max": resource["max"],
        "resource_penalty_mean": resource["mean"],
        "resource_penalty_p95": resource["p95"],
        "minimum_positive_resource_penalty": _minimum_positive(resource_penalty_raw),
        "weighted_flow_penalty_p95": float(np.percentile(weighted_flow, 95)),
        "weighted_resource_penalty_p95": float(np.percentile(weighted_resource, 95)),
        "weighted_total_penalty_p95": float(np.percentile(weighted_total_penalty, 95)),
        "total_energy_min": total["min"],
        "total_energy_max": total["max"],
        "total_energy_mean": total["mean"],
        "total_energy_p95": total["p95"],
        "total_energy_dynamic_range": energy_span,
        "energy_span": energy_span,
        "resource_penalty_raw_to_cost_ratio": resource["p95"] / cost_denominator,
        "flow_penalty_raw_to_cost_ratio": flow["p95"] / cost_denominator,
        "resource_penalty_to_cost_ratio": float(np.percentile(weighted_resource, 95)) / cost_denominator,
        "flow_penalty_to_cost_ratio": float(np.percentile(weighted_flow, 95)) / cost_denominator,
        "total_penalty_to_cost_ratio": float(np.percentile(weighted_total_penalty, 95)) / cost_denominator,
        "flow_penalty_strength": CURRENT_FLOW_STRENGTH,
        "resource_penalty_strength": CURRENT_RESOURCE_STRENGTH,
        "gamma_initial_min": gamma["gamma_initial_min"],
        "gamma_initial_median": gamma["gamma_initial_median"],
        "gamma_initial_max": gamma["gamma_initial_max"],
        "initial_phase_span_min": gamma["gamma_initial_min"] * energy_span,
        "initial_phase_span_median": gamma["gamma_initial_median"] * energy_span,
        "initial_phase_span_max": gamma["gamma_initial_max"] * energy_span,
        "initial_phase_wraps_at_median_gamma": gamma["gamma_initial_median"] * energy_span / (2 * np.pi),
    }
    row.update(_ground_state_audit(task, total_energy, components))
    return row, resource_excess, resource_penalty_raw, total_energy


def _controlled_task_values(
    task: Task,
    components: RawStateComponents,
    resource_excess: np.ndarray,
    gamma: dict[str, Any],
) -> dict[str, Any]:
    flow_scale = max(float(np.max(components.flow_penalty_raw)), 1.0)
    resource_scale = float(sum(edge.resource for edge in task.graph.edges))
    controlled_flow, controlled_resource = scale_controlled_penalties(
        components.flow_penalty_raw,
        resource_excess,
        flow_scale=flow_scale,
        resource_scale=resource_scale,
    )
    weighted_flow = CONTROLLED_FLOW_STRENGTH * controlled_flow
    weighted_resource = CONTROLLED_RESOURCE_STRENGTH * controlled_resource
    total_penalty = weighted_flow + weighted_resource
    energy = components.routing_cost + total_penalty
    cost_p95 = max(float(np.percentile(components.routing_cost, 95)), np.finfo(float).eps)
    energy_span = float(np.max(energy) - np.min(energy))
    ground = _ground_state_audit(task, energy, components)
    return {
        "controlled_flow_scale": flow_scale,
        "controlled_resource_scale": resource_scale,
        "controlled_flow_penalty_strength": CONTROLLED_FLOW_STRENGTH,
        "controlled_resource_penalty_strength": CONTROLLED_RESOURCE_STRENGTH,
        "controlled_flow_classification_unchanged": bool(
            np.array_equal(controlled_flow > 0.0, components.flow_penalty_raw > 0.0)
        ),
        "controlled_resource_classification_unchanged": bool(
            np.array_equal(controlled_resource > 0.0, resource_excess > 0.0)
        ),
        "controlled_flow_penalty_max": float(np.max(controlled_flow)),
        "controlled_resource_penalty_max": float(np.max(controlled_resource)),
        "controlled_flow_penalty_p95": float(np.percentile(controlled_flow, 95)),
        "controlled_resource_penalty_p95": float(np.percentile(controlled_resource, 95)),
        "controlled_total_energy_min": float(np.min(energy)),
        "controlled_total_energy_max": float(np.max(energy)),
        "controlled_total_energy_mean": float(np.mean(energy)),
        "controlled_total_energy_p95": float(np.percentile(energy, 95)),
        "controlled_energy_span": energy_span,
        "controlled_resource_penalty_to_cost_ratio": float(np.percentile(weighted_resource, 95)) / cost_p95,
        "controlled_flow_penalty_to_cost_ratio": float(np.percentile(weighted_flow, 95)) / cost_p95,
        "controlled_total_penalty_to_cost_ratio": float(np.percentile(total_penalty, 95)) / cost_p95,
        "controlled_initial_phase_span_min": gamma["gamma_initial_min"] * energy_span,
        "controlled_initial_phase_span_median": gamma["gamma_initial_median"] * energy_span,
        "controlled_initial_phase_span_max": gamma["gamma_initial_max"] * energy_span,
        "controlled_n_ground_states": ground["n_penalty_ground_states"],
        "controlled_ground_state_valid": ground["penalty_ground_state_valid"],
        "controlled_ground_state_resource_feasible": ground[
            "penalty_ground_state_resource_feasible"
        ],
        "controlled_ground_state_original_optimal": ground[
            "penalty_ground_state_original_optimal"
        ],
        "controlled_ground_state_cost": ground["penalty_ground_state_cost"],
        "controlled_ground_state_gap_to_exact": ground["ground_state_gap_to_exact"],
    }


def _audit_task_collection(
    tasks: list[Task], characterization: pd.DataFrame, *, include_controlled: bool
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    char_lookup = characterization.set_index("task_id").to_dict(orient="index")
    gamma = _gamma_initialization_summary()
    current_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    tasks_by_base: dict[str, list[Task]] = {}
    for task in tasks:
        tasks_by_base.setdefault(task.base_instance_id, []).append(task)
    for family in tasks_by_base.values():
        components = build_raw_state_components(family[0].graph)
        for task in family:
            current, resource_excess, _, _ = _current_task_row(
                task, char_lookup[task.task_id], components, gamma
            )
            current_rows.append(current)
            if include_controlled:
                controlled = _controlled_task_values(task, components, resource_excess, gamma)
                comparison_rows.append(
                    {
                        "task_id": task.task_id,
                        "base_graph_id": task.graph.graph_id,
                        "base_instance_id": task.base_instance_id,
                        "size_stratum": task.size_stratum,
                        "stress_level": task.tightness_level,
                        "n_edges": len(task.graph.edges),
                        "feasible_state_fraction": current["feasible_state_fraction"],
                        "dilution_score": current["dilution_score"],
                        "current_energy_span": current["energy_span"],
                        "current_total_energy_p95": current["total_energy_p95"],
                        "current_resource_penalty_to_cost_ratio": current[
                            "resource_penalty_to_cost_ratio"
                        ],
                        "current_flow_penalty_to_cost_ratio": current[
                            "flow_penalty_to_cost_ratio"
                        ],
                        "current_ground_state_original_optimal": current[
                            "penalty_ground_state_original_optimal"
                        ],
                        **controlled,
                    }
                )
    current_frame = pd.DataFrame(current_rows)
    comparison_frame = pd.DataFrame(comparison_rows) if include_controlled else None
    return current_frame, comparison_frame


CORRELATION_METRICS = [
    "resource_penalty_p95",
    "resource_penalty_max",
    "total_energy_p95",
    "total_energy_max",
    "resource_penalty_to_cost_ratio",
    "flow_penalty_to_cost_ratio",
]


def _spearman(x: pd.Series, y: pd.Series) -> tuple[float, float]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        result = spearmanr(x, y)
    return float(result.statistic), float(result.pvalue)


def _correlation_rows(frame: pd.DataFrame, grouping: str) -> pd.DataFrame:
    rows = []
    groups = [("ALL", frame)] if grouping == "global" else frame.groupby(grouping, sort=False)
    for group_name, group in groups:
        for metric in CORRELATION_METRICS:
            rho, pvalue = _spearman(group["dilution_score"], group[metric])
            rows.append(
                {
                    "grouping": grouping,
                    "group": group_name,
                    "metric": metric,
                    "n": len(group),
                    "spearman_rho": rho,
                    "spearman_pvalue": pvalue,
                }
            )
    return pd.DataFrame(rows)


def _within_base_summary(current: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    merged = current.merge(
        comparison[["task_id", "controlled_energy_span", "controlled_resource_penalty_to_cost_ratio"]],
        on="task_id",
    )
    rows = []
    for base, group in merged.groupby("base_instance_id", sort=False):
        rho_current, _ = _spearman(group.dilution_score, group.energy_span)
        rho_controlled, _ = _spearman(group.dilution_score, group.controlled_energy_span)
        rows.append(
            {
                "base_instance_id": base,
                "size_stratum": group.size_stratum.iloc[0],
                "n_levels": len(group),
                "current_energy_span_min": group.energy_span.min(),
                "current_energy_span_max": group.energy_span.max(),
                "current_energy_span_max_over_min": group.energy_span.max() / group.energy_span.min(),
                "controlled_energy_span_min": group.controlled_energy_span.min(),
                "controlled_energy_span_max": group.controlled_energy_span.max(),
                "controlled_energy_span_max_over_min": (
                    group.controlled_energy_span.max() / group.controlled_energy_span.min()
                ),
                "spearman_dilution_current_span": rho_current,
                "spearman_dilution_controlled_span": rho_controlled,
            }
        )
    return pd.DataFrame(rows)


def _aggregate_scale(frame: pd.DataFrame, tasks: list[Task]) -> dict[str, float]:
    first_tasks: dict[str, Task] = {}
    for task in tasks:
        first_tasks.setdefault(task.base_instance_id, task)
    resources = np.asarray(
        [edge.resource for task in first_tasks.values() for edge in task.graph.edges], dtype=float
    )
    return {
        "edge_resource_min": float(resources.min()),
        "edge_resource_median": float(np.median(resources)),
        "edge_resource_max": float(resources.max()),
        "budget_min": float(frame.budget.min()),
        "budget_median": float(frame.budget.median()),
        "budget_max": float(frame.budget.max()),
        "resource_penalty_p95_min": float(frame.resource_penalty_p95.min()),
        "resource_penalty_p95_median": float(frame.resource_penalty_p95.median()),
        "resource_penalty_p95_max": float(frame.resource_penalty_p95.max()),
        "energy_span_min": float(frame.energy_span.min()),
        "energy_span_median": float(frame.energy_span.median()),
        "energy_span_max": float(frame.energy_span.max()),
        "resource_penalty_to_cost_ratio_min": float(frame.resource_penalty_to_cost_ratio.min()),
        "resource_penalty_to_cost_ratio_median": float(frame.resource_penalty_to_cost_ratio.median()),
        "resource_penalty_to_cost_ratio_max": float(frame.resource_penalty_to_cost_ratio.max()),
        "flow_penalty_to_cost_ratio_min": float(frame.flow_penalty_to_cost_ratio.min()),
        "flow_penalty_to_cost_ratio_median": float(frame.flow_penalty_to_cost_ratio.median()),
        "flow_penalty_to_cost_ratio_max": float(frame.flow_penalty_to_cost_ratio.max()),
    }


def _finish_figure(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def _make_figures(
    v1: pd.DataFrame,
    current: pd.DataFrame,
    comparison: pd.DataFrame,
) -> list[str]:
    output = RESULT_DIR / "hamiltonian_scale_figures"
    figures = []
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for size, group in current.groupby("size_stratum", sort=False):
        ax.scatter(group.dilution_score, group.energy_span, label=size, alpha=0.65)
    ax.set_yscale("log")
    ax.set_xlabel("Dilution score")
    ax.set_ylabel("Current total-energy span")
    ax.set_title("Dilution vs current Hamiltonian span")
    ax.legend()
    figures.append(_finish_figure(fig, output / "figure1_dilution_vs_current_energy_span.png"))

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for size, group in current.groupby("size_stratum", sort=False):
        ax.scatter(
            group.dilution_score,
            group.resource_penalty_to_cost_ratio,
            label=size,
            alpha=0.65,
        )
    ax.set_yscale("log")
    ax.set_xlabel("Dilution score")
    ax.set_ylabel("Weighted resource-penalty p95 / routing-cost p95")
    ax.set_title("Dilution vs resource penalty dominance")
    ax.legend()
    figures.append(_finish_figure(fig, output / "figure2_dilution_vs_resource_cost_ratio.png"))

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4))
    axes[0].boxplot([v1.energy_span, current.energy_span], tick_labels=["v1", "v2"])
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Current-contract energy span")
    axes[0].set_title("Hamiltonian span")
    axes[1].boxplot(
        [v1.resource_penalty_to_cost_ratio, current.resource_penalty_to_cost_ratio],
        tick_labels=["v1", "v2"],
    )
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Weighted resource penalty / cost")
    axes[1].set_title("Penalty dominance")
    figures.append(_finish_figure(fig, output / "figure3_v1_vs_v2_scale_distributions.png"))

    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    ax.scatter(comparison.current_energy_span, comparison.controlled_energy_span, alpha=0.55)
    lower = min(comparison.current_energy_span.min(), comparison.controlled_energy_span.min())
    upper = max(comparison.current_energy_span.max(), comparison.controlled_energy_span.max())
    ax.plot([lower, upper], [lower, upper], linestyle="--", color="black", linewidth=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Current raw-contract energy span")
    ax.set_ylabel("Scale-controlled energy span")
    ax.set_title("Raw vs scale-controlled contract")
    figures.append(_finish_figure(fig, output / "figure4_current_vs_controlled_span.png"))

    merged = current.merge(
        comparison[["task_id", "controlled_energy_span"]], on="task_id"
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5), sharex=True)
    for _, group in merged.groupby("base_instance_id", sort=False):
        group = group.sort_values("dilution_score")
        axes[0].plot(
            group.dilution_score,
            group.energy_span / group.energy_span.median(),
            alpha=0.45,
            linewidth=1,
        )
        axes[1].plot(
            group.dilution_score,
            group.controlled_energy_span / group.controlled_energy_span.median(),
            alpha=0.45,
            linewidth=1,
        )
    axes[0].set_title("Current contract")
    axes[1].set_title("Scale-controlled contract")
    for ax in axes:
        ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
        ax.set_xlabel("Dilution score")
        ax.set_ylabel("Span / within-base median")
    fig.suptitle("Within-base energy-scale variation across stress levels")
    figures.append(_finish_figure(fig, output / "figure5_within_base_scale_variation.png"))
    return figures


def _markdown_table(frame: pd.DataFrame, columns: list[str], formats: dict[str, str] | None = None) -> list[str]:
    formats = formats or {}
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in frame[columns].itertuples(index=False, name=None):
        values = []
        for column, value in zip(columns, row):
            if isinstance(value, (float, np.floating)):
                values.append(format(value, formats.get(column, ".6g")))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def _write_reports(
    current: pd.DataFrame,
    comparison: pd.DataFrame,
    v1_scale: dict[str, float],
    v2_scale: dict[str, float],
    global_correlations: pd.DataFrame,
    size_correlations: pd.DataFrame,
    base_correlation_summary: pd.DataFrame,
    within: pd.DataFrame,
    figures: list[str],
    verdict: str,
) -> None:
    current_optimal = int(current.penalty_ground_state_original_optimal.sum())
    controlled_optimal = int(comparison.controlled_ground_state_original_optimal.sum())
    span_factor = v2_scale["energy_span_median"] / v1_scale["energy_span_median"]
    ratio_factor = (
        v2_scale["resource_penalty_to_cost_ratio_median"]
        / v1_scale["resource_penalty_to_cost_ratio_median"]
    )
    within_current = within.current_energy_span_max_over_min
    within_controlled = within.controlled_energy_span_max_over_min
    gamma = _gamma_initialization_summary()
    lines = [
        "# Hamiltonian scale and penalty-confound audit",
        "",
        "Phase 0.6 reads the frozen v1/v2 tasks and exact references. It does not execute QAOA.",
        "No existing result row, task manifest, or evidence file was modified.",
        "",
        f"**Scale audit verdict: `{verdict}`.**",
        "",
        "## Exact ground-state correctness",
        "",
        f"- Current medium contract exact-original-optimal: **{current_optimal}/140**.",
        f"- Scale-controlled prospective contract exact-original-optimal: **{controlled_optimal}/140**.",
        f"- Current valid ground states: {int(current.penalty_ground_state_valid.sum())}/140.",
        f"- Current resource-feasible ground states: "
        f"{int(current.penalty_ground_state_resource_feasible.sum())}/140.",
        f"- Controlled flow/resource classification unchanged: "
        f"{int((comparison.controlled_flow_classification_unchanged & comparison.controlled_resource_classification_unchanged).sum())}/140.",
        "",
        "Any count below 140 is a penalty-correctness failure, not a QAOA result.",
        "",
        "## Scale-confound evidence",
        "",
        f"- Current v2 energy-span range: {current.energy_span.min():.6g} to "
        f"{current.energy_span.max():.6g}; median {current.energy_span.median():.6g}.",
        f"- Current weighted resource-penalty/cost ratio range: "
        f"{current.resource_penalty_to_cost_ratio.min():.6g} to "
        f"{current.resource_penalty_to_cost_ratio.max():.6g}.",
        f"- V2/v1 median energy-span factor: {span_factor:.6g}.",
        f"- V2/v1 median resource-penalty/cost-ratio factor: {ratio_factor:.6g}.",
        f"- Within-base max/min span ratio, current: min {within_current.min():.6g}, "
        f"median {within_current.median():.6g}, max {within_current.max():.6g}.",
        f"- Within-base max/min span ratio, controlled: min {within_controlled.min():.6g}, "
        f"median {within_controlled.median():.6g}, max {within_controlled.max():.6g}.",
        "",
        "Correlations below are diagnostics, not causal claims.",
        "",
        "### Global Spearman correlations with dilution score",
        "",
        *_markdown_table(
            global_correlations,
            ["metric", "n", "spearman_rho", "spearman_pvalue"],
        ),
        "",
        "### Size-stratified Spearman correlations",
        "",
        *_markdown_table(
            size_correlations,
            ["group", "metric", "n", "spearman_rho", "spearman_pvalue"],
        ),
        "",
        "### Within-base-graph Spearman summary",
        "",
        "Each metric was evaluated separately inside every base graph. Undefined correlations",
        "occur when the numerical component is constant across that graph's stress levels.",
        "",
        *_markdown_table(
            base_correlation_summary,
            [
                "metric",
                "base_graphs",
                "defined_correlations",
                "rho_min",
                "rho_median",
                "rho_max",
            ],
        ),
        "",
        "## V1 vs v2 current-contract scale",
        "",
        "| Metric | v1 | v2 |",
        "|---|---:|---:|",
    ]
    scale_metrics = [
        "edge_resource_min",
        "edge_resource_median",
        "edge_resource_max",
        "budget_min",
        "budget_median",
        "budget_max",
        "resource_penalty_p95_median",
        "energy_span_min",
        "energy_span_median",
        "energy_span_max",
        "resource_penalty_to_cost_ratio_median",
        "flow_penalty_to_cost_ratio_median",
    ]
    for metric in scale_metrics:
        lines.append(f"| {metric} | {v1_scale[metric]:.8g} | {v2_scale[metric]:.8g} |")
    lines.extend(
        [
            "",
            "The 1–1000 redesign leaves feasible-set semantics intact but materially enlarges the",
            "raw squared-resource component and phase scale. Tighter budgets within a fixed graph",
            "also increase raw excess, so numerical scale moves with dilution under the current form.",
            "",
            "## Cost-phase scale",
            "",
            f"Pilot initial gammas are sampled from {gamma['gamma_initial_support']}; observed frozen "
            f"initial values span {gamma['gamma_initial_min']:.6g} to {gamma['gamma_initial_max']:.6g} "
            f"with median {gamma['gamma_initial_median']:.6g}. {gamma['optimizer_parameter_bounds']}.",
            f"Current median-gamma raw phase spans range from "
            f"{current.initial_phase_span_median.min():.6g} to "
            f"{current.initial_phase_span_median.max():.6g} radians.",
            f"Controlled median-gamma phase spans range from "
            f"{comparison.controlled_initial_phase_span_median.min():.6g} to "
            f"{comparison.controlled_initial_phase_span_median.max():.6g} radians.",
            "These are numerical phase spans only; no barren-plateau or ruggedness theorem is claimed.",
            "",
            "## Prospective scale-controlled contract",
            "",
            "```text",
            "P_resource = 1[excess>0] + min((excess / sum_edge_resources)^2, 1)",
            "P_flow     = 1[flow_raw>0] + min(flow_raw / max_x(flow_raw), 1)",
            "E_control  = routing_cost + 172 P_flow + 172 P_resource",
            "```",
            "",
            "The scales are shared by all stress levels of the same base graph. Both controlled",
            "components are zero exactly for their original valid class and lie in `(1,2]` for any",
            "violation. The global coefficient 172 is one above the declared generator-wide routing",
            "cost bound `19 edges × cost 9 = 171`; it was not chosen from QAOA outcomes.",
            "",
            "## Within-base-graph scale isolation",
            "",
            *_markdown_table(
                within,
                [
                    "base_instance_id",
                    "size_stratum",
                    "n_levels",
                    "current_energy_span_max_over_min",
                    "controlled_energy_span_max_over_min",
                    "spearman_dilution_current_span",
                    "spearman_dilution_controlled_span",
                ],
            ),
            "",
            "## Recommendation and execution status",
            "",
            "Freeze `penalty_contract_v2_scale_controlled` for the future Phase 1 pilot.",
            "The current medium contract remains historical and is not overwritten.",
            "",
            "**Phase 1 executed: false.**",
            "",
            "## Figures",
            "",
            *[f"- `{Path(path).relative_to(PROJECT_ROOT)}`" for path in figures],
        ]
    )
    (RESULT_DIR / "HAMILTONIAN_SCALE_AUDIT.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    doc_lines = [
        "# Penalty scale control",
        "",
        "The prospective `penalty_contract_v2_scale_controlled` isolates feasible-space dilution",
        "from the raw magnitude of v2 integer resources. It does not replace the historical medium",
        "contract and was selected without QAOA outcomes.",
        "",
        "## Frozen formula",
        "",
        "```text",
        "S_resource = sum of edge resources for the base graph",
        "P_resource = 1[resource_excess > 0] + min((resource_excess/S_resource)^2, 1)",
        "S_flow = exact max flow_penalty_raw over the fixed edge-bit representation",
        "P_flow = 1[flow_penalty_raw > 0] + min(flow_penalty_raw/S_flow, 1)",
        "E = routing_cost + 172*P_flow + 172*P_resource",
        "```",
        "",
        "The hard indicator preserves constraint classification even for the smallest positive",
        "violation. The bounded severity retains ordering information without allowing resource units",
        "to dominate the diagonal scale. Base-graph scales are reused unchanged across stress budgets.",
        "",
        "## Exhaustive validation",
        "",
        f"- Flow/resource classification preserved: "
        f"{int((comparison.controlled_flow_classification_unchanged & comparison.controlled_resource_classification_unchanged).sum())}/140 tasks.",
        f"- Valid, resource-feasible, exact-original-optimal ground state: {controlled_optimal}/140 tasks.",
        f"- Current contract exact-original-optimal ground state: {current_optimal}/140 tasks.",
        "- QAOA outcomes consulted: no.",
        "- Phase 1 executed: false.",
    ]
    (PROJECT_ROOT / "docs" / "PENALTY_SCALE_CONTROL.md").write_text(
        "\n".join(doc_lines) + "\n", encoding="utf-8"
    )


def run_phase06() -> dict[str, Any]:
    started = time.perf_counter()
    hashes_before = verify_phase06_frozen_evidence()
    v2_tasks, v2_char = _load_v2_tasks()
    current, comparison = _audit_task_collection(v2_tasks, v2_char, include_controlled=True)
    assert comparison is not None
    v1_tasks, v1_char = _load_v1_tasks()
    v1_current, _ = _audit_task_collection(v1_tasks, v1_char, include_controlled=False)

    atomic_write_csv(RESULT_DIR / "hamiltonian_scale_audit.csv", current)
    atomic_write_csv(RESULT_DIR / "penalty_contract_comparison.csv", comparison)
    global_correlations = _correlation_rows(current, "global")
    size_correlations = _correlation_rows(current, "size_stratum")
    base_correlations = _correlation_rows(current, "base_instance_id")
    base_correlation_summary = (
        base_correlations.groupby("metric", sort=False)
        .agg(
            base_graphs=("group", "size"),
            defined_correlations=("spearman_rho", "count"),
            rho_min=("spearman_rho", "min"),
            rho_median=("spearman_rho", "median"),
            rho_max=("spearman_rho", "max"),
        )
        .reset_index()
    )
    within = _within_base_summary(current, comparison)
    v1_scale = _aggregate_scale(v1_current, v1_tasks)
    v2_scale = _aggregate_scale(current, v2_tasks)
    current_optimal = int(current.penalty_ground_state_original_optimal.sum())
    controlled_optimal = int(comparison.controlled_ground_state_original_optimal.sum())
    scale_factor = v2_scale["energy_span_median"] / v1_scale["energy_span_median"]
    ratio_factor = (
        v2_scale["resource_penalty_to_cost_ratio_median"]
        / v1_scale["resource_penalty_to_cost_ratio_median"]
    )
    materially_scaled = scale_factor >= 10.0 or ratio_factor >= 10.0
    if controlled_optimal < len(comparison):
        verdict = "PENALTY_FORMULATION_REDESIGN_REQUIRED"
    elif materially_scaled:
        verdict = "SCALE_CONTROL_RECOMMENDED"
    else:
        verdict = "CURRENT_CONTRACT_SAFE"
    figures = _make_figures(v1_current, current, comparison)
    _write_reports(
        current,
        comparison,
        v1_scale,
        v2_scale,
        global_correlations,
        size_correlations,
        base_correlation_summary,
        within,
        figures,
        verdict,
    )
    hashes_after = verify_phase06_frozen_evidence()
    if hashes_before != hashes_after:
        raise AssertionError("frozen evidence changed during Phase 0.6")
    return {
        "verdict": verdict,
        "task_count": len(current),
        "current_exact_optimal": current_optimal,
        "controlled_exact_optimal": controlled_optimal,
        "current_energy_span_range": [float(current.energy_span.min()), float(current.energy_span.max())],
        "current_resource_ratio_range": [
            float(current.resource_penalty_to_cost_ratio.min()),
            float(current.resource_penalty_to_cost_ratio.max()),
        ],
        "v2_over_v1_median_energy_span_factor": scale_factor,
        "v2_over_v1_median_resource_ratio_factor": ratio_factor,
        "phase1_executed": False,
        "runtime_s": time.perf_counter() - started,
    }
