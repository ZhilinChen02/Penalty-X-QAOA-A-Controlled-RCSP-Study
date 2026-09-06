from __future__ import annotations

from qroute_dilution.theory.adaptive_query_bound import (
    expected_query_truncation_bound,
    optimized_expected_query_bound,
    random_adaptive_protocol,
    rare_long_branch_counterexample,
)
from qroute_dilution.theory.deferred_measurement import simulate_direct


def test_early_stopping_respects_hard_cap() -> None:
    protocol = random_adaptive_protocol(
        4, 3, 2, "phase_flip", seed=301, early_stop=True
    )
    result = simulate_direct(protocol, (1,))
    assert max(result.query_counts) <= 3
    assert min(result.query_counts) < 3


def test_mean_query_substitution_has_explicit_counterexample() -> None:
    example = rare_long_branch_counterexample(1e-6, 785, 0.01)
    assert example["violates_naive_substitution"] is True
    assert example["mixture_success"] > example["naive_mean_substitution_bound"]


def test_truncation_bound_is_validly_capped_and_optimizable() -> None:
    assert 0.0 <= expected_query_truncation_bound(1024, 1, 2.0, 5) <= 1.0
    value, threshold = optimized_expected_query_bound(1024, 1, 2.0)
    assert 0.0 <= value <= 1.0
    assert threshold >= 0
