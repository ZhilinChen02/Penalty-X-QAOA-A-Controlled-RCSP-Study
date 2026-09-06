from __future__ import annotations

from qroute_dilution.theory.structure_cost_ledger import (
    METHODS,
    RESOURCE_CONTRACT,
    empty_cost_ledger,
    method_matrix,
    validate_ledger,
)


def test_cost_contract_is_orthogonal_and_complete() -> None:
    assert len(RESOURCE_CONTRACT) == 7
    assert len(METHODS) == 10
    ledger = empty_cost_ledger()
    validate_ledger(ledger)
    assert len(ledger) == len(METHODS) * sum(map(len, RESOURCE_CONTRACT.values()))
    assert set(ledger.unit) == {"RESOURCE_SPECIFIC"}


def test_method_matrix_does_not_invent_scalar_deployment_scores() -> None:
    matrix = method_matrix()
    assert len(matrix) == 10
    assert "score" not in matrix.columns
    assert set(matrix.method) == {record.method for record in METHODS}
    assert matrix.unknown.str.len().min() > 0
