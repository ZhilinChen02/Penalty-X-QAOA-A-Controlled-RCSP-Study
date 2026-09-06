#!/usr/bin/env python3
"""Rebuild preregistered held-out inference and task-level win counts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from _reproduction_common import DEFAULT_OUTPUT, output_directory, verify, write_json
from paper_scripts.rebuild_publication_results import (
    AUTHORITATIVE_FLOAT_ATOL,
    compare_graph_rows,
    reconstruct_heldout,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = output_directory(args.output_dir)

    heldout, task_rows, graph_rows, _ = reconstruct_heldout()
    heldout["maximum_abs_graph_contrast_difference_vs_stored"] = compare_graph_rows(
        graph_rows
    )
    if heldout["maximum_abs_graph_contrast_difference_vs_stored"] > AUTHORITATIVE_FLOAT_ATOL:
        raise RuntimeError("held-out graph contrasts disagree with authoritative rows")
    if (heldout["task_count"], heldout["base_graph_count"]) != (84, 15):
        raise RuntimeError("held-out analysis denominator changed")
    if heldout["secondary"]["O3_vs_O0_P_opt_wins"] != 80:
        raise RuntimeError("80/84 P_opt count did not reproduce")
    if heldout["secondary"]["O3_vs_O0_both_Pfeas_Popt_wins"] != 79:
        raise RuntimeError("79/84 joint count did not reproduce")

    json_path = output_dir / "heldout.json"
    graph_path = output_dir / "heldout_graph_contrasts.csv"
    task_path = output_dir / "heldout_task_metrics.csv"
    write_json(json_path, heldout)
    graph_rows.to_csv(graph_path, index=False, float_format="%.12f", lineterminator="\n")
    task_rows.to_csv(task_path, index=False, float_format="%.12f", lineterminator="\n")

    if args.verify:
        for path in (json_path, graph_path, task_path):
            verify(path)
    print(
        "HELD-OUT PASS: graph-level H1/H2 rebuilt with grouped bootstrap, exact "
        "sign flips, Holm correction, and 80/84 plus 79/84 secondary counts."
    )


if __name__ == "__main__":
    main()
