from __future__ import annotations

import numpy as np

from qroute_dilution.theory.advice_query_tradeoff import (
    advice_alphabet_lambda_bound,
    finite_advice_success_bound,
    phase_sensitive_advice_bound,
    required_advice_bits,
)
from qroute_dilution.theory.posterior_structure_bound import (
    all_fixed_size_subsets,
    deterministic_channel,
    posterior_summary,
)


def test_advice_naming_a_mark_saturates_the_alphabet_bound_for_singletons() -> None:
    subsets = all_fixed_size_subsets(8, 1)
    summary = posterior_summary(8, 1, deterministic_channel(range(8), 8), subsets)
    assert np.isclose(summary.Lambda, 1.0)
    assert advice_alphabet_lambda_bound(1 / 8, summary.support_size) == 1.0


def test_duplicate_maximizers_do_not_break_support_bound() -> None:
    subsets = all_fixed_size_subsets(4, 2)
    assignments = tuple(int(0 in subset) for subset in subsets)
    summary = posterior_summary(4, 2, deterministic_channel(assignments, 4), subsets)
    assert summary.support_size == 2
    assert summary.Lambda <= summary.support_size * summary.phi + 1e-12


def test_integer_advice_requirement_and_edge_cases() -> None:
    assert required_advice_bits(1 / 1024, 0, 1 / 2) == 9
    assert required_advice_bits(1 / 1024, 3, 1 / 2) == 4
    assert required_advice_bits(1.0, 0, 1.0) == 0
    assert required_advice_bits(1 / 8, 0, 0.0) == 0
    assert finite_advice_success_bound(1 / 1024, 0, 9) == 0.5
    assert phase_sensitive_advice_bound(1 / 1024, 2, (0.5,)) == 9 / 1024
