"""Small, gap-safe hybrid ESP pilot models; parameters are effective, not plant physics."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from sklearn.preprocessing import RobustScaler

from src.electrical_state import FIELDS, RAPPING_TAGS, derive_electrical_state, process_context
from src.time_analysis import STEP, segments, time_shift, validate_time

PROCESS = (
    "generator_MW", "flue_flow_thousand_m3_h", "flue_temperature_mean_C",
    "flue_temperature_L_minus_R_C", "flue_moisture_pct", "O2_before_OPP_L_pct",
    "O2_before_OPP_R_pct", "burner_008B01474_on", "burner_008B01479_on",
    "burner_008B01484_on", "burner_008B01489_on",
)
KERNEL_TAUS = (30, 120, 300)
HISTORY_SAMPLES = 90  # 15 minutes at 10 seconds
CORE_FIT_MAX_ROWS = 1_000


def _continuous_valid(mask: pd.Series, samples: int) -> pd.Series:
    """True only after `samples` consecutive observed, finite input rows."""
    validate_time(mask)
    run = mask.astype("int64").groupby((~mask | mask.index.to_series().diff().ne(STEP)).cumsum()).cumsum()
    return run.ge(samples)


def _causal_kernel(starts: pd.Series, tau_seconds: int) -> pd.Series:
    """Finite causal rapping kernel, never crossing an observed time gap."""
    validate_time(starts)
    samples = 900 // int(STEP.total_seconds())
    offset = np.arange(samples + 1, dtype=float) * STEP.total_seconds()
    taper = np.where(offset <= 600, 1.0, (900 - offset) / 300)
    kernel = (offset / tau_seconds) * np.exp(1 - offset / tau_seconds) * taper
    # Convolution is computed per timestamp-continuous segment. It is exactly the
    # causal sum of shifted starts, without 91 repeated whole-series groupbys.
    result = np.zeros(len(starts), dtype=np.float64)
    for _, positions in starts.groupby(segments(starts), sort=False).indices.items():
        values = starts.to_numpy(dtype=float)[positions]
        result[positions] = np.convolve(values, kernel, mode="full")[:len(values)]
    return pd.Series(result, index=starts.index, dtype="float32")


def build_hybrid_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    """Features observable at t. Invalid rows include gaps and signal-level breaks."""
    validate_time(raw)
    state = derive_electrical_state(raw)
    context = process_context(raw)
    frame = pd.DataFrame(index=raw.index)
    frame["dust_mg_Nm3"] = state["dust_mg_Nm3"].astype("float32")
    frame["dust_lag_60s"] = time_shift(frame["dust_mg_Nm3"], 6).astype("float32")
    frame["flow_proxy"] = context["flue_flow_thousand_m3_h"]
    for name in PROCESS:
        frame[name] = context[name]
        frame[f"{name}_mean_5m"] = context[name].groupby(segments(context[name]), group_keys=False).transform(
            lambda value: value.shift(1).rolling(30, min_periods=30).mean()
        )
        frame[f"{name}_diff_5m"] = context[name] - time_shift(context[name], 30)
    voltage_columns, current_columns = [], []
    for field in FIELDS:
        voltage, current = f"field_{field.number}_U_kV", f"field_{field.number}_I_mA"
        frame[voltage] = state[voltage]
        frame[current] = state[current]
        voltage_columns.append(voltage); current_columns.append(current)
    frame["chi_raw"] = frame[voltage_columns].pow(2).mean(axis=1) / frame["flow_proxy"]
    rapping_columns = []
    for tag in RAPPING_TAGS:
        starts = raw[tag].eq(1) & time_shift(raw[tag], 1).eq(0)
        frame[f"rap_{tag}_state"] = raw[tag].astype("float32")
        rapping_columns.append(f"rap_{tag}_state")
        for tau in KERNEL_TAUS:
            name = f"rap_{tag}_kernel_{tau}s"
            frame[name] = _causal_kernel(starts, tau)
            rapping_columns.append(name)
    required = list(frame.columns)
    finite = pd.Series(np.isfinite(frame[required].to_numpy(dtype=float)).all(axis=1), index=frame.index)
    frame["valid_origin"] = _continuous_valid(finite, HISTORY_SAMPLES)
    process_columns = [name for name in frame if name in PROCESS or name.endswith("_mean_5m") or name.endswith("_diff_5m")]
    common = process_columns + voltage_columns + current_columns + ["chi_raw"] + rapping_columns
    baseline = process_columns + rapping_columns
    return frame.astype({"valid_origin": "bool"}), {"common": common, "baseline": baseline,
        "process": process_columns, "voltage": voltage_columns, "current": current_columns,
        "rapping": rapping_columns}


@dataclass
class CoreFit:
    scaler: RobustScaler
    process_columns: list[str]
    rapping_columns: list[str]
    voltage_columns: list[str]
    flow_column: str
    theta: np.ndarray
    success: bool
    cost: float
    nfev: int
    at_bound_count: int
    fit_rows: int

    def _design(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        z = self.scaler.transform(frame[self.process_columns])
        voltage = frame[self.voltage_columns].to_numpy(dtype=float)
        median_u = np.maximum(np.nanmedian(voltage, axis=0), 1e-6)
        # Medians are deliberately stored in theta tail after the fitted coefficients.
        medians = self.theta[-len(self.voltage_columns)-1:-1]
        chi = np.mean((voltage / medians) ** 2, axis=1) / (frame[self.flow_column].to_numpy(dtype=float) / self.theta[-1])
        rap = frame[self.rapping_columns].to_numpy(dtype=float)
        return z, chi, rap

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        z, chi, rap = self._design(frame)
        p = len(self.process_columns); r = len(self.rapping_columns)
        base = self.theta[0] + z @ self.theta[1:1 + p] - self.theta[1 + p] * (chi - 1)
        additive = rap @ self.theta[2 + p:2 + p + r]
        return np.maximum(np.exp(np.clip(base, -20, 20)) + additive, 0.0)


def fit_core(frame: pd.DataFrame, process_columns: list[str], rapping_columns: list[str], voltage_columns: list[str]) -> CoreFit:
    """Fit effective constrained core. Its coefficients are not material parameters."""
    x = frame.dropna(subset=process_columns + rapping_columns + voltage_columns + ["flow_proxy", "dust_mg_Nm3"])
    if len(x) < 100:
        raise ValueError("Too few complete rows for the core")
    # Deterministic time-spread subsample limits numerical calibration cost. The
    # learned correction and all reported metrics still use the full common set.
    if len(x) > CORE_FIT_MAX_ROWS:
        x = x.iloc[np.linspace(0, len(x) - 1, CORE_FIT_MAX_ROWS, dtype=int)]
    scaler = RobustScaler().fit(x[process_columns])
    z = scaler.transform(x[process_columns])
    voltage = x[voltage_columns].to_numpy(dtype=float)
    u_median = np.maximum(np.median(voltage, axis=0), 1e-6)
    flow_median = max(float(x["flow_proxy"].median()), 1e-6)
    chi = np.mean((voltage / u_median) ** 2, axis=1) / (x["flow_proxy"].to_numpy(dtype=float) / flow_median)
    rap = x[rapping_columns].to_numpy(dtype=float)
    y = np.log1p(x["dust_mg_Nm3"].to_numpy(dtype=float))
    p, r = z.shape[1], rap.shape[1]

    def residual(theta: np.ndarray) -> np.ndarray:
        base = theta[0] + z @ theta[1:1 + p] - theta[1 + p] * (chi - 1)
        prediction = np.exp(np.clip(base, -20, 20)) + rap @ theta[2 + p:2 + p + r]
        penalty = np.sqrt(.01) * theta[1:2 + p + r]  # intercept is excluded
        return np.r_[np.log1p(np.maximum(prediction, 0)) - y, penalty]

    initial = np.r_[np.log(max(float(np.median(x["dust_mg_Nm3"])), 1e-3)), np.zeros(p), .1, np.zeros(r)]
    lower = np.r_[[-20], np.full(p, -10.), [0.], np.zeros(r)]
    upper = np.r_[[20], np.full(p, 10.), [20.], np.full(r, 1e4)]
    starts = (initial, initial + np.r_[0, np.full(p, .05), .2, np.zeros(r)], initial + np.r_[0, np.full(p, -.05), .5, np.zeros(r)])
    fits = [least_squares(residual, np.clip(start, lower + 1e-9, upper - 1e-9), bounds=(lower, upper), max_nfev=200) for start in starts]
    best = min(fits, key=lambda item: item.cost)
    at_bound = np.isclose(best.x, lower, atol=1e-6) | np.isclose(best.x, upper, atol=1e-6)
    theta = np.r_[best.x, u_median, flow_median]
    return CoreFit(scaler, process_columns, rapping_columns, voltage_columns, "flow_proxy", theta,
                   bool(best.success), float(best.cost), int(best.nfev), int(at_bound.sum()), len(x))


def synthetic_step(inlet: float, k: np.ndarray, stored: np.ndarray, rapping_fraction: np.ndarray,
                   hopper_fraction: np.ndarray) -> tuple[float, np.ndarray, float]:
    """One dimensionless serial ESP step; returns outlet, new stored mass, hopper flux."""
    incoming, hopper = float(inlet), 0.0
    next_stored = np.asarray(stored, dtype=float).copy()
    for j, kj in enumerate(np.asarray(k, dtype=float)):
        release = min(next_stored[j], max(float(rapping_fraction[j]), 0.0) * next_stored[j])
        to_hopper = min(release, max(float(hopper_fraction[j]), 0.0) * release)
        reentrained = release - to_hopper
        next_stored[j] -= release
        collected = (1 - np.exp(-max(kj, 0.0))) * incoming
        next_stored[j] += collected
        incoming = incoming - collected + reentrained
        hopper += to_hopper
    return incoming, next_stored, hopper
