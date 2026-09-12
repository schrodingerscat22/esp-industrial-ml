"""Gap-safe event and block comparisons for the observational ESP energy audit."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from src.electrical_state import FIELDS, RAPPING_TAGS
from src.time_analysis import STEP, complete_window, rapping_starts, validate_time

EVENT_START_SECONDS, EVENT_END_SECONDS = -300, 900
EVENT_WINDOWS = (("post_0_5", 0, 300), ("post_5_10", 300, 600), ("post_10_15", 600, 900))
BLOCK_SECONDS = 600


def event_analysis(df: pd.DataFrame, state: pd.DataFrame, max_events: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Paired rapping summaries and median profiles; incomplete windows are rejected."""
    validate_time(df)
    columns = ["dust_mg_Nm3", "total_P_tag_kW"]
    for field in FIELDS:
        prefix = f"field_{field.number}"
        columns.extend((f"{prefix}_U_kV", f"{prefix}_I_mA", f"{prefix}_R_app_Mohm", f"{prefix}_P_tag_kW"))
    values = state[columns]
    summaries, profiles, overlap_rows = [], [], []
    all_starts = {tag: df.index[rapping_starts(df[tag])] for tag in RAPPING_TAGS}
    for tag, starts in all_starts.items():
        if max_events is not None:
            starts = starts[:max_events]
        accepted = 0
        for event_id, when in enumerate(starts):
            window = complete_window(values, when, EVENT_START_SECONDS, EVENT_END_SECONDS)
            if window is None:
                overlap_rows.append({"tag": tag, "event_id": event_id, "event_time": when, "status": "rejected_incomplete", "other_starts": None})
                continue
            accepted += 1
            other = sum(int(((times >= when + pd.Timedelta(seconds=EVENT_START_SECONDS)) & (times <= when + pd.Timedelta(seconds=EVENT_END_SECONDS))).sum())
                        for other_tag, times in all_starts.items() if other_tag != tag)
            base = window.loc[when + pd.Timedelta(minutes=-5):when + pd.Timedelta(minutes=-1)]
            row: dict[str, object] = {"tag": tag, "event_id": event_id, "event_time": when, "other_starts": other}
            for column in columns:
                baseline = base[column].median()
                row[f"{column}_baseline"] = baseline
                for label, start, end in EVENT_WINDOWS:
                    # Right edge is retained for profiles; summaries use [start,end).
                    interval = window.loc[when + pd.Timedelta(seconds=start):when + pd.Timedelta(seconds=end - 10), column]
                    row[f"{column}_{label}_median_delta"] = interval.median() - baseline
            summaries.append(row)
            relative = (window.index - when).total_seconds().astype(int)
            profile = window.copy()
            profile["relative_seconds"] = relative
            profile["tag"] = tag
            for column in columns:
                profile[column] = profile[column] - base[column].median()
            profiles.append(profile.reset_index(drop=True))
            overlap_rows.append({"tag": tag, "event_id": event_id, "event_time": when, "status": "accepted", "other_starts": other})
        if not len(starts):
            overlap_rows.append({"tag": tag, "event_id": None, "event_time": None, "status": "no_observed_starts", "other_starts": None})
    profile_frame = pd.concat(profiles, ignore_index=True) if profiles else pd.DataFrame()
    if len(profile_frame):
        profile_frame = profile_frame.groupby(["tag", "relative_seconds"], as_index=False)[columns].agg(["median", "quantile", "count"])
        profile_frame.columns = ["_".join(str(part) for part in item if part) for item in profile_frame.columns.to_flat_index()]
        profile_frame = profile_frame.rename(columns={"tag_": "tag", "relative_seconds_": "relative_seconds"})
    return pd.DataFrame(summaries), profile_frame, pd.DataFrame(overlap_rows)


def _phase(value: float) -> str:
    if not np.isfinite(value):
        return "unknown"
    if value < 0:
        return ">15"
    if value <= 1:
        return "0_1"
    if value <= 3:
        return "1_3"
    if value <= 5:
        return "3_5"
    return "5_15"


