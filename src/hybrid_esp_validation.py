"""Chronological splitting, common metrics and bounded support for the H pilot."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler

from src.forecast_validation import DEVELOPMENT_FOLDS


def d1_split(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    fold = next(item for item in DEVELOPMENT_FOLDS if item.name == "D1")
    eligible = frame["valid_origin"] & frame["dust_mg_Nm3"].notna()
    before = frame.index < fold.evaluation_start
    dates = pd.DatetimeIndex(frame.index[eligible & before].normalize().unique()).sort_values()
    if len(dates) < 5:
        raise ValueError("D1 requires at least five complete dates before evaluation")
    calibration_dates = dates[-2:]
    fit = eligible & before & ~frame.index.normalize().isin(calibration_dates)
    calibration = eligible & before & frame.index.normalize().isin(calibration_dates)
    evaluation = eligible & (frame.index >= fold.evaluation_start) & (frame.index < fold.evaluation_end)
    return fit, calibration, evaluation


def metrics(y: np.ndarray, pred: np.ndarray) -> dict[str, float | int | None]:
    y, pred = np.asarray(y, dtype=float), np.asarray(pred, dtype=float)
    error = pred - y
    return {"n": int(len(y)), "MAE": float(mean_absolute_error(y, pred)),
            "RMSE": float(mean_squared_error(y, pred) ** .5), "bias": float(error.mean()),
            "R2": float(r2_score(y, pred)) if len(y) and np.var(y) else None,
            "P90_AE": float(np.quantile(abs(error), .9)), "P95_AE": float(np.quantile(abs(error), .95))}


class Support:
    def __init__(self, columns: list[str], reference_limit: int = 20_000):
        self.columns = columns; self.reference_limit = reference_limit

    def fit(self, frame: pd.DataFrame) -> "Support":
        source = frame[self.columns].replace([np.inf, -np.inf], np.nan).dropna()
        if len(source) > self.reference_limit:
            source = source.iloc[np.linspace(0, len(source) - 1, self.reference_limit, dtype=int)]
        self.scaler = RobustScaler().fit(source)
        value = self.scaler.transform(source)
        self.model = NearestNeighbors(n_neighbors=min(20, len(value))).fit(value)
        distances, _ = self.model.kneighbors(value)
        self.d95 = float(np.quantile(distances[:, -1], .95))
        return self

    def classify(self, frame: pd.DataFrame) -> pd.Series:
        output = pd.Series("outside", index=frame.index, dtype="string")
        clean = frame[self.columns].replace([np.inf, -np.inf], np.nan).dropna()
        if not len(clean) or not self.d95 > 0:
            return output
        distance, _ = self.model.kneighbors(self.scaler.transform(clean))
        far = distance[:, -1]
        output.loc[clean.index] = np.where(far <= self.d95, "supported", np.where(far < 2 * self.d95, "marginal", "outside"))
        return output
