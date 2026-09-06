#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qroute_dilution.io import PROJECT_ROOT, write_json
from qroute_dilution.pipeline import build_resource_projection, run_phase0_workflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase0_v1.yaml")
    args = parser.parse_args()
    characterization, summary = run_phase0_workflow(args.config)
    projection = build_resource_projection(
        characterization,
        args.config,
        PROJECT_ROOT / "results" / "smoke" / "master_results.csv",
    )
    write_json(PROJECT_ROOT / "results" / "phase0" / "resource_projection.json", projection)
    summary["resource_projection"] = projection
    write_json(PROJECT_ROOT / "results" / "phase0" / "summary.json", summary)
    print(
        f"Phase 0 complete: tasks={len(characterization)}; "
        f"projected Phase 1 runs={projection['phase1_penalty_x_run_count']}. "
        "No full Phase 1 runs were started."
    )


if __name__ == "__main__":
    main()
