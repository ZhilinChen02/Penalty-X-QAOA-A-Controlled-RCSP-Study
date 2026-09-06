"""Posterior-concentration bounds for membership-query search.

The functions here evaluate finite classical advice channels exactly.  They
also expose the scalar bounds used by the analytic hybrid proof in the v3
theory documents; numerical evaluation is evidence, not the proof itself.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


@dataclass(frozen=True)
class PosteriorSummary:
    """Posterior membership data for a finite advice channel.

    Columns with zero marginal probability are removed.  ``memberships[j,x]``
    is Pr[x in F | S=j], so the posterior projector is the diagonal operator
    with that row on its label register.
    """

    N: int
    M: int
    advice_probabilities: np.ndarray
    memberships: np.ndarray
    lambdas: np.ndarray

    @property
    def phi(self) -> float:
        return self.M / self.N

    @property
    def support_size(self) -> int:
        return int(len(self.advice_probabilities))

    @property
    def Lambda(self) -> float:
        return float(np.dot(self.advice_probabilities, self.lambdas))

    def trace_errors(self) -> np.ndarray:
        return np.sum(self.memberships, axis=1) - self.M


def all_fixed_size_subsets(N: int, M: int) -> tuple[tuple[int, ...], ...]:
    _validate_domain(N, M)
    return tuple(itertools.combinations(range(N), M))


def _validate_domain(N: int, M: int) -> None:
    if int(N) != N or N <= 0:
        raise ValueError("N must be a positive integer")
    if int(M) != M or not 0 <= M <= N:
        raise ValueError("M must be an integer in [0,N]")


def incidence_matrix(
    N: int, feasible_sets: Sequence[Sequence[int]]
) -> np.ndarray:
    matrix = np.zeros((len(feasible_sets), N), dtype=np.float64)
    for row, subset in enumerate(feasible_sets):
        values = tuple(int(value) for value in subset)
        if len(values) != len(set(values)):
            raise ValueError("feasible set contains duplicate labels")
        if any(value < 0 or value >= N for value in values):
            raise ValueError("feasible-set label out of range")
        matrix[row, list(values)] = 1.0
    return matrix


def posterior_summary(
    N: int,
    M: int,
    channel: Sequence[Sequence[float]] | np.ndarray,
    feasible_sets: Sequence[Sequence[int]] | None = None,
    *,
    tolerance: float = 1e-12,
) -> PosteriorSummary:
    """Evaluate a channel P(S|F) under the uniform size-M subset prior."""
    _validate_domain(N, M)
    subsets = tuple(feasible_sets or all_fixed_size_subsets(N, M))
    if not subsets:
        raise ValueError("the feasible-set prior must be nonempty")
    if any(len(subset) != M for subset in subsets):
        raise ValueError("every feasible set must have size M")
    advice = np.asarray(channel, dtype=np.float64)
    if advice.ndim != 2 or advice.shape[0] != len(subsets):
        raise ValueError("channel must have one row per feasible set")
    if advice.shape[1] == 0:
        raise ValueError("advice alphabet must be nonempty")
    if np.any(advice < -tolerance) or not np.all(np.isfinite(advice)):
        raise ValueError("channel probabilities must be finite and nonnegative")
    advice = np.maximum(advice, 0.0)
    if np.max(np.abs(advice.sum(axis=1) - 1.0)) > tolerance:
        raise ValueError("each channel row must sum to one")

    prior = np.full(len(subsets), 1.0 / len(subsets), dtype=np.float64)
    joint = prior[:, None] * advice
    marginals = joint.sum(axis=0)
    active = marginals > tolerance
    if not np.any(active):
        raise ValueError("channel has no positive-probability advice value")
    joint = joint[:, active]
    marginals = marginals[active]
    posterior = joint / marginals[None, :]
    memberships = posterior.T @ incidence_matrix(N, subsets)
    lambdas = memberships.max(axis=1)
    return PosteriorSummary(
        N=N,
        M=M,
        advice_probabilities=marginals,
        memberships=memberships,
        lambdas=lambdas,
    )


def deterministic_channel(assignments: Iterable[int], alphabet_size: int) -> np.ndarray:
    values = tuple(int(value) for value in assignments)
    if alphabet_size <= 0:
        raise ValueError("alphabet_size must be positive")
    if any(value < 0 or value >= alphabet_size for value in values):
        raise ValueError("advice assignment out of range")
    channel = np.zeros((len(values), alphabet_size), dtype=np.float64)
    channel[np.arange(len(values)), values] = 1.0
    return channel


def posterior_projector(membership_probabilities: Sequence[float]) -> np.ndarray:
    """Return the label-space diagonal matrix E[Pi_F | S=s]."""
    values = np.asarray(membership_probabilities, dtype=np.float64)
    if values.ndim != 1 or np.any(values < -1e-12) or np.any(values > 1 + 1e-12):
        raise ValueError("posterior memberships must lie in [0,1]")
    return np.diag(np.clip(values, 0.0, 1.0))


def posterior_projector_norm(membership_probabilities: Sequence[float]) -> float:
    values = np.asarray(membership_probabilities, dtype=np.float64)
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("posterior membership vector must be nonempty")
    return float(np.linalg.norm(posterior_projector(values), ord=2))


def reference_marked_mass(
    state: Sequence[complex] | np.ndarray,
    memberships: Sequence[float],
    *,
    ancilla_dim: int = 1,
) -> float:
    """Compute <psi|overline(Pi) tensor I|psi> for a normalized reference."""
    weights = np.asarray(memberships, dtype=np.float64)
    vector = np.asarray(state, dtype=np.complex128)
    if ancilla_dim <= 0 or vector.shape != (len(weights) * ancilla_dim,):
        raise ValueError("state dimension does not match label and ancilla dimensions")
    if abs(float(np.vdot(vector, vector).real) - 1.0) > 1e-10:
        raise ValueError("state must be normalized")
    probabilities = np.sum(np.abs(vector.reshape(len(weights), ancilla_dim)) ** 2, axis=1)
    return float(np.dot(weights, probabilities))


def phase_sensitive_conditional_bound(
    lambda_s: float, slot_coefficients: Sequence[float]
) -> float:
    if not -1e-12 <= lambda_s <= 1.0 + 1e-12:
        raise ValueError("lambda_s must lie in [0,1]")
    lambda_s = min(1.0, max(0.0, float(lambda_s)))
    coefficients = tuple(float(value) for value in slot_coefficients)
    if any(not 0.0 <= value <= 2.0 + 1e-12 for value in coefficients):
        raise ValueError("query coefficients must lie in [0,2]")
    C = 1.0 + sum(coefficients)
    return float(min(1.0, C * C * lambda_s))


def phase_sensitive_average_bound(
    summary: PosteriorSummary,
    coefficients_by_advice: Sequence[Sequence[float]],
) -> float:
    """Average the conditional caps; do not move a cap through expectation."""
    if len(coefficients_by_advice) != summary.support_size:
        raise ValueError("one coefficient sequence is required per supported advice value")
    conditional = np.asarray(
        [
            phase_sensitive_conditional_bound(lambda_s, coefficients)
            for lambda_s, coefficients in zip(summary.lambdas, coefficients_by_advice)
        ]
    )
    return float(np.dot(summary.advice_probabilities, conditional))


def coarse_posterior_bound(Lambda: float, q: int) -> float:
    if not -1e-12 <= Lambda <= 1.0 + 1e-12 or q < 0 or int(q) != q:
        raise ValueError("require Lambda in [0,1] and an integer q >= 0")
    Lambda = min(1.0, max(0.0, float(Lambda)))
    return float(min(1.0, (2 * int(q) + 1) ** 2 * Lambda))


def effective_structure_bits(phi: float, Lambda: float) -> float:
    if not 0.0 < phi <= 1.0 or not phi - 1e-12 <= Lambda <= 1.0 + 1e-12:
        raise ValueError("require 0 < phi <= Lambda <= 1")
    return float(math.log2(min(1.0, Lambda) / phi))


def effective_support(M: int, Lambda: float) -> float:
    if M <= 0 or not 0.0 < Lambda <= 1.0:
        raise ValueError("require M > 0 and Lambda in (0,1]")
    return float(M / Lambda)


def known_candidate_posterior(N: int, M: int, candidates: Sequence[int]) -> np.ndarray:
    """Uniform size-M posterior supported on a declared candidate set."""
    _validate_domain(N, M)
    values = tuple(int(value) for value in candidates)
    if len(values) != len(set(values)) or any(value < 0 or value >= N for value in values):
        raise ValueError("candidate labels must be distinct and in range")
    if not M <= len(values):
        raise ValueError("candidate set must contain at least M labels")
    memberships = np.zeros(N, dtype=np.float64)
    memberships[list(values)] = M / len(values)
    return memberships


def quantum_advice_dimension_bound(
    phi: float,
    dimension: int,
    q: int | None = None,
    *,
    slot_coefficients: Sequence[float] | None = None,
) -> float:
    """Single-advice-state dimension bound under oracle-only later access.

    For any F-dependent density operator rho_F on a d-dimensional advice
    register and any F-independent channel A, rho_F <= I_d implies
    E Tr[Pi_F A(rho_F)] <= phi Tr[A(I_d)] = d*phi.  Applying this fact to
    every identity-oracle reference state in the hybrid argument yields the
    returned query bound.  Multiple copies count through their joint dimension.
    """
    if not 0.0 <= phi <= 1.0:
        raise ValueError("phi must lie in [0,1]")
    if dimension <= 0 or int(dimension) != dimension:
        raise ValueError("dimension must be a positive integer")
    if slot_coefficients is not None and q is not None:
        raise ValueError("supply q or slot_coefficients, not both")
    if slot_coefficients is None:
        if q is None or q < 0 or int(q) != q:
            raise ValueError("q must be a nonnegative integer")
        coefficient = 2 * int(q) + 1
    else:
        values = tuple(float(value) for value in slot_coefficients)
        if any(not 0.0 <= value <= 2.0 + 1e-12 for value in values):
            raise ValueError("query coefficients must lie in [0,2]")
        coefficient = 1.0 + sum(values)
    return float(min(1.0, coefficient * coefficient * dimension * phi))
