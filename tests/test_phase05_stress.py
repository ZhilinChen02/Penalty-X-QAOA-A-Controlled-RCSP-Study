from __future__ import annotations

import json
import math
from pathlib import Path

from qroute_dilution.metrics import dilution_score, log_feasibility_gain
from qroute_dilution.models import Route
from qroute_dilution.phase05 import verify_v1_evidence_hashes
from qroute_dilution.stress import build_stress_task_family, select_stress_levels


def _routes_with_resources(values):
    return tuple(
        Route(nodes=(0, index + 1), edge_indices=(index,), cost=float(index + 1), resource=float(value))
        for index, value in enumerate(values)
    )


def test_distinct_level_generation_is_deterministic():
    kwargs = dict(
        size_stratum="S2",
        target_n_edges=10,
        layer_widths=[1, 2, 2, 2, 1],
        base_index=2,
        master_seed=20260827,
        resource_range=(1, 1000),
        preferred_counts=(1, 2, 4, 8, 16, 32),
        max_levels=7,
    )
    first = build_stress_task_family(**kwargs)
    second = build_stress_task_family(**kwargs)
    signature = lambda family: [
        (
            task.task_id,
            task.graph.to_dict(),
            task.budget,
            selection.target_feasible_route_count,
            selection.actual_feasible_route_count,
        )
        for task, selection in family
    ]
    assert signature(first) == signature(second)


def test_budget_produces_intended_count_when_achievable():
    routes = _routes_with_resources(range(1, 11))
    selections = select_stress_levels(routes)
    exact_preferred = {1, 2, 4, 8, 10}
    for selection in selections:
        feasible_count = sum(route.resource <= selection.budget for route in routes)
        assert feasible_count == selection.actual_feasible_route_count
        if selection.target_feasible_route_count in exact_preferred:
            assert selection.actual_feasible_route_count == selection.target_feasible_route_count


def test_no_duplicate_feasible_set_within_base_graph():
    family = build_stress_task_family(
        size_stratum="S1",
        target_n_edges=7,
        layer_widths=[1, 2, 2, 1],
        base_index=0,
        master_seed=20260827,
        resource_range=(1, 1000),
        preferred_counts=(1, 2, 4, 8, 16, 32),
        max_levels=7,
    )
    counts = [selection.actual_feasible_route_count for _, selection in family]
    budgets = [task.budget for task, _ in family]
    assert len(counts) == len(set(counts))
    assert len(budgets) == len(set(budgets))
    assert len(family) < 7  # explicitly insufficient, never padded with duplicates


def test_tied_resources_use_only_achievable_counts():
    routes = _routes_with_resources([1, 1, 3, 3, 5])
    selections = select_stress_levels(routes)
    assert [selection.actual_feasible_route_count for selection in selections] == [2, 4, 5]
    assert all(selection.actual_feasible_route_count != 1 for selection in selections)


def test_dilution_score_formula():
    assert math.isclose(dilution_score(1e-5), 5.0)
    assert math.isnan(dilution_score(0.0))
    assert math.isnan(dilution_score(-1.0))


def test_log_feasibility_gain_formula():
    assert math.isclose(log_feasibility_gain(1e-3, 1e-4), 1.0)
    assert math.isclose(log_feasibility_gain(1e-5, 1e-4), -1.0)
    assert math.isclose(log_feasibility_gain(1e-4, 1e-4), 0.0)
    assert math.isnan(log_feasibility_gain(0.0, 1e-4))
    assert math.isnan(log_feasibility_gain(1e-4, 0.0))


def test_v1_evidence_remains_byte_identical():
    fixture_path = Path(__file__).parent / "fixtures" / "v1_evidence_sha256.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))["files"]
    assert verify_v1_evidence_hashes() == expected
