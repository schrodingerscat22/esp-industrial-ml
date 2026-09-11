"""Leakage-safe features and labels for direct multi-horizon dust forecasts."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.time_analysis import STEP, rapping_starts, segments, time_shift, validate_time

TARGET = "008A01345"
HORIZON_SECONDS = (60, 180, 300)
LAG_SAMPLES = (1, 3, 6, 12, 30, 60, 180)
WINDOW_SAMPLES = (6, 30, 60, 180)
DIFF_SAMPLES = (6, 18, 30)
# Deliberately compact P catalogue. All current signals remain available; these
# temporal summaries cover short, medium and 30-minute process dynamics without
# an uncontrolled Cartesian expansion across 75 tags.
PROCESS_LAG_SAMPLES = (6, 30, 180)
PROCESS_WINDOW_SAMPLES = (30, 180)
PROCESS_DIFF_SAMPLES = (18, 30)
ANALYTIC_THRESHOLDS = (20.0, 40.0)


def delay_to_samples(delay_seconds: int) -> int:
    if delay_seconds < 0 or delay_seconds % int(STEP.total_seconds()):
        raise ValueError("delay_seconds must be a non-negative multiple of 10")
    return delay_seconds // int(STEP.total_seconds())


def clean_forecast_data(df: pd.DataFrame, input_cols: list[str]) -> pd.DataFrame:
    """Complete-case source frame, deliberately without interpolation or filling."""
    validate_time(df)
    if TARGET in input_cols or len(set(input_cols)) != len(input_cols):
        raise ValueError("Input columns must be unique and exclude the target")
    required = [TARGET] + list(input_cols)
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise KeyError(f"Missing forecast columns: {missing}")
    return df[required].replace([np.inf, -np.inf], np.nan).dropna().copy()


def fit_forecast_schema(
    train: pd.DataFrame, classification: pd.DataFrame
) -> dict[str, list[str]]:
    """Fit data-dependent feature schema strictly on the training window."""
    required = {"tag", "role", "category"}
    if not required.issubset(classification.columns):
        raise ValueError(f"Classification requires {sorted(required)}")
    if classification["tag"].duplicated().any():
        raise ValueError("Tag classification contains duplicate tags")
    inputs = classification.loc[classification["role"].eq("input"), "tag"].tolist()
    if TARGET in inputs or not inputs:
        raise ValueError("Invalid input-tag definition")
    absent = sorted(set(inputs) - set(train.columns))
    if absent:
        raise KeyError(f"Classified inputs unavailable in training data: {absent}")
    rapping = classification.loc[
        classification["tag"].isin(inputs) & classification["category"].eq("esp_rapping"),
        "tag",
    ].tolist()
    return {
        "inputs": inputs,
        "continuous": [tag for tag in inputs if train[tag].nunique(dropna=True) > 10],
        "rapping": rapping,
    }


def _rolling(frame: pd.DataFrame, segment: pd.Series, window: int, operation: str) -> pd.DataFrame:
    grouped = frame.groupby(segment).rolling(window=window, min_periods=window)
    if operation == "iqr":
        result = grouped.quantile(0.75) - grouped.quantile(0.25)
    else:
        result = getattr(grouped, operation)()
    return result.reset_index(level=0, drop=True).reindex(frame.index)


def _minutes_since_start(starts: pd.Series, available: pd.Series, segment: pd.Series) -> pd.Series:
    times = starts.index.to_series()
    last_start = times.where(starts).groupby(segment).ffill()
    elapsed = (times - last_start).dt.total_seconds() / 60
    return elapsed.where(available.notna()).astype("float32")


def history_features(df: pd.DataFrame, measurement_delay_seconds: int = 0) -> pd.DataFrame:
    """Features that use only the latest dust measurement available at an origin."""
    validate_time(df)
    delay = delay_to_samples(measurement_delay_seconds)
    segment = segments(df)
    available = time_shift(df[TARGET].astype("float32"), delay)
    parts: dict[str, pd.Series] = {"dust_available": available}

    for lag in LAG_SAMPLES:
        parts[f"dust_lag_{lag}"] = time_shift(available, lag)
    for window in WINDOW_SAMPLES:
        frame = available.to_frame("dust")
        for operation in ("mean", "median", "min", "max", "std", "iqr"):
            parts[f"dust_roll_{operation}_{window}"] = _rolling(frame, segment, window, operation)["dust"]
    for period in DIFF_SAMPLES:
        past = time_shift(available, period)
        minutes = period * STEP.total_seconds() / 60
        parts[f"dust_diff_{period}"] = available - past
        parts[f"dust_slope_{period}_per_min"] = (available - past) / minutes
    for threshold in ANALYTIC_THRESHOLDS:
        starts = available.gt(threshold) & available.notna()
        parts[f"dust_minutes_since_gt_{int(threshold)}"] = _minutes_since_start(starts, available, segment)
    return pd.DataFrame(parts, index=df.index).astype("float32")


def process_features(df: pd.DataFrame, schema: dict[str, list[str]]) -> pd.DataFrame:
    """Current and historical process features, never crossing timestamp gaps."""
    validate_time(df)
    inputs = schema["inputs"]
    continuous = schema["continuous"]
    rapping = schema["rapping"]
    if not set(continuous).issubset(inputs) or not set(rapping).issubset(inputs):
        raise ValueError("Invalid process feature schema")
    segment = segments(df)
    # Preallocate the final matrix. Building a list of nearly 2,000 DataFrames
    # temporarily duplicates the matrix and is needlessly expensive on the
    # developer workstation; this preserves the exact same feature definition.
    names = list(inputs)
    names += [f"{tag}_lag_{lag}" for lag in PROCESS_LAG_SAMPLES for tag in inputs]
    names += [
        f"{tag}_roll_{operation}_{window}"
        for window in PROCESS_WINDOW_SAMPLES
        for operation in ("mean", "std")
        for tag in continuous
    ]
    names += [f"{tag}_diff_{period}" for period in PROCESS_DIFF_SAMPLES for tag in continuous]
    names += [name for tag in rapping for name in (f"{tag}_rapping_start", f"{tag}_minutes_since_rapping_start")]
    values = np.empty((len(df), len(names)), dtype="float32")
    position = 0

    def add(part: pd.DataFrame | pd.Series) -> None:
        nonlocal position
        width = 1 if isinstance(part, pd.Series) else part.shape[1]
        array = part.to_numpy(dtype="float32", copy=False).reshape(len(df), width)
        values[:, position:position + width] = array
        position += width

    base = df[inputs].astype("float32")
    add(base)
    for lag in PROCESS_LAG_SAMPLES:
        add(base.groupby(segment).shift(lag))

    analog = base[continuous]
    for window in PROCESS_WINDOW_SAMPLES:
        for operation in ("mean", "std"):
            add(_rolling(analog, segment, window, operation))
    for period in PROCESS_DIFF_SAMPLES:
        add(analog.groupby(segment).diff(period))
    for tag in rapping:
        starts = rapping_starts(df[tag])
        add(starts.astype("float32"))
        add(_minutes_since_start(starts, df[tag], segment))
    if position != len(names):
        raise RuntimeError("Process feature matrix was not filled completely")
    return pd.DataFrame(values, index=df.index, columns=names)


def direct_target(df: pd.DataFrame, horizon_seconds: int) -> pd.Series:
    """Exact y(t+h); target may be after a telemetry gap but must have exact timestamp."""
    if horizon_seconds not in HORIZON_SECONDS:
        raise ValueError(f"Unsupported horizon: {horizon_seconds}")
    validate_time(df)
    future_index = df.index + pd.Timedelta(seconds=horizon_seconds)
    values = df[TARGET].reindex(future_index).to_numpy()
    return pd.Series(values, index=df.index, name=f"target_{horizon_seconds}s", dtype="float32")


def future_event_target(df: pd.DataFrame, horizon_seconds: int, threshold: float) -> pd.Series:
    """Event label for max(y(t+10s), ..., y(t+h)) > threshold.

    Every expected future point must be observed in the same continuous segment.
    A partial future window is unknown (NaN), never a negative event.
    """
    if horizon_seconds not in HORIZON_SECONDS:
        raise ValueError(f"Unsupported horizon: {horizon_seconds}")
    validate_time(df)
    samples = horizon_seconds // int(STEP.total_seconds())
    future = pd.concat(
        [time_shift(df[TARGET].astype("float32"), -step) for step in range(1, samples + 1)],
        axis=1,
    )
    complete = future.notna().all(axis=1)
    label = future.gt(threshold).any(axis=1).astype("float32")
    return label.where(complete).rename(f"event_{horizon_seconds}s_gt_{threshold:g}")


def feature_family_counts(columns: pd.Index) -> dict[str, int]:
    names = pd.Index(columns).astype(str)
    return {
        "current": int((~names.str.contains("_lag_|_roll_|_diff_|_slope_|minutes_since|rapping_start")).sum()),
        "lags": int(names.str.contains("_lag_").sum()),
        "rolling": int(names.str.contains("_roll_").sum()),
        "differences_and_slopes": int((names.str.contains("_diff_") | names.str.contains("_slope_")).sum()),
        "rapping_events": int((names.str.contains("minutes_since_rapping") | names.str.contains("rapping_start")).sum()),
        "threshold_recency": int(names.str.contains("minutes_since_gt").sum()),
    }
