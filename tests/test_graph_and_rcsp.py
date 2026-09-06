from __future__ import annotations

from qroute_dilution.graph_generator import generate_layered_graph
from qroute_dilution.rcsp import enumerate_simple_routes, solve_exact_rcsp


def test_graph_generation_deterministic():
    kwargs = dict(target_n_edges=7, layer_widths=[1, 2, 2, 1], seed=90210)
    assert generate_layered_graph(**kwargs).to_dict() == generate_layered_graph(**kwargs).to_dict()


def test_different_seed_changes_weighted_graph():
    first = generate_layered_graph(target_n_edges=7, layer_widths=[1, 2, 2, 1], seed=1)
    second = generate_layered_graph(target_n_edges=7, layer_widths=[1, 2, 2, 1], seed=2)
    assert first.graph_id != second.graph_id


def test_stable_edge_ordering():
    graph = generate_layered_graph(target_n_edges=10, layer_widths=[1, 2, 2, 2, 1], seed=4)
    pairs = [(edge.source, edge.target) for edge in graph.edges]
    assert pairs == sorted(pairs)
    assert [edge.index for edge in graph.edges] == list(range(len(graph.edges)))


def test_exact_rcsp_optimum(known_graph):
    routes = enumerate_simple_routes(known_graph)
    feasible, optimal, cost = solve_exact_rcsp(routes, budget=3.0)
    assert len(routes) == 2
    assert len(feasible) == 1
    assert len(optimal) == 1
    assert cost == 4.0
    assert optimal[0].nodes == (0, 1, 3)


def test_all_generated_edges_positive():
    graph = generate_layered_graph(target_n_edges=13, layer_widths=[1, 3, 3, 1], seed=11)
    assert all(edge.cost > 0 and edge.resource > 0 for edge in graph.edges)
