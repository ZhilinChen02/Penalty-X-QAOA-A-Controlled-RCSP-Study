"""Small explicit constructions for the RCSP bridge adversarial audit."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import pandas as pd


@dataclass(frozen=True)
class BridgeAudit:
    construction: str
    n: int
    N: int
    M: int
    graph_vertices: int
    graph_edges: int
    resource_count: int
    coefficient_entries: int
    coefficient_bit_length_max: int
    candidate_path_domain_N: int
    candidate_path_feasible_M: int
    edge_bit_domain_N: int
    edge_bit_feasible_M: int
    explicit_input_reveals_marked_set: bool
    polynomial_in_n: bool
    status: str

    def to_dict(self) -> dict[str, object]:
        return dict(self.__dict__)


def labels(n: int) -> tuple[tuple[int, ...], ...]:
    if n <= 0:
        raise ValueError("n must be positive")
    return tuple(itertools.product((0, 1), repeat=n))


def normalize_marked(n: int, marked: Iterable[int]) -> tuple[int, ...]:
    N = 2**n
    values = tuple(sorted(set(int(value) for value in marked)))
    if any(value < 0 or value >= N for value in values):
        raise ValueError("marked label out of range")
    return values


def parallel_path_audit(n: int, marked: Iterable[int]) -> BridgeAudit:
    marked_values = normalize_marked(n, marked)
    N, M = 2**n, len(marked_values)
    # s -> v_x -> t for every label x.
    return BridgeAudit(
        construction="EXPLICIT_PARALLEL_PATHS",
        n=n,
        N=N,
        M=M,
        graph_vertices=N + 2,
        graph_edges=2 * N,
        resource_count=1,
        coefficient_entries=2 * N,
        coefficient_bit_length_max=1,
        candidate_path_domain_N=N,
        candidate_path_feasible_M=M,
        edge_bit_domain_N=2 ** (2 * N),
        edge_bit_feasible_M=M,
        explicit_input_reveals_marked_set=True,
        polynomial_in_n=False,
        status="VALID_BUT_EXPLICIT_SIZE_THETA_N",
    )


def layered_resource_encoding(
    n: int, marked: Iterable[int]
) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...]]:
    """Encode any marked set using one upper-bound resource per unmarked label.

    For an unmarked word y, its resource counts positions where candidate x
    matches y.  Budget n-1 excludes exactly x=y.  The graph itself is the
    O(n)-edge binary-choice chain, but the resource table is exponential.
    """
    marked_values = set(normalize_marked(n, marked))
    unmarked = tuple(value for value in range(2**n) if value not in marked_values)
    rows: list[tuple[int, ...]] = []
    for word in labels(n):
        integer = int("".join(str(bit) for bit in word), 2)
        consumptions = []
        for excluded in unmarked:
            excluded_bits = tuple(int(bit) for bit in f"{excluded:0{n}b}")
            consumptions.append(sum(a == b for a, b in zip(word, excluded_bits)))
        rows.append(tuple(consumptions))
    return tuple(rows), tuple(n - 1 for _ in unmarked)


def layered_feasible_labels(n: int, marked: Iterable[int]) -> tuple[int, ...]:
    resources, budgets = layered_resource_encoding(n, marked)
    return tuple(
        label
        for label, consumption in enumerate(resources)
        if all(value <= budget for value, budget in zip(consumption, budgets))
    )


def layered_binary_audit(n: int, marked: Iterable[int]) -> BridgeAudit:
    marked_values = normalize_marked(n, marked)
    N, M = 2**n, len(marked_values)
    resources = N - M
    return BridgeAudit(
        construction="LAYERED_BINARY_GRAPH",
        n=n,
        N=N,
        M=M,
        graph_vertices=n + 1,
        graph_edges=2 * n,
        resource_count=resources,
        coefficient_entries=2 * n * resources,
        coefficient_bit_length_max=max(1, math.ceil(math.log2(n + 1))),
        candidate_path_domain_N=N,
        candidate_path_feasible_M=M,
        edge_bit_domain_N=2 ** (2 * n),
        edge_bit_feasible_M=M,
        explicit_input_reveals_marked_set=True,
        polynomial_in_n=False,
        status="ARBITRARY_SUBSET_REQUIRES_EXPONENTIAL_RESOURCE_TABLE",
    )


def singleton_encoding(n: int, marked_label: int) -> tuple[tuple[int, int], ...]:
    """One-resource compact singleton encoding; zero weight reveals each bit."""
    normalize_marked(n, (marked_label,))
    bits = tuple(int(bit) for bit in f"{marked_label:0{n}b}")
    return tuple((0, 1) if bit == 0 else (1, 0) for bit in bits)


def singleton_from_explicit_coefficients(coefficients: Sequence[Sequence[int]]) -> int:
    bits: list[str] = []
    for pair in coefficients:
        if tuple(pair) == (0, 1):
            bits.append("0")
        elif tuple(pair) == (1, 0):
            bits.append("1")
        else:
            raise ValueError("coefficients do not encode a unique singleton")
    return int("".join(bits), 2)


def hidden_singleton_audit(n: int, marked_label: int) -> BridgeAudit:
    singleton_encoding(n, marked_label)
    return BridgeAudit(
        construction="HIDDEN_SINGLETON_ATTEMPT",
        n=n,
        N=2**n,
        M=1,
        graph_vertices=n + 1,
        graph_edges=2 * n,
        resource_count=1,
        coefficient_entries=2 * n,
        coefficient_bit_length_max=1,
        candidate_path_domain_N=2**n,
        candidate_path_feasible_M=1,
        edge_bit_domain_N=2 ** (2 * n),
        edge_bit_feasible_M=1,
        explicit_input_reveals_marked_set=True,
        polynomial_in_n=True,
        status="COMPACT_BUT_EXPLICIT_INPUT_REVEALS_SINGLETON",
    )


def circuit_verifier_audit(
    n: int, predicate_circuit_size: int, marked_count: int
) -> BridgeAudit:
    """Audit a succinct predicate, without claiming an additive-RCSP compiler."""
    polynomial = predicate_circuit_size <= n**4
    return BridgeAudit(
        construction="CIRCUIT_VERIFIER_AUTOMATON",
        n=n,
        N=2**n,
        M=marked_count,
        graph_vertices=predicate_circuit_size + n + 2,
        graph_edges=2 * (predicate_circuit_size + n),
        resource_count=0,
        coefficient_entries=predicate_circuit_size,
        coefficient_bit_length_max=max(1, math.ceil(math.log2(predicate_circuit_size + 1))),
        candidate_path_domain_N=2**n,
        candidate_path_feasible_M=marked_count,
        edge_bit_domain_N=2 ** (2 * (predicate_circuit_size + n)),
        edge_bit_feasible_M=marked_count,
        explicit_input_reveals_marked_set=False,
        polynomial_in_n=polynomial,
        status="SUCCINCT_PREDICATE_NOT_COMPILED_TO_STANDARD_ADDITIVE_RCSP",
    )


def oracle_rcsp_audit(n: int, marked_count: int) -> BridgeAudit:
    return BridgeAudit(
        construction="ORACLE_RCSP",
        n=n,
        N=2**n,
        M=marked_count,
        graph_vertices=n + 1,
        graph_edges=2 * n,
        resource_count=0,
        coefficient_entries=0,
        coefficient_bit_length_max=0,
        candidate_path_domain_N=2**n,
        candidate_path_feasible_M=marked_count,
        edge_bit_domain_N=2 ** (2 * n),
        edge_bit_feasible_M=marked_count,
        explicit_input_reveals_marked_set=False,
        polynomial_in_n=True,
        status="ORACLE_RCSP_COROLLARY",
    )


def explicit_signature(n: int, marked: Iterable[int], construction: str) -> str:
    marked_values = normalize_marked(n, marked)
    if construction == "parallel":
        payload = {"n": n, "resources": [int(x not in marked_values) for x in range(2**n)]}
    elif construction == "layered":
        resources, budgets = layered_resource_encoding(n, marked_values)
        payload = {"n": n, "resources": resources, "budgets": budgets}
    elif construction == "singleton":
        if len(marked_values) != 1:
            raise ValueError("singleton construction requires one marked label")
        payload = {"n": n, "coefficients": singleton_encoding(n, marked_values[0])}
    else:
        raise ValueError("unknown construction")
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def small_bridge_validation(n_values=(2, 3, 4)) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for n in n_values:
        N = 2**n
        marked = tuple(sorted({0, N // 3, N - 1}))
        for audit in (
            parallel_path_audit(n, marked),
            layered_binary_audit(n, marked),
            hidden_singleton_audit(n, N // 3),
            circuit_verifier_audit(n, 3 * n, len(marked)),
            oracle_rcsp_audit(n, len(marked)),
        ):
            mapping_ok = True
            if audit.construction == "LAYERED_BINARY_GRAPH":
                mapping_ok = layered_feasible_labels(n, marked) == marked
            if audit.construction == "HIDDEN_SINGLETON_ATTEMPT":
                coefficients = singleton_encoding(n, N // 3)
                mapping_ok = singleton_from_explicit_coefficients(coefficients) == N // 3
            signature_a = "NOT_EXPLICIT"
            signature_b = "NOT_EXPLICIT"
            visibly_different = False
            if audit.construction == "EXPLICIT_PARALLEL_PATHS":
                signature_a = explicit_signature(n, marked, "parallel")
                signature_b = explicit_signature(n, tuple((x + 1) % N for x in marked), "parallel")
                visibly_different = signature_a != signature_b
            elif audit.construction == "LAYERED_BINARY_GRAPH":
                signature_a = explicit_signature(n, marked, "layered")
                signature_b = explicit_signature(n, tuple((x + 1) % N for x in marked), "layered")
                visibly_different = signature_a != signature_b
            elif audit.construction == "HIDDEN_SINGLETON_ATTEMPT":
                signature_a = explicit_signature(n, (N // 3,), "singleton")
                signature_b = explicit_signature(n, ((N // 3 + 1) % N,), "singleton")
                visibly_different = signature_a != signature_b
            rows.append(
                {
                    **audit.to_dict(),
                    "label_path_bijection": audit.candidate_path_domain_N == N,
                    "marked_feasibility_mapping": mapping_ok,
                    "explicit_signature": signature_a,
                    "alternative_signature": signature_b,
                    "different_marked_sets_visible": visibly_different,
                    "candidate_path_phi": audit.M / audit.candidate_path_domain_N,
                    "edge_bit_phi": audit.edge_bit_feasible_M / audit.edge_bit_domain_N,
                }
            )
    return pd.DataFrame(rows)
