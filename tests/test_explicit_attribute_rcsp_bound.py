from __future__ import annotations

import math

from qroute_dilution.theory.explicit_rcsp_bounds import (
    average_search_lower_bound_queries,
    exact_search_complexity_class,
    free_array_access_queries,
    grover_upper_bound_queries,
    parallel_branch_instance,
    query_complexity_scope,
)


def test_parallel_branch_feasibility_is_one_attribute_bit() -> None:
    instance = parallel_branch_instance(8, (1, 3, 6))
    assert instance.feasible_branches == (1, 3, 6)
    assert all(instance.is_feasible(i) == bool(instance.oracle_bit(i)) for i in range(8))
    assert instance.M == 3
    assert instance.phi_path == 3 / 8
    assert instance.phi_state == 3 / 2**16
    assert instance.phi_path != instance.phi_state


def test_search_bound_and_matching_upper_scale_as_sqrt_K_over_M() -> None:
    for K, M in ((16, 1), (64, 4), (256, 16)):
        lower = average_search_lower_bound_queries(K, M, 2 / 3)
        upper = grover_upper_bound_queries(K, M)
        assert lower > 0
        assert upper <= math.ceil(math.pi / 4 * math.sqrt(K / M)) + 1


def test_dense_and_all_marked_edge_cases_are_explicit() -> None:
    assert query_complexity_scope(8, 8, 2 / 3) == "ZERO_QUERY_UNIFORM_GUESS_SUFFICES"
    assert query_complexity_scope(8, 6, 2 / 3) == "ZERO_QUERY_UNIFORM_GUESS_SUFFICES"
    assert grover_upper_bound_queries(8, 8) == 0
    assert exact_search_complexity_class(8, 8) == "ZERO_QUERIES"
    assert exact_search_complexity_class(8, 7) == "THETA_SQRT_K_OVER_M"
    assert free_array_access_queries((0, 1, 0)) == 0
