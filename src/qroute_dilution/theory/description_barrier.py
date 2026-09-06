"""Information-theoretic description bounds for marked subsets."""

from __future__ import annotations

import math

import pandas as pd


def log2_binomial(N: int, M: int) -> float:
    if N < 0 or not 0 <= M <= N:
        raise ValueError("require N >= 0 and 0 <= M <= N")
    if M in (0, N):
        return 0.0
    if M in (1, N - 1):
        return float(math.log2(N))
    return float(
        (math.lgamma(N + 1) - math.lgamma(M + 1) - math.lgamma(N - M + 1))
        / math.log(2.0)
    )


def binary_entropy(phi: float) -> float:
    if not 0.0 <= phi <= 1.0:
        raise ValueError("phi must lie in [0,1]")
    if phi in (0.0, 1.0):
        return 0.0
    return float(-phi * math.log2(phi) - (1.0 - phi) * math.log2(1.0 - phi))


def entropy_leading_term(N: int, M: int) -> float:
    if N <= 0 or not 0 <= M <= N:
        raise ValueError("invalid binomial domain")
    return float(N * binary_entropy(M / N))


def sparse_marked_asymptotic(N: int, M: int) -> float:
    """Leading sparse approximation M log2(N/M), not an equality."""
    if N <= 0 or not 1 <= M <= N:
        raise ValueError("require 1 <= M <= N")
    return float(M * math.log2(N / M))


def description_barrier_table(n_values=range(2, 21)) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for n in n_values:
        N = 2**int(n)
        choices = {
            "singleton": 1,
            "sparse_n_squared": min(N - 1, max(1, int(n) ** 2)),
            "quarter_fraction": max(1, N // 4),
            "half_fraction": N // 2,
        }
        for regime, M in choices.items():
            exact = log2_binomial(N, M)
            rows.append(
                {
                    "n": int(n),
                    "N": N,
                    "M": M,
                    "regime": regime,
                    "log2_binomial": exact,
                    "entropy_leading_term": entropy_leading_term(N, M),
                    "sparse_leading_term": sparse_marked_asymptotic(N, M),
                    "bits_per_label_qubit": exact / n,
                }
            )
    return pd.DataFrame(rows)
