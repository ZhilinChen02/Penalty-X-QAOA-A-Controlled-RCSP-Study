from __future__ import annotations

from qroute_dilution.theory.rcsp_bridge import (
    explicit_signature,
    layered_binary_audit,
    layered_feasible_labels,
    parallel_path_audit,
    singleton_encoding,
    singleton_from_explicit_coefficients,
)


def test_layered_arbitrary_subset_mapping_and_exponential_resources() -> None:
    marked = (0, 3, 7)
    assert layered_feasible_labels(3, marked) == marked
    audit = layered_binary_audit(3, marked)
    assert audit.resource_count == 8 - len(marked)
    assert audit.graph_edges == 6


def test_parallel_paths_are_explicit_size_theta_N() -> None:
    audit = parallel_path_audit(4, (1, 2))
    assert audit.graph_vertices == 18
    assert audit.graph_edges == 32
    assert not audit.polynomial_in_n
    assert audit.explicit_input_reveals_marked_set


def test_singleton_is_compact_but_readable() -> None:
    coefficients = singleton_encoding(4, 11)
    assert singleton_from_explicit_coefficients(coefficients) == 11


def test_different_marked_sets_change_explicit_input() -> None:
    assert explicit_signature(3, (0, 2), "layered") != explicit_signature(
        3, (1, 3), "layered"
    )
