"""B2 exact label-setting RCSP baseline with dominance instrumentation."""

from __future__ import annotations

import heapq
import math
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, atomic_write_text
from qroute_dilution.models import DirectedGraph, Task

from .common import REVIEW_ROOT, load_json, stable_run_id, task_from_manifest_row, utc_timestamp
from .manifests import MANIFEST_PATHS, execution_code_fingerprint
from .registry import (
    read_valid_terminal_record,
    rebuild_registry,
    registry_payload,
    write_new_record,
)


B2_ROOT = REVIEW_ROOT / "B2_classical"


@dataclass(frozen=True)
class Label:
    identifier: int
    node: int
    cost: float
    resource: float
    nodes: tuple[int, ...]
    edge_indices: tuple[int, ...]
    visited: frozenset[int]


@dataclass(frozen=True)
class LabelSettingResult:
    feasible: bool
    optimal_cost: float | None
    nodes: tuple[int, ...]
    edge_indices: tuple[int, ...]
    resource: float | None
    labels_generated: int
    labels_expanded: int
    labels_dominance_pruned: int
    labels_resource_pruned: int
    labels_cycle_pruned: int
    maximum_live_labels: int


def _dominates(left: Label, right: Label, atol: float) -> bool:
    """Safe elementary-path dominance: left has no extra visited restrictions."""
    weak = (
        left.cost <= right.cost + atol
        and left.resource <= right.resource + atol
        and left.visited.issubset(right.visited)
    )
    strict = (
        left.cost < right.cost - atol
        or left.resource < right.resource - atol
        or left.visited < right.visited
    )
    return bool(weak and strict)


def solve_label_setting(
    graph: DirectedGraph, budget: float, *, atol: float = 1e-12
) -> LabelSettingResult:
    """Solve nonnegative-cost one-resource elementary RCSP exactly."""
    adjacency: dict[int, list[Any]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.source, []).append(edge)
    for edges in adjacency.values():
        edges.sort(key=lambda edge: (edge.target, edge.index))
    source = Label(
        identifier=0,
        node=graph.source,
        cost=0.0,
        resource=0.0,
        nodes=(graph.source,),
        edge_indices=(),
        visited=frozenset({graph.source}),
    )
    labels_at: dict[int, list[Label]] = {graph.source: [source]}
    active = {0}
    queue: list[tuple[float, float, int, Label]] = [(0.0, 0.0, 0, source)]
    next_identifier = 1
    generated = 1
    expanded = 0
    dominance_pruned = 0
    resource_pruned = 0
    cycle_pruned = 0
    maximum_live = 1
    targets: list[Label] = []
    while queue:
        _, _, _, label = heapq.heappop(queue)
        if label.identifier not in active:
            continue
        expanded += 1
        if label.node == graph.target:
            targets.append(label)
            continue
        for edge in adjacency.get(label.node, []):
            if edge.target in label.visited:
                cycle_pruned += 1
                continue
            resource = label.resource + float(edge.resource)
            if resource > float(budget) + atol:
                resource_pruned += 1
                continue
            candidate = Label(
                identifier=next_identifier,
                node=edge.target,
                cost=label.cost + float(edge.cost),
                resource=resource,
                nodes=(*label.nodes, edge.target),
                edge_indices=(*label.edge_indices, edge.index),
                visited=label.visited | {edge.target},
            )
            next_identifier += 1
            generated += 1
            incumbents = labels_at.setdefault(edge.target, [])
            if any(_dominates(incumbent, candidate, atol) for incumbent in incumbents):
                dominance_pruned += 1
                continue
            dominated = [
                incumbent
                for incumbent in incumbents
                if _dominates(candidate, incumbent, atol)
            ]
            if dominated:
                dominance_pruned += len(dominated)
                dominated_ids = {item.identifier for item in dominated}
                active.difference_update(dominated_ids)
                incumbents[:] = [
                    item for item in incumbents if item.identifier not in dominated_ids
                ]
            incumbents.append(candidate)
            active.add(candidate.identifier)
            heapq.heappush(
                queue,
                (candidate.cost, candidate.resource, candidate.identifier, candidate),
            )
            maximum_live = max(maximum_live, len(active))
        active.discard(label.identifier)
    if not targets:
        return LabelSettingResult(
            feasible=False,
            optimal_cost=None,
            nodes=(),
            edge_indices=(),
            resource=None,
            labels_generated=generated,
            labels_expanded=expanded,
            labels_dominance_pruned=dominance_pruned,
            labels_resource_pruned=resource_pruned,
            labels_cycle_pruned=cycle_pruned,
            maximum_live_labels=maximum_live,
        )
    best = min(targets, key=lambda label: (label.cost, label.resource, label.edge_indices))
    return LabelSettingResult(
        feasible=True,
        optimal_cost=float(best.cost),
        nodes=best.nodes,
        edge_indices=best.edge_indices,
        resource=float(best.resource),
        labels_generated=generated,
        labels_expanded=expanded,
        labels_dominance_pruned=dominance_pruned,
        labels_resource_pruned=resource_pruned,
        labels_cycle_pruned=cycle_pruned,
        maximum_live_labels=maximum_live,
    )


