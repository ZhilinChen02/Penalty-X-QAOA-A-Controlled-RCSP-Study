from __future__ import annotations

import os
import subprocess

import pytest
from pathlib import Path

from qroute_dilution.io import PROJECT_ROOT


BASE_V2 = "68d0799be9d6e50f4a06e704d4c5a0265bcb5045"
BASE_V3 = "0657e603434cf7a7b7f9b7d1f5756dc1f85ae882"
BASE_SYNTHESIS = "260e258af7d397f53c62521d9f52b31223076ec9"
THEORY_V2 = Path(os.environ.get("QROUTE_THEORY_V2_WORKTREE", PROJECT_ROOT.parent / "Q-RouteDilution-theory-v2"))
THEORY_V3 = Path(os.environ.get("QROUTE_THEORY_V3_WORKTREE", PROJECT_ROOT.parent / "Q-RouteDilution-theory-v3"))
SYNTHESIS = Path(os.environ.get("QROUTE_SYNTHESIS_WORKTREE", PROJECT_ROOT.parent / "Q-RouteDilution-synthesis-v1"))
ORIGINAL = Path(os.environ.get("QROUTE_ORIGINAL_WORKTREE", PROJECT_ROOT.parent / "Q-RouteDilution"))


def _run(cwd: Path, *args: str) -> str:
    if not cwd.is_dir():
        pytest.skip("historical author worktree is not available in a public snapshot")
    if len(args) > 3 and args[:2] == ("git", "diff"):
        known = subprocess.run(["git", "cat-file", "-e", args[3]], cwd=cwd, capture_output=True)
        if known.returncode:
            pytest.skip("historical audit commit is not included in the public snapshot")
    return subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True).stdout


def test_theory_v1_v2_artifacts_are_hash_identical() -> None:
    protected = (
        "results/theory_validation_v1",
        "results/theory_validation_v2",
        "docs/theory/GLOBAL_QAOA_DILUTION_THEOREM.md",
        "docs/theory/GLOBAL_QAOA_DILUTION_THEOREM.tex",
        "docs/theory/ADAPTIVE_QUERY_DILUTION_THEOREM.md",
        "docs/theory/ADAPTIVE_QUERY_DILUTION_THEOREM.tex",
        "docs/theory/TRAINED_QAOA_TOTAL_QUERY_THEOREM.md",
        "docs/theory/RCSP_BRIDGE_AUDIT.md",
    )
    assert _run(PROJECT_ROOT, "git", "diff", "--name-only", BASE_V2, "--", *protected) == ""


def test_protected_worktree_heads_and_theory_v2_cleanliness() -> None:
    assert _run(THEORY_V2, "git", "rev-parse", "HEAD").strip() == BASE_V2
    assert _run(THEORY_V2, "git", "status", "--porcelain") == ""
    assert _run(THEORY_V3, "git", "rev-parse", "HEAD").strip() == BASE_V3
    assert _run(THEORY_V3, "git", "status", "--porcelain") == ""
    assert _run(SYNTHESIS, "git", "rev-parse", "HEAD").strip() == BASE_SYNTHESIS
    assert _run(SYNTHESIS, "git", "status", "--porcelain") == ""
    assert _run(ORIGINAL, "git", "rev-parse", "HEAD").strip() == "b9922aadbc3c098db74a8e4ee992572a698d1f53"
    assert PROJECT_ROOT.name == "Q-RouteDilution-paper-v1"