def complete_blocks(state: pd.DataFrame, context: pd.DataFrame, max_blocks: int | None = None) -> tuple[pd.DataFrame, dict[str, int]]:
    """Non-overlapping 10-minute blocks with exact observed endpoints and common power exposure."""
    validate_time(state)
    required = ["total_P_tag_kW", "dust_mg_Nm3"] + [f"field_{f.number}_P_tag_kW" for f in FIELDS]
    joined = pd.concat([state[required + [f"rapping_{tag}_minutes_since_0_15" for tag in RAPPING_TAGS]], context], axis=1)
    rows, rejected = [], defaultdict(int)
    starts = state.index[(state.index.second == 0) & ((state.index.minute % 10) == 0)]
    for start in starts:
        end = start + pd.Timedelta(seconds=BLOCK_SECONDS)
        if end > state.index[-1]:
            rejected["right_edge_missing"] += 1
            continue
        expected = pd.date_range(start, end, freq=STEP)
        window = joined.loc[start:end]
        if not window.index.equals(expected):
            rejected["time_gap_or_boundary"] += 1
            continue
        left = window.iloc[:-1]
        if not np.isfinite(left[required].to_numpy(dtype=float)).all():
            rejected["power_or_dust_missing"] += 1
            continue
        if not np.isfinite(left[context.columns].to_numpy(dtype=float)).all():
            rejected["context_missing"] += 1
            continue
        power = left["total_P_tag_kW"]
        row: dict[str, object] = {
            "block_start": start, "day": start.normalize(), "duration_seconds": BLOCK_SECONDS,
            "energy_kWh": float(power.sum() * STEP.total_seconds() / 3600), "mean_power_kW": float(power.mean()),
            "dust_mean_mg_Nm3": float(left["dust_mg_Nm3"].mean()), "dust_p95_mg_Nm3": float(left["dust_mg_Nm3"].quantile(.95)),
            "dust_max_mg_Nm3": float(left["dust_mg_Nm3"].max()), "dust_seconds_gt20": int(left["dust_mg_Nm3"].gt(20).sum() * 10),
            "dust_seconds_gt40": int(left["dust_mg_Nm3"].gt(40).sum() * 10),
        }
        for f in FIELDS:
            row[f"field_{f.number}_energy_kWh"] = float(left[f"field_{f.number}_P_tag_kW"].sum() * 10 / 3600)
        for col in context.columns:
            row[col] = float(left[col].mean())
        for tag in RAPPING_TAGS:
            row[f"phase_{tag}"] = _phase(float(state.at[start, f"rapping_{tag}_minutes_since_0_15"]))
            row[f"active_seconds_{tag}"] = int(left[f"rapping_{tag}_minutes_since_0_15"].between(0, 15).sum() * 10)
        rows.append(row)
        if max_blocks is not None and len(rows) >= max_blocks:
            break
    return pd.DataFrame(rows), dict(rejected)


def _within(reference: pd.Series, candidate: pd.Series, level: int, tolerance_scale: float) -> bool:
    relative = (abs(candidate["generator_MW"] - reference["generator_MW"]) / max(abs(reference["generator_MW"]), 1e-9) <= .02 * tolerance_scale and
                abs(candidate["flue_flow_thousand_m3_h"] - reference["flue_flow_thousand_m3_h"]) / max(abs(reference["flue_flow_thousand_m3_h"]), 1e-9) <= .05 * tolerance_scale)
    if not relative or level == 1:
        return bool(relative)
    continuous = ("flue_temperature_mean_C", "flue_temperature_L_minus_R_C", "flue_moisture_pct", "O2_before_OPP_L_pct", "O2_before_OPP_R_pct")
    tolerances = (2, 2, .2, .5, .5)
    if any(abs(candidate[c] - reference[c]) > tolerance * tolerance_scale for c, tolerance in zip(continuous, tolerances)):
        return False
    burner_cols = [c for c in reference.index if c.startswith("burner_")]
    if any(candidate[c] != reference[c] for c in burner_cols):
        return False
    if level == 2:
        return True
    for tag in RAPPING_TAGS:
        if candidate[f"phase_{tag}"] == "unknown" or reference[f"phase_{tag}"] == "unknown":
            return False
        if candidate[f"phase_{tag}"] != reference[f"phase_{tag}"]:
            return False
        if abs(candidate[f"active_seconds_{tag}"] - reference[f"active_seconds_{tag}"]) > 60:
            return False
    return True


def _candidate_mask(reference: pd.Series, candidates: pd.DataFrame, level: int, tolerance_scale: float) -> pd.Series:
    """Vectorised form of the documented matching tolerances."""
    mask = (candidates.generator_MW.sub(reference.generator_MW).abs().le(.02 * tolerance_scale * max(abs(reference.generator_MW), 1e-9)) &
            candidates.flue_flow_thousand_m3_h.sub(reference.flue_flow_thousand_m3_h).abs().le(.05 * tolerance_scale * max(abs(reference.flue_flow_thousand_m3_h), 1e-9)))
    if level >= 2:
        for column, tolerance in (("flue_temperature_mean_C", 2), ("flue_temperature_L_minus_R_C", 2), ("flue_moisture_pct", .2),
                                  ("O2_before_OPP_L_pct", .5), ("O2_before_OPP_R_pct", .5)):
            mask &= candidates[column].sub(reference[column]).abs().le(tolerance * tolerance_scale)
        for column in (c for c in candidates if c.startswith("burner_")):
            mask &= candidates[column].eq(reference[column])
    if level >= 3:
        for tag in RAPPING_TAGS:
            phase, active = f"phase_{tag}", f"active_seconds_{tag}"
            mask &= candidates[phase].eq(reference[phase]) & candidates[phase].ne("unknown")
            mask &= candidates[active].sub(reference[active]).abs().le(60)
    return mask


