"""Exact rational RCSP edge subdivision and route-bijection checks."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Hashable, Iterable, Sequence


Node = Hashable


@dataclass(frozen=True)
class RationalEdge:
    name: str
    source: Node
    target: Node
    cost: Fraction
    resources: tuple[Fraction, ...]

    @classmethod
    def make(
        cls,
        name: str,
        source: Node,
        target: Node,
        cost: int | float | str | Fraction,
        resources: Sequence[int | float | str | Fraction],
    ) -> "RationalEdge":
        return cls(
            str(name),
            source,
            target,
            Fraction(cost),
            tuple(Fraction(value) for value in resources),
        )


@dataclass(frozen=True)
class RationalRCSP:
    vertices: tuple[Node, ...]
    edges: tuple[RationalEdge, ...]
    source: Node
    target: Node
    budgets: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.vertices) != len(set(self.vertices)):
            raise ValueError("vertices must be distinct")
        if self.source not in self.vertices or self.target not in self.vertices:
            raise ValueError("source and target must be vertices")
        if len({edge.name for edge in self.edges}) != len(self.edges):
            raise ValueError("edge names must be distinct")
        resource_count = len(self.budgets)
        if any(len(edge.resources) != resource_count for edge in self.edges):
            raise ValueError("every edge must have one coefficient per resource")
        if any(edge.source not in self.vertices or edge.target not in self.vertices for edge in self.edges):
            raise ValueError("edge endpoint is not a vertex")
        if any(value < 0 for edge in self.edges for value in edge.resources):
            raise ValueError("resource coefficients must be nonnegative")


@dataclass(frozen=True)
class RouteRecord:
    nodes: tuple[Node, ...]
    edges: tuple[str, ...]
    cost: Fraction
    resources: tuple[Fraction, ...]
    feasible: bool


@dataclass(frozen=True)
class PaddingResult:
    original: RationalRCSP
    padded: RationalRCSP
    expanded_edge: str
    segment_edges: tuple[str, ...]
    r: int

    def expand_route(self, edge_names: Sequence[str]) -> tuple[str, ...]:
        result: list[str] = []
        for name in edge_names:
            result.extend(self.segment_edges if name == self.expanded_edge else (name,))
        return tuple(result)

    def contract_route(self, edge_names: Sequence[str]) -> tuple[str, ...]:
        values = tuple(edge_names)
        result: list[str] = []
        index = 0
        while index < len(values):
            if values[index] == self.segment_edges[0]:
                block = values[index : index + self.r]
                if block != self.segment_edges:
                    raise ValueError("padded route contains an incomplete subdivision chain")
                result.append(self.expanded_edge)
                index += self.r
            else:
                if values[index] in self.segment_edges:
                    raise ValueError("padded route enters a subdivision chain internally")
                result.append(values[index])
                index += 1
        return tuple(result)


def make_instance(
    vertices: Iterable[Node],
    edges: Iterable[RationalEdge],
    source: Node,
    target: Node,
    budgets: Sequence[int | float | str | Fraction],
) -> RationalRCSP:
    return RationalRCSP(
        tuple(vertices), tuple(edges), source, target, tuple(Fraction(value) for value in budgets)
    )


def enumerate_simple_routes(instance: RationalRCSP) -> tuple[RouteRecord, ...]:
    adjacency: dict[Node, list[RationalEdge]] = {vertex: [] for vertex in instance.vertices}
    for edge in instance.edges:
        adjacency[edge.source].append(edge)
    for values in adjacency.values():
        values.sort(key=lambda edge: edge.name)
    routes: list[RouteRecord] = []

    def visit(
        node: Node,
        seen: frozenset[Node],
        nodes: tuple[Node, ...],
        edges: tuple[str, ...],
        cost: Fraction,
        resources: tuple[Fraction, ...],
    ) -> None:
        if node == instance.target:
            routes.append(
                RouteRecord(
                    nodes,
                    edges,
                    cost,
                    resources,
                    all(value <= budget for value, budget in zip(resources, instance.budgets)),
                )
            )
            return
        for edge in adjacency[node]:
            if edge.target in seen:
                continue
            visit(
                edge.target,
                seen | {edge.target},
                nodes + (edge.target,),
                edges + (edge.name,),
                cost + edge.cost,
                tuple(a + b for a, b in zip(resources, edge.resources)),
            )

    zero_resources = tuple(Fraction(0) for _ in instance.budgets)
    visit(instance.source, frozenset({instance.source}), (instance.source,), (), Fraction(0), zero_resources)
    return tuple(routes)


def subdivide_edge(instance: RationalRCSP, edge_name: str, r: int) -> PaddingResult:
    """Replace one edge by r serial edges, splitting every coefficient exactly."""
    if r <= 0 or int(r) != r:
        raise ValueError("r must be a positive integer")
    matches = [edge for edge in instance.edges if edge.name == edge_name]
    if len(matches) != 1:
        raise ValueError("edge_name must identify exactly one edge")
    original = matches[0]
    r = int(r)
    if r == 1:
        return PaddingResult(instance, instance, edge_name, (edge_name,), 1)

    occupied = set(instance.vertices)
    new_vertices: list[Node] = []
    for segment in range(1, r):
        candidate: Node = f"__pad_{edge_name}_{segment}"
        suffix = 0
        while candidate in occupied:
            suffix += 1
            candidate = f"__pad_{edge_name}_{segment}_{suffix}"
        occupied.add(candidate)
        new_vertices.append(candidate)

    chain_nodes = (original.source, *new_vertices, original.target)
    segment_names = tuple(f"{edge_name}::segment::{index + 1}/{r}" for index in range(r))
    split_cost = original.cost / r
    split_resources = tuple(value / r for value in original.resources)
    segments = tuple(
        RationalEdge(
            segment_names[index],
            chain_nodes[index],
            chain_nodes[index + 1],
            split_cost,
            split_resources,
        )
        for index in range(r)
    )
    edges: list[RationalEdge] = []
    for edge in instance.edges:
        edges.extend(segments if edge.name == edge_name else (edge,))
    padded = RationalRCSP(
        instance.vertices + tuple(new_vertices),
        tuple(edges),
        instance.source,
        instance.target,
        instance.budgets,
    )
    return PaddingResult(instance, padded, edge_name, segment_names, r)


def feasible_route_count(instance: RationalRCSP) -> int:
    return sum(route.feasible for route in enumerate_simple_routes(instance))


def raw_edge_bit_phi(instance: RationalRCSP) -> Fraction:
    return Fraction(feasible_route_count(instance), 2 ** len(instance.edges))


def exact_optimum(instance: RationalRCSP) -> Fraction | None:
    feasible = [route.cost for route in enumerate_simple_routes(instance) if route.feasible]
    return min(feasible) if feasible else None


def coefficient_bit_length(value: Fraction) -> int:
    value = Fraction(value)
    return max(1, abs(value.numerator).bit_length()) + max(1, value.denominator.bit_length())


def maximum_coefficient_bit_length(instance: RationalRCSP) -> int:
    values = [*instance.budgets]
    for edge in instance.edges:
        values.extend((edge.cost, *edge.resources))
    return max((coefficient_bit_length(value) for value in values), default=1)


def padding_audit(result: PaddingResult) -> dict[str, object]:
    original_routes = enumerate_simple_routes(result.original)
    padded_routes = enumerate_simple_routes(result.padded)
    original_by_edges = {route.edges: route for route in original_routes}
    padded_by_contracted = {result.contract_route(route.edges): route for route in padded_routes}
    bijection = set(original_by_edges) == set(padded_by_contracted)
    totals_preserved = bijection and all(
        original_by_edges[key].cost == padded_by_contracted[key].cost
        and original_by_edges[key].resources == padded_by_contracted[key].resources
        for key in original_by_edges
    )
    feasibility_preserved = totals_preserved and all(
        original_by_edges[key].feasible == padded_by_contracted[key].feasible
        for key in original_by_edges
    )
    original_phi = raw_edge_bit_phi(result.original)
    padded_phi = raw_edge_bit_phi(result.padded)
    expected_phi = original_phi / (2 ** (result.r - 1))
    return {
        "r": result.r,
        "original_edges": len(result.original.edges),
        "padded_edges": len(result.padded.edges),
        "route_bijection": bijection,
        "totals_preserved": totals_preserved,
        "feasibility_preserved": feasibility_preserved,
        "objective_ordering_preserved": totals_preserved,
        "optimum_preserved": exact_optimum(result.original) == exact_optimum(result.padded),
        "valid_feasible_route_count_preserved": feasible_route_count(result.original)
        == feasible_route_count(result.padded),
        "original_phi_numerator": original_phi.numerator,
        "original_phi_denominator": original_phi.denominator,
        "padded_phi_numerator": padded_phi.numerator,
        "padded_phi_denominator": padded_phi.denominator,
        "phi_factor_exact": padded_phi == expected_phi,
        "original_coefficient_bits": maximum_coefficient_bit_length(result.original),
        "padded_coefficient_bits": maximum_coefficient_bit_length(result.padded),
        "coefficient_growth_upper_bound": maximum_coefficient_bit_length(result.original)
        + max(1, result.r.bit_length()),
        "explicit_topology_growth": result.r - 1,
    }


def unique_chain_instance(m: int) -> RationalRCSP:
    if m <= 0 or int(m) != m:
        raise ValueError("m must be a positive integer")
    vertices = tuple(range(int(m) + 1))
    edges = tuple(
        RationalEdge.make(f"e{index}", index, index + 1, 1, (1,))
        for index in range(int(m))
    )
    return make_instance(vertices, edges, 0, int(m), (int(m),))
