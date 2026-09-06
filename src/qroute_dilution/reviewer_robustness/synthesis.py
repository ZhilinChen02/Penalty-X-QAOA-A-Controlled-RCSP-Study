"""Read-only scientific synthesis for the completed reviewer-robustness pass."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from qroute_dilution.io import PROJECT_ROOT, atomic_write_csv, atomic_write_text, write_json

from .audit import CANONICAL_HASHES_BEFORE
from .common import REVIEW_ROOT, load_json, verify_canonical_hash_snapshot
from .statistics import bootstrap_mean_ci


SUMMARY_ROOT = REVIEW_ROOT / "summaries"
SYNTHESIS_MARKER = "<!-- REVIEWER_ROBUSTNESS_SYNTHESIS -->"


def _bootstrap(values: np.ndarray, label: str) -> dict[str, float]:
    protocol = load_json(PROJECT_ROOT / "analysis" / "reviewer_robustness" / "protocol_v1.json")
    seed = int(protocol["global"]["bootstrap_seed"])
    offset = int.from_bytes(label.encode("utf-8"), "little", signed=False) % 1_000_003
    return bootstrap_mean_ci(
        np.asarray(values, dtype=float),
        resamples=int(protocol["global"]["bootstrap_resamples"]),
        seed=seed + offset,
    )


def _contrast_record(
    values: np.ndarray,
    *,
    label: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    summary = _bootstrap(values, label)
    return {
        **metadata,
        "n_graphs": int(len(values)),
        "positive_graphs": int((values > 0.0).sum()),
        "zero_graphs": int((values == 0.0).sum()),
        "negative_graphs": int((values < 0.0).sum()),
        **{f"graph_delta_{key}": value for key, value in summary.items()},
    }


def build_depth_budget_contrasts() -> pd.DataFrame:
    graph = pd.read_csv(REVIEW_ROOT / "B1_depth_budget" / "depth_budget_summary_graph.csv")
    rows: list[dict[str, Any]] = []
    metrics = ("objective_value", "G_feas", "P_feas", "P_opt", "P_opt_given_feas")
    for objective in ("O0", "O3"):
        for budget in (120, 240, 480):
            subset = graph[(graph.objective == objective) & (graph.budget == budget)]
            for shallower, deeper in ((2, 3), (3, 4)):
                for metric in metrics:
                    pivot = subset.pivot(index="graph_id", columns="depth", values=metric)
                    values = (pivot[deeper] - pivot[shallower]).to_numpy(dtype=float)
                    label = f"depth:{objective}:{budget}:{shallower}:{deeper}:{metric}"
                    rows.append(
                        _contrast_record(
                            values,
                            label=label,
                            metadata={
                                "contrast_type": "DEPTH",
                                "objective": objective,
                                "budget": budget,
                                "depth": deeper,
                                "comparison": f"p{deeper}_minus_p{shallower}",
                                "metric": metric,
                            },
                        )
                    )
    for objective in ("O0", "O3"):
        for depth in (2, 3, 4):
            subset = graph[(graph.objective == objective) & (graph.depth == depth)]
            for metric in metrics:
                pivot = subset.pivot(index="graph_id", columns="budget", values=metric)
                values = (pivot[480] - pivot[120]).to_numpy(dtype=float)
                label = f"budget:{objective}:{depth}:{metric}"
                rows.append(
                    _contrast_record(
                        values,
                        label=label,
                        metadata={
                            "contrast_type": "BUDGET",
                            "objective": objective,
                            "budget": 480,
                            "depth": depth,
                            "comparison": "nfev480_minus_nfev120",
                            "metric": metric,
                        },
                    )
                )
    result = pd.DataFrame(rows)
    atomic_write_csv(REVIEW_ROOT / "B1_depth_budget" / "depth_budget_contrasts.csv", result)
    return result


def build_alpha_neighborhood_contrasts() -> pd.DataFrame:
    graph = pd.read_csv(REVIEW_ROOT / "A2_alpha" / "alpha_summary_graph.csv")
    rows: list[dict[str, Any]] = []
    metrics = ("G_feas", "P_feas", "P_opt", "P_opt_given_feas")
    discovery = graph[graph.split == "discovery"]
    for alpha in sorted(discovery.alpha.unique()):
        for metric in metrics:
            pivot = discovery.pivot(index="graph_id", columns="alpha", values=metric)
            values = (pivot[float(alpha)] - pivot[0.10]).to_numpy(dtype=float)
            rows.append(
                _contrast_record(
                    values,
                    label=f"alpha:{alpha}:{metric}",
                    metadata={
                        "split": "discovery",
                        "alpha": float(alpha),
                        "reference_alpha": 0.10,
                        "comparison": f"alpha_{float(alpha):g}_minus_alpha_0.1",
                        "metric": metric,
                    },
                )
            )
    result = pd.DataFrame(rows)
    atomic_write_csv(REVIEW_ROOT / "A2_alpha" / "alpha_neighborhood_effects.csv", result)
    return result


def build_resource_summary() -> pd.DataFrame:
    registry = pd.read_csv(REVIEW_ROOT / "run_registry.csv")
    rows: list[dict[str, Any]] = []
    training = pd.read_csv(
        REVIEW_ROOT / "A3_finite_shot" / "finite_shot_training_runs.csv"
    )
    for experiment, group in registry.groupby("experiment", sort=True):
        sampled = 0
        if experiment == "A3_ALPHA_SHOT_ESTIMATOR":
            sampled = int(group.shots.fillna(0).sum())
        elif experiment == "A3_FINITE_SHOT_TRAINING":
            sampled = int(training.total_sampled_bitstrings.sum())
        rows.append(
            {
                "experiment": experiment,
                "formal_records": len(group),
                "complete": int((group.status == "COMPLETE").sum()),
                "failed": int((group.status == "FAILED").sum()),
                "timeout": int((group.status == "TIMEOUT").sum()),
                "actual_objective_calls": int(group.actual_nfev.fillna(0).sum()),
                "sampled_bitstrings": sampled,
                "recorded_worker_runtime_s": float(group.runtime_s.fillna(0).sum()),
            }
        )
    frame = pd.DataFrame(rows)
    total = {
        "experiment": "FORMAL_TOTAL",
        "formal_records": int(frame.formal_records.sum()),
        "complete": int(frame.complete.sum()),
        "failed": int(frame.failed.sum()),
        "timeout": int(frame.timeout.sum()),
        "actual_objective_calls": int(frame.actual_objective_calls.sum()),
        "sampled_bitstrings": int(frame.sampled_bitstrings.sum()),
        "recorded_worker_runtime_s": float(frame.recorded_worker_runtime_s.sum()),
    }
    frame = pd.concat([frame, pd.DataFrame([total])], ignore_index=True)
    atomic_write_csv(SUMMARY_ROOT / "resource_summary.csv", frame)
    return frame


def _append_synthesis(path: Path, body: str) -> None:
    original = path.read_text(encoding="utf-8")
    if SYNTHESIS_MARKER in original:
        original = original.split(SYNTHESIS_MARKER, 1)[0].rstrip()
    atomic_write_text(path, f"{original}\n\n{SYNTHESIS_MARKER}\n\n{body.strip()}\n")


def _row(frame: pd.DataFrame, **filters: Any) -> pd.Series:
    subset = frame
    for key, value in filters.items():
        subset = subset[subset[key] == value]
    if len(subset) != 1:
        raise RuntimeError(f"expected one row for {filters}, found {len(subset)}")
    return subset.iloc[0]


def _phase_addenda(depth: pd.DataFrame, alpha: pd.DataFrame) -> None:
    b1_lines = ["## Completed-result interpretation", ""]
    for objective in ("O0", "O3"):
        for budget in (120, 240, 480):
            g = _row(
                depth,
                contrast_type="DEPTH",
                objective=objective,
                budget=budget,
                comparison="p4_minus_p3",
                metric="G_feas",
            )
            loss = _row(
                depth,
                contrast_type="DEPTH",
                objective=objective,
                budget=budget,
                comparison="p4_minus_p3",
                metric="objective_value",
            )
            b1_lines.append(
                f"- {objective}, {budget} nfev: p4−p3 graph-mean G_feas={g.graph_delta_mean:.4f} "
                f"(95% graph bootstrap CI [{g.graph_delta_ci_lower:.4f}, {g.graph_delta_ci_upper:.4f}]); "
                f"terminal loss difference={loss.graph_delta_mean:.4f} (negative favors p4)."
            )
    b1_lines.extend(
        [
            "",
            "At 120 evaluations p=4 is not worse than p=3 on the reported state-quality metrics: the G_feas contrast is positive for all ten graphs under both O0 and O3. Raising the budget from 120 to 480 modestly improves p=4 mean G_feas, but nested failures do not decline. Thus the experiment does not support an intrinsic p=4 disadvantage or a simple claim that more budget cures the nested diagnostic; depth behavior is objective- and diagnostic-dependent.",
            "",
            "**Claim impact:** mixed for a generic budget-dependent depth-degradation statement, but supportive that p=4 adds information beyond the frozen p=2/p=3 study.",
        ]
    )
    _append_synthesis(
        REVIEW_ROOT / "B1_depth_budget" / "B1_DEPTH_BUDGET.md",
        "\n".join(b1_lines),
    )

    optimizer = pd.read_csv(REVIEW_ROOT / "A1_optimizer" / "optimizer_summary.csv")
    runs = pd.read_csv(REVIEW_ROOT / "A1_optimizer" / "optimizer_runs.csv")
    a1_lines = ["## Completed-result interpretation", ""]
    for name in ("COBYLA", "Nelder-Mead", "SLSQP"):
        item = optimizer[optimizer.optimizer == name].iloc[0]
        a1_lines.append(
            f"- {name}: certified-PASS graph mean O3−O0 G_feas={item.pass_subset_O3_minus_O0_G_mean:.4f}, "
            f"95% graph bootstrap CI [{item.pass_subset_O3_minus_O0_G_ci_lower:.4f}, "
            f"{item.pass_subset_O3_minus_O0_G_ci_upper:.4f}]."
        )
    reported = runs.dropna(subset=["scipy_reported_nfev"])
    mismatch = int(
        (reported.actual_nfev.astype(int) != reported.scipy_reported_nfev.astype(int)).sum()
    )
    slsqp_null = int(
        runs[(runs.optimizer == "SLSQP") & runs.scipy_reported_nfev.isna()].shape[0]
    )
    a1_lines.extend(
        [
            "",
            f"Where SciPy reported nfev, wrapper-versus-SciPy disagreements were {mismatch}/{len(reported)}. SLSQP has {slsqp_null} null SciPy nfev entries because the strict wrapper stopped at the call cap; its own counter still records every numerical finite-difference call.",
            "",
            "Nested failures occur for all three tested local optimizers, so the phenomenon is not COBYLA-specific. More importantly, the positive PASS-only graph intervals and the frequent lower-energy/lower-feasibility O0 comparisons show that objective misalignment persists after the certified optimizer-failure cases are removed. This supports treating optimizer inadequacy and objective misalignment as distinct tested mechanisms, without claiming either optimizer is universally unsuitable.",
            "",
            "**Claim impact:** supported across the tested local optimizers, with scope limited to the frozen tasks, seeds, depths, and 120-call budget.",
        ]
    )
    _append_synthesis(
        REVIEW_ROOT / "A1_optimizer" / "A1_OPTIMIZER_ROBUSTNESS.md",
        "\n".join(a1_lines),
    )

    a2_lines = ["## Completed-result interpretation", ""]
    for value in (0.02, 0.05, 0.25, 0.50, 1.00):
        item = _row(alpha, split="discovery", alpha=value, metric="G_feas")
        a2_lines.append(
            f"- alpha={value:g} versus 0.10: graph-mean ΔG_feas={item.graph_delta_mean:.4f}, "
            f"95% graph bootstrap CI [{item.graph_delta_ci_lower:.4f}, {item.graph_delta_ci_upper:.4f}]."
        )
    effects = pd.read_csv(REVIEW_ROOT / "A2_alpha" / "alpha_effect_summary.csv")
    a2_lines.append("")
    for value in (0.05, 0.25, 0.50):
        item = _row(effects, split="heldout", alpha=value)
        a2_lines.append(
            f"- Held-out POST_HOC_SENSITIVITY alpha={value:g} versus alpha=1: "
            f"graph-mean ΔG_feas={item.delta_G_vs_alpha1_mean:.4f}, "
            f"95% CI [{item.delta_G_vs_alpha1_ci_lower:.4f}, {item.delta_G_vs_alpha1_ci_upper:.4f}]."
        )
    a2_lines.extend(
        [
            "",
            "The discovery curve has a robust neighborhood around 0.10: 0.05 and 0.25 are close on equal-weight graph means, while 0.02 and 0.50 are weaker but remain above the alpha=1 endpoint. The optimized curve is strongly non-monotone (54/56 tasks), which was allowed by protocol. Alpha=1 recovers the mean-energy objective numerically but does not authorize replacing the historical frozen alpha=0.10 choice.",
            "",
            "**Claim impact:** supports that alpha=0.10 is not an isolated brittle choice; all held-out additions remain explicitly post-hoc.",
        ]
    )
    _append_synthesis(
        REVIEW_ROOT / "A2_alpha" / "A2_ALPHA_SENSITIVITY.md",
        "\n".join(a2_lines),
    )

    training = pd.read_csv(
        REVIEW_ROOT / "A3_finite_shot" / "finite_shot_training_effect_summary.csv"
    )
    a3_lines = ["## Completed-result interpretation", ""]
    for regime in ("EXACT_CANONICAL", "SHOT_10000", "SHOT_1000"):
        item = _row(training, regime=regime)
        a3_lines.append(
            f"- {regime}: {int(item.graph_positive_count)}/{int(item.n_graphs)} graph effects are positive; "
            f"mean={item.graph_effect_mean:.4f}, 95% CI [{item.graph_effect_ci_lower:.4f}, "
            f"{item.graph_effect_ci_upper:.4f}]."
        )
    a3_lines.extend(
        [
            "",
            "Both shot-trained point estimates retain the exact O3−O0 sign, and 10k shots has better graphwise sign consistency than 1k. However, both shot-trained graph-cluster intervals cross zero and both effects are attenuated relative to exact training. The appropriate result is therefore a threshold-like, mixed finding: ordering is mostly preserved at 10k, less stable at 1k, and neither regime supports a hardware-readiness claim.",
            "",
            "**Claim impact:** mixed for end-to-end finite-shot training; supported with qualification for fixed-endpoint estimation.",
        ]
    )
    _append_synthesis(
        REVIEW_ROOT / "A3_finite_shot" / "A3_FINITE_SHOT_TRAINING.md",
        "\n".join(a3_lines),
    )


def _claim_table() -> pd.DataFrame:
    rows = [
        ("optimizer failure is not COBYLA-specific", "SUPPORTED", "Nested failures occur under COBYLA, Nelder-Mead, and SLSQP."),
        ("objective misalignment is distinct from certified optimizer failure", "SUPPORTED", "PASS-only O3−O0 graph CIs are positive for all three optimizers."),
        ("CVaR alpha=0.10 is not a brittle isolated choice", "SUPPORTED", "Discovery alpha=0.05/0.10/0.25 form a similar high-feasibility neighborhood."),
        ("finite-shot estimator is stable at tested shot counts", "SUPPORTED_WITH_QUALIFICATION", "Endpoint ordering is usually retained at 1k and strongly retained at 10k/100k; this is fixed-theta evidence only."),
        ("finite-shot training preserves O3-vs-O0 ordering", "MIXED", "Mean signs remain positive, but 1k/10k graph-cluster intervals include zero."),
        ("depth degradation is optimization-budget dependent", "MIXED", "p4 is not worse than p3, and nested failure does not fall as budget grows."),
        ("p=4 provides additional evidence beyond p=2/p=3", "SUPPORTED", "p3→p4 has more nested failures while terminal state metrics generally improve, separating diagnostics."),
        ("current benchmark is classically easy by design", "SUPPORTED", "The exact label-setting solver matches 140/140 optima with sub-millisecond timings."),
    ]
    frame = pd.DataFrame(rows, columns=["claim", "status", "evidence"])
    atomic_write_csv(SUMMARY_ROOT / "claim_status.csv", frame)
    return frame


def _master_summary(
    depth: pd.DataFrame,
    alpha: pd.DataFrame,
    resources: pd.DataFrame,
    claims: pd.DataFrame,
    canonical: dict[str, Any],
) -> str:
    nested = pd.read_csv(REVIEW_ROOT / "B1_depth_budget" / "nested_diagnostics.csv")
    opt = pd.read_csv(REVIEW_ROOT / "A1_optimizer" / "optimizer_summary.csv")
    passed = pd.read_csv(REVIEW_ROOT / "A1_optimizer" / "optimizer_pass_subset.csv")
    alpha_runs = pd.read_csv(REVIEW_ROOT / "A2_alpha" / "alpha_runs.csv")
    alpha_graph = pd.read_csv(REVIEW_ROOT / "A2_alpha" / "alpha_summary_graph.csv")
    training = pd.read_csv(
        REVIEW_ROOT / "A3_finite_shot" / "finite_shot_training_effect_summary.csv"
    )
    estimator = pd.read_csv(REVIEW_ROOT / "A3_finite_shot" / "alpha_shot_estimator.csv")
    classical = pd.read_csv(REVIEW_ROOT / "B2_classical" / "classical_summary.csv")
    registry = pd.read_csv(REVIEW_ROOT / "run_registry.csv")
    total = _row(resources, experiment="FORMAL_TOTAL")
    test_path = REVIEW_ROOT / "provenance" / "final_test_results.json"
    tests = load_json(test_path) if test_path.exists() else {"status": "PENDING"}
    preexisting = (
        REVIEW_ROOT / "provenance" / "preexisting_git_status.txt"
    ).read_text(encoding="utf-8").splitlines()

    p4_120_o0 = _row(depth, contrast_type="DEPTH", objective="O0", budget=120, comparison="p4_minus_p3", metric="G_feas")
    p4_120_o3 = _row(depth, contrast_type="DEPTH", objective="O3", budget=120, comparison="p4_minus_p3", metric="G_feas")
    p4_budget_o0 = _row(depth, contrast_type="BUDGET", objective="O0", depth=4, comparison="nfev480_minus_nfev120", metric="G_feas")
    p4_budget_o3 = _row(depth, contrast_type="BUDGET", objective="O3", depth=4, comparison="nfev480_minus_nfev120", metric="G_feas")
    alpha_means = alpha_graph[alpha_graph.split == "discovery"].groupby("alpha").G_feas.mean()
    exact_error = float(alpha_runs[alpha_runs.alpha == 1.0].alpha1_minus_mean_endpoint_error.abs().max())
    classical_all = _row(classical, scope="ALL")
    formal_started = pd.to_datetime(registry.started_at, errors="coerce", utc=True)
    formal_finished = pd.to_datetime(registry.finished_at, errors="coerce", utc=True)
    formal_elapsed_hours = (
        formal_finished.max() - formal_started.min()
    ).total_seconds() / 3600.0

    lines = [
        "# Reviewer-robustness master summary",
        "",
        "## Repository integrity",
        "",
        f"- Starting tree: intentionally dirty with {len([line for line in preexisting if line.strip()])} pre-existing status entries, captured before this pass. They were preserved.",
        "- This pass added only the reviewer protocol, reviewer execution/analysis modules, one reviewer CLI, reviewer tests, and isolated reviewer results. No `overleaf/main.tex` or canonical result/manifests were edited by this pass.",
        f"- Canonical protection: **{'PASS' if canonical['pass'] else 'FAIL'}**, {canonical['observed_file_count']}/{canonical['expected_file_count']} protected files, aggregate SHA-256 `{canonical['observed_aggregate_sha256']}`.",
        f"- Final tests: {tests.get('summary', tests.get('status', 'PENDING'))}.",
        "- Pre-existing modifications and this pass are separated by the provenance snapshot and `THIS_PASS_MODIFICATIONS.md`.",
        "- Namespace decision: frozen reviewer manifests are under `results/reviewer_robustness/manifests/` and the protocol under `analysis/reviewer_robustness/`, rather than below the canonical `configs/` tree, because existing Phase-3 validation recursively interprets that tree as experiment configuration. This avoids contaminating frozen config enumeration; B1 and A3 also carry execution-local manifest copies.",
        "",
        "## R0 — clustering and frozen inference",
        "",
        "Discovery contains 56 tasks/10 base graphs; held-out contains 84/15; Phase 3 contains 180/30 with six tasks per graph. Existing Phase-2 H1/H2 inference already averages within graph, uses the 15 graphs as the sampling unit, performs whole-graph bootstrap/exact paired sign flips, and applies Holm correction to the frozen two-hypothesis family. **Existing confirmatory inference is already graph-level and does not require correction.** New task rows are descriptive; new uncertainty is based on paired equal-weight graph effects.",
        "",
        "## B1 — depth × budget",
        "",
        "B1 completed 432/432 trajectories and 1,296 genuine prefix checkpoint rows on 24 outcome-blind tasks/10 graphs, with no failed run. The 480-call single-trajectory design was licensed only after exact prefix equivalence against independently capped smoke runs.",
        f"At 120 calls, p4−p3 graph-mean G_feas is {p4_120_o0.graph_delta_mean:.4f} for O0 (CI [{p4_120_o0.graph_delta_ci_lower:.4f}, {p4_120_o0.graph_delta_ci_upper:.4f}]) and {p4_120_o3.graph_delta_mean:.4f} for O3 (CI [{p4_120_o3.graph_delta_ci_lower:.4f}, {p4_120_o3.graph_delta_ci_upper:.4f}]); all ten graph contrasts are positive in both arms. Thus p4 is not worse than p3 in this matrix.",
        f"From 120 to 480 calls, p4 graph-mean G_feas changes by {p4_budget_o0.graph_delta_mean:.4f} (O0) and {p4_budget_o3.graph_delta_mean:.4f} (O3): modest improvement, not a qualitative rescue.",
    ]
    for transition in ("p2->p3", "p3->p4"):
        rates = []
        for budget in (120, 240, 480):
            group = nested[(nested.transition == transition) & (nested.budget == budget)]
            rates.append(f"{budget}: {int(group.nested_failure.sum())}/{len(group)} ({group.nested_failure.mean():.3f})")
        lines.append(f"- {transition} nested failures — " + "; ".join(rates) + ".")
    lines.extend(
        [
            "Nested failure is higher for p3→p4 than p2→p3 and does not decrease with budget. This is not evidence of a barren plateau or intrinsic depth harm; it means the deeper terminal run sometimes fails to beat the simultaneously improving embedded shallower incumbent within the tested call budgets.",
            "",
            "## A1 — optimizer robustness and mechanism separation",
            "",
            "A1 completed all 2,016 runs (56 tasks × 3 optimizers × 2 objectives × 2 depths × 3 seeds), with 1,008 nested comparisons and no failures/timeouts.",
        ]
    )
    for optimizer in ("COBYLA", "Nelder-Mead", "SLSQP"):
        o0 = _row(opt, optimizer=optimizer, objective="O0")
        o3 = _row(opt, optimizer=optimizer, objective="O3")
        subset = passed[passed.optimizer == optimizer]
        lines.append(
            f"- {optimizer}: nested failures O0 {int(o0.nested_failure_count)}/168 and O3 {int(o3.nested_failure_count)}/168; "
            f"{len(subset)} paired runs pass both diagnostics; PASS-only graph mean O3−O0 G_feas={o0.pass_subset_O3_minus_O0_G_mean:.4f}, "
            f"CI [{o0.pass_subset_O3_minus_O0_G_ci_lower:.4f}, {o0.pass_subset_O3_minus_O0_G_ci_upper:.4f}]."
        )
    lines.extend(
        [
            "**Q1:** The frozen 29/168 observation is not mechanically redefined, but its mechanism is not COBYLA-only: both Nelder–Mead and SLSQP also show certified nested failures at the same call budget.",
            "**Q2:** Yes. Within dual-PASS pairs, O0 has lower energy but lower feasibility than O3 in 103/113 COBYLA, 65/72 Nelder–Mead, and 58/70 SLSQP comparisons. Optimizer inadequacy and objective misalignment remain empirically distinct within this scope.",
            "",
            "## A2 — CVaR alpha sensitivity",
            "",
            "A2 completed the full 1,008-run discovery grid plus 216 explicitly post-hoc held-out sensitivity runs; no run failed. Alpha=0.10 remains the only historical confirmatory choice.",
            f"Discovery equal-weight graph means for G_feas are: alpha=.02 {alpha_means[0.02]:.4f}, .05 {alpha_means[0.05]:.4f}, .10 {alpha_means[0.10]:.4f}, .25 {alpha_means[0.25]:.4f}, .50 {alpha_means[0.50]:.4f}, 1.00 {alpha_means[1.0]:.4f}.",
            "**Q3:** Alpha=0.10 lies in a reasonable robustness neighborhood: 0.05 and 0.25 are close, while 0.02 and 0.50 retain smaller advantages over alpha=1. The optimized response is non-monotone for 54/56 tasks, which was allowed rather than hidden.",
            f"**Q4:** Yes. Across all executed alpha=1 rows, max |CVaR−mean energy| is {exact_error:.3e}.",
            "",
            "## A3 — finite-shot estimation and training",
            "",
            "The pre-existing all-held-out endpoint study (84 tasks/15 graphs, O0/O3, 1k/10k/100k, 20 repeats) passed its hashes and was reused without rerunning. It establishes fixed-theta estimator convergence only: P_feas ordering recovery is 0.948/0.993/1.000 at 1k/10k/100k.",
            "The new alpha×shots grid adds 5,400 records (18 tasks/15 graphs, 50 repeats). At alpha=.10, pooled O0/O3 CVaR RMSE is 0.04839/0.01570/0.00486 and exact objective-order preservation is 0.901/0.967/0.992 at 1k/10k/100k. Alpha=.02 is costlier (RMSE 0.08217/0.02718/0.00813), supporting the expected sampling trade-off without assuming monotonic optimized performance.",
        ]
    )
    for regime in ("EXACT_CANONICAL", "SHOT_10000", "SHOT_1000"):
        item = _row(training, regime=regime)
        lines.append(
            f"- {regime}: graph mean O3−O0 G_feas={item.graph_effect_mean:.4f}, CI [{item.graph_effect_ci_lower:.4f}, {item.graph_effect_ci_upper:.4f}], positive graphs {int(item.graph_positive_count)}/{int(item.n_graphs)}."
        )
    lines.extend(
        [
            "**Q5:** Fixed-endpoint estimation is materially more stable by 10k shots and near-converged by 100k in this grid; 1k remains visibly noisy, especially for aggressive alpha=.02.",
            "**Q6:** Exact training gives a robust positive ordering. Both 10k and 1k shot-trained means retain the sign, but their graph CIs include zero; graphwise consistency is 8/10 at 10k and 6/10 at 1k. The correct conclusion is mostly preserved at 10k and unstable/attenuated at 1k, not hardware readiness.",
            "",
            "## B2 — classical context",
            "",
            f"The exact label-setting solver matches {int(classical_all.optimum_match_count)}/{int(classical_all.task_count)} frozen optima. Median solve time is {1e6*classical_all.median_solve_time_s:.1f} μs, p95 {1e6*classical_all.p95_solve_time_s:.1f} μs, maximum {1e6*classical_all.max_solve_time_s:.1f} μs; median/max generated labels are {classical_all.median_labels_generated:.0f}/{int(classical_all.max_labels_generated)}.",
            "**Q10:** These instances are classically trivial by design. They support controlled exact-statevector attribution, not a quantum-advantage or wall-clock comparison.",
            "",
            "## Direct answers to remaining depth questions",
            "",
            "- **Q7:** p4 is not worse than p3 on terminal loss, G_feas, P_feas, or P_opt in the aggregate matrix; extra budget gives modest p4 improvement, so no 'recovery from worse' is required.",
            "- **Q8:** Yes for the pooled diagnostic: p3→p4 failure rates exceed p2→p3 at every budget.",
            "- **Q9:** No. Failure rates do not decrease from 120 to 480; they are flat/slightly higher.",
            "",
            "## Paper-writable conclusion levels",
            "",
            "| Claim | Level |",
            "|---|---|",
        ]
    )
    for item in claims.itertuples(index=False):
        lines.append(f"| {item.claim} | **{item.status}** |")
    lines.extend(
        [
            "",
            "## What strengthens, what limits",
            "",
            "The optimizer and PASS-only analyses strengthen the two-mechanism attribution; the alpha scan strengthens the non-cherry-picking response; p4 removes the superficial concern that the paper stops at p3; and B2 makes the mechanistic/non-advantage framing explicit. Finite-shot training is the main limiting result: the positive point ordering is attenuated and graph-level uncertainty crosses zero. The budget ablation also weakens any simple story that more evaluations monotonically remove nested failures.",
            "",
            "## Main text versus appendix",
            "",
            "Main text should receive a compact optimizer/PASS-only result, one alpha-neighborhood sentence plus alpha=1 control, the qualified finite-shot-training result, the p4/budget nuance, and the classically-tractable context. Full matrices, per-optimizer accounting, all alpha curves, alpha×shots heatmap, classical counters, selection rules, and rebalancing provenance belong in the appendix/artifact. The frozen primary claims and numbers must not be replaced.",
            "",
            "## Scope boundary and B3",
            "",
            "This pass does not support hardware robustness, device/noise robustness, quantum advantage, claims about all constrained QAOA, or rankings of feasibility-preserving methods. B3 was **NOT TESTED**. It is not recommended for this revision unless a reviewer specifically requires a non-layered-network external-validity check; adding a new family now would broaden scope after all four core reviewer questions are already answered.",
            "",
            "## Resource and completion ledger",
            "",
            f"Formal records: {int(total.formal_records):,}; complete {int(total.complete):,}; failed {int(total.failed)}; timeout {int(total.timeout)}. Optimizer-objective statevector calls recorded by wrappers: {int(total.actual_objective_calls):,}. Sampled bitstrings in newly executed A3 studies: {int(total.sampled_bitstrings):,}. Sum of run-record wall durations (parallel-worker time, not elapsed wall clock): {total.recorded_worker_runtime_s/3600:.2f} h.",
            f"The formal execution wall-clock envelope was {formal_elapsed_hours:.2f} h, including inter-phase gaps and parallelism. CPU time was not instrumented and is not estimated.",
            "Post-run diagnostic/plot statevector evaluations are not centrally instrumented and are excluded rather than estimated. The reused pre-existing endpoint study is also excluded from this pass's compute totals.",
            "",
            "All planned core formal runs completed. The only failed event was the pre-formal alpha×shots smoke wiring check; it created no formal record, was preserved as evidence, fixed with a regression test, and passed deterministically on rerun. B3 is the only intentionally unexecuted optional phase.",
            "",
        ]
    )
    return "\n".join(lines)


def _revision_plan() -> str:
    return """# Paper revision plan (no manuscript files modified)

