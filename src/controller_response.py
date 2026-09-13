"""Leakage-safe descriptive audit of delayed electrical response after dust changes."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.electrical_state import FIELDS, RAPPING_TAGS, derive_electrical_state, process_context
from src.time_analysis import STEP, complete_window, rapping_starts, segments, time_shift, validate_time

HORIZONS_SECONDS = (10, 30, 60, 120, 180, 300, 600)
PAST_SAMPLES = (1, 3, 6, 12, 18, 30)
PROCESS_COLUMNS = ("generator_MW", "flue_flow_thousand_m3_h", "flue_temperature_mean_C",
                   "flue_temperature_L_minus_R_C", "flue_moisture_pct", "O2_before_OPP_L_pct",
                   "O2_before_OPP_R_pct")


def gap_safe_difference(series: pd.Series, samples: int) -> pd.Series:
    """Current minus past value; neither side may cross an observed time gap."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    return (series - time_shift(series, samples)).astype("float32")


def future_difference(series: pd.Series, samples: int) -> pd.Series:
    """Future minus current, where positive `samples` is a true future horizon."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    return (time_shift(series, -samples) - series).astype("float32")


def rapping_phase(state: pd.DataFrame) -> pd.DataFrame:
    """Known current rapping phase for all tags, retaining missing/unknown as NaN."""
    out = pd.DataFrame(index=state.index)
    for tag in RAPPING_TAGS:
        elapsed = state[f"rapping_{tag}_minutes_since_0_15"]
        out[f"phase_{tag}"] = elapsed.where(elapsed.ge(-1) & elapsed.notna()).astype("float32")
        out[f"active_{tag}"] = elapsed.between(0, 15).astype("float32").where(elapsed.notna())
    return out


def electrical_targets(state: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=state.index)
    out["P_total_kW"] = state["total_P_tag_kW"]
    out["U_mean_kV"] = state[[f"field_{field.number}_U_kV" for field in FIELDS]].mean(axis=1)
    for field in FIELDS:
        prefix = f"field_{field.number}"
        for value in ("P_tag_kW", "U_kV", "I_mA"):
            out[f"{prefix}_{value}"] = state[f"{prefix}_{value}"]
    return out.astype("float32")


def _history(frame: pd.DataFrame, columns: list[str], prefix: str) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for column in columns:
        for lag in PAST_SAMPLES:
            out[f"{prefix}{column}_lag_{lag * 10}s"] = time_shift(frame[column], lag)
    return out


def build_audit_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Build only features observable at `t`, with targets added separately by horizon."""
    state = derive_electrical_state(raw)
    context = process_context(raw)
    values = electrical_targets(state)
    dust = state["dust_mg_Nm3"].astype("float32")
    phase = rapping_phase(state)
    frame = pd.DataFrame(index=raw.index)
    electrical_columns = list(values.columns)
    base_history = _history(values, electrical_columns, "")
    frame = frame.join(base_history)
    frame = frame.join(context)
    frame = frame.join(phase)
    radians = 2 * np.pi * (frame.index.hour * 3600 + frame.index.minute * 60 + frame.index.second) / 86400
    frame["tod_sin"] = np.sin(radians).astype("float32")
    frame["tod_cos"] = np.cos(radians).astype("float32")
    dust_columns = []
    frame["dust_level"] = dust; dust_columns.append("dust_level")
    for lag in PAST_SAMPLES:
        name = f"dust_lag_{lag * 10}s"; frame[name] = time_shift(dust, lag); dust_columns.append(name)
    for samples in (1, 3, 6, 12, 18, 30):
        name = f"dust_diff_{samples * 10}s"; frame[name] = gap_safe_difference(dust, samples); dust_columns.append(name)
    base_columns = list(base_history.columns) + list(context.columns) + list(phase.columns) + ["tod_sin", "tod_cos"]
    frame = frame.copy().astype("float32")
    return frame, {"base": base_columns, "dust": dust_columns, "targets": electrical_columns, "dust_level": ["dust_level"]}


def add_future_targets(frame: pd.DataFrame, raw: pd.DataFrame, horizon_seconds: int) -> pd.DataFrame:
    """Append future electrical deltas without ever exposing them as predictors."""
    if horizon_seconds not in HORIZONS_SECONDS:
        raise ValueError("unsupported horizon")
    samples = horizon_seconds // 10
    state = derive_electrical_state(raw)
    values = electrical_targets(state)
    out = frame.copy()
    for column in values:
        out[f"target_{column}_h{horizon_seconds}s"] = future_difference(values[column], samples)
    out["dust_diff_60s_for_events"] = gap_safe_difference(state["dust_mg_Nm3"], 6)
    return out


@dataclass(frozen=True)
class ResponseFold:
    name: str
    evaluation_start: pd.Timestamp
    evaluation_end: pd.Timestamp


