import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.surfing_policy import score_surfing_activity, surfing_safety_decision


BASE_HOUR = {
    "time": "2026-09-08T17:00:00-07:00",
    "wave_height_ft": 4.0,
    "wave_period_s": 7.0,
    "wind_mph": 3.0,
    "gust_mph": 6.0,
    "wind_direction_deg": 270.0,
    "precip_probability_pct": 0.0,
    "condition_text": "Partly Sunny",
}


class SurfingActiveAlertPolicyTests(unittest.TestCase):
    def test_any_active_nws_alert_hard_stops_numeric_surf_score(self):
        for event in (
            "Heat Advisory",
            "Dense Fog Advisory",
            "Coastal Flood Advisory",
            "Special Weather Statement",
        ):
            with self.subTest(event=event):
                decision = surfing_safety_decision(
                    BASE_HOUR,
                    [{"event": event}],
                    coast_bearing=270.0,
                ).apply(95)
                self.assertTrue(decision["hard_stop"])
                self.assertEqual(decision["status"], "NOT RECOMMENDED")
                self.assertIsNone(decision["final_score"])

    def test_future_alert_does_not_block_before_onset(self):
        now = datetime.fromisoformat("2026-09-08T17:30:00-07:00")
        fetched = "2026-09-09T00:30:00+00:00"
        snapshot = {
            "schema_version": 1,
            "location": "half-moon-bay",
            "timezone": "America/Los_Angeles",
            "generated_at_utc": fetched,
            "providers": {
                "alerts": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "marine": {"source": "NWS forecastGridData", "status": "ok", "fetched_at_utc": fetched},
            },
            "alerts": {
                "status": "ok",
                "items": [{
                    "event": "Heat Advisory",
                    "onset": "2026-09-09T10:00:00-07:00",
                    "ends": "2026-09-10T22:00:00-07:00",
                }],
            },
            "hourly": [
                {
                    **BASE_HOUR,
                    "time": f"2026-09-08T{hour:02d}:00:00-07:00",
                }
                for hour in (17, 18, 19, 20)
            ],
            "astronomy": {
                "today": {
                    "civil_dawn": "2026-09-08T06:00:00-07:00",
                    "sunrise": "2026-09-08T06:30:00-07:00",
                    "sunset": "2026-09-08T19:30:00-07:00",
                    "civil_dusk": "2026-09-08T20:00:00-07:00",
                },
                "tomorrow": {},
            },
        }
        location = {
            "slug": "half-moon-bay",
            "timezone": "America/Los_Angeles",
            "activity": {"coast_bearing": 270.0},
        }
        result = score_surfing_activity(snapshot, location=location, now=now)
        self.assertEqual(result["today"]["status"], "normal")
        self.assertIsNotNone(result["today"]["score"])
        self.assertTrue(result["today"]["ranking_eligible"])


if __name__ == "__main__":
    unittest.main()
