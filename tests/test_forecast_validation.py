import unittest

import numpy as np
import pandas as pd

from src.forecast_features import TARGET
from src.forecast_validation import (
    ForecastFold,
    forecast_origins,
    mase_scale,
    point_metrics,
    rapping_window,
    strata,
    threshold_episode_starts,
)


def frame(rows=240):
    index = pd.date_range("2025-07-01", periods=rows, freq="10s")
    rapping = np.zeros(rows, dtype=int)
    if rows > 40:
        rapping[40] = 1
    return pd.DataFrame(
        {TARGET: np.arange(rows, dtype=float), "008B05154": rapping,
         "016A00219": np.arange(rows, dtype=float), "016A00396": np.arange(rows, dtype=float)},
        index=index,
    )


class ForecastValidationTests(unittest.TestCase):
    def test_origins_have_horizon_purge_on_both_fold_boundaries(self):
        data = frame()
        fold = ForecastFold("test", data.index[120], data.index[180])
        valid = pd.Series(True, index=data.index)
        label = data[TARGET]
        train, evaluate, diagnostics = forecast_origins(data.index, valid, label, fold, 60)
        self.assertEqual(train[-1], data.index[113])
        self.assertEqual(evaluate[-1], data.index[173])
        self.assertEqual(diagnostics["purged_train_origins"], 6)

    def test_mase_omits_pairs_that_cross_a_gap(self):
        data = frame(rows=20).drop(frame(rows=20).index[10])
        scale = mase_scale(data[TARGET], 10)
        self.assertEqual(scale, 1.0)

    def test_rapping_is_unknown_immediately_after_a_gap(self):
        data = frame(rows=100).drop(frame(rows=100).index[50])
        window = rapping_window(data)
        self.assertTrue(pd.isna(window.loc[pd.Timestamp("2025-07-01 00:08:30")]))
        self.assertEqual(window.loc[pd.Timestamp("2025-07-01 00:14:30")], 0.0)

    def test_strata_and_metrics_are_defined_for_regular_data(self):
        data = frame()
        origin = pd.DataFrame(index=data.index[120:180])
        groups = strata(origin, data.loc[origin.index, TARGET], data.index[:120], data)
        self.assertEqual(groups["all"].sum(), len(origin))
        self.assertTrue(groups["cadence_60s"].any())
        metrics = point_metrics(np.array([1, 2]), np.array([-1, 3]), 1.0)
        self.assertEqual(metrics["MAE"], 1.5)

    def test_episode_starts_are_not_inferred_through_gap(self):
        data = frame(rows=20)
        data.loc[data.index[8:13], TARGET] = 50
        data = data.drop(data.index[10])
        self.assertEqual(threshold_episode_starts(data[TARGET], 40), 2)


if __name__ == "__main__":
    unittest.main()
