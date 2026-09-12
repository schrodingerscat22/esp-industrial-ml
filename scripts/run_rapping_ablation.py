"""F3 ablation: quantify the contribution of critical rapping to F2 warnings."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from xgboost import XGBClassifier

from src.forecast_features import (
    ANALYTIC_THRESHOLDS, HORIZON_SECONDS, clean_forecast_data, fit_forecast_schema,
    future_event_target, history_features, process_features,
)
from src.forecast_validation import (
    DEVELOPMENT_FOLDS, critical_rapping_relation, forecast_origins, warning_metrics,
)

PARAMS = dict(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8,
              colsample_bytree=0.8, objective="binary:logistic", eval_metric="logloss",
              random_state=42, n_jobs=1, tree_method="hist")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", choices=("D1", "D2", "D3"), action="append")
    parser.add_argument("--horizon-seconds", choices=HORIZON_SECONDS, type=int, action="append")
    parser.add_argument("--threshold", choices=ANALYTIC_THRESHOLDS, type=float, action="append")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed" / "forecast_f3_rapping_ablation")
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output.mkdir(exist_ok=True)
    classification = pd.read_excel(ROOT / "data" / "processed" / "tag_classification_v1.xlsx")
    inputs = classification.loc[classification.role.eq("input"), "tag"].tolist()
    source = clean_forecast_data(pd.read_parquet(ROOT / "data" / "processed" / "dataset_clean.parquet"), inputs)
    history = history_features(source)
    history_valid = history.drop(columns=history.filter(like="minutes_since_gt").columns).notna().all(axis=1)
    rows = []
    for fold in DEVELOPMENT_FOLDS[:3]:
        if args.fold and fold.name not in args.fold:
            continue
        fold_source = source if fold.evaluation_end is None else source.loc[source.index < fold.evaluation_end]
        schema = fit_forecast_schema(fold_source.loc[fold_source.index < fold.evaluation_start], classification)
        process = process_features(fold_source, schema)
        valid = (history_valid & process[schema["inputs"]].notna().all(axis=1)).reindex(fold_source.index)
        rapping_columns = [col for col in process if any(col == tag or col.startswith(f"{tag}_") for tag in schema["rapping"])]
        critical_columns = [col for col in process if col == "008B05154" or col.startswith("008B05154_")]
        features = {
            "xgboost_h": history,
            "xgboost_ph_no_rapping": pd.concat([process.drop(columns=rapping_columns), history], axis=1),
            "xgboost_critical_rapping": process[critical_columns],
            "xgboost_ph": pd.concat([process, history], axis=1),
        }
        for horizon in args.horizon_seconds or HORIZON_SECONDS:
            related = critical_rapping_relation(fold_source, horizon).fillna(False)
            for threshold in args.threshold or ANALYTIC_THRESHOLDS:
                label = future_event_target(fold_source, horizon, threshold)
                train, evaluate, _ = forecast_origins(fold_source.index, valid, label, fold, horizon)
                prediction = pd.DataFrame({"event": label.loc[evaluate]}, index=evaluate)
                for name, matrix in features.items():
                    print(f"{fold.name}, h={horizon}s, gt={threshold:g}: {name}", flush=True)
                    model = XGBClassifier(**PARAMS).fit(matrix.loc[train], label.loc[train].astype(int))
                    prediction[name] = model.predict_proba(matrix.loc[evaluate])[:, 1]
                for stratum, mask in {"all": pd.Series(True, index=evaluate), "outside_critical_rapping": ~related.loc[evaluate]}.items():
                    for name in features:
                        row = {"fold": fold.name, "horizon_seconds": horizon, "threshold": threshold, "stratum": stratum, "model": name}
                        row.update(warning_metrics(prediction.loc[mask, "event"], prediction.loc[mask, name]))
                        rows.append(row)
                prediction.to_parquet(output / f"predictions_{fold.name}_h{horizon}s_gt{threshold:g}.parquet")
                pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)


if __name__ == "__main__":
    main()
