#!/usr/bin/env python3
"""Audit the manuscript against frozen evidence and its self-contained package.

This is a read-only integrity recomputation over canonical rows plus static
LaTeX checks.  It neither runs an optimizer nor changes historical evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OVERLEAF = ROOT / "overleaf"
AUDIT = ROOT / "paper_audit"


def load_json(relative: str) -> dict:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def numeric_audit() -> list[dict]:
    """Record every scientific/protocol number used in main-text prose.

    Repeated use in separate high-visibility sections is recorded separately.
    Pure equation coefficients (for example the factor two in a square) are
    mathematical definitions and are not empirical numeric claims.
    """

    p0 = load_json("results/phase0/summary.json")
    p0v2 = load_json("results/phase0_v2_dilution_stress/summary.json")
    pilot = load_json("results/phase1_pilot_v1/pilot_summary.json")
    opt = load_json("results/phase1_1_optimization_diagnostic/summary.json")
    obj = load_json("results/phase1_2_objective_alignment/summary.json")
    held = load_json("results/phase2_confirmatory_v1/summary.json")
    conf = load_json("results/phase2_confirmatory_v1/confirmatory_statistics.json")
    scaling = load_json("results/phase3_scaling_v1/summary.json")

    rows: list[dict] = []

    def add(section: str, manuscript_value: str | int | float,
            canonical_value: str | int | float, source: str,
            field: str, note: str = "") -> None:
        sid = f"NV{len(rows) + 1:03d}"
        difference = ""
        try:
            mv = float(str(manuscript_value).replace(",", ""))
            cv = float(canonical_value)
            difference = f"{abs(mv - cv):.12g}"
            shown = str(manuscript_value).replace(",", "").lower()
            if "e" in shown:
                mantissa, exponent = shown.split("e", 1)
                decimals = len(mantissa.split(".", 1)[1]) if "." in mantissa else 0
                display_tolerance = 0.500001 * 10 ** (int(exponent) - decimals)
            elif "." in shown:
                decimals = len(shown.split(".", 1)[1])
                display_tolerance = 0.500001 * 10 ** (-decimals)
            else:
                display_tolerance = 5e-13
            tolerance = max(5e-13, display_tolerance)
            status = "SUPPORTED_EXACT" if abs(mv - cv) <= 5e-13 else (
                "SUPPORTED_ROUNDED" if abs(mv - cv) <= tolerance else "MISMATCH"
            )
        except (TypeError, ValueError):
            status = "SUPPORTED_EXACT" if str(manuscript_value) == str(canonical_value) else "MISMATCH"
        rows.append(
            {
                "statement_id": sid,
                "section": section,
                "manuscript_value": manuscript_value,
                "canonical_value": canonical_value,
                "source": f"{source} :: {field}",
                "difference": difference,
                "status": status,
                "notes": note,
            }
        )

    s0 = "results/phase0/summary.json"
    s0v2 = "results/phase0_v2_dilution_stress/summary.json"
    sp = "results/phase1_pilot_v1/pilot_summary.json"
    so = "results/phase1_1_optimization_diagnostic/summary.json"
    sj = "results/phase1_2_objective_alignment/summary.json"
    sh = "results/phase2_confirmatory_v1/summary.json"
    sc = "results/phase2_confirmatory_v1/confirmatory_statistics.json"
    ss = "results/phase3_scaling_v1/summary.json"

    # Abstract: every empirical quantity appearing there.
    for value, canonical, field in [
        (0.10, 0.10, "frozen CVaR alpha"),
        (84, held["heldout_task_count"], "heldout_task_count"),
        (15, held["heldout_base_graph_count"], "heldout_base_graph_count"),
        (20, scaling["task_universe"]["completed_size_ceiling"], "task_universe.completed_size_ceiling"),
        (22, scaling["resource_preflight"]["resource_censored_sizes"][0], "resource_preflight.resource_censored_sizes[0]"),
    ]:
        add("Abstract", value, canonical, sh if field.startswith("heldout") else ss if value in (20, 22) else "configs/phase2_confirmatory_v1.yaml", field)

    # Introduction repeats headline construction, attribution, held-out, and scaling values.
    intro = [
        (53, p0["duplicate_feasible_set_count"], s0, "duplicate_feasible_set_count"),
        (175, p0["task_count"], s0, "task_count"),
        (140, p0v2["task_count"], s0v2, "task_count"),
        (1.90735e-6, p0v2["feasible_state_fraction_min"], s0v2, "feasible_state_fraction_min"),
        (2.34375e-2, p0v2["feasible_state_fraction_max"], s0v2, "feasible_state_fraction_max"),
        (168, opt["validation"]["nested_identity_rows"], so, "validation.nested_identity_rows"),
        (29, opt["original_p3_optimizer_adequacy"]["worse_than_embedded_count"], so, "original_p3_optimizer_adequacy.worse_than_embedded_count"),
        (27, opt["original_p3_optimizer_adequacy"]["failed_original_runs_with_higher_G_under_continuation"], so, "original_p3_optimizer_adequacy.failed_original_runs_with_higher_G_under_continuation"),
        (82, opt["continuation"]["random_lower_objective_but_lower_G_count"], so, "continuation.random_lower_objective_but_lower_G_count"),
        (0.10, 0.10, "configs/phase2_confirmatory_v1.yaml", "frozen CVaR alpha"),
        (97.9, 97.9, sj, "median stable gap closure, percent"),
        (84, held["heldout_task_count"], sh, "heldout_task_count"),
        (15, held["heldout_base_graph_count"], sh, "heldout_base_graph_count"),
        (0.354714949, conf["H1"]["effect_mean"], sc, "H1.effect_mean"),
        (0.2374, conf["H1"]["one_sided_95_lower_bound"], sc, "H1.one_sided_95_lower_bound"),
        (0.000244, conf["H1"]["holm_adjusted_p_value"], sc, "H1.holm_adjusted_p_value"),
        (-0.0086, conf["H2"]["effect_mean"], sc, "H2.effect_mean"),
        (-0.0360, conf["H2"]["one_sided_95_lower_bound"], sc, "H2.one_sided_95_lower_bound"),
        (-0.10, conf["H2"]["null_margin"], sc, "H2.null_margin"),
        (80, held["routing_quality"]["O3_vs_O0_P_opt_wins"], sh, "routing_quality.O3_vs_O0_P_opt_wins"),
        (79, held["routing_quality"]["O3_vs_O0_both_Pfeas_Popt_greater"], sh, "routing_quality.O3_vs_O0_both_Pfeas_Popt_greater"),
        (84, held["cvar_tail_mechanism"]["tail_condition_pass_count"], sh, "cvar_tail_mechanism.tail_condition_pass_count"),
        (20, scaling["task_universe"]["completed_size_ceiling"], ss, "task_universe.completed_size_ceiling"),
        (1.2821, scaling["exponent_summaries"]["extrapolation_holdout"]["O3"]["mean"], ss, "exponent_summaries.extrapolation_holdout.O3.mean"),
        (0.6150, scaling["exponent_summaries"]["extrapolation_holdout"]["O0"]["mean"], ss, "exponent_summaries.extrapolation_holdout.O0.mean"),
        (22, scaling["resource_preflight"]["resource_censored_sizes"][0], ss, "resource_preflight.resource_censored_sizes[0]"),
    ]
    for value, canonical, source, field in intro:
        add("Introduction", value, canonical, source, field)

    # Controlled methods: construction and scale contract.
    methods = [
        (53, p0["duplicate_feasible_set_count"], s0, "duplicate_feasible_set_count"),
        (175, p0["task_count"], s0, "task_count"),
        (30.29, 100 * p0["duplicate_feasible_set_count"] / p0["task_count"], s0, "duplicate_feasible_set_count/task_count"),
        (35, p0v2["v1_duplicate_cause_counts"]["repeated_quantile_indices_due_to_too_few_routes"], s0v2, "v1_duplicate_cause_counts.repeated_quantile_indices_due_to_too_few_routes"),
        (18, p0v2["v1_duplicate_cause_counts"]["integer_resource_ties_at_distinct_indices"], s0v2, "v1_duplicate_cause_counts.integer_resource_ties_at_distinct_indices"),
        (140, p0v2["task_count"], s0v2, "task_count"),
        (0, p0v2["duplicate_feasible_set_count"], s0v2, "duplicate_feasible_set_count"),
        (1.9073486328125e-6, p0v2["feasible_state_fraction_min"], s0v2, "feasible_state_fraction_min"),
        (0.0234375, p0v2["feasible_state_fraction_max"], s0v2, "feasible_state_fraction_max"),
        (1.6300887149, p0v2["dilution_score_min"], s0v2, "dilution_score_min"),
        (5.7195699176, p0v2["dilution_score_max"], s0v2, "dilution_score_max"),
        ("3.42698e7", 34269838, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "current span minimum"),
        ("1.82405e9", 1.8240518e9, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "current span maximum"),
        ("4.65752e8", 4.6575239e8, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "current span median"),
        (11683.8, 11683.8, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "V2/v1 median span factor"),
        (1.7253, 1.72526, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "within-base current median span variation"),
        (140, 140, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "controlled exact ground states"),
        (490.51, 490.51, "results/phase0_v2_dilution_stress/penalty_contract_comparison.csv", "controlled span minimum"),
        (744.17, 744.17, "results/phase0_v2_dilution_stress/penalty_contract_comparison.csv", "controlled span maximum"),
        (1.07495, 1.07495, "results/phase0_v2_dilution_stress/HAMILTONIAN_SCALE_AUDIT.md", "controlled within-base median variation"),
        (56, pilot["frozen_execution_identity"]["task_count"], sp, "frozen_execution_identity.task_count"),
        (504, pilot["frozen_execution_identity"]["completed_optimized_row_count"], sp, "frozen_execution_identity.completed_optimized_row_count"),
        (84, held["heldout_task_count"], sh, "heldout_task_count"),
        (15, held["heldout_base_graph_count"], sh, "heldout_base_graph_count"),
        (180, scaling["execution"]["resource_censored_rows"], ss, "execution.resource_censored_rows"),
    ]
    for value, canonical, source, field in methods:
        add("Controlled Experimental Design", value, canonical, source, field)

    # Optimizer attribution result prose.
    pilot_ranges = {item["depth"]: item for item in pilot["main_numerical_ranges"]}
    pilot_kappa = {item["depth"]: item for item in pilot["dilution_response"]}
    optimizer = [
        (56, pilot["frozen_execution_identity"]["task_count"], sp, "frozen_execution_identity.task_count"),
        (504, pilot["frozen_execution_identity"]["completed_optimized_row_count"], sp, "frozen_execution_identity.completed_optimized_row_count"),
        (5.09e-3, pilot_ranges[1]["p_feas_median"], sp, "main_numerical_ranges[p=1].p_feas_median"),
        (5.98e-3, pilot_ranges[2]["p_feas_median"], sp, "main_numerical_ranges[p=2].p_feas_median"),
        (3.19e-3, pilot_ranges[3]["p_feas_median"], sp, "main_numerical_ranges[p=3].p_feas_median"),
        (0.542, pilot_kappa[1]["kappa_median"], sp, "dilution_response[p=1].kappa_median"),
        (0.412, pilot_kappa[2]["kappa_median"], sp, "dilution_response[p=2].kappa_median"),
        (-0.540, pilot_kappa[3]["kappa_median"], sp, "dilution_response[p=3].kappa_median"),
        (-0.2572, pilot["depth_effect"]["Delta_G_3_2"], sp, "depth_effect.Delta_G_3_2"),
        (29, opt["original_p3_optimizer_adequacy"]["worse_than_embedded_count"], so, "original_p3_optimizer_adequacy.worse_than_embedded_count"),
        (168, opt["original_p3_optimizer_adequacy"]["denominator"], so, "original_p3_optimizer_adequacy.denominator"),
        (17.3, 100 * opt["original_p3_optimizer_adequacy"]["fraction"], so, "original_p3_optimizer_adequacy.fraction, percent"),
        (168, opt["validation"]["nested_identity_rows"], so, "validation.nested_identity_rows"),
        (29, opt["original_p3_optimizer_adequacy"]["failed_original_runs_recovered_to_lower_objective_by_continuation"], so, "original_p3_optimizer_adequacy.failed_original_runs_recovered_to_lower_objective_by_continuation"),
        (27, opt["original_p3_optimizer_adequacy"]["failed_original_runs_with_higher_G_under_continuation"], so, "original_p3_optimizer_adequacy.failed_original_runs_with_higher_G_under_continuation"),
        (0.1530, opt["continuation"]["median_delta_G_from_embedded_start"], so, "continuation.median_delta_G_from_embedded_start"),
        (-0.5400, opt["compensation"]["original_p3"]["kappa_median"], so, "compensation.original_p3.kappa_median"),
        (0.3672, opt["compensation"]["continuation_p3"]["kappa_median"], so, "compensation.continuation_p3.kappa_median"),
        (0.1780, opt["depth_effects"][1]["median_Delta_G_3_2"], so, "depth_effects.P3_CONTINUATION_B1.median_Delta_G_3_2"),
        (17, opt["continuation"]["classification_counts"]["OBJECTIVE_IMPROVES_FEASIBILITY_WORSENS"], so, "continuation.classification_counts.OBJECTIVE_IMPROVES_FEASIBILITY_WORSENS"),
        (108, opt["continuation"]["random_lower_objective_than_continuation_count"], so, "continuation.random_lower_objective_than_continuation_count"),
        (82, opt["continuation"]["random_lower_objective_but_lower_G_count"], so, "continuation.random_lower_objective_but_lower_G_count"),
        (-0.0973, opt["paired_decomposition_median_random_minus_continuation"]["objective"], so, "paired_decomposition_median_random_minus_continuation.objective"),
        (-0.0223, opt["paired_decomposition_median_random_minus_continuation"]["expected_routing_component"], so, "paired_decomposition_median_random_minus_continuation.expected_routing_component"),
        (0.0027, opt["paired_decomposition_median_random_minus_continuation"]["expected_flow_penalty"], so, "paired_decomposition_median_random_minus_continuation.expected_flow_penalty"),
        (-0.0573, opt["paired_decomposition_median_random_minus_continuation"]["expected_resource_penalty"], so, "paired_decomposition_median_random_minus_continuation.expected_resource_penalty"),
        (0.00498, abs(opt["paired_decomposition_median_random_minus_continuation"]["mass_valid_flow_resource_feasible"]), so, "paired_decomposition_median_random_minus_continuation.mass_valid_flow_resource_feasible, magnitude"),
        (0.00847, opt["paired_decomposition_median_random_minus_continuation"]["mass_flow_invalid"], so, "paired_decomposition_median_random_minus_continuation.mass_flow_invalid"),
        (0.05425, abs(opt["paired_decomposition_median_random_minus_continuation"]["mass_resource_violating"]), so, "paired_decomposition_median_random_minus_continuation.mass_resource_violating, magnitude"),
    ]
    for value, canonical, source, field in optimizer:
        add("Optimizer and Objective Attribution", value, canonical, source, field)

    # Objective discovery.
    objective = [
        (240, obj["matched_eval_budget"], sj, "matched_eval_budget"),
        (56, obj["task_count"], sj, "task_count"),
        (0.02168, obj["objectives"]["O0"]["median_p_feas"], sj, "objectives.O0.median_p_feas"),
        (2.1161, obj["objectives"]["O0"]["median_G_feas"], sj, "objectives.O0.median_G_feas"),
        (140, obj["theoretical_audit"]["basis_penalty_contract_pass_count"], sj, "theoretical_audit.basis_penalty_contract_pass_count"),
        (224, obj["theoretical_audit"]["optimization_state_penalty_bound_pass_count"], sj, "theoretical_audit.optimization_state_penalty_bound_pass_count"),
        (56, obj["penalty_surrogate_diagnostic"]["O1_own_objective_improved_count"], sj, "penalty_surrogate_diagnostic.O1_own_objective_improved_count"),
        (51, obj["penalty_surrogate_diagnostic"]["O1_lower_penalty_but_lower_P_feas_than_O2_count"], sj, "penalty_surrogate_diagnostic.O1_lower_penalty_but_lower_P_feas_than_O2_count"),
        (2.8, 2.8, sj, "median O1 capacity-gap closure, percent"),
        (2, obj["mechanistic_tags"]["PENALTY_SURROGATE_SUCCESS"], sj, "mechanistic_tags.PENALTY_SURROGATE_SUCCESS"),
        (53, obj["paired_comparisons_vs_O0"]["O2"]["P_feas_improved"], sj, "paired_comparisons_vs_O0.O2.P_feas_improved"),
        (0.2192983546, obj["capacity_gaps"]["median_O2_minus_O0_G"], sj, "capacity_gaps.median_O2_minus_O0_G"),
        (0.01522, obj["capacity_gaps"]["median_O2_minus_O0_P_feas"], sj, "capacity_gaps.median_O2_minus_O0_P_feas"),
        (0.662, obj["capacity_gaps"]["capacity_gap_vs_dilution"]["capacity_gap_mean"]["spearman_D_vs_gap"], sj, "capacity_gaps.capacity_gap_vs_dilution.capacity_gap_mean.spearman_D_vs_gap"),
        (56, obj["theoretical_audit"]["cvar_tail_condition_pass_count"], sj, "theoretical_audit.cvar_tail_condition_pass_count"),
        (14, 14, "results/phase1_2_objective_alignment/cvar_tail_diagnostics.csv", "fully feasible discovery tails"),
        (50, obj["paired_comparisons_vs_O0"]["O3"]["P_feas_improved"], sj, "paired_comparisons_vs_O0.O3.P_feas_improved"),
        (51, obj["paired_comparisons_vs_O0"]["O3"]["P_opt_improved"], sj, "paired_comparisons_vs_O0.O3.P_opt_improved"),
        (0.00690, obj["capacity_gaps"]["median_O2_minus_O3_G"], sj, "capacity_gaps.median_O2_minus_O3_G"),
        (0.21930, obj["capacity_gaps"]["median_O2_minus_O0_G"], sj, "capacity_gaps.median_O2_minus_O0_G"),
        (97.9, 97.9, sj, "median stable gap closure, percent"),
        (27, obj["paired_comparisons_vs_O0"]["O3"]["P_opt_given_feasible_improved"], sj, "paired_comparisons_vs_O0.O3.P_opt_given_feasible_improved"),
        (10, obj["paired_comparisons_vs_O0"]["O3"]["P_opt_given_feasible_unchanged"], sj, "paired_comparisons_vs_O0.O3.P_opt_given_feasible_unchanged"),
        (19, obj["paired_comparisons_vs_O0"]["O3"]["P_opt_given_feasible_worsened"], sj, "paired_comparisons_vs_O0.O3.P_opt_given_feasible_worsened"),
        (0.10, 0.10, "configs/phase1_2_objective_alignment.yaml", "frozen CVaR alpha"),
    ]
    for value, canonical, source, field in objective:
        add("Objective-Alignment Study", value, canonical, source, field)

    # Held-out primary and secondary results.
    heldout = [
        (84, held["heldout_task_count"], sh, "heldout_task_count"),
        (15, held["heldout_base_graph_count"], sh, "heldout_base_graph_count"),
        (0, held["phase2_task_overlap_with_discovery"], sh, "phase2_task_overlap_with_discovery"),
        (0, held["phase2_base_graph_overlap_with_discovery"], sh, "phase2_base_graph_overlap_with_discovery"),
        (-0.10, conf["H2"]["null_margin"], sc, "H2.null_margin"),
        (10000, 10000, "protocols/PHASE2_PREREGISTRATION.md", "grouped bootstrap resamples"),
        (32768, 2 ** conf["n_base_graphs"], sc, "all graph sign configurations"),
        (0.05, 0.05, "protocols/PHASE2_PREREGISTRATION.md", "family alpha"),
        (0.3547149490180106, conf["H1"]["effect_mean"], sc, "H1.effect_mean"),
        (0.0747258211, conf["H1"]["bootstrap_standard_error"], sc, "H1.bootstrap_standard_error"),
        (0.2373785365, conf["H1"]["one_sided_95_lower_bound"], sc, "H1.one_sided_95_lower_bound"),
        (0.0001220703, conf["H1"]["raw_p_value"], sc, "H1.raw_p_value"),
        (0.000244140625, conf["H1"]["holm_adjusted_p_value"], sc, "H1.holm_adjusted_p_value"),
        (-0.008595149938274194, conf["H2"]["effect_mean"], sc, "H2.effect_mean"),
        (0.0166760478, conf["H2"]["bootstrap_standard_error"], sc, "H2.bootstrap_standard_error"),
        (-0.0360487499, conf["H2"]["one_sided_95_lower_bound"], sc, "H2.one_sided_95_lower_bound"),
        (0.0001525879, conf["H2"]["raw_p_value"], sc, "H2.raw_p_value"),
        (0.000244140625, conf["H2"]["holm_adjusted_p_value"], sc, "H2.holm_adjusted_p_value"),
        (80, held["routing_quality"]["O3_vs_O0_P_opt_wins"], sh, "routing_quality.O3_vs_O0_P_opt_wins"),
        (4, held["routing_quality"]["O3_vs_O0_P_opt_losses"], sh, "routing_quality.O3_vs_O0_P_opt_losses"),
        (0.00639968, held["routing_quality"]["paired_median_P_opt_difference"], sh, "routing_quality.paired_median_P_opt_difference"),
        (79, held["routing_quality"]["O3_vs_O0_both_Pfeas_Popt_greater"], sh, "routing_quality.O3_vs_O0_both_Pfeas_Popt_greater"),
        (0.3605, held["routing_quality"]["median_P_opt_given_feasible_O0"], sh, "routing_quality.median_P_opt_given_feasible_O0"),
        (0.4077, held["routing_quality"]["median_P_opt_given_feasible_O3"], sh, "routing_quality.median_P_opt_given_feasible_O3"),
        (14.9322, held["routing_quality"]["median_conditional_route_cost_O0"], sh, "routing_quality.median_conditional_route_cost_O0"),
        (14.8318, held["routing_quality"]["median_conditional_route_cost_O3"], sh, "routing_quality.median_conditional_route_cost_O3"),
        (32, held["routing_quality"]["O3_feasibility_up_conditional_quality_down"], sh, "routing_quality.O3_feasibility_up_conditional_quality_down"),
        (84, held["cvar_tail_mechanism"]["tail_condition_pass_count"], sh, "cvar_tail_mechanism.tail_condition_pass_count"),
        (20, held["cvar_tail_mechanism"]["fully_feasible_tail_count"], sh, "cvar_tail_mechanism.fully_feasible_tail_count"),
        (64, held["heldout_task_count"] - held["cvar_tail_mechanism"]["fully_feasible_tail_count"], sh, "heldout_task_count - fully_feasible_tail_count"),
        (0.0561, held["cvar_tail_mechanism"]["median_O3_minus_O0_G_fully_feasible_tail"], sh, "cvar_tail_mechanism.median_O3_minus_O0_G_fully_feasible_tail"),
        (0.3865, held["cvar_tail_mechanism"]["median_O3_minus_O0_G_partial_tail"], sh, "cvar_tail_mechanism.median_O3_minus_O0_G_partial_tail"),
    ]
    for value, canonical, source, field in heldout:
        add("Preregistered Held-Out Confirmation", value, canonical, source, field)

    # Scaling response; these are deliberately not audited as a global law.
    exp = scaling["exponent_summaries"]
    scale_rows = [
        (180, scaling["task_universe"]["tasks"], ss, "task_universe.tasks"),
        (16, exp["development"]["O0"]["n"], ss, "exponent_summaries.development.O0.n"),
        (1.0005, exp["development"]["O0"]["mean"], ss, "exponent_summaries.development.O0.mean"),
        (0.6467, exp["development"]["O2"]["mean"], ss, "exponent_summaries.development.O2.mean"),
        (0.6309, exp["development"]["O3"]["mean"], ss, "exponent_summaries.development.O3.mean"),
        (-0.6152, exp["development"]["O0"]["min"], ss, "exponent_summaries.development.O0.min"),
        (3.3117, exp["development"]["O0"]["max"], ss, "exponent_summaries.development.O0.max"),
        (4, exp["interpolation_holdout"]["O0"]["n"], ss, "exponent_summaries.interpolation_holdout.O0.n"),
        (0.9998, exp["interpolation_holdout"]["O0"]["mean"], ss, "exponent_summaries.interpolation_holdout.O0.mean"),
        (0.4127, exp["interpolation_holdout"]["O2"]["mean"], ss, "exponent_summaries.interpolation_holdout.O2.mean"),
        (0.3489, exp["interpolation_holdout"]["O3"]["mean"], ss, "exponent_summaries.interpolation_holdout.O3.mean"),
        (5, exp["extrapolation_holdout"]["O0"]["n"], ss, "exponent_summaries.extrapolation_holdout.O0.n"),
        (0.6150, exp["extrapolation_holdout"]["O0"]["mean"], ss, "exponent_summaries.extrapolation_holdout.O0.mean"),
        (0.7885, exp["extrapolation_holdout"]["O2"]["mean"], ss, "exponent_summaries.extrapolation_holdout.O2.mean"),
        (1.2821, exp["extrapolation_holdout"]["O3"]["mean"], ss, "exponent_summaries.extrapolation_holdout.O3.mean"),
        (0.6539, exp["extrapolation_holdout"]["O3"]["min"], ss, "exponent_summaries.extrapolation_holdout.O3.min"),
        (2.7952, exp["extrapolation_holdout"]["O3"]["max"], ss, "exponent_summaries.extrapolation_holdout.O3.max"),
        (20, scaling["task_universe"]["completed_size_ceiling"], ss, "task_universe.completed_size_ceiling"),
        (22, scaling["resource_preflight"]["resource_censored_sizes"][0], ss, "resource_preflight.resource_censored_sizes[0]"),
        (520, 520, "results/phase3_scaling_v1/resource_preflight.csv", "m22 estimated_peak_memory_mb"),
        (2249.3, 2249.3, "results/phase3_scaling_v1/resource_preflight.csv", "m22 projected_seconds"),
        (1200, 1200, "configs/phase3_scaling_v1.yaml", "resource guard seconds"),
        (180, scaling["execution"]["resource_censored_rows"], ss, "execution.resource_censored_rows"),
        (75, 75, "results/phase3_scaling_v1/optimality_scaling.csv", "completed graph-objective trajectories"),
        (0.696, 0.696, "results/phase3_scaling_v1/optimality_scaling.csv", "minimum reported median endpoint conditional increase"),
        (0.832, 0.832, "results/phase3_scaling_v1/optimality_scaling.csv", "maximum reported median endpoint conditional increase"),
    ]
    for value, canonical, source, field in scale_rows:
        add("Scaling Response and Resource Ceiling", value, canonical, source, field,
            "SCALING_RESPONSE_RESOURCE_CENSORED")

    # Discussion and conclusion repeat only a small subset of audited results.
    discussion = [
        (32, held["routing_quality"]["O3_feasibility_up_conditional_quality_down"], sh, "routing_quality.O3_feasibility_up_conditional_quality_down"),
        (0.10, 0.10, "configs/phase2_confirmatory_v1.yaml", "frozen CVaR alpha"),
        (82, opt["continuation"]["random_lower_objective_but_lower_G_count"], so, "continuation.random_lower_objective_but_lower_G_count"),
        (20, scaling["task_universe"]["completed_size_ceiling"], ss, "task_universe.completed_size_ceiling"),
        (22, scaling["resource_preflight"]["resource_censored_sizes"][0], ss, "resource_preflight.resource_censored_sizes[0]"),
    ]
    for value, canonical, source, field in discussion:
        add("Discussion", value, canonical, source, field)
    conclusion = [
        (0.10, 0.10, "configs/phase2_confirmatory_v1.yaml", "frozen CVaR alpha"),
        (84, held["heldout_task_count"], sh, "heldout_task_count"),
        (15, held["heldout_base_graph_count"], sh, "heldout_base_graph_count"),
        (20, scaling["task_universe"]["completed_size_ceiling"], ss, "task_universe.completed_size_ceiling"),
        (22, scaling["resource_preflight"]["resource_censored_sizes"][0], ss, "resource_preflight.resource_censored_sizes[0]"),
    ]
    for value, canonical, source, field in conclusion:
        add("Conclusion", value, canonical, source, field)

    return rows


def claim_audit() -> list[dict]:
    matrix_path = ROOT / "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv"
    with matrix_path.open(newline="", encoding="utf-8") as handle:
        matrix = {row["claim_id"]: row for row in csv.DictReader(handle)}

    rows: list[dict] = []
    tex_files = [OVERLEAF / "main.tex", *sorted((OVERLEAF / "sections").glob("*.tex")),
                 *sorted((OVERLEAF / "appendices").glob("*.tex"))]
    marker = re.compile(r"^\s*%\s*CLAIM:\s*(.+?)\s*$")
    for tex in tex_files:
        active: list[str] = []
        paragraph: list[str] = []
        paragraph_number = 0

        def flush() -> None:
            nonlocal paragraph, paragraph_number
            wording = " ".join(line.strip() for line in paragraph if line.strip())
            paragraph = []
            if not wording or not active:
                return
            paragraph_number += 1
            clean = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", "", wording)
            clean = re.sub(r"[{}$]", "", clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            for claim_id in active:
                source = matrix.get(claim_id, {})
                rows.append(
                    {
                        "claim_id": claim_id,
                        "section": tex.relative_to(OVERLEAF).as_posix(),
                        "paragraph": paragraph_number,
                        "wording": clean[:800],
                        "source": source.get("source_files", ""),
                        "status": source.get("status", "UNSUPPORTED") if source else "UNSUPPORTED",
                        "scope": source.get("scope", ""),
                    }
                )

        for line in tex.read_text(encoding="utf-8").splitlines():
            found = marker.match(line)
            if found:
                flush()
                active = [item.strip() for item in found.group(1).split(",")]
                continue
            if not line.strip():
                flush()
                active = []
            elif not line.lstrip().startswith("%"):
                paragraph.append(line)
        flush()

    # Explicitly record prohibited candidate claims as rejected and absent.
    rejected = [
        ("R-NO-ADVANTAGE", "Quantum advantage is demonstrated."),
        ("R-NO-UNIVERSAL-RCSP", "Every explicit RCSP instance requires a raw-density query lower bound."),
        ("R-NO-GLOBAL-SCALING", "A global dilution scaling law was confirmed."),
        ("R-NO-CVAR-NOVELTY", "CVaR variational optimization is introduced here."),
        ("R-NO-FREE-STRUCTURE", "A feasibility-preserving mixer obtains structure for free."),
        ("R-NO-THEORY-PRIORITY", "The posterior-projector form is the first such theorem."),
    ]
    for claim_id, wording in rejected:
        rows.append(
            {
                "claim_id": claim_id,
                "section": "EXCLUDED_FROM_MANUSCRIPT",
                "paragraph": "",
                "wording": wording,
                "source": "results/synthesis_v1/CLAIM_EVIDENCE_MATRIX.csv",
                "status": "REJECTED_NOT_USED",
                "scope": "Prohibited wording",
            }
        )
    return rows


def parse_bib() -> dict[str, dict[str, str]]:
    text = (OVERLEAF / "references.bib").read_text(encoding="utf-8")
    starts = list(re.finditer(r"@([A-Za-z]+)\s*\{\s*([^,\s]+)\s*,", text))
    entries: dict[str, dict[str, str]] = {}
    for idx, start in enumerate(starts):
        body = text[start.end(): starts[idx + 1].start() if idx + 1 < len(starts) else len(text)]
        fields = {
            key.lower(): value.strip().strip("{},\n ")
            for key, value in re.findall(
                r"(?ms)^\s*([A-Za-z]+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\")\s*,?",
                body,
            )
        }
        # Nested TeX accents can exceed the intentionally small value parser;
        # field existence is sufficient for the bibliography audit.
        for field in ("author", "title", "year", "doi", "eprint", "url"):
            if field not in fields and re.search(rf"(?mi)^\s*{field}\s*=", body):
                fields[field] = "PRESENT"
        fields["entry_type"] = start.group(1).lower()
        entries[start.group(2)] = fields
    return entries


def citation_audit() -> tuple[list[dict], set[str], set[str]]:
    entries = parse_bib()
    tex = "\n".join(path.read_text(encoding="utf-8") for path in OVERLEAF.rglob("*.tex"))
    cited: set[str] = set()
    for group in re.findall(r"\\cite\w*\s*\{([^}]+)\}", tex):
        cited.update(key.strip() for key in group.split(","))
    rows: list[dict] = []
    for key in sorted(cited):
        entry = entries.get(key, {})
        required = all(entry.get(field) for field in ("author", "title", "year"))
        persistent = bool(entry.get("doi") or entry.get("eprint") or entry.get("url"))
        rows.append(
            {
                "citation_key": key,
                "key_exists": "YES" if key in entries else "NO",
                "author_present": "YES" if entry.get("author") else "NO",
                "title_present": "YES" if entry.get("title") else "NO",
                "year_present": "YES" if entry.get("year") else "NO",
                "doi_or_arxiv_or_url": entry.get("doi") or entry.get("eprint") or entry.get("url") or "",
                "primary_source_verified": "YES" if required and persistent else "NO",
                "status": "VERIFIED" if key in entries and required and persistent else "UNRESOLVED",
            }
        )
    return rows, cited, set(entries)


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", line) for line in text.splitlines())


def static_validation(cited: set[str], bib_keys: set[str]) -> dict:
    tex_paths = [OVERLEAF / "main.tex", *sorted((OVERLEAF / "sections").glob("*.tex")),
                 *sorted((OVERLEAF / "appendices").glob("*.tex")),
                 *sorted((OVERLEAF / "tables").glob("*.tex"))]
    combined = "\n".join(strip_comments(path.read_text(encoding="utf-8")) for path in tex_paths)

    labels = re.findall(r"\\label\{([^}]+)\}", combined)
    refs: set[str] = set()
    for group in re.findall(r"\\(?:ref|eqref|cref|Cref)\{([^}]+)\}", combined):
        refs.update(item.strip() for item in group.split(","))
    missing_refs = sorted(refs - set(labels))
    duplicate_labels = sorted(key for key, count in Counter(labels).items() if count > 1)

    missing_inputs: list[str] = []
    for item in re.findall(r"\\input\{([^}]+)\}", combined):
        target = OVERLEAF / item
        if not target.suffix:
            target = target.with_suffix(".tex")
        if not target.is_file():
            missing_inputs.append(item)
    missing_figures: list[str] = []
    for item in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", combined):
        candidates = [OVERLEAF / item, OVERLEAF / "figures" / item]
        if not any(path.is_file() for path in candidates):
            missing_figures.append(item)

    begin = Counter(re.findall(r"\\begin\{([^}]+)\}", combined))
    end = Counter(re.findall(r"\\end\{([^}]+)\}", combined))
    environment_mismatch = {
        key: begin[key] - end[key]
        for key in sorted(set(begin) | set(end))
        if begin[key] != end[key]
    }

    files = [path for path in OVERLEAF.rglob("*") if path.is_file()]
    absolute_paths = []
    for path in files:
        if path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "/home/" in text or "file://" in text:
            absolute_paths.append(path.relative_to(OVERLEAF).as_posix())
    symlinks = [path.relative_to(OVERLEAF).as_posix() for path in OVERLEAF.rglob("*") if path.is_symlink()]
    forbidden = [
        path.relative_to(OVERLEAF).as_posix()
        for path in OVERLEAF.rglob("*")
        if any(part in {".git", "__pycache__", ".ipynb_checkpoints", ".venv", "venv"} for part in path.parts)
    ]

    # Braces after escaped braces are removed.  This catches accidental gross imbalance.
    brace_text = re.sub(r"\\[{}]", "", combined)
    brace_balance = brace_text.count("{") - brace_text.count("}")

    prohibited_patterns = {
        "quantum_advantage_claim": r"\b(?:we|this (?:work|study)) (?:demonstrate|establish|prove)s? quantum advantage\b",
        "global_scaling_claim": r"(?<!not a )\b(?:confirm|establish|prove)(?:s|ed)? (?:a )?global scaling law\b",
        "theory_priority_claim": r"\b(?:first|novel|new) (?:theorem|bound|result)\b",
        "universal_qaoa_claim": r"\b(?:applies? universally to QAOA|all QAOA instances (?:obey|show|exhibit))\b",
    }
    prohibited_hits = {
        name: re.findall(pattern, combined, flags=re.IGNORECASE)
        for name, pattern in prohibited_patterns.items()
        if re.search(pattern, combined, flags=re.IGNORECASE)
    }

    unresolved_citations = sorted(cited - bib_keys)
    return {
        "latex_compiler": "LATEX_COMPILER_NOT_AVAILABLE",
        "tex_file_count": len(tex_paths),
        "overleaf_file_count": len(files),
        "brace_balance": brace_balance,
        "environment_mismatch": environment_mismatch,
        "label_count": len(labels),
        "reference_key_count": len(refs),
        "missing_references": missing_refs,
        "duplicate_labels": duplicate_labels,
        "citation_key_count": len(cited),
        "unresolved_citations": unresolved_citations,
        "missing_inputs": sorted(set(missing_inputs)),
        "missing_figures": sorted(set(missing_figures)),
        "absolute_paths": absolute_paths,
        "symlinks": symlinks,
        "forbidden_package_content": forbidden,
        "prohibited_wording_hits": prohibited_hits,
        "static_pass": not any(
            [brace_balance, environment_mismatch, missing_refs, duplicate_labels,
             unresolved_citations, missing_inputs, missing_figures, absolute_paths,
             symlinks, forbidden, prohibited_hits]
        ),
    }


def word_count() -> dict:
    def count_text(text: str) -> int:
        text = strip_comments(text)
        text = re.sub(r"\\begin\{(?:equation|equation\*|align|align\*|gather|gather\*)\}[\s\S]*?\\end\{(?:equation|equation\*|align|align\*|gather|gather\*)\}", " ", text)
        text = re.sub(r"\\(?:cite|ref|cref|Cref|label|input|includegraphics)\w*(?:\[[^]]*\])?\{[^}]*\}", " ", text)
        text = re.sub(r"\\(?:begin|end)\{[^}]+\}", " ", text)
        text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", " ", text)
        text = re.sub(r"\$[^$]*\$|\\\[[\s\S]*?\\\]", " ", text)
        text = re.sub(r"[{}&_^~]", " ", text)
        return len(re.findall(r"\b[\w'-]+\b", text))

    main_document = (OVERLEAF / "main.tex").read_text(encoding="utf-8")
    abstract_match = re.search(r"\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}", main_document)
    abstract = abstract_match.group(1) if abstract_match else ""
    main_paths = sorted((OVERLEAF / "sections").glob("*.tex"))
    appendix_paths = sorted((OVERLEAF / "appendices").glob("*.tex"))
    main_count = count_text(abstract) + sum(count_text(path.read_text(encoding="utf-8")) for path in main_paths)
    appendix_count = sum(count_text(path.read_text(encoding="utf-8")) for path in appendix_paths)
    return {"main_text_words": main_count, "appendix_words": appendix_count,
            "total_words": main_count + appendix_count, "method": "static approximate prose count"}


def main() -> None:
    AUDIT.mkdir(exist_ok=True)
    numeric = numeric_audit()
    write_csv(
        AUDIT / "numeric_verification.csv",
        ["statement_id", "section", "manuscript_value", "canonical_value", "source", "difference", "status", "notes"],
        numeric,
    )
    # The public package carries the same complete, project-relative audit.
    write_csv(
        OVERLEAF / "supplementary/numeric_audit.csv",
        ["statement_id", "section", "manuscript_value", "canonical_value", "source", "difference", "status", "notes"],
        numeric,
    )
    claims = claim_audit()
    write_csv(
        AUDIT / "claim_usage.csv",
        ["claim_id", "section", "paragraph", "wording", "source", "status", "scope"],
        claims,
    )
    citations, cited, bib_keys = citation_audit()
    write_csv(
        AUDIT / "citation_verification.csv",
        ["citation_key", "key_exists", "author_present", "title_present", "year_present",
         "doi_or_arxiv_or_url", "primary_source_verified", "status"],
        citations,
    )
    static = static_validation(cited, bib_keys)
    static["numeric_status_counts"] = dict(Counter(row["status"] for row in numeric))
    static["claim_status_counts"] = dict(Counter(row["status"] for row in claims))
    static["citation_status_counts"] = dict(Counter(row["status"] for row in citations))
    static["word_count"] = word_count()
    (AUDIT / "static_validation.json").write_text(json.dumps(static, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(static, indent=2))
    if not static["static_pass"]:
        raise SystemExit("static manuscript validation failed")
    if any(row["status"] in {"MISMATCH", "UNSUPPORTED"} for row in numeric):
        raise SystemExit("numeric audit failed")
    if any(row["status"] == "UNSUPPORTED" for row in claims):
        raise SystemExit("claim audit failed")
    if any(row["status"] == "UNRESOLVED" for row in citations):
        raise SystemExit("citation audit failed")


if __name__ == "__main__":
    main()
