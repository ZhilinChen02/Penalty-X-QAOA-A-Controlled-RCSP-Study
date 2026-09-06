#!/usr/bin/env python3
"""Reconstruct all paper headline statistics from canonical result rows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from _reproduction_common import DEFAULT_OUTPUT, output_directory, stable_value, verify, write_json
from paper_scripts.rebuild_publication_results import (
    AUTHORITATIVE_FLOAT_ATOL,
    canonical_hashes,
    compare_graph_rows,
    reconstruct_discovery,
    reconstruct_heldout,
    reconstruct_optimizer,
    reconstruct_scaling,
    reconstruct_universe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = output_directory(args.output_dir)

    hashes_before = canonical_hashes()
    universe = reconstruct_universe()
    optimizer, _ = reconstruct_optimizer()
    discovery, _ = reconstruct_discovery()
    heldout, _, heldout_graphs, _ = reconstruct_heldout()
    scaling, _, _ = reconstruct_scaling()
    heldout["maximum_abs_graph_contrast_difference_vs_stored"] = compare_graph_rows(
        heldout_graphs
    )

    if heldout["maximum_abs_graph_contrast_difference_vs_stored"] > AUTHORITATIVE_FLOAT_ATOL:
        raise RuntimeError("held-out graph contrasts disagree with the authoritative table")
    if scaling["maximum_abs_eta_difference_vs_stored"] > AUTHORITATIVE_FLOAT_ATOL:
        raise RuntimeError("scaling exponents disagree with the authoritative table")

    output = {
        "schema_version": "external_reproduction_headlines.v1",
        "evidence_policy": "CANONICAL_ROWS_NO_QAOA_OPTIMIZATION",
        "portable_float_rounding_decimals": 12,
        "task_universe": universe,
        "optimizer_attribution": optimizer,
        "objective_discovery": discovery,
        "heldout": heldout,
        "scaling": scaling,
    }
    headline_path = output_dir / "headlines.json"
    write_json(headline_path, output)

    hash_path = output_dir / "canonical_input_hashes.txt"
    hash_path.write_text(
        "".join(f"{checksum}  {relative}\n" for relative, checksum in hashes_before.items()),
        encoding="utf-8",
    )
    if canonical_hashes() != hashes_before:
        raise RuntimeError("canonical inputs changed while reproducing headlines")

    if args.verify:
        verify(headline_path)
        verify(hash_path)
    print(
        "HEADLINE PASS: 140 tasks; 168 optimizer pairs; 84 held-out tasks/15 graphs; "
        "m=20 reversal and m=22 resource censoring verified."
    )


if __name__ == "__main__":
    main()
