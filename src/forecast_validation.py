"""Fixed folds, purge rules and leakage-safe F1 forecast metrics."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss

from src.time_analysis import STEP, coverage, segments, time_shift, validate_time


@dataclass(frozen=True)
class ForecastFold:
    name: str
    evaluation_start: pd.Timestamp
    evaluation_end: pd.Timestamp | None


DEVELOPMENT_FOLDS = (
    ForecastFold("D1", pd.Timestamp("2025-07-12"), pd.Timestamp("2025-07-17")),
    ForecastFold("D2", pd.Timestamp("2025-07-17"), pd.Timestamp("2025-07-22")),
    ForecastFold("D3", pd.Timestamp("2025-07-22"), pd.Timestamp("2025-07-27")),
    ForecastFold("legacy_evaluation", pd.Timestamp("2025-07-27"), None),
)


def forecast_origins(
    index: pd.DatetimeIndex,
    valid: pd.Series,
    target: pd.Series,
    fold: ForecastFold,
    horizon_seconds: int,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex, dict[str, int]]:
    """Return train/evaluation origins with h-minute purge at both boundaries."""
    if not index.equals(valid.index) or not index.equals(target.index):
        raise ValueError("index, valid and target must have identical timestamps")
    horizon = pd.Timedelta(seconds=horizon_seconds)
    train_mask = valid & target.notna() & (index < fold.evaluation_start - horizon)
    eval_mask = valid & target.notna() & (index >= fold.evaluation_start)
    if fold.evaluation_end is not None:
        eval_mask &= index < fold.evaluation_end - horizon
    diagnostics = {
        "origins_total": int(len(index)),
        "feature_or_label_invalid": int((~(valid & target.notna())).sum()),
        "purged_train_origins": int(((index < fold.evaluation_start) & ~(index < fold.evaluation_start - horizon)).sum()),
        "evaluation_origins_before_end_purge": int((valid & target.notna() & (index >= fold.evaluation_start)).sum()),
        "evaluation_origins": int(eval_mask.sum()),
    }
    return index[train_mask], index[eval_mask], diagnostics


def mase_scale(train_target: pd.Series, horizon_seconds: int) -> float:
    """Train-only h-step naive MAE, restricted to continuous 10-second segments."""
    validate_time(train_target)
    samples = horizon_seconds // int(STEP.total_seconds())
    previous = time_shift(train_target.astype(float), samples)
    differences = (train_target - previous).abs().dropna()
    return float(differences.mean()) if len(differences) else np.nan


def clip_nonnegative(prediction: np.ndarray | pd.Series) -> tuple[np.ndarray, dict[str, float | int]]:
    values = np.asarray(prediction, dtype=float)
    negative = values < 0
    return np.maximum(values, 0), {
        "negative_prediction_count": int(negative.sum()),
        "negative_prediction_total_magnitude": float((-values[negative]).sum()),
    }


def point_metrics(y_true: pd.Series | np.ndarray, prediction: pd.Series | np.ndarray, mase_denominator: float) -> dict[str, float | int | None]:
    y = np.asarray(y_true, dtype=float)
    pred = np.asarray(prediction, dtype=float)
    if not len(y):
        return {key: None for key in ("n", "MAE", "RMSE", "bias", "median_AE", "p90_AE", "p95_AE", "R2", "MASE")}
    error = pred - y
    absolute = np.abs(error)
    total = np.sum((y - y.mean()) ** 2)
    return {
        "n": int(len(y)),
        "MAE": float(absolute.mean()),
        "RMSE": float(np.sqrt(np.mean(error**2))),
        "bias": float(error.mean()),
        "median_AE": float(np.median(absolute)),
        "p90_AE": float(np.quantile(absolute, 0.90)),
        "p95_AE": float(np.quantile(absolute, 0.95)),
        "R2": float(1 - np.sum(error**2) / total) if total else None,
        "MASE": float(absolute.mean() / mase_denominator) if mase_denominator and np.isfinite(mase_denominator) else None,
    }


def warning_metrics(y_true: pd.Series | np.ndarray, probability: pd.Series | np.ndarray) -> dict[str, float | int | None]:
    """Threshold-free F2 metrics; an operational alarm threshold is intentionally absent."""
    y = np.asarray(y_true, dtype=int)
    p = np.clip(np.asarray(probability, dtype=float), 0, 1)
    if not len(y):
        return {key: None for key in ("n", "positive_n", "positive_rate", "PR_AUC", "Brier")}
    return {
        "n": int(len(y)),
        "positive_n": int(y.sum()),
        "positive_rate": float(y.mean()),
        "PR_AUC": float(average_precision_score(y, p)) if y.min() != y.max() else None,
        "Brier": float(brier_score_loss(y, p)),
    }


def calibration_table(y_true: pd.Series | np.ndarray, probability: pd.Series | np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Observed event frequency by equal-width probability bins, including empty bins."""
    y = np.asarray(y_true, dtype=int)
    p = np.clip(np.asarray(probability, dtype=float), 0, 1)
    edges = np.linspace(0, 1, bins + 1)
    group = np.digitize(p, edges[1:-1], right=True)
    rows = []
    for number in range(bins):
        mask = group == number
        rows.append({
            "bin": number,
            "lower": float(edges[number]),
            "upper": float(edges[number + 1]),
            "n": int(mask.sum()),
            "mean_probability": float(p[mask].mean()) if mask.any() else None,
            "observed_rate": float(y[mask].mean()) if mask.any() else None,
        })
    return pd.DataFrame(rows)


