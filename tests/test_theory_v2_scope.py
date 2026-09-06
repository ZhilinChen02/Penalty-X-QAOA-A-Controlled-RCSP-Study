from __future__ import annotations

from pathlib import Path

from qroute_dilution.io import PROJECT_ROOT


def test_v2_documents_keep_required_nonclaims() -> None:
    required = [
        "ADAPTIVE_QUERY_DILUTION_THEOREM.md",
        "TRAINED_QAOA_TOTAL_QUERY_THEOREM.md",
        "QAOA_INFORMATION_ACCESS_MODELS.md",
        "RCSP_BRIDGE_AUDIT.md",
        "THEORY_V2_CLAIM_BOUNDARY.md",
    ]
    for name in required:
        text = (PROJECT_ROOT / "docs/theory" / name).read_text(encoding="utf-8")
        assert "All QAOA algorithms require" not in text or "prohibited" in text.lower()
    report = (PROJECT_ROOT / "results/theory_validation_v2/THEORY_V2_REPORT.md").read_text()
    assert "ORACLE_RCSP_ONLY" in report
    assert "RICH_COST_ORACLE_EXTENSION_OPEN" in report


def test_no_downloaded_papers_are_committed_to_result_root() -> None:
    root = PROJECT_ROOT / "results/theory_validation_v2"
    assert not list(root.rglob("*.pdf"))