FOLDS = (
    ResponseFold("D1", pd.Timestamp("2025-07-12"), pd.Timestamp("2025-07-17")),
    ResponseFold("D2", pd.Timestamp("2025-07-17"), pd.Timestamp("2025-07-22")),
    ResponseFold("D3", pd.Timestamp("2025-07-22"), pd.Timestamp("2025-07-27")),
)


def fold_masks(index: pd.DatetimeIndex, fold: ResponseFold, horizon_seconds: int) -> tuple[pd.Series, pd.Series]:
    horizon = pd.Timedelta(seconds=horizon_seconds)
    train = pd.Series(index < fold.evaluation_start - horizon, index=index)
    evaluation = pd.Series((index >= fold.evaluation_start) & (index < fold.evaluation_end - horizon), index=index)
    return train, evaluation


def _metrics(y: pd.Series, prediction: np.ndarray) -> dict[str, float | int]:
    return {"n": int(len(y)), "MAE": float(mean_absolute_error(y, prediction)),
            "RMSE": float(mean_squared_error(y, prediction) ** .5), "R2": float(r2_score(y, prediction))}


def fit_compare(frame: pd.DataFrame, schema: dict[str, list[str]], horizon_seconds: int, alpha: float = 10.0) -> pd.DataFrame:
    """Chronological Ridge comparison; dust features are the only model difference."""
    rows = []
    target_columns = [f"target_{name}_h{horizon_seconds}s" for name in schema["targets"]]
    for fold in FOLDS:
        train_time, eval_time = fold_masks(frame.index, fold, horizon_seconds)
        for target in target_columns:
            common = frame[schema["base"] + schema["dust"] + [target]].replace([np.inf, -np.inf], np.nan).dropna()
            train = common.loc[train_time.reindex(common.index, fill_value=False)]
            evaluate = common.loc[eval_time.reindex(common.index, fill_value=False)]
            for name, features in (("base", schema["base"]), ("base_plus_dust", schema["base"] + schema["dust"])):
                model = make_pipeline(StandardScaler(), Ridge(alpha=alpha))
                model.fit(train[features], train[target])
                prediction = model.predict(evaluate[features])
                row = {"fold": fold.name, "horizon_seconds": horizon_seconds, "target": target.removeprefix("target_").removesuffix(f"_h{horizon_seconds}s"),
                       "model": name, **_metrics(evaluate[target], prediction)}
                rows.append(row)
    metrics = pd.DataFrame(rows)
    paired = metrics.pivot(index=["fold", "horizon_seconds", "target"], columns="model", values=["MAE", "RMSE", "R2"]).reset_index()
    paired.columns = ["_".join(filter(None, map(str, column))).rstrip("_") for column in paired.columns]
    for metric in ("MAE", "RMSE", "R2"):
        paired[f"delta_{metric}_dust_minus_base"] = paired[f"{metric}_base_plus_dust"] - paired[f"{metric}_base"]
    return metrics.merge(paired, on=["fold", "horizon_seconds", "target"], how="left")


def dust_innovation(frame: pd.DataFrame, schema: dict[str, list[str]], alpha: float = 10.0) -> tuple[pd.Series, pd.DataFrame]:
    """Out-of-fold dust residual from past dust, process, rapping and time only."""
    features = [column for column in schema["base"] if not column.startswith("field_") and not column.startswith("P_total") and not column.startswith("U_mean")]
    features += [column for column in schema["dust"] if column.startswith("dust_lag_")]
    work = frame[features + ["dust_level"]].replace([np.inf, -np.inf], np.nan).dropna()
    innovation = pd.Series(np.nan, index=frame.index, dtype="float32")
    rows = []
    for fold in FOLDS:
        train_mask, eval_mask = fold_masks(work.index, fold, 10)
        train, evaluate = work.loc[train_mask], work.loc[eval_mask]
        model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(train[features], train["dust_level"])
        predicted = model.predict(evaluate[features])
        innovation.loc[evaluate.index] = (evaluate["dust_level"] - predicted).astype("float32")
        rows.append({"fold": fold.name, "n_train": len(train), "n_evaluation": len(evaluate), **_metrics(evaluate["dust_level"], predicted)})
    return innovation, pd.DataFrame(rows)


