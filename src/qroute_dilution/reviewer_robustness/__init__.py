"""Isolated post-hoc reviewer-robustness experiments.

Nothing in this package is imported by the frozen Phase 0--3 execution paths.
All writes are confined to ``results/reviewer_robustness``.
"""

from .common import REVIEW_ROOT

__all__ = ["REVIEW_ROOT"]