## Main text candidates

1. Add a compact reviewer-robustness paragraph stating that nested failures also occur under Nelder–Mead and SLSQP, while PASS-only O3−O0 graph intervals remain positive for all three tested optimizers. Preserve the frozen 29/168 observation as the historical diagnostic.
2. State that the full discovery alpha scan places 0.10 on a broad 0.05–0.25 plateau and that alpha=1 agrees numerically with mean energy. Label the scan post-hoc and do not replace the preregistered alpha.
3. Add the finite-shot threshold result: fixed-endpoint ordering is strong by 10k shots, but end-to-end 1k/10k training effects are attenuated and their graph-level intervals cross zero.
4. Add the p=4 nuance: p4 terminal metrics improve over p3, while p3→p4 nested failures are more frequent and do not fall with budget. Avoid intrinsic-depth or barren-plateau language.
5. Add one explicit classical-context sentence: exact label-setting matches 140/140 optima in sub-millisecond time; the benchmark is mechanistic, not an advantage benchmark.

## Appendix/artifact

- Table R1: optimizer rates, signed regret, G_feas, and PASS-only graph intervals.
- Figure R1 and `depth_budget_contrasts.csv`: full depth × budget matrix and nested transitions.
- Figure R2 and `alpha_neighborhood_effects.csv`: alpha scan, with held-out rows marked POST_HOC_SENSITIVITY.
- Figures R3/R4: shot-trained effects and alpha×shots estimator map.
- Table R2: exact classical timings and label counters.
- Include frozen selection algorithms, run registry, code-amendment chain, and scheduling-only rebalancing records.

