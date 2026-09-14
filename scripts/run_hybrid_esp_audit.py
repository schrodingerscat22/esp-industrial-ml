"""Run the H0--H2 hybrid ESP pilot without storing industrial predictions or models."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import numpy as np
import pandas as pd
import psutil
import scipy
import sklearn
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.hybrid_esp import CORE_FIT_MAX_ROWS, build_hybrid_frame, fit_core
from src.hybrid_esp_validation import Support, d1_split, metrics

SOURCE = ROOT / "data/processed/audit_v3/df_model_clean_v1.parquet"
OUTPUT = ROOT / "data/processed/hybrid_esp_h2_d1_v1"
SEED = 42


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(part)
    return hasher.hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, default=str), encoding="utf-8")
    temporary.replace(path)


def resource() -> dict[str, float]:
    process = psutil.Process()
    return {"process_rss_GiB": process.memory_info().rss / 2**30,
            "available_RAM_GiB": psutil.virtual_memory().available / 2**30,
            "disk_free_GiB": psutil.disk_usage(str(ROOT)).free / 2**30}


def model_tree() -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(loss="squared_error", max_iter=150, max_leaf_nodes=15,
        min_samples_leaf=50, learning_rate=.05, l2_regularization=1., early_stopping=False,
        random_state=SEED)


def select(frame: pd.DataFrame, mask: pd.Series, columns: list[str]) -> pd.DataFrame:
    needed = list(dict.fromkeys(columns + ["flow_proxy", "dust_mg_Nm3"]))
    return frame.loc[mask, needed].replace([np.inf, -np.inf], np.nan).dropna()


def metrics_by_day(y: pd.Series, prediction: np.ndarray) -> list[dict[str, object]]:
    result = []
    values = pd.DataFrame({"target": y, "prediction": prediction}, index=y.index)
    for day, group in values.groupby(values.index.normalize()):
        result.append({"date": str(day.date()), **metrics(group.target, group.prediction)})
    return result


def paired_daily_bootstrap(daily: pd.DataFrame) -> dict[str, object]:
    pair = daily.pivot(index="date", columns="model", values="MAE")
    if not {"M1_tree_common_features", "M3_core_plus_oof_correction"}.issubset(pair):
        return {"n_dates": 0}
    delta = (pair["M1_tree_common_features"] - pair["M3_core_plus_oof_correction"]).dropna().to_numpy()
    rng = np.random.default_rng(SEED)
    boot = np.array([np.mean(rng.choice(delta, size=len(delta), replace=True)) for _ in range(1000)]) if len(delta) else np.array([])
    return {"definition": "positive means M3 has lower daily MAE than M1", "n_dates": int(len(delta)),
            "mean_delta_MAE_mg_Nm3": float(delta.mean()) if len(delta) else None,
            "median_delta_MAE_mg_Nm3": float(np.median(delta)) if len(delta) else None,
            "bootstrap_day_CI95_low": float(np.quantile(boot, .025)) if len(boot) else None,
            "bootstrap_day_CI95_high": float(np.quantile(boot, .975)) if len(boot) else None}


def oof_core_residuals(frame: pd.DataFrame, fit_mask: pd.Series, schema: dict[str, list[str]]) -> pd.DataFrame:
    """Only predictions from cores that precede the evaluated date enter correction training."""
    data = frame.loc[fit_mask].copy()
    dates = pd.DatetimeIndex(data.index.normalize().unique()).sort_values()
    parts = []
    for day in dates[3:]:
        prior = data.index.normalize() < day
        current = data.index.normalize() == day
        prior_frame = select(data, prior, schema["common"])
        current_frame = select(data, current, schema["common"])
        if len(prior_frame) < 100 or not len(current_frame):
            continue
        core = fit_core(prior_frame, schema["process"], schema["rapping"], schema["voltage"])
        residual = np.log1p(current_frame.dust_mg_Nm3.to_numpy()) - np.log1p(core.predict(current_frame))
        part = current_frame[schema["common"]].copy(); part["residual"] = residual
        parts.append(part)
    if not parts:
        raise ValueError("No chronological out-of-fold core residuals")
    return pd.concat(parts).sort_index()


def run_pilot(frame: pd.DataFrame, schema: dict[str, list[str]], smoke: bool) -> tuple[pd.DataFrame, dict[str, object], pd.DataFrame]:
    fit_mask, calibration_mask, evaluation_mask = d1_split(frame)
    if smoke:
        # Take a chronological subset of D1 while retaining all prior fit/calibration separation.
        candidates = frame.index[evaluation_mask]
        evaluation_mask &= frame.index <= candidates[min(len(candidates) - 1, 359)]
    fit = select(frame, fit_mask, schema["common"])
    calibration = select(frame, calibration_mask, schema["common"])
    evaluation = select(frame, evaluation_mask, schema["common"])
    if psutil.virtual_memory().available < 2**30:
        raise RuntimeError("Less than 1 GiB RAM available before model fitting")
    if min(len(fit), len(calibration), len(evaluation)) < 100:
        raise ValueError("Insufficient complete origins in D1 split")

    base = make_pipeline(StandardScaler(), Ridge(alpha=10)).fit(fit[schema["baseline"]], np.log1p(fit.dust_mg_Nm3))
    m1 = model_tree().fit(fit[schema["common"]], np.log1p(fit.dust_mg_Nm3))
    core = fit_core(fit, schema["process"], schema["rapping"], schema["voltage"])
    oof = oof_core_residuals(frame, fit_mask, schema)
    correction = model_tree().fit(oof[schema["common"]], oof.residual)
    support = Support(schema["common"]).fit(fit)
    status = support.classify(evaluation)
    core_prediction = core.predict(evaluation)
    weight = np.where(status.eq("supported"), 1., np.where(status.eq("marginal"), .5, 0.))
    m3_prediction = np.maximum(np.expm1(np.log1p(core_prediction) + weight * correction.predict(evaluation[schema["common"]])), 0.)
    prediction = {
        "M0_ridge_process_rapping": np.maximum(np.expm1(base.predict(evaluation[schema["baseline"]])), 0.),
        "M1_tree_common_features": np.maximum(np.expm1(m1.predict(evaluation[schema["common"]])), 0.),
        "M2_constrained_core": core_prediction,
        "M3_core_plus_oof_correction": m3_prediction,
        "P60_dust_history_baseline": frame.loc[evaluation.index, "dust_lag_60s"].to_numpy(),
    }
    rows, days = [], []
    for name, values in prediction.items():
        row = {"model": name, **metrics(evaluation.dust_mg_Nm3, values),
               "supported_pct": float(status.eq("supported").mean() * 100),
               "marginal_pct": float(status.eq("marginal").mean() * 100),
               "outside_pct": float(status.eq("outside").mean() * 100)}
        rows.append(row)
        for daily in metrics_by_day(evaluation.dust_mg_Nm3, values):
            days.append({"model": name, **daily})
    calibration_core = core.predict(calibration)
    residual_quantile = float(np.quantile(abs(calibration.dust_mg_Nm3 - calibration_core), .9))
    details = {
        "fold": "D1", "smoke": smoke, "fit_origins": len(fit), "calibration_origins": len(calibration),
        "evaluation_origins": len(evaluation), "fit_dates": int(fit.index.normalize().nunique()),
        "calibration_dates": int(calibration.index.normalize().nunique()), "evaluation_dates": int(evaluation.index.normalize().nunique()),
        "oof_residual_origins": len(oof), "core": {"success": core.success, "cost": core.cost,
        "nfev": core.nfev, "at_bound_count": core.at_bound_count, "fit_rows": core.fit_rows},
        "core_calibration_abs_residual_p90_mg_Nm3": residual_quantile,
        "support": {"d95": support.d95, "reference_n": len(support.model._fit_X)},
    }
    daily_frame = pd.DataFrame(days)
    details["M3_minus_M1_daily_MAE"] = paired_daily_bootstrap(daily_frame)
    return pd.DataFrame(rows), details, daily_frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("preflight", "synthetic", "pilot", "all"), default="all")
    parser.add_argument("--fold", choices=("D1",), default="D1")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or (ROOT / "data/processed" / ("hybrid_esp_h2_d1_smoke_v1" if args.smoke else OUTPUT.name))
    output = output if output.is_absolute() else ROOT / output
    output.mkdir(parents=True, exist_ok=True)
    config = {"input": str(SOURCE.relative_to(ROOT)), "input_sha256": sha256(SOURCE), "stage": args.stage,
              "fold": args.fold, "smoke": args.smoke, "seed": SEED, "kernel_taus_seconds": [30, 120, 300],
              "max_core_nfev": 200, "core_fit_max_rows": CORE_FIT_MAX_ROWS,
              "tree": {"max_iter": 150, "max_leaf_nodes": 15, "min_samples_leaf": 50,
              "learning_rate": .05, "l2_regularization": 1.}, "max_threads": 2}
    prior = output / "config.json"
    if prior.exists() and json.loads(prior.read_text(encoding="utf-8")) != config:
        raise ValueError("Output directory has a different configuration; choose a new directory")
    write_json(prior, config)
    started = time.perf_counter(); before = sha256(SOURCE)
    raw = pd.read_parquet(SOURCE)
    comparison_source = ROOT / "data/processed/dataset_clean.parquet"
    comparison = None
    if comparison_source.exists():
        metadata = pq.ParquetFile(comparison_source).metadata
        comparison = {"path": str(comparison_source.relative_to(ROOT)), "rows": metadata.num_rows,
                      "columns": len(pq.ParquetFile(comparison_source).schema.names), "sha256": sha256(comparison_source)}
    frame, schema = build_hybrid_frame(raw)
    preflight = {"input_sha256_before": before, "rows": len(raw), "columns": len(raw.columns),
        "frame_valid_origins": int(frame.valid_origin.sum()), "features_common": len(schema["common"]),
        "comparison_source": comparison, "git_head": os.popen("git rev-parse HEAD").read().strip(),
        "resource_after_features": resource(), "python": platform.python_version(), "numpy": np.__version__,
        "pandas": pd.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__}
    write_json(output / "preflight.json", preflight)
    if args.stage == "preflight":
        return
    # Synthetic validity is primarily enforced by tests; persist only scalar aggregate identities.
    synthetic = {"c_in_k_identity": bool(np.isclose(1000*np.exp(-4.6), 2000*np.exp(-(4.6+np.log(2))))),
                 "scope": "dimensionless synthetic identity; no industrial prediction"}
    write_json(output / "synthetic_summary.json", synthetic)
    if args.stage == "synthetic":
        return
    model_metrics, details, daily = run_pilot(frame, schema, args.smoke)
    model_metrics.to_csv(output / "model_metrics.csv", index=False)
    daily.to_csv(output / "daily_metrics.csv", index=False)
    after = sha256(SOURCE)
    report = {"completed": True, "input_sha256_before": before, "input_sha256_after": after,
              "input_unchanged": before == after, "elapsed_seconds": time.perf_counter() - started,
              "resource_final": resource(), "pilot": details,
              "artefacts": ["config.json", "preflight.json", "synthetic_summary.json", "model_metrics.csv", "daily_metrics.csv"]}
    write_json(output / "report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
