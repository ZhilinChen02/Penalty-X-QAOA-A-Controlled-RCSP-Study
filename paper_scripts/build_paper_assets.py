#!/usr/bin/env python3
"""Build manuscript figures, tables, and compact supplements from frozen evidence.

This script performs presentation-only aggregation of canonical Phase 0--3 and
Theory-v3 rows.  It does not execute QAOA, refit confirmatory models, alter any
source file, or use unfinished Phase 3B material.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from textwrap import shorten

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OVERLEAF = ROOT / "overleaf"
FIG_DIR = OVERLEAF / "figures"
TABLE_DIR = OVERLEAF / "tables"
SUPP_DIR = OVERLEAF / "supplementary"
AUDIT_DIR = ROOT / "paper_audit"

BLUE = "#3264A8"
ORANGE = "#E17C22"
GREEN = "#4C9F70"
RED = "#C94C4C"
PURPLE = "#7A5AA6"
TEAL = "#2A8C91"
GRAY = "#66717E"
LIGHT = "#EEF2F6"
DARK = "#202A35"
OBJECTIVE_COLORS = {"O0": BLUE, "O1": ORANGE, "O2": GREEN, "O3": RED}
OBJECTIVE_LABELS = {
    "O0": "O0 mean energy",
    "O1": "O1 expected penalty",
    "O2": "O2 feasibility control",
    "O3": "O3 CVaR-0.10",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.edgecolor": "#66717E",
            "axes.linewidth": 0.7,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.6,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 160,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.04,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def load_csv(relative: str) -> pd.DataFrame:
    return pd.read_csv(ROOT / relative)


def load_json(relative: str) -> dict:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def save(fig: plt.Figure, filename: str) -> None:
    fig.savefig(FIG_DIR / filename, format="pdf")
    plt.close(fig)


def panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.12,
        1.05,
        label.lower(),
        transform=ax.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
    )


def jitter(values: np.ndarray, width: float = 0.08) -> np.ndarray:
    # Deterministic display jitter; no scientific values are changed.
    if len(values) == 0:
        return values
    ranks = np.arange(len(values))
    offsets = ((ranks * 0.61803398875) % 1.0 - 0.5) * 2.0 * width
    return values + offsets


def box(ax: plt.Axes, xy: tuple[float, float], wh: tuple[float, float], text: str,
        color: str, fontsize: float = 9) -> None:
    patch = FancyBboxPatch(
        xy,
        wh[0],
        wh[1],
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=color,
        edgecolor=DARK,
        linewidth=0.8,
    )
    ax.add_patch(patch)
    ax.text(xy[0] + wh[0] / 2, xy[1] + wh[1] / 2, text,
            ha="center", va="center", color="white", fontsize=fontsize,
            fontweight="bold", wrap=True)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float],
          color: str = GRAY) -> None:
    ax.add_patch(
        FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                        linewidth=1.1, color=color)
    )


def figure_01() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.65))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.01, 1.07)
    ax.axis("off")

    box(ax, (0.28, 0.90), (0.44, 0.085),
        "Controlled RCSP\nfeasible-space dilution", ORANGE, fontsize=8.7)
    box(ax, (0.28, 0.77), (0.44, 0.085),
        "Apparent shallow Penalty-X\ndegradation", RED, fontsize=8.7)
    arrow(ax, (0.50, 0.90), (0.50, 0.86))

    box(ax, (0.055, 0.64), (0.35, 0.075), "Optimizer inadequacy", PURPLE)
    box(ax, (0.595, 0.64), (0.35, 0.075), "Objective mismatch", TEAL)
    arrow(ax, (0.46, 0.77), (0.23, 0.72))
    arrow(ax, (0.54, 0.77), (0.77, 0.72))

    box(ax, (0.055, 0.49), (0.35, 0.085),
        "$p=2\\to p=3$ zero-layer\nnesting diagnostic", BLUE, fontsize=8.5)
    box(ax, (0.055, 0.33), (0.35, 0.085),
        "Continuation repair", BLUE, fontsize=8.5)
    arrow(ax, (0.23, 0.64), (0.23, 0.58))
    arrow(ax, (0.23, 0.49), (0.23, 0.42))
    ax.text(0.23, 0.455, "certified failures", ha="center", va="center",
            color=GRAY, fontsize=7.5)

    box(ax, (0.595, 0.515), (0.35, 0.065),
        "Mean energy $\\neq P_{\\mathrm{feas}}$", TEAL, fontsize=8.5)
    box(ax, (0.595, 0.395), (0.35, 0.065),
        "O2 feasible-capacity control", GREEN, fontsize=8.5)
    box(ax, (0.595, 0.275), (0.35, 0.065),
        "CVaR-0.10 selected in discovery", RED, fontsize=8.5)
    arrow(ax, (0.77, 0.64), (0.77, 0.585))
    arrow(ax, (0.77, 0.515), (0.77, 0.465))
    arrow(ax, (0.77, 0.395), (0.77, 0.345))

    box(ax, (0.26, 0.135), (0.48, 0.085),
        "Preregistered held-out graphs\nimproved feasible entry in tested family",
        GREEN, fontsize=8.1)
    arrow(ax, (0.23, 0.33), (0.42, 0.225))
    arrow(ax, (0.77, 0.275), (0.58, 0.225))

    box(ax, (0.13, 0.005), (0.74, 0.075),
        "$m=20$ ordering reversal  |  $m=22$ resource censoring\n"
        "No global scaling conclusion", GRAY, fontsize=8.2)
    arrow(ax, (0.50, 0.135), (0.50, 0.085))

    ax.text(0.5, 1.055, "Controlled attribution pipeline", ha="center", va="top",
            fontsize=11, fontweight="bold", color=DARK)
    save(fig, "fig01_experimental_concept.pdf")


def figure_02() -> None:
    tasks = load_csv("results/phase0_v2_dilution_stress/task_characterization.csv")
    scales = load_csv("results/phase0_v2_dilution_stress/penalty_contract_comparison.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.15))

    ax = axes[0]
    for size, group in tasks.groupby("n_edges"):
        ax.scatter(
            np.full(len(group), size) + jitter(np.zeros(len(group)), 0.10),
            group.feasible_state_fraction,
            s=16,
            alpha=0.72,
            label=fr"$m={int(size)}$",
        )
    ax.set_yscale("log")
    ax.set_xticks(sorted(tasks.n_edges.unique()))
    ax.set_xlabel("edge-bit variables $m$")
    ax.set_ylabel(r"feasible-state fraction $\phi_{\mathrm{state}}$")
    ax.set_title("Distinct-cardinality task universe")
    ax.legend(ncol=2, frameon=False, loc="lower left")
    ax.annotate(
        "140 tasks; no duplicate feasible sets",
        xy=(0.03, 0.96),
        xycoords="axes fraction",
        va="top",
        color=DARK,
    )
    panel_label(ax, "A")

    ax = axes[1]
    raw = scales.current_energy_span.to_numpy()
    controlled = scales.controlled_energy_span.to_numpy()
    data = [raw, controlled]
    bp = ax.boxplot(data, positions=[0, 1], widths=0.48, patch_artist=True,
                    showfliers=False, medianprops={"color": DARK, "linewidth": 1.5})
    for patch, color in zip(bp["boxes"], [ORANGE, BLUE]):
        patch.set_facecolor(color)
        patch.set_alpha(0.35)
        patch.set_edgecolor(color)
    ax.scatter(jitter(np.zeros(len(raw)), 0.16), raw, s=8, alpha=0.25, color=ORANGE)
    ax.scatter(jitter(np.ones(len(controlled)), 0.16), controlled, s=8, alpha=0.25, color=BLUE)
    ax.set_yscale("log")
    ax.set_xticks([0, 1], ["raw", "scale-controlled"])
    ax.set_ylabel("absolute Hamiltonian energy span")
    ax.set_title("Hamiltonian-scale audit")
    ax.annotate("ground-state correct: 140/140 in both", xy=(0.03, 0.96),
                xycoords="axes fraction", va="top", color=DARK)
    panel_label(ax, "B")
    fig.tight_layout(w_pad=2.0)
    save(fig, "fig02_dilution_scale_control.pdf")


def figure_03() -> None:
    gap = load_csv("results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv")
    cont = load_csv(
        "results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv"
    )
    merged = cont.merge(
        gap[["task_id", "optimizer_seed", "original_p3_worse_than_embedded_p2"]],
        on=["task_id", "optimizer_seed"],
        how="left",
        validate="one_to_one",
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.15))

    ax = axes[0]
    ordered = gap.sort_values("p3_optimization_gap_vs_embedded_p2").reset_index(drop=True)
    colors = np.where(ordered.original_p3_worse_than_embedded_p2, RED, BLUE)
    ax.scatter(np.arange(len(ordered)), ordered.p3_optimization_gap_vs_embedded_p2,
               c=colors, s=13, alpha=0.82)
    ax.axhline(0, color=DARK, linewidth=0.9)
    ax.set_xlabel("sorted seed-level comparison")
    ax.set_ylabel(r"$E_{p=3}^{\rm original}-E_{p=2}^{\rm embedded}$")
    ax.set_title("Nested-ansatz optimizer diagnostic")
    ax.text(0.03, 0.96, "29/168 above zero", transform=ax.transAxes,
            va="top", color=RED, fontweight="bold")
    panel_label(ax, "A")

    ax = axes[1]
    ok = ~merged.original_p3_worse_than_embedded_p2.astype(bool)
    ax.scatter(merged.loc[ok, "original_p3_G_feas"], merged.loc[ok, "G_feas_final"],
               s=16, color=BLUE, alpha=0.46, label="other pairs")
    ax.scatter(merged.loc[~ok, "original_p3_G_feas"], merged.loc[~ok, "G_feas_final"],
               s=23, color=RED, alpha=0.78, label="original failure set")
    limits = [min(merged.original_p3_G_feas.min(), merged.G_feas_final.min()),
              max(merged.original_p3_G_feas.max(), merged.G_feas_final.max())]
    ax.plot(limits, limits, color=DARK, linestyle="--", linewidth=0.9)
    ax.set_xlim(limits)
    ax.set_ylim(limits)
    ax.set_xlabel(r"original $p=3$ $G_{\mathrm{feas}}$")
    ax.set_ylabel(r"continuation $p=3$ $G_{\mathrm{feas}}$")
    ax.set_title("Continuation from embedded $p=2$")
    ax.legend(frameon=False, loc="lower right")
    ax.text(0.03, 0.96, "27/29 failure-set pairs gain feasibility",
            transform=ax.transAxes, va="top", color=DARK)
    panel_label(ax, "B")
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig03_optimizer_attribution.pdf")


def figure_04() -> None:
    cont = load_csv(
        "results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv"
    )
    decomp = load_csv("results/phase1_1_optimization_diagnostic/objective_decomposition.csv")
    random = decomp[decomp.arm.eq("P3_RANDOM_ORIGINAL")]
    continuation = decomp[decomp.arm.eq("P3_CONTINUATION_B1")]
    pair = random.merge(
        continuation,
        on=["task_id", "source_p2_seed"],
        suffixes=("_random", "_continuation"),
        validate="one_to_one",
    )
    delta_e = cont.original_p3_objective - cont.objective_final
    delta_g = cont.original_p3_G_feas - cont.G_feas_final
    paradox = (delta_e < 0) & (delta_g < 0)

    fig = plt.figure(figsize=(7.25, 3.25))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.45, 0.9, 0.9], wspace=0.42)
    ax = fig.add_subplot(gs[0, 0])
    ax.scatter(delta_e[~paradox], delta_g[~paradox], s=15, color=BLUE, alpha=0.45,
               label="other")
    ax.scatter(delta_e[paradox], delta_g[paradox], s=20, color=RED, alpha=0.72,
               label="lower energy, lower gain")
    ax.axhline(0, color=DARK, linewidth=0.8)
    ax.axvline(0, color=DARK, linewidth=0.8)
    ax.set_xlabel(r"original minus continuation $\Delta E$")
    ax.set_ylabel(r"original minus continuation $\Delta G_{\mathrm{feas}}$")
    ax.set_title("Paired endpoint contrasts")
    ax.legend(frameon=False, loc="lower right")
    ax.text(0.03, 0.96, "82/168 pairs", transform=ax.transAxes,
            va="top", color=RED, fontweight="bold")
    panel_label(ax, "A")

    ax = fig.add_subplot(gs[0, 1])
    energy_cols = [
        ("expected_routing_component", "routing"),
        ("expected_flow_penalty", "flow"),
        ("expected_resource_penalty", "resource"),
    ]
    medians = [
        np.median(pair[f"{col}_random"] - pair[f"{col}_continuation"])
        for col, _ in energy_cols
    ]
    ax.bar(np.arange(3), medians, color=[PURPLE, ORANGE, GREEN], alpha=0.8)
    ax.axhline(0, color=DARK, linewidth=0.8)
    ax.set_xticks(np.arange(3), [label for _, label in energy_cols], rotation=32, ha="right")
    ax.set_ylabel("median random minus continuation")
    ax.set_title("Energy terms")
    panel_label(ax, "B")

    ax = fig.add_subplot(gs[0, 2])
    mass_cols = [
        ("mass_valid_flow_resource_feasible", "feasible"),
        ("mass_flow_invalid", "flow invalid"),
        ("mass_resource_violating", "resource invalid"),
    ]
    medians = [
        np.median(pair[f"{col}_random"] - pair[f"{col}_continuation"])
        for col, _ in mass_cols
    ]
    ax.bar(np.arange(3), medians, color=[BLUE, ORANGE, RED], alpha=0.8)
    ax.axhline(0, color=DARK, linewidth=0.8)
    ax.set_xticks(np.arange(3), [label for _, label in mass_cols], rotation=32, ha="right")
    ax.set_ylabel("median probability-mass difference")
    ax.set_title("State classes")
    panel_label(ax, "C")
    save(fig, "fig04_objective_misalignment.pdf")


def figure_05() -> None:
    task = load_csv("results/phase1_2_objective_alignment/task_objective_summary.csv")
    gaps = load_csv("results/phase1_2_objective_alignment/capacity_gap.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.2))
    objectives = ["O0", "O1", "O2", "O3"]

    ax = axes[0]
    arrays = [task[f"log_feasibility_gain_{o}"].to_numpy() for o in objectives]
    bp = ax.boxplot(arrays, positions=np.arange(4), widths=0.55, patch_artist=True,
                    showfliers=False, medianprops={"color": DARK, "linewidth": 1.4})
    for idx, (patch, objective) in enumerate(zip(bp["boxes"], objectives)):
        patch.set_facecolor(OBJECTIVE_COLORS[objective])
        patch.set_alpha(0.25)
        patch.set_edgecolor(OBJECTIVE_COLORS[objective])
        ax.scatter(jitter(np.full(len(arrays[idx]), idx), 0.16), arrays[idx], s=8,
                   alpha=0.28, color=OBJECTIVE_COLORS[objective])
    ax.set_xticks(np.arange(4), objectives)
    ax.set_ylabel(r"$G_{\mathrm{feas}}=\log_{10}(P_{\mathrm{feas}}/\phi_{\mathrm{state}})$")
    ax.set_title("Discovery: attainable feasibility gain")
    ax.text(0.03, 0.96, "$n=56$ discovery tasks", transform=ax.transAxes,
            va="top", color=DARK)
    panel_label(ax, "A")

    ax = axes[1]
    delta_arrays = [
        task.log_feasibility_gain_O1 - task.log_feasibility_gain_O0,
        task.log_feasibility_gain_O2 - task.log_feasibility_gain_O0,
        task.log_feasibility_gain_O3 - task.log_feasibility_gain_O0,
    ]
    for idx, (arr, objective) in enumerate(zip(delta_arrays, ["O1", "O2", "O3"])):
        ax.scatter(jitter(np.full(len(arr), idx), 0.16), arr, s=10,
                   alpha=0.36, color=OBJECTIVE_COLORS[objective])
        ax.hlines(np.median(arr), idx - 0.24, idx + 0.24,
                  color=OBJECTIVE_COLORS[objective], linewidth=2.2)
    ax.axhline(0, color=DARK, linewidth=0.8)
    ax.set_xticks([0, 1, 2], ["O1$-$O0", "O2$-$O0", "O3$-$O0"])
    ax.set_ylabel(r"paired $\Delta G_{\mathrm{feas}}$ (decades)")
    ax.set_title("Paired objective contrasts")
    closure_o1 = 100 * gaps.penalty_gap_closure_fraction.median()
    closure_o3 = 100 * gaps.cvar_gap_closure_fraction.median()
    ax.text(0.03, 0.96,
            f"median capacity-gap closure: O1 {closure_o1:.1f}%, O3 {closure_o3:.1f}%",
            transform=ax.transAxes, va="top", color=DARK)
    panel_label(ax, "B")
    fig.tight_layout(w_pad=1.7)
    save(fig, "fig05_objective_discovery.pdf")


def figure_06() -> None:
    graph = load_csv("results/phase2_confirmatory_v1/graph_level_contrasts.csv")
    stats = load_json("results/phase2_confirmatory_v1/confirmatory_statistics.json")
    fig, axes = plt.subplots(1, 2, figsize=(7.25, 3.25))
    specifications = [
        ("Delta1_CVAR_MEAN", "H1: O3 $-$ O0", stats["H1"], 0.0, BLUE),
        ("Delta2_CVAR_CAPACITY", "H2: O3 $-$ O2", stats["H2"], -0.10, RED),
    ]
    for label, (column, title, result, null, color) in zip(["A", "B"], specifications):
        ax = axes[0] if label == "A" else axes[1]
        ordered = graph.sort_values(column).reset_index(drop=True)
        y = np.arange(len(ordered))
        ax.scatter(ordered[column], y, s=24, c=color, alpha=0.72)
        ax.axvline(null, color=DARK, linestyle="--", linewidth=1.0,
                   label="null / margin")
        ax.axvline(result["effect_mean"], color=color, linewidth=2.0, label="mean")
        ax.axvline(result["one_sided_95_lower_bound"], color=color,
                   linestyle=":", linewidth=1.5, label="one-sided 95% lower bound")
        ax.set_yticks([])
        ax.set_xlabel(r"graph-level $\Delta G_{\mathrm{feas}}$ (decades)")
        ax.set_title(title)
        ax.legend(frameon=False, loc="lower right")
        ax.text(
            0.03,
            0.96,
            f"mean={result['effect_mean']:+.4f}\nlower={result['one_sided_95_lower_bound']:+.4f}\nHolm $p$={result['holm_adjusted_p_value']:.6f}",
            transform=ax.transAxes,
            va="top",
            color=DARK,
        )
        panel_label(ax, label)
    fig.suptitle("Preregistered held-out evaluation: 84 tasks on 15 base graphs",
                 y=1.03, fontsize=10.5, fontweight="bold")
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig06_heldout_confirmation.pdf")


def figure_07() -> None:
    task = load_csv("results/phase2_confirmatory_v1/task_level_contrasts.csv")
    dx = np.log10(task.p_feas_O3 / task.p_feas_O0)
    dy = np.log10(task.p_opt_given_feasible_O3 / task.p_opt_given_feasible_O0)
    dz = np.log10(task.p_opt_O3 / task.p_opt_O0)
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    win = dz > 0
    ax.scatter(dx[win], dy[win], c=GREEN, s=25, alpha=0.65,
               label=r"$P_{\mathrm{opt}}$ increased")
    ax.scatter(dx[~win], dy[~win], c=RED, s=29, alpha=0.78,
               label=r"$P_{\mathrm{opt}}$ did not increase")
    limits = [min(dx.min(), dy.min()) - 0.05, max(dx.max(), dy.max()) + 0.05]
    xline = np.linspace(limits[0], limits[1], 100)
    ax.plot(xline, -xline, color=DARK, linestyle="--", linewidth=1.0,
            label=r"$\Delta\log_{10}P_{\mathrm{opt}}=0$")
    ax.axhline(0, color=GRAY, linewidth=0.7)
    ax.axvline(0, color=GRAY, linewidth=0.7)
    ax.set_xlabel(r"feasible-entry change $\Delta\log_{10}P_{\mathrm{feas}}$")
    ax.set_ylabel(r"conditional-optimality change $\Delta\log_{10}P_{\mathrm{opt}\mid\mathrm{feas}}$")
    ax.set_title(r"Held-out decomposition: $P_{\mathrm{opt}}=P_{\mathrm{feas}}P_{\mathrm{opt}\mid\mathrm{feas}}$")
    ax.legend(frameon=False, loc="lower left")
    ax.text(0.03, 0.97,
            "80/84 improve $P_{\\mathrm{opt}}$\n"
            "79/84 improve both $P_{\\mathrm{feas}}$ and $P_{\\mathrm{opt}}$\n"
            "32/84 trade conditional quality for entry",
            transform=ax.transAxes, va="top", color=DARK)
    save(fig, "fig07_feasibility_optimality.pdf")


def figure_08() -> None:
    exponents = load_csv("results/phase3_scaling_v1/base_graph_exponents.csv")
    groups = [
        ("development", "Development\n$m=12$--18"),
        ("interpolation_holdout", "Interpolation\n$m=12$--18"),
        ("extrapolation_holdout", "$m=20$\nholdout"),
    ]
    objectives = ["O0", "O2", "O3"]
    offsets = {"O0": -0.20, "O2": 0.0, "O3": 0.20}
    fig, ax = plt.subplots(figsize=(7.15, 3.55))
    for group_index, (split, _) in enumerate(groups):
        subset = exponents[exponents.split.eq(split)]
        for objective in objectives:
            values = subset[subset.objective.eq(objective)].eta.to_numpy()
            x = group_index + offsets[objective]
            ax.scatter(jitter(np.full(len(values), x), 0.055), values, s=15,
                       alpha=0.33, color=OBJECTIVE_COLORS[objective])
            ax.scatter([x], [np.mean(values)], s=62, marker="D",
                       edgecolor="white", linewidth=0.7,
                       color=OBJECTIVE_COLORS[objective], zorder=4,
                       label=OBJECTIVE_LABELS[objective] if group_index == 0 else None)
    censored_x = 3.0
    ax.add_patch(Rectangle((censored_x - 0.42, ax.get_ylim()[0]), 0.84,
                           ax.get_ylim()[1] - ax.get_ylim()[0], facecolor="#E1E5EA",
                           edgecolor=GRAY, hatch="///", alpha=0.55, zorder=-1))
    ax.text(censored_x, 0.55, "RESOURCE\nCENSORED", ha="center", va="center",
            color=DARK, fontweight="bold", transform=ax.get_xaxis_transform())
    ax.axhline(1.0, color=DARK, linestyle="--", linewidth=0.9,
               label=r"uniform response $\eta=1$")
    ax.set_xticks(np.arange(4), [label for _, label in groups] + ["$m=22$"])
    ax.set_xlim(-0.55, 3.5)
    ax.set_ylabel(r"graph-level exponent $\eta$ (points; diamonds are means)")
    ax.set_title("Objective-specific scaling response; no extrapolation through censoring")
    ax.legend(frameon=False, ncol=2, loc="upper left")
    save(fig, "fig08_scaling_response.pdf")


def figure_09() -> None:
    fig, ax = plt.subplots(figsize=(7.25, 3.35))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    box(ax, (0.03, 0.60), (0.25, 0.20), "raw edge-bit density\n$\\phi_{\\mathrm{state}}$", PURPLE)
    box(ax, (0.03, 0.18), (0.25, 0.20), "explicit RCSP\ninput and output", BLUE)
    ax.text(0.155, 0.49, r"$\neq$ intrinsic hardness", ha="center", va="center",
            color=RED, fontsize=10, fontweight="bold")
    arrow(ax, (0.30, 0.69), (0.40, 0.69))
    box(ax, (0.41, 0.60), (0.25, 0.20), "membership-only\nfull-space search", ORANGE)
    ax.text(0.535, 0.47, r"$\mathbb{E}P\leq(2q+1)^2\phi$", ha="center",
            fontsize=10, color=DARK)
    arrow(ax, (0.67, 0.69), (0.75, 0.69))
    box(ax, (0.76, 0.60), (0.21, 0.20), "posterior\nstructure $S$", GREEN)
    ax.text(0.865, 0.47, r"$\phi\rightarrow\Lambda(S)$", ha="center",
            fontsize=10, color=DARK)
    arrow(ax, (0.535, 0.43), (0.535, 0.32))
    box(ax, (0.38, 0.12), (0.29, 0.16), "stronger access model\nor simulation cost", TEAL, 8.3)
    ax.text(0.835, 0.20,
            "preprocessing | state prep.\nmixer / oracle\nsampling | validation",
            ha="center", va="center", color=GRAY, fontsize=7.7, linespacing=1.25)
    ax.text(0.5, 0.93, "Theory scope: representation, query domain, and structure are distinct",
            ha="center", va="center", fontsize=11, fontweight="bold", color=DARK)
    save(fig, "fig09_theory_scope.pdf")


def figure_10() -> None:
    matrix = load_csv("results/theory_validation_v3/structure_cost_method_matrix.csv")
    wanted = [
        "Penalty-X full-space QAOA",
        "CVaR Penalty-X",
        "Warm-start QAOA",
        "Feasible-subspace state preparation",
        "Path-exchange mixer",
        "Explicit feasible-basis QAOA",
        "Classical corridor restriction",
    ]
    matrix = matrix.set_index("method").loc[wanted].reset_index()
    buckets = {
        "Information": ("advice", "explicit", "energy", "list", "candidate", "structure"),
        "Classical\npreprocess": ("training", "sorting", "relaxation", "enumeration", "generation", "corridor", "construction"),
        "State\npreparation": ("state", "loader", "loading", "postselection", "ancilla", "warm-state"),
        "Mixer /\ncompilation": ("mixer", "compilation", "connectivity", "reflection"),
        "Query /\nvalidation": ("query", "oracle", "sampling", "energy evaluation", "validation", "checks"),
    }
    presence = np.zeros((len(wanted), len(buckets)), dtype=int)
    for row_index, row in matrix.iterrows():
        text_blob = " ".join(
            str(row[column]).lower()
            for column in ["injected_structure", "theorem_class", "relocated_burden", "unknown"]
        )
        for col_index, keywords in enumerate(buckets.values()):
            presence[row_index, col_index] = int(any(word.lower() in text_blob for word in keywords))

    display_names = [
        "Penalty-X",
        "CVaR Penalty-X",
        "Warm start",
        "Feasible-state prep.",
        "Path-exchange mixer",
        "Explicit path basis",
        "Corridor restriction",
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    cmap = ListedColormap(["#F5F6F7", "#5B8E7D"])
    ax.imshow(presence, cmap=cmap, aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(buckets)), list(buckets))
    ax.set_yticks(np.arange(len(display_names)), display_names)
    ax.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False)
    for i in range(presence.shape[0]):
        for j in range(presence.shape[1]):
            ax.text(j, i, "cost" if presence[i, j] else "--", ha="center", va="center",
                    color="white" if presence[i, j] else GRAY,
                    fontsize=8, fontweight="bold" if presence[i, j] else "normal")
    ax.set_title("Where structure injection relocates burden", pad=34)
    ax.text(0.5, -0.10,
            "Cells identify cost categories named in the method ledger; they do not assign a scalar runtime.",
            transform=ax.transAxes, ha="center", va="top", color=GRAY, fontsize=8)
    ax.grid(False)
    save(fig, "fig10_structure_cost_relocation.pdf")


def write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def table_01() -> str:
    return r"""
