from __future__ import annotations

import numpy as np

from qroute_dilution.theory.advice_query_tradeoff import maximum_effective_support
from qroute_dilution.theory.posterior_structure_bound import (
    effective_structure_bits,
    effective_support,
    known_candidate_posterior,
)


def test_effective_support_identity_and_bounds() -> None:
    N, M, Lambda = 64, 4, 0.25
    phi = M / N
    K_eff = effective_support(M, Lambda)
    assert M <= K_eff <= N
    assert np.isclose(N / K_eff, Lambda / phi)
    assert np.isclose(N / K_eff, 2 ** effective_structure_bits(phi, Lambda))


def test_known_candidate_set_needs_conditional_uniformity() -> None:
    memberships = known_candidate_posterior(16, 2, (0, 1, 2, 3))
    assert np.max(memberships) == 2 / 4
    assert effective_support(2, float(np.max(memberships))) == 4
    nonuniform = np.asarray([0.9, 0.6, 0.3, 0.2] + [0.0] * 12)
    assert np.isclose(nonuniform.sum(), 2.0)
    assert np.max(nonuniform) != 2 / 4


def test_target_success_requires_candidate_compression() -> None:
    assert maximum_effective_support(M=2, q=1, target_success=0.5) == 36