## Wording to narrow

- Replace any unqualified “depth-three failure is optimizer-induced” wording with “a certified subset is optimizer-inadequate; objective misalignment remains after those failures are removed.”
- Do not say that more budget monotonically repairs deeper optimization.
- Do not call finite-shot results hardware/noise robustness.
- Do not compare simulator wall time with the exact solver as a hardware-performance claim.

## B3

Do not add B3 for this revision unless a reviewer explicitly requests external validity beyond the layered-DAG construction. If triggered later, freeze a separate family manifest before generation and keep it appendix-only.
"""


def _this_pass_modifications() -> str:
    return """# This robustness pass modifications

## Implementation

- `analysis/reviewer_robustness/protocol_v1.json`
- `paper_scripts/reviewer_robustness/run_reviewer_robustness.py`
- `src/qroute_dilution/reviewer_robustness/` (isolated reviewer package)
- `tests/test_reviewer_robustness.py`

## Generated isolated outputs

- `results/reviewer_robustness/R0/`
- `results/reviewer_robustness/B1_depth_budget/` (432 run JSON records)
- `results/reviewer_robustness/A1_optimizer/` (2,016 run JSON records)
- `results/reviewer_robustness/A2_alpha/` (1,224 run JSON records)
- `results/reviewer_robustness/A3_finite_shot/` (200 training + 5,400 estimator JSON records)
- `results/reviewer_robustness/B2_classical/` (140 run JSON records)
- `results/reviewer_robustness/manifests/`, `provenance/`, `summaries/`, `run_registry.csv`, and resume instructions.