def _execute_task(
    task_record: dict[str, Any], manifest: dict[str, Any], output_root: Path
) -> str:
    run_id = stable_run_id(
        "b2", task_record["task_id"], execution_code_fingerprint(manifest)
    )
    path = output_root / "runs" / f"{run_id}.json"
    if read_valid_terminal_record(path, run_id=run_id) is not None:
        return "SKIPPED_EXISTING"
    started_at = utc_timestamp()
    started = time.perf_counter()
    try:
        task = task_from_manifest_row(task_record)
        first = solve_label_setting(task.graph, task.budget)
        expected_feasible = task.optimal_cost is not None
        match = bool(
            first.feasible == expected_feasible
            and (
                not expected_feasible
                or abs(float(first.optimal_cost) - float(task.optimal_cost)) <= 1e-12
            )
        )
        if not match:
            raise RuntimeError(
                f"classical optimum mismatch: observed={first.optimal_cost}, frozen={task.optimal_cost}"
            )
        protocol = load_json(PROJECT_ROOT / manifest["protocol_path"])["classical_baseline"]
        minimum = int(protocol["minimum_timing_repeats"])
        maximum = int(protocol["maximum_timing_repeats"])
        minimum_duration = float(protocol["minimum_timed_duration_s"])
        timings_ns = []
        timed_started = time.perf_counter()
        while len(timings_ns) < maximum:
            one_started = time.perf_counter_ns()
            repeated = solve_label_setting(task.graph, task.budget)
            timings_ns.append(time.perf_counter_ns() - one_started)
            if repeated != first:
                raise RuntimeError("label-setting result or counters are nondeterministic")
            if len(timings_ns) >= minimum and time.perf_counter() - timed_started >= minimum_duration:
                break
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        record = {
            "schema_version": "qroute-dilution.B2.classical-run.v1",
            "experiment": "B2_CLASSICAL_CONTEXT",
            "run_id": run_id,
            "status": "COMPLETE",
            "task": task_record,
            "solver": manifest["solver"],
            "feasible": first.feasible,
            "optimal_objective": first.optimal_cost,
            "frozen_optimal_objective": task.optimal_cost,
            "optimum_match": match,
            "optimal_nodes": list(first.nodes),
            "optimal_edge_indices": list(first.edge_indices),
            "optimal_resource": first.resource,
            "labels_generated": first.labels_generated,
            "labels_expanded": first.labels_expanded,
            "labels_dominance_pruned": first.labels_dominance_pruned,
            "labels_resource_pruned": first.labels_resource_pruned,
            "labels_cycle_pruned": first.labels_cycle_pruned,
            "maximum_live_labels": first.maximum_live_labels,
            "timing_repeats": len(timings_ns),
            "solve_time_ns_median": int(statistics.median(timings_ns)),
            "solve_time_ns_min": min(timings_ns),
            "solve_time_ns_max": max(timings_ns),
            "timing_samples_ns": timings_ns,
            "runtime_s": runtime,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="B2_CLASSICAL_CONTEXT",
            run_id=run_id,
            task_id=task.task_id,
            graph_id=task.graph.graph_id,
            objective="exact constrained route cost",
            optimizer=None,
            depth=None,
            alpha=None,
            nfev_budget=None,
            actual_nfev=None,
            shots=None,
            seed=None,
            status="COMPLETE",
            started_at=started_at,
            finished_at=finished_at,
            runtime_s=runtime,
            error_message="",
            git_commit=manifest["code_git_commit"],
            dirty_state_fingerprint=execution_code_fingerprint(manifest),
        )
        write_new_record(path, record)
        return "COMPLETE"
    except Exception as exc:
        finished_at = utc_timestamp()
        runtime = time.perf_counter() - started
        message = f"{type(exc).__name__}: {exc}"
        record = {
            "schema_version": "qroute-dilution.B2.classical-run.v1",
            "experiment": "B2_CLASSICAL_CONTEXT",
            "run_id": run_id,
            "status": "FAILED",
            "task": task_record,
            "error_message": message,
            "runtime_s": runtime,
            "started_at": started_at,
            "finished_at": finished_at,
        }
        record["registry"] = registry_payload(
            experiment="B2_CLASSICAL_CONTEXT",
            run_id=run_id,
            task_id=task_record["task_id"],
            graph_id=task_record["graph_id"],
            objective="exact constrained route cost",
            optimizer=None,
            depth=None,
            alpha=None,
            nfev_budget=None,
            actual_nfev=None,
            shots=None,
            seed=None,
            status="FAILED",
            started_at=started_at,
            finished_at=finished_at,
            runtime_s=runtime,
            error_message=message,
            git_commit=manifest["code_git_commit"],
            dirty_state_fingerprint=execution_code_fingerprint(manifest),
        )
        write_new_record(path, record)
        return "FAILED"


