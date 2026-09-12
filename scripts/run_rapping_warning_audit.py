"""Stratify saved F2 predictions by their ex-post relation to critical rapping."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.forecast_features import HORIZON_SECONDS, TARGET
from src.forecast_validation import DEVELOPMENT_FOLDS, critical_rapping_relation, warning_metrics

DEFAULT_DIRS = {"D1": "forecast_f2_v1", "D2": "forecast_f2_d2", "D3": "forecast_f2_d3"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed" / "forecast_f3_rapping_audit")
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output.mkdir(exist_ok=True)
    source = pd.read_parquet(ROOT / "data" / "processed" / "dataset_clean.parquet")
    if TARGET not in source:
        raise KeyError(TARGET)
    rows: list[dict[str, object]] = []
    for fold in DEVELOPMENT_FOLDS[:3]:
        for horizon in HORIZON_SECONDS:
            related = critical_rapping_relation(source, horizon).reindex(source.index).fillna(False)
            for threshold in (20.0, 40.0):
                path = ROOT / "data" / "processed" / DEFAULT_DIRS[fold.name] / f"predictions_{fold.name}_h{horizon}s_gt{threshold:g}.parquet"
                prediction = pd.read_parquet(path)
                relation = related.reindex(prediction.index).fillna(False)
                for stratum, mask in {"all": pd.Series(True, index=prediction.index), "critical_rapping_related": relation, "outside_critical_rapping": ~relation}.items():
                    for model in ("persistence", "xgboost_p", "xgboost_ph"):
                        item = {"fold": fold.name, "horizon_seconds": horizon, "threshold": threshold, "stratum": stratum, "model": model}
                        item.update(warning_metrics(prediction.loc[mask, "event"], prediction.loc[mask, model]))
                        rows.append(item)
    metrics = pd.DataFrame(rows)
    metrics.to_csv(output / "metrics_by_rapping_stratum.csv", index=False)
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
