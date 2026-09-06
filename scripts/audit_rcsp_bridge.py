#!/usr/bin/env python3
"""Generate the explicit-input RCSP bridge and description audits."""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, write_json
from qroute_dilution.theory.description_barrier import description_barrier_table
from qroute_dilution.theory.rcsp_bridge import small_bridge_validation


RESULT_ROOT = PROJECT_ROOT / "results/theory_validation_v2"
FIGURE_ROOT = RESULT_ROOT / "figures"


BRIDGE_ROWS = [
    {
        "construction": "PARALLEL_PATH_CONSTRUCTION",
        "domain_definition": "N explicitly listed source-target paths",
        "N": "2^n candidate paths",
        "M": "marked paths",
        "phi": "M/N in path-index domain; M/2^(2N) in edge-bit domain",
        "decoder": "intermediate path vertex identifies label",
        "invalid_state_treatment": "all non-path edge-bit strings invalid",
        "oracle_action": "explicit resource coefficients, not hidden oracle",
        "size_scaling": "Theta(N) vertices and edges",
        "leakage": "marked set visible from path coefficients",
        "status": "VALID_BUT_EXPLICIT_SIZE_THETA_N",
    },
    {
        "construction": "LAYERED_BINARY_GRAPH",
        "domain_definition": "2^n paths through n binary choices",
        "N": "2^n candidate paths",
        "M": "arbitrary target subset",
        "phi": "M/2^n in path domain; M/2^(2n) in raw edge-bit domain",
        "decoder": "edge choice sequence is the label",
        "invalid_state_treatment": "edge-bit selections not choosing exactly one edge/layer invalid",
        "oracle_action": "explicit additive resource inequalities",
        "size_scaling": "O(n) graph but N-M resources for audited arbitrary-subset encoding",
        "leakage": "full resource table reconstructs feasibility",
        "status": "NO_POLYNOMIAL_ARBITRARY_SUBSET_ENCODING_FOUND",
    },
    {
        "construction": "CIRCUIT_VERIFIER_CONSTRUCTION",
        "domain_definition": "labels accepted by a succinct Boolean predicate",
        "N": "2^n labels",
        "M": "accepting assignments",
        "phi": "M/2^n before any edge-bit compilation",
        "decoder": "predicate input bits",
        "invalid_state_treatment": "depends on unproved compiler",
        "oracle_action": "explicit predicate/circuit can expose structure",
        "size_scaling": "polynomial only for predicates with polynomial circuits",
        "leakage": "predicate description is free F-dependent side information",
        "status": "SUCCINCT_PREDICATE_NOT_STANDARD_ADDITIVE_RCSP_BRIDGE",
    },
    {
        "construction": "HIDDEN_SINGLETON",
        "domain_definition": "2^n binary-choice paths",
        "N": "2^n",
        "M": "1",
        "phi": "2^-n in path domain",
        "decoder": "choice bits",
        "invalid_state_treatment": "raw edge-bit strings invalid unless one choice/layer",
        "oracle_action": "one explicit resource with zero cost on marked choices",
        "size_scaling": "O(n)",
        "leakage": "zero-weight choice in every layer reads out singleton",
        "status": "COMPACT_BUT_EXPLICIT_INPUT_REVEALS_SINGLETON",
    },
    {
        "construction": "ORACLE_RCSP",
        "domain_definition": "route-index labels with oracle-only feasibility",
        "N": "2^n route indices",
        "M": "hidden feasible route indices",
        "phi": "M/2^n",
        "decoder": "binary label to logical route",
        "invalid_state_treatment": "none in route-index domain",
        "oracle_action": "binary membership phase/bit query",
        "size_scaling": "polynomial interface",
        "leakage": "none beyond oracle",
        "status": "ORACLE_RCSP_COROLLARY",
    },
    {
        "construction": "RICH_COST_ORACLE",
        "domain_definition": "basis states with multilevel RCSP energy",
        "N": "representation-dependent",
        "M": "feasible ground/accepted states",
        "phi": "representation-dependent",
        "decoder": "problem encoding",
        "invalid_state_treatment": "energy penalties reveal violation magnitudes",
        "oracle_action": "multilevel phase/value information",
        "size_scaling": "not resolved",
        "leakage": "may reveal gradients, distances, and local constraints",
        "status": "RICH_COST_ORACLE_EXTENSION_OPEN",
    },
    {
        "construction": "EDGE_BIT_SPACE_MAPPING",
        "domain_definition": "all 2^|E| edge selections",
        "N": "2^|E|",
        "M": "feasible edge selections under the exact encoding",
        "phi": "M/2^|E|, not feasible routes/candidate routes",
        "decoder": "flow-valid edge selection to path",
        "invalid_state_treatment": "disconnected/cyclic/branched selections remain in denominator",
        "oracle_action": "encoding-specific penalties or membership",
        "size_scaling": "polynomial qubits but exponentially many basis states",
        "leakage": "depends on explicit Hamiltonian",
        "status": "DOMAIN_IDENTIFIED_NO_BLACK_BOX_REDUCTION",
    },
]