def rapping_window(df: pd.DataFrame, tag: str = "008B05154") -> pd.Series:
    """0–5 minute window after observed starts, unknown at the first 5 min of gaps."""
    validate_time(df)
    signal = df[tag]
    segment = segments(df)
    starts = signal.eq(1) & time_shift(signal, 1).eq(0)
    times = df.index.to_series()
    last = times.where(starts).groupby(segment).ffill()
    elapsed = (times - last).dt.total_seconds() / 60
    since_segment = (times - times.groupby(segment).transform("first")).dt.total_seconds() / 60
    known = elapsed.notna() | since_segment.gt(5)
    return elapsed.between(0, 5).astype("float32").where(known)


def strata(
    origin: pd.DataFrame,
    target: pd.Series,
    train: pd.DatetimeIndex,
    source: pd.DataFrame,
) -> dict[str, np.ndarray]:
    """Fixed F1 strata; target ranges use future truth and load cutoffs use training only."""
    result: dict[str, np.ndarray] = {"all": np.ones(len(origin), dtype=bool)}
    rap = rapping_window(source).reindex(origin.index)
    result["rapping_0_5min"] = rap.eq(1).to_numpy()
    result["outside_rapping"] = rap.eq(0).to_numpy()
    result["unknown_rapping"] = rap.isna().to_numpy()
    for lower, upper in ((-np.inf, 10), (10, 20), (20, 40), (40, np.inf)):
        result[f"target_{lower}_{upper}"] = (target.gt(lower) & target.le(upper)).to_numpy()
    result["cadence_60s"] = origin.index.second.to_numpy() == 0
    load = source["016A00219"] + source["016A00396"]
    edges = load.reindex(train).quantile([.25, .5, .75]).drop_duplicates().tolist()
    if len(edges) == 3:
        bins = pd.cut(load.reindex(origin.index), [-np.inf, *edges, np.inf])
        for interval in bins.cat.categories:
            result[f"load_{interval}"] = bins.eq(interval).to_numpy()
    for segment_id, rows in segments(origin).groupby(segments(origin)).groups.items():
        result[f"segment_{segment_id}"] = origin.index.isin(rows)
    return result


def observed_hours(frame: pd.DataFrame) -> float:
    return coverage(frame)["observed_days"] * 24


def threshold_episode_starts(target: pd.Series, threshold: float) -> int:
    """Observed starts of target exceedance episodes; no inference through gaps."""
    validate_time(target)
    segment = segments(target)
    above = target.gt(threshold)
    starts = above & ~above.groupby(segment).shift(1, fill_value=False)
    return int(starts.sum())


def paired_day_bootstrap(predictions: pd.DataFrame, model_names: list[str], count: int = 1000) -> dict[str, object]:
    """Descriptive paired calendar-day bootstrap of MAE and MAE difference to persistence."""
    days = predictions.index.normalize()
    losses = pd.DataFrame({name: (predictions[name] - predictions["y_true"]).abs() for name in model_names})
    sums = losses.groupby(days).sum()
    sizes = predictions.groupby(days).size().to_numpy()
    if len(sizes) < 2:
        return {"status": "insufficient_days"}
    rng = np.random.default_rng(42)
    draws = rng.integers(0, len(sizes), (count, len(sizes)))
    means = sums.to_numpy()[draws].sum(axis=1) / sizes[draws].sum(axis=1)[:, None]
    output: dict[str, object] = {"days": int(len(sizes)), "replicates": count, "method": "paired calendar-day bootstrap; descriptive"}
    persistence_idx = model_names.index("persistence")
    for position, name in enumerate(model_names):
        output[f"{name}_MAE_95pct"] = np.quantile(means[:, position], [.025, .975]).tolist()
        if name != "persistence":
            output[f"{name}_minus_persistence_MAE_95pct"] = np.quantile(means[:, position] - means[:, persistence_idx], [.025, .975]).tolist()
    return output
