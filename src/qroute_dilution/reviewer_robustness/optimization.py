"""Strict function-evaluation-budget wrappers for reviewer diagnostics."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import OptimizeResult, minimize


class EvaluationBudgetReached(RuntimeError):
    """Internal signal raised before an objective call would exceed its budget."""


class OptimizationWalltimeReached(RuntimeError):
    """Internal signal raised between objective calls at the walltime guard."""


@dataclass(frozen=True)
class EvaluationRecord:
    nfev: int
    parameters: np.ndarray
    value: float


@dataclass(frozen=True)
class BudgetedOptimizationResult:
    method: str
    initial_parameters: np.ndarray
    terminal_parameters: np.ndarray
    best_evaluated_parameters: np.ndarray
    objective_initial: float
    terminal_objective_observed: float
    best_evaluated_objective: float
    nfev: int
    scipy_reported_nfev: int | None
    nit: int
    status: int | None
    message: str
    termination_reason: str
    scipy_success: bool
    runtime_s: float
    history: tuple[EvaluationRecord, ...]

    def incumbent_at(self, budget: int) -> EvaluationRecord:
        eligible = [record for record in self.history if record.nfev <= int(budget)]
        if not eligible:
            raise ValueError(f"no evaluation exists at budget {budget}")
        return min(eligible, key=lambda record: (record.value, record.nfev))


def _method_options(method: str, max_nfev: int, settings: dict[str, float | bool]) -> tuple[str, dict]:
    normalized = method.upper().replace("_", "-")
    if normalized == "COBYLA":
        return "COBYLA", {
            "maxiter": int(max_nfev),
            "rhobeg": float(settings.get("cobyla_rhobeg", 0.5)),
            "catol": float(settings.get("cobyla_catol", 1e-8)),
        }
    if normalized in {"NELDER-MEAD", "NELDERMEAD"}:
        return "Nelder-Mead", {
            "maxfev": int(max_nfev),
            "maxiter": int(max_nfev) * 20,
            "xatol": float(settings.get("nelder_mead_xatol", 1e-8)),
            "fatol": float(settings.get("nelder_mead_fatol", 1e-8)),
            "adaptive": bool(settings.get("nelder_mead_adaptive", False)),
        }
    if normalized == "SLSQP":
        return "SLSQP", {
            "maxiter": int(max_nfev) * 2,
            "ftol": float(settings.get("slsqp_ftol", 1e-9)),
            "disp": False,
        }
    raise ValueError(f"unsupported optimizer {method}")


def optimize_with_strict_nfev(
    objective: Callable[[np.ndarray], float],
    initial_parameters: np.ndarray,
    *,
    method: str,
    max_nfev: int,
    timeout_s: float | None,
    settings: dict[str, float | bool] | None = None,
) -> BudgetedOptimizationResult:
    """Run SciPy while counting every objective call, including SLSQP probes.

    The wrapper raises internally before call ``max_nfev + 1``.  If SciPy has no
    native function-call limit (notably SLSQP), the latest completed callback
    iterate is the budget-terminal point.  The best actually evaluated point is
    retained separately and is used for single-trajectory budget checkpoints.
    """
    x0 = np.asarray(initial_parameters, dtype=np.float64).copy()
    if x0.ndim != 1 or not x0.size or not np.all(np.isfinite(x0)):
        raise ValueError("initial parameters must be a finite nonempty vector")
    if int(max_nfev) <= 0:
        raise ValueError("max_nfev must be positive")
    scipy_method, options = _method_options(method, int(max_nfev), settings or {})
    history: list[EvaluationRecord] = []
    callback_parameters: np.ndarray | None = None
    callback_nit = 0
    started = time.perf_counter()

    def tracked(parameters: np.ndarray) -> float:
        if len(history) >= int(max_nfev):
            raise EvaluationBudgetReached(
                f"strict objective-evaluation budget {max_nfev} reached"
            )
        if timeout_s is not None and time.perf_counter() - started >= float(timeout_s):
            raise OptimizationWalltimeReached(
                f"optimizer exceeded timeout_s={float(timeout_s):g}"
            )
        point = np.asarray(parameters, dtype=np.float64).copy()
        value = float(objective(point))
        if not np.isfinite(value):
            raise FloatingPointError("objective returned a non-finite value")
        history.append(EvaluationRecord(len(history) + 1, point, value))
        return value

    def callback(intermediate_result=None):
        nonlocal callback_parameters, callback_nit
        callback_nit += 1
        if isinstance(intermediate_result, OptimizeResult):
            callback_parameters = np.asarray(intermediate_result.x, dtype=np.float64).copy()
        elif intermediate_result is not None:
            callback_parameters = np.asarray(intermediate_result, dtype=np.float64).copy()

    result: OptimizeResult | None = None
    caught: Exception | None = None
    try:
        result = minimize(
            tracked,
            x0,
            method=scipy_method,
            callback=callback,
            options=options,
        )
    except (EvaluationBudgetReached, OptimizationWalltimeReached) as exc:
        caught = exc
    if not history:
        if caught is not None:
            raise caught
        raise RuntimeError("optimizer made no objective evaluations")
    best = min(history, key=lambda record: (record.value, record.nfev))
    if result is not None:
        terminal = np.asarray(result.x, dtype=np.float64).copy()
        terminal_value = float(result.fun)
        status = int(result.status)
        scipy_reported_nfev = int(result.nfev)
        message = str(result.message)
        success = bool(result.success)
        nit = int(getattr(result, "nit", callback_nit))
        if len(history) >= int(max_nfev):
            reason = "EVALUATION_BUDGET_EXHAUSTED"
        elif success:
            reason = "EARLY_CONVERGENCE"
        else:
            reason = "SCIPY_TERMINATION"
    else:
        if isinstance(caught, OptimizationWalltimeReached):
            reason = "WALLTIME_LIMIT"
        else:
            reason = "EVALUATION_BUDGET_EXHAUSTED"
        terminal = callback_parameters.copy() if callback_parameters is not None else best.parameters.copy()
        matching = [
            record
            for record in history
            if np.array_equal(record.parameters, terminal)
        ]
        terminal_value = matching[-1].value if matching else best.value
        status = None
        scipy_reported_nfev = None
        message = str(caught)
        success = False
        nit = callback_nit
    if not (
        np.all(np.isfinite(terminal))
        and np.all(np.isfinite(best.parameters))
        and np.isfinite(terminal_value)
    ):
        raise FloatingPointError("optimizer produced a non-finite terminal state")
    return BudgetedOptimizationResult(
        method=scipy_method,
        initial_parameters=x0,
        terminal_parameters=terminal,
        best_evaluated_parameters=best.parameters.copy(),
        objective_initial=float(history[0].value),
        terminal_objective_observed=float(terminal_value),
        best_evaluated_objective=float(best.value),
        nfev=len(history),
        scipy_reported_nfev=scipy_reported_nfev,
        nit=nit,
        status=status,
        message=message,
        termination_reason=reason,
        scipy_success=success,
        runtime_s=float(time.perf_counter() - started),
        history=tuple(history),
    )
