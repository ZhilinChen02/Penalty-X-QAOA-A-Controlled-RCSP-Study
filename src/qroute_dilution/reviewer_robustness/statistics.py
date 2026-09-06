"""Small graph-clustered summaries shared by all post-hoc experiments."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from qroute_dilution.phase2_statistics import exact_sign_flip_pvalue


def bootstrap_mean_ci(
    values: np.ndarray,
    *,
    resamples: int,
    seed: int,
    confidence: float = 0.95,
) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        raise ValueError("bootstrap values must be a nonempty finite vector")
    if int(resamples) <= 0 or not 0.0 < float(confidence) < 1.0:
        raise ValueError("invalid bootstrap settings")
    rng = np.random.default_rng(int(seed))
    indices = rng.integers(0, len(values), size=(int(resamples), len(values)))
    means = values[indices].mean(axis=1)
    tail = (1.0 - float(confidence)) / 2.0
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "ci_lower": float(np.quantile(means, tail)),
        "ci_upper": float(np.quantile(means, 1.0 - tail)),
        "bootstrap_se": float(means.std(ddof=1)),
    }


def paired_objective_effects(
    frame: pd.DataFrame,
    *,
    value_column: str,
    group_columns: list[str],
    task_aggregation: str = "median",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return task effects and equal-weight graph means for O3 minus O0."""
    needed = {
        "task_id",
        "graph_id",
        "objective",
        value_column,
        *group_columns,
    }
    missing = needed - set(frame.columns)
    if missing:
        raise ValueError(f"effect frame missing {sorted(missing)}")
    subset = frame[frame.objective.isin(["O0", "O3"])].copy()
    keys = [*group_columns, "task_id", "graph_id", "objective"]
    if task_aggregation == "median":
        aggregated = subset.groupby(keys, as_index=False)[value_column].median()
    elif task_aggregation == "mean":
        aggregated = subset.groupby(keys, as_index=False)[value_column].mean()
    else:
        raise ValueError("task_aggregation must be median or mean")
    pivot = aggregated.pivot(
        index=[*group_columns, "task_id", "graph_id"],
        columns="objective",
        values=value_column,
    ).reset_index()
    if not {"O0", "O3"}.issubset(pivot.columns):
        raise RuntimeError("paired O0/O3 effects are incomplete")
    pivot["delta_O3_minus_O0"] = pivot["O3"] - pivot["O0"]
    graph = (
        pivot.groupby([*group_columns, "graph_id"], as_index=False)
        .agg(
            graph_delta=("delta_O3_minus_O0", "mean"),
            n_tasks=("task_id", "nunique"),
        )
        .sort_values([*group_columns, "graph_id"], kind="stable")
    )
    return pivot, graph


def graph_effect_summary(
    graph_effects: pd.DataFrame,
    *,
    group_columns: list[str],
    resamples: int,
    seed: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped: Any
    if group_columns:
        grouped = graph_effects.groupby(group_columns, sort=True, dropna=False)
    else:
        grouped = [((), graph_effects)]
    for offset, (key, group) in enumerate(grouped):
        keys = key if isinstance(key, tuple) else (key,)
        values = group.graph_delta.to_numpy(dtype=float)
        summary = bootstrap_mean_ci(
            values, resamples=resamples, seed=int(seed) + offset
        )
        record = dict(zip(group_columns, keys))
        record.update(
            {
                "n_graphs": int(group.graph_id.nunique()),
                "n_tasks": int(group.n_tasks.sum()),
                "graph_positive_count": int((values > 0.0).sum()),
                "graph_zero_count": int((values == 0.0).sum()),
                "graph_negative_count": int((values < 0.0).sum()),
                "exact_one_sided_sign_flip_p": (
                    exact_sign_flip_pvalue(values) if len(values) <= 20 else math.nan
                ),
                **{f"graph_effect_{name}": value for name, value in summary.items()},
            }
        )
        rows.append(record)
    return pd.DataFrame(rows)
