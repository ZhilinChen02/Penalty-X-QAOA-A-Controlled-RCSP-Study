"""Prospective Phase-3 scaling universe and exact structural characterization."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from .graph_generator import derive_seed, generate_layered_graph
from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json, write_task
from .models import DirectedGraph, Route, Task
from .penalties import RawStateComponents, build_raw_state_components, scale_controlled_penalties
from .rcsp import enumerate_simple_routes, solve_exact_rcsp
from .representation import validate_edge_selection


CONFIG_PATH = PROJECT_ROOT / "configs" / "phase3_scaling_v1.yaml"
RESULT_ROOT = PROJECT_ROOT / "results" / "phase3_scaling_v1"
TASK_ROOT = PROJECT_ROOT / "data" / "tasks" / "phase3_scaling_v1"
MANIFEST_ROOT = PROJECT_ROOT / "data" / "manifests" / "phase3_scaling_v1"
UNIVERSE_PATH = MANIFEST_ROOT / "task_universe.json"
DEVELOPMENT_PATH = MANIFEST_ROOT / "development.json"
INTERPOLATION_PATH = MANIFEST_ROOT / "interpolation_holdout.json"
EXTRAPOLATION_PATH = MANIFEST_ROOT / "extrapolation_holdout.json"
MANIFEST_HASH_PATH = MANIFEST_ROOT / "manifest_hashes.json"
CHARACTERIZATION_PATH = RESULT_ROOT / "task_characterization.csv"
REJECTION_PATH = RESULT_ROOT / "construction_rejections.csv"
PREDECESSOR_HASH_PATH = RESULT_ROOT / "predecessor_hashes_before.json"


PROTECTED_RESULT_ROOTS = (
    "results/smoke",
    "results/phase0",
    "results/phase0_v2_dilution_stress",
    "results/phase1_pilot_v1",
    "results/phase1_1_optimization_diagnostic",
    "results/phase1_2_objective_alignment",
    "results/phase2_confirmatory_v1",
)


@dataclass(frozen=True)
class CardinalitySelection:
    level: int
    logspace_target: int
    intended_count: int
    budget: float
    selection_reason: str


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _protected_files() -> list[Path]:
    files: list[Path] = []
    for relative in PROTECTED_RESULT_ROOTS:
        root = PROJECT_ROOT / relative
        if not root.is_dir():
            raise FileNotFoundError(f"protected predecessor root missing: {relative}")
        files.extend(path for path in root.rglob("*") if path.is_file())
    files.extend(
        path
        for path in (PROJECT_ROOT / "configs").rglob("*")
        if path.is_file() and path.name != "phase3_scaling_v1.yaml"
    )
    files.extend(
        path
        for path in (PROJECT_ROOT / "data" / "manifests").rglob("*")
        if path.is_file() and "phase3_scaling_v1" not in path.parts
    )
    return sorted(set(files), key=lambda path: str(path.relative_to(PROJECT_ROOT)))


def predecessor_hash_inventory() -> dict[str, Any]:
    """Hash exactly the predecessor result roots plus predecessor configs/manifests."""
    files = _protected_files()
    hashes = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in files
    }
    sha_lines = "".join(f"{digest}  {path}\n" for path, digest in hashes.items())
    digest = hashlib.sha256(sha_lines.encode()).hexdigest()
    return {"file_count": len(hashes), "inventory_sha256": digest, "files": hashes}


def capture_predecessor_hashes() -> dict[str, Any]:
    inventory = predecessor_hash_inventory()
    expected = str(load_config(CONFIG_PATH)["predecessor_inventory_sha256"])
    if inventory["inventory_sha256"] != expected:
        raise RuntimeError(
            "predecessor inventory differs from the pre-edit hash; STOP: "
            f"{inventory['inventory_sha256']} != {expected}"
        )
    write_json(PREDECESSOR_HASH_PATH, inventory)
    return inventory


def verify_predecessor_hashes() -> dict[str, Any]:
    if not PREDECESSOR_HASH_PATH.exists():
        raise RuntimeError("predecessor hash snapshot is missing")
    frozen = json.loads(PREDECESSOR_HASH_PATH.read_text(encoding="utf-8"))
    observed = predecessor_hash_inventory()
    if observed != frozen:
        before = frozen.get("files", {})
        after = observed.get("files", {})
        changed = sorted(
            path for path in set(before) | set(after) if before.get(path) != after.get(path)
        )
        raise RuntimeError(f"immutable predecessor changed: {changed}")
    return observed


def log_spaced_cardinality_targets(n_routes: int, levels: int = 6) -> tuple[int, ...]:
    """Return deterministic distinct order-statistic targets from 1 through M."""
    if n_routes < levels:
        raise ValueError("n_routes must be at least the number of levels")
    raw = np.rint(np.logspace(0.0, math.log10(n_routes), levels)).astype(int)
    raw = np.clip(raw, 1, n_routes)
    chosen: list[int] = []
    for count in raw:
        if int(count) not in chosen:
            chosen.append(int(count))
    if len(chosen) < levels:
        # Fill gaps by maximizing log-distance from chosen counts, then smaller count.
        while len(chosen) < levels:
            unused = [count for count in range(1, n_routes + 1) if count not in chosen]
            fill = max(
                unused,
                key=lambda count: (
                    min(abs(math.log(count / selected)) for selected in chosen),
                    -count,
                ),
            )
            chosen.append(fill)
    return tuple(sorted(chosen))


def achievable_route_thresholds(routes: Sequence[Route]) -> tuple[tuple[int, float], ...]:
    counts: dict[float, int] = {}
    for route in routes:
        counts[float(route.resource)] = counts.get(float(route.resource), 0) + 1
    cumulative = 0
    output: list[tuple[int, float]] = []
    for resource, count in sorted(counts.items()):
        cumulative += count
        output.append((cumulative, resource))
    return tuple(output)


def select_six_cardinalities(routes: Sequence[Route]) -> tuple[CardinalitySelection, ...]:
    """Map frozen log targets to six unused exactly achievable resource thresholds."""
    if len(routes) < 6:
        raise ValueError("at least six candidate routes are required")
    targets = log_spaced_cardinality_targets(len(routes), 6)
    achievable = achievable_route_thresholds(routes)
    if len(achievable) < 6:
        raise ValueError("fewer than six distinct feasible-set thresholds are achievable")
    budget_by_count = dict(achievable)
    unused = set(budget_by_count)
    selected: list[tuple[int, int, float, str]] = []
    for target in targets:
        if target in unused:
            actual = target
            reason = "LOGSPACE_EXACT"
        else:
            actual = min(
                unused,
                key=lambda count: (abs(math.log(count / target)), count),
            )
            reason = "LOGSPACE_NEAREST_ACHIEVABLE_TIE_ADJUSTMENT"
        unused.remove(actual)
        selected.append((target, actual, budget_by_count[actual], reason))
    selected.sort(key=lambda item: item[1])
    return tuple(
        CardinalitySelection(
            level=index,
            logspace_target=target,
            intended_count=actual,
            budget=budget,
            selection_reason=reason,
        )
        for index, (target, actual, budget, reason) in enumerate(selected, start=1)
    )


def topology_features(graph: DirectedGraph, routes: Sequence[Route]) -> dict[str, Any]:
    out_degrees = np.zeros(graph.n_nodes, dtype=int)
    for edge in graph.edges:
        out_degrees[edge.source] += 1
    internal = [node for node in range(graph.n_nodes) if node not in (graph.source, graph.target)]
    route_counts = {
        node: sum(node in route.nodes[1:-1] for route in routes) for node in internal
    }
    max_bottleneck_fraction = (
        max(route_counts.values()) / len(routes) if routes and route_counts else 0.0
    )
    possible_dag_edges = graph.n_nodes * (graph.n_nodes - 1) / 2
    hop_counts = [len(route.edge_indices) for route in routes]
    return {
        "layer_widths": [len(layer) for layer in graph.layers],
        "n_layers": len(graph.layers),
        "path_redundancy": len(routes) / max(1, len(internal)),
        "n_candidate_routes": len(routes),
        "average_out_degree": float(out_degrees.mean()),
        "maximum_out_degree": int(out_degrees.max()),
        "bottleneck_score": float(max_bottleneck_fraction),
        "source_target_hop_min": int(min(hop_counts)),
        "source_target_hop_max": int(max(hop_counts)),
        "graph_density": len(graph.edges) / possible_dag_edges,
    }


def _split_for(size_m: int, base_index: int, config: dict[str, Any]) -> str:
    policy = config["split_policy"]
    if size_m in policy["development_sizes"] and base_index in policy["development_base_indices"]:
        return "development"
    if (
        size_m in policy["interpolation_holdout_sizes"]
        and base_index in policy["interpolation_holdout_base_indices"]
    ):
        return "interpolation_holdout"
    if (
        size_m in policy["extrapolation_holdout_sizes"]
        and base_index in policy["extrapolation_holdout_base_indices"]
    ):
        return "extrapolation_holdout"
    raise RuntimeError(f"no frozen split for m={size_m}, base_index={base_index}")


def _execution_has_started() -> bool:
    receipt_root = RESULT_ROOT / "run_receipts"
    return receipt_root.exists() and any(receipt_root.rglob("*.json"))


def generate_task_universe() -> dict[str, Any]:
    """Generate and freeze the complete 180-task structural universe before QAOA."""
    if _execution_has_started():
        raise RuntimeError("QAOA receipts exist; structural universe is immutable")
    config = load_config(CONFIG_PATH)
    capture_predecessor_hashes()
    tasks_manifest: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []
    TASK_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)

    for size_m in (int(value) for value in config["sizes"]):
        templates = config["layer_width_templates"][size_m]
        for base_index in range(int(config["base_graphs_per_size"])):
            widths = [int(value) for value in templates[base_index % len(templates)]]
            accepted: tuple[DirectedGraph, tuple[Route, ...], int, int] | None = None
            for attempt in range(int(config["maximum_generation_attempts"])):
                seed = derive_seed(
                    int(config["master_seed"]), "phase3", size_m, base_index, attempt
                )
                graph = generate_layered_graph(
                    target_n_edges=size_m,
                    layer_widths=widths,
                    seed=seed,
                    cost_range=tuple(int(v) for v in config["cost_range"]),
                    resource_range=tuple(int(v) for v in config["resource_range"]),
                )
                routes = enumerate_simple_routes(graph)
                thresholds = achievable_route_thresholds(routes)
                reasons = []
                if len(routes) < int(config["minimum_candidate_routes"]):
                    reasons.append("FEWER_THAN_SIX_CANDIDATE_ROUTES")
                if len(thresholds) < int(config["minimum_distinct_thresholds"]):
                    reasons.append("FEWER_THAN_SIX_DISTINCT_THRESHOLDS")
                if reasons:
                    rejections.append(
                        {
                            "size_m": size_m,
                            "base_index": base_index,
                            "attempt": attempt,
                            "attempt_seed": seed,
                            "layer_widths": json.dumps(widths),
                            "n_candidate_routes": len(routes),
                            "n_distinct_thresholds": len(thresholds),
                            "rejection_reason": ";".join(reasons),
                            "qaoa_outcome_used": False,
                        }
                    )
                    continue
                accepted = (graph, routes, attempt, seed)
                break
            if accepted is None:
                raise RuntimeError(
                    f"construction failed after frozen attempts: m={size_m}, base={base_index}"
                )
            graph, routes, attempt, seed = accepted
            selections = select_six_cardinalities(routes)
            split = _split_for(size_m, base_index, config)
            base_id = f"phase3-m{size_m:02d}-b{base_index:02d}-{graph.graph_id}"
            features = topology_features(graph, routes)
            family_task_ids: list[str] = []
            for selection in selections:
                started = time.perf_counter()
                feasible, optimal, optimal_cost = solve_exact_rcsp(routes, selection.budget)
                exact_time = time.perf_counter() - started
                if len(feasible) != selection.intended_count:
                    raise AssertionError("budget does not create intended feasible cardinality")
                raw_identity = (
                    f"phase3|{base_id}|L{selection.level}|{selection.intended_count}|"
                    f"{selection.budget:.17g}"
                )
                task_id = "task-p3-" + hashlib.sha256(raw_identity.encode()).hexdigest()[:16]
                task = Task(
                    task_id=task_id,
                    base_instance_id=base_id,
                    size_stratum=f"m{size_m}",
                    tightness_level=f"L{selection.level}",
                    target_n_edges=size_m,
                    actual_n_edges=len(graph.edges),
                    generation_seed=seed,
                    budget=selection.budget,
                    quantile=math.nan,
                    duplicate_budget=False,
                    duplicate_feasible_set=False,
                    graph=graph,
                    candidate_routes=routes,
                    feasible_routes=feasible,
                    optimal_routes=optimal,
                    optimal_cost=optimal_cost,
                    task_build_time_s=0.0,
                    exact_reference_time_s=exact_time,
                )
                task_path = TASK_ROOT / f"{task_id}.json"
                write_task(task_path, task)
                family_task_ids.append(task_id)
                tasks_manifest.append(
                    {
                        "manifest_order": len(tasks_manifest),
                        "task_id": task_id,
                        "base_graph_id": graph.graph_id,
                        "base_instance_id": base_id,
                        "base_index": base_index,
                        "split": split,
                        "size_m": size_m,
                        "target_n_edges": size_m,
                        "actual_n_edges": len(graph.edges),
                        "n_nodes": graph.n_nodes,
                        "dilution_level": selection.level,
                        "logspace_target_feasible_routes": selection.logspace_target,
                        "intended_feasible_routes": selection.intended_count,
                        "actual_feasible_routes": len(feasible),
                        "budget": selection.budget,
                        "selection_reason": selection.selection_reason,
                        "task_path": str(task_path.relative_to(PROJECT_ROOT)),
                    }
                )
            resources = [route.resource for route in routes]
            families.append(
                {
                    "manifest_order": len(families),
                    "base_instance_id": base_id,
                    "base_graph_id": graph.graph_id,
                    "base_index": base_index,
                    "split": split,
                    "size_m": size_m,
                    "target_n_edges": size_m,
                    "actual_n_edges": len(graph.edges),
                    "n_nodes": graph.n_nodes,
                    "generation_attempt": attempt,
                    "generation_seed": seed,
                    "task_ids": family_task_ids,
                    "unique_route_resource_sums": len(set(resources)),
                    "remaining_route_resource_ties": len(resources) - len(set(resources)),
                    **features,
                }
            )

    rejection_frame = pd.DataFrame(
        rejections,
        columns=[
            "size_m", "base_index", "attempt", "attempt_seed", "layer_widths",
            "n_candidate_routes", "n_distinct_thresholds", "rejection_reason",
            "qaoa_outcome_used",
        ],
    )
    atomic_write_csv(REJECTION_PATH, rejection_frame)
    payload = {
        "schema_version": "phase3_scaling_v1.task_universe.v1",
        "experiment_name": config["experiment_name"],
        "predecessor_git_sha": config["predecessor_git_sha"],
        "construction_qaoa_outcome_used": False,
        "base_graph_count": len(families),
        "task_count": len(tasks_manifest),
        "construction_rejection_count": len(rejections),
        "planned_primary_optimization_runs": int(config["planned_runs"]["primary_total"]),
        "families": families,
        "tasks": tasks_manifest,
    }
    if len(families) != 30 or len(tasks_manifest) != 180:
        raise RuntimeError("Phase-3 denominator construction failed")
    write_json(UNIVERSE_PATH, payload)
    split_paths = {
        "development": DEVELOPMENT_PATH,
        "interpolation_holdout": INTERPOLATION_PATH,
        "extrapolation_holdout": EXTRAPOLATION_PATH,
    }
    expected = {"development": (16, 96), "interpolation_holdout": (4, 24), "extrapolation_holdout": (10, 60)}
    for split, path in split_paths.items():
        split_families = [row for row in families if row["split"] == split]
        split_tasks = [row for row in tasks_manifest if row["split"] == split]
        if (len(split_families), len(split_tasks)) != expected[split]:
            raise RuntimeError(f"split denominator mismatch for {split}")
        write_json(
            path,
            {
                "schema_version": "phase3_scaling_v1.split.v1",
                "split": split,
                "base_graph_count": len(split_families),
                "task_count": len(split_tasks),
                "base_graph_ids": [row["base_instance_id"] for row in split_families],
                "families": split_families,
                "tasks": split_tasks,
            },
        )
    base_sets = [
        set(json.loads(path.read_text())["base_graph_ids"]) for path in split_paths.values()
    ]
    if any(base_sets[i] & base_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise RuntimeError("base-graph leakage across frozen splits")
    hashes = {path.name: sha256_file(path) for path in [UNIVERSE_PATH, *split_paths.values()]}
    write_json(MANIFEST_HASH_PATH, hashes)
    return payload


def load_manifest(split: str | None = None) -> dict[str, Any]:
    paths = {
        None: UNIVERSE_PATH,
        "development": DEVELOPMENT_PATH,
        "interpolation_holdout": INTERPOLATION_PATH,
        "extrapolation_holdout": EXTRAPOLATION_PATH,
    }
    path = paths[split]
    if not path.exists():
        raise RuntimeError("Phase-3 manifests must be generated and frozen first")
    hashes = json.loads(MANIFEST_HASH_PATH.read_text(encoding="utf-8"))
    if sha256_file(path) != hashes[path.name]:
        raise RuntimeError(f"frozen manifest changed: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_phase3_energy_context(
    task: Task, components: RawStateComponents | None = None
) -> dict[str, Any]:
    config = load_config(CONFIG_PATH)
    components = components or build_raw_state_components(task.graph)
    resource_excess = np.maximum(0.0, components.resource_total - task.budget)
    flow_scale = max(float(components.flow_penalty_raw.max()), 1.0)
    resource_scale = float(sum(edge.resource for edge in task.graph.edges))
    flow, resource = scale_controlled_penalties(
        components.flow_penalty_raw,
        resource_excess,
        flow_scale=flow_scale,
        resource_scale=resource_scale,
    )
    coefficient = float(config["raw_penalty_coefficient"])
    normalization = float(config["hamiltonian_normalization_factor"])
    raw_energy = components.routing_cost + coefficient * flow + coefficient * resource
    energy = raw_energy / normalization
    feasible_mask = (components.flow_penalty_raw == 0.0) & (resource_excess == 0.0)
    optimal_mask = np.zeros(len(energy), dtype=bool)
    optimal_mask[[route.bitstring_int for route in task.optimal_routes]] = True
    return {
        "components": components,
        "raw_energy": raw_energy,
        "energy": energy,
        "routing_cost_raw": components.routing_cost,
        "routing_component": components.routing_cost / normalization,
        "flow_penalty": flow,
        "resource_penalty": resource,
        "total_penalty": flow + resource,
        "feasible_mask": feasible_mask,
        "optimal_mask": optimal_mask,
        "energy_order": np.argsort(energy, kind="stable"),
        "flow_scale": flow_scale,
        "resource_scale": resource_scale,
        "normalization_factor": normalization,
    }


def _characterize_task(
    task: Task,
    family: dict[str, Any],
    components: RawStateComponents,
) -> dict[str, Any]:
    context = build_phase3_energy_context(task, components)
    feasible_ids = np.flatnonzero(context["feasible_mask"])
    validator_ids = []
    for state in feasible_ids:
        validation = validate_edge_selection(task.graph, int(state), task.budget)
        if validation.feasible:
            validator_ids.append(int(state))
    route_ids = sorted(route.bitstring_int for route in task.feasible_routes)
    if validator_ids != route_ids:
        raise RuntimeError(f"route/state feasibility count mismatch: {task.task_id}")
    feasible = context["feasible_mask"]
    infeasible = ~feasible
    raw = context["raw_energy"]
    energy = context["energy"]
    ground_mask = np.isclose(raw, raw.min(), atol=1e-12, rtol=0.0)
    ground_ids = set(np.flatnonzero(ground_mask).tolist())
    optimal_ids = {route.bitstring_int for route in task.optimal_routes}
    ground_valid = all(
        validate_edge_selection(task.graph, state, task.budget).feasible
        for state in ground_ids
    )
    ground_exact_optimal = ground_ids == optimal_ids
    n_feasible = len(feasible_ids)
    state_space = len(raw)
    phi = n_feasible / state_space
    log_n = math.log10(n_feasible)
    m_log_2 = task.actual_n_edges * math.log10(2.0)
    reconstructed = log_n - m_log_2
    identity_error = abs(reconstructed - math.log10(phi))
    if identity_error >= 1e-12:
        raise RuntimeError("representation dilution identity failed")
    max_feasible_raw = float(raw[feasible].max())
    min_infeasible_raw = float(raw[infeasible].min())
    strict = min_infeasible_raw > max_feasible_raw
    contract = bool(ground_valid and ground_exact_optimal and strict)
    return {
        "task_id": task.task_id,
        "base_graph_id": task.graph.graph_id,
        "base_instance_id": task.base_instance_id,
        "split": family["split"],
        "size_m": task.actual_n_edges,
        "target_n_edges": task.target_n_edges,
        "actual_n_edges": task.actual_n_edges,
        "n_nodes": task.graph.n_nodes,
        "n_edges": task.actual_n_edges,
        "state_space_size": state_space,
        "n_candidate_routes": len(task.candidate_routes),
        "n_feasible_routes": len(task.feasible_routes),
        "route_feasible_fraction": len(task.feasible_routes) / len(task.candidate_routes),
        "n_feasible_states": n_feasible,
        "feasible_state_fraction": phi,
        "phi_state": phi,
        "dilution_score": -math.log10(phi),
        "D": -math.log10(phi),
        "log10_n_feasible": log_n,
        "m_log10_2": m_log_2,
        "log10_phi_reconstructed": reconstructed,
        "identity_error": identity_error,
        "budget": task.budget,
        "n_optimal_states": len(optimal_ids),
        "optimal_cost": task.optimal_cost,
        "optimal_state_ids": json.dumps(sorted(optimal_ids)),
        "raw_energy_min": float(raw.min()),
        "raw_energy_max": float(raw.max()),
        "raw_energy_span": float(np.ptp(raw)),
        "normalized_energy_min": float(energy.min()),
        "normalized_energy_max": float(energy.max()),
        "normalized_energy_span": float(np.ptp(energy)),
        "min_infeasible_energy_raw": min_infeasible_raw,
        "max_feasible_energy_raw": max_feasible_raw,
        "penalty_separation_raw": min_infeasible_raw - max_feasible_raw,
        "strict_energy_separation": strict,
        "penalty_ground_state_valid": ground_valid,
        "penalty_ground_state_resource_feasible": bool(ground_mask[feasible].sum() == ground_mask.sum()),
        "penalty_ground_state_exact_original_optimal": ground_exact_optimal,
        "penalty_contract_pass": contract,
        "route_enumeration_feasible_count": len(route_ids),
        "edge_bit_validator_feasible_count": len(validator_ids),
        "feasible_count_agreement": len(route_ids) == len(validator_ids),
        "flow_scale": context["flow_scale"],
        "resource_scale": context["resource_scale"],
        "global_penalty_coefficient": 199.0,
        "global_normalization_factor": 199.0,
        "path_redundancy": family["path_redundancy"],
        "average_out_degree": family["average_out_degree"],
        "maximum_out_degree": family["maximum_out_degree"],
        "bottleneck_score": family["bottleneck_score"],
        "source_target_hop_min": family["source_target_hop_min"],
        "source_target_hop_max": family["source_target_hop_max"],
        "graph_density": family["graph_density"],
    }


def characterize_task_universe() -> pd.DataFrame:
    """Exhaustively audit all 180 tasks before any scientific QAOA execution."""
    universe = load_manifest()
    rows: list[dict[str, Any]] = []
    existing = (
        pd.read_csv(CHARACTERIZATION_PATH).to_dict(orient="records")
        if CHARACTERIZATION_PATH.exists()
        else []
    )
    existing_by_task = {row["task_id"]: row for row in existing}
    task_items = {row["task_id"]: row for row in universe["tasks"]}
    for family in universe["families"]:
        family_ids = family["task_ids"]
        if all(task_id in existing_by_task for task_id in family_ids):
            rows.extend(existing_by_task[task_id] for task_id in family_ids)
            continue
        tasks = [read_task(PROJECT_ROOT / task_items[task_id]["task_path"]) for task_id in family_ids]
        components = build_raw_state_components(tasks[0].graph)
        family_rows = [_characterize_task(task, family, components) for task in tasks]
        rows.extend(family_rows)
        atomic_write_csv(CHARACTERIZATION_PATH, pd.DataFrame(rows))
    frame = pd.DataFrame(rows).sort_values("task_id", kind="stable")
    atomic_write_csv(CHARACTERIZATION_PATH, frame)
    required = (
        len(frame) == 180
        and frame.penalty_contract_pass.astype(bool).all()
        and frame.feasible_count_agreement.astype(bool).all()
        and (frame.identity_error < 1e-12).all()
        and frame.strict_energy_separation.astype(bool).all()
    )
    if not required:
        raise RuntimeError("Phase-3 exhaustive task contract failed; STOP before optimization")
    write_task_universe_report(frame, universe)
    return frame


def write_task_universe_report(frame: pd.DataFrame, universe: dict[str, Any]) -> Path:
    by_size = frame.groupby("size_m").agg(
        base_graphs=("base_instance_id", "nunique"),
        tasks=("task_id", "count"),
        candidate_routes_min=("n_candidate_routes", "min"),
        candidate_routes_max=("n_candidate_routes", "max"),
        phi_min=("phi_state", "min"),
        phi_max=("phi_state", "max"),
        D_min=("D", "min"),
        D_max=("D", "max"),
    ).reset_index()
    lines = [
        "# Phase 3 task universe report", "",
        "The complete structural universe was generated without QAOA outcomes. All task",
        "identities and graph-disjoint splits were frozen before scientific optimization.", "",
        f"- Base graphs: {universe['base_graph_count']}",
        f"- Tasks: {universe['task_count']}",
        f"- Construction rejections: {universe['construction_rejection_count']}",
        f"- Feasible-count agreement: {int(frame.feasible_count_agreement.sum())}/180",
        f"- Penalty contract: {int(frame.penalty_contract_pass.sum())}/180", "",
        "## Coverage by size", "",
        by_size.to_string(index=False), "",
        "The exact identity `phi_state=N_feasible/2^m` reconstructs log10(phi) with",
        f"maximum error {frame.identity_error.max():.3e}.",
    ]
    path = RESULT_ROOT / "TASK_UNIVERSE_REPORT.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def characterization_lookup() -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(CHARACTERIZATION_PATH)
    return frame.set_index("task_id").to_dict(orient="index")
