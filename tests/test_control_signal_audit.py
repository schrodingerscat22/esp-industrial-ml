import unittest

import pandas as pd

from src.control_signal_audit import audit_decision, signal_inventory


class ControlSignalAuditTest(unittest.TestCase):
    def _classification(self):
        return pd.DataFrame([
            {"tag": "U", "description": "Napięcie wtórne", "unit": "kV", "category": "esp_voltage", "role": "input"},
            {"tag": "M", "description": "Tryb cykliczny / ciągły", "unit": "", "category": "esp_rapping", "role": "input"},
            {"tag": "S", "description": "Wartość zadana napięcia", "unit": "kV", "category": "esp_other", "role": "input"},
        ])

    def test_measurement_is_not_called_a_controller_input(self):
        inventory = signal_inventory(pd.DataFrame({"U": [30., 31.], "M": [0, 1]}), self._classification())
        self.assertEqual(inventory.set_index("tag").loc["U", "semantic_class"], "measured_electrical_response")
        self.assertEqual(inventory.set_index("tag").loc["M", "semantic_class"], "mode_candidate")

    def test_explicit_setpoint_is_the_only_positive_controller_decision(self):
        no_setpoint = signal_inventory(pd.DataFrame({"U": [30., 31.], "M": [0, 1]}), self._classification().iloc[:2])
        self.assertEqual(audit_decision(no_setpoint)["decision"], "no_recorded_controller_input")
        with_setpoint = signal_inventory(pd.DataFrame({"U": [30., 31.], "M": [0, 1], "S": [30., 30.]}), self._classification())
        self.assertTrue(audit_decision(with_setpoint)["controller_signal_found"])


if __name__ == "__main__":
    unittest.main()
