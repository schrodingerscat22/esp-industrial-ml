import unittest
import numpy as np
import pandas as pd
from src.model_features import TARGET, clean_inputs, fit_schema, process_features, dust_history, chronological_blocks


class ModelFeaturesTest(unittest.TestCase):
    def setUp(self):
        idx = pd.date_range('2020-01-01', periods=500, freq='10s')
        self.df = pd.DataFrame({TARGET: np.arange(500.), 'x': np.arange(500.), 'state': 0.}, index=idx)

    def test_current_and_future_target_cannot_change_current_history(self):
        original = dust_history(self.df)
        changed = self.df.copy()
        changed.iloc[250:, 0] = -1234
        pd.testing.assert_frame_equal(original.iloc[:251], dust_history(changed).iloc[:251])
        self.assertEqual(original.iloc[250].dust_past_mean_6, np.mean(np.arange(244,250)))

    def test_future_process_values_do_not_change_past_features(self):
        schema = fit_schema(self.df.iloc[:250], ['x','state'])
        before = process_features(self.df, schema)
        changed = self.df.copy()
        changed.iloc[251:,1:] = 9999
        pd.testing.assert_frame_equal(before.iloc[:251], process_features(changed,schema).iloc[:251])
        self.assertFalse(any(TARGET in c for c in before.columns))

    def test_20_second_gap_invalidates_full_history(self):
        df = self.df.drop(self.df.index[250])
        schema = fit_schema(df.iloc[:200], ['x'])
        X = process_features(df,schema)
        self.assertTrue(np.isnan(X.loc[self.df.index[251], 'x_lag_1']))
        self.assertTrue(np.isnan(X.loc[self.df.index[400], 'x_lag_180']))
        self.assertEqual(X.loc[self.df.index[431], 'x_lag_180'], 251.)
        self.assertTrue(dust_history(df).loc[self.df.index[251]].isna().all())

    def test_no_label_or_state_imputation(self):
        df = self.df.copy()
        df.iloc[1,0] = np.nan
        df.iloc[2,2] = np.nan
        clean = clean_inputs(df,['x','state'])
        self.assertEqual(len(clean),498)
        self.assertNotIn(df.index[1], clean.index)
        self.assertNotIn(df.index[2], clean.index)
        with self.assertRaises(ValueError):
            clean_inputs(df,[TARGET,'x'])

    def test_schema_is_fitted_only_on_training_period(self):
        train = self.df.iloc[:250]
        schema = fit_schema(train,['x','state'])
        self.assertEqual(schema['continuous'],['x'])
        changed = self.df.copy()
        changed.iloc[250:,2] = np.arange(250.)
        self.assertEqual(schema,fit_schema(changed.iloc[:250],['x','state']))

    def test_validation_and_test_do_not_overlap(self):
        blocks = chronological_blocks(self.df.index)
        self.assertEqual(blocks[0][2],blocks[1][1])
        self.assertEqual(blocks[1][2],blocks[2][1])
        self.assertIsNone(blocks[2][2])
        self.assertEqual(blocks[2][1],self.df.index[400])


if __name__ == '__main__':
    unittest.main()
