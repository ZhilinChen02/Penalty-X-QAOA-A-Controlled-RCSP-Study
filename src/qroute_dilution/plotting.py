"""Required Phase 0 and Phase 1 diagnostic figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _finish(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_phase0(characterization: pd.DataFrame, figure_dir: Path, prefix: str) -> list[str]:
    outputs: list[str] = []
    positive = characterization[characterization["feasible_state_fraction"] > 0].copy()

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for level, group in positive.groupby("tightness_level", sort=False):
        ax.scatter(group["n_edges"], group["feasible_state_fraction"], label=level, alpha=0.75)
    ax.set_yscale("log")
    ax.set_xlabel("Number of edges / qubits")
    ax.set_ylabel("Feasible-state fraction")
    ax.set_title("Representation dilution vs edge count")
    ax.legend(ncol=2, fontsize=8)
    path = figure_dir / f"{prefix}_figure1_feasible_state_fraction_vs_n_edges.png"
    _finish(fig, path)
    outputs.append(str(path))

    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    for stratum, group in characterization.groupby("size_stratum", sort=False):
        ax.scatter(
            group["route_feasible_fraction"],
            group["feasible_state_fraction"],
            label=stratum,
            alpha=0.75,
        )
    if len(positive):
        ax.set_yscale("log")
    ax.set_xlabel("Route-feasible fraction (candidate-path pool)")
    ax.set_ylabel("Feasible-state fraction (edge-bit state space)")
    ax.set_title("Route feasibility is not state-space feasibility")
    ax.legend(fontsize=8)
    path = figure_dir / f"{prefix}_figure2_route_vs_state_feasible_fraction.png"
    _finish(fig, path)
    outputs.append(str(path))

    heat = characterization.copy()
    heat["dilution_log10"] = np.where(
        heat["feasible_state_fraction"] > 0,
        -np.log10(heat["feasible_state_fraction"]),
        np.nan,
    )
    size_order = list(dict.fromkeys(heat["size_stratum"].tolist()))
    tight_order = list(dict.fromkeys(heat["tightness_level"].tolist()))
    matrix = (
        heat.groupby(["size_stratum", "tightness_level"], sort=False)["dilution_log10"]
        .mean()
        .unstack()
        .reindex(index=size_order, columns=tight_order)
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    image = ax.imshow(matrix.to_numpy(), aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns)
    ax.set_yticks(range(len(matrix.index)), matrix.index)
    ax.set_xlabel("Tightness (loose → tight)")
    ax.set_ylabel("Size stratum")
    ax.set_title(r"Mean $-\log_{10}(\phi_{state})$")
    fig.colorbar(image, ax=ax, label=r"$-\log_{10}(\phi_{state})$")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix.iloc[i, j]
            if np.isfinite(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center", color="white", fontsize=8)
    path = figure_dir / f"{prefix}_figure3_dilution_heatmap.png"
    _finish(fig, path)
    outputs.append(str(path))
    return outputs


def plot_phase1(results: pd.DataFrame, figure_dir: Path, prefix: str) -> list[str]:
    outputs: list[str] = []
    frame = results.copy()
    frame = frame[frame["feasible_state_fraction"] > 0].copy()
    frame["dilution_log10"] = -np.log10(frame["feasible_state_fraction"])

    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    uniform = frame[frame["algorithm"] == "Uniform"]
    ax.scatter(uniform["dilution_log10"], uniform["p_feas"], label="Uniform", marker="x")
    penalty = frame[frame["algorithm"] == "Penalty-X"]
    for depth, group in penalty.groupby("depth", sort=True):
        ax.scatter(group["dilution_log10"], group["p_feas"], label=f"Penalty-X p={int(depth)}", alpha=0.75)
    ax.set_yscale("log")
    ax.set_xlabel(r"$-\log_{10}(\phi_{state})$")
    ax.set_ylabel(r"$P_{feas}$")
    ax.set_title("Absolute feasible recovery")
    ax.legend(fontsize=8)
    path = figure_dir / f"{prefix}_figure4_p_feas_vs_dilution.png"
    _finish(fig, path)
    outputs.append(str(path))

    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    amplified = frame[frame["feasibility_amplification"] > 0]
    for (algorithm, depth), group in amplified.groupby(["algorithm", "depth"], sort=True):
        label = "Uniform" if algorithm == "Uniform" else f"Penalty-X p={int(depth)}"
        ax.scatter(
            group["dilution_log10"],
            group["feasibility_amplification"],
            label=label,
            alpha=0.75,
        )
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set_yscale("log")
    ax.set_xlabel(r"$-\log_{10}(\phi_{state})$")
    ax.set_ylabel(r"$A_{feas}=P_{feas}/\phi_{state}$")
    ax.set_title("Feasibility amplification")
    ax.legend(fontsize=8)
    path = figure_dir / f"{prefix}_figure5_amplification_vs_dilution.png"
    _finish(fig, path)
    outputs.append(str(path))

    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    for (algorithm, depth), group in frame.groupby(["algorithm", "depth"], sort=True):
        label = "Uniform" if algorithm == "Uniform" else f"Penalty-X p={int(depth)}"
        ax.scatter(group["feasible_state_fraction"], group["p_opt"], label=label, alpha=0.75)
    ax.set_xscale("log")
    positive_opt = frame[frame["p_opt"] > 0]
    if len(positive_opt):
        ax.set_yscale("log")
    ax.set_xlabel("Feasible-state fraction")
    ax.set_ylabel(r"$P_{opt}$")
    ax.set_title("Optimal recovery vs feasible-state density")
    ax.legend(fontsize=8)
    path = figure_dir / f"{prefix}_figure6_p_opt_vs_feasible_state_fraction.png"
    _finish(fig, path)
    outputs.append(str(path))
    return outputs
