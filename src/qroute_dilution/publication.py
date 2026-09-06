"""Frozen-row analysis used by the paper; no optimization or scaling refit.

The numerical functions below retain the original publication reconstruction
implementation. Paths use the repository layout shared with the experiment code.
"""
from __future__ import annotations
import itertools
import json
from pathlib import Path
from typing import Any, Iterable
import numpy as np
import pandas as pd
import yaml
from .io import PROJECT_ROOT
ROOT = PROJECT_ROOT

def read_json(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def read_yaml(relative: str) -> dict[str, Any]:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"configuration is not a mapping: {relative}")
    return value


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


def reconstruct_theory() -> dict:
    """Check numerical bound residuals against frozen summaries, without optimization."""
    import numpy as np
    import pandas as pd

    checks = {}
    specifications = [
        ('v1', 'finite_case_summary.csv', 'numerical_validation_summary.json',
         'average_success', 'phase_sensitive_bound', 'maximum_phase_bound_residual'),
        ('v2', 'adaptive_finite_case_summary.csv', 'adaptive_validation_summary.json',
         'average_success', 'hard_cap_bound', 'maximum_coarse_residual'),
        ('v3', 'posterior_advice_validation.csv', 'posterior_advice_validation_summary.json',
         'actual_average_success', 'coarse_bound', 'maximum_success_residual'),
    ]
    for version, csv_name, json_name, success, bound, summary_key in specifications:
        directory = ROOT / 'results' / f'theory_validation_{version}'
        frame = pd.read_csv(directory / csv_name)
        summary = json.loads((directory / json_name).read_text())
        residual = frame[success].to_numpy() - frame[bound].to_numpy()
        maximum = float(np.max(residual))
        assert abs(maximum - summary[summary_key]) <= 1e-12, version
        assert int((residual > 1e-10).sum()) == summary['violations'] == 0, version
        if version == 'v1':
            assert len(frame) == summary['random_algorithms']
            assert int(frame.n_unique_feasible_sets.sum()) == summary['unique_feasible_sets_across_algorithm_rows']
        else:
            assert len(frame) == summary['protocols' if version == 'v2' else 'parameter_rows']
            assert int(frame.subset_evaluations.sum()) == summary['subset_evaluations']
        checks[version] = {'rows': len(frame), 'maximum_residual': maximum, 'violations': 0}
    directory = ROOT / 'results/theory_validation_v3'
    summary = json.loads((directory / 'explicit_rcsp_validation_summary.json').read_text())
    for name, key in [('raw_phi_counterexamples.csv', 'unique_chain_rows'),
                      ('representation_padding_validation.csv', 'padding_rows'),
                      ('parallel_branch_validation.csv', 'parallel_branch_rows')]:
        frame = pd.read_csv(directory / name)
        assert len(frame) == summary[key], name
    branches = pd.read_csv(directory / 'parallel_branch_validation.csv')
    assert branches.attribute_mapping_ok.astype(str).str.lower().eq('true').all()
    assert summary['construction_failures'] == 0
    checks['explicit_rcsp'] = summary
    return checks