\begin{table}[t]
\centering
\caption{Experimental stages and protocol roles. Discovery and held-out rows are never pooled for inference.}
\label{tab:protocol-summary}
\small
\begin{tabularx}{\textwidth}{@{}lXrrl@{}}
\toprule
Stage & Scientific role & Tasks & Graphs & QAOA setting \\
\midrule
Task audit v1 & Expose duplicate feasible-set levels & 175 & 25 & No QAOA \\
Distinct-cardinality v2 & Controlled universe and scale audit & 140 & 25 & No QAOA \\
Depth pilot & Exploratory dilution response & 56 & 10 & Penalty-X, $p=1,2,3$ \\
Optimizer diagnostic & Nested-ansatz and continuation attribution & 56 & 10 & Penalty-X, $p=3$ \\
Objective discovery & Select the held-out objective & 56 & 10 & O0--O3, $p=3$ \\
Held-out evaluation & Preregistered graph-level confirmation & 84 & 15 & O0/O2/O3, $p=3$ \\
Scaling response & Prespecified size-conditioned response; $m=22$ censored & 180 planned & 30 & O0/O2/O3, $p=3$ \\
\bottomrule
\end{tabularx}
\end{table}
"""


def table_02() -> str:
    return r"""
\begin{table}[t]
\centering
\caption{Classical training losses applied to the same $p=3$ Penalty-X ansatz and the same normalized cost-phase Hamiltonian.}
\label{tab:objectives}
\small
\begin{tabularx}{\textwidth}{@{}l>{\raggedright\arraybackslash}p{1.8cm}>{\raggedright\arraybackslash}p{5.0cm}X@{}}
\toprule
ID & Name & Loss minimized & Role \\
\midrule
O0 & Mean energy & $\mathbb{E}_{\theta}[H_C]$ & Standard variational baseline \\
O1 & Expected penalty & $\mathbb{E}_{\theta}[P_{\mathrm{flow}}+P_{\mathrm{resource}}]$ & Mechanistic feasibility surrogate \\
O2 & Exact feasibility & $1-P_{\mathrm{feas}}(\theta)$ & Statevector-only ansatz-capacity control; not deployable \\
O3 & CVaR-0.10 & Mean of the lowest-energy probability mass $\alpha=0.10$ & Tail-focused rich-energy objective \\
\bottomrule
\end{tabularx}
\end{table}
"""


def table_03() -> str:
    headline = load_json(
        "results/finalization_audit_v1/reconstructed_headlines.json"
    )["optimizer_attribution"]
    rows = [
        f"Nested $p=2\\to p=3$ zero-layer identity & "
        f"{headline['nested_identity_pass_count']}/{headline['nested_identity_denominator']} \\\\",
        f"Original $p=3$ objective worse than embedded $p=2$ & "
        f"{headline['certified_optimizer_failures']}/"
        f"{headline['certified_optimizer_failure_denominator']} \\\\",
        f"Continuation recovered lower objective in that failure set & "
        f"{headline['continuation_objective_repairs']}/"
        f"{headline['continuation_objective_repair_denominator']} \\\\",
        f"Continuation increased $G_{{\\mathrm{{feas}}}}$ in that failure set & "
        f"{headline['continuation_feasibility_improvements']}/"
        f"{headline['continuation_feasibility_improvement_denominator']} \\\\",
        f"Random $p=3$ had lower energy but lower $G_{{\\mathrm{{feas}}}}$ & "
        f"{headline['lower_energy_and_lower_feasibility_gain']}/"
        f"{headline['lower_energy_and_lower_feasibility_gain_denominator']} \\\\",
    ]
    return r"""
