"""Frozen Phase-3 scaling models, clustered summaries, and holdout prediction."""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy

from .io import PROJECT_ROOT, atomic_write_csv, load_config, write_json
from .phase2_statistics import holm_adjust
from .phase3_tasks import CONFIG_PATH, RESULT_ROOT, sha256_file


MODEL_IDS = ("M1", "M2", "M3", "M4")
MODEL_FORMULAS = {
    "M1": "Yc = -eta * Dc",
    "M2": "Yc = -[eta_0 + eta_m * (m - 15)] * Dc",
    "M3": "Yc = -eta * Dc + q * [Dc^2 - mean_g(Dc^2)]",
    "M4": "Yc = -[eta_0 + eta_m * (m - 15)] * Dc + q * [Dc^2 - mean_g(Dc^2)]",
}
COEFFICIENT_NAMES = {
    "M1": ("eta",),
    "M2": ("eta_0", "eta_m"),
    "M3": ("eta", "q"),
    "M4": ("eta_0", "eta_m", "q"),
}
FREEZE_PATH = RESULT_ROOT / "SCALING_MODEL_FREEZE.json"
FREEZE_HASH_PATH = RESULT_ROOT / "SCALING_MODEL_FREEZE.sha256.json"
MODEL_SELECTION_PATH = RESULT_ROOT / "development_model_selection.csv"
EXPONENT_PATH = RESULT_ROOT / "base_graph_exponents.csv"


@dataclass(frozen=True)
class LinearFit:
    coefficients: np.ndarray
    covariance: np.ndarray
    predictions: np.ndarray
    residuals: np.ndarray
    rmse: float
    mae: float
    aicc: float


def prepare_scaling_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Create log response and exact within-graph centered terms without epsilon."""
    required = {"base_graph_id", "size_m", "objective_id", "p_feas", "dilution_score"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"scaling frame missing fields: {sorted(missing)}")
    output = frame.copy()
    output["zero_p_feas"] = output.p_feas.eq(0.0)
    output["Y"] = np.nan
    positive = output.p_feas > 0.0
    output.loc[positive, "Y"] = np.log10(output.loc[positive, "p_feas"])
    keys = ["base_graph_id", "objective_id"]
    output["Yc"] = output["Y"] - output.groupby(keys)["Y"].transform("mean")
    output["Dc"] = output["dilution_score"] - output.groupby(keys)[
        "dilution_score"
    ].transform("mean")
    output["Q"] = output["Dc"] ** 2
    output["Qc"] = output["Q"] - output.groupby(keys)["Q"].transform("mean")
    return output


def model_matrix(frame: pd.DataFrame, model_id: str) -> np.ndarray:
    if model_id not in MODEL_IDS:
        raise ValueError(f"unknown candidate model {model_id}")
    dc = frame.Dc.to_numpy(dtype=float)
    size = frame.size_m.to_numpy(dtype=float)
    qc = frame.Qc.to_numpy(dtype=float)
    columns = {
        "M1": [-dc],
        "M2": [-dc, -(size - 15.0) * dc],
        "M3": [-dc, qc],
        "M4": [-dc, -(size - 15.0) * dc, qc],
    }[model_id]
    return np.column_stack(columns)


def fit_candidate(frame: pd.DataFrame, model_id: str) -> LinearFit:
    valid = frame[np.isfinite(frame.Yc) & np.isfinite(frame.Dc) & np.isfinite(frame.Qc)]
    x = model_matrix(valid, model_id)
    y = valid.Yc.to_numpy(dtype=float)
    if len(y) <= x.shape[1] + 1:
        raise ValueError("insufficient centered responses for candidate model")
    coefficients, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    predictions = x @ coefficients
    residuals = y - predictions
    sse = float(np.dot(residuals, residuals))
    n, k = len(y), x.shape[1]
    sigma2 = sse / max(1, n - k)
    covariance = sigma2 * np.linalg.pinv(x.T @ x)
    rmse = math.sqrt(sse / n)
    mae = float(np.mean(np.abs(residuals)))
    safe_sse = max(sse, np.finfo(float).tiny)
    aic = n * math.log(safe_sse / n) + 2 * k
    aicc = aic + (2 * k * (k + 1)) / (n - k - 1)
    return LinearFit(coefficients, covariance, predictions, residuals, rmse, mae, aicc)


def leave_one_base_graph_out_cv(frame: pd.DataFrame, model_id: str) -> dict[str, float]:
    valid = frame[np.isfinite(frame.Yc)].copy()
    folds: list[dict[str, float]] = []
    all_residuals: list[np.ndarray] = []
    for base_graph_id in sorted(valid.base_graph_id.unique()):
        train = valid[valid.base_graph_id != base_graph_id]
        test = valid[valid.base_graph_id == base_graph_id]
        fit = fit_candidate(train, model_id)
        residuals = test.Yc.to_numpy(dtype=float) - model_matrix(test, model_id) @ fit.coefficients
        all_residuals.append(residuals)
        folds.append(
            {
                "rmse": float(np.sqrt(np.mean(residuals**2))),
                "mae": float(np.mean(np.abs(residuals))),
            }
        )
    residuals = np.concatenate(all_residuals)
    fold_rmse = np.asarray([fold["rmse"] for fold in folds])
    full = fit_candidate(valid, model_id)
    return {
        "cv_rmse": float(np.sqrt(np.mean(residuals**2))),
        "cv_mae": float(np.mean(np.abs(residuals))),
        "cv_rmse_se": float(np.std(fold_rmse, ddof=1) / math.sqrt(len(fold_rmse))),
        "aicc": full.aicc,
        "n_rows": int(len(valid)),
        "n_base_graphs": int(valid.base_graph_id.nunique()),
    }


def select_model_one_standard_error(metrics: pd.DataFrame) -> str:
    """Use the minimum model's SE and frozen complexity order."""
    if set(metrics.model_id) != set(MODEL_IDS):
        raise ValueError("all four frozen candidate models are required")
    best = metrics.sort_values(["cv_rmse", "model_id"], kind="stable").iloc[0]
    threshold = float(best.cv_rmse + best.cv_rmse_se)
    eligible = set(metrics.loc[metrics.cv_rmse <= threshold + 1e-15, "model_id"])
    return next(model_id for model_id in MODEL_IDS if model_id in eligible)


