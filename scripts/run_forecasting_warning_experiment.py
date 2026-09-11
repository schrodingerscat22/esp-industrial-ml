"""Run F2 warning models for dust exceedances without operational alarm tuning."""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from src.forecast_features import (
    ANALYTIC_THRESHOLDS,
    HORIZON_SECONDS,
    TARGET,
    clean_forecast_data,
    delay_to_samples,
    feature_family_counts,
    fit_forecast_schema,
    future_event_target,
    history_features,
    process_features,
)
from src.forecast_validation import (
    DEVELOPMENT_FOLDS,
    calibration_table,
    forecast_origins,
    observed_hours,
    warning_metrics,
)
from src.time_analysis import coverage

OUT = ROOT / "data" / "processed" / "forecast_f2_v1"
MODEL_NAMES = ("persistence", "xgboost_p", "xgboost_ph")
XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": 42,
    "n_jobs": 1,
    "tree_method": "hist",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, content: object) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def save_model(model: XGBClassifier, features: pd.DataFrame, fold: str, horizon: int, threshold: float, name: str) -> None:
    model_dir = OUT / "models"
    model_dir.mkdir(exist_ok=True)
    stem = f"{fold}_h{horizon}s_gt{threshold:g}_{name}"
    model.save_model(model_dir / f"{stem}.ubj")
    pd.DataFrame({"feature": features.columns, "importance": model.feature_importances_}).sort_values(
        "importance", ascending=False
    ).to_csv(model_dir / f"{stem}_importance.csv", index=False)


