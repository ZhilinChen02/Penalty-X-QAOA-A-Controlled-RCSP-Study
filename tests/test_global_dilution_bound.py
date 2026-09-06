from __future__ import annotations

import math

import numpy as np
import pytest

from qroute_dilution.theory.global_dilution_bound import (
    QueryAlgorithm,
    algorithm_successes,
    all_fixed_size_subsets,
    coarse_query_bound,
    phase_query_coefficient,
    phase_sensitive_bound,
    query_lower_bound,
    random_normalized_state,
    uniform_subset_projection_expectation,
    verify_historical_hashes,
)


def test_uniform_random_m_subset_expectation_identity_with_ancilla():
    rng = np.random.default_rng(123)
    for N in (2, 4, 6):
        for M in range(N + 1):
            for ancilla_dim in (1, 2, 3):
                state = random_normalized_state(N * ancilla_dim, rng)
                observed = uniform_subset_projection_expectation(
                    state, N, M, ancilla_dim
                )
                assert observed == pytest.approx(M / N, abs=1e-14)


def test_phase_sensitive_coefficient_identity_and_extrema():
    for gamma in np.linspace(-4 * np.pi, 4 * np.pi, 33):
        direct = abs(np.exp(-1j * gamma) - 1.0)
        assert phase_query_coefficient(float(gamma)) == pytest.approx(direct, abs=1e-15)
        assert phase_query_coefficient(float(gamma)) <= 2.0 + 1e-15
    assert phase_query_coefficient(0.0) == 0.0
    assert phase_query_coefficient(math.pi) == pytest.approx(2.0)


def test_q_zero_average_success_equals_phi_for_arbitrary_initial_and_unitary():
    N, M, ancilla = 8, 3, 2
    rng = np.random.default_rng(77)
    initial = random_normalized_state(N * ancilla, rng)
    # A deterministic diagonal unitary is sufficient to make V0 nontrivial.
    phases = np.exp(1j * rng.uniform(0, 2 * np.pi, N * ancilla))
    v0 = np.diag(phases)
    algorithm = QueryAlgorithm(N, ancilla, (), initial, (v0,))
    success = algorithm_successes(algorithm, all_fixed_size_subsets(N, M))
    assert success.mean() == pytest.approx(M / N, abs=1e-14)
    assert phase_sensitive_bound(N, M, ()) == pytest.approx(M / N)


def test_coarse_bound_dominates_phase_sensitive_bound():
    rng = np.random.default_rng(91)
    for q in range(5):
        phases = rng.uniform(0, 2 * np.pi, q)
        assert phase_sensitive_bound(32, 2, phases) <= coarse_query_bound(32, 2, q) + 1e-15


def test_worst_and_average_case_query_lower_bound_algebra():
    phi, target = 1 / 1024, 0.5
    lower = query_lower_bound(phi, target)
    assert (2 * lower + 1) ** 2 * phi == pytest.approx(target)
    assert query_lower_bound(0.8, 0.2) == 0.0


def test_exponential_dilution_corollary_has_exponential_decay():
    alpha, degree, constant = 0.2, 3, 4.0
    ratios = []
    # The corollary is eventual: a large polynomial prefactor can dominate at
    # moderate n even though every polynomial is subexponential.
    for n in range(2000, 2051):
        q = constant * n**degree
        bound = (2 * q + 1) ** 2 * 2 ** (-alpha * n)
        ratios.append(bound / 2 ** (-(alpha / 2) * n))
    assert max(ratios) < 1.0


def test_binary_hamiltonian_cost_layer_is_global_phase_times_query():
    N, M, gamma = 8, 3, 0.731
    projector = np.diag([1.0] * M + [0.0] * (N - M))
    hamiltonian = np.eye(N) - projector
    lhs = np.diag(np.exp(-1j * gamma * np.diag(hamiltonian)))
    rhs = np.exp(-1j * gamma) * (
        np.eye(N) + (np.exp(1j * gamma) - 1.0) * projector
    )
    assert np.max(np.abs(lhs - rhs)) < 1e-15


def test_historical_evidence_immutability_for_theory_stage():
    result = verify_historical_hashes()
    assert result["unchanged"]
    assert result["file_count"] == 1314
    assert result["inventory_sha256"] == "a4bbd21a183f1621f721e6fe46e604d3d7542db64ba96da695510bdf778f63f2"