def base_graph_exponents(
    frame: pd.DataFrame,
    *,
    minimum_levels: int = 5,
    optimizer_flags: dict[tuple[str, str], bool] | None = None,
) -> pd.DataFrame:
    prepared = prepare_scaling_rows(frame)
    rows: list[dict[str, Any]] = []
    optimizer_flags = optimizer_flags or {}
    for (base, objective), group in prepared.groupby(
        ["base_graph_id", "objective_id"], sort=True
    ):
        valid = group[np.isfinite(group.Y)].sort_values("dilution_score")
        if len(valid) < minimum_levels:
            continue
        d = valid.dilution_score.to_numpy(dtype=float)
        y = valid.Y.to_numpy(dtype=float)
        design = np.column_stack([np.ones(len(d)), -d])
        coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
        intercept, eta = coefficients
        prediction = design @ coefficients
        residual = y - prediction
        sse = float(np.dot(residual, residual))
        centered_sse = float(np.dot(y - y.mean(), y - y.mean()))
        sigma2 = sse / max(1, len(y) - 2)
        covariance = sigma2 * np.linalg.pinv(design.T @ design)
        eta_se = math.sqrt(max(0.0, float(covariance[1, 1])))
        g_feas = y + d
        kappa_design = np.column_stack([np.ones(len(d)), d])
        kappa = float(np.linalg.lstsq(kappa_design, g_feas, rcond=None)[0][1])
        identity_error = abs(kappa - (1.0 - float(eta)))
        rows.append(
            {
                "base_graph_id": base,
                "split": str(valid.split.iloc[0]),
                "size_m": int(valid.size_m.iloc[0]),
                "objective": objective,
                "n_levels": len(valid),
                "eta": float(eta),
                "eta_se": eta_se,
                "kappa": kappa,
                "eta_kappa_identity_error": identity_error,
                "intercept": float(intercept),
                "R2": 1.0 - sse / centered_sse if centered_sse > 0 else math.nan,
                "RMSE": math.sqrt(sse / len(y)),
                "D_min": float(d.min()),
                "D_max": float(d.max()),
                "P_feas_min": float(valid.p_feas.min()),
                "P_feas_max": float(valid.p_feas.max()),
                "optimizer_adequacy_flag": bool(optimizer_flags.get((base, objective), False)),
                "resource_censored": bool(valid.resource_censored.astype(bool).any())
                if "resource_censored" in valid
                else False,
            }
        )
    output = pd.DataFrame(rows)
    tolerance = float(load_config(CONFIG_PATH)["model_selection"]["eta_kappa_tolerance"])
    if len(output) and output.eta_kappa_identity_error.max() > tolerance:
        raise RuntimeError("eta/kappa identity failed")
    return output