\begin{table}[t]
\centering
\caption{Optimizer attribution on the 56-task discovery set. Counts are seed-level unless stated otherwise.}
\label{tab:optimizer-attribution}
\small
\begin{tabularx}{\textwidth}{@{}Xr@{}}
\toprule
Diagnostic & Result \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabularx}
\end{table}
"""


def table_04() -> str:
    heldout = load_json(
        "results/finalization_audit_v1/heldout_statistics_rebuilt.json"
    )
    h1 = heldout["H1"]
    h2 = heldout["H2"]
    h1_row = (
        "H1 & O3 CVaR $-$ O0 mean energy & "
        f"${h1['effect_mean']:+.4f}$ & ${h1['one_sided_95_lower_bound']:+.4f}$ & "
        f"${h1['null_margin']:.0f}$ & ${h1['holm_adjusted_p_value']:.3g}$ \\\\"
    )
    h2_row = (
        "H2 & O3 CVaR $-$ O2 capacity control & "
        f"${h2['effect_mean']:+.4f}$ & ${h2['one_sided_95_lower_bound']:+.4f}$ & "
        f"${h2['null_margin']:.2f}$ & ${h2['holm_adjusted_p_value']:.3g}$ \\\\"
    )
    return r"""
\begin{table}[t]
\centering
\caption{Preregistered held-out graph-level tests ($15$ base graphs; $84$ tasks). Lower bounds are one-sided grouped-bootstrap 95\% bounds; $p$-values are Holm adjusted.}
\label{tab:heldout-tests}
\small
\begin{tabularx}{\textwidth}{@{}lXrrrr@{}}
\toprule
Test & Contrast in $G_{\mathrm{feas}}$ & Effect & Lower bound & Null/margin & Holm $p$ \\
\midrule
""" + h1_row + "\n" + h2_row + r"""
\bottomrule
\end{tabularx}
\end{table}
"""


def table_05() -> str:
    exponent = load_csv(
        "results/finalization_audit_v1/scaling_exponents_rebuilt.csv"
    )
    means = exponent.groupby(["split", "objective"]).eta.mean()
    row_specs = [
        ("Development, $m=12$--18", "development"),
        ("Interpolation, $m=12$--18", "interpolation_holdout"),
        ("Extrapolation, $m=20$", "extrapolation_holdout"),
    ]
    rows = [
        f"{label} & {means.loc[(split, 'O0')]:.4f} & "
        f"{means.loc[(split, 'O2')]:.4f} & {means.loc[(split, 'O3')]:.4f} \\\\"
        for label, split in row_specs
    ]
    return r"""
