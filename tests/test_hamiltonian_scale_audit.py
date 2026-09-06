from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from qroute_dilution.hamiltonian_audit import (
    CONTROLLED_FLOW_STRENGTH,
    CONTROLLED_RESOURCE_STRENGTH,
    verify_phase06_frozen_evidence,
)
from qroute_dilution.penalties import build_raw_state_components, scale_controlled_penalties


def test_penalty_component_calculations(known_graph):
    components = build_raw_state_components(known_graph)
    valid_low_resource_route = (1 << 0) | (1 << 2)
    assert components.routing_cost[valid_low_resource_route] == 4.0
    assert components.flow_penalty_raw[valid_low_resource_route] == 0.0
    assert components.resource_total[valid_low_resource_route] == 2.0
    assert components.routing_cost[0] == 0.0
    assert components.flow_penalty_raw[0] == 2.0
    assert components.resource_total[0] == 0.0


def test_normalized_penalty_is_deterministic():
    flow = np.array([0.0, 2.0, 8.0, 20.0])
    excess = np.array([0.0, 1.0, 5.0, 15.0])
    first = scale_controlled_penalties(flow, excess, flow_scale=20.0, resource_scale=10.0)
    second = scale_controlled_penalties(flow, excess, flow_scale=20.0, resource_scale=10.0)
    assert np.array_equal(first[0], second[0])
    assert np.array_equal(first[1], second[1])


def test_controlled_penalty_classification_is_unchanged():
    flow = np.array([0.0, 2.0, 8.0, 20.0])
    excess = np.array([0.0, 1.0, 5.0, 15.0])
    controlled_flow, controlled_resource = scale_controlled_penalties(
        flow, excess, flow_scale=20.0, resource_scale=10.0
    )
    assert np.array_equal(controlled_flow > 0, flow > 0)
    assert np.array_equal(controlled_resource > 0, excess > 0)
    assert controlled_flow[1:].min() > 1.0
    assert controlled_resource[1:].min() > 1.0
    assert controlled_flow.max() <= 2.0
    assert controlled_resource.max() <= 2.0


def test_controlled_contract_preserves_exact_optimum(small_task_and_characterization):
    task, _ = small_task_and_characterization
    components = build_raw_state_components(task.graph)
    excess = np.maximum(0.0, components.resource_total - task.budget)
    flow, resource = scale_controlled_penalties(
        components.flow_penalty_raw,
        excess,
        flow_scale=float(components.flow_penalty_raw.max()),
        resource_scale=sum(edge.resource for edge in task.graph.edges),
    )
    energy = (
        components.routing_cost
        + CONTROLLED_FLOW_STRENGTH * flow
        + CONTROLLED_RESOURCE_STRENGTH * resource
    )
    ground_states = set(np.flatnonzero(np.isclose(energy, energy.min(), atol=1e-12)))
    exact_states = {route.bitstring_int for route in task.optimal_routes}
    assert ground_states
    assert ground_states.issubset(exact_states)


def test_generated_exact_ground_state_audit_is_complete():
    root = Path(__file__).resolve().parents[1]
    current = pd.read_csv(
        root / "results" / "phase0_v2_dilution_stress" / "hamiltonian_scale_audit.csv"
    )
    proposed = pd.read_csv(
        root / "results" / "phase0_v2_dilution_stress" / "penalty_contract_comparison.csv"
    )
    assert len(current) == len(proposed) == 140
    assert current["penalty_ground_state_valid"].all()
    assert current["penalty_ground_state_resource_feasible"].all()
    assert current["penalty_ground_state_original_optimal"].all()
    assert proposed["controlled_ground_state_valid"].all()
    assert proposed["controlled_ground_state_resource_feasible"].all()
    assert proposed["controlled_ground_state_original_optimal"].all()
