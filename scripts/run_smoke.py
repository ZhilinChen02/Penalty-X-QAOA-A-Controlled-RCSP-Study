#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qroute_dilution.pipeline import run_phase0_workflow, run_phase1_workflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/smoke.yaml")
    args = parser.parse_args()
    characterization, _ = run_phase0_workflow(args.config)
    results, summary = run_phase1_workflow(args.config)
    print(
        f"smoke complete: tasks={len(characterization)}, rows={len(results)}, "
        f"failures={summary['failure_count']}"
    )


if __name__ == "__main__":
    main()
