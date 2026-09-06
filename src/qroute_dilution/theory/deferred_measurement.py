"""Direct and purified simulations of small adaptive query protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .adaptive_query_bound import (
    AdaptiveProtocol,
    apply_query,
    marked_projected_norm_squared,
    measurement_masks,
    query_distribution,
)


@dataclass
class DirectBranch:
    probability: float
    state: np.ndarray
    history: tuple[int, ...]
    stopped: bool
    actual_queries: int


@dataclass
class PurifiedBranch:
    """One orthogonal history/environment block of a global pure state."""

    amplitude: np.ndarray
    history: tuple[int, ...]
    stopped: bool
    actual_queries: int


@dataclass
class PaddedBranch:
    """Purified branch with an isolated scratch oracle register."""

    amplitude: np.ndarray
    scratch: np.ndarray
    history: tuple[int, ...]
    stopped: bool
    actual_queries: int


@dataclass(frozen=True)
class SimulationResult:
    success: float
    output_distribution: np.ndarray
    query_counts: tuple[int, ...]
    branch_weights: tuple[float, ...]


def _should_stop(protocol: AdaptiveProtocol, slot: int, outcome: int) -> bool:
    return bool(protocol.early_stop and outcome == 1 and slot + 1 < protocol.q)


def simulate_direct(
    protocol: AdaptiveProtocol, feasible_set: Sequence[int]
) -> SimulationResult:
    branches = [
        DirectBranch(weight, state.copy(), history, False, 0)
        for history, state in protocol.initial_states.items()
        for weight in (protocol.initial_weights[history],)
    ]
    masks = measurement_masks(protocol)
    for slot in range(protocol.q):
        evolved: list[DirectBranch] = []
        for branch in branches:
            if branch.stopped:
                evolved.append(branch)
                continue
            state = apply_query(
                branch.state, protocol, feasible_set, slot, branch.history
            )
            state = protocol.unitaries[(slot, branch.history)] @ state
            query_count = branch.actual_queries + 1
            if protocol.measure_between_slots and slot + 1 < protocol.q:
                for outcome, mask in enumerate(masks):
                    projected = state * mask
                    conditional = float(np.vdot(projected, projected).real)
                    if conditional <= 1e-16:
                        continue
                    evolved.append(
                        DirectBranch(
                            probability=branch.probability * conditional,
                            state=projected / math_sqrt(conditional),
                            history=branch.history + (outcome,),
                            stopped=_should_stop(protocol, slot, outcome),
                            actual_queries=query_count,
                        )
                    )
            else:
                evolved.append(
                    DirectBranch(
                        branch.probability,
                        state,
                        branch.history,
                        False,
                        query_count,
                    )
                )
        branches = evolved
    distribution = np.zeros(protocol.N, dtype=float)
    for branch in branches:
        distribution += branch.probability * query_distribution(branch.state, protocol)
    success = float(distribution[np.asarray(feasible_set, dtype=int)].sum())
    return SimulationResult(
        success=success,
        output_distribution=distribution,
        query_counts=tuple(branch.actual_queries for branch in branches),
        branch_weights=tuple(branch.probability for branch in branches),
    )


def simulate_purified(
    protocol: AdaptiveProtocol, feasible_set: Sequence[int]
) -> SimulationResult:
    """Defer measurements by retaining orthogonal history blocks.

    Each vector is unnormalized; its squared norm is its branch weight.  The
    omitted explicit tensor product with |history>|environment> is lossless
    because distinct dictionary branches represent orthogonal basis states and
    no later unitary mixes those registers.
    """
    branches = [
        PurifiedBranch(
            math_sqrt(protocol.initial_weights[history]) * state.copy(),
            history,
            False,
            0,
        )
        for history, state in protocol.initial_states.items()
    ]
    masks = measurement_masks(protocol)
    for slot in range(protocol.q):
        evolved: list[PurifiedBranch] = []
        for branch in branches:
            if branch.stopped:
                evolved.append(branch)
                continue
            amplitude = apply_query(
                branch.amplitude, protocol, feasible_set, slot, branch.history
            )
            amplitude = protocol.unitaries[(slot, branch.history)] @ amplitude
            query_count = branch.actual_queries + 1
            if protocol.measure_between_slots and slot + 1 < protocol.q:
                for outcome, mask in enumerate(masks):
                    projected = amplitude * mask
                    if float(np.vdot(projected, projected).real) <= 1e-16:
                        continue
                    evolved.append(
                        PurifiedBranch(
                            projected,
                            branch.history + (outcome,),
                            _should_stop(protocol, slot, outcome),
                            query_count,
                        )
                    )
            else:
                evolved.append(
                    PurifiedBranch(
                        amplitude, branch.history, False, query_count
                    )
                )
        branches = evolved
    distribution = np.zeros(protocol.N, dtype=float)
    weights: list[float] = []
    for branch in branches:
        weight = float(np.vdot(branch.amplitude, branch.amplitude).real)
        weights.append(weight)
        distribution += query_distribution(branch.amplitude, protocol)
    success = float(distribution[np.asarray(feasible_set, dtype=int)].sum())
    return SimulationResult(
        success=success,
        output_distribution=distribution,
        query_counts=tuple(branch.actual_queries for branch in branches),
        branch_weights=tuple(weights),
    )


def _apply_padding_query(
    scratch: np.ndarray,
    protocol: AdaptiveProtocol,
    feasible_set: Sequence[int],
) -> np.ndarray:
    """Apply the ordinary fixed oracle to isolated halted-branch scratch."""
    result = np.asarray(scratch, dtype=np.complex128).copy()
    marked = np.asarray(feasible_set, dtype=int)
    if protocol.oracle_model == "membership_bit":
        tensor = result.reshape(protocol.N, 2, protocol.ancilla_dim)
        tensor[marked] = tensor[marked][:, ::-1, :]
        return tensor.reshape(-1)
    if protocol.oracle_model == "phase_flip":
        tensor = result.reshape(protocol.N, protocol.work_dim)
        tensor[marked] *= -1.0
        return tensor.reshape(-1)
    # In the controlled-phase interface, a halted transcript selects gamma=0.
    return result


def simulate_purified_padded(
    protocol: AdaptiveProtocol, feasible_set: Sequence[int]
) -> SimulationResult:
    """Purified simulation with every early branch padded to exactly q slots."""
    scratch = np.zeros(protocol.dimension, dtype=np.complex128)
    scratch[0] = 1.0
    branches = [
        PaddedBranch(
            math_sqrt(protocol.initial_weights[history]) * state.copy(),
            scratch.copy(),
            history,
            False,
            0,
        )
        for history, state in protocol.initial_states.items()
    ]
    masks = measurement_masks(protocol)
    for slot in range(protocol.q):
        evolved: list[PaddedBranch] = []
        for branch in branches:
            if branch.stopped:
                evolved.append(
                    PaddedBranch(
                        branch.amplitude,
                        _apply_padding_query(branch.scratch, protocol, feasible_set),
                        branch.history,
                        True,
                        branch.actual_queries + 1,
                    )
                )
                continue
            amplitude = apply_query(
                branch.amplitude, protocol, feasible_set, slot, branch.history
            )
            amplitude = protocol.unitaries[(slot, branch.history)] @ amplitude
            query_count = branch.actual_queries + 1
            if protocol.measure_between_slots and slot + 1 < protocol.q:
                for outcome, mask in enumerate(masks):
                    projected = amplitude * mask
                    if float(np.vdot(projected, projected).real) <= 1e-16:
                        continue
                    evolved.append(
                        PaddedBranch(
                            projected,
                            branch.scratch.copy(),
                            branch.history + (outcome,),
                            _should_stop(protocol, slot, outcome),
                            query_count,
                        )
                    )
            else:
                evolved.append(
                    PaddedBranch(
                        amplitude,
                        branch.scratch,
                        branch.history,
                        False,
                        query_count,
                    )
                )
        branches = evolved
    distribution = np.zeros(protocol.N, dtype=float)
    weights: list[float] = []
    for branch in branches:
        scratch_norm = float(np.vdot(branch.scratch, branch.scratch).real)
        if abs(scratch_norm - 1.0) > 1e-12:
            raise AssertionError("padding query failed to preserve scratch norm")
        weight = float(np.vdot(branch.amplitude, branch.amplitude).real)
        weights.append(weight)
        distribution += query_distribution(branch.amplitude, protocol)
    return SimulationResult(
        success=float(distribution[np.asarray(feasible_set, dtype=int)].sum()),
        output_distribution=distribution,
        query_counts=tuple(branch.actual_queries for branch in branches),
        branch_weights=tuple(weights),
    )


def coherent_hybrid_trace(
    protocol: AdaptiveProtocol, feasible_set: Sequence[int]
) -> list[dict[str, float | int]]:
    """Trace the hybrid recursion in orthogonal purified history blocks."""
    true_branches = [
        PurifiedBranch(
            math_sqrt(protocol.initial_weights[history]) * state.copy(),
            history,
            False,
            0,
        )
        for history, state in protocol.initial_states.items()
    ]
    reference_branches = [
        PurifiedBranch(branch.amplitude.copy(), branch.history, False, 0)
        for branch in true_branches
    ]
    masks = measurement_masks(protocol)
    rows: list[dict[str, float | int]] = []

    def blocks(branches: list[PurifiedBranch]) -> dict[tuple[int, ...], np.ndarray]:
        return {branch.history: branch.amplitude for branch in branches}

    def distance(left: list[PurifiedBranch], right: list[PurifiedBranch]) -> float:
        left_map, right_map = blocks(left), blocks(right)
        histories = set(left_map) | set(right_map)
        total = 0.0
        for history in histories:
            zero = np.zeros(protocol.dimension, dtype=np.complex128)
            delta = left_map.get(history, zero) - right_map.get(history, zero)
            total += float(np.vdot(delta, delta).real)
        return math_sqrt(total)

    for slot in range(protocol.q):
        distance_before = distance(true_branches, reference_branches)
        reference_marked = math_sqrt(
            sum(
                marked_projected_norm_squared(
                    branch.amplitude, protocol, feasible_set
                )
                for branch in reference_branches
                if not branch.stopped
            )
        )
        coefficient = protocol.phase_coefficients()[slot]
        queried_true: list[PurifiedBranch] = []
        for branch in true_branches:
            amplitude = branch.amplitude
            if not branch.stopped:
                amplitude = apply_query(
                    amplitude, protocol, feasible_set, slot, branch.history
                )
            queried_true.append(
                PurifiedBranch(
                    amplitude, branch.history, branch.stopped, branch.actual_queries
                )
            )
        distance_after_query = distance(queried_true, reference_branches)

        def post_query_map(
            branches: list[PurifiedBranch], *, queried: bool
        ) -> list[PurifiedBranch]:
            output: list[PurifiedBranch] = []
            for branch in branches:
                if branch.stopped:
                    output.append(branch)
                    continue
                amplitude = protocol.unitaries[(slot, branch.history)] @ branch.amplitude
                count = branch.actual_queries + (1 if queried else 0)
                if protocol.measure_between_slots and slot + 1 < protocol.q:
                    for outcome, mask in enumerate(masks):
                        projected = amplitude * mask
                        if float(np.vdot(projected, projected).real) <= 1e-16:
                            continue
                        output.append(
                            PurifiedBranch(
                                projected,
                                branch.history + (outcome,),
                                _should_stop(protocol, slot, outcome),
                                count,
                            )
                        )
                else:
                    output.append(
                        PurifiedBranch(amplitude, branch.history, False, count)
                    )
            return output

        true_branches = post_query_map(queried_true, queried=True)
        reference_branches = post_query_map(reference_branches, queried=False)
        distance_after = distance(true_branches, reference_branches)
        rows.append(
            {
                "slot": slot + 1,
                "distance_before": distance_before,
                "reference_marked_norm": reference_marked,
                "coefficient": coefficient,
                "single_step_bound": coefficient * reference_marked,
                "distance_after_query": distance_after_query,
                "distance_after": distance_after,
                "recursion_residual": distance_after
                - distance_before
                - coefficient * reference_marked,
            }
        )
    return rows


def math_sqrt(value: float) -> float:
    return float(np.sqrt(max(0.0, float(value))))
