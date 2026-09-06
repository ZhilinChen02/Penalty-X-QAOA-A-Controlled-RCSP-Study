from __future__ import annotations

import math

from qroute_dilution.theory.description_barrier import (
    binary_entropy,
    entropy_leading_term,
    log2_binomial,
    sparse_marked_asymptotic,
)


def test_description_length_exact_small_values_and_singleton() -> None:
    assert np_close(log2_binomial(8, 2), math.log2(28))
    assert log2_binomial(16, 1) == 4.0
    assert log2_binomial(16, 0) == 0.0


def test_entropy_and_sparse_leading_terms() -> None:
    assert binary_entropy(0.5) == 1.0
    assert entropy_leading_term(1024, 512) == 1024.0
    assert sparse_marked_asymptotic(1024, 4) == 32.0


def np_close(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-12
