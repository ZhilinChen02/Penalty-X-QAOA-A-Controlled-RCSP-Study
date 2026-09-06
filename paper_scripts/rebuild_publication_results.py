#!/usr/bin/env python3
"""Rebuild publication statistics and assets from frozen row-level evidence.

This entry point never runs a QAOA optimizer.  It independently reconstructs
the headline statistics from canonical CSV rows, compares them with frozen
summary artifacts and manuscript displays, and only then invokes the
presentation-only figure/table and manuscript-audit scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results" / "finalization_audit_v1"

CANONICAL_INPUTS = (
    "configs/phase0_v2_dilution_stress.yaml",
    "configs/penalty_contract_v2_scale_controlled.yaml",
    "configs/phase1_pilot_v1.yaml",
    "configs/phase1_1_optimization_diagnostic.yaml",
    "configs/phase1_2_objective_alignment.yaml",
    "configs/phase2_confirmatory_v1.yaml",
    "configs/phase3_scaling_v1.yaml",
    "data/manifests/phase0_v2_dilution_stress.json",
    "data/manifests/phase1_pilot_v1.json",
    "data/manifests/phase2_confirmatory_v1.json",
    "data/manifests/phase3_scaling_v1/development.json",
    "data/manifests/phase3_scaling_v1/interpolation_holdout.json",
    "data/manifests/phase3_scaling_v1/extrapolation_holdout.json",
    "data/manifests/phase3_scaling_v1/task_universe.json",
    "results/phase0_v2_dilution_stress/task_characterization.csv",
    "results/phase1_pilot_v1/master_seed_level_results.csv",
    "results/phase1_1_optimization_diagnostic/nested_ansatz_identity.csv",
    "results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv",
    "results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv",
    "results/phase1_2_objective_alignment/objective_results.csv",
    "results/phase1_2_objective_alignment/capacity_gap.csv",
    "results/phase2_confirmatory_v1/PREREGISTRATION.md",
    "results/phase2_confirmatory_v1/p3_objective_results.csv",
    "results/phase3_scaling_v1/PREREGISTRATION.md",
    "results/phase3_scaling_v1/canonical_results.csv",
    "results/phase3_scaling_v1/base_graph_exponents.csv",
    "results/phase3_scaling_v1/resource_preflight.csv",
    "results/phase3_scaling_v1/failure_census.csv",
    "results/theory_validation_v3/summary.json",
    "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv",
)

EXACT_COUNT_TOLERANCE = 0.0
AUTHORITATIVE_FLOAT_ATOL = 5e-12


def read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_yaml(relative: str) -> dict[str, Any]:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration is not a mapping: {relative}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hashes() -> dict[str, str]:
    missing = [relative for relative in CANONICAL_INPUTS if not (ROOT / relative).is_file()]
    if missing:
        raise RuntimeError(f"STOP: canonical inputs are missing: {missing}")
    return {relative: sha256(ROOT / relative) for relative in sorted(CANONICAL_INPUTS)}


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def bool_series(values: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def exact_sign_flip_pvalue(contrasts: Iterable[float], null: float) -> float:
    values = np.asarray(tuple(contrasts), dtype=np.float64) - float(null)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("sign-flip contrasts must be a finite vector")
    observed = float(values.mean())
    assignments = np.asarray(
        tuple(itertools.product((-1.0, 1.0), repeat=len(values))),
        dtype=np.float64,
    )
    permuted = assignments @ values / len(values)
    return float(np.mean(permuted >= observed - 1e-15))


def grouped_bootstrap(contrasts: Iterable[float], resamples: int, seed: int) -> dict[str, float]:
    values = np.asarray(tuple(contrasts), dtype=np.float64)
    rng = np.random.default_rng(int(seed))
    indices = rng.integers(0, len(values), size=(int(resamples), len(values)))
    means = values[indices].mean(axis=1)
    return {
        "effect_mean": float(values.mean()),
        "one_sided_95_lower_bound": float(np.quantile(means, 0.05)),
        "bootstrap_standard_error": float(means.std(ddof=1)),
    }


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues, key=lambda key: (pvalues[key], key))
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, key in enumerate(ordered):
        candidate = min(1.0, (len(ordered) - rank) * float(pvalues[key]))
        running = max(running, candidate)
        adjusted[key] = running
    return {key: adjusted[key] for key in pvalues}


def reconstruct_optimizer() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    nested = pd.read_csv(
        ROOT / "results/phase1_1_optimization_diagnostic/nested_ansatz_identity.csv"
    )
    gaps = pd.read_csv(
        ROOT / "results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv"
    )
    continuation = pd.read_csv(
        ROOT
        / "results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv"
    )
    if len(nested) != 168 or len(gaps) != 168 or len(continuation) != 168:
        raise RuntimeError("STOP: optimizer-attribution denominator changed")
    if nested.duplicated(["task_id", "optimizer_seed"]).any():
        raise RuntimeError("STOP: duplicate nested-identity comparison")
    tolerance = float(gaps.comparison_tolerance.iloc[0])
    if not np.allclose(gaps.comparison_tolerance, tolerance, atol=0.0, rtol=0.0):
        raise RuntimeError("STOP: comparison tolerance is not constant")
    certified = gaps.assign(
        certified=(
            gaps.original_p3_objective
            > gaps.embedded_p2_objective + gaps.comparison_tolerance
        )
    )
    failure_keys = certified.loc[certified.certified, ["task_id", "optimizer_seed"]]
    paired = continuation.merge(
        failure_keys.assign(certified=True),
        on=["task_id", "optimizer_seed"],
        how="left",
        validate="one_to_one",
    )
    failure = paired[paired.certified.fillna(False)].copy()
    objective_repairs = int(
        (failure.objective_final < failure.original_p3_objective - tolerance).sum()
    )
    feasibility_improvements = int(
        (failure.G_feas_final > failure.original_p3_G_feas + tolerance).sum()
    )
    lower_energy_lower_gain = int(
        (
            (continuation.original_p3_objective < continuation.objective_final - tolerance)
            & (continuation.original_p3_G_feas < continuation.G_feas_final - tolerance)
        ).sum()
    )
    result = {
        "comparison_tolerance": tolerance,
        "nested_identity_denominator": int(len(nested)),
        "nested_identity_pass_count": int(bool_series(nested.identity_pass).sum()),
        "nested_identity_max_abs_objective_difference": float(
            np.abs(nested.objective_difference).max()
        ),
        "nested_identity_max_abs_state_difference": float(
            np.abs(nested.state_max_abs_difference).max()
        ),
        "certified_optimizer_failures": int(certified.certified.sum()),
        "certified_optimizer_failure_denominator": int(len(certified)),
        "continuation_objective_repairs": objective_repairs,
        "continuation_objective_repair_denominator": int(len(failure)),
        "continuation_feasibility_improvements": feasibility_improvements,
        "continuation_feasibility_improvement_denominator": int(len(failure)),
        "lower_energy_and_lower_feasibility_gain": lower_energy_lower_gain,
        "lower_energy_and_lower_feasibility_gain_denominator": int(len(continuation)),
    }
    rows = [
        {
            "table": "optimizer_attribution",
            "row": name,
            "metric": "count",
            "value": value,
            "denominator": denominator,
            "unit": "seed_level_comparison",
            "source": "Phase 1.1 row-level CSVs",
        }
        for name, value, denominator in (
            ("nested_zero_layer_identity", result["nested_identity_pass_count"], 168),
            ("certified_optimizer_failure", result["certified_optimizer_failures"], 168),
            ("continuation_objective_repair", objective_repairs, len(failure)),
            ("continuation_feasibility_improvement", feasibility_improvements, len(failure)),
            ("lower_energy_lower_feasibility_gain", lower_energy_lower_gain, 168),
        )
    ]
    return result, rows


def reconstruct_discovery() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    results = pd.read_csv(
        ROOT / "results/phase1_2_objective_alignment/objective_results.csv"
    )
    manifest = read_json("data/manifests/phase1_pilot_v1.json")
    expected_objectives = {"O0", "O1", "O2", "O3"}
    if set(results.objective_id) != expected_objectives:
        raise RuntimeError("STOP: discovery objective family changed")
    counts = results.groupby("task_id").objective_id.nunique()
    if len(counts) != 56 or not (counts == 4).all():
        raise RuntimeError("STOP: discovery task/objective matrix changed")
    wide = results.pivot(index="task_id", columns="objective_id", values="log_feasibility_gain")
    capacity_gap = wide.O2 - wide.O0
    closure = (wide.O3 - wide.O0) / capacity_gap
    eligible = capacity_gap > 0.0
    closure_values = closure[eligible]
    alphas = results.loc[results.objective_id == "O3", "cvar_alpha"].dropna().unique()
    if len(alphas) != 1:
        raise RuntimeError("STOP: discovery CVaR alpha is not unique")
    result = {
        "task_count": int(results.task_id.nunique()),
        "base_graph_count": int(results.base_instance_id.nunique()),
        "manifest_task_count": int(manifest["task_count"]),
        "cvar_alpha": float(alphas[0]),
        "positive_capacity_gap_task_count": int(eligible.sum()),
        "median_capacity_gap_decades": float(np.median(capacity_gap)),
        "median_cvar_residual_gap_decades": float(np.median(wide.O2 - wide.O3)),
        "median_cvar_gap_closure_fraction": float(np.median(closure_values)),
        "median_cvar_gap_closure_percent": float(100.0 * np.median(closure_values)),
    }
    rows = [
        {
            "table": "objective_discovery",
            "row": "O2_minus_O0_capacity_gap",
            "metric": "median",
            "value": result["median_capacity_gap_decades"],
            "denominator": 56,
            "unit": "decades_G_feas",
            "source": "Phase 1.2 objective_results.csv",
        },
        {
            "table": "objective_discovery",
            "row": "O3_closure_of_O2_minus_O0_gap",
            "metric": "median",
            "value": result["median_cvar_gap_closure_percent"],
            "denominator": result["positive_capacity_gap_task_count"],
            "unit": "percent",
            "source": "Phase 1.2 objective_results.csv",
        },
    ]
    return result, rows


def reconstruct_heldout() -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, list[dict[str, Any]]]:
    results = pd.read_csv(ROOT / "results/phase2_confirmatory_v1/p3_objective_results.csv")
    manifest = read_json("data/manifests/phase2_confirmatory_v1.json")
    config = read_yaml("configs/phase2_confirmatory_v1.yaml")
    primary = results[results.objective_id.isin(["O0", "O2", "O3"])].copy()
    if len(primary) != 252 or primary.task_id.nunique() != 84:
        raise RuntimeError("STOP: held-out task/objective denominator changed")
    if not bool_series(primary.paired_analysis_eligible).all():
        raise RuntimeError("STOP: held-out primary row is not paired-analysis eligible")
    task_counts = primary.groupby("task_id").objective_id.nunique()
    if not (task_counts == 3).all():
        raise RuntimeError("STOP: held-out task/objective matrix is incomplete")

    identity = [
        "task_id",
        "base_graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "dilution_score",
        "feasible_state_fraction",
    ]
    metrics = ["log_feasibility_gain", "p_feas", "p_opt", "p_opt_given_feasible"]
    task = primary.pivot(index=identity, columns="objective_id", values=metrics)
    task.columns = [f"{metric}_{objective}" for metric, objective in task.columns]
    task = task.reset_index()
    task["Delta1_CVAR_MEAN"] = task.log_feasibility_gain_O3 - task.log_feasibility_gain_O0
    task["Delta2_CVAR_CAPACITY"] = task.log_feasibility_gain_O3 - task.log_feasibility_gain_O2
    tolerance = float(config["numerical_tolerance"])
    task["O3_popt_win"] = task.p_opt_O3 > task.p_opt_O0 + tolerance
    task["O3_both_pfeas_popt_win"] = (
        (task.p_feas_O3 > task.p_feas_O0 + tolerance)
        & (task.p_opt_O3 > task.p_opt_O0 + tolerance)
    )

    records: list[dict[str, Any]] = []
    for base_instance_id in manifest["base_graph_ids"]:
        group = task[task.base_instance_id == base_instance_id]
        if group.empty:
            raise RuntimeError(f"STOP: missing held-out graph {base_instance_id}")
        records.append(
            {
                "base_graph_id": str(group.base_graph_id.iloc[0]),
                "base_instance_id": base_instance_id,
                "size_stratum": str(group.size_stratum.iloc[0]),
                "n_levels": int(len(group)),
                "bar_G_O0": float(group.log_feasibility_gain_O0.mean()),
                "bar_G_O2": float(group.log_feasibility_gain_O2.mean()),
                "bar_G_O3": float(group.log_feasibility_gain_O3.mean()),
            }
        )
    graph = pd.DataFrame(records)
    graph["Delta1_CVAR_MEAN"] = graph.bar_G_O3 - graph.bar_G_O0
    graph["Delta2_CVAR_CAPACITY"] = graph.bar_G_O3 - graph.bar_G_O2
    if len(graph) != 15:
        raise RuntimeError("STOP: held-out graph denominator changed")

    settings = config["primary_inference"]
    resamples = int(settings["bootstrap_resamples"])
    seed = int(settings["bootstrap_seed"])
    margin = -float(config["noninferiority_margin_decades"])
    h1 = grouped_bootstrap(graph.Delta1_CVAR_MEAN, resamples, seed)
    h2 = grouped_bootstrap(graph.Delta2_CVAR_CAPACITY, resamples, seed)
    raw = {
        "H1": exact_sign_flip_pvalue(graph.Delta1_CVAR_MEAN, 0.0),
        "H2": exact_sign_flip_pvalue(graph.Delta2_CVAR_CAPACITY, margin),
    }
    adjusted = holm_adjust(raw)
    h1.update(
        {
            "null_margin": 0.0,
            "raw_p_value": raw["H1"],
            "holm_adjusted_p_value": adjusted["H1"],
            "pass": bool(
                adjusted["H1"] < float(settings["family_alpha"])
                and h1["one_sided_95_lower_bound"] > 0.0
            ),
        }
    )
    h2.update(
        {
            "null_margin": margin,
            "raw_p_value": raw["H2"],
            "holm_adjusted_p_value": adjusted["H2"],
            "pass": bool(
                adjusted["H2"] < float(settings["family_alpha"])
                and h2["one_sided_95_lower_bound"] > margin
            ),
        }
    )
    result = {
        "analysis_unit": "base_graph_id",
        "task_count": int(len(task)),
        "base_graph_count": int(len(graph)),
        "bootstrap_resamples": resamples,
        "bootstrap_seed": seed,
        "sign_flip_assignments": int(2 ** len(graph)),
        "H1": h1,
        "H2": h2,
        "secondary": {
            "O3_vs_O0_P_opt_wins": int(task.O3_popt_win.sum()),
            "O3_vs_O0_both_Pfeas_Popt_wins": int(task.O3_both_pfeas_popt_win.sum()),
            "denominator": int(len(task)),
        },
    }
    rows: list[dict[str, Any]] = []
    for hypothesis, values in (("H1", h1), ("H2", h2)):
        for metric in (
            "effect_mean",
            "one_sided_95_lower_bound",
            "bootstrap_standard_error",
            "raw_p_value",
            "holm_adjusted_p_value",
            "null_margin",
        ):
            rows.append(
                {
                    "table": "heldout_primary",
                    "row": hypothesis,
                    "metric": metric,
                    "value": values[metric],
                    "denominator": 15,
                    "unit": "decades_or_probability",
                    "source": "Phase 2 p3_objective_results.csv",
                }
            )
    for row, value in (
        ("O3_vs_O0_P_opt_wins", result["secondary"]["O3_vs_O0_P_opt_wins"]),
        (
            "O3_vs_O0_both_Pfeas_Popt_wins",
            result["secondary"]["O3_vs_O0_both_Pfeas_Popt_wins"],
        ),
    ):
        rows.append(
            {
                "table": "heldout_secondary",
                "row": row,
                "metric": "count",
                "value": value,
                "denominator": 84,
                "unit": "task",
                "source": "Phase 2 p3_objective_results.csv",
            }
        )
    return result, task, graph, rows


def fit_scaling_exponents(canonical: pd.DataFrame) -> pd.DataFrame:
    valid = canonical[
        canonical.objective_id.isin(["O0", "O2", "O3"])
        & canonical.execution_status.eq("SUCCESS")
        & ~bool_series(canonical.resource_censored)
    ].copy()
    rows: list[dict[str, Any]] = []
    for (base, objective), group in valid.groupby(["base_graph_id", "objective_id"]):
        group = group[(group.p_feas > 0.0) & np.isfinite(group.p_feas)]
        if len(group) < 5:
            continue
        d = group.dilution_score.to_numpy(dtype=np.float64)
        y = np.log10(group.p_feas.to_numpy(dtype=np.float64))
        design = np.column_stack([np.ones(len(d)), -d])
        intercept, eta = np.linalg.lstsq(design, y, rcond=None)[0]
        rows.append(
            {
                "base_graph_id": base,
                "split": str(group.split.iloc[0]),
                "size_m": int(group.size_m.iloc[0]),
                "objective": objective,
                "n_levels": int(len(group)),
                "eta": float(eta),
                "intercept": float(intercept),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["split", "size_m", "base_graph_id", "objective"], kind="stable"
    ).reset_index(drop=True)


def reconstruct_scaling() -> tuple[dict[str, Any], pd.DataFrame, list[dict[str, Any]]]:
    canonical = pd.read_csv(ROOT / "results/phase3_scaling_v1/canonical_results.csv")
    stored = pd.read_csv(ROOT / "results/phase3_scaling_v1/base_graph_exponents.csv")
    resource = pd.read_csv(ROOT / "results/phase3_scaling_v1/resource_preflight.csv")
    exponents = fit_scaling_exponents(canonical)
    comparison = exponents.merge(
        stored[["base_graph_id", "split", "size_m", "objective", "eta"]].rename(
            columns={"eta": "stored_eta"}
        ),
        on=["base_graph_id", "split", "size_m", "objective"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not comparison._merge.eq("both").all():
        raise RuntimeError("STOP: reconstructed and stored scaling exponent keys differ")
    maximum_eta_difference = float(np.abs(comparison.eta - comparison.stored_eta).max())
    summaries = (
        exponents.groupby(["split", "objective"], as_index=False)
        .agg(mean_eta=("eta", "mean"), graph_count=("base_graph_id", "nunique"))
    )
    m20 = summaries[summaries.split.eq("extrapolation_holdout")].set_index("objective")
    if set(m20.index) != {"O0", "O2", "O3"}:
        raise RuntimeError("STOP: incomplete m=20 objective family")
    preflight22 = resource[resource.size_m.eq(22)]
    rows22 = canonical[canonical.size_m.eq(22)]
    m22_censored = bool(
        len(preflight22) == 1
        and bool_series(preflight22.resource_censored).all()
        and not bool_series(preflight22.resource_guard_pass).any()
        and len(rows22) == 180
        and bool_series(rows22.resource_censored).all()
        and rows22.execution_status.eq("RESOURCE_CENSORED").all()
        and rows22.objective_final.isna().all()
        and rows22.p_feas.isna().all()
        and rows22.terminal_parameters.isna().all()
    )
    result = {
        "exponent_definition": "OLS log10(P_feas) = intercept - eta * dilution_score",
        "reconstructed_graph_objective_exponents": int(len(exponents)),
        "maximum_abs_eta_difference_vs_stored": maximum_eta_difference,
        "m20": {
            objective: {
                "mean_eta": float(m20.loc[objective, "mean_eta"]),
                "graph_count": int(m20.loc[objective, "graph_count"]),
            }
            for objective in ("O0", "O2", "O3")
        },
        "m20_O3_vs_O0_ordering_reversed": bool(
            float(m20.loc["O3", "mean_eta"]) > float(m20.loc["O0", "mean_eta"])
        ),
        "m22_resource_censored": m22_censored,
        "m22_planned_rows": int(len(rows22)),
        "m22_scientific_outcome_rows": int(rows22.p_feas.notna().sum()),
        "global_scaling_law_supported": False,
    }
    rows = [
        {
            "table": "scaling_response",
            "row": "m20",
            "metric": f"mean_eta_{objective}",
            "value": result["m20"][objective]["mean_eta"],
            "denominator": result["m20"][objective]["graph_count"],
            "unit": "graph_level_eta",
            "source": "Phase 3 canonical_results.csv",
        }
        for objective in ("O0", "O2", "O3")
    ]
    rows.extend(
        [
            {
                "table": "scaling_response",
                "row": "m20",
                "metric": "O3_vs_O0_ordering_reversed",
                "value": int(result["m20_O3_vs_O0_ordering_reversed"]),
                "denominator": 1,
                "unit": "boolean",
                "source": "Phase 3 canonical_results.csv",
            },
            {
                "table": "scaling_response",
                "row": "m22",
                "metric": "resource_censored",
                "value": int(result["m22_resource_censored"]),
                "denominator": 1,
                "unit": "boolean",
                "source": "Phase 3 resource_preflight.csv and canonical_results.csv",
            },
        ]
    )
    return result, exponents, rows


def manuscript_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "overleaf").rglob("*.tex"))
    )


def build_claim_audit(
    universe: dict[str, Any],
    optimizer: dict[str, Any],
    discovery: dict[str, Any],
    heldout: dict[str, Any],
    scaling: dict[str, Any],
) -> pd.DataFrame:
    opt_summary = read_json("results/phase1_1_optimization_diagnostic/summary.json")
    held_summary = read_json("results/phase2_confirmatory_v1/summary.json")
    held_stats = read_json("results/phase2_confirmatory_v1/confirmatory_statistics.json")
    scaling_summary = read_json("results/phase3_scaling_v1/summary.json")
    phase0_summary = read_json("results/phase0_v2_dilution_stress/summary.json")
    capacity = pd.read_csv(ROOT / "results/phase1_2_objective_alignment/capacity_gap.csv")
    text = manuscript_text()
    rows: list[dict[str, Any]] = []

    def add(
        claim_id: str,
        reconstructed: float | int | bool,
        authoritative: float | int | bool,
        authoritative_source: str,
        manuscript_pattern: str,
        manuscript_display: float | int | bool,
        manuscript_tolerance: float,
        evidence_stage: str,
    ) -> None:
        is_boolean = isinstance(reconstructed, (bool, np.bool_))
        authoritative_tolerance = EXACT_COUNT_TOLERANCE if (
            is_boolean or isinstance(reconstructed, (int, np.integer))
        ) else AUTHORITATIVE_FLOAT_ATOL
        authoritative_difference = abs(float(reconstructed) - float(authoritative))
        manuscript_difference = abs(float(reconstructed) - float(manuscript_display))
        pattern_found = bool(re.search(manuscript_pattern, text, flags=re.IGNORECASE))
        authoritative_match = authoritative_difference <= authoritative_tolerance
        manuscript_match = pattern_found and manuscript_difference <= manuscript_tolerance
        rows.append(
            {
                "claim_id": claim_id,
                "evidence_stage": evidence_stage,
                "reconstructed_value": reconstructed,
                "authoritative_value": authoritative,
                "authoritative_source": authoritative_source,
                "authoritative_abs_difference": authoritative_difference,
                "authoritative_tolerance": authoritative_tolerance,
                "manuscript_display_value": manuscript_display,
                "manuscript_abs_difference": manuscript_difference,
                "manuscript_tolerance": manuscript_tolerance,
                "manuscript_pattern": manuscript_pattern,
                "manuscript_pattern_found": pattern_found,
                "status": "PASS" if authoritative_match and manuscript_match else "MISMATCH",
            }
        )

    add("task_universe_count", universe["task_count"], phase0_summary["task_count"],
        "phase0_v2/summary.json", r"140\s+tasks", 140, 0.0, "PHASE0_V2")
    add("duplicate_primary_feasible_sets", universe["duplicate_primary_feasible_sets"],
        phase0_summary["duplicate_feasible_set_count"], "phase0_v2/summary.json",
        r"(?:no|zero|0)\s+duplicate", 0, 0.0, "PHASE0_V2")
    add("nested_identity", optimizer["nested_identity_pass_count"],
        opt_summary["validation"]["nested_identity_rows"], "phase1_1/summary.json",
        r"168/168", 168, 0.0, "PHASE1_1")
    add("certified_optimizer_failures", optimizer["certified_optimizer_failures"],
        opt_summary["original_p3_optimizer_adequacy"]["worse_than_embedded_count"],
        "phase1_1/summary.json", r"(?:29/168|29\s+(?:of|out of)\s+168)", 29, 0.0, "PHASE1_1")
    add("continuation_objective_repairs", optimizer["continuation_objective_repairs"],
        opt_summary["original_p3_optimizer_adequacy"]["failed_original_runs_recovered_to_lower_objective_by_continuation"],
        "phase1_1/summary.json", r"29/29", 29, 0.0, "PHASE1_1")
    add("continuation_feasibility_improvements", optimizer["continuation_feasibility_improvements"],
        opt_summary["original_p3_optimizer_adequacy"]["failed_original_runs_with_higher_G_under_continuation"],
        "phase1_1/summary.json", r"27/29", 27, 0.0, "PHASE1_1")
    add("energy_feasibility_mismatch", optimizer["lower_energy_and_lower_feasibility_gain"],
        opt_summary["continuation"]["random_lower_objective_but_lower_G_count"],
        "phase1_1/summary.json", r"(?:82/168|82\s+(?:of|out of)\s+168)", 82, 0.0, "PHASE1_1")
    stored_closure = float(np.nanmedian(capacity.cvar_gap_closure_fraction)) * 100.0
    add("discovery_cvar_gap_closure_percent", discovery["median_cvar_gap_closure_percent"],
        stored_closure, "phase1_2/capacity_gap.csv", r"97\.9\\%", 97.9, 0.050001, "PHASE1_2_DISCOVERY")
    for hypothesis, metric, display, tolerance, pattern in (
        ("H1", "effect_mean", 0.3547, 0.000050001, r"0\.3547"),
        ("H1", "one_sided_95_lower_bound", 0.2374, 0.000050001, r"0\.2374"),
        ("H1", "holm_adjusted_p_value", 0.000244, 0.00000050001, r"(?:0\.000244|2\.44(?:\\times|e)\s*10\^?\{?-4\}?)"),
        ("H2", "effect_mean", -0.0086, 0.000050001, r"-0\.0086"),
        ("H2", "one_sided_95_lower_bound", -0.0360, 0.000050001, r"-0\.0360"),
    ):
        add(f"heldout_{hypothesis}_{metric}", heldout[hypothesis][metric],
            held_stats[hypothesis][metric], "phase2/confirmatory_statistics.json",
            pattern, display, tolerance, "PHASE2_HELDOUT")
    add("heldout_H2_margin", heldout["H2"]["null_margin"],
        held_stats["H2"]["null_margin"], "phase2/confirmatory_statistics.json",
        r"-0\.10", -0.10, 0.0000001, "PHASE2_HELDOUT")
    add("heldout_Popt_wins", heldout["secondary"]["O3_vs_O0_P_opt_wins"],
        held_summary["routing_quality"]["O3_vs_O0_P_opt_wins"], "phase2/summary.json",
        r"(?:80/84|80\s+(?:of|out of)\s+84)", 80, 0.0, "PHASE2_SECONDARY")
    add("heldout_both_wins", heldout["secondary"]["O3_vs_O0_both_Pfeas_Popt_wins"],
        held_summary["routing_quality"]["O3_vs_O0_both_Pfeas_Popt_greater"], "phase2/summary.json",
        r"(?:79/84|79\s+(?:of|out of)\s+84|79\s+tasks)", 79, 0.0, "PHASE2_SECONDARY")
    for objective, display in (("O0", 0.6150), ("O2", 0.7885), ("O3", 1.2821)):
        add(f"m20_mean_eta_{objective}", scaling["m20"][objective]["mean_eta"],
            scaling_summary["exponent_summaries"]["extrapolation_holdout"][objective]["mean"],
            "phase3/summary.json", rf"{display:.4f}", display, 0.000050001, "PHASE3_SCALING")
    add("m20_ordering_reversal", scaling["m20_O3_vs_O0_ordering_reversed"], True,
        "phase3 canonical exponents", r"m=20[^\n]{0,160}(?:revers|ordering)", True, 0.0, "PHASE3_SCALING")
    add("m22_resource_censor", scaling["m22_resource_censored"],
        bool(scaling_summary["resource_preflight"]["resource_censored_sizes"] == [22]),
        "phase3/summary.json", r"m=22[^\n]{0,160}(?:censor|resource)", True, 0.0, "PHASE3_SCALING")
    return pd.DataFrame(rows)


def reconstruct_universe() -> dict[str, Any]:
    task = pd.read_csv(ROOT / "results/phase0_v2_dilution_stress/task_characterization.csv")
    manifest = read_json("data/manifests/phase0_v2_dilution_stress.json")
    duplicate_sets = int(task.duplicated(["base_instance_id", "n_feasible_states"]).sum())
    return {
        "task_count": int(task.task_id.nunique()),
        "base_graph_count": int(task.base_instance_id.nunique()),
        "manifest_task_count": int(manifest["task_count"]),
        "duplicate_primary_feasible_sets": duplicate_sets,
        "minimum_feasible_state_fraction": float(task.feasible_state_fraction.min()),
        "maximum_feasible_state_fraction": float(task.feasible_state_fraction.max()),
    }


def compare_graph_rows(graph: pd.DataFrame) -> float:
    stored = pd.read_csv(ROOT / "results/phase2_confirmatory_v1/graph_level_contrasts.csv")
    joined = graph.merge(
        stored[["base_instance_id", "Delta1_CVAR_MEAN", "Delta2_CVAR_CAPACITY"]].rename(
            columns={
                "Delta1_CVAR_MEAN": "stored_Delta1",
                "Delta2_CVAR_CAPACITY": "stored_Delta2",
            }
        ),
        on="base_instance_id",
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not joined._merge.eq("both").all():
        raise RuntimeError("STOP: reconstructed and stored held-out graph keys differ")
    return float(
        max(
            np.abs(joined.Delta1_CVAR_MEAN - joined.stored_Delta1).max(),
            np.abs(joined.Delta2_CVAR_CAPACITY - joined.stored_Delta2).max(),
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="rebuild audit statistics without regenerating publication figures/tables",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    hashes_before = canonical_hashes()

    universe = reconstruct_universe()
    optimizer, optimizer_rows = reconstruct_optimizer()
    discovery, discovery_rows = reconstruct_discovery()
    heldout, heldout_tasks, heldout_graphs, heldout_rows = reconstruct_heldout()
    scaling, scaling_exponents, scaling_rows = reconstruct_scaling()
    heldout["maximum_abs_graph_contrast_difference_vs_stored"] = compare_graph_rows(
        heldout_graphs
    )

    headlines = {
        "schema_version": "publication_finalization_reconstruction.v1",
        "evidence_policy": "ROW_LEVEL_FROZEN_INPUTS_NO_OPTIMIZATION",
        "tolerance_policy": {
            "authoritative_float_absolute": AUTHORITATIVE_FLOAT_ATOL,
            "counts_and_verdicts": "exact",
            "manuscript_display": "half unit in the final displayed place plus 1e-9 guard",
        },
        "task_universe": universe,
        "optimizer_attribution": optimizer,
        "objective_discovery": discovery,
        "heldout": heldout,
        "scaling": scaling,
    }
    claim_audit = build_claim_audit(universe, optimizer, discovery, heldout, scaling)

    table_rows = optimizer_rows + discovery_rows + heldout_rows + scaling_rows
    for row in heldout_graphs.itertuples(index=False):
        table_rows.extend(
            [
                {
                    "table": "heldout_graph_contrasts",
                    "row": row.base_instance_id,
                    "metric": "Delta1_CVAR_MEAN",
                    "value": row.Delta1_CVAR_MEAN,
                    "denominator": row.n_levels,
                    "unit": "decades_G_feas",
                    "source": "Phase 2 p3_objective_results.csv",
                },
                {
                    "table": "heldout_graph_contrasts",
                    "row": row.base_instance_id,
                    "metric": "Delta2_CVAR_CAPACITY",
                    "value": row.Delta2_CVAR_CAPACITY,
                    "denominator": row.n_levels,
                    "unit": "decades_G_feas",
                    "source": "Phase 2 p3_objective_results.csv",
                },
            ]
        )

    write_json(OUTPUT / "reconstructed_headlines.json", headlines)
    write_json(OUTPUT / "heldout_statistics_rebuilt.json", heldout)
    write_json(OUTPUT / "scaling_verdict_rebuilt.json", scaling)
    pd.DataFrame(table_rows).to_csv(OUTPUT / "reconstructed_tables.csv", index=False)
    claim_audit.to_csv(OUTPUT / "claim_evidence_audit.csv", index=False)
    heldout_tasks.to_csv(OUTPUT / "heldout_task_metrics_rebuilt.csv", index=False)
    heldout_graphs.to_csv(OUTPUT / "heldout_graph_contrasts_rebuilt.csv", index=False)
    scaling_exponents.to_csv(OUTPUT / "scaling_exponents_rebuilt.csv", index=False)
    (OUTPUT / "hash_manifest.txt").write_text(
        "".join(f"{digest}  {relative}\n" for relative, digest in hashes_before.items()),
        encoding="utf-8",
    )

    mismatches = claim_audit[claim_audit.status.ne("PASS")]
    direct_mismatch = (
        universe["task_count"] != universe["manifest_task_count"]
        or universe["duplicate_primary_feasible_sets"] != 0
        or optimizer["nested_identity_pass_count"] != 168
        or heldout["maximum_abs_graph_contrast_difference_vs_stored"]
        > AUTHORITATIVE_FLOAT_ATOL
        or scaling["maximum_abs_eta_difference_vs_stored"] > AUTHORITATIVE_FLOAT_ATOL
        or not scaling["m20_O3_vs_O0_ordering_reversed"]
        or not scaling["m22_resource_censored"]
    )
    if len(mismatches) or direct_mismatch:
        mismatch_ids = mismatches.claim_id.tolist()
        raise RuntimeError(
            "STOP: reconstruction/manuscript mismatch; no assets were regenerated. "
            f"claim_ids={mismatch_ids}, direct_mismatch={direct_mismatch}"
        )

    if not args.skip_assets:
        subprocess.run(
            [sys.executable, str(ROOT / "paper_scripts/build_paper_assets.py")],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "paper_scripts/audit_manuscript.py")],
            cwd=ROOT,
            check=True,
        )

    hashes_after = canonical_hashes()
    if hashes_after != hashes_before:
        changed = [key for key in hashes_before if hashes_before[key] != hashes_after.get(key)]
        raise RuntimeError(f"STOP: canonical scientific inputs changed during rebuild: {changed}")

    audit_path = OUTPUT / "audit.json"
    audit = read_json("results/finalization_audit_v1/audit.json")
    audit["audit_status"] = "PHASE1_RECONSTRUCTION_PASS"
    audit["reconstruction"] = {
        "canonical_inputs_unchanged": True,
        "claim_evidence_rows": int(len(claim_audit)),
        "claim_evidence_mismatches": 0,
        "heldout_graph_contrast_max_abs_difference": heldout[
            "maximum_abs_graph_contrast_difference_vs_stored"
        ],
        "scaling_exponent_max_abs_difference": scaling[
            "maximum_abs_eta_difference_vs_stored"
        ],
        "assets_rebuilt": not args.skip_assets,
        "optimizer_invoked": False,
    }
    write_json(audit_path, audit)
    print(
        "Publication reconstruction PASS: 140 tasks, 168 optimizer pairs, "
        "84 held-out tasks/15 graphs, and resource-censored scaling verified."
    )


if __name__ == "__main__":
    main()
