import unittest

import numpy as np
import pandas as pd

from src.hybrid_esp_validation import Support, d1_split


class HybridEspValidationTests(unittest.TestCase):
    def test_d1_is_chronological_and_calibration_is_before_evaluation(self):
        index = pd.date_range("2025-07-01", "2025-07-16 23:59", freq="1min")
        frame = pd.DataFrame({"valid_origin": True, "dust_mg_Nm3": 1.}, index=index)
        fit, calibration, evaluation = d1_split(frame)
        self.assertLess(frame.index[fit].max(), frame.index[calibration].min())
        self.assertLess(frame.index[calibration].max(), frame.index[evaluation].min())

    def test_support_flags_unseen_values(self):
        train = pd.DataFrame({"x": np.linspace(0, 1, 100), "y": np.linspace(0, 1, 100)})
        check = pd.DataFrame({"x": [.5, 1e6], "y": [.5, 1e6]})
        support = Support(["x", "y"]).fit(train).classify(check)
        self.assertEqual(support.iloc[0], "supported")
        self.assertEqual(support.iloc[1], "outside")


if __name__ == "__main__":
    unittest.main()
