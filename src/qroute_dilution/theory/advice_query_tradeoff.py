"""Finite-advice, effective-support, and query-accounting utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


def advice_alphabet_lambda_bound(phi: float, support_size: int) -> float:
    if not 0.0 <= phi <= 1.0:
        raise ValueError("phi must lie in [0,1]")
    if support_size <= 0 or int(support_size) != support_size:
        raise ValueError("support_size must be a positive integer")
    return float(min(1.0, int(support_size) * phi))


def finite_advice_success_bound(phi: float, q: int, b: int) -> float:
    if not 0.0 <= phi <= 1.0:
        raise ValueError("phi must lie in [0,1]")
    if q < 0 or int(q) != q or b < 0 or int(b) != b:
        raise ValueError("q and b must be nonnegative integers")
    return float(min(1.0, (2 * int(q) + 1) ** 2 * (2**int(b)) * phi))


def phase_sensitive_advice_bound(
    phi: float, b: int, slot_coefficients: Sequence[float]
) -> float:
    """Bound for global coefficients independent of the advice value.

    Advice-dependent coefficients require conditioning first; they cannot be
    replaced by an average coefficient.  Uniform per-slot suprema may be passed
    here as global coefficients.
    """
    if not 0.0 <= phi <= 1.0 or b < 0 or int(b) != b:
        raise ValueError("require phi in [0,1] and an integer b >= 0")
    values = tuple(float(value) for value in slot_coefficients)
    if any(not 0.0 <= value <= 2.0 + 1e-12 for value in values):
        raise ValueError("query coefficients must lie in [0,2]")
    C = 1.0 + sum(values)
    return float(min(1.0, C * C * (2**int(b)) * phi))


def required_advice_bits(phi: float, q: int, target_success: float) -> int:
    """Smallest nonnegative integer allowed by the necessary scalar bound."""
    if not 0.0 < phi <= 1.0:
        raise ValueError("phi must lie in (0,1]")
    if q < 0 or int(q) != q:
        raise ValueError("q must be a nonnegative integer")
    if not 0.0 <= target_success <= 1.0:
        raise ValueError("target_success must lie in [0,1]")
    if target_success == 0.0:
        return 0
    ratio = target_success / (((2 * int(q) + 1) ** 2) * phi)
    if ratio <= 1.0:
        return 0
    # The tolerance only avoids returning k+1 for a floating representation of 2**k.
    return max(0, int(math.ceil(math.log2(ratio) - 1e-12)))


def necessary_effective_bits(
    phi: float, q: int, target_success: float
) -> float:
    if not 0.0 < phi <= 1.0 or q < 0 or int(q) != q:
        raise ValueError("require phi in (0,1] and an integer q >= 0")
    if not 0.0 < target_success <= 1.0:
        raise ValueError("target_success must lie in (0,1]")
    return float(
        max(
            0.0,
            math.log2(target_success / phi) - 2.0 * math.log2(2 * int(q) + 1),
        )
    )


def structure_query_budget_lhs(b_eff: float, q: int) -> float:
    if b_eff < 0.0 or q < 0 or int(q) != q:
        raise ValueError("require b_eff >= 0 and an integer q >= 0")
    return float(b_eff + 2.0 * math.log2(2 * int(q) + 1))


def maximum_effective_support(M: int, q: int, target_success: float) -> float:
    if M <= 0 or int(M) != M or q < 0 or int(q) != q:
        raise ValueError("M must be positive and q a nonnegative integer")
    if not 0.0 < target_success <= 1.0:
        raise ValueError("target_success must lie in (0,1]")
    return float(((2 * int(q) + 1) ** 2) * int(M) / target_success)


def exponential_dilution_effective_bits(
    alpha: float, n: int, q: int, target_success: float
) -> float:
    if alpha <= 0.0 or n <= 0 or int(n) != n:
        raise ValueError("require alpha > 0 and a positive integer n")
    return necessary_effective_bits(2.0 ** (-alpha * int(n)), q, target_success)


@dataclass(frozen=True)
class TwoStageQueryAccount:
    """Hard-cap accounting for query-generated classical structure."""

    preprocessing_queries: int
    postprocessing_queries: int

    def __post_init__(self) -> None:
        if any(
            value < 0 or int(value) != value
            for value in (self.preprocessing_queries, self.postprocessing_queries)
        ):
            raise ValueError("query counts must be nonnegative integers")

    @property
    def total_queries(self) -> int:
        return int(self.preprocessing_queries + self.postprocessing_queries)

    def success_bound(self, phi: float) -> float:
        if not 0.0 <= phi <= 1.0:
            raise ValueError("phi must lie in [0,1]")
        return float(min(1.0, (2 * self.total_queries + 1) ** 2 * phi))


@dataclass(frozen=True)
class StructuredOracleAccount:
    invocations: int
    membership_queries_per_invocation: int
    other_membership_queries: int = 0

    def __post_init__(self) -> None:
        values = (
            self.invocations,
            self.membership_queries_per_invocation,
            self.other_membership_queries,
        )
        if any(value < 0 or int(value) != value for value in values):
            raise ValueError("query-account values must be nonnegative integers")

    @property
    def charged_membership_queries(self) -> int:
        return int(
            self.invocations * self.membership_queries_per_invocation
            + self.other_membership_queries
        )

    @property
    def classification(self) -> str:
        return "MEMBERSHIP_SIMULABLE_CHARGED"


def classify_structured_operation(simulation_queries: int | None) -> str:
    if simulation_queries is None:
        return "STRICTLY_STRONGER_STRUCTURE_ORACLE"
    if simulation_queries < 0 or int(simulation_queries) != simulation_queries:
        raise ValueError("simulation query count must be a nonnegative integer")
    return "MEMBERSHIP_SIMULABLE_CHARGED"
