#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qroute_dilution.phase05 import run_phase05


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase0_v2_dilution_stress.yaml")
    args = parser.parse_args()
    summary = run_phase05(args.config)
    print(
        f"Phase 0.5 complete: verdict={summary['audit_verdict']}; "
        f"v2_tasks={summary['task_count']}; "
        f"pilot_runs={summary['pilot_projection']['phase1_penalty_x_run_count']}. "
        "No Phase 1 run was executed."
    )


if __name__ == "__main__":
    main()
