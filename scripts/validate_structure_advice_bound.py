#!/usr/bin/env python3
"""Finite posterior/advice stress test and Figures 5--7."""

from __future__ import annotations

import argparse
import hashlib
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, write_json
from qroute_dilution.theory.advice_query_tradeoff import required_advice_bits
from qroute_dilution.theory.global_dilution_bound import (
    algorithm_successes,
    phase_query_coefficient,
    random_query_algorithm,
)
from qroute_dilution.theory.posterior_structure_bound import (
    all_fixed_size_subsets,
    deterministic_channel,
    effective_structure_bits,
    effective_support,
    phase_sensitive_average_bound,
    posterior_summary,
)


RESULT_ROOT = PROJECT_ROOT / "results/theory_validation_v3"
FIGURE_ROOT = RESULT_ROOT / "figures"
MASTER_SEED = 0x53_7A_19_BD


def _seed(*parts: object) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def advice_channel(kind: str, subsets, N: int, alphabet_size: int, seed: int) -> np.ndarray:
    count = len(subsets)
    if kind == "constant_advice":
        return np.ones((count, 1), dtype=np.float64)
    if kind == "partition_advice":
        assignments = [sum((index + 1) * value for index, value in enumerate(subset)) % alphabet_size for subset in subsets]
        return deterministic_channel(assignments, alphabet_size)
    if kind == "noisy_bucket_advice":
        if alphabet_size == 1:
            return np.ones((count, 1), dtype=np.float64)
        base = advice_channel("partition_advice", subsets, N, alphabet_size, seed)
        return 0.8 * base + 0.2 * (1.0 - base) / (alphabet_size - 1)
    if kind == "one_marked_label_advice":
        assignments = [min(subset) % alphabet_size for subset in subsets]
        return deterministic_channel(assignments, alphabet_size)
    rng = np.random.default_rng(seed)
    if kind == "random_deterministic_map":
        return deterministic_channel(rng.integers(0, alphabet_size, size=count), alphabet_size)
    if kind == "random_stochastic_map":
        return rng.dirichlet(np.linspace(0.7, 1.3, alphabet_size), size=count)
    raise ValueError(f"unknown advice channel: {kind}")


def run_validation() -> pd.DataFrame:
    kinds = (
        "constant_advice",
        "partition_advice",
        "noisy_bucket_advice",
        "one_marked_label_advice",
        "random_deterministic_map",
        "random_stochastic_map",
    )
    rows: list[dict[str, object]] = []
    row_index = 0
    for N in (2, 4, 8):
        for M in range(1, N):
            subsets = all_fixed_size_subsets(N, M)
            prior = 1.0 / len(subsets)
            for q in range(4):
                for declared_alphabet in (1, 2, 4, 8):
                    for kind in kinds:
                        channel_seed = _seed(MASTER_SEED, N, M, q, declared_alphabet, kind)
                        channel = advice_channel(kind, subsets, N, declared_alphabet, channel_seed)
                        summary = posterior_summary(N, M, channel, subsets)
                        active = channel.mean(axis=0) > 1e-12
                        active_channel = channel[:, active]
                        actual = 0.0
                        coefficient_rows = []
                        algorithms = []
                        for advice_index in range(summary.support_size):
                            algorithm_seed = _seed(channel_seed, "algorithm", advice_index)
                            algorithm = random_query_algorithm(N, 1, q, seed=algorithm_seed)
                            algorithms.append(algorithm)
                            successes = algorithm_successes(algorithm, subsets)
                            actual += float(np.sum(prior * active_channel[:, advice_index] * successes))
                            coefficient_rows.append(
                                tuple(phase_query_coefficient(gamma) for gamma in algorithm.phases)
                            )
                        phase_bound = phase_sensitive_average_bound(summary, coefficient_rows)
                        coarse_bound = min(1.0, (2 * q + 1) ** 2 * summary.Lambda)
                        alphabet_bound = min(1.0, summary.support_size * M / N)
                        row = {
                            "row_id": row_index,
                            "N": N,
                            "M": M,
                            "phi": M / N,
                            "q": q,
                            "channel_kind": kind,
                            "declared_alphabet_size": declared_alphabet,
                            "supported_alphabet_size": summary.support_size,
                            "feasible_sets": len(subsets),
                            "subset_evaluations": len(subsets) * summary.support_size,
                            "Lambda": summary.Lambda,
                            "minimum_lambda_s": float(summary.lambdas.min()),
                            "maximum_lambda_s": float(summary.lambdas.max()),
                            "maximum_trace_error": float(np.max(np.abs(summary.trace_errors()))),
                            "actual_average_success": actual,
                            "phase_sensitive_bound": phase_bound,
                            "coarse_bound": coarse_bound,
                            "alphabet_lambda_bound": alphabet_bound,
                            "success_residual": actual - coarse_bound,
                            "phase_success_residual": actual - phase_bound,
                            "lambda_residual": summary.Lambda - alphabet_bound,
                            "channel_seed": channel_seed,
                        }
                        rows.append(row)
                        row_index += 1
                        if max(row["success_residual"], row["phase_success_residual"], row["lambda_residual"]) > 1e-10:
                            write_json(
                                RESULT_ROOT / "posterior_advice_violation_reproducer.json",
                                {
                                    "row": row,
                                    "subsets": subsets,
                                    "channel": channel.tolist(),
                                    "algorithms": [algorithm.minimal_reproducer() for algorithm in algorithms],
                                },
                            )
                            raise AssertionError("posterior/advice violation reproducer saved")
    return pd.DataFrame(rows)


