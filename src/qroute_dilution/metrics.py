"""Representation and probability-recovery metrics."""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np


def dilution_score(feasible_state_fraction: float) -> float:
    """Return -log10(phi_state), or NaN when no feasible state exists."""
    if feasible_state_fraction <= 0.0 or not np.isfinite(feasible_state_fraction):
        return math.nan
    return float(-math.log10(feasible_state_fraction))


def log_feasibility_gain(p_feas: float, feasible_state_fraction: float) -> float:
    """Return log10(P_feas / phi_state) on its strictly positive domain."""
    if (
        p_feas <= 0.0
        or feasible_state_fraction <= 0.0
        or not np.isfinite(p_feas)
        or not np.isfinite(feasible_state_fraction)
    ):
        return math.nan
    return float(math.log10(p_feas / feasible_state_fraction))


def probability_metrics(
    probabilities: np.ndarray,
    feasible_states: Iterable[int],
    optimal_states: Iterable[int],
    feasible_state_fraction: float,
) -> dict[str, float]:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    feasible = np.fromiter(feasible_states, dtype=np.int64)
    optimal = np.fromiter(optimal_states, dtype=np.int64)
    p_feas = float(probabilities[feasible].sum()) if feasible.size else 0.0
    p_opt = float(probabilities[optimal].sum()) if optimal.size else 0.0
    p_feas = float(np.clip(p_feas, 0.0, 1.0))
    p_opt = float(np.clip(p_opt, 0.0, 1.0))
    conditional = p_opt / p_feas if p_feas > 0.0 else math.nan
    amplification = (
        p_feas / feasible_state_fraction if feasible_state_fraction > 0.0 else math.nan
    )
    return {
        "p_feas": p_feas,
        "p_opt": p_opt,
        "p_opt_given_feasible": conditional,
        "feasibility_amplification": amplification,
        "log_feasibility_gain": log_feasibility_gain(p_feas, feasible_state_fraction),
    }


def uniform_metrics(
    state_space_size: int, feasible_states: Iterable[int], optimal_states: Iterable[int]
) -> dict[str, float]:
    feasible = tuple(feasible_states)
    optimal = tuple(optimal_states)
    fraction = len(feasible) / state_space_size
    p_opt = len(optimal) / state_space_size
    return {
        "p_feas": fraction,
        "p_opt": p_opt,
        "p_opt_given_feasible": len(optimal) / len(feasible) if feasible else math.nan,
        "feasibility_amplification": 1.0 if fraction > 0.0 else math.nan,
        "log_feasibility_gain": 0.0 if fraction > 0.0 else math.nan,
    }
