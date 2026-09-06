#!/usr/bin/env python3
"""Stage-gated command-line runner for Phase 3 empirical dilution scaling."""

from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from qroute_dilution.phase3_analysis import analyze_phase3
from qroute_dilution.phase3_execution import (
    ADEQUACY_PATH,
    SPLIT_RESULT_PATHS,
    freeze_execution_identity,
    record_execution_provenance,
    run_optimization_adequacy,
    run_protocol_preflight,
    run_resource_preflight,
    run_split,
)
from qroute_dilution.phase3_models import base_graph_exponents, freeze_development_models
from qroute_dilution.phase3_tasks import (
    characterize_task_universe,
    generate_task_universe,
    verify_predecessor_hashes,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=[
            "generate", "characterize", "resource", "preflight", "freeze-execution",
            "development", "adequacy", "freeze-model", "interpolation",
            "extrapolation", "analyze", "verify-hashes",
        ],
    )
    parser.add_argument("--pytest-result", default="not recorded")
    args = parser.parse_args()
    started = time.perf_counter()
    if args.stage == "generate":
        value = generate_task_universe()
        details = {"base_graphs": value["base_graph_count"], "tasks": value["task_count"]}
    elif args.stage == "characterize":
        frame = characterize_task_universe()
        details = {"tasks": len(frame), "contract_pass": int(frame.penalty_contract_pass.sum())}
    elif args.stage == "resource":
        frame = run_resource_preflight()
        details = {"largest_allowed_m": int(frame.loc[~frame.resource_censored.astype(bool), "size_m"].max()), "censored_sizes": frame.loc[frame.resource_censored.astype(bool), "size_m"].astype(int).tolist()}
    elif args.stage == "preflight":
        value = run_protocol_preflight()
        details = value
    elif args.stage == "freeze-execution":
        value = freeze_execution_identity(args.pytest_result)
        details = {"scientific_input_count": len(value["scientific_input_hashes"]), "pytest_result": value["pytest_result"]}
    elif args.stage == "development":
        frame = run_split("development")
        details = {"rows": len(frame), "p2": int((frame.depth == 2).sum()), "p3": int((frame.depth == 3).sum())}
    elif args.stage == "adequacy":
        frame = run_optimization_adequacy()
        details = {"rows": len(frame), "substantial": int(frame.substantial_budget_sensitivity.sum()), "claim_ceiling": bool(frame.optimizer_adequacy_flag.any())}
    elif args.stage == "freeze-model":
        if not ADEQUACY_PATH.exists():
            raise RuntimeError("optimization adequacy must be reported before model freeze")
        development = pd.read_csv(SPLIT_RESULT_PATHS["development"])
        p3 = development[
            development.objective_id.isin(["O0", "O2", "O3"])
            & development.execution_status.isin(["SUCCESS", "ZERO_P_FEAS", "ZERO_P_OPT"])
            & ~development.resource_censored.astype(bool)
        ]
        exponents = base_graph_exponents(p3)
        if len(exponents) != 48:
            raise RuntimeError("development exponent denominator incomplete")
        value = freeze_development_models(p3)
        details = {objective: value["objectives"][objective]["selected_model_id"] for objective in ("O0", "O2", "O3")}
    elif args.stage == "interpolation":
        frame = run_split("interpolation_holdout")
        details = {"rows": len(frame), "resource_censored": int(frame.resource_censored.sum())}
    elif args.stage == "extrapolation":
        frame = run_split("extrapolation_holdout")
        details = {"rows": len(frame), "resource_censored": int(frame.resource_censored.sum())}
    elif args.stage == "analyze":
        value = analyze_phase3()
        details = {"status": value["phase3_status"], "primary_verdict": value["primary_scientific_verdict"], "objective_verdict": value["objective_comparison_verdict"]}
    else:
        value = verify_predecessor_hashes()
        details = {"verified_files": value["file_count"], "inventory_sha256": value["inventory_sha256"]}
    elapsed = time.perf_counter() - started
    record_execution_provenance(args.stage, elapsed, details)
    print(json.dumps({"stage": args.stage, "wall_time_s": elapsed, **details}, sort_keys=True))


if __name__ == "__main__":
    main()
