import unittest

from activities.rendering.surfing_alert_details import (
    build_detailed_surfing_explanation as build_surfing_explanation,
)
from activities.rendering.surfing_page import render_surfing_location
from locations import LOCATIONS


def _row(time="2026-09-03T17:00:00-07:00", score=100.0, **overrides):
    row = {
        "time": time,
        "components": {
            "wave_height": 100,
            "wave_period": 100,
            "wind": 100,
            "weather": 100,
            "daylight": 100,
        },
        "raw_quality_score": score,
        "final_score": score,
        "hard_stop": False,
        "safety_status": "normal",
        "safety_cap": 100.0,
        "safety_penalty": 0,
        "confidence": "High",
        "available": True,
        "ranking_eligible": True,
        "reasons": ["moderate-wave-height", "organized-wave-period", "lighter-wind"],
    }
    row.update(overrides)
    return row


def _result(row, *, score=100.0, window_end="2026-09-03T20:00:00-07:00"):
    day = {
        "status": "normal",
        "score": score,
        "rating": "Excellent",
        "confidence": "High",
        "best_window": {"start": row["time"], "end": window_end},
        "ranking_eligible": True,
        "reasons": row["reasons"],
    }
    return {
        "today": day,
        "tomorrow": day,
        "hourly": {"today": [row], "tomorrow": [row]},
        "safety_disclaimer": "Surf Conditions Score is a planning metric, not a safety guarantee or a break-specific forecast.",
    }


def _raw(row):
    return {
        "time": row["time"],
        "wave_height_ft": 3.0,
        "wave_period_s": 9.0,
        "wind_mph": 3.0,
        "gust_mph": 13.8,
        "precip_probability_pct": 10.0,
        "condition_text": "Mostly Sunny",
    }


def _snapshot(row, alerts, *, timezone="America/Los_Angeles"):
    return {
        "timezone": timezone,
        "alerts": {"status": "ok", "items": alerts},
        "hourly": [_raw(row)],
        "tide": {"hilo": [{"t": "2026-09-03 14:17", "type": "H", "v": "5.4"}]},
    }


class SurfingAlertDetailTests(unittest.TestCase):
    def test_future_beach_hazards_statement_shows_full_period_and_hazards(self):
        row = _row()
        result = _result(row)
        alert = {
            "event": "Beach Hazards Statement",
            "onset": "2026-09-04T06:00:00-07:00",
            "expires": "2026-09-03T07:00:00-07:00",
            "ends": "2026-09-07T23:00:00-07:00",
            "description": (
                "* WHAT...Increased risk of sneaker waves and strong rip currents due to incoming long period "
                "southerly swell. Breaking waves to around 10 feet expected.\n\n"
                "* WHERE...Pacific Coast beaches."
            ),
        }
        snapshot = _snapshot(row, [alert])

        text = build_surfing_explanation(result, snapshot)
        self.assertIn(
            "NWS alert details: Beach Hazards Statement (Sep 4, 6:00 AM – Sep 7, 11:00 PM PDT).",
            text,
        )
        self.assertIn("begins after the 5:00 PM–8:00 PM planning window", text)
        self.assertNotIn("in effect today", text)

        html = render_surfing_location(LOCATIONS["santa-cruz"], result, snapshot)
        self.assertIn("1 NWS alert for this location", html)
        self.assertIn("Beach Hazards Statement", html)
        self.assertIn("Sep 4, 6:00 AM – Sep 7, 11:00 PM PDT", html)
        self.assertIn("sneaker waves", html)
        self.assertIn("strong rip currents", html)
        self.assertIn("around 10 feet", html)

    def test_multiple_nws_alerts_are_all_listed_with_periods(self):
        row = _row()
        result = _result(row)
        alerts = [
            {
                "event": "Beach Hazards Statement",
                "onset": "2026-09-04T06:00:00-07:00",
                "ends": "2026-09-07T23:00:00-07:00",
                "description": "* WHAT...Sneaker waves and strong rip currents expected.",
            },
            {
                "event": "Dense Fog Advisory",
                "onset": "2026-09-03T22:00:00-07:00",
                "ends": "2026-09-04T08:00:00-07:00",
                "description": "* WHAT...Visibility one quarter mile or less in dense fog.",
            },
        ]
        snapshot = _snapshot(row, alerts)

        text = build_surfing_explanation(result, snapshot)
        self.assertIn("Beach Hazards Statement (Sep 4, 6:00 AM – Sep 7, 11:00 PM PDT)", text)
        self.assertIn("Dense Fog Advisory (Sep 3, 10:00 PM – Sep 4, 8:00 AM PDT)", text)

        html = render_surfing_location(LOCATIONS["santa-cruz"], result, snapshot)
        self.assertIn("2 NWS alerts for this location", html)
        self.assertIn("Beach Hazards Statement", html)
        self.assertIn("Dense Fog Advisory", html)
        self.assertIn("Visibility one quarter mile or less", html)

    def test_applied_alert_keeps_period_before_score_effect(self):
        row = _row(
            time="2026-09-03T06:00:00-07:00",
            score=69.0,
            raw_quality_score=92.0,
            final_score=69.0,
            safety_cap=69.0,
            reasons=["moderate-wave-height", "lighter-wind", "small-craft-advisory"],
        )
        result = _result(row, score=69.0, window_end="2026-09-03T09:00:00-07:00")
        alert = {
            "event": "Small Craft Advisory",
            "onset": "2026-09-03T05:00:00-07:00",
            "ends": "2026-09-03T12:00:00-07:00",
            "description": "* WHAT...Hazardous conditions for small craft.",
        }
        text = build_surfing_explanation(result, _snapshot(row, [alert]))

        self.assertTrue(text.startswith("NWS alert details: Small Craft Advisory (Sep 3, 5:00 AM–12:00 PM PDT)."))
        self.assertIn("caps the Surf Conditions Score at 69", text)


if __name__ == "__main__":
    unittest.main()
