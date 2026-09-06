from __future__ import annotations

import pandas as pd

from qroute_dilution.io import PROJECT_ROOT


def test_v3_claim_boundary_contains_required_verdicts_and_nonclaims() -> None:
    boundary = (PROJECT_ROOT / "docs/theory/THEORY_V3_CLAIM_BOUNDARY.md").read_text()
    for token in (
        "RAW_PHI_STATE_LOWER_BOUND_IMPOSSIBLE",
        "EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND_VALID",
        "POSTERIOR_STRUCTURE_BOUND_VALID",
        "FINITE_ADVICE_TRADEOFF_VALID",
        "QUANTUM_ADVICE_BOUND_VALID",
        "STRUCTURE_COST_CONTRACT_COMPLETE",
        "RICH_COST_ORACLE_EXTENSION_OPEN",
    ):
        assert token in boundary
    assert "## Prohibited claims" in boundary
    assert "Every explicit RCSP instance requires" in boundary


def test_required_v3_outputs_and_no_downloaded_papers() -> None:
    result_root = PROJECT_ROOT / "results/theory_validation_v3"
    assert (result_root / "THEORY_V3_REPORT.md").is_file()
    assert (result_root / "summary.json").is_file()
    assert not list(result_root.rglob("*.pdf"))


def test_all_required_documents_code_results_and_figures_exist() -> None:
    required = (
        "docs/theory/RAW_EDGE_BIT_DILUTION_COUNTEREXAMPLE.md",
        "docs/theory/REPRESENTATION_PADDING_LEMMA.md",
        "docs/theory/EXPLICIT_ATTRIBUTE_QUERY_RCSP_BOUND.md",
        "docs/theory/POSTERIOR_STRUCTURE_DILUTION_THEOREM.md",
        "docs/theory/POSTERIOR_STRUCTURE_DILUTION_THEOREM.tex",
        "docs/theory/ADVICE_QUERY_TRADEOFF.md",
        "docs/theory/EFFECTIVE_STRUCTURE_BITS.md",
        "docs/theory/STRUCTURE_COST_RELOCATION_CONTRACT.md",
        "docs/theory/STRUCTURE_INJECTION_METHOD_MATRIX.md",
        "docs/theory/STRUCTURE_TRADEOFF_PRIOR_ART.md",
        "src/qroute_dilution/theory/explicit_rcsp_bounds.py",
        "src/qroute_dilution/theory/posterior_structure_bound.py",
        "src/qroute_dilution/theory/advice_query_tradeoff.py",
        "src/qroute_dilution/theory/representation_padding.py",
        "src/qroute_dilution/theory/structure_cost_ledger.py",
    )
    assert all((PROJECT_ROOT / path).is_file() for path in required)


def test_claim_matrix_uses_controlled_status_vocabulary() -> None:
    matrix = pd.read_csv(PROJECT_ROOT / "results/theory_validation_v3/claim_matrix_v3.csv")
    assert list(matrix.columns) == [
        "claim_id",
        "claim_text",
        "track",
        "status",
        "assumptions",
        "proof_location",
        "numerical_validation",
        "prior_art_status",
        "allowed_wording",
        "prohibited_wording",
    ]
    allowed = {
        "VALID_AS_STATED",
        "VALID_AFTER_REFINEMENT",
        "INVALID",
        "COUNTEREXAMPLE_ESTABLISHED",
        "OPEN_GAP",
        "KNOWN_PRIOR_ART",
        "REFORMULATION",
        "NOVELTY_UNRESOLVED",
        "OUTSIDE_MODEL",
    }
    assert set(matrix.status) <= allowed
