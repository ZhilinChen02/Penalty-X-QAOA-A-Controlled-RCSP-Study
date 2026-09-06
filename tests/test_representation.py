from __future__ import annotations

from qroute_dilution.exact import enumerate_structural_path_states
from qroute_dilution.rcsp import enumerate_simple_routes
from qroute_dilution.representation import validate_bitstring, validate_edge_selection


def test_valid_route_decoding(known_graph):
    # edge indices 0 and 2 form 0->1->3
    result = validate_edge_selection(known_graph, (1 << 0) | (1 << 2), budget=2.0)
    assert result.feasible
    assert result.route_nodes == (0, 1, 3)


def test_bitstring_uses_edge_index_order(known_graph):
    result = validate_bitstring(known_graph, "1010", budget=2.0)
    assert result.feasible
    assert result.selected_edge_indices == (0, 2)


def test_detached_cycles_rejected(detached_cycle_graph):
    result = validate_edge_selection(detached_cycle_graph, 0b111, budget=10.0)
    assert not result.valid_structure
    assert result.reason == "EXTRANEOUS_EDGES"


def test_resource_violation_rejected(known_graph):
    result = validate_edge_selection(known_graph, (1 << 1) | (1 << 3), budget=5.0)
    assert result.valid_structure
    assert not result.resource_feasible
    assert result.reason == "RESOURCE_VIOLATION"


def test_branching_flow_violation_rejected(known_graph):
    result = validate_edge_selection(known_graph, 0b1111, budget=20.0)
    assert not result.valid_structure
    assert result.reason == "FLOW_VIOLATION"


def test_exhaustive_structural_count_agrees_with_route_enumeration(known_graph):
    states = enumerate_structural_path_states(known_graph)
    routes = enumerate_simple_routes(known_graph)
    assert len(states) == len(routes) == 2
    assert {state.state for state in states} == {route.bitstring_int for route in routes}
