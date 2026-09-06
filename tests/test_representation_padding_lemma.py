from __future__ import annotations

from fractions import Fraction

from qroute_dilution.theory.representation_padding import (
    RationalEdge,
    make_instance,
    padding_audit,
    raw_edge_bit_phi,
    subdivide_edge,
)


def _diamond_instance():
    edges = (
        RationalEdge.make("a", "s", "u", Fraction(3, 5), (Fraction(2, 3),)),
        RationalEdge.make("b", "u", "t", Fraction(4, 5), (Fraction(1, 3),)),
        RationalEdge.make("c", "s", "v", 2, (1,)),
        RationalEdge.make("d", "v", "t", 2, (2,)),
    )
    return make_instance(("s", "u", "v", "t"), edges, "s", "t", (2,))


def test_edge_subdivision_representation_padding_lemma() -> None:
    instance = _diamond_instance()
    result = subdivide_edge(instance, "a", 7)
    audit = padding_audit(result)
    assert audit["route_bijection"]
    assert audit["totals_preserved"]
    assert audit["feasibility_preserved"]
    assert audit["objective_ordering_preserved"]
    assert audit["optimum_preserved"]
    assert audit["valid_feasible_route_count_preserved"]
    assert audit["phi_factor_exact"]
    assert raw_edge_bit_phi(result.padded) == raw_edge_bit_phi(instance) / 2**6
    assert audit["padded_coefficient_bits"] <= audit["coefficient_growth_upper_bound"]


def test_route_conversion_is_linear_and_exact() -> None:
    result = subdivide_edge(_diamond_instance(), "a", 4)
    original = ("a", "b")
    expanded = result.expand_route(original)
    assert len(expanded) == len(original) + 3
    assert result.contract_route(expanded) == original
