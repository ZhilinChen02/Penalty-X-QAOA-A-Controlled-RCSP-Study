from __future__ import annotations

import math

from qroute_dilution.theory.advice_query_tradeoff import (
    exponential_dilution_effective_bits,
    structure_query_budget_lhs,
)
from qroute_dilution.theory.posterior_structure_bound import effective_structure_bits


def test_effective_structure_bit_range_and_classical_advice_cap() -> None:
    phi = 1 / 64
    assert effective_structure_bits(phi, phi) == 0.0
    assert effective_structure_bits(phi, 1.0) == 6.0
    assert effective_structure_bits(phi, 1 / 8) == 3.0


def test_structure_query_budget_is_necessary_not_sufficient() -> None:
    b_eff = 5.0
    q = 3
    assert math.isclose(structure_query_budget_lhs(b_eff, q), b_eff + 2 * math.log2(7))
    required = exponential_dilution_effective_bits(0.5, 100, 100**2, 2 / 3)
    assert required >= 50 - 2 * math.log2(2 * 100**2 + 1) - 1
