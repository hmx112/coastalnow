import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.engine import group_local_days
from activities.scoring.surfing_policy import score_surfing_activity


class ActivityCurrentPlanningTests(unittest.TestCase):
    def test_today_group_excludes_hours_that_have_already_finished(self):
        now = datetime.fromisoformat("2026-08-29T19:30:00-07:00")
        hourly = [
            {"time": "2026-08-29T18:00:00-07:00"},
            {"time": "2026-08-29T19:00:00-07:00"},
            {"time": "2026-08-29T20:00:00-07:00"},
            {"time": "2026-08-29T23:00:00-07:00"},
            {"time": "2026-08-30T00:00:00-07:00"},
        ]
        grouped = group_local_days(hourly, "America/Los_Angeles", now)
        self.assertEqual(
            [row["time"] for row in grouped["today"]],
            [
                "2026-08-29T19:00:00-07:00",
                "2026-08-29T20:00:00-07:00",
                "2026-08-29T23:00:00-07:00",
            ],
        )
        self.assertEqual(
            [row["time"] for row in grouped["tomorrow"]],
            ["2026-08-30T00:00:00-07:00"],
        )

    def test_current_active_surf_hard_stop_overrides_later_safe_window(self):
        now = datetime.fromisoformat("2026-09-08T06:30:00-04:00")
        fetched = "2026-09-08T10:30:00+00:00"
        location = {
            "slug": "wrightsville-beach",
            "timezone": "America/New_York",
            "activity": {"coast_bearing": 90.0},
        }
        snapshot = {
            "schema_version": 1,
            "location": "wrightsville-beach",
            "timezone": "America/New_York",
            "generated_at_utc": fetched,
            "providers": {
                "alerts": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "marine": {"source": "NWS forecastGridData", "status": "ok", "fetched_at_utc": fetched},
            },
            "alerts": {
                "status": "ok",
                "items": [
                    {
                        "event": "Rip Current Statement",
                        "onset": "2026-09-08T06:00:00-04:00",
                        "ends": "2026-09-08T20:00:00-04:00",
                        "headline": "Dangerous rip currents expected",
                        "description": "Dangerous rip currents expected.",
                    }
                ],
            },
            "hourly": [
                {
                    "time": f"2026-09-08T{hour:02d}:00:00-04:00",
                    "wave_height_ft": 3.0,
                    "wave_period_s": 10.0,
                    "wind_mph": 6.0,
                    "gust_mph": 8.0,
                    "wind_direction_deg": 90.0,
                    "precip_probability_pct": 5.0,
                    "condition_text": "Clear",
                }
                for hour in (21, 22, 23)
            ],
            "astronomy": {
                "today": {
                    "civil_dawn": "2026-09-08T05:30:00-04:00",
                    "sunrise": "2026-09-08T06:00:00-04:00",
                    "sunset": "2026-09-08T19:30:00-04:00",
                    "civil_dusk": "2026-09-08T20:00:00-04:00",
                },
                "tomorrow": {},
            },
        }
        result = score_surfing_activity(snapshot, location=location, now=now)
        today = result["today"]
        self.assertEqual(today["status"], "NOT RECOMMENDED")
        self.assertIsNone(today["score"])
        self.assertIsNone(today["best_window"])
        self.assertFalse(today["ranking_eligible"])
        self.assertIn("rip-current-statement", today["reasons"])


if __name__ == "__main__":
    unittest.main()
