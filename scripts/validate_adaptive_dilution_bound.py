#!/usr/bin/env python3
"""Deterministic finite-case audit of adaptive hard-cap query bounds."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, write_json
from qroute_dilution.theory.adaptive_query_bound import (
    adaptive_phase_bound,
    random_adaptive_protocol,
    protocol_identifier,
)
from qroute_dilution.theory.deferred_measurement import (
    coherent_hybrid_trace,
    simulate_direct,
    simulate_purified_padded,
    simulate_purified,
)


RESULT_ROOT = PROJECT_ROOT / "results/theory_validation_v2"
FIGURE_ROOT = RESULT_ROOT / "figures"


def subsets(N: int, M: int) -> tuple[tuple[int, ...], ...]:
    return tuple(itertools.combinations(range(N), M))


def run_validation(protocols_per_model: int = 2) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    finite_rows: list[dict[str, object]] = []
    equivalence_rows: list[dict[str, object]] = []
    trace_rows: list[dict[str, object]] = []
    master_seed = 0xA4D4_7E52
    protocol_index = 0
    for N in (2, 4, 8):
        for M in range(1, N):
            feasible_sets = subsets(N, M)
            for q in range(4):
                for ancilla_dim in (1, 2):
                    for oracle_model in ("phase_flip", "membership_bit", "branch_phase"):
                        for variant in range(protocols_per_model):
                            seed = master_seed + protocol_index * 104729
                            protocol_index += 1
                            protocol = random_adaptive_protocol(
                                N,
                                q,
                                ancilla_dim,
                                oracle_model,
                                seed=seed,
                                measure_between_slots=True,
                                early_stop=bool(variant % 2),
                                randomized_control=bool((variant + q) % 2),
                            )
                            successes: list[float] = []
                            coherent_successes: list[float] = []
                            padded_successes: list[float] = []
                            max_equivalence = 0.0
                            branch_counts: set[int] = set()
                            for feasible_set in feasible_sets:
                                direct = simulate_direct(protocol, feasible_set)
                                coherent = simulate_purified(protocol, feasible_set)
                                padded = simulate_purified_padded(protocol, feasible_set)
                                successes.append(direct.success)
                                coherent_successes.append(coherent.success)
                                padded_successes.append(padded.success)
                                max_equivalence = max(
                                    max_equivalence,
                                    abs(direct.success - coherent.success),
                                    float(
                                        np.max(
                                            np.abs(
                                                direct.output_distribution
                                                - coherent.output_distribution
                                            )
                                        )
                                    ),
                                    float(
                                        np.max(
                                            np.abs(
                                                direct.output_distribution
                                                - padded.output_distribution
                                            )
                                        )
                                    ),
                                )
                                if any(count != q for count in padded.query_counts):
                                    raise AssertionError("padding did not use every hard-cap slot")
                                branch_counts.update(direct.query_counts)
                            average = float(np.mean(successes))
                            coherent_average = float(np.mean(coherent_successes))
                            padded_average = float(np.mean(padded_successes))
                            phase_bound = adaptive_phase_bound(
                                N, M, protocol.phase_coefficients()
                            )
                            coarse = min(1.0, (2 * q + 1) ** 2 * M / N)
                            residual = average - coarse
                            phase_residual = average - phase_bound
                            if residual > 1e-10 or phase_residual > 1e-10:
                                reproducer = {
                                    "protocol_id": protocol_identifier(protocol),
                                    "N": N,
                                    "M": M,
                                    "q": q,
                                    "seed": seed,
                                    "oracle_model": oracle_model,
                                    "successes": successes,
                                    "phase_coefficients": protocol.phase_coefficients(),
                                }
                                path = RESULT_ROOT / "adaptive_violation_reproducer.json"
                                write_json(path, reproducer)
                                raise AssertionError(f"adaptive bound violation saved to {path}")
                            if max_equivalence > 1e-10:
                                raise AssertionError("direct/deferred simulation mismatch")
                            row = {
                                "protocol_id": protocol_identifier(protocol),
                                "N": N,
                                "M": M,
                                "phi": M / N,
                                "q_hard_cap": q,
                                "ancilla_dim": ancilla_dim,
                                "oracle_model": oracle_model,
                                "intermediate_measurement": q >= 2,
                                "classical_feed_forward": q >= 2,
                                "early_stopping": protocol.early_stop,
                                "randomized_control": protocol.randomized_control,
                                "feasible_sets": len(feasible_sets),
                                "subset_evaluations": len(feasible_sets),
                                "average_success": average,
                                "hard_cap_bound": coarse,
                                "phase_sensitive_bound": phase_bound,
                                "maximum_pointwise_success": max(successes),
                                "minimum_pointwise_success": min(successes),
                                "maximum_bound_residual": residual,
                                "maximum_phase_residual": phase_residual,
                                "query_count_by_branch": json.dumps(sorted(branch_counts)),
                            }
                            finite_rows.append(row)
                            equivalence_rows.append(
                                {
                                    "protocol_id": row["protocol_id"],
                                    "N": N,
                                    "M": M,
                                    "q_hard_cap": q,
                                    "oracle_model": oracle_model,
                                    "direct_average_success": average,
                                    "coherent_average_success": coherent_average,
                                    "padded_average_success": padded_average,
                                    "maximum_output_distribution_difference": max_equivalence,
                                    "tolerance": 1e-10,
                                    "pass": max_equivalence <= 1e-10,
                                }
                            )
                            if N == 4 and M == 1 and q == 3 and variant == 0:
                                for feasible_set in feasible_sets[:2]:
                                    for trace in coherent_hybrid_trace(protocol, feasible_set):
                                        trace_rows.append(
                                            {
                                                "protocol_id": row["protocol_id"],
                                                "feasible_set": json.dumps(feasible_set),
                                                **trace,
                                            }
                                        )
    return pd.DataFrame(finite_rows), pd.DataFrame(equivalence_rows), pd.DataFrame(trace_rows)


def make_figures(finite: pd.DataFrame, equivalence: pd.DataFrame) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    scaled = finite.assign(
        success_over_phi=finite.average_success / finite.phi
    )
    grouped = scaled.groupby(["q_hard_cap", "oracle_model"], as_index=False).agg(
        success_over_phi=("success_over_phi", "mean"),
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    for model, frame in grouped.groupby("oracle_model"):
        ax.plot(frame.q_hard_cap, frame.success_over_phi, "o-", label=model)
    q_values = np.arange(4)
    ax.plot(q_values, (2 * q_values + 1) ** 2, "k--", label=r"$(2q+1)^2$")
    ax.set(xlabel="hard query cap q", ylabel=r"mean adaptive success / mean $\phi$")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure01_adaptive_success_over_phi.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.4, 5.1))
    ax.scatter(
        equivalence.direct_average_success,
        equivalence.coherent_average_success,
        s=12,
        alpha=0.55,
    )
    ax.plot([0, 1], [0, 1], "k--")
    ax.set(
        xlabel="direct measurement/feed-forward success",
        ylabel="coherent deferred-measurement success",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure02_direct_vs_deferred.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.4, 5.1))
    ax.scatter(finite.hard_cap_bound, finite.average_success, s=12, alpha=0.55)
    ax.plot([0, 1], [0, 1], "k--")
    ax.set(
        xlabel="coarse hard-cap theorem bound",
        ylabel="adaptive average success",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure03_adaptive_success_vs_bound.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocols-per-model", type=int, default=2)
    args = parser.parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    finite, equivalence, traces = run_validation(args.protocols_per_model)
    atomic_write_csv(RESULT_ROOT / "adaptive_finite_case_summary.csv", finite)
    atomic_write_csv(RESULT_ROOT / "adaptive_equivalence.csv", equivalence)
    atomic_write_csv(RESULT_ROOT / "adaptive_hybrid_traces.csv", traces)
    make_figures(finite, equivalence)
    write_json(
        RESULT_ROOT / "adaptive_validation_summary.json",
        {
            "protocols": int(len(finite)),
            "subset_evaluations": int(finite.subset_evaluations.sum()),
            "maximum_coarse_residual": float(finite.maximum_bound_residual.max()),
            "maximum_phase_residual": float(finite.maximum_phase_residual.max()),
            "maximum_equivalence_difference": float(
                equivalence.maximum_output_distribution_difference.max()
            ),
            "maximum_hybrid_recursion_residual": float(traces.recursion_residual.max()),
            "violations": int((finite.maximum_bound_residual > 1e-10).sum()),
            "master_seed": 0xA4D4_7E52,
        },
    )


if __name__ == "__main__":
    main()
