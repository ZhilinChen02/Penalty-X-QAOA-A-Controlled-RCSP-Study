from __future__ import annotations

import itertools

import numpy as np

from qroute_dilution.theory.adaptive_query_bound import (
    adaptive_phase_bound,
    branch_phase_coefficient,
    random_adaptive_protocol,
)
from qroute_dilution.theory.deferred_measurement import simulate_direct


def test_branch_phase_coefficient_and_coarse_cap() -> None:
    assert np.isclose(branch_phase_coefficient([0.0, np.pi / 3, np.pi]), 2.0)
    assert adaptive_phase_bound(64, 1, [2.0, 2.0]) == 25 / 64
    assert adaptive_phase_bound(4, 3, [2.0]) == 1.0


def test_adaptive_average_bound_with_ancillas_and_feed_forward() -> None:
    for ancilla_dim in (1, 2):
        protocol = random_adaptive_protocol(
            4,
            2,
            ancilla_dim,
            "branch_phase",
            seed=8080 + ancilla_dim,
            measure_between_slots=True,
            early_stop=False,
            randomized_control=True,
        )
        successes = [
            simulate_direct(protocol, feasible_set).success
            for feasible_set in itertools.combinations(range(4), 1)
        ]
        assert np.mean(successes) <= adaptive_phase_bound(
            4, 1, protocol.phase_coefficients()
        ) + 1e-12


def test_q_zero_average_is_phi_for_mixed_randomized_control() -> None:
    protocol = random_adaptive_protocol(
        4,
        0,
        2,
        "phase_flip",
        seed=91,
        randomized_control=True,
    )
    successes = [
        simulate_direct(protocol, feasible_set).success
        for feasible_set in itertools.combinations(range(4), 2)
    ]
    assert np.isclose(np.mean(successes), 0.5, atol=1e-12)
