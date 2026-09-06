from __future__ import annotations

import itertools

import numpy as np

from qroute_dilution.theory.adaptive_query_bound import random_adaptive_protocol
from qroute_dilution.theory.deferred_measurement import (
    coherent_hybrid_trace,
    simulate_direct,
    simulate_purified_padded,
    simulate_purified,
)


def test_direct_and_purified_output_distributions_match() -> None:
    protocol = random_adaptive_protocol(
        4,
        3,
        2,
        "phase_flip",
        seed=4401,
        measure_between_slots=True,
        early_stop=True,
        randomized_control=True,
    )
    for feasible_set in itertools.combinations(range(4), 2):
        direct = simulate_direct(protocol, feasible_set)
        purified = simulate_purified(protocol, feasible_set)
        padded = simulate_purified_padded(protocol, feasible_set)
        assert np.allclose(
            direct.output_distribution, purified.output_distribution, atol=1e-12
        )
        assert np.isclose(direct.success, purified.success, atol=1e-12)
        assert np.allclose(
            direct.output_distribution, padded.output_distribution, atol=1e-12
        )
        assert all(count == protocol.q for count in padded.query_counts)
        assert np.isclose(sum(purified.branch_weights), 1.0, atol=1e-12)


def test_purified_hybrid_recursion() -> None:
    protocol = random_adaptive_protocol(
        4, 3, 2, "branch_phase", seed=771, measure_between_slots=True
    )
    trace = coherent_hybrid_trace(protocol, (1,))
    assert len(trace) == 3
    assert max(float(row["recursion_residual"]) for row in trace) <= 1e-12