def effective_examples() -> pd.DataFrame:
    N, M = 1024, 4
    phi = M / N
    rows = []
    for b_eff in np.linspace(0, np.log2(1 / phi), 33):
        Lambda = min(1.0, phi * 2**b_eff)
        rows.append(
            {
                "N": N,
                "M": M,
                "phi": phi,
                "Lambda": Lambda,
                "b_eff": effective_structure_bits(phi, Lambda),
                "K_eff": effective_support(M, Lambda),
                "identity_N_over_K_eff": N / effective_support(M, Lambda),
            }
        )
    return pd.DataFrame(rows)


def make_figures(validation: pd.DataFrame, examples: pd.DataFrame) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    q_values = np.arange(0, 41)
    phi, tau = 2.0**-30, 2 / 3
    bits = [required_advice_bits(phi, int(q), tau) for q in q_values]
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.step(q_values, bits, where="mid")
    ax.set(xlabel="membership-query cap q", ylabel="necessary classical advice bits b", title=r"$\phi=2^{-30},\ \tau=2/3$")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure05_advice_query_tradeoff.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    ax.plot(examples.b_eff, examples.K_eff, "o-")
    ax.set_yscale("log", base=2)
    ax.set(xlabel=r"effective structure bits $b_{eff}$", ylabel=r"effective support $K_{eff}$")
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure06_effective_bits_support.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5.1))
    ax.scatter(validation.coarse_bound, validation.actual_average_success, s=9, alpha=0.35)
    ax.plot([0, 1], [0, 1], "k--")
    ax.set(xlabel=r"$(2q+1)^2\Lambda$ with cap", ylabel="actual average success", xlim=(0, 1), ylim=(0, 1))
    fig.tight_layout()
    fig.savefig(FIGURE_ROOT / "figure07_posterior_actual_vs_bound.png", dpi=180)
    plt.close(fig)


def main() -> None:
    argparse.ArgumentParser().parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    validation = run_validation()
    examples = effective_examples()
    atomic_write_csv(RESULT_ROOT / "posterior_advice_validation.csv", validation)
    atomic_write_csv(RESULT_ROOT / "effective_structure_examples.csv", examples)
    make_figures(validation, examples)
    summary = {
        "parameter_rows": len(validation),
        "parameter_cells_N_M_q": int(validation[["N", "M", "q"]].drop_duplicates().shape[0]),
        "advice_channel_kinds": sorted(validation.channel_kind.unique()),
        "declared_alphabet_sizes": sorted(int(value) for value in validation.declared_alphabet_size.unique()),
        "subset_evaluations": int(validation.subset_evaluations.sum()),
        "maximum_success_residual": float(validation.success_residual.max()),
        "maximum_phase_success_residual": float(validation.phase_success_residual.max()),
        "maximum_lambda_residual": float(validation.lambda_residual.max()),
        "maximum_trace_error": float(validation.maximum_trace_error.max()),
        "violations": int(
            ((validation.success_residual > 1e-10) | (validation.phase_success_residual > 1e-10) | (validation.lambda_residual > 1e-10)).sum()
        ),
        "master_seed": MASTER_SEED,
    }
    write_json(RESULT_ROOT / "posterior_advice_validation_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
