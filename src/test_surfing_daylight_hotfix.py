import unittest
from datetime import date
from zoneinfo import ZoneInfo

from activities.conditions.astronomy import solar_events
from activities.scoring.surfing_policy import daylight_quality, score_surfing_hour


SOLAR = {
    "dawn": "2026-09-03T05:50:00-07:00",
    "sunrise": "2026-09-03T06:15:00-07:00",
    "sunset": "2026-09-03T19:10:00-07:00",
    "dusk": "2026-09-03T19:35:00-07:00",
}

FRESH = {
    "normal_safety_state_allowed": True,
    "alerts": "fresh",
    "forecast": "fresh",
    "marine": "fresh",
    "high_medium_eligible": True,
}

BASE_HOUR = {
    "wave_height_ft": 3.0,
    "wave_period_s": 10.0,
    "wind_mph": 6.0,
    "gust_mph": 8.0,
    "wind_direction_deg": 270.0,
    "precip_probability_pct": 10.0,
    "condition_text": "Clear",
}


class SurfingDaylightHotfixTests(unittest.TestCase):
    def test_san_diego_solar_events_stay_on_requested_local_date(self):
        day = date(2026, 9, 3)
        events = solar_events(
            day,
            latitude=32.71419,
            longitude=-117.17358,
            tz=ZoneInfo("America/Los_Angeles"),
        )
        for name in ("dawn", "sunrise", "sunset", "dusk"):
            with self.subTest(name=name):
                self.assertIsNotNone(events[name])
                self.assertEqual(events[name].date(), day)
        self.assertLess(events["dawn"], events["sunrise"])
        self.assertLess(events["sunrise"], events["sunset"])
        self.assertLess(events["sunset"], events["dusk"])

    def test_daylight_quality_uses_snapshot_dawn_and_dusk_keys(self):
        self.assertEqual(daylight_quality("2026-09-03T00:00:00-07:00", SOLAR), 35)
        self.assertEqual(daylight_quality("2026-09-03T12:00:00-07:00", SOLAR), 100)

    def test_otherwise_equal_daytime_hour_scores_above_midnight(self):
        night = score_surfing_hour(
            {**BASE_HOUR, "time": "2026-09-03T00:00:00-07:00"},
            solar=SOLAR,
            alerts=[],
            freshness=FRESH,
            coast_bearing=270.0,
        )
        daytime = score_surfing_hour(
            {**BASE_HOUR, "time": "2026-09-03T12:00:00-07:00"},
            solar=SOLAR,
            alerts=[],
            freshness=FRESH,
            coast_bearing=270.0,
        )
        self.assertEqual(night["components"]["daylight"], 35)
        self.assertEqual(daytime["components"]["daylight"], 100)
        self.assertGreater(daytime["final_score"], night["final_score"])


if __name__ == "__main__":
    unittest.main()
