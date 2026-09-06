from __future__ import annotations

import json

import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, load_config
from qroute_dilution.phase1_1_diagnostic import embed_p2_in_p3
from qroute_dilution.phase1_2_objectives import weighted_exact_cvar
from qroute_dilution.phase2_confirmatory import (
    CONFIG_PATH,
    MANIFEST_PATH,
    SNAPSHOT_PATH,
    build_phase2_manifest,
    preregistration_identity,
    verify_predecessor_commit_clean,
    verify_predecessor_immutability,
)
from qroute_dilution.phase2_statistics import (
    aggregate_base_graph_means,
    confirmatory_graph_inference,
    exact_sign_flip_pvalue,
    grouped_bootstrap_lower_bound,
    holm_adjust,
)


def test_phase2_task_set_construction_and_disjointness():
    manifest = build_phase2_manifest()
    discovery = json.loads(
        (PROJECT_ROOT / "data/manifests/phase1_pilot_v1.json").read_text()
    )
    phase2_bases = {row["base_instance_id"] for row in manifest["tasks"]}
    phase2_tasks = {row["task_id"] for row in manifest["tasks"]}
    discovery_bases = {row["base_instance_id"] for row in discovery["tasks"]}
    discovery_tasks = {row["task_id"] for row in discovery["tasks"]}
    assert len(phase2_bases) == 15
    assert len(phase2_tasks) == 84
    assert not phase2_bases & discovery_bases
    assert not phase2_tasks & discovery_tasks
    assert manifest["counts_by_size"] == {
        "S1": {"tasks": 9, "base_graphs": 3, "levels_per_graph": [3]},
        "S2": {"tasks": 12, "base_graphs": 3, "levels_per_graph": [4]},
        "S3": {"tasks": 21, "base_graphs": 3, "levels_per_graph": [7]},
        "S4": {"tasks": 21, "base_graphs": 3, "levels_per_graph": [7]},
        "S5": {"tasks": 21, "base_graphs": 3, "levels_per_graph": [7]},
    }


def test_preregistration_freeze_identity_inputs():
    identity = preregistration_identity()
    assert MANIFEST_PATH.exists()
    assert set(identity) == {
        "phase2_manifest_sha256",
        "phase2_config_sha256",
        "preregistration_sha256",
        "task_universe_manifest_sha256",
        "discovery_manifest_sha256",
        "penalty_contract_sha256",
    }
    assert all(len(value) == 64 for value in identity.values())
    if SNAPSHOT_PATH.exists():
        snapshot = json.loads(SNAPSHOT_PATH.read_text())
        assert all(snapshot[key] == value for key, value in identity.items())


def test_common_p2_to_p3_initialization_contract():
    p2 = np.array([0.1, 0.2, 0.3, 0.4])
    expected = np.array([0.1, 0.2, 0.0, 0.3, 0.4, 0.0])
    initializations = [embed_p2_in_p3(p2) for _ in ("O0", "O2", "O3")]
    assert all(np.array_equal(value, expected) for value in initializations)


def test_o0_o2_o3_matched_budget_and_frozen_margin():
    config = load_config(CONFIG_PATH)
    assert config["p3_comparison"]["objective_ids"] == ["O0", "O2", "O3"]
    assert config["p3_comparison"]["eval_budget"] == 240
    assert config["p2_preparation"]["eval_budget"] == 120
    assert config["noninferiority_margin_decades"] == 0.10


def test_phase2_exact_weighted_cvar_fractional_cutoff():
    result = weighted_exact_cvar(
        np.array([0.0, 1.0, 2.0]), np.array([0.05, 0.10, 0.85]), 0.10
    )
    assert np.isclose(result["cvar_value"], 0.5)
    assert np.isclose(result["cvar_fractional_cutoff_mass"], 0.05)


def test_base_graph_aggregation_equal_weight():
    frame = pd.DataFrame(
        {
            "base_graph_id": ["a"] * 6 + ["b"] * 9,
            "task_id": ["a1", "a1", "a1", "a2", "a2", "a2"]
            + [f"b{i}" for i in range(3) for _ in range(3)],
            "objective_id": ["O0", "O2", "O3"] * 5,
            "log_feasibility_gain": [0.0, 0.2, 0.1, 2.0, 2.2, 2.1]
            + [1.0, 1.3, 1.2] * 3,
        }
    )
    graph = aggregate_base_graph_means(frame)
    a = graph.set_index("base_graph_id").loc["a"]
    b = graph.set_index("base_graph_id").loc["b"]
    assert np.isclose(a.bar_G_O0, 1.0)
    assert np.isclose(a.Delta1_CVAR_MEAN, 0.1)
    assert np.isclose(b.Delta1_CVAR_MEAN, 0.2)


def test_grouped_bootstrap_and_exact_sign_flip():
    values = np.array([1.0, 1.0])
    bootstrap = grouped_bootstrap_lower_bound(values, resamples=100, seed=7)
    assert bootstrap["effect_mean"] == 1.0
    assert bootstrap["one_sided_95_lower_bound"] == 1.0
    assert exact_sign_flip_pvalue(values) == 0.25


def test_holm_correction():
    adjusted = holm_adjust({"H1": 0.01, "H2": 0.04})
    assert np.isclose(adjusted["H1"], 0.02)
    assert np.isclose(adjusted["H2"], 0.04)


def test_noninferiority_margin_implementation():
    inference = confirmatory_graph_inference(
        np.full(15, 0.2),
        np.full(15, -0.02),
        noninferiority_margin=0.10,
        resamples=200,
        bootstrap_seed=3,
        family_alpha=0.05,
    )
    assert inference["H1"]["pass"]
    assert inference["H2"]["pass"]
    assert inference["H2"]["null_margin"] == -0.10
    assert inference["H2"]["one_sided_95_lower_bound"] > -0.10


def test_phase2_predecessor_commit_immutability():
    assert verify_predecessor_commit_clean()
    if SNAPSHOT_PATH.exists():
        observed = verify_predecessor_immutability()
        assert "results/phase1_2_objective_alignment/objective_results.csv" in observed
