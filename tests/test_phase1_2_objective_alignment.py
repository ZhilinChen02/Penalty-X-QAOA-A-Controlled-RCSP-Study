from __future__ import annotations

import numpy as np

from qroute_dilution.phase1_2_experiment import (
    build_objective_context,
    evaluate_objective_state,
    verify_historical_immutability,
)
from qroute_dilution.phase1_2_objectives import (
    OBJECTIVE_IDENTITIES,
    exact_feasibility_objective,
    expected_penalty_objective,
    feasibility_penalty_bound,
    optimize_cobyla_objective,
    weighted_exact_cvar,
)


def test_exact_pfeas_objective():
    probabilities = np.array([0.1, 0.2, 0.3, 0.4])
    feasible = np.array([False, True, False, True])
    assert np.isclose(exact_feasibility_objective(probabilities, feasible), 0.4)


def test_expected_penalty_objective():
    probabilities = np.array([0.1, 0.2, 0.3, 0.4])
    penalties = np.array([0.0, 1.0, 2.0, 4.0])
    assert np.isclose(expected_penalty_objective(probabilities, penalties), 2.4)


def test_weighted_exact_cvar_fractional_cutoff():
    energies = np.array([0.0, 1.0, 2.0])
    probabilities = np.array([0.05, 0.10, 0.85])
    result = weighted_exact_cvar(energies, probabilities, 0.10)
    # Lowest 0.10 mass is 0.05 at E=0 plus 0.05 of the E=1 atom.
    assert np.isclose(result["cvar_value"], 0.5)
    assert result["cvar_cutoff_energy"] == 1.0
    assert np.isclose(result["cvar_fractional_cutoff_mass"], 0.05)


def test_feasibility_penalty_inequality():
    probabilities = np.array([0.15, 0.35, 0.25, 0.25])
    feasible = np.array([True, True, False, False])
    penalties = np.array([0.0, 0.0, 1.0, 4.0])
    result = feasibility_penalty_bound(probabilities, feasible, penalties)
    assert result["bound_pass"]
    assert np.isclose(result["infeasible_probability"], 0.5)
    assert np.isclose(result["expected_total_penalty"], 1.25)


def test_cvar_feasible_tail_condition_under_strict_separation():
    energies = np.array([0.1, 0.2, 1.1, 1.2])
    feasible = np.array([True, True, False, False])
    enough = weighted_exact_cvar(
        energies, np.array([0.04, 0.08, 0.40, 0.48]), 0.10, feasible_mask=feasible
    )
    insufficient = weighted_exact_cvar(
        energies, np.array([0.03, 0.04, 0.43, 0.50]), 0.10, feasible_mask=feasible
    )
    assert enough["cvar_tail_fully_feasible"]
    assert np.isclose(enough["cvar_tail_feasible_mass"], 0.10)
    assert not insufficient["cvar_tail_fully_feasible"]
    assert np.isclose(insufficient["cvar_tail_feasible_mass"], 0.07)


def test_objective_identity_and_provenance():
    assert set(OBJECTIVE_IDENTITIES) == {"O0", "O1", "O2", "O3"}
    assert OBJECTIVE_IDENTITIES["O2"][2] == "STATEVECTOR_MECHANISTIC_CONTROL"
    assert len({identity[1] for identity in OBJECTIVE_IDENTITIES.values()}) == 4


def test_matched_budget_accounting():
    objective = lambda x: float(np.dot(x, x))
    result = optimize_cobyla_objective(
        objective,
        np.array([0.4, -0.2]),
        eval_budget=12,
        timeout_s=30.0,
        rhobeg=0.5,
        catol=1e-8,
    )
    assert result.optimizer_nfev <= 12
    assert result.tracked_optimizer_evaluations == result.optimizer_nfev
    assert result.total_objective_evaluations == result.optimizer_nfev + 1
    assert result.best_evaluated_objective <= result.objective_start + 1e-14
    assert result.best_evaluated_objective <= result.terminal_objective + 1e-14


def test_scientific_metric_decomposition_and_bound(small_task_and_characterization):
    task, _ = small_task_and_characterization
    context = build_objective_context(task)
    evaluation = evaluate_objective_state(
        task, context, np.array([0.2, 0.4, 0.0, 0.3, 0.5, 0.0]), cvar_alpha=0.10
    )
    assert abs(
        evaluation["mean_energy"]
        - evaluation["expected_routing_component"]
        - evaluation["expected_flow_penalty"]
        - evaluation["expected_resource_penalty"]
    ) < 1e-12
    assert evaluation["penalty_bound_pass"]
    assert np.isfinite(evaluation["expected_route_cost_given_feasible"])
