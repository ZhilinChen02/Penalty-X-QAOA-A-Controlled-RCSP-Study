from __future__ import annotations

import pytest

from qroute_dilution.exact import characterize_family
from qroute_dilution.models import DirectedGraph, Edge
from qroute_dilution.rcsp import build_task_family


@pytest.fixture
def known_graph() -> DirectedGraph:
    # Two routes: 0-1-3 costs/resources (4,2), 0-2-3 costs/resources (2,6).
    edges = (
        Edge(0, 0, 1, 2.0, 1.0),
        Edge(1, 0, 2, 1.0, 3.0),
        Edge(2, 1, 3, 2.0, 1.0),
        Edge(3, 2, 3, 1.0, 3.0),
    )
    return DirectedGraph(4, 0, 3, ((0,), (1, 2), (3,)), edges, "known")


@pytest.fixture
def detached_cycle_graph() -> DirectedGraph:
    edges = (
        Edge(0, 0, 3, 1.0, 1.0),
        Edge(1, 1, 2, 1.0, 1.0),
        Edge(2, 2, 1, 1.0, 1.0),
    )
    return DirectedGraph(4, 0, 3, ((0,), (1, 2), (3,)), edges, "cycle")


@pytest.fixture
def small_task_and_characterization():
    task = build_task_family(
        size_stratum="X",
        target_n_edges=5,
        layer_widths=[1, 2, 1],
        base_index=0,
        master_seed=123,
        tightness_levels={"T": 0.5},
    )[0]
    characterization = characterize_family([task])[0]
    return task, characterization


def pytest_collection_modifyitems(items):
    """Original-tree hash audits cannot describe sanitized public metadata.

    Keep them active in the author tree. Public releases retain their original
    references and explicitly skip only these provenance/ancestry checks, while
    test_public_snapshot_integrity_manifest checks every included public file.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    if not (root / 'release_manifest.json').exists():
        return
    historical = {
        'test_historical_evidence_immutability_for_theory_stage',
        'test_phase1_1_historical_evidence_immutable',
        'test_phase1_2_historical_hash_immutability',
        'test_phase2_predecessor_commit_immutability',
        'test_predecessor_immutability_inventory_is_the_pre_edit_snapshot',
    }
    for item in items:
        if item.name in historical:
            item.add_marker(pytest.mark.skip(
                reason='historical unredacted provenance/Git inventory; public bytes have a separate manifest'))
