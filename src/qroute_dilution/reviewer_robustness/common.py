"""Shared integrity, state evaluation, and deterministic-identity helpers."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from qroute_dilution.io import PROJECT_ROOT, load_config, read_task, write_json
from qroute_dilution.metrics import probability_metrics
from qroute_dilution.models import Task
from qroute_dilution.phase1_2_experiment import build_objective_context
from qroute_dilution.phase1_2_objectives import weighted_exact_cvar
from qroute_dilution.qaoa import simulate_qaoa
from qroute_dilution.stress import build_stress_task_family


REVIEW_ROOT = PROJECT_ROOT / "results" / "reviewer_robustness"
MANIFEST_ROOT = REVIEW_ROOT / "manifests"
PROTOCOL_PATH = PROJECT_ROOT / "analysis" / "reviewer_robustness" / "protocol_v1.json"
DISCOVERY_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase1_pilot_v1.json"
HELDOUT_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "phase2_confirmatory_v1.json"
UNIVERSE_MANIFEST = (
    PROJECT_ROOT / "data" / "manifests" / "phase0_v2_dilution_stress.json"
)
PHASE3_MANIFEST = (
    PROJECT_ROOT / "data" / "manifests" / "phase3_scaling_v1" / "task_universe.json"
)
CHARACTERIZATION_PATH = (
    PROJECT_ROOT / "results" / "phase0_v2_dilution_stress" / "task_characterization.csv"
)


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_protocol() -> dict[str, Any]:
    value = load_json(PROTOCOL_PATH)
    if value.get("canonical_science_mutable") is not False:
        raise RuntimeError("reviewer protocol must prohibit canonical-science mutation")
    return value


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_payload(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def git_is_dirty() -> bool:
    output = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return bool(output.strip())


def utc_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def derive_seed(namespace: str, *parts: object) -> int:
    payload = "|".join([namespace, *(str(part) for part in parts)])
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big") & (
        (1 << 63) - 1
    )


def stable_run_id(namespace: str, *parts: object) -> str:
    payload = "|".join([namespace, *(str(part) for part in parts)])
    return f"{namespace}-" + hashlib.sha256(payload.encode()).hexdigest()[:20]


def parse_parameters(value: str | Iterable[float]) -> np.ndarray:
    if isinstance(value, str):
        value = json.loads(value)
    return np.asarray(value, dtype=np.float64)


def embed_parameters(
    parameters: np.ndarray, from_depth: int, to_depth: int
) -> np.ndarray:
    """Append exact zero-angle QAOA layers in gammas-then-betas order."""
    parameters = np.asarray(parameters, dtype=np.float64)
    if from_depth <= 0 or to_depth < from_depth:
        raise ValueError("depths must satisfy 0 < from_depth <= to_depth")
    if parameters.shape != (2 * from_depth,):
        raise ValueError(
            f"expected {2 * from_depth} parameters, received {parameters.shape}"
        )
    output = np.zeros(2 * to_depth, dtype=np.float64)
    output[:from_depth] = parameters[:from_depth]
    output[to_depth : to_depth + from_depth] = parameters[from_depth:]
    return output


@lru_cache(maxsize=None)
def _regenerate_v2_task(task_id: str, size_stratum: str, base_index: int) -> Task:
    """Regenerate one frozen V2 family in memory when portable task JSON is absent.

    The repository's existing endpoint finite-shot analysis uses the same
    deterministic Phase-0 generator because task payloads are intentionally not
    included in this working copy.  No regenerated payload is written to disk.
    """
    config = load_config(PROJECT_ROOT / "configs" / "phase0_v2_dilution_stress.yaml")
    specification = config["size_strata"][size_stratum]
    family = build_stress_task_family(
        size_stratum=size_stratum,
        target_n_edges=int(specification["target_n_edges"]),
        layer_widths=specification["layer_widths"],
        base_index=int(base_index),
        master_seed=int(config["master_seed"]),
        resource_range=tuple(int(value) for value in config["resource_range"]),
        preferred_counts=tuple(
            int(value) for value in config["preferred_feasible_route_counts"]
        ),
        max_levels=int(config["max_distinct_levels"]),
    )
    matches = [task for task, _selection in family if task.task_id == task_id]
    if len(matches) != 1:
        raise RuntimeError(
            f"STOP: deterministic regeneration found {len(matches)} matches for {task_id}"
        )
    return matches[0]


@lru_cache(maxsize=1)
def _v2_universe_by_task() -> dict[str, dict[str, Any]]:
    return {
        item["task_id"]: item for item in load_json(UNIVERSE_MANIFEST)["tasks"]
    }


def task_from_manifest_row(row: dict[str, Any]) -> Task:
    task_path = PROJECT_ROOT / row["task_path"]
    if task_path.exists():
        task = read_task(task_path)
    else:
        match = re.search(r"-b(\d+)-", str(row["base_instance_id"]))
        if match is None:
            raise FileNotFoundError(
                f"task payload is absent and base index cannot be parsed: {task_path}"
            )
        task = _regenerate_v2_task(
            str(row["task_id"]), str(row["size_stratum"]), int(match.group(1))
        )

    expected = {
        "task_id": row["task_id"],
        "graph_id": row["graph_id"],
        "base_instance_id": row["base_instance_id"],
        "size_stratum": row["size_stratum"],
        "stress_level": row["stress_level"],
    }
    observed = {
        "task_id": task.task_id,
        "graph_id": task.graph.graph_id,
        "base_instance_id": task.base_instance_id,
        "size_stratum": task.size_stratum,
        "stress_level": task.tightness_level,
    }
    if observed != expected:
        raise RuntimeError(
            f"STOP: task identity differs from frozen manifest: {observed} != {expected}"
        )
    frozen = _v2_universe_by_task()[task.task_id]
    if float(task.budget) != float(frozen["budget"]):
        raise RuntimeError(f"STOP: regenerated task budget mismatch for {task.task_id}")
    if len(task.feasible_routes) != int(frozen["actual_feasible_route_count"]):
        raise RuntimeError(
            f"STOP: regenerated feasible-set size mismatch for {task.task_id}"
        )
    return task


def masks_for_task(task: Task, state_count: int) -> tuple[np.ndarray, np.ndarray]:
    feasible = np.zeros(state_count, dtype=bool)
    optimal = np.zeros(state_count, dtype=bool)
    feasible[[route.bitstring_int for route in task.feasible_routes]] = True
    optimal[[route.bitstring_int for route in task.optimal_routes]] = True
    return feasible, optimal


def evaluate_probabilities(
    task: Task,
    context: dict[str, Any],
    probabilities: np.ndarray,
    *,
    alpha: float,
) -> dict[str, float | bool]:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    total = float(probabilities.sum())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("probability distribution must have positive finite mass")
    probabilities = probabilities / total
    feasible = np.asarray(context["feasible_mask"], dtype=bool)
    optimal = np.asarray(context["optimal_mask"], dtype=bool)
    phi = float(feasible.mean())
    metrics = probability_metrics(
        probabilities,
        np.flatnonzero(feasible),
        np.flatnonzero(optimal),
        phi,
    )
    cvar = weighted_exact_cvar(
        context["energy"],
        probabilities,
        alpha,
        feasible_mask=feasible,
        energy_order=context["energy_order"],
    )
    tail_fraction = float(cvar["cvar_tail_feasible_mass"]) / float(alpha)
    return {
        "mean_energy": float(np.dot(probabilities, context["energy"])),
        "p_feas": float(metrics["p_feas"]),
        "p_opt": float(metrics["p_opt"]),
        "p_opt_given_feas": float(metrics["p_opt_given_feasible"]),
        "G_feas": float(metrics["log_feasibility_gain"]),
        "feasible_fraction_phi": phi,
        "cvar": float(cvar["cvar_value"]),
        "cvar_cutoff_energy": float(cvar["cvar_cutoff_energy"]),
        "tail_feasible_fraction": tail_fraction,
        "tail_fully_feasible": bool(cvar["cvar_tail_fully_feasible"]),
        "state_norm": total,
    }


def evaluate_parameters(
    task: Task,
    context: dict[str, Any],
    parameters: np.ndarray,
    depth: int,
    *,
    alpha: float,
) -> dict[str, float | bool]:
    state = simulate_qaoa(
        np.asarray(parameters, dtype=np.float64), context["energy"], int(depth)
    )
    return evaluate_probabilities(task, context, np.abs(state) ** 2, alpha=alpha)


def objective_value(
    objective_id: str,
    probabilities: np.ndarray,
    context: dict[str, Any],
    *,
    alpha: float,
) -> float:
    if objective_id == "O0":
        return float(np.dot(probabilities, context["energy"]))
    if objective_id == "O3":
        return float(
            weighted_exact_cvar(
                context["energy"],
                probabilities,
                alpha,
                energy_order=context["energy_order"],
            )["cvar_value"]
        )
    raise ValueError(f"reviewer experiments only support O0/O3, received {objective_id}")


def exact_objective_callable(
    context: dict[str, Any], depth: int, objective_id: str, alpha: float
):
    def objective(parameters: np.ndarray) -> float:
        state = simulate_qaoa(parameters, context["energy"], depth)
        return objective_value(
            objective_id, np.abs(state) ** 2, context, alpha=alpha
        )

    return objective


def canonical_tracked_files() -> list[Path]:
    """Return tracked frozen inputs/results, excluding the new namespace."""
    process = subprocess.run(
        ["git", "ls-files", "-z", "configs", "data", "protocols", "results"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    paths = []
    for raw in process.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode())
        if relative.parts[:2] == ("results", "reviewer_robustness"):
            continue
        path = PROJECT_ROOT / relative
        if path.is_file():
            paths.append(path)
    return sorted(paths, key=lambda path: str(path.relative_to(PROJECT_ROOT)))


def canonical_hash_snapshot() -> dict[str, Any]:
    files = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in canonical_tracked_files()
    }
    return {
        "schema_version": "reviewer-robustness.canonical-hashes.v1",
        "git_head": git_head(),
        "file_count": len(files),
        "aggregate_sha256": sha256_payload(files),
        "files": files,
    }


def write_canonical_hash_snapshot(path: str | Path) -> dict[str, Any]:
    snapshot = canonical_hash_snapshot()
    write_json(path, snapshot)
    return snapshot


def verify_canonical_hash_snapshot(path: str | Path) -> dict[str, Any]:
    expected = load_json(path)
    observed = canonical_hash_snapshot()
    changed = sorted(
        key
        for key in set(expected["files"]) | set(observed["files"])
        if expected["files"].get(key) != observed["files"].get(key)
    )
    return {
        "pass": not changed,
        "changed_files": changed,
        "expected_file_count": int(expected["file_count"]),
        "observed_file_count": int(observed["file_count"]),
        "expected_aggregate_sha256": expected["aggregate_sha256"],
        "observed_aggregate_sha256": observed["aggregate_sha256"],
    }
