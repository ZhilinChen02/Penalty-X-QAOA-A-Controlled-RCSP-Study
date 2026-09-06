#!/usr/bin/env python3
"""Stage-gated runner for the immutable Phase 1.2 objective diagnostic."""

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
from qroute_dilution.phase1_2_analysis import (
    RECOMMENDATIONS,
    VERDICTS,
    analyze_phase1_2,
)
from qroute_dilution.phase1_2_experiment import (
    RESULT_ROOT,
    freeze_execution_identity,
    reuse_o0_rows,
    run_full_matrix,
    run_preflight,
    run_theoretical_audits,
    verify_historical_immutability,
)


def _record(stage: str, elapsed: float, details: dict) -> None:
    path = RESULT_ROOT / "execution_provenance.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {
            "host": socket.gethostname(),
            "platform": platform.platform(),
            "python_version": sys.version.replace("\n", " "),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "implementation_device": "CPU NumPy exact statevector",
            "stages": {},
        }
    payload["stages"][stage] = {"wall_time_s": elapsed, **details}
    payload["total_recorded_wall_time_s"] = sum(
        item["wall_time_s"] for item in payload["stages"].values()
    )
    write_json(path, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=["freeze", "audit", "reuse-o0", "preflight", "full", "analyze", "verify-hashes"],
    )
    parser.add_argument("--verdict", choices=sorted(VERDICTS))
    parser.add_argument("--recommendation", choices=sorted(RECOMMENDATIONS))
    parser.add_argument("--pytest-result", default="not_recorded")
    args = parser.parse_args()
    started = time.perf_counter()
    if args.stage == "freeze":
        identity = freeze_execution_identity()
        details = {
            "historical_file_count": identity["historical_file_count"],
            "frozen_initialization_count": len(identity["frozen_initializations"]),
        }
    elif args.stage == "audit":
        frame = run_theoretical_audits()
        details = {
            "rows": len(frame),
            "basis_contract_pass": int(frame.basis_penalty_contract_pass.sum()),
            "random_bound_pass": int(frame.random_state_penalty_bound_pass.sum()),
        }
    elif args.stage == "reuse-o0":
        frame = reuse_o0_rows()
        details = {"total_rows": len(frame), "O0_rows": int((frame.objective_id == "O0").sum())}
    elif args.stage == "preflight":
        frame = run_preflight()
        details = {"rows": len(frame), "status": "PASSED"}
    elif args.stage == "full":
        frame = run_full_matrix()
        details = {
            "rows": len(frame),
            "tasks": int(frame.task_id.nunique()),
            "successful": int((frame.execution_status == "SUCCESS").sum()),
        }
    elif args.stage == "analyze":
        if args.verdict is None or args.recommendation is None:
            parser.error("--verdict and --recommendation are required after inspecting results")
        summary = analyze_phase1_2(
            verdict=args.verdict,
            recommendation=args.recommendation,
            pytest_result=args.pytest_result,
        )
        details = {
            "status": summary["status"],
            "scientific_verdict": summary["scientific_verdict"],
            "next_recommendation": summary["next_recommendation"],
        }
    else:
        files = verify_historical_immutability()
        details = {"verified_files": len(files)}
    elapsed = time.perf_counter() - started
    _record(args.stage, elapsed, details)
    print({"stage": args.stage, "wall_time_s": elapsed, **details})


if __name__ == "__main__":
    main()