def run_b2(*, smoke: bool = False) -> dict[str, int]:
    manifest = load_json(MANIFEST_PATHS["classical"])
    tasks = list(manifest["tasks"])
    output_root = REVIEW_ROOT / "smoke" / "B2_classical" if smoke else B2_ROOT
    if smoke:
        tasks = sorted(tasks, key=lambda row: (row["m"], row["task_id"]))[:2]
    counts: dict[str, int] = {}
    for task in tasks:
        status = _execute_task(task, manifest, output_root)
        counts[status] = counts.get(status, 0) + 1
    rebuild_registry()
    return counts


def aggregate_b2() -> dict[str, Any]:
    manifest = load_json(MANIFEST_PATHS["classical"])
    paths = sorted((B2_ROOT / "runs").glob("*.json"))
    records = [load_json(path) for path in paths]
    complete = [record for record in records if record.get("status") == "COMPLETE"]
    rows = []
    for record in complete:
        task = record["task"]
        rows.append(
            {
                "run_id": record["run_id"],
                "task_id": task["task_id"],
                "graph_id": task["graph_id"],
                "size_stratum": task["size_stratum"],
                "stress_level": task["stress_level"],
                "m": task["m"],
                "dilution_score": task["dilution_score"],
                "feasibility_status": "FEASIBLE" if record["feasible"] else "INFEASIBLE",
                "optimal_objective": record["optimal_objective"],
                "frozen_optimal_objective": record["frozen_optimal_objective"],
                "optimum_match": record["optimum_match"],
                "optimal_nodes": json_dumps(record["optimal_nodes"]),
                "optimal_edge_indices": json_dumps(record["optimal_edge_indices"]),
                "optimal_resource": record["optimal_resource"],
                "solve_time_s_median": record["solve_time_ns_median"] / 1e9,
                "solve_time_s_min": record["solve_time_ns_min"] / 1e9,
                "solve_time_s_max": record["solve_time_ns_max"] / 1e9,
                "timing_repeats": record["timing_repeats"],
                "labels_generated": record["labels_generated"],
                "labels_expanded": record["labels_expanded"],
                "labels_dominance_pruned": record["labels_dominance_pruned"],
                "labels_resource_pruned": record["labels_resource_pruned"],
                "labels_cycle_pruned": record["labels_cycle_pruned"],
                "maximum_live_labels": record["maximum_live_labels"],
            }
        )
    frame = pd.DataFrame(rows)
    atomic_write_csv(B2_ROOT / "classical_runs.csv", frame)
    summary_rows = []
    if len(frame):
        for scope, group in [("ALL", frame), *list(frame.groupby("size_stratum"))]:
            summary_rows.append(
                {
                    "scope": scope,
                    "task_count": len(group),
                    "graph_count": int(group.graph_id.nunique()),
                    "optimum_match_count": int(group.optimum_match.sum()),
                    "median_solve_time_s": float(group.solve_time_s_median.median()),
                    "p95_solve_time_s": float(group.solve_time_s_median.quantile(0.95)),
                    "max_solve_time_s": float(group.solve_time_s_median.max()),
                    "median_labels_generated": float(group.labels_generated.median()),
                    "max_labels_generated": int(group.labels_generated.max()),
                    "median_labels_expanded": float(group.labels_expanded.median()),
                    "median_labels_dominance_pruned": float(group.labels_dominance_pruned.median()),
                    "max_live_labels": int(group.maximum_live_labels.max()),
                }
            )
    summary = pd.DataFrame(summary_rows)
    atomic_write_csv(B2_ROOT / "classical_summary.csv", summary)
    failed = len(paths) - len(complete)
    all_row = summary[summary.scope == "ALL"].iloc[0] if len(summary) else None
    report = [
        "# B2 — Exact classical RCSP context",
        "",
        f"Completed {len(complete)}/{manifest['planned_runs']} canonical tasks; failed records: {failed}.",
        "",
        "## Protocol and correctness",
        "",
        "A resource-cost label-setting solver with elementary-path-safe dominance is instrumented for generated, expanded, dominance-pruned, resource-pruned, and maximum-live labels. High-resolution timings repeat each complete solve 20–100 times until at least 0.02 s of timed work is observed. The median is reported; microsecond differences are not interpreted.",
        "",
        "Manifest: `results/reviewer_robustness/manifests/manifest_classical_baseline.json`.",
        "",
    ]
    if all_row is not None:
        report.extend(
            [
                f"Exact optimum agreement is **{int(all_row.optimum_match_count)}/{int(all_row.task_count)}**. Median solve time is {all_row.median_solve_time_s:.6g} s, p95 {all_row.p95_solve_time_s:.6g} s, maximum {all_row.max_solve_time_s:.6g} s. Median generated labels: {all_row.median_labels_generated:.1f}; maximum: {int(all_row.max_labels_generated)}.",
                "",
            ]
        )
    report.extend(
        [
            "## Interpretation and claim impact",
            "",
            "The benchmark is deliberately classically tractable and is used for controlled mechanistic attribution rather than a quantum-advantage claim. Classical timing is context only and is not compared with simulator wall time as a hardware-performance claim.",
            "",
            "Graph clustering is not used for the exact-agreement check: correctness is verified task by task on all 140 canonical instances. Timing summaries are descriptive and are not inferential performance comparisons.",
            "",
            "This result supports placing the classical context in the main methods/limitations text, with detailed counters in the appendix.",
            "",
        ]
    )
    atomic_write_text(B2_ROOT / "B2_CLASSICAL_CONTEXT.md", "\n".join(report))
    if len(frame) and not frame.optimum_match.all():
        raise RuntimeError("B2 includes a mismatch; publication table is invalid")
    return {
        "planned_runs": manifest["planned_runs"],
        "complete_runs": len(complete),
        "failed_runs": failed,
        "optimum_matches": int(frame.optimum_match.sum()) if len(frame) else 0,
    }


def json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, separators=(",", ":"))
