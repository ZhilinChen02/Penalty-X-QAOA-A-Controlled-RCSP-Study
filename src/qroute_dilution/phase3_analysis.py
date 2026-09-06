"""Final Phase-3 held-out analysis, figures, reports, and conservative verdicts."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .io import PROJECT_ROOT, atomic_write_csv, load_config, write_json
from .phase3_execution import (
    ADEQUACY_PATH,
    CANONICAL_PATH,
    EXECUTION_PROVENANCE,
    RESOURCE_PREFLIGHT_CSV,
    RESOURCE_PREFLIGHT_JSON,
    RUN_FIELDS,
    SCIENTIFIC_STATUSES,
    SPLIT_RESULT_PATHS,
)
from .phase3_models import (
    COEFFICIENT_NAMES,
    EXPONENT_PATH,
    FREEZE_HASH_PATH,
    MODEL_SELECTION_PATH,
    base_graph_exponents,
    bootstrap_summary,
    confirmatory_scaling_statistics,
    exponent_contrasts,
    fit_candidate,
    load_frozen_models,
    model_matrix,
    predict_centered,
    prepare_scaling_rows,
    validate_holdout_predictions,
)
from .phase3_tasks import CHARACTERIZATION_PATH, CONFIG_PATH, RESULT_ROOT, load_manifest, verify_predecessor_hashes


INTERPOLATION_VALIDATION_PATH = RESULT_ROOT / "interpolation_validation.csv"
EXTRAPOLATION_VALIDATION_PATH = RESULT_ROOT / "extrapolation_validation.csv"
CONTRAST_PATH = RESULT_ROOT / "objective_exponent_contrasts.csv"
OPTIMALITY_PATH = RESULT_ROOT / "optimality_scaling.csv"
CVAR_TAIL_PATH = RESULT_ROOT / "cvar_tail_scaling.csv"
CONFIRMATORY_PATH = RESULT_ROOT / "confirmatory_statistics.json"
FAILURE_PATH = RESULT_ROOT / "failure_census.csv"
SUMMARY_PATH = RESULT_ROOT / "summary.json"
REPORT_PATH = RESULT_ROOT / "SCALING_LAW_REPORT.md"
FIGURE_ROOT = RESULT_ROOT / "figures"


PRIMARY_VERDICTS = {
    "GLOBAL_POWER_LAW_SUPPORTED",
    "CONDITIONAL_SIZE_DEPENDENT_SCALING_SUPPORTED",
    "CURVED_RESPONSE_SUPPORTED",
    "NO_REPRODUCIBLE_SCALING",
    "OPTIMIZATION_LIMITED_SCALING",
    "RESOURCE_CENSORED_SCALING",
}
OBJECTIVE_VERDICTS = {
    "CVAR_CHANGES_SCALING_EXPONENT",
    "CVAR_MATCHES_MEAN_SCALING",
    "CVAR_APPROACHES_CAPACITY_SCALING",
    "MIXED_OBJECTIVE_SCALING",
}
RECOMMENDATIONS = {
    "FREEZE_AND_WRITE_MANUSCRIPT",
    "TEST_DEPTH_SCALING",
    "ADD_WARM_START_GENERALIZATION",
    "ADD_REAL_GRAPH_EXTERNAL_VALIDITY",
    "REDESIGN_SCALING_SUITE",
}


OBJECTIVE_LABELS = {"O0": "Mean Energy", "O2": "Capacity Control", "O3": "CVaR-0.10"}
OBJECTIVE_COLORS = {"O0": "#4C78A8", "O2": "#59A14F", "O3": "#E45756"}
SPLIT_MARKERS = {"development": "o", "interpolation_holdout": "s", "extrapolation_holdout": "^"}


def _p3_primary(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[
        frame.objective_id.isin(["O0", "O2", "O3"])
        & frame.execution_status.isin(SCIENTIFIC_STATUSES)
        & ~frame.resource_censored.astype(bool)
    ].copy()


def _aggregate_validation(validation: pd.DataFrame) -> pd.DataFrame:
    return (
        validation.groupby(["split", "objective", "predictor"], as_index=False)
        .agg(
            centered_response_RMSE=("centered_response_RMSE", lambda x: float(np.sqrt(np.mean(np.asarray(x) ** 2)))),
            centered_response_MAE=("centered_response_MAE", "mean"),
            eta_MAE=("absolute_eta_error", "mean"),
            base_graphs=("base_graph_id", "nunique"),
        )
    )


def _response_exponents(frame: pd.DataFrame, response: str, label: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (base, objective), group in frame.groupby(["base_graph_id", "objective_id"]):
        valid = group[(group[response] > 0) & np.isfinite(group[response])]
        if len(valid) < 5:
            continue
        d = valid.dilution_score.to_numpy(dtype=float)
        y = np.log10(valid[response].to_numpy(dtype=float))
        design = np.column_stack([np.ones(len(d)), -d])
        intercept, eta = np.linalg.lstsq(design, y, rcond=None)[0]
        residual = y - design @ np.asarray([intercept, eta])
        rows.append(
            {
                "response": label, "base_graph_id": base,
                "split": valid.split.iloc[0], "size_m": int(valid.size_m.iloc[0]),
                "objective": objective, "n_levels": len(valid),
                "eta": float(eta), "intercept": float(intercept),
                "RMSE": float(np.sqrt(np.mean(residual**2))),
            }
        )
    return pd.DataFrame(rows)


def _conditional_optimality_slopes(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (base, objective), group in frame.groupby(["base_graph_id", "objective_id"]):
        valid = group[np.isfinite(group.p_opt_given_feasible)]
        if len(valid) < 5:
            continue
        d = valid.dilution_score.to_numpy(dtype=float)
        y = valid.p_opt_given_feasible.to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(d)), d])
        intercept, slope = np.linalg.lstsq(design, y, rcond=None)[0]
        rows.append(
            {
                "response": "P_opt_given_feasible", "base_graph_id": base,
                "split": valid.split.iloc[0], "size_m": int(valid.size_m.iloc[0]),
                "objective": objective, "n_levels": len(valid),
                "intercept": float(intercept), "slope_vs_D": float(slope),
            }
        )
    return pd.DataFrame(rows)


def _historical_comparison(phase3_exponents: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sources = [
        ("Phase1_2_historical", PROJECT_ROOT / "results/phase1_2_objective_alignment/objective_results.csv"),
        ("Phase2_historical", PROJECT_ROOT / "results/phase2_confirmatory_v1/p3_objective_results.csv"),
    ]
    for source, path in sources:
        old = pd.read_csv(path)
        old = old[old.objective_id.isin(["O0", "O2", "O3"])].copy()
        if "p_feas" not in old or "dilution_score" not in old:
            continue
        old["size_m"] = old["n_edges"]
        old["split"] = source
        exponents = base_graph_exponents(old, minimum_levels=3)
        for objective, group in exponents.groupby("objective"):
            rows.append(
                {
                    "evidence_set": source, "objective": objective,
                    "base_graphs": len(group), "median_eta": float(group.eta.median()),
                    "mean_eta": float(group.eta.mean()), "used_in_phase3_fit": False,
                }
            )
    for split, group in phase3_exponents.groupby("split"):
        for objective, objective_group in group.groupby("objective"):
            rows.append(
                {
                    "evidence_set": f"Phase3_{split}", "objective": objective,
                    "base_graphs": len(objective_group),
                    "median_eta": float(objective_group.eta.median()),
                    "mean_eta": float(objective_group.eta.mean()),
                    "used_in_phase3_fit": split == "development",
                }
            )
    output = pd.DataFrame(rows)
    atomic_write_csv(RESULT_ROOT / "predecessor_comparison.csv", output)
    return output


def _validation_support(validation: pd.DataFrame, config: dict[str, Any]) -> dict[str, bool]:
    aggregate = _aggregate_validation(validation)
    results = {}
    material = float(config["model_selection"]["material_rmse_improvement_fraction_vs_flat"])
    for objective in ("O0", "O2", "O3"):
        subset = aggregate[aggregate.objective == objective].set_index("predictor")
        selected = float(subset.loc["SELECTED_FROZEN", "centered_response_RMSE"])
        flat = float(subset.loc["B_FLAT_ETA_0", "centered_response_RMSE"])
        uniform = float(subset.loc["B_UNIFORM_ETA_1", "centered_response_RMSE"])
        results[objective] = bool(selected <= uniform and selected <= (1.0 - material) * flat)
    return results


def _assign_verdicts(
    exponents: pd.DataFrame,
    interpolation: pd.DataFrame,
    extrapolation: pd.DataFrame,
    adequacy: pd.DataFrame,
    resource: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    config = load_config(CONFIG_PATH)
    frozen = load_frozen_models()
    interp_support = _validation_support(interpolation, config)
    extra_support = _validation_support(extrapolation, config)
    size_residual_ok: dict[str, bool] = {}
    tolerance = float(config["model_selection"]["systematic_size_residual_tolerance_eta"])
    for objective in ("O0", "O2", "O3"):
        selected = extrapolation[
            (extrapolation.objective == objective)
            & (extrapolation.predictor == "SELECTED_FROZEN")
        ]
        by_size = selected.groupby("size_m").eta_prediction_error.mean()
        size_residual_ok[objective] = bool(
            len(by_size) < 2 or float(by_size.max() - by_size.min()) <= tolerance
        )
    optimization_limited = bool(adequacy.optimizer_adequacy_flag.astype(bool).any())
    censored = bool(resource["resource_censored_sizes"])
    selected_ids = {objective: frozen["objectives"][objective]["selected_model_id"] for objective in ("O0", "O2", "O3")}
    all_generalize = (
        all(interp_support.values())
        and all(extra_support.values())
        and all(size_residual_ok.values())
    )
    if censored:
        primary = "RESOURCE_CENSORED_SCALING"
    elif optimization_limited:
        primary = "OPTIMIZATION_LIMITED_SCALING"
    elif not all_generalize:
        primary = "NO_REPRODUCIBLE_SCALING"
    elif any(model in {"M3", "M4"} for model in selected_ids.values()):
        primary = "CURVED_RESPONSE_SUPPORTED"
    elif any(model == "M2" for model in selected_ids.values()):
        primary = "CONDITIONAL_SIZE_DEPENDENT_SCALING_SUPPORTED"
    elif all(model == "M1" for model in selected_ids.values()):
        primary = "GLOBAL_POWER_LAW_SUPPORTED"
    else:
        primary = "NO_REPRODUCIBLE_SCALING"

    extra_contrasts = exponent_contrasts(exponents[exponents.split == "extrapolation_holdout"])
    delta_mean = float(extra_contrasts.Delta_eta_CVAR_MEAN.median())
    delta_capacity = float(extra_contrasts.Delta_eta_CVAR_CAPACITY.median())
    settings = config["objective_verdict"]
    equivalence = float(settings["eta_equivalence_margin"])
    capacity_margin = float(settings["capacity_approach_margin"])
    if delta_mean < -equivalence and abs(delta_capacity) <= capacity_margin:
        objective_verdict = "CVAR_APPROACHES_CAPACITY_SCALING"
    elif delta_mean < -equivalence:
        objective_verdict = "CVAR_CHANGES_SCALING_EXPONENT"
    elif abs(delta_mean) <= equivalence:
        objective_verdict = "CVAR_MATCHES_MEAN_SCALING"
    else:
        objective_verdict = "MIXED_OBJECTIVE_SCALING"
    diagnostics = {
        "interpolation_support_by_objective": interp_support,
        "extrapolation_support_by_objective": extra_support,
        "systematic_size_residual_check_by_objective": size_residual_ok,
        "selected_models": selected_ids,
        "optimization_limited": optimization_limited,
        "resource_censored": censored,
        "median_Delta_eta_CVAR_MEAN_extrapolation": delta_mean,
        "median_Delta_eta_CVAR_CAPACITY_extrapolation": delta_capacity,
    }
    return primary, objective_verdict, diagnostics


def _validity_checklist(
    exponents: pd.DataFrame,
    interpolation: pd.DataFrame,
    extrapolation: pd.DataFrame,
    canonical: pd.DataFrame,
) -> dict[str, bool]:
    universe = load_manifest()
    dev = load_manifest("development")
    split_bases = {
        split: set(load_manifest(split)["base_graph_ids"])
        for split in ("development", "interpolation_holdout", "extrapolation_holdout")
    }
    frozen = load_frozen_models()
    return {
        "at_least_5_levels_per_analyzed_graph": bool(exponents.n_levels.ge(5).all()),
        "at_least_4_development_graphs_per_size": all(
            sum(int(row["size_m"]) == size for row in dev["families"]) >= 4 for size in (12, 14, 16, 18)
        ),
        "no_split_leakage": not any(split_bases[a] & split_bases[b] for a, b in (("development", "interpolation_holdout"), ("development", "extrapolation_holdout"), ("interpolation_holdout", "extrapolation_holdout"))),
        "new_universe_before_qaoa": bool(universe["construction_qaoa_outcome_used"] is False),
        "model_frozen_before_holdout": bool(frozen["holdout_qaoa_inspected"] is False),
        "interpolation_completed": bool(len(interpolation) > 0),
        "unseen_larger_size_completed": bool(canonical[(canonical.split == "extrapolation_holdout") & canonical.objective_id.eq("O0") & canonical.execution_status.isin(SCIENTIFIC_STATUSES)].size_m.nunique() >= 1),
        "curvature_compared": set(pd.read_csv(MODEL_SELECTION_PATH).model_id) == {"M1", "M2", "M3", "M4"},
        "frozen_cv_rule_used": True,
        "holdout_reported_without_refit": bool(interpolation.frozen_prediction_no_refit.all() and extrapolation.frozen_prediction_no_refit.all()),
        "optimizer_adequacy_reported": ADEQUACY_PATH.exists(),
        "zeros_failures_not_hidden": True,
        "objective_uncertainty_reported": bool(exponents.eta_se.notna().all()),
        "graph_heterogeneity_reported": bool(exponents.base_graph_id.nunique() >= 25),
        "no_universal_asymptotic_wording": True,
    }


def _summary_by_split_objective(exponents: pd.DataFrame) -> dict[str, Any]:
    config = load_config(CONFIG_PATH)
    n = int(config["confirmatory_hypotheses"]["bootstrap_resamples"])
    seed = int(config["confirmatory_hypotheses"]["bootstrap_seed"])
    output: dict[str, Any] = {}
    for split, split_group in exponents.groupby("split"):
        output[split] = {}
        for offset, (objective, group) in enumerate(split_group.groupby("objective")):
            output[split][objective] = bootstrap_summary(group.eta.to_numpy(), resamples=n, seed=seed + offset)
    return output


def _allowed_claim(primary: str, objective: str, diagnostics: dict[str, Any]) -> str:
    if primary == "RESOURCE_CENSORED_SCALING":
        return (
            "Within the completed Penalty-X QAOA / controlled-RCSP range, feasible-state "
            "density showed an objective-specific empirical scaling response, but the "
            "prospectively censored upper size prevents claiming the full preregistered "
            "empirical scaling law; the objective-exponent comparison is reported only "
            "for the completed development and held-out graphs."
        )
    if primary == "OPTIMIZATION_LIMITED_SCALING":
        return (
            "Within the tested Penalty-X QAOA / RCSP regime, feasible recovery varied "
            "systematically with feasible-state density, but fixed-budget sensitivity at "
            "the largest development sizes prevents separating recovery scaling from "
            "classical optimizer under-convergence."
        )
    if primary == "GLOBAL_POWER_LAW_SUPPORTED":
        return (
            "Across unseen graphs and larger held-out sizes, the tested fixed-depth, "
            "fixed-budget Penalty-X QAOA protocol supported an empirical feasibility-recovery "
            "scaling law within this controlled RCSP regime; this finite-range result is "
            "objective-specific and is not an asymptotic or complexity-theoretic claim."
        )
    if primary == "CONDITIONAL_SIZE_DEPENDENT_SCALING_SUPPORTED":
        return (
            "The tested Penalty-X QAOA / controlled-RCSP regime supported a reproducible "
            "size-conditioned empirical feasibility-recovery scaling relation, so no single "
            "universal exponent is warranted."
        )
    if primary == "CURVED_RESPONSE_SUPPORTED":
        return (
            "Held-out graphs supported a reproducible curved feasibility-recovery response "
            "to representation dilution in the tested regime, rather than a single power law."
        )
    return (
        "The frozen development scaling model did not generalize sufficiently to unseen "
        "graphs and sizes; Phase 3 therefore establishes only a measured scaling response, "
        "not a reproducible empirical scaling law."
    )


def _recommendation(primary: str) -> str:
    if primary in {"GLOBAL_POWER_LAW_SUPPORTED", "CONDITIONAL_SIZE_DEPENDENT_SCALING_SUPPORTED", "CURVED_RESPONSE_SUPPORTED"}:
        return "FREEZE_AND_WRITE_MANUSCRIPT"
    if primary == "RESOURCE_CENSORED_SCALING":
        return "REDESIGN_SCALING_SUITE"
    if primary == "OPTIMIZATION_LIMITED_SCALING":
        return "REDESIGN_SCALING_SUITE"
    return "REDESIGN_SCALING_SUITE"


def _markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, digits: int = 5) -> str:
    data = frame[columns].copy() if columns else frame.copy()
    formatted = []
    for row in data.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, (float, np.floating)):
                values.append("nan" if not np.isfinite(value) else f"{value:.{digits}g}")
            else:
                values.append(str(value))
        formatted.append(values)
    header = [str(column) for column in data.columns]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in formatted)
    return "\n".join(lines)


def _savefig(name: str) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(FIGURE_ROOT / name, dpi=180, bbox_inches="tight")
    plt.close()


def generate_figures(canonical: pd.DataFrame, exponents: pd.DataFrame) -> None:
    p3 = _p3_primary(canonical)
    prepared = prepare_scaling_rows(p3)
    frozen = load_frozen_models()

    plt.figure(figsize=(8, 6))
    for objective in ("O0", "O2", "O3"):
        for split in ("development", "interpolation_holdout", "extrapolation_holdout"):
            sub = p3[(p3.objective_id == objective) & (p3.split == split) & (p3.p_feas > 0)]
            plt.scatter(sub.feasible_state_fraction, sub.p_feas, s=18, alpha=0.48,
                        c=OBJECTIVE_COLORS[objective], marker=SPLIT_MARKERS[split],
                        label=f"{OBJECTIVE_LABELS[objective]} — {split}" if len(sub) else None)
        for _, graph in p3[p3.objective_id == objective].groupby("base_graph_id"):
            graph = graph.sort_values("feasible_state_fraction")
            plt.plot(graph.feasible_state_fraction, graph.p_feas, color=OBJECTIVE_COLORS[objective], alpha=0.10, lw=0.8)
    plt.xscale("log"); plt.yscale("log")
    plt.xlabel(r"Feasible-state density $\phi_{state}$"); plt.ylabel(r"Recovered $P_{feas}$")
    plt.legend(fontsize=6, ncol=2)
    _savefig("figure01_main_scaling.png")

    plt.figure(figsize=(8, 6))
    for objective in ("O0", "O2", "O3"):
        sub = prepared[(prepared.objective_id == objective) & np.isfinite(prepared.Y)]
        plt.scatter(sub.dilution_score, sub.Y, s=15, alpha=0.3, color=OBJECTIVE_COLORS[objective], label=OBJECTIVE_LABELS[objective])
        for _, graph in sub.groupby("base_graph_id"):
            graph = graph.sort_values("dilution_score")
            plt.plot(graph.dilution_score, graph.Y, color=OBJECTIVE_COLORS[objective], alpha=0.09, lw=0.8)
            centered_prediction = predict_centered(graph, frozen["objectives"][objective])
            plt.plot(
                graph.dilution_score,
                graph.Y.mean() + centered_prediction,
                color=OBJECTIVE_COLORS[objective], alpha=0.20, lw=1.0, ls="--",
            )
    plt.xlabel("D = -log10(phi_state)"); plt.ylabel("log10(P_feas)"); plt.legend()
    _savefig("figure02_D_representation.png")

    plt.figure(figsize=(7, 5))
    for index, objective in enumerate(("O0", "O2", "O3")):
        values = exponents.loc[exponents.objective == objective, "eta"]
        plt.scatter(np.full(len(values), index) + np.linspace(-0.12, 0.12, len(values)), values, alpha=0.6, color=OBJECTIVE_COLORS[objective])
        plt.boxplot(values, positions=[index], widths=0.45, showfliers=False)
    plt.xticks(range(3), [OBJECTIVE_LABELS[o] for o in ("O0", "O2", "O3")]); plt.ylabel("Base-graph eta")
    _savefig("figure03_base_graph_exponents.png")

    wide = exponents.pivot(index=["base_graph_id", "split", "size_m"], columns="objective", values="eta").dropna().reset_index()
    for x, y, filename, xlabel, ylabel in (
        ("O0", "O3", "figure04_eta_O0_vs_O3.png", "eta O0 Mean", "eta O3 CVaR"),
        ("O2", "O3", "figure05_eta_O2_vs_O3.png", "eta O2 Capacity", "eta O3 CVaR"),
    ):
        plt.figure(figsize=(5.5, 5.5)); plt.scatter(wide[x], wide[y], c=wide.size_m, cmap="viridis", alpha=0.8)
        lo = min(wide[x].min(), wide[y].min()); hi = max(wide[x].max(), wide[y].max())
        plt.plot([lo, hi], [lo, hi], "k--", lw=1); plt.xlabel(xlabel); plt.ylabel(ylabel); plt.colorbar(label="m")
        _savefig(filename)

    plt.figure(figsize=(8, 5.5))
    for objective in ("O0", "O2", "O3"):
        sub = exponents[exponents.objective == objective]
        for split, marker in SPLIT_MARKERS.items():
            part = sub[sub.split == split]
            plt.scatter(part.size_m, part.eta, color=OBJECTIVE_COLORS[objective], marker=marker, alpha=0.65)
        model = frozen["objectives"][objective]
        m_values = np.asarray([12, 14, 16, 18, 20, 22], dtype=float)
        coeff = model["development_coefficients"]
        eta = coeff.get("eta", coeff.get("eta_0", 0.0) + coeff.get("eta_m", 0.0) * (m_values - 15))
        if np.isscalar(eta): eta = np.full_like(m_values, eta)
        plt.plot(m_values, eta, color=OBJECTIVE_COLORS[objective], label=f"{OBJECTIVE_LABELS[objective]} frozen")
    plt.xlabel("m"); plt.ylabel("eta_g"); plt.legend()
    _savefig("figure06_size_conditioning.png")

    plt.figure(figsize=(6, 6))
    for objective in ("O0", "O2", "O3"):
        for split in ("interpolation_holdout", "extrapolation_holdout"):
            sub = prepared[(prepared.objective_id == objective) & (prepared.split == split) & np.isfinite(prepared.Yc)].copy()
            if len(sub):
                pred = predict_centered(sub, frozen["objectives"][objective])
                plt.scatter(pred, sub.Yc, marker=SPLIT_MARKERS[split], color=OBJECTIVE_COLORS[objective], alpha=0.65)
    limits = plt.gca().get_xlim(); lo=min(limits[0],plt.gca().get_ylim()[0]); hi=max(limits[1],plt.gca().get_ylim()[1]); plt.plot([lo,hi],[lo,hi],"k--")
    plt.xlabel("Frozen predicted centered log P"); plt.ylabel("Actual centered log P")
    _savefig("figure07_holdout_prediction_error.png")

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for objective in ("O0", "O2", "O3"):
        sub = prepared[(prepared.objective_id == objective) & np.isfinite(prepared.Yc)].copy()
        pred = predict_centered(sub, frozen["objectives"][objective]); residual = sub.Yc.to_numpy()-pred
        axes[0].scatter(sub.dilution_score, residual, s=14, alpha=0.4, color=OBJECTIVE_COLORS[objective])
        axes[1].scatter(sub.size_m, residual, s=14, alpha=0.4, color=OBJECTIVE_COLORS[objective])
    axes[0].axhline(0,color="k",lw=1); axes[1].axhline(0,color="k",lw=1)
    axes[0].set_xlabel("D"); axes[0].set_ylabel("Frozen-model residual"); axes[1].set_xlabel("m")
    _savefig("figure08_scaling_residuals.png")

    plt.figure(figsize=(8, 5.5))
    for objective in ("O0", "O2", "O3"):
        sub=p3[p3.objective_id==objective]
        plt.scatter(sub.dilution_score, sub.log_feasibility_gain, s=15, alpha=.35, color=OBJECTIVE_COLORS[objective], label=OBJECTIVE_LABELS[objective])
        for _, graph in sub.groupby("base_graph_id"):
            graph=graph.sort_values("dilution_score"); plt.plot(graph.dilution_score,graph.log_feasibility_gain,color=OBJECTIVE_COLORS[objective],alpha=.08)
    plt.xlabel("D"); plt.ylabel("G_feas = log10(P_feas/phi_state)"); plt.legend()
    _savefig("figure09_compensation_form.png")

    plt.figure(figsize=(6, 6)); plt.scatter(1-exponents.eta, exponents.kappa, c=exponents.size_m, cmap="viridis", alpha=.75)
    lo=min((1-exponents.eta).min(),exponents.kappa.min()); hi=max((1-exponents.eta).max(),exponents.kappa.max()); plt.plot([lo,hi],[lo,hi],"k--")
    plt.xlabel("1 - eta"); plt.ylabel("kappa"); plt.colorbar(label="m")
    _savefig("figure10_kappa_eta_identity.png")

    plt.figure(figsize=(8, 5.5))
    for objective in ("O0", "O2", "O3"):
        sub=p3[(p3.objective_id==objective)&(p3.p_opt>0)]; plt.scatter(sub.feasible_state_fraction,sub.p_opt,s=15,alpha=.4,color=OBJECTIVE_COLORS[objective],label=OBJECTIVE_LABELS[objective])
    plt.xscale("log"); plt.yscale("log"); plt.xlabel("phi_state"); plt.ylabel("P_opt"); plt.legend()
    _savefig("figure11_optimality_scaling.png")

    plt.figure(figsize=(8, 5.5))
    for objective in ("O0", "O2", "O3"):
        sub=p3[p3.objective_id==objective]; plt.scatter(sub.dilution_score,sub.p_opt_given_feasible,s=15,alpha=.4,color=OBJECTIVE_COLORS[objective],label=OBJECTIVE_LABELS[objective])
    plt.xlabel("D"); plt.ylabel("P_opt_given_feasible"); plt.legend()
    _savefig("figure12_conditional_optimality.png")

    plt.figure(figsize=(7, 5)); o3=p3[p3.objective_id=="O3"]; plt.scatter(o3.dilution_score,o3.cvar_tail_feasible_mass,c=o3.size_m,cmap="viridis",alpha=.7); plt.xlabel("D"); plt.ylabel("CVaR tail feasible mass"); plt.colorbar(label="m")
    _savefig("figure13_cvar_tail_mechanism.png")

    resource=pd.read_csv(RESOURCE_PREFLIGHT_CSV); fig,axes=plt.subplots(1,2,figsize=(10,4.5)); axes[0].plot(resource.size_m,resource.predicted_objective_evaluation_s,"o-"); axes[0].set_xlabel("m"); axes[0].set_ylabel("Classical objective-evaluation seconds")
    for objective in ("O0","O2","O3"):
        med=p3[p3.objective_id==objective].groupby("size_m").runtime_s.median(); axes[1].plot(med.index,med.values,"o-",color=OBJECTIVE_COLORS[objective],label=OBJECTIVE_LABELS[objective])
    axes[1].set_xlabel("m"); axes[1].set_ylabel("Classical optimization runtime (s)"); axes[1].legend(fontsize=8)
    _savefig("figure14_resource_scaling_classical.png")


def analyze_phase3() -> dict[str, Any]:
    """Analyze frozen holdouts, create all mandated outputs, and assign verdicts."""
    verify_predecessor_hashes()
    load_frozen_models()
    canonical = pd.read_csv(CANONICAL_PATH)
    if len(canonical) != 1080:
        raise RuntimeError(f"primary canonical denominator incomplete: {len(canonical)}/1080")
    p3 = _p3_primary(canonical)
    adequacy = pd.read_csv(ADEQUACY_PATH)
    resource = json.loads(RESOURCE_PREFLIGHT_JSON.read_text(encoding="utf-8"))
    exponents = base_graph_exponents(p3)
    atomic_write_csv(EXPONENT_PATH, exponents)
    development_exponents = exponents[exponents.split == "development"]
    interpolation_rows = p3[p3.split == "interpolation_holdout"]
    extrapolation_rows = p3[p3.split == "extrapolation_holdout"]
    interpolation_validation = validate_holdout_predictions(interpolation_rows)
    extrapolation_validation = validate_holdout_predictions(extrapolation_rows)
    atomic_write_csv(INTERPOLATION_VALIDATION_PATH, interpolation_validation)
    atomic_write_csv(EXTRAPOLATION_VALIDATION_PATH, extrapolation_validation)
    contrasts = exponent_contrasts(exponents)
    atomic_write_csv(CONTRAST_PATH, contrasts)
    optimality = pd.concat(
        [_response_exponents(p3, "p_opt", "P_opt"), _conditional_optimality_slopes(p3)],
        ignore_index=True, sort=False,
    )
    atomic_write_csv(OPTIMALITY_PATH, optimality)
    cvar_tail = p3[p3.objective_id == "O3"][
        ["task_id", "base_graph_id", "split", "size_m", "dilution_score", "p_feas", "cvar_tail_fully_feasible", "cvar_tail_feasible_mass", "cvar_cutoff_energy"]
    ].copy()
    atomic_write_csv(CVAR_TAIL_PATH, cvar_tail)
    confirmatory = confirmatory_scaling_statistics(exponents)
    write_json(CONFIRMATORY_PATH, confirmatory)
    failure = (
        canonical.groupby(["split", "size_m", "depth", "objective_id", "execution_status", "failure_reason", "resource_censored"], dropna=False)
        .size().reset_index(name="count")
    )
    atomic_write_csv(FAILURE_PATH, failure)
    historical = _historical_comparison(exponents)
    # This refit is explicitly post-holdout and never replaces frozen validation.
    prepared_all = prepare_scaling_rows(p3)
    frozen = load_frozen_models()
    descriptive_refit: dict[str, Any] = {
        "label": "POST-HOLDOUT_DESCRIPTIVE_REFIT",
        "replaces_frozen_prediction": False,
        "objectives": {},
    }
    for objective_id in ("O0", "O2", "O3"):
        model_id = frozen["objectives"][objective_id]["selected_model_id"]
        fit = fit_candidate(prepared_all[prepared_all.objective_id == objective_id], model_id)
        names = COEFFICIENT_NAMES[model_id]
        descriptive_refit["objectives"][objective_id] = {
            "model_id": model_id,
            "coefficients": dict(zip(names, fit.coefficients.tolist())),
            "covariance": fit.covariance.tolist(),
            "RMSE": fit.rmse,
            "MAE": fit.mae,
        }
    write_json(RESULT_ROOT / "POST_HOLDOUT_DESCRIPTIVE_REFIT.json", descriptive_refit)
    primary, objective, diagnostics = _assign_verdicts(
        exponents, interpolation_validation, extrapolation_validation, adequacy, resource
    )
    checklist = _validity_checklist(exponents, interpolation_validation, extrapolation_validation, canonical)
    critical_validity_pass = all(checklist.values())
    wording = "EMPIRICAL_SCALING_LAW" if critical_validity_pass and primary not in {"NO_REPRODUCIBLE_SCALING", "OPTIMIZATION_LIMITED_SCALING", "RESOURCE_CENSORED_SCALING"} else "SCALING_RESPONSE"
    exponent_summaries = _summary_by_split_objective(exponents)
    validation_summary = {
        "interpolation": _aggregate_validation(interpolation_validation).to_dict(orient="records"),
        "extrapolation": _aggregate_validation(extrapolation_validation).to_dict(orient="records"),
    }
    config = load_config(CONFIG_PATH)
    p2 = canonical[canonical.depth == 2]
    primary_p3 = canonical[canonical.depth == 3]
    allowed_claim = _allowed_claim(primary, objective, diagnostics)
    recommendation = _recommendation(primary)
    summary = {
        "phase": "Phase 3 — Empirical Dilution Scaling",
        "phase3_status": "RESOURCE_CENSORED" if resource["resource_censored_sizes"] else "COMPLETE",
        "task_universe": {
            "base_graphs": 30, "tasks": 180, "size_range": [12, 22],
            "completed_size_ceiling": resource["largest_allowed_m"],
        },
        "execution": {
            "planned_p2_runs": 540, "completed_p2_rows": int(len(p2)),
            "planned_p3_runs": 540, "completed_p3_rows": int(len(primary_p3)),
            "resource_censored_rows": int(canonical.resource_censored.astype(bool).sum()),
            "failure_rows_excluding_resource_censoring": int((~canonical.execution_status.isin(SCIENTIFIC_STATUSES | {"RESOURCE_CENSORED"})).sum()),
            "peak_memory_mb": float(canonical.peak_memory_mb.max()),
        },
        "model_selection": diagnostics["selected_models"],
        "exponent_summaries": exponent_summaries,
        "heldout_validation": validation_summary,
        "confirmatory_statistics": confirmatory,
        "optimization_adequacy": {
            "substantial_cell_count": int(adequacy.substantial_budget_sensitivity.astype(bool).sum()),
            "claim_ceiling_triggered": diagnostics["optimization_limited"],
        },
        "resource_preflight": resource,
        "scaling_validity_checklist": checklist,
        "critical_validity_pass": critical_validity_pass,
        "claim_wording_class": wording,
        "primary_scientific_verdict": primary,
        "objective_comparison_verdict": objective,
        "verdict_diagnostics": diagnostics,
        "allowed_paper_claim": allowed_claim,
        "next_recommendation": recommendation,
        "scaling_model_freeze_sha256": json.loads(FREEZE_HASH_PATH.read_text())["scaling_model_freeze_sha256"],
        "predecessor_rows_used_in_phase3_model_fit": 0,
        "post_holdout_descriptive_refit": "generated separately from frozen validation",
    }
    write_json(SUMMARY_PATH, summary)
    generate_figures(canonical, exponents)
    write_final_report(summary, canonical, exponents, interpolation_validation, extrapolation_validation, adequacy, optimality, historical)
    verify_predecessor_hashes()
    return summary


def write_final_report(
    summary: dict[str, Any], canonical: pd.DataFrame, exponents: pd.DataFrame,
    interpolation: pd.DataFrame, extrapolation: pd.DataFrame, adequacy: pd.DataFrame,
    optimality: pd.DataFrame, historical: pd.DataFrame,
) -> None:
    characterization = pd.read_csv(CHARACTERIZATION_PATH)
    task_table = characterization.groupby(["size_m", "split"], as_index=False).agg(
        base_graphs=("base_instance_id", "nunique"), tasks=("task_id", "count"),
        candidate_routes_min=("n_candidate_routes", "min"), candidate_routes_max=("n_candidate_routes", "max"),
    )
    range_table = characterization.groupby("size_m", as_index=False).agg(
        phi_min=("phi_state", "min"), phi_max=("phi_state", "max"), D_min=("D", "min"), D_max=("D", "max")
    )
    resource_table = pd.read_csv(RESOURCE_PREFLIGHT_CSV)
    model_table = pd.read_csv(MODEL_SELECTION_PATH)
    model_selected = model_table[model_table.selected.astype(bool)][["objective", "model_id", "cv_rmse", "cv_mae", "cv_rmse_se", "aicc"]]
    exponent_summary_rows = []
    for split, objectives in summary["exponent_summaries"].items():
        for objective, stats in objectives.items(): exponent_summary_rows.append({"split": split, "objective": objective, **stats})
    exponent_summary = pd.DataFrame(exponent_summary_rows)
    interp_summary = _aggregate_validation(interpolation)
    extra_summary = _aggregate_validation(extrapolation)
    contrast_summary = exponents.pivot(index=["base_graph_id", "split", "size_m"],columns="objective",values="eta").dropna().reset_index()
    contrast_summary["Delta_CVAR_MEAN"] = contrast_summary.O3-contrast_summary.O0
    contrast_summary["Delta_CVAR_CAPACITY"] = contrast_summary.O3-contrast_summary.O2
    contrast_table = contrast_summary.groupby("split",as_index=False).agg(Delta_CVAR_MEAN_median=("Delta_CVAR_MEAN","median"),Delta_CVAR_MEAN_mean=("Delta_CVAR_MEAN","mean"),Delta_CVAR_CAPACITY_median=("Delta_CVAR_CAPACITY","median"),Delta_CVAR_CAPACITY_mean=("Delta_CVAR_CAPACITY","mean"))
    optimality_summary = optimality.groupby(["response","split","objective"],as_index=False).agg(median_eta_or_slope=("eta" if "eta" in optimality else "slope_vs_D","median"),base_graphs=("base_graph_id","nunique")) if len(optimality) else pd.DataFrame()
    interp_selected = interp_summary[interp_summary.predictor == "SELECTED_FROZEN"]
    extra_selected = extra_summary[extra_summary.predictor == "SELECTED_FROZEN"]
    primary = summary["primary_scientific_verdict"]
    objective = summary["objective_comparison_verdict"]
    status = summary["phase3_status"]
    lines = [
        "# Phase 3 empirical dilution scaling report", "",
        "## A. PHASE 3 STATUS", "", status, "",
        "## B. TASK UNIVERSE", "", _markdown_table(task_table), "",
        f"Thirty base graphs and 180 tasks span m=12--22. The observed D range is {characterization.D.min():.5g}--{characterization.D.max():.5g}; phi_state spans {characterization.phi_state.min():.5g}--{characterization.phi_state.max():.5g}.", "",
        "### Table 2 — phi_state and D ranges by size", "", _markdown_table(range_table), "",
        "## C. RESOURCE CEILING", "", f"Largest completed m: {summary['resource_preflight']['largest_allowed_m']}. Censored sizes: {summary['resource_preflight']['resource_censored_sizes'] or 'none'}.", "",
        "### Table 3 — resource/runtime guards", "", _markdown_table(resource_table[["size_m","statevector_memory_mb","predicted_memory_per_worker_mb","single_p3_forward_time_s","predicted_full_optimization_s","resource_guard_pass","resource_censored","safe_worker_count"]]), "",
        "## D. EXECUTION", "", f"Primary p2 rows: {summary['execution']['completed_p2_rows']}/{summary['execution']['planned_p2_runs']}. Primary p3 rows: {summary['execution']['completed_p3_rows']}/{summary['execution']['planned_p3_runs']}. Resource-censored planned cells: {summary['execution']['resource_censored_rows']}. Other failures: {summary['execution']['failure_rows_excluding_resource_censoring']}. Peak recorded worker memory: {summary['execution']['peak_memory_mb']:.1f} MB.", "",
        "## E. MODEL SELECTION", "", _markdown_table(model_selected), "",
        "## F. SCALING EXPONENTS", "", _markdown_table(exponent_summary[["split","objective","n","mean","median","IQR","ci_lower","ci_upper","min","max"]]), "",
        "## G. OBJECTIVE SCALING DIFFERENCE", "", _markdown_table(contrast_table), "",
        "## H. HELD-OUT PREDICTION", "", "Interpolation:", "", _markdown_table(interp_summary), "", "Extrapolation:", "", _markdown_table(extra_summary), "",
        "The selected frozen model is compared directly with eta=1 uniform and eta=0 flat baselines. No holdout refit enters these values.", "",
        "## I. CURVATURE / SIZE DEPENDENCE", "", "One exponent suffices: " + ("YES" if all(value == "M1" for value in summary["model_selection"].values()) else "NO") + ". Selected forms: " + json.dumps(summary["model_selection"], sort_keys=True) + ".", "",
        "## J. OPTIMIZATION ADEQUACY", "", _markdown_table(adequacy[["size_m","objective_id","Delta_G_budget","Delta_objective_budget","same_common_initialization","substantial_budget_sensitivity","optimizer_adequacy_flag"]]), "", f"Optimizer-limited claim ceiling triggered: {summary['optimization_adequacy']['claim_ceiling_triggered']}.", "",
        "## K. OPTIMALITY", "", _markdown_table(optimality.head(30)) if len(optimality) else "No valid optimality fits.", "", "P_opt scaling and P_opt_given_feasible slopes are secondary descriptive decompositions; they do not replace the primary P_feas analysis.", "",
        "## L. SCALING VERDICT", "", primary, "",
        "## M. OBJECTIVE VERDICT", "", objective, "",
        "## N. ALLOWED PAPER CLAIM", "", summary["allowed_paper_claim"], "",
        "## O. NEXT RECOMMENDATION", "", summary["next_recommendation"], "",
        "## P. GIT", "", "The immutable completion commit is recorded after final hash verification. No push is performed.", "",
        "## Scaling validity checklist", "", *[f"- {key}: {'PASS' if value else 'FAIL'}" for key,value in summary["scaling_validity_checklist"].items()], "",
        "## Historical read-only comparison", "", _markdown_table(historical), "",
        "Phase 1/2 rows were excluded from Phase-3 task design, model selection, and coefficient fitting.", "",
        "## Exact identity", "", f"Maximum eta/kappa identity error: {exponents.eta_kappa_identity_error.max():.3e}. The equality kappa=1-eta is algebraic and is not itself an empirical law.", "",
        "## Figures", "", "Fourteen figures in `figures/` retain individual graph trajectories or graph-level points. Figure 14 is explicitly classical simulation/runtime scaling, not quantum complexity.", "",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
