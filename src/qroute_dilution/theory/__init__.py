"""Offline theorem-audit utilities for global feasible-space dilution."""

from .global_dilution_bound import (
    QueryAlgorithm,
    coarse_query_bound,
    phase_query_coefficient,
    phase_sensitive_bound,
)
from .adaptive_query_bound import (
    adaptive_phase_bound,
    expected_query_truncation_bound,
    total_trained_queries,
)
from .advice_query_tradeoff import (
    finite_advice_success_bound,
    required_advice_bits,
)
from .explicit_rcsp_bounds import (
    parallel_branch_instance,
    unique_chain_audit,
)
from .posterior_structure_bound import (
    effective_structure_bits,
    effective_support,
    posterior_summary,
)

__all__ = [
    "QueryAlgorithm",
    "coarse_query_bound",
    "phase_query_coefficient",
    "phase_sensitive_bound",
    "adaptive_phase_bound",
    "expected_query_truncation_bound",
    "total_trained_queries",
    "finite_advice_success_bound",
    "required_advice_bits",
    "parallel_branch_instance",
    "unique_chain_audit",
    "posterior_summary",
    "effective_structure_bits",
    "effective_support",
]
