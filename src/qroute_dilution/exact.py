"""Exhaustive edge-bit characterization and exact task summaries."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .models import DirectedGraph, Task
from .representation import validate_edge_selection


@dataclass(frozen=True)
class StructuralState:
    state: int
    cost: float
    resource: float


def enumerate_structural_path_states(graph: DirectedGraph) -> tuple[StructuralState, ...]:
    """Exhaustively inspect all 2^m states and retain exact directed path states."""
    valid: list[StructuralState] = []
    for state in range(1 << len(graph.edges)):
        result = validate_edge_selection(graph, state, budget=float("inf"))
        if result.valid_structure:
            valid.append(StructuralState(state, result.cost, result.resource))
    return tuple(valid)


def characterize_task(
    task: Task,
    structural_states: Iterable[StructuralState],
    enumeration_time_s: float,
) -> dict[str, object]:
    structural_states = tuple(structural_states)
    feasible = tuple(s for s in structural_states if s.resource <= task.budget + 1e-12)
    optimal_states = ()
    if task.optimal_cost is not None:
        optimal_states = tuple(s for s in feasible if abs(s.cost - task.optimal_cost) <= 1e-12)
    n_candidate = len(task.candidate_routes)
    n_feasible_routes = len(task.feasible_routes)
    state_space_size = 1 << task.actual_n_edges
    n_feasible_states = len(feasible)
    return {
        "task_id": task.task_id,
        "graph_id": task.graph.graph_id,
        "base_instance_id": task.base_instance_id,
        "size_stratum": task.size_stratum,
        "tightness_level": task.tightness_level,
        "target_n_edges": task.target_n_edges,
        "actual_n_edges": task.actual_n_edges,
        "n_nodes": task.graph.n_nodes,
        "n_edges": task.actual_n_edges,
        "n_qubits": task.actual_n_edges,
        "resource_count": 1,
        "budget": task.budget,
        "budget_quantile": task.quantile,
        "duplicate_budget": task.duplicate_budget,
        "duplicate_feasible_set": task.duplicate_feasible_set,
        "n_candidate_routes": n_candidate,
        "n_feasible_routes": n_feasible_routes,
        "route_feasible_fraction": n_feasible_routes / n_candidate if n_candidate else np.nan,
        "state_space_size": state_space_size,
        "n_feasible_states": n_feasible_states,
        "feasible_state_fraction": n_feasible_states / state_space_size,
        "n_optimal_states": len(optimal_states),
        "optimal_cost": task.optimal_cost,
        "zero_feasible": n_feasible_states == 0,
        "task_build_time_s": task.task_build_time_s,
        "exact_reference_time_s": task.exact_reference_time_s + enumeration_time_s,
        "representation_enumeration_time_s": enumeration_time_s,
        "structural_path_state_count": len(structural_states),
    }


def characterize_family(tasks: Iterable[Task]) -> list[dict[str, object]]:
    tasks = tuple(tasks)
    if not tasks:
        return []
    graph = tasks[0].graph
    if any(task.graph.graph_id != graph.graph_id for task in tasks):
        raise ValueError("characterize_family requires one shared base graph")
    started = time.perf_counter()
    structural = enumerate_structural_path_states(graph)
    elapsed = time.perf_counter() - started
    return [characterize_task(task, structural, elapsed) for task in tasks]
