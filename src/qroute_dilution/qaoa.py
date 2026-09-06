"""Dependency-light exact-statevector QAOA primitives."""

from __future__ import annotations

import numpy as np


def plus_state(n_qubits: int) -> np.ndarray:
    if n_qubits < 0:
        raise ValueError("n_qubits must be nonnegative")
    return np.full(1 << n_qubits, 1 / np.sqrt(1 << n_qubits), dtype=np.complex128)


def apply_cost_layer(state: np.ndarray, energies: np.ndarray, gamma: float) -> np.ndarray:
    if state.shape != energies.shape:
        raise ValueError("state and energies must have the same shape")
    return state * np.exp(-1j * float(gamma) * energies)


def apply_x_mixer(state: np.ndarray, beta: float, n_qubits: int) -> np.ndarray:
    """Apply exp(-i beta sum_j X_j) using pairwise amplitude updates."""
    if state.shape != (1 << n_qubits,):
        raise ValueError("state length does not match n_qubits")
    mixed = np.asarray(state, dtype=np.complex128).copy()
    cosine = np.cos(float(beta))
    sine = np.sin(float(beta))
    for qubit in range(n_qubits):
        half_block = 1 << qubit
        blocks = mixed.reshape(-1, 2 * half_block)
        low = blocks[:, :half_block].copy()
        high = blocks[:, half_block:].copy()
        blocks[:, :half_block] = cosine * low - 1j * sine * high
        blocks[:, half_block:] = cosine * high - 1j * sine * low
    return mixed


def simulate_qaoa(parameters: np.ndarray, energies: np.ndarray, depth: int) -> np.ndarray:
    parameters = np.asarray(parameters, dtype=np.float64)
    if parameters.shape != (2 * depth,):
        raise ValueError("parameters must contain depth gammas followed by depth betas")
    n_qubits = int(np.log2(len(energies)))
    if (1 << n_qubits) != len(energies):
        raise ValueError("energy vector length must be a power of two")
    gammas = parameters[:depth]
    betas = parameters[depth:]
    state = plus_state(n_qubits)
    for gamma, beta in zip(gammas, betas):
        state = apply_cost_layer(state, energies, gamma)
        state = apply_x_mixer(state, beta, n_qubits)
    return state


def expected_energy(state: np.ndarray, energies: np.ndarray) -> float:
    probabilities = np.abs(state) ** 2
    return float(np.dot(probabilities, energies))


def qaoa_objective(parameters: np.ndarray, energies: np.ndarray, depth: int) -> float:
    return expected_energy(simulate_qaoa(parameters, energies, depth), energies)
