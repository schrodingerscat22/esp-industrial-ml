"""Electrical-state features for the observational ESP energy audit (E1)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.time_analysis import STEP, segments, time_shift, validate_time

TARGET = "008A01345"


@dataclass(frozen=True)
class FieldTags:
    number: int
    voltage: str
    current: str
    power: str
    spark: str
    enabled: str
    collecting_rapper: str
    discharge_rapper: str


FIELDS = (
    FieldTags(1, "008A02289", "008A02267", "008A02273", "008A02264", "008B05167", "008B05146", "008B05131"),
    FieldTags(2, "008A02290", "008A02268", "008A02274", "008A02265", "008B05173", "008B05150", "008B05135"),
    FieldTags(3, "008A02291", "008A02269", "008A02275", "008A02266", "008B05178", "008B05154", "008B05139"),
)
RAPPING_TAGS = tuple(tag for field in FIELDS for tag in (field.collecting_rapper, field.discharge_rapper))
BASE_PROCESS = (
    "008A00936", "008A01353", "008A00720", "008A00728", "008A02118", "008A00741", "008A00742",
    "008B01474", "008B01479", "008B01484", "008B01489",
)
EXTENDED_PROCESS = ("008A00910", "008A00911", "008A00719", "008A00727", "008A01350", "008A01341", "008A01343", "008A01347")


def required_columns(include_extended: bool = True) -> list[str]:
    electrical = [TARGET]
    for field in FIELDS:
        electrical.extend((field.voltage, field.current, field.power, field.spark, field.enabled,
                           field.collecting_rapper, field.discharge_rapper))
    return list(dict.fromkeys(electrical + list(BASE_PROCESS) + (list(EXTENDED_PROCESS) if include_extended else [])))


def require_schema(df: pd.DataFrame, include_extended: bool = False) -> None:
    validate_time(df)
    missing = set(required_columns(include_extended)) - set(df.columns)
    if missing:
        raise KeyError(f"Missing required ESP audit tags: {sorted(missing)}")


def generic_rapping_features(signal: pd.Series, prefix: str, max_minutes: int = 15) -> pd.DataFrame:
    """Observed starts and time since start, never bridging a 10-second gap."""
    validate_time(signal)
    previous = time_shift(signal, 1)
    starts = signal.eq(1) & previous.eq(0)
    seg = segments(signal)
    times = signal.index.to_series()
    last = times.where(starts).groupby(seg).ffill()
    elapsed = (times - last).dt.total_seconds() / 60
    since_segment = (times - times.groupby(seg).transform("first")).dt.total_seconds() / 60
    known = elapsed.notna() | since_segment.gt(max_minutes)
    elapsed = elapsed.where(elapsed.le(max_minutes), -1.0).where(known)
    return pd.DataFrame({
        f"{prefix}_start": starts.astype("int8"),
        f"{prefix}_minutes_since_0_{max_minutes}": elapsed.astype("float32"),
        f"{prefix}_known": known.astype("int8"),
    }, index=signal.index)


def _state_quality(voltage: pd.Series, current: pd.Series, enabled: pd.Series, low_current_ma: float) -> pd.Series:
    finite = np.isfinite(voltage) & np.isfinite(current)
    known_on = enabled.eq(1)
    return pd.Series(np.select(
        [~finite, enabled.isna(), ~known_on, voltage.le(0), current.le(0), current.lt(low_current_ma)],
        ["missing_measurement", "unknown_enabled", "off", "invalid_voltage", "invalid_current", "low_current"],
        default="valid",
    ), index=voltage.index, dtype="string")


def derive_electrical_state(df: pd.DataFrame, low_current_ma: float = 10.0) -> pd.DataFrame:
    """Return derived state without imputing a measurement or status."""
    require_schema(df)
    out = pd.DataFrame(index=df.index)
    for field in FIELDS:
        u, i, p = df[field.voltage].astype(float), df[field.current].astype(float), df[field.power].astype(float)
        quality = _state_quality(u, i, df[field.enabled], low_current_ma)
        valid = quality.eq("valid")
        name = f"field_{field.number}"
        out[f"{name}_quality"] = quality
        out[f"{name}_R_app_Mohm"] = (u / i).where(valid).astype("float32")
        out[f"{name}_G_app_uS"] = (i / u).where(valid).astype("float32")
        out[f"{name}_P_UI_kW"] = (u * i / 1000).where(valid).astype("float32")
        out[f"{name}_P_tag_kW"] = p.astype("float32")
        out[f"{name}_U_kV"] = u.astype("float32")
        out[f"{name}_I_mA"] = i.astype("float32")
        out[f"{name}_spark_n_min"] = df[field.spark].astype("float32")
    out["total_P_tag_kW"] = df[[field.power for field in FIELDS]].sum(axis=1, min_count=len(FIELDS)).astype("float32")
    out["dust_mg_Nm3"] = df[TARGET].astype("float32")
    for tag in RAPPING_TAGS:
        out = out.join(generic_rapping_features(df[tag], f"rapping_{tag}"))
    return out


def signal_quality(df: pd.DataFrame, state: pd.DataFrame) -> pd.DataFrame:
    """Signal coverage, quantisation indicators and algebraic power checks."""
    rows: list[dict[str, object]] = []
    for field in FIELDS:
        u, i, p = df[field.voltage].astype(float), df[field.current].astype(float), df[field.power].astype(float)
        quality = state[f"field_{field.number}_quality"]
        valid = quality.eq("valid")
        changes = u.ne(u.shift()) & u.notna() & u.shift().notna()
        p_ui = state.loc[valid, f"field_{field.number}_P_UI_kW"]
        p_tag = p[valid]
        rows.append({
            "field": field.number, "n": int(len(df)), "valid_R_n": int(valid.sum()),
            "valid_R_pct": float(valid.mean() * 100), "U_unique": int(u.nunique()), "I_unique": int(i.nunique()),
            "U_changed_pct": float(changes.mean() * 100), "spark_nonzero_pct": float(df[field.spark].ne(0).mean() * 100),
            "R_median_Mohm": float(state.loc[valid, f"field_{field.number}_R_app_Mohm"].median()),
            "R_p05_Mohm": float(state.loc[valid, f"field_{field.number}_R_app_Mohm"].quantile(.05)),
            "R_p95_Mohm": float(state.loc[valid, f"field_{field.number}_R_app_Mohm"].quantile(.95)),
            "P_UI_tag_corr": float(p_ui.corr(p_tag)) if p_ui.nunique() > 1 and p_tag.nunique() > 1 else np.nan,
            "P_UI_tag_MAE_kW": float((p_ui - p_tag).abs().mean()),
            "quality_valid_pct": float(valid.mean() * 100),
        })
    return pd.DataFrame(rows)


def process_context(df: pd.DataFrame) -> pd.DataFrame:
    """Named, conservative process features; no physical re-interpretation of tags."""
    require_schema(df)
    out = pd.DataFrame(index=df.index)
    out["generator_MW"] = df["008A00936"]
    out["flue_flow_thousand_m3_h"] = df["008A01353"]
    out["flue_temperature_mean_C"] = df[["008A00720", "008A00728"]].mean(axis=1)
    out["flue_temperature_L_minus_R_C"] = df["008A00720"] - df["008A00728"]
    out["flue_moisture_pct"] = df["008A02118"]
    out["O2_before_OPP_L_pct"] = df["008A00741"]
    out["O2_before_OPP_R_pct"] = df["008A00742"]
    for tag in ("008B01474", "008B01479", "008B01484", "008B01489"):
        out[f"burner_{tag}_on"] = df[tag]
    return out.astype("float32")


def daily_process_correlations(state: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    """Descriptive within-day electrical/process correlations, with gap-safe differences."""
    validate_time(state)
    critical = f"rapping_{FIELDS[2].collecting_rapper}_minutes_since_0_15"
    phase = state[critical].map(lambda value: "0_5" if 0 <= value <= 5 else ("5_15" if 5 < value <= 15 else (">15" if value < 0 else "unknown")))
    process_cols = ("generator_MW", "flue_flow_thousand_m3_h", "flue_temperature_mean_C", "flue_temperature_L_minus_R_C",
                    "flue_moisture_pct", "O2_before_OPP_L_pct", "O2_before_OPP_R_pct")
    rows: list[dict[str, object]] = []
    day = state.index.normalize()
    for field in FIELDS:
        value = state[f"field_{field.number}_R_app_Mohm"]
        variants = {"level": value, "diff_60s": value - time_shift(value, 6), "diff_180s": value - time_shift(value, 18)}
        for process_col in process_cols:
            process = context[process_col]
            process_variants = {"level": process, "diff_60s": process - time_shift(process, 6), "diff_180s": process - time_shift(process, 18)}
            for metric, electrical in variants.items():
                for phase_name in ("all", "0_5", "5_15", ">15"):
                    mask = phase.ne("unknown") if phase_name == "all" else phase.eq(phase_name)
                    frame = pd.DataFrame({"electrical": electrical[mask], "process": process_variants[metric][mask], "day": day[mask]}).dropna()
                    for date, group in frame.groupby("day"):
                        rows.append({"field": field.number, "process_feature": process_col, "metric": metric, "critical_phase": phase_name,
                                     "day": date, "n": len(group), "corr": group.electrical.corr(group.process) if len(group) >= 30 else np.nan})
    return pd.DataFrame(rows)
