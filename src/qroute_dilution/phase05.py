"""Phase 0.5 dilution audit, prospective v2 universe, and pilot projection."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .exact import characterize_family
from .io import PROJECT_ROOT, atomic_write_csv, load_config, read_task, write_json, write_task
from .metrics import dilution_score
from .pipeline import build_resource_projection
from .stress import INSUFFICIENT_STATUS, StressSelection, build_stress_task_family
from .stress_plotting import plot_stress_audit


V1_HASH_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "v1_evidence_sha256.json"


def verify_v1_evidence_hashes() -> dict[str, str]:
    fixture = json.loads(V1_HASH_FIXTURE.read_text(encoding="utf-8"))
    observed: dict[str, str] = {}
    for relative_path, expected in fixture["files"].items():
        path = PROJECT_ROOT / relative_path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(
                f"v1 evidence hash mismatch for {relative_path}: {digest} != {expected}"
            )
        observed[relative_path] = digest
    return observed


def _base_index(base_instance_id: str) -> int:
    marker = "-b"
    start = base_instance_id.index(marker) + len(marker)
    return int(base_instance_id[start : start + 3])


def build_v1_graph_audit() -> tuple[pd.DataFrame, dict[str, Any]]:
    characterization = pd.read_csv(PROJECT_ROOT / "results" / "phase0" / "task_characterization.csv")
    manifest = pd.read_csv(PROJECT_ROOT / "data" / "manifests" / "phase0_tasks.csv")
    config = load_config(PROJECT_ROOT / "configs" / "phase0_v1.yaml")
    level_order = list(config["tightness_levels"])
    quantiles = {key: float(value) for key, value in config["tightness_levels"].items()}
    order_map = {level: index for index, level in enumerate(level_order)}
    rows: list[dict[str, Any]] = []
    repeated_index_duplicates = 0
    tied_resource_duplicates = 0
    total_candidate_routes = 0
    total_unique_resources = 0

    for base_id, family in characterization.groupby("base_instance_id", sort=False):
        family = family.assign(
            _order=family["tightness_level"].map(order_map)
        ).sort_values("_order")
        family_manifest = manifest[manifest["base_instance_id"] == base_id]
        task_path = PROJECT_ROOT / family_manifest.iloc[0]["task_path"]
        if not task_path.exists():
            raise FileNotFoundError(
                f"v1 task payload required for resource-tie audit is missing: {task_path}"
            )
        task = read_task(task_path)
        resources = sorted(route.resource for route in task.candidate_routes)
        n_routes = len(resources)
        unique_resources = len(set(resources))
        total_candidate_routes += n_routes
        total_unique_resources += unique_resources

        seen_indices: set[int] = set()
        seen_budgets: set[float] = set()
        local_index_duplicates = 0
        local_tie_duplicates = 0
        for item in family.itertuples():
            order_index = math.floor(quantiles[item.tightness_level] * (n_routes - 1) + 1e-12)
            if item.budget in seen_budgets:
                if order_index in seen_indices:
                    repeated_index_duplicates += 1
                    local_index_duplicates += 1
                else:
                    tied_resource_duplicates += 1
                    local_tie_duplicates += 1
            seen_indices.add(order_index)
            seen_budgets.add(float(item.budget))

        duplicate_groups = []
        for _, group in family.groupby("budget", sort=False):
            levels = group["tightness_level"].tolist()
            if len(levels) > 1:
                duplicate_groups.append("=".join(levels))
        row: dict[str, Any] = {
            "base_instance_id": base_id,
            "base_index": _base_index(base_id),
            "size_stratum": family.iloc[0]["size_stratum"],
            "n_edges": int(family.iloc[0]["n_edges"]),
            "state_space_size": int(family.iloc[0]["state_space_size"]),
            "n_candidate_routes": n_routes,
            "unique_resource_consumptions": unique_resources,
            "effective_levels": int(family["n_feasible_states"].nunique()),
            "duplicate_tightness_pairs": "; ".join(duplicate_groups) or "none",
            "repeated_quantile_index_duplicates": local_index_duplicates,
            "integer_resource_tie_duplicates": local_tie_duplicates,
        }
        for item in family.itertuples():
            row[f"phi_{item.tightness_level}"] = float(item.feasible_state_fraction)
            row[f"route_{item.tightness_level}"] = float(item.route_feasible_fraction)
        rows.append(row)

    audit = pd.DataFrame(rows)
    duplicated_budget_rows = int(
        characterization.duplicated(["base_instance_id", "budget"]).sum()
    )
    duplicated_set_rows = int(
        characterization.duplicated(["base_instance_id", "n_feasible_states"]).sum()
    )
    phi = characterization["feasible_state_fraction"]
    summary = {
        "task_count": int(len(characterization)),
        "base_graph_count": int(characterization["base_instance_id"].nunique()),
        "duplicated_budget_rows": duplicated_budget_rows,
        "duplicated_budget_percentage": 100.0 * duplicated_budget_rows / len(characterization),
        "duplicated_feasible_set_rows": duplicated_set_rows,
        "duplicated_feasible_set_percentage": 100.0 * duplicated_set_rows / len(characterization),
        "effective_levels_min": int(audit.effective_levels.min()),
        "effective_levels_median": float(audit.effective_levels.median()),
        "effective_levels_max": int(audit.effective_levels.max()),
        "effective_levels_total": int(audit.effective_levels.sum()),
        "feasible_state_fraction_min": float(phi.min()),
        "feasible_state_fraction_median": float(phi.median()),
        "feasible_state_fraction_max": float(phi.max()),
        "dilution_score_min": float((-np.log10(phi)).min()),
        "dilution_score_max": float((-np.log10(phi)).max()),
        "total_candidate_routes": total_candidate_routes,
        "total_unique_resource_consumptions": total_unique_resources,
        "resource_tie_excess_routes": total_candidate_routes - total_unique_resources,
        "repeated_quantile_index_duplicates": repeated_index_duplicates,
        "integer_resource_tie_duplicates": tied_resource_duplicates,
        "budget_rounding_duplicates": 0,
        "graphs_with_fewer_than_7_candidate_routes": int(
            (audit.n_candidate_routes < 7).sum()
        ),
        "graphs_with_fewer_than_7_unique_resources": int(
            (audit.unique_resource_consumptions < 7).sum()
        ),
    }
    if repeated_index_duplicates + tied_resource_duplicates != duplicated_budget_rows:
        raise AssertionError("duplicate cause decomposition does not sum to observed duplicates")
    return audit, summary


def _stress_paths() -> dict[str, Path]:
    result_dir = PROJECT_ROOT / "results" / "phase0_v2_dilution_stress"
    return {
        "result_dir": result_dir,
        "task_dir": PROJECT_ROOT / "data" / "tasks" / "phase0_v2_dilution_stress",
        "manifest": PROJECT_ROOT / "data" / "manifests" / "phase0_v2_dilution_stress.json",
        "characterization": result_dir / "task_characterization.csv",
        "summary": result_dir / "summary.json",
        "projection": result_dir / "pilot_resource_projection.json",
        "figures": result_dir / "figures",
    }


def generate_stress_universe(
    config_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    config = load_config(config_path)
    paths = _stress_paths()
    paths["task_dir"].mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    task_manifest: list[dict[str, Any]] = []
    family_manifest: list[dict[str, Any]] = []
    resource_range = tuple(int(value) for value in config["resource_range"])
    preferred = tuple(int(value) for value in config["preferred_feasible_route_counts"])
    max_levels = int(config["max_distinct_levels"])

    for stratum, spec in config["size_strata"].items():
        for base_index in range(int(config["instances_per_stratum"])):
            family_pairs = build_stress_task_family(
                size_stratum=stratum,
                target_n_edges=int(spec["target_n_edges"]),
                layer_widths=spec["layer_widths"],
                base_index=base_index,
                master_seed=int(config["master_seed"]),
                resource_range=resource_range,
                preferred_counts=preferred,
                max_levels=max_levels,
            )
            tasks = [task for task, _ in family_pairs]
            selections = {task.task_id: selection for task, selection in family_pairs}
            characterized = characterize_family(tasks)
            unique_resources = len({route.resource for route in tasks[0].candidate_routes})
            status = "OK" if unique_resources >= max_levels else INSUFFICIENT_STATUS
            for task, row in zip(tasks, characterized):
                selection = selections[task.task_id]
                if int(row["n_feasible_states"]) != selection.actual_feasible_route_count:
                    raise AssertionError("exhaustive state count disagrees with stress selection")
                row.update(
                    {
                        "stress_level": task.tightness_level,
                        "base_index": base_index,
                        "stress_policy": "distinct_feasible_route_cardinality",
                        "target_feasible_route_count": selection.target_feasible_route_count,
                        "actual_feasible_route_count": selection.actual_feasible_route_count,
                        "selection_reason": selection.selection_reason,
                        "unique_resource_consumptions": unique_resources,
                        "achievable_distinct_feasible_sets": unique_resources,
                        "effective_distinct_stress_levels": len(tasks),
                        "stress_status": status,
                        "resource_support_min": resource_range[0],
                        "resource_support_max": resource_range[1],
                        "dilution_score": dilution_score(float(row["feasible_state_fraction"])),
                        "theoretical_min_positive_fraction": 1.0 / int(row["state_space_size"]),
                    }
                )
                task_path = paths["task_dir"] / f"{task.task_id}.json"
                write_task(task_path, task)
                task_manifest.append(
                    {
                        "task_id": task.task_id,
                        "graph_id": task.graph.graph_id,
                        "base_instance_id": task.base_instance_id,
                        "base_index": base_index,
                        "size_stratum": stratum,
                        "stress_level": task.tightness_level,
                        "target_feasible_route_count": selection.target_feasible_route_count,
                        "actual_feasible_route_count": selection.actual_feasible_route_count,
                        "budget": task.budget,
                        "stress_status": status,
                        "task_path": str(task_path.relative_to(PROJECT_ROOT)),
                    }
                )
                all_rows.append(row)
            family_manifest.append(
                {
                    "base_instance_id": tasks[0].base_instance_id,
                    "graph_id": tasks[0].graph.graph_id,
                    "base_index": base_index,
                    "size_stratum": stratum,
                    "n_candidate_routes": len(tasks[0].candidate_routes),
                    "unique_resource_consumptions": unique_resources,
                    "effective_distinct_stress_levels": len(tasks),
                    "stress_status": status,
                }
            )
            partial = pd.DataFrame(all_rows)
            atomic_write_csv(paths["characterization"], partial)

    frame = pd.DataFrame(all_rows)
    duplicate_sets = int(frame.duplicated(["base_instance_id", "n_feasible_states"]).sum())
    duplicate_budgets = int(frame.duplicated(["base_instance_id", "budget"]).sum())
    if duplicate_sets or duplicate_budgets:
        raise AssertionError("prospective primary stress suite contains duplicate feasible sets")
    v1_task_ids = set(
        pd.read_csv(PROJECT_ROOT / "data" / "manifests" / "phase0_tasks.csv")["task_id"]
    )
    overlap = v1_task_ids.intersection(frame.task_id)
    if overlap:
        raise AssertionError(f"prospective v2 reused v1 task IDs: {sorted(overlap)[:3]}")
    manifest_payload = {
        "schema_version": "phase0_v2_dilution_stress.v1",
        "experiment_name": config["experiment_name"],
        "policy": {
            "resource_policy": config["resource_policy"],
            "resource_range": list(resource_range),
            "preferred_feasible_route_counts": list(preferred),
            "max_distinct_levels": max_levels,
            "at_least_one_feasible_route": True,
            "qaoa_result_dependent": False,
        },
        "family_count": len(family_manifest),
        "task_count": len(task_manifest),
        "families": family_manifest,
        "tasks": task_manifest,
    }
    write_json(paths["manifest"], manifest_payload)
    summary = {
        "task_count": int(len(frame)),
        "base_graph_count": int(frame.base_instance_id.nunique()),
        "duplicate_budget_count": duplicate_budgets,
        "duplicate_feasible_set_count": duplicate_sets,
        "insufficient_distinct_graph_count": int(
            frame.loc[frame.stress_status == INSUFFICIENT_STATUS, "base_instance_id"].nunique()
        ),
        "feasible_state_fraction_min": float(frame.feasible_state_fraction.min()),
        "feasible_state_fraction_median": float(frame.feasible_state_fraction.median()),
        "feasible_state_fraction_max": float(frame.feasible_state_fraction.max()),
        "dilution_score_min": float(frame.dilution_score.min()),
        "dilution_score_max": float(frame.dilution_score.max()),
        "resource_tie_graph_count": int(
            frame.loc[
                frame.unique_resource_consumptions < frame.n_candidate_routes,
                "base_instance_id",
            ].nunique()
        ),
        "total_candidate_routes_across_graphs": int(
            frame.groupby("base_instance_id")["n_candidate_routes"].first().sum()
        ),
        "total_unique_resource_consumptions_across_graphs": int(
            frame.groupby("base_instance_id")["unique_resource_consumptions"].first().sum()
        ),
    }
    write_json(paths["summary"], summary)
    return frame, summary


def _coverage_summary(frame: pd.DataFrame) -> dict[str, Any]:
    phi = frame.feasible_state_fraction
    return {
        "task_rows": int(len(frame)),
        "feasible_state_fraction_min": float(phi.min()),
        "feasible_state_fraction_median": float(phi.median()),
        "feasible_state_fraction_max": float(phi.max()),
        "dilution_score_min": float((-np.log10(phi)).min()),
        "dilution_score_max": float((-np.log10(phi)).max()),
        "distinct_feasible_sets_summed_over_graphs": int(
            frame.groupby("base_instance_id")["n_feasible_states"].nunique().sum()
        ),
        "globally_distinct_phi_values": int(phi.nunique()),
    }


def write_audit_report(
    audit: pd.DataFrame,
    v1_summary: dict[str, Any],
    v1: pd.DataFrame,
    v2: pd.DataFrame,
    v2_summary: dict[str, Any],
    projection: dict[str, Any],
    verdict: str,
) -> Path:
    path = PROJECT_ROOT / "results" / "phase0" / "PHASE0_DILUTION_AUDIT.md"
    v1_coverage = _coverage_summary(v1)
    v2_coverage = _coverage_summary(v2)
    improvement = (
        v2_coverage["distinct_feasible_sets_summed_over_graphs"]
        - v1_coverage["distinct_feasible_sets_summed_over_graphs"]
    )
    improvement_pct = 100 * improvement / v1_coverage["distinct_feasible_sets_summed_over_graphs"]
    lines = [
        "# Phase 0 dilution stress audit",
        "",
        "This report audits the immutable Phase 0 v1 evidence at commit",
        "`5aa822f586f66ab3bb2b00e165780b111b13ad45`. Existing v1 result files and rows",
        "were read only. Prospective v2 construction does not use QAOA outcomes.",
        "",
        f"**Audit verdict: `{verdict}`.**",
        "",
        "## V1 summary",
        "",
        f"- Duplicated budgets: {v1_summary['duplicated_budget_rows']} / {v1_summary['task_count']} "
        f"({v1_summary['duplicated_budget_percentage']:.2f}%).",
        f"- Duplicated feasible sets: {v1_summary['duplicated_feasible_set_rows']} / "
        f"{v1_summary['task_count']} ({v1_summary['duplicated_feasible_set_percentage']:.2f}%).",
        f"- Effective distinct levels per graph: min {v1_summary['effective_levels_min']}, "
        f"median {v1_summary['effective_levels_median']:.1f}, max {v1_summary['effective_levels_max']}.",
        f"- Feasible-state fraction: min {v1_summary['feasible_state_fraction_min']:.12g}, "
        f"median {v1_summary['feasible_state_fraction_median']:.12g}, "
        f"max {v1_summary['feasible_state_fraction_max']:.12g}.",
        f"- Dilution score range: {v1_summary['dilution_score_min']:.4f} to "
        f"{v1_summary['dilution_score_max']:.4f}.",
        "",
        "## Why 53 duplicate cases occurred",
        "",
        f"- {v1_summary['repeated_quantile_index_duplicates']} rows: repeated `lower`-quantile "
        "order-statistic indices. All are in S1/S2, whose graphs have only 3/4 candidate routes; "
        "seven requested quantiles therefore cannot yield seven sets.",
        f"- {v1_summary['integer_resource_tie_duplicates']} rows: different order-statistic indices "
        "had equal route-resource sums under edge resources drawn from integers 1–9.",
        f"- {v1_summary['budget_rounding_duplicates']} rows: budget rounding. V1 selected observed "
        "integer route resources directly, so there was no separate rounding operation.",
        f"- Across {v1_summary['total_candidate_routes']} route entries there were "
        f"{v1_summary['total_unique_resource_consumptions']} per-graph unique consumptions, leaving "
        f"{v1_summary['resource_tie_excess_routes']} tied excess entries.",
        f"- {v1_summary['graphs_with_fewer_than_7_candidate_routes']} graphs structurally cannot "
        "supply seven path-cardinality levels; "
        f"{v1_summary['graphs_with_fewer_than_7_unique_resources']} graphs had fewer than seven "
        "unique resource thresholds after integer ties.",
        "",
        "The generator structure is therefore the hard resolution limit for S1/S2. The narrow",
        "integer resource support contributes the remaining ties. Fixed ordinary quantiles can",
        "also miss an available distinct threshold when a selected order statistic is tied.",
        "",
        "## V1 vs prospective v2 coverage",
        "",
        "| Metric | Phase 0 v1 | Stress v2 |",
        "|---|---:|---:|",
        f"| Task rows | {v1_coverage['task_rows']} | {v2_coverage['task_rows']} |",
        f"| Summed distinct feasible sets | {v1_coverage['distinct_feasible_sets_summed_over_graphs']} | "
        f"{v2_coverage['distinct_feasible_sets_summed_over_graphs']} |",
        f"| Globally distinct phi_state values | {v1_coverage['globally_distinct_phi_values']} | "
        f"{v2_coverage['globally_distinct_phi_values']} |",
        f"| Minimum phi_state | {v1_coverage['feasible_state_fraction_min']:.12g} | "
        f"{v2_coverage['feasible_state_fraction_min']:.12g} |",
        f"| Median phi_state | {v1_coverage['feasible_state_fraction_median']:.12g} | "
        f"{v2_coverage['feasible_state_fraction_median']:.12g} |",
        f"| Maximum phi_state | {v1_coverage['feasible_state_fraction_max']:.12g} | "
        f"{v2_coverage['feasible_state_fraction_max']:.12g} |",
        f"| Dilution score range | {v1_coverage['dilution_score_min']:.4f}–"
        f"{v1_coverage['dilution_score_max']:.4f} | {v2_coverage['dilution_score_min']:.4f}–"
        f"{v2_coverage['dilution_score_max']:.4f} |",
        "",
        f"V2 adds {improvement} distinct within-graph feasible sets ({improvement_pct:.2f}%) while "
        f"storing zero duplicated primary sets. {v2_summary['insufficient_distinct_graph_count']} "
        "graphs are explicitly marked `INSUFFICIENT_DISTINCT_FEASIBLE_SETS`; no row is copied to "
        "force a balanced 175-task matrix. V2 improves distinct resolution, not the theoretical "
        "global endpoints, which were already reached by v1.",
        "",
        f"Wide integer support 1–1000 produced "
        f"{v2_summary['total_unique_resource_consumptions_across_graphs']} unique route-resource "
        f"thresholds across {v2_summary['total_candidate_routes_across_graphs']} per-graph route "
        "entries and zero resource-tie graphs. V2 has fewer globally unique numeric phi values "
        "because its shared cardinality schedule repeats the same count/2^m values across base "
        "graphs; its gain is within-graph distinct stress resolution.",
        "",
        "## Theoretical and actual minima by size",
        "",
        "| Size | Edges | Theoretical minimum 1/2^m | V1 actual minimum | V2 actual minimum |",
        "|---|---:|---:|---:|---:|",
    ]
    for stratum in sorted(v2.size_stratum.unique()):
        part1 = v1[v1.size_stratum == stratum]
        part2 = v2[v2.size_stratum == stratum]
        edges = int(part2.n_edges.iloc[0])
        lines.append(
            f"| {stratum} | {edges} | {1/(2**edges):.12g} | "
            f"{part1.feasible_state_fraction.min():.12g} | "
            f"{part2.feasible_state_fraction.min():.12g} |"
        )
    lines.extend(
        [
            "",
            "## Pilot Phase 1 projection (not executed)",
            "",
            f"- Selected pilot tasks: {projection['pilot_task_count']}.",
            f"- Penalty-X runs: {projection['phase1_penalty_x_run_count']}.",
            f"- Single-process central wall time: "
            f"{projection['wall_clock_central_hours_single_process']:.3f} h "
            f"(range {projection['wall_clock_range_hours_single_process'][0]:.3f}–"
            f"{projection['wall_clock_range_hours_single_process'][1]:.3f} h).",
            f"- Conservative peak process RSS: {projection['conservative_peak_process_rss_mb']:.1f} MiB.",
            f"- Estimated disk without statevectors: "
            f"{projection['estimated_total_disk_mb_without_statevectors']:.2f} MiB.",
            "",
            "## Per-base-graph v1 audit",
            "",
        ]
    )
    headers = [
        "Base graph",
        "m",
        "2^m",
        "Routes",
        "Unique R",
        "Effective",
        "Index dup",
        "Tie dup",
        "Duplicate pairs",
    ]
    for level in ("T1", "T2", "T3", "T4", "T5", "T6", "T7"):
        headers.extend([f"{level} phi", f"{level} route"])
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|")
    for item in audit.itertuples():
        values = [
            item.base_instance_id,
            str(item.n_edges),
            str(item.state_space_size),
            str(item.n_candidate_routes),
            str(item.unique_resource_consumptions),
            str(item.effective_levels),
            str(item.repeated_quantile_index_duplicates),
            str(item.integer_resource_tie_duplicates),
            item.duplicate_tightness_pairs,
        ]
        for level in ("T1", "T2", "T3", "T4", "T5", "T6", "T7"):
            values.extend(
                [
                    f"{getattr(item, f'phi_{level}'):.8g}",
                    f"{getattr(item, f'route_{level}'):.6g}",
                ]
            )
        lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run_phase05(config_path: str | Path) -> dict[str, Any]:
    started = time.perf_counter()
    hashes_before = verify_v1_evidence_hashes()
    audit, v1_summary = build_v1_graph_audit()
    v1 = pd.read_csv(PROJECT_ROOT / "results" / "phase0" / "task_characterization.csv")
    v2, v2_summary = generate_stress_universe(config_path)
    paths = _stress_paths()
    figure_paths = plot_stress_audit(v1, v2, audit, paths["figures"])

    pilot_tasks = (
        v2.sort_values(["size_stratum", "stress_level", "base_index"])
        .groupby(["size_stratum", "stress_level"], sort=False)
        .head(2)
        .reset_index(drop=True)
    )
    projection = build_resource_projection(
        pilot_tasks,
        config_path,
        PROJECT_ROOT / "results" / "smoke" / "master_results.csv",
    )
    projection.update(
        {
            "pilot_task_count": int(len(pilot_tasks)),
            "pilot_selection": "up to 2 base instances per size_stratum x stress_level",
            "full_phase1_executed": False,
        }
    )
    write_json(paths["projection"], projection)

    v1_coverage = _coverage_summary(v1)
    v2_coverage = _coverage_summary(v2)
    verdict = (
        "V2_RECOMMENDED"
        if v2_coverage["distinct_feasible_sets_summed_over_graphs"]
        > v1_coverage["distinct_feasible_sets_summed_over_graphs"]
        and v2_summary["duplicate_feasible_set_count"] == 0
        else "V1_SUFFICIENT"
    )
    report_path = write_audit_report(
        audit, v1_summary, v1, v2, v2_summary, projection, verdict
    )
    hashes_after = verify_v1_evidence_hashes()
    if hashes_before != hashes_after:
        raise AssertionError("v1 evidence changed during Phase 0.5")
    summary = {
        **v2_summary,
        "audit_verdict": verdict,
        "recommended_task_universe": "use v2 for Phase 1" if verdict == "V2_RECOMMENDED" else "keep v1",
        "v1": v1_coverage,
        "v2": v2_coverage,
        "v1_duplicate_cause_counts": {
            "repeated_quantile_indices_due_to_too_few_routes": v1_summary[
                "repeated_quantile_index_duplicates"
            ],
            "integer_resource_ties_at_distinct_indices": v1_summary[
                "integer_resource_tie_duplicates"
            ],
            "budget_rounding": 0,
        },
        "pilot_projection": projection,
        "figures": [str(Path(path).relative_to(PROJECT_ROOT)) for path in figure_paths],
        "audit_report": str(report_path.relative_to(PROJECT_ROOT)),
        "v1_evidence_hashes_verified": hashes_after,
        "phase05_wall_time_s": time.perf_counter() - started,
        "full_phase1_executed": False,
    }
    write_json(paths["summary"], summary)
    return summary
