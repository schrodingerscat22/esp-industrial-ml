"""Audited online nowcasting features; no filling, future target or gap crossing."""
import numpy as np
import pandas as pd
from src.time_analysis import segments, validate_time

TARGET = '008A01345'
LAGS = (1, 3, 6, 12, 30, 60, 180)
WINDOWS = (6, 30, 60, 180)
DIFFS = (1, 6, 30, 60)


def clean_inputs(df, input_cols):
    validate_time(df)
    if TARGET in input_cols or len(set(input_cols)) != len(input_cols):
        raise ValueError('Input schema must be unique and exclude the target')
    selected = df[[TARGET] + list(input_cols)].replace([np.inf, -np.inf], np.nan)
    return selected.dropna().copy()  # never impute labels or bridge missing states


def fit_schema(train, input_cols):
    """Signal selection uses train only; schema remains fixed during evaluation."""
    if TARGET in input_cols:
        raise ValueError('Current target cannot be a process feature')
    return {'inputs': list(input_cols),
            'continuous': [c for c in input_cols if train[c].nunique() > 10]}


def process_features(df, schema):
    """x(t) is assumed available at t. Rolling includes current PROCESS signal."""
    cols, analog = schema['inputs'], schema['continuous']
    if TARGET in cols or not set(analog).issubset(cols):
        raise ValueError('Invalid process schema')
    seg = segments(df)
    base = df[cols].astype('float32')
    parts = [base]
    for lag in LAGS:
        parts.append(base.groupby(seg).shift(lag).add_suffix(f'_lag_{lag}'))
    continuous = base[analog]
    for n in WINDOWS:
        rolling = continuous.groupby(seg).rolling(n, min_periods=n)
        for stat in ('mean', 'std'):
            part = getattr(rolling, stat)().reset_index(level=0, drop=True).reindex(df.index)
            parts.append(part.astype('float32').add_suffix(f'_roll_{stat}_{n}'))
    for n in DIFFS:
        parts.append(continuous.groupby(seg).diff(n).add_suffix(f'_diff_{n}'))
    return pd.concat(parts, axis=1)


def dust_history(df):
    """Every feature uses y no later than t-10 s, including historical differences."""
    seg = segments(df)
    y = df[TARGET].astype('float32')
    previous = y.groupby(seg).shift(1)
    parts = {f'dust_lag_{n}': y.groupby(seg).shift(n) for n in LAGS}
    for n in WINDOWS:
        rolling = previous.groupby(seg).rolling(n, min_periods=n)
        for stat in ('mean', 'std'):
            parts[f'dust_past_{stat}_{n}'] = getattr(rolling, stat)().reset_index(level=0, drop=True).reindex(df.index)
    for n in DIFFS:
        parts[f'dust_past_diff_{n}'] = previous - y.groupby(seg).shift(n + 1)
    return pd.DataFrame(parts, index=df.index).astype('float32')


def chronological_blocks(index):
    """Freeze boundaries before feature generation; two expanding validation folds."""
    if len(index) < 20 or not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError('At least 20 ordered unique timestamps required')
    p40, p60, p80 = [index[int(len(index) * f)] for f in (.4, .6, .8)]
    return [('validation_1', p40, p60), ('validation_2', p60, p80), ('test', p80, None)]
