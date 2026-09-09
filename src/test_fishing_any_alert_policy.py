import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.fishing import fishing_safety_decision, score_fishing_snapshot


class FishingAnyActiveAlertPolicyTests(unittest.TestCase):
    def test_any_active_nws_alert_hard_stops_numeric_fishing_score(self):
        hour = {
            "wind_mph": 6,
            "gust_mph": 9,
            "wave_height_ft": 2,
            "wave_period_s": 8,
            "condition_text": "Clear",
        }
        for event in (
            "Heat Advisory",
            "Small Craft Advisory",
            "Rip Current Statement",
            "Dense Fog Advisory",
            "Coastal Flood Advisory",
            "Special Weather Statement",
        ):
            with self.subTest(event=event):
                result = fishing_safety_decision(
                    hour,
                    [{"event": event, "headline": event, "description": "Active NWS alert."}],
                    coast_bearing=None,
                ).apply(92)
                self.assertTrue(result["hard_stop"])
                self.assertEqual(result["status"], "NOT RECOMMENDED")
                self.assertIsNone(result["final_score"])
                self.assertIn(event.lower().replace(" ", "-"), result["reasons"])

    def test_current_active_alert_keeps_today_not_recommended_even_if_later_window_is_clear(self):
        now = datetime.fromisoformat("2026-09-08T18:15:00-07:00")
        fetched = "2026-09-09T01:15:00+00:00"
        snapshot = {
            "generated_at_utc": fetched,
            "providers": {
                "alerts": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
                "forecast": {"source": "NWS", "status": "ok", "fetched_at_utc": fetched},
            },
            "hourly": [
                {
                    "time": f"2026-09-08T{hour:02d}:00:00-07:00",
                    "wind_mph": 6,
                    "gust_mph": 9,
                    "wind_direction_deg": 270,
                    "precip_probability_pct": 0,
                    "wave_height_ft": 2,
                    "wave_period_s": 8,
                    "water_temperature_f": 65,
                    "condition_text": "Clear",
                }
                for hour in range(18, 23)
            ],
            "alerts": {
                "status": "ok",
                "items": [{
                    "event": "Heat Advisory",
                    "headline": "Heat Advisory",
                    "description": "Active now, ending before the later window.",
                    "effective": "2026-09-08T18:00:00-07:00",
                    "onset": "2026-09-08T18:00:00-07:00",
                    "ends": "2026-09-08T19:00:00-07:00",
                    "expires": "2026-09-08T19:00:00-07:00",
                }],
            },
            "astronomy": {
                "today": {
                    "civil_dawn": "2026-09-08T05:30:00-07:00",
                    "sunrise": "2026-09-08T06:00:00-07:00",
                    "sunset": "2026-09-08T19:00:00-07:00",
                    "civil_dusk": "2026-09-08T19:30:00-07:00",
                    "moon_phase_fraction": 0.5,
                },
                "tomorrow": {},
            },
            "tide": {
                "hilo": [
                    {"t": "2026-09-08 17:00", "type": "L", "v": 1.0},
                    {"t": "2026-09-08 23:00", "type": "H", "v": 5.0},
                ]
            },
        }
        location = {
            "slug": "san-diego",
            "timezone": "America/Los_Angeles",
            "activity": {"coast_bearing": 270},
        }
        result = score_fishing_snapshot(snapshot, location=location, now=now)
        self.assertEqual(result["today"]["status"], "NOT RECOMMENDED")
        self.assertIsNone(result["today"]["score"])
        self.assertIsNone(result["today"]["best_window"])
        self.assertFalse(result["today"]["ranking_eligible"])
        self.assertIn("heat-advisory", result["today"]["reasons"])


if __name__ == "__main__":
    unittest.main()
