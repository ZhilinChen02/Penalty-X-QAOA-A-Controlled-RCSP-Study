#!/usr/bin/env python3
"""Rebuild the resource-censored scaling verdict from canonical rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from _reproduction_common import DEFAULT_OUTPUT, output_directory, verify, write_json
from paper_scripts.rebuild_publication_results import AUTHORITATIVE_FLOAT_ATOL, reconstruct_scaling


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = output_directory(args.output_dir)

    verdict, exponents, _ = reconstruct_scaling()
    if verdict["maximum_abs_eta_difference_vs_stored"] > AUTHORITATIVE_FLOAT_ATOL:
        raise RuntimeError("scaling exponents disagree with authoritative rows")
    if not verdict["m20_O3_vs_O0_ordering_reversed"]:
        raise RuntimeError("m=20 O3/O0 reversal did not reproduce")
    if not verdict["m22_resource_censored"] or verdict["m22_scientific_outcome_rows"] != 0:
        raise RuntimeError("m=22 prospective resource censoring did not reproduce")
    if verdict["global_scaling_law_supported"]:
        raise RuntimeError("unsupported global scaling verdict")

    json_path = output_dir / "scaling_verdict.json"
    exponent_path = output_dir / "scaling_exponents.csv"
    write_json(json_path, verdict)
    exponents.to_csv(
        exponent_path, index=False, float_format="%.12f", lineterminator="\n"
    )

    if args.verify:
        verify(json_path)
        verify(exponent_path)
    print(
        "SCALING PASS: m=20 O3/O0 ordering reversal reproduced; m=22 has 180 "
        "resource-censored planned rows and zero scientific outcomes."
    )


if __name__ == "__main__":
    main()
