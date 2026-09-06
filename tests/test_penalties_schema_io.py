from __future__ import annotations

import copy
from dataclasses import replace

import numpy as np
import pandas as pd

from qroute_dilution.io import append_canonical_rows
from qroute_dilution.penalties import build_diagonal_energies
from qroute_dilution.schemas import CANONICAL_FIELDS, make_uniform_row, run_penalty_x


def test_resource_penalty_is_present(known_graph):
    components = build_diagonal_energies(
        known_graph, budget=5.0, flow_penalty_strength=0.0, resource_penalty_strength=1.0
    )
    high_resource_route = (1 << 1) | (1 << 3)
    low_resource_route = (1 << 0) | (1 << 2)
    assert components.resource_penalty[high_resource_route] == 1.0
    assert components.resource_penalty[low_resource_route] == 0.0
    assert components.total[high_resource_route] > components.objective_cost[high_resource_route]


def test_canonical_schema_contains_required_fields(small_task_and_characterization):
    task, characterization = small_task_and_characterization
    row = make_uniform_row(task, characterization)
    assert list(row) == CANONICAL_FIELDS
    assert row["uniform_p_feas"] == row["feasible_state_fraction"]


def test_schema_identity_does_not_require_dataframe_index_column(small_task_and_characterization):
    task, characterization = small_task_and_characterization
    indexed_payload = dict(characterization)
    indexed_payload.pop("task_id")
    row = make_uniform_row(task, indexed_payload)
    assert row["task_id"] == task.task_id
    assert row["graph_id"] == task.graph.graph_id


def test_result_scientific_fields_reproducible_with_same_seed(small_task_and_characterization):
    task, characterization = small_task_and_characterization
    kwargs = dict(
        depth=1,
        seed=77,
        flow_penalty_strength=50.0,
        resource_penalty_strength=20.0,
        eval_budget=18,
    )
    first = run_penalty_x(task, characterization, **kwargs)
    second = run_penalty_x(task, characterization, **kwargs)
    stable_fields = [
        "run_id",
        "initial_parameters",
        "optimized_parameters",
        "nfev",
        "status",
        "objective_initial",
        "objective_final",
        "p_feas",
        "p_opt",
        "p_opt_given_feasible",
        "feasibility_amplification",
        "execution_status",
    ]
    for field in stable_fields:
        if isinstance(first[field], float):
            assert np.allclose(first[field], second[field], equal_nan=True)
        else:
            assert first[field] == second[field]


def test_failure_rows_are_retained(tmp_path, small_task_and_characterization):
    task, characterization = small_task_and_characterization
    success = make_uniform_row(task, characterization)
    failure = copy.deepcopy(success)
    failure["run_id"] = "run-deliberate-failure"
    failure["execution_status"] = "OOM"
    failure["failure_reason"] = "deliberate test row"
    path = tmp_path / "results.csv"
    append_canonical_rows(path, [success])
    append_canonical_rows(path, [failure])
    # Duplicate restart write must not remove either original row.
    append_canonical_rows(path, [failure])
    stored = pd.read_csv(path)
    assert len(stored) == 2
    assert set(stored["execution_status"]) == {"SUCCESS", "OOM"}
    assert "deliberate test row" in set(stored["failure_reason"].dropna())


def test_zero_feasible_state_is_marked_and_nan(small_task_and_characterization):
    task, characterization = small_task_and_characterization
    empty_task = replace(task, feasible_routes=(), optimal_routes=(), optimal_cost=None)
    empty_char = dict(characterization)
    empty_char.update(
        n_feasible_routes=0,
        route_feasible_fraction=0.0,
        n_feasible_states=0,
        feasible_state_fraction=0.0,
        n_optimal_states=0,
        optimal_cost=np.nan,
        zero_feasible=True,
    )
    row = make_uniform_row(empty_task, empty_char)
    assert row["execution_status"] == "NO_FEASIBLE_STATE"
    assert np.isnan(row["feasibility_amplification"])


def test_optimizer_timeout_becomes_canonical_row(small_task_and_characterization):
    task, characterization = small_task_and_characterization
    row = run_penalty_x(
        task,
        characterization,
        depth=1,
        seed=4,
        flow_penalty_strength=50.0,
        resource_penalty_strength=20.0,
        eval_budget=20,
        timeout_s=0.0,
    )
    assert row["execution_status"] == "TIMEOUT"
    assert "timeout" in row["failure_reason"]


def test_exhaustive_feasible_state_count_agrees(small_task_and_characterization):
    task, characterization = small_task_and_characterization
    assert characterization["n_feasible_states"] == len(task.feasible_routes)
    assert characterization["state_space_size"] == 2 ** task.actual_n_edges
