#!/usr/bin/env python3
"""Resumable command-line entry point for isolated reviewer experiments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qroute_dilution.io import write_json
from qroute_dilution.reviewer_robustness.alpha_sensitivity import aggregate_a2, run_a2
from qroute_dilution.reviewer_robustness.audit import (
    CANONICAL_HASHES_BEFORE,
    run_r0_audit,
)
from qroute_dilution.reviewer_robustness.classical_rcsp import aggregate_b2, run_b2
from qroute_dilution.reviewer_robustness.common import (
    REVIEW_ROOT,
    verify_canonical_hash_snapshot,
)
from qroute_dilution.reviewer_robustness.depth_budget import (
    aggregate_b1,
    run_b1,
    validate_single_trajectory_checkpoints,
)
from qroute_dilution.reviewer_robustness.finite_shot import (
    aggregate_alpha_shot_estimators,
    aggregate_finite_shot_training,
    audit_existing_endpoint_study,
    run_alpha_shot_estimators,
    run_finite_shot_training,
)
from qroute_dilution.reviewer_robustness.manifests import (
    MANIFEST_PATHS,
    build_manifests,
    record_code_amendment,
    verify_execution_code_fingerprint,
)
from qroute_dilution.reviewer_robustness.optimizer_robustness import (
    aggregate_a1,
    run_a1,
)
from qroute_dilution.reviewer_robustness.registry import rebuild_registry
from qroute_dilution.reviewer_robustness.statistical_audit import (
    run_statistical_audit,
)
from qroute_dilution.reviewer_robustness.synthesis import generate_synthesis


def integrity_gate() -> dict:
    if not CANONICAL_HASHES_BEFORE.exists():
        raise RuntimeError("R0 canonical hash snapshot must be created first")
    result = verify_canonical_hash_snapshot(CANONICAL_HASHES_BEFORE)
    if not result["pass"]:
        raise RuntimeError(
            f"canonical science changed; STOP: {result['changed_files']}"
        )
    return result


def require_manifests() -> None:
    missing = [str(path) for path in MANIFEST_PATHS.values() if not path.exists()]
    if missing:
        raise RuntimeError(f"freeze manifests before execution: {missing}")
    code_gate = verify_execution_code_fingerprint()
    if not code_gate["pass"]:
        raise RuntimeError(
            "reviewer execution code differs from frozen/amended fingerprint; "
            "record a code-amendment before formal execution"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "r0",
            "freeze",
            "code-amendment",
            "integrity",
            "registry",
            "b1-gate",
            "b1-smoke",
            "b1-run",
            "b1-aggregate",
            "endpoint-audit",
            "a3-estimator-smoke",
            "a3-estimator-run",
            "a3-estimator-aggregate",
            "a3-training-smoke",
            "a3-training-run",
            "a3-training-aggregate",
            "a1-smoke",
            "a1-run24",
            "a1-run-full",
            "a1-aggregate",
            "a2-smoke",
            "a2-discovery24",
            "a2-discovery-full",
            "a2-heldout-initial",
            "a2-aggregate",
            "b2-smoke",
            "b2-run",
            "b2-aggregate",
            "statistical-audit",
            "synthesis",
        ],
    )
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--reason", type=str, default=None)
    args = parser.parse_args()
    command = args.command
    result = None
    if command == "r0":
        result = run_r0_audit()
    elif command == "freeze":
        integrity_gate()
        result = {key: value["status"] for key, value in build_manifests().items()}
    elif command == "code-amendment":
        integrity_gate()
        require_reason = args.reason or (
            "Pre-formal smoke fix: deterministically regenerate absent portable V2 "
            "task payloads in memory and verify frozen task identity."
        )
        result = record_code_amendment(require_reason)
    elif command == "integrity":
        result = integrity_gate()
    elif command == "registry":
        result = {"registry_rows": len(rebuild_registry())}
    elif command == "statistical-audit":
        integrity_gate()
        result = {"rows": len(run_statistical_audit())}
    elif command == "synthesis":
        integrity_gate()
        result = generate_synthesis()
    else:
        integrity_gate()
        require_manifests()
        if command == "b1-gate":
            manifest = json.loads(MANIFEST_PATHS["depth_budget"].read_text())
            task = min(manifest["tasks"], key=lambda row: (row["m"], row["task_id"]))
            result = validate_single_trajectory_checkpoints(task)
            write_json(REVIEW_ROOT / "B1_depth_budget" / "checkpoint_semantics_gate.json", result)
            if not result["pass"]:
                raise RuntimeError("single-trajectory checkpoint gate failed")
        elif command == "b1-smoke":
            result = run_b1(smoke=True, max_workers=args.workers)
        elif command == "b1-run":
            gate = REVIEW_ROOT / "B1_depth_budget" / "checkpoint_semantics_gate.json"
            if not gate.exists() or not json.loads(gate.read_text())["pass"]:
                raise RuntimeError("run and pass b1-gate before formal B1")
            result = run_b1(max_workers=args.workers)
        elif command == "b1-aggregate":
            result = aggregate_b1()
        elif command == "endpoint-audit":
            result = audit_existing_endpoint_study()
        elif command == "a3-estimator-smoke":
            result = run_alpha_shot_estimators(smoke=True, max_workers=args.workers)
        elif command == "a3-estimator-run":
            result = run_alpha_shot_estimators(max_workers=args.workers)
        elif command == "a3-estimator-aggregate":
            result = aggregate_alpha_shot_estimators()
        elif command == "a3-training-smoke":
            result = run_finite_shot_training(smoke=True, max_workers=args.workers)
        elif command == "a3-training-run":
            result = run_finite_shot_training(max_workers=args.workers)
        elif command == "a3-training-aggregate":
            result = aggregate_finite_shot_training()
        elif command == "a1-smoke":
            result = run_a1(scope="initial24", smoke=True, max_workers=args.workers)
        elif command == "a1-run24":
            result = run_a1(scope="initial24", max_workers=args.workers)
        elif command == "a1-run-full":
            result = run_a1(scope="full", max_workers=args.workers)
        elif command == "a1-aggregate":
            result = aggregate_a1()
        elif command == "a2-smoke":
            result = run_a2(split="discovery", scope="initial24", smoke=True, max_workers=args.workers)
        elif command == "a2-discovery24":
            result = run_a2(split="discovery", scope="initial24", max_workers=args.workers)
        elif command == "a2-discovery-full":
            result = run_a2(split="discovery", scope="full", max_workers=args.workers)
        elif command == "a2-heldout-initial":
            result = run_a2(split="heldout", scope="initial", max_workers=args.workers)
        elif command == "a2-aggregate":
            result = aggregate_a2()
        elif command == "b2-smoke":
            result = run_b2(smoke=True)
        elif command == "b2-run":
            result = run_b2()
        elif command == "b2-aggregate":
            result = aggregate_b2()
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