No canonical science file, frozen result, task assignment, manuscript source, or pre-existing untracked file was modified by this pass.
"""


def generate_synthesis() -> dict[str, Any]:
    SUMMARY_ROOT.mkdir(parents=True, exist_ok=True)
    depth = build_depth_budget_contrasts()
    alpha = build_alpha_neighborhood_contrasts()
    resources = build_resource_summary()
    claims = _claim_table()
    canonical = verify_canonical_hash_snapshot(CANONICAL_HASHES_BEFORE)
    write_json(REVIEW_ROOT / "provenance" / "final_canonical_integrity.json", canonical)
    _phase_addenda(depth, alpha)
    master = _master_summary(depth, alpha, resources, claims, canonical)
    atomic_write_text(REVIEW_ROOT / "REVIEWER_ROBUSTNESS_MASTER_SUMMARY.md", master)
    atomic_write_text(SUMMARY_ROOT / "REVIEWER_ROBUSTNESS_MASTER_SUMMARY.md", master)
    atomic_write_text(REVIEW_ROOT / "PAPER_REVISION_PLAN.md", _revision_plan())
    atomic_write_text(SUMMARY_ROOT / "PAPER_REVISION_PLAN.md", _revision_plan())
    atomic_write_text(REVIEW_ROOT / "THIS_PASS_MODIFICATIONS.md", _this_pass_modifications())
    b3 = """# B3 — external-validity mini benchmark

