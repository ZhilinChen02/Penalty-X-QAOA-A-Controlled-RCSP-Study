#!/usr/bin/env python3
"""Explicit stage runner for the frozen Phase 1 pilot."""

from __future__ import annotations

import argparse

from qroute_dilution.phase1_analysis import analyze_pilot
from qroute_dilution.phase1_pilot import (
    freeze_execution_identity,
    run_execution_preflight,
    run_frozen_pilot,
    verify_global_normalization,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage", choices=["freeze", "normalization", "preflight", "execute", "analyze"]
    )
    parser.add_argument("--pytest-result", default="not_recorded")
    args = parser.parse_args()
    if args.stage == "freeze":
        identity = freeze_execution_identity()
        print(
            f"tasks={identity['task_count']} runs={identity['planned_optimized_run_count']} "
            f"manifest_sha256={identity['manifest_sha256']} config_sha256={identity['config_sha256']}"
        )
    elif args.stage == "normalization":
        frame = verify_global_normalization()
        print(
            f"normalization_pass={len(frame)}/{len(frame)} "
            f"span=[{frame.normalized_energy_span.min():.9g}, {frame.normalized_energy_span.max():.9g}]"
        )
    elif args.stage == "preflight":
        print(run_execution_preflight())
    elif args.stage == "execute":
        frame, execution = run_frozen_pilot()
        print(
            f"rows={len(frame)} optimized={execution['optimized_rows']} "
            f"wall_time_s={execution['new_execution_wall_time_s']:.3f}"
        )
    else:
        print(analyze_pilot(pytest_result=args.pytest_result))


if __name__ == "__main__":
    main()
