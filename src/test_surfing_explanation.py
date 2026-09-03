import unittest

from activities.rendering.surfing_explanation import build_surfing_explanation
from activities.rendering.surfing_page import render_surfing_location
from locations import LOCATIONS


LOCATION = LOCATIONS["san-diego"]


def _row(time="2026-09-03T06:00:00-07:00", score=86.2, **overrides):
    row = {
        "time": time,
        "components": {
            "wave_height": 100,
            "wave_period": 55,
            "wind": 90,
            "weather": 100,
            "daylight": 100,
        },
        "raw_quality_score": 86.2,
        "final_score": score,
        "hard_stop": False,
        "safety_status": "normal",
        "safety_cap": 100.0,
        "safety_penalty": 0,
        "confidence": "High",
        "available": True,
        "ranking_eligible": True,
        "reasons": ["moderate-wave-height", "lighter-wind"],
    }
    row.update(overrides)
    return row


def _result(row, *, score=86.2, status="normal", window_end="2026-09-03T09:00:00-07:00"):
    day = {
        "status": status,
        "score": None if status == "NOT RECOMMENDED" else score,
        "rating": "Good" if status == "normal" else None,
        "confidence": "High",
        "best_window": None if status == "NOT RECOMMENDED" else {"start": row["time"], "end": window_end},
        "ranking_eligible": status == "normal",
        "reasons": row["reasons"],
    }
    return {
        "today": day,
        "tomorrow": day,
        "hourly": {"today": [row], "tomorrow": [row]},
        "safety_disclaimer": "Surf Conditions Score is a planning metric, not a safety guarantee or a break-specific forecast.",
    }


def _snapshot(raw, alerts=None, *, alert_status="ok"):
    return {
        "alerts": {"status": alert_status, "items": alerts or []},
        "hourly": [raw],
        "tide": {"hilo": [{"t": "2026-09-03 11:00", "type": "H", "v": "4.2"}]},
    }