\begin{table}[t]
\centering
\caption{Mean graph-level scaling-response exponent $\eta$ by frozen split. The $m=22$ cells were prospectively resource-censored; no global scaling law is inferred.}
\label{tab:scaling-summary}
\small
\begin{tabular}{@{}lrrr@{}}
\toprule
Split & O0 mean & O2 capacity & O3 CVaR \\
\midrule
""" + "\n".join(rows) + r"""
$m=22$ & \multicolumn{3}{c}{\textsc{resource censored}} \\
\bottomrule
\end{tabular}
\end{table}
"""


def table_06() -> str:
    return r"""
\begin{table}[t]
\centering
\caption{Theory statements are tied to their information-access model. They are interpretation boundaries, not an end-to-end runtime theorem for the experiments.}
\label{tab:theory-scope}
\small
\begin{tabularx}{\textwidth}{@{}lXX@{}}
\toprule
Result & Model and conclusion & Explicit nonclaim \\
\midrule
Membership dilution & Uniform random size-$M$ marked set; counted membership queries; $\mathbb{E}P\leq\min\{1,(2q+1)^2\phi\}$ & Not pointwise for every set; not rich-energy RCSP \\
Raw-density counterexample & Explicit chain has $\phi_{\mathrm{state}}=2^{-m}$ and $O(m)$ output time & Raw density is not intrinsic explicit-RCSP hardness \\
Attribute-query RCSP & Length-$K$ counted random-access array; $\Theta_{\tau}(\sqrt{K/M})$ in the nontrivial target regime & Not explicit RAM time or compact-input exponential hardness \\
Posterior structure & Classical side information enters through $\Lambda(S)$ & Advice concentration is not implementation time \\
Finite advice & At most $b$ classical support bits multiply the coarse bound by $2^b$ & Necessary condition only; not sufficient \\
\bottomrule
\end{tabularx}
\end{table}
"""


def supplementary_tables() -> dict[str, str]:
    return {
        "tableS1_failure_census.tex": r"""
