import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.location_page import render_fishing_location


LOCATION = {
    "name": "San Diego",
    "state": "California",
    "state_code": "CA",
    "state_slug": "california",
    "slug": "san-diego",
    "page_path": "tides/california/san-diego/index.html",
    "timezone": "America/Los_Angeles",
}

SNAPSHOT = {"alerts": {"status": "ok", "items": []}, "hourly": [], "tide": {"hilo": []}}


def row(timestamp: str, score: float | None, *, hard_stop: bool = False):
    return {
        "time": timestamp,
        "final_score": score,
        "raw_quality_score": 90,
        "confidence": "High",
        "hard_stop": hard_stop,
        "components": {},
        "reasons": ["beach-hazards-statement"] if hard_stop else ["light-wind"],
    }


class Fishing24HourForecastTests(unittest.TestCase):
    def test_hourly_forecast_spans_next_24_hours_across_today_and_tomorrow(self):
        today_rows = [row(f"2026-09-08T{hour:02d}:00:00-07:00", 82 + (hour - 20)) for hour in range(20, 24)]
        tomorrow_rows = [row(f"2026-09-09T{hour:02d}:00:00-07:00", 86) for hour in range(20)]
        result = {
            "today": {"status": "normal", "score": 84, "rating": "Good", "confidence": "High", "best_window": None, "ranking_eligible": True, "reasons": []},
            "tomorrow": {"status": "normal", "score": 86, "rating": "Good", "confidence": "High", "best_window": None, "ranking_eligible": True, "reasons": []},
            "hourly": {"today": today_rows, "tomorrow": tomorrow_rows},
            "safety_disclaimer": "Fishing Score is a planning metric, not a safety guarantee.",
        }
        html = render_fishing_location(LOCATION, result, SNAPSHOT)
        self.assertIn("24-Hour Fishing Conditions Forecast", html)
        self.assertIn("NEXT 24 HOURS", html)
        self.assertEqual(html.count('class="activity-hour-row"'), 24)
        self.assertIn("8:00 PM", html)
        self.assertIn("7:00 PM", html)

    def test_alert_hours_show_not_recommended_but_later_safe_hours_keep_scores(self):
        today_rows = [
            row("2026-09-08T20:00:00-07:00", None, hard_stop=True),
            row("2026-09-08T21:00:00-07:00", None, hard_stop=True),
            row("2026-09-08T22:00:00-07:00", 78),
            row("2026-09-08T23:00:00-07:00", 80),
        ]
        tomorrow_rows = [row(f"2026-09-09T{hour:02d}:00:00-07:00", 82) for hour in range(20)]
        result = {
            "today": {"status": "NOT RECOMMENDED", "score": None, "rating": None, "confidence": "High", "best_window": None, "ranking_eligible": False, "reasons": ["beach-hazards-statement"]},
            "tomorrow": {"status": "normal", "score": 82, "rating": "Good", "confidence": "High", "best_window": None, "ranking_eligible": True, "reasons": []},
            "hourly": {"today": today_rows, "tomorrow": tomorrow_rows},
            "safety_disclaimer": "Fishing Score is a planning metric, not a safety guarantee.",
        }
        html = render_fishing_location(LOCATION, result, SNAPSHOT)
        self.assertEqual(html.count('class="activity-hour-row"'), 24)
        self.assertGreaterEqual(html.count("NOT RECOMMENDED"), 2)
        self.assertIn(">78<", html)
        self.assertIn(">82<", html)
        self.assertNotIn("hourly numerical recommendation is not shown", html)


if __name__ == "__main__":
    unittest.main()
