import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_tides import desktop_forecast_rows, mobile_forecast


class TideForecastChronologyTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "station": {"timezone": "America/Los_Angeles"},
            "hilo": [
                {"t": "2026-09-10 03:17", "v": -0.5, "type": "L"},
                {"t": "2026-09-10 09:33", "v": 5.2, "type": "H"},
                {"t": "2026-09-10 15:17", "v": 0.9, "type": "L"},
                {"t": "2026-09-10 21:22", "v": 6.1, "type": "H"},
                {"t": "2026-09-11 03:47", "v": -0.1, "type": "L"},
                {"t": "2026-09-11 10:01", "v": 5.5, "type": "H"},
            ],
        }
        self.start = date(2026, 9, 10)

    def test_desktop_forecast_uses_one_tide_events_cell_in_chronological_order(self):
        html = desktop_forecast_rows(self.data, self.start)
        first_row = html.split("</tr>", 1)[0]
        self.assertEqual(first_row.count("<td"), 2)
        self.assertLess(first_row.index("Low"), first_row.index("High"))
        self.assertLess(first_row.index("3:17 AM"), first_row.index("9:33 AM"))
        self.assertLess(first_row.index("9:33 AM"), first_row.index("3:17 PM"))
        self.assertLess(first_row.index("3:17 PM"), first_row.index("9:22 PM"))
        self.assertNotIn("Next", first_row)

    def test_mobile_forecast_keeps_only_same_day_events_in_time_order(self):
        html = mobile_forecast(self.data, self.start)
        first_day = html.split("</article>", 1)[0]
        self.assertLess(first_day.index("Low · 3:17 AM"), first_day.index("High · 9:33 AM"))
        self.assertLess(first_day.index("High · 9:33 AM"), first_day.index("Low · 3:17 PM"))
        self.assertLess(first_day.index("Low · 3:17 PM"), first_day.index("High · 9:22 PM"))
        self.assertNotIn("Next", first_day)
        self.assertNotIn("3:47 AM Fri", first_day)


if __name__ == "__main__":
    unittest.main()