\begin{table}[ht]
\centering
\caption{Retained execution and censoring census. A zero denotes a retained planned category with no observed event.}
\label{tab:failure-census}
\small
\begin{tabularx}{\textwidth}{@{}Xrrrr@{}}
\toprule
Stage & Success & \shortstack{Timeout/\\OOM} & \shortstack{Other scientific\\failure} & \shortstack{Resource-\\censored} \\
\midrule
Pilot optimized runs & 504 & 0 & 0 & 0 \\
Held-out $p=2$ preparation & 252 & 0 & 0 & 0 \\
Held-out $p=3$ comparison & 252 & 0 & 0 & 0 \\
Scaling $p=2$ and $p=3$ & 1080 & 0 & 0 & 180 planned cells \\
\bottomrule
\end{tabularx}
\end{table}
""",
        "tableS2_task_strata.tex": task_strata_table(),
        "tableS3_statistics.tex": r"""
\begin{table}[ht]
\centering
\caption{Frozen held-out inferential contract.}
\label{tab:statistics-contract}
\small
\begin{tabularx}{\textwidth}{@{}lX@{}}
\toprule
Item & Frozen specification \\
\midrule
Analysis unit & Base graph; arithmetic mean over all planned dilution levels \\
Primary family & H1 superiority and H2 non-inferiority only \\
Uncertainty & 10,000 grouped bootstrap resamples; one-sided 5th-percentile lower bound \\
Tests & Exact $2^{15}=32768$ graph-level sign flips \\
Multiplicity & Holm correction over the two-hypothesis family at $\alpha=0.05$ \\
H2 margin & $-0.10$ decades in $G_{\mathrm{feas}}$ \\
Separation & 84 tasks and 15 graphs; zero overlap with discovery \\
\bottomrule
\end{tabularx}
\end{table}
""",
        "tableS4_proof_assumptions.tex": r"""
