from __future__ import annotations

from qroute_dilution.theory.explicit_rcsp_bounds import unique_chain_audit


def test_unique_chain_has_exponentially_small_raw_phi_and_linear_output() -> None:
    for m in (1, 2, 8, 32):
        audit = unique_chain_audit(m)
        assert audit.edge_bit_states == 2**m
        assert audit.valid_feasible_edge_bitstrings == 1
        assert audit.phi_state == 2.0 ** (-m)
        assert audit.inverse_sqrt_phi_state == 2.0 ** (m / 2)
        assert audit.traversal_steps == len(audit.output_edges) == m


def test_any_positive_universal_raw_phi_constant_is_eventually_contradicted() -> None:
    for constant in (1.0, 1e-3, 1e-12):
        ratios = [constant * unique_chain_audit(m).inverse_sqrt_phi_state / m for m in range(1, 257)]
        assert max(ratios) > 1.0
