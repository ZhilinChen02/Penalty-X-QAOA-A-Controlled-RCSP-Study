from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from qroute_dilution.graph_generator import derive_seed, generate_layered_graph
from qroute_dilution.io import PROJECT_ROOT, load_config
from qroute_dilution.phase2_statistics import holm_adjust
from qroute_dilution.phase3_execution import apply_upper_tail_resource_censoring
from qroute_dilution.phase3_models import (
    FREEZE_HASH_PATH,
    FREEZE_PATH,
    MODEL_IDS,
    base_graph_exponents,
    bootstrap_summary,
    leave_one_base_graph_out_cv,
    load_frozen_models,
    model_matrix,
    prepare_scaling_rows,
    select_model_one_standard_error,
)
from qroute_dilution.phase3_tasks import (
    CONFIG_PATH,
    DEVELOPMENT_PATH,
    EXTRAPOLATION_PATH,
    INTERPOLATION_PATH,
    MANIFEST_HASH_PATH,
    UNIVERSE_PATH,
    achievable_route_thresholds,
    build_phase3_energy_context,
    log_spaced_cardinality_targets,
    predecessor_hash_inventory,
    select_six_cardinalities,
    sha256_file,
)
from qroute_dilution.rcsp import enumerate_simple_routes, solve_exact_rcsp


def _representative_graph(size_m: int = 12):
    config = load_config(CONFIG_PATH)
    widths = config["layer_width_templates"][size_m][0]
    return generate_layered_graph(
        target_n_edges=size_m,
        layer_widths=widths,
        seed=derive_seed(config["master_seed"], "phase3-test", size_m),
        cost_range=tuple(config["cost_range"]),
        resource_range=tuple(config["resource_range"]),
    )


def test_phase3_exact_target_edge_size_policy_and_stable_ordering():
    config = load_config(CONFIG_PATH)
    for size_m in config["sizes"]:
        graph = _representative_graph(size_m)
        assert len(graph.edges) == size_m
        assert [edge.index for edge in graph.edges] == list(range(size_m))
        assert [(edge.source, edge.target) for edge in graph.edges] == sorted(
            (edge.source, edge.target) for edge in graph.edges
        )


def test_log_spaced_cardinality_determinism_and_six_distinct_counts():
    assert log_spaced_cardinality_targets(6) == (1, 2, 3, 4, 5, 6)
    first = log_spaced_cardinality_targets(37)
    second = log_spaced_cardinality_targets(37)
    assert first == second
    assert len(first) == len(set(first)) == 6
    assert first[0] == 1 and first[-1] == 37


def test_minimum_route_richness_and_exact_threshold_counts():
    config = load_config(CONFIG_PATH)
    for attempt in range(config["maximum_generation_attempts"]):
        graph = generate_layered_graph(
            target_n_edges=12,
            layer_widths=config["layer_width_templates"][12][0],
            seed=derive_seed(config["master_seed"], "phase3", 12, 0, attempt),
            cost_range=tuple(config["cost_range"]),
            resource_range=tuple(config["resource_range"]),
        )
        routes = enumerate_simple_routes(graph)
        if len(routes) >= 6 and len(achievable_route_thresholds(routes)) >= 6:
            break
    selections = select_six_cardinalities(routes)
    assert len(routes) >= 6
    assert len(selections) == 6
    assert len({selection.intended_count for selection in selections}) == 6
    for selection in selections:
        feasible, _, _ = solve_exact_rcsp(routes, selection.budget)
        assert len(feasible) == selection.intended_count


def test_phase3_global_lambda_199_preserves_exact_ground_state():
    from qroute_dilution.models import Task

    graph = _representative_graph(12)
    routes = enumerate_simple_routes(graph)
    selection = select_six_cardinalities(routes)[2]
    feasible, optimal, optimal_cost = solve_exact_rcsp(routes, selection.budget)
    task = Task(
        "unit-phase3", "unit-base", "m12", "L3", 12, 12, 7,
        selection.budget, math.nan, False, False, graph, routes, feasible,
        optimal, optimal_cost,
    )
    context = build_phase3_energy_context(task)
    ground = set(np.flatnonzero(np.isclose(context["raw_energy"], context["raw_energy"].min())))
    assert ground == {route.bitstring_int for route in optimal}
    assert context["raw_energy"][~context["feasible_mask"]].min() > context["raw_energy"][context["feasible_mask"]].max()
    assert np.allclose(context["energy"], context["raw_energy"] / 199.0)




