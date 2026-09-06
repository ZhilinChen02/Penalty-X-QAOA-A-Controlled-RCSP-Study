from __future__ import annotations

import numpy as np

from qroute_dilution.theory.posterior_structure_bound import (
    all_fixed_size_subsets,
    deterministic_channel,
    phase_sensitive_average_bound,
    posterior_projector_norm,
    posterior_summary,
    quantum_advice_dimension_bound,
    reference_marked_mass,
)


def test_constant_advice_reduces_to_uniform_dilution() -> None:
    subsets = all_fixed_size_subsets(8, 3)
    summary = posterior_summary(8, 3, np.ones((len(subsets), 1)))
    assert np.allclose(summary.memberships, 3 / 8)
    assert np.isclose(summary.Lambda, 3 / 8)
    assert np.allclose(summary.trace_errors(), 0)


def test_posterior_norm_is_maximum_membership_probability() -> None:
    memberships = np.asarray([0.1, 0.7, 0.2])
    assert np.isclose(posterior_projector_norm(memberships), 0.7)
    state = np.asarray([0.0, 1.0, 0.0], dtype=np.complex128)
    assert np.isclose(reference_marked_mass(state, memberships), 0.7)


def test_nonuniform_posteriors_and_conditional_caps_are_averaged_correctly() -> None:
    subsets = all_fixed_size_subsets(4, 1)
    channel = deterministic_channel((0, 0, 1, 1), 2)
    summary = posterior_summary(4, 1, channel, subsets)
    assert np.allclose(summary.lambdas, 0.5)
    bound = phase_sensitive_average_bound(summary, ((0.1,), (2.0,)))
    expected = 0.5 * min(1.0, 1.1**2 * 0.5) + 0.5 * 1.0
    assert np.isclose(bound, expected)


def test_single_copy_quantum_advice_dimension_bound() -> None:
    assert quantum_advice_dimension_bound(1 / 16, 4, q=0) == 0.25
    assert quantum_advice_dimension_bound(1 / 16, 16, q=0) == 1.0
    assert quantum_advice_dimension_bound(1 / 64, 2, slot_coefficients=(2.0,)) == 18 / 64
