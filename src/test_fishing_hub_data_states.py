import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from activities.rendering.hub_page import render_fishing_hub
from activities.rendering.location_page import render_fishing_location


class FishingHubDataStateTests(unittest.TestCase):
    def setUp(self):
        self.location = {
            "name": "Bar Harbor",
            "state": "Maine",
            "state_code": "ME",
            "state_slug": "maine",
            "slug": "bar-harbor",
            "page_path": "tides/maine/bar-harbor/index.html",
            "timezone": "America/New_York",
        }

    def result(self, *, status, confidence, score=None, rating=None):
        day = {
            "status": status,
            "confidence": confidence,
            "score": score,
            "rating": rating,
            "ranking_eligible": confidence in {"High", "Medium"} and score is not None,
            "best_window": None,
            "reasons": [],
        }
        return {
            "activity": "fishing",
            "today": day,
            "tomorrow": dict(day),
            "hourly": {
                "today": [{
                    "time": "2026-08-30T10:00:00-04:00",
                    "final_score": score,
                    "raw_quality_score": score,
                    "confidence": confidence,
                    "hard_stop": False,
                    "components": {},
                    "reasons": [],
                }],
                "tomorrow": [],
            },
            "safety_disclaimer": "Fishing Score is a planning metric, not a safety guarantee.",
        }

    def snapshot(self):
        return {
            "hourly": [{
                "time": "2026-08-30T10:00:00-04:00",
                "wind_mph": 8.0,
                "gust_mph": 10.0,
                "wave_height_ft": None,
                "wave_period_s": None,
                "precip_probability_pct": 10.0,
                "air_temperature_f": 70.0,
                "water_temperature_f": None,
                "condition_text": "Partly Sunny",
            }],
            "alerts": {"status": "ok", "items": []},
            "tide": {"hilo": []},
        }

    def test_limited_group_hides_numeric_recommendation_even_if_diagnostic_score_exists(self):
        results = {
            "bar-harbor": self.result(
                status="Limited",
                confidence="Limited",
                score=88.4,
                rating="Good",
            )
        }
        html = render_fishing_hub({"bar-harbor": self.location}, results)
        limited = html.split("<h3>Limited / Unavailable</h3>", 1)[1]
        self.assertIn("Bar Harbor", limited)
        self.assertIn("Limited", limited)
        self.assertNotIn("88.4 Good", limited)

    def test_end_of_day_locations_have_their_own_group_not_poor_unfavorable(self):
        results = {
            "bar-harbor": self.result(
                status="No 3-hour window remaining",
                confidence="High",
            )
        }
        html = render_fishing_hub({"bar-harbor": self.location}, results)
        self.assertIn("<h3>Today’s Window Closed</h3>", html)
        closed = html.split("<h3>Today’s Window Closed</h3>", 1)[1]
        self.assertIn("Bar Harbor", closed)
        if "<h3>Poor / Unfavorable</h3>" in html:
            poor = html.split("<h3>Poor / Unfavorable</h3>", 1)[1].split("</section>", 1)[0]
            self.assertNotIn("Bar Harbor", poor)

    def test_not_recommended_remains_visible_when_confidence_is_limited(self):
        results = {
            "bar-harbor": self.result(
                status="NOT RECOMMENDED",
                confidence="Limited",
                score=42.0,
                rating="Poor",
            )
        }
        html = render_fishing_hub({"bar-harbor": self.location}, results)
        section = html.split("<h3>Not Recommended</h3>", 1)[1].split("</section>", 1)[0]
        self.assertIn("Bar Harbor", section)
        self.assertIn("NOT RECOMMENDED", section)
        self.assertNotIn("<strong>Limited</strong>", section)

    def test_limited_location_page_hides_diagnostic_fishing_scores(self):
        result = self.result(
            status="Limited",
            confidence="Limited",
            score=88.4,
            rating="Good",
        )
        html = render_fishing_location(self.location, result, self.snapshot())
        hero = html.split('class="activity-score-card', 1)[1].split("</section>", 1)[0]
        self.assertIn("Limited", hero)
        self.assertNotIn("88.4", hero)
        day_cards = html.split('class="activity-day-switch"', 1)[1].split("</section>", 1)[0]
        self.assertNotIn("88.4", day_cards)
        hourly = html.split("<h2>Hourly Fishing Score</h2>", 1)[1].split("</section>", 1)[0]
        self.assertIn("Limited", hourly)
        self.assertNotIn("88.4", hourly)


if __name__ == "__main__":
    unittest.main()