class SurfingExplanationTests(unittest.TestCase):
    def test_high_score_names_actual_support_and_main_drag(self):
        row = _row()
        raw = {
            "time": row["time"],
            "wave_height_ft": 3.0,
            "wave_period_s": 6.0,
            "wind_mph": 5.0,
            "gust_mph": 6.0,
            "precip_probability_pct": 0.0,
            "condition_text": "Sunny",
        }
        text = build_surfing_explanation(_result(row), _snapshot(raw))
        self.assertIn("Today's 86.2 score", text)
        self.assertIn("3.0 ft wave height", text)
        self.assertIn("5 mph winds", text)
        self.assertIn("6 sec wave period", text)
        self.assertIn("keeping the score below the top range", text)

    def test_low_score_leads_with_actual_drags(self):
        row = _row(
            score=49,
            components={"wave_height": 100, "wave_period": 25, "wind": 45, "weather": 100, "daylight": 100},
            raw_quality_score=49,
            final_score=49,
        )
        raw = {
            "time": row["time"],
            "wave_height_ft": 3.0,
            "wave_period_s": 4.0,
            "wind_mph": 18.0,
            "gust_mph": 22.0,
            "precip_probability_pct": 0.0,
            "condition_text": "Sunny",
        }
        text = build_surfing_explanation(_result(row, score=49), _snapshot(raw))
        self.assertIn("Today's 49 score is being held down mainly", text)
        self.assertIn("18 mph winds", text)
        self.assertIn("short 4 sec wave period", text)

    def test_overlapping_nws_alert_is_first_and_names_score_cap(self):
        row = _row(
            score=69,
            raw_quality_score=92,
            final_score=69,
            safety_cap=69,
            reasons=["moderate-wave-height", "lighter-wind", "small-craft-advisory"],
        )
        raw = {
            "time": row["time"],
            "wave_height_ft": 3.0,
            "wave_period_s": 11.0,
            "wind_mph": 5.0,
            "gust_mph": 6.0,
            "precip_probability_pct": 0.0,
            "condition_text": "Sunny",
        }
        alert = {
            "event": "Small Craft Advisory",
            "onset": "2026-09-03T05:00:00-07:00",
            "ends": "2026-09-03T12:00:00-07:00",
        }
        text = build_surfing_explanation(_result(row, score=69), _snapshot(raw, [alert]))
        self.assertTrue(text.startswith("NWS Small Craft Advisory"))
        self.assertIn("caps the Surf Conditions Score at 69", text)

    def test_future_nws_alert_is_first_and_explains_no_direct_reduction(self):
        row = _row(
            time="2026-09-03T07:00:00-04:00",
            score=97.5,
            components={"wave_height": 100, "wave_period": 100, "wind": 90, "weather": 100, "daylight": 100},
            raw_quality_score=97.5,
            final_score=97.5,
        )
        raw = {
            "time": row["time"],
            "wave_height_ft": 2.0,
            "wave_period_s": 9.0,
            "wind_mph": 8.0,
            "gust_mph": 10.0,
            "precip_probability_pct": 2.0,
            "condition_text": "Sunny",
        }
        alert = {
            "event": "Heat Advisory",
            "onset": "2026-09-03T11:00:00-04:00",
            "ends": "2026-09-03T20:00:00-04:00",
        }
        result = _result(row, score=97.5, window_end="2026-09-03T10:00:00-04:00")
        text = build_surfing_explanation(result, _snapshot(raw, [alert]))
        self.assertTrue(text.startswith("NWS Heat Advisory"))
        self.assertIn("begins after", text)
        self.assertIn("does not directly reduce", text)

    def test_nws_hard_stop_warning_is_primary_reason(self):
        row = _row(
            score=None,
            hard_stop=True,
            safety_status="NOT RECOMMENDED",
            safety_cap=0,
            raw_quality_score=95,
            final_score=None,
            reasons=["high-surf-warning"],
        )
        raw = {
            "time": row["time"],
            "wave_height_ft": 7.0,
            "wave_period_s": 12.0,
            "wind_mph": 8.0,
            "gust_mph": 10.0,
            "precip_probability_pct": 5.0,
            "condition_text": "Sunny",
        }
        alert = {
            "event": "High Surf Warning",
            "onset": "2026-09-03T05:00:00-07:00",
            "ends": "2026-09-03T12:00:00-07:00",
        }
        text = build_surfing_explanation(_result(row, status="NOT RECOMMENDED"), _snapshot(raw, [alert]))
        self.assertTrue(text.startswith("NWS High Surf Warning"))
        self.assertIn("primary reason", text)
        self.assertIn("NOT RECOMMENDED", text)

    def test_non_alert_wind_hard_stop_names_actual_trigger(self):
        row = _row(
            score=None,
            hard_stop=True,
            safety_status="NOT RECOMMENDED",
            safety_cap=0,
            raw_quality_score=90,
            final_score=None,
            reasons=["wind-hard-stop"],
        )
        raw = {
            "time": row["time"],
            "wave_height_ft": 3.0,
            "wave_period_s": 11.0,
            "wind_mph": 41.0,
            "gust_mph": 52.0,
            "precip_probability_pct": 5.0,
            "condition_text": "Windy",
        }
        text = build_surfing_explanation(_result(row, status="NOT RECOMMENDED"), _snapshot(raw))
        self.assertTrue(text.startswith("41 mph sustained wind"))
        self.assertIn("Surfing Safety Gate", text)
        self.assertIn("NOT RECOMMENDED", text)

    def test_location_page_uses_dynamic_explanation_instead_of_old_generic_copy(self):
        row = _row()
        raw = {
            "time": row["time"],
            "wave_height_ft": 3.0,
            "wave_period_s": 6.0,
            "wind_mph": 5.0,
            "gust_mph": 6.0,
            "precip_probability_pct": 0.0,
            "condition_text": "Sunny",
        }
        html = render_surfing_location(LOCATION, _result(row), _snapshot(raw))
        self.assertIn("Today&#x27;s 86.2 score", html)
        self.assertIn("3.0 ft wave height", html)
        self.assertIn("6 sec wave period", html)
        self.assertNotIn("Moderate wave height supports the composite planning score.", html)


if __name__ == "__main__":
    unittest.main()
