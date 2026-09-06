"""Orthogonal cost ledger for structure-injected RCSP/QAOA methods."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

import pandas as pd


class EvidenceStatus(str, Enum):
    MEASURED = "MEASURED"
    DERIVED = "DERIVED"
    BOUNDED = "BOUNDED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


RESOURCE_CONTRACT: dict[str, tuple[str, ...]] = {
    "information_resource": (
        "classical_advice_bits",
        "effective_structure_bits_b_eff",
        "candidate_effective_support_K_eff",
        "explicit_instance_bytes",
        "learned_parameter_bytes",
        "feasible_list_size",
    ),
    "classical_computation": (
        "preprocessing_wall_time",
        "candidate_generation",
        "corridor_construction",
        "constraint_propagation",
        "relaxation",
        "repair",
        "feasible_set_enumeration",
        "mixer_graph_construction",
        "parameter_transfer_training",
    ),
    "quantum_state_preparation": (
        "state_preparation_depth",
        "state_preparation_1q_2q_gates",
        "ancillas",
        "amplitude_loading_calls",
        "postselection_probability",
        "retries",
    ),
    "structured_mixer": (
        "mixer_description_size",
        "mixer_compilation_time",
        "mixer_gate_depth",
        "mixer_two_qubit_gates",
        "neighbor_oracle_calls",
        "trotter_steps",
        "connectivity_overhead",
    ),
    "query_oracle": (
        "membership_queries",
        "rich_cost_queries",
        "feasible_neighbor_queries",
        "attribute_queries",
        "training_queries",
        "sampling_queries",
        "final_execution_queries",
    ),
    "verification_decoding": (
        "route_decoding",
        "constraint_validation",
        "objective_validation",
        "repair_after_invalid_sample",
    ),
    "dynamic_reuse": (
        "one_time_build_cost",
        "per_instance_cost",
        "cache_identity",
        "reuse_fraction",
        "patch_cost",
        "rebuild_cost",
        "amortization_horizon",
    ),
}


@dataclass(frozen=True)
class MethodRecord:
    method: str
    injected_structure: str
    theorem_class: str
    phi_effect: str
    Lambda_effect: str
    relocated_burden: str
    measured: str
    derived: str
    bounded: str
    unknown: str
    not_applicable: str
    readiness: str


METHODS: tuple[MethodRecord, ...] = (
    MethodRecord(
        "Penalty-X full-space QAOA",
        "Explicit multilevel penalty Hamiltonian on the full edge-bit basis",
        "RICH_COST_INFORMATION; membership theorem only under a proved simulation",
        "Raw phi_state unchanged",
        "No classical-advice Lambda assigned",
        "Penalty construction, rich energy evaluation, training, and invalid-sample validation",
        "Held-out success and sampled energies in the existing empirical study",
        "Membership-query accounting if an oracle simulation is specified",
        "Posterior theorem does not cover uncharged rich costs",
        "Hardware gate/state-preparation and deployment costs",
        "Feasible-list storage",
        "EMPIRICAL_CASE_STUDY_NOT_DEPLOYMENT_READY",
    ),
    MethodRecord(
        "CVaR Penalty-X",
        "Full RCSP energy distribution plus tail-risk aggregation",
        "RICH_COST_INFORMATION",
        "Raw phi_state unchanged",
        "No membership-only Lambda assigned",
        "Energy sampling, sorting/tail estimation, optimizer evaluations, and validation",
        "Held-out CVaR benefit and sampled-energy outcomes in the existing study",
        "Sampling/training counts are accountably chargeable",
        "Not a violation of the membership-only theorem",
        "Rich-cost query lower bound and deployment overhead",
        "Feasible-list storage",
        "EMPIRICAL_CASE_STUDY_NOT_DEPLOYMENT_READY",
    ),
    MethodRecord(
        "Warm-start QAOA",
        "Instance-dependent classical solution, relaxation, or learned initialization",
        "POSTERIOR_STRUCTURE if summarized as S; otherwise stronger explicit information",
        "Basis phi unchanged unless candidates are restricted",
        "May increase Lambda; must be measured or bounded from the induced posterior",
        "Classical solve/relaxation, parameter production, and warm-state preparation",
        "None in Theory-v3",
        "Advice/query necessary bound once Lambda is known",
        "Success remains bounded by posterior concentration in the membership model",
        "Warm-start construction time, state gates, and reuse behavior",
        "Feasible-basis mixer graph unless separately used",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "Feasible-subspace state preparation",
        "A state supported on feasible solutions",
        "STRONGER_STRUCTURE_ORACLE or membership-simulable operation charged by queries",
        "Operational search support changes; raw edge-bit phi remains a representation fact",
        "Can reach Lambda=1 for feasibility success",
        "Enumeration/loader construction, state-preparation gates, postselection, and retries",
        "None in Theory-v3",
        "Oracle simulation cost rL when a simulation is supplied",
        "Membership theorem applies to total simulated queries",
        "Loader construction, depth, ancillas, postselection, and amortization",
        "Invalid-sample repair when support is exactly feasible",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "Path-exchange mixer",
        "A graph of feasible paths and allowed exchange moves",
        "STRUCTURED_MIXER; stronger oracle unless membership simulation is supplied",
        "Raw encoding phi unchanged; reachable support may be restricted",
        "Depends on seed/support and induced posterior; not automatically M/K",
        "Path generation, neighbor structure, mixer compilation, and connectivity proof",
        "None in Theory-v3",
        "rL membership charge if each neighbor step has an r-query simulation",
        "Total-query theorem after simulation",
        "Mixer graph size/depth, disconnected components, and dynamic patching",
        "Rich cost sampling unless combined with objective phases",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "XY/constraint-preserving mixer",
        "Known algebraic constraints preserved by mixer dynamics",
        "FIXED_STRUCTURE if instance independent; STRUCTURED_MIXER otherwise",
        "Can exclude some invalid states but does not by itself determine feasible resource density",
        "Changes only when the preserved subspace is instance-informative",
        "Mixer compilation, connectivity routing, Trotterization, and residual validation",
        "None in Theory-v3",
        "Fixed-constraint effects are mechanically derived",
        "Membership bound still applies to hidden residual feasibility",
        "Gate depth, two-qubit count, and hardware connectivity overhead",
        "Feasible enumeration if not used",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "Grover feasible-state mixer",
        "Reflections about a feasible-state superposition",
        "STRONGER_STRUCTURE_ORACLE unless preparation/reflection is simulated and charged",
        "Effective basis may become feasible-only; raw phi_state remains unchanged",
        "Feasibility support can make Lambda=1",
        "Feasible-state loader, reflection synthesis, membership calls, and retries",
        "None in Theory-v3",
        "Invocation cost rL under an explicit membership simulation",
        "Total membership-query bound after charging the simulation",
        "Preparation/reflection circuits and amortized build cost",
        "Invalid-sample repair for exact feasible support",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "Explicit feasible-basis QAOA",
        "Complete feasible list, basis index, objective table, and usually a mixer graph",
        "OUTSIDE_MEMBERSHIP_ONLY_MODEL; ENUMERATION_EXPOSURE",
        "Working-basis feasibility fraction becomes one; raw edge-bit phi is unchanged",
        "Lambda=1 for feasibility, but b_eff is only a summary of much richer access",
        "Enumeration, objective evaluation, storage, indexing, mixer construction, and loading",
        "None in Theory-v3",
        "Classical argmin over the supplied objective list returns an optimum",
        "Enumeration exposure establishes classical solvability after full listing",
        "All implementation and reuse costs",
        "Invalid-state validation if the basis is exact",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "Classical corridor restriction",
        "An instance-dependent candidate corridor/subgraph",
        "POSTERIOR_STRUCTURE or stronger explicit preprocessing",
        "Candidate-domain phi may increase; original raw phi_state does not change",
        "Increases according to posterior concentration, not corridor size alone",
        "Corridor computation, missed-route risk, patch/rebuild, and validation",
        "None in Theory-v3",
        "K_eff compression condition once posterior data are specified",
        "Necessary support compression for target success",
        "Construction quality/time and dynamic reuse",
        "Structured mixer gates unless combined with one",
        "MECHANISTIC_ONLY",
    ),
    MethodRecord(
        "Oracle-RCSP branch search",
        "Explicit K-branch topology plus counted random-access status attributes",
        "EXPLICIT_ATTRIBUTE_QUERY_RCSP",
        "Relevant phi_path=M/K; raw phi_state=M/2^(2K)",
        "Constant advice gives Lambda=M/K",
        "Attribute queries and amplitude amplification",
        "Small construction/Grover simulations in Theory-v3",
        "Theta(sqrt(K/M)) in the qualified nontrivial query regime",
        "Average and uniform worst-case lower bounds under the stated access model",
        "Fault-tolerant QRAM and deployment costs",
        "Feasible-list enumeration",
        "MECHANISTIC_QUERY_MODEL",
    ),
)


def method_matrix() -> pd.DataFrame:
    return pd.DataFrame([asdict(record) for record in METHODS])


def empty_cost_ledger() -> pd.DataFrame:
    """Return every method/resource cell without collapsing orthogonal units."""
    rows: list[dict[str, str]] = []
    for method in METHODS:
        for category, resources in RESOURCE_CONTRACT.items():
            for resource in resources:
                rows.append(
                    {
                        "method": method.method,
                        "resource_category": category,
                        "resource": resource,
                        "evidence_status": EvidenceStatus.UNKNOWN.value,
                        "value": "",
                        "unit": "RESOURCE_SPECIFIC",
                        "note": "Populate only from measured, derived, or proved evidence.",
                    }
                )
    return pd.DataFrame(rows)


def validate_ledger(frame: pd.DataFrame) -> None:
    required = {
        "method",
        "resource_category",
        "resource",
        "evidence_status",
        "value",
        "unit",
        "note",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"ledger is missing columns: {sorted(missing)}")
    allowed = {status.value for status in EvidenceStatus}
    invalid = set(frame.evidence_status) - allowed
    if invalid:
        raise ValueError(f"invalid evidence statuses: {sorted(invalid)}")
    expected = {
        (method.method, category, resource)
        for method in METHODS
        for category, resources in RESOURCE_CONTRACT.items()
        for resource in resources
    }
    observed = set(zip(frame.method, frame.resource_category, frame.resource))
    if observed != expected:
        raise ValueError("ledger does not contain exactly one cell per contract resource")
