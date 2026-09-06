from __future__ import annotations

import numpy as np
import pandas as pd

from qroute_dilution.models import DirectedGraph, Edge
from qroute_dilution.phase1_2_objectives import weighted_exact_cvar
from qroute_dilution.qaoa import qaoa_objective, simulate_qaoa
from qroute_dilution.rcsp import enumerate_simple_routes, solve_exact_rcsp
from qroute_dilution.reviewer_robustness.classical_rcsp import solve_label_setting
from qroute_dilution.reviewer_robustness.common import (
    derive_seed,
    embed_parameters,
    task_from_manifest_row,
)
from qroute_dilution.reviewer_robustness.finite_shot import (
    empirical_event_probability,
    endpoint_objectives_from_manifest,
    empirical_cvar,
    sample_states,
    total_shot_count,
)
from qroute_dilution.reviewer_robustness.optimization import (
    optimize_with_strict_nfev,
)
from qroute_dilution.reviewer_robustness.registry import REVIEW_ROOT
from qroute_dilution.reviewer_robustness.selection import (
    select_depth_budget_tasks,
    select_finite_shot_tasks,
    task_frame,
)
from qroute_dilution.reviewer_robustness.common import (
    CHARACTERIZATION_PATH,
    DISCOVERY_MANIFEST,
    HELDOUT_MANIFEST,
    load_json,
)


def _graph(edges: list[tuple[int, int, float, float]], target: int) -> DirectedGraph:
    values = tuple(
        Edge(index=index, source=source, target=destination, cost=cost, resource=resource)
        for index, (source, destination, cost, resource) in enumerate(edges)
    )
    return DirectedGraph(
        n_nodes=target + 1,
        source=0,
        target=target,
        layers=((0,), tuple(range(1, target)), (target,)),
        edges=values,
        graph_id="test-graph",
    )


def test_zero_angle_embedding_p2_p3_and_p3_p4_is_exact():
    energies = np.asarray([0.2, 1.1, -0.4, 2.0, 0.7, 0.8, -0.1, 1.3])
    p2 = np.asarray([0.2, 1.3, 0.7, -0.4])
    p3 = embed_parameters(p2, 2, 3)
    p4 = embed_parameters(p3, 3, 4)
    state2 = simulate_qaoa(p2, energies, 2)
    state3 = simulate_qaoa(p3, energies, 3)
    state4 = simulate_qaoa(p4, energies, 4)
    assert np.allclose(state2, state3, rtol=0.0, atol=1e-12)
    assert np.allclose(state3, state4, rtol=0.0, atol=1e-12)
    assert abs(qaoa_objective(p2, energies, 2) - qaoa_objective(p3, energies, 3)) < 1e-12
    assert abs(qaoa_objective(p3, energies, 3) - qaoa_objective(p4, energies, 4)) < 1e-12


def test_strict_cobyla_nfev_accounting_and_termination_logging():
    result = optimize_with_strict_nfev(
        lambda point: float(np.dot(point - 1.0, point - 1.0)),
        np.asarray([3.0, -2.0]),
        method="COBYLA",
        max_nfev=17,
        timeout_s=10.0,
    )
    assert result.nfev <= 17
    assert len(result.history) == result.nfev
    assert result.scipy_reported_nfev in {None, result.nfev}
    assert result.termination_reason in {
        "EVALUATION_BUDGET_EXHAUSTED",
        "EARLY_CONVERGENCE",
        "SCIPY_TERMINATION",
    }
    assert result.message


def test_slsqp_finite_difference_calls_count_against_nfev():
    result = optimize_with_strict_nfev(
        lambda point: float(np.dot(point, point)),
        np.asarray([3.0, -2.0, 1.0, 4.0]),
        method="SLSQP",
        max_nfev=7,
        timeout_s=10.0,
    )
    assert result.nfev == 7
    assert len(result.history) == 7
    assert result.termination_reason == "EVALUATION_BUDGET_EXHAUSTED"
    # Initial value plus four numerical-gradient probes already consume five calls.
    assert len({tuple(record.parameters) for record in result.history[:5]}) == 5


def test_weighted_exact_cvar_corner_cases_and_alpha_one_endpoint():
    energies = np.asarray([0.0, 1.0, 1.0, 3.0])
    probabilities = np.asarray([0.1, 0.2, 0.3, 0.4])
    expected = float(np.dot(energies, probabilities))
    at_one = weighted_exact_cvar(energies, probabilities, 1.0)["cvar_value"]
    assert abs(at_one - expected) < 1e-14
    # Scaling probabilities exercises internal normalization.
    scaled = weighted_exact_cvar(energies, probabilities * 17.0, 1.0)["cvar_value"]
    assert abs(scaled - expected) < 1e-14
    # alpha=.25 consumes 0.1 at E=0 and a fractional 0.15 at tied E=1.
    assert abs(weighted_exact_cvar(energies, probabilities, 0.25)["cvar_value"] - 0.6) < 1e-14
    assert weighted_exact_cvar(energies, probabilities, 1e-8)["cvar_value"] == 0.0
    deterministic = weighted_exact_cvar(
        np.asarray([2.0, 5.0]), np.asarray([0.0, 4.0]), 0.37
    )["cvar_value"]
    assert deterministic == 5.0
    assert weighted_exact_cvar(energies, probabilities, 0.25) == weighted_exact_cvar(
        energies, probabilities, 0.25
    )


