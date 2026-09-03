import unittest

from activities.scoring.surfing_policy import (
    SURFING_WEIGHTS,
    score_surfing_hour,
    wave_height_quality,
    wave_period_quality,
    wind_quality,
)


GOOD_HOUR = {
    "time": "2026-09-03T10:00:00-07:00",
    "wave_height_ft": 3.0,
    "wave_period_s": 11.0,
    "wind_mph": 6.0,
    "gust_mph": 8.0,
    "wind_direction_deg": 270.0,
    "precip_probability_pct": 10.0,
    "condition_text": "Sunny",
}

SOLAR = {
    "civil_dawn": "2026-09-03T05:50:00-07:00",
    "sunrise": "2026-09-03T06:15:00-07:00",
    "sunset": "2026-09-03T19:10:00-07:00",
    "civil_dusk": "2026-09-03T19:35:00-07:00",
}

FRESH = {
    "normal_safety_state_allowed": True,
    "alerts": "fresh",
    "forecast": "fresh",
    "marine": "fresh",
    "high_medium_eligible": True,
}

FAILED_ALERTS = {
    **FRESH,
    "normal_safety_state_allowed": False,
    "alerts": "unknown",
}


class SurfingPolicyTests(unittest.TestCase):
    def test_weights_are_fixed_v1_contract(self):
        self.assertEqual(
            SURFING_WEIGHTS,
            {
                "wave_height": 0.30,
                "wave_period": 0.25,
                "wind": 0.25,
                "weather": 0.10,
                "daylight": 0.10,
            },
        )
        self.assertAlmostEqual(sum(SURFING_WEIGHTS.values()), 1.0)

    def test_moderate_wave_height_scores_above_extreme_height(self):
        self.assertGreater(wave_height_quality(3.0), wave_height_quality(10.5))

    def test_useful_period_scores_above_short_period(self):
        self.assertGreater(wave_period_quality(11.0), wave_period_quality(4.0))

    def test_light_wind_scores_above_strong_wind(self):
        self.assertGreater(wind_quality(6.0), wind_quality(25.0))

    def test_missing_wave_period_is_limited_and_not_ranking_eligible(self):
        hour = dict(GOOD_HOUR)
        hour["wave_period_s"] = None
        row = score_surfing_hour(
            hour,
            alerts=[],
            freshness=FRESH,
            solar=SOLAR,
            coast_bearing=270.0,
        )
        self.assertEqual(row["confidence"], "Limited")
        self.assertFalse(row["ranking_eligible"])

    def test_alert_failure_is_unavailable(self):
        row = score_surfing_hour(
            GOOD_HOUR,
            alerts=[],
            freshness=FAILED_ALERTS,
            solar=SOLAR,
            coast_bearing=270.0,
        )
        self.assertEqual(row["confidence"], "Unavailable")
        self.assertFalse(row["available"])

    def test_high_surf_warning_hard_stops_even_high_quality(self):
        row = score_surfing_hour(
            GOOD_HOUR,
            alerts=[{"event": "High Surf Warning"}],
            freshness=FRESH,
            solar=SOLAR,
            coast_bearing=270.0,
        )
        self.assertTrue(row["hard_stop"])
        self.assertEqual(row["safety_status"], "NOT RECOMMENDED")

    def test_not_recommended_priority_above_limited(self):
        hour = dict(GOOD_HOUR)
        hour["wave_period_s"] = None
        row = score_surfing_hour(
            hour,
            alerts=[{"event": "Tsunami Warning"}],
            freshness=FRESH,
            solar=SOLAR,
            coast_bearing=270.0,
        )
        self.assertTrue(row["hard_stop"])
        self.assertEqual(row["safety_status"], "NOT RECOMMENDED")

    def test_forecast_thunderstorm_caps_score(self):
        hour = dict(GOOD_HOUR)
        hour["condition_text"] = "Thunderstorms likely"
        row = score_surfing_hour(
            hour,
            alerts=[],
            freshness=FRESH,
            solar=SOLAR,
            coast_bearing=270.0,
        )
        self.assertLessEqual(row["final_score"], 39)


if __name__ == "__main__":
    unittest.main()
