"""Run E1: electrical state, rapping cycles and energy-comparability audit.

Writes only ignored local artefacts.  No model is trained and no setting is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MPL_CACHE = ROOT / "data" / "processed" / "electrical_energy_matplotlib_cache"
MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.electrical_state import FIELDS, RAPPING_TAGS, daily_process_correlations, derive_electrical_state, process_context, required_columns, signal_quality
from src.energy_comparability import complete_blocks, event_analysis, gate_decision, match_blocks
from src.time_analysis import coverage

DEFAULT_INPUT = ROOT / "data" / "processed" / "audit_v3" / "df_model_clean_v1.parquet"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "electrical_energy_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True, default=str), encoding="utf-8")


def source_selection() -> dict[str, object]:
    paths = [ROOT / "data" / "processed" / name for name in ("dataset_clean.parquet", "df_model_clean_v1.parquet")]
    paths.append(DEFAULT_INPUT)
    result = {}
    for path in paths:
        frame = pd.read_parquet(path)
        useful = [c for c in ("008A01345", "008A02273", "008A02274", "008A02275", "008B05154") if c in frame]
        result[path.as_posix()] = {"rows": len(frame), "columns": len(frame.columns), "start": str(frame.index.min()), "end": str(frame.index.max()),
                                   "coverage": coverage(frame[useful]), "sha256": sha256(path)}
    return result


def plot_figures(output: Path, quality: pd.DataFrame, events: pd.DataFrame, profiles: pd.DataFrame,
                 blocks: pd.DataFrame, pairs: pd.DataFrame) -> None:
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    fig, axis = plt.subplots(figsize=(7, 4))
    axis.bar(quality.field.astype(str), quality.R_median_Mohm)
    axis.set(xlabel="Pole", ylabel="Mediana U/I [MΩ]", title="Pozorna rezystancja pól")
    fig.tight_layout(); fig.savefig(figures / "01_resistance_by_field.png", dpi=150); plt.close(fig)
    if len(events):
        fig, axis = plt.subplots(figsize=(7, 4))
        events.boxplot(column="total_P_tag_kW_post_0_5_median_delta", by="tag", ax=axis, rot=45)
        axis.set(xlabel="Tag strzepywacza", ylabel="Δ moc [kW]", title="Zmiana mocy 0–5 min po starcie")
        fig.suptitle(""); fig.tight_layout(); fig.savefig(figures / "02_rapping_power_delta.png", dpi=150); plt.close(fig)
    if len(profiles):
        column = "total_P_tag_kW_median"
        fig, axis = plt.subplots(figsize=(7, 4))
        for tag, group in profiles.groupby("tag"):
            axis.plot(group.relative_seconds, group[column], label=tag)
        axis.axvline(0, color="black", linewidth=.8); axis.set(xlabel="Czas od startu [s]", ylabel="Mediana Δ mocy [kW]", title="Profile mocy po strzepywaniu")
        axis.legend(fontsize=6, ncol=2); fig.tight_layout(); fig.savefig(figures / "03_rapping_profiles.png", dpi=150); plt.close(fig)
    if len(blocks):
        fig, axis = plt.subplots(figsize=(7, 4))
        axis.scatter(blocks.generator_MW, blocks.mean_power_kW, s=5, alpha=.35)
        axis.set(xlabel="Moc generatora [MW]", ylabel="Średnia moc ESP [kW]", title="Moc ESP a obciążenie")
        fig.tight_layout(); fig.savefig(figures / "04_power_vs_generator.png", dpi=150); plt.close(fig)
    if len(pairs):
        fig, axis = plt.subplots(figsize=(7, 4))
        axis.scatter(pairs.delta_power_kW, pairs.delta_dust_mean_mg_Nm3, s=10, alpha=.5)
        axis.axhline(0, color="black", linewidth=.8); axis.set(xlabel="Różnica mocy wysokiej–niskiej [kW]", ylabel="Różnica średniego pyłu [mg/Nm³]", title="Dopasowane bloki")
        fig.tight_layout(); fig.savefig(figures / "05_matched_power_dust.png", dpi=150); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("signals", "events", "overlap", "all"), default="all")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    source = args.input if args.input.is_absolute() else ROOT / args.input
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    config = {"stage": args.stage, "smoke": args.smoke, "input": source.as_posix(), "input_sha256": sha256(source),
              "low_current_ma": 10, "block_seconds": 600, "matching_levels": (1, 2, 3), "tolerance_scales": (.5, 1., 2.),
              "power_difference_kW": (1., 2., 3.),
              "max_events": 20 if args.smoke else None, "max_blocks": 200 if args.smoke else None, "seed": 42}
    design_path = output / "design.json"
    if design_path.exists():
        prior = json.loads(design_path.read_text(encoding="utf-8"))
        if prior["input_sha256"] != config["input_sha256"] or prior["smoke"] != config["smoke"]:
            raise ValueError("Output directory has a different input hash or smoke mode; choose a new output directory.")
        if not args.resume:
            raise FileExistsError("Output directory already contains a matching run; pass --resume to continue it.")
    else:
        write_json(design_path, config)
    tracemalloc.start(); started = time.perf_counter()
    columns = required_columns(include_extended=True)
    raw = pd.read_parquet(source, columns=columns)
    before = sha256(source)
    state = derive_electrical_state(raw)
    context = process_context(raw)
    quality = signal_quality(raw, state)
    quality.to_csv(output / "signal_quality.csv", index=False)
    correlations = daily_process_correlations(state, context)
    correlations.to_csv(output / "daily_process_correlations.csv", index=False)
    write_json(output / "source_selection.json", source_selection())
    run_state: dict[str, object] = {"completed": ["signals"], "rows": len(raw), "coverage": coverage(raw[["008A01345", "008A02273", "008A02274", "008A02275"]])}
    events = profiles = overlap = pd.DataFrame()
    if args.stage in ("events", "all") and args.resume and (output / "event_summary.parquet").exists():
        events = pd.read_parquet(output / "event_summary.parquet")
        profiles = pd.read_parquet(output / "event_profiles.parquet")
        overlap = pd.read_csv(output / "overlap_counts.csv")
    elif args.stage in ("events", "all"):
        events, profiles, overlap = event_analysis(raw, state, config["max_events"])
        events.to_parquet(output / "event_summary.parquet", index=False)
        profiles.to_parquet(output / "event_profiles.parquet", index=False)
        overlap.to_csv(output / "overlap_counts.csv", index=False)
        run_state["completed"] = ["signals", "events"]
    blocks = pd.DataFrame(); all_pairs = []; support = []
    has_requested_power_sensitivity = False
    if args.resume and (output / "support_summary.csv").exists():
        prior_support = pd.read_csv(output / "support_summary.csv")
        has_requested_power_sensitivity = ("minimum_power_difference_kw" in prior_support and
                                          set(prior_support.minimum_power_difference_kw.unique()) == set(config["power_difference_kW"]))
    if args.stage in ("overlap", "all") and args.resume and (output / "block_summary.parquet").exists() and has_requested_power_sensitivity:
        blocks = pd.read_parquet(output / "block_summary.parquet")
        matched = pd.read_parquet(output / "matched_pairs.parquet")
        support_frame = pd.read_csv(output / "support_summary.csv")
        rejected = json.loads((output / "run_state.json").read_text(encoding="utf-8")).get("block_rejections", {})
    elif args.stage in ("overlap", "all"):
        blocks, rejected = complete_blocks(state, context, config["max_blocks"])
        blocks.to_parquet(output / "block_summary.parquet", index=False)
        for level in config["matching_levels"]:
            for scale in config["tolerance_scales"]:
                for power_difference_kw in config["power_difference_kW"]:
                    pairs, report = match_blocks(blocks, int(level), float(scale), float(power_difference_kw))
                    report.update({"level": level, "tolerance_scale": scale})
                    support.append(report)
                    if len(pairs):
                        all_pairs.append(pairs)
        matched = pd.concat(all_pairs, ignore_index=True) if all_pairs else pd.DataFrame()
        matched.to_parquet(output / "matched_pairs.parquet", index=False)
        support_frame = pd.DataFrame(support)
        support_frame.to_csv(output / "support_summary.csv", index=False)
        run_state["completed"] = ["signals", "events", "overlap"] if args.stage == "all" else ["signals", "overlap"]
        run_state["block_rejections"] = rejected
    else:
        matched = pd.DataFrame(); support_frame = pd.DataFrame()
    central = support_frame[(support_frame.level == 3) & (support_frame.tolerance_scale == 1) &
                            (support_frame.minimum_power_difference_kw == 2)] if len(support_frame) else pd.DataFrame()
    central_pairs = matched[(matched.level == 3) & (matched.tolerance_scale == 1) &
                            (matched.minimum_power_difference_kw == 2)] if len(matched) else pd.DataFrame()
    gate = gate_decision(central_pairs, central.iloc[0].to_dict()) if len(central) else {"decision": "B", "reason": "overlap_not_run", "gate_passed": False}
    after = sha256(source)
    current, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    report = {
        "observations": {"signal_quality_rows": len(quality), "rapping_tags": list(RAPPING_TAGS), "event_summary_rows": len(events), "complete_blocks": len(blocks),
                         "daily_process_correlation_rows": len(correlations)},
        "hypotheses": {"H1": "E1 is descriptive; repeatability is assessed by daily and cycle stratification.", "H3": "Comparable blocks do not identify a causal power effect."},
        "unknowns": ["controller setpoints and modes", "physical boundary of power tags", "dust sensor delay and process geometry", "inlet dust properties"],
        "gate_decision": gate, "source_integrity": {"sha256_before": before, "sha256_after": after, "unchanged": before == after},
        "rejection_counts": run_state.get("block_rejections", {}), "resource": {"elapsed_seconds": time.perf_counter() - started, "tracemalloc_peak_bytes": peak},
    }
    write_json(output / "report.json", report); write_json(output / "run_state.json", run_state)
    if args.stage == "all":
        plot_figures(output, quality, events, profiles, blocks, central_pairs)
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