def local_projection(frame: pd.DataFrame, schema: dict[str, list[str]], horizon_seconds: int,
                     alpha: float = 10.0) -> pd.DataFrame:
    """Descriptive conditional coefficient of out-of-fold dust innovation by horizon."""
    rows = []
    targets = [f"target_{name}_h{horizon_seconds}s" for name in schema["targets"]]
    dust_features = [column for column in schema["base"] if not column.startswith("field_") and not column.startswith("P_total") and not column.startswith("U_mean")]
    dust_features += [column for column in schema["dust"] if column.startswith("dust_lag_")]
    features = schema["base"] + ["dust_innovation"]
    for fold in FOLDS:
        train_time, evaluate_time = fold_masks(frame.index, fold, horizon_seconds)
        dust_work = frame[dust_features + ["dust_level"]].replace([np.inf, -np.inf], np.nan).dropna()
        dust_train = dust_work.loc[train_time.reindex(dust_work.index, fill_value=False)]
        dust_model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(dust_train[dust_features], dust_train["dust_level"])
        innovation = pd.Series(np.nan, index=frame.index, dtype="float32")
        for subset in (dust_train, dust_work.loc[evaluate_time.reindex(dust_work.index, fill_value=False)]):
            innovation.loc[subset.index] = (subset["dust_level"] - dust_model.predict(subset[dust_features])).astype("float32")
        work = frame.assign(dust_innovation=innovation)
        for target in targets:
            common = work[features + [target]].replace([np.inf, -np.inf], np.nan).dropna()
            train = common.loc[train_time.reindex(common.index, fill_value=False)]
            evaluate = common.loc[evaluate_time.reindex(common.index, fill_value=False)]
            model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(train[features], train[target])
            scaler, ridge = model.steps[0][1], model.steps[1][1]
            coefficient = float(ridge.coef_[features.index("dust_innovation")] / scaler.scale_[features.index("dust_innovation")])
            daily_betas = []
            for _, day_frame in train.groupby(train.index.normalize()):
                if len(day_frame) < 30:
                    continue
                day_model = make_pipeline(StandardScaler(), Ridge(alpha=alpha)).fit(day_frame[features], day_frame[target])
                day_scaler, day_ridge = day_model.steps[0][1], day_model.steps[1][1]
                daily_betas.append(float(day_ridge.coef_[features.index("dust_innovation")] / day_scaler.scale_[features.index("dust_innovation")]))
            if len(daily_betas) >= 3:
                rng = np.random.default_rng(abs(hash((fold.name, target, horizon_seconds))) % (2**32))
                boot = [np.median(rng.choice(daily_betas, size=len(daily_betas), replace=True)) for _ in range(200)]
                ci_low, ci_high = float(np.quantile(boot, .025)), float(np.quantile(boot, .975))
            else:
                ci_low = ci_high = np.nan
            rows.append({"fold": fold.name, "horizon_seconds": horizon_seconds,
                         "target": target.removeprefix("target_").removesuffix(f"_h{horizon_seconds}s"),
                         "beta_innovation": coefficient, "beta_bootstrap_day_ci_low": ci_low,
                         "beta_bootstrap_day_ci_high": ci_high, "bootstrap_days": len(daily_betas), "n": len(evaluate),
                         **_metrics(evaluate[target], model.predict(evaluate[features]))})
    return pd.DataFrame(rows)


def event_starts(dust_diff: pd.Series, train_mask: pd.Series) -> tuple[pd.Series, pd.Series, dict[str, float]]:
    """Train-defined symmetric thresholds and one start per contiguous episode."""
    train_values = dust_diff[train_mask & dust_diff.notna()]
    high, low = float(train_values.quantile(.95)), float(train_values.quantile(.05))
    positive = dust_diff.ge(high); negative = dust_diff.le(low)
    return positive & ~time_shift(positive.astype(float), 1).fillna(0).astype(bool), negative & ~time_shift(negative.astype(float), 1).fillna(0).astype(bool), {"positive_threshold": high, "negative_threshold": low}


def daily_placebo(series: pd.Series, shift_samples: int = 180) -> pd.Series:
    """Fixed within-day shift used only as a negative-control dust feature."""
    validate_time(series)
    if shift_samples <= 0:
        raise ValueError("shift_samples must be positive")
    return series.groupby(series.index.normalize()).shift(shift_samples)


def response_events(frame: pd.DataFrame, raw: pd.DataFrame, schema: dict[str, list[str]], horizon_seconds: int = 600) -> pd.DataFrame:
    """Event-level directional response; event windows cannot cross gaps."""
    state = derive_electrical_state(raw); values = electrical_targets(state)
    all_active = rapping_phase(state)[[f"active_{tag}" for tag in RAPPING_TAGS]].max(axis=1)
    rows = []
    for fold in FOLDS:
        train, evaluate = fold_masks(frame.index, fold, horizon_seconds)
        up, down, thresholds = event_starts(frame["dust_diff_60s_for_events"], train)
        for direction, starts in (("increase", up), ("decrease", down)):
            for when in frame.index[starts & evaluate]:
                window = complete_window(pd.concat((values, all_active.rename("any_rapping")), axis=1), when, 0, horizon_seconds)
                if window is None:
                    continue
                response = window.iloc[-1] - window.iloc[0]
                for condition, accepted in (("all", True), ("outside_all_rapping", bool(window.any_rapping.eq(0).all()))):
                    if not accepted:
                        continue
                    for target in values:
                        rows.append({"fold": fold.name, "direction": direction, "condition": condition, "event_time": when,
                                     "target": target, "dust_diff_60s": frame.at[when, "dust_diff_60s_for_events"],
                                     "response_horizon_seconds": horizon_seconds, "response": response[target], **thresholds})
    return pd.DataFrame(rows)
