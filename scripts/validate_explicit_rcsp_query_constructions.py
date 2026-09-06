#!/usr/bin/env python3
"""Validate the v3 explicit-RCSP constructions and generate Figures 1--4."""

from __future__ import annotations

import argparse
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, write_json
from qroute_dilution.theory.explicit_rcsp_bounds import (
    grover_success_probability,
    grover_upper_bound_queries,
    parallel_branch_instance,
    unique_chain_audit,
)
from qroute_dilution.theory.representation_padding import (
    RationalEdge,
    make_instance,
    padding_audit,
    raw_edge_bit_phi,
    subdivide_edge,
)


RESULT_ROOT = PROJECT_ROOT / "results/theory_validation_v3"
FIGURE_ROOT = RESULT_ROOT / "figures"


def raw_chain_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                **audit.__dict__,
                "explicit_solution_model": "adjacency-list traversal plus edge-list output",
                "counterexample_ratio": audit.inverse_sqrt_phi_state / audit.traversal_steps,
            }
            for audit in (unique_chain_audit(m) for m in range(1, 41))
        ]
    )


def _base_padding_instance():
    return make_instance(
        ("s", "u", "v", "t"),
        (
            RationalEdge.make("a", "s", "u", "7/11", ("2/5", "1/3")),
            RationalEdge.make("b", "u", "t", "5/7", ("1/5", "2/3")),
            RationalEdge.make("c", "s", "v", "3/2", (1, 1)),
            RationalEdge.make("d", "v", "t", "3/2", (1, 1)),
        ),
        "s",
        "t",
        (2, 2),
    )


def padding_rows() -> pd.DataFrame:
    instance = _base_padding_instance()
    rows = []
    for r in (1, 2, 3, 4, 8, 16, 32):
        result = subdivide_edge(instance, "a", r)
        rows.append(
            {
                **padding_audit(result),
                "original_phi": float(raw_edge_bit_phi(instance)),
                "padded_phi": float(raw_edge_bit_phi(result.padded)),
                "logical_problem_id": "diamond_rcsp_exact_rational_v1",
            }
        )
    return pd.DataFrame(rows)


def parallel_rows() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for K in (2, 4, 8, 16):
        for M in range(1, K + 1):
            instance = parallel_branch_instance(K, range(M))
            upper = grover_upper_bound_queries(K, M)
            candidates = range(max(1, upper + 1))
            best_q = max(candidates, key=lambda q: grover_success_probability(K, M, q))
            mapping_ok = all(
                instance.is_feasible(index) == bool(instance.z[index]) for index in range(K)
            )
            rows.append(
                {
                    "K": K,
                    "M": M,
                    "edge_count": instance.edge_count,
                    "feasible_routes": len(instance.feasible_branches),
                    "attribute_mapping_ok": mapping_ok,
                    "attribute_queries_per_feasibility_check": 1,
                    "phi_path": instance.phi_path,
                    "phi_state": instance.phi_state,
                    "K_over_M": K / M,
                    "sqrt_K_over_M": math.sqrt(K / M),
                    "grover_big_O_query_cap": upper,
                    "best_standard_grover_q_in_cap": best_q,
                    "best_standard_grover_success": grover_success_probability(K, M, best_q),
                    "query_model": "explicit topology + counted quantum random-access z array",
                    "bounded_error_scope": (
                        "zero-query target may already hold at high density"
                        if M / K >= 2 / 3
                        else "nontrivial target-success regime"
                    ),
                }
            )
    return pd.DataFrame(rows)


def make_figures(chains: pd.DataFrame, padding: pd.DataFrame, branches: pd.DataFrame) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(7.3, 4.8))
    ax1.plot(
        chains.m,
        chains.inverse_sqrt_phi_state,
        color="#b91c1c",
        linewidth=2.2,
        label=r"raw $\phi_{state}^{-1/2}=2^{m/2}$",
    )
    ax1.plot(
        chains.m,
        chains.traversal_steps,
        "o-",
        markersize=3,
        color="#1d4ed8",
        label="explicit traversal/output cost m",
    )
    ax1.set_yscale("log", base=2)
    ax1.set(xlabel="chain edges m", ylabel="scale (base-2 log axis)")
    ax1.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure01_unique_chain_counterexample.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(padding.r - 1, padding.padded_phi, "o-", label=r"raw $\phi_{state}$")
    ax.set_yscale("log", base=2)
    ax.set(xlabel="added serial edges r-1", ylabel=r"raw $\phi_{state}$")
    ax2 = ax.twinx()
    ax2.plot(padding.r - 1, np.ones(len(padding)), "k--", label="logical route problem unchanged")
    ax2.set(ylim=(0.8, 1.2), yticks=[1], yticklabels=["same"])
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure02_representation_padding.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.scatter(branches.K_over_M, branches.grover_big_O_query_cap, s=24, alpha=0.7, label="query cap")
    x = np.linspace(1, branches.K_over_M.max(), 200)
    ax.plot(x, np.sqrt(x), "k--", label=r"$\sqrt{K/M}$")
    ax.set(xlabel=r"$K/M$", ylabel="attribute-query complexity")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure03_parallel_branch_queries.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.8, 5.1))
    positive = branches[(branches.phi_path > 0) & (branches.phi_state > 0)]
    ax.scatter(positive.phi_path, positive.phi_state, c=positive.K, cmap="viridis", s=28)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.set(xlabel=r"candidate-path $\phi_{path}=M/K$", ylabel=r"raw edge-bit $\phi_{state}=M/2^{2K}$")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure04_path_vs_state_phi.png", dpi=180)
    plt.close(fig)


def main() -> None:
    argparse.ArgumentParser().parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    chains = raw_chain_rows()
    padding = padding_rows()
    branches = parallel_rows()
    atomic_write_csv(RESULT_ROOT / "raw_phi_counterexamples.csv", chains)
    atomic_write_csv(RESULT_ROOT / "representation_padding_validation.csv", padding)
    atomic_write_csv(RESULT_ROOT / "parallel_branch_validation.csv", branches)
    make_figures(chains, padding, branches)
    failures = int(
        (~padding.route_bijection).sum()
        + (~padding.feasibility_preserved).sum()
        + (~padding.optimum_preserved).sum()
        + (~padding.phi_factor_exact).sum()
        + (~branches.attribute_mapping_ok).sum()
    )
    write_json(
        RESULT_ROOT / "explicit_rcsp_validation_summary.json",
        {
            "unique_chain_rows": len(chains),
            "padding_rows": len(padding),
            "parallel_branch_rows": len(branches),
            "construction_failures": failures,
            "lower_bound_proof_source": "analytic reduction, not numerical validation",
        },
    )
    if failures:
        raise AssertionError(f"explicit RCSP validation recorded {failures} failures")


if __name__ == "__main__":
    main()
