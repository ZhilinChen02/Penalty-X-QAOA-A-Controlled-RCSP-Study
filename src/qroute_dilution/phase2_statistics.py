"""Frozen graph-level inference and discovery-only power planning for Phase 2."""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t as student_t


def aggregate_base_graph_means(
    results: pd.DataFrame,
    *,
    value_column: str = "log_feasibility_gain",
    expected_objectives: tuple[str, ...] = ("O0", "O2", "O3"),
) -> pd.DataFrame:
    """Give each base graph equal weight after averaging its dilution levels."""
    required = {"base_graph_id", "task_id", "objective_id", value_column}
    missing = required - set(results.columns)
    if missing:
        raise ValueError(f"missing graph aggregation columns: {sorted(missing)}")
    subset = results[results.objective_id.isin(expected_objectives)].copy()
    duplicates = subset.duplicated(["base_graph_id", "task_id", "objective_id"])
    if duplicates.any():
        raise ValueError("duplicate task/objective rows in graph aggregation")
    counts = subset.groupby(["base_graph_id", "objective_id"]).task_id.nunique().unstack()
    means = subset.groupby(["base_graph_id", "objective_id"])[value_column].mean().unstack()
    for objective in expected_objectives:
        if objective not in means or objective not in counts:
            means[objective] = np.nan
            counts[objective] = 0
    means = means[list(expected_objectives)]
    counts = counts[list(expected_objectives)]
    output = means.add_prefix("bar_G_").reset_index()
    for objective in expected_objectives:
        output[f"n_levels_{objective}"] = counts[objective].to_numpy(dtype=int)
    output["Delta1_CVAR_MEAN"] = output.bar_G_O3 - output.bar_G_O0
    output["Delta2_CVAR_CAPACITY"] = output.bar_G_O3 - output.bar_G_O2
    return output


def exact_sign_flip_pvalue(contrasts: np.ndarray, *, null: float = 0.0) -> float:
    """Exact one-sided cluster sign-flip p-value for the mean contrast."""
    values = np.asarray(contrasts, dtype=np.float64) - float(null)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("contrasts must be a nonempty finite vector")
    observed = float(values.mean())
    n = len(values)
    if n > 20:
        raise ValueError("exact sign-flip enumeration is capped at 20 clusters")
    assignments = np.asarray(list(itertools.product((-1.0, 1.0), repeat=n)))
    permuted = assignments @ values / n
    tolerance = 1e-15
    return float(np.mean(permuted >= observed - tolerance))


