from __future__ import annotations

import os
import subprocess

import pytest
from pathlib import Path

from qroute_dilution.io import PROJECT_ROOT


BASE = "b9922aadbc3c098db74a8e4ee992572a698d1f53"
ORIGINAL = Path(os.environ.get("QROUTE_ORIGINAL_WORKTREE", PROJECT_ROOT.parent / "Q-RouteDilution"))


def _run(cwd: Path, *args: str) -> str:
    if not cwd.is_dir():
        pytest.skip("historical author worktree is not available in a public snapshot")
    if len(args) > 3 and args[:2] == ("git", "diff"):
        known = subprocess.run(["git", "cat-file", "-e", args[3]], cwd=cwd, capture_output=True)
        if known.returncode:
            pytest.skip("historical audit commit is not included in the public snapshot")
    return subprocess.run(
        args, cwd=cwd, check=True, text=True, capture_output=True
    ).stdout


def test_v1_theory_artifacts_unchanged_from_audited_commit() -> None:
    paths = [
        "results/theory_validation_v1",
        "docs/theory/GLOBAL_QAOA_DILUTION_THEOREM.md",
        "docs/theory/GLOBAL_QAOA_DILUTION_THEOREM.tex",
        "docs/theory/PROOF_AUDIT.md",
    ]
    output = _run(PROJECT_ROOT, "git", "diff", "--name-only", BASE, "--", *paths)
    assert output == ""


def test_original_dirty_worktree_snapshot_is_unchanged() -> None:
    observed = (
        "COMMAND: git status --short\n"
        + _run(ORIGINAL, "git", "status", "--short")
        + "COMMAND: git diff --stat\n"
        + _run(ORIGINAL, "git", "diff", "--stat")
        + "COMMAND: git rev-parse HEAD\n"
        + _run(ORIGINAL, "git", "rev-parse", "HEAD")
    )
    expected = (
        PROJECT_ROOT
        / "results/theory_validation_v2/original_worktree_initial_snapshot.txt"
    ).read_text(encoding="utf-8")
    assert observed == expected
    final_snapshot = (
        PROJECT_ROOT
        / "results/theory_validation_v2/original_worktree_final_snapshot.txt"
    ).read_text(encoding="utf-8")
    assert final_snapshot == expected
