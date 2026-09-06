"""Adaptive hard-cap extensions of the global dilution query bound.

The analytic proof lives in the v2 theorem documents.  This module keeps the
model constants, deterministic finite-case protocol generator, query
accounting, and expected-query counterexample executable.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from dataclasses import dataclass
from typing import Iterable, Literal, Mapping, Sequence

import numpy as np

from .global_dilution_bound import (
    coarse_query_bound,
    haar_like_unitary,
    phase_query_coefficient,
    random_normalized_state,
)


OracleModel = Literal["phase_flip", "membership_bit", "branch_phase"]


def branch_phase_coefficient(phases: Iterable[float]) -> float:
    """Operator-norm coefficient for a history-controlled phase query."""
    values = tuple(float(value) for value in phases)
    return max((phase_query_coefficient(value) for value in values), default=0.0)


def adaptive_phase_bound(N: int, M: int, slot_coefficients: Sequence[float]) -> float:
    """Hard-cap bound with one controlled phase coefficient per query slot."""
    if N <= 0 or not 0 <= M <= N:
        raise ValueError("require N > 0 and 0 <= M <= N")
    if any(not 0.0 <= coefficient <= 2.0 + 1e-15 for coefficient in slot_coefficients):
        raise ValueError("slot coefficients must lie in [0,2]")
    scale = 1.0 + sum(float(value) for value in slot_coefficients)
    return float(min(1.0, scale * scale * M / N))


def expected_query_truncation_bound(
    N: int, M: int, expected_queries: float, threshold: int
) -> float:
    """Rigorous bound from truncation plus integer-valued Markov.

    The event Q > T is the event Q >= T+1, hence its probability is at most
    E[Q]/(T+1).  The truncated protocol has hard cap T.
    """
    if expected_queries < 0.0:
        raise ValueError("expected_queries must be nonnegative")
    if threshold < 0:
        raise ValueError("threshold must be nonnegative")
    tail = min(1.0, float(expected_queries) / (threshold + 1.0))
    return float(min(1.0, tail + coarse_query_bound(N, M, threshold)))


def optimized_expected_query_bound(
    N: int, M: int, expected_queries: float, max_threshold: int | None = None
) -> tuple[float, int]:
    """Minimize the valid truncation bound over deterministic thresholds."""
    if max_threshold is None:
        phi = max(M / N, np.finfo(float).tiny)
        scale = (max(expected_queries, 1.0) / phi) ** (1.0 / 3.0)
        max_threshold = max(16, int(math.ceil(4.0 * scale)))
    candidates = [
        expected_query_truncation_bound(N, M, expected_queries, threshold)
        for threshold in range(max_threshold + 1)
    ]
    best = int(np.argmin(candidates))
    return float(candidates[best]), best


def rare_long_branch_counterexample(
    phi: float, long_queries: int, branch_probability: float
) -> dict[str, float | bool]:
    """A mixture showing why a mean cap cannot enter the hard-cap formula.

    The long branch runs the standard Grover construction for the supplied
    number of queries.  The short branch is uniform guessing with success phi.
    """
    if not 0.0 < phi < 1.0:
        raise ValueError("phi must lie in (0,1)")
    if long_queries <= 0 or not 0.0 < branch_probability < 1.0:
        raise ValueError("invalid branch parameters")
    mean_queries = branch_probability * long_queries
    theta = math.asin(math.sqrt(phi))
    grover_success = math.sin((2 * long_queries + 1) * theta) ** 2
    success = (
        branch_probability * grover_success
        + (1.0 - branch_probability) * phi
    )
    naive = min(1.0, (2.0 * mean_queries + 1.0) ** 2 * phi)
    expected_square = (
        branch_probability * (2 * long_queries + 1) ** 2
        + (1.0 - branch_probability)
    ) * phi
    return {
        "phi": phi,
        "long_queries": float(long_queries),
        "branch_probability": branch_probability,
        "expected_queries": mean_queries,
        "long_branch_grover_success": grover_success,
        "mixture_success": success,
        "naive_mean_substitution_bound": naive,
        "expected_square_bound": min(1.0, expected_square),
        "violates_naive_substitution": bool(success > naive),
    }


@dataclass(frozen=True)
class TrainedRound:
    """One variational round with exact per-circuit depth and shot counts."""

    query_depths: tuple[int, ...]
    shots: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.query_depths) != len(self.shots):
            raise ValueError("query_depths and shots must have equal length")
        if any(value < 0 for value in self.query_depths + self.shots):
            raise ValueError("query counts and shots must be nonnegative")

    @property
    def queries(self) -> int:
        return int(sum(depth * shots for depth, shots in zip(self.query_depths, self.shots)))


def total_trained_queries(rounds: Sequence[TrainedRound], final_queries: int = 0) -> int:
    if final_queries < 0:
        raise ValueError("final_queries must be nonnegative")
    return int(sum(round_.queries for round_ in rounds) + final_queries)


@dataclass(frozen=True)
class AdaptiveProtocol:
    """Small deterministic adaptive protocol used for adversarial validation.

    Histories consist of an optional randomized-control bit followed by
    intermediate projective-measurement outcomes.  Every phase and unitary is
    generated without reference to the feasible set.
    """

    N: int
    q: int
    ancilla_dim: int
    oracle_model: OracleModel
    seed: int
    initial_states: Mapping[tuple[int, ...], np.ndarray]
    initial_weights: Mapping[tuple[int, ...], float]
    unitaries: Mapping[tuple[int, tuple[int, ...]], np.ndarray]
    phases: Mapping[tuple[int, tuple[int, ...]], float]
    measure_between_slots: bool
    early_stop: bool
    randomized_control: bool

    @property
    def work_dim(self) -> int:
        return self.ancilla_dim * (2 if self.oracle_model == "membership_bit" else 1)

    @property
    def dimension(self) -> int:
        return self.N * self.work_dim

    def phase_coefficients(self) -> tuple[float, ...]:
        if self.oracle_model == "membership_bit":
            return tuple(2.0 for _ in range(self.q))
        by_slot: list[float] = []
        for slot in range(self.q):
            slot_phases = [
                phase for (key_slot, _), phase in self.phases.items() if key_slot == slot
            ]
            by_slot.append(branch_phase_coefficient(slot_phases))
        return tuple(by_slot)


def _seed_from(*values: object) -> int:
    payload = "|".join(str(value) for value in values)
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def possible_histories(q: int, randomized_control: bool) -> tuple[tuple[int, ...], ...]:
    prefixes = ((0,), (1,)) if randomized_control else ((),)
    histories: list[tuple[int, ...]] = []
    for prefix in prefixes:
        histories.append(prefix)
        for length in range(1, q):
            histories.extend(prefix + suffix for suffix in itertools.product((0, 1), repeat=length))
    return tuple(sorted(set(histories), key=lambda value: (len(value), value)))


def random_adaptive_protocol(
    N: int,
    q: int,
    ancilla_dim: int,
    oracle_model: OracleModel,
    *,
    seed: int,
    measure_between_slots: bool = True,
    early_stop: bool = False,
    randomized_control: bool = False,
) -> AdaptiveProtocol:
    if N <= 0 or q < 0 or ancilla_dim <= 0:
        raise ValueError("invalid protocol dimensions")
    work_dim = ancilla_dim * (2 if oracle_model == "membership_bit" else 1)
    dimension = N * work_dim
    initial_histories = ((0,), (1,)) if randomized_control else ((),)
    initial_states: dict[tuple[int, ...], np.ndarray] = {}
    initial_weights: dict[tuple[int, ...], float] = {}
    for history in initial_histories:
        rng = np.random.default_rng(_seed_from(seed, "initial", history))
        initial_states[history] = random_normalized_state(dimension, rng)
        initial_weights[history] = 1.0 / len(initial_histories)

    unitaries: dict[tuple[int, tuple[int, ...]], np.ndarray] = {}
    phases: dict[tuple[int, tuple[int, ...]], float] = {}
    random_prefix_length = 1 if randomized_control else 0
    for slot in range(q):
        measurement_count = slot if measure_between_slots else 0
        for prefix in initial_histories:
            suffixes = itertools.product((0, 1), repeat=measurement_count)
            for suffix in suffixes:
                history = prefix + tuple(suffix)
                rng = np.random.default_rng(_seed_from(seed, "unitary", slot, history))
                unitaries[(slot, history)] = haar_like_unitary(dimension, rng)
                if oracle_model == "phase_flip":
                    phases[(slot, history)] = math.pi
                elif oracle_model == "branch_phase":
                    phase_seed = _seed_from(seed, "phase", slot, history)
                    phases[(slot, history)] = float(
                        2.0 * math.pi * ((phase_seed % 1_000_003) / 1_000_003.0)
                    )
    # Silence an otherwise easy-to-miss malformed history convention.
    if any(len(history) < random_prefix_length for history in initial_states):
        raise AssertionError("invalid randomized history")
    return AdaptiveProtocol(
        N=N,
        q=q,
        ancilla_dim=ancilla_dim,
        oracle_model=oracle_model,
        seed=seed,
        initial_states=initial_states,
        initial_weights=initial_weights,
        unitaries=unitaries,
        phases=phases,
        measure_between_slots=measure_between_slots,
        early_stop=early_stop,
        randomized_control=randomized_control,
    )


def marked_projected_norm_squared(
    state: np.ndarray, protocol: AdaptiveProtocol, feasible_set: Sequence[int]
) -> float:
    reshaped = np.asarray(state).reshape(protocol.N, protocol.work_dim)
    return float(np.sum(np.abs(reshaped[np.asarray(feasible_set, dtype=int)]) ** 2))


def query_distribution(state: np.ndarray, protocol: AdaptiveProtocol) -> np.ndarray:
    reshaped = np.asarray(state).reshape(protocol.N, protocol.work_dim)
    return np.sum(np.abs(reshaped) ** 2, axis=1).real


def apply_query(
    state: np.ndarray,
    protocol: AdaptiveProtocol,
    feasible_set: Sequence[int],
    slot: int,
    history: tuple[int, ...],
) -> np.ndarray:
    result = np.asarray(state, dtype=np.complex128).copy()
    marked = np.asarray(feasible_set, dtype=int)
    if protocol.oracle_model == "membership_bit":
        tensor = result.reshape(protocol.N, 2, protocol.ancilla_dim)
        tensor[marked] = tensor[marked][:, ::-1, :]
        return tensor.reshape(-1)
    gamma = protocol.phases[(slot, history)]
    tensor = result.reshape(protocol.N, protocol.work_dim)
    tensor[marked] *= np.exp(-1j * gamma)
    return tensor.reshape(-1)


def measurement_masks(protocol: AdaptiveProtocol) -> tuple[np.ndarray, np.ndarray]:
    """Two fixed projectors, independent of the feasible set."""
    if protocol.work_dim > 1:
        labels = np.tile(np.arange(protocol.work_dim), protocol.N)
        first = labels % 2 == 0
    else:
        query_labels = np.repeat(np.arange(protocol.N), protocol.work_dim)
        first = query_labels % 2 == 0
    return first, ~first


def protocol_identifier(protocol: AdaptiveProtocol) -> str:
    return (
        f"N{protocol.N}_q{protocol.q}_a{protocol.ancilla_dim}_"
        f"{protocol.oracle_model}_s{protocol.seed}_m{int(protocol.measure_between_slots)}_"
        f"e{int(protocol.early_stop)}_r{int(protocol.randomized_control)}"
    )
