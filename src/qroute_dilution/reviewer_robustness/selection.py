"""Outcome-blind task selection rules frozen before reviewer experiments."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .common import derive_seed


def task_frame(
    manifest: dict[str, Any], characterization: pd.DataFrame
) -> pd.DataFrame:
    rows = []
    characterization = characterization.set_index("task_id", drop=False)
    for manifest_order, item in enumerate(manifest["tasks"]):
        task_id = str(item["task_id"])
        if task_id not in characterization.index:
            raise KeyError(f"characterization missing {task_id}")
        source = characterization.loc[task_id]
        rows.append(
            {
                **item,
                "manifest_order": manifest_order,
                "graph_id": str(item.get("graph_id", item.get("base_graph_id"))),
                "m": int(source["n_edges"]),
                "feasible_fraction_phi": float(source["feasible_state_fraction"]),
                "dilution_score": float(source["dilution_score"]),
                "size_stratum": str(item.get("size_stratum", source["size_stratum"])),
                "stress_level": str(item.get("stress_level", source["stress_level"])),
            }
        )
    frame = pd.DataFrame(rows)
    if frame.task_id.duplicated().any():
        raise ValueError("manifest contains duplicate task IDs")
    return frame


def _unique_take(frame: pd.DataFrame, indices: list[int]) -> pd.DataFrame:
    return frame.loc[list(dict.fromkeys(indices))].copy()


def select_depth_budget_tasks(
    frame: pd.DataFrame, *, count: int, seed: int
) -> pd.DataFrame:
    """Cover every graph at both dilution endpoints, then seeded graph medians."""
    selected: list[int] = []
    median_candidates: list[tuple[int, str, int]] = []
    for graph_id, group in frame.groupby("graph_id", sort=True):
        ordered = group.sort_values(
            ["dilution_score", "task_id"], kind="stable"
        )
        selected.extend([int(ordered.index[0]), int(ordered.index[-1])])
        middle = int(ordered.index[(len(ordered) - 1) // 2])
        if middle not in selected:
            median_candidates.append(
                (derive_seed("B1-extra-graph", seed, graph_id), graph_id, middle)
            )
    selected = list(dict.fromkeys(selected))
    for _, _, index in sorted(median_candidates):
        if len(selected) >= int(count):
            break
        selected.append(index)
    if len(selected) != int(count):
        raise RuntimeError(f"B1 selector produced {len(selected)}, expected {count}")
    output = _unique_take(frame, selected)
    if output.graph_id.nunique() != frame.graph_id.nunique():
        raise RuntimeError("B1 selection failed complete graph coverage")
    return output.sort_values(
        ["size_stratum", "graph_id", "dilution_score", "task_id"], kind="stable"
    )


def select_finite_shot_tasks(
    frame: pd.DataFrame, *, estimator_count: int, training_count: int, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Select held-out tasks by graph, size, and within-graph dilution rank only."""
    selected: list[int] = []
    # Each size has three held-out graphs.  A seeded ordering assigns low, middle,
    # and high dilution ranks without consulting any QAOA result.
    for size, size_group in frame.groupby("size_stratum", sort=True):
        graph_ids = sorted(
            size_group.graph_id.unique(),
            key=lambda value: (derive_seed("A3-graph-order", seed, size, value), value),
        )
        target_quantiles = np.linspace(0.0, 1.0, len(graph_ids))
        for graph_id, quantile in zip(graph_ids, target_quantiles):
            group = size_group[size_group.graph_id == graph_id].sort_values(
                ["dilution_score", "task_id"], kind="stable"
            )
            position = int(round(float(quantile) * (len(group) - 1)))
            selected.append(int(group.index[position]))
    # Add outcome-blind alternate dilution points in small/medium/large strata.
    for size in ("S1", "S3", "S5"):
        size_group = frame[frame.size_stratum == size]
        graph_id = min(
            size_group.graph_id.unique(),
            key=lambda value: (derive_seed("A3-extra", seed, size, value), value),
        )
        group = size_group[size_group.graph_id == graph_id].sort_values(
            ["dilution_score", "task_id"], kind="stable"
        )
        candidates = [int(group.index[0]), int(group.index[-1])]
        chosen = next(index for index in candidates if index not in selected)
        selected.append(chosen)
    selected = list(dict.fromkeys(selected))
    if len(selected) != int(estimator_count):
        raise RuntimeError(
            f"A3 estimator selector produced {len(selected)}, expected {estimator_count}"
        )
    estimator = _unique_take(frame, selected).sort_values(
        ["size_stratum", "dilution_score", "graph_id", "task_id"], kind="stable"
    )
    # Two dilution endpoints per size among the already frozen 18 tasks.
    training_indices: list[int] = []
    for _, group in estimator.groupby("size_stratum", sort=True):
        ordered = group.sort_values(["dilution_score", "task_id"], kind="stable")
        training_indices.extend([int(ordered.index[0]), int(ordered.index[-1])])
    training = _unique_take(estimator, training_indices).sort_values(
        ["size_stratum", "dilution_score", "graph_id", "task_id"], kind="stable"
    )
    if len(training) != int(training_count):
        raise RuntimeError(
            f"A3 training selector produced {len(training)}, expected {training_count}"
        )
    return estimator, training


def selection_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    fields = [
        "task_id",
        "graph_id",
        "base_instance_id",
        "size_stratum",
        "stress_level",
        "m",
        "feasible_fraction_phi",
        "dilution_score",
        "task_path",
        "manifest_order",
    ]
    return frame[fields].to_dict(orient="records")
