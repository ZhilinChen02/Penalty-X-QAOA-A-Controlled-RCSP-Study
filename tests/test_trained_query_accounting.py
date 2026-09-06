from __future__ import annotations

from qroute_dilution.theory.adaptive_query_bound import TrainedRound, total_trained_queries


def test_exact_trained_total_query_accounting() -> None:
    rounds = [
        TrainedRound((2, 3), (100, 20)),
        TrainedRound((4,), (50,)),
    ]
    assert total_trained_queries(rounds, final_queries=3) == 463


def test_free_explicit_feasible_list_is_zero_query_counterexample() -> None:
    feasible_list = [7, 11]
    output = feasible_list[0]
    oracle_queries = 0
    assert output in feasible_list
    assert oracle_queries == 0