def test_generated_split_disjointness_and_hashes_when_universe_exists():
    if not UNIVERSE_PATH.exists():
        pytest.skip("prospective universe is generated before the formal full test run")
    universe = json.loads(UNIVERSE_PATH.read_text())
    manifests = [json.loads(path.read_text()) for path in (DEVELOPMENT_PATH, INTERPOLATION_PATH, EXTRAPOLATION_PATH)]
    sets = [set(value["base_graph_ids"]) for value in manifests]
    assert universe["task_count"] == 180 and universe["base_graph_count"] == 30
    assert [value["task_count"] for value in manifests] == [96, 24, 60]
    assert not sets[0] & sets[1] and not sets[0] & sets[2] and not sets[1] & sets[2]
    hashes = json.loads(MANIFEST_HASH_PATH.read_text())
    for path in (UNIVERSE_PATH, DEVELOPMENT_PATH, INTERPOLATION_PATH, EXTRAPOLATION_PATH):
        assert hashes[path.name] == sha256_file(path)


def _synthetic_scaling_frame() -> pd.DataFrame:
    rows = []
    for graph_index in range(5):
        for level, d in enumerate(np.linspace(1, 3, 6)):
            eta = 0.4 + 0.01 * graph_index
            p = 10 ** (-0.2 - eta * d)
            rows.append(
                {
                    "base_graph_id": f"g{graph_index}", "task_id": f"g{graph_index}-{level}",
                    "split": "development", "size_m": 12 + 2 * (graph_index % 4),
                    "objective_id": "O0", "p_feas": p, "dilution_score": d,
                    "resource_censored": False,
                }
            )
    return pd.DataFrame(rows)


def test_within_graph_centering_and_zero_pfeas_handling_no_epsilon():
    frame = _synthetic_scaling_frame()
    frame.loc[0, "p_feas"] = 0.0
    prepared = prepare_scaling_rows(frame)
    assert prepared.loc[0, "zero_p_feas"]
    assert math.isnan(prepared.loc[0, "Y"])
    finite = prepared[np.isfinite(prepared.Y)]
    assert np.allclose(finite.groupby(["base_graph_id", "objective_id"]).Yc.sum(), 0.0)
    assert np.allclose(prepared.groupby(["base_graph_id", "objective_id"]).Dc.sum(), 0.0)


def test_eta_kappa_identity_to_tighter_than_frozen_tolerance():
    exponents = base_graph_exponents(_synthetic_scaling_frame())
    assert len(exponents) == 5
    assert exponents.eta_kappa_identity_error.max() < 1e-12
    assert np.allclose(exponents.kappa, 1.0 - exponents.eta)


def test_candidate_model_formulas_and_leave_one_graph_out_cv():
    prepared = prepare_scaling_rows(_synthetic_scaling_frame())
    expected_columns = {"M1": 1, "M2": 2, "M3": 2, "M4": 3}
    for model_id in MODEL_IDS:
        matrix = model_matrix(prepared, model_id)
        assert matrix.shape == (len(prepared), expected_columns[model_id])
        metrics = leave_one_base_graph_out_cv(prepared, model_id)
        assert metrics["n_base_graphs"] == 5
        assert np.isfinite(metrics["cv_rmse"])


def test_one_standard_error_selection_uses_frozen_complexity_order():
    metrics = pd.DataFrame(
        {
            "model_id": ["M1", "M2", "M3", "M4"],
            "cv_rmse": [1.05, 1.00, 0.99, 0.98],
            "cv_rmse_se": [0.01, 0.01, 0.01, 0.08],
        }
    )
    assert select_model_one_standard_error(metrics) == "M1"


def test_model_freeze_hash_and_holdout_access_guard():
    if FREEZE_PATH.exists():
        frozen = load_frozen_models()
        identity = json.loads(FREEZE_HASH_PATH.read_text())
        assert identity["scaling_model_freeze_sha256"] == sha256_file(FREEZE_PATH)
        assert frozen["holdout_qaoa_inspected"] is False
    else:
        with pytest.raises(RuntimeError, match="holdout access denied"):
            load_frozen_models()


def test_resource_censoring_is_all_tasks_at_and_above_failed_size():
    frame = pd.DataFrame(
        {"size_m": [12, 14, 16, 18, 20, 22], "resource_guard_pass": [True, True, True, True, False, True], "resource_censored": [False] * 6}
    )
    censored = apply_upper_tail_resource_censoring(frame)
    assert censored.loc[censored.resource_censored, "size_m"].tolist() == [20, 22]
    assert not censored.loc[censored.size_m >= 20, "resource_guard_pass"].any()


def test_cluster_bootstrap_resamples_base_graph_values_and_holm_family():
    summary = bootstrap_summary(np.array([0.1, 0.2, 0.3]), resamples=500, seed=9)
    assert summary["n"] == 3
    assert summary["ci_lower"] <= summary["mean"] <= summary["ci_upper"]
    adjusted = holm_adjust({"S-H1": 0.01, "S-H2": 0.02, "S-H3": 0.04})
    assert adjusted == {"S-H1": 0.03, "S-H2": 0.04, "S-H3": 0.04}
