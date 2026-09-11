import unittest

import numpy as np
import pandas as pd

from src.forecast_features import (
    TARGET,
    clean_forecast_data,
    direct_target,
    future_event_target,
    history_features,
    process_features,
)


def source_frame(rows=240):
    index = pd.date_range("2025-07-01", periods=rows, freq="10s")
    return pd.DataFrame(
        {
            TARGET: np.arange(rows, dtype=float),
            "process": np.linspace(0, 1, rows),
            "008B05154": [0] * 20 + [1] + [0] * (rows - 21),
        },
        index=index,
    )


SCHEMA = {"inputs": ["process", "008B05154"], "continuous": ["process"], "rapping": ["008B05154"]}


class ForecastFeatureTests(unittest.TestCase):
    def test_direct_target_requires_exact_future_timestamp_but_can_cross_gap(self):
        frame = source_frame().drop(source_frame().index[[3, 20]])
        target = direct_target(frame, 60)
        self.assertEqual(target.iloc[0], 6.0)
        missing_endpoint = source_frame().index[20]
        self.assertTrue(pd.isna(target.loc[missing_endpoint - pd.Timedelta(seconds=60)]))

    def test_history_respects_measurement_delay_and_future_changes(self):
        frame = source_frame()
        delayed = history_features(frame, measurement_delay_seconds=60)
        self.assertEqual(delayed.loc[frame.index[100], "dust_available"], 94.0)
        changed = frame.copy()
        changed.loc[frame.index[101]:, TARGET] += 10000
        unaffected = history_features(changed)
        original = history_features(frame)
        pd.testing.assert_frame_equal(original.loc[:frame.index[100]], unaffected.loc[:frame.index[100]])

    def test_history_and_process_lags_do_not_cross_a_gap(self):
        frame = source_frame()
        missing = frame.index[100]
        gapped = frame.drop(missing)
        first_after_gap = frame.index[101]
        history = history_features(gapped)
        process = process_features(gapped, SCHEMA)
        self.assertTrue(pd.isna(history.loc[first_after_gap, "dust_lag_1"]))
        self.assertTrue(pd.isna(process.loc[first_after_gap, "process_lag_6"]))

    def test_availability_delays_do_not_cross_a_gap(self):
        frame = source_frame()
        missing = frame.index[100]
        gapped = frame.drop(missing)
        first_after_gap = frame.index[101]
        history = history_features(gapped, measurement_delay_seconds=60)
        process = process_features(gapped, SCHEMA, availability_delay_seconds=60)
        self.assertTrue(pd.isna(history.loc[first_after_gap, "dust_available"]))
        self.assertTrue(pd.isna(process.loc[first_after_gap, "process"]))

    def test_complete_case_cleaning_does_not_fill_missing_values(self):
        frame = source_frame()
        frame.loc[frame.index[10], "process"] = np.nan
        clean = clean_forecast_data(frame, SCHEMA["inputs"])
        self.assertNotIn(frame.index[10], clean.index)

    def test_future_event_requires_complete_window_and_excludes_current_value(self):
        frame = source_frame(rows=30)
        frame[TARGET] = 0.0
        frame.loc[frame.index[0], TARGET] = 100
        frame.loc[frame.index[6], TARGET] = 25
        label = future_event_target(frame, 60, 20)
        self.assertEqual(label.loc[frame.index[0]], 1.0)
        self.assertEqual(label.loc[frame.index[20]], 0.0)
        gapped = frame.drop(frame.index[3])
        self.assertTrue(pd.isna(future_event_target(gapped, 60, 20).loc[frame.index[0]]))


if __name__ == "__main__":
    unittest.main()
