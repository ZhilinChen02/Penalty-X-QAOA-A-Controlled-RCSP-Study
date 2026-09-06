#!/usr/bin/env python3
"""Run the offline Grover achievability/formula validation."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from qroute_dilution.io import atomic_write_csv, write_json
from qroute_dilution.theory.global_dilution_bound import (
    THEORY_RESULT_ROOT,
    grover_validation,
)


def main() -> None:
    frame = grover_validation()
    path = THEORY_RESULT_ROOT / "grover_validation.csv"
    atomic_write_csv(path, frame)
    dilute = frame[(frame.phi <= 0.125) & ((2 * frame.q + 1) ** 2 * frame.phi <= 0.35)]
    plt.figure(figsize=(6, 5))
    plt.scatter(
        dilute.leading_dilute_term,
        dilute.grover_success_numerical,
        s=24,
        alpha=0.7,
        color="#E45756",
    )
    upper = max(float(dilute.leading_dilute_term.max()), float(dilute.grover_success_numerical.max()))
    plt.plot([0, upper], [0, upper], "k--", lw=1)
    plt.xlabel("(2q+1)^2 phi")
    plt.ylabel("Grover success")
    plt.tight_layout()
    figure_root = THEORY_RESULT_ROOT / "figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    plt.savefig(figure_root / "figure03_grover_vs_leading_dilute_term.png", dpi=180, bbox_inches="tight")
    plt.close()
    positive = dilute.leading_dilute_term > 0
    relative = (
        (dilute.loc[positive, "grover_success_numerical"] - dilute.loc[positive, "leading_dilute_term"])
        / dilute.loc[positive, "leading_dilute_term"]
    ).abs()
    summary = {
        "schema_version": "theory_validation_v1.grover_summary.v1",
        "rows": len(frame),
        "maximum_formula_absolute_error": float(frame.formula_absolute_error.max()),
        "dilute_rows": len(dilute),
        "maximum_dilute_relative_leading_term_error": float(relative.max()),
        "exact_formula_universal_upper_bound_claimed": False,
        "achievability_only": True,
    }
    write_json(THEORY_RESULT_ROOT / "grover_validation_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
