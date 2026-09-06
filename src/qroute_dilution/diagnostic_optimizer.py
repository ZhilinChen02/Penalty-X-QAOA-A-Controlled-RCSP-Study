"""Budget-accounted derivative-free optimizers for Phase 1.1 diagnostics."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .optimizer import OptimizationTimeout
from .qaoa import qaoa_objective


@dataclass(frozen=True)
class TrackedOptimizationResult:
    method: str
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


def optimize_from_initial(
    energies: np.ndarray,
    depth: int,
    initial_parameters: np.ndarray,
    *,
    method: str,
    eval_budget: int,
    timeout_s: float | None,
    cobyla_rhobeg: float = 0.5,
    cobyla_catol: float = 1e-8,
    nelder_mead_xatol: float = 1e-8,
    nelder_mead_fatol: float = 1e-8,
    nelder_mead_adaptive: bool = False,
) -> TrackedOptimizationResult:
    """Optimize from a fixed point while retaining terminal and best-evaluated states.

    The diagnostic start evaluation is recorded separately. ``eval_budget`` applies
    to SciPy's optimizer calls, matching the Phase 1 COBYLA max-function-evaluation
    contract. Thus total objective evaluations are ``1 + optimizer_nfev``.
    """
    energies = np.asarray(energies, dtype=np.float64)
    x0 = np.asarray(initial_parameters, dtype=np.float64).copy()
    if x0.shape != (2 * depth,):
        raise ValueError(f"expected {2 * depth} parameters, received {x0.shape}")
    if eval_budget <= 0:
        raise ValueError("eval_budget must be positive")
    started = time.perf_counter()
    objective_start = float(qaoa_objective(x0, energies, depth))
    best_value = objective_start
    best_parameters = x0.copy()
    tracked_evaluations = 0

    def tracked_objective(parameters: np.ndarray) -> float:
        nonlocal best_value, best_parameters, tracked_evaluations
        if timeout_s is not None and time.perf_counter() - started >= timeout_s:
            raise OptimizationTimeout(f"optimizer exceeded fixed timeout_s={timeout_s:g}")
        value = float(qaoa_objective(parameters, energies, depth))
        tracked_evaluations += 1
        if np.isfinite(value) and value < best_value:
            best_value = value
            best_parameters = np.asarray(parameters, dtype=np.float64).copy()
        return value

    normalized_method = method.upper().replace("_", "-")
    if normalized_method == "COBYLA":
        scipy_method = "COBYLA"
        options = {
            "maxiter": int(eval_budget),
            "rhobeg": float(cobyla_rhobeg),
            "catol": float(cobyla_catol),
        }
    elif normalized_method in {"NELDER-MEAD", "NELDERMEAD"}:
        scipy_method = "Nelder-Mead"
        options = {
            "maxfev": int(eval_budget),
            "maxiter": int(eval_budget) * 10,
            "xatol": float(nelder_mead_xatol),
            "fatol": float(nelder_mead_fatol),
            "adaptive": bool(nelder_mead_adaptive),
        }
    else:
        raise ValueError(f"unsupported diagnostic optimizer: {method}")

    result = minimize(tracked_objective, x0, method=scipy_method, options=options)
    terminal_parameters = np.asarray(result.x, dtype=np.float64)
    terminal_objective = float(result.fun)
    if np.isfinite(terminal_objective) and terminal_objective < best_value:
        best_value = terminal_objective
        best_parameters = terminal_parameters.copy()
    optimizer_nfev = int(result.nfev)
    numerically_valid = bool(
        np.isfinite(terminal_objective)
        and np.isfinite(best_value)
        and np.all(np.isfinite(terminal_parameters))
        and np.all(np.isfinite(best_parameters))
    )
    return TrackedOptimizationResult(
        method=scipy_method,
        initial_parameters=x0,
        terminal_parameters=terminal_parameters,
        best_evaluated_parameters=best_parameters,
        objective_start=objective_start,
        terminal_objective=terminal_objective,
        best_evaluated_objective=float(best_value),
        optimizer_nfev=optimizer_nfev,
        tracked_optimizer_evaluations=tracked_evaluations,
        total_objective_evaluations=1 + tracked_evaluations,
        eval_budget=int(eval_budget),
        status=int(result.status),
        message=str(result.message),
        scipy_success=bool(result.success),
        numerically_valid=numerically_valid,
        runtime_s=float(time.perf_counter() - started),
    )
