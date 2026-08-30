import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.conditions.providers.nws import parse_grid_data


class NwsDurationParsingTests(unittest.TestCase):
    def grid(self, valid_time):
        return {
            "properties": {
                "waveHeight": {
                    "uom": "wmoUnit:m",
                    "values": [{"validTime": valid_time, "value": 1.0}],
                },
                "wavePeriod": {
                    "uom": "wmoUnit:s",
                    "values": [{"validTime": valid_time, "value": 8.0}],
                },
            }
        }

    def test_nws_iso8601_day_and_hour_durations_expand_to_hourly_rows(self):
        cases = {
            "2026-08-30T00:00:00+00:00/P1DT18H": 42,
            "2026-08-30T00:00:00+00:00/P2D": 48,
            "2026-08-30T00:00:00+00:00/P7DT4H": 172,
        }
        for valid_time, expected_hours in cases.items():
            with self.subTest(valid_time=valid_time):
                rows = parse_grid_data(self.grid(valid_time))
                self.assertEqual(len(rows), expected_hours)
                self.assertIsNotNone(rows[0]["wave_height_ft"])
                self.assertEqual(rows[0]["wave_period_s"], 8.0)


if __name__ == "__main__":
    unittest.main()
