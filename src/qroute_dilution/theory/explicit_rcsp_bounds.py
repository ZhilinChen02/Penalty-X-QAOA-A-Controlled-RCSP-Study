"""Auditable explicit RCSP constructions and their input-query bounds."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class UniqueChainAudit:
    m: int
    edge_bit_states: int
    valid_feasible_edge_bitstrings: int
    phi_state: float
    inverse_sqrt_phi_state: float
    traversal_steps: int
    output_edges: tuple[int, ...]


def unique_chain_audit(m: int) -> UniqueChainAudit:
    if m <= 0 or int(m) != m:
        raise ValueError("m must be a positive integer")
    m = int(m)
    return UniqueChainAudit(
        m=m,
        edge_bit_states=2**m,
        valid_feasible_edge_bitstrings=1,
        phi_state=2.0 ** (-m),
        inverse_sqrt_phi_state=2.0 ** (m / 2.0),
        traversal_steps=m,
        output_edges=tuple(range(m)),
    )


@dataclass(frozen=True)
class ParallelBranchRCSP:
    """K explicit two-edge branches with a counted status attribute array."""

    z: tuple[int, ...]
    budget: int = 2

    def __post_init__(self) -> None:
        if not self.z or any(value not in (0, 1) for value in self.z):
            raise ValueError("z must be a nonempty bit array")
        if self.budget != 2:
            raise ValueError("the audited construction uses budget B=2")

    @property
    def K(self) -> int:
        return len(self.z)

    @property
    def M(self) -> int:
        return int(sum(self.z))

    @property
    def edge_count(self) -> int:
        return 2 * self.K

    def second_edge_resource(self, branch: int) -> int:
        self._check_branch(branch)
        return 1 if self.z[branch] == 1 else 2

    def route_resource(self, branch: int) -> int:
        return 1 + self.second_edge_resource(branch)

    def is_feasible(self, branch: int) -> bool:
        return self.route_resource(branch) <= self.budget

    def oracle_bit(self, branch: int) -> int:
        """One counted attribute query returns exactly the marked-search bit."""
        self._check_branch(branch)
        return self.z[branch]

    def _check_branch(self, branch: int) -> None:
        if branch < 0 or branch >= self.K or int(branch) != branch:
            raise IndexError("branch index out of range")

    @property
    def feasible_branches(self) -> tuple[int, ...]:
        return tuple(index for index in range(self.K) if self.is_feasible(index))

    @property
    def phi_path(self) -> float:
        return self.M / self.K

    @property
    def phi_state(self) -> float:
        return self.M / (2 ** self.edge_count)


def parallel_branch_instance(K: int, marked: Iterable[int]) -> ParallelBranchRCSP:
    if K <= 0 or int(K) != K:
        raise ValueError("K must be a positive integer")
    marked_values = tuple(int(value) for value in marked)
    if len(marked_values) != len(set(marked_values)):
        raise ValueError("marked branch indices must be distinct")
    if any(value < 0 or value >= K for value in marked_values):
        raise ValueError("marked branch index out of range")
    marked_set = set(marked_values)
    return ParallelBranchRCSP(tuple(int(index in marked_set) for index in range(K)))


def average_search_lower_bound_queries(
    K: int, M: int, target_success: float
) -> float:
    """Continuous necessary bound from the audited random-subset theorem."""
    _validate_search_domain(K, M)
    if M == 0:
        raise ValueError("finding a marked branch requires M >= 1")
    if not 0.0 <= target_success <= 1.0:
        raise ValueError("target_success must lie in [0,1]")
    return float(max(0.0, 0.5 * (math.sqrt(target_success * K / M) - 1.0)))


def query_complexity_scope(K: int, M: int, target_success: float) -> str:
    """State whether a nonzero lower bound is possible at the target success."""
    _validate_search_domain(K, M)
    if M == 0:
        return "NO_FEASIBLE_BRANCH"
    if not 0.0 < target_success <= 1.0:
        raise ValueError("target_success must lie in (0,1]")
    if M / K >= target_success:
        return "ZERO_QUERY_UNIFORM_GUESS_SUFFICES"
    return "THETA_SQRT_K_OVER_M_AT_FIXED_TARGET"


def grover_success_probability(K: int, M: int, queries: int) -> float:
    _validate_search_domain(K, M)
    if queries < 0 or int(queries) != queries:
        raise ValueError("queries must be a nonnegative integer")
    if M == 0:
        return 0.0
    theta = math.asin(math.sqrt(M / K))
    return float(math.sin((2 * int(queries) + 1) * theta) ** 2)


def grover_upper_bound_queries(K: int, M: int) -> int:
    """An O(sqrt(K/M)) query cap; the all-marked endpoint needs none."""
    _validate_search_domain(K, M)
    if M == 0:
        raise ValueError("finding a marked branch requires M >= 1")
    if M == K:
        return 0
    return int(math.ceil((math.pi / 4.0) * math.sqrt(K / M)) + 1)


def exact_search_complexity_class(K: int, M: int) -> str:
    """Exact-success classification, including the M=K degeneracy."""
    _validate_search_domain(K, M)
    if M == 0:
        return "INFEASIBLE_PROMISE"
    if M == K:
        return "ZERO_QUERIES"
    return "THETA_SQRT_K_OVER_M"


def free_array_access_queries(z: Iterable[int]) -> int:
    """A fully supplied free array has no input-query charge (but costs time to scan)."""
    values = tuple(int(value) for value in z)
    if not values or any(value not in (0, 1) for value in values):
        raise ValueError("z must be a nonempty bit array")
    if not any(values):
        raise ValueError("the array has no feasible branch")
    return 0


def _validate_search_domain(K: int, M: int) -> None:
    if K <= 0 or int(K) != K:
        raise ValueError("K must be a positive integer")
    if M < 0 or M > K or int(M) != M:
        raise ValueError("M must be an integer in [0,K]")
