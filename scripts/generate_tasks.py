#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qroute_dilution.pipeline import generate_task_universe


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/smoke.yaml")
    args = parser.parse_args()
    tasks, manifest = generate_task_universe(args.config)
    print(f"generated {len(tasks)} tasks; manifest rows={len(manifest)}")


if __name__ == "__main__":
    main()
