from __future__ import annotations

import numpy as np

from qroute_dilution.theory.adaptive_query_bound import (
    apply_query,
    random_adaptive_protocol,
)


def test_membership_bit_oracle_kickback_gives_phase_flip() -> None:
    N = 4
    query = np.asarray([1, 2j, -3, 4 - 1j], dtype=np.complex128)
    query /= np.linalg.norm(query)
    minus = np.asarray([1, -1], dtype=np.complex128) / np.sqrt(2)
    bit_state = np.kron(query, minus)
    bit_protocol = random_adaptive_protocol(N, 1, 1, "membership_bit", seed=1)
    observed = apply_query(bit_state, bit_protocol, (1, 3), 0, ())
    expected_query = query.copy()
    expected_query[[1, 3]] *= -1
    assert np.allclose(observed, np.kron(expected_query, minus), atol=1e-12)


def test_bit_oracle_direct_perturbation_has_coefficient_two() -> None:
    protocol = random_adaptive_protocol(4, 1, 2, "membership_bit", seed=2)
    state = next(iter(protocol.initial_states.values()))
    queried = apply_query(state, protocol, (0, 2), 0, ())
    marked = state.reshape(4, protocol.work_dim)[[0, 2]]
    assert np.linalg.norm(queried - state) <= 2 * np.linalg.norm(marked) + 1e-12
