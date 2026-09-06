"""Frozen objective definitions and exact distributional diagnostics for Phase 1.2."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .optimizer import OptimizationTimeout


OBJECTIVE_IDENTITIES = {
    "O0": ("MEAN_ENERGY", "E_theta[H_C]", "HISTORICAL_MEAN_ENERGY_BASELINE"),
    "O1": (
        "EXPECTED_PENALTY",
        "E_theta[P_flow + P_resource]",
        "FEASIBILITY_ALIGNED_MECHANISTIC_OBJECTIVE_CONTROL",
    ),
    "O2": (
        "EXACT_FEASIBILITY_CONTROL",
        "1 - P_feas(theta)",
        "STATEVECTOR_MECHANISTIC_CONTROL",
    ),
    "O3": (
        "CVAR_ENERGY",
        "exact_weighted_lowest_energy_CVaR_alpha_0.10",
        "EXACT_DISTRIBUTIONAL_ENERGY_CONTROL",
    ),
}


def expected_penalty_objective(
    probabilities: np.ndarray, total_penalty: np.ndarray
) -> float:
    """Return E[P_flow + P_resource] for an exact probability distribution."""
    probabilities = np.asarray(probabilities, dtype=np.float64)
    total_penalty = np.asarray(total_penalty, dtype=np.float64)
    if probabilities.shape != total_penalty.shape:
        raise ValueError("probabilities and total_penalty must have the same shape")
    return float(np.dot(probabilities, total_penalty))


def exact_feasibility_objective(
    probabilities: np.ndarray, feasible_mask: np.ndarray
) -> float:
    """Return 1-P_feas using exact statevector probability mass."""
    probabilities = np.asarray(probabilities, dtype=np.float64)
    feasible_mask = np.asarray(feasible_mask, dtype=bool)
    if probabilities.shape != feasible_mask.shape:
        raise ValueError("probabilities and feasible_mask must have the same shape")
    return float(1.0 - probabilities[feasible_mask].sum())


def weighted_exact_cvar(
    energies: np.ndarray,
    probabilities: np.ndarray,
    alpha: float,
    *,
    feasible_mask: np.ndarray | None = None,
    energy_order: np.ndarray | None = None,
) -> dict[str, float | bool]:
    """Exact lower-tail CVaR with fractional probability at the alpha cutoff.

    Probabilities are normalized by their observed total to remove floating-point
    state-norm drift. Equal-energy ordering cannot change CVaR; the optional
    feasible-tail diagnostic assumes the separately audited strict class separation.
    """
    energies = np.asarray(energies, dtype=np.float64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if energies.shape != probabilities.shape or energies.ndim != 1:
        raise ValueError("energies and probabilities must be same-length vectors")
    if not 0.0 < float(alpha) <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    if np.any(probabilities < -1e-14) or not np.all(np.isfinite(probabilities)):
        raise ValueError("probabilities must be finite and nonnegative")
    total = float(probabilities.sum())
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("probabilities must have positive finite mass")
    order = (
        np.argsort(energies, kind="stable")
        if energy_order is None
        else np.asarray(energy_order, dtype=np.int64)
    )
    if order.shape != energies.shape:
        raise ValueError("energy_order has the wrong shape")
    sorted_probabilities = probabilities[order] / total
    cumulative = np.cumsum(sorted_probabilities)
    cutoff_index = min(
        int(np.searchsorted(cumulative, float(alpha), side="left")), len(energies) - 1
    )
    mass_before = float(cumulative[cutoff_index - 1]) if cutoff_index else 0.0
    fractional_mass = max(0.0, float(alpha) - mass_before)
    sorted_energies = energies[order]
    numerator = float(
        np.dot(
            sorted_probabilities[:cutoff_index], sorted_energies[:cutoff_index]
        )
        + fractional_mass * sorted_energies[cutoff_index]
    )
    tail_feasible_mass = math.nan
    tail_fully_feasible = False
    if feasible_mask is not None:
        feasible_mask = np.asarray(feasible_mask, dtype=bool)
        if feasible_mask.shape != energies.shape:
            raise ValueError("feasible_mask has the wrong shape")
        sorted_feasible = feasible_mask[order]
        tail_feasible_mass = float(
            np.dot(
                sorted_probabilities[:cutoff_index],
                sorted_feasible[:cutoff_index].astype(np.float64),
            )
            + fractional_mass * float(sorted_feasible[cutoff_index])
        )
        tail_fully_feasible = bool(tail_feasible_mass >= float(alpha) - 1e-10)
    return {
        "cvar_value": numerator / float(alpha),
        "cvar_cutoff_energy": float(sorted_energies[cutoff_index]),
        "cvar_tail_feasible_mass": tail_feasible_mass,
        "cvar_tail_fully_feasible": tail_fully_feasible,
        "cvar_fractional_cutoff_mass": fractional_mass,
    }


def feasibility_penalty_bound(
    probabilities: np.ndarray,
    feasible_mask: np.ndarray,
    total_penalty: np.ndarray,
    *,
    tolerance: float = 1e-10,
) -> dict[str, float | bool]:
    """Evaluate 1-P_feas <= E[P_total] <= 4(1-P_feas)."""
    probabilities = np.asarray(probabilities, dtype=np.float64)
    feasible_mask = np.asarray(feasible_mask, dtype=bool)
    total_penalty = np.asarray(total_penalty, dtype=np.float64)
    if not (probabilities.shape == feasible_mask.shape == total_penalty.shape):
        raise ValueError("all penalty-bound arrays must have the same shape")
    mass = float(probabilities.sum())
    if mass <= 0.0:
        raise ValueError("probability mass must be positive")
    normalized = probabilities / mass
    infeasible_mass = float(1.0 - normalized[feasible_mask].sum())
    expected_penalty = float(np.dot(normalized, total_penalty))
    lower_margin = expected_penalty - infeasible_mass
    upper_margin = 4.0 * infeasible_mass - expected_penalty
    return {
        "infeasible_probability": infeasible_mass,
        "expected_total_penalty": expected_penalty,
        "lower_bound_margin": lower_margin,
        "upper_bound_margin": upper_margin,
        "bound_pass": bool(lower_margin >= -tolerance and upper_margin >= -tolerance),
    }


@dataclass(frozen=True)
class ObjectiveOptimizationResult:
    initial_parameters: np.ndarray
    terminal_parameters: np.ndarray
    best_evaluated_parameters: np.ndarray
    objective_start: float
    terminal_objective: float
    best_evaluated_objective: float
    optimizer_nfev: int
    tracked_optimizer_evaluations: int
    total_objective_evaluations: int
    eval_budget: int
    status: int
    message: str
    scipy_success: bool
    numerically_valid: bool
    runtime_s: float


def optimize_cobyla_objective(
    objective: Callable[[np.ndarray], float],
    initial_parameters: np.ndarray,
    *,
    eval_budget: int,
    timeout_s: float | None,
    rhobeg: float,
    catol: float,
) -> ObjectiveOptimizationResult:
    """Optimize a frozen callable under the Phase-1 COBYLA accounting contract."""
    x0 = np.asarray(initial_parameters, dtype=np.float64).copy()
    if x0.ndim != 1 or x0.size == 0:
        raise ValueError("initial_parameters must be a nonempty vector")
    if eval_budget <= 0:
        raise ValueError("eval_budget must be positive")
    started = time.perf_counter()
    objective_start = float(objective(x0))
    best_value = objective_start
    best_parameters = x0.copy()
    evaluations = 0

    def tracked(parameters: np.ndarray) -> float:
        nonlocal best_value, best_parameters, evaluations
        if timeout_s is not None and time.perf_counter() - started >= timeout_s:
            raise OptimizationTimeout(f"optimizer exceeded fixed timeout_s={timeout_s:g}")
        value = float(objective(np.asarray(parameters, dtype=np.float64)))
        evaluations += 1
        if np.isfinite(value) and value < best_value:
            best_value = value
            best_parameters = np.asarray(parameters, dtype=np.float64).copy()
        return value

    result = minimize(
        tracked,
        x0,
        method="COBYLA",
        options={
            "maxiter": int(eval_budget),
            "rhobeg": float(rhobeg),
            "catol": float(catol),
        },
    )
    terminal_parameters = np.asarray(result.x, dtype=np.float64)
    terminal_objective = float(result.fun)
    if np.isfinite(terminal_objective) and terminal_objective < best_value:
        best_value = terminal_objective
        best_parameters = terminal_parameters.copy()
    valid = bool(
        np.isfinite(terminal_objective)
        and np.isfinite(best_value)
        and np.all(np.isfinite(terminal_parameters))
        and np.all(np.isfinite(best_parameters))
    )
    return ObjectiveOptimizationResult(
        initial_parameters=x0,
        terminal_parameters=terminal_parameters,
        best_evaluated_parameters=best_parameters,
        objective_start=objective_start,
        terminal_objective=terminal_objective,
        best_evaluated_objective=float(best_value),
        optimizer_nfev=int(result.nfev),
        tracked_optimizer_evaluations=evaluations,
        total_objective_evaluations=1 + evaluations,
        eval_budget=int(eval_budget),
        status=int(result.status),
        message=str(result.message),
        scipy_success=bool(result.success),
        numerically_valid=valid,
        runtime_s=float(time.perf_counter() - started),
    )
