"""Run F1 direct 1/3/5-minute dust forecasts without writing industrial data to Git.

Default data are known legacy/development data. This is not a confirmatory test.
"""
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

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from src.forecast_features import (
    HORIZON_SECONDS,
    TARGET,
    clean_forecast_data,
    delay_to_samples,
    direct_target,
    feature_family_counts,
    fit_forecast_schema,
    history_features,
    process_features,
)
from src.forecast_validation import (
    DEVELOPMENT_FOLDS,
    clip_nonnegative,
    forecast_origins,
    mase_scale,
    observed_hours,
    paired_day_bootstrap,
    point_metrics,
    strata,
    threshold_episode_starts,
)
from src.time_analysis import coverage, segments

OUT = ROOT / "data" / "processed" / "forecast_v1"
XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "objective": "reg:absoluteerror",
    "random_state": 42,
    "n_jobs": 1,
    "tree_method": "hist",
}
RIDGE_ALPHA = 1.0
MODEL_NAMES = ("persistence", "median_level", "linear_ar_h", "xgboost_h", "xgboost_p", "xgboost_ph")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, content: object) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def xgb() -> XGBRegressor:
    return XGBRegressor(**XGB_PARAMS)


def fit_xgb(
    name: str,
    features: pd.DataFrame,
    train: pd.DatetimeIndex,
    evaluate: pd.DatetimeIndex,
    target: pd.Series,
    fold_name: str,
    horizon_seconds: int,
) -> tuple[np.ndarray, XGBRegressor]:
    model = xgb()
    model.fit(features.loc[train], target.loc[train])
    prediction = model.predict(features.loc[evaluate])
    return prediction, model


def save_xgb_artifacts(model: XGBRegressor, features: pd.DataFrame, fold_name: str, horizon_seconds: int, name: str) -> None:
    model_dir = OUT / "models"
    model_dir.mkdir(exist_ok=True)
    model.save_model(model_dir / f"{fold_name}_h{horizon_seconds}s_{name}.ubj")
    importance = pd.DataFrame({"feature": features.columns, "importance": model.feature_importances_})
    importance.sort_values("importance", ascending=False).to_csv(
        model_dir / f"{fold_name}_h{horizon_seconds}s_{name}_importance.csv", index=False
    )


