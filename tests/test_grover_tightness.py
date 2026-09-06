from __future__ import annotations

import math

import pytest

from qroute_dilution.theory.global_dilution_bound import (
    first_grover_success_maximum,
    grover_formula_success,
    grover_numerical_success,
    grover_validation,
)


def test_grover_two_dimensional_formula():
    for N in (8, 16, 32, 64):
        for M in sorted({1, max(1, N // 8), N // 4, N // 2}):
            for q in range(first_grover_success_maximum(N, M) + 1):
                assert grover_numerical_success(N, M, q) == pytest.approx(
                    grover_formula_success(N, M, q), abs=1e-12
                )


def test_grover_small_phi_expansion_has_fourth_order_remainder():
    q = 3
    scaled = []
    for exponent in (16, 18, 20, 22):
        phi = 2.0 ** (-exponent)
        theta = math.asin(math.sqrt(phi))
        actual = math.sin((2 * q + 1) * theta) ** 2
        leading = (2 * q + 1) ** 2 * phi
        scaled.append(abs(actual - leading) / (q**4 * phi**2))
    assert max(scaled) < 100.0


def test_full_grover_validation_has_no_formula_violation():
    frame = grover_validation()
    assert frame.formula_absolute_error.max() <= 1e-12
    assert (frame.grover_success_numerical <= frame.phase_sensitive_bound + 1e-12).all()
    assert (frame.phase_sensitive_bound <= frame.coarse_bound + 1e-12).all()
