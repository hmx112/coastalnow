import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.hub_page import render_fishing_hub
from activities.rendering.location_page import render_fishing_location


class ActivityRenderingTests(unittest.TestCase):
    def setUp(self):
        self.san_diego = {
            "name": "San Diego",
            "state": "California",
            "state_code": "CA",
            "state_slug": "california",
            "slug": "san-diego",
            "page_path": "tides/california/san-diego/index.html",
            "timezone": "America/Los_Angeles",
        }
        self.result = {
            "activity": "fishing",
            "location": "san-diego",
            "scorer_version": "fishing-v1",
            "generated_at_utc": "2026-08-30T12:00:00+00:00",
            "today": {
                "status": "normal",
                "score": 87.0,
                "rating": "Good",
                "confidence": "High",
                "best_window": {
                    "start": "2026-08-30T06:00:00-07:00",
                    "end": "2026-08-30T09:00:00-07:00",
                },
                "ranking_eligible": True,
                "reasons": ["favorable-tide-movement", "light-wind", "manageable-sea-state"],
            },
            "tomorrow": {
                "status": "normal",
                "score": 76.0,
                "rating": "Good",
                "confidence": "Medium",
                "best_window": {
                    "start": "2026-08-31T07:00:00-07:00",
                    "end": "2026-08-31T10:00:00-07:00",
                },
                "ranking_eligible": True,
                "reasons": ["light-wind"],
            },
            "hourly": {
                "today": [
                    {"time": "2026-08-30T06:00:00-07:00", "final_score": 84, "raw_quality_score": 84, "confidence": "High", "hard_stop": False, "components": {"tide": 85, "wind": 100, "wave": 100, "weather": 100, "time_of_day": 100, "solunar": 70, "water_temperature": 75}, "reasons": ["favorable-tide-movement", "light-wind"]},
                    {"time": "2026-08-30T07:00:00-07:00", "final_score": 90, "raw_quality_score": 90, "confidence": "High", "hard_stop": False, "components": {"tide": 100, "wind": 100, "wave": 100, "weather": 100, "time_of_day": 100, "solunar": 70, "water_temperature": 75}, "reasons": ["favorable-tide-movement", "light-wind", "manageable-sea-state"]},
                    {"time": "2026-08-30T08:00:00-07:00", "final_score": 88, "raw_quality_score": 88, "confidence": "High", "hard_stop": False, "components": {"tide": 92, "wind": 100, "wave": 100, "weather": 100, "time_of_day": 100, "solunar": 70, "water_temperature": 75}, "reasons": ["light-wind", "manageable-sea-state"]},
                ],
                "tomorrow": [],
            },
            "scope": "shore / pier / nearshore recreational fishing",
            "safety_disclaimer": "Fishing Score is a planning metric, not a safety guarantee. Official warnings and local guidance always take priority.",
        }
        self.snapshot = {
            "hourly": [
                {"time": "2026-08-30T06:00:00-07:00", "wind_mph": 8.0, "gust_mph": 12.0, "wave_height_ft": 2.0, "wave_period_s": 8.0, "precip_probability_pct": 10.0, "air_temperature_f": 72.0, "water_temperature_f": 66.0, "condition_text": "Mostly Sunny"},
                {"time": "2026-08-30T07:00:00-07:00", "wind_mph": 9.0, "gust_mph": 13.0, "wave_height_ft": 2.1, "wave_period_s": 8.0, "precip_probability_pct": 10.0, "air_temperature_f": 73.0, "water_temperature_f": 66.0, "condition_text": "Mostly Sunny"},
                {"time": "2026-08-30T08:00:00-07:00", "wind_mph": 10.0, "gust_mph": 14.0, "wave_height_ft": 2.2, "wave_period_s": 8.0, "precip_probability_pct": 15.0, "air_temperature_f": 74.0, "water_temperature_f": 66.0, "condition_text": "Sunny"},
            ],
            "alerts": {"status": "ok", "items": []},
            "tide": {
                "hilo": [
                    {"t": "2026-08-30 04:12", "v": 0.7, "type": "L"},
                    {"t": "2026-08-30 10:31", "v": 5.2, "type": "H"},
                ]
            },
        }

    def test_location_page_contains_decision_information_and_bidirectional_links(self):
        html = render_fishing_location(self.san_diego, self.result, self.snapshot)
        self.assertIn("San Diego Fishing Conditions Today", html)
        self.assertIn("87", html)
        self.assertIn("Good", html)
        self.assertIn("Best Fishing Time", html)
        self.assertIn("6:00 AM–9:00 AM", html)
        self.assertIn("Confidence", html)
        self.assertIn("High", html)
        self.assertIn("Why this score?", html)
        self.assertIn("Hourly Fishing Score", html)
        self.assertIn("Tide movement", html)
        self.assertIn("Wind", html)
        self.assertIn("Wave / sea state", html)
        self.assertIn("2.0 ft", html)
        self.assertIn("8.0 sec", html)
        self.assertIn("/tides/california/san-diego/", html)
        self.assertIn("/fishing/", html)
        self.assertIn("not a safety guarantee", html)
        self.assertNotIn("{{", html)
        self.assertNotIn("}}", html)

    def test_hard_stop_page_never_publishes_raw_excellent_score_as_recommendation(self):
        result = dict(self.result)
        result["today"] = {
            "status": "NOT RECOMMENDED",
            "score": None,
            "rating": None,
            "confidence": "High",
            "best_window": None,
            "ranking_eligible": False,
            "reasons": ["high-surf-warning"],
        }
        result["hourly"] = {
            "today": [{"time": "2026-08-30T06:00:00-07:00", "raw_quality_score": 97, "final_score": None, "confidence": "High", "hard_stop": True, "components": {"tide": 100, "wind": 100, "wave": 100, "weather": 100, "time_of_day": 100, "solunar": 70, "water_temperature": 75}, "reasons": ["high-surf-warning"]}],
            "tomorrow": [],
        }
        html = render_fishing_location(self.san_diego, result, self.snapshot)
        self.assertIn("NOT RECOMMENDED", html)
        hero = html.split('class="activity-score-card', 1)[1].split("</section>", 1)[0]
        self.assertNotIn(">97<", hero)
        self.assertIn("Safety condition takes priority", html)

    def test_limited_and_unavailable_pages_show_data_state_not_fake_score(self):
        for state in ("Limited", "Unavailable"):
            result = dict(self.result)
            result["today"] = {
                "status": state,
                "score": None,
                "rating": None,
                "confidence": state,
                "best_window": None,
                "ranking_eligible": False,
                "reasons": [],
            }
            result["hourly"] = {"today": [], "tomorrow": []}
            html = render_fishing_location(self.san_diego, result, self.snapshot)
            self.assertIn(state, html)
            score_card = html.split('class="activity-score-card', 1)[1].split("</section>", 1)[0]
            self.assertIn("—", score_card)
            self.assertNotRegex(score_card, r">\d{2,3}<")

    def test_hub_ranks_only_high_medium_then_groups_other_states(self):
        locations = {
            "san-diego": self.san_diego,
            "monterey": {**self.san_diego, "name": "Monterey", "slug": "monterey"},
            "key-west": {**self.san_diego, "name": "Key West", "state": "Florida", "state_code": "FL", "state_slug": "florida", "slug": "key-west"},
            "galveston": {**self.san_diego, "name": "Galveston", "state": "Texas", "state_code": "TX", "state_slug": "texas", "slug": "galveston"},
            "cannon-beach": {**self.san_diego, "name": "Cannon Beach", "state": "Oregon", "state_code": "OR", "state_slug": "oregon", "slug": "cannon-beach"},
        }
        def result(score, rating, confidence="High", status="normal", eligible=True):
            return {
                "activity": "fishing",
                "today": {"score": score, "rating": rating, "confidence": confidence, "status": status, "ranking_eligible": eligible, "best_window": {"start": "2026-08-30T06:00:00-07:00", "end": "2026-08-30T09:00:00-07:00"} if score is not None else None, "reasons": ["light-wind"]},
                "tomorrow": {"score": score, "rating": rating, "confidence": confidence, "status": status, "ranking_eligible": eligible, "best_window": None, "reasons": []},
            }
        results = {
            "san-diego": result(88, "Good", "High"),
            "monterey": result(91, "Excellent", "Medium"),
            "key-west": result(91, "Excellent", "High"),
            "galveston": result(None, None, "Limited", "Limited", False),
            "cannon-beach": result(None, None, "High", "NOT RECOMMENDED", False),
        }
        html = render_fishing_hub(locations, results)
        ranking = html.split('id="top-locations"', 1)[1].split('id="condition-groups"', 1)[0]
        ranked_names = re.findall(r'<h3>([^<]+)</h3>', ranking)
        # Equal scores use location name as stable tie break.
        self.assertEqual(ranked_names[:3], ["Key West", "Monterey", "San Diego"])
        self.assertNotIn("Galveston", ranking)
        self.assertNotIn("Cannon Beach", ranking)
        self.assertIn("Limited / Unavailable", html)
        self.assertIn("Galveston", html)
        self.assertIn("Not Recommended", html)
        self.assertIn("Cannon Beach", html)
        self.assertIn("Why #1 today", html)
        self.assertIn("/tides/florida/key-west/fishing/", html)
        self.assertNotIn("{{", html)


if __name__ == "__main__":
    unittest.main()
