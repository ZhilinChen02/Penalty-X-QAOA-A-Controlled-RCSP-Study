"""Small immutable data models used across task generation and simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, order=True)
class Edge:
    index: int
    source: int
    target: int
    cost: float
    resource: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(**data)


@dataclass(frozen=True)
class Route:
    nodes: tuple[int, ...]
    edge_indices: tuple[int, ...]
    cost: float
    resource: float

    @property
    def bitstring_int(self) -> int:
        value = 0
        for edge_index in self.edge_indices:
            value |= 1 << edge_index
        return value

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["nodes"] = list(self.nodes)
        data["edge_indices"] = list(self.edge_indices)
        data["bitstring_int"] = self.bitstring_int
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Route":
        cleaned = dict(data)
        cleaned.pop("bitstring_int", None)
        cleaned["nodes"] = tuple(cleaned["nodes"])
        cleaned["edge_indices"] = tuple(cleaned["edge_indices"])
        return cls(**cleaned)


@dataclass(frozen=True)
class DirectedGraph:
    n_nodes: int
    source: int
    target: int
    layers: tuple[tuple[int, ...], ...]
    edges: tuple[Edge, ...]
    graph_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_nodes": self.n_nodes,
            "source": self.source,
            "target": self.target,
            "layers": [list(layer) for layer in self.layers],
            "edges": [edge.to_dict() for edge in self.edges],
            "graph_id": self.graph_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DirectedGraph":
        return cls(
            n_nodes=int(data["n_nodes"]),
            source=int(data["source"]),
            target=int(data["target"]),
            layers=tuple(tuple(layer) for layer in data["layers"]),
            edges=tuple(Edge.from_dict(edge) for edge in data["edges"]),
            graph_id=str(data["graph_id"]),
        )


@dataclass
class Task:
    task_id: str
    base_instance_id: str
    size_stratum: str
    tightness_level: str
    target_n_edges: int
    actual_n_edges: int
    generation_seed: int
    budget: float
    quantile: float
    duplicate_budget: bool
    duplicate_feasible_set: bool
    graph: DirectedGraph
    candidate_routes: tuple[Route, ...]
    feasible_routes: tuple[Route, ...]
    optimal_routes: tuple[Route, ...]
    optimal_cost: float | None
    task_build_time_s: float = 0.0
    exact_reference_time_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "base_instance_id": self.base_instance_id,
            "size_stratum": self.size_stratum,
            "tightness_level": self.tightness_level,
            "target_n_edges": self.target_n_edges,
            "actual_n_edges": self.actual_n_edges,
            "generation_seed": self.generation_seed,
            "budget": self.budget,
            "quantile": self.quantile,
            "duplicate_budget": self.duplicate_budget,
            "duplicate_feasible_set": self.duplicate_feasible_set,
            "graph": self.graph.to_dict(),
            "candidate_routes": [route.to_dict() for route in self.candidate_routes],
            "feasible_routes": [route.to_dict() for route in self.feasible_routes],
            "optimal_routes": [route.to_dict() for route in self.optimal_routes],
            "optimal_cost": self.optimal_cost,
            "task_build_time_s": self.task_build_time_s,
            "exact_reference_time_s": self.exact_reference_time_s,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            task_id=data["task_id"],
            base_instance_id=data["base_instance_id"],
            size_stratum=data["size_stratum"],
            tightness_level=data["tightness_level"],
            target_n_edges=int(data["target_n_edges"]),
            actual_n_edges=int(data["actual_n_edges"]),
            generation_seed=int(data["generation_seed"]),
            budget=float(data["budget"]),
            quantile=float(data["quantile"]),
            duplicate_budget=bool(data["duplicate_budget"]),
            duplicate_feasible_set=bool(data["duplicate_feasible_set"]),
            graph=DirectedGraph.from_dict(data["graph"]),
            candidate_routes=tuple(Route.from_dict(r) for r in data["candidate_routes"]),
            feasible_routes=tuple(Route.from_dict(r) for r in data["feasible_routes"]),
            optimal_routes=tuple(Route.from_dict(r) for r in data["optimal_routes"]),
            optimal_cost=data["optimal_cost"],
            task_build_time_s=float(data.get("task_build_time_s", 0.0)),
            exact_reference_time_s=float(data.get("exact_reference_time_s", 0.0)),
        )
