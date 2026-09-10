"""Conservative 10-second time-series rules; no interpolation across missing data."""
import numpy as np
import pandas as pd

STEP = pd.Timedelta(seconds=10)


def validate_time(obj):
    idx = obj.index
    if not isinstance(idx, pd.DatetimeIndex) or idx.hasnans:
        raise ValueError("A non-null DatetimeIndex is required")
    if not idx.is_unique or not idx.is_monotonic_increasing:
        raise ValueError("Timestamps must be unique and sorted; resolve duplicates explicitly")


def segments(obj):
    validate_time(obj)
    return obj.index.to_series().diff().ne(STEP).cumsum()


def time_shift(series, periods):
    """Positive periods = past values, restricted to continuous observed segments."""
    return series.groupby(segments(series)).shift(periods)


def past_mean(series, minutes=5):
    """[t-window,t), all expected samples required; current target never included."""
    n = int(pd.Timedelta(minutes=minutes) / STEP)
    return series.groupby(segments(series), group_keys=False).transform(
        lambda s: s.shift(1).rolling(n, min_periods=n).mean()
    )


def lagged_corr(x, y, max_lag_samples):
    """corr(x(t), y(t+lag)); positive lag means x leads y. No gap crossing."""
    if not x.index.equals(y.index):
        raise ValueError("Signals must have identical timestamps")
    rows = []
    for lag in range(-max_lag_samples, max_lag_samples + 1):
        future_y = time_shift(y, -lag)
        valid = x.notna() & future_y.notna()
        rows.append(dict(lag_samples=lag, lag_minutes=lag / 6,
                         corr=x[valid].corr(future_y[valid]) if valid.sum() > 2 else np.nan,
                         n=int(valid.sum())))
    return pd.DataFrame(rows)


def rapping_starts(signal):
    return signal.eq(1) & time_shift(signal, 1).eq(0)


def complete_window(df, event_time, start_seconds, end_seconds):
    """Closed timestamp window, requiring all samples and finite selected signals."""
    validate_time(df)
    start = event_time + pd.Timedelta(seconds=start_seconds)
    end = event_time + pd.Timedelta(seconds=end_seconds)
    expected = pd.date_range(start, end, freq=STEP)
    window = df.loc[start:end]
    if not window.index.equals(expected) or not np.isfinite(window.to_numpy(dtype=float)).all():
        return None
    return window.copy()


def rapping_features(signal):
    starts = rapping_starts(signal)
    seg = segments(signal)
    times = signal.index.to_series()
    last = times.where(starts).groupby(seg).ffill()
    elapsed = (times - last).dt.total_seconds() / 60
    # Before first observed start, unknown for 5 min after segment begins.
    since_segment = (times - times.groupby(seg).transform('first')).dt.total_seconds() / 60
    known = elapsed.notna() | since_segment.gt(5)
    elapsed = elapsed.where(elapsed.le(5), -1).where(known)
    return pd.DataFrame({
        'rapping_3_collecting_start': starts.astype(int),
        'minutes_since_rapping_3_collecting_start_0_5': elapsed,
        'is_within_5min_after_rapping_3_collecting': elapsed.ge(0).astype(float).where(known),
    })


def tail_mask(p_rel, dust_rel, power_threshold=5., dust_threshold=5., recovery_seconds=60):
    """Post-excursion tail after LAST dust exceedance; >=60 s observed recovery.

    Input is the 90 left endpoints of [0,15 min). No excursion or right-censored
    recovery yields an empty mask, not evidence of absence of a later tail.
    """
    above = np.flatnonzero(dust_rel.to_numpy() > dust_threshold)
    mask = pd.Series(False, index=p_rel.index)
    if not len(above):
        return mask
    start = int(above[-1]) + 1
    if (len(dust_rel) - start) * 10 < recovery_seconds:
        return mask
    mask.iloc[start:] = (p_rel.iloc[start:] > power_threshold) & (dust_rel.iloc[start:] <= dust_threshold)
    return mask


def coverage(df):
    """Observed interval exposure: only adjacent, finite pairs exactly 10 s apart."""
    validate_time(df)
    valid = pd.Series(np.isfinite(df.to_numpy(dtype=float)).all(axis=1), index=df.index)
    dt = df.index.to_series().diff()
    observed = float((dt.eq(STEP) & valid & valid.shift(1, fill_value=False)).sum() * 10)
    span = float((df.index[-1] - df.index[0]).total_seconds()) if len(df) else 0.
    return dict(observed_days=observed / 86400, calendar_days=span / 86400,
                coverage_fraction=observed / span if span else np.nan,
                gap_count=int(dt.gt(STEP).sum()))
