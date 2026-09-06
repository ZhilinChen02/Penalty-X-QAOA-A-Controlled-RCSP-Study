"""Fixed-budget deterministic COBYLA wrapper."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .qaoa import qaoa_objective


class OptimizationTimeout(RuntimeError):
    """Raised by the fixed wall-clock guard between objective evaluations."""


@dataclass(frozen=True)
class OptimizationResult:
    initial_parameters: np.ndarray
    optimized_parameters: np.ndarray
    nfev: int
    status: int
    message: str
    success: bool
    objective_initial: float
    objective_final: float
    runtime_s: float


def initial_parameters(depth: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    gammas = rng.uniform(0.0, 2.0 * np.pi, size=depth)
    betas = rng.uniform(0.0, np.pi, size=depth)
    return np.concatenate([gammas, betas])


def optimize_cobyla(
    energies: np.ndarray,
    depth: int,
    seed: int,
    eval_budget: int,
    timeout_s: float | None = None,
) -> OptimizationResult:
    x0 = initial_parameters(depth, seed)
    started = time.perf_counter()

    def timed_objective(parameters: np.ndarray, diagonal: np.ndarray, qaoa_depth: int) -> float:
        if timeout_s is not None and time.perf_counter() - started >= timeout_s:
            raise OptimizationTimeout(f"optimizer exceeded fixed timeout_s={timeout_s:g}")
        return qaoa_objective(parameters, diagonal, qaoa_depth)

    objective_initial = timed_objective(x0, energies, depth)
    result = minimize(
        timed_objective,
        x0,
        args=(energies, depth),
        method="COBYLA",
        options={"maxiter": int(eval_budget), "rhobeg": 0.5, "catol": 1e-8},
    )
    elapsed = time.perf_counter() - started
    final = float(result.fun)
    numerically_valid = bool(np.isfinite(final) and np.all(np.isfinite(result.x)))
    return OptimizationResult(
        initial_parameters=x0,
        optimized_parameters=np.asarray(result.x, dtype=float),
        nfev=int(result.nfev),
        status=int(result.status),
        message=str(result.message),
        success=numerically_valid,
        objective_initial=float(objective_initial),
        objective_final=final,
        runtime_s=elapsed,
    )