def test_sampled_cvar_fractional_boundary_and_seeded_reproducibility():
    values = np.asarray([0.0, 1.0, 2.0])
    assert abs(empirical_cvar(values, 0.5) - (0.5 / 1.5)) < 1e-14
    probabilities = np.asarray([0.2, 0.8])
    first = sample_states(probabilities, 20_000, 1234)
    second = sample_states(probabilities, 20_000, 1234)
    assert np.array_equal(first, second)
    assert abs(float((first == 0).mean()) - 0.2) < 0.015
    assert derive_seed("training", "task", 1) == derive_seed("training", "task", 1)
    assert derive_seed("training", "task", 1) != derive_seed("training", "task", 2)


def test_finite_shot_feasibility_estimator_and_total_shot_accounting():
    states = np.asarray([0, 1, 1, 2, 3, 3, 3, 3])
    feasible_mask = np.asarray([True, False, True, True])
    assert empirical_event_probability(states, feasible_mask) == 6 / 8
    assert total_shot_count(nfev=73, shots_per_evaluation=10_000) == 730_000


def test_label_setting_matches_bruteforce_feasible_tied_and_boundary_cases():
    graph = _graph(
        [
            (0, 1, 1.0, 1.0),
            (1, 3, 1.0, 1.0),
            (0, 2, 1.0, 1.0),
            (2, 3, 1.0, 1.0),
        ],
        target=3,
    )
    routes = enumerate_simple_routes(graph)
    _, brute_optimal, brute_cost = solve_exact_rcsp(routes, 2.0)
    result = solve_label_setting(graph, 2.0)
    assert result.feasible
    assert result.resource == 2.0  # equality at the resource boundary is feasible
    assert result.optimal_cost == brute_cost == 2.0
    assert len(brute_optimal) == 2


def test_label_setting_infeasible_and_dominance_pruning():
    infeasible_graph = _graph([(0, 1, 1.0, 2.0)], target=1)
    infeasible = solve_label_setting(infeasible_graph, 1.0)
    assert not infeasible.feasible
    assert infeasible.optimal_cost is None
    graph = _graph(
        [
            (0, 1, 1.0, 1.0),
            (0, 1, 2.0, 2.0),
            (1, 2, 1.0, 1.0),
        ],
        target=2,
    )
    result = solve_label_setting(graph, 4.0)
    routes = enumerate_simple_routes(graph)
    _, _, brute_cost = solve_exact_rcsp(routes, 4.0)
    assert result.optimal_cost == brute_cost == 2.0
    assert result.labels_dominance_pruned >= 1


def test_outcome_blind_selectors_have_frozen_counts_and_graph_coverage():
    characterization = pd.read_csv(CHARACTERIZATION_PATH)
    discovery = task_frame(load_json(DISCOVERY_MANIFEST), characterization)
    heldout = task_frame(load_json(HELDOUT_MANIFEST), characterization)
    b1 = select_depth_budget_tasks(discovery, count=24, seed=2026090411)
    estimator, training = select_finite_shot_tasks(
        heldout, estimator_count=18, training_count=10, seed=2026090421
    )
    assert len(b1) == 24
    assert b1.graph_id.nunique() == 10
    assert len(estimator) == 18
    assert estimator.graph_id.nunique() == 15
    assert len(training) == 10
    assert set(training.task_id) <= set(estimator.task_id)
    assert set(b1.columns).isdisjoint({"p_feas", "G_feas", "objective_final"})


def test_absent_portable_task_payload_is_regenerated_and_identity_checked():
    manifest = load_json(DISCOVERY_MANIFEST)
    row = dict(manifest["tasks"][0])
    assert not (DISCOVERY_MANIFEST.parents[2] / row["task_path"]).exists()
    task = task_from_manifest_row(row)
    assert task.task_id == row["task_id"]
    assert task.graph.graph_id == row["graph_id"]
    assert task.base_instance_id == row["base_instance_id"]
    assert task.size_stratum == row["size_stratum"]
    assert task.tightness_level == row["stress_level"]
    assert task.budget == row["budget"]


def test_smoke_namespace_is_distinct_from_formal_registry_namespace():
    formal = REVIEW_ROOT / "A3_finite_shot" / "training_runs" / "same-id.json"
    smoke = REVIEW_ROOT / "smoke" / "A3_finite_shot" / "training_runs" / "same-id.json"
    assert "smoke" not in formal.relative_to(REVIEW_ROOT).parts
    assert "smoke" in smoke.relative_to(REVIEW_ROOT).parts


def test_endpoint_objectives_are_recovered_from_frozen_sampling_rows():
    manifest = load_json(
        REVIEW_ROOT / "manifests" / "manifest_finite_shot.json"
    )
    assert "endpoint_objectives" not in manifest
    assert endpoint_objectives_from_manifest(manifest) == ("O0", "O3")


def test_b2_smoke_routes_records_to_isolated_namespace(monkeypatch):
    from qroute_dilution.reviewer_robustness import classical_rcsp

    observed = []

    def fake_execute(task_record, manifest, output_root):
        observed.append(output_root)
        return "COMPLETE"

    monkeypatch.setattr(classical_rcsp, "_execute_task", fake_execute)
    monkeypatch.setattr(classical_rcsp, "rebuild_registry", lambda: pd.DataFrame())
    result = classical_rcsp.run_b2(smoke=True)
    assert result == {"COMPLETE": 2}
    assert observed
    assert all("smoke" in path.relative_to(REVIEW_ROOT).parts for path in observed)
