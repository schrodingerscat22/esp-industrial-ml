import unittest

import numpy as np
import pandas as pd

from src.hybrid_esp import _causal_kernel, _continuous_valid, fit_core, synthetic_step


class HybridEspPhysicsTests(unittest.TestCase):
    def test_serial_balance_and_nonnegative_store(self):
        outlet, stored, hopper = synthetic_step(100.0, np.array([.4, .5, .6]), np.zeros(3), np.zeros(3), np.zeros(3))
        self.assertTrue(np.all(stored >= 0))
        self.assertAlmostEqual(100.0, outlet + stored.sum() + hopper, places=10)

    def test_last_field_rapping_does_not_recollect_in_fake_field(self):
        outlet, stored, hopper = synthetic_step(0.0, np.zeros(3), np.array([0., 0., 10.]), np.array([0., 0., .5]), np.array([0., 0., .2]))
        self.assertAlmostEqual(outlet, 4.0)
        self.assertAlmostEqual(hopper, 1.0)
        self.assertAlmostEqual(stored[2], 5.0)

    def test_identifiability_identities(self):
        c, k, a = 1000., 4.6, 2.
        self.assertAlmostEqual(c * np.exp(-k), (a * c) * np.exp(-(k + np.log(a))))
        self.assertAlmostEqual((.3 * 5.) / 100., (.6 * 2.5) / 100.)

    def test_kernel_is_causal_and_additive(self):
        index = pd.date_range("2025-01-01", periods=100, freq="10s")
        starts = pd.Series(False, index=index); starts.iloc[10] = True; starts.iloc[20] = True
        joint = _causal_kernel(starts, 30)
        one = _causal_kernel(starts.where(np.arange(len(starts)) != 20, False), 30)
        two = _causal_kernel(starts.where(np.arange(len(starts)) != 10, False), 30)
        self.assertEqual(joint.iloc[:10].sum(), 0)
        np.testing.assert_allclose(joint, one + two, rtol=1e-6, atol=1e-7)

    def test_gap_and_nan_require_warmup(self):
        index = pd.date_range("2025-01-01", periods=12, freq="10s").append(pd.date_range("2025-01-01 00:03:00", periods=12, freq="10s"))
        mask = pd.Series(True, index=index); mask.iloc[5] = False
        valid = _continuous_valid(mask, 4)
        self.assertFalse(valid.iloc[8])
        self.assertFalse(valid.iloc[12])
        self.assertTrue(valid.iloc[-1])

    def test_future_mutation_does_not_change_prior_core_fit(self):
        index = pd.date_range("2025-01-01", periods=140, freq="10s")
        frame = pd.DataFrame({"process": np.linspace(0, 1, 140), "rap": 0.,
                              "u": 40 + np.sin(np.arange(140)), "flow_proxy": 150.,
                              "dust_mg_Nm3": 5 + np.cos(np.arange(140))}, index=index)
        first = fit_core(frame.iloc[:100], ["process"], ["rap"], ["u"])
        changed = frame.copy(); changed.iloc[100:, changed.columns.get_loc("dust_mg_Nm3")] = 1e6
        second = fit_core(changed.iloc[:100], ["process"], ["rap"], ["u"])
        np.testing.assert_allclose(first.theta, second.theta)


if __name__ == "__main__":
    unittest.main()
