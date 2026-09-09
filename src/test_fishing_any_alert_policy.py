import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.scoring.fishing import fishing_safety_decision


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


if __name__ == "__main__":
    unittest.main()
