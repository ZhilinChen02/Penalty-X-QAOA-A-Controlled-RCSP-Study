#!/usr/bin/env python3
from __future__ import annotations

from qroute_dilution.hamiltonian_audit import run_phase06


def main() -> None:
    summary = run_phase06()
    print(
        f"Phase 0.6 complete: verdict={summary['verdict']}; "
        f"current_exact={summary['current_exact_optimal']}/{summary['task_count']}; "
        f"controlled_exact={summary['controlled_exact_optimal']}/{summary['task_count']}. "
        "Phase 1 executed: false."
    )


if __name__ == "__main__":
    main()
