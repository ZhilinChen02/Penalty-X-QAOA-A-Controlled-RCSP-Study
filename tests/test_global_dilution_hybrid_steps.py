from __future__ import annotations

import numpy as np
import pytest

from qroute_dilution.theory.global_dilution_bound import (
    all_fixed_size_subsets,
    hybrid_trace,
    hybrid_trace_examples,
    phase_query_coefficient,
    projected_norm_squared,
    random_query_algorithm,
    reference_states_before_queries,
)


def test_single_query_perturbation_and_hybrid_recursion():
    algorithm = random_query_algorithm(4, 2, 3, seed=177)
    for subset in all_fixed_size_subsets(4, 2):
        trace = hybrid_trace(algorithm, subset)
        for row in trace[:-1]:
            assert row["single_query_perturbation"] == pytest.approx(
                row["c_t"] * row["a_t"], abs=1e-14
            )
            assert row["d_after"] <= row["recursion_rhs"] + 1e-14
        final = trace[-1]
        assert final["sqrt_success"] <= final["sqrt_reference_plus_distance"] + 1e-14


def test_reference_marked_amplitude_l2_identity_at_every_query_with_ancilla():
    N, M = 6, 2
    algorithm = random_query_algorithm(N, 3, 3, seed=201)
    subsets = all_fixed_size_subsets(N, M)
    for state in reference_states_before_queries(algorithm):
        values = [projected_norm_squared(state, N, 3, subset) for subset in subsets]
        assert np.mean(values) == pytest.approx(M / N, abs=1e-14)


def test_numerical_minkowski_and_final_projection_l2_bounds():
    frame = hybrid_trace_examples()
    query = frame[frame.row_type == "QUERY_STEP"]
    aggregate = frame[frame.row_type == "L2_AGGREGATE"]
    assert query.recursion_residual.max() <= 1e-12
    assert query.single_query_identity_residual.abs().max() <= 1e-12
    assert aggregate.l2_residual.max() <= 1e-12
    assert aggregate.average_success_projection_residual.max() <= 1e-12
    assert aggregate.maximum_a_squared_expectation_error.max() <= 1e-12
