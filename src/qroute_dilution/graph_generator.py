"""Deterministic controlled layered-DAG generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import numpy as np

from .models import DirectedGraph, Edge


def derive_seed(master_seed: int, *parts: object) -> int:
    """Derive a stable 32-bit seed without depending on Python's hash randomization."""
    payload = "|".join([str(master_seed), *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:4], "big")


def _layer_nodes(widths: Sequence[int]) -> tuple[tuple[int, ...], ...]:
    if len(widths) < 3 or widths[0] != 1 or widths[-1] != 1:
        raise ValueError("layer widths must contain singleton source/target and >=1 inner layer")
    if any(width < 1 for width in widths):
        raise ValueError("all layer widths must be positive")
    layers: list[tuple[int, ...]] = []
    next_node = 0
    for width in widths:
        layers.append(tuple(range(next_node, next_node + width)))
        next_node += width
    return tuple(layers)


def _coverage_edges(layers: tuple[tuple[int, ...], ...]) -> set[tuple[int, int]]:
    """Adjacent-layer edges ensuring every node has route-relevant in/out coverage."""
    selected: set[tuple[int, int]] = set()
    for left, right in zip(layers[:-1], layers[1:]):
        for i, node in enumerate(left):
            selected.add((node, right[i % len(right)]))
        for i, node in enumerate(right):
            selected.add((left[i % len(left)], node))
    return selected


def generate_layered_graph(
    *,
    target_n_edges: int,
    layer_widths: Sequence[int],
    seed: int,
    cost_range: tuple[int, int] = (1, 9),
    resource_range: tuple[int, int] = (1, 9),
    allow_skip_connections: bool = True,
) -> DirectedGraph:
    """Generate exactly ``target_n_edges`` forward edges with stable edge indices.

    All possible edges span one layer, plus optional two-layer skip connections.
    A deterministic coverage subset first makes all nodes participate in at least one
    source-target route; remaining edges are sampled without replacement.
    """
    if cost_range[0] <= 0 or resource_range[0] <= 0:
        raise ValueError("cost and resource ranges must be strictly positive")
    if cost_range[0] > cost_range[1] or resource_range[0] > resource_range[1]:
        raise ValueError("invalid cost or resource range")
    layers = _layer_nodes(layer_widths)
    mandatory = _coverage_edges(layers)
    candidates: set[tuple[int, int]] = set(mandatory)
    max_span = 2 if allow_skip_connections else 1
    for layer_index, left in enumerate(layers[:-1]):
        for span in range(1, max_span + 1):
            right_index = layer_index + span
            if right_index >= len(layers):
                continue
            candidates.update((u, v) for u in left for v in layers[right_index])

    if target_n_edges < len(mandatory):
        raise ValueError(
            f"target_n_edges={target_n_edges} is below connectivity minimum {len(mandatory)}"
        )
    if target_n_edges > len(candidates):
        raise ValueError(
            f"target_n_edges={target_n_edges} exceeds available forward edges {len(candidates)}"
        )

    rng = np.random.default_rng(seed)
    optional = sorted(candidates - mandatory)
    n_extra = target_n_edges - len(mandatory)
    if n_extra:
        chosen_indices = rng.choice(len(optional), size=n_extra, replace=False)
        selected = mandatory | {optional[int(i)] for i in chosen_indices}
    else:
        selected = mandatory

    ordered_pairs = sorted(selected)
    edges: list[Edge] = []
    for index, (source, target) in enumerate(ordered_pairs):
        cost = int(rng.integers(cost_range[0], cost_range[1] + 1))
        resource = int(rng.integers(resource_range[0], resource_range[1] + 1))
        edges.append(Edge(index, source, target, float(cost), float(resource)))

    identity = {
        "layers": layers,
        "edges": [(e.source, e.target, e.cost, e.resource) for e in edges],
    }
    graph_id = "g-" + hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()[:16]
    return DirectedGraph(
        n_nodes=sum(layer_widths),
        source=layers[0][0],
        target=layers[-1][0],
        layers=layers,
        edges=tuple(edges),
        graph_id=graph_id,
    )
