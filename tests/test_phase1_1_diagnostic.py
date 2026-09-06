from __future__ import annotations

import numpy as np

from qroute_dilution.diagnostic_optimizer import optimize_from_initial
from qroute_dilution.phase1_1_diagnostic import (
    build_evaluation_context,
    classify_continuation,
    embed_p2_in_p3,
    energy_class_gap,
    evaluate_parameters,
    verify_immutable_evidence,
)
from qroute_dilution.qaoa import simulate_qaoa


def test_p2_to_p3_parameter_ordering():
    p2 = np.array([0.1, 0.2, 0.3, 0.4])
    assert np.array_equal(embed_p2_in_p3(p2), [0.1, 0.2, 0.0, 0.3, 0.4, 0.0])


def test_zero_layer_nested_state_equivalence(small_task_and_characterization):
    task, _ = small_task_and_characterization
    context = build_evaluation_context(task)
    p2 = np.array([0.4, 1.1, 0.2, 0.7])
    state2 = simulate_qaoa(p2, context["energy"], 2)
    state3 = simulate_qaoa(embed_p2_in_p3(p2), context["energy"], 3)
    assert np.allclose(state2, state3, rtol=0.0, atol=1e-14)


def test_objective_component_and_mass_sums(small_task_and_characterization):
    task, _ = small_task_and_characterization
    context = build_evaluation_context(task)
    evaluation = evaluate_parameters(task, context, np.array([0.2, 0.6]), 1)
    assert abs(evaluation["component_sum"] - evaluation["objective"]) < 1e-12
    assert abs(evaluation["mass_category_sum"] - 1.0) < 1e-12
    assert abs(evaluation["mass_valid_flow_resource_feasible"] - evaluation["p_feas"]) < 1e-12


def test_energy_class_gap_calculation():
    energy = np.array([2.0, 0.2, 1.5, 0.4])
    result = energy_class_gap(energy, (1, 3))
    assert result["max_feasible_energy"] == 0.4
    assert result["min_infeasible_energy"] == 1.5
    assert np.isclose(result["feasible_infeasible_energy_gap"], 1.1)
    assert result["complete_energy_separation"]


def test_continuation_classifications():
    tolerance = 1e-10
    assert classify_continuation(1.0, 0.9, 0.2, 0.3, tolerance) == "OBJECTIVE_AND_FEASIBILITY_IMPROVE"
    assert classify_continuation(1.0, 0.9, 0.2, 0.1, tolerance) == "OBJECTIVE_IMPROVES_FEASIBILITY_WORSENS"
    assert classify_continuation(1.0, 1.0, 0.2, 0.2, tolerance) == "NO_MEANINGFUL_OBJECTIVE_GAIN"
    assert classify_continuation(1.0, 1.1, 0.2, 0.3, tolerance) == "OPTIMIZER_REGRESSION"


def test_budget_accounting_and_best_evaluated_tracking():
    energies = np.array([0.0, 1.0, 1.5, 0.3])
    initial = np.array([0.2, 0.4])
    result = optimize_from_initial(
        energies,
        1,
        initial,
        method="Nelder-Mead",
        eval_budget=12,
        timeout_s=30,
    )
    assert result.optimizer_nfev <= 12
    assert result.tracked_optimizer_evaluations == result.optimizer_nfev
    assert result.total_objective_evaluations == result.optimizer_nfev + 1
    assert result.best_evaluated_objective <= result.objective_start + 1e-14
    assert result.best_evaluated_objective <= result.terminal_objective + 1e-14
