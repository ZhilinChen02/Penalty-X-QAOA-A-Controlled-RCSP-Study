"""Prospective Phase 0.5 distinct-cardinality dilution stress construction."""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass
from collections.abc import Sequence

from .graph_generator import derive_seed, generate_layered_graph
from .models import Route, Task
from .rcsp import enumerate_simple_routes, solve_exact_rcsp


INSUFFICIENT_STATUS = "INSUFFICIENT_DISTINCT_FEASIBLE_SETS"


@dataclass(frozen=True)
class StressSelection:
    target_feasible_route_count: int
    actual_feasible_route_count: int
    budget: float
    selection_reason: str


def achievable_feasible_counts(routes: Sequence[Route]) -> tuple[tuple[int, float], ...]:
    """Return (cumulative feasible count, threshold budget) for unique resources."""
    resource_counts: dict[float, int] = {}
    for route in routes:
        resource_counts[route.resource] = resource_counts.get(route.resource, 0) + 1
    cumulative = 0
    achievable: list[tuple[int, float]] = []
    for resource, count in sorted(resource_counts.items()):
        cumulative += count
        achievable.append((cumulative, float(resource)))
    return tuple(achievable)


def select_stress_levels(
    routes: Sequence[Route],
    preferred_counts: Sequence[int] = (1, 2, 4, 8, 16, 32),
    max_levels: int = 7,
) -> tuple[StressSelection, ...]:
    """Select up to max_levels distinct feasible sets near preferred cardinalities.

    Exactly achievable preferred counts are reserved first. Unachievable preferred
    counts map to the nearest unused achievable count in log-cardinality distance.
    Any remaining capacity is filled with achievable counts farthest from the
    selected counts, increasing resolution without duplicating a feasible set.
    """
    achievable = achievable_feasible_counts(routes)
    if not achievable:
        return ()
    count_to_budget = dict(achievable)
    counts = tuple(count_to_budget)
    n_routes = len(routes)
    n_select = min(int(max_levels), len(counts))
    desired = []
    for value in (*preferred_counts, n_routes):
        value = int(value)
        if 1 <= value <= n_routes and value not in desired:
            desired.append(value)

    selected: dict[int, tuple[int, str]] = {}
    for target in desired:
        if target in count_to_budget and len(selected) < n_select:
            selected[target] = (target, "PREFERRED_EXACT")

    for target in desired:
        if len(selected) >= n_select:
            break
        if target in selected:
            continue
        available = [count for count in counts if count not in selected]
        if not available:
            break
        actual = min(available, key=lambda count: (abs(math.log(count / target)), count))
        selected[actual] = (target, "PREFERRED_NEAREST_ACHIEVABLE")

    while len(selected) < n_select:
        available = [count for count in counts if count not in selected]
        if not selected:
            actual = available[0]
        else:
            actual = max(
                available,
                key=lambda count: (
                    min(abs(math.log(count / chosen)) for chosen in selected),
                    -count,
                ),
            )
        selected[actual] = (actual, "ADAPTIVE_RESOLUTION_FILL")

    return tuple(
        StressSelection(
            target_feasible_route_count=selected[actual][0],
            actual_feasible_route_count=actual,
            budget=count_to_budget[actual],
            selection_reason=selected[actual][1],
        )
        for actual in sorted(selected)
    )


def build_stress_task_family(
    *,
    size_stratum: str,
    target_n_edges: int,
    layer_widths: Sequence[int],
    base_index: int,
    master_seed: int,
    resource_range: tuple[int, int],
    preferred_counts: Sequence[int],
    max_levels: int = 7,
) -> tuple[tuple[Task, StressSelection], ...]:
    started = time.perf_counter()
    generation_seed = derive_seed(master_seed, size_stratum, base_index)
    graph = generate_layered_graph(
        target_n_edges=target_n_edges,
        layer_widths=layer_widths,
        seed=generation_seed,
        resource_range=resource_range,
    )
    routes = enumerate_simple_routes(graph)
    if not routes:
        raise RuntimeError("generator invariant violated: graph has no source-target route")
    build_time = time.perf_counter() - started
    selections = select_stress_levels(routes, preferred_counts, max_levels)
    base_instance_id = f"v2-{size_stratum}-b{base_index:03d}-{graph.graph_id}"
    family: list[tuple[Task, StressSelection]] = []
    for rank, selection in enumerate(selections, start=1):
        exact_started = time.perf_counter()
        feasible, optimal, optimal_cost = solve_exact_rcsp(routes, selection.budget)
        exact_time = time.perf_counter() - exact_started
        if len(feasible) != selection.actual_feasible_route_count:
            raise AssertionError("selected budget does not produce its intended feasible count")
        raw_id = (
            f"phase0-v2|{base_instance_id}|D{rank}|"
            f"{selection.actual_feasible_route_count}|{selection.budget:.12g}"
        )
        task_hash = hashlib.sha256(raw_id.encode()).hexdigest()[:12]
        task = Task(
            task_id=f"task-v2-{task_hash}",
            base_instance_id=base_instance_id,
            size_stratum=size_stratum,
            tightness_level=f"D{rank}",
            target_n_edges=target_n_edges,
            actual_n_edges=len(graph.edges),
            generation_seed=generation_seed,
            budget=selection.budget,
            quantile=math.nan,
            duplicate_budget=False,
            duplicate_feasible_set=False,
            graph=graph,
            candidate_routes=routes,
            feasible_routes=feasible,
            optimal_routes=optimal,
            optimal_cost=optimal_cost,
            task_build_time_s=build_time,
            exact_reference_time_s=exact_time,
        )
        family.append((task, selection))
    return tuple(family)
