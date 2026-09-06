"""Exact simple-route enumeration and deterministic RCSP task construction."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence

import numpy as np

from .graph_generator import derive_seed, generate_layered_graph
from .models import DirectedGraph, Route, Task


def enumerate_simple_routes(graph: DirectedGraph) -> tuple[Route, ...]:
    """Enumerate all directed simple source-target routes in stable DFS order."""
    adjacency: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for edge in graph.edges:
        adjacency[edge.source].append((edge.target, edge.index))
    for outgoing in adjacency.values():
        outgoing.sort()

    routes: list[Route] = []

    def visit(node: int, nodes: list[int], edge_indices: list[int], visited: set[int]) -> None:
        if node == graph.target:
            selected = [graph.edges[index] for index in edge_indices]
            routes.append(
                Route(
                    nodes=tuple(nodes),
                    edge_indices=tuple(edge_indices),
                    cost=float(sum(edge.cost for edge in selected)),
                    resource=float(sum(edge.resource for edge in selected)),
                )
            )
            return
        for next_node, edge_index in adjacency.get(node, []):
            if next_node in visited:
                continue
            visit(
                next_node,
                [*nodes, next_node],
                [*edge_indices, edge_index],
                visited | {next_node},
            )

    visit(graph.source, [graph.source], [], {graph.source})
    return tuple(sorted(routes, key=lambda r: (r.nodes, r.edge_indices)))


def solve_exact_rcsp(
    routes: Sequence[Route], budget: float, *, atol: float = 1e-12
) -> tuple[tuple[Route, ...], tuple[Route, ...], float | None]:
    feasible = tuple(route for route in routes if route.resource <= budget + atol)
    if not feasible:
        return feasible, (), None
    optimal_cost = min(route.cost for route in feasible)
    optimal = tuple(route for route in feasible if abs(route.cost - optimal_cost) <= atol)
    return feasible, optimal, float(optimal_cost)


def budget_from_quantile(
    routes: Sequence[Route], quantile: float, method: str = "lower"
) -> float:
    if not routes:
        raise ValueError("cannot derive a resource budget without candidate routes")
    values = np.asarray([route.resource for route in routes], dtype=float)
    return float(np.quantile(values, quantile, method=method))


def build_task_family(
    *,
    size_stratum: str,
    target_n_edges: int,
    layer_widths: Sequence[int],
    base_index: int,
    master_seed: int,
    tightness_levels: Mapping[str, float],
    quantile_method: str = "lower",
    cost_range: tuple[int, int] = (1, 9),
    resource_range: tuple[int, int] = (1, 9),
) -> tuple[Task, ...]:
    """Build one base graph and its frozen quantile-derived budget variants."""
    started = time.perf_counter()
    generation_seed = derive_seed(master_seed, size_stratum, base_index)
    graph = generate_layered_graph(
        target_n_edges=target_n_edges,
        layer_widths=layer_widths,
        seed=generation_seed,
        cost_range=cost_range,
        resource_range=resource_range,
    )
    routes = enumerate_simple_routes(graph)
    if not routes:
        raise RuntimeError("generator invariant violated: graph has no source-target route")
    task_build_time = time.perf_counter() - started

    base_instance_id = f"{size_stratum}-b{base_index:03d}-{graph.graph_id}"
    seen_budgets: set[float] = set()
    seen_sets: set[tuple[int, ...]] = set()
    tasks: list[Task] = []
    for level, quantile in tightness_levels.items():
        exact_started = time.perf_counter()
        budget = budget_from_quantile(routes, float(quantile), quantile_method)
        feasible, optimal, optimal_cost = solve_exact_rcsp(routes, budget)
        exact_time = time.perf_counter() - exact_started
        feasible_signature = tuple(route.bitstring_int for route in feasible)
        duplicate_budget = budget in seen_budgets
        duplicate_feasible_set = feasible_signature in seen_sets
        seen_budgets.add(budget)
        seen_sets.add(feasible_signature)
        raw_task_id = f"{base_instance_id}|{level}|{budget:g}"
        task_hash = hashlib.sha256(raw_task_id.encode()).hexdigest()[:12]
        tasks.append(
            Task(
                task_id=f"task-{task_hash}",
                base_instance_id=base_instance_id,
                size_stratum=size_stratum,
                tightness_level=level,
                target_n_edges=target_n_edges,
                actual_n_edges=len(graph.edges),
                generation_seed=generation_seed,
                budget=budget,
                quantile=float(quantile),
                duplicate_budget=duplicate_budget,
                duplicate_feasible_set=duplicate_feasible_set,
                graph=graph,
                candidate_routes=routes,
                feasible_routes=feasible,
                optimal_routes=optimal,
                optimal_cost=optimal_cost,
                task_build_time_s=task_build_time,
                exact_reference_time_s=exact_time,
            )
        )
    return tuple(tasks)