def match_blocks(blocks: pd.DataFrame, level: int, tolerance_scale: float = 1.0,
                 power_difference_kw: float = 2.0, max_candidates: int = 20) -> tuple[pd.DataFrame, dict[str, object]]:
    """Deterministic, no-reuse matching across days without using dust or U/I."""
    if blocks.empty:
        return pd.DataFrame(), {"candidate_pairs": 0, "matched_pairs": 0, "reason": "no_complete_blocks"}
    used: set[int] = set()
    pairs, candidate_pairs = [], 0
    sort = blocks.sort_values("block_start").reset_index(names="block_id")
    for pos, ref in sort.iterrows():
        if ref.block_id in used:
            continue
        candidates = sort[(sort.day != ref.day) & (~sort.block_id.isin(used))]
        candidates = candidates[_candidate_mask(ref, candidates, level, tolerance_scale)]
        candidate_pairs += len(candidates)
        if candidates.empty:
            continue
        scale = pd.Series({"generator_MW": max(abs(ref.generator_MW), 1), "flue_flow_thousand_m3_h": max(abs(ref.flue_flow_thousand_m3_h), 1)})
        candidates = candidates.assign(_distance=((candidates.generator_MW - ref.generator_MW).abs() / scale.generator_MW +
                                                  (candidates.flue_flow_thousand_m3_h - ref.flue_flow_thousand_m3_h).abs() / scale.flue_flow_thousand_m3_h))
        candidate = candidates.sort_values(["_distance", "block_start"]).head(max_candidates).iloc[0]
        delta = candidate.mean_power_kW - ref.mean_power_kW
        threshold = max(power_difference_kw, .05 * ((candidate.mean_power_kW + ref.mean_power_kW) / 2))
        if abs(delta) < threshold:
            continue
        low, high = (ref, candidate) if ref.mean_power_kW <= candidate.mean_power_kW else (candidate, ref)
        pairs.append({
            "level": level, "tolerance_scale": tolerance_scale, "low_block_start": low.block_start, "high_block_start": high.block_start,
            "low_day": low.day, "high_day": high.day, "low_mean_power_kW": low.mean_power_kW, "high_mean_power_kW": high.mean_power_kW,
            "delta_power_kW": high.mean_power_kW - low.mean_power_kW, "delta_energy_kWh": high.energy_kWh - low.energy_kWh,
            "delta_dust_mean_mg_Nm3": high.dust_mean_mg_Nm3 - low.dust_mean_mg_Nm3,
            "delta_dust_p95_mg_Nm3": high.dust_p95_mg_Nm3 - low.dust_p95_mg_Nm3,
            "context_distance": candidate._distance, "minimum_power_difference_kw": power_difference_kw,
        })
        used.update((int(ref.block_id), int(candidate.block_id)))
    result = pd.DataFrame(pairs)
    hours = len(result) * 2 * BLOCK_SECONDS / 3600
    report = {"candidate_pairs": int(candidate_pairs), "matched_pairs": int(len(result)), "matched_hours": hours,
              "eligible_hours": len(blocks) * BLOCK_SECONDS / 3600, "coverage_pct": 100 * hours / (len(blocks) * BLOCK_SECONDS / 3600) if len(blocks) else 0,
              "minimum_power_difference_kw": power_difference_kw}
    return result, report


def gate_decision(pairs: pd.DataFrame, match_report: dict[str, object]) -> dict[str, object]:
    if len(pairs) < 30:
        return {"decision": "B", "reason": "fewer_than_30_unique_pairs", "gate_passed": False}
    days = pd.concat((pairs.low_day, pairs.high_day)).value_counts()
    sufficient_days = len(days) >= 3 and days.max() / (2 * len(pairs)) <= .5
    coverage = float(match_report["coverage_pct"]) >= 10
    if sufficient_days and coverage:
        return {"decision": "A", "reason": "observational_energy_overlap_gate_passed", "gate_passed": True}
    return {"decision": "B", "reason": "pairs_exist_but_coverage_or_day_diversity_gate_failed", "gate_passed": False}