\begin{table}[ht]
\centering
\caption{Assumptions that bound the interpretation of the formal results.}
\label{tab:proof-assumptions}
\small
\begin{tabularx}{\textwidth}{@{}lX@{}}
\toprule
Result & Required assumptions \\
\midrule
Fixed/adaptive dilution & Uniform fixed-cardinality prior; all remaining feasible-set dependence enters through counted membership queries; pathwise hard cap for adaptive protocols \\
Trained specialization & Training, sampling, feedback, and final membership calls are counted jointly \\
Expected-query form & Integer truncation with an explicit tail term; no substitution of $\mathbb{E}Q$ for a hard cap \\
Posterior structure & One classical pre-search channel; conditional reference circuit independent of residual feasible-set uncertainty \\
Classical advice & Advice support has cardinality at most $2^b$; $b$ is not mutual information \\
Quantum advice & One accessible pre-search state of total dimension $d$; no refreshing or interactive provider \\
Attribute-query RCSP & Explicit length-$K$ attribute array accessed only through counted quantum random access \\
\bottomrule
\end{tabularx}
\end{table}
""",
        "tableS5_artifact_hashes.tex": artifact_hash_table(),
    }


def task_strata_table() -> str:
    task = load_csv("results/phase0_v2_dilution_stress/task_characterization.csv")
    rows = []
    for size, group in task.groupby("size_stratum", sort=True):
        rows.append(
            f"{size} & {int(group.n_edges.iloc[0])} & {group.base_instance_id.nunique()} & "
            f"{len(group)} & {group.feasible_state_fraction.min():.3g} & "
            f"{group.feasible_state_fraction.max():.3g} \\\\"
        )
    body = "\n".join(rows)
    return rf"""
