#!/usr/bin/env python3
"""Build the structure-cost method matrix, full ledger, and Figure 8."""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv
from qroute_dilution.theory.structure_cost_ledger import (
    empty_cost_ledger,
    method_matrix,
    validate_ledger,
)


RESULT_ROOT = PROJECT_ROOT / "results/theory_validation_v3"
FIGURE_ROOT = RESULT_ROOT / "figures"


def _box(ax, x: float, text: str, costs: str, color: str) -> None:
    ax.text(
        x,
        0.62,
        text,
        ha="center",
        va="center",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": color, "edgecolor": "0.25"},
    )
    ax.text(x, 0.28, costs, ha="center", va="center", fontsize=7.5, wrap=True)


def make_figure() -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(13.5, 4.8))
    ax.axis("off")
    boxes = (
        (0.09, "full-space\nsearch", "membership/rich-cost queries\ntraining and sampling", "#fee2e2"),
        (0.29, "candidate\nrestriction", "advice/instance bytes\npreprocessing, K_eff", "#ffedd5"),
        (0.50, "state\npreparation", "loader depth/gates\nancillas, retries", "#e0f2fe"),
        (0.71, "structured\nmixer", "description/compile\ndepth, neighbors", "#ede9fe"),
        (0.91, "validation", "decode/check/repair\ndynamic reuse", "#dcfce7"),
    )
    for x, label, costs, color in boxes:
        _box(ax, x, label, costs, color)
    for left, right in zip(boxes, boxes[1:]):
        ax.annotate("", xy=(right[0] - 0.08, 0.62), xytext=(left[0] + 0.08, 0.62), arrowprops={"arrowstyle": "->", "lw": 1.5})
    ax.set_title("Structure injection relocates burden across orthogonal resources")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure08_structure_cost_relocation.png", dpi=180)
    plt.close(fig)


def main() -> None:
    argparse.ArgumentParser().parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    matrix = method_matrix()
    ledger = empty_cost_ledger()
    validate_ledger(ledger)
    atomic_write_csv(RESULT_ROOT / "structure_cost_method_matrix.csv", matrix)
    atomic_write_csv(RESULT_ROOT / "structure_cost_full_ledger.csv", ledger)
    make_figure()


if __name__ == "__main__":
    main()
