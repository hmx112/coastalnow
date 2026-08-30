import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.conditions.providers.nws import parse_grid_data


class NwsZeroWavePeriodTests(unittest.TestCase):
    def test_zero_wave_period_is_unknown_not_a_valid_zero_second_wave(self):
        payload = {
            "properties": {
                "waveHeight": {
                    "uom": "wmoUnit:m",
                    "values": [{"validTime": "2026-08-30T00:00:00+00:00/PT2H", "value": 0.0}],
                },
                "wavePeriod": {
                    "uom": "wmoUnit:s",
                    "values": [{"validTime": "2026-08-30T00:00:00+00:00/PT2H", "value": 0.0}],
                },
            }
        }
        rows = parse_grid_data(payload)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["wave_height_ft"], 0.0)
        self.assertIsNone(rows[0]["wave_period_s"])
        self.assertIsNone(rows[1]["wave_period_s"])


if __name__ == "__main__":
    unittest.main()
