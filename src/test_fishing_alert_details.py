import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.location_page import _safety_strip, _why_section


class FishingAlertDetailTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "timezone": "America/Los_Angeles",
            "alerts": {
                "status": "ok",
                "items": [
                    {
                        "event": "Beach Hazards Statement",
                        "onset": "2026-08-30T05:00:00-07:00",
                        "ends": "2026-08-30T11:00:00-07:00",
                        "expires": "2026-08-30T12:00:00-07:00",
                        "description": (
                            "* WHAT...Sneaker waves and strong rip currents are expected.\n\n"
                            "* WHERE...Pacific Coast beaches."
                        ),
                    }
                ],
            },
        }
        self.result = {
            "today": {
                "status": "normal",
                "score": 87,
                "rating": "Good",
                "confidence": "High",
                "best_window": {
                    "start": "2026-08-30T06:00:00-07:00",
                    "end": "2026-08-30T09:00:00-07:00",
                },
                "reasons": ["favorable-tide-movement", "light-wind"],
            }
        }

    def test_safety_strip_shows_event_period_and_hazard_summary(self):
        html = _safety_strip(self.result, self.snapshot)
        self.assertIn("Beach Hazards Statement", html)
        self.assertIn("Aug 30, 5:00 AM–11:00 AM PDT", html)
        self.assertIn("Sneaker waves and strong rip currents are expected.", html)

    def test_why_section_puts_alert_details_before_score_explanation(self):
        html = _why_section(self.result, self.snapshot)
        self.assertIn("NWS alert details:", html)
        self.assertIn("Beach Hazards Statement", html)
        self.assertIn("Aug 30, 5:00 AM–11:00 AM PDT", html)
        self.assertIn("overlaps the 6:00 AM–9:00 AM fishing window", html)
        self.assertIn("official alert should be reviewed first", html)
        self.assertLess(html.index("NWS alert details:"), html.index("Conditions are generally supportive"))


if __name__ == "__main__":
    unittest.main()
