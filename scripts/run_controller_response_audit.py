"""Run the descriptive controller-response audit without saving models or row predictions."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.controller_response import (HORIZONS_SECONDS, add_future_targets, build_audit_frame,
                                     daily_placebo, dust_innovation, fit_compare, local_projection,
                                     response_events)
from src.electrical_state import required_columns
from src.time_analysis import coverage

DEFAULT_INPUT = ROOT / "data" / "processed" / "audit_v3" / "df_model_clean_v1.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "controller_response_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--stage", choices=("all", "events"), default="all")
    args = parser.parse_args()
    source = args.input if args.input.is_absolute() else ROOT / args.input
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    before = sha256(source)
    tracemalloc.start(); started = time.perf_counter()
    raw = pd.read_parquet(source, columns=required_columns(include_extended=True))
    frame, schema = build_audit_frame(raw)
    horizons = (60,) if args.smoke else HORIZONS_SECONDS
    run_schema = {**schema, "targets": ["P_total_kW", "U_mean_kV"]} if args.smoke else schema
    if args.stage == "events":
        event_frames = [response_events(add_future_targets(frame, raw, horizon), raw, run_schema, horizon) for horizon in horizons]
        events = pd.concat(event_frames, ignore_index=True)
        event_summary = (events.groupby(["fold", "direction", "condition", "target", "response_horizon_seconds"], as_index=False)
                         .agg(events=("event_time", "size"), median_response=("response", "median"),
                              positive_response_pct=("response", lambda values: float((values > 0).mean() * 100)),
                              median_dust_diff_60s=("dust_diff_60s", "median")))
        event_summary.to_csv(output / "event_response_summary.csv", index=False)
        after = sha256(source)
        _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        write_json(output / "event_report.json", {"source_integrity": {"sha256_before": before, "sha256_after": after, "unchanged": before == after},
                                                     "observations": {"rows": len(raw), "horizons_seconds": horizons, "event_summary_rows": len(event_summary)},
                                                     "resource": {"elapsed_seconds": time.perf_counter() - started, "tracemalloc_peak_bytes": peak}})
        return
    metric_rows, local_rows, innovation_rows, placebo_rows = [], [], [], []
    for horizon in horizons:
        work = add_future_targets(frame, raw, horizon)
        metrics = fit_compare(work, run_schema, horizon)
        metric_rows.append(metrics)
        innovation, innovation_metric = dust_innovation(work, run_schema)
        innovation_metric["horizon_seconds"] = horizon
        innovation_rows.append(innovation_metric)
        local_rows.append(local_projection(work, run_schema, horizon))
        placebo = work.copy()
        for column in schema["dust"]:
            placebo[column] = daily_placebo(placebo[column], 180)
        placebo_metrics = fit_compare(placebo, run_schema, horizon)
        placebo_rows.append(placebo_metrics.loc[placebo_metrics.target.isin(("P_total_kW", "U_mean_kV"))])
    event_frames = [response_events(add_future_targets(frame, raw, horizon), raw, run_schema if args.smoke else schema, horizon) for horizon in horizons]
    events = pd.concat(event_frames, ignore_index=True)
    event_summary = (events.groupby(["fold", "direction", "condition", "target", "response_horizon_seconds"], as_index=False)
                     .agg(events=("event_time", "size"), median_response=("response", "median"),
                          positive_response_pct=("response", lambda values: float((values > 0).mean() * 100)),
                          median_dust_diff_60s=("dust_diff_60s", "median"))) if len(events) else pd.DataFrame()
    metrics = pd.concat(metric_rows, ignore_index=True)
    local = pd.concat(local_rows, ignore_index=True)
    innovation_metrics = pd.concat(innovation_rows, ignore_index=True)
    placebo_metrics = pd.concat(placebo_rows, ignore_index=True)
    metrics.to_csv(output / "model_comparison.csv", index=False)
    local.to_csv(output / "local_projection.csv", index=False)
    innovation_metrics.to_csv(output / "dust_innovation_metrics.csv", index=False)
    placebo_metrics.to_csv(output / "placebo_model_comparison.csv", index=False)
    event_summary.to_csv(output / "event_response_summary.csv", index=False)
    after = sha256(source)
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    report = {"source_integrity": {"sha256_before": before, "sha256_after": after, "unchanged": before == after},
              "observations": {"rows": len(raw), "coverage": coverage(raw[["008A01345", "008A02273", "008A02274", "008A02275"]]),
                               "horizons_seconds": horizons, "model_rows": len(metrics), "event_summary_rows": len(event_summary)},
              "resource": {"elapsed_seconds": time.perf_counter() - started, "tracemalloc_peak_bytes": peak}}
    write_json(output / "report.json", report)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
