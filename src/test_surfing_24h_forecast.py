import unittest

from activities.rendering.surfing_page import _hourly_section


def _row(time: str, score: float | None, *, hard_stop: bool = False, confidence: str = "High") -> dict:
    return {
        "time": time,
        "final_score": score,
        "hard_stop": hard_stop,
        "confidence": confidence,
    }


class Surfing24HourForecastTests(unittest.TestCase):
    def test_hourly_forecast_spans_next_24_hours_across_midnight(self):
        today = [
            _row(f"2026-09-08T{hour:02d}:00:00-07:00", 80 + (hour - 20))
            for hour in range(20, 24)
        ]
        tomorrow = [
            _row(f"2026-09-09T{hour:02d}:00:00-07:00", 70 + hour / 10)
            for hour in range(24)
        ]
        result = {
            "today": {"status": "normal", "confidence": "High"},
            "hourly": {"today": today, "tomorrow": tomorrow},
        }

        html = _hourly_section(result)

        self.assertIn("NEXT 24 HOURS", html)
        self.assertIn("24-Hour Surf Conditions Forecast", html)
        self.assertEqual(html.count('class="activity-hour-row"'), 24)
        self.assertIn("8:00 PM", html)
        self.assertIn("12:00 AM", html)
        self.assertIn("7:00 PM", html)
        self.assertNotIn("8:00 PM</span><div class=\"activity-hour-track\"><i style=\"width:72%", html)

    def test_active_alert_hours_render_not_recommended_without_hiding_safe_hours(self):
        today = [
            _row("2026-09-08T20:00:00-07:00", None, hard_stop=True),
            _row("2026-09-08T21:00:00-07:00", None, hard_stop=True),
            _row("2026-09-08T22:00:00-07:00", 88.0),
            _row("2026-09-08T23:00:00-07:00", 87.0),
        ]
        tomorrow = [
            _row(f"2026-09-09T{hour:02d}:00:00-07:00", 86.0)
            for hour in range(24)
        ]
        result = {
            "today": {"status": "NOT RECOMMENDED", "confidence": "High"},
            "hourly": {"today": today, "tomorrow": tomorrow},
        }

        html = _hourly_section(result)

        self.assertGreaterEqual(html.count("NOT RECOMMENDED"), 2)
        self.assertIn("Alert active", html)
        self.assertIn(">88<", html)
        self.assertNotIn("hourly numerical planning score is not shown", html)
        self.assertIn("Active NWS alert hours show NOT RECOMMENDED", html)


if __name__ == "__main__":
    unittest.main()