def grouped_bootstrap_lower_bound(
    contrasts: np.ndarray,
    *,
    resamples: int,
    seed: int,
    lower_quantile: float = 0.05,
) -> dict[str, float]:
    """Bootstrap whole base graphs, never individual dilution rows."""
    values = np.asarray(contrasts, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("contrasts must be a nonempty finite vector")
    if resamples <= 0 or not 0.0 < lower_quantile < 1.0:
        raise ValueError("invalid bootstrap configuration")
    rng = np.random.default_rng(int(seed))
    indices = rng.integers(0, len(values), size=(int(resamples), len(values)))
    bootstrap_means = values[indices].mean(axis=1)
    return {
        "effect_mean": float(values.mean()),
        "one_sided_95_lower_bound": float(
            np.quantile(bootstrap_means, float(lower_quantile))
        ),
        "bootstrap_standard_error": float(bootstrap_means.std(ddof=1)),
    }


def holm_adjust(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down multiplicity correction for a named hypothesis family."""
    if not pvalues:
        raise ValueError("pvalues cannot be empty")
    if any(not 0.0 <= float(value) <= 1.0 for value in pvalues.values()):
        raise ValueError("p-values must be in [0,1]")
    ordered = sorted(pvalues, key=lambda key: (pvalues[key], key))
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, key in enumerate(ordered):
        candidate = min(1.0, (m - rank) * float(pvalues[key]))
        running = max(running, candidate)
        adjusted[key] = running
    return {key: adjusted[key] for key in pvalues}


def confirmatory_graph_inference(
    delta1: np.ndarray,
    delta2: np.ndarray,
    *,
    noninferiority_margin: float,
    resamples: int,
    bootstrap_seed: int,
    family_alpha: float,
) -> dict[str, Any]:
    """Apply the preregistered exact tests, grouped bootstrap, and Holm family."""
    delta1 = np.asarray(delta1, dtype=np.float64)
    delta2 = np.asarray(delta2, dtype=np.float64)
    if delta1.shape != delta2.shape or delta1.ndim != 1:
        raise ValueError("paired graph contrasts must be same-length vectors")
    h1_bootstrap = grouped_bootstrap_lower_bound(
        delta1, resamples=resamples, seed=bootstrap_seed
    )
    h2_bootstrap = grouped_bootstrap_lower_bound(
        delta2, resamples=resamples, seed=bootstrap_seed
    )
    raw = {
        "H1": exact_sign_flip_pvalue(delta1, null=0.0),
        "H2": exact_sign_flip_pvalue(delta2, null=-float(noninferiority_margin)),
    }
    adjusted = holm_adjust(raw)
    h1_pass = bool(
        adjusted["H1"] < family_alpha
        and h1_bootstrap["one_sided_95_lower_bound"] > 0.0
    )
    h2_pass = bool(
        adjusted["H2"] < family_alpha
        and h2_bootstrap["one_sided_95_lower_bound"] > -float(noninferiority_margin)
    )
    return {
        "analysis_unit": "base_graph_id",
        "n_base_graphs": int(len(delta1)),
        "H1": {
            **h1_bootstrap,
            "null_margin": 0.0,
            "raw_p_value": raw["H1"],
            "holm_adjusted_p_value": adjusted["H1"],
            "pass": h1_pass,
        },
        "H2": {
            **h2_bootstrap,
            "null_margin": -float(noninferiority_margin),
            "raw_p_value": raw["H2"],
            "holm_adjusted_p_value": adjusted["H2"],
            "pass": h2_pass,
        },
    }


def simulate_holm_power(
    discovery_contrasts: np.ndarray,
    *,
    heldout_n: int,
    simulations: int,
    seed: int,
    noninferiority_margin: float,
    family_alpha: float,
) -> dict[str, Any]:
    """Discovery-only bivariate-normal planning simulation for the Holm family."""
    discovery = np.asarray(discovery_contrasts, dtype=np.float64)
    if discovery.ndim != 2 or discovery.shape[1] != 2 or discovery.shape[0] < 3:
        raise ValueError("discovery_contrasts must have shape (n>=3, 2)")
    if not np.all(np.isfinite(discovery)):
        raise ValueError("discovery contrasts must be finite")
    mean = discovery.mean(axis=0)
    covariance = np.cov(discovery, rowvar=False, ddof=1)
    rng = np.random.default_rng(int(seed))
    samples = rng.multivariate_normal(
        mean, covariance, size=(int(simulations), int(heldout_n))
    )
    sample_means = samples.mean(axis=1)
    sample_sds = samples.std(axis=1, ddof=1)
    standard_errors = sample_sds / math.sqrt(heldout_n)
    t_statistics = np.empty_like(sample_means)
    t_statistics[:, 0] = sample_means[:, 0] / standard_errors[:, 0]
    t_statistics[:, 1] = (
        sample_means[:, 1] + float(noninferiority_margin)
    ) / standard_errors[:, 1]
    raw = student_t.sf(t_statistics, df=heldout_n - 1)
    order = np.argsort(raw, axis=1)
    adjusted = np.empty_like(raw)
    rows = np.arange(len(raw))
    first = order[:, 0]
    second = order[:, 1]
    first_adjusted = np.minimum(1.0, 2.0 * raw[rows, first])
    adjusted[rows, first] = first_adjusted
    adjusted[rows, second] = np.maximum(first_adjusted, raw[rows, second])
    rejection = adjusted < float(family_alpha)
    return {
        "source_graph_count": int(len(discovery)),
        "heldout_graph_count": int(heldout_n),
        "simulations": int(simulations),
        "seed": int(seed),
        "discovery_effect_mean": {
            "H1_Delta1": float(mean[0]),
            "H2_Delta2": float(mean[1]),
        },
        "discovery_effect_sd": {
            "H1_Delta1": float(math.sqrt(covariance[0, 0])),
            "H2_Delta2": float(math.sqrt(covariance[1, 1])),
        },
        "projected_Holm_power": {
            "H1": float(rejection[:, 0].mean()),
            "H2": float(rejection[:, 1].mean()),
            "both": float(np.all(rejection, axis=1).mean()),
        },
    }
