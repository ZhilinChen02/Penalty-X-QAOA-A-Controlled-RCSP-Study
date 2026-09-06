"""Phase 0.5 audit and v2 coverage figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _finish(fig: plt.Figure, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return str(path)


def plot_stress_audit(
    v1: pd.DataFrame,
    v2: pd.DataFrame,
    v1_graph_audit: pd.DataFrame,
    output_dir: Path,
) -> list[str]:
    outputs: list[str] = []
    v2_graph = (
        v2.groupby(["size_stratum", "base_index"], sort=False)
        .agg(v2_levels=("task_id", "size"))
        .reset_index()
    )
    comparison = v1_graph_audit.merge(v2_graph, on=["size_stratum", "base_index"])
    labels = [f"{row.size_stratum}-b{int(row.base_index):03d}" for row in comparison.itertuples()]
    positions = np.arange(len(comparison))
    fig, ax = plt.subplots(figsize=(11.5, 4.5))
    ax.bar(positions - 0.2, comparison["effective_levels"], width=0.4, label="Phase 0 v1")
    ax.bar(positions + 0.2, comparison["v2_levels"], width=0.4, label="Stress v2")
    ax.axhline(7, color="black", linestyle="--", linewidth=1)
    ax.set_xticks(positions, labels, rotation=65, ha="right", fontsize=7)
    ax.set_ylabel("Distinct feasible sets / levels")
    ax.set_title("Effective distinct tightness levels per base graph")
    ax.legend()
    outputs.append(_finish(fig, output_dir / "figure_A_effective_distinct_levels.png"))

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    bins = np.logspace(
        np.log10(min(v1.feasible_state_fraction.min(), v2.feasible_state_fraction.min())),
        np.log10(max(v1.feasible_state_fraction.max(), v2.feasible_state_fraction.max())),
        18,
    )
    axes[0].hist(v1.feasible_state_fraction, bins=bins, alpha=0.55, label="v1")
    axes[0].hist(v2.feasible_state_fraction, bins=bins, alpha=0.55, label="v2")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Feasible-state fraction")
    axes[0].set_ylabel("Task count")
    axes[0].set_title("Histogram")
    axes[0].legend()
    for frame, label in ((v1, "v1"), (v2, "v2")):
        values = np.sort(frame.feasible_state_fraction.to_numpy())
        axes[1].step(values, np.arange(1, len(values) + 1) / len(values), where="post", label=label)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Feasible-state fraction")
    axes[1].set_ylabel("ECDF")
    axes[1].set_title("Empirical coverage")
    axes[1].legend()
    outputs.append(_finish(fig, output_dir / "figure_B_phi_histogram_ecdf.png"))

    size_order = list(dict.fromkeys(v2.size_stratum.tolist()))
    stress_order = sorted(v2.stress_level.unique(), key=lambda value: int(value[1:]))
    heat = (
        v2.groupby(["size_stratum", "stress_level"], sort=False)["dilution_score"]
        .mean()
        .unstack()
        .reindex(index=size_order, columns=stress_order)
    )
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    image = ax.imshow(heat.to_numpy(), aspect="auto", cmap="magma")
    ax.set_xticks(range(len(heat.columns)), heat.columns)
    ax.set_yticks(range(len(heat.index)), heat.index)
    ax.set_xlabel("Stress level (tight → loose)")
    ax.set_ylabel("Size stratum")
    ax.set_title(r"Prospective v2 mean $-\log_{10}(\phi_{state})$")
    fig.colorbar(image, ax=ax, label="Dilution score")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            value = heat.iloc[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", color="white", fontsize=8)
    outputs.append(_finish(fig, output_dir / "figure_C_v2_dilution_heatmap.png"))

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    strata = size_order
    rng = np.random.default_rng(0)
    for i, stratum in enumerate(strata):
        values1 = v1.loc[v1.size_stratum == stratum, "feasible_state_fraction"].to_numpy()
        values2 = v2.loc[v2.size_stratum == stratum, "feasible_state_fraction"].to_numpy()
        ax.scatter(
            i - 0.16 + rng.uniform(-0.05, 0.05, len(values1)),
            values1,
            alpha=0.45,
            s=20,
            color="#1f77b4",
            label="Phase 0 v1" if i == 0 else None,
        )
        ax.scatter(
            i + 0.16 + rng.uniform(-0.05, 0.05, len(values2)),
            values2,
            alpha=0.55,
            s=20,
            color="#ff7f0e",
            label="Stress v2" if i == 0 else None,
        )
    ax.set_yscale("log")
    ax.set_xticks(range(len(strata)), strata)
    ax.set_ylabel("Feasible-state fraction")
    ax.set_xlabel("Size stratum")
    ax.set_title("Phase 0 v1 vs prospective stress v2 coverage")
    ax.legend()
    outputs.append(_finish(fig, output_dir / "figure_D_v1_vs_v2_coverage.png"))
    return outputs
