import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.fishing import score_fishing_snapshot
from seo import activity_robots_directive


class ActivityEndOfDayTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "name": "San Diego",
            "state": "California",
            "state_code": "CA",
            "state_slug": "california",
            "slug": "san-diego",
            "page_path": "tides/california/san-diego/index.html",
            "timezone": "America/Los_Angeles",
            "activity": {"coast_bearing": 270.0},
        }
        self.now = datetime(2026, 8, 30, 5, 15, tzinfo=timezone.utc)  # Aug 29, 10:15 PM PDT
        hourly = []
        for stamp in (
            "2026-08-29T22:00:00-07:00",
            "2026-08-29T23:00:00-07:00",
            "2026-08-30T00:00:00-07:00",
            "2026-08-30T01:00:00-07:00",
            "2026-08-30T02:00:00-07:00",
            "2026-08-30T03:00:00-07:00",
        ):
            hourly.append({
                "time": stamp,
                "wind_mph": 7.0,
                "gust_mph": 10.0,
                "wind_direction_deg": 250.0,
                "precip_probability_pct": 5.0,
                "air_temperature_f": 68.0,
                "wave_height_ft": 2.0,
                "wave_period_s": 8.0,
                "water_temperature_f": 66.0,
                "condition_text": "Clear",
            })
        fetched = "2026-08-30T05:15:00+00:00"
        self.snapshot = {
            "schema_version": 1,
            "location": "san-diego",
            "timezone": "America/Los_Angeles",
            "generated_at_utc": fetched,
            "providers": {
                "alerts": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "marine": {"source": "NWS forecastGridData", "status": "ok", "fetched_at_utc": fetched},
                "tide": {"source": "NOAA/NOS/CO-OPS", "status": "ok", "fetched_at_utc": fetched},
            },
            "alerts": {"status": "ok", "items": []},
            "hourly": hourly,
            "tide": {
                "hilo": [
                    {"t": "2026-08-29 20:00", "v": 5.0, "type": "H"},
                    {"t": "2026-08-30 02:00", "v": 0.5, "type": "L"},
                    {"t": "2026-08-30 08:00", "v": 5.2, "type": "H"},
                ]
            },
            "astronomy": {
                "today": {
                    "civil_dawn": "2026-08-29T05:45:00-07:00",
                    "sunrise": "2026-08-29T06:10:00-07:00",
                    "sunset": "2026-08-29T19:15:00-07:00",
                    "civil_dusk": "2026-08-29T19:40:00-07:00",
                    "moon_phase_fraction": 0.5,
                },
                "tomorrow": {
                    "civil_dawn": "2026-08-30T05:46:00-07:00",
                    "sunrise": "2026-08-30T06:11:00-07:00",
                    "sunset": "2026-08-30T19:14:00-07:00",
                    "civil_dusk": "2026-08-30T19:39:00-07:00",
                    "moon_phase_fraction": 0.53,
                },
            },
            "provenance": {},
        }

    def test_late_evening_is_not_mislabeled_as_data_unavailable(self):
        result = score_fishing_snapshot(self.snapshot, location=self.location, now=self.now)
        self.assertEqual(result["today"]["status"], "No 3-hour window remaining")
        self.assertIsNone(result["today"]["score"])
        self.assertFalse(result["today"]["ranking_eligible"])
        self.assertIn(result["tomorrow"]["confidence"], {"High", "Medium"})
        self.assertIsNotNone(result["tomorrow"]["score"])

    def test_tomorrow_usable_data_keeps_page_indexable_after_today_window_closes(self):
        result = score_fishing_snapshot(self.snapshot, location=self.location, now=self.now)
        self.assertEqual(activity_robots_directive(result), "index,follow")

    def test_true_data_failure_still_noindexes(self):
        result = {
            "today": {"status": "Unavailable", "confidence": "Unavailable"},
            "tomorrow": {"status": "Unavailable", "confidence": "Unavailable"},
        }
        self.assertEqual(activity_robots_directive(result), "noindex,follow")


if __name__ == "__main__":
    unittest.main()
