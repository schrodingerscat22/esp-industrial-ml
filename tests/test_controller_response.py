import unittest

import numpy as np
import pandas as pd

from src.controller_response import daily_placebo, event_starts, future_difference, gap_safe_difference


class ControllerResponseTest(unittest.TestCase):
    def test_difference_direction_and_future_target(self):
        index = pd.date_range("2025-01-01", periods=5, freq="10s")
        value = pd.Series([0., 1., 3., 6., 10.], index=index)
        self.assertEqual(gap_safe_difference(value, 1).iloc[3], 3.)
        self.assertEqual(future_difference(value, 1).iloc[2], 3.)

    def test_differences_do_not_cross_gap(self):
        index = pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 00:00:10", "2025-01-01 00:01:00"])
        value = pd.Series([1., 2., 8.], index=index)
        self.assertTrue(np.isnan(gap_safe_difference(value, 1).iloc[-1]))
        self.assertTrue(np.isnan(future_difference(value, 1).iloc[1]))

    def test_future_target_does_not_change_past_difference(self):
        index = pd.date_range("2025-01-01", periods=8, freq="10s")
        value = pd.Series(np.arange(8, dtype=float), index=index)
        original = future_difference(value, 2).iloc[1]
        changed = value.copy(); changed.iloc[-1] = 999.
        self.assertEqual(future_difference(changed, 2).iloc[1], original)

    def test_event_starts_find_one_positive_and_one_negative_episode(self):
        index = pd.date_range("2025-01-01", periods=30, freq="10s")
        diff = pd.Series([0.] * 10 + [5., 5.] + [0.] * 8 + [-4., -4.] + [0.] * 8, index=index)
        train = pd.Series(True, index=index)
        up, down, thresholds = event_starts(diff, train)
        self.assertEqual(int(up.sum()), 1)
        self.assertEqual(int(down.sum()), 1)
        self.assertGreater(thresholds["positive_threshold"], 0)
        self.assertLess(thresholds["negative_threshold"], 0)

    def test_placebo_stays_inside_day_and_breaks_aligned_signal(self):
        index = pd.date_range("2025-01-01", periods=500, freq="10s")
        signal = pd.Series(np.sin(np.arange(500, dtype=float) / 7), index=index)
        placebo = daily_placebo(signal, 60)
        self.assertTrue(placebo.iloc[:60].isna().all())
        self.assertEqual(placebo.iloc[60], signal.iloc[0])
        self.assertLess(placebo.dropna().corr(signal.loc[placebo.dropna().index]), 1.)


if __name__ == "__main__":
    unittest.main()
