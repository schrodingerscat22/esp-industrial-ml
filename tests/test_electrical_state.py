import unittest

import numpy as np
import pandas as pd

from src.electrical_state import FIELDS, RAPPING_TAGS, derive_electrical_state, generic_rapping_features, process_context, required_columns, signal_quality


class ElectricalStateTest(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2020-01-01", periods=200, freq="10s")
        self.df = pd.DataFrame(1.0, index=self.index, columns=required_columns(True))
        self.df["008A01345"] = 10.0
        for field in FIELDS:
            self.df[field.voltage] = 50.0
            self.df[field.current] = 250.0
            self.df[field.power] = 12.5
            self.df[field.spark] = 0.0
            self.df[field.enabled] = 1.0
            self.df[field.collecting_rapper] = 0.0
            self.df[field.discharge_rapper] = 0.0
        self.df.loc[self.index[20], FIELDS[2].collecting_rapper] = 1.0

    def test_ohms_law_units_and_power(self):
        state = derive_electrical_state(self.df)
        self.assertAlmostEqual(state.loc[self.index[10], "field_1_R_app_Mohm"], .2)
        self.assertAlmostEqual(state.loc[self.index[10], "field_1_P_UI_kW"], 12.5)
        self.assertEqual(state.loc[self.index[20], f"rapping_{FIELDS[2].collecting_rapper}_start"], 1)

    def test_invalid_measurements_do_not_make_resistance(self):
        for current, quality in ((0, "invalid_current"), (5, "low_current"), (-2, "invalid_current")):
            with self.subTest(current=current):
                item = self.df.copy()
                item.loc[self.index[10], FIELDS[0].current] = current
                state = derive_electrical_state(item)
                self.assertTrue(np.isnan(state.loc[self.index[10], "field_1_R_app_Mohm"]))
                self.assertEqual(state.loc[self.index[10], "field_1_quality"], quality)

    def test_gap_does_not_make_start_or_known_elapsed(self):
        signal = self.df[FIELDS[0].collecting_rapper].drop(self.index[10:20])
        signal.loc[self.index[20]] = 1.0
        features = generic_rapping_features(signal, "r")
        self.assertEqual(features.loc[self.index[20], "r_start"], 0)
        self.assertTrue(np.isnan(features.loc[self.index[20], "r_minutes_since_0_15"]))

    def test_quality_and_context(self):
        state = derive_electrical_state(self.df)
        quality = signal_quality(self.df, state)
        self.assertEqual(len(quality), 3)
        self.assertAlmostEqual(quality.loc[0, "P_UI_tag_MAE_kW"], 0.0)
        context = process_context(self.df)
        self.assertIn("flue_temperature_mean_C", context)


if __name__ == "__main__":
    unittest.main()
