"""Frozen Penalty-X diagonal energy construction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import DirectedGraph


@dataclass(frozen=True)
class EnergyComponents:
    total: np.ndarray
    objective_cost: np.ndarray
    flow_penalty: np.ndarray
    resource_penalty: np.ndarray


@dataclass(frozen=True)
class RawStateComponents:
    routing_cost: np.ndarray
    flow_penalty_raw: np.ndarray
    resource_total: np.ndarray


def build_raw_state_components(
    graph: DirectedGraph, *, chunk_size: int = 100_000
) -> RawStateComponents:
    """Evaluate task-independent cost, flow residual, and resource total over 2^m."""
    m = len(graph.edges)
    n_states = 1 << m
    routing_cost = np.empty(n_states, dtype=np.float64)
    flow_penalty = np.empty(n_states, dtype=np.float64)
    resource_total = np.empty(n_states, dtype=np.float64)
    edge_costs = np.asarray([edge.cost for edge in graph.edges], dtype=np.float64)
    edge_resources = np.asarray([edge.resource for edge in graph.edges], dtype=np.float64)
    incidence = np.zeros((m, graph.n_nodes), dtype=np.float64)
    for edge in graph.edges:
        incidence[edge.index, edge.source] = 1.0
        incidence[edge.index, edge.target] = -1.0
    demand = np.zeros(graph.n_nodes, dtype=np.float64)
    demand[graph.source] = 1.0
    demand[graph.target] = -1.0
    shifts = np.arange(m, dtype=np.uint64)
    for start in range(0, n_states, chunk_size):
        stop = min(start + chunk_size, n_states)
        states = np.arange(start, stop, dtype=np.uint64)
        bits = ((states[:, None] >> shifts[None, :]) & 1).astype(np.float64)
        routing_cost[start:stop] = bits @ edge_costs
        residual = bits @ incidence - demand
        flow_penalty[start:stop] = np.einsum("ij,ij->i", residual, residual)
        resource_total[start:stop] = bits @ edge_resources
    return RawStateComponents(routing_cost, flow_penalty, resource_total)


def scale_controlled_penalties(
    flow_penalty_raw: np.ndarray,
    resource_excess: np.ndarray,
    *,
    flow_scale: float,
    resource_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Dimensionless hard-plus-bounded-severity constraint penalties.

    Each component is zero exactly when its original raw violation is zero, and is
    in (1, 2] for every violation. Scales are deterministic base-graph quantities.
    """
    if flow_scale <= 0.0 or resource_scale <= 0.0:
        raise ValueError("scale-controlled penalty scales must be positive")
    flow_raw = np.asarray(flow_penalty_raw, dtype=np.float64)
    excess = np.asarray(resource_excess, dtype=np.float64)
    controlled_flow = (flow_raw > 0.0).astype(np.float64) + np.minimum(
        flow_raw / flow_scale, 1.0
    )
    controlled_resource = (excess > 0.0).astype(np.float64) + np.minimum(
        (excess / resource_scale) ** 2, 1.0
    )
    return controlled_flow, controlled_resource


def build_diagonal_energies(
    graph: DirectedGraph,
    budget: float,
    flow_penalty_strength: float,
    resource_penalty_strength: float,
    *,
    chunk_size: int = 100_000,
) -> EnergyComponents:
    """Evaluate cost + squared flow + squared resource hinge for every state.

    The resource hinge is a diagonal evaluator. It is not presented as an exact
    quadratic unconstrained binary optimization (QUBO) transformation.
    """
    m = len(graph.edges)
    n_states = 1 << m
    objective = np.empty(n_states, dtype=np.float64)
    flow = np.empty(n_states, dtype=np.float64)
    resource = np.empty(n_states, dtype=np.float64)
    edge_costs = np.asarray([edge.cost for edge in graph.edges], dtype=np.float64)
    edge_resources = np.asarray([edge.resource for edge in graph.edges], dtype=np.float64)
    incidence = np.zeros((m, graph.n_nodes), dtype=np.float64)
    for edge in graph.edges:
        incidence[edge.index, edge.source] = 1.0
        incidence[edge.index, edge.target] = -1.0
    demand = np.zeros(graph.n_nodes, dtype=np.float64)
    demand[graph.source] = 1.0
    demand[graph.target] = -1.0
    shifts = np.arange(m, dtype=np.uint64)

    for start in range(0, n_states, chunk_size):
        stop = min(start + chunk_size, n_states)
        states = np.arange(start, stop, dtype=np.uint64)
        bits = ((states[:, None] >> shifts[None, :]) & 1).astype(np.float64)
        objective[start:stop] = bits @ edge_costs
        residual = bits @ incidence - demand
        flow[start:stop] = np.einsum("ij,ij->i", residual, residual)
        consumption = bits @ edge_resources
        violation = np.maximum(0.0, consumption - budget)
        resource[start:stop] = violation * violation

    total = (
        objective
        + float(flow_penalty_strength) * flow
        + float(resource_penalty_strength) * resource
    )
    return EnergyComponents(total, objective, flow, resource)
