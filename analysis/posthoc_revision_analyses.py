"""Post-hoc analyses added in the first revision of the manuscript (2026).

These analyses were not preregistered. They only re-read frozen result tables
that are already in this repository; no circuit is re-optimized.

1. Sensitivity of the frozen H2 non-inferiority test to its margin.
   The preregistered exact cluster sign-flip test (all 2^15 sign patterns of the
   15 held-out graph contrasts) is re-run with the margin changed, and the H2
   p-value is Holm-adjusted together with H1, as in the preregistration.
2. Mean scaling exponent eta per problem size and training loss.
3. Discovery-set gap closure of the expected-penalty loss (O1) and of CVaR (O3).

Usage, from the repository root:
    python analysis/posthoc_revision_analyses.py .
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def exact_sign_flip_p(values: np.ndarray) -> tuple[int, float]:
    """One-sided exact sign-flip p-value: share of sign patterns with mean >= observed."""
    signs = np.array(list(itertools.product([1.0, -1.0], repeat=len(values))))
    observed = values.mean()
    means = (signs * values).mean(axis=1)
    count = int((means >= observed - 1e-15).sum())
    return count, count / len(signs)


def holm(p_h1: float, p_h2: float) -> dict[str, float]:
    ordered = sorted([("H1", p_h1), ("H2", p_h2)], key=lambda item: item[1])
    adjusted, running = {}, 0.0
    for rank, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - rank) * p))
        adjusted[name] = running
    return adjusted


def margin_sensitivity(root: Path) -> None:
    frame = pd.read_csv(root / "results/phase2_confirmatory_v1/graph_level_contrasts.csv")
    d1 = frame["Delta1_CVAR_MEAN"].to_numpy()
    d2 = frame["Delta2_CVAR_CAPACITY"].to_numpy()
    print("== 1. H2 margin sensitivity (held-out, graph level) ==")
    print(f"graphs: {len(d1)}")
    print(f"H1 mean {d1.mean():.4f}, positive on {int((d1 > 0).sum())} graphs")
    print(f"H2 mean {d2.mean():.4f}, range {d2.min():.3f} to {d2.max():.3f}, "
          f"{int((d2 < -0.10).sum())} graph(s) below -0.10")
    count1, p1 = exact_sign_flip_p(d1)
    print(f"H1 raw sign-flip count {count1}/32768, p = {p1:.6g}")
    print("margin  raw count  raw p        Holm-adjusted p (H2)")
    for margin in (0.10, 0.07, 0.05, 0.04, 0.03):
        count2, p2 = exact_sign_flip_p(d2 + margin)
        print(f"{margin:5.2f}  {count2:9d}  {p2:<11.6g}  {holm(p1, p2)['H2']:.6g}")
    print(f"10^-0.10 = {10 ** -0.10:.4f}; 10^-0.04 = {10 ** -0.04:.4f}")


def eta_means(root: Path) -> None:
    frame = pd.read_csv(root / "results/phase3_scaling_v1/base_graph_exponents.csv")
    table = frame.pivot_table(index="size_m", columns="objective", values="eta", aggfunc="mean")
    table["n_graphs"] = frame[frame.objective == "O0"].groupby("size_m").size()
    print("\n== 2. Mean eta per size and loss (lower is better) ==")
    print(table.round(4).to_string())
    print("any resource-censored row:", bool(frame.resource_censored.any()))


def gap_closure(root: Path) -> None:
    gap = pd.read_csv(root / "results/phase1_2_objective_alignment/capacity_gap.csv")
    stable = gap[gap["capacity_gap_mean"] > 1e-6]
    print("\n== 3. Discovery gap closure of the O2-O0 gap ==")
    print(f"tasks: {len(gap)}, with a numerically stable gap (> 1e-6 decades): {len(stable)}")
    for label, column in (("O1 expected penalty", "penalty_gap_closure_fraction"),
                          ("O3 CVaR-0.10", "cvar_gap_closure_fraction")):
        values = stable[column].dropna()
        print(f"{label}: median closure {values.median():.4f} over {len(values)} tasks")
    print(f"median O2-O3 residual: {gap['capacity_gap_cvar'].median():.5f} decades")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    repository = Path(sys.argv[1])
    margin_sensitivity(repository)
    eta_means(repository)
    gap_closure(repository)