def select_development_models(development_p3: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Select models using development graphs only; never accepts holdout rows."""
    if set(development_p3.split.unique()) != {"development"}:
        raise RuntimeError("model selection may access development rows only")
    prepared = prepare_scaling_rows(development_p3)
    selection_rows: list[dict[str, Any]] = []
    frozen: dict[str, Any] = {}
    for objective in ("O0", "O2", "O3"):
        subset = prepared[prepared.objective_id == objective]
        metrics_rows = []
        for model_id in MODEL_IDS:
            metrics = leave_one_base_graph_out_cv(subset, model_id)
            metrics_rows.append({"objective": objective, "model_id": model_id, **metrics})
        metrics_frame = pd.DataFrame(metrics_rows)
        selected = select_model_one_standard_error(metrics_frame)
        best = metrics_frame.sort_values(["cv_rmse", "model_id"]).iloc[0]
        threshold = float(best.cv_rmse + best.cv_rmse_se)
        metrics_frame["one_se_threshold"] = threshold
        metrics_frame["within_one_se"] = metrics_frame.cv_rmse <= threshold + 1e-15
        metrics_frame["selected"] = metrics_frame.model_id.eq(selected)
        selection_rows.extend(metrics_frame.to_dict(orient="records"))
        full_fit = fit_candidate(subset, selected)
        names = COEFFICIENT_NAMES[selected]
        frozen[objective] = {
            "selected_model_id": selected,
            "formula": MODEL_FORMULAS[selected],
            "coefficient_names": list(names),
            "development_coefficients": dict(zip(names, full_fit.coefficients.tolist())),
            "development_covariance": full_fit.covariance.tolist(),
            "development_standard_errors": dict(
                zip(names, np.sqrt(np.maximum(0.0, np.diag(full_fit.covariance))).tolist())
            ),
            "model_selection_decision": (
                f"{selected} is the simplest model within one standard error of "
                f"minimum CV RMSE {best.cv_rmse:.12g}"
            ),
            "cv_metrics": metrics_frame.to_dict(orient="records"),
        }
    return pd.DataFrame(selection_rows), frozen


def freeze_development_models(development_p3: pd.DataFrame) -> dict[str, Any]:
    if FREEZE_PATH.exists() or FREEZE_HASH_PATH.exists():
        return load_frozen_models()
    metrics, objective_models = select_development_models(development_p3)
    atomic_write_csv(MODEL_SELECTION_PATH, metrics)
    config = load_config(CONFIG_PATH)
    payload = {
        "schema_version": "phase3_scaling_v1.model_freeze.v1",
        "evidence_identity": config["evidence_identity"],
        "selection_rule": config["model_selection"]["selection_rule"],
        "complexity_order": list(MODEL_IDS),
        "training_base_graph_ids": sorted(development_p3.base_graph_id.unique().tolist()),
        "training_task_ids": sorted(development_p3.task_id.unique().tolist()),
        "training_row_count": int(len(development_p3)),
        "software_versions": {
            "python": sys.version.replace("\n", " "),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "objectives": objective_models,
        "holdout_qaoa_inspected": False,
    }
    write_json(FREEZE_PATH, payload)
    digest = sha256_file(FREEZE_PATH)
    write_json(
        FREEZE_HASH_PATH,
        {"scaling_model_freeze_sha256": digest, "path": str(FREEZE_PATH.relative_to(PROJECT_ROOT))},
    )
    return payload


def load_frozen_models() -> dict[str, Any]:
    if not FREEZE_PATH.exists() or not FREEZE_HASH_PATH.exists():
        raise RuntimeError("holdout access denied: scaling model has not been frozen")
    identity = json.loads(FREEZE_HASH_PATH.read_text(encoding="utf-8"))
    if sha256_file(FREEZE_PATH) != identity["scaling_model_freeze_sha256"]:
        raise RuntimeError("scaling-model freeze artifact hash mismatch")
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def predict_centered(frame: pd.DataFrame, model: dict[str, Any]) -> np.ndarray:
    prepared = prepare_scaling_rows(frame)
    model_id = model["selected_model_id"]
    coefficients = np.asarray(
        [model["development_coefficients"][name] for name in COEFFICIENT_NAMES[model_id]],
        dtype=float,
    )
    return model_matrix(prepared, model_id) @ coefficients


def _effective_predicted_eta(prepared_graph: pd.DataFrame, predictions: np.ndarray) -> float:
    d = prepared_graph.dilution_score.to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(d)), -d])
    return float(np.linalg.lstsq(design, predictions, rcond=None)[0][1])


def validate_holdout_predictions(holdout_p3: pd.DataFrame) -> pd.DataFrame:
    frozen = load_frozen_models()
    if set(holdout_p3.split.unique()) not in (
        {"interpolation_holdout"}, {"extrapolation_holdout"}
    ):
        raise RuntimeError("validation accepts exactly one untouched holdout split")
    prepared = prepare_scaling_rows(holdout_p3)
    exponent = base_graph_exponents(holdout_p3).set_index(["base_graph_id", "objective"])
    rows: list[dict[str, Any]] = []
    for (base, objective), group in prepared.groupby(["base_graph_id", "objective_id"]):
        group = group[np.isfinite(group.Yc)].copy()
        if len(group) < 5:
            continue
        model = frozen["objectives"][objective]
        selected_prediction = predict_centered(group, model)
        uniform_prediction = -group.Dc.to_numpy(dtype=float)
        flat_prediction = np.zeros(len(group), dtype=float)
        actual = group.Yc.to_numpy(dtype=float)
        observed_eta = float(exponent.loc[(base, objective), "eta"])
        predicted_eta = _effective_predicted_eta(group, selected_prediction)
        for predictor, prediction in (
            ("SELECTED_FROZEN", selected_prediction),
            ("B_UNIFORM_ETA_1", uniform_prediction),
            ("B_FLAT_ETA_0", flat_prediction),
        ):
            residual = actual - prediction
            rows.append(
                {
                    "split": str(group.split.iloc[0]),
                    "base_graph_id": base,
                    "size_m": int(group.size_m.iloc[0]),
                    "objective": objective,
                    "predictor": predictor,
                    "selected_model_id": model["selected_model_id"],
                    "n_levels": len(group),
                    "observed_eta": observed_eta,
                    "predicted_eta": predicted_eta if predictor == "SELECTED_FROZEN" else (1.0 if predictor == "B_UNIFORM_ETA_1" else 0.0),
                    "eta_prediction_error": observed_eta - (predicted_eta if predictor == "SELECTED_FROZEN" else (1.0 if predictor == "B_UNIFORM_ETA_1" else 0.0)),
                    "absolute_eta_error": abs(observed_eta - (predicted_eta if predictor == "SELECTED_FROZEN" else (1.0 if predictor == "B_UNIFORM_ETA_1" else 0.0))),
                    "centered_response_RMSE": float(np.sqrt(np.mean(residual**2))),
                    "centered_response_MAE": float(np.mean(np.abs(residual))),
                    "frozen_prediction_no_refit": True,
                }
            )
    return pd.DataFrame(rows)


def bootstrap_summary(values: np.ndarray, *, resamples: int, seed: int) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {key: math.nan for key in ("mean", "median", "q1", "q3", "IQR", "ci_lower", "ci_upper", "min", "max")} | {"n": 0}
    rng = np.random.default_rng(seed)
    draws = rng.choice(values, size=(resamples, len(values)), replace=True).mean(axis=1)
    return {
        "n": len(values),
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "q1": float(np.quantile(values, 0.25)),
        "q3": float(np.quantile(values, 0.75)),
        "IQR": float(np.quantile(values, 0.75) - np.quantile(values, 0.25)),
        "ci_lower": float(np.quantile(draws, 0.025)),
        "ci_upper": float(np.quantile(draws, 0.975)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def exponent_contrasts(exponents: pd.DataFrame) -> pd.DataFrame:
    wide = exponents.pivot(index=["base_graph_id", "split", "size_m"], columns="objective", values="eta").reset_index()
    wide["Delta_eta_CVAR_MEAN"] = wide["O3"] - wide["O0"]
    wide["Delta_eta_CVAR_CAPACITY"] = wide["O3"] - wide["O2"]
    wide["S_H3_closeness_contrast"] = abs(wide["O3"] - wide["O2"]) - abs(wide["O0"] - wide["O2"])
    return wide


def _bootstrap_one_sided_p(
    values: np.ndarray, *, alternative: str, resamples: int, seed: int
) -> float:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    means = rng.choice(values, size=(resamples, len(values)), replace=True).mean(axis=1)
    if alternative == "greater":
        extreme = np.count_nonzero(means <= 0.0)
    elif alternative == "less":
        extreme = np.count_nonzero(means >= 0.0)
    else:
        raise ValueError("alternative must be greater or less")
    return float((extreme + 1) / (resamples + 1))


def confirmatory_scaling_statistics(exponents: pd.DataFrame) -> dict[str, Any]:
    config = load_config(CONFIG_PATH)
    settings = config["confirmatory_hypotheses"]
    target = exponents[exponents.split == "extrapolation_holdout"]
    wide = exponent_contrasts(target)
    o0 = wide.O0.to_numpy(dtype=float)
    delta = wide.Delta_eta_CVAR_MEAN.to_numpy(dtype=float)
    closeness = wide.S_H3_closeness_contrast.to_numpy(dtype=float)
    n_boot = int(settings["bootstrap_resamples"])
    seed = int(settings["bootstrap_seed"])
    raw = {
        "S-H1": _bootstrap_one_sided_p(o0, alternative="greater", resamples=n_boot, seed=seed + 1),
        "S-H2": _bootstrap_one_sided_p(delta, alternative="less", resamples=n_boot, seed=seed + 2),
        "S-H3": _bootstrap_one_sided_p(closeness, alternative="less", resamples=n_boot, seed=seed + 3),
    }
    adjusted = holm_adjust(raw)
    return {
        "analysis_unit": "base_graph_id",
        "split": "extrapolation_holdout",
        "base_graph_count": len(wide),
        "multiplicity": "Holm three-hypothesis family",
        "family_alpha": float(settings["family_alpha"]),
        "hypotheses": {
            "S-H1": {"estimand": "mean eta_O0", "effect": float(o0.mean()), "raw_p": raw["S-H1"], "holm_adjusted_p": adjusted["S-H1"], "pass": bool(o0.mean() > 0 and adjusted["S-H1"] < settings["family_alpha"])},
            "S-H2": {"estimand": "mean eta_O3-eta_O0", "effect": float(delta.mean()), "raw_p": raw["S-H2"], "holm_adjusted_p": adjusted["S-H2"], "pass": bool(delta.mean() < 0 and adjusted["S-H2"] < settings["family_alpha"])},
            "S-H3": {"estimand": "mean absolute-distance closeness contrast", "effect": float(closeness.mean()), "raw_p": raw["S-H3"], "holm_adjusted_p": adjusted["S-H3"], "pass": bool(closeness.mean() < 0 and adjusted["S-H3"] < settings["family_alpha"])},
        },
        "bootstrap_method": "grouped resampling of independent base-graph exponents",
        "bootstrap_resamples": n_boot,
        "bootstrap_seed": seed,
    }
