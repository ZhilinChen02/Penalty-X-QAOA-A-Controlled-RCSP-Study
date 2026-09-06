#!/usr/bin/env python3
"""Explicit stage runner for the immutable Phase 1.1 diagnostic."""

from __future__ import annotations

import argparse
import json
import platform
import socket
import sys
import time

import numpy as np
import scipy

from qroute_dilution.io import write_json
from qroute_dilution.phase1_1_analysis import analyze_phase1_1
from qroute_dilution.phase1_1_diagnostic import (
    RESULT_ROOT,
    freeze_diagnostic_identity,
    run_budget_scaling,
    run_continuation,
    run_energy_separation,
    run_nested_identity,
    run_objective_decomposition,
    run_optimizer_control,
    run_response_slices,
    verify_immutable_evidence,
)


def _record_stage(stage: str, elapsed: float, details: dict) -> None:
    path = RESULT_ROOT / "execution_provenance.json"
    if path.exists():
        provenance = json.loads(path.read_text(encoding="utf-8"))
    else:
        provenance = {
            "host": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": sys.version.replace("\n", " "),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "implementation_device": "CPU NumPy exact statevector",
            "stages": {},
        }
    provenance["stages"][stage] = {"wall_time_s": elapsed, **details}
    provenance["total_recorded_wall_time_s"] = sum(
        item["wall_time_s"] for item in provenance["stages"].values()
    )
    write_json(path, provenance)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "freeze",
            "nested",
            "continuation",
            "budget",
            "control",
            "separation",
            "decomposition",
            "slices",
            "analyze",
            "verify-hashes",
        ],
    )
    parser.add_argument("--pytest-result", default="not_recorded")
    parser.add_argument(
        "--attribution",
        choices=[
            "OPTIMIZER_LIMITATION",
            "OBJECTIVE_FEASIBILITY_MISALIGNMENT",
            "GENUINE_DEPTH_RESPONSE",
            "MIXED",
        ],
    )
    args = parser.parse_args()
    started = time.perf_counter()
    if args.stage == "freeze":
        value = freeze_diagnostic_identity()
        details = {"immutable_file_count": value["immutable_file_count"]}
    elif args.stage == "nested":
        nested, gaps = run_nested_identity()
        details = {
            "rows": len(nested),
            "pass_count": int(nested.identity_pass.sum()),
            "gap_rows": len(gaps),
        }
    elif args.stage == "continuation":
        frame = run_continuation()
        details = {"rows": len(frame)}
    elif args.stage == "budget":
        frame = run_budget_scaling()
        details = {"rows": len(frame)}
    elif args.stage == "control":
        frame = run_optimizer_control()
        details = {"rows": len(frame)}
    elif args.stage == "separation":
        frame = run_energy_separation()
        details = {
            "rows": len(frame),
            "separated": int(frame.complete_energy_separation.sum()),
        }
    elif args.stage == "decomposition":
        frame = run_objective_decomposition()
        details = {"rows": len(frame)}
    elif args.stage == "slices":
        frame = run_response_slices()
        details = {"rows": len(frame), "tasks": int(frame.task_id.nunique())}
    elif args.stage == "analyze":
        if args.attribution is None:
            parser.error("--attribution is required for analyze after reviewing diagnostics")
        summary = analyze_phase1_1(
            pytest_result=args.pytest_result, attribution=args.attribution
        )
        details = {"status": summary["diagnostic_status"]}
    else:
        files = verify_immutable_evidence()
        details = {"verified_files": len(files)}
    elapsed = time.perf_counter() - started
    _record_stage(args.stage, elapsed, details)
    print({"stage": args.stage, "wall_time_s": elapsed, **details})


if __name__ == "__main__":
    main()
