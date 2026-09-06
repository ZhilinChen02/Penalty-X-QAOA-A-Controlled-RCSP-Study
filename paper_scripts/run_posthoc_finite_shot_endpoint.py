#!/usr/bin/env python3
"""Run post-hoc finite-shot sampling at frozen held-out O0/O3 endpoints.

The script regenerates controlled tasks in memory, recreates terminal
statevectors from frozen p=3 parameters, verifies exact metrics against the
authoritative endpoint rows, and only then writes sampling summaries.  It does
not optimize parameters and never persists raw statevectors or samples.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qroute_dilution.models import Task
from qroute_dilution.penalties import build_raw_state_components, scale_controlled_penalties
from qroute_dilution.phase1_2_objectives import weighted_exact_cvar
from qroute_dilution.qaoa import simulate_qaoa
from qroute_dilution.stress import build_stress_task_family


OUTPUT = ROOT / "results" / "posthoc_finite_shot_endpoint_v1"
OVERLEAF_FIGURE = ROOT / "overleaf" / "figures" / "fig11_finite_shot_endpoint_robustness.pdf"
LABEL = "POSTHOC_FINITE_SHOT_ENDPOINT_ROBUSTNESS"
SHOT_COUNTS = (1_000, 10_000, 100_000)
REPLICATES = 20
ALPHA = 0.10
EXACT_TOLERANCE = 5e-12
NORMALIZATION_FACTOR = 172.0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def scientific_task_payload(task: Task) -> dict[str, Any]:
    """Return deterministic scientific task content, excluding measured build times."""
    payload = task.to_dict()
    payload.pop("task_build_time_s", None)
    payload.pop("exact_reference_time_s", None)
    return payload


def task_payload_hash(task: Task) -> str:
    encoded = json.dumps(
        scientific_task_payload(task),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def regenerate_tasks() -> tuple[dict[str, Task], dict[str, str], dict[str, Any]]:
    with (ROOT / "configs/phase0_v2_dilution_stress.yaml").open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    manifest = json.loads(
        (ROOT / "data/manifests/phase0_v2_dilution_stress.json").read_text(
            encoding="utf-8"
        )
    )
    characterization = pd.read_csv(
        ROOT / "results/phase0_v2_dilution_stress/task_characterization.csv"
    ).set_index("task_id")
    tasks: dict[str, Task] = {}
    payload_hashes: dict[str, str] = {}
    for stratum, specification in config["size_strata"].items():
        for base_index in range(int(config["instances_per_stratum"])):
            family = build_stress_task_family(
                size_stratum=stratum,
                target_n_edges=int(specification["target_n_edges"]),
                layer_widths=specification["layer_widths"],
                base_index=base_index,
                master_seed=int(config["master_seed"]),
                resource_range=tuple(int(value) for value in config["resource_range"]),
                preferred_counts=tuple(
                    int(value) for value in config["preferred_feasible_route_counts"]
                ),
                max_levels=int(config["max_distinct_levels"]),
            )
            for task, _ in family:
                if task.task_id in tasks:
                    raise RuntimeError(f"STOP: duplicate regenerated task {task.task_id}")
                tasks[task.task_id] = task
                payload_hashes[task.task_id] = task_payload_hash(task)

    manifest_rows = {row["task_id"]: row for row in manifest["tasks"]}
    if set(tasks) != set(manifest_rows) or set(tasks) != set(characterization.index):
        raise RuntimeError("STOP: regenerated task identity set differs from frozen evidence")

    maximum_numeric_difference = 0.0
    for task_id, task in tasks.items():
        manifest_row = manifest_rows[task_id]
        observed_identity = {
            "graph_id": task.graph.graph_id,
            "base_instance_id": task.base_instance_id,
            "size_stratum": task.size_stratum,
            "stress_level": task.tightness_level,
            "actual_feasible_route_count": len(task.feasible_routes),
        }
        for key, value in observed_identity.items():
            if value != manifest_row[key]:
                raise RuntimeError(
                    f"STOP: regenerated task mismatch {task_id} {key}: "
                    f"{value!r} != {manifest_row[key]!r}"
                )
        if float(task.budget) != float(manifest_row["budget"]):
            raise RuntimeError(f"STOP: regenerated budget mismatch for {task_id}")

        canonical = characterization.loc[task_id]
        comparisons = {
            "budget": (float(task.budget), float(canonical.budget)),
            "n_edges": (float(len(task.graph.edges)), float(canonical.n_edges)),
            "n_candidate_routes": (
                float(len(task.candidate_routes)),
                float(canonical.n_candidate_routes),
            ),
            "n_feasible_routes": (
                float(len(task.feasible_routes)),
                float(canonical.n_feasible_routes),
            ),
            "n_optimal_states": (
                float(len(task.optimal_routes)),
                float(canonical.n_optimal_states),
            ),
            "feasible_state_fraction": (
                len(task.feasible_routes) / (1 << len(task.graph.edges)),
                float(canonical.feasible_state_fraction),
            ),
            "optimal_cost": (float(task.optimal_cost), float(canonical.optimal_cost)),
        }
        for field, (observed, expected) in comparisons.items():
            difference = abs(observed - expected)
            maximum_numeric_difference = max(maximum_numeric_difference, difference)
            if difference > EXACT_TOLERANCE:
                raise RuntimeError(
                    f"STOP: regenerated characterization mismatch {task_id} {field}: "
                    f"difference={difference}"
                )
    audit = {
        "regenerated_task_count": len(tasks),
        "regenerated_base_graph_count": len({task.graph.graph_id for task in tasks.values()}),
        "manifest_identity_mismatches": 0,
        "characterization_mismatches": 0,
        "maximum_characterization_abs_difference": maximum_numeric_difference,
        "task_payload_hash_definition": (
            "SHA-256 of sorted compact Task JSON excluding nondeterministic build-time fields"
        ),
    }
    return tasks, payload_hashes, audit


def build_task_context(task: Task, components: Any, controlled_flow: np.ndarray) -> dict[str, Any]:
    resource_excess = np.maximum(0.0, components.resource_total - task.budget)
    _, controlled_resource = scale_controlled_penalties(
        components.flow_penalty_raw,
        resource_excess,
        flow_scale=max(float(components.flow_penalty_raw.max()), 1.0),
        resource_scale=float(sum(edge.resource for edge in task.graph.edges)),
    )
    energy = (
        components.routing_cost
        + 172.0 * controlled_flow
        + 172.0 * controlled_resource
    ) / NORMALIZATION_FACTOR
    feasible = np.zeros(len(energy), dtype=bool)
    optimal = np.zeros(len(energy), dtype=bool)
    feasible[[route.bitstring_int for route in task.feasible_routes]] = True
    optimal[[route.bitstring_int for route in task.optimal_routes]] = True
    return {
        "energy": energy,
        "energy_order": np.argsort(energy, kind="stable"),
        "feasible": feasible,
        "optimal": optimal,
    }


def sampling_seed(task_id: str, objective: str, shots: int, replicate: int) -> int:
    payload = f"{LABEL}|v1|{task_id}|{objective}|{shots}|{replicate}"
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def empirical_lower_tail_cvar(sample_energies: np.ndarray, alpha: float) -> float:
    """Lowest-energy empirical tail with fractional weighting at a noninteger cutoff."""
    values = np.asarray(sample_energies, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("sample energies must be a finite nonempty vector")
    tail_size = float(alpha) * len(values)
    full = int(math.floor(tail_size + 1e-12))
    fractional = max(0.0, tail_size - full)
    needed = full + (1 if fractional > 1e-12 else 0)
    if needed <= 0:
        raise ValueError("alpha is too small for this finite sample")
    if needed >= len(values):
        ordered = np.sort(values)
    else:
        ordered = np.partition(values, needed - 1)[:needed]
        ordered.sort()
    numerator = float(ordered[:full].sum()) if full else 0.0
    if fractional > 1e-12:
        numerator += fractional * float(ordered[full])
    return numerator / tail_size


def draw_estimates(
    probabilities: np.ndarray,
    context: dict[str, Any],
    *,
    task_id: str,
    objective: str,
    shots: int,
    replicate: int,
) -> dict[str, Any]:
    seed = sampling_seed(task_id, objective, shots, replicate)
    rng = np.random.default_rng(seed)
    cdf = np.cumsum(probabilities, dtype=np.float64)
    cdf[-1] = 1.0
    states = np.searchsorted(cdf, rng.random(int(shots)), side="right")
    energies = context["energy"][states]
    return {
        "sampling_seed": seed,
        "p_feas_estimate": float(context["feasible"][states].mean()),
        "p_opt_estimate": float(context["optimal"][states].mean()),
        "mean_energy_estimate": float(energies.mean()),
        "cvar_0_10_estimate": empirical_lower_tail_cvar(energies, ALPHA),
    }


def exact_metrics(probabilities: np.ndarray, context: dict[str, Any]) -> dict[str, float]:
    return {
        "p_feas": float(probabilities[context["feasible"]].sum()),
        "p_opt": float(probabilities[context["optimal"]].sum()),
        "mean_energy": float(np.dot(probabilities, context["energy"])),
        "cvar_0_10": float(
            weighted_exact_cvar(
                context["energy"],
                probabilities,
                ALPHA,
                energy_order=context["energy_order"],
            )["cvar_value"]
        ),
    }


def build_aggregate(metrics: pd.DataFrame) -> pd.DataFrame:
    metric_columns = {
        "p_feas": ("p_feas_estimate", "p_feas_exact"),
        "p_opt": ("p_opt_estimate", "p_opt_exact"),
        "mean_energy": ("mean_energy_estimate", "mean_energy_exact"),
        "cvar_0.10": ("cvar_0_10_estimate", "cvar_0_10_exact"),
    }
    rows: list[dict[str, Any]] = []
    scopes = [("ALL", metrics)] + [
        (stratum, group) for stratum, group in metrics.groupby("size_stratum", sort=True)
    ]
    for scope, scoped in scopes:
        for (objective, shots), group in scoped.groupby(["objective_id", "shots"], sort=True):
            for metric, (estimate_column, exact_column) in metric_columns.items():
                estimates = group[estimate_column].to_numpy(dtype=float)
                exact = group[exact_column].to_numpy(dtype=float)
                error = estimates - exact
                relative = np.divide(
                    error,
                    np.abs(exact),
                    out=np.full_like(error, np.nan),
                    where=np.abs(exact) > 1e-12,
                )
                rows.append(
                    {
                        "record_type": "ESTIMATOR_ERROR",
                        "scope": scope,
                        "objective_id": objective,
                        "shots": int(shots),
                        "metric": metric,
                        "n_estimates": int(len(error)),
                        "n_tasks": int(group.task_id.nunique()),
                        "bias": float(error.mean()),
                        "mae": float(np.abs(error).mean()),
                        "standard_deviation": float(error.std(ddof=1)),
                        "rmse": float(np.sqrt(np.mean(error**2))),
                        "error_p05": float(np.quantile(error, 0.05)),
                        "error_p50": float(np.quantile(error, 0.50)),
                        "error_p95": float(np.quantile(error, 0.95)),
                        "estimate_p05": float(np.quantile(estimates, 0.05)),
                        "estimate_p50": float(np.quantile(estimates, 0.50)),
                        "estimate_p95": float(np.quantile(estimates, 0.95)),
                        "relative_bias": float(np.nanmean(relative)),
                        "relative_mae": float(np.nanmean(np.abs(relative))),
                        "relative_rmse": float(np.sqrt(np.nanmean(relative**2))),
                        "ordering_agreement_probability": math.nan,
                        "ordering_comparison_count": 0,
                        "exact_tie_count": 0,
                    }
                )

    pair_identity = ["task_id", "size_stratum", "shots", "replicate"]
    for metric, (estimate_column, exact_column) in metric_columns.items():
        paired = metrics.pivot(index=pair_identity, columns="objective_id", values=[estimate_column, exact_column])
        paired.columns = [f"{column}_{objective}" for column, objective in paired.columns]
        paired = paired.reset_index()
        sampled_delta = paired[f"{estimate_column}_O3"] - paired[f"{estimate_column}_O0"]
        exact_delta = paired[f"{exact_column}_O3"] - paired[f"{exact_column}_O0"]
        sampled_sign = np.sign(sampled_delta.to_numpy(dtype=float))
        exact_sign = np.sign(exact_delta.to_numpy(dtype=float))
        paired["agreement"] = sampled_sign == exact_sign
        paired["exact_tie"] = exact_sign == 0.0
        ordering_scopes = [("ALL", paired)] + [
            (stratum, group) for stratum, group in paired.groupby("size_stratum", sort=True)
        ]
        for scope, scoped in ordering_scopes:
            for shots, group in scoped.groupby("shots", sort=True):
                comparable = group[~group.exact_tie]
                rows.append(
                    {
                        "record_type": "ORDERING_AGREEMENT",
                        "scope": scope,
                        "objective_id": "O3_vs_O0",
                        "shots": int(shots),
                        "metric": metric,
                        "n_estimates": int(len(group)),
                        "n_tasks": int(group.task_id.nunique()),
                        "bias": math.nan,
                        "mae": math.nan,
                        "standard_deviation": math.nan,
                        "rmse": math.nan,
                        "error_p05": math.nan,
                        "error_p50": math.nan,
                        "error_p95": math.nan,
                        "estimate_p05": math.nan,
                        "estimate_p50": math.nan,
                        "estimate_p95": math.nan,
                        "relative_bias": math.nan,
                        "relative_mae": math.nan,
                        "relative_rmse": math.nan,
                        "ordering_agreement_probability": float(comparable.agreement.mean()),
                        "ordering_comparison_count": int(len(comparable)),
                        "exact_tie_count": int(group.exact_tie.sum()),
                    }
                )
    return pd.DataFrame(rows)


def make_figure(metrics: pd.DataFrame, aggregate: pd.DataFrame, output: Path) -> None:
    colors = {"O0": "#3264A8", "O3": "#C94C4C"}
    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.75))
    panels = [
        (axes[0], "cvar_0.10", "CVaR-0.10 mean absolute error", "a"),
        (axes[1], "p_feas", r"$P_{\mathrm{feas}}$ mean absolute error", "b"),
    ]
    estimator = aggregate[
        aggregate.record_type.eq("ESTIMATOR_ERROR") & aggregate.scope.eq("ALL")
    ]
    for ax, metric, ylabel, label in panels:
        for objective in ("O0", "O3"):
            summary = estimator[
                estimator.objective_id.eq(objective) & estimator.metric.eq(metric)
            ].sort_values("shots")
            ax.plot(summary.shots, summary.mae, marker="o", color=colors[objective], label=objective)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("shots")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.22)
        ax.text(-0.14, 1.06, label, transform=ax.transAxes, fontweight="bold")
    axes[0].legend(frameon=False)

    ax = axes[2]
    ordering = aggregate[
        aggregate.record_type.eq("ORDERING_AGREEMENT")
        & aggregate.scope.eq("ALL")
        & aggregate.metric.isin(["p_feas", "p_opt", "cvar_0.10"])
    ]
    styles = {"p_feas": "o-", "p_opt": "s--", "cvar_0.10": "^-"}
    labels = {"p_feas": r"$P_{\mathrm{feas}}$", "p_opt": r"$P_{\mathrm{opt}}$", "cvar_0.10": "CVaR"}
    for metric, group in ordering.groupby("metric", sort=False):
        group = group.sort_values("shots")
        ax.plot(
            group.shots,
            group.ordering_agreement_probability,
            styles[metric],
            label=labels[metric],
        )
    ax.set_xscale("log")
    ax.set_ylim(0.45, 1.01)
    ax.set_xlabel("shots")
    ax.set_ylabel("O3-vs-O0 ordering recovered")
    ax.grid(alpha=0.22)
    ax.legend(frameon=False)
    ax.text(-0.14, 1.06, "c", transform=ax.transAxes, fontweight="bold")
    fig.tight_layout()
    metadata = {"CreationDate": None, "ModDate": None} if output.suffix.lower() == ".pdf" else None
    fig.savefig(output, metadata=metadata, dpi=180)
    plt.close(fig)


def build_readme(aggregate: pd.DataFrame, exact_max_difference: float) -> str:
    ordering = aggregate[
        aggregate.record_type.eq("ORDERING_AGREEMENT") & aggregate.scope.eq("ALL")
    ]
    pfeas = ordering[ordering.metric.eq("p_feas")].set_index("shots")
    cvar = aggregate[
        aggregate.record_type.eq("ESTIMATOR_ERROR")
        & aggregate.scope.eq("ALL")
        & aggregate.metric.eq("cvar_0.10")
    ]
    lines = [
        "# POSTHOC_FINITE_SHOT_ENDPOINT_ROBUSTNESS",
        "",
        "This directory contains a post-hoc sampling analysis of the already-frozen",
        "O0 and O3 terminal distributions for all 84 held-out tasks. It is not a new",
        "confirmatory experiment, does not retrain QAOA, and does not change the",
        "preregistered H1/H2 family or its interpretation.",
        "",
        "## Design",
        "",
        "- Endpoints: frozen p=3 terminal parameters for O0 and O3.",
        "- Sampling: 1,000, 10,000, and 100,000 shots; 20 deterministic replicates.",
        "- Seed identity: SHA-256 of label, task ID, objective, shot count, and replicate.",
        "- Estimators: P_feas, P_opt, normalized mean Hamiltonian energy, and empirical",
        "  lowest-energy CVaR-0.10.",
        "- All requested shot counts make alpha*N an integer (100, 1,000, 10,000).",
        "  The implementation nevertheless supports a fractional final observation for",
        "  noninteger cutoffs by weighting it fractionally before dividing by alpha*N.",
        "- Individual samples and raw statevectors are not persisted.",
        "- Ordering recovery is conditioned on a non-tied exact O3-vs-O0",
        "  comparison; exact ties are counted separately in `aggregate.csv`.",
        "",
        "## Integrity",
        "",
        "The 140-task universe was regenerated only in memory from the frozen generator",
        "seed/configuration and matched every manifest identity and characterization row.",
        f"The maximum absolute regenerated endpoint difference from stored exact metrics was `{exact_max_difference:.3e}`.",
        "",
        "## Compact ordering summary",
        "",
        "| Shots | P_feas O3-vs-O0 ordering recovered |",
        "|---:|---:|",
    ]
    for shots, row in pfeas.sort_index().iterrows():
        lines.append(f"| {int(shots):,} | {row.ordering_agreement_probability:.3f} |")
    lines.extend(
        [
            "",
            "Full bias, MAE, standard deviation, RMSE, percentile, relative-error, and",
            "ordering summaries are in `aggregate.csv`. Replicate-level estimates (not",
            "individual samples) are in `metrics.csv`.",
            "",
            "## Interpretation boundary",
            "",
            "These results quantify estimator uncertainty at exact simulator endpoints.",
            "They do not establish finite-shot training robustness, device robustness,",
            "noise robustness, compilation robustness, or hardware performance.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    tasks, payload_hashes, task_audit = regenerate_tasks()
    heldout_manifest = json.loads(
        (ROOT / "data/manifests/phase2_confirmatory_v1.json").read_text(encoding="utf-8")
    )
    heldout_ids = [row["task_id"] for row in heldout_manifest["tasks"]]
    endpoints = pd.read_csv(ROOT / "results/phase2_confirmatory_v1/p3_objective_results.csv")
    endpoints = endpoints[endpoints.objective_id.isin(["O0", "O3"])].copy()
    if len(endpoints) != 168 or endpoints.task_id.nunique() != 84:
        raise RuntimeError("STOP: frozen O0/O3 endpoint matrix is incomplete")
    if set(endpoints.task_id) != set(heldout_ids):
        raise RuntimeError("STOP: endpoint task IDs differ from the held-out manifest")
    if endpoints.terminal_parameters.isna().any():
        raise RuntimeError("STOP: a frozen terminal parameter vector is unavailable")

    endpoint_index = endpoints.set_index(["task_id", "objective_id"])
    exact_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    maximum_exact_difference = 0.0
    graphs: dict[str, tuple[Any, np.ndarray]] = {}

    for position, task_id in enumerate(heldout_ids, start=1):
        task = tasks[task_id]
        if task.graph.graph_id not in graphs:
            components = build_raw_state_components(task.graph)
            controlled_flow, _ = scale_controlled_penalties(
                components.flow_penalty_raw,
                np.zeros_like(components.resource_total),
                flow_scale=max(float(components.flow_penalty_raw.max()), 1.0),
                resource_scale=float(sum(edge.resource for edge in task.graph.edges)),
            )
            graphs[task.graph.graph_id] = (components, controlled_flow)
        components, controlled_flow = graphs[task.graph.graph_id]
        context = build_task_context(task, components, controlled_flow)
        print(
            f"[{position:02d}/84] {task_id} m={len(task.graph.edges)} {task.tightness_level}",
            flush=True,
        )
        for objective in ("O0", "O3"):
            stored = endpoint_index.loc[(task_id, objective)]
            parameters_text = str(stored.terminal_parameters)
            parameters = np.asarray(json.loads(parameters_text), dtype=np.float64)
            if parameters.shape != (6,) or not np.isfinite(parameters).all():
                raise RuntimeError(f"STOP: invalid terminal parameters for {task_id}/{objective}")
            state = simulate_qaoa(parameters, context["energy"], depth=3)
            probabilities = np.abs(state) ** 2
            exact = exact_metrics(probabilities, context)
            stored_values = {
                "p_feas": float(stored.p_feas),
                "p_opt": float(stored.p_opt),
                "mean_energy": float(stored.mean_energy),
                "cvar_0_10": float(stored.cvar_value),
            }
            differences = {
                metric: abs(exact[metric] - stored_values[metric]) for metric in exact
            }
            maximum_exact_difference = max(maximum_exact_difference, max(differences.values()))
            if max(differences.values()) > EXACT_TOLERANCE:
                raise RuntimeError(
                    f"STOP: exact endpoint reconstruction mismatch for {task_id}/{objective}: "
                    f"{differences}"
                )
            exact_rows.append(
                {
                    "evidence_label": LABEL,
                    "task_id": task_id,
                    "base_graph_id": task.graph.graph_id,
                    "base_instance_id": task.base_instance_id,
                    "size_stratum": task.size_stratum,
                    "stress_level": task.tightness_level,
                    "n_edges": len(task.graph.edges),
                    "dilution_score": float(stored.dilution_score),
                    "objective_id": objective,
                    "depth": 3,
                    "task_scientific_payload_sha256": payload_hashes[task_id],
                    "terminal_parameters_sha256": hashlib.sha256(parameters_text.encode()).hexdigest(),
                    "p_feas_exact": exact["p_feas"],
                    "p_opt_exact": exact["p_opt"],
                    "mean_energy_exact": exact["mean_energy"],
                    "cvar_0_10_exact": exact["cvar_0_10"],
                    "probability_norm": float(probabilities.sum()),
                    "max_abs_difference_vs_stored": max(differences.values()),
                    "source_run_id": str(stored.run_id),
                }
            )
            for shots in SHOT_COUNTS:
                for replicate in range(REPLICATES):
                    sampled = draw_estimates(
                        probabilities,
                        context,
                        task_id=task_id,
                        objective=objective,
                        shots=shots,
                        replicate=replicate,
                    )
                    metric_rows.append(
                        {
                            "evidence_label": LABEL,
                            "task_id": task_id,
                            "base_graph_id": task.graph.graph_id,
                            "base_instance_id": task.base_instance_id,
                            "size_stratum": task.size_stratum,
                            "stress_level": task.tightness_level,
                            "n_edges": len(task.graph.edges),
                            "dilution_score": float(stored.dilution_score),
                            "objective_id": objective,
                            "shots": int(shots),
                            "replicate": int(replicate),
                            **sampled,
                            "p_feas_exact": exact["p_feas"],
                            "p_opt_exact": exact["p_opt"],
                            "mean_energy_exact": exact["mean_energy"],
                            "cvar_0_10_exact": exact["cvar_0_10"],
                            "p_feas_error": sampled["p_feas_estimate"] - exact["p_feas"],
                            "p_opt_error": sampled["p_opt_estimate"] - exact["p_opt"],
                            "mean_energy_error": sampled["mean_energy_estimate"] - exact["mean_energy"],
                            "cvar_0_10_error": sampled["cvar_0_10_estimate"] - exact["cvar_0_10"],
                        }
                    )
            del state, probabilities
        del context

    exact_reference = pd.DataFrame(exact_rows)
    metrics = pd.DataFrame(metric_rows)
    aggregate = build_aggregate(metrics)
    if len(exact_reference) != 168 or len(metrics) != 84 * 2 * 3 * REPLICATES:
        raise RuntimeError("STOP: post-hoc output denominator mismatch")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    exact_reference.to_csv(OUTPUT / "exact_reference.csv", index=False)
    metrics.to_csv(OUTPUT / "metrics.csv", index=False)
    aggregate.to_csv(OUTPUT / "aggregate.csv", index=False)

    sampling_config = {
        "schema_version": "posthoc_finite_shot_endpoint_v1.sampling.v1",
        "evidence_label": LABEL,
        "scientific_role": "POSTHOC_ROBUSTNESS_ONLY",
        "task_selection": "all 84 held-out tasks; no result-dependent selection",
        "objectives": ["O0", "O3"],
        "depth": 3,
        "shot_counts": list(SHOT_COUNTS),
        "replicates_per_task_objective_shot_count": REPLICATES,
        "cvar_alpha": ALPHA,
        "seed_derivation": (
            "uint64(first 8 bytes SHA256('POSTHOC_FINITE_SHOT_ENDPOINT_ROBUSTNESS|"
            "v1|<task_id>|<objective>|<shots>|<replicate>'))"
        ),
        "empirical_cvar": (
            "mean of the lowest alpha*N sampled normalized-Hamiltonian energies; "
            "a fractional final order statistic is weighted if alpha*N is noninteger"
        ),
        "requested_tail_counts": {str(shots): int(ALPHA * shots) for shots in SHOT_COUNTS},
        "raw_samples_persisted": False,
        "raw_statevectors_persisted": False,
        "optimizer_invoked": False,
        "finite_shot_training": False,
        "hardware_noise_model": False,
    }
    write_json(OUTPUT / "sampling_config.json", sampling_config)

    make_figure(metrics, aggregate, OUTPUT / "figure11_finite_shot_endpoint_robustness.pdf")
    make_figure(metrics, aggregate, OUTPUT / "figure11_finite_shot_endpoint_robustness.png")
    OVERLEAF_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    make_figure(metrics, aggregate, OVERLEAF_FIGURE)
    (OUTPUT / "README.md").write_text(
        build_readme(aggregate, maximum_exact_difference), encoding="utf-8"
    )

    input_files = [
        "configs/phase0_v2_dilution_stress.yaml",
        "configs/penalty_contract_v2_scale_controlled.yaml",
        "configs/phase1_pilot_v1.yaml",
        "data/manifests/phase0_v2_dilution_stress.json",
        "data/manifests/phase2_confirmatory_v1.json",
        "results/phase0_v2_dilution_stress/task_characterization.csv",
        "results/phase2_confirmatory_v1/p3_objective_results.csv",
        "src/qroute_dilution/graph_generator.py",
        "src/qroute_dilution/stress.py",
        "src/qroute_dilution/penalties.py",
        "src/qroute_dilution/qaoa.py",
        "paper_scripts/run_posthoc_finite_shot_endpoint.py",
    ]
    output_files = [
        "metrics.csv",
        "aggregate.csv",
        "exact_reference.csv",
        "sampling_config.json",
        "README.md",
        "figure11_finite_shot_endpoint_robustness.pdf",
        "figure11_finite_shot_endpoint_robustness.png",
    ]
    manifest = {
        "schema_version": "posthoc_finite_shot_endpoint_v1.manifest.v1",
        "evidence_label": LABEL,
        "scientific_role": "POSTHOC_ROBUSTNESS_ONLY",
        "status": "COMPLETE",
        "primary_inference_changed": False,
        "optimizer_parameters_changed": False,
        "optimizer_invoked": False,
        "task_selection": "ALL_84_HELDOUT_TASKS_OUTCOME_BLIND",
        "task_count": 84,
        "base_graph_count": 15,
        "endpoint_count": 168,
        "replicate_metric_rows": int(len(metrics)),
        "total_measurement_draws": int(84 * 2 * REPLICATES * sum(SHOT_COUNTS)),
        "task_reconstruction_audit": task_audit,
        "terminal_parameter_availability": "168/168 O0/O3 endpoints",
        "maximum_exact_metric_abs_difference_vs_authoritative": maximum_exact_difference,
        "exact_reconstruction_tolerance": EXACT_TOLERANCE,
        "input_sha256": {relative: sha256(ROOT / relative) for relative in input_files},
        "output_sha256": {name: sha256(OUTPUT / name) for name in output_files},
        "interpretation_boundary": (
            "Endpoint estimator robustness only; not finite-shot training, hardware, noise, "
            "compilation, or device robustness."
        ),
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(
        f"{LABEL} complete: {len(metrics)} replicate rows; "
        f"max exact difference={maximum_exact_difference:.3e}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