\begin{{table}}[ht]
\centering
\caption{{Distinct-cardinality task strata used to define the controlled universe.}}
\label{{tab:task-strata}}
\small
\begin{{tabular}}{{@{{}}lrrrrr@{{}}}}
\toprule
Stratum & Edges & Graphs & Tasks & $\phi_{{\min}}$ & $\phi_{{\max}}$ \\
\midrule
{body}
\bottomrule
\end{{tabular}}
\end{{table}}
"""


def artifact_hash_table() -> str:
    entries = [
        ("Task-universe manifest", "data/manifests/phase0_v2_dilution_stress.json"),
        ("Held-out preregistration", "results/phase2_confirmatory_v1/PREREGISTRATION.md"),
        ("Held-out statistics", "results/phase2_confirmatory_v1/confirmatory_statistics.json"),
        ("Scaling freeze", "results/phase3_scaling_v1/SCALING_MODEL_FREEZE.json"),
        ("Synthesis claim matrix", "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv"),
    ]
    rows = []
    for name, path in entries:
        digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        rows.append(f"{name} & \\texttt{{{digest[:16]}...}} \\\\")
    body = "\n".join(rows)
    return rf"""
\begin{{table}}[ht]
\centering
\caption{{Selected frozen-input SHA-256 fingerprints (prefixes shown; complete values are in \texttt{{supplementary/artifact\_manifest.txt}}).}}
\label{{tab:artifact-hashes}}
\small
\begin{{tabular}}{{@{{}}ll@{{}}}}
\toprule
Asset & SHA-256 prefix \\
\midrule
{body}
\bottomrule
\end{{tabular}}
\end{{table}}
"""


def build_tables() -> None:
    tables = {
        "table01_protocol_summary.tex": table_01(),
        "table02_objectives.tex": table_02(),
        "table03_optimizer_attribution.tex": table_03(),
        "table04_heldout_results.tex": table_04(),
        "table05_scaling_response.tex": table_05(),
        "table06_theory_scope.tex": table_06(),
        **supplementary_tables(),
    }
    for filename, content in tables.items():
        write_text(TABLE_DIR / filename, content)


def build_claim_evidence_summary() -> None:
    source = load_csv("results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv")
    columns = [
        "claim_id",
        "candidate_wording",
        "claim_class",
        "evidence_stage",
        "inference_tier",
        "source_files",
        "scope",
        "status",
        "allowed_wording",
        "prohibited_wording",
    ]
    compact = source[columns].copy()
    for column in compact.columns:
        compact[column] = compact[column].astype(str).str.replace(str(ROOT) + "/", "", regex=False)
    compact.to_csv(SUPP_DIR / "claim_evidence_summary.csv", index=False)

    numeric = load_csv("results/synthesis_v1/numeric_claim_audit.csv")
    numeric = numeric.copy()
    numeric.source_file = numeric.source_file.astype(str).str.replace(str(ROOT) + "/", "", regex=False)
    numeric.to_csv(SUPP_DIR / "numeric_audit.csv", index=False)

    pilot = load_csv("results/phase1_pilot_v1/failure_census.csv").copy()
    pilot.insert(0, "evidence_stage", "pilot")
    pilot.insert(1, "phase", "PENALTY_X_OPTIMIZATION")
    pilot = pilot.rename(columns={"planned_optimized_denominator": "planned_denominator"})
    for column in ("split", "size_m", "depth", "objective_id", "failure_reason", "resource_censored"):
        pilot[column] = ""

    heldout = load_csv("results/phase2_confirmatory_v1/failure_census.csv").copy()
    heldout.insert(0, "evidence_stage", "heldout")
    for column in ("split", "size_m", "depth", "objective_id", "failure_reason", "resource_censored"):
        heldout[column] = ""

    scaling = load_csv("results/phase3_scaling_v1/failure_census.csv").copy()
    scaling.insert(0, "evidence_stage", "scaling")
    scaling.insert(1, "phase", "SCALING_EXECUTION")
    scaling["planned_denominator"] = scaling["count"]

    census_columns = [
        "evidence_stage", "phase", "split", "size_m", "depth", "objective_id",
        "execution_status", "failure_reason", "resource_censored", "count",
        "planned_denominator",
    ]
    pd.concat(
        [pilot[census_columns], heldout[census_columns], scaling[census_columns]],
        ignore_index=True,
    ).to_csv(SUPP_DIR / "full_failure_census.csv", index=False)

    task = load_csv("results/phase0_v2_dilution_stress/task_characterization.csv")
    strata = (
        task.groupby(["size_stratum", "n_edges"], as_index=False)
        .agg(
            base_graphs=("base_instance_id", "nunique"),
            tasks=("task_id", "size"),
            phi_min=("feasible_state_fraction", "min"),
            phi_max=("feasible_state_fraction", "max"),
            dilution_min=("dilution_score", "min"),
            dilution_max=("dilution_score", "max"),
        )
    )
    strata.to_csv(SUPP_DIR / "task_strata.csv", index=False)


def build_manifests() -> None:
    figure_rows = [
        ("F1", "Controlled attribution pipeline", "configs/phase0_v2_dilution_stress.yaml; configs/phase1_2_objective_alignment.yaml", "conceptual protocol sequence", "paper_scripts/build_paper_assets.py", "figures/fig01_experimental_concept.pdf"),
        ("F2", "Dilution coverage and Hamiltonian scale control", "results/phase0_v2_dilution_stress/task_characterization.csv; results/phase0_v2_dilution_stress/penalty_contract_comparison.csv", "all 140 v2 tasks; raw and controlled spans", "paper_scripts/build_paper_assets.py", "figures/fig02_dilution_scale_control.pdf"),
        ("F3", "Optimizer attribution", "results/phase1_1_optimization_diagnostic/p3_random_vs_embedded.csv; results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv", "all 168 matched seed-level rows", "paper_scripts/build_paper_assets.py", "figures/fig03_optimizer_attribution.pdf"),
        ("F4", "Objective--feasibility misalignment", "results/phase1_1_optimization_diagnostic/analysis/continuation_paired_comparison.csv; results/phase1_1_optimization_diagnostic/objective_decomposition.csv", "random p3 and continuation B1, matched by task and seed; medians", "paper_scripts/build_paper_assets.py", "figures/fig04_objective_misalignment.pdf"),
        ("F5", "Discovery objective comparison", "results/phase1_2_objective_alignment/task_objective_summary.csv; results/phase1_2_objective_alignment/capacity_gap.csv", "56 discovery tasks; paired objective contrasts", "paper_scripts/build_paper_assets.py", "figures/fig05_objective_discovery.pdf"),
        ("F6", "Preregistered held-out graph-level contrasts", "results/phase2_confirmatory_v1/graph_level_contrasts.csv; results/phase2_confirmatory_v1/confirmatory_statistics.json", "15 complete graph means; preregistered H1/H2 inference", "paper_scripts/build_paper_assets.py", "figures/fig06_heldout_confirmation.pdf"),
        ("F7", "Feasibility/conditional-optimality decomposition", "results/phase2_confirmatory_v1/task_level_contrasts.csv", "84 held-out paired task rows; log-ratio identity", "paper_scripts/build_paper_assets.py", "figures/fig07_feasibility_optimality.pdf"),
        ("F8", "Scaling response and resource censoring", "results/phase3_scaling_v1/base_graph_exponents.csv", "75 completed graph-objective exponents grouped by protocol split; m22 shown as censored", "paper_scripts/build_paper_assets.py", "figures/fig08_scaling_response.pdf"),
        ("F9", "Theory access-model scope", "docs/theory/RAW_EDGE_BIT_DILUTION_COUNTEREXAMPLE.md; docs/theory/ADAPTIVE_QUERY_DILUTION_THEOREM.md; docs/theory/POSTERIOR_STRUCTURE_DILUTION_THEOREM.md", "conceptual summary of audited statements", "paper_scripts/build_paper_assets.py", "figures/fig09_theory_scope.pdf"),
        ("F10", "Structure-cost relocation", "results/theory_validation_v3/structure_cost_method_matrix.csv", "selected representative methods; keyword-to-resource-category mapping from canonical burden text", "paper_scripts/build_paper_assets.py", "figures/fig10_structure_cost_relocation.pdf"),
        ("F11", "Post-hoc finite-shot endpoint robustness", "results/posthoc_finite_shot_endpoint_v1/aggregate.csv; results/posthoc_finite_shot_endpoint_v1/exact_reference.csv", "all 84 held-out tasks; frozen O0/O3 endpoints; 20 replicates at 1k/10k/100k shots", "paper_scripts/run_posthoc_finite_shot_endpoint.py", "figures/fig11_finite_shot_endpoint_robustness.pdf"),
    ]
    with (AUDIT_DIR / "figure_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["figure_id", "caption", "canonical_input_files", "filter", "aggregation", "script", "output_file"])
        for figure_id, caption, inputs, aggregation, script, output in figure_rows:
            writer.writerow([figure_id, caption, inputs, "frozen canonical rows only", aggregation, script, output])

    table_rows = [
        ("T1", "tables/table01_protocol_summary.tex", "canonical stage configs and summary.json files", "frozen stage counts", "integers exact; no rounding"),
        ("T2", "tables/table02_objectives.tex", "configs/phase1_2_objective_alignment.yaml", "verbatim frozen objective definitions", "not applicable"),
        ("T3", "tables/table03_optimizer_attribution.tex", "results/finalization_audit_v1/reconstructed_headlines.json", "independently rebuilt seed-level counts", "counts exact"),
        ("T4", "tables/table04_heldout_results.tex", "results/finalization_audit_v1/heldout_statistics_rebuilt.json", "independently rebuilt preregistered graph-level H1/H2", "effects/bounds 4 decimals; p 3 significant digits"),
        ("T5", "tables/table05_scaling_response.tex", "results/finalization_audit_v1/scaling_exponents_rebuilt.csv", "independently rebuilt mean graph-level eta by split/objective", "4 decimals"),
        ("T6", "tables/table06_theory_scope.tex", "docs/theory/* theorem audits", "statement/model/nonclaim synopsis", "not applicable"),
        ("T7", "tables/table07_related_work.tex", "verified primary literature listed in references.bib and docs/related_work_audit.md", "qualitative comparison of representative work", "not applicable"),
        ("TS1", "tables/tableS1_failure_census.tex", "phase pilot/heldout/scaling failure censuses", "retained denominators by stage", "counts exact"),
        ("TS2", "tables/tableS2_task_strata.tex", "results/phase0_v2_dilution_stress/task_characterization.csv", "group by size stratum", "phi 3 significant digits"),
        ("TS3", "tables/tableS3_statistics.tex", "configs/phase2_confirmatory_v1.yaml", "frozen inferential contract", "not applicable"),
        ("TS4", "tables/tableS4_proof_assumptions.tex", "results/synthesis_v1/second_pass_proof_review.csv", "publication-critical assumptions", "not applicable"),
        ("TS5", "tables/tableS5_artifact_hashes.tex", "five canonical files", "SHA-256", "16-character prefix in table"),
    ]
    with (AUDIT_DIR / "table_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["table_id", "output_file", "source", "aggregation", "rounding_policy"])
        writer.writerows(table_rows)


def main() -> None:
    for directory in (FIG_DIR, TABLE_DIR, SUPP_DIR, AUDIT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    configure_style()
    figure_01()
    figure_02()
    figure_03()
    figure_04()
    figure_05()
    figure_06()
    figure_07()
    figure_08()
    figure_09()
    figure_10()
    build_tables()
    build_claim_evidence_summary()
    build_manifests()
    print("Built 10 primary figures, retained 1 post-hoc figure, registered 12 tables, and refreshed supplements/manifests.")


if __name__ == "__main__":
    main()
