"""Finite-dimensional audit tools for the global dilution query theorem.

The analytic proof is documented separately.  These routines provide exact
complex128 finite-case checks of its identities and inequalities; they are not
a formal proof assistant.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from ..io import PROJECT_ROOT


THEORY_RESULT_ROOT = PROJECT_ROOT / "results/theory_validation_v1"
HISTORICAL_HASH_PATH = THEORY_RESULT_ROOT / "historical_hashes_before.sha256"


def phase_query_coefficient(gamma: float) -> float:
    """Return |exp(-i gamma)-1| in a phase-stable scalar form."""
    return float(2.0 * abs(math.sin(float(gamma) / 2.0)))


def phase_sensitive_bound(N: int, M: int, phases: Sequence[float]) -> float:
    _validate_domain(N, M)
    phi = M / N
    coefficient = 1.0 + sum(phase_query_coefficient(gamma) for gamma in phases)
    return float(min(1.0, coefficient * coefficient * phi))


def coarse_query_bound(N: int, M: int, q: int) -> float:
    _validate_domain(N, M)
    if q < 0:
        raise ValueError("q must be nonnegative")
    return float(min(1.0, (2 * int(q) + 1) ** 2 * (M / N)))


def query_lower_bound(phi: float, target_success: float) -> float:
    if not 0.0 < phi <= 1.0:
        raise ValueError("phi must be in (0,1]")
    if not 0.0 <= target_success <= 1.0:
        raise ValueError("target_success must be in [0,1]")
    return float(max(0.0, 0.5 * (math.sqrt(target_success / phi) - 1.0)))


def _validate_domain(N: int, M: int) -> None:
    if int(N) != N or N <= 0:
        raise ValueError("N must be a positive integer")
    if int(M) != M or not 0 <= M <= N:
        raise ValueError("M must be an integer in [0,N]")


@dataclass(frozen=True)
class QueryAlgorithm:
    """Pure fixed-query algorithm with query-major query/ancilla indexing."""

    N: int
    ancilla_dim: int
    phases: tuple[float, ...]
    initial_state: np.ndarray
    unitaries: tuple[np.ndarray, ...]
    seed: int | None = None

    def __post_init__(self) -> None:
        _validate_domain(self.N, 0)
        if self.ancilla_dim <= 0:
            raise ValueError("ancilla_dim must be positive")
        dimension = self.N * self.ancilla_dim
        initial = np.asarray(self.initial_state, dtype=np.complex128)
        if initial.shape != (dimension,):
            raise ValueError("initial state has the wrong dimension")
        if abs(float(np.vdot(initial, initial).real) - 1.0) > 1e-10:
            raise ValueError("initial state must be normalized")
        if len(self.unitaries) != len(self.phases) + 1:
            raise ValueError("unitaries must contain V_0 through V_q")
        for unitary in self.unitaries:
            matrix = np.asarray(unitary, dtype=np.complex128)
            if matrix.shape != (dimension, dimension):
                raise ValueError("unitary has the wrong dimension")
            identity_error = np.max(
                np.abs(matrix.conj().T @ matrix - np.eye(dimension))
            )
            if identity_error > 1e-10:
                raise ValueError("matrix is not unitary within tolerance")

    @property
    def q(self) -> int:
        return len(self.phases)

    @property
    def dimension(self) -> int:
        return self.N * self.ancilla_dim

    def minimal_reproducer(self) -> dict[str, Any]:
        def complex_array(value: np.ndarray) -> dict[str, Any]:
            array = np.asarray(value)
            return {"real": array.real.tolist(), "imag": array.imag.tolist()}

        return {
            "N": self.N,
            "ancilla_dim": self.ancilla_dim,
            "phases": list(self.phases),
            "seed": self.seed,
            "initial_state": complex_array(self.initial_state),
            "unitaries": [complex_array(unitary) for unitary in self.unitaries],
        }


def random_normalized_state(dimension: int, rng: np.random.Generator) -> np.ndarray:
    vector = rng.normal(size=dimension) + 1j * rng.normal(size=dimension)
    vector = vector.astype(np.complex128)
    return vector / np.linalg.norm(vector)


def haar_like_unitary(dimension: int, rng: np.random.Generator) -> np.ndarray:
    gaussian = rng.normal(size=(dimension, dimension)) + 1j * rng.normal(
        size=(dimension, dimension)
    )
    q_matrix, r_matrix = np.linalg.qr(gaussian.astype(np.complex128))
    diagonal = np.diag(r_matrix)
    phases = np.ones_like(diagonal)
    nonzero = np.abs(diagonal) > 0.0
    phases[nonzero] = diagonal[nonzero] / np.abs(diagonal[nonzero])
    return np.asarray(q_matrix * phases.conj()[None, :], dtype=np.complex128)


def deterministic_algorithm_seed(
    master_seed: int,
    N: int,
    M: int,
    q: int,
    ancilla_dim: int,
    algorithm_index: int,
) -> int:
    payload = f"{master_seed}|{N}|{M}|{q}|{ancilla_dim}|{algorithm_index}"
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def random_query_algorithm(
    N: int, ancilla_dim: int, q: int, *, seed: int
) -> QueryAlgorithm:
    rng = np.random.default_rng(seed)
    dimension = N * ancilla_dim
    return QueryAlgorithm(
        N=N,
        ancilla_dim=ancilla_dim,
        phases=tuple(float(value) for value in rng.uniform(0.0, 2.0 * np.pi, q)),
        initial_state=random_normalized_state(dimension, rng),
        unitaries=tuple(haar_like_unitary(dimension, rng) for _ in range(q + 1)),
        seed=seed,
    )


def feasible_mask(N: int, feasible_set: Iterable[int]) -> np.ndarray:
    mask = np.zeros(N, dtype=bool)
    indices = np.asarray(tuple(int(index) for index in feasible_set), dtype=np.int64)
    if len(indices) and (indices.min() < 0 or indices.max() >= N):
        raise ValueError("feasible-set element out of range")
    if len(indices) != len(set(indices.tolist())):
        raise ValueError("feasible set contains duplicates")
    mask[indices] = True
    return mask


def query_oracle_vector(
    N: int, ancilla_dim: int, feasible_set: Iterable[int], gamma: float
) -> np.ndarray:
    mask = feasible_mask(N, feasible_set)
    query_values = np.ones(N, dtype=np.complex128)
    query_values[mask] = np.exp(-1j * float(gamma))
    return np.repeat(query_values, ancilla_dim)


def projected_norm_squared(
    state: np.ndarray, N: int, ancilla_dim: int, feasible_set: Iterable[int]
) -> float:
    probabilities = np.abs(np.asarray(state).reshape(N, ancilla_dim)) ** 2
    return float(probabilities[feasible_mask(N, feasible_set)].sum())


def simulate_algorithm(
    algorithm: QueryAlgorithm, feasible_set: Iterable[int]
) -> np.ndarray:
    state = algorithm.unitaries[0] @ algorithm.initial_state
    for query_index, gamma in enumerate(algorithm.phases, start=1):
        state = state * query_oracle_vector(
            algorithm.N, algorithm.ancilla_dim, feasible_set, gamma
        )
        state = algorithm.unitaries[query_index] @ state
    return np.asarray(state, dtype=np.complex128)


def reference_states_before_queries(algorithm: QueryAlgorithm) -> tuple[np.ndarray, ...]:
    state = algorithm.unitaries[0] @ algorithm.initial_state
    states: list[np.ndarray] = []
    for query_index in range(1, algorithm.q + 1):
        states.append(np.asarray(state, dtype=np.complex128))
        state = algorithm.unitaries[query_index] @ state
    return tuple(states)


def reference_final_state(algorithm: QueryAlgorithm) -> np.ndarray:
    state = algorithm.unitaries[0] @ algorithm.initial_state
    for query_index in range(1, algorithm.q + 1):
        state = algorithm.unitaries[query_index] @ state
    return np.asarray(state, dtype=np.complex128)


def algorithm_successes(
    algorithm: QueryAlgorithm, feasible_sets: Sequence[Sequence[int]]
) -> np.ndarray:
    """Vectorized successes for a finite uniform or uniform-marginal multiset."""
    count = len(feasible_sets)
    masks = np.zeros((count, algorithm.N), dtype=bool)
    for row, subset in enumerate(feasible_sets):
        masks[row] = feasible_mask(algorithm.N, subset)
    state0 = algorithm.unitaries[0] @ algorithm.initial_state
    states = np.broadcast_to(state0, (count, algorithm.dimension)).copy()
    repeated_mask = np.repeat(masks, algorithm.ancilla_dim, axis=1)
    for query_index, gamma in enumerate(algorithm.phases, start=1):
        phase = np.exp(-1j * float(gamma))
        states *= np.where(repeated_mask, phase, 1.0)
        states = states @ algorithm.unitaries[query_index].T
    probabilities = np.abs(states.reshape(count, algorithm.N, algorithm.ancilla_dim)) ** 2
    return np.einsum("xna,xn->x", probabilities, masks.astype(np.float64))


def all_fixed_size_subsets(N: int, M: int) -> tuple[tuple[int, ...], ...]:
    _validate_domain(N, M)
    return tuple(itertools.combinations(range(N), M))


def balanced_cyclic_subset_sample(
    N: int, M: int, *, orbits: int, seed: int
) -> tuple[tuple[int, ...], ...]:
    """Return N*orbits draws whose one-point inclusion marginals are exactly M/N."""
    _validate_domain(N, M)
    rng = np.random.default_rng(seed)
    draws: list[tuple[int, ...]] = []
    for _ in range(int(orbits)):
        base = tuple(sorted(int(value) for value in rng.choice(N, size=M, replace=False)))
        for shift in range(N):
            draws.append(tuple(sorted((value + shift) % N for value in base)))
    return tuple(draws)


def inclusion_marginal_error(
    N: int, M: int, feasible_sets: Sequence[Sequence[int]]
) -> float:
    counts = np.zeros(N, dtype=np.float64)
    for subset in feasible_sets:
        counts[list(subset)] += 1.0
    marginals = counts / len(feasible_sets)
    return float(np.max(np.abs(marginals - M / N)))


def uniform_subset_projection_expectation(
    state: np.ndarray, N: int, M: int, ancilla_dim: int
) -> float:
    subsets = all_fixed_size_subsets(N, M)
    return float(
        np.mean(
            [projected_norm_squared(state, N, ancilla_dim, subset) for subset in subsets]
        )
    )


def finite_case_validation(
    *,
    master_seed: int = 2026082905,
    tolerance: float = 1e-10,
    failure_path: Path | None = None,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for N in (2, 4, 8, 16):
        for M in range(1, N):
            if N <= 8:
                subsets = all_fixed_size_subsets(N, M)
                algorithms_per_cell = 50
                scheme = "EXHAUSTIVE_UNIFORM"
            else:
                subset_seed = deterministic_algorithm_seed(
                    master_seed, N, M, 0, 1, 999999
                )
                subsets = balanced_cyclic_subset_sample(
                    N, M, orbits=13, seed=subset_seed
                )
                algorithms_per_cell = 25
                scheme = "208_DRAW_BALANCED_CYCLIC_UNIFORM_MARGINAL"
            marginal_error = inclusion_marginal_error(N, M, subsets)
            if marginal_error > 1e-15:
                raise AssertionError("finite subset sample lacks exact uniform marginals")
            for q in (0, 1, 2, 3):
                for ancilla_dim in (1, 2):
                    for algorithm_index in range(algorithms_per_cell):
                        seed = deterministic_algorithm_seed(
                            master_seed, N, M, q, ancilla_dim, algorithm_index
                        )
                        algorithm = random_query_algorithm(
                            N, ancilla_dim, q, seed=seed
                        )
                        successes = algorithm_successes(algorithm, subsets)
                        average = float(successes.mean())
                        phase_bound = phase_sensitive_bound(N, M, algorithm.phases)
                        coarse_bound = coarse_query_bound(N, M, q)
                        phase_residual = average - phase_bound
                        coarse_order_residual = phase_bound - coarse_bound
                        violation = bool(
                            phase_residual > tolerance
                            or coarse_order_residual > tolerance
                        )
                        row = {
                            "N": N,
                            "M": M,
                            "phi": M / N,
                            "q": q,
                            "ancilla_dim": ancilla_dim,
                            "algorithm_index": algorithm_index,
                            "algorithm_seed": seed,
                            "query_phases": json.dumps(list(algorithm.phases)),
                            "n_feasible_set_draws": len(subsets),
                            "n_unique_feasible_sets": len(set(subsets)),
                            "feasible_set_scheme": scheme,
                            "inclusion_marginal_error": marginal_error,
                            "average_success": average,
                            "phase_sensitive_bound": phase_bound,
                            "coarse_bound": coarse_bound,
                            "maximum_pointwise_success": float(successes.max()),
                            "minimum_pointwise_success": float(successes.min()),
                            "phase_bound_residual": phase_residual,
                            "phase_to_coarse_residual": coarse_order_residual,
                            "violation": violation,
                        }
                        rows.append(row)
                        if violation:
                            if failure_path is not None:
                                failure_path.parent.mkdir(parents=True, exist_ok=True)
                                failure_path.write_text(
                                    json.dumps(
                                        {
                                            "row": row,
                                            "feasible_sets": [list(value) for value in subsets],
                                            "algorithm": algorithm.minimal_reproducer(),
                                        },
                                        indent=2,
                                        sort_keys=True,
                                    )
                                    + "\n",
                                    encoding="utf-8",
                                )
                            raise AssertionError(
                                f"numerical theorem violation at seed {seed}"
                            )
    return pd.DataFrame(rows)


def hybrid_trace(
    algorithm: QueryAlgorithm, feasible_set: Sequence[int]
) -> list[dict[str, Any]]:
    true_state = algorithm.unitaries[0] @ algorithm.initial_state
    reference_state = true_state.copy()
    rows: list[dict[str, Any]] = []
    for query_index, gamma in enumerate(algorithm.phases, start=1):
        distance_before = float(np.linalg.norm(true_state - reference_state))
        a_value = math.sqrt(
            projected_norm_squared(
                reference_state,
                algorithm.N,
                algorithm.ancilla_dim,
                feasible_set,
            )
        )
        coefficient = phase_query_coefficient(gamma)
        perturbation = float(
            np.linalg.norm(
                (query_oracle_vector(
                    algorithm.N, algorithm.ancilla_dim, feasible_set, gamma
                ) - 1.0)
                * reference_state
            )
        )
        true_state = true_state * query_oracle_vector(
            algorithm.N, algorithm.ancilla_dim, feasible_set, gamma
        )
        true_state = algorithm.unitaries[query_index] @ true_state
        reference_state = algorithm.unitaries[query_index] @ reference_state
        distance_after = float(np.linalg.norm(true_state - reference_state))
        recursion_rhs = distance_before + coefficient * a_value
        rows.append(
            {
                "row_type": "QUERY_STEP",
                "query_index": query_index,
                "gamma": gamma,
                "c_t": coefficient,
                "a_t": a_value,
                "d_before": distance_before,
                "single_query_perturbation": perturbation,
                "c_t_a_t": coefficient * a_value,
                "d_after": distance_after,
                "recursion_rhs": recursion_rhs,
                "recursion_residual": distance_after - recursion_rhs,
                "single_query_identity_residual": perturbation - coefficient * a_value,
            }
        )
    success = projected_norm_squared(
        true_state, algorithm.N, algorithm.ancilla_dim, feasible_set
    )
    reference_success = projected_norm_squared(
        reference_state, algorithm.N, algorithm.ancilla_dim, feasible_set
    )
    final_distance = float(np.linalg.norm(true_state - reference_state))
    rows.append(
        {
            "row_type": "FINAL_PROJECTION",
            "query_index": algorithm.q,
            "final_success": success,
            "reference_success": reference_success,
            "d_final": final_distance,
            "sqrt_success": math.sqrt(success),
            "sqrt_reference_plus_distance": math.sqrt(reference_success)
            + final_distance,
            "final_projection_residual": math.sqrt(success)
            - math.sqrt(reference_success)
            - final_distance,
        }
    )
    return rows


def hybrid_trace_examples(master_seed: int = 2026082906) -> pd.DataFrame:
    examples = ((4, 1, 2, 2), (8, 3, 3, 1))
    output: list[dict[str, Any]] = []
    for example_index, (N, M, q, ancilla_dim) in enumerate(examples):
        seed = deterministic_algorithm_seed(
            master_seed, N, M, q, ancilla_dim, example_index
        )
        algorithm = random_query_algorithm(N, ancilla_dim, q, seed=seed)
        subsets = all_fixed_size_subsets(N, M)
        final_distances = []
        a_squared = [[] for _ in range(q)]
        final_successes = []
        reference_successes = []
        for subset_index, subset in enumerate(subsets):
            trace = hybrid_trace(algorithm, subset)
            for row in trace:
                output.append(
                    {
                        "example_id": example_index,
                        "N": N,
                        "M": M,
                        "q": q,
                        "ancilla_dim": ancilla_dim,
                        "algorithm_seed": seed,
                        "feasible_set_index": subset_index,
                        "feasible_set": json.dumps(list(subset)),
                        **row,
                    }
                )
            query_rows = [row for row in trace if row["row_type"] == "QUERY_STEP"]
            final = trace[-1]
            final_distances.append(final["d_final"])
            final_successes.append(final["final_success"])
            reference_successes.append(final["reference_success"])
            for index, row in enumerate(query_rows):
                a_squared[index].append(row["a_t"] ** 2)
        lhs = math.sqrt(float(np.mean(np.square(final_distances))))
        rhs = math.sqrt(M / N) * sum(
            phase_query_coefficient(value) for value in algorithm.phases
        )
        success_lhs = math.sqrt(float(np.mean(final_successes)))
        success_rhs = math.sqrt(float(np.mean(reference_successes))) + lhs
        output.append(
            {
                "example_id": example_index,
                "N": N,
                "M": M,
                "q": q,
                "ancilla_dim": ancilla_dim,
                "algorithm_seed": seed,
                "row_type": "L2_AGGREGATE",
                "l2_distance_lhs": lhs,
                "l2_minkowski_rhs": rhs,
                "l2_residual": lhs - rhs,
                "sqrt_average_success": success_lhs,
                "sqrt_average_reference_plus_l2_distance": success_rhs,
                "average_success_projection_residual": success_lhs - success_rhs,
                "maximum_a_squared_expectation_error": max(
                    abs(float(np.mean(values)) - M / N) for values in a_squared
                ),
            }
        )
    return pd.DataFrame(output)


def grover_formula_success(N: int, M: int, q: int) -> float:
    _validate_domain(N, M)
    if not 0 < M < N:
        return float(M == N)
    theta = math.asin(math.sqrt(M / N))
    return float(math.sin((2 * q + 1) * theta) ** 2)


def grover_numerical_success(N: int, M: int, q: int) -> float:
    _validate_domain(N, M)
    if M == 0:
        return 0.0
    if M == N:
        return 1.0
    marked = tuple(range(M))
    state = np.full(N, 1.0 / math.sqrt(N), dtype=np.complex128)
    uniform = state.copy()
    oracle = query_oracle_vector(N, 1, marked, math.pi)
    for _ in range(q):
        state *= oracle
        state = 2.0 * uniform * np.vdot(uniform, state) - state
    return projected_norm_squared(state, N, 1, marked)


def first_grover_success_maximum(N: int, M: int) -> int:
    previous = grover_formula_success(N, M, 0)
    for q in range(0, 10 * N + 1):
        following = grover_formula_success(N, M, q + 1)
        if following <= previous + 1e-15:
            return q
        previous = following
    raise RuntimeError("failed to locate first Grover success maximum")


def grover_validation(tolerance: float = 1e-12) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for N in (8, 16, 32, 64):
        m_values = sorted({1, max(1, N // 16), max(1, N // 8), N // 4, N // 2})
        for M in (value for value in m_values if 0 < value < N):
            q_max = first_grover_success_maximum(N, M)
            for q in range(q_max + 1):
                numerical = grover_numerical_success(N, M, q)
                formula = grover_formula_success(N, M, q)
                error = abs(numerical - formula)
                if error > tolerance:
                    raise AssertionError(
                        f"Grover formula mismatch N={N} M={M} q={q}: {error}"
                    )
                phi = M / N
                leading = (2 * q + 1) ** 2 * phi
                rows.append(
                    {
                        "N": N,
                        "M": M,
                        "phi": phi,
                        "q": q,
                        "first_success_maximum_q": q_max,
                        "grover_success_numerical": numerical,
                        "grover_success_formula": formula,
                        "formula_absolute_error": error,
                        "phase_sensitive_bound": phase_sensitive_bound(
                            N, M, [math.pi] * q
                        ),
                        "coarse_bound": coarse_query_bound(N, M, q),
                        "leading_dilute_term": leading,
                        "leading_term_residual": numerical - leading,
                        "q_squared_phi": q * q * phi,
                    }
                )
    return pd.DataFrame(rows)


def invalid_assumption_examples() -> pd.DataFrame:
    examples = [
        {
            "example_id": "F_DEPENDENT_INITIAL_GOOD_SUPERPOSITION",
            "construction": "Prepare |G_F> directly and use q=0.",
            "apparent_success": 1.0,
            "violated_assumption": "Initial state is independent of F.",
            "status": "OUTSIDE_THEOREM_CLASS",
            "hidden_resource": "Knowledge and preparation of the marked set.",
        },
        {
            "example_id": "F_DEPENDENT_UNITARY",
            "construction": "Use a unitary V_F mapping |0> to one marked basis state.",
            "apparent_success": 1.0,
            "violated_assumption": "All inter-query unitaries are independent of F.",
            "status": "OUTSIDE_THEOREM_CLASS",
            "hidden_resource": "An F-dependent compiled operation.",
        },
        {
            "example_id": "CLASSICALLY_ENUMERATED_F",
            "construction": "Enumerate F classically, then prepare a listed feasible item.",
            "apparent_success": 1.0,
            "violated_assumption": "All information about F enters through counted phase queries.",
            "status": "OUTSIDE_THEOREM_CLASS",
            "hidden_resource": "Uncounted classical enumeration and data loading.",
        },
        {
            "example_id": "KNOWN_PREFIX_STRUCTURE",
            "construction": "For a known fixed-prefix feasible family, prepare the prefix and uniform suffix.",
            "apparent_success": 1.0,
            "violated_assumption": "The feasible set is an unstructured unknown marked subset.",
            "status": "OUTSIDE_THEOREM_CLASS",
            "hidden_resource": "A succinct structural description of F.",
        },
    ]
    return pd.DataFrame(examples)


def verify_historical_hashes(path: Path | None = None) -> dict[str, Any]:
    path = path or HISTORICAL_HASH_PATH
    expected: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        expected[relative] = digest
    changed = []
    for relative, digest in expected.items():
        candidate = PROJECT_ROOT / relative
        observed = hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.is_file() else None
        if observed != digest:
            changed.append(relative)
    if changed:
        raise RuntimeError(f"historical scientific artifacts changed: {changed}")
    canonical = "".join(f"{digest}  {relative}\n" for relative, digest in expected.items())
    return {
        "file_count": len(expected),
        "inventory_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "unchanged": True,
    }