def developer_gate(metrics: pd.DataFrame, horizons: tuple[int, ...]) -> list[dict[str, object]]:
    rows = []
    development = metrics.loc[metrics["fold"].isin(["D1", "D2", "D3"])]
    for horizon in horizons:
        subset = development.loc[development["horizon_seconds"].eq(horizon)]
        persistence = subset.loc[subset["model"].eq("persistence"), ["fold", "MAE", "n"]].set_index("fold")
        for model in MODEL_NAMES:
            if model in ("persistence", "median_level"):
                continue
            candidate = subset.loc[subset["model"].eq(model), ["fold", "MAE", "n"]].set_index("fold")
            joined = candidate.join(persistence, lsuffix="_model", rsuffix="_persistence", how="inner")
            model_mae = np.average(joined["MAE_model"], weights=joined["n_model"])
            persistence_mae = np.average(joined["MAE_persistence"], weights=joined["n_persistence"])
            rows.append({
                "horizon_seconds": horizon,
                "model": model,
                "pooled_MAE_skill_vs_persistence": float(1 - model_mae / persistence_mae),
                "folds_with_positive_MAE_skill": int((joined["MAE_model"] < joined["MAE_persistence"]).sum()),
                "developer_gate_without_operational_bias_and_alarm_thresholds": bool(
                    model_mae < persistence_mae and (joined["MAE_model"] < joined["MAE_persistence"]).sum() >= 2
                ),
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", choices=[fold.name for fold in DEVELOPMENT_FOLDS], action="append")
    parser.add_argument("--horizon-seconds", choices=HORIZON_SECONDS, type=int, action="append")
    parser.add_argument("--measurement-delay-seconds", type=int, default=0)
    args = parser.parse_args()
    delay_to_samples(args.measurement_delay_seconds)

    OUT.mkdir(exist_ok=True)
    input_paths = [
        ROOT / "data" / "processed" / "dataset_clean.parquet",
        ROOT / "data" / "processed" / "tag_classification_v1.xlsx",
    ]
    source_paths = [Path(__file__), ROOT / "src" / "forecast_features.py", ROOT / "src" / "forecast_validation.py", ROOT / "src" / "time_analysis.py"]
    input_hashes_before = {str(path.relative_to(ROOT)): sha256(path) for path in input_paths}
    classification = pd.read_excel(input_paths[1])
    input_cols = classification.loc[classification["role"].eq("input"), "tag"].tolist()
    raw = pd.read_parquet(input_paths[0])
    source = clean_forecast_data(raw, input_cols)
    history = history_features(source, args.measurement_delay_seconds)
    # Recency features are structurally unknown before the first observed event.
    # XGBoost handles those missing values; the linear pipeline imputes them on train.
    history_required = history.columns[~history.columns.str.contains("minutes_since_gt")]
    history_valid = history[history_required].notna().all(axis=1)
    selected_folds = [fold for fold in DEVELOPMENT_FOLDS if args.fold is None or fold.name in args.fold]
    selected_horizons = tuple(args.horizon_seconds or HORIZON_SECONDS)
    design = {
        "status": "written_before_fit",
        "contract": "F1 direct forecast y(t+h), x(t) and dust up to y(t-delay) available at origin",
        "availability_unverified": True,
        "measurement_delay_seconds": args.measurement_delay_seconds,
        "horizons_seconds": selected_horizons,
        "folds": [fold.__dict__ for fold in selected_folds],
        "xgboost_parameters": XGB_PARAMS,
        "ridge_alpha": RIDGE_ALPHA,
        "input_hashes": input_hashes_before,
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in source_paths},
    }
    write_json(OUT / "design.json", design)
    report: dict[str, object] = {
        "status": "running",
        "design": design,
        "versions": {name: importlib.metadata.version(name) for name in ("numpy", "pandas", "xgboost", "scikit-learn", "pyarrow")},
        "raw_rows": len(raw),
        "clean_rows": len(source),
        "dropped_rows": len(raw) - len(source),
        "input_count": len(input_cols),
        "coverage": coverage(source),
        "history_feature_families": feature_family_counts(history.columns),
        "runs": [],
    }
    all_metrics: list[dict[str, object]] = []
    all_strata: list[dict[str, object]] = []

    for fold in selected_folds:
        print(f"{fold.name}: building process features", flush=True)
        started = time.monotonic()
        # Nothing after a bounded evaluation window can affect its features,
        # labels or estimates. Restricting the working frame makes F1 feasible
        # on a workstation without changing the declared fold.
        fold_source = source if fold.evaluation_end is None else source.loc[source.index < fold.evaluation_end]
        schema_train = fold_source.loc[fold_source.index < fold.evaluation_start]
        schema = fit_forecast_schema(schema_train, classification)
        process = process_features(fold_source, schema)
        # The source is complete-case for current process signals. Partial process
        # histories and event recencies remain missing rather than being imputed
        # across a gap; XGBoost natively routes missing values.
        process_valid = process[schema["inputs"]].notna().all(axis=1)
        joint_valid = history_valid & process_valid
        fold_summary: dict[str, object] = {
            "fold": fold.name,
            "evaluation_start": str(fold.evaluation_start),
            "evaluation_end_exclusive": str(fold.evaluation_end),
            "observed_evaluation_hours": observed_hours(fold_source.loc[fold_source.index >= fold.evaluation_start]),
            "schema": schema,
            "process_feature_families": feature_family_counts(process.columns),
            "runs": [],
        }
        source_segments = segments(fold_source)
        for horizon in selected_horizons:
            target = direct_target(fold_source, horizon)
            valid = joint_valid.reindex(fold_source.index)
            train, evaluate, diagnostics = forecast_origins(fold_source.index, valid, target, fold, horizon)
            if not len(train) or not len(evaluate):
                raise RuntimeError(f"{fold.name}, h={horizon}: empty train/evaluation origin set")
            mase_denominator = mase_scale(fold_source.loc[fold_source.index < fold.evaluation_start - pd.Timedelta(seconds=horizon), TARGET], horizon)
            y_train, y_eval = target.loc[train], target.loc[evaluate]
            prediction = pd.DataFrame({"y_true": y_eval}, index=evaluate)
            clip_summary: dict[str, dict[str, float | int]] = {}
            prediction["persistence"], clip_summary["persistence"] = clip_nonnegative(history.loc[evaluate, "dust_available"])
            prediction["median_level"], clip_summary["median_level"] = clip_nonnegative(np.repeat(float(y_train.median()), len(evaluate)))

            print(f"{fold.name}, h={horizon}s: fitting linear_ar_h", flush=True)
            linear = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=RIDGE_ALPHA))
            linear.fit(history.loc[train], y_train)
            prediction["linear_ar_h"], clip_summary["linear_ar_h"] = clip_nonnegative(linear.predict(history.loc[evaluate]))

            feature_sets = {"xgboost_h": history, "xgboost_p": process, "xgboost_ph": pd.concat([process, history], axis=1)}
            fitted: dict[str, tuple[XGBRegressor, pd.DataFrame]] = {}
            for name, features in feature_sets.items():
                print(f"{fold.name}, h={horizon}s: fitting {name} ({len(train)} train / {len(evaluate)} evaluation)", flush=True)
                raw_prediction, model = fit_xgb(name, features, train, evaluate, target, fold.name, horizon)
                prediction[name], clip_summary[name] = clip_nonnegative(raw_prediction)
                fitted[name] = (model, features)
            model_dir = OUT / "models"
            model_dir.mkdir(exist_ok=True)
            joblib.dump(linear, model_dir / f"{fold.name}_h{horizon}s_linear_ar_h.joblib")
            for name, (model, features) in fitted.items():
                save_xgb_artifacts(model, features, fold.name, horizon, name)

            persistence_mae = point_metrics(y_eval, prediction["persistence"], mase_denominator)["MAE"]
            for name in MODEL_NAMES:
                row = {"fold": fold.name, "horizon_seconds": horizon, "horizon_minutes": horizon / 60, "model": name}
                row.update(point_metrics(y_eval, prediction[name], mase_denominator))
                row["MAE_skill_vs_persistence"] = float(1 - row["MAE"] / persistence_mae) if persistence_mae else None
                row.update({f"clip_{key}": value for key, value in clip_summary[name].items()})
                all_metrics.append(row)
            origin_segment = source_segments.reindex(evaluate)
            target_segment = source_segments.reindex(evaluate + pd.Timedelta(seconds=horizon))
            run_summary = {
                "horizon_seconds": horizon,
                "train_origins": len(train),
                "evaluation_origins": len(evaluate),
                "mase_denominator_train_only": mase_denominator,
                "feature_rows_invalid_history": int((~history_valid).sum()),
                "feature_rows_invalid_process": int((~process_valid).sum()),
                "point_label_crosses_gap": int((origin_segment.to_numpy() != target_segment.to_numpy()).sum()),
                "diagnostics": diagnostics,
                "target_episode_starts": {str(threshold): threshold_episode_starts(y_eval, threshold) for threshold in (20.0, 40.0)},
            }
            fold_summary["runs"].append(run_summary)
            groups = strata(pd.DataFrame(index=evaluate), y_eval, train, fold_source)
            for group_name, mask in groups.items():
                for name in MODEL_NAMES:
                    row = {"fold": fold.name, "horizon_seconds": horizon, "group": group_name, "model": name}
                    row.update(point_metrics(y_eval.to_numpy()[mask], prediction[name].to_numpy()[mask], mase_denominator))
                    all_strata.append(row)
            prediction.to_parquet(OUT / f"predictions_{fold.name}_h{horizon}s.parquet")
            if fold.name == "legacy_evaluation":
                run_summary["bootstrap"] = paired_day_bootstrap(prediction, list(MODEL_NAMES))
            del feature_sets, fitted, linear, prediction
            gc.collect()
            pd.DataFrame(all_metrics).to_csv(OUT / "metrics.csv", index=False)
            pd.DataFrame(all_strata).to_csv(OUT / "stratified_metrics.csv", index=False)
        fold_summary["seconds"] = time.monotonic() - started
        report["runs"].append(fold_summary)
        write_json(OUT / "report.json", report)
        del process
        gc.collect()

    metrics = pd.DataFrame(all_metrics)
    report["developer_gates"] = developer_gate(metrics, selected_horizons)
    report["metrics_rows"] = len(metrics)
    report["inputs_unchanged"] = input_hashes_before == {str(path.relative_to(ROOT)): sha256(path) for path in input_paths}
    if not report["inputs_unchanged"]:
        raise RuntimeError("Input-integrity check failed")
    report["status"] = "complete"
    write_json(OUT / "report.json", report)
    print(metrics[["fold", "horizon_minutes", "model", "n", "MAE", "RMSE", "MAE_skill_vs_persistence"]].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
