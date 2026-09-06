from __future__ import annotations

import math

import numpy as np

from qroute_dilution.metrics import probability_metrics, uniform_metrics
from qroute_dilution.qaoa import (
    apply_cost_layer,
    apply_x_mixer,
    plus_state,
    simulate_qaoa,
)


def test_uniform_p_feas_equals_feasible_state_fraction():
    metrics = uniform_metrics(16, [5, 9], [5])
    assert metrics["p_feas"] == 2 / 16
    assert metrics["p_opt"] == 1 / 16
    assert metrics["feasibility_amplification"] == 1.0


def test_amplification_formula_correct():
    probabilities = np.array([0.1, 0.2, 0.3, 0.4])
    metrics = probability_metrics(probabilities, [1, 2], [2], 0.25)
    assert np.isclose(metrics["p_feas"], 0.5)
    assert np.isclose(metrics["feasibility_amplification"], 2.0)
    assert np.isclose(metrics["p_opt_given_feasible"], 0.6)


def test_zero_feasible_fraction_gives_nan_amplification():
    metrics = probability_metrics(np.array([0.5, 0.5]), [], [], 0.0)
    assert metrics["p_feas"] == 0.0
    assert math.isnan(metrics["feasibility_amplification"])


def test_cost_layer_preserves_basis_probabilities():
    state = np.array([0.5, 0.5j, -0.5, -0.5j], dtype=complex)
    energies = np.array([0.0, 1.0, 2.0, 4.0])
    evolved = apply_cost_layer(state, energies, gamma=0.73)
    assert np.allclose(np.abs(evolved) ** 2, np.abs(state) ** 2)


def test_x_mixer_preserves_norm():
    rng = np.random.default_rng(5)
    state = rng.normal(size=8) + 1j * rng.normal(size=8)
    state /= np.linalg.norm(state)
    assert np.isclose(np.linalg.norm(apply_x_mixer(state, 0.42, 3)), 1.0)


def test_qaoa_norm_preserved():
    energies = np.arange(16, dtype=float) ** 2
    state = simulate_qaoa(np.array([0.2, 0.4, 0.3, 0.7]), energies, depth=2)
    assert np.isclose(np.linalg.norm(state), 1.0)


def test_probability_metrics_are_bounded():
    state = plus_state(3)
    metrics = probability_metrics(np.abs(state) ** 2, [1, 2, 3], [2], 3 / 8)
    assert 0 <= metrics["p_feas"] <= 1
    assert 0 <= metrics["p_opt"] <= 1
