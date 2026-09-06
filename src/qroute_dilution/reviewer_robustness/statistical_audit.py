"""Task-versus-graph clustered reconstruction without changing frozen inference."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, atomic_write_text
from qroute_dilution.phase2_statistics import exact_sign_flip_pvalue

from .common import REVIEW_ROOT, load_json
from .statistics import bootstrap_mean_ci


R0_ROOT = REVIEW_ROOT / "R0"


def _effect_rows(frame: pd.DataFrame, source: str, value_column: str) -> pd.DataFrame:
    subset = frame[frame.objective_id.isin(["O0", "O3"])].copy()
    pivot = subset.pivot(
        index=["task_id", "base_graph_id"], columns="objective_id", values=value_column
    ).reset_index()
    if len(pivot) * 2 != len(subset):
        raise RuntimeError(f"{source} O0/O3 pairing is incomplete")
    pivot["delta_G_feas"] = pivot.O3 - pivot.O0
    pivot["source"] = source
    return pivot


def run_statistical_audit() -> pd.DataFrame:
    discovery_path = (
        PROJECT_ROOT / "results" / "phase1_2_objective_alignment" / "objective_results.csv"
    )
    heldout_path = (
        PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "p3_objective_results.csv"
    )
    discovery = _effect_rows(
        pd.read_csv(discovery_path), "DISCOVERY", "log_feasibility_gain"
    )
    heldout = _effect_rows(
        pd.read_csv(heldout_path), "HELDOUT", "log_feasibility_gain"
    )
    all_effects = pd.concat([discovery, heldout], ignore_index=True)
    output_rows: list[dict[str, Any]] = []
    for offset, (source, task) in enumerate(all_effects.groupby("source", sort=True)):
        graph = (
            task.groupby("base_graph_id", as_index=False)
            .agg(delta_G_feas=("delta_G_feas", "mean"), n_tasks=("task_id", "nunique"))
        )
        task_summary = bootstrap_mean_ci(
            task.delta_G_feas.to_numpy(dtype=float),
            resamples=20000,
            seed=2026090450 + offset,
        )
        graph_summary = bootstrap_mean_ci(
            graph.delta_G_feas.to_numpy(dtype=float),
            resamples=20000,
            seed=2026090460 + offset,
        )
        for unit, summary, n_units in (
            ("task_id", task_summary, len(task)),
            ("base_graph_id", graph_summary, len(graph)),
        ):
            output_rows.append(
                {
                    "source": source,
                    "estimand": "O3_minus_O0_G_feas",
                    "sampling_unit": unit,
                    "n_units": n_units,
                    "task_count": len(task),
                    "graph_count": len(graph),
                    "effect_mean": summary["mean"],
                    "effect_median": summary["median"],
                    "bootstrap_ci_lower": summary["ci_lower"],
                    "bootstrap_ci_upper": summary["ci_upper"],
                    "bootstrap_se": summary["bootstrap_se"],
                    "exact_one_sided_sign_flip_p": (
                        exact_sign_flip_pvalue(graph.delta_G_feas.to_numpy(dtype=float))
                        if unit == "base_graph_id"
                        else math.nan
                    ),
                    "inferential_role": (
                        "POST_HOC_GRAPH_CLUSTER_ROBUSTNESS"
                        if unit == "base_graph_id"
                        else "DESCRIPTIVE_TASK_LEVEL_COMPARISON"
                    ),
                }
            )
    output = pd.DataFrame(output_rows)
    atomic_write_csv(R0_ROOT / "graph_clustered_effects.csv", output)
    heldout_stored = load_json(
        PROJECT_ROOT / "results" / "phase2_confirmatory_v1" / "summary.json"
    )["confirmatory_inference"]["H1"]
    rebuilt = output[
        (output.source == "HELDOUT") & (output.sampling_unit == "base_graph_id")
    ].iloc[0]
    matches = abs(float(rebuilt.effect_mean) - float(heldout_stored["effect_mean"])) <= 1e-12
    discovery_task = output[
        (output.source == "DISCOVERY") & (output.sampling_unit == "task_id")
    ].iloc[0]
    discovery_graph = output[
        (output.source == "DISCOVERY") & (output.sampling_unit == "base_graph_id")
    ].iloc[0]
    heldout_task = output[
        (output.source == "HELDOUT") & (output.sampling_unit == "task_id")
    ].iloc[0]
    report = f"""# Statistical audit — task rows versus graph clusters

## Outcome

Existing confirmatory inference is already graph-level and does not require correction. The independent unit in frozen Phase 2 is `base_graph_id`; its exact sign-flip test, graph bootstrap, and Holm-corrected H1/H2 family remain canonical and unchanged.

## O3−O0 feasibility-gain comparison

| Source | Unit | n | Mean effect | 95% bootstrap CI |
|---|---|---:|---:|---:|
| Discovery | task | {int(discovery_task.n_units)} | {discovery_task.effect_mean:.6f} | [{discovery_task.bootstrap_ci_lower:.6f}, {discovery_task.bootstrap_ci_upper:.6f}] |
| Discovery | graph | {int(discovery_graph.n_units)} | {discovery_graph.effect_mean:.6f} | [{discovery_graph.bootstrap_ci_lower:.6f}, {discovery_graph.bootstrap_ci_upper:.6f}] |
| Held-out | task | {int(heldout_task.n_units)} | {heldout_task.effect_mean:.6f} | [{heldout_task.bootstrap_ci_lower:.6f}, {heldout_task.bootstrap_ci_upper:.6f}] |
| Held-out | graph | {int(rebuilt.n_units)} | {rebuilt.effect_mean:.6f} | [{rebuilt.bootstrap_ci_lower:.6f}, {rebuilt.bootstrap_ci_upper:.6f}] |

The held-out graph mean {'exactly matches' if matches else 'DOES NOT MATCH'} the frozen H1 effect ({heldout_stored['effect_mean']:.6f}) within 1e-12. The interval above is a new two-sided robustness interval and does not replace the frozen one-sided bound or p-value.

## Sampling-unit inventory

- Discovery has 56 tasks nested in 10 graphs; its Phase-1 result was exploratory/descriptive.
- Held-out has 84 tasks nested in 15 graphs; the preregistered Phase-2 inference averages within graph before inference.
- Phase 3 has 180 tasks nested in 30 graphs, six tasks per graph; its frozen inference operates on graph-level fitted exponents and grouped resampling.
- New B1, A1, A2, and A3 summaries use task rows descriptively and paired graph aggregation for robustness intervals.

No historical p-value, confidence bound, hypothesis family, or headline effect is modified by this audit.
"""
    atomic_write_text(R0_ROOT / "statistical_audit.md", report)
    if not matches:
        raise RuntimeError("rebuilt held-out graph effect differs from frozen H1")
    return output