def main() -> None:
    global OUT
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", choices=[fold.name for fold in DEVELOPMENT_FOLDS], action="append")
    parser.add_argument("--horizon-seconds", choices=HORIZON_SECONDS, type=int, action="append")
    parser.add_argument("--threshold", choices=ANALYTIC_THRESHOLDS, type=float, action="append")
    parser.add_argument("--measurement-delay-seconds", type=int, default=0)
    parser.add_argument("--process-availability-delay-seconds", type=int, default=0)
    parser.add_argument("--include-legacy", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    delay_to_samples(args.measurement_delay_seconds)
    delay_to_samples(args.process_availability_delay_seconds)
    if args.output_dir is not None:
        OUT = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    OUT.mkdir(exist_ok=True)

    input_paths = [ROOT / "data" / "processed" / "dataset_clean.parquet", ROOT / "data" / "processed" / "tag_classification_v1.xlsx"]
    source_paths = [Path(__file__), ROOT / "src" / "forecast_features.py", ROOT / "src" / "forecast_validation.py", ROOT / "src" / "time_analysis.py"]
    input_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in input_paths}
    classification = pd.read_excel(input_paths[1])
    input_cols = classification.loc[classification["role"].eq("input"), "tag"].tolist()
    raw = pd.read_parquet(input_paths[0])
    source = clean_forecast_data(raw, input_cols)
    history = history_features(source, args.measurement_delay_seconds)
    history_required = history.columns[~history.columns.str.contains("minutes_since_gt")]
    history_valid = history[history_required].notna().all(axis=1)
    selected_folds = [
        fold
        for fold in DEVELOPMENT_FOLDS
        if (args.include_legacy or fold.name != "legacy_evaluation")
        and (args.fold is None or fold.name in args.fold)
    ]
    selected_horizons = tuple(args.horizon_seconds or HORIZON_SECONDS)
    selected_thresholds = tuple(args.threshold or ANALYTIC_THRESHOLDS)
    design = {
        "status": "written_before_fit",
        "contract": "F2 event=max(y(t+10s),...,y(t+h))>threshold; incomplete future window=unknown",
        "availability_unverified": True,
        "measurement_delay_seconds": args.measurement_delay_seconds,
        "process_availability_delay_seconds": args.process_availability_delay_seconds,
        "horizons_seconds": selected_horizons,
        "analytic_thresholds": selected_thresholds,
        "operational_alarm_threshold": None,
        "folds": [fold.__dict__ for fold in selected_folds],
        "xgboost_parameters": XGB_PARAMS,
        "input_hashes": input_hashes,
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in source_paths},
    }
    write_json(OUT / "design.json", design)
    report: dict[str, object] = {
        "status": "running", "design": design, "raw_rows": len(raw), "clean_rows": len(source),
        "coverage": coverage(source), "history_feature_families": feature_family_counts(history.columns), "runs": [],
        "versions": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "xgboost", "scikit-learn", "pyarrow")},
    }
    metric_rows: list[dict[str, object]] = []
    calibration_rows: list[dict[str, object]] = []

    for fold in selected_folds:
        print(f"{fold.name}: building process features", flush=True)
        started = time.monotonic()
        fold_source = source if fold.evaluation_end is None else source.loc[source.index < fold.evaluation_end]
        schema = fit_forecast_schema(fold_source.loc[fold_source.index < fold.evaluation_start], classification)
        process = process_features(
            fold_source, schema, availability_delay_seconds=args.process_availability_delay_seconds
        )
        process_valid = process[schema["inputs"]].notna().all(axis=1)
        valid = (history_valid & process_valid).reindex(fold_source.index)
        fold_summary: dict[str, object] = {
            "fold": fold.name, "evaluation_start": str(fold.evaluation_start), "evaluation_end_exclusive": str(fold.evaluation_end),
            "observed_evaluation_hours": observed_hours(fold_source.loc[fold_source.index >= fold.evaluation_start]),
            "schema": schema, "process_feature_families": feature_family_counts(process.columns), "runs": [],
        }
        for horizon in selected_horizons:
            for threshold in selected_thresholds:
                label = future_event_target(fold_source, horizon, threshold)
                train, evaluate, diagnostics = forecast_origins(fold_source.index, valid, label, fold, horizon)
                if not len(train) or not len(evaluate):
                    raise RuntimeError(f"{fold.name}, h={horizon}, threshold={threshold}: empty origin set")
                y_train = label.loc[train].astype(int)
                y_eval = label.loc[evaluate].astype(int)
                prediction = pd.DataFrame({"event": y_eval}, index=evaluate)
                prediction["persistence"] = history.loc[evaluate, "dust_available"].gt(threshold).astype(float)
                feature_sets = {"xgboost_p": process, "xgboost_ph": pd.concat([process, history], axis=1)}
                for name, features in feature_sets.items():
                    print(f"{fold.name}, h={horizon}s, gt={threshold:g}: fitting {name} ({len(train)} train / {len(evaluate)} evaluation)", flush=True)
                    model = XGBClassifier(**XGB_PARAMS)
                    model.fit(features.loc[train], y_train)
                    prediction[name] = model.predict_proba(features.loc[evaluate])[:, 1]
                    save_model(model, features, fold.name, horizon, threshold, name)
                for name in MODEL_NAMES:
                    row = {"fold": fold.name, "horizon_seconds": horizon, "horizon_minutes": horizon / 60, "threshold": threshold, "model": name}
                    row.update(warning_metrics(y_eval, prediction[name]))
                    metric_rows.append(row)
                    calibration = calibration_table(y_eval, prediction[name])
                    calibration.insert(0, "model", name)
                    calibration.insert(0, "threshold", threshold)
                    calibration.insert(0, "horizon_seconds", horizon)
                    calibration.insert(0, "fold", fold.name)
                    calibration_rows.extend(calibration.to_dict("records"))
                prediction.to_parquet(OUT / f"predictions_{fold.name}_h{horizon}s_gt{threshold:g}.parquet")
                fold_summary["runs"].append({
                    "horizon_seconds": horizon, "threshold": threshold, "train_origins": len(train), "evaluation_origins": len(evaluate),
                    "train_positive_rate": float(y_train.mean()), "evaluation_positive_rate": float(y_eval.mean()), "diagnostics": diagnostics,
                })
                del feature_sets, prediction
                gc.collect()
                pd.DataFrame(metric_rows).to_csv(OUT / "metrics.csv", index=False)
                pd.DataFrame(calibration_rows).to_csv(OUT / "calibration.csv", index=False)
        fold_summary["seconds"] = time.monotonic() - started
        report["runs"].append(fold_summary)
        write_json(OUT / "report.json", report)
        del process
        gc.collect()

    report["metrics_rows"] = len(metric_rows)
    report["inputs_unchanged"] = input_hashes == {str(path.relative_to(ROOT)): sha256(path) for path in input_paths}
    if not report["inputs_unchanged"]:
        raise RuntimeError("Input-integrity check failed")
    report["status"] = "complete"
    write_json(OUT / "report.json", report)
    print(pd.DataFrame(metric_rows)[["fold", "horizon_minutes", "threshold", "model", "n", "positive_rate", "PR_AUC", "Brier"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
