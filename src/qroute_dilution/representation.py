"""Strict edge-bit representation validation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import DirectedGraph


@dataclass(frozen=True)
class ValidationResult:
    valid_structure: bool
    resource_feasible: bool
    selected_edge_indices: tuple[int, ...]
    route_nodes: tuple[int, ...]
    cost: float
    resource: float
    reason: str

    @property
    def feasible(self) -> bool:
        return self.valid_structure and self.resource_feasible


def validate_edge_selection(
    graph: DirectedGraph,
    state: int,
    budget: float,
    *,
    atol: float = 1e-12,
) -> ValidationResult:
    """Validate that selected edges are exactly one connected directed s->t route.

    Flow is checked first. Then the route is reconstructed from the source and the
    traversed edge set must equal the complete selected set. This last equality
    rejects detached cycles, attached circulation, and all extraneous edges.
    """
    if state < 0 or state >= (1 << len(graph.edges)):
        raise ValueError("state is outside the edge-bit representation")
    selected = tuple(i for i in range(len(graph.edges)) if state & (1 << i))
    selected_set = set(selected)
    balances = [0] * graph.n_nodes
    outgoing: dict[int, list[int]] = {node: [] for node in range(graph.n_nodes)}
    cost = 0.0
    resource = 0.0
    for index in selected:
        edge = graph.edges[index]
        balances[edge.source] += 1
        balances[edge.target] -= 1
        outgoing[edge.source].append(index)
        cost += edge.cost
        resource += edge.resource
    expected = [0] * graph.n_nodes
    expected[graph.source] = 1
    expected[graph.target] = -1
    if balances != expected:
        return ValidationResult(False, False, selected, (), cost, resource, "FLOW_VIOLATION")

    current = graph.source
    route_nodes = [current]
    traversed: list[int] = []
    visited = {current}
    while current != graph.target:
        choices = outgoing.get(current, [])
        if len(choices) != 1:
            return ValidationResult(
                False, False, selected, tuple(route_nodes), cost, resource, "NON_UNIQUE_ROUTE"
            )
        edge_index = choices[0]
        edge = graph.edges[edge_index]
        traversed.append(edge_index)
        current = edge.target
        if current in visited:
            return ValidationResult(
                False, False, selected, tuple(route_nodes), cost, resource, "DIRECTED_CYCLE"
            )
        visited.add(current)
        route_nodes.append(current)
        if len(traversed) > len(selected):
            return ValidationResult(
                False, False, selected, tuple(route_nodes), cost, resource, "ROUTE_OVERFLOW"
            )

    if set(traversed) != selected_set:
        return ValidationResult(
            False, False, selected, tuple(route_nodes), cost, resource, "EXTRANEOUS_EDGES"
        )
    resource_feasible = resource <= budget + atol
    return ValidationResult(
        True,
        resource_feasible,
        selected,
        tuple(route_nodes),
        cost,
        resource,
        "VALID" if resource_feasible else "RESOURCE_VIOLATION",
    )


def validate_bitstring(
    graph: DirectedGraph, bitstring: str, budget: float
) -> ValidationResult:
    """Validate an edge-index ordered string (leftmost character is edge 0)."""
    if len(bitstring) != len(graph.edges) or set(bitstring) - {"0", "1"}:
        raise ValueError("bitstring must have one binary character per edge")
    state = sum((char == "1") << index for index, char in enumerate(bitstring))
    return validate_edge_selection(graph, state, budget)
