from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from qroute_dilution.phase1_analysis import build_task_depth_summary
from qroute_dilution.phase1_pilot import _energy_arrays, append_pilot_rows


def test_global_normalization_preserves_ground_state(small_task_and_characterization):
    task, _ = small_task_and_characterization
    components, raw, normalized, controlled_flow, controlled_resource = _energy_arrays(task, 172.0)
    excess = np.maximum(0.0, components.resource_total - task.budget)
    assert np.array_equal(np.flatnonzero(raw == raw.min()), np.flatnonzero(normalized == normalized.min()))
    assert np.allclose(normalized, raw / 172.0)
    assert np.array_equal(controlled_flow > 0, components.flow_penalty_raw > 0)
    assert np.array_equal(controlled_resource > 0, excess > 0)


def test_objective_multistart_selection_has_no_metric_leakage():
    common = {
        "task_id": "task",
        "base_graph_id": "graph",
        "base_instance_id": "base",
        "size_stratum": "S1",
        "stress_level": "D1",
        "depth": 1,
        "n_edges": 7,
        "feasible_state_fraction": 0.01,
        "dilution_score": 2.0,
        "raw_energy_span": 400.0,
        "normalized_energy_span": 400.0 / 172.0,
        "hamiltonian_normalization_factor": 172.0,
        "p_opt": 0.01,
        "log_feasibility_gain": 0.0,
        "optimizer_runtime_s": 1.0,
        "execution_status": "SUCCESS",
    }
    rows = [
        {**common, "optimizer_seed": 1, "objective_final": 1.0, "p_feas": 0.01},
        {**common, "optimizer_seed": 2, "objective_final": 0.5, "p_feas": 0.005},
        {**common, "optimizer_seed": 3, "objective_final": 0.8, "p_feas": 0.9},
    ]
    summary = build_task_depth_summary(pd.DataFrame(rows)).iloc[0]
    assert summary.objective_selected_multistart_optimizer_seed == 2
    assert summary.objective_selected_multistart_p_feas == 0.005
    assert summary.p_feas_median == 0.01


def test_resume_safe_writer_retains_failure_row(tmp_path):
    from qroute_dilution.phase1_pilot import PILOT_FIELDS

    row = {field: np.nan for field in PILOT_FIELDS}
    row.update(
        {
            "run_id": "failure-row",
            "execution_status": "OPTIMIZER_FAILURE",
            "failure_reason": "retained",
        }
    )
    path = tmp_path / "rows.csv"
    first = append_pilot_rows(path, [row])
    second = append_pilot_rows(path, [row])
    assert len(first) == len(second) == 1
    assert second.execution_status.iloc[0] == "OPTIMIZER_FAILURE"


def test_frozen_phase1_manifest_has_complete_trajectories_and_hashes():
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "data" / "manifests" / "phase1_pilot_v1.json"
    config_path = root / "configs" / "phase1_pilot_v1.yaml"
    snapshot = json.loads(
        (root / "results" / "phase1_pilot_v1" / "manifest_snapshot.json").read_text()
    )
    manifest = json.loads(manifest_path.read_text())
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == snapshot["manifest_sha256"]
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == snapshot["config_sha256"]
    assert manifest["task_count"] == 56
    assert manifest["planned_optimized_run_count"] == 504
    assert Counter(task["size_stratum"] for task in manifest["tasks"]) == {
        "S1": 6,
        "S2": 8,
        "S3": 14,
        "S4": 14,
        "S5": 14,
    }
    for bases in manifest["selected_base_graphs"].values():
        for base in bases:
            levels = [task["stress_level"] for task in manifest["tasks"] if task["base_instance_id"] == base]
            assert len(levels) == len(set(levels))


def test_completed_phase1_denominator_and_energy_bookkeeping():
    root = Path(__file__).resolve().parents[1]
    master = pd.read_csv(
        root / "results" / "phase1_pilot_v1" / "master_seed_level_results.csv"
    )
    optimized = master[master.algorithm == "Penalty-X"]
    uniform = master[master.algorithm == "Uniform"]
    assert len(master) == 560
    assert len(optimized) == 504
    assert len(uniform) == 56
    assert master.run_id.nunique() == 560
    assert (optimized.groupby(["task_id", "depth"]).size() == 3).all()
    assert optimized.execution_status.eq("SUCCESS").all()
    assert optimized.nfev.le(120).all()
    assert np.allclose(optimized.state_norm, 1.0, atol=1e-12)
    assert np.allclose(
        optimized.expected_energy_raw,
        172.0 * optimized.expected_energy_normalized,
        rtol=1e-11,
        atol=1e-9,
    )
    assert np.allclose(uniform.p_feas, uniform.feasible_state_fraction)
    assert np.allclose(uniform.p_opt, uniform.n_optimal_states / uniform.state_space_size)
    assert np.allclose(uniform.feasibility_amplification, 1.0)
    assert np.allclose(uniform.log_feasibility_gain, 0.0)
