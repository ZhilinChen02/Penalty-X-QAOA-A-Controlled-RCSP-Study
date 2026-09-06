from __future__ import annotations

import numpy as np

from qroute_dilution.theory.adaptive_query_bound import (
    apply_query,
    branch_phase_coefficient,
    random_adaptive_protocol,
)


def test_history_controlled_phase_norm_uses_supremum_coefficient() -> None:
    protocol = random_adaptive_protocol(
        4, 2, 2, "branch_phase", seed=600, randomized_control=True
    )
    coefficients = protocol.phase_coefficients()
    for history, state in protocol.initial_states.items():
        phase = protocol.phases[(0, history)]
        queried = apply_query(state, protocol, (0, 1), 0, history)
        marked_norm = np.linalg.norm(state.reshape(4, protocol.work_dim)[[0, 1]])
        assert np.linalg.norm(queried - state) <= coefficients[0] * marked_norm + 1e-12
        assert branch_phase_coefficient([phase]) <= coefficients[0] + 1e-15
