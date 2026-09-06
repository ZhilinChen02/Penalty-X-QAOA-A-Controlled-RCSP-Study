from __future__ import annotations

import numpy as np

from qroute_dilution.theory.global_dilution_bound import (
    QueryAlgorithm,
    algorithm_successes,
    coarse_query_bound,
    invalid_assumption_examples,
)


def test_deliberate_invalid_assumption_examples_are_explicitly_outside_class():
    examples = invalid_assumption_examples()
    assert len(examples) >= 4
    assert set(examples.status) == {"OUTSIDE_THEOREM_CLASS"}
    assert {
        "F_DEPENDENT_INITIAL_GOOD_SUPERPOSITION",
        "F_DEPENDENT_UNITARY",
        "CLASSICALLY_ENUMERATED_F",
        "KNOWN_PREFIX_STRUCTURE",
    } <= set(examples.example_id)


def test_average_bound_is_not_a_pointwise_bound():
    N = 8
    initial = np.zeros(N, dtype=np.complex128)
    initial[0] = 1.0
    algorithm = QueryAlgorithm(N, 1, (), initial, (np.eye(N, dtype=np.complex128),))
    success = algorithm_successes(algorithm, [(0,)])[0]
    assert success == 1.0
    assert coarse_query_bound(N, 1, 0) == 1 / N
    # This is not a counterexample: the theorem averages over all singleton sets.


def test_f_dependent_feasible_initial_state_bypasses_only_by_violating_assumption():
    N = 8
    for marked in range(N):
        initial = np.zeros(N, dtype=np.complex128)
        initial[marked] = 1.0
        algorithm = QueryAlgorithm(
            N, 1, (), initial, (np.eye(N, dtype=np.complex128),)
        )
        assert algorithm_successes(algorithm, [(marked,)])[0] == 1.0
