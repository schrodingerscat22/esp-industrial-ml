import unittest
import numpy as np
import pandas as pd
from src.time_analysis import (past_mean, time_shift, lagged_corr, rapping_starts,
                               rapping_features, complete_window, coverage, tail_mask)


class TimeRulesTest(unittest.TestCase):
    def setUp(self):
        self.idx = pd.date_range('2020-01-01', periods=200, freq='10s')

    def test_target_perturbation_does_not_change_current_feature(self):
        s = pd.Series(np.arange(200.), index=self.idx)
        before = past_mean(s)
        s.iloc[100:] = -999
        self.assertEqual(before.iloc[100], past_mean(s).iloc[100])
        self.assertEqual(before.iloc[100], np.mean(np.arange(70, 100)))

    def test_both_lag_directions(self):
        x = pd.Series(np.random.default_rng(5).normal(size=200), index=self.idx)
        y = x.shift(7)
        for a, b, expected in [(x, y, 7), (y, x, -7)]:
            result = lagged_corr(a, b, 12)
            best = result.loc[result['corr'].idxmax()]
            self.assertEqual(best.lag_samples, expected)
            self.assertAlmostEqual(best['corr'], 1.)

    def test_gap_resets_history_and_cannot_make_start(self):
        s = pd.Series(0., index=self.idx).drop(self.idx[50:80])
        s.loc[self.idx[80]] = 1
        self.assertTrue(np.isnan(time_shift(s, 1).loc[self.idx[80]]))
        self.assertFalse(rapping_starts(s).loc[self.idx[80]])
        self.assertTrue(np.isnan(past_mean(s).loc[self.idx[90]]))
        self.assertTrue(np.isnan(rapping_features(s).loc[self.idx[80]].iloc[-1]))

    def test_complete_window_rejects_gap_missing_and_edge(self):
        df = pd.DataFrame({'x': 1.}, index=self.idx)
        self.assertEqual(len(complete_window(df, self.idx[20], -100, 100)), 21)
        self.assertIsNone(complete_window(df.drop(self.idx[21]), self.idx[20], -100, 100))
        df.loc[self.idx[21], 'x'] = np.nan
        self.assertIsNone(complete_window(df, self.idx[20], -100, 100))
        self.assertIsNone(complete_window(df, self.idx[0], -10, 100))

    def test_coverage_excludes_gap_and_last_unobserved_interval(self):
        df = pd.DataFrame({'x': 1.}, index=self.idx[:10].append(self.idx[20:30]))
        self.assertAlmostEqual(coverage(df)['observed_days'] * 86400, 180.)
        self.assertEqual(coverage(df)['gap_count'], 1)

    def test_tail_follows_last_excursion_and_is_censored(self):
        p = pd.Series(60., index=self.idx[:90])
        dust = p * 0
        self.assertFalse(tail_mask(p, dust).any())
        dust.iloc[10:20] = 10
        mask = tail_mask(p, dust)
        self.assertFalse(mask.iloc[:20].any())
        self.assertEqual(mask.sum(), 70)
        self.assertAlmostEqual(p.sum() * 10 / 3600, 15.)  # exactly 15 min
        dust.iloc[87] = 10
        self.assertFalse(tail_mask(p, dust).any())

    def test_signed_sections_reconcile_on_common_mask(self):
        p1 = pd.Series(20., index=self.idx[:90])
        p2, p3 = p1 * -.5, p1 * .5
        dust = p1 * 0
        dust.iloc[:10] = 10
        mask = tail_mask(p1 + p2 + p3, dust)
        total = (p1 + p2 + p3).where(mask, 0).sum()
        self.assertAlmostEqual(total, sum(s.where(mask, 0).sum() for s in [p1,p2,p3]))

    def test_duplicate_and_unsorted_timestamps_fail(self):
        for idx in [self.idx[:3][::-1], self.idx[:3].append(self.idx[:1])]:
            with self.assertRaises(ValueError):
                time_shift(pd.Series(1., index=idx), 1)


if __name__ == '__main__':
    unittest.main()
