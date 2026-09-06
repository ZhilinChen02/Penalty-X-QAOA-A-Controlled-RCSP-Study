#!/usr/bin/env python3
"""Run the offline finite-case and hybrid-step theorem validations."""

from __future__ import annotations

import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from qroute_dilution.io import atomic_write_csv, write_json
from qroute_dilution.theory.global_dilution_bound import (
    THEORY_RESULT_ROOT,
    finite_case_validation,
    hybrid_trace_examples,
    invalid_assumption_examples,
    query_lower_bound,
    verify_historical_hashes,
)


FIGURE_ROOT = THEORY_RESULT_ROOT / "figures"


def savefig(name: str) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURE_ROOT / name, dpi=180, bbox_inches="tight")
    plt.close()


def generate_figures(frame) -> None:
    # Figure 1: normalized success and the coarse envelope.
    grouped = frame.groupby(["q", "phi"], sort=True).average_success.agg(["median", "max"]).reset_index()
    plt.figure(figsize=(7, 5))
    for q, sub in grouped.groupby("q"):
        plt.scatter(np.full(len(sub), q), sub["max"] / sub.phi, alpha=0.45, color="#4C78A8")
    q_values = np.arange(4)
    plt.plot(q_values, (2 * q_values + 1) ** 2, "o--", color="#E45756", label="(2q+1)^2")
    plt.xlabel("Query count q")
    plt.ylabel("Maximum tested average success / phi")
    plt.legend()
    savefig("figure01_average_success_over_phi_vs_q.png")

    # Figure 2: all algorithms against their phase-sensitive bounds.
    plt.figure(figsize=(6, 6))
    plt.scatter(frame.phase_sensitive_bound, frame.average_success, s=6, alpha=0.22, color="#4C78A8")
    plt.plot([0, 1], [0, 1], "k--", lw=1)
    plt.xlabel("Phase-sensitive bound")
    plt.ylabel("Actual average success")
    savefig("figure02_actual_vs_phase_sensitive_bound.png")

    # Figure 4: theorem lower bound for a fixed target success.
    phi = 2.0 ** (-np.arange(1, 21, dtype=float))
    target = 0.5
    required = np.asarray([query_lower_bound(value, target) for value in phi])
    plt.figure(figsize=(6, 5))
    plt.loglog(phi ** -0.5, required, "o-", color="#59A14F")
    plt.xlabel("phi^(-1/2)")
    plt.ylabel("Required q lower bound (target success 0.5)")
    savefig("figure04_required_queries_vs_inverse_sqrt_phi.png")

    # Figure 5: explicit theorem-scope map.
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.axis("off")
    boxes = [
        (0.05, 0.72, "Full-space black-box\nglobal search", "COVERED", "#D7E9F7"),
        (0.55, 0.72, "Structure-injected\ninitialization or mixer", "OUTSIDE DIRECT THEOREM", "#FBE3D5"),
        (0.05, 0.22, "Rich structured\noracle", "OUTSIDE DIRECT THEOREM", "#FBE3D5"),
        (0.55, 0.22, "Instance-trained\nQAOA", "TOTAL-QUERY ACCOUNTING", "#FFF2CC"),
    ]
    for x, y, title, status, color in boxes:
        axis.text(
            x,
            y,
            f"{title}\n\n{status}",
            transform=axis.transAxes,
            ha="left",
            va="center",
            fontsize=11,
            bbox={"boxstyle": "round,pad=0.6", "facecolor": color, "edgecolor": "#444444"},
        )
    savefig("figure05_theorem_scope_diagram.png")


def main() -> None:
    THEORY_RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    historical = verify_historical_hashes()
    finite = finite_case_validation(
        failure_path=THEORY_RESULT_ROOT / "finite_case_counterexample_reproducer.json"
    )
    trace = hybrid_trace_examples()
    invalid = invalid_assumption_examples()
    atomic_write_csv(THEORY_RESULT_ROOT / "finite_case_summary.csv", finite)
    atomic_write_csv(THEORY_RESULT_ROOT / "hybrid_trace_examples.csv", trace)
    atomic_write_csv(THEORY_RESULT_ROOT / "invalid_assumption_examples.csv", invalid)
    generate_figures(finite)
    summary = {
        "schema_version": "theory_validation_v1.numerical_summary.v1",
        "parameter_cells": int(finite[["N", "M", "q", "ancilla_dim"]].drop_duplicates().shape[0]),
        "random_algorithms": int(len(finite)),
        "feasible_set_evaluations": int(finite.n_feasible_set_draws.sum()),
        "unique_feasible_sets_across_algorithm_rows": int(finite.n_unique_feasible_sets.sum()),
        "maximum_phase_bound_residual": float(finite.phase_bound_residual.max()),
        "maximum_phase_to_coarse_residual": float(finite.phase_to_coarse_residual.max()),
        "violations": int(finite.violation.astype(bool).sum()),
        "maximum_inclusion_marginal_error": float(finite.inclusion_marginal_error.max()),
        "hybrid_maximum_recursion_residual": float(trace.recursion_residual.max(skipna=True)),
        "hybrid_maximum_single_query_identity_residual": float(trace.single_query_identity_residual.abs().max(skipna=True)),
        "hybrid_maximum_final_projection_residual": float(trace.final_projection_residual.max(skipna=True)),
        "historical_hashes": historical,
        "formal_proof_assistant": "PENDING_LOCAL_AVAILABILITY_CHECK",
    }
    write_json(THEORY_RESULT_ROOT / "numerical_validation_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
