#!/usr/bin/env python3
"""Run the two read-only pre-revision scientific sanity audits."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qroute_dilution.reviewer_robustness.final_audits import (  # noqa: E402
    run_final_scientific_audits,
)


if __name__ == "__main__":
    print(json.dumps(run_final_scientific_audits(), indent=2, sort_keys=True))
