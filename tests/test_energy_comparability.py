import unittest

import pandas as pd

from src.electrical_state import FIELDS, RAPPING_TAGS
from src.energy_comparability import BLOCK_SECONDS, complete_blocks, gate_decision, match_blocks


class EnergyComparabilityTest(unittest.TestCase):
    def _state_context(self):
        index = pd.date_range("2020-01-01", periods=61, freq="10s")
        state = pd.DataFrame(index=index)
        state["total_P_tag_kW"] = 12.0
        state["dust_mg_Nm3"] = 10.0
        for field in FIELDS:
            state[f"field_{field.number}_P_tag_kW"] = 4.0
        for tag in RAPPING_TAGS:
            state[f"rapping_{tag}_minutes_since_0_15"] = -1.0
        context = pd.DataFrame({"generator_MW": 30., "flue_flow_thousand_m3_h": 150., "flue_temperature_mean_C": 125.,
                                "flue_temperature_L_minus_R_C": 0., "flue_moisture_pct": 5., "O2_before_OPP_L_pct": 6.,
                                "O2_before_OPP_R_pct": 6., "burner_a_on": 0.}, index=index)
        return state, context

    def test_complete_block_energy_uses_left_endpoints(self):
        state, context = self._state_context()
        blocks, rejected = complete_blocks(state, context)
        self.assertEqual(len(blocks), 1)
        self.assertAlmostEqual(blocks.loc[0, "energy_kWh"], 2.0)
        self.assertEqual(blocks.loc[0, "duration_seconds"], BLOCK_SECONDS)
        self.assertEqual(rejected["right_edge_missing"], 1)

    def test_matching_avoids_same_day_and_dust_is_not_a_match_input(self):
        base = {"generator_MW": 30., "flue_flow_thousand_m3_h": 150., "flue_temperature_mean_C": 125.,
                "flue_temperature_L_minus_R_C": 0., "flue_moisture_pct": 5., "O2_before_OPP_L_pct": 6., "O2_before_OPP_R_pct": 6., "burner_a_on": 0.}
        rows = []
        for number, day in enumerate(pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"])):
            row = dict(base, block_start=day, day=day, mean_power_kW=38. if number % 2 == 0 else 42., energy_kWh=6.3,
                       dust_mean_mg_Nm3=10. + number, dust_p95_mg_Nm3=12.)
            for tag in RAPPING_TAGS:
                row[f"phase_{tag}"] = ">15"; row[f"active_seconds_{tag}"] = 0
            rows.append(row)
        pairs, report = match_blocks(pd.DataFrame(rows), level=3)
        self.assertGreaterEqual(len(pairs), 1)
        self.assertTrue((pairs.low_day != pairs.high_day).all())
        self.assertGreater(report["coverage_pct"], 0)
        self.assertEqual(gate_decision(pairs, report)["decision"], "B")

    def test_matching_records_configured_power_sensitivity(self):
        base = {"generator_MW": 30., "flue_flow_thousand_m3_h": 150., "flue_temperature_mean_C": 125.,
                "flue_temperature_L_minus_R_C": 0., "flue_moisture_pct": 5., "O2_before_OPP_L_pct": 6., "O2_before_OPP_R_pct": 6., "burner_a_on": 0.}
        rows = []
        for day, power in zip(pd.to_datetime(["2020-01-01", "2020-01-02"]), (38., 42.)):
            row = dict(base, block_start=day, day=day, mean_power_kW=power, energy_kWh=6.3,
                       dust_mean_mg_Nm3=10., dust_p95_mg_Nm3=12.)
            for tag in RAPPING_TAGS:
                row[f"phase_{tag}"] = ">15"; row[f"active_seconds_{tag}"] = 0
            rows.append(row)
        pairs, report = match_blocks(pd.DataFrame(rows), level=3, power_difference_kw=3.)
        self.assertEqual(report["minimum_power_difference_kw"], 3.)
        self.assertTrue((pairs.minimum_power_difference_kw == 3.).all())


if __name__ == "__main__":
    unittest.main()
