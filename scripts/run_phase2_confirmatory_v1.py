#!/usr/bin/env python3
"""Stage-gated runner for preregistered held-out Phase 2."""

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
from qroute_dilution.phase2_analysis import RECOMMENDATIONS, VERDICTS, analyze_phase2
from qroute_dilution.phase2_confirmatory import (
    RESULT_ROOT,
    build_phase2_manifest,
    freeze_execution_identity,
    run_discovery_only_preflight,
    run_energy_separation_audit,
    run_formal_p2_preparation,
    run_formal_p3_comparison,
    run_power_preflight,
    verify_predecessor_immutability,
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
        choices=[
            "manifest",
            "power",
            "preflight",
            "freeze",
            "audit",
            "p2",
            "p3",
            "analyze",
            "verify-hashes",
        ],
    )
    parser.add_argument("--verdict", choices=sorted(VERDICTS))
    parser.add_argument("--recommendation", choices=sorted(RECOMMENDATIONS))
    parser.add_argument("--pytest-result", default="not_recorded")
    args = parser.parse_args()
    started = time.perf_counter()
    if args.stage == "manifest":
        manifest = build_phase2_manifest()
        details = {
            "tasks": manifest["task_count"],
            "base_graphs": manifest["base_graph_count"],
            "graph_overlap": manifest["phase2_base_graph_overlap_with_discovery"],
            "task_overlap": manifest["phase2_task_overlap_with_discovery"],
        }
    elif args.stage == "power":
        power = run_power_preflight()
        details = {
            "power_gate": power["power_gate"],
            "H1_power": power["projected_Holm_power"]["H1"],
            "H2_power": power["projected_Holm_power"]["H2"],
        }
    elif args.stage == "preflight":
        summary = run_discovery_only_preflight()
        details = {"status": summary["status"], "p2_rows": 6, "p3_rows": 6}
    elif args.stage == "freeze":
        snapshot = freeze_execution_identity()
        details = {
            "tasks": snapshot["task_count"],
            "base_graphs": snapshot["base_graph_count"],
            "historical_file_count": snapshot["historical_file_count"],
            "power_gate": snapshot["power_gate"],
        }
    elif args.stage == "audit":
        frame = run_energy_separation_audit()
        details = {
            "rows": len(frame),
            "strict_separation": int(frame.strict_energy_class_separation.sum()),
        }
    elif args.stage == "p2":
        frame = run_formal_p2_preparation()
        details = {
            "rows": len(frame),
            "selected": int(frame.selected_for_p3.sum()),
            "successful_or_zero": int(
                frame.execution_status.isin(["SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT"]).sum()
            ),
        }
    elif args.stage == "p3":
        frame = run_formal_p3_comparison()
        details = {
            "rows": len(frame),
            "paired_eligible_rows": int(frame.paired_analysis_eligible.sum()),
            "successful_or_zero": int(
                frame.execution_status.isin(["SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT"]).sum()
            ),
        }
    elif args.stage == "analyze":
        if args.verdict is None or args.recommendation is None:
            parser.error("--verdict and --recommendation are required after result inspection")
        summary = analyze_phase2(
            verdict=args.verdict,
            recommendation=args.recommendation,
            pytest_result=args.pytest_result,
        )
        details = {
            "status": summary["phase2_status"],
            "H1_pass": summary["confirmatory_inference"]["H1"]["pass"],
            "H2_pass": summary["confirmatory_inference"]["H2"]["pass"],
            "verdict": summary["scientific_verdict"],
        }
    else:
        hashes = verify_predecessor_immutability()
        details = {"verified_files": len(hashes)}
    elapsed = time.perf_counter() - started
    _record(args.stage, elapsed, details)
    print({"stage": args.stage, "wall_time_s": elapsed, **details})


if __name__ == "__main__":
    main()
