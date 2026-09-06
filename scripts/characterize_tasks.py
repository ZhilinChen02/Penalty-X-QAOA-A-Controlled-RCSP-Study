#!/usr/bin/env python3
from __future__ import annotations

import argparse

from qroute_dilution.pipeline import characterize_tasks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/smoke.yaml")
    args = parser.parse_args()
    frame = characterize_tasks(args.config)
    print(f"characterized {len(frame)} tasks")


if __name__ == "__main__":
    main()