SCOPE_ROWS = [
    ("Hidden marked-set oracle QAOA", "YES", "All F-dependence is charged to membership queries."),
    ("Explicit-QUBO QAOA", "NO", "QUBO coefficients are free F-dependent side information."),
    ("Explicit RCSP graph + penalties", "NO", "Topology and coefficients expose structure and richer values."),
    ("Feasible-subspace state preparation", "NO", "Feasible structure enters through initialization."),
    ("Learned parameters transferred from unrelated instances", "CONDITIONAL", "Covered if transfer data are independent of the hidden F."),
    ("Same-instance parameters trained through oracle calls only", "YES_WITH_TOTAL_CAP", "Count every training shot, evaluation, and final query."),
    ("Parameters from complete feasible enumeration", "NO", "Enumeration supplies F outside the oracle account."),
]


def _box(ax, x: float, y: float, text: str, color: str) -> None:
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.5", "facecolor": color, "edgecolor": "0.25"},
    )


def make_figures(description: pd.DataFrame) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.axis("off")
    _box(ax, 0.18, 0.75, "membership oracle only\ncovered with hard cap", "#d8f3dc")
    _box(ax, 0.50, 0.75, "explicit cost input\nfree side information", "#ffe5b4")
    _box(ax, 0.82, 0.75, "rich value oracle\nseparate lower bound needed", "#ffd6d6")
    _box(ax, 0.34, 0.28, "structure-injected\ninitial state", "#dbeafe")
    _box(ax, 0.68, 0.28, "feasible-subspace\nmixer", "#dbeafe")
    ax.set_title("Query-information model taxonomy")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure04_information_access_taxonomy.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.axis("off")
    _box(ax, 0.12, 0.5, "black-box\nmarked set", "#e0f2fe")
    targets = [
        (0.42, 0.78, "oracle-RCSP\ndirect", "#d8f3dc"),
        (0.68, 0.5, "explicit parallel paths\nTheta(N)", "#ffe5b4"),
        (0.42, 0.20, "succinct explicit RCSP\nno valid bridge found", "#ffd6d6"),
    ]
    for x, y, label, color in targets:
        _box(ax, x, y, label, color)
        ax.annotate("", xy=(x - 0.10, y), xytext=(0.20, 0.5), arrowprops={"arrowstyle": "->"})
    ax.set_title("RCSP bridge audit")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure05_rcsp_bridge_map.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for regime, frame in description.groupby("regime"):
        ax.plot(frame.n, frame.log2_binomial, marker="o", markersize=3, label=regime)
    ax.set_yscale("log")
    ax.set(xlabel=r"label qubits $n=\log_2 N$", ylabel=r"$\log_2 \binom{N}{M}$ bits")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure06_description_length_barrier.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    ax.axis("off")
    _box(ax, 0.24, 0.58, "hidden oracle\nmarked labels not readable\nquery hardness retained", "#d8f3dc")
    _box(ax, 0.76, 0.58, "explicit coefficients\nmarked labels reconstructible\nzero-query leakage", "#ffd6d6")
    ax.annotate("same feasible subset", xy=(0.61, 0.58), xytext=(0.39, 0.58), arrowprops={"arrowstyle": "<->"}, ha="center")
    ax.text(0.5, 0.18, "Compact description does not imply hidden search.", ha="center", fontsize=11)
    ax.set_title("Search hardness depends on the information-access model")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure07_search_hardness_leakage.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    small = small_bridge_validation()
    description = description_barrier_table()
    atomic_write_csv(RESULT_ROOT / "rcsp_bridge_matrix.csv", pd.DataFrame(BRIDGE_ROWS))
    atomic_write_csv(RESULT_ROOT / "rcsp_small_case_validation.csv", small)
    atomic_write_csv(RESULT_ROOT / "description_barrier.csv", description)
    atomic_write_csv(
        RESULT_ROOT / "theorem_scope_matrix.csv",
        pd.DataFrame(SCOPE_ROWS, columns=["procedure", "membership_oracle_theorem_applies", "why"]),
    )
    make_figures(description)
    write_json(
        RESULT_ROOT / "rcsp_validation_summary.json",
        {
            "small_case_rows": int(len(small)),
            "mapping_failures": int((~small.marked_feasibility_mapping).sum()),
            "bijection_failures": int((~small.label_path_bijection).sum()),
            "primary_verdict": "ORACLE_RCSP_ONLY",
            "rich_cost_oracle": "RICH_COST_ORACLE_EXTENSION_OPEN",
        },
    )


if __name__ == "__main__":
    main()