**Status: NOT TESTED.** B3 is optional and was not started. All required core phases completed, but a new graph family would broaden the revision after optimizer attribution, alpha sensitivity, finite-shot training, depth × budget, and exact classical context were already resolved. Execute B3 only if a reviewer specifically requires a non-layered-network check; freeze a new manifest before generating any task.
"""
    atomic_write_text(REVIEW_ROOT / "B3_EXTERNAL_VALIDITY.md", b3)
    atomic_write_text(SUMMARY_ROOT / "B3_EXTERNAL_VALIDITY.md", b3)

    phase_sources = {
        "A0_STATISTICAL_AUDIT.md": REVIEW_ROOT / "R0" / "R0_AUDIT.md",
        "A1_OPTIMIZER_ROBUSTNESS.md": REVIEW_ROOT / "A1_optimizer" / "A1_OPTIMIZER_ROBUSTNESS.md",
        "A2_ALPHA_SENSITIVITY.md": REVIEW_ROOT / "A2_alpha" / "A2_ALPHA_SENSITIVITY.md",
        "A3_FINITE_SHOT.md": REVIEW_ROOT / "A3_finite_shot" / "A3_FINITE_SHOT_TRAINING.md",
        "B1_DEPTH_BUDGET.md": REVIEW_ROOT / "B1_depth_budget" / "B1_DEPTH_BUDGET.md",
        "B2_CLASSICAL_BASELINE.md": REVIEW_ROOT / "B2_classical" / "B2_CLASSICAL_CONTEXT.md",
    }
    for name, source in phase_sources.items():
        atomic_write_text(SUMMARY_ROOT / name, source.read_text(encoding="utf-8"))

    optimizer = pd.read_csv(REVIEW_ROOT / "A1_optimizer" / "optimizer_summary.csv")
    atomic_write_csv(SUMMARY_ROOT / "Table_R1_optimizer_robustness.csv", optimizer)
    classical = pd.read_csv(REVIEW_ROOT / "B2_classical" / "classical_summary.csv")
    atomic_write_csv(SUMMARY_ROOT / "Table_R2_classical_context.csv", classical)
    return {
        "canonical_integrity_pass": bool(canonical["pass"]),
        "depth_contrast_rows": len(depth),
        "alpha_neighborhood_rows": len(alpha),
        "formal_records": int(_row(resources, experiment="FORMAL_TOTAL").formal_records),
        "claim_rows": len(claims),
    }
