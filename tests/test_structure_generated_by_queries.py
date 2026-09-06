from __future__ import annotations

from qroute_dilution.theory.advice_query_tradeoff import (
    StructuredOracleAccount,
    TwoStageQueryAccount,
    classify_structured_operation,
)


def test_preprocessing_and_postprocessing_queries_are_both_charged() -> None:
    account = TwoStageQueryAccount(7, 3)
    assert account.total_queries == 10
    assert account.success_bound(1e-4) == min(1.0, 21**2 * 1e-4)


def test_simulable_structure_oracle_is_charged_per_invocation() -> None:
    account = StructuredOracleAccount(5, 3, 2)
    assert account.charged_membership_queries == 17
    assert account.classification == "MEMBERSHIP_SIMULABLE_CHARGED"
    assert classify_structured_operation(None) == "STRICTLY_STRONGER_STRUCTURE_ORACLE"
